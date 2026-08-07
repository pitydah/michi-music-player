# ADR-003: Contexto de acción explícito (ActionContext + ConfirmationToken)

## Status

Accepted (Fase 3 de P0 stabilization — commit `68a7aecf`)

## Context

La edición de metadatos aceptaba confirmación autodeclarada: el receptor validaba el
campo `source` ("ui"/"doctor"/"durable_job") en vez de una prueba emitida por
`ConfirmationService`. Falsos éxitos del baseline:

- `core/metadata_editor_service.py:251` — aceptaba `confirmed=True` autodeclarado (Falso
  éxito #3).
- `core/library_doctor_service.py:146` — `source="doctor"` autodeclarado (#4).
- `ui_qml_bridge/metadata_bridge.py:280` — `source="ui"` autodeclarado (#5).

Consecuencia: un caller arbitrario (bridge, job, script) podía marcar cualquier operación
como "confirmada" sin que el usuario la hubiera aprobado, y el sistema devolvía
`ok=True` con un efecto real en disco — falso éxito por construcción. Además, el
readback posterior podía omitirse: `ok=True` se afirmaba sin verificar el efecto
(ver ADR-005).

Evidencia del baseline: `audit_capability_truthfulness.py` y
`test_no_self_declared_confirmation.py` (gate de arquitectura) detectaban la
autodeclaración por AST.

## Decision

Toda operación de metadata destructiva o persistente requiere un contexto de acción
explícito: un `ActionContext` que vincula la confirmación al **comando, al target y a los
campos** mediante hashes, emitido por `ConfirmationService`:

1. **`ConfirmationToken`** con: `operation_id`, `command_hash`, `target_hash`,
   `selected_fields`, `issued_at`, `expires_at`, `approved`, `issuer`, `single_use`.
   El receptor rechaza cualquier mutación sin token verificable.
2. **Errores tipados**: `TOKEN_REQUIRED`, `EXPIRED`, `TARGET_MISMATCH`,
   `FIELD_MISMATCH`, `COMMAND_MISMATCH`, `USED`, `NOT_APPROVED`. Un token no es
   transferible entre comandos, targets ni campos.
3. **`effective_fields = proposal ∩ selected`**: el token solo autoriza los campos
   seleccionados por el usuario; cualquier campo extra propuesto se excluye o falla con
   `FIELD_MISMATCH`.
4. **Auditoría JSONL**: cada confirmación emitida/consumida se registra en un log
   append-only (`metadata_confirmations.jsonl`), con issuer y hashes.
5. **Legacy**: los callers sin token (`source="ui"|"doctor"|"durable_job"`) no degradan
   silenciosamente: delegan en el flujo con token o fallan con
   `LEGACY_OPERATION_DISABLED` (`test_legacy_api_delegates_or_disabled`).
6. **Backup y undo**: antes de aplicar se persiste backup (7 días con cleanup de
   expirados); el undo es restart-safe (persistido, no solo en memoria).

## Consequences

### Positive

- Un caller no autorizado no puede fabricar confirmaciones: el hash de comando/target/
  campos es la prueba, no la palabra `confirmed=True`.
- Los tests de seguridad son de caja negra: `test_confirmed_true_bypass_rejected`,
  `test_selected_fields_respected_end_to_end`, `test_db_readback_mismatch_failure`,
  `test_physical_tag_mismatch_failure` (`tests/integration/test_metadata_token_security.py`).
- Auditoría accionable: el JSONL permite reconstruir quién confirmó qué, cuándo y sobre
  qué hash.

### Negative

- Costo de integración: cada caller debe obtener un token emitido (flujo de 2 pasos)
  antes de mutar; los tests del dominio metadata necesitan emitir tokens reales.
- El token caduca (`expires_at`): flujos largos (doctor con preview humana) deben
  re-emitir.
- Los backups de 7 días ocupan espacio y exigen cleanup — riesgo de acumulación si el
  job de limpieza no corre.

### Migration

- `metadata_editor_service`, `library_doctor_service` y `metadata_bridge` migraron al
  flujo con token en `68a7aecf`; los tests actualizados documentan el cambio de contrato
  (criterio de aceptación 36: no se modificaron tests para ocultar, se actualizaron por
  mandato).
- El gate `test_no_self_declared_confirmation.py` impide reintroducir la autodeclaración.

## Alternatives considered

- **Confiar en `source` declarado (status quo)**: rechazado — es el defecto mismo; un
  string no es una prueba.
- **Firma HMAC simétrica simple por sesión**: rechazado — sin `target_hash`/`command_hash`
  un token firmado serviría para cualquier operación (replay entre operaciones).
- **Confirmación implícita (aprobar = click que ya ocurrió)**: rechazado — no distinguir
  selección parcial de campos ni tiempo de vida del consentimiento.
- **Sin confirmación para job durables (confiar en la UI)**: rechazado — reproduce el
  falso éxito #3; los durables ahora reciben tokens emitidos por `ConfirmationService`.
