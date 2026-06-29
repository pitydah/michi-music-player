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
