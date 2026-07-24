# Tasks: QML Convergence v2

## Unit1: Audit + Contracts (Gate: contratos PASS)

### Task1.1: Add granular signal filtering to QueueBridge
- **Files:** `ui_qml_bridge/queue_bridge.py`
- **Test:** `tests/qml/queue/test_queue_bridge_signals.py`
- **Description:** Filter QueueService subscription callbacks to emit specific signals based on operation type instead of a single `dataChanged` for everything
- **Estimated lines:** 80-120

### Task1.2: Verify no local queue in NowPlayingBridge
- **Files:** `ui_qml_bridge/nowplaying_bridge.py`
- **Test:** `tests/qml/playback/test_nowplaying_no_local_queue.py`
- **Description:** Add tests verifying NowPlayingBridge has no queue property and delegates all queue ops to QueueService
- **Estimated lines:** 30-50

### Task1.3: Clean PlaybackBridge fallback references
- **Files:** `ui_qml/pages/PlaybackPage.qml`, `ui_qml/pages/nowplaying/NowPlayingBar.qml`, `ui_qml/pages/nowplaying/NowPlayingPage.qml`, `ui_qml/pages/queue/QueuePage.qml`, `ui_qml/components/ExpandedNowPlayingPanel.qml`
- **Test:** visual verification
- **Description:** Replace `playbackBridge` fallback with `nowplayingBridge` as primary in all QML files
- **Estimated lines:** 20-30

### Task1.4: Contract tests for QueueBridge
- **Files:** `tests/qml/queue/test_queue_bridge_contract.py`
- **Description:** Verify all QueueBridge properties and commands exist and work
- **Estimated lines:** 100-150

### Task1.5: Contract tests for NowPlayingBridge
- **Files:** `tests/qml/playback/test_nowplaying_contract.py`
- **Description:** Verify all NowPlayingBridge properties and commands exist and work
- **Estimated lines:** 100-150

---

## Unit2: Projection (Gate: projection PASS)

### Task2.1: Incremental QueueListModel
- **Files:** `ui_qml/models/QueueListModel.py`
- **Test:** `tests/qml/models/test_queue_list_model_incremental.py`
- **Description:** Replace beginResetModel with dataChanged/beginInsertRows/beginRemoveRows/beginMoveRows for non-structural changes
- **Estimated lines:** 150-200

### Task2.2: QueueListModel signal tests
- **Files:** `tests/qml/models/test_queue_list_model_signals.py`
- **Description:** Verify exact signals emitted for each mutation type
- **Estimated lines:** 80-120

### Task2.3: Scroll and focus preservation tests
- **Files:** `tests/qml/models/test_queue_list_model_preservation.py`
- **Description:** Verify scroll position and keyboard focus preserved after non-structural changes
- **Estimated lines:** 50-80

---

## Unit3: Queue Runtime (Gate: queue-runtime PASS)

### Task3.1: QueuePage state machine
- **Files:** `ui_qml/pages/queue/QueuePage.qml`
- **Test:** `tests/qml/queue/test_queue_page_runtime.py`
- **Description:** Implement LOADING/READY/EMPTY/ERROR states with PageStateManager
- **Estimated lines:** 80-120

### Task3.2: QueuePage interaction tests
- **Files:** `tests/qml/queue/test_queue_page_interactions.py`
- **Description:** Test play, remove, move, clear, shuffle, repeat, undo, saveAsPlaylist
- **Estimated lines:** 100-150

### Task3.3: QueuePage accessibility
- **Files:** `ui_qml/pages/queue/QueuePage.qml`, sub-components
- **Test:** `tests/qml/queue/test_queue_page_accessibility.py`
- **Description:** Add Accessible.name/description to all interactive controls
- **Estimated lines:** 40-60

---

## Unit4: NowPlaying Runtime (Gate: playback-runtime PASS)

### Task4.1: NowPlayingPage state machine
- **Files:** `ui_qml/pages/nowplaying/NowPlayingPage.qml`
- **Test:** `tests/qml/playback/test_nowplaying_page_runtime.py`
- **Description:** Implement LOADING/EMPTY/READY/ERROR states
- **Estimated lines:** 60-80

### Task4.2: NowPlayingBar state machine
- **Files:** `ui_qml/components/NowPlayingBar.qml`
- **Test:** `tests/qml/playback/test_nowplaying_bar_runtime.py`
- **Description:** Implement state machine, commandPending only on affected control
- **Estimated lines:** 60-80

### Task4.3: NowPlaying sync tests
- **Files:** `tests/qml/playback/test_nowplaying_sync.py`
- **Description:** Test track change, play/pause, next/prev, seek, duration, position, volume, mute, artwork
- **Estimated lines:** 100-150

---

## Unit5: Session (Gate: session-continuity PASS)

### Task5.1: Session restore verification
- **Files:** `tests/test_session_continuity.py`
- **Description:** Test queue restore, index remap, position clamp, no autoplay
- **Estimated lines:** 100-150

### Task5.2: Missing track handling tests
- **Files:** `tests/test_session_missing_tracks.py`
- **Description:** Test resolver, available:false marking, index adjustment
- **Estimated lines:** 80-120

---

## Unit6: Integration (Gate: vertical-integration PASS)

### Task6.1: Vertical integration tests
- **Files:** `tests/test_vertical_integration.py`
- **Description:** Library→QueueService→QueueBridge→QueueListModel→QueuePage flow
- **Estimated lines:** 100-150

### Task6.2: Performance tests
- **Files:** `tests/test_queue_performance.py`
- **Description:** 100/1000/5000 track benchmarks
- **Estimated lines:** 80-120

### Task6.3: Runtime QML instantiation tests
- **Files:** `tests/qml/test_qml_instantiation.py`
- **Description:** QQmlComponent instantiation of QueuePage, NowPlayingPage, NowPlayingBar
- **Estimated lines:** 80-120

---

## Total Estimated Lines

| Unit | Estimated |
|------|-----------|
| Unit1 | 330-500 |
| Unit2 | 280-400 |
| Unit3 | 220-330 |
| Unit4 | 220-310 |
| Unit5 | 180-270 |
| Unit6 | 260-390 |
| **Total** | **1490-2200** |

## Review Budget

- Per-slice budget: 400 lines
- Estimated slices: 4-6
- Chain strategy: stacked-to-main
