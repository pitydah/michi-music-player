# CI Pipeline — Michi Music Player

File: `.github/workflows/ci.yml`

## Jobs

### 1. `qml-migration-gate` (sequential)

| Step | Purpose |
|------|---------|
| checkout + setup-python | Standard setup |
| Install system deps | `libegl1`, `libgl1`, `libxkbcommon0`, `libfontconfig1`, `xvfb` |
| Install Python deps | `pip install -e ".[dev]"` |
| Ruff check | `ruff check . --output-format concise` |
| Compileall | `python -m compileall -q .` |
| Core tests | 8 service files under `QT_QPA_PLATFORM=offscreen` |
| Productive workflows (offscreen) | 42 files via `run_tests.sh` |
| Productive workflows (Xvfb) | Same 42 files under `xvfb-run -a` with `QT_QPA_PLATFORM=xcb` (continue-on-error) |
| QML compile check | Loads every `.qml` via QQmlComponent |

## Failure modes

- **Qt crash (134/139)** during offscreen run: expected in headless. Xvfb step provides baseline.
- **Ruff violation**: fails immediately. Run `ruff check . --output-format concise` locally.
- **Compileall error**: syntax error or import issue. Run `python -m compileall -q .` locally.

## Pip cache

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('pyproject.toml') }}
```

## Artifacts

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: results
    path: results.xml
```

## Local reproduction

```bash
# Simulate CI offscreen run
QT_QPA_PLATFORM=offscreen bash scripts/run_tests.sh tests/qml/productive_workflows/ offscreen

# Simulate CI Xvfb run
xvfb-run -a bash scripts/run_tests.sh tests/qml/productive_workflows/ xcb
```
