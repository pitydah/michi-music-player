# Track Identity — Player

## Overview

`TrackIdentityService` computes a stable identity for each local track file,
used for import preflight (checking if the Micro Server already has a track)
and for Continue on Server (resolving local queue to remote track_ids).

## Identity fields

| Field | Source | Purpose |
|-------|--------|---------|
| `sha256_prefix` | First 64KB of file → SHA-256 → 32 hex chars | Fast content fingerprint |
| `file_size` | `os.path.getsize()` | Size check |
| `duration_ms` | DB metadata (duration × 1000) | Duration check |
| `title`, `artist`, `album` | DB metadata or filename | Human-readable |
| `normalized_*` | Lower-cased, stripped, whitespace-collapsed | Fuzzy matching |

## Match logic

```python
def match(a: TrackIdentity, b: TrackIdentity) -> bool:
    if both have sha256_prefix:
        return sha256_prefix == sha256_prefix
    if same file_size AND duration within 2s:
        return normalized_title == normalized_title
        AND normalized_artist == normalized_artist
    return False
```

## Preflight

`ImportToServerService.preflight()` sends identities to the Micro Server:

```
POST /api/v1/import/preflight
Body: { "tracks": [{ sha256_prefix, file_size, duration_ms, title, artist, album }] }
Response: { "results": [{ local_track_id, exists, remote_track_id }] }
```

If the Micro Server does not support `/api/v1/import/preflight` (404),
the Player falls back to assuming every track needs upload.

## Service

```python
from integrations.michi_link.services.track_identity_service import (
    TrackIdentityService,
)

svc = TrackIdentityService()
result = svc.compute("/path/to/song.flac", db_item=db_item)
if result.ok:
    identity = result.data
    preflight_payload = svc.identity_to_preflight(identity)
```
