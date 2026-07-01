# Playlist Sync — Michi Link API

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/playlists` | List all playlists |
| GET | `/api/v1/playlists/{id}` | Playlist metadata |
| GET | `/api/v1/playlists/{id}/tracks` | Tracks in playlist |
| POST | `/api/v1/playlists` | Create playlist |
| POST | `/api/v1/playlists/{id}/tracks` | Add tracks |
| POST | `/api/v1/playlists/{id}/reorder` | Reorder tracks |
| DELETE | `/api/v1/playlists/{id}` | Delete playlist |
| GET | `/api/v1/playlists/manifest` | Full sync manifest |
| GET | `/api/v1/playlists/manifest/delta` | Delta since cursor |

## Permissions

- `playlist.read` — for all GET endpoints
- `playlist.write` — for POST/DELETE endpoints

## Security

- No filepaths exposed to mobile clients
- Token-based auth via Authorization header
- Rate limiting on public pairing endpoints

## Manifest format

```json
{
  "format": "michi.playlists.manifest.v1",
  "playlists": [
    {
      "id": "1",
      "name": "My Playlist",
      "track_count": 42,
      "duration": 8400.0,
      "tracks_hash": "abc123..."
    }
  ]
}
```
