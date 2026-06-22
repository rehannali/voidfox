#!/usr/bin/env python3
"""
install.py - install voidfox into your Firefox and/or Zen profile.

This is the END-USER side. Run it from a clone of the voidfox repository:

    python install.py                 # auto-detect installed browsers, install to each
    python install.py --browser zen   # only Zen
    python install.py --browser firefox --profile-dir /path/to/profile
    python install.py --dry-run       # show what would happen, write nothing
    python install.py --no-backup     # skip backing up the existing user.js

It combines the synced upstream Betterfox user.js (in ./upstream) with your
overrides (in ./overrides) and writes the result as user.js in the profile.
Your existing user.js is backed up first unless --no-backup is given.

For automatic, ongoing updates use update.py instead (separate on purpose, so
people who prefer to install once and manage it by hand are not forced into a
background service).

Pure standard library: works on Windows, macOS and Linux with Python 3.8+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the script runnable from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import voidfox_core as core  # noqa: E402


def detect_browsers() -> list[str]:
    found = []
    for browser in core.BROWSERS:
        if any(root.exists() for root in core.profile_roots(browser)):
            found.append(browser)
    return found


def install_one(
    browser: str,
    source_dir: Path,
    profile_dir_override: str | None,
    do_backup: bool,
    dry_run: bool,
) -> bool:
    core.step(f"{browser}: building user.js")
    content = core.build_user_js(source_dir, browser)
    ver = core.betterfox_version(source_dir)
    core.info(f"Betterfox base version: {ver or 'unknown'}  ({len(content.splitlines())} lines total)")

    profile = core.default_profile_dir(browser, profile_dir_override)
    core.info(f"Profile: {profile}")

    if dry_run:
        core.info("dry-run: nothing written")
        return True

    if do_backup:
        backup = core.backup_user_js(profile)
        core.info(f"Backed up existing user.js -> {backup.name}" if backup else "No existing user.js to back up")

    target = core.write_user_js(profile, content)
    core.info(f"Installed -> {target}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Install voidfox into a browser profile.")
    ap.add_argument(
        "--browser", "-b",
        choices=[*core.BROWSERS, "both", "auto"],
        default="auto",
        help="Which browser(s) to target. 'auto' (default) installs to every "
             "browser whose profile is found.",
    )
    ap.add_argument(
        "--profile-dir", "-p",
        default=None,
        help="Install into this exact profile directory (implies a single browser).",
    )
    ap.add_argument("--no-backup", "-nb", action="store_true", help="Do not back up the existing user.js.")
    ap.add_argument("--dry-run", "-n", action="store_true", help="Show what would happen; write nothing.")
    args = ap.parse_args()

    source_dir = core.repo_root()

    if args.browser in ("firefox", "zen"):
        targets = [args.browser]
    elif args.browser == "both":
        targets = list(core.BROWSERS)
    else:  # auto
        targets = detect_browsers()
        if not targets:
            core.warn("No Firefox or Zen profile found. Launch the browser once, "
                      "or pass --profile-dir.")
            return 1
        core.step(f"Detected: {', '.join(targets)}")

    if args.profile_dir and len(targets) != 1:
        ap.error("--profile-dir requires a single --browser (firefox or zen).")

    ok = True
    for browser in targets:
        try:
            install_one(browser, source_dir, args.profile_dir, not args.no_backup, args.dry_run)
        except Exception as exc:  # keep going across browsers
            ok = False
            core.warn(f"{browser}: {exc}")

    if not args.dry_run and ok:
        core.step("All set. Fully restart the browser for changes to take effect.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
