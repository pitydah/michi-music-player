# ADR-004: DurableJobService como runtime único de jobs (recovery + cancelación scoped)

## Status

Accepted (Fase 2 de P0 stabilization — commit `1600f1f5`)

## Context

El runtime de jobs durables tenía dos defectos de recovery y dos de semántica:

- **Jobs zombies**: `core/jobs/job_service.py:146-151` restauraba jobs `RUNNING →
  INTERRUPTED` pero los dejaba AUSENTES de memoria (invisibles en `list_jobs`), y los
  `QUEUED` se re-enqueueaban pero NADIE llamaba a `process_queue` tras boot — el usuario
  acumuló 24+ jobs zombies (falso éxito #6).
- **Retry con semántica doble**: `ui_qml_bridge/job_bridge.py:184` (`retryJob`)
  reencolaba sin iniciar; `core/notification_action_service.py:90` sí hacía
  `start_job`/`process_queue`. Dos caminos, dos comportamientos (falso éxito #7).
- **Handlers sin contrato**: los jobs de library/doctor/metadata se cableaban con
  `container.get` dentro del handler (service locator), imposible de auditar estáticamente
  y con duplicación de autoridad (ver ADR-002).
- **Cancelación global**: `mix_bridge.cancel_all()` cancelaba jobs ajenos al dominio
  (falso éxito #1) porque no existía concepto de scope de cancelación.

Evidencia del baseline: log del usuario con 24+ jobs zombies; `audit_runtime_reachability.py`
y `audit_bridge_responsibilities.py` (variantes D/F) marcaban el service locator y
`cancel_all`.

## Decision

`DurableJobService` es la autoridad única de jobs durables (ADR-002). Su runtime define:

1. **Política de recovery en boot**:
   - `RUNNING → INTERRUPTED`, **visible** en `list_jobs`, con estado `retryable`
     (`test_restart_recovery_interrupts_running_and_reloads_queued`,
     `test_restart_running_job_interrupted_visible_retryable_and_starts`).
   - `QUEUED` → **auto-resume**: tras registrar handlers se llama a `process_queue`
     (`test_queued_job_auto_resumed_at_boot_after_handlers_registered`).
   - Sin handler registrado para un job pendiente → `HANDLER_UNAVAILABLE` **persistido**
     (no en memoria): el job queda visible y retryable con diagnóstico
     (`test_missing_handler_persisted_failure.py`).
2. **Retry unificado**: `JobBridge.retryJob` y `NotificationActionService.retry` delegan
   en un único `job_service.retry_job(...)` que re-ejecuta el payload original hasta el
   éxito (`test_retry_semantics_unified.py`).
3. **Cancelación scoped**: `cancel_owner(owner)` / `cancel_scope(scope)` reemplazan al
   `cancel_all` global no administrativo. La cancelación de un mix cancela **solo el job
   de mix** (owner `mix`, job id propio): `test_cancel_mix_does_not_cancel_scan.py` y
   `test_mix_cancel_only_cancels_mix_job_scan_keeps_running`.
4. **Handlers por ports**: los jobs reciben `LibraryScanPort` / `MetadataBatchPort` /
   `HistoryExportPort` / `DoctorRepairPort` / `DeviceSyncPort` / `AudioLabPort` — cero
   `container.get` en handlers (verificado por AST, 0 violaciones; `test_no_service_direct_subprocess_when_port_exists.py` y variante D de `audit_runtime_reachability.py`).
5. **Cancelación de terminal**: cancelar un job inexistente o terminal no produce éxito
   falso (`test_job_not_found_no_success.py`).

## Consequences

### Positive

- Los jobs interrumpidos son visibles y retryables tras un crash: el usuario ve qué
  quedó pendiente y puede re-lanzarlo con un solo camino (`retry_job`).
- Un solo método de retry en todo el producto: bridge QML y notificaciones comparten
  semántica (test `test_retry_semantics_unified`).
- La cancelación scoped elimina el efecto colateral de matar escaneos ajenos.
- Gates permanentes: `test_single_durable_job_authority.py`,
  `test_no_job_manager_parallel_repository.py`, `test_audio_lab_uses_durable_jobs.py`,
  `test_no_cancel_all_in_job_consumers_productive_code`.

### Negative

- El recovery es ahora observable: los jobs `INTERRUPTED` visibles pueden requerir
  acción del usuario (UX pendiente de pulir en el skin QML).
- `HANDLER_UNAVAILABLE` persistido introduce un estado nuevo que el skin debe renderizar
  (hoy solo lo expone el modelo).
- Los ports por dominio exigen mantener las interfaces de handlers sincronizadas con
  `DurableJobService`.

### Migration

- `device_sync` y `device_transfer` migraron a jobs durables owner `device:{id}` (F8).
- `mix_generate` migró a job durable owner `mix` (F6).
- `audio_lab` usa jobs durables vía port (F2).
- Los handlers legacy que usaban `container.get` fueron re-escritos con ports en
  `1600f1f5`; el auditor AST impide reintroducir el locator.

## Alternatives considered

- **Mantener el doble sistema (sync_service._jobs + DurableJobService)**: rechazado —
  divergencia ya observada; ADR-002 manda autoridad única.
- **Re-encolar QUEUED sin reprocesar (status quo corregido)**: rechazado — deja jobs
  colgados para siempre; el auto-resume es el comportamiento esperado.
- **`cancel_all` restringido por flags**: rechazado — un flag global en un bridge no
  escala a N dominios; `cancel_owner`/`cancel_scope` son explícitos y auditable.
- **Inyección de servicios en handlers sin ports (DI por nombre)**: rechazado — el AST no
  puede verificar nombres dinámicos; los ports dan contrato estático.
