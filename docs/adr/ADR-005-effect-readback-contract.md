# ADR-005: Contrato de efecto + readback (ok=True exige efecto verificado)

## Status

Accepted (P0 stabilization — fases F3, F4, F5; gate F11 variante A)

## Context

`ok=True` se afirmaba sin evidencia del efecto. Tres familias de falsos éxitos:

- **Metadata**: la edición devolvía `ok=True` tras escribir el tag, sin verificar el
  valor efectivo en DB ni en el archivo físico; el readback podía omitirse o compararse
  de forma laxa (baseline #3/#4/#5, ver ADR-003).
- **Favoritos**: `set_favorite`/`set_favorite_group` podían reportar éxito con
  aplicaciones parciales (algunos tracks inexistentes silenciados) y el desfavoritar un
  álbum destruía favoritos directos de tracks internos (regresión F4).
- **Radio**: `accept`/`play` devolvía éxito mientras el backend no estuviera en
  `PLAYING`; se registraba historial de "play" en estados `CONNECTING`/`REQUESTED` que
  nunca llegaron a reproducir (F5).

Evidencia: `audit_capability_truthfulness.py` (F11, variante A) escanea por AST los
efectos de los métodos con `ok: True` productivos: **598 `ok: True` → 0 violaciones**,
23 allowlist documentadas (efectos verificados por contratos no-readback), 16 `QUERY`
(sin efecto mutante), 0 `return True` sin efecto. En el baseline este mismo auditor
marcaba decenas de falsos éxitos.

## Decision

Contrato de dos partes para toda operación mutante de dominio:

1. **`ok=True` exige efecto + readback**: el resultado exitoso debe incluir la evidencia
   del efecto (dato persistido, checksum, estado) obtenida por lectura posterior — no por
   la intención. `ok=True` sin verificación es una violación del contrato.
2. **Readback per-field en metadata**: cada campo efectivo se clasifica:
   `VERIFIED` (DB y tag coinciden con lo esperado), `DB_MISMATCH`, `TAG_MISMATCH`,
   `READ_ERROR`, `UNSUPPORTED_TAG`, `FILE_MISSING`. Si algún campo no es `VERIFIED`, la
   operación devuelve `READBACK_MISMATCH` (o éxito parcial tipado), nunca `ok=True` liso
   (`test_db_readback_mismatch_failure`, `test_physical_tag_mismatch_failure`).
3. **Bulk atómico con desglose honesto**: los bulk de favoritos reportan por item
   `applied` / `already_set` / `not_found` / `failed`, con aplicación atómica por grupo y
   `READBACK_MISMATCH` si el readback falla (`test_bulk_mixed_ids`).
4. **Origen preservado en favoritos**: desfavoritar un álbum preserva los favoritos
   `direct` de tracks internos; `parent_entity` distingue
   `direct` / `inherited_album` / `inherited_artist` / `inherited_genre` /
   `migrated_legacy` (migración DB 9; `test_direct_favorite_inside_favorited_album`).
5. **Radio: éxito solo en `PLAYING`**: `accepted=True` se emite únicamente en estado
   `PLAYING`; historial de kinds `attempt`/`play`/`failure`/`reconnect`/`stopped` — nunca
   `play` en `CONNECTING` (`test_no_play_history_on_connecting`). Sin backend disponible
   no hay éxito (`test_backend_absent`).
6. **Excepciones documentadas**: 23 allowlist de `audit_capability_truthfulness.py` con
   razón escrita (lecturas, no-ops honestos, respuestas de estado), más 16 `QUERY` — toda
   excepción debe estar justificada en el propio auditor.

## Consequences

### Positive

- El sistema ya no puede afirmar éxito sin efecto: los tests verticales F3/F4/F5 prueban
  el readback con archivos físicos reales y DB real.
- El auditor AST (variante A) es un gate permanente: 598 `ok: True` auditados, 0
  violaciones en head.
- El historial de radio es un registro fiel de lo que sonó, no de lo que se intentó.

### Negative

- Costo de I/O: cada mutación exitosa requiere una lectura de verificación (tag + DB) —
  aceptable para metadata/favoritos/radio, inaceptable para operaciones masivas sin
  readback (cubiertas por la allowlist con justificación).
- `READBACK_MISMATCH` introduce estados de resultado que los callers QML deben renderizar
  (hoy tipados, no todos representados en el skin).

### Migration

- `metadata_editor_service` implementó readback per-field en `68a7aecf` (con ADR-003).
- `favorites` implementó bulk atómico + `parent_entity` en `0f5130ed` (migración 9).
- `RadioPlaybackAdapter` sobre `PlayerService` con estados canónicos en `e2cbb204`.
- Los tests actualizados por fase documentan el cambio de contrato (criterio 36 del
  acceptance matrix): no se debilitó ninguna aserción.

## Alternatives considered

- **Confiar en el retorno del backend (status quo)**: rechazado — el backend puede
  reportar intención sin efecto (radio `CONNECTING` como éxito).
- **Readback global a posteriori (job de reconciliación)**: rechazado — tarde para el
  caller; la verificación debe ser parte del resultado.
- **`ok=True` solo tras verificación humana**: rechazado — inaplicable a jobs durables
  y sync; la verificación por lectura posterior es el estándar.
