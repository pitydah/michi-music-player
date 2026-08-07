"""Michi Link API v1 — permission constants."""
from __future__ import annotations

V1_PERMISSIONS: set[str] = {
    "library.read",
    "library.write",
    "stream.read",
    "artwork.read",
    "artwork.write",
    "sync.read_manifest",
    "sync.upload_state",
    "playback.read",
    "playback.control",
    "queue.read",
    "queue.write",
    "import.read",
    "import.write",
}

V1_ENDPOINT_PERMISSIONS: dict[str, str] = {
    # Library
    "GET/api/v1/library/stats": "library.read",
    "GET/api/v1/tracks": "library.read",
    "GET/api/v1/search": "library.read",
    "GET/api/v1/playlists": "library.read",
    "GET/api/v1/sync/manifest": "sync.read_manifest",
    "GET/api/v1/sync/manifest/delta": "sync.read_manifest",
    "POST/api/v1/sync/state": "sync.upload_state",
    # Stream
    "GET/api/v1/stream": "stream.read",
    "GET/api/v1/artwork": "artwork.read",
    # Import
    "POST/api/v1/import/preflight": "import.read",
    "POST/api/v1/import/session/create": "import.write",
    "POST/api/v1/import/track/upload": "import.write",
    "POST/api/v1/import/track/artwork": "artwork.write",
    "POST/api/v1/import/playlists/upload": "import.write",
    "GET/api/v1/import/session/status": "import.read",
    "POST/api/v1/import/session/commit": "import.write",
    "POST/api/v1/import/session/rollback": "import.write",
    "GET/api/v1/import/track/info": "import.read",
    "GET/api/v1/import/track/stream": "stream.read",
    # Playback
    "GET/api/v1/playback/state": "playback.read",
    "POST/api/v1/playback/control": "playback.control",
    "GET/api/v1/queue": "queue.read",
    "POST/api/v1/queue/items": "queue.write",
    "POST/api/v1/queue/jump": "queue.write",
}
