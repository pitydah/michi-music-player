> STATUS: HISTORICAL SNAPSHOT
> BASELINE: 6ae14b89 (head SHA recorded in this document)
> SUPERSEDED BY: AGENTS.md §2A + docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md + docs/testing/SUBSYSTEM_MATURITY.yaml

# P0 Stabilization — Acceptance Matrix

Los 40 criterios de aceptación del mandato P0 con su estado y evidencia ejecutada sobre
el head `6ae14b89` (rama `agent/runtime-refactor-p0-stabilization`). Ningún criterio se
marca PASS sin evidencia ejecutada (test, auditor o comando). La convención es
PASS = evidencia ejecutada en head / PARTIAL = evidencia parcial o condicionada /
FAIL = no cumplido.

## 1. Criterios de runtime y container (F1)

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Manifest como única fuente de verdad del ciclo de vida | **PASS** | `tests/architecture/test_single_graph_manifest.py` (green); `test_manifest_cycle_detected.py` |
| 2 | Sin `BUILTIN_DEPENDENCIES` ni listas históricas en código productivo | **PASS** | Source scan: 0 referencias productivas (solo tests QML legacy); `test_single_graph_manifest.py` |
| 3 | Ciclos de dependencia detectados (no silenciosos) | **PASS** | `ManifestCycleError`; `tests/architecture/test_manifest_cycle_detected.py`, `test_manifest_missing_dependency_rejected.py` |
| 4 | Alias no produce doble `start()` | **PASS** | `tests/architecture/test_alias_single_start_shutdown.py`, `test_all_managed_services_started_once.py` |
| 5 | Alias no produce doble `shutdown()` | **PASS** | Ídem + `test_all_managed_services_shutdown_once.py` |
| 6 | Jobs `RUNNING` restaurados visibles e `INTERRUPTED` retryable | **PASS** | `tests/integration/jobs/test_job_restart_running_visible.py`, `test_job_persistence_restart.py` |
| 7 | Retry unificado inicia la ejecución real (no solo reencola) | **PASS** | `tests/integration/jobs/test_retry_semantics_unified.py`, `tests/integration/test_notification_retry_real_job.py` |
| 8 | Cancelación de Mix no cancela jobs ajenos | **PASS** | `tests/integration/jobs/test_cancel_mix_does_not_cancel_scan.py` (2 tests) + auditor F (0 cancel_all) |
| 9 | Mix sin matches / vacío no reporta éxito | **PASS** | `tests/integration/test_mix_no_matches_status.py` (10 tests), `test_mix_generation_job_vertical.py::test_empty_library_not_success` / `test_no_matches_not_success`; gate `test_mix_empty_result_is_not_success.py` |
| 10 | Guardar mix crea playlist con id real | **PASS** | `test_mix_generation_job_vertical.py::test_save_playlist_real_id`; `test_partial_playlist_save` |
| 11 | Metadata sin `confirmed=True` verificable es rechazada | **PASS** | `tests/integration/test_metadata_token_security.py::test_confirmed_true_bypass_rejected`; gate `test_no_self_declared_confirmation.py` |
| 12 | `selected_fields` respetado end-to-end | **PASS** | `test_metadata_token_security.py::test_selected_fields_respected_end_to_end` |
| 13 | Readback compara esperado vs efectivo (DB y tag físico) | **PASS** | `test_db_readback_mismatch_failure`, `test_physical_tag_mismatch_failure` (mismo archivo) |
| 14 | Legacy delega o falla explícito (nunca éxito falso) | **PASS** | `test_metadata_token_security.py::test_legacy_api_delegates_or_disabled`; `LEGACY_OPERATION_DISABLED` |
| 15 | Desfavoritar álbum preserva favoritos directos | **PASS** | `tests/integration/test_favorites_integrity.py::test_direct_favorite_inside_favorited_album` |
| 16 | Bulk tolera ids inexistentes con desglose honesto | **PASS** | `test_favorites_integrity.py::test_bulk_mixed_ids` (applied/already_set/not_found/failed) |
| 17 | Radio sin backend disponible no reporta éxito | **PASS** | `tests/integration/test_radio_playback_vertical.py::test_backend_absent`; gate `test_radio_no_success_without_playback.py` |
| 18 | Radio no registra `play` en `CONNECTING` | **PASS** | `test_radio_playback_vertical.py::test_no_play_history_on_connecting` |
| 19 | Mobile verifica firma real (válida acepta, inválida rechaza) | **PASS** | `tests/integration/test_mobile_pairing_signature.py::test_valid_signature_pairing`, `test_invalid_signature_rejected` |
| 20 | Code-only no obtiene confianza automática | **PASS** | `test_code_without_signature_fails`, `test_legacy_mode_flagged` (loopback+TTL+audit); gate `test_mobile_pairing_no_unverified_fingerprint.py` |
| 21 | Fallo de persistencia invalida el pairing | **PASS** | `test_mobile_pairing_signature.py::test_persistence_failure_invalidates`; `test_mobile_pairing_persistence.py` |
| 22 | Un solo `DeviceRegistry` (y un solo bus) | **PASS** | `tests/architecture/test_single_event_bus_and_registry.py`; `test_lyrics_single_authority.py` |
| 23 | Device sync usa jobs durables | **PASS** | `tests/integration/test_device_sync_vertical.py`; gates `test_device_sync_single_authority.py`, `test_audio_lab_uses_durable_jobs.py` |
| 24 | Device sync verifica transferencias (checksum) | **PASS** | `test_device_sync_vertical.py::test_checksum_mismatch` |
| 25 | Device sync sin sistema de jobs interno | **PASS** | Source scan AST: 0 `threading.Lock`/`_jobs` en facade; auditor G + `test_single_durable_job_authority.py` |
| 26 | AI con un solo planner/executor | **PASS** | `tests/architecture/test_assistant_runtime_single.py`; `test_ai_gateway_contracts.py` |
| 27 | Composición AI completa registrada en container | **PASS** | `tests/integration/test_assistant_runtime_vertical.py::test_runtime_registered_full`; `test_all_runtime_components_manifested.py` |
| 28 | Lyrics con un solo event bus | **PASS** | `test_single_event_bus_and_registry.py`, `test_lyrics_single_authority.py` |
| 29 | Recognition avanzado conectado (provider manager + captura + detección) | **PASS** | `test_single_event_bus_and_registry.py` + auditor B (0 construcción en bridges); ports Recognition |
| 30 | Sin construcción de servicios en bridges/handlers | **PASS** | `tests/architecture/test_handlers_no_service_construction.py`; `audit_bridge_responsibilities.py` (B): 0 violaciones, 52 documentadas |
| 31 | Sin SQL directo en bridges | **PASS** | `tests/architecture/test_bridge_has_no_direct_sql.py`; auditor B |
| 32 | Sin subprocess directo en árbol productivo | **PASS** | `tools/audit_process_isolation.py` (G): 633 archivos, 2 en port, 16 adaptadores, 0 violaciones |
| 33 | `ok=True` crítico exige efecto + readback | **PASS** | `tools/audit_capability_truthfulness.py` (A): 598 `ok: True` → 0 violaciones, 23 allowlist razonadas, 16 QUERY, 0 `return True` bare; tests F3/F4/F5 |
| 34 | Tests verticales por reparación | **PASS** | F1: 7 archivos; F2: 12+ `tests/integration/jobs/`; F3: 2 archivos verticales; F4: 1; F5: 1; F6: 3; F7: 3; F8: 1; F9: 2; F10: gates — todos ejecutados en suite |
| 35 | CI completo (suite canónica + architecture + auditores + QML) | **PARTIAL** | Suite no-QML **4348 passed / 3 failed / 96 skipped / 13 errors** — 3 failed y 13 errors **idénticos a baseline** (perf FTS 10k/50k + flaky `test_player_service_apply_profile` + fixture `_qt_app` en `tests/perf`), demostrado por comparación base=head. Architecture+integration **563 passed**. Auditores 7/7. **QML**: `tests/qml` tiene fallos pre-existentes idénticos al baseline — no regresión, pero el gate QML completo no está verde. Honestidad: el mandato exige que cualquier error de suite se demuestre idéntico base=head; eso se hizo, pero `tests/qml` completo sigue rojo. |
| 36 | No se modificaron tests para ocultar fallos | **PASS** | Todos los tests actualizados documentan cambio de contrato por mandato (contrato token F3, bulk F4, estados radio F5, jobs F2); diffs de fase revisables en commits |
| 37 | No se deshabilitaron gates de CI | **PASS** | `.github/workflows/` intactos; gates de arquitectura nuevos agregados en `tests/architecture/` (56 archivos) — la suite creció, no se excluyó |
| 38 | Sin excepciones silenciosas en auditores | **PASS** | Allowlists explícitas con razón en cada auditor (23 A / 52 B / 5 E / 16 QUERY / 7 probes D / 2 shared C); 0 excepción sin justificación |
| 39 | No fusionar antes de cerrar P0 | **PASS** | Rama `agent/runtime-refactor-p0-stabilization` sin merge: 12 commits sobre `66245d11`, PR pendiente de revisión; este informe es el cierre que habilita la revisión |
| 40 | Informe distingue COMPLETED / PARTIAL / DEFERRED | **PASS** | Este documento: 39 PASS + 1 PARTIAL (criterio 35, QML); deuda explícita en `P0_STABILIZATION_COMPLETION_REPORT.md` §6 |

## 2. Resumen

| Estado | Cantidad |
|---|---|
| PASS | 39 |
| PARTIAL | 1 (criterio 35 — suite QML completa roja, idéntica a baseline, sin regresión) |
| FAIL | 0 |

## 3. Notas de evidencia

- Todos los tests citados pertenecen a la suite ejecutada en head `6ae14b89`
  (`pytest tests/ -q --ignore=tests/qml --ignore=tests/test_large_library.py` → 4348
  passed; `pytest tests/architecture tests/integration -q` → 563 passed).
- Los auditores se ejecutaron con exit 0 (7/7): `audit_runtime_reachability.py`,
  `audit_service_duplicates.py`, `audit_bridge_responsibilities.py`,
  `audit_ai_tool_mappings.py`, `audit_capability_truthfulness.py`,
  `audit_process_isolation.py`, `audit_nominal_tests.py`.
- Criterio 35: la comparación base=head se hizo contra `P0_STABILIZATION_BASELINE.md`
  (sección 3): mismos 3 failed, mismos 13 errors, mismos motivos. La suite `tests/qml`
  no está verde en head NI en baseline: se documenta como PARTIAL y se excluye de la
  señal de regresión P0, pero NO se declara cumplida.
- Referencia cruzada: problemas por fase y deuda restante en
  `P0_STABILIZATION_COMPLETION_REPORT.md` (§2 y §6).
