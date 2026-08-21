# Michi Music Player

Audio-only desktop music player rebuilt from scratch.

**Status:** advanced pre-alpha clean rebuild. M1–M11 Required-1.0 contracts are tested; the M9 Premium Presentation System baseline is delivered (CLOSED / TESTED / FROZEN, PR #204) and the current development direction is M8-R1 Playlists First-Class Navigation, followed by multi-engine audio (Qt Multimedia + GStreamer + MPD) and audiophile output milestones. Component states: `docs/STATUS_MATRIX.md`.

**Platform:** Linux is the 1.0 target (AppImage/Flatpak/deb at M13). Windows and macOS are Post-1.0 — see `docs/POST_1_0_BACKLOG.md`.

## Requirements

- Python ≥ 3.11
- PySide6 ≥ 6.5
- Qt 6 with multimedia support (FFmpeg backend)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
michi
```

Or without install:

```bash
PYTHONPATH=src python -m michi
```

## Stack

Python 3.11+, PySide6 (Qt 6 / Qt Multimedia, FFmpeg backend), QML, SQLite (WAL), pytest, Ruff, setuptools + build, GitHub Actions CI (lint/test/build, QT_QPA_PLATFORM=offscreen).

## Architecture

```
src/michi/
├── domain/          Pure logic, no Qt
├── application/     Use cases + ports
├── infrastructure/  Qt, SQLite, filesystem
├── presentation/    QML + bridges
└── bootstrap/       Composition root
```

Dependencies flow inward: Presentation → Application → Domain. Infrastructure implements Application ports.

## What works

- Play, pause, resume, stop; seek, volume, mute; position/duration events
- Queue: add/remove/clear, play by index, next/previous, auto-advance
- Library: recursive directory scan with extension filter, substring search
- Navigation: now playing / library / queue / settings screens
- UI foundation: Aurora semantic tokens, smoked-glass control surfaces, desktop controls, accessibility/motion contracts, shared artwork and UI gallery
- Settings persistence (SQLite, WAL): volume, muted, last_directory, recent_files — with restart gate and read-only health detection
- Failure contracts: explicit runtime errors, best-effort shutdown (first-error-wins)

## Current implementation focus

- M9 Premium Presentation System: CLOSED / TESTED / FROZEN baseline delivered by PR #204 — Michi UI Design Canon 2.0
- M8-R1 Playlists First-Class Navigation: next authorized WP (then M9-R1 playlists sidebar presentation)
- M11.3–M11.5: multi-engine audio (Qt Multimedia + GStreamer + MPD), audiophile output/DAC management, playback guarantees (incl. Required-1.0 gapless)
- M12 Performance, M13 Packaging, M14 Beta, M15 RC, M16 Stable

See `docs/MASTER_ROADMAP_1.0.md` for the canonical 1.0 contract and current statuses.

## Governance

- `docs/MASTER_ROADMAP_1.0.md` — roadmap and canonical 1.0 contract
- `docs/ARCHITECTURE.md` — layer contracts, state ownership, boundaries
- `docs/STATUS_MATRIX.md` — component and work-package states
- `docs/DEFINITION_OF_DONE.md` — DoR, DoD, Golden Path
- `docs/INVARIANTS.md` — freeze, P0/P1 gate, WIP limits
- `docs/TECHNICAL_DEBT_REGISTER.md` — active and resolved debt
- `docs/POST_1_0_BACKLOG.md` — deferred scope
- `docs/MIGRATION_LEDGER.md` — Legacy evidence disposition
- `docs/M9_PREMIUM_PRESENTATION_SYSTEM.md` — UI Design Canon 2.0 implementation contract
- `docs/RESEARCH_01_AUDIO_PLAYLISTS_FINDINGS.md` — reference study closeout (playlists + multi-engine + audiophile)
- `docs/M11_3_MULTI_ENGINE_AUDIO_RUNTIME.md` — multi-engine audio runtime contract
- `docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md` — audiophile output & DAC management contract
- `docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md` — audiophile playback guarantees contract
- `docs/adr/` — accepted architectural decisions

## Development

```bash
pytest -q
ruff check src tests
ruff format --check src tests
python -m build
```

## License

GPL-3.0
