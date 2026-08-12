# Michi Music Player

Audio-only desktop music player rebuilt from scratch.

**Status:** advanced pre-alpha clean rebuild. Development has progressed through M11.2A; several Required-1.0 capabilities remain partial (shuffle, repeat, metadata extraction). Component states: `docs/STATUS_MATRIX.md`.

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
- UI foundation: theme tokens + primitives (MichiButton, MichiPanel, MichiSlider, MichiTextField)
- Settings persistence (SQLite, WAL): volume, muted, last_directory, recent_files — with restart gate and read-only health detection
- Failure contracts: explicit runtime errors, best-effort shutdown (first-error-wins)

## Not yet implemented (Required for 1.0)

- Shuffle, repeat (none/one/all)
- Basic metadata (title/artist/album/duration) — filename stem shown today

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
