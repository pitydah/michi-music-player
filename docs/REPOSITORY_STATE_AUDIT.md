# Repository State Audit — Michi Music Player

**Date:** 2026-07-02  
**Author:** AI audit

## Branch Analysis

| Field | Value |
|---|---|
| Current branch | `main` |
| HEAD commit | `04c9e4b` — "chore: estabilización post-QML" |
| Remote tracking | `origin/main` — same commit |
| Working tree | Clean (no unstaged changes) |
| Tag `v0.2.0-beta` | Exists, **behind** HEAD by 3 commits |
| Tag `v0.1.0-alpha` | Exists, behind |

## Available Branches (relevant)

| Branch | Commits ahead of main | Description |
|---|---|---|
| `qml-migration-foundation` | 34 ahead | QML refinements: Home, Sidebar, HomeAudio, Connections, ActionButton |
| `qml-migration-foundation-clean` | ~34 ahead | Same content, cleaned history |
| `qml-nowplaying-experiment` | Unknown | NowPlaying QML experiment |
| `playlists-backend` | Unknown | Playlists backend refactor |

## QML Infrastructure Present in `main`

| Component | Present |
|---|---|
| `ui_qml/` directory | ✅ Yes |
| `ui_qml_bridge/` directory | ✅ Yes |
| `main.py --qml` launcher | ✅ Yes |
| QML bridges (16) | ✅ Yes |
| QML tests (`tests/qml/`) | ✅ Yes — 165 passed |
| QML sidebar | ✅ Basic version |
| QML Library, Playlists, Devices, Connections, Audio Lab | ✅ Yes |
| QML PlayerService connection | ✅ Yes (`QmlServiceFactory`) |

## QML Refinements NOT in `main` (in `qml-migration-foundation`)

| Feature | Status in qml-migration-foundation |
|---|---|
| Home QML page | 100% — Hero, ContinueCard, LibraryStatusCard |
| Sidebar premium | 100% — glyphs, microinteractions, 10 items |
| HeaderBar premium | 100% — MichiGlass 2.0, 15+ tokens |
| ActionButton | 100% — microinteractions, loading, focus |
| HomeAudio QML | 100% — ModeSelector, zones, ReceiverCard |
| Connections QML | 100% — grid 2x2, premium |
| PageStack | Fixed relative routes |
| Navigation history | Full back/forward with album:/artist:/genre: |
| Michi Link playlist API | Complete REST |
| Playlists premium suite | Store, import, export, audit, relinker |
| Emoji prohibition | Tested |
| QML tests | 53 passed (vs 165 in main — different tests) |

## Version Status

| File | Version declared | Correct? |
|---|---|---|
| `pyproject.toml` | `0.2.0-alpha.1` | ✅ |
| `AGENTS.md` | No explicit version | ✅ (describes pre-beta) |
| `ESTADO.md` | `0.2.0-alpha.1` | ✅ |
| `u_qml_bridge/app_bridge.py` | `importlib.metadata` → `0.2.0-alpha.1` fallback | ✅ |
| `ui_qml_bridge/qml_main.py` | `importlib.metadata` → `0.2.0-alpha.1` fallback | ✅ |
| `docs/roadmap.md` | `0.2.0-alpha.1` | ✅ |
| `docs/FEATURE_STATUS.md` | `0.2.0-alpha.1` | ✅ |
| Tag `v0.2.0-beta` | `0.2.0-beta` | ⚠️ Behind HEAD, not applied to current commits |

## Demo Data Status

| Bridge | Demo data gated behind `MICHI_QML_DEMO=1`? |
|---|---|
| `connections_bridge.py` | ✅ Yes, with `is_demo: True` |
| `playlists_bridge.py` | ✅ Yes, with `is_demo: True` |
| `radio_bridge.py` | ✅ Removed entirely (no fallback) |

## Hardcoded DB Paths

| File | Path | Correct? |
|---|---|---|
| `ui_qml_bridge/qml_main.py` | `core.paths.database_path()` | ✅ |

## AGENTS.md

| Statement | line | Correct? |
|---|---|---|
| "QtWidgets stable/fallback + QML experimental skin" | 13 | ✅ |
| QML section #13 says "experimental/premium — NOT the default" | 546 | ✅ |

## Architecture Compliance

| Rule | Status |
|---|---|
| QtWidgets not broken | ✅ `python main.py` works |
| QML not default | ✅ `--qml` flag required |
| QML bridges use real services | ✅ LibraryDB, PlayerService, RadioManager, SyncManager |
| No business logic in QML | ✅ All logic in Python bridges |
| No demo data as real | ✅ Gated behind `MICHI_QML_DEMO=1` |
| DB path via core.paths | ✅ |
| Version unified | ✅ |

## Conclusions

1. **`main` is the correct branch** — it contains all QML infrastructure, correct versioning, and is synced with `origin/main`.
2. **`qml-migration-foundation` has 34 unreleased commits** with QML refinements (Home, Sidebar premium, HomeAudio, ActionButton, Connections, playlists backend). These are **not merged** into `main`.
3. **Version is unified** at `0.2.0-alpha.1` — no contradictions.
4. **Demo data is properly gated** — not visible by default.
5. **DB paths are correct** — using `core.paths.database_path()`.
6. **`AGENTS.md` correctly** describes QtWidgets as stable and QML as experimental.
7. **The stale `v0.2.0-beta` tag** exists 3 commits behind HEAD. It should be overwritten or ignored.
8. **No contradictions remain** in the `main` branch.

## Recommended Next Step

The `qml-migration-foundation` branch contains valuable QML refinements. If QML is to be the premium skin, merging those 34 commits into `main` would bring: Home QML, Sidebar premium, HomeAudio QML, Connections premium, ActionButton, and playlists backend improvements.

However, this audit confirms that `main` is **self-consistent and usable** as-is for the `0.2.0-alpha.1` release without those refinements.
