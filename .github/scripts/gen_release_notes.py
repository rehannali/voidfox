#!/usr/bin/env python3
"""Generate markdown release notes for a voidfox tag.

Usage:
    python gen_release_notes.py <tag>

Prints to stdout; redirect to a file for gh release create --notes-file.
"""

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.strip()


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else "HEAD"

    # Find the previous tag so we can scope the commit range.
    all_tags = [t for t in run(["git", "tag", "--sort=-version:refname"]).splitlines() if t.strip()]
    prev_tag = None
    if tag in all_tags:
        idx = all_tags.index(tag)
        prev_tag = all_tags[idx + 1] if idx + 1 < len(all_tags) else None

    range_spec = f"{prev_tag}..{tag}" if prev_tag else tag
    raw = run(["git", "log", range_spec, "--format=%s"])
    commits = [c for c in raw.splitlines() if c.strip()]

    syncs = [c for c in commits if c.lower().startswith("chore(upstream):")]
    changes = [c for c in commits if not c.lower().startswith("chore(upstream):")]

    # Betterfox version from the synced metadata.
    meta_path = Path("upstream/sync-meta.json")
    bf_version = "unknown"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        bf_version = meta.get("betterfox_version") or "unknown"

    lines: list[str] = []
    lines.append(
        f"**Betterfox base:** version {bf_version}"
        " — [yokoffing/Betterfox](https://github.com/yokoffing/Betterfox)"
    )
    lines.append("")

    if changes:
        lines.append("## Changes")
        for c in changes:
            lines.append(f"- {c}")
        lines.append("")

    if syncs:
        lines.append("## Upstream Betterfox syncs")
        for c in syncs:
            lines.append(f"- {c}")
        lines.append("")

    if not changes and not syncs:
        lines.append("## Changes")
        lines.append("- Initial release")
        lines.append("")

    lines.append("## Install / Update")
    lines.append("")
    lines.append("**Fresh install:**")
    lines.append("```bash")
    lines.append("git clone git@github.com:rehannali/voidfox.git && cd voidfox")
    lines.append("python install.py")
    lines.append("```")
    lines.append("")
    lines.append("**Update existing install:**")
    lines.append("```bash")
    lines.append("cd voidfox && git pull && python install.py")
    lines.append("# or, using the auto-updater:")
    lines.append("python update.py")
    lines.append("```")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
