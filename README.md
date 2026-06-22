# voidfox

> Firefox, but with everything unnecessary stripped into the void.

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

- **Automation side (mine, hands-off):** a GitHub Action runs `sync.py` on a
  schedule, pulls the latest raw Betterfox files into `upstream/`, and commits
  *only if something changed*. I never have to babysit upstream.
- **Setup side (install/update):** `install.py` and `update.py` are the voidfox
  installer/updater — **they are part of voidfox, not Betterfox.** They merge
  the synced `upstream/user.js` with my `overrides/` and write the combined
  `user.js` into the right profile folder.

Because Firefox applies the **last** matching `user_pref()`, voidfox appends the
overrides *after* the Betterfox content — so my prefs always win, with no
fragile find-and-replace.

---

## Repository structure

```
voidfox/
├── upstream/                 # auto-synced mirror of Betterfox (do not edit)
│   ├── firefox/
│   │   ├── user.js           # the combined config that actually gets installed
│   │   ├── Fastfox.js        # ─┐ the four Betterfox modules, mirrored for
│   │   ├── Securefox.js      #  │ reference so I can lift prefs into overrides
│   │   ├── Peskyfox.js       #  │
│   │   └── Smoothfox.js      # ─┘
│   ├── zen/
│   │   └── user.js           # Betterfox's dedicated Zen config
│   └── sync-meta.json        # records source, Betterfox version, sync time
├── overrides/                # MY changes — the only files I hand-edit
│   ├── common.js             # applied to both browsers
│   ├── firefox.js            # Firefox-only
│   └── zen.js                # Zen-only
├── sync.py                   # automation: mirror Betterfox → upstream/
├── install.py                # setup: build + install into a profile
├── update.py                 # setup: pull latest + reinstall (+ background service)
├── voidfox_core.py           # shared logic (profiles, download, merge)
├── .github/
│   ├── workflows/sync-betterfox.yml   # the daily sync Action
│   └── ISSUE_TEMPLATE/                # bug report adapted from Betterfox
└── LICENSE                   # MIT, with Betterfox attribution
```

### The Betterfox source files

Betterfox curates four "module" guides; its combined `user.js` is built from
them. voidfox mirrors all of them but installs the combined `user.js`:

| File | What it covers |
|------|----------------|
| **Fastfox** | Performance tuning (rendering, caching, network). |
| **Securefox** | Privacy & security — tracking protection, telemetry off, HTTPS-only, etc. |
| **Peskyfox** | Unclutters the UI — kills nags, sponsored tiles, built-in AI prompts, etc. |
| **Smoothfox** | *Optional* smooth-scrolling presets (not included in `user.js` by default). |
| **user.js** | The combined, ready-to-use config curated from the modules above. |

**My adjustments always stay in `overrides/`** — never in `upstream/`. That keeps
the upstream mirror byte-for-byte identical to Betterfox so the auto-sync stays
clean. Smooth scrolling isn't in Betterfox's `user.js`, so voidfox enables a
Smoothfox preset *via* `overrides/common.js`.

---

## Quick start (install)

Requirements: **Python 3.8+** (standard library only — nothing to `pip install`)
and Firefox and/or Zen launched at least once.

```bash
git clone git@github.com:rehannali/voidfox.git
cd voidfox

python install.py            # auto-detects Firefox/Zen, installs to each
```

Then **fully restart** the browser.

Useful flags:

```bash
python install.py --browser zen          # only Zen
python install.py --browser firefox       # only Firefox
python install.py --dry-run               # show what would happen, write nothing
python install.py --no-backup             # don't back up the existing user.js
python install.py -b firefox -p "/path/to/profile"   # exact profile dir
```

By default the existing `user.js` is copied to
`user.js.voidfox-backup-<timestamp>` before being replaced.

voidfox finds the default profile by reading `profiles.ini` in the standard
location for your OS:

| | Firefox | Zen |
|---|---|---|
| **Windows** | `%APPDATA%\Mozilla\Firefox` | `%APPDATA%\zen` |
| **macOS** | `~/Library/Application Support/Firefox` | `~/Library/Application Support/zen` |
| **Linux** | `~/.mozilla/firefox` (+ Flatpak) | `~/.zen` (+ Flatpak) |

---

## Updating

`update.py` is **separate from `install.py` on purpose** — if you'd rather
install once and manage it by hand, you never have to touch the updater. It
fetches the latest published files straight from this repo (the freshest
Betterfox `user.js` the Action committed, plus the current overrides), rebuilds,
and replaces `user.js`:

```bash
python update.py                 # update every detected browser, once
python update.py --browser zen   # only Zen
python update.py --dry-run       # preview only
```

### Optional: background auto-update

Want it to keep itself current with no terminal open? Opt in to a native
scheduled job (this is voidfox's extra automation on top of Betterfox):

```bash
python update.py --service install --interval daily   # hourly | daily | weekly
python update.py --service status
python update.py --service uninstall
```

It uses the OS-native scheduler — **launchd** on macOS, a **systemd-user timer**
(with a cron fallback) on Linux, and **Task Scheduler** on Windows. Each tick
just runs `update.py` for every detected browser.

---

## Customising — the overrides

All personal changes go in `overrides/`:

- `common.js` — both browsers. Ships with sensible enhancements already enabled
  (session restore, "Natural Smooth Scrolling", inline PDFs) plus a menu of
  commented-out toggles for relaxing Betterfox's stricter defaults (search
  suggestions, form history, disk cache, …).
- `firefox.js` — Firefox-only prefs.
- `zen.js` — Zen-only prefs (note: Zen ships its own scrolling defaults).

Add a line like `user_pref("some.pref", value);`, then re-run `install.py` (or
`update.py`). Because overrides are appended last, they override Betterfox.
Browse Betterfox's [Common Overrides](https://github.com/yokoffing/Betterfox/wiki/Common-Overrides)
and [Optional Hardening](https://github.com/yokoffing/Betterfox/wiki/Optional-Hardening)
wikis for more.

---

## The sync automation (maintainer notes)

`.github/workflows/sync-betterfox.yml` runs daily (and on manual dispatch):

1. `python sync.py` downloads the raw Betterfox files for Firefox + Zen into
   `upstream/` (Waterfox and personal variants are intentionally skipped).
2. If `git status` shows a change, it commits
   `chore(upstream): sync Betterfox (version N)` and pushes. Quiet days → no
   commit, so the history is a clean "upstream bumped" trail.

Run it locally any time:

```bash
python sync.py            # write the latest into upstream/
python sync.py --check    # exit 1 if upstream differs (no writes) — "did anything change?"
```

---

## Credits

voidfox is a wrapper. The hard work belongs to others:

- **[Betterfox](https://github.com/yokoffing/Betterfox)** by **yokoffing** — the
  source of every hardening pref and the Firefox/Zen `user.js`. voidfox fetches,
  redistributes, and layers on top of it. **MIT licensed.**
- **arkenfox** — foundational `user.js` research that Betterfox builds on.
- The **Mozilla Firefox** and **Zen Browser** teams.
- Smooth-scrolling presets: black7375's *Firefox-UI-Fix* and **AveYo** (Natural
  Smooth Scrolling), as bundled in Betterfox's Smoothfox.
- Betterfox's `install.py` (by Denperidge) — the inspiration for the
  profile-detection approach reimplemented here.

## License

[MIT](LICENSE). The files under `upstream/` are copies of Betterfox and remain
under their original MIT copyright (© yokoffing).
