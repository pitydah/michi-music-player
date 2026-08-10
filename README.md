# Michi Music Player

Audio-only desktop music player rebuilt from scratch.

**Status:** pre-alpha — M1–M7 functional core working.

## Requirements

- Python ≥ 3.11
- PySide6 ≥ 6.5
- Qt 6 with multimedia support

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

## What works (M1–M7)

- Play, pause, resume, stop
- Seek, volume, mute
- Queue with auto-advance
- Directory scan for audio files
- Live search
- Settings persistence (SQLite)
- Keyboard shortcuts

## License

GPL-3.0
