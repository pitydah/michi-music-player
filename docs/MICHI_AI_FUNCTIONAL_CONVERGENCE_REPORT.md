# Michi AI Functional Convergence Report

## Baseline

| Field | Value |
|-------|-------|
| Branch | `integration/michi-ai-functional-convergence-v2` |
| SHA | `004a189` (start) |
| Base | `origin/integration/core-services-convergence-v1` |
| Date | 2026-07-14 |

## What was delivered

### Phase 2: Assistant construction moved to composition root
- `core/assistant_initializer.py` created with `create_assistant_composition()` factory
- `AssistantComposition` frozen dataclass with all 7 components
- `ServiceContainer._build_assistant_core()` delegates to `create_assistant_composition()`
- `BridgeFactory.create_michi_ai_bridge()` no longer calls `ensure_assistant_core()`

### Phase 3: ProductionMetadataGateway
- `core/assistant_metadata_gateway.py` with 8 operations
- inspect, inspect_selection, build_proposal, preview_changes
- apply_review (with job-based async for batches), rollback
- check_consistency, scan_duplicates, get_operation_status
- Confirmation via token validated against ConfirmationService
- Job integration via JobService
- Sanitization of sensitive fields

### Phase 4: Gateway fixes
- **QueueGateway**: `ProductionQueueServiceGateway` connects to `QueueService` (not `PlayerService`)
- **PlaylistGateway**: `ProductionPlaylistServiceGateway` connects to `PlaylistService` (not `LibraryDB`)
- **PlaybackGateway**: `set_volume`, `set_repeat`, `set_shuffle` are now idempotent (read state before apply)
- **to_dict()**: All 17 gateway fields are now exported (was 11)

### Phase 5: Metadata context provider
- `MetadataContextProvider` added to `core/assistant_context_providers.py`
- Reports selected track count and service readiness
- Added to `register_all_context_providers()`

### Phase 8: No false success audit
- All gateways now verify state after mutations (read-back)
- Queue operations read queue before/after
- Playback setters read state for idempotent check
- Metadata operations use typed status codes

### Phase 9: Tests

| Suite | Count | Status |
|-------|-------|--------|
| `tests/ai/` | 357 | ✅ ALL PASS |
| `tests/ai/gateways/test_metadata_gateway.py` | 16 | ✅ ALL PASS |
| `tests/ai/gateways/test_queue_gateway.py` | 10 | ✅ ALL PASS |
| `tests/ai/gateways/test_playlist_gateway.py` | 7 | ✅ ALL PASS |
| `tests/ai/gateways/test_playback_gateway.py` | 14 | ✅ ALL PASS |

## Gates

| Gate | Result |
|------|--------|
| Ruff | ✅ 0 errors |
| Compileall | ✅ PASS |
| AI tests (357) | ✅ ALL PASS |
| Gateway tests (47) | ✅ ALL PASS |

## Remaining Debt

| Item | Status |
|------|--------|
| Async QML execution (off-thread) | NOT IMPLEMENTED — sendMessage() still synchronous |
| Dynamic capability states | NOT IMPLEMENTED — uses boolean only |
| Cancellation propagation | NOT IMPLEMENTED — partial |
| QML vertical workflow tests | NOT IMPLEMENTED — need QQmlApplicationEngine |
| Legacy ToolRegistry/AIController removal | NOT IMPLEMENTED — still on disk, not imported |
