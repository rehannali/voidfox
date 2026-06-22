#!/usr/bin/env python3
"""
voidfox_core.py
===============

Shared library for the voidfox tooling. Pure Python standard library only,
so every script that imports it runs out-of-the-box on Windows, macOS and
Linux with nothing more than a Python 3.8+ interpreter.

voidfox uses Betterfox (https://github.com/yokoffing/Betterfox) as its source
of truth for the hardened `user.js`. This module knows how to:

  * locate the default Firefox / Zen profile on any platform,
  * download the latest raw Betterfox files,
  * download voidfox's own published files from this repository,
  * merge an upstream `user.js` with the local overrides into a single
    file that is dropped into a browser profile.

It performs NO git operations and never talks to the GitHub plugin/API for
writes; the only network access is plain HTTPS GETs of raw files.
"""

from __future__ import annotations

import os
import shutil
import sys
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

# --------------------------------------------------------------------------- #
# Source-of-truth configuration
# --------------------------------------------------------------------------- #

# Upstream project we build on top of.
BETTERFOX_OWNER = "yokoffing"
BETTERFOX_REPO = "Betterfox"
BETTERFOX_BRANCH = "main"

# This repository (where the GitHub Action commits the synced upstream files
# plus your overrides). update.py pulls the latest published copies from here.
VOIDFOX_OWNER = "rehannali"
VOIDFOX_REPO = "voidfox"
VOIDFOX_BRANCH = "main"

# Repo-relative layout.
UPSTREAM_DIR = "upstream"
OVERRIDES_DIR = "overrides"

# We only care about Firefox and Zen from Betterfox. Waterfox / personal
# variants are intentionally skipped.
#
# Map: destination path inside this repo  ->  path inside the Betterfox repo.
# The combined `user.js` is what actually gets installed; the individual
# module files (Fastfox / Securefox / Peskyfox / Smoothfox) are mirrored for
# reference and so you can lift extra prefs into your overrides.
SYNC_MAP = {
    f"{UPSTREAM_DIR}/firefox/user.js": "user.js",
    f"{UPSTREAM_DIR}/firefox/Fastfox.js": "Fastfox.js",
    f"{UPSTREAM_DIR}/firefox/Securefox.js": "Securefox.js",
    f"{UPSTREAM_DIR}/firefox/Peskyfox.js": "Peskyfox.js",
    f"{UPSTREAM_DIR}/firefox/Smoothfox.js": "Smoothfox.js",
    f"{UPSTREAM_DIR}/zen/user.js": "zen/user.js",
}

# Supported browsers and where each keeps its profiles per platform.
# Paths are evaluated lazily so missing env vars don't blow up on import.
BROWSERS = ("firefox", "zen")


def _appdata() -> Path:
    return Path(os.getenv("APPDATA") or Path.home() / "AppData/Roaming")


def _localappdata() -> Path:
    return Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData/Local")


def profile_roots(browser: str) -> list[Path]:
    """Candidate profile-ROOT directories for *browser* on this platform.

    NOTE: the profile location follows each OS's app-data convention and does
    NOT depend on where the application is installed. On macOS it is always
    under ~/Library/Application Support regardless of whether the .app sits in
    /Applications or ~/Applications. The variation that *does* matter is the
    packaging format (native vs Flatpak vs Snap), which is what the extra
    entries below cover.
    """
    home = Path.home()
    if browser == "firefox":
        if sys.platform.startswith("win"):
            return [_appdata() / "Mozilla/Firefox"]
        if sys.platform == "darwin":
            return [home / "Library/Application Support/Firefox"]
        return [
            home / ".mozilla/firefox",                                       # native
            home / ".var/app/org.mozilla.firefox/.mozilla/firefox",          # flatpak
            home / "snap/firefox/common/.mozilla/firefox",                   # snap
        ]
    if browser == "zen":
        if sys.platform.startswith("win"):
            return [_appdata() / "zen", _localappdata() / "zen"]
        if sys.platform == "darwin":
            return [home / "Library/Application Support/zen"]
        return [
            home / ".zen",                                                   # native
            home / ".var/app/app.zen_browser.zen/.zen",                      # flatpak
        ]
    raise ValueError(f"Unknown browser: {browser!r}")


def app_locations(browser: str) -> list[Path]:
    """Candidate application binary / bundle locations for *browser*.

    Used only for friendlier diagnostics ("installed but never launched") and
    `--diagnose`. The profile path above is what voidfox actually writes to;
    this is purely informational. macOS deliberately includes BOTH the
    system-wide /Applications and the per-user ~/Applications.
    """
    home = Path.home()
    if browser == "firefox":
        if sys.platform.startswith("win"):
            pf = Path(os.getenv("ProgramFiles") or "C:/Program Files")
            pf86 = Path(os.getenv("ProgramFiles(x86)") or "C:/Program Files (x86)")
            return [
                pf / "Mozilla Firefox/firefox.exe",
                pf86 / "Mozilla Firefox/firefox.exe",
                _localappdata() / "Mozilla Firefox/firefox.exe",
            ]
        if sys.platform == "darwin":
            return [
                Path("/Applications/Firefox.app"),
                home / "Applications/Firefox.app",
            ]
        return _which("firefox") + [
            Path("/usr/lib/firefox/firefox"),
            Path("/var/lib/flatpak/exports/bin/org.mozilla.firefox"),
            home / ".local/share/flatpak/exports/bin/org.mozilla.firefox",
            Path("/snap/bin/firefox"),
        ]
    if browser == "zen":
        if sys.platform.startswith("win"):
            pf = Path(os.getenv("ProgramFiles") or "C:/Program Files")
            return [
                _localappdata() / "zen/zen.exe",
                pf / "Zen Browser/zen.exe",
            ]
        if sys.platform == "darwin":
            return [
                Path("/Applications/Zen.app"),
                Path("/Applications/Zen Browser.app"),
                home / "Applications/Zen.app",
                home / "Applications/Zen Browser.app",
            ]
        return _which("zen") + [
            Path("/var/lib/flatpak/exports/bin/app.zen_browser.zen"),
            home / ".local/share/flatpak/exports/bin/app.zen_browser.zen",
        ]
    raise ValueError(f"Unknown browser: {browser!r}")


def _which(name: str) -> list[Path]:
    found = shutil.which(name)
    return [Path(found)] if found else []


def find_installed_app(browser: str) -> Path | None:
    """First existing application location for *browser*, or None."""
    for loc in app_locations(browser):
        if loc.exists():
            return loc
    return None


# --------------------------------------------------------------------------- #
# Small console helpers
# --------------------------------------------------------------------------- #

def info(msg: str) -> None:
    print(f"  {msg}")


def step(msg: str) -> None:
    print(f"==> {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


# --------------------------------------------------------------------------- #
# Networking (raw HTTPS GET only)
# --------------------------------------------------------------------------- #

def http_get(url: str) -> bytes:
    """Fetch *url* and return its raw bytes. Raises on HTTP errors."""
    req = Request(url, headers={"User-Agent": "voidfox-installer"})
    with urlopen(req) as resp:  # noqa: S310 - fixed https hosts only
        return resp.read()


def betterfox_raw_url(repo_path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{BETTERFOX_OWNER}/"
        f"{BETTERFOX_REPO}/{BETTERFOX_BRANCH}/{repo_path}"
    )


def voidfox_raw_url(repo_path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{VOIDFOX_OWNER}/"
        f"{VOIDFOX_REPO}/{VOIDFOX_BRANCH}/{repo_path}"
    )


# --------------------------------------------------------------------------- #
# Profile discovery
# --------------------------------------------------------------------------- #

def find_profile_root(browser: str) -> Path:
    """Best profile root for *browser*.

    A machine may have more than one (e.g. native + Flatpak). Prefer a root
    that actually contains profiles.ini, then one that has any profile dir,
    then just the first that exists.
    """
    existing = [r for r in profile_roots(browser) if r.exists()]
    for root in existing:
        if (root / "profiles.ini").exists():
            return root
    for root in existing:
        if any(c.is_dir() for c in root.glob("*")):
            return root
    if existing:
        return existing[0]

    app = find_installed_app(browser)
    hint = (
        f"\n  {browser.title()} appears to be installed at {app}, but it has no "
        f"profile yet — launch it once, then re-run."
        if app
        else f"\n  Is {browser.title()} installed and has it been launched at least once?"
    )
    raise FileNotFoundError(
        f"Could not find a {browser} profile root. Looked in:\n"
        + "\n".join(f"    {p}" for p in profile_roots(browser))
        + hint
    )


def default_profile_dir(browser: str, explicit: str | None = None) -> Path:
    """Return the default profile directory for *browser*.

    If *explicit* is given it is used verbatim. Otherwise profiles.ini is
    parsed the same way Firefox does, with sensible fallbacks for installs
    that never recorded a default.
    """
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Profile directory does not exist: {p}")
        return p

    root = find_profile_root(browser)
    ini = root / "profiles.ini"

    if ini.exists():
        cp = ConfigParser(strict=False)
        cp.read(ini, encoding="utf-8")

        # 1) An [Install*] section pointing at the default profile.
        for section in cp.sections():
            if section.lower().startswith("install") and cp.has_option(section, "Default"):
                rel = cp[section]["Default"].strip()
                if rel:
                    return _resolve_profile_path(root, cp, rel)

        # 2) A [Profile*] section flagged Default=1.
        for section in cp.sections():
            if cp.has_option(section, "Default") and cp[section]["Default"].strip() == "1":
                rel = cp[section].get("Path", "").strip()
                if rel:
                    return _resolve_profile_path(root, cp, rel)

        # 3) First profile listed.
        for section in cp.sections():
            if section.lower().startswith("profile") and cp.has_option(section, "Path"):
                return _resolve_profile_path(root, cp, cp[section]["Path"].strip())

    # 4) Last-ditch: a single *.default* directory under the root.
    candidates = sorted(
        d for d in root.glob("*") if d.is_dir() and "default" in d.name.lower()
    )
    if candidates:
        return candidates[-1]

    raise FileNotFoundError(
        f"Could not determine the default {browser} profile under {root}. "
        f"Pass --profile-dir to choose one explicitly."
    )


def _resolve_profile_path(root: Path, cp: ConfigParser, rel: str) -> Path:
    # profiles.ini paths may be relative (IsRelative=1, the norm) or absolute.
    candidate = Path(rel)
    if candidate.is_absolute():
        return candidate
    return root / rel


def diagnose(browsers=BROWSERS) -> None:
    """Print what voidfox detects on this machine for each browser."""
    step(f"Platform: {sys.platform}")
    for browser in browsers:
        step(browser)
        app = find_installed_app(browser)
        info(f"app: {app}" if app else "app: not found (checked "
             f"{', '.join(str(p) for p in app_locations(browser))})")
        for root in profile_roots(browser):
            mark = "✓" if root.exists() else "·"
            ini = " (has profiles.ini)" if (root / "profiles.ini").exists() else ""
            info(f"[{mark}] root: {root}{ini}")
        try:
            info(f"=> default profile: {default_profile_dir(browser)}")
        except Exception as exc:
            warn(str(exc).splitlines()[0])


# --------------------------------------------------------------------------- #
# Merge logic
# --------------------------------------------------------------------------- #

VOIDFOX_BANNER = """

/****************************************************************************
 * START: VOIDFOX OVERRIDES                                                 *
 * Everything below is layered on top of Betterfox by voidfox.              *
 * Firefox applies the LAST matching user_pref(), so these win.             *
 * Edit overrides/*.js in the voidfox repo, never this generated file.      *
****************************************************************************/
"""

VOIDFOX_FOOTER = """
/****************************************************************************
 * END: VOIDFOX OVERRIDES                                                   *
****************************************************************************/
"""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def build_user_js(source_dir: Path, browser: str) -> str:
    """Combine the synced upstream user.js with the voidfox overrides.

    *source_dir* is a checkout (or temp download) that contains
    ``upstream/<browser>/user.js`` and ``overrides/{common,<browser>}.js``.
    Overrides are appended after the upstream content so they always win.
    """
    if browser not in BROWSERS:
        raise ValueError(f"Unsupported browser: {browser!r}")

    upstream = source_dir / UPSTREAM_DIR / browser / "user.js"
    if not upstream.exists():
        raise FileNotFoundError(
            f"Upstream user.js not found at {upstream}. "
            f"Run sync.py (or let the GitHub Action) populate {UPSTREAM_DIR}/ first."
        )

    common = source_dir / OVERRIDES_DIR / "common.js"
    specific = source_dir / OVERRIDES_DIR / f"{browser}.js"

    parts = [_read(upstream).rstrip(), VOIDFOX_BANNER.rstrip()]
    common_text = _read(common).strip()
    specific_text = _read(specific).strip()
    if common_text:
        parts.append("\n/* --- overrides/common.js --- */\n" + common_text)
    if specific_text:
        parts.append(f"\n/* --- overrides/{browser}.js --- */\n" + specific_text)
    parts.append(VOIDFOX_FOOTER.rstrip())
    return "\n".join(parts) + "\n"


# --------------------------------------------------------------------------- #
# Installation primitives
# --------------------------------------------------------------------------- #

def backup_user_js(profile_dir: Path) -> Path | None:
    """Back up an existing user.js inside *profile_dir*. Returns the backup path."""
    target = profile_dir / "user.js"
    if not target.exists():
        return None
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    backup = profile_dir / f"user.js.voidfox-backup-{stamp}"
    shutil.copy2(target, backup)
    return backup


def write_user_js(profile_dir: Path, content: str) -> Path:
    profile_dir.mkdir(parents=True, exist_ok=True)
    target = profile_dir / "user.js"
    target.write_text(content, encoding="utf-8")
    return target


def repo_root() -> Path:
    """Directory this module lives in (== the repo root)."""
    return Path(__file__).resolve().parent


def betterfox_version(source_dir: Path | None = None) -> str | None:
    """Best-effort parse of the Betterfox version from the synced user.js header."""
    src = source_dir or repo_root()
    uj = src / UPSTREAM_DIR / "firefox" / "user.js"
    if not uj.exists():
        return None
    for line in _read(uj).splitlines():
        low = line.lower()
        if "version:" in low:
            return line.split("version:", 1)[1].strip(" *")
    return None
