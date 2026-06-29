# Player Import Preflight

## Flow

```
1. Player selects tracks to import
2. Player computes TrackIdentity for each track
3. Player calls POST /api/v1/import/preflight on Micro Server
4. Micro Server responds with:
   - which tracks already exist (remote_track_id)
   - which tracks need upload
5. Player creates import session with ONLY the tracks that need upload
6. Player uploads missing tracks (push model, X-Checksum header)
7. Player commits session
8. Player receives local_track_id → remote_track_id mapping
```

## Preflight payload

```json
POST /api/v1/import/preflight
{
  "tracks": [
    {
      "sha256_prefix": "a1b2c3d4e5f6...",
      "file_size": 5000000,
      "duration_ms": 240000,
      "title": "song title",
      "artist": "artist name",
      "album": "album name"
    }
  ]
}
```

## Preflight response

```json
{
  "results": [
    {
      "local_track_id": "t1",
      "exists": true,
      "remote_track_id": "rt_abc123"
    },
    {
      "local_track_id": "t2",
      "exists": false,
      "remote_track_id": ""
    }
  ]
}
```

## Fallback

If the Micro Server returns 404 (preflight not implemented), the Player
falls back to creating a session with all tracks. This is backwards-compatible
with older Micro Server versions.
