# P0 Stabilization Baseline

Documento de la Fase 0 del refactor de estabilización: línea base reproducible ANTES de cualquier cambio de código de estabilización. Cualquier PR posterior debe poder compararse contra este documento para demostrar que no se alteró el comportamiento del runtime.

## 1. Metadata del baseline

| Campo | Valor |
|-------|-------|
| SHA auditado | `66245d11797ecb70e1a84cab1b79930d9dd32c28` |
| Branch | `agent/runtime-refactor-p0-stabilization` |
| Origen del branch | `agent/runtime-service-architecture-refactor` (head igual al SHA auditado, sin commits posteriores a `66245d11`) |
| Fecha | 2026-08-06 |
| PR de referencia | #186 (`agent/runtime-service-architecture-refactor` → `main`) |
| Base del PR | `4ea914f5` |

## 2. Entorno y comandos exactos

Entorno: Linux desktop, Python 3.11+, KDE Plasma / Qt 6. Suite ejecutada desde la raíz del repo sobre el SHA `66245d11` (working tree limpio).

```bash
# Suite no-QML (excluye tests/qml y test_large_library.py)
python -m pytest tests/ --ignore=tests/qml --ignore=tests/test_large_library.py -q

# Subsuelo arquitectura + integración
python -m pytest tests/architecture tests/integration -q

# Auditores de runtime
python tools/audit_runtime_reachability.py
python tools/audit_service_duplicates.py
python tools/audit_bridge_responsibilities.py
python tools/audit_ai_tool_mappings.py
python tools/audit_capability_truthfulness.py

# Calidad estática
ruff check . --output-format concise
python -m compileall -q -x '.venv/|\.tmpl\.' .
```

## 3. Resultados de suite

| Métrica | Resultado |
|---------|-----------|
| Suite no-QML (excl. `tests/qml`, excl. `test_large_library.py`) | **4134 passed, 3 failed, 96 skipped, 7 deselected, 13 errors** |
| `tests/architecture` + `tests/integration` | **358 passed** |

### Demostración de que los 3 fallos son ambientales

| Test | Motivo |
|------|--------|
| `tests/perf/test_qml_real_db_10k_50k.py::TestQmlRealDB::test_global_search_fts[10000]` | Requiere una base real indexada con 10k pistas — condicion ambiental, no defecto de código |
| `tests/perf/test_qml_real_db_10k_50k.py::TestQmlRealDB::test_global_search_fts[50000]` | Ídem, 50k pistas |
| `tests/test_player_service_apply_profile.py::TestApplyProfileTransactional::test_verify_failure_rolls_back_to_previous` | Flaky por polución entre tests; **pasa en aislamiento** |

Estos 3 fallos se reproducen sobre el mismo SHA base `66245d11` y el mismo entorno: son estables respecto al baseline y no se espera que la estabilización los altere.

### Los 13 errors

Concentrados en `tests/perf/test_qml_startup_time.py` (fixture `_qt_app` ausente) y demás tests de `tests/perf`. El fixture `_qt_app` no existe en el código actual — los errors son de colección, no de aserción. Fuera de alcance P0 (la suite canónica de P0 es la no-QML).

## 4. Auditores (tools/)

| Auditor | Exit code | Observaciones |
|---------|-----------|---------------|
| `audit_runtime_reachability.py` | 0 | 114 líneas |
| `audit_service_duplicates.py` | 0 | 8 |
| `audit_bridge_responsibilities.py` | 0 | 17 |
| `audit_ai_tool_mappings.py` | 0 | 3 |
| `audit_capability_truthfulness.py` | 0 | 8 |

## 5. Ruff / compileall

- `ruff check .` → **0 violaciones**
- `python -m compileall -q -x '.venv/|\.tmpl\.' .` → **limpio**

## 6. Inventario de servicios

- `SERVICE_MANIFEST` en `core/service_manifest.py` con **80 descriptores**, todos registrados en el container.
- Boot reporta **"80 services"**; bridge graph: **43 ok / 0 missing_required / 0 degraded**.
- Bootstrap: **DEGRADED** por `snapserver_manager` → `SNAPSERVER_BINARY_UNAVAILABLE`. El binario `snapserver` no está instalado en la máquina: degradación esperada y honesta (no es un falso éxito).

## 7. Componentes fuera del container

No hay componentes construidos fuera del container conocidos en el baseline. El inventario completo de instanciación fuera del `ServiceContainer` queda pendiente de auditoría en la fase F11. Este documento no afirma que no existan: afirma que NO SON CONOCIDOS todavía.

## 8. Procesos / listeners iniciados durante la composición

| Componente | Comportamiento |
|------------|----------------|
| `snapserver_manager.start()` | No-op honesto (sin binario disponible) |
| `recognition_service.start()` | No-op |
| Mobile sync listener | SOLO se inicia cuando se invoca explícitamente — no arranca en boot |
| Sync server | Via `MichiLinkServer` |

## 9. Falsos éxitos conocidos (confirmados con archivo:línea)

| # | Ubicación | Problema | Fase que lo corrige |
|---|-----------|----------|---------------------|
| 1 | `ui_qml_bridge/mix_bridge.py:310` | `cancel_all()` global desde el dominio Mix — cancela jobs ajenos al dominio | Fase Mix |
| 2 | `ui_qml_bridge/mix_bridge.py:369-439` | `_build_daily_mix` / `_build_custom_mix`: dispatch de estrategias y estado de negocio en el BRIDGE (duplicado del servicio) | Fase Mix |
| 3 | `core/metadata_editor_service.py:251` | Acepta `confirmed=True` autodeclarado con `source` ("ui"/"doctor"/"durable_job") sin token verificable de `ConfirmationService` | Fase Metadata |
| 4 | `core/library_doctor_service.py:146` | `source="doctor"` autodeclarado (sin token) | Fase Metadata |
| 5 | `ui_qml_bridge/metadata_bridge.py:280` | `source="ui"` autodeclarado | Fase Metadata |
| 6 | `core/jobs/job_service.py:146-151` | Restore: jobs RUNNING→INTERRUPTED pero AUSENTES de memoria (no visibles en `list_jobs`); jobs QUEUED re-enqueueados pero NUNCA reprocesados (nadie llama a `process_queue` tras boot) — jobs zombies acumulados (24+ en el log del usuario) | Fase Jobs |
| 7 | `ui_qml_bridge/job_bridge.py:184` (`retryJob`) | Reencola pero no inicia; semántica distinta a `NotificationActionService.retry` (`core/notification_action_service.py:90`, que sí hace `start_job`/`process_queue`) | Fase Jobs |
| 8 | `core/device_sync_service.py:14,155,158,226,274,457` | `threading.Lock` propio + dict `_jobs` paralelo (sistema de jobs duplicado); `hash(mount_path)` como serial (identidad inestable entre procesos) | Fase Sync |
| 9 | `core/mobile_sync_service.py:314-326` | Pairing con HMAC de código de 6 dígitos sin prueba de posesión de la clave privada | Fase Sync |
| 10 | `core/service_container.py:47,128,146,155,159` | `BUILTIN_DEPENDENCIES` + listas históricas `_required_names`/`_optional_names`/`_capability_gated_names`/`_deferred_*`: segundo inventario y segundo grafo — la manifest no es única fuente de verdad | Fase Container |
| 11 | `core/settings_service.py` ↔ `settings_coordinator` | Ciclo de dependencia circular entre servicio y coordinador | Fase Settings |

## 10. Warnings QML observados (fuera de alcance P0)

Observados en boot QML sobre el SHA baseline. Son skin QML pre-existentes y NO se corrigen en P0; se registran como observación para fases QML futuras:

- `Accessible` en `ui_qml/components/AudioOutputMenu.qml:12` (rol inválido/incompleto)
- `Shortcut` en `ui_qml/.../HeaderBar.qml:79` (binding roto)
- Iconos rotos: `previous.svg` inexistente; rutas relativas resueltas contra base `/home`
- `blue-noise-64.png` corrupto (referenciado en `ui_qml/materials/BlueNoiseOverlay.qml`)
- `_pythonToCppCopy` Property ×2
- `SettingsContentPage`: `mouse is not defined`
- `OutputTestResult`: `details` null
- `LibraryDoctorFixPreview`: `undefined → bool`
- `AudioAnalysisPage`: binding loop

## 11. CI workflows disponibles

`.github/workflows/` (verificado con `ls`):

| Workflow | Estado |
|----------|--------|
| `ci.yml` | Presente (suite canónica) |
| `library-data-validation.yml` | Presente |
| `library-premium-validation.yml` | Presente |

Nota: no hay `dependabot.yml` en `.github/` al momento del baseline (solo workflows en `.github/workflows/`).

## 12. Referencias

- PR #186 — `agent/runtime-service-architecture-refactor` → `main` (base `4ea914f5`)
- SHA auditado: `66245d11797ecb70e1a84cab1b79930d9dd32c28`
- Commit head del branch: `66245d11` — `test(architecture): reachability and authority gates + completion report`
- Documentos relacionados: `docs/audits/RUNTIME_SERVICE_AUDIT_CURRENT.md`, `docs/audits/RUNTIME_REFACTOR_COMPLETION_REPORT.md`
