# ADR-005: OperationResult canónico para toda operación

## Status

Accepted

## Context

Cada servicio define su propia forma de resultado, o directamente devuelve `ok: True` sin evidencia de que la operación haya ocurrido. Casos verificados:

- `PlayerBarService` inventa valores (`volume=75`, `state=stopped`, `position=0`) cuando el player no está disponible, en lugar de reportar la indisponibilidad.
- `SettingsService.open()` devuelve `ok: True` nominal sin efecto observable ni readback.
- `reset_all` no es transaccional: si una parte falla, el estado queda a medias sin señalizarlo.
- `process_message` (Michi AI) devuelve `ok: True` incluso cuando la herramienta falló (ver ADR-006).
- Cada bridge y servicio modela errores, warnings y metadatos con nombres y estructuras propias (tuplas, dicts, `True/False`).

Consecuencias:

- La UI no puede distinguir "operación completada" de "operación aceptada" de "capacidad no disponible": todo es un booleano.
- El estado inventado por servicios fallidos se muestra como real, rompiendo la confianza en los datos (mismo problema que el `isPlaying` prematuro del ADR-003).
- El consumo de resultados exige conocer el shape específico de cada servicio: el acoplamiento es per-servicio y no hay composición.

## Decision

Introducir un **`OperationResult` canónico** en `core/` (junto a `core/interfaces.py` o módulo dedicado `core/operation_result.py`) que toda operación productiva devuelve:

- `ok: bool` — verdadero solo para `COMPLETED`, `ACCEPTED` o `PARTIAL_SUCCESS`; **nunca** se fija `ok=True` sin side effect o readback que lo confirme.
- `status: OperationStatus` — enum: `COMPLETED`, `ACCEPTED`, `PENDING`, `PARTIAL_SUCCESS`, `CAPABILITY_UNAVAILABLE`, `DEFERRED_PHYSICAL`, `FAILED`, `CANCELLED`.
- `code: str` — código estable y accionable (p. ej. `INFRASTRUCTURE_UNAVAILABLE`, `SERVICE_MISSING`).
- `message: str` — texto legible para UI/logs.
- `data: Any | None` — payload de la operación.
- `warnings: list[str]` — advertencias no fatales.
- `errors: list[str]` — errores agregados.
- `operation_id: str | None` — correlación de la operación.
- `job_id: str | None` — correlación con un job durable (ADR-004) cuando aplique.
- `rollback_available: bool` — si la operación puede revertirse.

Reglas de uso:

- **No hay `ok=True` nominal**: un servicio que no puede ejecutar la operación devuelve el status correspondiente (`CAPABILITY_UNAVAILABLE`, `FAILED`) aunque internamente no lance excepción.
- **No hay shapes de resultado inventados por servicio**: tuplas ad-hoc, dicts sin esquema o booleanos desnudos quedan prohibidos en la superficie pública de servicios productivos.
- El status enum es la fuente de verdad; `ok` es un derivado conveniente para la UI, no un campo independiente que cada servicio rellena a su gusto.
- `DEFERRED_PHYSICAL` cubre operaciones que la lógica acepta pero cuyo efecto físico (p. ej. reescritura de tags, borrado en disco) aún no se confirmó; `rollback_available` documenta la reversibilidad.
- `CAPABILITY_UNAVAILABLE` es el status de los modos degradados de los bridges (ADR-003) y de servicios ausentes (ADR-001), en lugar de valores inventados.
- Durante la migración se permiten **adapters** en los límites (p. ej. convertir el resultado de un servicio legacy a `OperationResult`), pero el dominio productivo debe hablar `OperationResult` nativo.

## Consequences

### Positive

- La UI distingue sin ambigüedad completado/aceptado/pendiente/no disponible/fallido.
- Desaparecen los valores inventados (`volume=75`, `state=stopped` cuando no hay player): se sustituyen por `CAPABILITY_UNAVAILABLE`.
- Los resultados se componen y se correlacionan (operation_id/job_id), lo que habilita auditoría y diagnóstico.
- Un test estructural puede prohibir `ok=True` sin status derivado real.

### Negative

- Migración amplia: tocar PlayerBarService, SettingsService, reset_all, process_message y los shapes per-servicio.
- `OperationResult` es más verboso que un booleano; los servicios simples deben devolverlo igualmente por consistencia.
- Riesgo de "ok fabricado" si un servicio marca `COMPLETED` sin verificar el side effect; la disciplina debe acompañarse de tests de readback en los puntos críticos.

### Migration

1. Definir el dataclass/enum en `core/operation_result.py` con tests de construcción y derivación de `ok`.
2. Migrar primero los puntos de mayor daño: `PlayerBarService` (eliminar valores inventados), `SettingsService.open()`, `reset_all` transaccional.
3. Migrar `process_message` de Michi AI junto con ADR-006.
4. Agregar adapters temporales en los límites legacy y un test estructural que prohíba retornos booleanos/tupla en servicios productivos.

## Alternatives considered

- **Retornar el resultado del servicio actual sin cambiar los shapes (solo estandarizar booleans).** Rechazada: el booleano no expresa PARTIAL_SUCCESS ni CAPABILITY_UNAVAILABLE, que son los casos reales que hoy se pierden.
- **Excepciones como única señal de error.** Rechazada como estándar único: los errores de capacidad no son excepciones del programador y los resultados parciales no lanzan; `OperationResult` los modela explícitamente.
- **Resultado tipo Either (Ok/Err).** Válida para fallos binarios, pero no cubre los 8 estados de la aplicación (pendiente, deferred, parcial); rechazada por insuficiente.
