# A49 — Integración candidata, auditoría de fuentes reales y gates producto

**Programa:** Michi Music Player / Audio Phase 2 / F11 / Michi Signal Truth
**Corte:** 2026-11-08, America/Santiago
**Referencia examinada solo en lectura:** `pitydah/michi-music-player` PR245 SHA `d32228fbcc49c4f107e4295b1a70e31fde4d9b07`.
**Artefactos:** MISMO plan maestro acumulativo y MISMO `.patch` acumulativo en Drive, A49 reemplaza A48, no se aplica sobre A48.
**Veredicto:** `NO_GO` para certificación F11. No hubo cambios a GitHub, no hubo hardware DAC, no hubo KWin ni CI exact-SHA de A49.

## 0. Procedencia y realidad de integración

Se inspeccionaron fuentes exactas por el conector GitHub de **solo lectura**. El contenedor local no resuelve `github.com` por DNS; no se pudo obtener un checkout completo ni ejecutar su suite sobre el producto. Los ficheros `fixture_...` de A42–A49 tienen líneas de relleno y no son un checkout de la aplicación: `src/michi/domain/signal_truth.py` incluso arroja `IndentationError` si se intenta ejecutar la suite de integración completa de esa copia. Por ello la suite focal A49 sobre módulos reales propuestos es útil, pero **no** equivale a `TESTED_REPOSITORY`.

### Preimágenes reales inspeccionadas

| Propietario | SHA blob del PR245, lectura remota | Contrato no negociable |
|---|---|---|
| F03 `signal_truth.py` | `8859d9c6519807f20551a0f5650b40bcd277465a` | Un recorder; capturas con revisión, familias, mediciones con execution fence |
| F03 `signal_path_service.py` | `5f35b803efc8e40291b91fc19afa7dc4aaf7f3a8` | Cuatro nodos semánticos F03, motivos 1:1 |
| F05 `audio_processing_service.py` | `f11e76c39acfd708cc978235f98fbfa4cfa5d70e` | Readback; requested/committed/effective nunca indistintos |
| OutputSession | `db3228bdc9d385fb46f022a22a714ca92e0dc158` | Generación, execution_id, familias y binding observados |
| Qt `signal_path_bridge.py` | `70970e00cf163af27c5e91da27ab4294b6dba6cb` | Fan-out en owner thread, un bridge por instancia |
| QML `SignalTruthPopup.qml` | `3ad6080b48d3f953a21b4d353592255d48f0db33` | Popup único, stage viewport y foco |
| QML `MichiSignalPathView.qml` | `34ff5875051c7d1345cf32d98d61a3b049c1023f` | Renderer único usado por popup/DAC |
| Bootstrap `__init__.py` | `bf6b63179cb1d33ba195ddc56d68afc17381163e` | Inyección de propietarios existentes |

**Nota sobre GitHub:** todo el trabajo A49 permanece fuera del repositorio, en el parche de Drive. La lectura de blobs y del SHA PR245 **no** es prueba de aplicación del parche o de ausencia de conflictos en todo el árbol. El verificador `scripts/verify_michi_truth_product_a49.py` ejecuta esa evaluación solo sobre un checkout íntegro local.

## 1. Matriz de las siete solicitudes

| ID | Entrega candidata concreta A49 | Evidencia disponible | Gate real pendiente |
|---|---|---|---|
| `OPEN-P0-01/02` | Checker `verify_michi_truth_product_a49.py` clona localmente al SHA base, aplica parche, lanza verificadores AP2/DAC, QML y tests; audita responsables F03/F05/OutputSession/Qt sin cambiar autoridad | Código y tests aislados; blobs fuente remotos | `git apply --check`, suite y alineación sobre checkout íntegro `NOT_RUN` |
| `OPEN-P1-01` | `SignalPathBridge.metricItems` → `SignalTruthPopup.metricItems` → `MichiSignalTruthMetrics` único dentro de la tarjeta resumen del inspector existente, activo y accesible | Pruebas de conexión y modelo; QML estático | KWin, DPR 1/1.25/1.5/2, W1–W9, teclado, foco, screenshots reales `NOT_RUN` |
| `OPEN-P1-02` | `OwnerProjectionMeter` lee `perf_counter_ns` exclusivamente en `_drain_owner_refresh` ya owner-thread, no dentro de audio; scope F03 rígido y revocación al dejar ACTIVE | Tests temporales/propiedad/identidad/percentiles | Qt vivo, mediciones PCM, XRUN/true peak/LUFS/processing speed de productores auténticos `NOT_RUN` |
| `OPEN-P1-03` | Muestreador Linux `/proc/<pid>` externo, con CPU/RSS p50/p95/p99, sin instrumentar reproducción | Ejecución de humo sobre proceso `sleep` **no productivo** | DSP ON/OFF, Michi AI ON/OFF, cambio de familias, RT p99/p99.9, XRUN y QML frames `NOT_RUN` |
| `OPEN-P1-05` | Adaptador de capacidades F05 consulta `processing_truth` (`capability_state=queried`, `strategies`); Quick EQ habilitado solo si `canApply`, `BIQUAD_CASCADE`, `GAIN`. Ningún claim de adopción DSP actual sin vínculo OutputSession. CRUD Settings solo con receipt explícito. | Negativos y pruebas aisladas | F05/Settings vivos, actual adopción/revocación y EQ Advanced UI `NOT_RUN` |
| `OPEN-P0-06/07` | Ejecutor de 50 escenarios R15C con mapping explícito node ID + JUnit sin SKIP silencioso; inspector DAC por familia que nunca convierte JSON en verificación física | Con checkouts sintéticos: `0/50 PASS`, `50/50 NOT_RUN` | Pruebas producto completas, DAC verdadero por familia/capacidad, wheel, CI exact-SHA `NOT_RUN` |
| `OPEN-GOV-01` | ACL directo leído de carpeta Drive, plan, parche: `anyone: writer`, `allowFileDiscovery=false`; carpeta también abre escritura | Metadatos Drive de tres recursos, verificados | Revocación/restricción **no autorizada expresamente**, no cambiada |

## 2. Modelo de métrica real instalado como candidato

El único productor efectivamente conectado por A49 al código de presentación es `ui_observer/projection_build_ms`. Mide `perf_counter_ns()` alrededor de `_rebuild()`, `_apply_f03_semantics()`, `_apply_output_owner_truth()`, `_publish_truth_frame()` y del adaptador de capacidades F05. Solo se ejecuta en el drenaje Qt ya existente; jamás se agrega un callback por muestra PCM, timer ni consulta ALSA. La ventana conserva hasta 256 muestras y publica valor reciente, p95/p99 **de la construcción del modelo Qt**. Un identificador pseudo-opaco derivado del snapshot F03 se usa solo para eliminar muestras al cambiar identidad; **no** prueba vínculo con ejecución OutputSession.

La métrica se muestra únicamente en `ACTIVE` con plan ID/generaciones positivas y lectura estricta; al pasar a `HISTORICAL`, `PENDING` o ausente se retira. Los otros ocho campos A48 no se promueven: no hay proveedor RT probado para clipping, peak, true peak, LUFS, speed o XRUN. `ProcessingMeasurement.sample_peak` del recorder está expresado en medidas de laboratorio de identidad y debe tener contrato de escala/ventana antes de convertirse a dBFS. El nombre `projection_build_ms` evita presentarlo falsamente como latencia de audio o `frame_dispatch_ms`.

## 3. DSP y capacidades

La fuente real F05 (PR245) publica `processing_truth()` con `capability_state` (`queried`, `unknown`, `unavailable`), `strategies`, revisiones, `effective_plan_id`, `readback_proven` y estimación de latencia de plan compilado. `capability_state=queried` **no es** DSP adoptado, y una estimación de latencia no es medición de pipeline, sink ni DAC.

`signal_truth_p1_f05_adapter.py` pasa al proyector A48 `project_capabilities()` solo los receipts de capacidad verificados. Quick EQ solo puede abrirse cuando `AudioProcessingBridge.canApply` y las estrategias reales coinciden; `effective=False` hasta tener proof de adopción OutputSession para la ejecución actual. No se activa convolución, gráfico avanzado ni perfiles CRUD por el mero descubrimiento de factories. Los ajustes y commit DSP siguen únicamente en F05. El contrato actual del puente QML publica `capabilityItems` pasivamente, sin botones nuevos ni UI que prometa features bloqueadas.

## 4. Instrumentación de rendimiento (sin datos inventados)

Script `scripts/benchmark_michi_truth_p1_a49.py`:

```fish
python scripts/benchmark_michi_truth_p1_a49.py --pid $MICHI_PID --scenario pcm_direct --duration 120 --interval 0.1 --out /tmp/michi_f11_direct.json
python scripts/benchmark_michi_truth_p1_a49.py --pid $MICHI_PID --scenario managed_dsp_ai --duration 120 --interval 0.1 --out /tmp/michi_f11_dsp_ai.json
```

El script verifica que el proceso real esté vivo y recolecta CPU/RSS del PID sin entrar en el audio callback. El argumento `--scenario` es una etiqueta del operador, **no** evidencia de que DSP o IA estén efectivos. Sin trazas owner-Qt, latencias callback y XRUN de ALSA, los campos respectivos quedan `NOT_RUN`. No declarar presupuesto p99 ni ausencia de interrupciones sin baseline comparable.

## 5. Certificación exacta y DAC

`verify_michi_truth_product_a49.py` usa una **copia local temporal** del checkout; nunca modifica la original ni GitHub. Ejecución de referencia:

```fish
python scripts/verify_michi_truth_product_a49.py --repo /ruta/al/checkout --patch /ruta/MICHI_SIGNAL_TRUTH_A49_CUMULATIVE.patch --baseline-sha d32228fbcc49c4f107e4295b1a70e31fde4d9b07 --out /tmp/a49_product_gate.json
```

Chequea `AGENTS.md`, `pyproject.toml`, propietarios; `git apply --check`, aplicación, `phase2_context`, AP2/DAC alignment, tests F11 de Qt, regresiones Signal Truth, `git diff --check`, reversión. **No** equivale a KWin live ni CI remoto: ambos tienen gates aparte. Esta ejecución no se completó sobre producto porque no existe checkout íntegro accesible al contenedor.

`execute_michi_truth_r15c_a49.py` lee `F11_SIGNAL_TRUTH_A46_R15C_COVERAGE.json` con 50 oráculos; exige checkout real y mapping explícito de cada ID a un `pytest` nodeid existente; JUnit debe tener tests >0, cero error/fallo/SKIP y exit 0. Si no hay mapping, devuelve `NOT_RUN` y `NO_GO`; incluso 50 software PASS quedarían `SOFTWARE_MAPPING_PASS_PHYSICAL_CI_NOT_RUN`. Para un parche sin commit se permite `--allow-local-patch` **solo** como evidencia local; ningún SHA base falsifica un SHA exacto de A49.

`inspect_michi_truth_dac_a49.py` examina candidate receipts de seis familias: `direct`, `managed`, `shared`, `native_dsd`, `dop`, `dsd_pcm`. Para DoP exige readback de ejecutor y deja explícitamente `receiver_interpretation=NOT_RUN`; un documento alegando bit-perfect o `receiver_verified=True` no eleva el estado. El gate físico seguirá `NOT_RUN` hasta pruebas reales según DAC V3.5.

## 6. Seguridad de Drive

Metadatos confirmados el 2026-11-08:
- Folder `1RULyBtk3YQ8vy71DOAPYDMwnNRk8FFow`: `anyone`, `writer`, `allowFileDiscovery=false`.
- Plan `1K8pxEUwSwtqyMRzuYNDyXAyfJCuhd5MZ`: `anyone`, `writer`, `allowFileDiscovery=false`.
- Patch `1LK9i0sxptqlWSoI_JIdyb2U6GMCJTMzK`: `anyone`, `writer`, `allowFileDiscovery=false`.

**Riesgo:** cualquier persona con el enlace puede alterar los artefactos de código y especificación, la carpeta permite escritura en su nivel. La operación solicitada fue **revisar**, no aprobar la sustitución de accesos. Sin una lista autorizada de destinatarios/permisos no se cambian roles. **OPEN-GOV-01 permanece abierto**; recomendar acceso restringido solo al dueño y colaboradores designados y verificación posterior por SHA y Drive revisions.

## 7. Controles negativos, ambiente y verdad de progreso

- A48+A49 pruebas focales seleccionadas: 110 PASS / 0 FAIL **en fixture sintético**, no en producto.
- Compilación estática de scripts A49: PASS; no existe PySide6, QML runner, KWin, DAC ni host audio de Michi en este contenedor.
- Prueba de muestreador `/proc`: ejecutada sobre proceso `sleep`, nunca atribuida al reproductor.
- Ejecución de suite completa en fixture: aborta con `IndentationError` de fuente de relleno; **no** describe fallo del producto ni PASS total.
- R15C producto `0/50 PASS`, `50/50 NOT_RUN`.
- A49 F11 product integration `NO_GO`; PR245 exact-SHA fuente observada, **CI A49 NOT_RUN**.

## 8. Próximas decisiones y orden bloqueante

1. **P0-01** disponer de checkout completo de PR245, calcular hash del patch A49 y ejecutar `verify_michi_truth_product_a49.py`; si falla `git apply`, resolver usando preimágenes completas, no mediante fixture de relleno.
2. **P0-02** integrar y confirmar los owners F03/F05/OutputSession/Qt, test A→B→A y subprocesos; revisar que A48 no incluya alteraciones cross-phase no aprobadas.
3. **P1-01/02** QML/KWin activo 900×600/200%/DPR, a11y/foco con Qt y cualquier métrica owner en vivo. La propiedad `metricItems` no certifica screenshot.
4. **P1-03** Baseline comparativo DSP OFF/ON con Michi AI real, p99 callback, XRUN, RSS, frames y soak; no cuantificar impacto sin prueba.
5. **P1-05** avanzar FIR/profiles solo tras F05 y Settings owner readback + backend real; mantener gates inactivos.
6. **P0-06/07** mapear 50 oráculos reales, correr R15C, DAC por familia y CI exact SHA **sin saltarse NO_GO**.
7. **GOV** restringir Drive solo tras instrucción explícita sobre accesos; auditar historial y hash.

### Rollback

A49 es una **versión única** acumulativa. Si se instala en un checkout local, aplicar A49 sobre preimagen limpia PR245, jamás aplicar A48+A49 dos veces. Para volver: `git apply --reverse MICHI_SIGNAL_TRUTH_A49_CUMULATIVE.patch` sobre la copia donde esté aplicado; nunca alterar repositorio remoto sin petición.

## 9. Integración ejecutada en checkout real (OpenCode, 2026-11-08)

Esta sección reemplaza el estado "no ejecutado" solo para lo que fue medido localmente. No cambia el veredicto **F11 ACTIVE / PRODUCT NO-GO**.

- Checkout aislado `/tmp/opencode/michi-a49`, rama `ap2-f11/st-a49-integration-20261108`, base PR245 `d32228fbcc49c4f107e4295b1a70e31fde4d9b07`. El checkout principal `main` no fue modificado.
- `git apply --check` falló en 4 archivos porque las preimágenes del patch son de fixture sintético. Se aplicó con `git apply --reject` y se resolvieron manualmente los 3 archivos con rechazos (`output_session_service.py`, `signal_path_bridge.py`, `SignalTruthPopup.qml`); el resto de archivos y assets nuevos se aplicó completo.
- Conflictos de integración resueltos:
  1. Los tres registradores de familia de `OutputSession` publican por `_publish_signal_truth_family(...)`; no queda una segunda escritura directa al recorder.
  2. `SignalPathBridge.__init__` conserva la secuencia `_rebuild` → `_apply_f03_semantics` → `_apply_output_owner_truth` → `_publish_truth_frame` → `_project_f05_capabilities` (contrato A42 de dos publicaciones).
  3. La proyección recibe `captureRevision` antes de publicar, sin una segunda lectura del recorder (contrato A15 de captura única).
  4. El downgrade POR `dspExecutionState` solo aplica cuando el overlay owner A49 está presente; F11 Direct conserva su prueba DSP.
  5. La identidad histórica reconciliada conserva solo la allowlist acotada; no resucita hechos del owner actual.
  6. `SignalTruthPopup` prefiere `canonicalTruthFrame.stages` cuando existe y cae a `signalPathBridge.stages` cuando el bridge F11 de medición no expone `truthFrame`; se restauró el binding `stages: root.stages` que exige el contrato visual.
- Lint: 51 archivos Python modificados/nuevos, `ruff format` aplicado, `ruff check` y `ruff format --check` limpios. No se debilitó la configuración de Ruff.
- Evidencia local medida: 536 pruebas `signal_truth`/`michi_truth` PASS; 1067 pruebas DAC+F11+contratos QML PASS; `test_f11_qml_contract.py` 16 PASS; alineación AP2-F11 **GO** y alineación DAC OK antes del commit.
- R15C con mapa explícito de node IDs: **40 PASS / 10 NOT_RUN / 0 FAIL_or_SKIP**, `overall=NO_GO`. Los 10 no mapeados siguen siendo R15C-16, 20, 22, 23, 24, 31, 32, 34, 37 y 44. Esto es evidencia software de oráculos, no certificación física.
- La suite completa local abortó con SIGABRT en `test_album_browse_identity_modes_runtime.py` por interacción Qt/GStreamer de orden/teardown; ese test aislado pasa. No se declara PASS de suite completa ni de CI.
- Siguen **NOT_RUN**: DAC físico por familia, KWin en vivo, DPR 1/1.25/1.5/2, W1–W9, rendimiento DSP ON/OFF/XRUN, y CI exact-SHA de esta rama. El veredicto permanece **NO_GO** hasta ejecutarlos.
