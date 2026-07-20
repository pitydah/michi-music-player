# Biblioteca V2 — arquitectura consolidada

## 1. Objetivo

La Biblioteca V2 establece una sola ruta funcional entre indexación, catálogo SQLite, modelos QML y presentación. Su finalidad es evitar que cada vista implemente filtros, agrupaciones, identidad de álbum o acceso a carátulas por separado.

```text
Archivos de audio
    ↓
MetadataExtractor
    ↓
MetadataNormalizer / enrich_index_record
    ↓
BatchWriter
    ↓
media_items + album_art_cache + FTS5
    ↓
LibraryFilteredQueryService
    ↓
TrackListModel / AlbumListModel / ArtistListModel
    ↓
LibraryPage / AlbumViewHost
```

## 2. Superficie QML canónica

### Biblioteca principal

`LibraryPage.qml` es el contenedor canónico para Canciones, Álbumes, Artistas y Carpetas. La pestaña Álbumes utiliza `AlbumViewHost.qml` y comparte el mismo `AlbumListModel` entre las cinco presentaciones:

1. Grid
2. CoverFlow
3. Vinyl Wall
4. Timeline
5. Magazine

Cambiar de vista no vuelve a consultar la base ni duplica modelos.

### Ruta de compatibilidad

`library.albums` continúa resolviendo `AlbumGridPage.qml`, pero esa página ya no mantiene un selector o implementación propios. Es un adaptador delgado hacia `AlbumViewHost`, por lo que ambas entradas ofrecen exactamente las mismas cinco vistas y acciones.

### CoverFlow

El CoverFlow QML usa `PathView` como único renderer. La geometría se limita a cinco elementos en ventanas normales y siete en ventanas amplias. Se eliminó la pseudo-reflexión rectangular, se estabilizó el orden Z y se añadieron controles de teclado portables.

### Carátulas

`CoverImage.qml` consume `coverProviderBridge`. El bridge:

- consulta primero un servicio de carátulas inyectado cuando existe;
- usa `album_art_cache` como fallback canónico;
- abre SQLite en modo solo lectura;
- valida MIME y tamaño máximo;
- devuelve data URLs compatibles con `Image`;
- mantiene una caché LRU acotada, incluyendo misses.

## 3. Identidad y metadatos

### Campos de presentación

`title`, `artist`, `album`, `albumartist` y `genre` conservan mayúsculas, acentos y grafía humana.

### Campos normalizados

Las columnas siguientes son claves técnicas, no valores visibles:

- `normalized_title`
- `normalized_artist`
- `normalized_album`
- `normalized_albumartist`

Se generan mediante Unicode NFKD, eliminación de marcas diacríticas, `casefold` y normalización de puntuación. Permiten búsqueda, agrupación y ordenación coherentes sin alterar el texto mostrado.

### Identidad estable

`album_key` se calcula una vez en la frontera de escritura cuando el extractor no lo entrega. `track_uid` continúa siendo la identidad estable de pista y `filepath` la identidad física.

### Proveniencia y calidad

Cada fila incorpora:

- `metadata_source`: origen estimado de la información;
- `metadata_confidence`: confianza normalizada entre 0 y 1;
- `metadata_completeness`: puntuación 0–100;
- `metadata_issues`: códigos JSON de campos ausentes o inválidos;
- `metadata_hash`: SHA-256 de los metadatos semánticos.

El hash excluye ruta, timestamps y atributos físicos para detectar cambios reales de tags.

### Normalización soportada

- Unicode NFC y eliminación de caracteres de control;
- géneros múltiples separados por `;`, `|` o NUL;
- fechas completas reducidas a año validado;
- posiciones `track/total` y `disc/total`;
- BPM numérico;
- ISRC normalizado;
- UUID MusicBrainz validados;
- valores multi-tag convertidos de forma determinista.

## 4. Escritura y preservación de estado

`BatchWriter` es la única frontera de persistencia del indexador. Antes de almacenar una fila:

1. normaliza campos visibles;
2. crea claves de búsqueda;
3. calcula identidad de álbum;
4. evalúa calidad y proveniencia;
5. calcula el hash semántico;
6. ejecuta el upsert transaccional.

Los upserts de metadatos no reemplazan datos propiedad del usuario:

- `rating`
- `play_count`
- `last_played`

También reactivan filas encontradas nuevamente mediante `deleted_at=NULL` y `scan_status='ok'`.

## 5. Esquema SQL e índices

La migración 6 añade las columnas normalizadas y de diagnóstico. Las migraciones son transaccionales, idempotentes y toleran columnas incorporadas previamente por backports.

Índices parciales para contenido activo:

- `idx_media_active_norm_title`
- `idx_media_active_norm_artist_album`
- `idx_media_active_album_tracks`
- `idx_media_active_year_album`
- `idx_media_active_directory`
- `idx_media_active_format`
- `idx_media_active_last_played`
- `idx_media_metadata_health`
- `idx_play_history_track_time`

Los índices parciales excluyen filas con `deleted_at`, reduciendo tamaño y costo de lectura.

## 6. Contrato de consultas

`LibraryFilteredQueryService` es el contrato único de filtros QML. Conteo y página usan el mismo constructor de predicados, evitando discrepancias de paginación.

Características:

- FTS5 cuando está disponible;
- fallback LIKE escapado sobre claves normalizadas;
- búsqueda sin sensibilidad a acentos o mayúsculas;
- filtros por artista, álbum, género, compositor, formato, carpeta, año y calidad;
- favoritos por `filepath`, `id` o `track_uid`;
- filtros de no reproducidas, faltantes y salud mínima de metadatos;
- orden estable con desempate por clave normalizada e `id`;
- agrupación normalizada de álbumes y artistas;
- límites de carpetas que no confunden `/Rock` con `/Rockabilly`;
- historial reciente basado en el esquema real `media_items + play_history`.

## 7. Compatibilidad y backfill

Al abrir una biblioteca existente:

1. se aplican las migraciones pendientes;
2. se preservan columnas ya presentes;
3. se copian contadores legacy cuando corresponde;
4. se rellenan claves normalizadas y hashes en lotes;
5. la segunda inicialización es un no-op seguro.

El backfill detecta las columnas disponibles en cada esquema histórico y usa valores neutros para campos todavía ausentes.

## 8. Presupuestos de rendimiento

Objetivos para una biblioteca local grande:

- ningún cambio de vista debe ejecutar una nueva consulta;
- paginación por cursor lógico `LIMIT/OFFSET` con orden determinista;
- consultas de conteo y página deben compartir filtros;
- las carátulas nunca deben decodificarse dentro de `paint()` ni bloquear el renderer;
- cachés de carátulas deben tener tamaño máximo explícito;
- los backfills deben procesarse en lotes;
- los índices deben favorecer contenido activo y no inflar filas eliminadas.

## 9. Validación

El workflow `Library Data Validation` comprueba:

- Ruff en la superficie modificada;
- compilación Python;
- migraciones vacías, repetidas y desde esquemas previos;
- normalización y diagnóstico de metadatos;
- persistencia de `album_key` y preservación de estado de usuario;
- filtros, ordenación, agregados e historial;
- proveedor de carátulas y caché;
- compilación e instanciación QML;
- geometría de CoverFlow y unificación de rutas.

## 10. Evolución posterior

Las siguientes mejoras deben construirse sobre este contrato, no en paralelo:

- paginación keyset para bibliotecas de millones de pistas;
- materialización incremental de agregados de álbum/artista;
- editor visual de incidencias `metadata_issues`;
- reparación asistida por MusicBrainz con diff previo;
- thumbnails persistentes por tamaño;
- `EXPLAIN QUERY PLAN` automatizado en benchmarks;
- vacuum/analyze programado según crecimiento real del catálogo.
