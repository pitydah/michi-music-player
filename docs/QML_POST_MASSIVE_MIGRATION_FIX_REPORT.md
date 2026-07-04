# QML Post Massive Migration Fix Report

Date: 2026-07-04
Base: `6333399` plus local stabilization fixes

## Scope

This pass fixes the immediate CI lint blocker and the QML runtime/layout issues found after the massive QML migration landed on `main`.

## Fixes Applied

| Area | Change |
|---|---|
| CI / Ruff | Fixed remaining `SIM102` and `E701` lint failures. |
| LibraryBridge | Kept file existence validation readable and Ruff-clean. |
| NowPlayingBar | Added stable sizing for cover/info/status layout so title and artist no longer collapse to negative width. |
| ExpandedNowPlayingPanel | Prevented collapsed panel children from receiving negative dimensions. |
| FilterChip | Added `implicitWidth` so library format chips are visible and clickable. |
| Home Audio | Registered `homeAudioBridge` in `qml_main.py`, reconnecting `HomeAudioPage.qml` to its bridge. |
| QML property warnings | Removed custom `enabled`/`palette` declarations that shadowed Qt base properties. |
| Bridge audit | Scoped bridge-contract audit rules to real bridge files and stateful refresh contracts. |
| Tests | Added QML regression tests for NowPlayingBar dimensions, FilterChip width, and `homeAudioBridge` registration. |

## Validation

| Command | Result |
|---|---|
| `ruff check .` | OK |
| `python -m compileall -q -x '.venv/|\\.tmpl\\.' .` | OK |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q` | 310 passed |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/test_qml_bridges.py -q` | 171 passed |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/test_qml_components.py -q` | 139 passed |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 timeout 6s python main.py --qml` | Loads root QML; timeout expected; no QML property override warnings |
| `python scripts/qml_route_registry_audit.py` | 0 errors |
| `python scripts/qml_bridge_contract_audit.py` | 0 warnings |

## Known Residual Notes

Full `pytest` still includes pre-existing QtWidgets/Michi Link failures outside the CI-selected groups. They were present before this QML stabilization pass and remain separate from the QML migration fix.
