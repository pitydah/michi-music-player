# Contributing to Michi Music Player

## Development Setup

```bash
git clone https://github.com/pitydah/michi-music-player.git
cd michi-music-player
pip install -e ".[dev]"
python main.py
```

## Running Tests

```bash
# Quick test
pytest tests/ -q

# Full CI suite
bash scripts/ci_canonical.sh
```

## Code Style

- Ruff with default config
- Type hints on all public functions
- No `except Exception: pass`
- No `{"ok": True}` without verification

## Pull Request Process

1. Run `bash scripts/ci_canonical.sh` locally
2. Add tests for new functionality
3. Update documentation if needed
4. Create PR with clear description
