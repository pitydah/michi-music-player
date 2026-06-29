# Michi Music Player — Context System

## Objetivo
El sistema de contexto permite que Inicio, Assistant, Mix y vistas inteligentes conozcan el estado actual de la app sin acoplarse directamente a la UI ni consultar SQLite desde widgets.

## Principios
- `ContextService` es la fachada pública.
- La UI no accede a `context_repository` directamente.
- Los snapshots son pequeños.
- No se guardan filepaths en Assistant snapshot.
- No se guardan rutas absolutas.
- Sync queda fuera de esta fase.
- Los eventos deben ser semánticamente correctos.

## Arquitectura

```
core/context/
├── context_events.py        # 45+ constantes de eventos AppEvent.*
├── context_repository.py    # SQLite WAL (context.sqlite), 4 tablas
├── context_invalidator.py   # Mapa evento → dirty flags
├── context_snapshot.py      # Builders de snapshots + sanitize
└── context_service.py       # Fachada pública ContextService
```

## Selection Contract

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `selection_scope` | str | track, album, artist, genre, playlist, folder, mix, search |
| `album` | str | Álbum seleccionado |
| `artist` | str | Artista seleccionado |
| `genre` | str | Género seleccionado |
| `track` | str | Título de pista seleccionada |
| `playlist_id` | int | ID de playlist |
| `playlist_name` | str | Nombre de playlist |
| `folder_name` | str | Solo basename, no path completo |
| `mix_key` | str | mix_daily, mix_unplayed, favs, recent, etc |
| `search_query` | str | Truncado a 80 caracteres |

## Reglas de seguridad
- No guardar filepaths ni rutas absolutas en snapshots.
- `sanitize_snapshot()` filtra `filepath`, `filepaths`, `path`, `paths`, `uri`.
- Strings largos truncados a 300 caracteres.
- Listas limitadas a 10 elementos.
- Assistant snapshot pasa por `sanitize_snapshot()`.

## Tablas de tracks y selección
Todas las tablas de `TrackRef` (canciones) reconectan la señal `selectionModel().currentChanged`
mediante `PlaybackController.attach_track_table(table, model)`. Esto garantiza que:

- Al hacer click en una fila se actualiza `selection.scope == "track"` sin reproducir.
- La conexión no interfiere con otros listeners (`disconnect` dirigido solo a `_on_table_selection`).
- `setModel` y reconexión ocurren en un solo método.

Ver `core/playback_controller.py:attach_track_table()` y `connect_table_selection()`.

## Search semantics
- `SEARCH_PERFORMED`: solo con conteo real de resultados.
- `SEARCH_STARTED`: búsqueda activa sin conteo confiable.
- `SEARCH_CLEARED`: query vacía.
- No se inventan conteos falsos.

## Assistant snapshot safety
- El snapshot final se sanitiza en `ContextService.get_assistant_snapshot()`.
- No se permiten `filepath`, `uri`, `path` ni rutas absolutas (Linux o Windows).
- `assistant_capabilities` refleja el tipo de selección (contrato explícito):

| Scope | can_search_library | can_create_playlist | can_queue | can_edit_metadata | can_analyze |
|-------|:---:|:---:|:---:|:---:|:---:|
| `None` | ✓ | ✗ | ✗ | ✗ | ✗ |
| `track` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `album` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `artist` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `genre` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `playlist` | ✓ | ✓ | ✓ | ✗ | ✓ |
| `mix` | ✓ | ✓ | ✓ | ✗ | ✓ |
| `folder` | ✓ | ✓ | ✓ | ✗ | ✗ |
| `search` | ✓ | ✓ | ✓ | ✗ | ✓ |

## Proxy / Source model selection
Cuando la selección de tabla proviene de un `QSortFilterProxyModel` o similar con `mapToSource()`,
`_on_table_selection()` resuelve la fila real mediante:
1. `current.model()` → si tiene `get_trackref()`, usa `current.row()`.
2. `model.sourceModel()` + `model.mapToSource(current)` → fila del source model.
3. Registry `_track_table_models` → modelo registrado por `attach_track_table()`.
4. Fallback global `self._win._ctx.model`.

Ver `core/playback_controller.py:_resolve_track_model_and_row()`.

## detach_track_table
`PlaybackController.detach_track_table(table)` elimina una tabla del registry interno
`_track_table_models` y limpia `_active_context_table`. Útil cuando una tabla de tracks
deja de representar datos de `TrackRef`.

## Event semantics
| Evento | Significado |
|--------|-------------|
| `TRACK_SELECTED` | Selección de pista individual |
| `SELECTION_CHANGED` | Selección no-track (album, artist, genre, playlist, folder, mix, search) |
| `TRACK_PLAYED` | Reproducción real iniciada |
| `QUALITY_UPDATED` | Cambio de calidad de audio |
| `PLAYBACK_STOPPED` | Stop/reset de reproducción |
| `METADATA_SAVED` | Metadatos guardados |
| `SCAN_FINISHED` | Escaneo real de biblioteca |
| `LIBRARY_RELOADED` | Recarga genérica de biblioteca |
| `IMPORT_FINISHED` | Importación de archivos |
| `PLAYLIST_CREATED` / `PLAYLIST_DELETED` / `PLAYLIST_PLAYED` / `PLAYLIST_QUEUED` / `PLAYLIST_IMPORTED` / `PLAYLIST_EXPORTED` | Acciones sobre playlists (sin filepaths en payload) |
| `MIX_OPENED` | Vista de mix, favoritos o recientes |
| `FOLDER_SELECTED` / `FOLDER_SCANNED` / `FOLDER_QUEUED` | Acciones sobre carpetas (solo basename) |
| `SEARCH_PERFORMED` / `SEARCH_STARTED` / `SEARCH_CLEARED` | Búsqueda (conteo real solo en PERFORMED) |
| `ASSISTANT_OPENED` / `ASSISTANT_ACTION_CONFIRMED` | Uso del asistente |
