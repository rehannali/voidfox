# voidfox

> Firefox, but with everything unnecessary stripped into the void.

[![CI](https://github.com/rehannali/voidfox/actions/workflows/ci.yml/badge.svg)](https://github.com/rehannali/voidfox/actions/workflows/ci.yml)
[![Sync Betterfox](https://github.com/rehannali/voidfox/actions/workflows/sync-betterfox.yml/badge.svg)](https://github.com/rehannali/voidfox/actions/workflows/sync-betterfox.yml)
[![Latest Release](https://img.shields.io/github/v/release/rehannali/voidfox)](https://github.com/rehannali/voidfox/releases)

**voidfox** is a thin, personal layer on top of [**Betterfox**](https://github.com/yokoffing/Betterfox).
It keeps a fresh copy of Betterfox's hardened `user.js` automatically, lets me
keep *my* tweaks in one tidy place, and ships cross-platform Python scripts that
merge the two and drop the result into a **Firefox** or **Zen** profile in one
run — on Windows, macOS, or Linux.

> voidfox is **not** affiliated with or endorsed by Betterfox. It simply uses
> Betterfox as its source and reshapes it to my taste. All the hardening work is
> theirs — see [Credits](#credits).

---

## How it works

```
        ┌──────────────────────────┐
        │  Betterfox (upstream)     │   yokoffing/Betterfox
        └────────────┬─────────────┘
                     │  GitHub Action (sync.py), daily + on demand
                     │  commits ONLY when a file actually changed
                     ▼
        ┌──────────────────────────┐
        │  this repo                │
        │  ├─ upstream/   (mirror)  │  ← auto-updated, never hand-edit
        │  └─ overrides/  (mine)    │  ← my personal prefs live here
        └────────────┬─────────────┘
                     │  install.py / update.py (you run these)
                     │  merge upstream user.js + overrides  →  user.js
                     ▼
        ┌──────────────────────────┐
        │  Firefox / Zen profile    │   …/<profile>/user.js
        └──────────────────────────┘
```

Two clean halves:

- **Automation side (hands-off):** a GitHub Action runs `sync.py` on a schedule,
  pulls the latest raw Betterfox files into `upstream/`, and commits *only if
  something changed*. The sync history is a clean "upstream bumped" trail with no
  noise on quiet days.
- **Setup side (you run these):** `install.py` and `update.py` are voidfox's own
  tooling — **not Betterfox's**. They merge the synced `upstream/user.js` with
  `overrides/` and write the combined `user.js` into the right profile folder.

Because Firefox applies the **last** matching `user_pref()`, voidfox appends
overrides *after* the Betterfox content — so personal prefs always win, with no
fragile find-and-replace.

---

## Repository structure

```
voidfox/
├── upstream/                     # auto-synced mirror of Betterfox (do not edit)
│   ├── firefox/
│   │   ├── user.js               # combined config that actually gets installed
│   │   ├── Fastfox.js            # ─┐ the four Betterfox modules, mirrored for
│   │   ├── Securefox.js          #  │ reference — lift prefs into overrides/
│   │   ├── Peskyfox.js           #  │ to customise them
│   │   └── Smoothfox.js          # ─┘
│   ├── zen/
│   │   └── user.js               # Betterfox's dedicated Zen config
│   └── sync-meta.json            # source, Betterfox version, last sync time
├── overrides/                    # YOUR changes — the only files you hand-edit
│   ├── common.js                 # applied to both Firefox and Zen
│   ├── firefox.js                # Firefox-only
│   └── zen.js                    # Zen-only
├── sync.py                       # automation: fetch Betterfox → upstream/
├── install.py                    # setup: build + install into a profile
├── update.py                     # setup: pull latest + reinstall (+ background service)
├── voidfox_core.py               # shared logic (profiles, download, merge, strip)
├── .github/
│   ├── workflows/
│   │   ├── sync-betterfox.yml    # daily upstream sync Action
│   │   ├── ci.yml                # CI: install + verify on every push
│   │   ├── release.yml           # create GitHub Release on manual tag push
│   │   └── auto-release.yml      # monthly CalVer release (first of month)
│   └── ISSUE_TEMPLATE/           # bug report template (adapted from Betterfox)
└── LICENSE                       # MIT, with Betterfox attribution
```

### The Betterfox source files

Betterfox curates four module guides; its combined `user.js` is assembled from
them. voidfox mirrors all four for reference but installs the combined `user.js`:

| File | What it covers |
|------|----------------|
| **Fastfox** | Performance — rendering pipeline, caching, network pre-connects. |
| **Securefox** | Privacy & security — tracking protection, telemetry off, HTTPS-only, OCSP, etc. |
| **Peskyfox** | Cleaner UI — kills nags, sponsored tiles, built-in AI chat, welcome screens. |
| **Smoothfox** | *Optional* smooth-scrolling presets. Not included in `user.js` by default. |
| **user.js** | The combined, ready-to-use config curated from the modules above. |

**Personal adjustments always stay in `overrides/`** — never in `upstream/`.
That keeps the upstream mirror byte-for-byte identical to Betterfox so the
auto-sync stays clean. Smooth scrolling isn't in Betterfox's default `user.js`,
so voidfox enables a Smoothfox preset via `overrides/common.js`.

---

## Quick start (install)

**Requirements:** Python 3.8+ (standard library only — nothing to `pip install`)
and Firefox and/or Zen launched at least once so a profile exists.

```bash
git clone git@github.com:rehannali/voidfox.git
cd voidfox

python install.py            # auto-detects Firefox and Zen, installs to each
```

Then **fully restart** the browser for the new `user.js` to take effect.

### All install flags

```bash
python install.py --browser firefox          # only Firefox
python install.py --browser zen              # only Zen
python install.py --browser both             # Firefox and Zen explicitly

python install.py --dry-run                  # show what would happen, write nothing
python install.py --no-backup                # skip backing up the existing user.js
python install.py -b firefox -p "/path/to/profile"   # target an exact profile dir

python install.py --diagnose                 # show detected app + profile paths, exit
python install.py --preview                  # print merged user.js to stdout, exit
python install.py --preview --browser zen    # preview Zen's version
python install.py --strip-comments           # install without JS comments (prefs only)
```

By default the existing `user.js` is backed up to
`user.js.voidfox-backup-<timestamp>` before being replaced.

### Profile detection

voidfox reads `profiles.ini` in each browser's standard data directory.
The profile location **does not depend on where the app is installed** — on
macOS the profile always lives under `~/Library/Application Support` whether
the `.app` bundle is in `/Applications` or `~/Applications`.

What does matter is the packaging format. voidfox checks every candidate in
priority order and picks the first root that contains `profiles.ini`:

| | Firefox | Zen |
|---|---|---|
| **Windows** | `%APPDATA%\Mozilla\Firefox` | `%APPDATA%\zen`, `%LOCALAPPDATA%\zen` |
| **macOS** | `~/Library/Application Support/Firefox` | `~/Library/Application Support/zen` |
| **Linux — native** | `~/.mozilla/firefox` | `~/.zen` |
| **Linux — Flatpak** | `~/.var/app/org.mozilla.firefox/.mozilla/firefox` | `~/.var/app/app.zen_browser.zen/.zen` · `~/.var/app/app.zen_browser.zen/zen` ¹ |
| **Linux — Snap** | `~/snap/firefox/common/.mozilla/firefox` | — |

> ¹ Zen Flatpak uses either the hidden (`.zen`) or the non-hidden (`zen`) path
> depending on the version. voidfox checks both and picks the one that has
> `profiles.ini`.

Not sure what voidfox will detect on your machine? Run:

```bash
python install.py --diagnose
```

It prints every candidate path, marks which ones exist, and shows the final
profile it would use — without writing anything.

---

## Inspecting the output

Before installing, you can see the exact `user.js` that will be generated:

```bash
# Full merged output — upstream Betterfox + your overrides
python install.py --browser firefox --preview

# Preview the Zen version
python install.py --browser zen --preview

# Pipe into other tools
python install.py --browser firefox --preview | grep "telemetry"
python install.py --browser firefox --preview | wc -l
```

### Comments in the final file

JS comments (`//` and `/* */`) have **zero effect** on Firefox — the engine
parses them away at startup before any pref is applied. Keeping them is useful:
you can open your profile's `user.js` and read why each setting is there.

If you prefer a compact, comment-free file that is easier to diff and grep:

```bash
# Preview the stripped version first
python install.py --browser firefox --preview --strip-comments

# Then install it
python install.py --browser firefox --strip-comments
```

Stripping reduces the file from ~300 lines to ~150 (prefs only). All
`user_pref()` values are unchanged; only comment lines are removed. URLs inside
pref strings (e.g. `"https://..."`) are preserved safely.

---

## Updating

`update.py` is **separate from `install.py` on purpose.** If you installed once
and prefer to manage it by hand, you never need to touch the updater.

`update.py` fetches the latest published files directly from this repo (the
freshest Betterfox `user.js` the Action committed, plus the current overrides),
rebuilds the merged `user.js`, and replaces it in the profile:

```bash
python update.py                         # update every detected browser, once
python update.py --browser zen           # only Zen
python update.py --dry-run               # preview only, write nothing
python update.py --strip-comments        # update and remove comments
```

### Background auto-update (optional)

Opt in to a native scheduled job that keeps your profile current with no
terminal open:

```bash
python update.py --service install --interval daily    # hourly | daily | weekly
python update.py --service status
python update.py --service uninstall
```

Uses the OS-native scheduler — **launchd** on macOS, a **systemd-user timer**
(with a cron fallback) on Linux, **Task Scheduler** on Windows.

---

## Customising — the overrides

All personal changes go in `overrides/`. These are the **only files you should
ever hand-edit** in this repo.

- **`common.js`** — applied to both Firefox and Zen. Ships with:
  - Session restore (reopens previous tabs on startup)
  - Natural Smooth Scrolling v3 (Smoothfox preset, great on 120 Hz+)
  - Inline PDF viewer
  - Commented-out menu to relax Betterfox's stricter defaults (search
    suggestions, form history, disk cache, etc.)
- **`firefox.js`** — Firefox-only prefs (vertical tabs, bookmarks bar, etc.)
- **`zen.js`** — Zen-only prefs. Note: Zen ships its own scrolling defaults;
  see the comments in this file if you prefer Zen's feel over Smoothfox.

Add a line like `user_pref("some.pref", value);`, then re-run `install.py` or
`update.py`. Because overrides are appended last, they always win over Betterfox.

Useful references for finding more prefs to override:
- [Common Overrides](https://github.com/yokoffing/Betterfox/wiki/Common-Overrides)
- [Optional Hardening](https://github.com/yokoffing/Betterfox/wiki/Optional-Hardening)
- `upstream/firefox/Smoothfox.js` — scrolling presets to copy into `common.js`

---

## CI

Every push and pull request runs the full test suite defined in
`.github/workflows/ci.yml`. The **CI** badge at the top of this page reflects
the latest result.

### What is tested

| Job | Runs on | What it does |
|-----|---------|--------------|
| **Syntax check** | Ubuntu | Compiles all `.py` scripts; smoke-tests imports |
| **sync.py** | Ubuntu | Downloads Betterfox, verifies all files, checks idempotency |
| **Firefox / ubuntu** | Ubuntu | Installs Firefox (apt), creates profile, installs voidfox, verifies `user.js` |
| **Firefox / macos** | macOS | Installs Firefox (`brew --cask`), same verification |
| **Firefox / windows** | Windows | Installs Firefox (choco), same verification |
| **Zen / ubuntu** | Ubuntu | Installs Zen (tarball from GitHub releases), verifies |
| **Zen / macos** | macOS | Installs Zen (`brew --cask zen`), verifies |
| **Zen / windows** | Windows | Installs Zen (`choco install zen-browser`), verifies |
| **Firefox / Linux / Snap** | Ubuntu | Installs Firefox via `snap`, verifies Snap profile path is detected |
| **Firefox / Linux / Flatpak** | Ubuntu | Creates Flatpak profile path, verifies detection over native path |
| **Zen / Linux / Flatpak** | Ubuntu | Tests both `.zen` and `zen` Flatpak path variants |
| **All checks passed** | Ubuntu | Gate job — reference this in branch protection rules |

Each Firefox/Zen job also runs `--preview` before installing, so the full
merged `user.js` is visible in the Actions log for every push.

### Branch protection

To require CI to pass before merging, add only the **"All checks passed"** job
to your branch protection rule — it depends on every job above, so you don't
have to list each matrix entry individually.

---

## Sync automation (maintainer notes)

`.github/workflows/sync-betterfox.yml` runs daily at 06:00 UTC and on manual
dispatch. The **Sync Betterfox** badge at the top shows its latest status.

1. `python sync.py` fetches the raw Betterfox files for Firefox and Zen into
   `upstream/` (Waterfox and personal variants are intentionally skipped).
2. `git status` is checked. If anything changed, the Action commits
   `chore(upstream): sync Betterfox (version N)` and pushes. Quiet days
   produce no commit — the history stays clean.

No secrets needed. The workflow uses the built-in `GITHUB_TOKEN` (requires
**Settings → Actions → General → Workflow permissions → Read and write**).

Run the sync locally any time:

```bash
python sync.py            # write the latest Betterfox files into upstream/
python sync.py --check    # exit 1 if upstream differs, no writes ("anything changed?")
```

---

## Releases

voidfox uses **CalVer** tags in the form `vYYYY.M.PATCH` (e.g., `v2026.6.0`). Each
release is a versioned snapshot of `upstream/` (the synced Betterfox files) and
`overrides/`, so you can pin to a known-good state and read a clean changelog of what
changed between Betterfox syncs and your own overrides.

### Automatic monthly releases

`.github/workflows/auto-release.yml` runs on the first of every month. If there are any
commits since the last tag it picks the next CalVer tag, pushes it, and creates a GitHub
Release with categorised release notes (voidfox changes vs. Betterfox syncs). Quiet
months produce no release.

### Manual release

To cut a release at any time:

```bash
git tag v2026.6.1     # patch increments if a tag already exists for this month
git push origin v2026.6.1
```

The **Release** workflow (`release.yml`) fires on every `v*` tag push. It reads the
Betterfox version from `upstream/sync-meta.json`, pulls the commit log since the
previous tag, separates Betterfox sync commits from voidfox changes, and publishes a
GitHub Release with those notes as the body. No extra tokens or secrets are needed —
the built-in `GITHUB_TOKEN` is sufficient (requires the same **Read and write** workflow
permission as the sync Action).

---

## Credits

voidfox is a wrapper. The hard work belongs to others:

- **[Betterfox](https://github.com/yokoffing/Betterfox)** by **yokoffing** —
  every hardening pref and the Firefox/Zen `user.js` come from here. voidfox
  fetches, redistributes, and layers on top of it. **MIT licensed.**
- **arkenfox** — foundational `user.js` research that Betterfox builds on.
- The **Mozilla Firefox** and **Zen Browser** teams.
- Smooth-scrolling presets: **black7375** (*Firefox-UI-Fix*) and **AveYo**
  (Natural Smooth Scrolling v3), as packaged in Betterfox's Smoothfox.
- Betterfox's `install.py` by **Denperidge** — inspiration for the
  cross-platform profile-detection approach.

---

## License

[MIT](LICENSE). The files under `upstream/` are copies of Betterfox and remain
under their original MIT copyright (© yokoffing).
