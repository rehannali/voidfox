#!/usr/bin/env python3
"""
install.py - install voidfox into your Firefox and/or Zen profile.

This is the END-USER side. Run it from a clone of the voidfox repository:

    python install.py                    # auto-detect installed browsers, install to each
    python install.py --browser zen      # only Zen
    python install.py -b firefox -p /path/to/profile
    python install.py --dry-run          # show what would happen, write nothing
    python install.py --no-backup        # skip backing up the existing user.js

Preview the merged output before installing:

    python install.py --browser firefox --preview
    python install.py --browser firefox --preview --strip-comments
    python install.py --browser firefox --preview | grep "some_pref"

Install a comment-free version (prefs only, smaller file):

    python install.py --browser firefox --strip-comments

Comments in user.js have zero effect on Firefox (it parses JS and discards them
at startup). Keeping them is useful for understanding why each pref is set.
Stripping them gives a compact file that's easier to diff and grep.

Pure standard library: works on Windows, macOS and Linux with Python 3.8+.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voidfox_core as core  # noqa: E402


def detect_browsers() -> list[str]:
    return [b for b in core.BROWSERS if any(r.exists() for r in core.profile_roots(b))]


def install_one(
    browser: str,
    source_dir: Path,
    profile_dir_override: str | None,
    do_backup: bool,
    dry_run: bool,
    strip_comments: bool,
    preview: bool,
) -> bool:
    content = core.build_user_js(source_dir, browser)
    if strip_comments:
        content = core.strip_comments(content)

    ver = core.betterfox_version(source_dir)
    lines = len(content.splitlines())

    if preview:
        # Print to stdout and stop — do not touch the profile.
        sys.stdout.write(content)
        sys.stdout.flush()
        return True

    core.step(f"{browser}: building user.js")
    core.info(
        f"Betterfox base version: {ver or 'unknown'}  "
        f"({lines} lines{'  [comments stripped]' if strip_comments else ''})"
    )

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
    ap = argparse.ArgumentParser(
        description="Install voidfox into a browser profile.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
    ap.add_argument("--no-backup", "-nb", action="store_true",
                    help="Do not back up the existing user.js.")
    ap.add_argument("--dry-run", "-n", action="store_true",
                    help="Show what would happen; write nothing.")
    ap.add_argument("--diagnose", action="store_true",
                    help="Print detected app + profile locations for each browser and exit.")
    ap.add_argument("--preview", action="store_true",
                    help="Print the merged user.js to stdout and exit without installing. "
                         "Combine with --strip-comments to preview the stripped version. "
                         "Combine with --browser to choose which browser's config to show.")
    ap.add_argument("--strip-comments", action="store_true",
                    help="Remove all JS comments from the generated user.js before writing. "
                         "Comments have zero effect on Firefox, but stripping gives a compact "
                         "prefs-only file that is easier to diff and grep. "
                         "Default: keep comments.")
    args = ap.parse_args()

    if args.diagnose:
        core.diagnose()
        return 0

    source_dir = core.repo_root()

    # --preview with --browser auto: default to firefox so the output is unambiguous.
    if args.preview and args.browser == "auto":
        args.browser = "firefox"

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

    if args.preview and len(targets) > 1:
        ap.error("--preview requires a single --browser (firefox or zen).")

    ok = True
    for browser in targets:
        try:
            install_one(
                browser, source_dir, args.profile_dir,
                not args.no_backup, args.dry_run,
                args.strip_comments, args.preview,
            )
        except Exception as exc:
            ok = False
            core.warn(f"{browser}: {exc}")

    if not args.preview and not args.dry_run and ok:
        core.step("All set. Fully restart the browser for changes to take effect.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
