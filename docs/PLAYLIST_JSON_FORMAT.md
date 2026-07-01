# Playlist JSON Format — Michi Music Player

Formato de exportación/importación de playlists.

## Formato

```json
{
  "format": "michi.playlist.v1",
  "exported_at": 1719000000.0,
  "playlist": {
    "id": 1,
    "name": "Mi Playlist",
    "description": "Descripción opcional",
    "cover_type": "mosaic",
    "cover_path": "/path/to/cover.jpg",
    "is_smart": false
  },
  "tracks": [
    {
      "position": 0,
      "track_id": 42,
      "track_uid": "uid-abc-123",
      "filepath": "/music/song.flac",
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "year": 2024,
      "genre": "Rock",
      "duration": 200.0,
      "ext": "flac",
      "bitrate": 1411,
      "sample_rate": 44100,
      "bit_depth": 16,
      "quality": "lossless",
      "content_hash": "sha256-hash"
    }
  ]
}
```

## Compatibilidad

- Export `safe_mobile=True` omite `filepath` para no exponer rutas locales.
- Import reconoce tanto `filepath` como `path`.
