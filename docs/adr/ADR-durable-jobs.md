# ADR-004: DurableJobService como autoridad única de jobs

## Status

Accepted

## Context

Existen **cuatro** sistemas de jobs paralelos, con vocabularios y semánticas distintas:

1. **`DurableJobService`** (`core/jobs/job_service.py`): jobs persistidos en la base de datos, con estado durable, pero **sin handlers registrados** y **ejecución síncrona** sobre el thread del caller.
2. **`JobBridge`** (`ui_qml_bridge/job_bridge.py`): registro en memoria; es el **camino de producción real** para los escaneos de biblioteca.
3. **`JobManager`** (`core/jobs/job_manager.py`): repositorio propio sin DI, huérfano del container.
4. **`AudioLabJobAdapter`** (`core/audio_lab/audio_lab_job_adapter.py`): huérfano, sin cablear.

Consecuencias:

- La persistencia (DurableJobService) y la ejecución real (JobBridge en memoria) están separadas: un job "durable" no corre, y un job que corre no se persiste.
- No existe un vocabulario único: `job_id`, `kind`, `status` tienen significados y nombres distintos según el sistema.
- La ejecución síncrona en el thread del caller bloquea la UI (el caso de escaneos largos) o fuerza hacks como `QTimer.singleShot(0)` pseudo-async en otros puntos.
- `JobManager` y `AudioLabJobAdapter` son código muerto que confunde el inventario: parecen productivos y no lo son.

## Decision

`DurableJobService` es la **única autoridad de jobs durables** de la aplicación. El resto de sistemas migran o se marcan legacy (ADR-002).

Capacidades que adquiere `DurableJobService`:

- **Ejecución asíncrona real**: los jobs corren vía `WorkerManager` (QThread/ThreadPoolExecutor), nunca en el thread del caller. Un job aceptado devuelve de inmediato con estado `QUEUED`/`RUNNING`; la UI no se bloquea.
- **Handlers registrados por job kind**: `library_scan`, `library_scan_all`, `metadata_scan`, `doctor_scan`, `history_export`, operaciones de audio lab. El registro es explícito: no existe ningún kind sin handler declarado.
- **Restart recovery**: al arrancar, los jobs `RUNNING` huérfanos (proceso anterior) pasan a `INTERRUPTED` y los `QUEUED` se re-encolan. El estado durable se respeta tras reinicios.
- **Cancelación cooperativa real**: un job expone un mecanismo de cancelación (flag/evento consultado en puntos de cooperación del handler); cancelar no es matar el thread.
- **Un solo vocabulario**: `job_id`, `kind`, `status` se definen una vez y se usan en todos los consumidores (bridges, controllers, UI). No existen nombres paralelos.

Roles resultantes:

- `JobBridge` pasa a ser **una vista fina** (según ADR-003): expone estado y operaciones del `DurableJobService` sin registro propio ni lógica de scheduling.
- `JobManager` y `AudioLabJobAdapter` migran sus capacidades al servicio durable (si aportan algo real) o se marcan `LEGACY`/se eliminan.

## Consequences

### Positive

- Persistencia y ejecución quedan unidas: un job durable realmente corre, y un job que corre se puede recuperar tras reinicio.
- Se elimina el bloqueo del thread de UI en escaneos largos.
- El inventario de jobs se vuelve verificable: kinds con handler, handlers con tests, cero sistemas paralelos.
- `QTimer.singleShot(0)` y otros pseudo-async pueden retirarse en los caminos de jobs.

### Negative

- Introducir `WorkerManager` en `DurableJobService` agrega complejidad de threading (lifetime de workers, shutdown ordenado, errores en thread).
- La migración de `JobBridge` toca el camino de producción de escaneos: hay que congelar el comportamiento actual con tests antes de conmutar.
- Los jobs síncronos existentes (si algunos dependen del resultado en el caller) requieren re-diseñar la espera: progreso por estado + señal, no retorno síncrono.

### Migration

1. Registrar los kinds actuales que `JobBridge` ya maneja (escaneos) como handlers de `DurableJobService`, con tests que verifiquen ejecución asíncrona (el handler corre en otro thread).
2. Añadir recovery de `RUNNING`→`INTERRUPTED` y re-queue de `QUEUED` al arranque del servicio, con test de reinicio simulado.
3. Implementar cancelación cooperativa y exponerla en el vocabulario único de estados.
4. Migrar `JobBridge` a vista fina; evaluar `JobManager`/`AudioLabJobAdapter` y marcarlos `LEGACY` o eliminarlos.

## Alternatives considered

- **Dejar JobBridge como producción y usar DurableJobService solo para persistencia.** Rechazada: perpetúa la separación persistencia/ejecución y mantiene dos vocabularios.
- **Consolidar todo en JobManager (el más simple, sin DI).** Rechazada: no tiene persistencia ni está cableado; DurableJobService ya tiene el modelo de datos durable que la aplicación necesita.
- **Scheduler global tipo APScheduler/celery.** Rechazada: dependencia externa pesada para un modelo de jobs ya definido; el costo de infraestructura no se justifica.
