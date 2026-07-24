# Technical Design: QML Convergence v2

## Architecture

```
QueueService (single authority)
├── QueueBridge → QML queue state + commands
│   └── QueueListModel → incremental QAbstractListModel
└── NowPlayingBridge → QML playback state + commands
    └── (no local queue)

PlayerService → physical playback execution
PlaybackBridge → thin delegate to NowPlayingBridge (legacy, not primary)
```

## Key Design Decisions

### D1: Signal Granularity via Subscription Filtering

QueueService already publishes granular operation types (`add`, `remove`, `move`, `clear`, `shuffle`, `repeat`, `current_index`, `restore`, `compatibility_index`). QueueBridge should filter signals based on operation type:

- `current_index` / `compatibility_index` → emit only `currentIndexChanged` + targeted `dataChanged`
- `add` → emit `itemsChanged` + `countChanged` + `durationSummaryChanged`
- `remove` → emit `itemsChanged` + `countChanged` + `durationSummaryChanged`
- `move` → emit `itemsChanged`
- `shuffle` → emit `itemsChanged` + `shuffleEnabledChanged` + `currentIndexChanged`
- `repeat` → emit `repeatModeChanged`

### D2: Incremental QueueListModel

Replace the blanket `beginResetModel()` approach with granular model updates:

1. Connect to QueueBridge's granular signals (not just a single `dataChanged`)
2. For `currentIndexChanged`: emit `dataChanged` for old row + new row only
3. For `add`: use `beginInsertRows`/`endInsertRows`
4. For `remove`: use `beginRemoveRows`/`endRemoveRows`
5. For `move`: use `beginMoveRows`/`endMoveRows`
6. For `shuffle`/`restore`: use `beginResetModel` (structural change)

### D3: PlaybackBridge Cleanup

PlaybackBridge is a thin delegate (3 lines: `self._nowplaying = nowplaying_bridge`). QML files should use `nowplayingBridge` as primary. The fallback pattern `typeof nowplayingBridge !== "undefined" && nowplayingBridge ? nowplayingBridge : playbackBridge` is safe but should be simplified to just `nowplayingBridge`.

### D4: QueuePage State Machine

```
QueueService.ready == false → LOADING
QueueService.ready == true && error != null → ERROR
QueueService.ready == true && count == 0 → EMPTY
QueueService.ready == true && count > 0 → READY
```

`operationPending` does NOT affect page state — only individual control states.

### D5: NowPlayingPage State Machine

```
nowplayingBridge.currentTrack == null → EMPTY
nowplayingBridge.error != null → ERROR
nowplayingBridge.playbackState == "idle" && currentTrack != null → READY
nowplayingBridge.playbackState == "unavailable" → ERROR
```

`commandPending` does NOT affect page state — only individual button states.

### D6: Session Restore Flow

```
ApplicationBootstrap._restore_session_once()
  → QueueService.load_state(resolve_fn=resolver)
    → validates JSON structure
    → resolves each track via resolve_fn
    → marks unresolvable as available:false
    → remaps current_index
    → clamps position to duration
    → returns restored state
  → QueueBridge receives restored state via subscription
  → QueueListModel rebuilds from restored state
  → NO autoplay triggered
```

## File Change Plan

### Unit1: Audit + Contracts
- `ui_qml_bridge/queue_bridge.py` — add granular signal filtering
- `ui_qml_bridge/nowplaying_bridge.py` — verify no local queue, clean PlaybackBridge refs
- `tests/qml/` — add contract tests

### Unit2: Projection
- `ui_qml/models/QueueListModel.py` — incremental updates
- `ui_qml/models/queue_item.py` — verify roles
- `tests/qml/models/` — add incremental update tests

### Unit3: Queue Runtime
- `ui_qml/pages/queue/QueuePage.qml` — state machine, foundations
- `ui_qml/pages/queue/QueueHeader.qml` — verify instantiation
- `ui_qml/pages/queue/QueueActions.qml` — verify commands
- `ui_qml/pages/queue/QueueListView.qml` — incremental updates
- `tests/qml/queue/` — add runtime tests

### Unit4: NowPlaying Runtime
- `ui_qml/pages/nowplaying/NowPlayingPage.qml` — state machine
- `ui_qml/components/NowPlayingBar.qml` — state machine
- `tests/qml/playback/` — add runtime tests

### Unit5: Session
- `core/queue_service.py` — verify restore logic
- `tests/` — add session continuity tests

### Unit6: Integration
- `tests/qml/` — add vertical integration tests
- `tests/` — add performance tests
