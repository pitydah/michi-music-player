# Songs Premium — Biblioteca > Canciones

## Propósito

Convertir la sección `Biblioteca > Canciones` en un centro maestro de gestión musical:
tabla premium basada en `MediaItem`, filtros avanzados, estados visuales, selección múltiple,
acciones masivas y panel lateral informativo.

## Arquitectura

```
SongsPremiumPage (UI pasiva)
  ├── SongsFilterBar → emite SongsFilterState
  ├── MediaItemTableModel (QAbstractTableModel) basado en MediaItem
  ├── SongsBulkActionBar → emite señales sin payload
  └── SongsDetailPanel → emite señales con item

SongsController (coordinador)
  ├── SongsQueryService → consultas + filtros (sin UI)
  └── SongsStatusService → badges + favoritos (sin UI)

LibraryController → crea SongsController + SongsPremiumPage
SearchRouter      → usa SongsController si existe, fallback legado
ViewModeRouter    → list = premium, grid = SongGridWidget
```

## Flujo de datos

1. `LibraryController.show_library_hub()` crea `SongsController` + `SongsPremiumPage`.
2. `SongsController.load()` carga items desde la DB y calcula status badges.
3. `SongsPremiumPage.load_data()` pobla `MediaItemTableModel`.
4. El usuario filtra → `SongsFilterBar` emite `SongsFilterState`.
5. `SongsPremiumPage._on_filters_changed()` → `SongsController.apply_filter()`.
6. `SongsQueryService.filter()` aplica filtros en memoria.
7. `SongsPremiumPage.load_data()` refresca el modelo.
8. El usuario selecciona filas → bulk bar o panel lateral.
9. Acciones → `SongsController.play_items/queue_items/edit_metadata/etc`.

## Relación con LibraryController

- `LibraryController` crea `SongsController` y `SongsPremiumPage` una sola vez.
- No accede a internos privados (`_fav_ids`, `_quality_cache`).
- Pasa callbacks de metadata, locate y add_to_playlist.
- Refresca la vista premium cuando la biblioteca cambia (`refresh_songs()`).

## Relación con SearchRouter

- Si `_songs_ctrl` y `_songs_premium_page` existen, usa el flujo premium exclusivamente.
- No actualiza la tabla legado.
- Combina texto de búsqueda con filtros visuales activos.

## Relación con ViewModeRouter

- Modo list (index 0): `_refresh_songs_list()` usa `SongsController` si existe.
- Modo grid (index 1): `_show_song_grid()` con `SongGridWidget`.
- No llama `_apply_filters()` legado cuando premium está activo.

## Filtros soportados

| Filtro | UI | Backend |
|--------|----|---------|
| Formato | ComboBox | `ext` normalizado uppercase |
| Calidad | ComboBox (Hi-Res, Lossless, Lossy, DSD) | `_classify()` por ext + sample_rate + bit_depth |
| Género | ComboBox | `genre` lowercase/strip |
| Año min/max | QLineEdit | `year >= / <=` |
| Sample rate min | QLineEdit (kHz→Hz) | `sample_rate >=` |
| Bitrate min | QLineEdit (kbps) | `bitrate >=` (bps) |
| Favoritos | CheckBox | `item.filepath in fav_set` |
| Sin metadata | CheckBox | título/artista/álbum/género vacío |
| Sin carátula | CheckBox | `CoverArtService.find_cover()` con cache |
| Archivo perdido | CheckBox | `os.path.isfile()` |
| Audio Lab warning | CheckBox | `has_audio_lab_warning` booleano desde status cache |
| Búsqueda textual | SearchRouter | Combina con filtros visuales activos |

## Acciones masivas

1. Reproducir selección
2. Añadir a cola
3. Editar metadata
4. Agregar a playlist (diálogo: existente o nueva)
5. Marcar/desmarcar favorito
6. Analizar calidad (vía WorkerManager)
7. Localizar archivo (`xdg-open`)
8. Placeholder: Micro Server, Mobile Sync, conversión

## Estados visuales

- Hi-Res, Lossless, Lossy, DSD
- Favorito (★)
- Metadata incompleta
- Sin carátula
- Archivo perdido
- Audio Lab warning (espectral sospechoso)
- Calidad desconocida

## Columnas opcionales

Click derecho en el header de la tabla. Persiste en QSettings.

- Bitrate, Sample Rate, Bit Depth, Canales
- BPM, Tonalidad
- Reproducciones, Última reproducción, Rating
- Tamaño, Agregado, Último escaneo
- Track UID
- ReplayGain track, ReplayGain album

## Roles Qt (MediaItemTableModel)

| Rol | Valor |
|-----|-------|
| `Qt.UserRole` | `MediaItem` completo |
| `STATUS_ROLE` (User+10) | Dict con quality_label, badges, is_favorite, has_audio_lab_warning |
| `QUALITY_ROLE` (User+11) | String: hires, lossless, lossy, dsd, unknown |
| `FAVORITE_ROLE` (User+12) | bool |
| `FILEPATH_ROLE` (User+13) | String: filepath |

## Límites actuales

- `only_audio_lab_warning` requiere status cache precomputada (se hace en `load()`).
- `only_missing_cover` usa `CoverArtService.find_cover()` con caché interna para evitar repeticiones.
- No se analiza audio pesado durante filtrado.
- `only_missing_file` usa `os.path.isfile` (puede ser lento en monturas de red).

## Próximas integraciones

- Michi Micro Server (enviar canciones al servidor)
- Michi Mobile (sincronizar a móvil)
- Conversión de formato batch
- Fake Hi-Res avanzado (análisis espectral)
- Análisis batch profundo de Audio Lab
- Columnas configurables con UI completa de arrastrar/soltar
