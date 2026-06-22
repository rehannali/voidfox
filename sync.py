#!/usr/bin/env python3
"""
sync.py - mirror the latest Betterfox files into this repository.

This is the MAINTAINER / automation side of voidfox. It is what the GitHub
Action runs on a schedule: it downloads the raw Betterfox files we care about
(Firefox + Zen only) and writes them into ``upstream/``. It does NOT commit —
the workflow decides whether anything changed and commits if so.

Usage:
    python sync.py              # download into ./upstream
    python sync.py --check      # exit 1 if a download differs from what's on disk
                                # (handy for "did anything change?" in CI)

Pure standard library; safe to run locally too.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import voidfox_core as core


def sync(check_only: bool = False) -> bool:
    """Download upstream files. Returns True if anything changed on disk."""
    root = core.repo_root()
    changed = False

    core.step(f"Syncing from {core.BETTERFOX_OWNER}/{core.BETTERFOX_REPO}@{core.BETTERFOX_BRANCH}")
    for dest_rel, src_rel in core.SYNC_MAP.items():
        url = core.betterfox_raw_url(src_rel)
        dest = root / dest_rel
        new = core.http_get(url)
        old = dest.read_bytes() if dest.exists() else None

        if old == new:
            core.info(f"unchanged  {dest_rel}")
            continue

        changed = True
        if check_only:
            core.info(f"WOULD UPDATE  {dest_rel}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(new)
            core.info(f"updated    {dest_rel}")

    if not check_only:
        _write_meta(root)

    core.step("Done. Changes detected." if changed else "Done. Already up to date.")
    return changed


def _write_meta(root) -> None:
    meta = {
        "source": f"{core.BETTERFOX_OWNER}/{core.BETTERFOX_REPO}",
        "branch": core.BETTERFOX_BRANCH,
        "betterfox_version": core.betterfox_version(root),
        "synced_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": sorted(core.SYNC_MAP.keys()),
    }
    path = root / core.UPSTREAM_DIR / "sync-meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror Betterfox into ./upstream")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Don't write; exit 1 if upstream differs from disk.",
    )
    args = ap.parse_args()

    changed = sync(check_only=args.check)
    if args.check:
        return 1 if changed else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
