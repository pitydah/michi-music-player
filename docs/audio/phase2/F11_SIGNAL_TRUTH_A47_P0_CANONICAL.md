# AP2-F11 · MICHI SIGNAL TRUTH · ESPECIFICACIÓN CANÓNICA P0 A47

**Naturaleza:** contrato de implementación candidato para revisión normativa. No sustituye `AGENTS.md`, Biblia AP2 R11-F11, F03/F05/F09/F10, M11.5 ni DAC V3.5 hasta aprobación formal de sus dueños. A47 **cierra el diseño de los siete P0 del plan**, no certifica integración con el producto ni prueba física.

**Fuente de reconciliación estática:** PR #245, SHA `d32228fbcc49c4f107e4295b1a70e31fde4d9b07`. `SignalTruthRecorder`, `SignalPathService`, `SignalPathBridge` y `F11_CLOSURE_READINESS` inspeccionados; F11 sigue `ACTIVE / NO-GO`. El PR no es `main` y no equivale a trabajo aprobado. El parche A47 acumulado depende de esa preimagen y no debe aplicarse por inercia.

**Prohibiciones:** ningún commit, PR, push, merge, cambio de branch o escritura en GitHub; no borrar ni renombrar el corpus histórico; no reconfigurar DAC/ALSA/GStreamer; no segunda autoridad de audio; no lanzamiento de F12–F15; no promesas físicas/analógicas mediante prueba de software.

## 0. Tabla de cierre P0: qué queda resuelto y qué no

| ID | Requisito crítico | Decisión final de diseño A47 | Demostración offline | Gate productivo |
|---|---|---|---|---|
| `P0-ARCH` | Autoridad y arquitectura | Una autoridad (`SignalTruthRecorder`), proyección semántica F03, F05 DSP, OutputSession, F11 adapter/Qt | Inventario y ADR, sin autoridad paralela | `NOT_RUN` |
| `P0-SCHEMA` | Modelo único | Envelope tipado v1, identidad/epochs/branch/operaciones/evidencias/familia y cambios versionados | Validador estructural con negativos | `NOT_RUN` |
| `P0-OPS` | DSP dinámico | N operaciones repetibles por ID/branch/generation, DAG sólo por recibo explícito, repetibles 2 SRC/PEQ/FIR | Ciclos, duplicados, falta de orden, adopción falsa | `NOT_RUN` |
| `P0-FAMILIES` | Familias de audio | PCM Direct/Managed/Shared; DSD→PCM; Native; DoP; lenguaje de evidencia diferente por familia | Contrato estricto y casos negativos por transporte | `NOT_RUN` |
| `P0-FIDELITY` | Fidelidad | Oráculo de cobertura exacta digital, sólo M11.5 puede emitir prueba productiva; DAC analógico separado | Fixture PCM multi-canal y gaps, negativo DSD | `NOT_RUN` |
| `P0-CERT` | Certificación | 50 R15C con oráculo/owner/gate; estado NOT_RUN, no suma artificial de casos | Matriz machine-readable y tests de integridad | `NOT_RUN` |
| `P0-DELIVERY` | Entrega implementable | Orden M0→M12, allowed/forbidden, preimage check, red→green, rollback, GO/STOP | Script de validación y recibo de package | `NOT_RUN` |

Las decisiones son `SPECIFIED` o `STATIC/SYNTHETIC_VERIFIED`, nunca `INTEGRATED` o `PHYSICAL_VERIFIED`. Es improcedente llamar «P0 productivos corregidos» a la tabla anterior. Las modificaciones de código en A47 son validadores/fixtures candidatos, no productores runtime autorizados.

## 1. Arquitectura cerrada — `P0-ARCH`

```text
Source/Decoder ───────┐    F05 AudioProcessing ────┐
GStreamer/ALSA ───────┼──> SignalTruthRecorder <───┼─ OutputSession/executors
F09/F10 family receipts┘       ÚNICO           ──────┘
                                | immutable classified capture + epochs
                                v
                     F03 SignalPathService.project()
                          4 nodos semánticos
                                |
                      F11 TruthFrame read model
                  5 anclas UI + operations[] repetibles
                                |
                 Qt owner-thread SignalPathBridge
                   /         |             \
             NowPlaying  SignalTruthPopup  Diagnostics
                                |
                     NO DSP/output commands
```

1. `SignalTruthRecorder`: dueño de la aceptación de hechos, candidate/active/history, identidad, revisión, motivos y clasificador existente. **No clonarlo, no sustituir el criterio M11.5**.
2. `SignalPathService` (F03): dueño exclusivo del mapeo `SignalTruthReason`→nodo y de `verdict` semántico. `SignalPathBridge` no recalcula clasificación de audio, ni deduce hechos de badges.
3. `AudioProcessingService` (F05): dueño de solicitado, plan construido, `readback_proven`, adoptado/renderizado, generaciones y revocación; **plan DSP y plan de salida son namespaces distintos**.
4. `OutputSessionService`: dueño de ejecución y estado `PREPARING/READY/RUNNING/RELEASED`, familia y binding exactos. No deducir adopción DSP por igualdad casual de enteros o por nombre del DAC.
5. F09/F10/M11.5/DAC: dueños de modo Native/DoP/DSD→PCM, negociación y prueba de muestras en la frontera que instrumentan. F11 sólo presenta esos hechos.
6. `TruthFrame`: representación inmutable, sin `QObject`, sin clasificación propia. Las cinco secciones son UX; N operaciones anidadas son hechos/adiciones sólo cuando hay recibos y época coherente.
7. `SignalPathBridge` y QML: únicamente adaptación owner-thread, presentación, navegación a owners de Settings/Devices, sin control de audio oculto.

### Propiedades atómicas y límites de concurrencia

- Un `RecorderCaptureState` debe contener candidate/active/last + eventos y revisión observados bajo un mismo lock o snapshot inmutable. `begin_candidate/commit_candidate/retire_active` ya usan `_lock` en PR245 según auditoría A45: la advertencia A01 de «sin lock» está **supersedida** para esa preimagen. No reescribir código que ya cumple sin un test rojo.
- Callbacks se invocan fuera de locks; cada transición a Qt ocurre por owner-thread. Nunca hacer espera, JSON, hashing de grandes buffers, enumeración ALSA, QML ni mutex de larga retención en callback RT.
- A→B→A reutilizando `plan_id` **no** recicla `execution_generation`, `route_epoch` ni binding. Evento tardío de A1 jamás modifica A2; los terminales recientes revocan los recibos positivos antiguos.
- `F05 MOTOR_EFFECTIVE` no se promociona a `CURRENT_EXECUTION_CONFIRMED` sin vínculo emitido por owner OutputSession + continuidad certificada por recorder. A47 no crea esos certificados; son un gap productivo explícito.
- Cinco nodos F11 + etapas legacy A46 `resample/channel-remap/fir` seguirán por compatibilidad hasta que los propietarios autoricen migración a `operations[]`. No pintar ambas listas como dos cadenas causales independientes.

## 2. Esquema de evidencia v1 — `P0-SCHEMA`

**Identidad versionada mínima** de todo envelope AP2-F11:

```yaml
schema: michi.signal_truth.p0.v1
status: ACTIVE  # ACTIVE | PENDING | HISTORICAL | NOT_ACTIVE
identity:
  output_plan_id: output.123      # namespace exclusivo OutputSession
  execution_generation: 11       # generación efectiva, >0
  port_generation: 8             # F03/host port coherente, >0
  binding_generation: 3          # enlace a dispositivo/puerto, >0
  media_epoch: 9                 # pista/cambio de contenido, >0
  route_epoch: 17                # cambio de ruta/transfer/hotplug, >0
  branch_id: main                # futuro crossfade/multiroom, NO singleton implícito
  endpoint_stable_id: dac.local.01
family: ...
operations: []
fidelity:
  claim: UNPROVEN                # A47 nunca fabrica M11.5
  dac_analog_verified: false
```

El código original tiene `SignalTruthIdentity.plan_id/execution_generation/port_generation/binding_generation/stable_device_id/stable_endpoint_signature`. Los campos nuevos no se declaran existentes: **ADR de migración**: los adaptadores deben tomar sólo los valores existentes verificados; `media_epoch`, `route_epoch`, `branch_id` u otros faltantes se mantienen `UNOBSERVED` y bloquean la nueva atribución fuerte hasta que el dueño de fuente emita receipts. No derivarlos de timestamp, título, ruta, display name ni posición en lista.

**Campos por operación** (el verificador A47 exige identificación, clase, recibo, formato opcional y edges verificados):

```yaml
operation_instance_id: src.1
kind: resample                  # admite 0..N instancias del mismo kind
branch_id: main
execution_generation: 11
producer_id: host.gst.02
state: RUNTIME_OBSERVED         # CONFIGURED/REQUESTED no implica ADOPTED
# operacionalmente: REQUESTED/BUILT/RUNTIME_OBSERVED/ADOPTED/UNOBSERVED/REVOKED
evidence_class: RUNTIME_NEGOTIATED
evidence_ref: gst.pad.1
input_format: {family: PCM, rate_hz: 44100, channels: 2, significant_bits: 24}
output_format: {family: PCM, rate_hz: 96000, channels: 2, significant_bits: 24}
predecessors: []               # vacía cuando orden causal no se puede acreditar
order_evidence_ref: null       # requerido por cada edge causal
adoption_receipt_id: null      # obligatorio sólo cuando se declara ADOPTED
```

**Contrato de proveniencia**: `SOURCE_METADATA`, `CONFIGURED`, `REQUESTED`, `ACKNOWLEDGED`, `READBACK_CONFIRMED`, `ADOPTED_BY_AUDIO`, `RUNTIME_NEGOTIATED`, `SAMPLE_COMPARISON`, `ENDPOINT_SELF_REPORTED`, `UNKNOWN`; atributos de cada capa no forman una escala ordinal universal. `SAMPLE_COMPARISON` exige tap/ventana/canales; `ENDPOINT_SELF_REPORTED` no es medida externa; `ADOPTED_BY_AUDIO` no es certeza de DAC.

**Versionado/compatibilidad:** `schema` desconocido ⇒ `SCHEMA_UNSUPPORTED`, no positivo. La migración F03/Qt legado mantiene properties `stages`, `reasonCodes`, `pathVerdict`, `status`, `captureRevision` sin cambiar sus significados. `operations[]` es un **desglose enriquecido**, nunca un segundo resultado de clasificación. Un consumidor previo continúa mostrando las cinco secciones; uno nuevo puede hacer disclosure repetible. La exportación elimina identificadores privados, rutas, URLs, títulos, MAC/seriales y tokens; usa allowlist y referencias opacas de sesión.

## 3. Operaciones dinámicas y topología — `P0-OPS`

- Clases mínimas: `decode`, `resample`, `channel-remap`, `peq`, `fir`, `gain`, `headroom`, `dither`, `requantize`, `mix`, `dsd-to-pcm`, `dop-pack`. Es una taxonomía de **operaciones posibles**, no evidencia de que todas existan hoy en el motor.
- Una operación se identifica por `(execution_generation, branch_id, operation_instance_id)`; dos SRC consecutivos pueden ser distintos aunque ambos muestren «SRC». Prohibir deduplicación por tipo, título y posición UI.
- El orden visual no confirma causalidad. Se permite un DAG **sólo** si cada edge trae `order_evidence_ref` de un productor verificado en el mismo scope. Detectar ciclos, referencias externas, ambigüedad y ausencia de orden: cuando no hay prueba, `operationsObservedUnordered` con texto explícito y sin flechas falsas.
- Etapa `fir` detectada por factory ≠ kernel adoptado; `peq` seleccionado ≠ ejecutado; `headroom 0 dB` ≠ garantía bit-perfect. Estados de un DSP: `desired/configured`, `published`, `built`, `adopted`, `rendered`, `drained`, `released`, `revoked`; cada promoción requiere receipt y generación actual. `adoption_receipt_id` sólo prueba existencia de una referencia en A47, **no su autenticidad runtime**.
- Operaciones limitadas a 24 en la vista base; si hay más, mostrar indicador `STAGES_TRUNCATED / detailed diagnostics` sin omitir operaciones del audio ni afirmar cobertura. Las lecturas F03 no dependen de crear QML delegates para cada instancia.
- Crossfade y multiroom: múltiples `branch_id` reales, un sink por ruta; la mezcla deja el resultado modificado. A47 fija la regla, pero no implementa ramas activas de AP3/remoto fuera de fase.

**Aceptación P0-OPS real:** pruebas de dos SRC y dos PEQ/FIR, ciclos, orden desconocido, reorganización con same-kind, supersedencia, bypass, host loss y captura completa de ejecución. Las actuales pruebas offline no constituyen aceptación productiva.

## 4. Tabla definitiva de familias — `P0-FAMILIES`

| Familia OutputSession | Origen/resultado | Frontera legítima | Riesgo negativo obligatorio |
|---|---|---|---|
| `direct_pcm` | PCM→PCM | Host/ALSA `hw_params` + binding real; `hw:`/`plughw:` explícitos | Rate igual ≠ muestra igual, fallback no silenciado, EBUSY no cambia backend por engaño |
| `managed_pcm` | PCM→PCM con procesamiento posible | Host efectivo + F05 readback + OutputSession RUNNING | Draft ≠ adopted, PEQ/FIR no hacen «Direct», salida sin prueba puede quedar unknown |
| `shared_pcm` | PCM→PCM por OS | API de salida negociada sólo si existe recibo; downstream OS desconocido | No inventar ALSA exclusiva o pizarra bit-perfect por tasa nominal |
| `dsd_to_pcm` | DSD→PCM | Recibo host de PCM resultante + output real; F05 DSP cuando compatible | No inferir PCM desde visualizador DSD→PCM lateral, no fabricar F32LE |
| `native_dsd` | DSD→DSD | Backend DSD y salida Native realmente adoptada, DAC receiver según su propia prueba | **Prohibido** decoded PCM ficticio, ni tasa carrier PCM como payload |
| `dop` | DSD→DSD encapsulado en carrier PCM | Payload DSD y rate/format carrier por separado; USB/ALSA ACK no acredita receptor | **Prohibido** leer carrier como música PCM o declarar interpretación del DAC sin oráculo |

La estructura `family` incluye `transport`, `source_family`, `sink_family`, `state`, `owner_receipt_id`, `receiver_evidence`, `carrier` (sólo DoP), `decoded_pcm` (sólo cuando corresponda), `pcm_host_receipt` obligatorio para DSD→PCM RUNNING, y `external_measurement_id` cuando se afirme medida externa. `receiver_evidence` puede ser `UNKNOWN`, `USB_ACK`, `ALSA_NEGOTIATED`, `ENDPOINT_SELF_REPORTED`, `EXTERNALLY_MEASURED`; ninguna categoría permite afirmar por defecto `analog_verified`.

Las familias se autorizan por capacidad de la máquina **sin inventar PASS**: un DAC incompatible con Native puede producir `UNSUPPORTED_WITH_REASON` y eso es producto funcionando honestamente; no sustituye una prueba positiva de hardware cuando se anuncia la función.

## 5. Política M11.5 de fidelidad — `P0-FIDELITY`

**No hay booleano global «bit-perfect».** Hay 4 ejes independientes: `source_quality`, `path_transformation`, `sample_match_at_boundary`, `endpoint_report/physical`. El verbo «verificado» requiere indicar una frontera observable concreta.

- `MATCHED_COMPLETE` a nivel **tap digital** sólo cuando (a) comparación exacta del dominio PCM sin conversión ambigua, (b) todos los canales esperados, (c) todos los frames del intervalo declarado, (d) sin spans perdidos, overlaps ni gaps, (e) misma identidad y ventana, (f) fuente de comparación instrumentada y validada por **M11.5**.
- `MATCHED_PARTIAL` para coincidencias incompletas; `MISMATCH` cuando hay una diferencia real; `CONTRADICTED` ante frames superpuestos o hechos incompatibles; `INCONCLUSIVE` sin oráculo suficiente; `UNSUPPORTED` cuando la familia no es PCM comparable.
- El validador offline A47 implementa **sólo la aritmética de cobertura** para fixtures con `method=SAMPLE_EXACT`, `source_trace_id`, `execution_id`, `tap_id`, `boundary`, frames [inicio,fin), todos los canales y segmentos. La prueba de que el motor capturó muestras correctas **no** es creada por el script. M11.5 debe adaptar y aprobar la integración, no F11.
- Un hash 64-bit, un `ACK`, un metadata FLAC, un tuple ALSA, un modo USB o un bit `readback_proven` DSP no demuestra integridad de todas las muestras ni operación analógica. `DoP` requiere un oráculo de encapsulación/marcadores, y Native otro de flujo DSD; no se ejecuta el oráculo PCM a ciegas.
- Toda visualización de prueba informará `compared_channel_frames/expected_channel_frames`, `gaps`, `channel_mask`, `tap_id`, ventana y `last_proven_boundary`, además de que el DAC analógico no fue medido.
- Auditoría negativa obligatoria: canal central alterado con L/R intactos; un frame omitido; paquetes descartados; seek/A→B; tasas y canales iguales con cuantización distinta; compatibilidad `plughw`; DoP carrier; `ACK` sin device proof.

## 6. Certificación completa trazable — `P0-CERT`

**Archivo machine-readable:** `F11_SIGNAL_TRUTH_A47_P0_ACCEPTANCE.json` contiene siete gates y las 50 pruebas `R15C-01..50` con estímulo, oráculo y owner principal. Las 50 conservan `product_status=NOT_RUN`: ningún `PASS` por el mero hecho de haber creado el JSON. Los escenarios R06/R0Y/R0X/V13/V14/V15 se solapan; no se suman como cobertura distinta sin un ledger de deduplicación.

Estados de gate permitidos: `NOT_RUN_FULL_PRODUCT`, `FAIL`, `PASS`, `BLOCKED_CAPABILITY`, `SKIP_APPROVED_WITH_REASON`. Un `SKIP` de hardware sólo es legítimo cuando hay una política explícita de capacidad; **no** levanta automáticamente un requisito de seguridad, identidad, no-false-positive o UI funcional.

**Evidence receipt exigido para cada PASS productivo:** SHA exacto del commit local bajo prueba; spec SHA; etapa/suite y argumento de test; logs o XML JUnit con checks/failed/skipped; filesystem digest; OS/Python/PySide6/GStreamer/ALSA y dispositivos reales aplicables; origen del oráculo; última frontera alcanzada; estado antes/después y reason codes. La evidencia de un test físico añade modelo DAC, VID/PID **sanitizado**, tuple/versión y limitaciones de receiver; no registrar identificadores secretos ni archivos de usuario.

**Gates P0 no suplibles por tests sintéticos:** recorder atomicidad/owner-thread real; versión de snapshot F03 con reason 1:1; adopción DSP con identidad y revocación; motor/familias real; M11.5 sample oracle; 50 R15C con deduplicación a tests reales y resultados; CI exact-SHA y verificación de scripts AP2/DAC; firma manual de limitaciones por hardware.

## 7. Entrega determinista a OpenCode — `P0-DELIVERY`

### 7.1. Orden por propietario, sin autopatch

| Paquete | Precondición | Cambios permitidos | RED→GREEN / STOP |
|---|---|---|---|
| `ST47-M0` freeze/ABI | checkout PR245 SHA + AGENTS/R11/DAC | sólo lectura de inventarios y pruebas rojas | `STOP_SPEC_DRIFT` si normas/preimagen divergen |
| `ST47-M1` seguridad owner | recorder/Qt owner identificados | sólo fixes demostrados por carreras/fanout | A→B→A, dispose, callback tardío; cero RT UI call |
| `ST47-M2` causal F05 | plan output≠DSP | adaptación de lectura con owner-issued proof | BYPASSED posterior revoca; sin fake `current_confirmed` |
| `ST47-M3` F03/readmodel | `SignalPathService` canon 1:1 | read model aditivo y migración de tests | no cambiar veredicto ni nombres públicos sin compat |
| `ST47-M4/M5` PCM/Ops | tuple real y DAG receipts | operaciones repetibles sin UI author | 2 SRC/PEQ/FIR, SRC implícito, no order forged |
| `ST47-M6/M7` salida | F09/F10/DAC gates | lecturas por familia sin tocar procesamiento del audio | Native/DoP/DSD→PCM falsifiers y PAUSED/EOS |
| `ST47-M8` UI | familia y prueba coherente | QML renderer único, badges honestos | Qt owner, KWin, focus, 5+N, a11y |
| `ST47-M9` privacidad | allowlist aprobada | export sólo si con consentimiento y sanitización | fuzz de secretos/campos no allowlist |
| `ST47-M10` RT | benchmark base real | coalescing de visual, sin pérdida terminal | p99/XRUN/no bloqueo con carga |
| `ST47-M11` dispositivo | opt-in DAC capaz | pruebas por familia y recibos | fallos/unsupported explicados, no falso PASS |
| `ST47-M12` closure | siete gates PASS aplicables | cierre documental/normativo aprobado | exact-SHA CI, rollback, revisión final |

### 7.2. Política de entrada, reversión y no modificación remota

```fish
set -gx PRIMARY_PHASE AP2-F11
# Solo lectura antes de solicitar cualquier permiso de mutación local:
git rev-parse HEAD
git status --porcelain
python scripts/phase2_context.py --phase AP2-F11 --receipt-json
python scripts/verify_audio_phase2_repository_alignment.py --phase AP2-F11
python scripts/verify_dac_repository_alignment.py
# comprobar PR245 exacto y preimage git apply --check en COPIA LOCAL DESCARTABLE
# nunca ejecutar migrador A41 sin aprobación de gobierno de nombres
# nunca commit, push, PR ni modificaciones remotas
```

- **Fail-closed:** si el checkout no coincide con PR245, ejecutar `STOP_PREIMAGE_CHANGED` y construir nuevo diff; no efectuar `git apply --3way` para forzar. No editar estado `PHASE2_STATE` ni AGENTS por cumplimiento cosmético.
- **Rollback:** cada work package debe tener snapshot de worktree local SHA, lista exacta de ficheros, prueba `git apply --reverse --check`, y diff de salida inspeccionable. No reescribir fuentes no gobernadas ni reemplazar pruebas F09/F10/DAC.
- **Migración A41:** la solicitud editorial de usar sólo nombres «Michi Signal Truth» es válida como futuro target, pero el script que renombra `AGENTS`, Biblia y rutas de importación es **NO-GO automático**. Requiere autorización normativa independiente y suite de imports/QML/packaging sobre el checkout completo.
- **Traspaso:** entregar a OpenCode los dos artefactos acumulativos `plan.md` + `patch` con hash; solicitar `M0_AUDIT_READ_ONLY` antes de cualquier aplicación local; exigir reportes por owner y gates. La presente adenda no concede permiso implícito de escritura a GitHub.

## 8. Definición precisa de progreso y siguiente trabajo

**A47 plan P0:** `7/7` áreas especificadas, owners, negativas, criterios STOP, fixtures y matriz. **A47 producto P0:** `0/7` gates certificados en checkout completo en esta iteración. No equivale a que el producto existente esté al 0%: significa que ninguno de los gates **nuevos de A47** ha recibido evidencia end-to-end.

**P0 productivos bloqueados hasta una sesión autorizada en checkout íntegro:** cierre real del join F03/F05/OutputSession, adopción y revocación de DSP, integración de `operations[]` a un único read model, seis familias instrumentadas por motor real, comparación M11.5 y negativa DAC, pruebas adversariales R15C, CI exact-SHA. La ausencia de hardware capaz se reporta por capacidad con un oráculo adaptado, nunca con PASS ficticio.

**P1 a preservar sin olvido:** final UI/UX y medidas exactas QML; KWin/DPR/lectores de pantalla; métricas de clipping/processing speed/latencia/XRUN; budgets de audio y cargas DSP+Michi AI/GPU; exportación diagnóstica con allowlist y privacidad; UX de acciones y recovery; esquema remoto (sólo documental en F11); diseño futuro de AP3. Estos no se dejan implícitos: el documento maestro mantiene un ledger formal actualizado en A47.

**Estado de revisión:** `P0_SPECIFICATION_CLOSED_CANDIDATE / P0_INTEGRATION_NO_GO` hasta que los owners y CI del checkout real demuestren lo contrario.
