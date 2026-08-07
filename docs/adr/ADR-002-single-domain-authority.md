# ADR-002: Autoridad única por dominio (Single Domain Authority)

## Status

Accepted (P0 stabilization — fases F2, F6, F8, F9, F10)

## Context

El baseline confirmó múltiples autoridades paralelas para un mismo dominio, cada una con
su propia copia de estado y su propia semántica:

- **Jobs**: `core/device_sync_service.py:14,155,158,226,274,457` mantenía su propio
  `threading.Lock` + dict `_jobs` paralelo al `DurableJobService` (falso éxito #8) —
  cancelación, retry y persistencia divergentes entre sistemas.
- **Mix**: `ui_qml_bridge/mix_bridge.py:369-439` duplicaba el dispatch de estrategias y el
  estado de negocio del servicio (falso éxito #2), y `cancel_all()` global cancelaba jobs
  ajenos al dominio (falso éxito #1).
- **AI**: `MichiAIEngine` concentraba 415 líneas con lógica de planificación/ejecución
  duplicada del runtime, sin estar registrado como servicio en el container.
- **Ecosistema**: múltiples event buses y registries de dispositivos convivían
  (`LyricEventBus`, radio EventBus, `DeviceRegistry` propio de mobile sync) en paralelo al
  `event_bus` canónico (F10).
- **Settings**: `settings_service` ↔ `settings_coordinator` con ciclo de dependencia
  (falso éxito #11).

Evidencia: `audit_service_duplicates.py` (F11, variante C) — 2 instancias compartidas
encontradas, ambas declaradas `alias_of`; `test_single_authority_per_domain` y
`test_no_duplicate_service_class_names` como gates.

## Decision

Cada dominio funcional tiene **exactamente una autoridad**: la clase que posee el estado
y las reglas de negocio. Todo el resto es consumidor o adaptador fino:

1. **Autoridad canónica por dominio**, con gates por dominio: `DurableJobService`
   (jobs), `DeviceSyncService` (sync de dispositivos), `PlaybackController`/`PlayerService`
   (playback), `radio` adapter, `lyrics`, `theme`, `michi_link`, `metadata_editor_service`.
2. **Legado = adaptador fino sobre la autoridad, o `LEGACY_OPERATION_DISABLED`**: si una
   API histórica no puede delegar con seguridad, se deshabilita explícitamente (ver
   ADR-003) — nunca se mantiene una segunda implementación viva.
3. **Los bridges no construyen ni despachan negocio** (ADR-003 del wave anterior,
   `ADR-thin-qml-bridges.md`): `MixBridge` quedó en ~fino (estados 1:1 a QML, delega en
   `mix_generate` durable), `DeviceSyncService` quedó como facade sin threads ni `_jobs`.
4. **Un solo bus / un solo registry**: `LyricEventBus` y el radio EventBus son wrappers
   finos sobre `event_bus` canónico; `DeviceRegistry` único compartido
   (`test_single_event_bus_and_registry`).
5. **Migración de dependencias a ports**: los handlers de jobs reciben
   `LibraryScanPort` / `MetadataBatchPort` / `HistoryExportPort` / `DoctorRepairPort` /
   `DeviceSyncPort` / `AudioLabPort` (F2); `FileManagerService` expone port (F10).

## Consequences

### Positive

- Una sola copia de estado por dominio: la cancelación, el retry y la persistencia
  coinciden en todos los puntos de entrada.
- Los gates `test_single_authority_per_domain.py`, `test_single_durable_job_authority.py`,
  `test_device_sync_single_authority.py`, `test_radio_single_authority.py`,
  `test_lyrics_single_authority.py`, `test_theme_single_authority.py`,
  `test_michi_link_single_authority.py` y `test_no_orphan_productive_service.py` hacen
  que una segunda autoridad futura falle en CI.
- El AST (`audit_bridge_responsibilities.py`, variantes B/E) verifica 0 construcción de
  servicios en bridges (52 documentadas) y 0 estado paralelo (5 allowlist).

### Negative

- Los facades (ej. `DeviceSyncService`) obligan a tocar la pipeline interna
  (`core/device_sync/`) para cualquier cambio de comportamiento — la autoridad está en la
  pipeline, el facade es el punto de entrada.
- Los wrappers finos de buses agregan una capa de indirección que requiere consistencia
  de firma con `event_bus`.

### Migration

- `MichiAIEngine`: 415 → 50 líneas de facade sobre `AssistantRuntime` (F9).
- `device_sync_service`: `_jobs` propio eliminado; transfers migrados a jobs durables
  `device_sync`/`device_transfer` con owner `device:{id}` (F8).
- `mix_bridge`: dispatch eliminado; `mix_generate` durable con owner `mix` (F6).
- Historial legacy de sync migrado a `core/device_sync/history.py` (migración DB 10).

## Alternatives considered

- **Mantener servicios paralelos pero sincronizarlos**: rechazado — es el estado previo,
  con divergencias ya observadas (24+ jobs zombies, retry con semántica distinta).
- **Composición por agregación sin facade**: rechazado — los callers del ecosistema
  (bridges QML, Notifications, Sync) necesitan una superficie estable, no la pipeline
  interna.
- **Eliminar las APIs legacy**: rechazado — rompe callers documentados (QML skin,
  e2e); se prefiere delegación o deshabilitación explícita con `LEGACY_OPERATION_DISABLED`.
