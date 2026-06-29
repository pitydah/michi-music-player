# Import to Server — Track Import Flow

## Overview

The "Import to Server" feature allows Michi Music Player to send tracks, artwork,
and playlists to a paired Michi Micro Server. The Micro Server downloads each track
from the Player's stream endpoint.

## Flow

```
1. User selects tracks to import
2. Player creates import session with Micro Server
   → POST /api/v1/import/session/create
3. For each track:
   a. Player computes local SHA-256 hash
   b. Micro Server streams track from Player
      → GET /api/v1/stream/{track_id}
   c. On success: mark uploaded
   d. On failure: log error, continue
4. Player uploads artwork
5. Player uploads playlist metadata
6. Player commits session
   → POST /api/v1/import/session/commit
7. On any error before commit:
   → POST /api/v1/import/session/rollback
```

## Service API

### ImportToServerService

```python
class ImportToServerService:
    def create_session(self, server, track_ids) -> Result
    def upload_track(self, session_id, track_id, download_path,
                     local_filepath="", progress_cb=None) -> Result
    def upload_artwork(self, session_id, cover_id, artwork_path="") -> Result
    def upload_playlist(self, session_id, playlist) -> Result
    def commit(self, session_id) -> Result
    def rollback(self, session_id) -> Result
    def status(self, session_id) -> Result
```

### Progress callback

```python
def progress_cb(current: int, total: int, track_id: str) -> None:
    """Called after each track upload."""
```

## Hash verification

Before uploading, the Player computes `SHA-256` of the local file.
The hash is included in the upload result for verification on the Micro Server side.

## Session lifecycle

```
create_session() → [...upload_track()...] → commit()  or  rollback()
```

- commit() fails if any errors were recorded
- rollback() removes the session from memory
- status() returns progress at any point
