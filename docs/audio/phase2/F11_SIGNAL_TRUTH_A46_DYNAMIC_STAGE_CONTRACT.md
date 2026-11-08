# AP2-F11 · A46 · Contrato correctivo de topología Signal Truth

**Estado:** CANDIDATO DE CÓDIGO, prueba aislada PASS; aplicación sobre checkout completo PR245 **NOT_RUN**. Ninguna autorización para editar `main`, registrar commits, crear PR, realizar migración A41 ni anunciar F11 CLOSED.

## Causa raíz de A45-P0

`SignalPathBridge._rebuild()` ya construía las cinco secciones legibles y podía insertar `resample`, `channel-remap` y `fir` después de Processing y antes de Output. El adaptador A42 `signal_truth_frame._stages` exigía la tupla exacta de cinco IDs. Aunque el productor aportara un SRC observado, `_normalize` acababa con `ST_A42_INVALID_UI_TOPOLOGY`, perdía la identidad, los `reasonCodes` y el veredicto. Una transformación observada no debe provocar pérdida de la explicación de la ruta completa.

## A46-FIX-01 · Presentación 5+N, NO reconstrucción del grafo

En la fase F11 presente, `TruthFrame` admite como **anclas** las cinco secciones de UI `source → decode → processing → output → device`. Entre `processing` y `output` admite **cero a tres** etapas reportadas por el bridge vigente: `resample`, `channel-remap`, `fir`. Rechaza entradas mal ordenadas, desconocidas, repetidas o no acotadas. Actualiza `index`, `count`, `first` y `last` para que `MichiSignalPathView` dibuje y navegue correctamente el número efectivo de nodos.

El formato F03 permanece con **cuatro** nodos semánticos `source/decode/engine/device` y sigue siendo la autoridad del veredicto y las razones. El nuevo código no crea un recorder, segunda decisión de fidelidad, DSP, sondeo Qt ni compromiso ALSA. `SignalTruthPopup` sigue usando el `truthFrame` compartido por el bridge propietario.

Una etapa extra en el arreglo significa *presentación de un recibo producido por el bridge*; **NO** es prueba del orden causal, correlación con una generación DSP o identidad de muestras en un DAC. `operationOrderVerified` permanece `false`; `fidelityClaim` permanece `UNPROVEN`. Las etapas `resample` y `channel-remap` pueden conservar el estado de transformación derivado de la evidencia runtime ya reconciliada por F03. Una factoría `fir` con estado `transformed` sin `CURRENT_EXECUTION_CONFIRMED` se degrada a `unknown`, manteniendo una explicación de observabilidad no acreditada. Las capturas `HISTORICAL`, `PENDING`, `NOT_ACTIVE`, los owner links inválidos y las revisiones contradictorias no heredan estados efectivos de una captura anterior.

> **Prohibición:** No convertir automáticamente un arreglo de 5+N etapas en una cadena de ejecución físicamente certificada. La posición de pantalla no acredita el `order_index` del callback.

## A46-FIX-02 · Límites actuales y contrato del siguiente incremento

El productor actual inserta a lo sumo una etapa de cada uno de los tres tipos. **No** representa todavía dos SRC consecutivos, múltiples PEQ/FIR, branches de crossfade, reordenamiento dinámico ni un `operation_instance_id`. Esos casos seguirán pendientes y no se falsearán mediante identificadores deducidos del tipo. El contrato futuro (pendiente de ratificación F03/F05) requiere `{operation_instance_id, producer_instance, branch_id, media_epoch, route_epoch, pipeline_generation, format_in, format_out, adoption_receipt_id, observed_boundary, stage_order_receipt?}`. El último campo solo puede suministrarlo el productor efectivo, nunca QML; si falta, mostrar orden desconocido.

La investigación V1.5 propone un inspector de dos profundidades: cinco secciones de lectura humana + operaciones reales repetibles cuando existan recibos. A46 corrige el bug del productor **existente**, sin fingir que ya implementa la capa futura.

## Tests ejecutables y oráculos de aceptación

- `tests/audio_phase2/test_signal_truth_dynamic_stages_a46.py`: cobertura de cinco contraejemplos P0 A45, ocho combinaciones, indexación y `reasonCodes`, SRC/remix, FIR sin adopción, FIR con prueba afirmada en fixture, capturas no activas, scope de owner sin F03, freeze profundo, allowlist y topología inválida. Son tests de contrato puros, **NO** pruebas de hardware o CI exact-SHA del producto.
- Ejecutar también A42, A38/A39, A41/A43, A44 y la suite existente `test_f11_signal_path_bridge.py` en la copia local del PR245. La integración completa requiere que un `SignalPathBridge._rebuild` REAL emita las etapas mediante fixtures del motor: **NOT_RUN** fuera del checkout real.
- La matriz `F11_SIGNAL_TRUTH_A46_R15C_COVERAGE.json` registra los cincuenta escenarios adversariales de la investigación V1.5, inicializados todos `NOT_RUN` (sin prometer cobertura por tener tests candidatos). Los casos 13, 42, 43 y 44 se relacionan con escenarios sintéticos del módulo A46, sin marcar prueba productiva PASS.
- `git apply --check`/`git apply`/reverse se ejecutan solo contra una **copia sintética** en esta fase y, más adelante, una copia descartable del PR245; nunca contra GitHub o el checkout productivo sin autorización.

## Gate de entrega a OpenCode (dos decisiones)

1. **GO_AUDIT_READ_ONLY:** entregarle plan A00–A46, investigación V1.5, parche A46 y SHA final; observar y comparar el PR245 real, registrar contraejemplos, generar plan de QA. Sin aplicar, commitear, PR, push, migrate ni cambiar la Biblia normativa.
2. **NO_GO_APPLY:** no hay recepción física Native/DoP, tests Qt/KWin ni full checkout exact-SHA postmigración; A44 previo tenía además un P0 y el nuevo parche sólo lo corrige en un modelo puro. A46 no debe convertir certificados propuestos o `NOT_RUN` en PASS.

## Backlog obligatorio posterior a A46

| Prioridad | Código/contrato pendiente | Prueba de aceptación |
|---|---|---|
| P0 | Correlación real F03/OutputSession/F05 + owner thread | Fixture productivo A→B→A, host-loss, callback tardío, recorder revision|
| P0 | Reconciliar `AGENTS.md`, Biblia y A41 | Review humana, plan migratorio sin ejecutar y verificador contra full HEAD|
| P1 | `SignalOperation` por instancia y ramificación | Dos PEQ y dos SRC reales, IDs por epoch, orden UNKNOWN si no hay recibo|
| P1 | Modelo Native/DoP sin F03 PCM heredada | R15C-49, carrier/payload separados; receiver no observado|
| P1 | Receipts/medidas de DSP F05, caps GStreamer y ALSA | C0X/DSD PCM con identidad y readback independiente|
| P1 | QA visual Qt/KWin DPI, foco y scroll 5+N | R15C-44, 200 % DPI, teclado y reduced motion|
| P1 | Telemetría no bloqueante y diagnóstico privado | R15C-45, R15C-46, XRUN/p99 y export allowlist|
| P1 | Matrix DAC por capacidades frente a físico | CAPABILITY_UNSUPPORTED ≠ PASS; no-claim honesto|

**Criterio de cierre:** no pasar de `CANDIDATE` a `GO_APPLY` únicamente por tests sintéticos ni por inventario 20/20 de artefactos de Drive.
