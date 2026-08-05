# ADR-001: Service Container Manifest declarativo

## Status

Accepted

## Context

`ServiceContainer` (`core/service_container.py`) es el punto único de composición de la aplicación: registra 61 claves vía los composition builders de `core/composition/*.py`. Sin embargo, el ciclo de vida está partido en dos verdades distintas:

- `start()` recorre listas estáticas de nombres: solo **37** servicios son lifecycle-tracked. Los otros **24** objetos registrados (recognition_service, snapserver_manager, library_service, songs/track/genres/folder_service, cd_ripper_service, mobile_sync_service, etc.) se construyen pero **nunca se inician**.
- `shutdown()` cubre todo lo que conoce, pero como `start()` no conoce a los 24 restantes, hay componentes cuyo estado queda a mitad de camino entre "registrado" y "vivo".

Problemas derivados:

- No existe un módulo manifest que declare qué servicio existe, qué interfaz cumple, quién lo consume y en qué orden debe arrancar.
- Un servicio olvidado en las listas de nombres se registra en silencio y nunca recibe `start()`, sin que nada falle en tiempo de importación.
- Las dependencias entre servicios se resuelven por convención de orden, no por declaración: cambiar el orden de un composition builder puede romper dependencias sin diagnóstico claro.
- `core/dependency_graph.py` existe pero es un huérfano: intentó modelar dependencias y quedó fuera de uso, evidencia de que la necesidad de un grafo real no se resolvió.

## Decision

Reemplazar las listas estáticas de nombres por un módulo declarativo **`core/service_manifest.py`** que sea la única fuente de verdad del ciclo de vida del container.

Cada servicio queda descrito por un `ServiceDescriptor` con los siguientes campos:

- `name` — clave canónica del servicio (debe existir en el container).
- `interface` — clase/Protocol que el servicio debe satisfacer.
- `implementation` — clase concreta esperada.
- `factory` — callable de composición (por defecto: lookup por nombre en los builders).
- `dependencies` — lista de nombres de servicios que deben estar `started` antes que él.
- `priority` — orden topológico de arranque derivado de las dependencias.
- `lifecycle` — `managed` (start/shutdown automático), `lazy` (se inicia bajo demanda), `stateless` (no requiere ciclo de vida).
- `capabilities` — capacidades declaradas (para discovery y para validación con bridges).
- `consumers` — lista de módulos/bridges que lo consumen (para detectar huérfanos).

Consecuencias operativas:

- `start()` y `shutdown()` del container se generan **exclusivamente a partir del manifest**; las listas de nombres estáticos desaparecen.
- **Todo componente con estado** —incluidos `*Manager`, `*Registry`, `*Executor`, `*Store`— debe estar manifestado y ser lifecycle-owned. No se admite registrar objetos con estado fuera del manifest.
- Los servicios marcados como `required` nunca pueden resolverse como `None`: la composición falla en arranque con un error explícito (nombre, dependencia faltante, orden), no en runtime.
- Validación automática en tests: detectar servicios sin `consumers` (nadie los usa) y dependencias no declaradas en el manifest (se consumen pero no se listan).

## Consequences

### Positive

- Un solo archivo describe qué existe, qué hace falta para arrancar y quién consume cada servicio; la verificación se vuelve estática.
- Los 24 servicios hoy "registrados pero nunca iniciados" quedan visibles: o se les asigna lifecycle o se declaran stateless, eliminando el estado fantasma.
- Los fallos de composición se detectan en arranque con mensajes accionables, no como `None` en runtime.
- `dependency_graph.py` puede resucitarse como visualización derivada del manifest o eliminarse sin ambigüedad.

### Negative

- Migración costosa: cada composition builder debe declarar sus servicios en el manifest (61 entradas iniciales).
- Riesgo de arranque en cascada: si una dependencia se declara mal, el orden topológico puede diferir del actual; se debe congelar el orden vigente antes de migrar.
- El manifest duplica información que hoy vive dispersa en builders; hay que evitar que ambos divergan (regla: el manifest es fuente, los builders solo construyen).

### Migration

1. Generar el manifest inicial leyendo las claves registradas y las dos listas de nombres de `service_container.py`; asignar `lifecycle=managed` a las 37 actuales y revisar una a una las 24 restantes.
2. Congelar el orden de arranque actual con un test snapshot antes de derivar `priority`.
3. Incorporar la validación de consumers/dependencias como test de composición, y hacer que `start()` falle ante un servicio `required` ausente.
4. Eliminar las listas estáticas y dejar `dependency_graph.py` fuera de servicio (o re-generado desde el manifest).

## Alternatives considered

- **Mantener las listas estáticas y solo agregar las 24 claves faltantes.** Menor esfuerzo inmediato, pero conserva la doble verdad y no resuelve el problema de las dependencias no declaradas; rechazada por corto plazo.
- **Auto-discovery por convención (importar todo `core/` y derivar lifecycle por tipo de clase).** Elimina el manifest pero introduce magia implícita, hace impredecible el orden de arranque y complica el testeo; rechazada por favorecer la explícitud.
- **Container con inyección completa por anotaciones (tipo `pydantic`/`dataclass` autowired).** Elegante a futuro, pero es un refactor total de los 15 controllers y 61 builders; el manifest declarativo da el mismo diagnóstico con mucho menor riesgo.
