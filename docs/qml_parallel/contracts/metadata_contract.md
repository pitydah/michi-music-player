# Metadata Bridge Contract

## Context Property
`MetadataBridge` registered as `metadata` context property.

## Class Name
`MetadataBridge` (`ui_qml_bridge/metadata_bridge.py`)

## Constructor Dependencies
| Parameter | Type | Default |
|-----------|------|---------|
| `metadata_service` | `Any (MetadataService) \| None` | `None` |
| `job_service` | `Any (JobService) \| None` | `None` |
| `parent` | `QObject \| None` | `None` |

## Properties
| Name | Type | Notify | Description |
|------|------|--------|-------------|
| `hasSelection` | `bool` | `selectionChanged` | Whether a file is currently selected |
| `isLoading` | `bool` | `dataChanged` | Whether metadata is being loaded |
| `errorMessage` | `str` | `dataChanged` | Last error message |
| `trackTitle` | `str` | `dataChanged` | Current track title |
| `trackArtist` | `str` | `dataChanged` | Current track artist |
| `trackAlbum` | `str` | `dataChanged` | Current track album |
| `fields` | `QVariantList` | `dataChanged` | All metadata fields with key, label, value, type |
| `qualitySummary` | `str` | `dataChanged` | Format/bitrate/samplerate summary |
| `artworkStatus` | `str` | `dataChanged` | Artwork presence description |
| `canApply` | `bool` | `selectionChanged` | Whether save is possible |
| `status` | `str` | `statusChanged` | Current operation status |

## Slots
| Name | Parameters | Return | Description |
|------|-----------|--------|-------------|
| `loadMetadata` | `filepath: str` | `dict` | Load metadata for a file |
| `setField` | `key: str, value: str` | `dict` | Update a metadata field |
| `saveChanges` | — | `dict` | Save pending changes; enters AWAITING_CONFIRMATION if service available |
| `confirmSave` | `review_id: str` | `dict` | Confirm and apply pending save |
| `rejectSave` | — | `dict` | Reject pending save |
| `hasArtwork` | — | `dict` | Return whether current file has artwork |
| `replaceArtwork` | `image_path: str` | `dict` | Replace artwork with external image |
| `removeArtwork` | — | `dict` | Remove artwork from file |
| `clear` | — | `void` | Clear all selection and field state |
| `batchSetField` | `filepaths: list, key: str, value: QVariant` | `dict` | Batch set a field on multiple files |
| `cancelBatch` | — | `dict` | Cancel batch operation |
| `refresh` | — | `void` | Reload metadata for current file |

## Signals
| Name | Payload | Description |
|------|---------|-------------|
| `dataChanged` | — | Metadata fields or state changed |
| `selectionChanged` | — | File selection changed |
| `batchProgress` | `int applied, int total` | Progress during batch operation |
| `statusChanged` | `str` | Current status changed |
| `operationCompleted` | `str` | Operation completed (save, artwork, artwork_removed) |
| `operationFailed` | `str code, str message` | Operation failed |
| `confirmationRequested` | `str review_id, int change_count` | Confirmation required for destructive save |

## Models Exposed
None. Fields returned as QVariantList of dicts with key, label, value, type.

## Status Values
IDLE, READING, BACKING_UP, WRITING, VERIFYING, ROLLING_BACK, AWAITING_CONFIRMATION, QUEUED, APPLYING, SUCCEEDED, PARTIAL, FAILED, CANCELLED, ERROR

## Field Types
- `text` — string values (title, artist, album, album_artist, genre, composer, comment)
- `int` — numeric values (year, track_number, track_total, disc_number, disc_total, bpm)
- `info` — read-only values (format, bitrate, sample_rate, bit_depth, channels, duration)

## Error Handling
- All slots return `dict` with `ok: bool`
- Error codes: `"EMPTY_FILEPATH"`, `"FILE_NOT_FOUND"`, `"NO_FILE_SELECTED"`, `"NO_CHANGES"`, `"INVALID_TOKEN"`, `"WRITE_FAILED"`, `"VERIFY_FAILED"`, `"METADATA_SERVICE_UNAVAILABLE"`

## Error Codes
- `EMPTY_FILEPATH` — empty path passed to loadMetadata
- `FILE_NOT_FOUND` — file doesn't exist
- `NO_FILE_SELECTED` — no file loaded for save/edit
- `NO_CHANGES` — no dirty fields to save
- `INVALID_TOKEN` — review_id mismatch for confirmation
- `WRITE_FAILED` — tag write failed
- `VERIFY_FAILED` — verification after write failed
- `METADATA_SERVICE_UNAVAILABLE` — batch operation without metadata_service

## States
- `_status` tracks operation lifecycle (IDLE → READING → BACKING_UP → WRITING → VERIFYING → SUCCEEDED/FAILED)
- Rollback on write/verify failure
- Confirmation flow: AWAITING_CONFIRMATION → confirmSave/rejectSave

## Lifecycle
- Created by `BridgeFactory.create_metadata_bridge()` with metadata_service + job_service
- Single-file mode: `loadMetadata(filepath)` → set fields → `saveChanges()` → `confirmSave()`
- Batch mode: `batchSetField(filepaths, key, value)` → progress via `batchProgress`
- Backup-verify-rollback pattern for all writes (via `metadata_tag_adapter.py`)

## Behavior When Service Is Null/Missing
- Without `metadata_service`: falls back to `_legacy_read()` for reading; `saveChanges()` uses direct `write_tags_safe()` (bypasses confirmation token)
- Without `job_service`: batch operations not tracked as jobs

## Integration
- **JobService**: `batchSetField` creates job via `_js.create()` for tracking, updates progress
- **ActionRegistry**: Not used
- **NavigationBridge**: Not used
- **CapabilityBridge**: Registered as `metadata` bridge with no explicit capability gate

## Cancellation Contract
- `cancelBatch()` sets status to CANCELLED
- Batch operation processes files sequentially (no cancellation mid-batch beyond status flag)

## Destructive Action Handling
- `saveChanges()` + `confirmSave()` — writes metadata to file (backup created for rollback)
- `replaceArtwork(image_path)` — replaces embedded artwork (backup created)
- `removeArtwork()` — removes embedded artwork (backup created)
- `batchSetField()` — batch metadata write (backup per file)
- All destructive writes follow backup → write → verify → rollback on failure pattern
- Confirmation required: `saveChanges()` requests confirmation via `confirmationRequested` signal when metadata_service available
- `_write_and_verify()` performs backup-rollback sequence on failure
