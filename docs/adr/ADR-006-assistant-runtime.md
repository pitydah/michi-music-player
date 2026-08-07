# ADR-006: AssistantRuntime como pipeline única de Michi AI

## Status

Accepted (Fase 9 de P0 stabilization — commit `6fbf2f86`)

## Context

El dominio AI tenía múltiples pipelines de ejecución en paralelo:

- `MichiAIEngine` concentraba **415 líneas** con lógica de planificación, ejecución de
  tools y resolución de capacidades — duplicada del runtime de asistente existente, con
  criterios de habilitación distintos según el entry point (bridge QML vs servicio).
- El runtime de asistente **no estaba registrado en `ServiceContainer`**: se componía
  por demanda en el bridge, fuera de la composición canónica — invisible para los
  auditores de ciclo de vida (ADR-001) y sin `start()`/`shutdown()`.
- La resolución de capacidades dependía de un health-check genérico sin proveedor de
  salud real por servicio: una capability podía reportarse disponible con el backend
  caído.

Evidencia del baseline: `audit_runtime_reachability.py` (variante D) marcaba el
runtime fuera de composición; `audit_bridge_responsibilities.py` (variante B) marcaba la
construcción de servicios en bridges; `MichiAIEngine` de 415 líneas era el mayor
acumulador de lógica de dominio fuera de la autoridad (ADR-002).

## Decision

`AssistantRuntime` es la pipeline única de ejecución de Michi AI, y
`MichiAIEngine` pasa a ser un **facade fino**:

1. **Una sola generación activa**: toda solicitud del usuario (QML, API, jobs) pasa por
   `AssistantRuntime`; no existe un segundo planner/executor productivo
   (`test_assistant_runtime_single`).
2. **`MichiAIEngine` = facade de 50 líneas**: delega en el runtime; conserva firma
   pública para no romper callers, sin lógica de planificación propia.
3. **Capability = gateway + service + health + method + backend**: una capability solo se
   declara disponible si el gateway existe, el servicio está registrado, el health check
   del servicio (`health_provider`) responde, el método está cableado y el backend está
   vivo. `CapabilityResolver` con `health_provider` explícito
   (`test_capabilities_require_healthy_handlers.py`).
4. **Composición completa registrada**: `assistant_runtime` se registra en
   `SERVICE_MANIFEST` y `michi_ai_service` declara su dependencia — ciclo de vida
   gestionado por el container (ADR-001), sin construcción en bridges
   (`test_runtime_registered_full` en `tests/integration/test_assistant_runtime_vertical.py`).
5. **Diez interfaces explícitas** entre el runtime y el mundo exterior (gateway,
   resolver de capacidades, history, etc.): el runtime consume contratos, no locator.

## Consequences

### Positive

- Un solo lugar donde se decide qué puede hacer el asistente y cómo se ejecuta: el
  comportamiento es idéntico desde QML, API y tests verticales.
- La composición del dominio AI es auditable por los mismos gates que el resto del
  container (registrado, iniciado, apagado una vez).
- La truthful-ness de capacidades mejora: el health check real del servicio alimenta la
  disponibilidad, no una suposición.
- `MichiAIEngine` de 415 → 50 líneas: la lógica de negocio migró a su autoridad
  (ADR-002).

### Negative

- El facade retiene superficie pública (compatibilidad de firmas) — riesgo de que crezca
  de nuevo si se le agregan wrappers sin migrar la lógica.
- La resolución de capacidades con health check añade latencia al priming de la UI
  (mitigada cacheando el resolver).

### Migration

- `MichiAIEngine` re-escrito como facade en `6fbf2f86`; sus tests actualizados apuntan
  al runtime como autoridad.
- `assistant_runtime` agregado a `SERVICE_MANIFEST`; `michi_ai_service` declara
  dependencia explícita.
- Los callers que componían el runtime por demanda (bridges) pasan a recibirlo del
  container vía `ServiceContainer`.

## Alternatives considered

- **Conservar `MichiAIEngine` como autoridad y eliminar el runtime**: rechazado — el
  runtime ya era el pipeline real en producción; el engine duplicaba el trabajo.
- **Dos pipelines según entry point (bridge vs service)**: rechazado — reproduce el
  estado previo con comportamiento divergente según la puerta de entrada.
- **Capability sin health check (estática por registro)**: rechazado — reportaba
  capacidades con backend caído; el `health_provider` es el dato honesto.
