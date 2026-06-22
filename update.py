#!/usr/bin/env python3
"""
update.py - pull the latest voidfox build and refresh your browser profile.

This is deliberately SEPARATE from install.py: installing is a one-off, but
not everyone wants an auto-updater running in the background. update.py:

  1. downloads the latest published files straight from the voidfox repo
     (the upstream Betterfox user.js that the GitHub Action keeps fresh,
     plus your committed overrides),
  2. rebuilds the combined user.js,
  3. backs up and replaces user.js in your Firefox / Zen profile.

So a single run always gives you the newest Betterfox + your overrides without
needing a git checkout.

    python update.py                      # update every detected browser, once
    python update.py --browser zen        # only Zen
    python update.py --dry-run            # show what would happen

Background automation (optional, opt-in):

    python update.py --service install --interval daily
    python update.py --service status
    python update.py --service uninstall

The service runs `update.py` on a schedule using the OS-native scheduler
(launchd on macOS, systemd-user timers/cron on Linux, Task Scheduler on
Windows). It does NOT require this terminal to stay open.

Pure standard library; Windows / macOS / Linux; Python 3.8+.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voidfox_core as core  # noqa: E402

SERVICE_LABEL = "com.voidfox.update"
SERVICE_NAME = "voidfox-update"
INTERVAL_SECONDS = {"hourly": 3600, "daily": 86400, "weekly": 604800}


# --------------------------------------------------------------------------- #
# The actual update
# --------------------------------------------------------------------------- #

def _download_sources(browser: str, dest: Path) -> None:
    """Fetch the files build_user_js() needs from the voidfox repo into *dest*."""
    wanted = [
        f"{core.UPSTREAM_DIR}/{browser}/user.js",
        f"{core.OVERRIDES_DIR}/common.js",
        f"{core.OVERRIDES_DIR}/{browser}.js",
    ]
    for rel in wanted:
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.write_bytes(core.http_get(core.voidfox_raw_url(rel)))
        except Exception as exc:
            # overrides files are optional; upstream user.js is not.
            if rel.endswith("user.js"):
                raise
            core.warn(f"optional file missing upstream, skipping: {rel} ({exc})")


def detect_browsers() -> list[str]:
    return [b for b in core.BROWSERS if any(r.exists() for r in core.profile_roots(b))]


def update_one(browser: str, profile_override: str | None, do_backup: bool, dry_run: bool) -> None:
    core.step(f"{browser}: fetching latest from {core.VOIDFOX_OWNER}/{core.VOIDFOX_REPO}")
    with tempfile.TemporaryDirectory(prefix="voidfox-") as tmp:
        tmp_dir = Path(tmp)
        _download_sources(browser, tmp_dir)
        content = core.build_user_js(tmp_dir, browser)
        ver = core.betterfox_version(tmp_dir)
        core.info(f"Betterfox base version: {ver or 'unknown'}")

        profile = core.default_profile_dir(browser, profile_override)
        core.info(f"Profile: {profile}")

        if dry_run:
            core.info("dry-run: nothing written")
            return
        if do_backup:
            backup = core.backup_user_js(profile)
            core.info(f"Backed up -> {backup.name}" if backup else "No existing user.js to back up")
        target = core.write_user_js(profile, content)
        core.info(f"Updated -> {target}")


def run_update(args) -> int:
    if args.browser in ("firefox", "zen"):
        targets = [args.browser]
    elif args.browser == "both":
        targets = list(core.BROWSERS)
    else:
        targets = detect_browsers()
        if not targets:
            core.warn("No Firefox or Zen profile found.")
            return 1

    if args.profile_dir and len(targets) != 1:
        core.warn("--profile-dir requires a single --browser.")
        return 1

    ok = True
    for browser in targets:
        try:
            update_one(browser, args.profile_dir, not args.no_backup, args.dry_run)
        except Exception as exc:
            ok = False
            core.warn(f"{browser}: {exc}")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Background service management
# --------------------------------------------------------------------------- #

def _periodic_command() -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--browser", "auto"]


def _service_install(interval: str) -> int:
    if sys.platform == "darwin":
        return _launchd_install(interval)
    if sys.platform.startswith("win"):
        return _schtasks_install(interval)
    return _systemd_install(interval)


def _service_uninstall() -> int:
    if sys.platform == "darwin":
        return _launchd_uninstall()
    if sys.platform.startswith("win"):
        return _schtasks_uninstall()
    return _systemd_uninstall()


def _service_status() -> int:
    if sys.platform == "darwin":
        return _run(["launchctl", "list", SERVICE_LABEL])
    if sys.platform.startswith("win"):
        return _run(["schtasks", "/Query", "/TN", SERVICE_NAME])
    return _run(["systemctl", "--user", "status", f"{SERVICE_NAME}.timer"])


def _run(cmd: list[str]) -> int:
    core.info("$ " + " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        core.warn(f"command not found: {cmd[0]}")
        return 1


# ---- macOS launchd -------------------------------------------------------- #

def _launchd_plist_path() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{SERVICE_LABEL}.plist"


def _launchd_install(interval: str) -> int:
    py, script = _periodic_command()[0], _periodic_command()[1]
    log = Path.home() / "Library/Logs" / f"{SERVICE_NAME}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{SERVICE_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py}</string>
        <string>{script}</string>
        <string>--browser</string><string>auto</string>
    </array>
    <key>StartInterval</key><integer>{INTERVAL_SECONDS[interval]}</integer>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>{log}</string>
    <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""
    path = _launchd_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plist, encoding="utf-8")
    subprocess.call(["launchctl", "unload", str(path)])  # ignore if not loaded
    rc = _run(["launchctl", "load", "-w", str(path)])
    core.step(f"launchd agent installed ({interval}). Logs: {log}")
    return rc


def _launchd_uninstall() -> int:
    path = _launchd_plist_path()
    if path.exists():
        subprocess.call(["launchctl", "unload", str(path)])
        path.unlink()
        core.step("launchd agent removed.")
    else:
        core.info("No launchd agent installed.")
    return 0


# ---- Linux systemd-user (with cron fallback) ------------------------------ #

def _systemd_dir() -> Path:
    return Path.home() / ".config/systemd/user"


def _systemd_install(interval: str) -> int:
    py, script = _periodic_command()[0], _periodic_command()[1]
    d = _systemd_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{SERVICE_NAME}.service").write_text(
        f"[Unit]\nDescription=voidfox profile update\n\n"
        f"[Service]\nType=oneshot\nExecStart={py} {script} --browser auto\n",
        encoding="utf-8",
    )
    (d / f"{SERVICE_NAME}.timer").write_text(
        f"[Unit]\nDescription=voidfox update timer\n\n"
        f"[Timer]\nOnCalendar={interval}\nPersistent=true\n\n"
        f"[Install]\nWantedBy=timers.target\n",
        encoding="utf-8",
    )
    if _run(["systemctl", "--user", "daemon-reload"]) != 0:
        core.warn("systemd --user not available. Add this cron line instead "
                  "(crontab -e):")
        spec = {"hourly": "0 * * * *", "daily": "0 9 * * *", "weekly": "0 9 * * 1"}[interval]
        core.info(f"{spec} {py} {script} --browser auto")
        return 0
    rc = _run(["systemctl", "--user", "enable", "--now", f"{SERVICE_NAME}.timer"])
    core.step(f"systemd-user timer installed ({interval}).")
    return rc


def _systemd_uninstall() -> int:
    subprocess.call(["systemctl", "--user", "disable", "--now", f"{SERVICE_NAME}.timer"])
    removed = False
    for fn in (f"{SERVICE_NAME}.service", f"{SERVICE_NAME}.timer"):
        p = _systemd_dir() / fn
        if p.exists():
            p.unlink()
            removed = True
    subprocess.call(["systemctl", "--user", "daemon-reload"])
    core.step("systemd-user timer removed." if removed else "Nothing to remove "
              "(if you used cron, run `crontab -e` and delete the voidfox line).")
    return 0


# ---- Windows Task Scheduler ----------------------------------------------- #

def _schtasks_install(interval: str) -> int:
    py, script = _periodic_command()[0], _periodic_command()[1]
    sc = {"hourly": "HOURLY", "daily": "DAILY", "weekly": "WEEKLY"}[interval]
    tr = f'"{py}" "{script}" --browser auto'
    rc = _run(["schtasks", "/Create", "/TN", SERVICE_NAME, "/TR", tr, "/SC", sc, "/F"])
    core.step(f"Scheduled task '{SERVICE_NAME}' created ({interval})." if rc == 0
              else "Failed to create scheduled task.")
    return rc


def _schtasks_uninstall() -> int:
    return _run(["schtasks", "/Delete", "/TN", SERVICE_NAME, "/F"])


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description="Update voidfox in your browser profile(s).")
    ap.add_argument("--browser", "-b", choices=[*core.BROWSERS, "both", "auto"], default="auto")
    ap.add_argument("--profile-dir", "-p", default=None, help="Target a specific profile directory.")
    ap.add_argument("--no-backup", "-nb", action="store_true")
    ap.add_argument("--dry-run", "-n", action="store_true")
    ap.add_argument(
        "--service",
        choices=["install", "uninstall", "status"],
        help="Manage the background auto-update service instead of updating now.",
    )
    ap.add_argument(
        "--interval",
        choices=list(INTERVAL_SECONDS),
        default="daily",
        help="Schedule for --service install (default: daily).",
    )
    args = ap.parse_args()

    if args.service == "install":
        return _service_install(args.interval)
    if args.service == "uninstall":
        return _service_uninstall()
    if args.service == "status":
        return _service_status()

    return run_update(args)


if __name__ == "__main__":
    raise SystemExit(main())
