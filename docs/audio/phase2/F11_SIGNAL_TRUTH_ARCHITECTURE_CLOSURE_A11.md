# Michi Music Player — Signal Truth: cierre de arquitectura y especificación avanzada A11

**ID:** `MICHI-AP2-F11-ST-A11-ARCH-FREEZE` · **Fecha:** 2026-11-06 · **Ámbito:** AP2-F11 · **Revisión:** A11/v1 · **Estado:** `DESIGN_FREEZE_CANDIDATE / CANONICAL_APPROVAL_PENDING / CODE_NOT_ALL_MERGED / NO_GO_F11_CLOSURE`.

> **Naturaleza de este documento:** contrato avanzado **propuesto para revisión** en el repositorio, subordinado a `AGENTS.md`, a la Biblia AP2 R11.1, a las decisiones F03/F05/F09/F10, a M11.3F y DAC V3.5. No constituye por sí mismo una enmienda aprobada, un cambio del clasificador, permiso para fusionar los PR abiertos ni certificación física. El documento acumulativo de Drive A00–A11 continúa siendo el registro de investigación/implementación; este anexo es una especificación de arquitectura para revisión de código, no un plan paralelo.

## A11.0. Registro de evidencia y alcance exacto

| Elemento | Verificación al corte | Implicación |
|---|---|---|
| `main` | `cb5b141a4ee87ad56b4a2b75b5a0ed6538732700` | Estado estable de referencia; NO contiene los PR nuevos |
| PR #239, M0 | `8d578d923ae4ac8f57c385fa220cf76f647ab0d5`, Draft | Auditoría reproducible, gate M0 específico PASS, no merge |
| PR #240, SIM102 | `f4bd6f77c0449a4d2ce33049d044508a6d3d08a3`, Draft | Lint PASS pero test hash F42 y DAC closure NO-GO; no merge |
| PR #241, atomicidad + captura | `b34f434466bfc4ba99e75c4818987ec8e3070088`, Draft | 50/50 tests focalizados, Ruff PASS, no merge |
| `PHASE2_STATE.json` | F00–F10 CLOSED, F11 ACTIVE, F12–F15 LOCKED | El cierre F11 no está autorizado |
| `F11_CLOSURE_READINESS.md` | NO-GO | Las pruebas históricas son válidas para su SHA/alcance, no cierran A11 |
| A05/A10 | 40,00 % global estimado del programa ampliado | Mantener métrica separada de avance arquitectónico y de PRs |

**Distinción de control:** `DESIGN_FREEZE` significa que las decisiones y contratos de este anexo tienen una propuesta suficientemente precisa para revisión e implementación; `CANONICAL_APPROVAL` exige aceptación por los dueños normativos; `IMPLEMENTED`, `CI_EXACT_SHA`, `HARDWARE_PASS` y `CLOSED` son estados independientes.

## A11.1. Decisiones de arquitectura — resolución recomendada y puerta de aprobación

| ADR | Decisión de diseño propuesta | Autoridad / implementación | Estado |
|---|---|---|---|
| `ST-ADR-015` | Recorder único; NO hay segunda instancia ni segundo clasificador, y QML no crea hechos | R11/F03/DAC | `DESIGN_LOCKED; owner sign-off pending` |
| `ST-ADR-016` | `RecorderCaptureState` es una captura **atómica SOLO del recorder**; agregación externa nunca se declara atómica implícitamente | F03 + F11 + Output/Playback | `DESIGN_LOCKED; cross-phase pending` |
| `ST-ADR-017` | Separar `last_committed` de `last_aborted_candidate` sin romper `last_snapshot` sellado; UI histórico usa solo confirmado | F03 / DAC V3.5 | `DESIGN_LOCKED; cross-phase pending` |
| `ST-ADR-018` | Normalización de eventos y read model **profundamente inmutables**, pues el `OutputFamilyEvent` actual posee `runtime_identity: dict | None` mutable | F03 / F05 | `DESIGN_LOCKED; implementation pending` |
| `ST-ADR-019` | El owner Qt recibe **notificación queued explícita**, con token de vida y coalescing de reconstrucción, sin llamar `_rebuild` desde workers | F11 / Qt | `DESIGN_LOCKED; PySide6 gate pending` |
| `ST-ADR-020` | Plan de procesamiento y plan de salida son espacios de nombres independientes; correlación por ejecución, generación y readback | F05 / OutputSession / F11 | `DESIGN_LOCKED; producer link pending` |
| `ST-ADR-021` | El **último estado causal compatible** revoca todo EFFECTIVE anterior; si se perdió el terminal o hay gap, el DSP se muestra `UNCORRELATED/UNKNOWN` | F05 + F11 | `DESIGN_LOCKED; tests pending` |
| `ST-ADR-022` | Un único proyector semántico F03, derivado del recorder, alimenta una o más presentaciones; las cinco secciones F11 son **agrupación UX**, no aristas físicas | F03 + F11 | `DESIGN_LOCKED; port pending` |
| `ST-ADR-023` | Operaciones repetibles, con identidad por instancia; el orden se dibuja solo con evidencia de topología | F05/F10 + F03/F11 | `DESIGN_LOCKED; data producer pending` |
| `ST-ADR-024` | Un `TruthFrame` **family-neutral** separa PCM, DSD Native, DoP carrier y DSD→PCM; nunca rellena PCM inventado | F09/F10/DAC + F11 | `DESIGN_LOCKED; source adaptation pending` |
| `ST-ADR-025` | Calidad nominal, transformación, observación de frontera, prueba de preservación y estado temporal son dimensiones diferentes | F03/M11.5 + F11 | `DESIGN_LOCKED; claims review pending` |
| `ST-ADR-026` | Exportador de diagnóstico por allowlist, sin rutas/tokens/IP/seriales; identidad opaca derivada por exportación | Seguridad/diagnostics | `DESIGN_LOCKED; test pending` |
| `ST-ADR-027` | Nombres propios solo Michi: `TruthGraph`, `SignalTruthProjectionService`, `SignalTruthBridge`, `MichiSignalTruthView`; renombrado coordinado incluye Biblia, tests, wheel y scripts | ST-NAME-001 / R11 | `PRODUCT REQUIREMENT APPROVED; migration pending` |
| `ST-ADR-028` | Preservar sello M11.3F/F42; preferencia por conservar fuente y tramitar una excepción Ruff **hash-scoped y probada**, o reapertura expresa del owner con reseal | M11.3F + DAC + CI | `SOLUTION PROPOSED; DECISION BLOCKED` |
| `ST-ADR-029` | F11 no certifica salida física/analógica ni abre F12–F15; todo claim `MATCHED_COMPLETE` exige autoridad M11.5 y cobertura íntegra | R11 + M11.5/DAC | `FROZEN SCOPE` |

### A11.1.1. Precedencia, conflicto y gobierno

1. El **código `main` vigente** define la preimagen. La Biblia R11 y DAC V3.5 definen permisos y límites, no pueden «corregirse» por conveniencia de UI.
2. `F11_VR_CONTRACTS.md` y `F11_VR_SIGNAL_TRUTH_SPEC.md` describen la condición antigua `effective_plan_id == output_snapshot.plan_id`, contradictoria con la asociación R3 por generación. **Decisión de especificación:** *superseder* explícitamente esas cláusulas, sin borrar historia, después de comprobar el contrato R11 actual; el plan DSP **no** iguala por requisito el plan de salida.
3. Ningún documento A11 reescribe `PHASE2_STATE.json`, `spec.sha256_at_last_transition`, la ruta de la Biblia o el SHA F42. Estos cambios necesitan acto de gobierno propio.
4. Si la enmienda R11 contradice una cláusula vigente F03/F05/M11.3F/DAC, detener en `STOP_SPEC_DRIFT`, identificar dueño y documento, registrar resolución y no fusionar.

## A11.2. Topología por autoridades (no por estética)

```text
SOURCE CHARACTERIZER / DECODER         OUTPUT SESSION + DIRECT / MANAGED / DSD
              |                                      |
              +----------------+---------------------+
                               |
                  RECEIPTS TIPADOS POR OWNER
                               |
                  SignalTruthRecorder (ÚNICO)
                  · SignalTruthSnapshot/clasificador DAC
                  · candidate/active/last legacy
                  · read_capture_state() [PR #241, DRAFT]
                               |
                  CAPTURE COHERENTE DEL RECORDER
                               |
          +--------------------+-------------------+
          |                                        |
  SignalTruthProjectionService              READBACK owners:
  (F03: 4 nodos semánticos                  · AudioProcessingService
   y reason codes 1:1)                     · OutputSession/Playback
          |                                        |
          +---------------------+------------------+
                                |
             TRUTH FRAME PURE JOIN (solo si IDs/gens coinciden)
             · no reclasificación, no IO, fail-closed
             · cinco secciones de disclosure, operaciones DAG opcionales
                                |
                     SignalTruthBridge [QObject OWNER]
                     · mailbox queued, lifecycle token
                     · projection cache por revisión compatible
                                |
           +--------------------+---------------------+
           |                    |                     |
   NowPlaying capsule   SignalTruthPopup       DAC diagnostics/Settings
                            |
                   MichiSignalTruthView (ÚNICO)
```

El nombre final del proyector/bridge seguirá la migración A02. **No instanciar un `SignalTruthProjectionService` adicional con semántica alternativa**: es la evolución/renombrado transaccional del servicio F03, no una autoridad paralela.

### A11.2.1. Tabla de ownership y prohibiciones

| Dato / transición | Único owner productivo | Lectores legítimos | Nunca |
|---|---|---|---|
| Plan de output y binding | OutputSession/planificadores, DAC V3.5 | recorder y proyector | QML «corrige» ALSA |
| Hechos decodificados y fuente | characterizer/decoder real | recorder, proyector | sufijo de archivo prueba PCM efectivo |
| Veredicto `DIRECT/DSP/...` + `ST_*` | clasificador `domain/signal_truth.py` | servicio semántico, UI, diagnóstico | nuevo enum de veredicto en QML |
| DSP `REQUESTED/PREPARING/EFFECTIVE/BYPASSED` | `AudioProcessingService` y child readback | recorder/events, proyector | draft EQ se pinta como efectivo |
| Estado playback (`PLAYING/PAUSED/STOPPED`) | PlaybackService / Session | F11 read model | recorder decide play/pause |
| Captura recorder | `SignalTruthRecorder` | proyector/Qt owner | se inventa un segundo store |
| Grafos 4-nodos y reasons | proyector F03 | F11/DAC diagnostics | F11 altera razón o arista normativa |
| Disposición visual/capacidades | bridge F11 + QML existente | UI | asignar DSP/DoP desde color/icono |
| Prueba bit-perfect, muestras, salida física | M11.5 / DAC-F14 según fase | UI como reporte explícitamente scoped | `RUNNING` o `ALSA hw_params` se promueve a fidelidad |

## A11.3. Contrato técnico `TruthFrame v1` (propuesto, no ABI del HEAD)

Archivo acompañante: `docs/audio/phase2/F11_SIGNAL_TRUTH_FRAME_V1.schema.json`, versión `michi.truth_frame.v1`. El frame es **derivado**, no se persiste como fuente de verdad ni se inyecta de vuelta a owners.

### A11.3.1. Campos cerrados del read model

| Campo | Tipo y semántica |
|---|---|
| `schema` | literal `michi.truth_frame.v1` |
| `capture_revision` | entero monotónico dentro de una instancia de recorder; **no** reloj global ni número de playback |
| `temporal` | `NOT_ACTIVE / PENDING / ACTIVE / HISTORICAL`; `PAUSED` es una subetiqueta de reproducción, no prueba de muestras |
| `consistency` | `RECORDER_ONLY / CORRELATED / PARTIAL / CONFLICTED`; agregación cross-owner tiene su propia evidencia |
| `identity` | identidad completa output o `null` cuando no hay snapshot; jamás reutilizar epoch por título |
| `family` | `SHARED / DIRECT_PCM / MANAGED_PCM / NATIVE_DSD / DOP / DSD_TO_PCM / UNKNOWN` |
| `source` | hechos nominales separados de PCM efectivamente decodificado; DSD no se transforma en falso PCM |
| `dsp` | `state`, `correlation`, `readback_proven` y `processing_plan_id`; `CONFIRMED` requiere múltiples fences |
| `route` | frontera más alta realmente observada, nunca «hasta DAC interno» por ruta ALSA |
| `quality` | clase nominal, veredicto DAC existente, prueba de preservación independiente |
| `operations[]` | instancias únicas, tipo, estado, evidencia y predecesores **solo con orden sustentado** |
| `stages[]` | cinco grupos UX como máximo contractual base; extensiones dinámicas sujetas a datos |
| `reason_codes[]` | copiados 1:1 del clasificador, en mismo orden, sin razones nuevas de Qt |
| `provenance[]` | dueño, frontera, generación y referencia opaca; nunca secretos o rutas personales |
| `blockers[]` | faltantes, contradicciones, gap o fase no autorizada; sin inventar ceros/false |

**Null vs UNKNOWN:** `null` significa ausencia de hecho tipado; `UNKNOWN` comunica decisión de presentación. `NOT_OBSERVABLE` exige que el owner declare que esa frontera no está expuesta; no confundirla con error ni ausencia temporal de eventos.

### A11.3.2. Regla de captura y consistencia inter-owner

El PR #241 proporciona una lectura atómica de candidate/active/last/streams **solo para el recorder**. El estado del reproductor, el dispositivo activo y DSP siguen en owners distintos. Por ello:

1. Leer `capture_a=recorder.read_capture_state()` en el **hilo owner de presentación**; elegir `active`, luego `candidate`, luego `last_committed`, nunca el `last_snapshot` heredado para decidir «Última reproducción».
2. Leer status/output/DSP **sin bloquear el audio**. Obtener sus `execution_id/epoch/host/pipeline/binding` y revisión si están disponibles.
3. Leer `capture_b=read_capture_state()`. Si `revision` cambió, reintentar *una vez* en el siguiente tick Qt; no bucle ocupado ni afirmar consistencia. Si no cambió pero faltan scopes de otros owners, `consistency=PARTIAL`.
4. Sólo `CORRELATED` cuando todos los hechos usados para claims positivos comparten el **mismo** execution/binding/host/pipeline bajo contratos documentados. Si un owner no provee generación, degradar los claims dependientes a `UNKNOWN/UNCORRELATED` aunque source y formato sean coincidentes.
5. La UI puede mostrar una captura del recorder `RECORDER_ONLY` honesta mientras faltan owners, sin extrapolar lo no confirmado. Un conflicto de identidad produce `CONFLICTED`, revoca success badge y conserva razones.

**Inmutabilidad profunda:** `RecorderCaptureState` y `OutputFamilyEvent` usan dataclasses frozen, pero `runtime_identity: dict|None` es mutable. Antes de hacer un `TruthFrame` compartible, copiar sus valores primitivos a tuplas inmutables/DTO cerrados y **no compartir** el dict original; `MappingProxyType` no resuelve automáticamente el problema de serialización, y `frozen=True` no protege la estructura recursiva.

**Brecha identificada en A10:** `activate_execution()/retire_execution()` deben comprobarse frente a `_capture_revision` cuando cambian las mediciones retenidas visibles. El contrato de monotonicidad será un test rojo específico, no una afirmación de cobertura completa hasta ejecutarlo.

### A11.3.3. Máquina temporal y precedencia explícita

```text
SIN_EJECUCIÓN: identity=null, temporal=NOT_ACTIVE, fidelity=NOT_ESTABLISHED
BEGIN(A)         → PENDING(A)            [nada efectivo]
OBSERVE(A)       → PENDING(A)            [evidencia no compromete]
COMMIT(A)        → ACTIVE(A)             [owner autoriza ejecución]
BEGIN(B)         → ACTIVE(A) + PENDING(B) [UI principal A; detalle B pending]
DISCARD(B)       → ACTIVE(A) + ABORT(B)   [B nunca last playback]
RETIRE(A)        → HISTORICAL_COMMITTED(A)
HOST_LOSS(A)     → terminal/contradicted; jamás se conserva «Live» obsoleto
PAUSED(A)        → ACTIVE(A) con subestado paused si PlaybackService coincide
STOPPED(A)       → no PLAYING; si recorder no retiró aún, PARTIAL/CONFLICTED
REPLACE_A→B→A    → tres identidades/epochs distintas, sin reutilizar receipts
```

Un snapshot histórico no se convierte en activo por tener `output_family_event=RUNNING` viejo. Dos ejecuciones A y B coexistentes se muestran como lanes separadas, nunca se mezclan por frecuencia o nombre. Un candidato descartado aparece en diagnóstico de intentos, no como playback histórico.

## A11.4. Identidad, DSP y revocación causal

### A11.4.1. Namespaces y método de correlación

```text
OUTPUT:   plan_id + execution_generation + port_generation
          + binding_generation + stable_device_id + endpoint_signature
FAMILY:   execution_id + device_id + family + state
DSP:      processing_plan_id + processing_generation + host_generation
          + pipeline_generation + runtime_identity + readback_proven
FUTURO:   event_sequence y execution_id por productor, si el owner los autoriza
```

**Regla:** dos cadenas de caracteres iguales en ámbitos diferentes no constituyen un vínculo. El cambio A→B del mismo plan no autoriza DSP de A para B. `host_generation` y `pipeline_generation` son dimensiones distintas; equivalencia con `port_generation` se prueba por contrato del productor, no por que ambos contengan el entero 7.

### A11.4.2. Algoritmo de asociación DSP — sin falsos positivos

1. Si la captura no está `ACTIVE`, `dsp.correlation=UNCORRELATED` y nunca `CONFIRMED`.
2. Si el service no está `effective` con revisión/readback válido, tratar `BYPASSED`, `PREPARING`, `UNAVAILABLE` o `UNKNOWN` conforme al estado actual, sin reciclaje de EFFECTIVE.
3. Obtener el **último evento causal** del scope que enlaza execution, host y pipeline. El stream actual no incluye `execution_id/event_sequence` en todos los productores: si falta el vínculo exigido para una afirmación fuerte, estado `UNCORRELATED` mientras se tramita extensión de dueño F05/OutputSession.
4. Un evento terminal `BYPASSED/UNAVAILABLE`, un host perdido, una generación supersedida o un gap de secuencia invalida un EFFECTIVE anterior; no filtrar terminales y luego buscar «el último EFFECTIVE que queda».
5. `CONFIRMED` exige state=EFFECTIVE, plan DSP del mismo namespace, generación/ejecución verificadas, `readback_proven=true` y ninguna revocación posterior. Únicamente confirma DSP aplicado, no fidelidad.
6. **No** comparar DSP `effective_plan_id` con output `snapshot.plan_id`. Los documentos F11 anteriores que lo exigen necesitan enmienda de supersesión versionada.

**Retención y gaps:** las listas de eventos DSP y familia están acotadas a 64 entradas, mediciones a 16; el truncamiento puede ocultar una invalidación anterior. El join necesita un `last_terminal_sequence` / `stream_floor_revision` o evidencia equivalente del owner para poder decir que los eventos retenidos son suficientes. Si falta: `UNCORRELATED`; nunca reconstruir una continuidad por timestamp de pared.

## A11.5. Publicación segura en Qt y rendimiento

### A11.5.1. Contrato `owner-mailbox` — no callback directo a QObject

```text
RECORDER._publish(callback sin Qt) en worker
    → callback escribe únicamente high_watermark revision en mailbox pequeño
    → schedule una señal Qt (queued) al objeto Relay que YA vive en owner
    → @Slot() OWNER verifica alive_token / weak guard
    → read_capture_state() / join F03-F05-Output
    → _rebuild() únicamente en owner Qt
    → emitir state_changed una sola vez por revisión observada
```

Prohibido usar `QTimer.singleShot(0, callback)` desde un worker como si garantizara el hilo owner: el timer depende del hilo que lo crea y de su event loop. Usar `Qt.QueuedConnection` sobre un receptor QObject realmente afiliado al hilo de aplicación, con prueba `QThread.currentThread() == bridge.thread()` y test `threading.get_ident()`.

- **Coalescing:** se agrupan solicitudes repetidas de *rebuild*, no mutaciones ni hechos en el recorder; la señal de invalidación terminal debe sobrevivir, al menos como revisión/recibo retenido, aunque visualmente se muestre el último frame. Si la cola de terminales no está aún versionada, no prometer reproducción forense de cada transición.
- **Teardown:** antes de destruir la vista incrementar `alive_token`, marcar disposed, cancelar nuevas solicitudes, desconectar productor y limpiar la bandera scheduled; callbacks ya en cola comprueban token y no tocan un QObject destruido. Crear/destruir 1000 veces en test real.
- **Recursividad:** un callback reentrante no mantiene lock del recorder; dos publishers simultáneos provocan como máximo un rebuild en curso y una re-evaluación final.
- **Fallo de dispatcher:** registrar degradación y bloquear afirmaciones de frescura; *nunca* fallback a `_rebuild` inline desde audio worker.
- **RT:** no usar Python QObjects, IO, locks prolongados, file access, JSON o DSP por buffer en callback de audio; una cola de control fuera de callback o productores no-RT entregan el recibo.
- **Mediciones:** las mediciones de p50/p95/p99 y p99.9, XRUN, CPU/RSS y dropped events se comparan con baseline equivalente. Objetivos de A03 (p95 ≤2ms con 5–20 etapas, p99 ≤8ms con 50, hasta 10 Hz en ráfagas) son **presupuestos propuestos**, NO resultados certificados. Bajo terminal crítico, no retrasar invalidación por un throttle global de 100ms.

### A11.5.2. Invariantes de threading obligatorias

`T01` recorder no necesita Qt ni ejecuta callbacks bajo RLock. `T02` ningún mutador de QObject fuera del owner. `T03` notificación de worker encolada y no bloqueo del productor. `T04` pérdida de UI no rompe salida; sin `disconnect` fantasma. `T05` coalescing conserva snapshot final y aviso terminal. `T06` no reconstrucción después del dispose. `T07` reproyección recupera fallos sin falsa etiqueta verificadora.

## A11.6. Grafo de operaciones y proyección unificada

- `TruthGraph` (nombre final A02) es el DTO semántico F03 renombrado, con **4 nodos normativos** actuales `SOURCE/DECODE/ENGINE/DEVICE` y mapping exhaustivo `SignalTruthReason -> primary node`; la UI F11 ordena **5 secciones informativas** `SOURCE/DECODE/PROCESSING/OUTPUT/DEVICE` sin afirmar que sean cinco filtros físicos enlazados.
- Reuse en un único adaptador puro: `SignalTruthProjectionService.project(snapshot)`, seguido de `project_truth_frame(capture, receipts)`; no segunda clasificación de `verdict`. Antes del rename, ejecutar pruebas diferenciales 1:1 contra el proyector de F03.
- `operation_instance_id` obligatorio por instancia, estable dentro del execution epoch y distinto para SRC1/SRC2, FIR1/FIR2. `predecessors[]` únicamente de conexiones **observadas** con mismo epoch/host/pipeline; sin esa prueba, `order_state=UNKNOWN`, predecesores vacíos, chips de «operaciones observadas sin orden comprobado».
- Rechazar DAG con ciclos, IDs duplicados, predecesor inexistente o de generación ajena. No inferir orden de factories, flags, arrays ni posición visual del QML.
- Evidencias de `audiofirfilter` certifican como máximo presencia informada del factory; no carga de IR, kernel, impulse response, latencia o audio realmente convolucionado sin recibo/medición del dueño.
- Outputs: `stages[]` y `reason_codes[]` son funciones deterministas de una captura y sus receipts tipados. Tests de idempotencia, orden y snapshots golden contra R10 antes de reemplazar la vista.

## A11.7. Matriz family-neutral de fronteras y afirmaciones

| Familia | Fuentes admisibles | Evidencia suficiente para «observado» | Sin evidencia | Negación obligatoria |
|---|---|---|---|---|
| Shared/Qt | engine real + estado provider | estado de engine; formato si expuesto | `PARTIAL/NOT_OBSERVABLE` | no exclusividad ALSA por analogía |
| MPD | MPD owner + port | receipt real, endpoint solo si observable | `UNKNOWN` | no inferir salida por selección |
| Direct PCM | recorder + ALSA V3.5 | decoded tuple, engine efectivo, binding y negotiated | frontera parcial | no bit-perfect por DIRECT |
| Managed PCM | output-family + host | ejecución RUNNING de mismo ID y tuple/readback compatible | `UNCORRELATED` | READY no es ejecución efectiva |
| Managed + DSP | F05 + output-family | readback DSP por ejecución/pipeline sin terminal posterior | `UNCORRELATED` | factory o preset no prueban DSP |
| Native DSD | F09 executor/host | DSD source, familia Native real, session y device recibos | `REQUESTED/UNKNOWN` | no fabricar PCM ni interpretación DAC |
| DoP | F09 executor + carrier | DSD origen, packing/carrier y marcadores si medidos | `CARRIER_UNVERIFIED` | carrier PCM no demuestra modo DAC DSD |
| DSD→PCM | F10 planner + host | decoder DSD→PCM efectivo, PCM tuple y salida | `CONVERSION_UNOBSERVED` | no EQ «aplicado» por policy |
| Handover A→B | output/session | release predecessor + commit target con IDs | `PENDING/CONFLICTED` | no mezclar readback A con B |

**Regla de afirmaciones:** `source_quality` (nominal), `path_verdict` (clasificación del recorder), `last_observed_boundary` (prueba de transporte) y `fidelity_proof` (autoridad M11.5/DAC) son cuatro ejes independientes. Mínimo autorizado por F11: `NOT_ESTABLISHED` o `CONTRADICTED` para fidelidad; `MATCHED_PARTIAL/MATCHED_COMPLETE` solo al consumir una evidencia de M11.5 autorizada, con cobertura de frames/canales/tramo y alcance explícito. Ninguna prueba analógica se infiere de `hw_params`.

## A11.8. Contrato avanzado UX/diagnóstico

**Un renderer:** `MichiSignalTruthView.qml` tras migración; hoy el antiguo componente está activo. `SignalTruthPopup.qml`, NowPlayingBar y diagnóstico DAC consumen **el mismo `TruthFrame` derivado**, con densidad distinta, no proyectores paralelos.

- NowPlayingBar: 154 px sin tercera fila, sin scroll ni relayout del transporte; capsule responde al estado, no a `hasTrack` ni color de codec.
- Inspector: cinco secciones de disclosure con header/footer fijos, scroll solo del cuerpo, anchura inicial ~480 px acotada al overlay, 900×600 y DPR 1/1.25/1.5/2 con QA real. Pointer modal sin dim ni click-through; foco vuelve al opener; Enter/Space/Esc/Tab y lector de pantalla.
- Estados: `ACTIVE`, `PENDING`, `HISTORICAL`, `NOT_ACTIVE`; PAUSED es señal adicional del propietario Playback, `last_aborted_candidate` se limita al diagnóstico. `order_unknown` se anuncia textualmente, no flechas físicas.
- Wording: «Ruta observada hasta [frontera]», «DSP aplicado · recibo confirmado», «Procesamiento sin vínculo verificable», «Formato de fuente nominal», «Fidelidad no establecida», «Última reproducción · histórico», «Intento de salida fallido». El indicador `Verified path` no autoriza un claim físico o de muestras.
- Recursos: tokens `MichiPalette`, `MichiSemanticColors`, `MichiSpacing`, `MichiRadius`, `MichiTypography`, `MichiMetrics`, `MichiMotion`, Inter y Tabler licenciado. Sin tema nuevo, sin gráficos copiados de Roon ni comparación implícita de marca.
- Acciones: `NONE/OPEN_ENGINE/OPEN_PROCESSING/OPEN_OUTPUT/OPEN_DEVICE_SETUP`, solo intents hacia dueños existentes, condicionados a capability. Nunca crear un botón que inicie DSD→PCM implícitamente.

### A11.8.1. Diagnóstico seguro

La exportación usa una allowlist: schema/version, SHA abreviado del build, family/codec nominal, states, generaciones **no vinculables externamente** o hashes efímeros por export, reason codes, tipos de eventos, límites, missing evidence, métricas agregadas y `redacted=true`. Prohibido incluir nombre de pista/archivo, ruta bibliográfica, usuario, hostname, IP, token, serial USB sin autorización, `runtime_identity` dict bruto, datos PCM, credentials y payloads GStreamer arbitrarios. Modo local ampliado opt-in solo bajo nueva especificación. No cargar telemetría automáticamente a servicios externos.

Retención **por defecto en RAM**: últimos eventos DSP/familia acotados 64, medidas acotadas 16 según fuentes actuales; cualquier nuevo buffer terminal exige límite/version/schema y criterio de descarte explícito, con `dropped_count` observable. El logger nunca registra hechos sensibles sin redacción.

## A11.9. Resolución del bloqueo F42 y negociación del cierre normativo

**Hallazgo confirmado:** PR #240 corrige Ruff SIM102 en GStreamer pero altera bytes de archivo con sello M11.3F: `test_f42_no_adapter_source_changes` falla. Aquel PR NO debe fusionarse en su estado actual ni «actualizar hash» automáticamente. `main` mantiene el archivo sellado.

**Ruta preferente sometida a aprobación** (`A11-F42-B`): preservar GStreamer byte a byte e introducir solo una excepción Ruff acotada a `SIM102` en **ese archivo** bajo guardia CI de SHA del archivo completo y auditoría negativa: 1) confirmar hash sellado vigente; 2) medir exactamente UNA infracción base y compararla con una huella del snippet/ubicación; 3) CI debe seguir detectando infracciones nuevas o diferentes; 4) dueño M11.3F + AP2/DAC aprueban el alcance; 5) mantener 4/4 CI con los checks sin SKIP artificial. La excepción genérica por archivo, sin guardia negativa, NO está autorizada por esta propuesta.

**Alternativa `A11-F42-A`:** owner reabre expresamente adaptador y sello, registra compatibilidad en ADR, exige regresiones de motor y DAC más pruebas físicas aplicables y reseal legítimo. No es trabajo de F11 aislado.

**Tercera decisión válida: `STOP_SPEC_DRIFT`**, si ninguno de los propietarios ratifica A/B; los PR continúan Draft, la arquitectura puede revisarse pero no fusionarse.

## A11.10. Migración de nombres y compatibilidad

Obligación **ST-NAME-001** ya aprobada por producto: renombrar servicio y DTO de F03, Bridge Qt, QML renderer, output properties, bootstrap, recursos, tests, scripts y referencias canónicas. El M0 detectó **275 coincidencias léxicas en 30 archivos** para clasificar, no 275 bugs. El nombre histórico solo se permite en documentación contextual y procedencia.

**Paquetes atómicos**: `N00` inventario exacto imports/QML/resources/wheel; `N01` ADR y migración de ruta de Biblia con autoridad R11; `N02` refactor semántico DTO/servicio; `N03` bridge Qt/context; `N04` QML/NowPlaying/DAC; `N05` OutputBridge y settings; `N06` test/gate de cero referencias en árbol y wheel; `N07` snapshots KWin/review; `N08` release gate. No aliases persistentes ni dos Biblias en la distribución.

**Atención a SHA histórico:** el campo `PHASE2_STATE.spec.sha256_at_last_transition` no es un campo de cache del nombre nuevo; no se recalcula hasta que una transición normativamente autorizada exija actualizarlo con su justificación histórica. No alterar `CLOSED` de F03/F10 o fases LOCKED por un cambio nominal.

## A11.11. Catálogo de pruebas de aceptación y falsación

| ID | Caso de falsación | Gate / salida esperada |
|---|---|---|
| `AT-ST-A11-01` | A→B→A reutilizando plan/endpoint pero otra generación | recibo viejo descartado; identidad actual intacta |
| `AT-ST-A11-02` | dos eventos `observe` simultáneos | no se pierde ningún hecho válido |
| `AT-ST-A11-03` | commit y `observe` intercalados | receipt termina en ACTIVE exacto, no candidato resucitado |
| `AT-ST-A11-04` | retiro/host loss y `observe` tardío | terminal prevalece, no revive ACTIVE |
| `AT-ST-A11-05` | candidato abortado después de A confirmado | `last_committed=A`, `last_aborted_candidate=B` |
| `AT-ST-A11-06` | se modifica `runtime_identity` dict después de publicar | TruthFrame mantiene copia inmutable |
| `AT-ST-A11-07` | `retire_execution` elimina mediciones | `capture_revision` avanza y cap se actualiza |
| `AT-ST-A11-08` | status Playback cambia entre doble lectura recorder | `PARTIAL`, no estado falsely correlated |
| `AT-ST-A11-09` | worker notifica al Qt bridge | `_rebuild()` solo en `QThread` owner |
| `AT-ST-A11-10` | 1000 subscribe/dispose bajo ráfaga | no leaks ni QObject destruido invocado |
| `AT-ST-A11-11` | mailbox lleno con un host lost terminal | terminal no desaparece en éxito visual |
| `AT-ST-A11-12` | dispatcher de DSP falla | jamás fallback `_rebuild` inline al worker |
| `AT-ST-A11-13` | DSP plan ID ≠ output plan ID, generaciones sí coinciden | no contradicción por comparación de strings |
| `AT-ST-A11-14` | EFFECTIVE seguido de BYPASSED/UNAVAILABLE | último estado revoca claim anterior |
| `AT-ST-A11-15` | DSP host/pipeline/exec no ligado | `UNCORRELATED` y no `CONFIRMED` |
| `AT-ST-A11-16` | truncamiento de ring elimina terminal/genera gap | claim positivo revocado/UNKNOWN |
| `AT-ST-A11-17` | F03 reason codes antes y después de rename | correspondencia 1:1, misma razón/veredicto |
| `AT-ST-A11-18` | dos SRC, dos FIR sin orden conocido | instancias separadas, ningún edge causal inventado |
| `AT-ST-A11-19` | DAG con ciclo o predecesor extranjero | rechazo/orden UNKNOWN, nunca cadena dibujada |
| `AT-ST-A11-20` | Shared sin ALSA exclusivo | sin `ALSA negotiated` ni `bit-perfect` |
| `AT-ST-A11-21` | Native DSD sin PCM decodificado | ninguna etapa PCM ficticia |
| `AT-ST-A11-22` | DoP carrier observado sin modo del DAC | «carrier observado», receptor `UNKNOWN` |
| `AT-ST-A11-23` | DSD→PCM solicitado pero no adoptado | conversión y EQ no efectivo |
| `AT-ST-A11-24` | ALSA tuple exacto con fuente lossless | no `MATCHED_COMPLETE` automático |
| `AT-ST-A11-25` | fichero FLAC 24/96 nominal con resampling observado | calidad fuente y modificación separadas |
| `AT-ST-A11-26` | export JSON con ruta/token/IP/serial | veto por allowlist y prueba negativa |
| `AT-ST-A11-27` | QML wheel con antiguo identificador/tipo | naming gate falla y empaquetado bloqueado |
| `AT-ST-A11-28` | código GStreamer cambiado sin ADR F42 | sello falla (NO actualizar hash) |
| `AT-ST-A11-29` | CI target pasa pero full CI/R11 falla | no merge ni F11 CLOSED |
| `AT-ST-A11-30` | KWin a 900×600, 200%DPR, teclado y popup externo | cero clipping/pointer bleed/foco perdido |

**Oráculos adicionales:** `RECORDER_ONLY != CORRELATED`, unknown ≠ false, source nominal ≠ decoded actual, carrier DoP ≠ PCM musical, `RUNNING` ≠ prueba de fidelidad, UI temporal ≠ owner de playback, `Qt queued` ≠ entrega probada sin test con thread ID.

## A11.12. Plan de adopción y criterio de cierre de arquitectura

### Paquetes de decisión (sin cambiar el porcentaje productivo por documentación)

| Corte | Decisión y entregable | Puerta |
|---|---|---|
| `SPEC-S0` | Validar texto A11, schema, fixtures y dependencias | Schema/meta + tests PASS |
| `SPEC-S1` | Rescatar cláusulas antiguas F11 sobre IDs/last/history con tabla de supersesión | Dueños AP2/F03/F05/DAC revisan |
| `SPEC-S2` | Aprobar solución F42 A/B o STOP en ADR | M11.3F/DAC explícitos |
| `SPEC-S3` | Ratificar tipos captura/correlation, frozen conversion y mailbox Qt | F03/F05/F11 + tests PySide6 |
| `SPEC-S4` | Aprobar nomenclatura y transacción de Biblia/wheel | ST-NAME-001/R11 verifiers |
| `SPEC-S5` | Aprobar pruebas de claims por familia y límites de M11.5 | propietarios F09/F10/DAC |
| `SPEC-S6` | Firmar especificación con SHA exacto + matriz de resoluciones P0/P1 | arquitectura `ARCH_CLOSED` |

`ARCH_CLOSED` requiere **S0–S6 cerrados con evidencia**, pero todavía no `AP2-F11 CLOSED`. El desarrollo avanza después: M1 Qt, M2 DSP causal, M3 proyector, migración nombres, matriz familias, UI/KWin/RT y CI total. Mantener `MAIN_IMPLEMENTATION_ESTIMATE = 40,00 %` de A05/A10 hasta integrar y recalibrar las capacidades, con incertidumbre ±10 puntos.

### Decisión binaria de esta adenda

- **GO:** publicar la documentación y el schema como PR `DRAFT` de arquitectura; ejecutar tests sobre el schema; solicitar aprobación de los ADR y resolver documentación contradictoria.
- **NO-GO:** marcar Biblia/PHASE2_STATE nuevos, sellar F42, fusionar cambios cross-phase, habilitar claims físicos o declarar F11 cerrado sin los owners y gates.

**Fin del documento técnico A11.**
