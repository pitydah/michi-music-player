# Playlists Premium — Michi Music Player

La suite de Playlists premium incluye servicios modulares,
UI de gestión completa, importación/exportación inteligente,
Health Center, Relinker, Smart Playlists, Cover Studio,
y sincronización con Michi Link.

## Arquitectura

```
library/playlists/
├── __init__.py
├── playlist_models.py        — Dataclasses puras (sin Qt, sin DB)
├── playlist_store.py          — CRUD sobre SQLite
├── playlist_import.py         — M3U/M3U8/PLS/JSON
├── playlist_export.py         — M3U/M3U8/TXT/CSV/JSON/Portable Pack
├── playlist_audit.py          — Health score, duplicados, perdidos, metadata
├── playlist_relinker.py       — Reemplazo inteligente de canciones perdidas
├── playlist_ordering.py       — Ordenamiento manual e inteligente
├── playlist_smart_engine.py   — Smart playlists por reglas SQL
└── playlist_sync_manifest.py  — Manifest/delta para Michi Link
```

## Servicios

### PlaylistStore (`playlist_store.py`)
CRUD completo. Operaciones atómicas.

```python
store = PlaylistStore(conn)
pid = store.create_playlist("Mi Playlist", "Descripción")
store.add_track(pid, filepath="/m/song.flac")
store.set_playlist_order(pid, ordered_filepaths=["/b.flac", "/a.flac"])
items = store.get_playlist_items(pid)
summary = store.get_summary(pid)
```

### PlaylistImport (`playlist_import.py`)
- `preview_import(path)` — analiza archivo sin importar
- `import_as_playlist(path, store, options)` — importa a DB

### PlaylistExport (`playlist_export.py`)
- `export_m3u`, `export_m3u8`, `export_txt`, `export_csv`, `export_michi_json`
- `export_portable_pack` — copia archivos + reporte HTML

### PlaylistAudit (`playlist_audit.py`)
- `audit_playlist(store, pid)` → `PlaylistHealthReport`
- Detecta: perdidos, duplicados, metadata incompleta, carátulas faltantes, baja calidad

### PlaylistRelinker (`playlist_relinker.py`)
- `find_candidates(lost_item, db_conn)` — busca reemplazos
- `auto_relink(store, pid, db_conn)` — repara automáticamente

### PlaylistOrdering (`playlist_ordering.py`)
- `order_by_title`, `order_by_artist`, `order_by_quality`, `order_by_bpm`
- `alternate_artists`, `random_weighted`

### SmartEngine (`playlist_smart_engine.py`)
- `evaluate_rules(rules_json, db_conn)` — evalúa reglas contra DB
- `refresh_smart_playlist(store, pid, db_conn)` — recalcula

### SyncManifest (`playlist_sync_manifest.py`)
- `build_manifest(store, db_conn)` → manifest completo
- `build_delta(store, db_conn, since)` → cambios incrementales

## DB Schema

Migraciones idempotentes en `library/schema.py` (versión 4).
Columnas agregadas: `updated_at`, `is_smart`, `rules_json`, `health_score`, etc.

## Tests

109 tests de playlist (34 legacy + 52 nuevos + 23 navegación).
