# ADR-003: Bridges QML como adaptadores finos

## Status

Accepted

## Context

Los bridges de `ui_qml_bridge/` son la única capa de comunicación entre la UI QML y Python (regla establecida en AGENTS.md: QML emite intención, Python ejecuta). En la práctica, varios bridges han dejado de ser adaptadores y se han convertido en segunda capa de lógica:

- `library_bridge` ejecuta SQL (favorites) directamente, saltándose el servicio de biblioteca.
- `playlists_bridge`, `job_bridge`, `history_bridge` y `library_doctor_bridge` construyen servicios como fallback cuando el inyectado no está disponible, en lugar de reportar la indisponibilidad.
- `lyrics_bridge` crea su propio cliente LRCLIB en vez de consumir `LyricsService`.
- `radio_bridge` mantiene una historia paralela a la del servicio y un `isPlaying` prematuro (estado inventado antes de que el backend lo confirme).

Consecuencias:

- Se pierde la garantía de "single source of truth": hay SQL, caches y estados viviendo en la capa de presentación.
- El fallback de construcción de servicios enmascara fallos de composición (ver ADR-001): un servicio ausente se "resuelve" en el bridge en vez de fallar en el arranque.
- La UI puede mostrar estados que el backend nunca confirmó (historia paralela, `isPlaying` prematuro), rompiendo la confianza en los datos mostrados.
- El testeo se duplica: hay que mockear tanto el servicio como el bridge, porque ambos contienen lógica.

## Decision

Los bridges de `ui_qml_bridge/` son **adaptadores finos (thin adapters)** con responsabilidades estrictamente limitadas a:

1. **Type conversion**: traducir tipos QML/Python (QVariant, listas, dicts) a los tipos del servicio y viceversa.
2. **Argument validation**: validar entradas del frontend (formato, rangos, obligatoriedad) antes de delegar.
3. **Llamar al servicio canónico**: toda operación delega en el servicio del dominio (el canonical owner según ADR-002); el bridge nunca implementa la operación.
4. **Exponer signals/properties reactivas**: propagar estado del servicio hacia QML sin transformarlo en una segunda fuente de verdad.

Queda **prohibido** en un bridge:

- Ejecutar SQL o abrir conexiones a la base de datos.
- Construir servicios, repositorios o clientes HTTP como fallback o en cualquier otra circunstancia.
- Mantener segundas fuentes de verdad: historias paralelas, caches de resultados, estados inventados.
- Programar jobs o lanzar trabajo asíncrono propio (ver ADR-004: el scheduler vive en `DurableJobService`).

Modo degradado:

- Si un servicio no está disponible, el bridge **no lo construye**: devuelve un resultado explícito `INFRASTRUCTURE_UNAVAILABLE` (ver ADR-005) con el código y el mensaje correspondientes, y la UI decide cómo presentarlo.
- Un bridge sin servicio inyectado al arrancar se reporta a `ServiceContainer` como dependencia insatisfecha; nunca resuelve la dependencia por su cuenta.

Casos existentes a corregir:

- `library_bridge`: eliminar SQL directo; delegar en el servicio de biblioteca.
- `lyrics_bridge`: consumir `LyricsService` (canonical según ADR-002); eliminar el cliente LRCLIB propio.
- `radio_bridge`: eliminar historia paralela y `isPlaying` prematuro; exponer solo el estado confirmado por el servicio de radio.
- `playlists_bridge`, `job_bridge`, `history_bridge`, `library_doctor_bridge`: eliminar la construcción de servicios como fallback.

## Consequences

### Positive

- La UI muestra solo estado confirmado por el backend; desaparecen las segundas fuentes de verdad.
- Los fallos de composición se ven en arranque (ADR-001), no enmascarados por fallback en el bridge.
- Los bridges se vuelven triviales de testear: son transformaciones puras sobre servicios mockeados.
- La lógica de negocio queda verificable en una sola capa por dominio.

### Negative

- Los bridges pueden necesitar más llamadas al servicio para obtener datos que hoy tienen en cache paralela (coste de red/CPU marginal).
- La migración requiere tocar los 4 bridges con fallback y los 2 con estado paralelo de una vez, para no dejar comportamientos híbridos.
- La UX de "modo degradado" debe diseñarse: la UI tiene que poder mostrar `INFRASTRUCTURE_UNAVAILABLE` sin crashear ni mostrar datos falsos.

### Migration

1. Eliminar los fallbacks de construcción de servicios en los 4 bridges listados; verificar con tests que la indisponibilidad devuelve `INFRASTRUCTURE_UNAVAILABLE`.
2. Mover el SQL de favorites de `library_bridge` al servicio de biblioteca y eliminar la historia/`isPlaying` paralelos de `radio_bridge`.
3. Migrar `lyrics_bridge` al `LyricsService` canónico.
4. Añadir un test estructural que prohíba `sqlite3`, `QSqlDatabase` y constructores de servicios/clients en `ui_qml_bridge/` (grep de imports en CI).

## Alternatives considered

- **Bridges ricos (fat bridges) con lógica de dominio.** Rechazada: duplica la lógica, rompe single source of truth y triplica el testeo; contradice la arquitectura QML-emite/Python-ejecuta.
- **Eliminar los bridges y conectar QML directo a servicios.** Rechazada: se pierde la barrera de conversión de tipos y validación, y la UI quedaría acoplada a APIs Python internas.
- **Service locator global dentro de los bridges.** Rechazada: reintroduce dependencias implícitas y es el mismo problema de ADR-001 en otra capa; la inyección explícita desde `ServiceContainer` se mantiene.
