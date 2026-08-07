# ADR-002: Autoridad única por dominio

## Status

Accepted

## Context

La base de código contiene múltiples implementaciones productivas para un mismo dominio, con nombres y responsabilidades superpuestos:

- **Sync / Link**: `MicroServerService` existe en 3 variantes paralelas (stacks de `michi_link` con `integrations/michi_link/services/` sin cablear, más variantes en sync/integrations). `ContinueOnServerService` existe en 2 variantes.
- **Radio**: `RadioService` duplicado en 2 ubicaciones; `radio_bridge` mantiene además su propia historia paralela y un `isPlaying` prematuro.
- **Lyrics**: `LyricsService` duplicado en 2 ubicaciones; `lyrics_bridge` crea su propio cliente LRCLIB en vez de consumir el servicio.
- **Library**: `library_service` convive con queries directas desde bridges (p. ej. `library_bridge` ejecuta SQL de favoritos).

Consecuencias:

- Un bug corregido en una variante queda vivo en la otra; el diagnóstico depende de qué import se esté usando.
- El contrato de un dominio se difumina: cada variante define su propia forma de resultados, errores y estado.
- El atributo de "single source of truth" deja de ser verificable por inspección: hay que rastrear imports para saber qué clase es productiva.
- Algunas variantes están sin cablear (p. ej. el stack avanzado de `integrations/michi_link/services/`), lo que sugiere que se escribieron sin ser integradas.

## Decision

Cada dominio de la aplicación debe tener **exactamente una autoridad productiva**: una única clase canónica que posee el estado y la lógica de negocio del dominio.

Dominios cubiertos (lista no exhaustiva): playback, queue, library, mutations, playlists, metadata, lyrics, radio, jobs, mix, recognition, sync, michi link, settings, context.

Reglas de aplicación:

- Las clases duplicadas (MicroServerService ×3, ContinueOnServerService ×2, RadioService ×2, LyricsService ×2, y cualquier otro par/terna) se resuelven con **un único canonical owner**: se elige una implementación, se migran los consumidores y las demás se eliminan o se marcan `LEGACY`.
- **No pueden existir dos clases productivas con el mismo nombre o la misma responsabilidad.** Una clase no productiva debe declararse explícitamente (sufijo `Legacy` o `Deprecated`), no convivir como variante silenciosa.
- Toda duplicación nueva debe justificarse en el ADR de su dominio o en el code review; la presunción es que el duplicado se elimina.
- Un módulo heredado que se conserva durante la migración queda marcado con la anotación de estado en su docstring y en el manifest del container (ver ADR-001), nunca como una variante sin etiqueta.
- La elección del canonical owner se documenta en un comentario de módulo con referencia al ADR de dominio cuando exista.

Criterios para elegir el canonical owner: (1) está cableado en el container de producción; (2) cubre el 100% de los consumidores actuales; (3) tiene tests; (4) tiene la forma de estado más simple (preferir la que no mantiene caches paralelos).

## Consequences

### Positive

- Un fix, un owner: el diagnóstico deja de depender de qué import esté activo.
- Los contratos de dominio se pueden documentar y testear contra una sola clase.
- La deuda de "variante paralela" se reduce a un inventario explícito y migrable, no a un misterio.
- La verificación se vuelve automática: un test de estructura puede prohibir dos clases con el mismo nombre/`__qualname__` productivo en el árbol de `core/`.

### Negative

- La migración de consumidores a un único owner puede tocar muchos archivos a la vez (p. ej. los 3 stacks de Michi Link).
- Riesgo de perder comportamiento que solo existía en la variante no elegida; hay que inventariar el API de cada duplicado antes de descartarlo.
- Durante la ventana de migración conviven `canonical` y `Legacy`, y hay que vigilar que los nuevos imports no apunten al legacy.

### Migration

1. Inventariar duplicados con un script/grep de nombres de clase y responsabilidad (arrancar por los ×3 y ×2 listados arriba).
2. Por dominio: elegir canonical owner con los criterios indicados, migrar consumidores (bridges, controllers, composition), mover tests.
3. Marcar `Legacy` o eliminar la variante restante; para Michi Link, decidir si el stack avanzado `integrations/michi_link/services/` reemplaza al actual o se descarta.
4. Añadir el test estructural de nombre/responsabilidad únicos y dejarlo en CI.

## Alternatives considered

- **Dejar convivir las variantes y solo documentar cuál es canónica.** Evita el refactor pero mantiene el riesgo de fixes divergentes y no reduce la deuda; rechazada porque documentar sin eliminar no baja el costo de mantenimiento.
- **Consolidación total inmediata de todos los dominios en un solo commit.** Máximo riesgo y sin posibilidad de validación incremental; rechazada a favor de migración por dominio.
- **Deduplicar solo por igualdad de nombre de clase.** Insuficiente: hay responsabilidades duplicadas con nombres distintos (p. ej. historia paralela en `radio_bridge`); se requiere dedup por dominio funcional.
