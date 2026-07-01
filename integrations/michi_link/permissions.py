"""Michi Link API v1 — permission constants."""
from __future__ import annotations

V1_PERMISSIONS: set[str] = {
    "library.read",
    "stream.read",
    "artwork.read",
    "sync.read_manifest",
    "sync.upload_state",
    "playback.read",
    "playback.control",
    "queue.read",
    "queue.write",
    "playlist.read",
    "playlist.write",
}

V1_ENDPOINT_PERMISSIONS: dict[str, str] = {
    # Library
    "GET/api/v1/library/stats": "library.read",
    "GET/api/v1/tracks": "library.read",
    "GET/api/v1/search": "library.read",
    "GET/api/v1/sync/manifest": "sync.read_manifest",
    "GET/api/v1/sync/manifest/delta": "sync.read_manifest",
    "POST/api/v1/sync/state": "sync.upload_state",
    # Stream
    "GET/api/v1/stream": "stream.read",
    "GET/api/v1/artwork": "artwork.read",
    # Playback
    "GET/api/v1/playback/state": "playback.read",
    "POST/api/v1/playback/control": "playback.control",
    "GET/api/v1/queue": "queue.read",
    "POST/api/v1/queue/items": "queue.write",
    "POST/api/v1/queue/jump": "queue.write",
    # Playlists
    "GET/api/v1/playlists": "playlist.read",
    "POST/api/v1/playlists": "playlist.write",
    "DELETE/api/v1/playlists": "playlist.write",
    "GET/api/v1/playlists/manifest": "playlist.read",
    "GET/api/v1/playlists/manifest/delta": "playlist.read",
}
