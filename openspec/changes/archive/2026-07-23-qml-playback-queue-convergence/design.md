# Design: QML Playback Queue Convergence

## Technical Approach

Create a single canonical `QueueItem` dataclass + normalizer under `ui_qml/models/`, then collapse 3 in-memory queue copies (QueueService._items, QueueListModel._items, NowPlayingBridge._queue) into 2 (QueueService + QueueListModel). NowPlayingBridge drops all queue state; QML consumers read from QueueBridge's `queueModel`. Delivered in 3 autonomous slices within the 400-line review budget.

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Normalizer location | Core (QueueService) vs Bridge vs Model | `ui_qml/models/queue_item.py` | QML-specific fields (cover_key, source_type) don't belong in domain layer. Model co-location follows existing `_item_to_dict` pattern. |
| NowPlayingBridge queue removal | Delete property outright vs pass-through compat | Delete after migration | Spec requires "MUST NOT cache, normalize, or subscribe". Consumers migrate to QueueBridge context in slice 2. |
| QueueItem shape | dataclass vs TypedDict vs plain dict | `@dataclass` with `as_dict()` method | Type-safe, IDE-friendly, testable. QAbstractListModel.data() returns dict via as_dict(). |
| saveAsPlaylist dedup | QueueBridge single-write vs both bridges | QueueBridge only | QueueActions.qml already calls `qb.saveAsPlaylist`. NowPlayingBridge has no playlist save. One path, one write. |
| _cover_key_for_path extraction | Duplicate in normalizer vs shared util | Extracted to `queue_item.py` | Removes implicit dependency from nowplaying_bridge. Both normalizer and bridge import from single source. |

## Data Flow

```
                  QueueService (core/)
                  _items: list[dict] ── subscribe() ──┐
                       │                              │
                  replace_and_play()                   │
                       │                              │
                       ▼                              ▼
                  QueueBridge                     QueueListModel
                  queueModel ──→ exposes ──→ _queue_state
                  queueCount                      │
                  currentIndex           _fetch_page() calls
                       │                queue_item_from_raw()
                       │                       │
                       ▼                       ▼
                  QML Consumers          dict[QueueItem fields]
                  QueuePage.qml            (11 typed roles)
                  PlaybackPage.qml
                  NowPlayingQueuePreview.qml

                  NowPlayingBridge
                  (transport, history, quality ONLY)
                  ✗ NO _queue, NO _normalize_queue, NO queue subscription
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `ui_qml/models/queue_item.py` | **Create** | QueueItem dataclass (11 fields) + `queue_item_from_raw()` normalizer + `_cover_key_for_path()` |
| `ui_qml/models/QueueListModel.py` | Modify | Import normalizer; add CoverKeyRole, SourceTypeRole; _item_to_dict delegates to normalizer |
| `ui_qml_bridge/queue_bridge.py` | Modify | Add `currentIndex` property, `add(items)` slot, `replaceAndPlay(items, startIndex)` slot |
| `ui_qml_bridge/nowplaying_bridge.py` | Modify | Remove `_queue`, `_queue_internal_refs`, `_normalize_queue*()`, `_queueDomainChanged` subscription; keep transport+history+quality |
| `ui_qml/pages/PlaybackPage.qml` | Modify | Replace `ps.queue` with `qb.queueModel`/`qb.queueCount` |
| `ui_qml/pages/nowplaying/NowPlayingQueuePreview.qml` | Modify | Replace `ps.queue` with `qb.queueModel` |
| `tests/qml/models/test_queue_item.py` | **Create** | Contract tests: dict/object convergence, defaults, types, cover_key derivation |
| `tests/qml/queue/test_queue_bridge_v2.py` | **Create** | QueueBridge add/replaceAndPlay delegation, currentIndex, single-event propagation |
| `tests/qml/playback/test_nowplaying_queue_removal.py` | **Create** | Verify NowPlayingBridge has no queue state after migration |
| `tests/qml/queue/test_queue_offscreen_rendering.py` | **Create** | Offscreen QueuePage tests: empty, populated, current, reordered states |

## Interfaces / Contracts

### QueueItem (new dataclass)
```python
@dataclass
class QueueItem:
    queue_index: int = 0
    track_id: str = ""
    track_uid: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_key: str = ""
    duration: int = 0
    filepath: str = ""        # internal, not exposed as QML role
    cover_key: str = ""
    source_type: str = "local_file"
    is_current: bool = False
    position: int = 0

    def as_dict(self) -> dict: ...

def queue_item_from_raw(raw: dict, index: int, current_index: int) -> QueueItem: ...
def _cover_key_for_path(filepath: str) -> str: ...
```

### QueueListModel roleNames (post-change)
```
trackId:string, trackUid:string, title:string, artist:string, album:string,
albumKey:string, duration:int, current:bool, position:int,
coverKey:string, sourceType:string
```

### QueueBridge new slots
```
add(items: QVariantList) → dict        # delegates to QueueService.enqueue(play_now=False)
replaceAndPlay(items: QVariantList, startIndex: int) → dict  # delegates to QueueService.replace_and_play
currentIndex: int (property)            # delegates to QueueService.current_index
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | QueueItem defaults, normalizer contract (dict/object convergence) | `test_queue_item.py` — TDD first |
| Unit | QueueListModel roleNames includes all 11 roles, data() returns typed values | Extend existing `test_queue_canonical_inyeccion.py` |
| Integration | QueueBridge.add/replaceAndPlay delegation count, NowPlayingBridge has no queue state | `test_queue_bridge_v2.py`, `test_nowplaying_queue_removal.py` |
| Integration | One queue event → one model refresh across QueuePage + PlaybackPage + NowPlayingQueuePreview | Extend `test_playback_queue_workflow.py` |
| QML | Offscreen rendering: empty, populated, current-item highlight, reorder animation | `test_queue_offscreen_rendering.py` — QQuickView + mock bridges |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

**Slice 1** (projector): No consumer changes. QueueListModel internally uses new normalizer. Add roles: compatible with existing consumers.

**Slice 2** (observation): PlaybackPage and NowPlayingQueuePreview switch context from `ps.queue` to `qb.queueModel`. NowPlayingBridge drops queue properties. If reverted mid-slice, QML consumers fall back to `ps.queue` (still available until removal commit).

**Slice 3** (commands + render): add/replaceAndPlay semantics + offscreen tests. Revertable independently.

## Open Questions

- [ ] Does PlaybackPage.qml have access to `queueBridge` context, or does it need injection?
- [ ] Should `QueueItem.as_dict()` include `filepath` internally but exclude from QML roles? (Design says yes — filepath is for cover derivation only)
