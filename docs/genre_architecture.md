# Arquitectura del Módulo Géneros

## Visión General

El módulo Géneros transforma la sección de géneros de una simple lista de etiquetas
en un centro de curaduría musical por estilos. Soporta exploración visual,
normalización, limpieza, descubrimiento y generación inteligente de mixes.

## Capas

### 1. Metadata / Lógica Pura (`metadata/`)

- **`genre_normalizer.py`** — Normalización, splitting, detección de basura,
  alias, duplicados. Funciones puras sin dependencias.
- **`genre_taxonomy.py`** — 15 familias taxonómicas, mood hints.
- **`genre_grouping.py`** — `GenreGroup` dataclass, `build_genre_groups()`.

### 2. Base de Datos (`library/`)

- **`genre_repository.py`** — `GenreRepository` con operaciones CRUD sobre
  `track_genres`, `genre_aliases`, `genre_stats_cache`, `genre_cleanup_suggestions`,
  `genre_operation_log`. Accede via `LibraryDB._conn`.
- **`schema.py`** — Define las 5 nuevas tablas de género y sus índices.
  Las migraciones son automáticas via `ALTER TABLE ADD COLUMN` (idempotente).

### 3. Servicios de Aplicación (`core/genre/`)

- **`genre_stats_service.py`** — `GenreStatsService`: estadísticas agregadas,
  health summary, tracks sin género, caché con TTL de 5 minutos.
- **`genre_cleanup_service.py`** — `GenreCleanupService`: detección de duplicados,
  basura, raros, sin género, álbumes inconsistentes, artistas inconsistentes.
  Generación y ejecución de sugerencias.
- **`genre_mix_service.py`** — `GenreMixService`: creación de mixes (all,
  favorites, unplayed, high_quality, discovery, artist_variety), radio local,
  playlist inteligente con reglas (año, calidad, formato, favoritos).

### 4. UI (`ui/genres/`)

- **`genre_hub_page.py`** — Página principal con health summary, búsqueda,
  filtros, tarjetas de género.
- **`genre_detail_page.py`** — Vista detalle con hero, acciones, tabs de
  canciones y estadísticas.
- **`genre_cleanup_page.py`** — Panel de limpieza con secciones para
  duplicados, basura, raros, sin género, separadores múltiples.
- **`genre_card.py`** — Tarjeta premium con health badge.
- **`genre_empty_states.py`** — Estados vacíos y errores.
- **`genre_stats_panel.py`** — Panel de estadísticas detalladas.
- **`genre_actions_panel.py`** — Panel de acciones rápidas.

### 5. Controladores (`ui/controllers/`)

- **`genre_controller.py`** — Orquesta navegación, reproducción, mix, radio,
  playlist, limpieza. Conecta UI con servicios.
- **`genre_cleanup_controller.py`** — Orquesta detección y ejecución de limpieza.

## Tablas Nuevas

### `track_genres`
Relación muchos-a-muchos entre tracks y géneros normalizados.

### `genre_aliases`
Mapeo de variantes a géneros canónicos. Soportado por alias builtin y de usuario.

### `genre_stats_cache`
Caché de estadísticas por género para UI rápida. Se invalida al cambiar la biblioteca.

### `genre_cleanup_suggestions`
Sugerencias generadas por `GenreCleanupService` con estados: pending/accepted/rejected.

### `genre_operation_log`
Historial de operaciones de limpieza para posible rollback.

## Normalización

El normalizador (`metadata/genre_normalizer.py`) maneja:

1. **Alias** — 150+ mapeos builtin (hiphop→Hip-Hop, rnb→R&B, clasica→Música Clásica)
2. **Géneros compuestos** — 80+ entradas que no deben separarse (R&B, Drum & Bass)
3. **Géneros basura** — 30+ valores a detectar (unknown, other, misc, none)
4. **Separadores** — `, ; / | & +` con preservación de compuestos
5. **Unicode** — Normalización NFKC
6. **Mayúsculas** — Title case con preservación de palabras especiales

## Flujo de Limpieza

1. Usuario abre "Limpiar géneros"
2. `GenreCleanupController.scan_and_show()` ejecuta detección
3. UI muestra secciones con sugerencias
4. Usuario revisa y acepta/rechaza
5. `GenreCleanupService.execute_*()` aplica cambios en DB
6. `GenreOperationLog` registra para posible rollback

## Integraciones

- **Audio Lab**: Tarjeta "Limpieza de géneros" en AudioLabHub
- **Michi Assistant**: Contexto de género via `ContextService.update_selection(scope="genre")`
- **Michi Link**: Preparado para enviar playlists/mixes por género

## Tests

- `test_genre_normalizer.py` — 35+ tests de normalización, splitting, alias
- `test_genre_repository_db.py` — 18+ tests de CRUD, merge, stats, sugerencias
- `test_genre_cleanup_service.py` — 20+ tests de detección y ejecución
- `test_genre_mix_service.py` — 20+ tests de mix, radio, smart playlist
- `test_genre_ui_smoke.py` — 25+ tests de UI (instantiation, signals)
- `test_genre_controller.py` — Tests existentes (13) + expansión

## Límites Conocidos

1. **Escritura en tags**: Solo DB por defecto. Escribir en archivos físicos requiere
   confirmación explícita y no está implementado en esta iteración.
2. **Rollback**: El `genre_operation_log` registra operaciones pero no implementa
   rollback automático. Puede usarse para revertir manualmente.
3. **Radio local**: La radio es una cola generada, no streaming continuo. No tiene
   "más como esto" / "menos como esto".
4. **Playlist inteligente**: Las reglas se aplican una vez al crear la playlist.
   No hay actualización dinámica.
5. **Relaciones por coocurrencia**: `GenreMixService.get_related_genres()` usa
   coocurrencia simple en track_genres, no análisis avanzado.
