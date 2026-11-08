# MICHI AP2-F11 — A48 CIERRE DE DISEÑO P1 + PATCH DE ADAPTADORES CANDIDATOS

**Corte de especificación:** 2026-11-08. **Corte real revisado:** PR #245 `d32228fbcc49c4f107e4295b1a70e31fde4d9b07`; no se han alterado repositorios GitHub. **Estado normativo:** A48 es subordinado a AGENTS, Biblia AP2, F03/F05/F09/F10 y DAC V3.5; no declara GO de F11. **Preimagen de patch:** A47 exacto; el archivo A48 es un reemplazo acumulativo de A47, no un delta a aplicar sobre A47.

## 0. Definición de los seis P1 técnicos y una revisión de gobierno

| Área | ID | Diseño A48 | Código/fixture A48 | Gate de aceptación productiva |
|---|---|---|---|---|
| UI/UX y accesibilidad | P1-UI | Microcopy por scope/observación, misma familia visual, layout W1–W9 | `signal_truth_p1_ui.py`; `MichiSignalTruthMetrics.qml` componente opcional | UI real y screenshots/manual KWin/DPR, Qt owner y golden |
| Métricas | P1-METRICS | Medición por productor autorizado, epoch, contador/latencia, cobertura | `signal_truth_p1_metrics.py` | Tap real + clocks iguales, p95/p99, clipping/peak/truepeak separados |
| Rendimiento | P1-PERF | Coalescing limitado con eventos críticos preservados, resnapshot al overflow | `signal_truth_p1_scheduler.py` | Tráfico de 1000/s, 95/99/99.9, XRUN/RSS/CPU vs baseline real |
| Diagnóstico/privacidad | P1-DIAG | Export por consentimiento, allowlist cerrada, sin ruta ni secretos ni PCM | `signal_truth_p1_diagnostics.py` | Integrar botón exportar en UI + fuzz/retención/revisión humana |
| DSP avanzado | P1-DSP | PEQ/FIR/perfiles/TruePeak/LUFS capability-gated y readback por ejecución | `signal_truth_p1_capabilities.py` | F05/Settings owner real, sin control sin conectar, draft≠effective |
| Remotos | P1-REMOTE | Esquema remoto versión 1, epoch, sequence, TTL, defensa antirreplay | `signal_truth_p1_remote_receipts.py` | Sólo schema+fixtures en F11, producción requiere fase y auth propias |
| Gobierno | GOV-ACL | Inspección de permisos/estado de Drive; minimizar privilegios | nota documental y revisión con owner | No cambiar permisos sin autorización explícita |

**Alcance de cierre:** `SPECIFIED + CODE_CANDIDATE + SYNTHETIC_PASS` para P1-UI/METRICS/PERF/DIAG/DSP/REMOTE. Esto NO equivale a `INTEGRATED`, a QA KWin o a pruebas del motor real. `GOV-ACL` sigue `REVIEW_REQUIRED` hasta acción de propietario.

## 1. Diseño final P1-UI dentro del renderer existente

### 1.1. Jerarquía, materiales y geometría

`MichiSignalPathView` sigue siendo el **único renderer del recorrido**; `SignalTruthPopup` es el único inspector. `MichiSignalTruthMetrics.qml` sólo dibuja métricas provistas por el read model como una subsección **opcional**. No se crea otra instancia de recorder, otro popup, un procesador QML ni un controlador de salida. Su wiring de Qt requiere la fase P0 real antes de activarse.

- **NowPlayingBar**: alto fijo de 154 px, sin scroll, sin botón extra, sin mini reproductor. Indicador Signal Truth existente: primer gesto abre el mismo inspector; no mostrar picos/VU en el espacio reservado para transporte. Colapsar información antes que reducir el hit target.
- **Popup**: ancho óptico de 480 px dentro de banda objetivo 440–500 px, limitado al viewport; gap anclado 8–12 px, `modal:true`, `dim:false`, `CloseOnEscape|CloseOnPressOutside`. Encabezado y pie fijos; scroll sólo en cuerpo del recorrido y datos expandidos. El diseño existente tiene `maxPopupHeight` como frontera real: conservar su derivación y evitar bucles `implicitHeight→height`.
- **Etapas**: `SOURCE`, `DECODE`, `PROCESSING`, `OUTPUT`, `DEVICE` son cinco anclas de comprensión. Las N operaciones dinámicas quedan agrupadas **dentro de Processing** mientras no exista un grafo real del motor: no dibujar resamplers/FIR en serie sólo por un orden de array. IDs de operación repetibles nunca sustituyen IDs de ancla F03.
- **Color**: exclusivamente tokens `MichiPalette`, `MichiSemanticColors`, `MichiSpacing`, `MichiMotion`, `MichiAccessibility`. Inter, iconografía Tabler en `MichiSignalStageIcon` y CurveRenderer ya presentes; no inventar paleta CSS ni importar otro UI framework.
- **Métricas**: máximo 8 filas visibles bajo disclosure voluntario, **solo con `temporalStatus=ACTIVE`** y sólo con fuente autorizada. Mostrar `No observado` si no hay recibo; `Parcial` al existir huecos; jamás representar valor cero como *ausente* ni *ausente* como cero. No mostrar True Peak por Sample Peak, ni LUFS desde amplitud RMS.
- **Teclado y a11y**: Escape cierra; Tab/Shift+Tab transitan elementos; Enter/Space expande etapas; descripción accesible incluye título, estado textual y por qué falta evidencia; foco retorna al abridor. Hover no sustituye activación. Alto contraste/reduced-motion siguen tokens de sistema; ninguna conclusión usa exclusivamente color.
- **Responsive / DPI**: 1920×1080, 1320, 1100×700, 1024 y 900×600; DPR 1.0, 1.25, 1.5, 2.0. Si el contenido excede el cuerpo, scroll de contenido sin cortar el footer y sin escape de foco. Las operaciones N no cambian el alto de NowPlayingBar.

### 1.2. Estados de lectura (español; i18n de producción requerido)

| Fuente actual | Resumen permitido | Contraejemplo prohibido |
|---|---|---|
| `ACTIVE` + boundary ALSA + estado observado | «Ruta observada hasta ALSA» | «Fidelidad analógica garantizada» |
| `ACTIVE` con recibo parcial | «Verificación parcial; tramo no observable» | «Bit-perfect confirmado» |
| `PENDING` | «Preparando ruta; aún no está activa» | «En reproducción» |
| `HISTORICAL` | «Última reproducción; información histórica» | «Ruta actual verificada» |
| `NOT_ACTIVE` | «Sin reproducción activa» | Métricas positivas sin epoch vigente |
| `DoP` | «Portadora PCM DoP; receptor no observado» | «DoP decodificado por DAC» sin prueba receptora |
| `Native DSD` | «Salida Native reportada» | Campos PCM falsos o tasa PCM de fuente |
| FIR factory presente sin adopción | «Filtro disponible; ejecución no confirmada» | «FIR aplicado» |
| operaciones con orden desconocido | «Operaciones observadas; orden no acreditado» | Línea causal falsa |
| owner desconocido / QoS | «Métrica no observada» | Cero, p99 o badge verde inventados |

`inspector_labels()` protege el microcopy en un adapter puro. Para reconocer orden, exige `operationOrderVerified=True` Y `operationOrderProof='OWNER_ATTESTED'` sobre el read model de owner: ninguno se sintetiza en QML. El propio adaptador no valida el emisor, de modo que la integración todavía exige F03/OutputSession.

## 2. P1-METRICS — metrología verificable sin inventar ejecución

- Fuentes autorizadas por tipo: `pcm_meter` para `sample_peak_dbfs` y `clipped_samples`; `true_peak_meter` para `true_peak_dbtp`; `loudness_meter` para `integrated_lufs`; `alsa_observer` para `xrun_events`; `processing_host` para `processing_speed`; `ui_observer` para latencias de publicación.
- Un evento de métrica incluye `execution_id`, `epoch`, `sequence`, `producer`, `clock_domain` cuando haya latencia, `missing_before` y el valor finito. Los alias de nombre de pista, metadata y bytes de audio se **excluyen**.
- Sólo `MONOTONIC_SAME_DOMAIN` permite medir `owner_to_ui_ms` y `frame_dispatch_ms`; timestamps ALSA/PipeWire/QPC sin calibración no se convierten en valores ms. Un p99 de **presentación** no es p99 del callback de audio. Los percentiles se calculan sobre la ventana publicada (nearest rank, máximo 2048); informan cantidad de muestras.
- Los contadores `xrun_events` y `clipped_samples` son **absolutos por epoch y productor**, no se suman cada snapshot. Primer sample en sequence superior a 1 y huecos posteriores convierten lectura en `PARTIAL`. Un contador de muestras que desaparece tras `retire` vuelve a `UNOBSERVED`, nunca 0 probado.
- Sample peak describe pico discreto; true peak requiere sobre-muestreo y medición certificada; LUFS requiere algoritmo y ventana declarados. Ninguna lectura virtual de CPU o factory FIR puede fabricar esas métricas.
- Análisis de reproducción bajo DSP/DSD→PCM sólo si hay PCM realmente confirmado; Native DSD y DoP no pasan por meter PCM musical para el payload. Perf de UI puede seguir observándose por separado.

## 3. P1-PERF — presupuestos y política de cargas

**Principio:** audio continuo tiene prioridad absoluta sobre Signal Truth. Los observadores de métricas son *off realtime*. El callback no ejecuta Python, Qt, JSON, procesamiento FIR, sampling de LUFS ni toma locks del ledger.

- Backend de eventos: recepción desde productor→dispatcher seguro (worker/owner Qt). Revisión de secuencia y epoch en consumer; cola limitada con snapshots completos de estado. `FRAME_UPDATE`/`METRIC_UPDATE` redundantes se coalescen. `RETIRE`, `HOST_LOSS`, `CONTRADICTION`, `EXECUTION_CHANGED`, `RELEASE` no pueden perderse silenciosamente; overflow fuerza `FULL_RESNAPSHOT_REQUIRED` del recorder antes de continuar mostrando una conclusión positiva.
- **Targets no inventados**: baseline y delta medidos para PCM Direct sin DSP, PCM Managed+PEQ/FIR, DSD→PCM, Native, DoP, transiciones A→B→A y UI abierta/cerrada, con Michi AI GPU activo y sin él. Tomar p50/p95/p99 y p99.9 de latencia audio real (instrumentada), XRUN, CPU por proceso/worker, RSS, memoria, fotogramas Qt y latencia input→render. Fijar umbrales de regresión con datos emparejados del mismo host; no extrapolar R10 del popup a camino DSP.
- Desactivar/retardar primero métricas de interés secundario, nunca degradar output o romper el readback de verdad. En sobrecarga registrar `PARTIAL`, contadores de pérdida y causa. Resnapshot no se produce dentro de audio callback.
- Política de GPU universal: AI y DSP solicitan recursos por prioridad/capability, sin afirmar descarga a GPU para toda operación. Signal Truth no fuerza Vulkan/CUDA/OpenCL. Pruebas con RADV/AMD, Intel, Nvidia donde haya equipo, además de CPU-only; F11 no es plataforma de optimización de GPU.

## 4. P1-DIAG — privacidad, consentimiento y exportación reproducible

`build_diagnostic_report(consent=True)` construye exclusivamente un JSON técnico **sanitizado por lista blanca**. La función no escribe archivos, no abre red, no lee rutas de biblioteca, no incluye PCM y no aporta un identificador estable. El usuario debe solicitar la exportación mediante control futuro de la UI y confirmar antes de crear cualquier archivo local.

- Admitidos: estado temporal, familia, último límite probatorio de enum, veredicto conservador, número acotado de etapas/operaciones, códigos reason tipados, métricas numéricas agregadas (sólo opt-in adicional). Fuera de alcance: título, artista, ruta local, UID, home, IP/MAC, números de serie, tokens Link, credenciales, previews de PCM, FFT cruda, muestras de un dispositivo y exception text arbitrario.
- En el JSON **nunca** trasladar `MATCHED_COMPLETE` o `MATCHED_PARTIAL` desde un DTO QML como prueba real: el módulo degrada a `UNPROVEN` sin certificado M11.5. `physical_dac_verified` es false por defecto.
- Máximo 64 reason codes y 32 KiB report. No conservar nada entre sesiones por defecto. El export de métricas se limita a `ACTIVE` para no mezclar lecturas históricas sin autorización. Un almacenamiento/exportación futura debe gobernar destino, retención, borrado, permisos `0600` y consentimiento específico.
- Pruebas negativas con `/home/...`, títulos, IP y `sk-proj-`, estructuras malignas, NaN/Inf, campos desconocidos y excesos. Ningún campo libre de usuario atraviesa allowlist.

## 5. P1-DSP — pantalla avanzada sin funciones ficticias

**Selector del owner:** sólo F05 o Settings pueden certificar qué acciones existen. `supported=true` no habilita un botón si `wired!=true`, `owner` desconocido o un backend no implementado. Los controles avanzados (Graphic EQ, Convolution/FIR, Profiles CRUD, medición True Peak y LUFS) permanecen deshabilitados y explicados hasta receipt real. El slider/curva es calculado, no medición de respuesta física.

- `AVAILABLE` significa **capacidad realmente cableada**; no significa aplicada a audio activo.
- `effective=True` requiere `readback_proven=True`, `state=EFFECTIVE`, `effective_execution_id` igual a ejecución actual **y `owner_execution_correlated=True` suministrado por un join P0 verificado**, no por QML. Este último enlace no se crea desde el adapter; por tanto el parche A48 por sí solo no certifica adopción.
- `DISABLED` y `UNAVAILABLE` tienen reason tipado; ausencia de recibo queda `UNOBSERVED`. Draft de perfil con preview puede representarse como **intención**, separado de aplicado y de estado efectivo.
- Intents de navegación remiten a Settings/Processing existentes; nunca modificar motor de audio desde esta capa. Las capacidades efectivamente implementadas se descubren de F05, no de un flag en QML.

## 6. P1-REMOTE — contrato futuro, sin adelantar F12–F15

`RemoteReport v1`: `endpoint_id` opaco, `producer` entre Micro/Big/Stream, `route_epoch`, `sequence`, `issued_ms`, `ttl_ms ≤30 s`, `family`, `state`. Sólo un **adaptador autenticador externo** puede proporcionar la marca `owner_authenticated=True` al validador; una cadena entregada por un cliente no es autenticación. Esta función de A48 es un **contrato aislado**, no un validador criptográfico.

- Nuevos reportes de mismo endpoint/epoch con `sequence` anterior o duplicada se rechazan; epoch anterior no puede aceptar sequence mayor; TTL vencido o relojes adelantados se rechazan; máximo 64 endpoints por defecto.
- Estado positivo máximo: `REMOTE_REPORTED` (autorreporte de endpoint). No eleva ALSA local, DAC receiver, reproducción audible, igualdad de muestras o `MATCHED_COMPLETE`.
- El auto descubrimiento `mDNS/Whisker` no demuestra autenticación. Ningún controlador de Micro/Big/Stream se modifica durante F11. Implementación productiva requiere contrato de identidad Michi Link, firmas/replay y autorización propia.

## 7. Gate P1 — cierre documental ≠ cierre de producto

| Gate | Test y prueba offline | Requisito para pasar en producto | Estado A48 |
|---|---|---|---|
| `P1-UI` | test de status/microcopy + componente QML estático | Qt + KWin screenshot DPR+a11y, acciones y foco | `PRODUCT_NOT_RUN` |
| `P1-METRICS` | producer/epoch/quantile/gaps, peak separado | observadores reales y oráculos de ventana/clock | `PRODUCT_NOT_RUN` |
| `P1-PERF` | coalescing y saturación→resnapshot | benchmarks p99/XRUN/soak con GPU DSP/AI y CPU | `PRODUCT_NOT_RUN` |
| `P1-DIAG` | strict allowlist y fuzz de secretos | botón con consentimiento, persistencia local y retención | `PRODUCT_NOT_RUN` |
| `P1-DSP` | capability states y draft≠effective | F05/Settings readback y cross-output real | `PRODUCT_NOT_RUN` |
| `P1-REMOTE` | contract, TTL, replay, limit bounded | para F11 basta diseño y fixtures; autorizar F12+ en su fase | `DESIGN_ONLY_F11` |

**No reemplazar P0 pendientes:** OPEN-P0-01..07 continúan exactamente con estado NOT_RUN. El gate de A48 no puede certificar rendimiento del callback por una medición de `owner_to_ui_ms`. La UI avanzada no habilita FIR/Profiles sin prueba de backend. Ningún resultado sintético certifica audio, red, DAC analógico ni KWin.

## 8. Orden de integración A48 y rollback

1. P0 real `OPEN-P0-01` revisar SHA/preimage/AGENTS/Biblia y comprobar aplicación en checkout completo, sin escritura GitHub.
2. P1-DIAG y P1-CAPABILITIES pueden importarse en unit tests sin QML; jamás exportar automáticamente.
3. P1-METRICS sólo después de habilitar productores off-RT con contratos de epoch/sequence y sin DSP inventado.
4. P1-PERF conectar Qt owner seguro después del P0 threading fence; probar flush, commit/terminal y `FULL_RESNAPSHOT_REQUIRED` antes de optimizar.
5. P1-UI conectar una sola subsección de métricas dentro de inspector existente, sin mover `NowPlayingBar`, y medir KWin/DPR/a11y.
6. P1-REMOTE continúa desligado de runtime y no altera `Michi Link` hasta fase futura y autorización.
7. Revisar ACL `GOV-ACL` con propietario; no cambiar permisos por cuenta del parche.

**Rollback:** revertir adaptadores y qml opcional si hay fuga de datos, efecto RT, QML warning o falso estado. Mantener exactamente los tests A47/P0 y contrato V1.5. Un FAIL productivo no puede reportarse como P1 cerrado por la existencia de tests aislados.
