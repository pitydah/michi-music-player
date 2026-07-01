# Carpetas — Mantenimiento físico de la biblioteca musical

## Propósito

El apartado **Carpetas** responde a la pregunta:

> "¿Cómo está físicamente organizada mi música en el disco? ¿Qué carpetas están sanas, incompletas, no indexadas, corruptas, desordenadas, sin metadata, sin carátulas o con rutas rotas? ¿Qué acciones seguras puedo ejecutar sin romper la biblioteca?"

Es la sección definitiva de mantenimiento físico, complementaria a **Biblioteca** (que organiza por metadatos: artista, álbum, género).

## Diferencia con Biblioteca

| Biblioteca | Carpetas |
|---|---|
| Organiza por metadatos (artista, álbum, género) | Organiza por estructura física (árbol de directorios) |
| Muestra lo que la DB conoce | Muestra lo que realmente hay en disco |
| No revela archivos no indexados | Revela archivos no indexados, no soportados, auxiliares |
| No analiza salud de directorios | Analiza salud, integridad y consistencia |

## Escanear vs Reindexar vs Agregar a biblioteca

### Escanear
- **Qué hace**: Agrega archivos nuevos a la base de datos y actualiza metadatos de archivos modificados.
- **Cuándo usarlo**: Cuando agregaste archivos nuevos a una carpeta ya indexada.
- **Implementación**: Usa `Indexer.run()` con detección incremental de cambios (`ChangeDetector`).
- **Seguridad**: No borra datos de usuario (playlists, favoritos, historial).

### Reindexar
- **Qué hace**: Fuerza re-extracción de metadatos de todos los archivos bajo una carpeta, preservando play_count, rating, last_played y track_uid.
- **Cuándo usarlo**: Cuando corregiste metadatos con una herramienta externa (MusicBrainz Picard, MP3Tag, etc.) y quieres que la biblioteca refleje los cambios.
- **Implementación**: Usa el mismo pipeline de extracción que Indexer, pero actualiza registros existentes sin marcar como "nuevos".

### Agregar a biblioteca
- **Qué hace**: Registra una carpeta como raíz de biblioteca en `library_roots` y ejecuta un escaneo completo.
- **Cuándo usarlo**: Cuando tienes una carpeta con música que nunca fue indexada.
- **Nota**: Una carpeta fuera de la biblioteca muestra acciones "Escanear una vez" y "Agregar a biblioteca". Una vez agregada, muestra acciones completas de mantenimiento.

## Salud de carpeta (FolderHealthService)

Cada carpeta recibe un score de 0 a 100 basado en:

| Factor | Penalización máxima |
|---|---|
| No existe | Score = 0 |
| No legible | Score máximo 20 |
| Audios no indexados (índice < 50%) | -15 |
| Metadata incompleta | -15 |
| Sin carátula local (si tiene audios) | -8 |
| Formatos mezclados | -6 |
| Archivos no soportados | -8 |
| Rutas en DB que no existen en disco | -20 |
| Errores de permisos | -30 |

### Estados
- **Excelente** (90-100): Carpeta en perfecto estado.
- **Buena** (75-89): Algún detalle menor.
- **Atención** (55-74): Problemas que requieren revisión.
- **Advertencia** (30-54): Problemas significativos.
- **Crítica** (0-29): La carpeta no está disponible o tiene daños graves.

## Integridad (FolderIntegrityService)

### Verificación rápida
- Comprueba existencia, permisos, tamaño y fecha de modificación.
- Compara con registros de la DB.
- Detecta archivos no indexados.

### Verificación profunda
- Incluye todo lo de la verificación rápida.
- Intenta extraer metadatos con Mutagen.
- Si se solicita, calcula hash SHA-256 completo.

## Apertura en gestor de archivos

Carpetas detecta automáticamente el gestor de archivos preferido:

| Entorno | Gestor | Comando |
|---|---|---|
| KDE / Plasma | Dolphin | `dolphin <path>` / `dolphin --select <file>` |
| GNOME | Nautilus | `nautilus <path>` / `nautilus --select <file>` |
| Cinnamon | Nemo | `nemo <path>` |
| XFCE | Thunar | `thunar <path>` |
| LXQt | PCManFM-Qt | `pcmanfm-qt <path>` |
| Otro | Fallback | `xdg-open <path>` |

También disponible: "Abrir terminal aquí" (konsole, gnome-terminal, xfce4-terminal, kitty, alacritty).

## Mover/Renombrar seguro (SafeFileOperations)

### Preflight
Antes de cualquier movimiento, se genera un `FolderMovePlan` que verifica:

- [ ] Origen existe
- [ ] Destino no existe (o se reporta conflicto)
- [ ] Permisos de lectura/escritura
- [ ] Cantidad de archivos y carpetas
- [ ] Registros en DB afectados (media_items, playlists, favoritos, historial)
- [ ] Archivos sidecar (carátulas, .cue, .log, playlists)
- [ ] Mismo filesystem
- [ ] Si destino queda fuera de la raíz de biblioteca

### Ejecución
1. Mueve físicamente con `shutil.move`.
2. Actualiza todas las tablas de la DB: `media_items`, `playlist_items`, `play_history`, `favorites`, `queue_state`.
3. Reconstruye FTS.
4. Si la DB falla después del movimiento, intenta rollback automático.

### Limitaciones
- Solo intra-raíz de biblioteca.
- No cruza raíces de biblioteca (no mueve entre diferentes library_roots).
- No purga archivos si un disco está desmontado.

## Arquitectura

```
library/folder_models.py         → Dataclasses puras (sin Qt)
library/folder_index.py          → Listado y clasificación de entradas FS
library/folder_health.py         → Análisis de salud (FolderHealthService)
library/folder_integrity.py      → Verificación de integridad (FolderIntegrityService)
core/file_manager_service.py     → Detección de gestor de archivos
core/safe_file_ops.py            → Mover/renombrar seguro (SafeFileOperations)
ui/controllers/folder_controller.py → Orquestación (FolderController)
ui/folder_browser.py              → Widget visual (mantenido delgado)
ui/folders/folder_problem_report.py → Diálogo de reporte de problemas
```

## Operaciones destructivas

- **Ninguna operación destruye archivos físicamente.**
- `cleanup_missing_under_root()` hace soft-delete (marca `deleted_at`) — no borra filas.
- `purge_deleted()` solo se ejecuta si el usuario lo pide explícitamente.
- `remove_missing()` solo soft-deletea archivos bajo raíces activas que no existen en disco.
- Mover/renombrar seguro intenta rollback si la DB falla.

## Tests

| Archivo | Tests | Estado |
|---|---|---|
| `tests/test_folder_models.py` | 22 | ✅ |
| `tests/test_folder_index.py` | 22 | ✅ |
| `tests/test_folder_health.py` | 14 | ✅ |
| `tests/test_file_manager_service.py` | 24 | ✅ |
| `tests/test_folder_integrity.py` | 12 | ✅ |
| `tests/test_safe_file_ops.py` | 10 | ✅ |
| **Total** | **104** | ✅ |

## Riesgos restantes

1. **Symlinks**: No se siguen symlinks por defecto, pero un usuario que tenga symlinks dentro de su biblioteca podría ver carpetas duplicadas. No se implementó detección explícita de symlinks rotos.
2. **Archivos bloqueados**: En Windows/Linux, archivos abiertos por otro proceso pueden fallar en el probe de metadatos. Se manejan con try/except.
3. **CIFS/NFS montados**: Carpeta puede aparecer como "existente" pero no responder en operaciones de stat. `cleanup_missing_under_root` verifica `os.path.isdir()` antes de limpiar.
4. **Hash completo**: La verificación profunda con hash completo puede ser lenta en carpetas grandes (>10GB). Se recomienda usar solo en archivos individuales sospechosos.
