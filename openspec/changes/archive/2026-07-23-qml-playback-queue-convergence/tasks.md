# Tasks: QML Playback Queue Convergence

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 650–850 |
| 400-line budget risk | High overall; Low per slice |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 |
| Delivery / chain strategy | auto-chain / stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Canonical projector/model | PR 1 | `pytest tests/qml/models/test_queue_item.py tests/qml/queue/test_queue_canonical_inyeccion.py -q` | N/A: pure projection | `queue_item.py`, `QueueListModel.py` |
| 2 | One QML observation path | PR 2 | `QT_QPA_PLATFORM=offscreen pytest tests/qml/playback/ -q` | `python main.py`; inspect three queue surfaces | bridge/QML migration files |
| 3 | Commands and rendered states | PR 3 | `QT_QPA_PLATFORM=offscreen pytest tests/qml/queue/ -q` | `python main.py`; add, replace, reorder, save | QueueBridge commands/render tests |

## Slice 1: Canonical QueueItem + QueueBridge normalization

- [x] **1.1 QueueItem contract (90–130 lines; deps: none).** RED: create `tests/qml/models/test_queue_item.py` for dict/object parity, defaults/types, private-path exclusion, and cover derivation; run it failing. GREEN: create `ui_qml/models/queue_item.py` with the typed dataclass, projector, and cover helper; rerun.
- [x] **1.2 Complete model roles (80–120 lines; deps: 1.1).** RED: extend `tests/qml/queue/test_queue_canonical_inyeccion.py` for all 11 roles, row positions, and one current item. GREEN: update `ui_qml/models/QueueListModel.py` to delegate normalization and expose `coverKey`/`sourceType`; run both slice-1 tests.

## Slice 2: NowPlayingBridge alignment + observation convergence

- [x] **2.1 Consumer alignment (80–120 lines; deps: 1.2).** RED: extend `tests/qml/playback/test_playback_queue_workflow.py` for QueueBridge model/count/current-index use and unavailable fallback. GREEN: migrate `ui_qml/pages/PlaybackPage.qml` and `ui_qml/pages/nowplaying/NowPlayingQueuePreview.qml`; run the test offscreen.
- [x] **2.2 Remove duplicate state (100–150 lines; deps: 2.1).** RED: create `tests/qml/playback/test_nowplaying_queue_removal.py` asserting no queue cache/property/signal/subscription and retained history/transport. GREEN: remove queue projection code from `ui_qml_bridge/nowplaying_bridge.py`, importing the shared cover helper; rerun.
- [x] **2.3 One-event convergence (70–110 lines; deps: 2.2).** RED: add reorder/update-count and teardown assertions to `test_playback_queue_workflow.py`. GREEN: add `currentIndex` and tighten notifications/unsubscribe behavior in `ui_qml_bridge/queue_bridge.py`; run `QT_QPA_PLATFORM=offscreen pytest tests/qml/playback/ -q`.

## Slice 3: Cleanup + tests + verification

- [x] **3.1 Ingress commands (90–130 lines; deps: 2.3).** RED: create `tests/qml/queue/test_queue_bridge_v2.py` for append preservation, atomic replace, invalid input, and exactly-once delegation. GREEN: implement `add`/`replaceAndPlay` in `queue_bridge.py`; rerun.
- [x] **3.2 Single playlist write (50–80 lines; deps: 3.1).** RED: test success order, blank name, empty queue, unavailable service, and write failure in `test_queue_bridge_v2.py`. GREEN: harden `saveAsPlaylist`; verify one write maximum.
- [x] **3.3 Offscreen states (140–190 lines; deps: 3.2).** RED: create `tests/qml/queue/test_queue_offscreen_rendering.py` for empty, populated, current, reordered, warning-free states. GREEN/refactor QML delegates only as required; run that file with `QT_QPA_PLATFORM=offscreen`.
- [ ] **3.4 Regression verification (20–40 lines; deps: all).** Run all 42+ queue-named tests, then `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q`; run `python -m compileall -q -x '.venv/|\.tmpl\.' .` and scoped Ruff, recording 303 pre-existing global Ruff errors separately.
