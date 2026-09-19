# Verified source provenance

This repository was bootstrapped on 2026-09-19T06:03:36.070841+03:00 from four verified source states.

**The first four Git commits are transparent reconstructions. They are not the original historical Git commits, and their Git timestamps were not backdated.**

Historical source identity was established from SHA-256-pinned, safe source archives. The production Flatpak manifest was maintained as a separately pinned external build descriptor and was not a member of the three historical application source archives.

## Verified states

| State | Observed window | Files | Source tree digest | Archive SHA-256 |
| --- | --- | ---: | --- | --- |
| 1 | `20260915004639 → 20260915023403` | 90 | `0ecb202f07ebb2f7deeeff95f698637f6fe88f9ea12a52a47229e76000ab88ac` | `3240d2c310df4eef26d2f88f41815dfd83b4e5ab613f74c88e210befa58ef261` |
| 2 | `20260915023403 → 20260916201219` | 90 | `307b698d7cba7b7664a8e28917dfb395d841614b9d41e322b47444d216e111a7` | `d0c1fbdea610e21fdbef86277afed9fd55b6ae243d8f048fb49798b4643e866c` |
| 3 | `20260916201219 → 20260917132526` | 90 | `e1cf08f4b0047c1b209925cb2dc61c4e73d89a41f976b215b869750188b56391` | `2156de3a068f18dd346e099308b3320e391c4d55324f2667a295a0b57ba712f3` |
| 4 | `CURRENT → CURRENT` | 108 | `876d9ddef42261ec30212ec627b6e2786e679a2969c7fd0297f81182da3c561d` | `current working source` |

## Verified transitions

### State 1 → State 2

- Added: 0; removed: 0; changed: 2.
- `io.github.dasguardcorenotify_del.hatirlatici.Devel.yml`
- `tests/test_packaging_release.py`

### State 2 → State 3

- Added: 0; removed: 0; changed: 3.
- `CHANGELOG.md`
- `tests/test_core_v2.py`
- `ui_v2/core_v2.py`

### State 3 → State 4

- Added: 18; removed: 0; changed: 0.
- `.github/workflows/flatpak.yml`
- `.github/workflows/quality.yml`
- `.github/workflows/release-candidate.yml`
- `.gitignore`
- `FLATHUB_TECHNICAL_READINESS_REPORT.md`
- `docs/RELEASE_NOTES_2.0.0.md`
- `docs/screenshots/01-today-new-reminder.png`
- `docs/screenshots/02-reminder-list.png`
- `docs/screenshots/03-history.png`
- `docs/screenshots/04-settings-local-security.png`
- `docs/screenshots/05-first-run-gmail-guide.png`
- `docs/screenshots/06-support-and-language.png`
- `hatirlatici_app.sh`
- `hatirlatici_quick.sh`
- `io.github.dasguardcorenotify_del.hatirlatici.yml`
- `packaging/flatpak/release_gate.py`
- `packaging/flatpak/verify-built-flatpak.py`
- `pc_notify.sh`

## Integrity and disclosure

- The canonical pre-bootstrap source tree remained unchanged.
- No historical commit dates were fabricated.
- Snapshot observations are provenance evidence, not claims that an original Git repository existed.
- AI assistance is disclosed separately in [AI_ASSISTANCE_DISCLOSURE.md](../AI_ASSISTANCE_DISCLOSURE.md).
