# ADR-006: Runtime de Michi AI — una sola generación activa y cableado semánticamente correcto

## Status

Accepted

## Context

Michi AI tiene un historial de generaciones de herramientas (v1, v2, y propuestas de v3/v4). El estado actual verificado:

- **Una generación activa**: v2, compuesta por `core/assistant_initializer.py`.
- **80 tools** registradas, de las cuales **20 están muertas por attribute mismatch** (apuntan a métodos que no existen o tienen nombres distintos en el gateway) y **25 son stubs** (sin implementación real).
- Varios mappings semánticamente incorrectos: `delete_playlist`→`create_playlist`, `draft_playlist`→`list_playlists`, `apply_library_repair`→`list_recent`. La herramienta invoca una operación distinta de la que su nombre promete, con riesgo de efectos no deseados (borrar algo distinto de lo esperado).
- `process_message` devuelve `ok: True` incluso cuando la herramienta falló (viola ADR-005).
- Existen nombres `Production*` para gateways que no llegan a operaciones productivas reales (p. ej. el stack avanzado de `integrations/michi_link/services/` no está cableado — ver ADR-002).

Consecuencias:

- 45 de 80 tools no hacen lo que dicen o no hacen nada: la UI expone capacidades falsas.
- Un mapping incorrecto puede ejecutar una operación no deseada sobre datos reales (borrado/creación con destino equivocado).
- El usuario recibe "ok" cuando la operación falló, erosionando la confianza (mismo patrón que ADR-005).
- La propuesta de una 4ª generación añadiría otro barrido de reescritura sin resolver los defectos de la actual.

## Decision

**No crear una 4ª generación de herramientas.** Se mantiene la generación activa actual (v2, vía `assistant_initializer` composition) y se la corrige en su lugar.

Reglas del runtime:

1. **Cableado semánticamente correcto**: cada tool debe apuntar al método de gateway correcto, con schema, permiso y confirmación (`requires_confirmation`) correctos. Se prohíben mappings donde el nombre de la tool no describe la operación invocada (`delete_playlist`→`create_playlist`, `draft_playlist`→`list_playlists`, `apply_library_repair`→`list_recent` son bugs y se corrigen o se eliminan).
2. **Capability = evidencia, no existencia**: una tool se declara disponible solo si: (a) el servicio está registrado en el container (ADR-001), (b) es del tipo correcto, (c) su lifecycle está saludable (started), (d) el método referenciado existe en el gateway, y (e) el backend confirma la operación. La **existencia del objeto no es suficiente** para declarar capability.
3. **`process_message` honesto**: nunca reporta `ok: True` cuando la tool falló; devuelve el resultado de la tool (conforme a ADR-005) y propaga `FAILED`/`CAPABILITY_UNAVAILABLE` con el detalle.
4. **Tools muertas y stubs**: los 20 attribute mismatches se reparan (apuntando al método correcto) o se eliminan; los 25 stubs se implementan o se retiran del registro. No pueden convivir tools "registradas pero no ejecutables" en el inventario público.
5. **`Production*` reservado**: los nombres `Production*` solo se usan para gateways que realmente alcanzan operaciones productivas (cableadas en el container y verificables). Un gateway sin cablear no lleva el prefijo `Production`.

## Consequences

### Positive

- El inventario de tools pasa a ser verificable: nombre ↔ método ↔ schema ↔ backend, con tests por tool.
- Desaparecen las capacidades falsas de la UI y el riesgo de invocar operaciones equivocadas sobre datos reales.
- `process_message` se alinea con ADR-005 y la UI puede distinguir fallo real de "ok" nominal.
- Se ahorra el costo de una 4ª generación sin corregir la actual.

### Negative

- La auditoría de 80 tools es trabajo significativo (revisar las 20 muertas y 25 stubs una por una).
- Reducir el inventario puede quitar tools que algún flujo esperaba; hay que verificar consumidores antes de eliminar.
- Alinear capability con backend confirmado puede hacer que algunas tools aparezcan "no disponibles" en entornos sin servicio (p. ej. sin Michi Link), requiriendo copy de UI honesto.

### Migration

1. Generar un inventario machine-readable de las 80 tools: name, método objetivo, schema, permiso, confirmación, estado (viva/muerta/stub).
2. Reparar o eliminar los 20 attribute mismatches; implementar o retirar los 25 stubs; corregir los mappings semánticamente erróneos con prioridad (son bugs de efectos no deseados).
3. Introducir la función de capability con evidencia (registro + tipo + lifecycle + método + backend) y usarla en la composición de `assistant_initializer`.
4. Hacer honesto `process_message` y añadir tests que simulen fallo de tool y verifiquen `ok=False`.
5. Renombrar/deprecar los gateways `Production*` no cableados; cablearlos o quitarles el prefijo.

## Alternatives considered

- **Lanzar v3/v4 con barrido completo de herramientas.** Rechazada: repite el ciclo sin corregir los defectos estructurales (mappings, capability, honestidad de resultados); el costo no se justifica.
- **Eliminar todas las tools y reconstruir desde cero.** Rechazada: descarta trabajo correcto de v2 y pierde compatibilidad con flujos existentes; la reparación dirigida es más segura.
- **Declarar capability por existencia de objeto (status quo).** Rechazada: es la causa de las capacidades falsas; la evidencia de backend es el mínimo necesario.
