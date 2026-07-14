# Metadata QML Integration Baseline

**SHA:** c73c76a870140d7191947603475a33a08b82e728
**Rama:** integration/metadata-core-v2
**Metadata Core SHA:** 3bc9be749fbc236677c1bf9f42749c2910120b97

## Pre-integration State

### ServiceContainer
- `metadata_service` declared as REQUIRED (line 52) but **never registered**
- No concrete `MetadataService` instance existed in production
- `ServiceBundle` aliased `metadata_service = smart_tagging_service` (incorrect)

### BridgeFactory
- `create_metadata_bridge()` created `MetadataBridge` with only `worker_manager`
- No `metadata_service` or `job_service` was injected
- `_register_capability("metadata", ...)` was never called

### MetadataBridge (pre-refactor)
- **402 lines** with inline mutagen reading (`_read_full_metadata`)
- Used `Path(filepath)` directly for filesystem operations
- Saved changes via `metadata_tag_adapter` (backup/write/verify/rollback)
- No `MetadataService` dependency
- No confirmation tokens (QML-side boolean toggles only)
- No status machine
- No job service integration

### Settings Schema
- No `METADATA_SETTINGS` category
- Metadata-related settings were scattered under `ai_assistant/` keys
- No artwork settings

## Integration Changes Applied

| Change | File | Status |
|--------|------|--------|
| Core MetadataService created | `core/metadata_service.py` | ✅ |
| ConfirmationService created | `core/confirmation_service.py` | ✅ |
| Service init created | `core/metadata_init.py` | ✅ |
| Bridge refactored (thin) | `ui_qml_bridge/metadata_bridge.py` | ✅ |
| BridgeFactory injection | `ui_qml_bridge/bridge_factory.py` | ✅ |
| Settings schema added | `core/settings_schema.py` | ✅ |
| Integration tests | `tests/core/test_metadata_integration.py` | ✅ |

## Remaining Debt
- MusicBrainz provider not wired into bridge (import available)
- Artwork provider not wired
- QML pages not updated to use new signals (statusChanged, confirmationRequested, operationCompleted)
