# ADR-001: Service Manifest como única fuente de verdad del ciclo de vida

## Status

Accepted (Fase 1 de P0 stabilization — commit `670d0857`)

## Context

`ServiceContainer` (`core/service_container.py`) es el punto único de composición de la
aplicación: registra todos los servicios productivos vía los composition builders de
`core/composition/*.py`. Sin embargo, el ciclo de vida estaba partido en dos verdades:

- **Segundo inventario**: `BUILTIN_DEPENDENCIES` más las listas históricas
  `_required_names` / `_optional_names` / `_capability_gated_names` / `_deferred_*`
  (baseline falso éxito #10, `core/service_container.py:47,128,146,155,159`). La manifest
  no era la única fuente de verdad: un servicio olvidado en las listas se registraba en
  silencio y nunca recibía `start()`, sin que nada fallara en importación.
- **Segundo grafo**: las dependencias se resolvían por convención de orden en los
  builders, no por declaración. `core/dependency_graph.py` quedó huérfano — evidencia de
  que la necesidad de un grafo real se sintió y no se resolvió.
- **Ciclo de dependencia circular** entre `core/settings_service.py` y
  `settings_coordinator` (baseline falso éxito #11), que no se detectaba en boot y
  degradaba el bootstrap en runtime.

Evidencia del baseline (SHA `66245d11`): `audit_runtime_reachability.py` reportaba
80 descriptores en `SERVICE_MANIFEST` (`core/service_manifest.py`) pero el boot afirmaba
"80 services" sin garantía de que el ciclo de vida coincidiera con el inventario.

## Decision

El ciclo de vida del `ServiceContainer` se deriva **exclusivamente** de `SERVICE_MANIFEST`:

1. **Un solo inventario**: se eliminan `BUILTIN_DEPENDENCIES` y todas las listas
   históricas de `service_container.py`. `start()` y `shutdown()` recorren únicamente la
   manifest.
2. **`alias_of`**: un descriptor puede declarar `alias_of="<canonical>"` para claves
   equivalentes sin duplicar ciclo de vida. Registrados: `connection_factory → database`
   y `library_filtered_query_service → library_query_service`. El alias se inicia/cierra
   una sola vez (`test_alias_single_start_shutdown`).
3. **Fallo rápido ante ciclos**: si la resolución de dependencias encuentra un ciclo, la
   composición aborta con `ManifestCycleError` al importar (no en runtime).
   `test_manifest_cycle_detected` lo verifica; `test_manifest_missing_dependency_rejected`
   cubre dependencias inexistentes.
4. **Resolución del ciclo settings**: se elimina el coordinador paralelo; el servicio de
   settings queda como autoridad única de su dominio (`test_settings_cycle_resolved`).
5. **Auditoría permanente**: `audit_runtime_reachability.py` verifica que todo descriptor
   esté registrado y que no exista construcción de servicios fuera de composición
   (probes documentados en la allowlist).

## Consequences

### Positive

- Una sola fuente de verdad: el grafo de arranque es declarativo y verificable por AST.
- Fallo rápido en importación ante ciclos o dependencias faltantes — errores de diseño
  se convierten en errores de boot, no en degradaciones silenciosas.
- Gates de arquitectura (`tests/architecture/test_single_graph_manifest.py`,
  `test_all_registered_have_descriptor_or_alias.py`, `test_all_managed_services_*_once`)
  ejecutados en CI con la suite canónica.
- El ciclo settings desapareció: boot sin warnings de degradación estructural.

### Negative

- La manifest debe mantenerse en sync con los builders de composición: una clave nueva
  sin descriptor falla el gate, pero un descriptor sin factory falla en boot — hay que
  actualizar ambos en el mismo cambio.
- Los alias agregan un nivel de indirección que exige documentar la clave canónica.

### Migration

- `BUILTIN_DEPENDENCIES` y las listas históricas fueron eliminadas en `670d0857`.
- Las claves duplicadas existentes migraron a `alias_of` en la manifest (2 alias).
- El `settings_coordinator` fue removido; `settings_service` asumió la autoridad.
- Cualquier código que consultara las listas históricas usa ahora `SERVICE_MANIFEST`.

## Alternatives considered

- **Dos inventarios sincronizados (mantener `BUILTIN_DEPENDENCIES` corregida)**: rechazado
  — reproduce el defecto original con mejores tests; el sync manual es la raíz del bug.
- **Detección de ciclos en runtime (al `start()`)**: rechazado — tarde y con efectos
  parciales; el boot debe abortar en importación con `ManifestCycleError`.
- **Grafos externos (dependency-graph libs)**: rechazado — sobre-ingeniería para un
  grafo de 80 nodos acíclico que la manifest + AST ya cubren.
