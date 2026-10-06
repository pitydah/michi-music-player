# MICHI MUSIC PLAYER --- AUDIO PHASE 2 — R11.1 RESTRICTED ACTIVATION SPEC

## Especificación ejecutable: DAC + Managed PCM + Signal Truth + DSP + DSD + DoP + convergencia NowPlayingBar

**Estado:** `PRE-ACTIVATION / RESTRICTED ENTRY PROPOSED` — `DO NOT START AP2-F01 UNTIL PRE-AP2-01 PASS`\
**Naturaleza:** especificación maestra de Audio Phase 2 con **entrada restringida**: F00–F04 pueden activarse tras el preflight R11.1 sin falsificar el cierre físico M11.4; F05+ conserva gates runtime adicionales. Alcance: DAC, Signal Path, DSP, Native DSD, DoP y UX audiófila. **No sustituye ni reabre la autoridad DAC V3.5 vigente**.\
**Repositorio reconciliado:** `main @ 8bea498b0c2838b962352e09aa70da73088ced23` (2026-10-03 UTC, `test(dac): record the wedged R32 attempt 5 and park the soak`).\
**Estado heredado actual:** M11.3 `DONE / TESTED / FROZEN`; M11.4 software/tooling `CLOSED`, R24 `PASS` en SMSL y HA01, R25 `PASS` en SMSL, R25 HA01 pendiente, R32 `DEFERRED_UPSTREAM_BLOCKER` por deadlock GStreamer 1.28.x reproducido, R35/R36 pendientes y `PHYSICAL_VERDICT = INCOMPLETE`. Source characterization ya está aislada en subprocess; el Direct GStreamer lifecycle sigue expuesto. M11.5 runtime completo no se exige para F00 restringido: se exige primero `M11.5A CONTRACT FREEZE`.\
**Dependencia R11.1:** no se falsifica ningún PASS físico. La entrada a F00 requiere `PRE-AP2-01 PASS`, exact-head regression verde y `M11.5A FROZEN`. F01–F04 pueden avanzar con M11.4 físico `INCOMPLETE/DEFERRED`; F05+ queda bloqueado por `GST_LIFECYCLE_GATE` y por sus dependencias específicas.\
**Plataforma primaria:** Linux.\
**Legacy auditado como cantera, no autoridad:** `pitydah/michi-legacy main @ 2332a45c7a645d645e4b4882ef30aedeb2d7ef07`.\
**Principio rector:** reutilizar Linux/ALSA/snd-usb-audio como autoridad
de bajo nivel; construir en Michi la capa de identidad, conocimiento,
evidencia, verificación y explicación que Linux no entrega como una
experiencia audiófila integrada.

> **KILLCRITIC_R11_1_EXECUTION_SEAL:** §§381–440 constituyen la capa
> **CANÓNICA DE IMPLEMENTACIÓN**. Para un agente de código, esa capa y los
> `MUST_READ_ANCHORS` de la fase prevalecen sobre todo el material histórico
> §§0–380. Los §§0–380 se conservan como rationale, investigación, matrices de
> falsación y trazabilidad; **no se cargan automáticamente para implementar**.
> Si un bloque antiguo contradice un contrato R11/R11.1, el bloque antiguo queda
> retirado sin necesidad de interpretación. `phase2_context.py` R11 indexa
> anchors estables, no números de sección. Esto elimina el riesgo de que una
> corrección append-only quede fuera de la ventana de contexto.

**Ampliación 2026-09-21, reconciliada nuevamente 2026-09-28:** este documento incorpora un segundo eje **post-baseline** (no necesariamente post-Stable):
`AUDIO PROCESSING / DSP` y una integración DSD/DoP de primer nivel. El objetivo
ya no es únicamente explicar el DAC: es poder representar y ejecutar, de forma
explícita y falsable, una cadena `SOURCE → DECODE → PROCESSING → TRANSPORT →
DEVICE` para PCM y DSD. R11.1 **refina el gate temporal**: el cierre físico exhaustivo M11.4 sigue siendo una certificación separada y honesta, pero no bloquea por sí solo F00–F04 cuando sus pendientes están clasificados y documentados. `M11.5A CONTRACT FREEZE` sustituye al antiguo requisito circular de M11.5 runtime completo antes de F00. F05+ mantiene gates runtime adicionales.


<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->

# BIBLIA A — CONSTITUCIÓN OPERATIVA PARA OPENCODE Y CUALQUIER AGENTE DE IMPLEMENTACIÓN

> **NORMA DE MÁXIMA PRIORIDAD PARA AGENTES:** este archivo no es material de
> referencia opcional. Es la **especificación canónica de ejecución de Audio
> Phase 2**. Ningún agente puede implementar, refactorizar, crear schema,
> cambiar ownership, añadir una dependencia, mover una autoridad o modificar
> UI de este subsistema basándose sólo en memoria conversacional, un resumen
> anterior, un diff aislado o conocimiento general. **Debe volver a consultar
> este archivo en cada sesión y en cada cambio de fase.**

La intención de esta constitución es resolver un problema práctico: distintos
modelos usados por OpenCode, subagentes o herramientas de programación tienen
ventanas de contexto diferentes. Un modelo con una ventana pequeña no puede
mantener 20 000+ líneas del documento, el código afectado, los tests y el diff
completo simultáneamente. La solución **no** es permitir que el agente improvise
cuando el documento no cabe. La solución es que el documento sea consultable
por partes estables, con un protocolo de lectura obligatorio y repetible.

## BIBLIA A.1 — IDENTIDAD CANÓNICA DEL DOCUMENTO

Cuando este archivo se incorpore al repositorio, el destino preferido es:

```text
CANONICAL_PHASE2_SPEC_PATH =
  docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md
```

El nombre canónico es:

```text
MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md
```

Regla de resolución para OpenCode:

```text
1. Si CANONICAL_PHASE2_SPEC_PATH existe → usarlo.
2. Si no existe → buscar el nombre canónico con git ls-files.
3. Debe existir exactamente UNA coincidencia versionada.
4. Cero coincidencias → STOP_SPEC_NOT_FOUND.
5. Más de una coincidencia → STOP_SPEC_AMBIGUOUS.
6. Nunca usar una copia descargada, temporal o backup como autoridad si existe
   una versión versionada en el repositorio.
```

Comando de referencia:

```bash
python - <<'PY_RESOLVE'
from pathlib import Path
import hashlib
import subprocess

name = "MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md"
preferred = Path("docs/audio") / name
if preferred.is_file():
    spec = preferred
else:
    out = subprocess.run(
        ["git", "ls-files", f"*{name}"],
        check=True, capture_output=True, text=True
    ).stdout.splitlines()
    matches = [Path(item) for item in out if item.strip()]
    if len(matches) != 1:
        raise SystemExit("STOP_SPEC_NOT_FOUND" if not matches else "STOP_SPEC_AMBIGUOUS")
    spec = matches[0]

h = hashlib.sha256(spec.read_bytes()).hexdigest()
head = subprocess.run(
    ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
).stdout.strip()
print(f"PHASE2_SPEC={spec}")
print(f"PHASE2_SPEC_SHA256={h}")
print(f"REPO_HEAD={head}")
PY_RESOLVE
```

El hash del archivo **se calcula en runtime**. No se escribe un SHA-256 fijo
dentro del propio archivo porque cualquier edición legítima invalidaría un hash
autorreferente.

## BIBLIA A.2 — REGLA «NO CONTEXT → NO CODE»

Antes de editar cualquier archivo productivo el agente debe poder responder,
con evidencia del plan actual, estas preguntas:

```text
CURRENT_PHASE?
PHASE_ENTRY_GATE_SATISFIED?
WHICH_EXISTING_AUTHORITY_OWNS_THE_STATE?
WHICH_NEW_AUTHORITY_IS_ALLOWED?
WHICH_FILES_ARE_IN_SCOPE?
WHICH_FILES_ARE_FORBIDDEN?
WHICH_INVARIANTS_MUST_SURVIVE?
WHICH_TESTS_CLOSE_THE_CHANGE?
WHAT_IS_THE_ROLLBACK_OR_FAILURE_BEHAVIOR?
```

Si no puede responder cualquiera de ellas:

```text
NO CONTEXT → NO CODE
UNKNOWN OWNERSHIP → NO CODE
UNKNOWN PHASE → NO CODE
UNKNOWN SOURCE OF TRUTH → NO CODE
UNREAD SPEC → NO CODE
```

No se permite rellenar huecos con una decisión «razonable» del modelo. El
agente debe volver al archivo, localizar la sección aplicable y continuar sólo
cuando el contrato esté claro.

## BIBLIA A.3 — CHECKPOINTS OBLIGATORIOS DE RELECTURA

OpenCode debe consultar esta especificación en los siguientes momentos. No es
suficiente haberla leído al comienzo de una conversación larga.

```text
C0  SESSION_BOOT
    Al comenzar una nueva sesión, agente o subagente.

C1  PHASE_SELECTION
    Antes de declarar qué fase se va a ejecutar.

C2  PRE_MUTATION
    Inmediatamente antes del primer cambio productivo.

C3  PUBLIC_CONTRACT_CHANGE
    Antes de cambiar un tipo de dominio, port, schema, bridge, public API,
    state machine, ownership o persistencia.

C4  HYPOTHESIS_CHANGE
    Si un test o prueba física falsifica la hipótesis de implementación y el
    agente considera una arquitectura distinta.

C5  CROSS_PHASE_TOUCH
    Si el cambio necesita editar un archivo gobernado por otra fase.

C6  PRE_COMMIT
    Después de los tests y antes de cerrar un commit/work package.

C7  CONTEXT_RESET
    Después de context compaction, resumen automático, cambio de modelo,
    cambio de agente, nueva conversación o reanudación tras una pausa.

C8  HANDOFF
    Antes de entregar trabajo a otro modelo/agente.
```

En `C3`, `C4` y `C5` la relectura debe incluir el bloque de fase completo y la
sección normativa que define la autoridad afectada, no sólo un resumen.

## BIBLIA A.4 — RECEIPT DE CONTEXTO

Antes de modificar código, el agente debe producir en su log de trabajo o
respuesta interna un recibo equivalente a:

```text
PHASE2_SPEC_ACK
spec_path=<resolved path>
spec_sha256=<runtime sha256>
repo_head=<git rev-parse HEAD>
primary_phase=<AP2-Fxx>
phase_dependencies=<...>
anchors_read=<...>
sections_read=<...>
contract_conflicts=NONE | <list>
implementation_allowed=YES | NO
```

No es necesario versionar este recibo. Su función es impedir que un modelo crea
que «recuerda» la especificación cuando en realidad está trabajando desde un
resumen antiguo.

Para commits de Audio Phase 2, la forma recomendada de trailers es:

```text
Michi-Phase2-Phase: AP2-Fxx
Michi-Phase2-Spec: MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md
Michi-Phase2-Spec-SHA256: <sha256 leído antes del commit>
Michi-Phase2-Gate: <gate/verifier ejecutado>
```

Los trailers son evidencia de proceso; **no sustituyen la lectura del plan**.

## BIBLIA A.5 — JERARQUÍA DE AUTORIDAD CUANDO HAY CONFLICTO

La implementación no puede resolver contradicciones silenciosamente. La
precedencia depende del estado temporal del proyecto.

### Antes de activar Audio Phase 2

```text
1. Código/contratos V3.5 + M11.5 realmente cerrados en la baseline futura.
2. ADR aceptados de la baseline.
3. Este plan como diseño DEFERRED.
4. Notas, conversaciones, prompts o memoria de agentes.
```

Si este plan contradice la baseline antes de su activación, el plan se corrige;
**no se reabre V3.5 para acomodarlo**.

### Después de `AP2-F00` y del freeze formal

```text
1. ADR aceptados de Audio Phase 2 + contratos de baseline congelados.
2. Este archivo, en su versión activa y versionada.
3. Código que implementa esos contratos.
4. Tests/verifiers que prueban esos contratos.
5. Conversaciones, prompts, resúmenes y memoria de agentes.
```

Si código y plan divergen después de la activación:

```text
STOP_SPEC_DRIFT
```

El agente debe describir la divergencia y corregir una sola autoridad mediante
un cambio explícito y revisable. Nunca «hacer que los tests pasen» alterando
silenciosamente la intención del documento.

## BIBLIA A.6 — VENTANAS DE CONTEXTO: ESTRATEGIA ADAPTATIVA

No se presupone ningún proveedor ni tamaño fijo. Cada agente debe clasificarse
por la **ventana efectiva disponible después de system prompts, herramientas y
memoria**, no por el tamaño publicitado del modelo.

```text
MICRO / SMALL
    hasta ~32k tokens efectivos o tamaño desconocido

STANDARD
    ~32k–64k tokens efectivos

LARGE
    ~64k–128k tokens efectivos

EXTENDED
    >128k tokens efectivos
```

Si el agente no conoce su ventana efectiva, debe operar como `MICRO / SMALL`.

### Presupuesto de contexto recomendado

```text
<= 35 %   especificación/plan
<= 45 %   código, tests y diffs del repositorio
>= 20 %   razonamiento, comandos, errores, salida y margen de seguridad
```

Un modelo pequeño **no debe intentar cargar la Biblia completa**. Debe cargar
los paquetes mínimos definidos por cada fase. Un modelo grande puede cargar más
contexto, pero sigue obligado a identificar las mismas autoridades y gates.

### Perfil MINIMUM

Siempre carga:

```text
1. BIBLIA A — constitución operativa.
2. BIBLIA B — mapa de fases.
3. Tarjeta completa de la fase activa AP2-Fxx.
4. Secciones MUST_READ de esa tarjeta que gobiernan el cambio concreto.
5. Archivos productivos directamente afectados.
```

### Perfil STANDARD

Añade:

```text
6. Tarjetas de fases dependientes.
7. Implementation Blueprint de tipos/servicios tocados.
8. Tests existentes del subsistema.
9. Contratos de persistencia/threading cuando apliquen.
```

### Perfil DEEP

Añade:

```text
10. Tracks adyacentes completos.
11. Matrices físicas y adversariales.
12. Investigación técnica y fuentes.
13. UI/UX master spec si el cambio tiene cualquier efecto observable.
```

### Regla de compaction

Después de cualquier compactación o resumen automático:

```text
SUMMARY_IS_NOT_AUTHORITY = TRUE
RELOAD_PHASE_CARD = REQUIRED
RELOAD_AFFECTED_NORMATIVE_SECTIONS = REQUIRED
```

## BIBLIA A.7 — PROHIBICIÓN DE MEMORIA COMO FUENTE DE VERDAD

El agente puede usar memoria o resúmenes para localizar más rápido una sección,
pero nunca para afirmar que una regla sigue vigente.

Incorrecto:

```text
"Recuerdo que DoP usa X, así que implementaré X."
```

Correcto:

```text
"El resumen sugiere que DoP está en AP2-F09. Releo la tarjeta AP2-F09,
las secciones 86–88, 123, 134 y 138, y recién después implemento."
```

## BIBLIA A.8 — GRANULARIDAD DE TAREA PARA MODELOS PEQUEÑOS

Una tarea OpenCode debe caber en una sola `PRIMARY_PHASE`. Si necesita dos
fases productivas simultáneas, primero debe dividirse o recibir una excepción
explícita del plan.

Unidad recomendada:

```text
1 intent de producto
1 autoridad principal
1 pequeño conjunto de archivos
1 conjunto de tests de cierre
1 commit reversible
```

No pedir a un modelo pequeño:

```text
"implementa DSP + DSD + DoP + UI completa"
```

Sí pedir:

```text
"AP2-F04: implementar PcmSignalFormat/DsdSignalFormat/DopCarrierFormat y sus
invariantes, sin wiring productivo, cerrando los tests de dominio indicados."
```

## BIBLIA A.9 — PROTOCOLO DE SUBAGENTES

Si OpenCode delega a subagentes:

```text
PARENT
  ↓ lee Biblia + fase
  ↓ define PRIMARY_PHASE y scope
SUBAGENT
  ↓ DEBE releer por sí mismo la fase y secciones normativas
  ↓ no recibe autoridad por el resumen del parent
  ↓ devuelve evidencia + diff + tests
PARENT
  ↓ relee PRE_COMMIT
  ↓ integra sólo si conserva invariantes
```

Un subagente no puede recibir como única instrucción «haz lo que dice el
resumen». Debe recibir la ruta de la Biblia y el ID de fase.

## BIBLIA A.10 — CUÁNDO EL AGENTE DEBE DETENERSE

Parar y reportar, sin seguir modificando, cuando ocurra cualquiera:

```text
STOP_SPEC_NOT_FOUND
STOP_SPEC_AMBIGUOUS
STOP_PHASE_UNKNOWN
STOP_PHASE_LOCKED
STOP_ENTRY_GATE_UNSATISFIED
STOP_AUTHORITY_CONFLICT
STOP_SPEC_DRIFT
STOP_BASELINE_DRIFT
STOP_SCHEMA_UNOWNED
STOP_RUNTIME_EVIDENCE_AMBIGUOUS
STOP_CROSS_PHASE_SCOPE
STOP_REQUIRED_HARDWARE_NOT_AVAILABLE
STOP_TEST_GATE_NOT_REPRODUCIBLE
```

El comportamiento seguro es detener la mutación y conservar el estado
coherente, no inventar una salida.

## BIBLIA A.11 — LINE NUMBERS NO SON API

Este documento crecerá. Las líneas cambiarán. Los agentes deben localizar
contenido por:

```text
1. anchors MICHI_PHASE2:*;
2. IDs de fase AP2-Fxx;
3. números/títulos de sección;
4. símbolos de código canónicos.
```

Nunca un prompt debe depender sólo de «lee línea 8123».

## BIBLIA A.12 — REGLA DE ENMIENDA DE LA BIBLIA

Si durante implementación aparece un hecho que invalida el plan:

```text
OBSERVE
  ↓
FALSIFY CURRENT ASSUMPTION
  ↓
STOP PRODUCTIVE MUTATION
  ↓
UPDATE SPEC / ADR EXPLICITLY
  ↓
REVIEW
  ↓
RELOAD NEW SPEC
  ↓
CONTINUE
```

No se permite que el código «se adelante» a la Biblia por comodidad.

<!-- MICHI_PHASE2:BOOTSTRAP:END -->

------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE_INDEX:BEGIN -->

# BIBLIA B — MAPA DE FASES DE IMPLEMENTACIÓN

Las fases siguientes son **gates de aceptación**, no una excusa para reconstruir
el proyecto mediante un big-bang rewrite. Cada fase consume las autoridades
cerradas de la anterior y produce contratos verificables para la siguiente.

Estados permitidos:

```text
LOCKED      dependencia o gate aún no satisfecho
READY       dependencias cerradas; puede iniciarse
ACTIVE      existe trabajo productivo en curso
VERIFYING   código terminado; gates/physical evidence en ejecución
CLOSED      DoD completo y baseline de la fase congelada
BLOCKED     una falsación externa/hardware impide continuar
```

Todo Audio Phase 2 comienza con:

```text
AP2-F00 = LOCKED
```

mientras el contrato temporal de la sección 0 continúe activo.

## BIBLIA B.1 — DAG DE FASES

```text
                               AP2-F00
                      ACTIVATION / BASELINE FREEZE
                                  │
                                  ▼
                               AP2-F01
                     AUTHORITIES / COMPATIBILITY
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
           AP2-F02             AP2-F03             AP2-F04
       DEVICE KNOWLEDGE     SIGNAL PATH BASE       DSP DOMAIN
              │                   │                   │
              │                   │                   ▼
              │                   │                AP2-F05
              │                   │             PCM DSP RUNTIME
              │                   │                   │
              │                   │                   ▼
              │                   │                AP2-F06
              │                   │          DSP FEATURE COMPLETENESS
              │                   │
              │                   └────────────┐
              │                                │
              │                                ▼
              │                             AP2-F07
              │                      DSD SOURCE / QUALIFICATION
              │                                │
              │                                ▼
              │                             AP2-F08
              │                         NATIVE DSD RUNTIME
              │                                │
              │                                ▼
              │                             AP2-F09
              │                               DOP
              │                                │
              │                    ┌───────────┴───────────┐
              │                    │                       │
              │                    ▼                       │
              │                 AP2-F10 ◄──────────────────┘
              │         DSD→PCM / DSP / TRANSITIONS
              │                    │
              └──────────┬─────────┴──────────┬──────────┐
                         │                    │          │
                         ▼                    ▼          ▼
                      AP2-F11              AP2-F12    AP2-F13
                  UI/UX CONVERGENCE   DEVICE HIGH-END PERSIST/PACKAGING
                         │                    │          │
                         └──────────────┬─────┘          │
                                        └──────┬─────────┘
                                               ▼
                                            AP2-F14
                                   PHYSICAL / PERFORMANCE
                                               │
                                               ▼
                                            AP2-F15
                                     FINAL ADVERSARIAL SEAL
```

`AP2-F02`, `AP2-F03` y `AP2-F04` pueden avanzar en paralelo **sólo después** de
cerrar F01. Sus merges deben seguir manteniendo los contracts de baseline.

## BIBLIA B.2 — TABLA MAESTRA

| Fase | Nombre | Dependencias | Núcleo | Resultado obligatorio |
|---|---|---|---|---|
| AP2-F00 | Activation & Baseline Freeze | gate sección 0 | baseline, manifests | commit base inmutable |
| AP2-F01 | Authority & Compatibility Foundation | F00 | ADR, tipos, adapters | fronteras de ownership cerradas |
| AP2-F02 | Device Knowledge & Capability Intelligence | F01 | **extensión de `audio_device_semantics.py` existente**, evidence Phase2, MAHKB, commercial identity | un device físico = una identidad explicable sin duplicar `AudioDeviceRegistry` |
| AP2-F03 | Signal Path & Proof Projection Foundation | F01 | graph, evidence, M11.5 projection | path generation-safe sin segunda proof authority |
| AP2-F04 | DSP Domain & Compiler | F01 | ProcessingGraph, profile, compiler | plan DSP puro/determinista |
| AP2-F05 | PCM DSP Runtime | F04 | GStreamer executor, evidence | DSP PCM transaccional |
| AP2-F06 | DSP Feature Completeness | F05 | PEQ/FIR/resample/dither/adapters gates | core DSP audiófilo cerrado |
| AP2-F07 | DSD Source Truth & Qualification | F01,F02,F03 | DSD format, characterization, ALSA | DSD first-class sin PCM implícito |
| AP2-F08 | Native DSD Runtime | F07 | strict DSD sink/execution | Native DSD fail-closed |
| AP2-F09 | DoP Runtime | F07,F08 | packer/carrier/planner | DoP byte-verificado y explícito |
| AP2-F10 | DSD↔PCM/DSP Interoperability | F06,F08,F09 | conversion, transitions | matriz DSD×DSP sin ambigüedad |
| AP2-F11 | Product UI/UX Convergence | F02,F03,F06,F10 | NowPlaying, Signal Path, Audio Lab, Device Setup | una UX con read models, no nuevas autoridades |
| AP2-F12 | High-End Device Intelligence & Native Profiles | F02,F10 | setup, health, native profile/control gates | conocimiento/automatización explicables |
| AP2-F13 | Persistence, Migration, Security & Packaging | F11,F12 | schema, migrations, feature discovery | instalación/restart/rollback seguros |
| AP2-F14 | Physical Qualification & Performance | F13 | hardware matrix, latency, CPU/XRUN | evidencia física por formato/path |
| AP2-F15 | Final Adversarial Seal | F14 | verifier, KILLCRITIC, full suite | Audio Phase 2 CLOSED/FROZEN |

## BIBLIA B.3 — PRIMARY_PHASE ES OBLIGATORIA

Cada tarea productiva declara exactamente una:

```text
PRIMARY_PHASE=AP2-Fxx
```

Puede leer dependencias cerradas pero no reabrirlas. Si una modificación necesita
mutar dos fases simultáneamente, debe dividirse en commits o elevar un
`STOP_CROSS_PHASE_SCOPE` para revisar el plan.

## BIBLIA B.4 — FASES Y WORK PACKAGES EXISTENTES

Los IDs históricos `P2-*`, `DSP-*` y `DSD-*` **no desaparecen**. Se convierten
en unidades internas de las fases AP2-Fxx. Las tarjetas detalladas de la sección
182 en adelante especifican el mapping normativo.

<!-- MICHI_PHASE2:PHASE_INDEX:END -->

------------------------------------------------------------------------

------------------------------------------------------------------------

# 0. CONTRATO TEMPORAL --- REGLA MÁS IMPORTANTE

Este documento **NO AUTORIZA todavía Audio Phase 2 productivo**. La autoridad
heredada debe leerse según el repositorio reconciliado V7, no según snapshots
históricos de septiembre 21.

## 0.1 Estado real reconciliado a `main @ 8bea498b0c2838b962352e09aa70da73088ced23`

```text
M11.3 Multi-Engine Audio Runtime
        = DONE / TESTED / FROZEN

M11.4 Audiophile Output & DAC
        = PRODUCTIVE PCM IMPLEMENTATION COMPLETE
        = FIELD-CLOSURE TOOLING COMPLETE
        = FINALIZATION / SEMANTIC EVALUATOR CONTRACT COMPLETE
        = prior bounded device-scoped SMSL physical PASS preserved
        = physical closure EXECUTION still INCOMPLETE
        = archived SMSL + KINMAX manifests still require:
          R25 per-delay first-sample campaign
          R32 8-hour soak / USB health campaign
          R35 four canonical tail/drain observations
          applicable cumulative R36 recovery cases
        = bit-perfect NOT claimed
        = exclusivity NOT claimed

M11.5 Audiophile Playback Guarantees
        = NOT STARTED
        = NOT IMPLEMENTED

DAC-V35-120 hardware volume
        = DO NOT START / OUT OF CURRENT CLOSURE SCOPE

DAC-V35-130 signed profile bundles
        = POST-STABLE ONLY under V3.5

DAC-V35-140 DSD / DoP
        = SEPARATE PROMOTION; NOT STARTED
```

## 0.2 Secuencia obligatoria actualizada

```text
M11.4 PCM implementation closure landed
        ↓
Preserve bounded SMSL physical evidence
        ↓
Complete/resolve the remaining M11.4 PCM closure gates required by the
active canonical V3.5 authority (including the field-closure laboratory
where the release gate requires it)
        ↓
zero inherited DAC P0/P1
        ↓
M11.5 Audiophile Playback Guarantees IMPLEMENTED + TESTED
        ↓
reconcile DSD/DoP ownership between M11.5 / DAC-V35-140 / this plan
        ↓
FREEZE EXACT BASELINE SHA
        ↓
AP2-F00
        ↓
AUDIO PHASE 2
```

No texto histórico de este plan puede degradar el estado actual de M11.4 a
“no implementado”, ni promover M11.5 a implementado.

## 0.3 Gate productivo

Hasta que `AP2-F00` pueda demostrar todos los requisitos de §326:

```text
AUDIO_PHASE_2_IMPLEMENTATION_ALLOWED = FALSE
AUDIO_PHASE_2_PRODUCTION_WIRING_ALLOWED = FALSE
AUDIO_PHASE_2_SCHEMA_MUTATION_ALLOWED = FALSE
AUDIO_PHASE_2_UI_INTEGRATION_ALLOWED = FALSE
AUDIO_PHASE_2_REFACTOR_OF_V35_ALLOWED = FALSE
RESEARCH_AND_DESIGN_ONLY = TRUE
```

La única excepción es trabajo que pertenezca **al contrato activo heredado**
(M11.4/M11.5) y esté autorizado por sus propias especificaciones. Ese trabajo
no se etiqueta falsamente como Audio Phase 2.

**No se debe “preparar” V3.5 mediante refactors oportunistas.** Si el repositorio
actual ya resolvió una capacidad que el plan había previsto implementar, Phase 2
la consume y elimina el duplicado de su alcance.

---

# 1. OBJETIVO

DAC Phase 2 no pretende crear un segundo sistema DAC. Su objetivo es
**elevar el sistema ya estable** mediante:

1.  clasificación estricta de dispositivos para evitar listas
    contaminadas;
2.  identidad comercial del DAC más precisa;
3.  correlación USB ↔ sysfs ↔ ALSA ↔ conocimiento externo;
4.  base local de conocimiento de hardware de audio;
5.  capacidades separadas en `DECLARED`, `OBSERVED`, `QUALIFIED` y
    `RUNTIME`;
6.  fingerprinting prudente de hardware;
7.  provenance/confidence de cada dato;
8.  representación completa del camino de señal;
9.  prueba auditable de preservación de señal;
10. soporte posterior y honesto de PCM, Native DSD, DoP y DSD→PCM;
11. motor de procesamiento DSP audiófilo con bypass verificable, PEQ, FIR,
    convolution, gain/headroom, channel mapping y resampling explícito;
12. integración opcional de procesadores externos de alto nivel sin crear un
    cuarto `AudioEngine`;
13. Signal Path capaz de distinguir señal original, transformaciones
    intencionales, carrier DoP y negociación final;
14. UX premium de Device Setup / Signal Path / Audio Processing;
15. diagnósticos reproducibles sin telemetría obligatoria;
16. presupuesto de latencia, CPU, memoria y XRUN para todo procesamiento;
17. persistencia versionada y reproducible de perfiles DSP;
18. pruebas físicas separadas para PCM, Native DSD, DoP y DSD→PCM.

El objetivo **no** es imitar superficialmente Roon. El objetivo es
conseguir un sistema donde Michi pueda responder:

``` text
¿QUÉ dispositivo es?
¿POR QUÉ creemos que es ese dispositivo?
¿QUÉ capacidades declara?
¿QUÉ capacidades expone Linux?
¿QUÉ capacidades comprobó Michi?
¿QUÉ está negociado ahora?
¿QUÉ transformaciones ocurrieron?
¿QUÉ evidencia respalda cada afirmación?
```

------------------------------------------------------------------------

# 2. NO-OBJETIVOS

Phase 2 NO debe:

-   escribir un driver USB Audio general;
-   reemplazar ALSA;
-   reemplazar `snd-usb-audio`;
-   duplicar la lógica de clocks, feedback, PCM o USB Audio del kernel;
-   inventar capacidades a partir de marketing;
-   considerar `ALSA Direct == bit-perfect`;
-   usar el nombre comercial como identidad persistente;
-   depender de Internet durante playback;
-   hacer telemetría obligatoria;
-   tratar `UNKNOWN` como `FAILED`;
-   inferir 32 bits significativos porque ALSA use `S32_LE`;
-   elegir arbitrariamente un endpoint cuando existan varios bindings
    ambiguos;
-   convertir una coincidencia VID/PID en certeza si el identificador
    corresponde a un controlador OEM reutilizado;
-   mezclar "fabricante comercial del DAC" con "fabricante/controlador
    de la interfaz USB";
-   tratar DoP como PCM musical sólo porque utilice un carrier PCM;
-   aplicar DSP PCM sobre un stream Native DSD o sobre el carrier DoP;
-   convertir DSD→PCM de forma implícita o silenciosa;
-   insertar resampling, limiter, normalization, dither o gain oculto;
-   convertir CamillaDSP, PipeWire o un host LV2 en un cuarto `AudioEngine`;
-   introducir trabajo Python por-muestra en el hot path de audio;
-   aceptar un plugin DSP de terceros como autoridad de playback o de DAC.

------------------------------------------------------------------------

# 3. BASELINE QUE PHASE 2 HEREDA --- NO REIMPLEMENTAR

La baseline real ha avanzado de forma sustancial. A `main @
bc53642039d1e2597abba476215a198949887c2d`, Phase 2 debe tratar las siguientes
piezas como **autoridades heredadas**, no como tareas nuevas.

## 3.1 Ownership y ejecución heredados

```text
PlaybackSessionService            sequence/navigation authority
PlaybackService                   PlaybackState + transport orchestration
AudioEngineService                engine state/selection authority
AudioDeviceRegistry               physical/local audio identity + current bindings
AudioOutputProfileService         persisted output profile authority
AudioOutputSelectionCoordinator   explicit output/path selection intents
OutputPlanner                     current PCM Direct plan authority
OutputSessionService              selected/active output session authority
DacQualificationService           exact ALSA qualification authority
CandidateCarrierResolver          bounded PCM carrier policy
DirectOutputExecutor              productive Direct execution authority
SignalTruthRecorder               canonical current runtime Signal Truth
VolumePolicyService               volume authority
AudioOutputBridge                 canonical current QML projection of output truth
```

## 3.2 Discovery/classification ya implementados

`AudioDeviceRegistry` admite una identidad nueva sólo cuando Linux demuestra un
**ALSA PCM playback binding actual**; conserva identidades previamente admitidas
como unavailable para preservar intent/hotplug.

Existe `src/michi/application/audio_device_semantics.py` con clasificación de
presentación separada de admission:

```text
EXTERNAL_AUDIO
AUDIO_INTERFACE      enum reservado; no inferir sólo por capture
LOCAL_AUDIO
DISPLAY_AUDIO
OTHER_AUDIO
```

`AudioOutputBridge` ya agrupa System Output, External Audio, Built-in / Local
Audio, Display Audio y Other Audio. P2-010 no puede crear un segundo classifier
paralelo.

## 3.3 Capability truth y carrier policy ya implementados

```text
DacQualificationService
  exact-open + exact readback
  BUSY/REMOVED/TIMEOUT != unsupported
  device-bound environment fingerprint v2
  single-flight exact qualification

CandidateCarrierResolver
  S16_LE exact for <=16 significant bits
  S32_LE exact for <=24 significant bits
  bounded S16→S32 container-width candidate only when policy allows

AudioOutputBridge
  tuple-scoped qualified capability projection
  no Cartesian capability fabrication
  Strict / Compatible / Shared vocabulary
```

Phase 2 construye `DECLARED / OBSERVED / QUALIFIED / RUNTIME` encima de estas
evidencias; no reemplaza `CapabilityEvidence` ni el resolver PCM.

## 3.4 Signal Truth actual

El recorder actual distingue `DIRECT`, `DIRECT_CONTAINER_ADAPTED`, `DSP`,
`RESAMPLED`, `REMIXED`, `UNKNOWN` y `CONTRADICTED`, con evidence de
converter/resampler/remix y readback de dithering/noise-shaping para una
adaptación autorizada. `SignalPathGraph` será explicación estructurada encima de
esta verdad, no otro classifier.

## 3.5 GStreamer actual sigue siendo PCM-first

`GStreamerSourceCharacterizer` todavía exige `audio/x-raw`; una salida no PCM
genera `SOURCE_ENCODING_UNSUPPORTED`. El strict Direct sink y
`CandidateCarrierResolver` actuales son PCM. Por tanto Native DSD/DoP siguen
siendo gaps reales.

## 3.6 Cierre PCM y laboratorio físico actual

```text
src/michi/application/dac_pcm_closure.py
scripts/dac_m11_4_pcm_lab.py
tests/dac/test_v35_final_pcm_closure.py
```

El cierre exige R24/R25/R32/R35/R36 con facts estructurados y evidence refs.
Un device completo produce como máximo `PASS_BOUNDED`; dos devices materialmente
distintos y completos son necesarios para `PASS_MULTI_HARDWARE`.

Los manifests 2026-09-26 para SMSL y KINMAX HA01 son real discovery pero todos
sus experimentos de cierre siguen `NOT_RUN`; no son una nueva physical PASS.

## 3.7 UI/output actual reutilizable

`AudioOutputPopup` ya es grouped + scroll-bounded; `DacDiagnosticsDisclosure`
muestra qualified tuples, identidad, classification, playback endpoints, ALSA,
environment y runtime graph. `AudioOutputBridge` preserva selected != active,
path mode y Signal Truth. `NowPlayingBar` sigue con engine quick selector,
quality pill sin HD/DSD, local AudioOutput en row0/col3 y Queue en row1/col2.

El target V6 §§306–313 aún no está implementado.

**Phase 2 se monta encima de estos contratos. No crea autoridades paralelas.**

---

# 4. PROBLEMA A --- EVITAR "UN SINFÍN DE DISPOSITIVOS"

El problema de admission masiva está **parcialmente resuelto**: el registry sólo
admite nuevos Audio Outputs con playback ALSA PCM actual, mientras classification
queda separada como presentation semantics.

## 4.1 Modelo actual a preservar

```text
raw sysfs / USB / ALSA observations
        ↓
AudioDeviceRegistry
        │ admission = real current ALSA playback capability
        ▼
AudioDeviceSnapshot
        ↓
classify_audio_device()
        ↓
AudioOutputBridge.deviceGroups
```

No allowlist/blacklist de vendor o VID/PID sustituye este gate. Capture
capability no demuestra por sí sola `AUDIO_INTERFACE`.

## 4.2 Delta Phase 2 permitido

Phase 2 sólo agrega **knowledge classification** encima de admission existente:

```text
PlaybackAdmission
  registry playback truth

Presentation/Knowledge
  current category
  + commercial role
  + MAHKB/provenance
  + conflicts/unknown
```

Network y virtual transports no se convierten en DAC local por clasificación.

## 4.3 Visible != Direct activation eligible

```text
visible_in_audio_output
    = registry admission + retained selected identity semantics

can_attempt_direct
    = current playback binding
      + GStreamer Direct available
      + endpoint resoluble
      + tuple qualification/plan policy
```

Un device puede ser visible antes de cualificar una nueva tuple.

## 4.4 Consecuencia para P2-010

`P2-010` significa `Classification Enrichment & Knowledge Projection`, consumiendo
`AudioDeviceRegistry`, `audio_device_semantics.py` y `AudioOutputBridge`.

---

# 5. PROBLEMA B --- IDENTIDAD COMERCIAL DEL DAC

## 5.1 Limitación real

Linux puede entregar:

``` text
manufacturer = XMOS
product      = USB Audio 2.0
```

aunque el aparato comercial sea de otro fabricante/modelo.

Windows/macOS pueden mostrar información más específica cuando un
driver/software del fabricante incorpora conocimiento adicional. Michi
no debe fingir que los descriptores USB contienen información que no
contienen.

## 5.2 Nuevo componente: `DacIdentityResolver`

``` text
USB descriptors ──────────────┐
VID/PID ──────────────────────┤
sysfs topology ───────────────┤
ALSA card/longname ───────────┤
udev/hwdb ────────────────────┤
Michi Hardware KB ────────────┤
known kernel knowledge ───────┤
                              ▼
                     DacIdentityResolver
                              ↓
                     ResolvedDacIdentity
```

### Modelo conceptual

``` python
@dataclass(frozen=True)
class ResolvedDacIdentity:
    stable_device_id: str
    commercial_manufacturer: EvidenceValue[str]
    commercial_model: EvidenceValue[str]
    usb_manufacturer: EvidenceValue[str]
    usb_product: EvidenceValue[str]
    vid: EvidenceValue[str]
    pid: EvidenceValue[str]
    serial: EvidenceValue[str]
    controller_family: EvidenceValue[str]
    usb_audio_class: EvidenceValue[str]
```

La identidad persistente V3.5 **no se sustituye** por este modelo.
`ResolvedDacIdentity` es enriquecimiento/proyección.

------------------------------------------------------------------------

# 6. EVIDENCE VALUE --- NINGÚN DATO SIN PROCEDENCIA

Toda afirmación enriquecida debe poder explicar de dónde salió.

``` python
class EvidenceOrigin(Enum):
    SYSFS = "sysfs"
    USB_DESCRIPTOR = "usb_descriptor"
    ALSA = "alsa"
    UDEV_HWDB = "udev_hwdb"
    USB_IDS = "usb_ids"
    KERNEL_KNOWLEDGE = "kernel_knowledge"
    MICHI_KB = "michi_kb"
    PHYSICAL_QUALIFICATION = "physical_qualification"
    RUNTIME = "runtime"
    USER_OVERRIDE = "user_override"

class EvidenceConfidence(Enum):
    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class EvidenceValue(Generic[T]):
    value: T | None
    origin: EvidenceOrigin
    confidence: EvidenceConfidence
    evidence_key: str | None
```

Regla:

``` text
NO EVIDENCE → UNKNOWN
CONFLICTING EVIDENCE → CONFLICT / UNKNOWN
DATABASE MATCH ≠ RUNTIME VERIFIED
USER LABEL ≠ HARDWARE IDENTITY
```

------------------------------------------------------------------------

# 7. MICHI AUDIO HARDWARE KNOWLEDGE BASE --- MAHKB

No crear simplemente una "lista de DAC". Crear una base extensible de
conocimiento de hardware de audio.

## 7.1 Fuentes candidatas a investigar

-   `usb.ids`: VID/PID y nombres USB.
-   Linux `snd-usb-audio`: quirks y conocimiento de dispositivos.
-   tablas/quirks del kernel Linux.
-   Linux Hardware / hw-probe / colecciones de `lsusb`.
-   ALSA UCM.
-   udev/hwdb.
-   PipeWire/ACP/UCM solo como evidencia complementaria de
    clasificación/perfiles.
-   documentación oficial del fabricante, únicamente como `DECLARED`.
-   resultados de la propia cualificación física Michi como `QUALIFIED`.

**Antes de importar o redistribuir datos, revisar licencia, formato,
atribución y política de actualización de cada fuente.**

## 7.2 Arquitectura local/offline

``` text
resources/
└── audio_hardware/
    ├── schema.json
    ├── vendors.json
    ├── usb_products.json
    ├── commercial_aliases.json
    ├── controller_families.json
    ├── linux_quirk_index.json
    ├── dsd_knowledge.json
    └── overrides.json
```

No se requiere acceso web durante reproducción.

## 7.3 Entrada conceptual

``` json
{
  "match": {
    "vid": "xxxx",
    "pid": "yyyy",
    "usb_product_regex": "..."
  },
  "identity": {
    "commercial_manufacturer": "...",
    "commercial_model": "...",
    "controller_family": "..."
  },
  "declared_capabilities": {},
  "provenance": [],
  "confidence": "high"
}
```

------------------------------------------------------------------------

# 8. CAPABILITY RESOLVER --- CUATRO VERDADES SEPARADAS

Nunca colapsar en un único `supports_*`.

``` text
DECLARED
    Lo que una fuente externa/fabricante afirma.

OBSERVED
    Lo que Linux/USB/ALSA expone.

QUALIFIED
    Lo que Michi probó explícitamente con el dispositivo.

RUNTIME
    Lo que está negociado durante esta sesión.
```

Ejemplo:

``` text
                    Declared   Observed   Qualified   Runtime
44.1 kHz               ✓          ✓           ✓          -
96 kHz                 ✓          ✓           ✓          ✓
192 kHz                ✓          ✓           ✓          -
768 kHz                ✓          ✓           ?          -
DSD256                 ✓          ?           ?          -
```

Un `?` no es un fallo.

## 8.1 API conceptual

``` python
@dataclass(frozen=True)
class CapabilityEvidence:
    capability: str
    declared: EvidenceValue[bool]
    observed: EvidenceValue[bool]
    qualified: EvidenceValue[bool]
    runtime: EvidenceValue[bool]
```

------------------------------------------------------------------------

# 9. DAC FINGERPRINTING

Solo se activa cuando los identificadores normales no bastan.

## 9.1 Señales posibles

``` text
VID/PID
USB strings
descriptor structure
interface count
altsettings
playback interfaces
USB Audio Class
PCM formats
sample-rate set
channel configurations
DSD behavior
ALSA longname
known quirks
serial pattern
topology
```

## 9.2 Regla de seguridad

Fingerprinting produce una **identificación derivada**, nunca una
observación.

``` text
OBSERVED IDENTITY
DERIVED IDENTITY
DATABASE IDENTITY
USER LABEL
```

deben permanecer distinguibles.

No usar un fingerprint para cambiar `stable_device_id`.

------------------------------------------------------------------------

# 10. SIGNAL PATH GRAPH

`SignalTruth` se conserva. Phase 2 agrega una representación estructural
de todo el camino.

``` text
SignalTruth = verificador/veredicto
SignalPathGraph = explicación estructurada
```

## 10.1 Modelo conceptual

``` python
@dataclass(frozen=True)
class SignalNode:
    node_id: str
    stage: SignalStage
    provider: str
    input_signal: SignalFormat | None
    output_signal: SignalFormat | None
    transformation: TransformationState
    evidence: tuple[SignalEvidence, ...]
    confidence: EvidenceConfidence
    generation: int
```

## 10.2 Etapas

``` text
CONTAINER
DECODE
ENGINE
CONVERTER
RESAMPLER
DSP
VOLUME
TRANSPORT
ALSA_NEGOTIATION
USB_AUDIO
DAC
```

Solo aparecen nodos que puedan justificarse. No inventar nodos para
"completar" visualmente la cadena.

## 10.3 Ejemplo PCM

``` text
SOURCE
FLAC · 96 kHz · 24 bit · Stereo
        ↓
DECODE
PCM · 96 kHz · 24 significant bits · Stereo
        ↓
ENGINE
GStreamer
96 kHz · 24 significant bits
        ↓
TRANSFORMS
No negotiated resampling
No negotiated remix
No DSP
        ↓
VOLUME
Fixed / unity
        ↓
ALSA DIRECT
hw binding actual
S32_LE · 96 kHz
24 significant bits · 2 ch
        ↓
USB AUDIO
UAC2
        ↓
DAC
Commercial identity + runtime evidence
```

------------------------------------------------------------------------

# 11. SIGNIFICANT BITS --- REGLA INNEGOCIABLE

`S32_LE` describe un contenedor. No demuestra 32 bits significativos.

``` text
container_bits != significant_bits
```

Ejemplo válido:

``` text
ALSA format       S32_LE
container bits    32
significant bits  24
```

Si la evidencia de bits significativos es ambigua:

``` text
significant_bits = UNKNOWN
BitPerfectState   = UNVERIFIED
```

Nunca rellenar ese hueco desde metadata, perfil, marketing o heurística.

------------------------------------------------------------------------

# 12. M11.5 PROOF AUTHORITY + PHASE 2 PROOF PROJECTION

Phase 2 **NO crea un segundo BitPerfect engine**. M11.5 es la autoridad
canónica que decide el estado de preservación una vez que su contrato haya sido
implementado y congelado. Phase 2 consume esa verdad y la vuelve explicable.

Nunca usar:

``` text
Direct ALSA => BIT PERFECT
GStreamer => BIT PERFECT
Native DSD => BIT PERFECT
DoP => BIT PERFECT
DSP bypass requested => BIT PERFECT
```

La cadena de autoridad es:

``` text
runtime evidence
      ↓
SignalTruth / M11.5 conformance
      ↓
BitPerfectState / preservation facts
      ↓
Phase 2 SignalProofProjection
      ↓
SignalPathGraph + WHY? + UI
```

## 12.1 Condiciones mínimas PCM

``` text
decoded.rate == engine.rate == negotiated.rate
decoded.significant_bits == engine.significant_bits == negotiated.significant_bits
decoded.channel_layout == engine.channel_layout == negotiated.channel_layout
resampling == FALSE
remix == FALSE
DSP == FALSE
software_gain == UNITY_OR_BYPASSED
lossy_format_conversion == FALSE
evidence_complete == TRUE
```

## 12.2 Estados — propiedad de M11.5

``` text
VERIFIED
UNVERIFIED
NOT_APPLICABLE
BROKEN
```

`UNVERIFIED` = evidencia insuficiente. `NOT_APPLICABLE` es el estado normal
cuando el usuario solicita una transformación intencional que hace inaplicable
la afirmación bit-perfect, por ejemplo PEQ, convolution, gain digital no-unity
o DSD→PCM.

## 12.3 Proyección Phase 2 — no autoridad paralela

``` python
@dataclass(frozen=True, slots=True)
class SignalProofProjection:
    state: BitPerfectState
    preserved_rate: TriState
    preserved_significant_bits: TriState
    preserved_channels: TriState
    resampling_absent: TriState
    remix_absent: TriState
    dsp_absent: TriState
    software_gain_unity: TriState
    intentional_transforms: tuple[str, ...]
    contradictions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    evidence_refs: tuple[str, ...]
```

`SignalProofProjection` explica; no recalcula el veredicto.

------------------------------------------------------------------------

# 13. DSD / DoP --- INTEGRACIÓN DE PRIMER NIVEL, SIN DUPLICAR M11.5

DSD deja de ser una extensión cosmética. La arquitectura final debe distinguir
**la señal**, **el transporte**, **el carrier** y **la negociación del DAC**.

M11.5 conserva la autoridad sobre sus garantías mínimas y transiciones. Phase 2
puede ampliar policy, instrumentación, Device Setup, Signal Path, matrices
físicas y backends, pero no crea un segundo contrato contradictorio. Al activar
Phase 2 se debe reconciliar con lo realmente entregado por M11.5.

## 13.1 Modos canónicos

``` text
NATIVE_DSD
DOP
DSD_TO_PCM
UNKNOWN
```

DoP **no** aparece como `PCM_CONVERSION`: el carrier es PCM-compatible, pero el
payload sigue siendo DSD.

## 13.2 Signal Path obligatorio

``` text
SOURCE ENCODING
TRANSPORT MODE
CARRIER
DEVICE NEGOTIATED MODE
FINAL EVIDENCE STATE
```

Ejemplo:

``` text
SOURCE        DSD64
ENGINE        DSD64
TRANSPORT     DoP
CARRIER       176.4 kHz / 24-bit framing
DAC MODE      DSD64
```

Si la capa final del DAC no puede observarse directamente:

``` text
software/carrier evidence = VERIFIED AT SOFTWARE BOUNDARY
DAC interpretation        = UNVERIFIED / QUALIFIED EXTERNALLY
```

Nunca promocionar automáticamente a `VERIFIED` sólo porque los markers DoP sean
correctos.

## 13.3 Policy

``` python
class DsdPolicy(Enum):
    AUTO = "auto"
    NATIVE = "native"
    DOP = "dop"
    PCM_CONVERSION = "pcm_conversion"
    DISABLED = "disabled"

class DsdFallbackPolicy(Enum):
    STOP = "stop"
    ASK = "ask"
    PCM_CONVERSION = "pcm_conversion"
```

`AUTO` sólo puede elegir un modo respaldado por evidence. `PCM_CONVERSION` como
fallback debe ser explícitamente admitido por policy; nunca silencioso.

## 13.4 Regla DSP

``` text
Native DSD + PCM DSP     = FORBIDDEN
DoP carrier + PCM DSP    = FORBIDDEN
DSD→PCM + DSP            = ALLOWED / EXPLICIT
Native DSD + DSP BYPASS  = ALLOWED
DoP + DSP BYPASS         = ALLOWED
```

Toda transformación DSD→PCM se muestra como nodo de Signal Path.

------------------------------------------------------------------------

# 14. HARDWARE VOLUME

Phase 2 puede enriquecer la cualificación, pero no debe romper
`VolumePolicyService`.

Distinguir:

``` text
FIXED
MICHI_SOFTWARE
ALSA_HARDWARE
DEVICE_EXTERNAL
UNKNOWN
```

El Signal Path debe representar la ganancia digital como transformación
cuando corresponda.

``` text
Software volume 72 %
    ↓
PROCESSED
```

No ocultarla para conservar una etiqueta "bit-perfect".

------------------------------------------------------------------------

# 15. DEVICE SETUP PREMIUM

La UI debe usar progressive disclosure.

## Nivel 1 --- usuario normal

``` text
TOPPING D90SE
USB DAC
Connected
Direct available
Current: 96 kHz / 24-bit significant
```

## Nivel 2 --- audiófilo

``` text
PCM capabilities
DSD/DoP
Volume authority
Transport
Current negotiated format
Verification state
```

## Nivel 3 --- diagnóstico

``` text
VID/PID
USB strings
stable identity
ALSA binding
driver
USB Audio Class
evidence provenance
qualification generation
runtime generation
conflicts/unknowns
```

La UI no debe inundar al usuario con endpoints técnicos.

------------------------------------------------------------------------

# 16. SIGNAL PATH UI

Objetivo conceptual:

``` text
MICHI SIGNAL PATH
● VERIFIED / UNVERIFIED / PROCESSED

SOURCE
FLAC · Lossless
96 kHz · 24 bit · Stereo
  ↓
DECODE
PCM · 96 kHz · 24 significant bits
  ↓
AUDIO ENGINE
GStreamer
No negotiated resampling
No remix
No DSP
  ↓
VOLUME
Fixed / Unity
  ↓
TRANSPORT
Direct ALSA
  ↓
DEVICE NEGOTIATION
S32_LE · 96 kHz
24 significant bits · 2 channels
  ↓
DAC
[Commercial manufacturer/model]
USB Audio Class 2
```

Cada tarjeta/nodo debe poder desplegar **Evidence**:

``` text
96 kHz
Evidence: GstPad current caps

24 significant bits
Evidence: ALSA runtime qualification

Model
Evidence: USB product + MAHKB mapping
Confidence: HIGH
```

Ese nivel de provenance es el diferenciador de Michi.

------------------------------------------------------------------------

# 17. PRIVACIDAD Y RED

Principio:

``` text
PLAYBACK_REQUIRES_NETWORK = FALSE
DAC_IDENTIFICATION_REQUIRES_NETWORK = FALSE
SIGNAL_VERIFICATION_REQUIRES_NETWORK = FALSE
TELEMETRY_REQUIRED = FALSE
```

La MAHKB puede actualizarse como recurso versionado del software. Una
futura actualización online debe ser explícita, cacheable, verificable y
no necesaria para reproducir.

------------------------------------------------------------------------

# 18. ESTRATEGIA DE IMPLEMENTACIÓN --- CATÁLOGO DE WORK PACKAGES

> **Orden normativo:** esta sección conserva los work packages históricos y sus DoD. El orden de ejecución, gates y dependencias entre agentes está definido por **BIBLIA B** y por las tarjetas `AP2-F00..AP2-F15` de las secciones 182–201. Si un listado lineal de esta sección parece contradecir el DAG de fases, prevalece el DAG.

## P2-000 --- Baseline Freeze

Antes de tocar código:

-   registrar commit exacto del DAC V3.5/M11.5 cerrado;
-   registrar suites y artefactos de verificación;
-   confirmar DAC-V35-110 completado;
-   confirmar cero P0/P1 DAC;
-   congelar contratos heredados;
-   crear branch específica Phase 2.

**NO-GO** si cualquiera falta.

## P2-010 --- Classification Enrichment Layer

**V7:** admission universal y clasificación de presentación ya existen. No
crear `AudioDeviceClassifier` paralelo.

Consume:

```text
AudioDeviceRegistry
AudioDeviceSnapshot
classify_audio_device()
current_playback_bindings()
AudioOutputBridge.deviceGroups
```

DoD:

- zero second registry/admission authority;
- categorías actuales compatibles;
- commercial role evidence-backed y UNKNOWN permitido;
- capture no prueba interface;
- network/virtual no contaminan local DAC admission;
- extender los gates de universal discovery ya existentes;
- no regresión de grouped Audio Output.

## P2-020 --- Evidence Primitive

Agregar `EvidenceValue`, provenance, confidence y conflict semantics.

DoD: - immutable; - serializable; - no truth promotion automática; -
unknown/conflict first-class.

## P2-030 --- MAHKB v1

Crear schema, loader, validator y una base mínima.

DoD: - offline; - versionada; - licencia de cada dataset documentada; -
datos externos no sustituyen runtime truth; - corrupción de DB no impide
playback.

## P2-040 --- DAC Identity Resolver

Fusionar evidencia sin alterar identidad estable.

DoD: - commercial identity separada de USB controller identity; -
collisions; - OEM VID/PID; - generic XMOS cases; - conflicting names; -
user alias separado de hardware identity.

## P2-050 --- Capability Resolver

Implementar las cuatro capas:

``` text
DECLARED / OBSERVED / QUALIFIED / RUNTIME
```

DoD: - ninguna capa rellena silenciosamente otra; - runtime tiene máxima
autoridad sobre estado actual; - BUSY/TIMEOUT/REMOVED no generan
evidencia negativa permanente.

## P2-060 --- Hardware Fingerprinting

Solo después de identidad básica.

DoD: - fingerprint versionado; - matching determinista; - confidence
threshold; - nunca cambia stable ID; - ambiguity =\> UNKNOWN.

## P2-070 --- SignalPathGraph Domain

Agregar grafo inmutable, sin UI inicialmente.

DoD: - generation scoped; - stale events rechazados; - no nodos
sintéticos; - provenance por nodo; - compatible con SignalTruth
existente.

## P2-080 --- GStreamer Instrumentation

Instrumentar decoder/effective caps/converter/resampler/volume/DSP seam.

DoD: - selected branch only; - pass-through presence ≠ processing; -
negotiated change sí es transformación; - ambiguity =\> UNKNOWN.

## P2-090 --- ALSA/Transport Evidence

Conectar exact-binding ALSA runtime evidence al grafo.

DoD: - formato; - rate; - channels; - significant bits solo cuando
exista autoridad; - endpoint exacto; - generación correcta.

## P2-100 --- M11.5 Proof Projection / Explainability

Consumir el `BitPerfectState` y preservation facts canónicos de M11.5; Phase 2
NO recalcula el veredicto.

DoD: - no inferencia por "Direct"; - no segunda autoridad de proof; -
contradictions/missing evidence preservados; - evidence refs proyectables; -
WHY? determinista.

## P2-110 --- PCM Physical Matrix

Ejecutar matriz con DAC reales.

Mínimo:

``` text
44.1 / 48 / 88.2 / 96 / 176.4 / 192 kHz
16 / 24 significant bits
S16_LE / S24 variants / S32_LE as applicable
stereo
hotplug
busy
disconnect during playback
suspend/resume
rate transition
same-format transition
```

## P2-120 --- DSD/DoP Evidence Foundation

Sólo después de PCM proof cerrado. Define taxonomía/evidence/presentation y
prepara la convergencia con el track `DSD-*`; cualquier ejecución avanzada
Native/DoP se implementa en ese track sin duplicar garantías M11.5.

## P2-130 --- Premium Device Setup

La UI consume read models; nunca se vuelve autoridad.

## P2-140 --- Signal Path UI

Solo después de que el grafo y proof engine estén físicamente validados.

## P2-150 --- Core Phase 2 Adversarial Seal

KILLCRITIC completo, regresión V3.5, M11.5, packaging, real hardware,
stale generations, malformed DB, conflicts, unplug races.

------------------------------------------------------------------------

# 19. ARCHIVOS PROPUESTOS --- NOMBRES ORIENTATIVOS, NO AUTORIDAD ACTUAL

No crear estos archivos antes de activar Phase 2.

``` text
src/michi/domain/audio_hardware/
    evidence.py
    classification.py
    identity.py
    capabilities.py
    fingerprint.py
    signal_path.py
    signal_proof.py

src/michi/application/audio_hardware/
    device_classifier.py
    dac_identity_resolver.py
    capability_resolver.py
    signal_path_service.py
    signal_proof_service.py

src/michi/infrastructure/audio_hardware/
    mahkb_loader.py
    usb_ids_adapter.py
    udev_hwdb_adapter.py
    linux_quirk_adapter.py

resources/audio_hardware/
    schema.json
    vendors.json
    usb_products.json
    commercial_aliases.json
    controller_families.json
    linux_quirk_index.json
    dsd_knowledge.json

src/michi/presentation/
    audio_hardware_bridge.py
    signal_path_bridge.py

qml/
    .../DacDeviceDetails.qml
    .../SignalPathPanel.qml
    .../SignalPathNode.qml
    .../EvidenceDisclosure.qml
```

Los nombres definitivos deben reconciliarse con la estructura real del
repositorio cuando Phase 2 sea autorizada.

------------------------------------------------------------------------

# 20. CONTRATOS DE NO-REGRESIÓN

Phase 2 no puede:

``` text
crear otro AudioDeviceRegistry
crear otro OutputPlanner
crear otro VolumePolicyService
crear otro playback authority
persistir hw:N,M como identidad
seleccionar DEV=0 por defecto
auto-resumir tras reconnect
hacer fallback silencioso Direct→Shared
rellenar evidence gaps desde metadata
confundir SourceFileFacts con DecodedSourceSignal
confundir S32_LE con 32 significant bits
convertir MAHKB en runtime authority
```

------------------------------------------------------------------------

# 21. FALLBACK Y DEGRADACIÓN

Si MAHKB falla:

``` text
playback continues
identity enrichment degrades
V3.5 canonical identity remains valid
```

Si Identity Resolver falla:

``` text
show canonical Linux/USB identity
do not block playback
```

Si SignalPathGraph carece de evidencia:

``` text
show UNKNOWN / UNVERIFIED
do not fabricate
```

Si la UI Phase 2 falla:

``` text
core playback and V3.5 DAC path remain independent
```

La mejora debe ser **fail-soft para enriquecimiento** y **fail-closed
para afirmaciones de fidelidad**.

------------------------------------------------------------------------

# 22. TESTING

## Unit

-   evidence precedence;
-   conflict resolution;
-   classification;
-   commercial alias matching;
-   OEM controller cases;
-   fingerprint ambiguity;
-   capability layers;
-   signal node normalization;
-   proof verdict.

## Integration

-   sysfs + ALSA + MAHKB;
-   hotplug generation;
-   exact binding;
-   GStreamer selected branch;
-   ALSA runtime;
-   UI read model.

## Adversarial

-   dos DAC idénticos sin serial;
-   dos DAC idénticos con serial;
-   mismo VID/PID, productos comerciales distintos;
-   generic `USB Audio 2.0`;
-   multiple PCM playback endpoints;
-   capture-only USB interface;
-   HDMI + USB DAC + virtual sinks simultáneos;
-   stale sysfs;
-   unplug entre discovery y qualification;
-   EBUSY;
-   malformed MAHKB;
-   conflicting database records;
-   stale Signal Path generation;
-   `S32_LE` con bits significativos desconocidos;
-   resampler presente pero pass-through;
-   resampler realmente activo;
-   software volume no-unity;
-   reconnect con binding ALSA distinto.

## Physical

No declarar `VERIFIED` basándose únicamente en mocks.

------------------------------------------------------------------------

# 23. MÉTRICAS DE ÉXITO

Phase 2 se considera exitosa cuando:

``` text
1 physical DAC = 1 logical DAC entry
```

salvo que exista razón explícita para más de un endpoint.

Además:

-   identidad comercial precisa cuando hay evidencia;
-   identidad genérica honesta cuando no la hay;
-   cero dependencia de Internet para playback;
-   capabilities con provenance;
-   runtime negotiated signal visible;
-   ningún "bit-perfect" derivado solo de Direct;
-   `UNKNOWN` preservado;
-   Signal Path generation-safe;
-   V3.5 y M11.5 sin regresiones;
-   desconectar MAHKB/Phase 2 no rompe el núcleo DAC.

------------------------------------------------------------------------

# 24. RELACIÓN CON ROON SIGNAL PATH

Roon se usa como **benchmark conceptual**, no como especificación.

Michi debe cubrir como mínimo:

``` text
source
decode
processing
volume
transport
device negotiation
DAC
```

pero añadir:

``` text
evidence origin
confidence
declared vs observed vs qualified vs runtime
significant-bit truth
generation identity
contradictions
missing evidence
```

La meta no es una etiqueta bonita; es una explicación falsable.

------------------------------------------------------------------------

# 25. INVESTIGACIÓN PENDIENTE ANTES DE P2-030

Cuando Phase 2 se active, investigar y congelar:

1.  licencias y redistribución de `usb.ids`;
2.  forma correcta de derivar conocimiento de quirks del kernel sin
    copiar lógica indebidamente;
3.  ALSA UCM y udev/hwdb como fuentes;
4.  Linux Hardware/hw-probe: licencia, estabilidad y utilidad real para
    audio;
5.  detección fiable de UAC1/UAC2/UAC3;
6.  fuentes de significant bits por backend/hardware;
7.  límites reales para DSD native/DoP en ALSA/GStreamer;
8.  hardware volume y mixers USB;
9.  DAC OEM que exponen controlador XMOS/CMedia en vez de marca
    comercial;
10. estrategia de actualización y firma/versionado de MAHKB.

------------------------------------------------------------------------

# 26. GATE DE ACTIVACIÓN

Phase 2 solo cambia de `DEFERRED` a `READY` si existe evidencia
explícita de:

``` text
[ ] M11.4 cerrado
[ ] DAC-V35-110 physical qualification cerrado
[ ] M11.5 cerrado
[ ] PCM Direct estable
[ ] Signal Truth estable
[ ] volume authority estable
[ ] disconnect/reconnect estable
[ ] zero DAC P0
[ ] zero DAC P1
[ ] baseline commit congelado
[ ] full suite green
[ ] hardware qualification artifacts preservados
```

Si falta una sola casilla:

``` text
PHASE_2 = NO-GO
```

------------------------------------------------------------------------

# 27. HISTÓRICO / SUPERSEDED — ORDEN LINEAL ANTERIOR (NO USAR PARA SELECCIONAR FASE)

> **SUPERSEDED:** la única autoridad para dependencias y orden de ejecución es **BIBLIA B + AP2-F00..AP2-F15**. Esta sección se conserva exclusivamente como genealogía de los work packages P2-*; ningún agente debe inferir una secuencia actual desde este diagrama.

``` text
AHORA
│
├── terminar DAC V3.5 original
├── cualificación física
├── terminar M11.5
└── congelar baseline
        │
        ▼
DAC PHASE 2
│
├── P2-010 Device Classification
├── P2-020 Evidence Primitive
├── P2-030 MAHKB
├── P2-040 Identity Resolver
├── P2-050 Capability Resolver
├── P2-060 Fingerprinting
├── P2-070 SignalPathGraph
├── P2-080 GStreamer Evidence
├── P2-090 ALSA/Transport Evidence
├── P2-100 M11.5 Proof Projection
├── P2-110 PCM Physical Matrix
├── P2-120 DSD/DoP Evidence Foundation
├── P2-130 Device Setup UI
├── P2-140 Signal Path UI
└── P2-150 Core Phase 2 Adversarial Seal
```

------------------------------------------------------------------------

# 28. DECISIÓN ARQUITECTÓNICA FINAL

La innovación de Michi **no debe ser escribir un nuevo driver DAC**.

La división correcta es:

``` text
Linux / snd-usb-audio / ALSA
        │
        │ sabe hablar con el hardware
        ▼
Michi V3.5
        │
        │ selecciona, planifica y ejecuta con seguridad
        ▼
DAC Phase 2
        │
        ├── comprende la identidad
        ├── clasifica el hardware
        ├── correlaciona conocimiento
        ├── diferencia capacidades
        ├── observa runtime
        ├── construye Signal Path
        ├── verifica preservación
        └── explica la evidencia
```

La aspiración final es:

``` text
LINUX SABE
        ↓
MICHI CORRELACIONA
        ↓
MICHI COMPRENDE
        ↓
MICHI OBSERVA
        ↓
MICHI COMPRUEBA
        ↓
MICHI EXPLICA
```

**DAC Phase 2 debe permanecer desacoplada y posterior al cierre de
V3.5.** Su éxito se mide tanto por lo que añade como por su capacidad de
demostrar que no alteró la autoridad, estabilidad y seguridad del DAC
original.

------------------------------------------------------------------------

# 29. FUENTES Y CONTEXTO TÉCNICO A REVALIDAR AL ACTIVAR PHASE 2

Este plan consolida la discusión y el estado actual del repositorio.
Antes de implementación deberán revalidarse las versiones vigentes de:

-   `docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md`
-   `docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md`
-   `docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md`
-   `docs/STATUS_MATRIX.md`
-   Linux USB Audio / `snd-usb-audio`
-   ALSA PCM/hw_params
-   `usb.ids`
-   ALSA UCM
-   udev/hwdb
-   Linux Hardware / hw-probe
-   PipeWire/ACP/UCM, solo donde aporte clasificación o evidencia

**Regla de revalidación:** el código y los contratos existentes en el
momento de activar Phase 2 tienen precedencia sobre los nombres y seams
hipotéticos de este documento.


---

# 30. EXTENSIÓN HIGH-END — DEVICE SETUP, NATIVE PROFILES Y OPERACIÓN ASISTIDA

Esta extensión consolida la investigación comparativa posterior al plan inicial. Mantiene exactamente el mismo contrato temporal:

```text
STATUS = DEFERRED
IMPLEMENT_NOW = FALSE
MAY_CHANGE_V35 = FALSE
MAY_REOPEN_M11_4 = FALSE
```

Nada de esta sección debe interferir con DAC V3.5/M11.5 mientras la baseline original no esté completamente cerrada.

El objetivo no es acumular opciones. El estándar de calidad es:

```text
correctness
+ explainability
+ hardware awareness
+ safe automation
+ progressive disclosure
+ physical evidence
= high-end DAC experience
```

Roon, Audirvāna y otros reproductores high-end se utilizan como benchmark conceptual y UX, no como especificación ni como obligación de paridad feature-by-feature.

---

# 31. DEVICE SETUP ADAPTATIVO

No utilizar una página universal llena de controles irrelevantes. La configuración debe construirse desde las capacidades y el estado real del dispositivo.

```text
DAC
 ↓
Resolved identity
 ↓
Capabilities
 ↓
Transport availability
 ↓
Volume authority
 ↓
Qualification evidence
 ↓
Device Setup read model
```

Ejemplo:

```text
TOPPING D90SE
────────────────────────────
Connected · USB · Direct ALSA

CURRENT SIGNAL
96 kHz · 24 significant bits · Stereo

PLAYBACK
Mode             Source Native
Volume           Fixed
Buffer           Automatic

CAPABILITIES
PCM              ...
DSD              ...
DoP              ...

SIGNAL INTEGRITY
VERIFIED / UNVERIFIED / PROCESSED

[Advanced] [Diagnostics]
```

## 31.1 Progressive disclosure

Tres niveles:

```text
GENERAL
ADVANCED
EXPERT
```

`GENERAL` debe contener solo decisiones de uso habitual.

`ADVANCED` puede contener:

- PCM limit;
- DSD strategy;
- DoP policy;
- buffer policy;
- channel policy;
- capability override;
- fallback behavior cuando sea aplicable.

`EXPERT` puede mostrar:

- stable identity;
- VID/PID;
- USB descriptors;
- driver;
- UAC revision;
- ALSA binding;
- negotiated hw_params;
- significant-bit evidence;
- qualification generation;
- Signal Path generation;
- provenance/conflicts.

La presencia de un parámetro técnico no obliga a exponerlo al usuario normal.

---

# 32. CAPABILITY OVERRIDES SEGUROS

Algunos dispositivos anuncian capacidades que en la práctica no son utilizables de forma estable. Phase 2 debe permitir limitar capacidades sin modificar la verdad observada.

Nunca hacer:

```text
user_limit = device_capability
```

Usar:

```text
declared_capability
observed_capability
qualified_capability
configured_limit
runtime_negotiation
```

Ejemplo:

```text
PCM maximum

Declared        768 kHz
Observed        768 kHz
Qualified       384 kHz
Configured      Automatic
Runtime         192 kHz
```

Un override es una política, no evidencia de hardware.

Debe existir:

```text
AUTOMATIC / RECOMMENDED
CUSTOM
RESTORE_RECOMMENDED
```

y la UI debe indicar qué parámetros difieren del perfil recomendado.

---

# 33. DAC QUALIFICATION / DEVICE HEALTH

Crear un diagnóstico controlado y reproducible del hardware.

Objetivo:

```text
DEVICE HEALTH

Identity                  VERIFIED
Direct open               VERIFIED
44.1 kHz                  VERIFIED
48 kHz                    VERIFIED
96 kHz                    VERIFIED
192 kHz                   VERIFIED
384 kHz                   UNKNOWN
Rate switching            VERIFIED
Disconnect/reconnect      VERIFIED
Volume authority          VERIFIED
```

La cualificación debe:

- utilizar exact-open/readback;
- no convertir BUSY/TIMEOUT/REMOVED en evidencia negativa permanente;
- ser cancelable;
- no alterar la configuración persistente sin consentimiento;
- no reproducir señales peligrosas;
- registrar entorno y generación;
- distinguir `NOT_TESTED`, `PASS`, `FAIL`, `INCONCLUSIVE`;
- conservar resultados solo cuando la identidad estable corresponda al mismo dispositivo.

No crear un benchmark subjetivo de “calidad sonora”.

---

# 34. ADAPTIVE BUFFER POLICY

La estabilidad debe poder optimizarse sin convertir Settings en un panel ALSA.

Modos:

```text
AUTOMATIC
LOW_LATENCY
MAXIMUM_STABILITY
CUSTOM
```

`AUTOMATIC` es el valor normal.

Métricas diagnósticas posibles:

```text
XRUN count
underrun/recovery
open latency
reopen latency
transition failures
device stalls
```

La adaptación nunca puede cambiar sample rate, bit depth, channel layout, DSP o transport semantics silenciosamente.

Si se recomienda un cambio:

```text
Playback stability issue detected.
Recommended buffer policy: Maximum Stability.
```

Debe requerir una transición segura y quedar explicada.

Los parámetros ALSA concretos permanecen en `EXPERT`/diagnóstico.

---

# 35. AUTOMATIC DAC SETUP

Primera conexión de un dispositivo conocido:

```text
New DAC detected
[commercial identity]

[Set Up Automatically]
[Configure Manually]
```

`Automatic DAC Setup` puede consultar:

```text
canonical V3.5 identity
+ observed ALSA capabilities
+ MAHKB
+ native profile
+ physical qualification
```

y producir un perfil recomendado.

Ejemplo:

```text
Playback        Direct
Rate policy     Source Native
Volume          Fixed
PCM limit       Automatic
DSD policy      ...
Buffer          Automatic
Fallback        Stop
```

Cada decisión automática debe ser explicable y reversible.

No seleccionar una función solo porque aparezca en una base externa si contradice runtime evidence.

---

# 36. EXPLAINABILITY — PATRÓN “WHY?”

Toda decisión automática importante debe poder explicar:

```text
WHAT
WHY
EVIDENCE
ALTERNATIVE
```

Ejemplo:

```text
Source Native

Why?

Source: 96 kHz
DAC qualified at 96 kHz.
No resampling is required.
Selected automatically by Michi.

Evidence:
DecodedSourceSignal
ALSA qualification
Current OutputPlan
```

Otro ejemplo:

```text
PCM limit: 384 kHz

Why?

768 kHz is declared and observed,
but the highest physically qualified
rate is currently 384 kHz.
```

La explicación no puede inventar causalidad cuando solo existe correlación.

---

# 37. INTERACTIVE SIGNAL PATH

El Signal Path debe tener dos niveles.

## 37.1 Compact

```text
VERIFIED

FLAC 96/24
 → PCM 96/24sig
 → GStreamer
 → ALSA Direct
 → DAC 96/24sig
```

## 37.2 Detailed

```text
SOURCE
 ↓
DECODE
 ↓
PROCESSING
 ↓
VOLUME
 ↓
TRANSPORT
 ↓
ALSA NEGOTIATION
 ↓
USB AUDIO
 ↓
DAC
```

Cada nodo debe ser desplegable y mostrar provenance.

Ejemplo:

```text
NEGOTIATED SIGNAL

Rate
96,000 Hz
Evidence: ALSA hw_params

Container format
S32_LE
Evidence: ALSA hw_params

Significant bits
24
Evidence: qualified runtime authority

Generation
1842
```

No convertir el Signal Path en una animación decorativa. Si un nodo no tiene evidencia, debe indicarlo.

---

# 38. DIAGNOSTICS & SUPPORT BUNDLE

Crear un paquete de diagnóstico local, explícitamente generado por el usuario.

Puede contener:

```text
Michi version
kernel version
ALSA version
GStreamer version
stable anonymizable device identity
VID/PID
USB descriptors relevant to audio
driver
ALSA bindings
qualification summary
Signal Path summary
recent typed DAC errors
XRUN statistics
configuration profile
```

Reglas:

- no telemetría automática;
- preview antes de exportar;
- redactar rutas personales, nombres de usuario y otros datos innecesarios;
- serial del DAC excluido por defecto o claramente indicado;
- nunca incluir biblioteca musical, historial o credenciales.

---

# 39. NATIVE DEVICE KNOWLEDGE — APROVECHAR LINUX SIN REIMPLEMENTARLO

Phase 2 debe aprovechar conocimiento libre/upstream disponible, pero no crear un segundo driver stack.

Fuentes candidatas:

```text
Linux snd-usb-audio
Linux USB Audio quirks
ALSA UCM
udev/hwdb
usb.ids
sysfs
ALSA runtime
MAHKB
Michi physical qualification
```

Responsabilidades:

```text
usb.ids
    identity hints

snd-usb-audio / kernel knowledge
    device-specific behavior already known by Linux

ALSA/UCM
    Linux audio configuration knowledge

MAHKB
    normalized Michi knowledge

physical qualification
    what Michi has actually proved
```

El kernel sigue siendo autoridad de ejecución de bajo nivel.

---

# 40. TRES NIVELES DE INTEGRACIÓN NATIVA

No todos los DAC permiten la misma integración.

## 40.1 LEVEL 1 — CLASS COMPLIANT

```text
USB Audio Class
 ↓
snd-usb-audio
 ↓
ALSA
 ↓
Michi
```

Capacidades normales de playback sin conocimiento comercial específico.

Estado UI sugerido:

```text
Class Compliant
```

Esto no es un estado de inferior calidad.

## 40.2 LEVEL 2 — MICHI NATIVE PROFILE

Dispositivo con conocimiento suficiente:

```text
V3.5 canonical identity
+ MAHKB
+ Linux knowledge
+ qualification
= Michi Native Profile
```

Puede aportar:

```text
commercial identity
recommended Direct policy
known PCM behavior
DSD/DoP knowledge
volume behavior
buffer recommendation
capability limits
known compatibility notes
```

El Native Profile es recomendación/conocimiento; nunca sustituye runtime truth.

## 40.3 LEVEL 3 — MICHI NATIVE CONTROL

Solo para hardware cuyo protocolo específico esté documentado de forma abierta, implementado upstream de forma reutilizable o pueda soportarse legal y técnicamente con alta confianza.

Posibles controles:

```text
input selection
digital filter
clock source
hardware volume
gain
mute
phase
DSD mode
display settings
```

`Native Control` es opcional por dispositivo.

No realizar ingeniería inversa indiscriminada de drivers propietarios dentro de este plan.

No introducir Native Control antes de cerrar completamente Levels 1 y 2.

---

# 41. DAC NATIVE PROFILE

Modelo conceptual:

```python
@dataclass(frozen=True)
class DacNativeProfile:
    profile_schema_version: int
    match_rules: tuple
    commercial_identity: object
    linux_knowledge: object
    pcm_knowledge: object
    dsd_knowledge: object
    volume_knowledge: object
    compatibility: object
    recommended_policy: object
    provenance: tuple
```

Un perfil puede contener:

```text
IDENTITY
VID/PID
USB descriptors
commercial manufacturer/model
controller family

LINUX
driver
known quirks
UCM relationship
minimum/relevant kernel notes

PCM
known formats/rates
significant-bit knowledge
known restrictions

DSD
native/DoP knowledge
transport restrictions

VOLUME
fixed/hardware/external knowledge

MICHI
recommended policy
qualification history
compatibility notes
```

No guardar `hw:N,M` como identidad.

---

# 42. NATIVE PROFILE RESOLVER

Pipeline:

```text
CanonicalAudioDevice
        │
        ├── USB descriptors
        ├── VID/PID
        ├── ALSA identity
        ├── Linux knowledge
        └── MAHKB
                ↓
       NativeProfileResolver
                ↓
       ResolvedNativeProfile
                ↓
       recommended policy
```

Precedencia:

```text
runtime evidence
    >
current physical qualification
    >
exact known profile
    >
observed descriptors
    >
external declared knowledge
```

Una recomendación nunca debe invalidar una contradicción runtime.

---

# 43. KERNEL KNOWLEDGE INGESTION

No consultar/parsing del source tree del kernel durante playback.

Si se decide incorporar conocimiento derivado de upstream:

```text
upstream source
    ↓
development/build importer
    ↓
normalization
    ↓
license/provenance validation
    ↓
versioned MAHKB artifact
    ↓
runtime read-only consumption
```

Antes de implementar:

- revisar licencias;
- determinar qué datos pueden redistribuirse;
- registrar versión/source commit;
- evitar duplicar lógica que debe permanecer en `snd-usb-audio`;
- mantener actualización reproducible.

Alternativa cuando la redistribución sea problemática: detectar el comportamiento ya expuesto por el kernel instalado en lugar de copiar tablas upstream.

---

# 44. NATIVE CONTROL PLUGIN BOUNDARY

Si Level 3 llega a existir, usar plugins/adapters estrictamente separados.

Conceptualmente:

```python
class NativeDacControlPort(Protocol):
    def probe_support(self, device) -> SupportEvidence: ...
    def read_capabilities(self, device) -> NativeControlCapabilities: ...
    def read_state(self, device) -> NativeControlState: ...
    def apply(self, command) -> NativeControlResult: ...
```

Reglas:

```text
no plugin => normal playback still works
plugin crash => normal playback still works
unknown command state => no write
device mismatch => refuse
stale generation => refuse
```

El plugin nunca posee playback, OutputPlan, volume authority global ni stable identity.

Para hardware volume, debe integrarse con `VolumePolicyService`; no crear una segunda autoridad.

---

# 45. COMPATIBILITY PROFILE

MAHKB puede contener conocimiento de compatibilidad:

```text
known-safe rates
known-problematic rates
kernel-specific issue
firmware-specific note
recommended buffer policy
DSD limitation
clock-selector quirk
```

Pero las categorías deben indicar su naturaleza:

```text
UPSTREAM_KNOWN
MANUFACTURER_DECLARED
MICHI_QUALIFIED
COMMUNITY_REPORT
```

`COMMUNITY_REPORT` nunca debe convertirse automáticamente en configuración productiva.

---

# 46. CONFIGURATION STATE — RECOMMENDED VS CUSTOM

Todo perfil debe poder distinguir:

```text
RECOMMENDED
CUSTOM
```

Si el usuario modifica una recomendación:

```text
CUSTOM
1 setting differs from recommended
```

Debe poder inspeccionar el diff y restaurar:

```text
Restore Recommended Settings
```

La actualización futura de un Native Profile no debe sobrescribir silenciosamente elecciones custom.

---

# 47. HIGH-END QUALITY FILTER

Toda nueva función DAC Phase 2 debe superar:

```text
1. ¿Resuelve un problema real?
2. ¿Puede verificarse?
3. ¿Tiene failure mode seguro?
4. ¿Puede explicarse?
5. ¿Respeta las autoridades existentes?
6. ¿Funciona sin Internet?
7. ¿Puede ocultarse si el dispositivo no la necesita?
8. ¿Añade calidad o solo opciones?
```

Si falla cualquiera de 1–5:

```text
REJECT / RESEARCH
```

Si falla 6–8:

```text
DEFER / REDESIGN
```

---

# 48. REALINEACIÓN DE SCOPE --- AUDIO PROCESSING / DSP ENTRA EN PHASE 2

La ampliación de este plan absorbe **el núcleo audiófilo de Audio Lab** como un
track post-Stable separado del DAC, pero integrado por Signal Path y las mismas
reglas de evidence. Esto NO autoriza implementación antes del gate.

## 48.1 Ahora quedan DENTRO del plan

``` text
preamp / digital headroom
parametric EQ
FIR filtering
convolution / room correction IR
balance / polarity / channel delay
channel mapping / mixer explícito
resampling solicitado por usuario
dither explícito cuando exista reducción cuantizada que lo justifique
crossfeed audiófilo como módulo opcional y verificable
loudness compensation como módulo opcional
multichannel crossover como extensión high-end
clip / headroom observability
```

## 48.2 Siguen FUERA del core Phase 2

``` text
crossfade
pitch/time creative effects
reverb creativo
voice effects
video DSP
DRM audio pipelines
arbitrary untrusted plugin execution by default
cloud DSP mandatory
```

Un host LV2 general puede investigarse como extensión opcional después de sellar
el graph DSP canónico. No forma parte del core hasta que exista sandbox/isolation,
state versioning, licensing policy y real-time safety demostrada.

## 48.3 Regla de producto

DSP solicitado por el usuario es una transformación legítima, no un error. Por
tanto:

``` text
DSP ACTIVE -> path_verdict = PROCESSED
DSP ACTIVE -> bit-perfect proof = NOT_APPLICABLE
DSP BYPASSED + exact preserved chain -> M11.5 may verify
```

Nunca ocultar procesamiento para conservar un badge audiófilo.

---

# 49. PAQUETES ADICIONALES

Añadir al roadmap, después de los paquetes P2 originales:

```text
P2-160  Device Setup Architecture
P2-170  Safe Capability Overrides
P2-180  DAC Qualification / Device Health
P2-190  Adaptive Buffer Policy
P2-200  Compatibility Profiles
P2-210  Automatic DAC Setup
P2-220  Recommended vs Custom Configuration
P2-230  Explainability / Why?
P2-240  Interactive Signal Path
P2-250  Diagnostics & Support Bundle
P2-260  High-End UX Convergence

P2-270  Native Device Knowledge
P2-280  Native Profile Resolver
P2-290  Kernel/ALSA Knowledge Ingestion
P2-300  Native Profile Qualification
P2-310  Native Control Plugin Boundary
P2-320  First Native Control Device Pilot
P2-330  Native Integration Adversarial Seal
```

## Dependencias

```text
P2-270
  ↓
P2-280
  ↓
P2-290
  ↓
P2-300
  ↓
P2-310
  ↓
P2-320
  ↓
P2-330
```

`P2-310+` no bloquean el cierre general de Phase 2. Native Control es una extensión opcional por dispositivo.

---

# 50. TEST MATRIX PARA NATIVE PROFILES

Fixtures obligatorios:

```text
generic UAC2 DAC
known DAC with exact commercial descriptors
generic XMOS descriptor
shared/OEM VID/PID
missing manufacturer
missing product
missing serial
two identical DACs with serials
two identical DACs without serials
multi-endpoint USB audio interface
capture + playback interface
capture-only USB device
kernel quirk known device
profile contradicts runtime evidence
profile database unavailable
profile schema newer than supported
stale qualification
custom user policy vs new recommended profile
```

Native Control adicional:

```text
supported device
unsupported device
wrong VID/PID
same model different revision
disconnect during command
stale generation
read failure
write failure
partial write
plugin exception
```

---

# 51. UI TAXONOMY DE INTEGRACIÓN

Evitar términos que sugieran que un dispositivo class-compliant es malo.

Propuesta:

```text
USB DAC
Class Compliant

USB DAC
Michi Known Device

USB DAC
Michi Native Profile

USB DAC
Michi Native Control
```

La etiqueta `Verified` queda reservada a evidencia/Signal Truth, no al nivel de integración.

Nunca mostrar:

```text
Native Profile = Bit Perfect
Native Control = Better Sound
Known Device = Verified
```

Son conceptos independientes.

---

# 52. PRINCIPIO FINAL DE NATIVIDAD

“Nativo” en Michi no significa poseer un driver privado.

La jerarquía correcta es:

```text
Linux knows how to drive the device
        ↓
Michi knows what the device is
        ↓
Michi knows what Linux says about it
        ↓
Michi knows what has been physically qualified
        ↓
Michi selects a safe device-specific policy
        ↓
Michi observes what actually happened
        ↓
Michi explains and verifies the result
```

Solo cuando exista un protocolo específico seguro y documentado:

```text
Michi may additionally control device-specific features
```

La prioridad permanece:

```text
native playback correctness
>
native knowledge
>
native configuration
>
native proprietary control
```

---

---

# 53. CONVERGENCIA NOWPLAYINGBAR --- INTEGRACIÓN DEL PLAN DE PRESENTACIÓN


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Esta sección consolida el rediseño de `NowPlayingBar` con DAC Phase 2 sin crear
un segundo roadmap ni una segunda autoridad de audio.

La regla de integración es:

```text
DAC V3.5 / M11.4 / M11.5
        │
        │ autoridades de ejecución y verdad
        ▼
DAC Phase 2
        │
        ├── identity / classification / capability evidence
        ├── SignalPathGraph
        ├── SignalProof
        └── Device Setup read models
        │
        ▼
NowPlayingBar
        │
        ├── Source Quality
        ├── Signal Path Quick Surface
        ├── DAC Quick Surface
        ├── Future Network Endpoint Surface
        └── Queue / Audio Lab entry points
```

`NowPlayingBar` es **presentación y acceso contextual**. Nunca se convierte en
autoridad de playback, output, Signal Truth, DAC identity, capabilities, volumen,
engine o network transport.

## 53.1 Regla temporal

La consolidación de diseño se autoriza como documentación. La integración
productiva que dependa de Phase 2 conserva el gate original:

```text
PHASE_2_UI_IMPLEMENTATION_ALLOWED = FALSE
```

hasta que se cumplan los requisitos de la sección 26.

No usar el rediseño de `NowPlayingBar` como pretexto para reabrir V3.5, M11.4 o
M11.5 antes de sus cierres.

El único elemento conceptualmente independiente de Phase 2 es la clasificación
factual de la **fuente** para el badge HD/DSD. Aun así, su implementación debe
programarse de forma que no interfiera con el corrective DAC activo ni altere
Signal Truth.

## 53.2 Geometría a preservar

La convergencia debe conservar la macrogeometría actual de la barra:

```text
NowPlayingBar
height = 154
three-zone composition
outputZone = GridLayout de 4 columnas
```

La reorganización objetivo, fijada por la referencia visual del product owner, es:

```text
ROW 0
[ Volume ....................... ] [ Audio / DSP ] [ #3 Michi Stream / Network Output ]

ROW 1
[ #4 Signal Truth / Signal Path ] [ Quality + #1 HD/DSD ] [ #2 DAC Quick ] [ Queue ]
```

La numeración `#1..#4` corresponde exactamente a la maqueta visual aprobada y
**no** al orden de implementación. La referencia visual completa y el contrato
de slots se congelan en §§306–313.

La barra conserva `implicitHeight = 154`, el `outputZone` de cuatro columnas y
los tamaños actuales de los botones. No se agrega una tercera fila, no se crea
un contenedor exterior nuevo y el borde blanco externo visible en la captura de
referencia **NO forma parte de la UI**.

Mientras Network Output no exista productivamente, su celda debe permanecer
oculta, deshabilitada de forma explícita o conservar temporalmente una función
válida. Nunca debe existir un botón visualmente activo sin backend real.

---

# 54. TAXONOMÍA SEMÁNTICA DE LA NOWPLAYINGBAR


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Cada superficie responde una sola pregunta.

| Superficie | Pregunta | Autoridad | No debe afirmar |
| --- | --- | --- | --- |
| `Quality` | ¿Qué archivo fuente estoy reproduciendo? | Library/source facts | bit-perfect, DAC capability, calidad audible |
| `Signal Path` | ¿Qué ocurrió realmente con la señal? | SignalTruth + SignalPathGraph | hechos sin evidence |
| `DAC` | ¿Qué dispositivo local está seleccionado/activo y cómo está configurado? | AudioDeviceRegistry + OutputProfile + Device Setup read model | network endpoint |
| `Network Output` | ¿A qué endpoint/zone de red se envía la reproducción? | futuro Network Output subsystem | identidad DAC local |
| `Audio / DSP` | ¿Qué procesamiento pidió el usuario? | futuro Audio Lab / DSP authority | inferir que el procesamiento está activo sin runtime evidence |
| `Queue` | ¿Qué viene después? | Queue / PlaybackSession authorities | decidir Signal Truth |

Reglas innegociables:

```text
HD != Signal Truth
DAC != Playback Endpoint
Audio Engine != Signal Path
DoP != PCM conversion
Direct != Bit Perfect
UNKNOWN != FAILED
```

---

# 55. SOURCE QUALITY BADGE --- HD / DSD SIN CONFUNDIR FUENTE Y RUNTIME

El Quality Badge representa **hechos de la fuente**. No depende de que la ruta
actual sea Direct, Shared, bit-perfect, procesada o resampled.

## 55.1 Modelo propuesto

No parsear strings QML para decidir el estado. Proyectar semántica estructurada:

```python
from enum import Enum

class SourceResolutionClass(Enum):
    UNKNOWN = "unknown"
    LOSSY = "lossy"
    LOSSLESS_STANDARD = "lossless_standard"
    HIGH_RES_PCM = "high_res_pcm"
    DSD = "dsd"
```

La clasificación factual reutiliza los datos ya disponibles:

```text
codec
container
sample_rate_hz
bit_depth
bitrate_bps
channels
normalized DSD rate
```

Criterio factual inicial compatible con el modelo existente de biblioteca:

```text
DSD
OR bit_depth >= 24
OR sample_rate_hz >= 96_000
```

Esto define una categoría de presentación. **No** implica mejor master,
superioridad audible ni fidelidad end-to-end.

## 55.2 UI objetivo

```text
MP3 · 320 kbps                 -> sin HD
FLAC · 16-bit · 44.1 kHz       -> sin HD
FLAC · 24-bit · 96 kHz         -> HD
FLAC · 24-bit · 192 kHz        -> HD
DSF · DSD64                    -> DSD
```

Un archivo puede ser `HD` y al mismo tiempo tener Signal Path `RESAMPLED`.

Ejemplo válido:

```text
SOURCE QUALITY
FLAC · 24-bit · 192 kHz [HD]

SIGNAL PATH
192 kHz -> 96 kHz
RESAMPLED
```

## 55.3 DoD

- clasificación fuera de QML;
- ninguna inferencia desde texto del label;
- test explícito para MP3 320 sin HD;
- DSD separado de PCM hi-res;
- `UNKNOWN` cuando faltan hechos;
- cero dependencia de DAC/Signal Truth;
- accesibilidad del indicador incluida.

---

# 56. DAC QUICK SURFACE --- DEVICE SETUP COMPACTO


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

El botón DAC de `NowPlayingBar` no crea una segunda configuración de audio. Es
la versión compacta del mismo Device Setup de Phase 2.

## 56.1 Arquitectura

```text
AudioDeviceRegistry
        +
AudioOutputProfile
        +
OutputSessionService
        +
Qualification / Capability Resolver
        +
ResolvedDacIdentity
        +
Signal Truth current read model
        │
        ▼
DeviceSetupReadModel
        │
        ├── NowPlaying DAC Quick Surface
        └── Settings > Full Device Setup
```

El read model es uno. Las dos superficies difieren sólo en profundidad de
presentación.

## 56.2 Nivel compacto objetivo

```text
TOPPING D90SE
USB DAC · Connected
● Active

Path             Direct
Volume           Fixed / Unity
Source           96 kHz
Device           96 kHz
Signal           Direct path

Profile          [ D90SE — Direct ▾ ]

[ Device Setup ]
```

Sólo se muestran valores respaldados por las autoridades actuales.

No mostrar como hecho:

```text
PCM 768 kHz
DSD512
Native DSD supported
DoP supported
hardware volume supported
```

si esa capacidad no tiene provenance compatible con la jerarquía
`DECLARED / OBSERVED / QUALIFIED / RUNTIME`.

## 56.3 Relación con la UI actual

Cuando Phase 2 se active, se debe evaluar primero **refactor/reuse** de las
superficies existentes antes de crear nuevos paralelos:

```text
AudioOutputPopup.qml
DacDeviceCard.qml
DacDiagnosticsDisclosure.qml
SignalTruthPanel.qml
AudioOutputBridge
```

Objetivo:

```text
NO duplicate bridge
NO duplicate selection authority
NO duplicate device state
NO duplicate volume state
```

`DacQuickPopup.qml` es un nombre orientativo, no una obligación. Si
`AudioOutputPopup.qml` puede evolucionar limpiamente a esa función sin romper
contratos, se prefiere refactor sobre duplicación.

## 56.4 DoD

- live-bound al read model;
- selección por `stable_device_id`, nunca por `hw:N,M`;
- selected != active visible;
- hotplug/reconnect generation-safe;
- failure copy tipada;
- no selector de engine dentro del popup;
- acceso a Device Setup completo;
- keyboard/focus/reduced-motion equivalentes al estándar actual.

---

# 57. SIGNAL PATH QUICK SURFACE + DETAILED SURFACE


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

La consolidación adopta esta relación como contrato:

```text
SignalTruth
    = verificador / verdict / contradiction / missing evidence

SignalPathGraph
    = explicación estructurada de la cadena

SignalPathReadModel
    = proyección de presentation

SignalPathQuickSurface
    = resumen contextual en NowPlayingBar

SignalPathDetailedSurface
    = explicación completa e interactiva
```

## 57.1 No crear dos Signal Paths

Compact y Detailed consumen el mismo `SignalPathReadModel`.

```text
SignalTruth + SignalPathGraph
            │
            ▼
     SignalPathReadModel
        ┌───────┴────────┐
        ▼                ▼
Compact popup       Detailed view
NowPlayingBar       full inspection
```

No se permite que el popup compacte su propia cadena leyendo labels sueltos.

## 57.2 Quick Surface objetivo

```text
● VERIFIED / DIRECT / UNVERIFIED / PROCESSED

FLAC 96/24
   ↓
PCM 96/24sig
   ↓
GStreamer
   ↓
ALSA Direct
   ↓
TOPPING D90SE
96/24sig

[ Detailed Signal Path ]
```

## 57.3 Detailed Surface objetivo

```text
SOURCE
FLAC · 96 kHz · 24 bit · Stereo
Evidence: file facts
        ↓
DECODE
PCM · 96 kHz · 24 significant bits
Evidence: selected decoder runtime caps
        ↓
AUDIO ENGINE
GStreamer
        ↓
PROCESSING
Resampling: absent / present / unknown
Remix: absent / present / unknown
DSP: absent / present / unknown
        ↓
VOLUME
Fixed / Unity
        ↓
TRANSPORT
Direct ALSA
        ↓
ALSA NEGOTIATION
S32_LE · 96 kHz
24 significant bits · 2 ch
        ↓
USB AUDIO
UAC2
        ↓
DAC
Commercial identity / canonical identity
```

Cada nodo puede desplegar:

```text
WHAT
WHY
EVIDENCE
CONFIDENCE
GENERATION
CONTRADICTIONS
MISSING EVIDENCE
```

## 57.4 Direct V1 vs universal final

El repositorio actual posee evidencia productiva más profunda en la ruta
Direct/GStreamer/ALSA. Por eso la implementación debe distinguir:

```text
Signal Path V1
Direct -> chain completa cuando exista evidence
Shared -> UNKNOWN / Not observed donde corresponda

Signal Path Final
Direct + Shared + Qt + GStreamer + MPD
+ future DSP
+ Native DSD / DoP
+ future Network Endpoint
```

Nunca completar visualmente una cadena con nodos sintéticos para que "se vea
bonita".

## 57.5 DoP

Representación obligatoria:

```text
SOURCE        DSD64
ENGINE        DSD64
TRANSPORT     DoP
CARRIER       PCM 176.4 kHz framing
DAC MODE      DSD64
```

El carrier PCM no convierte por sí solo DoP en `DSD_TO_PCM`.

---

# 58. MIGRACIÓN DEL SELECTOR DE AUDIO ENGINE


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

El selector rápido de motores de `NowPlayingBar` debe retirarse **sólo cuando**
el nuevo Signal Path Quick Surface esté listo y la selección completa permanezca
operativa en Settings.

## 58.1 Estado final

```text
NOW PLAYING
    Signal Path
        └── AUDIO ENGINE = GStreamer / MPD / Qt

SETTINGS
    Audio Engine
        └── selección/configuración del motor
```

El engine pasa de ser una acción primaria de reproducción a ser también una
etapa observable de la cadena.

## 58.2 Migración contractual

El cambio debe reabrir de forma controlada únicamente los contratos UI que hoy
exigen el quick selector y cerrar esa reapertura en el mismo work package.

Archivos/tests conocidos que deben reconciliarse al activar el trabajo:

```text
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioEnginePopup.qml
src/michi/presentation/qml/views/AudioEngineSettingsSection.qml
src/michi/presentation/qml/shell/AppShell.qml

tests/test_m11_3_ui_audio_engine.py
tests/test_m9_qml.py
tests/test_m9_design_canon.py
tests/test_production_container_golden.py
tests/test_m9_now_playing_golden.py
```

Regla:

```text
NO delete-first migration
```

Primero se prueba que Settings conserva la selección real; después se sustituye
el quick selector por Signal Path y finalmente se retiran wiring/tests obsoletos.

---

# 59. MICHI MUSIC STREAM --- FRONTERA FUERA DE DAC PHASE 2

Michi Music Stream **no** debe absorberse dentro de `AudioDeviceRegistry` ni de
DAC Phase 2.

Un DAC local y un endpoint remoto responden preguntas distintas:

```text
DAC
¿Qué hardware local convierte/recibe la señal?

NETWORK ENDPOINT / ZONE
¿Dónde se envía o reproduce la sesión remota?
```

## 59.1 Subsistema futuro

Nombres orientativos:

```text
PlaybackEndpoint
PlaybackZone
NetworkOutputRegistry
MichiStreamDiscoveryPort
MichiStreamTransportPort
NetworkOutputSessionService
NetworkOutputBridge
```

La implementación puede usar posteriormente Snapcast u otro transporte según el
contrato del ecosistema, pero DAC Phase 2 no toma esa decisión.

## 59.2 Integración futura con SignalPathGraph

Cuando el subsistema exista:

```text
SOURCE
  ↓
ENGINE
  ↓
PROCESSING
  ↓
NETWORK TRANSPORT
Michi Stream
  ↓
ENDPOINT
Living Room
  ↓
REMOTE DAC
PCM5122
```

SignalPathGraph debe **representar** network output, no poseerlo.

## 59.3 Política UI antes de existir el backend

El slot número 3 de NowPlayingBar no debe presentar una acción ficticia.

Opciones válidas:

```text
HIDDEN
or
DISABLED + explicit future/unavailable semantic
or
TEMPORARILY RETAIN CURRENT VALID OUTPUT ACTION
```

No válido:

```text
click -> placeholder with no functional authority
```

---

# 60. READ MODELS Y WIRING UNIFICADO

La consolidación define dos read models principales de presentation:

```text
DeviceSetupReadModel
SignalPathReadModel
```

No son autoridades. Son proyecciones derivadas de autoridades ya existentes.

## 60.1 DeviceSetupReadModel

Debe poder contener, cuando exista evidence:

```text
canonical identity
commercial identity enrichment
selected / active
availability
transport mode
volume authority
current source rate
current device rate
profile
qualified capabilities
runtime capabilities
reconnect state
typed failure
verification summary
```

## 60.2 SignalPathReadModel

Debe contener:

```text
verdict
proof state
nodes[]
transforms[]
reason codes
contradictions[]
missing evidence[]
generation
active identity
```

Cada `node` conserva su evidence y confidence.

## 60.3 Flujo QML

```text
AppShell
  │
  ├── NowPlayingBar
  │      ├── quality projection
  │      ├── SignalPathQuickSurface
  │      ├── DacQuickSurface
  │      └── future NetworkOutputSurface
  │
  └── Settings
         ├── AudioEngineSettingsSection
         └── DeviceSetupDetailedSurface
```

QML emite intents. Los bridges/coordinators ejecutan las acciones.

---

# 61. MATRIZ DE REUTILIZACIÓN Y TRABAJO RESTANTE

Los porcentajes de esta sección son exactos **dentro de un modelo de scoring
cerrado de 100 puntos por capacidad**, no estimaciones de LOC futuros.

Pesos:

```text
Domain / data             20
Application / runtime     20
Bridge / projection       15
QML / UX                  20
Production wiring         10
Tests / contracts         15
TOTAL                    100
```

## 61.1 Estado de reutilización

| Capacidad | Domain 20 | App 20 | Bridge 15 | QML 20 | Wiring 10 | Tests 15 | Reutilizable | Falta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Source Quality HD/DSD | 20 | 12 | 8 | 14 | 10 | 7 | **71 %** | **29 %** |
| DAC Quick Surface | 20 | 18 | 15 | 13 | 10 | 14 | **90 %** | **10 %** |
| Michi Stream / Network Output | 2 | 0 | 0 | 5 | 2 | 0 | **9 %** | **91 %** |
| Signal Path universal | 20 | 10 | 15 | 8 | 4 | 9 | **66 %** | **34 %** |
| Engine selector -> Settings | 20 | 20 | 15 | 12 | 5 | 4 | **76 %** | **24 %** |

Para una V1 de Signal Path limitada honestamente a la evidencia Direct ya
existente:

```text
Signal Path Direct V1 = 78 % reutilizable / 22 % pendiente
```

## 61.2 NowPlayingBar sin Network Output funcional

Ponderación de carga de implementación:

```text
HD                 13.3 %
DAC                 30.0 %
Signal Path         40.0 %
Engine migration    16.7 %
```

Resultado:

```text
REUTILIZABLE = 75.5 %
PENDIENTE    = 24.5 %
```

## 61.3 Visión completa con Michi Stream real

Ponderación:

```text
HD                  8 %
DAC                 18 %
Signal Path         24 %
Engine migration    10 %
Michi Stream        40 %
```

Resultado:

```text
REUTILIZABLE = 48.9 %
PENDIENTE    = 51.1 %
```

La caída no refleja un NowPlayingBar inmaduro: refleja que Network Output es un
subsistema completo, no un botón.

---

# 62. WORK PACKAGES CONSOLIDADOS DE PRESENTACIÓN

Estos identificadores son **propuestos** y deben reconciliarse con el roadmap
vigente al activar Phase 2.

## P2-130 --- Premium Device Setup

Se mantiene el paquete existente.

## P2-135 --- NowPlaying DAC Quick Surface

Dependencias:

```text
P2-010 classification
P2-040 identity resolver
P2-050 capability resolver
P2-130 Device Setup read model
```

DoD:

- una sola autoridad de device/output;
- popup compacto live-bound;
- selected vs active;
- profile y availability reales;
- no capability claim sin evidence;
- navegación al Device Setup completo.

## P2-140 --- Signal Path UI

Se mantiene el paquete existente como detailed surface.

## P2-145 --- NowPlaying Signal Path Quick Surface

Dependencias:

```text
P2-070 SignalPathGraph
P2-080 GStreamer evidence
P2-090 ALSA/transport evidence
P2-100 M11.5 proof projection
P2-140 detailed read model
```

DoD:

- consume el mismo read model que Detailed;
- no cadena paralela;
- UNKNOWN explícito;
- navegación a Detailed;
- focus/accessibility/reduced motion.

## P2-146 --- Audio Engine UI Migration

Objetivo:

```text
remove quick engine selection from NowPlayingBar
retain complete selection in Settings
replace slot with Signal Path
```

DoD:

- selección de engine plenamente operativa en Settings;
- old quick wiring retirado;
- tests contractuales actualizados;
- zero duplicate engine selectors en NowPlayingBar;
- Signal Path expone el engine activo como evidence, no como botón selector.

## P2-147 --- NowPlaying Quality Semantic Seal

Puede ejecutarse como paquete independiente de Phase 2 si su scheduling se
autoriza fuera de este plan; dentro de Phase 2 actúa como convergence gate.

DoD:

- `SourceResolutionClass`;
- HD/DSD factual;
- no false-HD en MP3;
- source truth separada de runtime truth.

## P2-245 --- NowPlaying Signal Path Final Convergence

Después de `P2-240 Interactive Signal Path`:

- compact/detailed parity;
- Explainability `WHY?` compartida;
- Evidence Disclosure compartido;
- DSD/DoP presentation cuando esté físicamente validada;
- Shared/Direct semantics honestas;
- future DSP nodes representables;
- no regressions del golden layout.

---

# 63. ARCHIVOS A RECONCILIAR AL ACTIVAR LA CONVERGENCIA

No crear ni borrar archivos antes del gate. Al activar el trabajo, auditar el
HEAD exacto y decidir `reuse / rename / split / retire`.

## 63.1 Reutilización probable

```text
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioOutputPopup.qml
src/michi/presentation/qml/player/AudioEnginePopup.qml
src/michi/presentation/qml/components/SignalTruthPanel.qml
src/michi/presentation/qml/components/DacDeviceCard.qml
src/michi/presentation/qml/components/DacDiagnosticsDisclosure.qml
src/michi/presentation/qml/views/AudioEngineSettingsSection.qml
src/michi/presentation/qml/shell/AppShell.qml

src/michi/presentation/audio_output_bridge.py
src/michi/presentation/playback_bridge.py
src/michi/domain/signal_truth.py
src/michi/domain/audio_device.py
src/michi/domain/audio_output.py
src/michi/application/audio_quality.py
```

## 63.2 Nuevos nombres orientativos sólo si el refactor los justifica

```text
src/michi/presentation/signal_path_bridge.py
src/michi/presentation/audio_hardware_bridge.py

src/michi/presentation/qml/player/DacQuickPopup.qml
src/michi/presentation/qml/player/SignalPathQuickPopup.qml
src/michi/presentation/qml/components/SignalPathPanel.qml
src/michi/presentation/qml/components/SignalPathNode.qml
src/michi/presentation/qml/components/EvidenceDisclosure.qml
```

Regla de preferencia:

```text
REUSE > REFACTOR > RENAME > NEW PARALLEL COMPONENT
```

siempre que reuse no fuerce mezcla de responsabilidades.

---

# 64. TESTING Y CONTRATOS DE NO-REGRESIÓN PARA NOWPLAYINGBAR

Además de los tests Phase 2 existentes, la convergencia debe añadir gates
específicos.

## 64.1 Quality

```text
MP3 320 -> no HD
FLAC 16/44.1 -> no HD
FLAC 24/96 -> HD
FLAC 24/192 -> HD
DSD64 -> DSD
missing metadata -> UNKNOWN / no false badge
```

## 64.2 DAC Quick Surface

```text
selected != active
active direct
selected disconnected
reconnect new generation
same-model collision labels
profile preserved
failure copy typed
keyboard navigation
focus restore
no raw ALSA id in normal surface
```

## 64.3 Signal Path

```text
Direct complete evidence
missing decoded evidence -> UNVERIFIED
missing ALSA evidence -> UNVERIFIED
resampler present pass-through -> not falsely RESAMPLED
actual rate change -> RESAMPLED
software gain != unity -> PROCESSED
XRUN -> CONTRADICTED/BROKEN according to canonical contract
stale generation ignored
DoP carrier not PCM conversion
```

## 64.4 Engine migration

```text
Settings can switch Qt -> GStreamer -> MPD per current contracts
NowPlayingBar has no engine quick selector
Signal Path shows active engine stage
AppShell has no orphan switch wiring from removed popup
production container tree instantiates new Signal Path surface
```

## 64.5 Geometry / visual regression

Preservar:

```text
1920 x 154 canonical reference class
responsive three-zone layout
trackCard
playbackZone
outputZone
timeline
play/pause
queue
quality badge
volume
```

El golden visual sólo se actualiza cuando el nuevo layout haya superado los
gates funcionales y de accesibilidad. No usar un nuevo golden para ocultar una
regresión.

## 64.6 Network Output

Mientras Michi Stream no exista:

```text
no fake discoverability
no fake connected state
no fake zones
no fake latency values
no disabled control presented as active
```

---

# 65. ROADMAP FINAL CONSOLIDADO --- DAG MULTI-TRACK

La implementación deja de modelarse como una única cadena lineal. Después del
freeze se abren tracks independientes que convergen sólo cuando sus contratos
están sellados.

``` text
DAC V3.5 / M11.4
        ↓
DAC-V35-110 Physical Qualification
        ↓
M11.5 Audiophile Playback Guarantees
        ↓
zero DAC P0/P1 + full suite green
        ↓
BASELINE FREEZE
        │
        ├──────────────────────────────────────────────────────────────┐
        │                                                              │
        ▼                                                              ▼
TRACK A — HARDWARE / KNOWLEDGE                                TRACK B — SIGNAL TRUTH
P2-010 Device Classification                                  P2-070 SignalPathGraph
P2-020 Evidence Primitive                                     P2-080 GStreamer evidence
P2-030 MAHKB                                                  P2-090 ALSA/transport
P2-040 Identity Resolver                                      P2-100 M11.5 proof projection
P2-050 Capability Resolver                                    P2-110 PCM physical matrix
P2-060 Fingerprinting                                                 │
        │                                                              │
        └───────────────────────┬──────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────────────┐
        ▼                       ▼                               ▼
TRACK C — DSP              TRACK D — DSD/DoP              TRACK E — PRESENTATION
DSP-000 contracts          DSD-000 signal model            P2-130 Device Setup
DSP-010 profiles           DSD-010 source truth            P2-135 DAC Quick
DSP-020 graph              DSD-020 ALSA qualification      P2-140 Detailed Signal Path
DSP-030 GStreamer          DSD-030 Native DSD              P2-145 Quick Signal Path
DSP-040 PEQ/headroom       DSD-040 DoP technology gate     P2-146 Engine UI migration
DSP-050 FIR/convolution    DSD-050 DoP executor            P2-147 Quality semantic seal
DSP-060 resampler          DSD-060 DSD→PCM                 DSP-UI Audio Processing Quick
DSP-070 evidence           DSD-070 transitions                    │
DSP-080 Camilla research   DSD-080 Signal Truth                  │
DSP-090 optional adapters  DSD-090 physical matrix               │
        │                       │                               │
        └───────────────────────┴───────────────────────────────┘
                                │
                                ▼
                     CORE AUDIO PHASE 2 CONVERGENCE
                                │
                                ├── P2-150 Core adversarial seal
                                ├── P2-160..230 High-End Experience
                                ├── P2-240 Interactive Signal Path
                                ├── P2-245 NowPlaying final convergence
                                ├── P2-250 Diagnostics bundle
                                ├── P2-260 High-End UX convergence
                                │
                                ▼
                     P2-270..300 Native Knowledge
                                │
                         OPTIONAL P2-310..330
                           Native Control
                                │
                                ▼
                       FINAL AUDIO PHASE 2 SEAL
```

Michi Music Stream permanece en un **roadmap separado de Network Output**. El
SignalPathGraph debe poder representarlo cuando exista, pero ninguna dependencia
de Network Output bloquea PCM/DSP/DSD/DoP local.

---

# 66. DECISIÓN FINAL DEL PLAN CONSOLIDADO

La experiencia final debe mantener seis preguntas claramente separadas:

```text
QUALITY
¿Qué archivo es?

SIGNAL PATH
¿Qué ocurrió realmente con la señal?

DAC
¿Qué hardware local está seleccionado/activo?

NETWORK OUTPUT
¿A qué endpoint remoto se envía la reproducción?

AUDIO / DSP
¿Qué procesamiento solicitó el usuario, qué graph fue compilado y cuál está realmente activo?

QUEUE
¿Qué se reproducirá después?
```

La arquitectura correcta es:

```text
SOURCE FACTS
    │
    ├──> Quality Badge
    │
    ▼
DECODE / ENGINE / PROCESSING / VOLUME / TRANSPORT / DEVICE
    │             │
    │             └──> AudioProcessingRuntimeEvidence
    ▼
SignalTruth / M11.5 proof authority
    │
    ▼
SignalPathGraph
    │
    ├──> NowPlaying Compact Signal Path
    └──> Detailed Interactive Signal Path

AudioDeviceRegistry + OutputProfile + Device Evidence
    │
    ▼
DeviceSetupReadModel
    │
    ├──> NowPlaying DAC Quick Surface
    └──> Settings Device Setup

Future Network Output authority
    │
    ├──> NowPlaying Network Output Surface
    └──> SignalPathGraph adapter
```

El objetivo no es que `NowPlayingBar` acumule botones. El objetivo es que cada
control o indicador tenga **una semántica inequívoca, una autoridad única,
evidencia verificable y una ruta de progressive disclosure**.

La barra se convierte así en el punto compacto de observabilidad del sistema de
audio, mientras Settings conserva la configuración y las superficies Detailed
conservan la explicación técnica completa.

---

# 67. AUDITORÍA DEL REPOSITORIO — RECONCILIACIÓN V7 (2026-09-26)

**HEAD auditado:** `main @ bc53642039d1e2597abba476215a198949887c2d`  
**Commit:** `feat(dac): close M11.4 PCM with tuple-scoped truth and a field-closure lab`  
**Delta desde V5 observado (`0d6907e...`):** 71 commits / 141 archivos cambiados.

## 67.1 Roadmap relevante

```text
M11.3 = DONE / TESTED / FROZEN
M11.4 = PCM implemented + PHYSICAL QUALIFICATION PASS (BOUNDED, device-scoped)
M11.5 = AUDITED / READY / NOT IMPLEMENTED
DAC-V35-140 = separate DSD/DoP promotion / NOT STARTED
```

## 67.2 Delta PCM/DAC ya aterrizado

```text
src/michi/application/audio_device_semantics.py
src/michi/application/carrier_resolution.py
src/michi/application/dac_pcm_closure.py
scripts/dac_m11_4_pcm_lab.py
tests/dac/test_v35_final_pcm_closure.py
```

Main ya tiene playback admission universal, retained identity on disconnect,
device grouping, tuple-scoped qualification, Strict/Compatible Direct,
CandidateCarrierResolver, `DIRECT_CONTAINER_ADAPTED`, converter preservation
readback y final PCM closure evidence model.

## 67.3 Physical truth actual

DAC-V35-110 conserva bounded PASS para SMSL. Ledger:

```text
PASS              R19 R21 R22 R28 R33 R34
NOT_APPLICABLE    R20 R23 R26 R30 R31
NOT_RUN           R24 R25 R27 R29 R32 R35 R36
```

El nuevo closure model exige R24/R25/R32/R35/R36 para un manifest completo.

## 67.4 Devices descubiertos por el nuevo lab

```text
SMSL USB AUDIO   usb:152a:85dd:3-3.3.2   hw:CARD=AUDIO,DEV=0
KINMAX HA01      usb:2fc6:f882:HA01       hw:CARD=HA01,DEV=0
```

Host registrado:

```text
kernel       7.2.6-1-cachyos
ALSA         1.2.16.1
GStreamer    1.28.7
snd-usb-audio
```

En ambos nuevos manifests R24/R25/R32/R35/R36 = `NOT_RUN`. Discovery no equivale
a qualification; KINMAX todavía no es `PASS_MULTI_HARDWARE` evidence.

## 67.5 Presentation/output actual

`AudioOutputBridge` proyecta device groups, selected/active/profile/path,
direct compatibility, tuple-scoped capabilities, volume authority, Signal Truth,
rates/formats, recovery actions y availability. `AudioOutputPopup` es grouped y
scroll-bounded. `DacDiagnosticsDisclosure` lista tuples realmente cualificadas.

## 67.6 NowPlayingBar actual

```text
ROW 0 [volume span2] [settings/equalizer] [outputDeviceButton]
ROW 1 [audioEngineButton] [qualityBadge] [queueButton] [empty]
```

El target §§306–313 todavía es futuro. `AppShell.qml` mantiene engine quick
selection y local Audio Output wiring.

## 67.7 Signal Truth actual

```text
DIRECT
DIRECT_CONTAINER_ADAPTED
DSP
RESAMPLED
REMIXED
UNKNOWN
CONTRADICTED
```

La adaptación requiere mecanismo observado + preservation readback.

## 67.8 Gaps reales

```text
M11.5 proof/gapless       missing
Native DSD runtime        missing
DoP runtime               missing
DSD→PCM product path      missing
DSP runtime               missing
SignalPathGraph           missing
MAHKB/commercial resolver missing
NowPlaying V6             missing
Michi Stream              missing
```

## 67.9 Regla de scope

No recrear registry, PCM qualification, carrier resolver, output planner, Signal
Truth ni PCM closure evidence. Phase 2 comienza por encima de esas autoridades.

---

# 68. INVESTIGACIÓN EXTERNA --- DECISIONES TÉCNICAS INCORPORADAS

Esta sección distingue explícitamente investigación externa de la evidencia del
repositorio.

## 68.1 GStreamer — base principal recomendada

GStreamer 1.24 introdujo representación first-class de DSD en `GstAudio`
(`GstDsdInfo` / `GstDsdFormat`) y soporte `audio/x-dsd` en `alsasink`.
`dsdconvert` permite cambiar grouping/layout/bit order sin alterar rate ni
channels. La arquitectura Phase 2 debe requerir **GStreamer >= 1.24 para las
features DSD**, con discovery de capabilities en runtime en vez de elevar el
mínimo global si la función no está instalada.

La propiedad `playbin3.audio-filter` permite instalar un element/bin de filtros,
lo que encaja con un `GStreamerProcessingExecutor` sin crear otro playback
engine.

Plugins oficiales útiles para un core DSP:

``` text
equalizer-nbands   ecualizador gráfico N-band / candidate optimization; NO arbitrary PEQ proof
audiofirfilter     FIR / impulse response
audioresample      sample-rate conversion explícita
audiodynamic       compressor/expander opcional
audioconvert       type/channel conversion explícita
```

**Regla Michi:** que un elemento exista en el graph no prueba que haya
transformado la señal. Se conserva la semántica actual de comparar caps
negociados entrada/salida.

## 68.2 MPD — referencia especialmente valiosa para DoP

MPD documenta tres modos DSD: Native, DoP y DSD→PCM. DoP se habilita
explícitamente porque el software no puede saber genéricamente si el DAC lo
interpreta; su plugin ALSA trata DoP como carrier 24-bit y rechaza una
negociación que rompa la preservación necesaria del carrier.

**Patrón a reutilizar conceptualmente, no copiar código:**

``` text
DSD source
  ↓
explicit DoP policy
  ↓
exact 24-bit-capable carrier negotiation
  ↓
refuse if carrier changes
```

## 68.3 Linux / ALSA

El ABI ALSA incluye formatos DSD (`DSD_U8`, `DSD_U16_LE/BE`,
`DSD_U32_LE/BE`). El código USB Audio del kernel contiene además soporte DoP
específico en ciertos paths/quirks y muestra la alternancia de markers `0x05` /
`0xFA` con dos bytes de payload DSD por frame de 24 bits.

**Regla:** usar kernel/ALSA como evidencia de bajo nivel; no asumir que todos los
DAC o drivers exponen DoP del mismo modo.

## 68.4 CamillaDSP

CamillaDSP v4.1 es un procesador externo maduro con IIR, FIR/convolution,
mixers, multichannel y varios backends. Su arquitectura usa chunks, thread de
capture, processing, playback y supervisor; su websocket puede limitarse a
`127.0.0.1`.

Sus formatos documentados son PCM integer/float. Por tanto, mientras no exista
una capacidad DSD documentada, Michi lo considera **PCM-only**:

``` text
Native DSD -> CamillaDSP = FORBIDDEN
DoP carrier -> CamillaDSP = FORBIDDEN
DSD -> explicit PCM conversion -> CamillaDSP = POSSIBLE
```

CamillaDSP será executor avanzado opcional; no el core inicial.

## 68.5 PipeWire filter-chain

PipeWire puede construir graphs con filtros builtin, LADSPA/LV2, convolver,
parametric EQ, SOFA y FFmpeg. Es excelente para un modo **Desktop/Shared DSP**,
pero no debe convertirse en la autoridad de un claim Direct porque el session
manager y el graph de sistema añaden capas que Michi no controla end-to-end.

## 68.6 LV2

LV2 es un estándar extensible con state persistente y un Worker extension para
trabajo no real-time. Es atractivo para un ecosistema de plugins, pero hospedar
plugins arbitrarios introduce crash isolation, real-time safety, licensing,
state migration y UX de parámetros.

**Decisión:** LV2 es extensión post-core, con allowlist e isolation gate.

## 68.7 libsoxr

libsoxr ofrece resampling de alta calidad con control de phase response,
bandwidth, aliasing y rejection. Debe estudiarse como backend/benchmark
opcional; no introducirlo como resampler oculto.

## 68.8 FFmpeg DSD

FFmpeg actual posee `AV_SAMPLE_FMT_DSD` first-class. Esta evolución refuerza el
principio de que Michi no debe depender de una conversión DSD→PCM opaca dentro de
un decoder cuando intenta construir Native DSD.

---

# 69. ADR NUEVO REQUERIDO --- AUDIO PROCESSING NO ES UN CUARTO AUDIO ENGINE

Antes de implementar DSP debe aceptarse un ADR que congele:

``` text
AudioPort = transport-only, unchanged
AudioEngine = Qt / GStreamer / MPD, unchanged
AudioProcessingService = sole processing-intent authority
AudioProcessingRuntimePort = separate capability interface
GStreamer = first processing-capable engine
CamillaDSP = optional processing sidecar, not AudioEngine
PipeWire filter-chain = optional Shared processing adapter
```

Un backend puede implementar simultáneamente:

``` python
class GStreamerAudioPort(AudioPort, AudioProcessingRuntimePort):
    ...
```

pero las interfaces no se fusionan.

## 69.1 Engine capability

No añadir DSP knobs a `AudioEngineCapabilities` de M11.3 si ese contrato está
frozen. Crear un registro independiente:

``` python
@dataclass(frozen=True, slots=True)
class ProcessingAttachmentCapability:
    engine_id: AudioEngineId
    available: bool
    backend: str
    supports_live_reconfigure: bool
    supports_fir: bool
    supports_peq: bool
    reason: str | None
```

## 69.2 UX cuando el engine no soporta DSP

``` text
DSP profile selected
Active engine = Qt/MPD
        ↓
DO NOT AUTO SWITCH
        ↓
"Audio Processing requires GStreamer"
[Open Audio Engine Settings]
```

---

# 70. SIGNAL FORMAT ALGEBRA --- PCM, DSD Y DOP COMO TIPOS DISTINTOS

No continuar expandiendo `PcmTuple` hasta que contenga campos DSD. Crear un tipo
sum explícito.

``` python
from dataclasses import dataclass
from enum import Enum

class SignalEncoding(Enum):
    PCM = "pcm"
    DSD = "dsd"
    DOP = "dop"

@dataclass(frozen=True, slots=True)
class PcmSignalFormat:
    rate_hz: int
    transport_format: str
    channels: int
    significant_bits: int | None
    channel_positions: tuple[str, ...] | None = None

@dataclass(frozen=True, slots=True)
class DsdSignalFormat:
    bit_rate_hz: int
    multiplier: int | None       # 64/128/256/... when canonical
    grouping: str                # DSD_U8/U16/U32 + endian
    channels: int
    reversed_bytes: bool | None
    channel_positions: tuple[str, ...] | None = None

@dataclass(frozen=True, slots=True)
class DopCarrierFormat:
    source: DsdSignalFormat
    carrier_rate_hz: int
    carrier_format: str          # e.g. S24-in-32 / exact negotiated form
    channels: int
    marker_scheme: str           # DOP_0X05_0XFA
    payload_bytes_per_frame: int = 2

SignalFormat = PcmSignalFormat | DsdSignalFormat | DopCarrierFormat
```

## 70.1 Invariante DoP

``` text
DopCarrierFormat is not PcmSignalFormat
```

Puede negociar un endpoint PCM-compatible, pero Signal Path y proof deben
preservar la semántica `DSD payload over PCM framing`.

## 70.2 Compatibilidad legacy

`PcmTuple` permanece para V3.5 frozen. Phase 2 introduce adapters explícitos:

``` python
def pcm_signal_from_v35(value: PcmTuple) -> PcmSignalFormat: ...
def v35_tuple_from_pcm(value: PcmSignalFormat) -> PcmTuple: ...
```

No mutar el tipo V3.5 si ello reabre el baseline.

---

# 71. AUDIO PROCESSING DOMAIN --- AUTORIDAD ÚNICA

## 71.1 Estado e identidad

``` python
class ProcessingState(Enum):
    BYPASSED = "bypassed"
    PREPARING = "preparing"
    ACTIVE = "active"
    RECONFIGURING = "reconfiguring"
    DEGRADED = "degraded"
    FAILED = "failed"

@dataclass(frozen=True, slots=True)
class ProcessingProfileRef:
    profile_id: str
    revision: int

@dataclass(frozen=True, slots=True)
class AudioProcessingState:
    selected_profile: ProcessingProfileRef | None
    active_profile: ProcessingProfileRef | None
    active_graph_id: str | None
    state: ProcessingState
    last_error_code: str | None
```

`AudioProcessingService` es la única autoridad del estado anterior.

## 71.2 Mutaciones

``` text
select_profile()
set_bypass()
prepare_graph()
commit_graph()
abort_graph()
restore_recommended()
```

QML nunca muta nodes directamente.

---

# 72. PROCESSING GRAPH --- MODELO INMUTABLE

``` python
class ProcessingNodeKind(Enum):
    PREAMP = "preamp"
    PARAMETRIC_EQ = "parametric_eq"
    FIR = "fir"
    CONVOLUTION = "convolution"
    BALANCE = "balance"
    POLARITY = "polarity"
    CHANNEL_DELAY = "channel_delay"
    CHANNEL_MAP = "channel_map"
    RESAMPLE = "resample"
    DITHER = "dither"
    CROSSFEED = "crossfeed"
    LOUDNESS = "loudness"

# R10: MIXER and LIMITER are reserved future capabilities, not valid CORE
# node kinds until they receive typed dataclasses, compiler semantics,
# runtime evidence and falsification gates.

@dataclass(frozen=True, slots=True)
class ProcessingNode:
    node_id: str
    kind: ProcessingNodeKind
    enabled: bool
    parameters: object

@dataclass(frozen=True, slots=True)
class ProcessingGraph:
    graph_id: str
    revision: int
    nodes: tuple[ProcessingNode, ...]
    input_format_policy: object
    output_format_policy: object
```

`parameters` no debe terminar siendo un dict sin schema. Cada node type tendrá
su dataclass tipado.

## 72.1 Orden canónico inicial

``` text
INPUT
  ↓
PREAMP / HEADROOM
  ↓
CHANNEL / POLARITY / DELAY
  ↓
PEQ / CROSSFEED / LOUDNESS
  ↓
FIR / CONVOLUTION
  ↓
RESAMPLER (si solicitado)
  ↓
DITHER (sólo si la reducción final lo requiere y está habilitado)
  ↓
OUTPUT
```

El compiler puede optimizar internamente, pero el Signal Path explica el orden
semántico efectivo.

---

# 73. PROCESSING PLAN --- COMPILAR ANTES DE TOCAR EL RUNTIME

``` python
@dataclass(frozen=True, slots=True)
class ProcessingPlan:
    plan_id: str
    graph_id: str
    graph_revision: int
    engine_id: AudioEngineId
    source_format: SignalFormat
    target_format: SignalFormat
    backend: str
    compiled_nodes: tuple[object, ...]
    total_declared_latency_frames: int | None
    preconditions: tuple[str, ...]
```

Pipeline:

``` text
ProcessingProfile
      ↓ validate
ProcessingGraph
      ↓ compile
ProcessingPlan
      ↓ prepare
backend candidate
      ↓ runtime evidence
commit OR abort
```

Nunca modificar live elements uno por uno desde QML.

---

# 74. GSTREAMER PROCESSING EXECUTOR --- CORE DSP RECOMENDADO

GStreamer será el primer executor productivo porque el engine y su threading ya
existen en Michi y `playbin3` admite `audio-filter`.

## 74.1 Nuevo puerto

``` python
class AudioProcessingRuntimePort(Protocol):
    def prepare_processing(self, plan: ProcessingPlan) -> str: ...
    def commit_processing(self, receipt: str) -> None: ...
    def abort_processing(self, receipt: str, reason: str) -> None: ...
    def bypass_processing(self) -> None: ...
    def snapshot_processing(self) -> ProcessingRuntimeSnapshot: ...
```

## 74.2 GStreamer bin

Propuesta:

``` text
michi_processing_bin
    ghost sink
      ↓
    audioconvert [sólo si plan lo autoriza]
      ↓
    preamp
      ↓
    PEQ
      ↓
    FIR/convolver
      ↓
    resampler [sólo si plan lo autoriza]
      ↓
    capsfilter
      ↓
    ghost src
```

No insertar elementos "por seguridad". Si un node no está en el plan, no
aparece o aparece sólo si se demuestra pass-through requerido por GStreamer.

## 74.3 Transacción

El filter bin debe instalarse con pipeline en estado seguro y publicarse como
active sólo después de:

``` text
build success
link success
caps negotiation success
runtime graph inspection success
processing evidence matches plan
```

---

# 75. PARAMETRIC EQ --- CORE DSP

## 75.1 Modelo

``` python
class EqFilterType(Enum):
    PEAKING = "peaking"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    NOTCH = "notch"

@dataclass(frozen=True, slots=True)
class PeqBand:
    band_id: str
    enabled: bool
    filter_type: EqFilterType
    frequency_hz: float
    gain_db: float
    q: float
```

## 75.2 Backend inicial — CORREGIDO R10

La auditoría de Michi Legacy aporta una distinción importante:

```text
graphic EQ      -> legacy experimented with `equalizer-nbands`
parametric EQ   -> legacy experimented with cascaded `audioiirfilter`
```

Por tanto `equalizer-nbands` **no se toma como prueba de un PEQ arbitrario**
capaz de expresar Peak/Shelf/LP/HP/Notch con la semántica Q de Michi.

F05 debe probar por separado:

```text
graphic strategy candidate   equalizer-nbands
PEQ strategy candidate       audioiirfilter biquad cascade
```

y comparar respuesta teórica vs medida antes de sellar cualquiera.

## 75.3 Importadores

Phase 2 puede aceptar importación de:

``` text
AutoEQ-style text
REW filter text
Michi native JSON/YAML schema
```

Los importadores producen `ProcessingGraph`; no controlan runtime.

---

# 76. HEADROOM, CLIPPING Y GAIN

No calcular "safe preamp" únicamente como `-max_positive_boost`; ese valor no
prueba ausencia de clipping para toda señal.

Implementar:

``` text
user preamp
recommended headroom estimate
runtime peak observability
clip counter
optional true-peak analysis outside audio hot path
```

## 76.1 Limiter — RESERVED / NOT CORE R10

Un limiter nunca se activa automáticamente para ocultar clipping.

R10 corrige una contradicción histórica: el documento hablaba de un limiter
visible, pero no definía `LimiterNode`, compilador, runtime ni evidencia. Por
tanto:

```text
LIMITER_CAPABILITY = RESERVED_FUTURE
LIMITER_UI_VISIBLE = FALSE
LIMITER_RUNTIME_ALLOWED = FALSE
```

Sólo podrá promoverse mediante una ampliación que defina, como mínimo:

```text
typed LimiterNode
threshold / ceiling / release / lookahead semantics
latency contract
backend capability probe
runtime readback/evidence
clipping/true-peak tests
Signal Truth node
bypass/rollback behavior
```

No esconder clipping activando un limiter implícito.

---

# 77. FIR / CONVOLUTION / ROOM CORRECTION

## 77.1 Core simple

GStreamer `audiofirfilter` puede representar FIR explícito y reporta su
latencia en samples. Esto sirve como primer backend de pruebas y filtros
moderados.

## 77.2 IR management

No persistir únicamente una ruta arbitraria.

``` python
@dataclass(frozen=True, slots=True)
class ImpulseResponseAsset:
    asset_id: str
    sha256: str
    sample_rate_hz: int
    channels: int
    frames: int
    managed_path: str
```

Al importar una IR:

``` text
validate format
copy to Michi-managed store
hash bytes
extract metadata
persist asset identity
```

Cambio de archivo externo posterior no puede alterar silenciosamente un preset.

## 77.3 Sample-rate mismatch

El plan debe elegir explícitamente una policy:

``` text
IR_EXACT_RATE_REQUIRED
IR_RESAMPLE_OFFLINE
IR_RESAMPLE_RUNTIME
```

La opción por defecto recomendada para reproducibilidad es preparar/cachear IR
por rate fuera del hot path, no resamplear la IR arbitrariamente durante cada
reproducción.

---

# 78. RESAMPLING EXPLÍCITO

Resampling deja de ser sólo una anomalía detectada; puede ser una transformación
solicitada.

``` python
class ResamplePolicy(Enum):
    OFF = "off"
    TARGET_RATE = "target_rate"
    MAX_DEVICE_RATE = "max_device_rate"
    FAMILY_PRESERVING = "family_preserving"
```

## 78.1 Backend inicial

GStreamer `audioresample` es el backend disponible con quality 0..10 y varios
métodos. Crear perfiles de quality internos, no exponer parámetros crudos a la
UI normal.

## 78.2 libsoxr

Investigar `libsoxr` como backend opcional/benchmark. Si se adopta:

``` text
backend choice is persisted in processing profile
backend/version appears in evidence
latency appears in Signal Path
quality preset is explicit
```

Ningún resampling automático puede ocurrir en Strict Direct.

---

# 79. DITHER Y REDUCCIÓN DE PRECISIÓN

Dither sólo tiene sentido cuando una transformación termina en una reducción
cuantizada que lo justifica. No aplicarlo a 32-bit float processing porque "es
audiófilo".

``` python
class DitherPolicy(Enum):
    OFF = "off"
    AUTO_ON_BIT_REDUCTION = "auto_on_bit_reduction"
    TPDF = "tpdf"
```

`AUTO` debe ser reproducible y explicable. Signal Path muestra:

``` text
DITHER
TPDF
24-bit float/int processing -> 16-bit output
```

---

# 80. CAMILLADSP --- EXECUTOR AVANZADO OPCIONAL

CamillaDSP encaja como sidecar PCM de alto nivel para convolution extensa,
crossovers y routing complejo.

## 80.1 No es AudioEngine

``` text
GStreamer/Qt/MPD = playback engines
CamillaDSP        = processing executor
```

## 80.2 Gate de investigación

Antes de elegir el handoff de audio, comparar:

``` text
A. PipeWire virtual nodes          -> Shared/system mode
B. ALSA loopback                   -> fácil, pero complica proof/latency
C. stdin/stdout/FIFO supported path -> posible IPC local
D. custom local stream bridge      -> mayor control, mayor costo
```

No congelar una opción hasta medir latency, xruns, failure recovery y proof
surface.

## 80.3 Control plane

Si se usa websocket:

``` text
bind 127.0.0.1 only
random per-session port or unix proxy when possible
no remote bind
Michi owns process lifecycle
Michi generates config
Michi validates every state transition
```

## 80.4 DSD

CamillaDSP se trata como PCM-only. Para una fuente DSD:

``` text
DSD -> explicit DSD_TO_PCM -> CamillaDSP -> PCM output
```

---

# 81. PIPEWIRE FILTER-CHAIN --- ADAPTER SHARED, NO DIRECT CANÓNICO

Puede ofrecer:

``` text
param_eq
convolver
LV2/LADSPA
SOFA
ffmpeg filters
virtual sink/source
```

Uso propuesto:

``` text
Desktop Shared DSP
system-wide processing opt-in
headphone EQ shared path
```

No usarlo para afirmar `Direct` o `BitPerfect VERIFIED` salvo que en el futuro
exista evidencia completa de toda la ruta de sistema.

---

# 82. LV2 HOST --- EXTENSIÓN POST-CORE

Antes de habilitar plugins arbitrarios:

``` text
plugin discovery cache
license metadata
crash isolation strategy
RT-safety declaration/allowlist
state serialization
Worker extension support
path/resource sandbox rules
latency reporting
parameter schema projection
blacklist/quarantine
```

Preferir inicialmente una allowlist de plugins conocidos. Un plugin que no puede
ser explicado por Signal Path no entra en el core audiófilo.

---

# 83. DSD SOURCE TRUTH --- NO DECODIFICAR A PCM PARA DESCUBRIR DSD

Crear un characterizer first-class:

``` python
class SourceSignalCharacterizerPort(Protocol):
    def characterize(self, path: Path) -> SignalFormat: ...
```

V3.5 `SourceCharacterizerPort` se conserva para PCM frozen. Phase 2 añade un
servicio superior que puede delegar en él.

## 83.1 GStreamer >=1.24

Investigar la ruta real DSF/DFF de la distro y comprobar si el stream puede
llegar como `audio/x-dsd`. No asumir que `playbin3` evita el decoder DSD→PCM:
autoplug puede seleccionar un decoder que produzca PCM.

Gate obligatorio:

``` text
DSF fixture
  ↓
selected branch introspection
  ↓
prove audio/x-dsd before output
  ↓
record grouping/rate/channels/reversed-bytes
```

Si el runtime sólo ofrece PCM:

``` text
Native DSD capability = unavailable on this runtime
DSD_TO_PCM may remain available if explicitly allowed
```

---

# 84. NATIVE DSD OUTPUT

## 84.1 Receta separada

``` python
@dataclass(frozen=True, slots=True)
class StrictDsdSinkRecipe:
    plan_id: str
    sink_factory: str
    device: str
    gst_format: str
    rate_hz: int
    channels: int
    reversed_bytes: bool
```

Caps:

``` text
audio/x-dsd,
format=DSDU8|DSDU16LE|DSDU16BE|DSDU32LE|DSDU32BE,
rate=...,
channels=...,
layout=interleaved,
reversed-bytes=false|true
```

## 84.2 `dsdconvert`

Puede utilizarse sólo para grouping/endianness/bit-order cuando la evidencia
muestre que no cambia rate ni channels. Signal Path lo clasifica como
`DSD_CONTAINER_ADAPTATION`, no como DSD→PCM.

## 84.3 Fail closed

``` text
source DSD format unknown       -> STOP/UNVERIFIED
ALSA exact format unsupported   -> STOP or explicit fallback policy
runtime caps become audio/x-raw -> Native DSD candidate FAILED
rate changes                    -> contradiction
unexpected PCM converter        -> contradiction
```

---

# 85. ALSA QUALIFICATION PARA DSD

No sobrecargar `CapabilityEvidence(PcmTuple)`.

Crear un namespace/tipo Phase 2:

``` python
@dataclass(frozen=True, slots=True)
class SignalCapabilityEvidence:
    stable_device_id: str
    signal_format: SignalFormat
    supported: bool | None
    strength: EvidenceStrength
    source: str
    observed_at_ns: int
    environment_fingerprint: str
    evidence_refs: tuple[str, ...]
```

El adapter ALSA Phase 2 debe exact-open/readback:

``` text
DSD_U8
DSD_U16_LE / BE
DSD_U32_LE / BE
rate/grouping/channels
```

BUSY/REMOVED/TIMEOUT mantienen la semántica V3.5: nunca equivalen a
UNSUPPORTED.

---

# 86. DOP --- ARQUITECTURA DEL CARRIER

DoP merece un pipeline separado; no una flag escondida en PCM.

``` text
DSD SOURCE
   ↓
normalise DSD grouping if required
   ↓
DoP PACKER
   ↓
exact carrier caps
   ↓
ALSA PCM endpoint
   ↓
DAC interprets DoP
```

## 86.1 Reglas del packer

La implementación debe producir frames con:

``` text
2 payload bytes DSD
+ marker 0x05 / 0xFA alternado por sample frame
+ channel-consistent marker phase
```

Debe manejar bit reversal únicamente cuando el source evidence lo exige.

## 86.2 Carrier rate

No hardcodear una tabla en QML. Un `DopCarrierPolicy` puro calcula/valida el
carrier a partir del DSD source y del contrato DoP. Cada mapping debe tener unit
tests con fixtures conocidos.

## 86.3 Negotiation

Carrier debe negociarse sin resample/remix/format mutation. Si ALSA/GStreamer
cambia el carrier:

``` text
DOP_CARRIER_MUTATED -> FAIL
```

---

# 87. DOP PACKER --- TECHNOLOGY DECISION GATE

La investigación no encontró un elemento GStreamer stock dedicado a DoP. No
implementar el packer por muestra en Python productivo.

Evaluar:

| Opción | Ventaja | Riesgo |
|---|---|---|
| Rust GStreamer element | RT-friendly, integración natural | añade toolchain/packaging nativo |
| C GStreamer element | ecosistema clásico Gst | memoria/seguridad + build C |
| Python GstBaseTransform | prototipo rápido | no aceptable sin benchmark RT extremo |
| MPD DoP path | implementación madura de referencia | no debe saltarse OutputPlan/ownership |

**Preferencia de investigación:** Rust/GStreamer plugin (`michi-dop`) si el
benchmark y packaging gate justifican añadir Rust. No es decisión final hasta
un ADR específico.

## 87.1 ADR de stack

El repo actual declara "no C++ / no native build system". Añadir Rust/C para
DoP exige un ADR explícito y actualización de M13 packaging. Hasta entonces:

``` text
DOP_EXECUTOR_STATUS = RESEARCH / NOT IMPLEMENTED
```

---

# 88. DOP EVIDENCE --- QUÉ PUEDE Y QUÉ NO PUEDE PROBAR MICHI

Michi puede probar software-side:

``` text
source is DSD
packer revision/hash
marker continuity
payload preservation
carrier rate/format/channels
ALSA negotiated carrier
no DSP/resample/remix on carrier
```

Michi normalmente **no puede observar directamente** que el DAC cambió a modo
DSD sólo mirando ALSA.

Por tanto:

``` text
DoP software transport verified  != DAC DSD mode physically verified
```

La última afirmación necesita:

``` text
device feedback
or physical qualification
or strong qualified device knowledge
```

La UI debe distinguirlas.

---

# 89. DSD→PCM --- TRANSFORMACIÓN EXPLÍCITA

No permitir que quede oculta dentro del decoder.

``` python
@dataclass(frozen=True, slots=True)
class DsdToPcmPolicy:
    target_rate_hz: int | None
    target_format: str
    converter_backend: str
    quality_profile: str
```

Signal Path:

``` text
SOURCE        DSD128
    ↓
DSD→PCM       backend/version/quality
    ↓
PCM           176.4 kHz float
    ↓
DSP           PEQ + convolution
    ↓
DAC           PCM 176.4/24
```

## 89.1 Backend gate

FFmpeg actual dispone de un sample format DSD first-class. Investigar una ruta
que haga la conversión de forma explícita y controlada. No atar el dominio a
un decoder concreto.

## 89.2 Filter quality

Antes de cerrar DSD→PCM:

``` text
frequency response tests
alias/noise measurement
latency measurement
DSD64/128/256 fixtures
44.1-family target policy
CPU benchmarks
```

---

# 90. MATRIZ DSD × DSP

| Fuente | Policy | DSP | Salida permitida | Signal Path |
|---|---|---:|---|---|
| PCM | source-native | OFF | PCM Direct | DIRECT candidate |
| PCM | DSP profile | ON | PCM Processed | PROCESSED |
| DSD | Native | OFF | Native DSD | DSD_NATIVE |
| DSD | DoP | OFF | DoP carrier | DOP |
| DSD | Preserve DSD | ON requested | refuse/bypass by explicit policy | explain conflict |
| DSD | Process as PCM | ON | DSD→PCM→DSP→PCM | PROCESSED |
| DSD | PCM conversion | OFF | DSD→PCM→PCM | CONVERTED |

No existe:

``` text
DSD -> PEQ -> Native DSD
DoP carrier -> convolution -> DoP
```

sin un modulador DSD específico, que no forma parte de este plan.

---

# 91. PROCESSING RUNTIME EVIDENCE

Crear evidencia por graph revision, no un booleano `dsp_observed` solamente.

``` python
@dataclass(frozen=True, slots=True)
class ProcessingNodeRuntimeEvidence:
    node_id: str
    kind: str
    active: bool | None
    input_format: SignalFormat | None
    output_format: SignalFormat | None
    latency_frames: int | None
    backend_element: str
    parameters_digest: str

@dataclass(frozen=True, slots=True)
class ProcessingRuntimeEvidence:
    graph_id: str
    graph_revision: int
    execution_generation: int
    nodes: tuple[ProcessingNodeRuntimeEvidence, ...]
    bypass_proven: bool | None
```

Esto alimenta SignalTruth y SignalPathGraph.

---

# 92. SIGNAL TRUTH 2 --- SEPARAR TRES EJES

No colapsar todo en un badge.

``` python
class PathVerdict(Enum):
    DIRECT = "direct"
    DSD_NATIVE = "dsd_native"
    DOP = "dop"
    PROCESSED = "processed"
    RESAMPLED = "resampled"
    REMIXED = "remixed"
    DSD_TO_PCM = "dsd_to_pcm"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"

# M11.5 authority
BitPerfectState = VERIFIED | UNVERIFIED | NOT_APPLICABLE | BROKEN

class ProcessingRuntimeState(Enum):
    BYPASSED = "bypassed"
    ACTIVE = "active"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
```

UI compacta puede renderizar:

``` text
Direct · Verified
DoP · Transport verified / DAC mode unverified
Processed · PEQ + FIR
DSD→PCM · Processed
```

pero los enums permanecen separados.

---

# 93. SIGNAL PATH GRAPH 2 --- NODOS DSP/DSD

Congelar stages canónicos:

``` text
SOURCE
DECODE_OR_DEMUX
ENGINE
FORMAT_ADAPTATION
PROCESSING
VOLUME
RESAMPLING
DITHER
TRANSPORT
DEVICE_NEGOTIATION
PHYSICAL_LINK
DEVICE
NETWORK_TRANSPORT      # futuro
NETWORK_ENDPOINT       # futuro
```

`PEQ`, `FIR`, `CONVOLUTION`, `DOP_PACKER`, `DSD_TO_PCM` son node subtypes, no
nuevos stages arbitrarios.

## 93.1 Snapshot

``` python
@dataclass(frozen=True, slots=True)
class SignalPathIdentity:
    playback_request_epoch: int
    output_plan_id: str | None
    processing_graph_id: str | None
    processing_graph_revision: int | None
    execution_generation: int
    binding_generation: int | None

@dataclass(frozen=True, slots=True)
class SignalEdge:
    source_node_id: str
    target_node_id: str

@dataclass(frozen=True, slots=True)
class SignalPathSnapshot:
    identity: SignalPathIdentity
    nodes: tuple[SignalNode, ...]
    edges: tuple[SignalEdge, ...]
    path_verdict: PathVerdict
    proof_state: BitPerfectState
    revision: int
```

---

# 94. EVIDENCE MODEL 2 --- PROVENANCE MULTIFUENTE

Sustituir el conceptual `EvidenceValue` simple por dos niveles.

``` python
class EvidenceResolution(Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"
    STALE = "stale"
    NOT_APPLICABLE = "not_applicable"

@dataclass(frozen=True, slots=True)
class EvidenceRecord(Generic[T]):
    evidence_id: str
    origin: EvidenceOrigin
    value: T
    observed_at_ns: int | None
    execution_generation: int | None
    binding_generation: int | None
    environment_fingerprint: str | None
    source_version: str | None
    source_ref: str | None
    confidence: EvidenceConfidence

@dataclass(frozen=True, slots=True)
class ResolvedEvidenceValue(Generic[T]):
    value: T | None
    resolution: EvidenceResolution
    records: tuple[EvidenceRecord[T], ...]
```

`USER_OVERRIDE` sale de `EvidenceOrigin`: un override es configuración/policy,
no evidencia de hardware.

Evitar además un segundo tipo llamado `CapabilityEvidence`, porque V3.5 ya lo
usa. Para Phase 2 usar `ResolvedCapability`.

---

# 95. PERSISTENCIA DSP / DSD / EVIDENCE

Definir scopes antes de schema migration.

| Dato | Persistir | Rebuildable | Invalidación |
|---|---|---|---|
| DSP profile | sí | no | user/version migration |
| selected DSP profile | sí | no | explicit user choice |
| active DSP graph | no | sí | cada runtime generation |
| FIR/IR asset | managed store + hash | no | hash mismatch |
| Native DSD runtime evidence | no | sí | session/generation |
| DSD capability qualification | cache | sí | environment fingerprint |
| DoP device qualification | cache/profile evidence | sí | device/env/profile version |
| Signal Path snapshot | no | sí | every committed runtime change |
| MAHKB | resource versioned | sí | KB version |

## 95.1 Tablas propuestas

``` text
processing_profiles
processing_profile_revisions
processing_assets
processing_selection
signal_capability_cache
```

No persistir raw GStreamer object names como autoridad; sí pueden aparecer como
diagnostic evidence.

---

# 96. THREADING / REAL-TIME CONTRACT

El trabajo reciente del repo demuestra que GLib/GStreamer ownership es una zona
crítica. Phase 2 debe declarar:

``` text
GStreamer pump thread:
    observe native runtime / execute Gst lifecycle commands

worker threads:
    load/hash IR
    parse profiles
    offline IR resample
    hardware probes
    expensive analysis

Qt/application owner thread:
    validate generations
    commit canonical state
    publish immutable projections

QML thread:
    render / emit intents only
```

Prohibido:

``` text
file I/O in audio processing callback
JSON parsing in audio callback
MAHKB lookup in audio callback
QML mutation from GStreamer thread
unbounded lock in real-time processing
Python per-sample DoP packing
```

---

# 97. ATOMIC LIVE DSP RECONFIGURATION

Cambiar un PEQ/IR durante playback no puede dejar medio graph viejo y medio
nuevo.

``` text
compile B
prepare B
preroll/validate B
atomic switch at safe boundary
publish B active
retire A
```

Si el backend no soporta switch seguro:

``` text
controlled pause/stop
rebuild
resume only according to explicit product contract
```

No prometer seamless hasta medirlo.

Cada graph tiene revision; callbacks tardíos de A no pueden mutar B.

---

# 98. LATENCY MODEL

Cada node puede declarar/observar latency.

``` python
@dataclass(frozen=True, slots=True)
class LatencyEvidence:
    declared_frames: int | None
    queried_frames: int | None
    measured_frames: int | None
    sample_rate_hz: int
```

Signal Path detailed muestra latency cuando está disponible. La UI normal sólo
la muestra si afecta uso (por ejemplo convolution larga).

Presupuestos deben fijarse tras benchmark, no inventarse ahora. El gate exige
medir:

``` text
PEQ 10/32/64 bands
FIR 1k/8k/64k/256k taps
stereo / multichannel
44.1 / 48 / 96 / 192 kHz
DSD transitions
DoP packer CPU
graph switch latency
XRUN count
memory
```

---

# 99. AUDIO PROCESSING UI / AUDIO LAB


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

## 99.1 NowPlaying Quick Surface

El botón Audio/DSP deja de ser un icono genérico y proyecta estado real:

``` text
DSP OFF
PEQ · 8 bands
PEQ + FIR
Room Correction · Living Room
DSD preserved · DSP bypassed
DSD→PCM · PEQ active
```

Popup:

``` text
AUDIO PROCESSING
────────────────────
Profile        Headphones
State          Active
Preamp         -5.5 dB
PEQ            8 bands
Convolution    Off
Resampling     Off

Signal impact  Processed
[ Open Audio Lab ]
```

No editar decenas de parámetros desde el popup.

## 99.2 Audio Lab full surface

Tres niveles:

``` text
GENERAL
    profile / bypass / preamp / PEQ summary

ADVANCED
    band editor / FIR / convolution / resampler / channel tools

EXPERT
    backend / graph / latency / caps / node evidence / diagnostics
```

## 99.3 Transaction UX

Edits son draft hasta Apply o live-preview transaction:

``` text
Draft -> Validate -> Compile -> Preview -> Commit
                         └──── failure -> rollback
```

---

# 100. DEVICE SETUP + DSD/DoP UI

El DAC Quick Popup puede añadir, cuando exista evidence:

``` text
DSD             Native up to DSD256        [Qualified]
DoP             Supported                  [Qualified]
Current mode    Native DSD128
DSP             Bypassed to preserve DSD
```

Nunca mostrar máximos derivados sólo de marketing.

Advanced:

``` text
Declared / Observed / Qualified / Runtime
Native DSD
DoP
DSD grouping
carrier constraints
stop-DSD-silence quirk
DSD→PCM fallback policy
```

---

# 101. DSD / DOP TRANSITION STATE MACHINE

Transiciones de format family son destructivas salvo evidencia contraria.

``` text
PCM -> PCM same tuple           candidate for gapless
PCM -> PCM different rate      controlled reopen
PCM -> Native DSD              controlled reopen
Native DSD -> PCM              controlled reopen
Native DSD -> DoP              controlled reopen
DoP -> Native DSD              controlled reopen
DSD64 -> DSD128                controlled reopen unless proven safe
DSP PCM -> Native DSD          bypass/teardown DSP then reopen
Native DSD -> DSP PCM          DSD→PCM + build DSP then reopen
```

No fabricar continuidad.

State machine debe preservar:

``` text
playback request epoch
output generation
processing graph revision
binding generation
source identity
```

---

# 102. STOP / PAUSE EN DSD

Algunos DACs pueden producir ruido al cerrar DSD; MPD expone una opción
`stop_dsd_silence` precisamente para workarounds específicos.

Michi no debe activarlo globalmente.

``` python
class DsdStopPolicy(Enum):
    NORMAL = "normal"
    QUALIFIED_SILENCE = "qualified_silence"
```

Sólo MAHKB/Native Profile + physical qualification pueden recomendar el modo
especial. Debe tener test físico por modelo/revisión.

---

# 103. TESTING DSP --- CONFORMANCE, NO SÓLO UI

## 103.1 Unit

``` text
PEQ parameter validation
biquad response reference
profile revision hashing
IR asset hashing
processing graph determinism
headroom policy
resampler policy
DSD/DSP compatibility matrix
```

## 103.2 Golden signal fixtures

Generar señales conocidas y comparar output:

``` text
impulse
sine sweeps
multitone
noise
stereo polarity fixtures
channel impulses
```

Gates:

``` text
bypass sample identity where format permits
PEQ magnitude response within tolerance
FIR convolution equals reference convolution within tolerance
delay exact frames
polarity exact inversion
channel map exact
no unplanned resampling
```

## 103.3 Failure

``` text
invalid IR
IR deleted after import
backend element unavailable
profile schema unsupported
GStreamer graph link failure
live reconfigure failure
stale graph callback
XRUN during processing
```

---

# 104. TESTING NATIVE DSD

Fixtures mínimas:

``` text
DSD64 stereo
DSD128 stereo
DSD256 stereo when toolchain supports fixture
DSDU8
DSDU16LE/BE
DSDU32LE/BE
bit-reversed fixture
```

Assertions:

``` text
source remains DSD
no audio/x-raw in Native candidate branch
rate/channel preserved
grouping adaptation explained
ALSA negotiated DSD format exact
unexpected DSD→PCM fails Native candidate
stale generation ignored
```

---

# 105. TESTING DOP BYTE-FOR-BYTE

DoP tests no dependen de un DAC para validar el packer.

``` text
known DSD bytes
     ↓
DoP packer
     ↓
expected exact carrier bytes
```

Validar:

``` text
0x05 / 0xFA alternation
per-channel marker phase
payload bytes preserved
wrap across buffer boundaries
odd/even chunk splits
state continuity across buffers
reset semantics on new stream
bit reversal cases
carrier rate mapping
24-in-32 alignment mode if supported
```

Luego pruebas ALSA y físicas por separado.

---

# 106. PHYSICAL HARDWARE MATRIX AMPLIADA

No cerrar esta Phase 2 sólo con mocks.

Mínimo recomendado:

``` text
A. generic UAC2 PCM DAC
B. known commercial PCM DAC
C. Native DSD-capable USB DAC
D. DoP-capable DAC
E. DAC with both Native + DoP
F. DAC that explicitly does NOT support DoP / negative safety case
G. generic XMOS descriptor device
H. multi-endpoint USB audio interface
```

Matrix por hardware:

``` text
PCM 44.1/48/96/192
24 significant-bit evidence
Native DSD64/128 (higher when supported)
DoP DSD64/128
DSD→PCM
PCM DSP PEQ
PCM DSP convolution
hotplug
busy
suspend/resume
format-family transition
DSP on/off transition
```

`NOT_RUN` permanece visible; nunca equivale a PASS.

---

# 107. PERFORMANCE / QUALITY GATES

Crear `scripts/verify_audio_phase2.py` sólo cuando Phase 2 sea autorizada.

Debe medir y registrar:

``` text
CPU mean / p95
RSS
pipeline prepare latency
graph switch latency
XRUN count
buffer recovery count
DSD/DoP transition time
DSP latency frames
long-run drift
```

Profiles de benchmark:

``` text
Baseline Direct PCM
PEQ 10 bands
PEQ 64 bands
FIR short
convolution long
resample 44.1->48
resample 96->192
Native DSD64/128
DoP DSD64/128
DSD→PCM + PEQ
```

No fijar umbrales de release hasta ejecutar baseline en hardware representativo.

---

# 108. PACKAGING Y FEATURE DISCOVERY

## 108.1 GStreamer

DSD features requieren runtime GStreamer con soporte first-class DSD; baseline
de investigación: 1.24+.

La app debe descubrir:

``` text
Gst version
playbin3
audio/x-dsd support in alsasink
dsdconvert
equalizer-nbands
audiofirfilter
audioresample
audiodynamic
```

Falta de un plugin degrada la capability; no rompe base playback.

## 108.2 CamillaDSP

Si se distribuye como companion runtime:

``` text
version probe
license notice
process integrity/lifecycle
optional package dependency
no network required
```

El repo ya lo trata conceptualmente como external process; mantener el firewall
de licencias y no copiar source.

## 108.3 DoP native plugin

Si el technology gate elige Rust/C:

``` text
new ADR
reproducible build
architecture matrix x86_64/aarch64
AppImage/Flatpak/deb packaging
ABI/version check
plugin signature/hash in diagnostics
```

---

# 109. HISTÓRICO / SUPERSEDED — LISTA TEMPRANA DE ARCHIVOS

> **SUPERSEDED BY §120:** el árbol canónico de archivos y ownership es §120. Esta lista se conserva sólo para rastrear la evolución del diseño y NO debe alimentar creación de archivos si contradice §120 o una tarjeta AP2-Fxx.

**No crear antes del gate.** Nombres orientativos, deben reconciliarse con el
repo frozen.

``` text
src/michi/domain/audio_signal.py
src/michi/domain/audio_processing.py
src/michi/domain/audio_processing_evidence.py
src/michi/domain/dsd.py
src/michi/domain/dop.py

src/michi/application/audio_processing_ports.py
src/michi/application/audio_processing_service.py
src/michi/application/processing_graph_compiler.py
src/michi/application/processing_profile_service.py
src/michi/application/dsd_policy_service.py
src/michi/application/dsd_output_planner.py
src/michi/application/signal_path_service.py

src/michi/infrastructure/audio_processing/gstreamer_processing.py
src/michi/infrastructure/audio_processing/camilladsp.py
src/michi/infrastructure/audio_processing/pipewire_filter_chain.py
src/michi/infrastructure/audio_processing/ir_store.py
src/michi/infrastructure/audio_output/strict_dsd_sink.py
src/michi/infrastructure/audio_output/dop_runtime.py
src/michi/infrastructure/audio_devices/alsa_dsd_probe.py

src/michi/presentation/audio_processing_bridge.py
src/michi/presentation/signal_path_bridge.py

src/michi/presentation/qml/views/AudioLabView.qml
src/michi/presentation/qml/player/AudioProcessingPopup.qml
src/michi/presentation/qml/player/SignalPathPopup.qml
src/michi/presentation/qml/components/ProcessingGraphSummary.qml
src/michi/presentation/qml/components/PeqEditor.qml
src/michi/presentation/qml/components/ConvolutionSetup.qml
src/michi/presentation/qml/components/DsdTransportCard.qml
```

Si DoP requiere plugin nativo:

``` text
companion/michi-gst-dop/       # sólo tras ADR de stack
```

---

# 110. WORK PACKAGES DSP

``` text
DSP-000  Architecture ADR + ownership freeze
DSP-010  Processing domain + profile schema
DSP-020  Immutable ProcessingGraph + compiler
DSP-030  GStreamer processing attachment
DSP-040  Preamp/headroom + PEQ
DSP-050  FIR/convolution + IR asset store
DSP-060  Explicit resampling + dither policy
DSP-070  Runtime evidence + SignalTruth integration
DSP-080  CamillaDSP feasibility / prototype gate
DSP-090  Shared PipeWire adapter research
DSP-100  LV2 host research gate
DSP-110  Audio Lab UI
DSP-120  Physical/performance matrix
DSP-130  DSP adversarial seal
```

Exit `DSP-130`:

``` text
bypass truth proven
no hidden processing
all active nodes observable
atomic graph transition
no stale graph events
full regression green
performance evidence published
```

---

# 111. WORK PACKAGES DSD / DOP

``` text
DSD-000  First-class SignalFormat domain
DSD-010  DSD source characterization
DSD-020  ALSA DSD exact qualification
DSD-030  Native DSD strict GStreamer path
DSD-040  DoP technology-decision ADR
DSD-050  DoP packer + exact carrier planning
DSD-060  DSD→PCM explicit converter seam
DSD-070  format-family transition state machine
DSD-080  SignalTruth/SignalPath DSD evidence
DSD-090  Device Setup DSD/DoP UX
DSD-100  Native/DoP physical matrix
DSD-110  DSD/DSP interoperability
DSD-120  DSD/DoP adversarial seal
```

Exit `DSD-120`:

``` text
Native DSD cannot silently become PCM
DoP cannot silently mutate carrier
DoP cannot auto-enable on unknown hardware
DSD→PCM is always visible
DSD+DSP policy is deterministic
transitions are generation-safe
physical matrix has real devices
```

---

# 112. WORK PACKAGES DE CONVERGENCIA

``` text
AUDIO2-000  reconcile actual frozen M11.5 API
AUDIO2-010  Signal Path 2 canonical taxonomy
AUDIO2-020  Device Setup + Processing capability convergence
AUDIO2-030  NowPlaying DSP / DAC / Signal Path convergence
AUDIO2-040  persistence + migration seal
AUDIO2-050  threading / stale-generation seal
AUDIO2-060  packaging feature-discovery seal
AUDIO2-070  full physical/performance qualification
AUDIO2-080  KILLCRITIC adversarial audit
AUDIO2-090  FINAL AUDIO PHASE 2 FREEZE
```

---

# 113. GATES DE NO-REGRESIÓN NUEVOS

``` text
Strict PCM Direct remains byte/format semantically unchanged when DSP OFF
DSP never changes selected DAC without explicit output intent
DSP never changes AudioEngine automatically
Native DSD never traverses PCM DSP
DoP carrier never traverses PCM DSP
DSD→PCM never occurs silently
unknown DoP capability never enables DoP
CamillaDSP failure never corrupts canonical playback/output authorities
PipeWire DSP cannot masquerade as Direct
LV2 plugin failure cannot own playback lifecycle
processing profile corruption cannot prevent base playback
missing Phase 2 dependencies degrade gracefully
```

---

# 114. DECISION TABLE --- QUÉ HACER CON CADA FUENTE / POLICY

| Source | Processing request | DSD policy | Output capability | Result |
|---|---|---|---|---|
| PCM | OFF | n/a | Direct PCM | Strict Direct |
| PCM | PEQ/FIR | n/a | PCM | Processed PCM |
| DSD | OFF | AUTO | Native qualified | Native DSD |
| DSD | OFF | AUTO | DoP qualified only | DoP |
| DSD | OFF | AUTO | neither, PCM conversion allowed | DSD→PCM |
| DSD | OFF | AUTO | neither, conversion forbidden | STOP/ASK |
| DSD | DSP ON | PRESERVE_DSD | Native/DoP available | refuse DSP or explicit bypass |
| DSD | DSP ON | PCM_CONVERSION | PCM output | DSD→PCM→DSP |
| DSD | DSP ON | AUTO | ambiguous | ASK; never guess |

---

# 115. HIGH-END PRODUCT EXPERIENCE OBJETIVO

La experiencia final debería poder responder, sin marketing ambiguo:

``` text
SOURCE
DSD128 · stereo

PROCESSING
Room Correction · Living Room
DSD converted to PCM explicitly
PEQ 6 bands
FIR 65,536 taps
Preamp -4.5 dB

ENGINE
GStreamer

TRANSPORT
ALSA Direct-like processed path
PCM 176.4 kHz / 24 significant bits

DAC
Topping D90SE

INTEGRITY
Processed — bit-perfect not applicable

WHY?
DSD processing requires PCM conversion.
Selected DSP profile explicitly allows it.
Target rate preserves the 44.1 kHz family.
Runtime caps and ALSA negotiation match the plan.
```

Y para Native DSD:

``` text
SOURCE
DSD128

PROCESSING
Bypassed — Preserve DSD

TRANSPORT
Native DSD

DEVICE
DSD_U32_LE · exact negotiated endpoint

INTEGRITY
Native DSD path
M11.5 proof state: [actual verified/unverified state]
```

Y para DoP:

``` text
SOURCE       DSD64
PACKER       DoP v1
CARRIER      176.4 kHz / 24-bit-compatible framing
MARKERS      0x05 / 0xFA continuity verified
ALSA         carrier exact
DAC MODE     qualified / runtime-unobservable
```

---

# 116. FUENTES TÉCNICAS EXTERNAS REVALIDADAS PARA ESTA AMPLIACIÓN

Revalidar de nuevo al activar Phase 2; las APIs pueden evolucionar.

## GStreamer

- https://gstreamer.freedesktop.org/releases/1.24/
- https://gstreamer.freedesktop.org/documentation/audio/gstdsd.html
- https://gstreamer.freedesktop.org/documentation/dsd/index.html
- https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html
- https://gstreamer.freedesktop.org/documentation/playback/playbin3.html
- https://gstreamer.freedesktop.org/documentation/equalizer/equalizer-nbands.html
- https://gstreamer.freedesktop.org/documentation/audiofx/audiofirfilter.html
- https://gstreamer.freedesktop.org/documentation/audiofx/audiodynamic.html
- https://gstreamer.freedesktop.org/documentation/audioresample/index.html

## MPD

- https://mpd.readthedocs.io/en/stable/user.html
- https://mpd.readthedocs.io/en/stable/plugins.html
- https://github.com/MusicPlayerDaemon/MPD/blob/master/src/output/plugins/AlsaOutputPlugin.cxx

## Linux / ALSA

- https://github.com/torvalds/linux/blob/master/include/uapi/sound/asound.h
- https://github.com/torvalds/linux/blob/master/include/sound/pcm.h
- Linux `sound/usb/pcm.c` DoP implementation as upstream reference pattern

## DSP

- https://docs.pipewire.org/page_module_filter_chain.html
- https://github.com/HEnquist/camilladsp
- https://github.com/HEnquist/camilladsp/blob/master/sample_formats.md
- https://github.com/HEnquist/camilladsp/blob/master/websocket.md
- https://lv2plug.in/
- https://lv2plug.in/ns/ext/state
- https://lv2plug.in/ns/ext/worker
- https://github.com/chirlu/soxr

## FFmpeg

- https://ffmpeg.org/doxygen/trunk/group__lavu__sampfmts.html

---

# 117. RESULTADO ARQUITECTÓNICO FINAL

La nueva arquitectura ambiciosa queda:

``` text
                           SOURCE
                             │
                ┌────────────┴────────────┐
                │                         │
               PCM                       DSD
                │                         │
                │              ┌──────────┼──────────┐
                │              │          │          │
                │          Native DSD    DoP      DSD→PCM
                │              │          │          │
                │              │          │          └─────┐
                │              │          │                │
                ▼              │          │                ▼
        PROCESSING GRAPH       │          │        PROCESSING GRAPH
        PEQ/FIR/etc            │          │        PEQ/FIR/etc
                │              │          │                │
                └──────┐       │          │        ┌───────┘
                       ▼       ▼          ▼        ▼
                   OUTPUT / TRANSPORT PLANNING
                             │
                             ▼
                        ALSA / DAC
                             │
                             ▼
                        RUNTIME EVIDENCE
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         SignalTruth     M11.5 Proof   Processing Evidence
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                      SignalPathGraph
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
          NowPlaying      Audio Lab    Device Setup
```

La regla de cierre es simple:

``` text
MICHI NEVER HIDES A TRANSFORMATION.
MICHI NEVER GUESSES A DSD TRANSPORT.
MICHI NEVER CALLS A CARRIER "PCM AUDIO" WHEN IT IS DoP.
MICHI NEVER CALLS PROCESSED AUDIO BIT-PERFECT.
MICHI NEVER LETS A DSP BACKEND BECOME PLAYBACK AUTHORITY.
MICHI EXPLAINS EVERY CLAIM WITH EVIDENCE.
```



---

# 118. IMPLEMENTATION BLUEPRINT — CONTRATO NORMATIVO DE ESTA AMPLIACIÓN

Desde esta sección el documento deja de ser únicamente arquitectura objetivo y pasa a
contener una **implementación de referencia integral**. El propósito es que un agente de
implementación no tenga que inventar módulos, ownership, semántica de estados, nombres de
campos, transacciones, error codes, layout o interacción.

Reglas de uso de esta parte:

1. El código incluido es normativo respecto de **semántica, ownership, contratos y flujo**.
2. Los imports y nombres que dependan del API exacto de la baseline congelada deben ser
   reconciliados en `AUDIO2-000`; no se permite alterar la arquitectura para hacerlos compilar.
3. Si la baseline futura ya ofrece una autoridad equivalente, se **adapta** este código a la
   autoridad existente; no se crea un duplicado.
4. Todo objeto de dominio es framework-free, inmutable cuando represente evidencia/plan/snapshot
   y serializable sin objetos Qt/GStreamer/ALSA.
5. Ninguna UI decide capacidades, transportes, prueba de integridad, DSP real ni fallback.
6. Ninguna callback nativa muta estado de aplicación sin pasar por el owner thread y revalidar
   generación/revisión.
7. Todo cambio DSP se compila fuera del hot path y se instala mediante transacción atómica.
8. Native DSD, DoP y DSD→PCM son caminos explícitos y mutuamente distinguibles.
9. DoP nunca se modela como PCM musical.
10. La ausencia de evidencia produce `UNKNOWN/UNVERIFIED/NOT_OBSERVABLE`, nunca una afirmación.

**Baseline auditada al redactar esta especificación:**

```text
repository  pitydah/michi-music-player
branch      main
sha         dad7b7c12920427712a4e67b7e0a66796fa1bf84
stack       Python 3.11+ / PySide6 / QML / SQLite / GStreamer GI / MPD managed
platform    Linux first
```

Al activar Phase 2 se debe sustituir el SHA anterior por el SHA de la baseline realmente
congelada y ejecutar el protocolo de reconciliación definido en este documento.

## 118.1 Hechos observados en la baseline auditada

La baseline ya aporta las siguientes piezas que se consideran reutilizables y que **no se
reimplementan**:

```text
AudioTransportRouter
AudioEngineService / Registry / SelectionCoordinator
GStreamerAudioPort + private GLib MainContext
MPD private transport
AudioDeviceRegistry generation-safe
DacQualificationService exact ALSA probe
AudioOutputProfileService
OutputPlanner
OutputSessionService
DirectOutputExecutor
Strict PCM Direct sink
runtime graph inspection
SignalTruthRecorder
AudioOutputBridge
NowPlayingBar output grid
```

Limitaciones concretas verificadas en la baseline:

```text
DecodedSourceSignal             PCM-oriented
OutputPlanner                   rejects decoded_source.encoding != PCM
OutputPlan.requested_pcm        PcmTuple only
StrictSinkRecipe                audio/x-raw only
ALSA->GStreamer format map      S16_LE / S32_LE only
SourceCharacterizer             requires audio/x-raw
Direct runtime validator        PCM caps semantics
SignalTruth                     PCM-centric evidence types
DSP                             observability seam only; no Michi DSP executor
DSD metadata                    available in library presentation, not a playback authority
DoP                             no productive packer/planner/executor
```

Por tanto, la ampliación debe generalizar la representación de señal sin destruir el
`Stable Direct PCM` actual.

## 118.2 Fuentes tecnológicas vinculantes para el diseño

Revalidar versiones al activar la fase. En esta especificación se adoptan los siguientes
hechos de diseño:

- GStreamer 1.24+ incorpora representación DSD first-class mediante `GstDsdInfo` y
  `GstDsdFormat` y soporte DSD en `alsasink`.
- `alsasink` acepta `audio/x-dsd` con `DSDU8`, `DSDU16LE/BE`, `DSDU32LE/BE`.
- `dsdconvert` cambia grouping/layout/byte reversal de DSD sin cambiar rate ni canales.
- `playbin3` ofrece `audio-filter` y `audio-sink` customizables.
- `equalizer-nbands` es un candidato para graphic/N-band EQ; no prueba por sí mismo un PEQ arbitrario.
- `audiofirfilter` permite FIR con kernel y latencia declarada.
- `audioresample` permite políticas configurables de sinc/interpolación.
- ALSA define `SND_PCM_FORMAT_DSD_U8`, `DSD_U16_LE/BE`, `DSD_U32_LE/BE`.
- Linux USB Audio documenta el framing DoP con markers `0x05/0xFA` alternados y payload DSD.
- MPD separa Native DSD, DoP y DSD→PCM y no autoactiva DoP en hardware desconocido.
- PipeWire `filter-chain` soporta graphs con filtros builtin, LADSPA/LV2, SOFA, FFmpeg y convolver.
- LV2 `state` y `worker` aportan state serializable y trabajo no-real-time explícito.
- CamillaDSP aporta IIR, FIR/convolution, mixers, gain/delay/dither y control local.

Referencias oficiales se conservan en §116 y deben actualizarse en `AUDIO2-000`.


---

# 119. MAPA DE AUTORIDADES — VERSIÓN CERRADA

La implementación sólo es aceptable si cada verdad tiene un único owner.

```text
PlaybackState                PlaybackService
QueueState                   QueueService
AudioEngineState             AudioEngineService
AudioOutputSelection         AudioOutputProfileService + OutputSessionService
DAC exact qualification      DacQualificationService
Volume authority             VolumePolicyService
DSP selected profile         AudioProcessingService
DSP profile persistence      ProcessingProfileService
DSP compiled plan            ProcessingGraphCompiler (pure) + AudioProcessingService owner
DSD/DoP user policy          DsdPolicyService
Output execution             existing output executor transaction boundary
Native DSD executor state    output executor extension/adaptor, not a new playback owner
DoP packer runtime           DoP transport executor owned by output transaction
Signal Truth runtime         SignalTruthRecorder / future M11.5 authority
Signal Path snapshot         SignalPathService projection owner
Presentation                 bridges only, read-only projections + intents
```

Regla de exclusión:

```text
NO second PlaybackService
NO second OutputPlanner
NO second DacQualificationService
NO second VolumePolicyService
NO second SignalTruth truth authority
NO DSP state in QML
NO DAC capability state in QML
NO DoP capability inference in QML
NO backend-specific Gst objects above infrastructure
```

## 119.1 Flujo PCM con DSP

```text
TrackRef / SourceFileFacts
        ↓
SourceCharacterizer
        ↓
PcmSignalFormat
        ↓
AudioProcessingService.selected_profile
        ↓
ProcessingGraphCompiler
        ↓
CompiledProcessingPlan
        ↓
Output planning
        ↓
GStreamer processing bin
        ↓
Strict/Managed output path
        ↓
RuntimeProcessingEvidence
        ↓
SignalTruth + M11.5 proof
        ↓
SignalPathService
        ↓
NowPlaying / Audio Lab
```

## 119.2 Flujo Native DSD

```text
DSF/DFF
  ↓
DsdSourceCharacterizer
  ↓
DsdSignalFormat
  ↓
DsdPolicyService = PRESERVE_DSD
  ↓
DsdOutputPlanner
  ↓
StrictDsdSinkRecipe
  ↓
GStreamer audio/x-dsd
  ↓
optional dsdconvert (grouping only)
  ↓
alsasink / exact DSD ALSA binding
  ↓
DAC
  ↓
DSD runtime evidence
  ↓
SignalPathGraph
```

El DSP PCM queda bypassed de forma **observable**, no simplemente invisible.

## 119.3 Flujo DoP

```text
DSD source
  ↓
DsdSignalFormat
  ↓
DoP qualification/policy gate
  ↓
DoP packer
  ↓
DopCarrierFormat
  ↓
exact PCM-compatible carrier
  ↓
ALSA hardware endpoint
  ↓
DAC interprets DoP (physical result only claimed if evidenced)
```

La capa Signal Path debe mostrar simultáneamente:

```text
source_encoding       DSD64
transport_mode        DoP
carrier_rate          176400 Hz
carrier_container     24-bit compatible framing
marker_integrity      VERIFIED/UNKNOWN/BROKEN
device_mode           VERIFIED/UNVERIFIED/NOT_OBSERVABLE
```

## 119.4 Flujo DSD→PCM + DSP

```text
DSD source
  ↓
explicit policy DSD_TO_PCM
  ↓
DsdToPcmConverter
  ↓
PcmSignalFormat
  ↓
ProcessingGraph
  ↓
PEQ/FIR/etc
  ↓
Output planning
  ↓
DAC PCM
```

El Signal Path debe contener un nodo `DSD_TO_PCM` que impide cualquier presentación de
preservación DSD o bit-perfect respecto del DSD original.


---

# 120. ÁRBOL DE ARCHIVOS R11 — TARGET EXACTO, SIN COMPONENT EXPLOSION

R11 reemplaza los árboles anteriores cuando difieran. Se parte del árbol
**real** de `main @ aa8a8d3`, donde ya existen:

```text
src/michi/bootstrap/__init__.py
src/michi/domain/audio_output.py
src/michi/domain/audio_evidence.py
src/michi/domain/signal_truth.py
src/michi/application/output_session_service.py
src/michi/application/audio_output_planner.py
src/michi/application/audio_output_ports.py
src/michi/application/audio_output_profile_service.py
src/michi/application/audio_output_selection_coordinator.py
src/michi/application/dac_qualification_service.py
src/michi/infrastructure/audio_engines/gstreamer.py
src/michi/infrastructure/audio_output/direct_output_executor.py
src/michi/infrastructure/audio_output/strict_sink.py
src/michi/infrastructure/audio_output/runtime_inspector.py
src/michi/infrastructure/sqlite_settings.py
src/michi/infrastructure/sqlite_audio_output_repository.py
src/michi/presentation/audio_output_bridge.py
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioOutputPopup.qml
src/michi/presentation/qml/player/AudioEnginePopup.qml
```

## 120.1 Crear — CORE Phase2

```text
src/michi/domain/audio_signal.py
src/michi/domain/audio_processing.py
src/michi/domain/audio_processing_evidence.py

src/michi/application/audio_processing_ports.py
src/michi/application/effective_processing_graph.py
src/michi/application/processing_graph_compiler.py
src/michi/application/audio_processing_service.py

src/michi/infrastructure/audio_processing/__init__.py
src/michi/infrastructure/audio_processing/biquad.py
src/michi/infrastructure/audio_processing/gstreamer_capabilities.py
src/michi/infrastructure/audio_processing/gstreamer_graph_builder.py
src/michi/infrastructure/audio_processing/gstreamer_runtime.py
src/michi/infrastructure/audio_processing/ir_asset_store.py

src/michi/presentation/audio_processing_bridge.py
src/michi/presentation/signal_path_bridge.py

src/michi/presentation/qml/player/EqualizerPopup.qml
src/michi/presentation/qml/player/AdvancedEqualizerPopup.qml
src/michi/presentation/qml/player/SignalTruthPopup.qml
```

## 120.2 Crear — sólo cuando su fase se active

```text
# Managed PCM to a specific local DAC, never called Direct
src/michi/domain/managed_pcm_output.py
src/michi/application/managed_pcm_output_planner.py
src/michi/infrastructure/audio_output/managed_pcm_executor.py

# DSD / DoP
src/michi/domain/dsd_signal.py
src/michi/domain/dsd_output.py
src/michi/application/dsd_output_planner.py
src/michi/application/dop_output_planner.py
src/michi/infrastructure/dsd/...
src/michi/infrastructure/dop/...
```

## 120.3 Modificar — integración

```text
src/michi/bootstrap/__init__.py
src/michi/application/playback_service.py                 [sólo seams autorizados]
src/michi/application/output_session_service.py           [bounded integration]
src/michi/domain/signal_truth.py                          [parity-gated extension]
src/michi/infrastructure/audio_engines/gstreamer.py       [adapter seams only]
src/michi/infrastructure/sqlite_settings.py               [schema migration]
src/michi/presentation/audio_output_bridge.py
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioOutputPopup.qml
```

## 120.4 NO crear

Los nombres siguientes aparecieron en iteraciones anteriores y quedan retirados:

```text
DacQuickPopup.qml
AudioProcessingPopup.qml
SignalPathPopup.qml
src/michi/bootstrap.py
michi-convolver plugin name
michi-balance plugin name
michi-polarity plugin name
michi-channel-delay plugin name
michi-channel-map plugin name
michi-dither plugin name
```

Motivo:

```text
AudioOutputPopup.qml   ya es la superficie canónica de destinations.
EqualizerPopup.qml     es la quick surface de DSP.
SignalTruthPopup.qml   es la superficie que renderiza el Signal Path.
bootstrap/__init__.py  ya es el composition root real.
Backend factories      se descubren/proban; no se inventan por spec.
```

## 120.5 Regla de creación de componentes QML

No crear un componente nuevo por cada fila, badge o variante. Crear componente
sólo si se cumplen ambos criterios:

```text
consumer_count >= 2
AND
semantic_contract_is_shared = true
```

Caso contrario, mantener el bloque local al popup para reducir API, archivos,
tests y contexto.

---

# 121. `domain/audio_signal.py` — IMPLEMENTACIÓN DE REFERENCIA COMPLETA

> **KILLCRITIC CORRECTION:** la semántica PCM de esta sección sigue vigente, pero los campos/tasas DSD y DoP aquí mostrados quedan **superseded por §§210–217**. Ningún agente debe implementar DSD tomando `bit_rate_hz` como si fuera la tasa `rate` de GStreamer o ALSA.




```python
"""Family-neutral audio-signal domain for Michi Audio Phase 2.

Pure domain module. No Qt, GStreamer, ALSA, filesystem or application imports.
The types describe WHAT the signal is, never HOW a backend encodes it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


class SignalEncoding(Enum):
    PCM = "pcm"
    DSD = "dsd"
    DOP = "dop_carrier"
    UNKNOWN = "unknown"


class ChannelLayoutKind(Enum):
    MONO = "mono"
    STEREO = "stereo"
    SURROUND = "surround"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ChannelLayout:
    kind: ChannelLayoutKind
    positions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.positions and self.kind is not ChannelLayoutKind.UNKNOWN:
            raise ValueError("non-unknown channel layout requires positions")
        if len(set(self.positions)) != len(self.positions):
            raise ValueError("channel positions must be unique")

    @property
    def channels(self) -> int:
        return len(self.positions)

    @classmethod
    def stereo(cls) -> "ChannelLayout":
        return cls(ChannelLayoutKind.STEREO, ("FL", "FR"))

    @classmethod
    def unknown(cls) -> "ChannelLayout":
        return cls(ChannelLayoutKind.UNKNOWN, ())


@dataclass(frozen=True, slots=True)
class PcmSignalFormat:
    rate_hz: int
    transport_format: str
    significant_bits: int | None
    layout: ChannelLayout
    encoding: SignalEncoding = SignalEncoding.PCM

    def __post_init__(self) -> None:
        if self.rate_hz <= 0:
            raise ValueError("PCM rate_hz must be > 0")
        if not self.transport_format.strip():
            raise ValueError("PCM transport_format is required")
        if self.significant_bits is not None and self.significant_bits <= 0:
            raise ValueError("significant_bits must be positive")
        if self.layout.channels <= 0:
            raise ValueError("PCM layout must contain channels")


class DsdGrouping(Enum):
    U8 = "DSDU8"
    U16_LE = "DSDU16LE"
    U16_BE = "DSDU16BE"
    U32_LE = "DSDU32LE"
    U32_BE = "DSDU32BE"


class DsdBitOrder(Enum):
    NATIVE = "native"
    REVERSED_BYTES = "reversed_bytes"


@dataclass(frozen=True, slots=True)
class DsdSignalFormat:
    bit_rate_hz: int
    grouping: DsdGrouping
    layout: ChannelLayout
    bit_order: DsdBitOrder = DsdBitOrder.NATIVE
    encoding: SignalEncoding = SignalEncoding.DSD

    def __post_init__(self) -> None:
        if self.bit_rate_hz <= 0:
            raise ValueError("DSD bit_rate_hz must be > 0")
        if self.layout.channels <= 0:
            raise ValueError("DSD layout must contain channels")

    @property
    def dsd_multiplier(self) -> int | None:
        base = 2_822_400
        if self.bit_rate_hz % base:
            return None
        multiple = self.bit_rate_hz // base
        return multiple if multiple in {1, 2, 4, 8, 16} else None

    @property
    def rate_label(self) -> str:
        multiple = self.dsd_multiplier
        return f"DSD{64 * multiple}" if multiple is not None else f"DSD {self.bit_rate_hz} Hz"


class DopMarkerConvention(Enum):
    DOP_1_0 = "dop_1_0"


@dataclass(frozen=True, slots=True)
class DopCarrierFormat:
    """Transport framing for DSD-over-PCM.

    `carrier_*` fields describe the endpoint framing. This object MUST NOT be
    converted to PcmSignalFormat because the samples are not PCM audio.
    """

    source_dsd: DsdSignalFormat
    carrier_rate_hz: int
    carrier_transport_format: str
    carrier_container_bits: int
    payload_bits_per_channel_frame: int
    marker: DopMarkerConvention
    layout: ChannelLayout
    encoding: SignalEncoding = SignalEncoding.DOP

    def __post_init__(self) -> None:
        if self.carrier_rate_hz <= 0:
            raise ValueError("DoP carrier rate must be > 0")
        if self.carrier_container_bits < 24:
            raise ValueError("DoP carrier requires >= 24 container bits")
        if self.payload_bits_per_channel_frame != 16:
            raise ValueError("DoP v1 carries 16 DSD payload bits per channel frame")
        if self.layout != self.source_dsd.layout:
            raise ValueError("DoP cannot silently remix channels")


@dataclass(frozen=True, slots=True)
class UnknownSignalFormat:
    reason: str
    encoding: SignalEncoding = SignalEncoding.UNKNOWN

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("unknown signal requires a reason")


SignalFormat: TypeAlias = (
    PcmSignalFormat | DsdSignalFormat | DopCarrierFormat | UnknownSignalFormat
)


def signal_family(value: SignalFormat) -> SignalEncoding:
    return value.encoding


def channels_of(value: SignalFormat) -> int | None:
    if isinstance(value, UnknownSignalFormat):
        return None
    return value.layout.channels


def same_signal_family(left: SignalFormat, right: SignalFormat) -> bool:
    return signal_family(left) is signal_family(right)


def same_pcm_semantics(left: PcmSignalFormat, right: PcmSignalFormat) -> bool:
    return (
        left.rate_hz == right.rate_hz
        and left.transport_format == right.transport_format
        and left.significant_bits == right.significant_bits
        and left.layout == right.layout
    )


def same_dsd_semantics(left: DsdSignalFormat, right: DsdSignalFormat) -> bool:
    return (
        left.bit_rate_hz == right.bit_rate_hz
        and left.grouping is right.grouping
        and left.bit_order is right.bit_order
        and left.layout == right.layout
    )


def compact_signal_label(value: SignalFormat) -> str:
    if isinstance(value, PcmSignalFormat):
        rate = (
            f"{value.rate_hz // 1000} kHz"
            if value.rate_hz % 1000 == 0
            else f"{value.rate_hz / 1000:.1f} kHz"
        )
        bits = f"{value.significant_bits}-bit" if value.significant_bits else "? bit"
        return f"PCM · {rate} · {bits} · {value.layout.channels} ch"
    if isinstance(value, DsdSignalFormat):
        return f"{value.rate_label} · {value.layout.channels} ch"
    if isinstance(value, DopCarrierFormat):
        return (
            f"DoP · {value.source_dsd.rate_label} · carrier "
            f"{value.carrier_rate_hz / 1000:g} kHz"
        )
    return "Unknown signal"
```

## 121.1 Invariantes obligatorias de `audio_signal.py`

```text
SIG-01  DopCarrierFormat can never satisfy isinstance(..., PcmSignalFormat)
SIG-02  Native DSD preserves a first-class DsdSignalFormat
SIG-03  layout changes require an explicit transformation node
SIG-04  unknown precision stays None/UNKNOWN
SIG-05  DSD rate is stored as bit rate, not disguised PCM sample rate
SIG-06  a DoP carrier stores BOTH source DSD identity and carrier framing
SIG-07  user-visible labels are derived projections, never persisted identity
SIG-08  no backend enum (Gst/ALSA) leaks into this module
```


---

# 122. `domain/dsd.py` — POLÍTICA Y ESTADOS DSD



```python
"""DSD policy domain. Framework-free and transport-agnostic."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DsdPlaybackMode(Enum):
    AUTO = "auto"
    NATIVE = "native"
    DOP = "dop"
    PCM_CONVERSION = "pcm_conversion"
    DISABLED = "disabled"


class DsdRuntimeMode(Enum):
    NATIVE = "native"
    DOP = "dop"
    PCM_CONVERSION = "pcm_conversion"
    NOT_ACTIVE = "not_active"
    UNKNOWN = "unknown"


class DsdCapabilityState(Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    INCONCLUSIVE = "inconclusive"


class DsdToPcmQuality(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    REFERENCE = "reference"


@dataclass(frozen=True, slots=True)
class DsdPolicy:
    preferred_mode: DsdPlaybackMode = DsdPlaybackMode.AUTO
    allow_native: bool = True
    allow_dop: bool = False
    allow_pcm_conversion: bool = True
    conversion_quality: DsdToPcmQuality = DsdToPcmQuality.HIGH
    preserve_dsd_when_dsp_bypassed: bool = True

    def __post_init__(self) -> None:
        if self.preferred_mode is DsdPlaybackMode.DOP and not self.allow_dop:
            raise ValueError("preferred DoP requires allow_dop")
        if (
            self.preferred_mode is DsdPlaybackMode.PCM_CONVERSION
            and not self.allow_pcm_conversion
        ):
            raise ValueError("preferred PCM conversion requires allow_pcm_conversion")
        if self.preferred_mode is DsdPlaybackMode.NATIVE and not self.allow_native:
            raise ValueError("preferred native DSD requires allow_native")


@dataclass(frozen=True, slots=True)
class DsdCapabilityMatrix:
    native: DsdCapabilityState
    dop: DsdCapabilityState
    max_native_multiplier: int | None
    max_dop_multiplier: int | None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DsdPlaybackDecision:
    mode: DsdRuntimeMode
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    requires_reopen: bool
    requires_dsp_bypass: bool
    requires_dsd_to_pcm: bool


DSD_NATIVE_SELECTED = "DSD_NATIVE_SELECTED"
DSD_DOP_SELECTED = "DSD_DOP_SELECTED"
DSD_PCM_CONVERSION_SELECTED = "DSD_PCM_CONVERSION_SELECTED"
DSD_DISABLED = "DSD_DISABLED"
DSD_NATIVE_UNKNOWN = "DSD_NATIVE_UNKNOWN"
DSD_DOP_NOT_EXPLICITLY_ALLOWED = "DSD_DOP_NOT_EXPLICITLY_ALLOWED"
DSD_DSP_REQUIRES_PCM = "DSD_DSP_REQUIRES_PCM"
DSD_NO_SAFE_PATH = "DSD_NO_SAFE_PATH"
```


---

# 123. `domain/dop.py` — FRAMING DoP Y VECTORES CANÓNICOS



```python
"""DoP domain contracts and pure framing reference.

The pure packer is intentionally small and deterministic. Production may use a
native GStreamer element after ADR approval, but that implementation MUST pass
these byte-for-byte vectors.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


DOP_MARKERS = (0x05, 0xFA)


class DopByteOrder(Enum):
    PAYLOAD_LSB_FIRST = "payload_lsb_first"


@dataclass(frozen=True, slots=True)
class DopState:
    marker_phase: int = 0

    def __post_init__(self) -> None:
        if self.marker_phase not in (0, 1):
            raise ValueError("marker_phase must be 0 or 1")


@dataclass(frozen=True, slots=True)
class DopPacketResult:
    payload: bytes
    next_state: DopState
    source_bytes_consumed: int
    carrier_frames_written: int


class DopPackingError(ValueError):
    pass


def expected_carrier_rate(dsd_bit_rate_hz: int) -> int:
    """DoP v1: two DSD bytes (16 bits) per PCM-compatible channel frame."""
    if dsd_bit_rate_hz <= 0 or dsd_bit_rate_hz % 16:
        raise DopPackingError("DSD bit rate must be positive and divisible by 16")
    return dsd_bit_rate_hz // 16


def pack_dop_interleaved_stereo(
    left: bytes,
    right: bytes,
    *,
    state: DopState = DopState(),
    reverse_bits: bool = False,
) -> DopPacketResult:
    """Reference DoP v1 stereo packer.

    Input channels contain raw DSD bytes. Every two payload bytes per channel
    become one 24-bit-compatible DoP frame [payload0, payload1, marker].
    Marker phase toggles once per *multichannel frame*, not once per channel.
    """
    if len(left) != len(right):
        raise DopPackingError("stereo channel payload lengths differ")
    if len(left) % 2:
        raise DopPackingError("DoP packing requires pairs of DSD bytes")

    def bitrev8(value: int) -> int:
        value = ((value & 0xF0) >> 4) | ((value & 0x0F) << 4)
        value = ((value & 0xCC) >> 2) | ((value & 0x33) << 2)
        return ((value & 0xAA) >> 1) | ((value & 0x55) << 1)

    output = bytearray()
    marker_phase = state.marker_phase
    frames = 0
    for offset in range(0, len(left), 2):
        marker = DOP_MARKERS[marker_phase]
        for channel in (left, right):
            a = channel[offset]
            b = channel[offset + 1]
            if reverse_bits:
                a = bitrev8(a)
                b = bitrev8(b)
            output.extend((a, b, marker))
        marker_phase ^= 1
        frames += 1
    return DopPacketResult(
        payload=bytes(output),
        next_state=DopState(marker_phase),
        source_bytes_consumed=len(left) + len(right),
        carrier_frames_written=frames,
    )


DOP_VECTOR_01_LEFT = bytes([0x11, 0x22, 0x33, 0x44])
DOP_VECTOR_01_RIGHT = bytes([0x55, 0x66, 0x77, 0x88])
DOP_VECTOR_01_EXPECTED = bytes([
    0x11, 0x22, 0x05, 0x55, 0x66, 0x05,
    0x33, 0x44, 0xFA, 0x77, 0x88, 0xFA,
])
```

## 123.1 Invariantes DoP que TODO backend debe cumplir

```text
DOP-01 marker sequence is 0x05, 0xFA, 0x05, 0xFA ... per multichannel frame
DOP-02 every channel in the same frame uses the same marker phase
DOP-03 exactly two DSD payload bytes are preserved per channel frame
DOP-04 channel order is preserved
DOP-05 optional bit reversal is explicit evidence, never implicit
DOP-06 seek/restart defines marker reset semantics explicitly
DOP-07 buffer chunk boundaries cannot change the resulting byte stream
DOP-08 carrier rate = source DSD bit rate / 16 for DoP v1
DOP-09 carrier is never passed through PCM DSP
DOP-10 software-volume mutation on a DoP carrier is forbidden
DOP-11 remix/resample of a DoP carrier is forbidden
DOP-12 unknown DAC DoP capability refuses unless user-qualified policy explicitly allows it
```


---

# 124. `domain/audio_processing.py` — DOMINIO DSP COMPLETO



```python
"""Audiophile processing domain for Michi Audio Phase 2."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


class ProcessingNodeKind(Enum):
    PREAMP = "preamp"
    PARAMETRIC_EQ = "parametric_eq"
    FIR = "fir"
    CONVOLUTION = "convolution"
    BALANCE = "balance"
    POLARITY = "polarity"
    CHANNEL_DELAY = "channel_delay"
    CHANNEL_MAP = "channel_map"
    RESAMPLE = "resample"
    DITHER = "dither"
    CROSSFEED = "crossfeed"
    LOUDNESS = "loudness"
    # MIXER/LIMITER intentionally absent in R10 CORE.
    # Reserved names are not executable capability.


class BiquadType(Enum):
    PEAK = "peak"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    LOW_PASS = "low_pass"
    HIGH_PASS = "high_pass"
    NOTCH = "notch"
    BAND_PASS = "band_pass"
    ALL_PASS = "all_pass"


class ResampleQuality(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    REFERENCE = "reference"


class DitherMode(Enum):
    NONE = "none"
    TPDF = "tpdf"
    BACKEND_DEFAULT = "backend_default"


@dataclass(frozen=True, slots=True)
class PreampNode:
    node_id: str
    gain_db: float
    kind: ProcessingNodeKind = ProcessingNodeKind.PREAMP

    def __post_init__(self) -> None:
        if not -60.0 <= self.gain_db <= 24.0:
            raise ValueError("preamp gain outside safe configuration range")


@dataclass(frozen=True, slots=True)
class PeqBand:
    band_id: str
    filter_type: BiquadType
    frequency_hz: float
    q: float
    gain_db: float
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0:
            raise ValueError("PEQ frequency must be > 0")
        if self.q <= 0:
            raise ValueError("PEQ Q must be > 0")
        if not -36.0 <= self.gain_db <= 36.0:
            raise ValueError("PEQ gain outside supported design envelope")


@dataclass(frozen=True, slots=True)
class ParametricEqNode:
    node_id: str
    bands: tuple[PeqBand, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.PARAMETRIC_EQ

    def __post_init__(self) -> None:
        if len(self.bands) > 64:
            raise ValueError("initial GStreamer PEQ backend supports at most 64 bands")
        if len({band.band_id for band in self.bands}) != len(self.bands):
            raise ValueError("PEQ band ids must be unique")


@dataclass(frozen=True, slots=True)
class FirNode:
    node_id: str
    coefficients: tuple[float, ...]
    latency_samples: int
    normalize: bool = False
    kind: ProcessingNodeKind = ProcessingNodeKind.FIR

    def __post_init__(self) -> None:
        if not self.coefficients:
            raise ValueError("FIR requires coefficients")
        if self.latency_samples < 0:
            raise ValueError("FIR latency must be >= 0")


@dataclass(frozen=True, slots=True)
class ConvolutionNode:
    node_id: str
    ir_id: str
    channel_mapping: tuple[int, ...]
    gain_db: float = 0.0
    latency_hint_samples: int | None = None
    kind: ProcessingNodeKind = ProcessingNodeKind.CONVOLUTION

    def __post_init__(self) -> None:
        if not self.ir_id.strip():
            raise ValueError("convolution requires immutable IR id")
        if not self.channel_mapping:
            raise ValueError("convolution requires explicit channel mapping")


@dataclass(frozen=True, slots=True)
class BalanceNode:
    node_id: str
    left_gain_db: float
    right_gain_db: float
    kind: ProcessingNodeKind = ProcessingNodeKind.BALANCE


@dataclass(frozen=True, slots=True)
class PolarityNode:
    node_id: str
    inverted_channels: tuple[int, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.POLARITY


@dataclass(frozen=True, slots=True)
class ChannelDelayNode:
    node_id: str
    delays_us: tuple[int, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.CHANNEL_DELAY

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.delays_us):
            raise ValueError("channel delay cannot be negative")


@dataclass(frozen=True, slots=True)
class ChannelMapNode:
    node_id: str
    output_to_input: tuple[int | None, ...]
    kind: ProcessingNodeKind = ProcessingNodeKind.CHANNEL_MAP


@dataclass(frozen=True, slots=True)
class ResampleNode:
    node_id: str
    target_rate_hz: int
    quality: ResampleQuality
    kind: ProcessingNodeKind = ProcessingNodeKind.RESAMPLE

    def __post_init__(self) -> None:
        if self.target_rate_hz <= 0:
            raise ValueError("resample target rate must be > 0")


@dataclass(frozen=True, slots=True)
class DitherNode:
    node_id: str
    mode: DitherMode
    target_bits: int
    kind: ProcessingNodeKind = ProcessingNodeKind.DITHER

    def __post_init__(self) -> None:
        if self.target_bits not in {8, 16, 20, 24, 32}:
            raise ValueError("unsupported dither target precision")


@dataclass(frozen=True, slots=True)
class CrossfeedNode:
    node_id: str
    amount: float
    feed_delay_us: int
    kind: ProcessingNodeKind = ProcessingNodeKind.CROSSFEED

    def __post_init__(self) -> None:
        if not 0.0 <= self.amount <= 1.0:
            raise ValueError("crossfeed amount must be 0..1")
        if self.feed_delay_us < 0:
            raise ValueError("crossfeed delay cannot be negative")


@dataclass(frozen=True, slots=True)
class LoudnessNode:
    node_id: str
    reference_phon: float
    strength: float
    kind: ProcessingNodeKind = ProcessingNodeKind.LOUDNESS


ProcessingNode: TypeAlias = (
    PreampNode
    | ParametricEqNode
    | FirNode
    | ConvolutionNode
    | BalanceNode
    | PolarityNode
    | ChannelDelayNode
    | ChannelMapNode
    | ResampleNode
    | DitherNode
    | CrossfeedNode
    | LoudnessNode
)


@dataclass(frozen=True, slots=True)
class ProcessingGraph:
    graph_id: str
    revision: int
    nodes: tuple[ProcessingNode, ...]
    bypassed: bool = False

    def __post_init__(self) -> None:
        if self.revision < 0:
            raise ValueError("processing graph revision must be >= 0")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("processing node ids must be unique")

    @property
    def active_nodes(self) -> tuple[ProcessingNode, ...]:
        if self.bypassed:
            return ()
        return self.nodes


@dataclass(frozen=True, slots=True)
class ProcessingProfile:
    profile_id: str
    display_name: str
    graph: ProcessingGraph
    enabled: bool = True
    auto_headroom: bool = False
    target_device_id: str | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class CompiledProcessingNode:
    node_id: str
    kind: ProcessingNodeKind
    # Semantic strategy selected by the compiler. It is NOT assumed to be a
    # one-element GStreamer factory.
    backend_strategy: str
    required_factories: tuple[str, ...]
    properties: tuple[tuple[str, object], ...]
    expected_latency_samples: int


@dataclass(frozen=True, slots=True)
class CompiledProcessingPlan:
    plan_id: str
    graph_id: str
    graph_revision: int
    backend_id: str
    input_rate_hz: int
    input_channels: int
    output_rate_hz: int
    output_channels: int
    nodes: tuple[CompiledProcessingNode, ...]
    total_latency_samples: int
    changes_rate: bool
    changes_channels: bool
    changes_sample_values: bool
    changes_timing: bool
    changes_channel_assignment: bool
    evidence_refs: tuple[str, ...]
```

## 124.1 Semántica DSP obligatoria

```text
DSP-DOM-01 bypassed graph compiles to zero processing nodes
DSP-DOM-02 profile identity and graph revision are distinct
DSP-DOM-03 a graph edit creates a new revision; runtime never mutates a graph in-place
DSP-DOM-04 rate-changing nodes are explicit
DSP-DOM-05 channel-changing nodes are explicit
DSP-DOM-06 gain != 0 dB is signal mutation
DSP-DOM-07 dither is signal mutation and remains visible in Signal Path
DSP-DOM-08 convolution references an immutable IR asset id, never an arbitrary UI path
DSP-DOM-09 no PCM ProcessingGraph accepts DopCarrierFormat
DSP-DOM-10 no PCM ProcessingGraph accepts Native DSD unless policy inserted explicit DSD→PCM
```


---

# 125. `domain/audio_processing_evidence.py` — EVIDENCIA DSP



```python
"""Runtime processing evidence; immutable and generation-scoped."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_signal import SignalFormat
from michi.domain.audio_processing import ProcessingNodeKind


class ProcessingActivity(Enum):
    NOT_PRESENT = "not_present"
    BYPASSED = "bypassed"
    PASS_THROUGH = "pass_through"
    ACTIVE = "active"
    UNKNOWN = "unknown"
    NOT_OBSERVABLE = "not_observable"


@dataclass(frozen=True, slots=True)
class ProcessingNodeRuntimeEvidence:
    graph_id: str
    graph_revision: int
    execution_generation: int
    node_id: str
    kind: ProcessingNodeKind
    activity: ProcessingActivity
    input_signal: SignalFormat | None
    output_signal: SignalFormat | None
    latency_samples: int | None
    backend_strategy: str | None
    observed_factories: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProcessingRuntimeSnapshot:
    graph_id: str
    graph_revision: int
    execution_generation: int
    backend_id: str
    input_signal: SignalFormat | None
    output_signal: SignalFormat | None
    nodes: tuple[ProcessingNodeRuntimeEvidence, ...]
    graph_bypassed: bool
    graph_inspection_complete: bool
    xruns: int
    measured_latency_frames: int | None
    peak_dbfs: float | None
    clipped_samples_observed: bool | None

    @property
    def active_nodes(self) -> tuple[ProcessingNodeRuntimeEvidence, ...]:
        return tuple(
            node for node in self.nodes
            if node.activity is ProcessingActivity.ACTIVE
        )

    @property
    def is_bypassed(self) -> bool:
        # R10: bypass is an explicit runtime/configuration fact. UNKNOWN,
        # NOT_OBSERVABLE or an empty evidence list never silently becomes BYPASSED.
        return self.graph_bypassed

    @property
    def has_observed_active_processing(self) -> bool:
        return bool(self.active_nodes)
```


---

# 126. `domain/evidence.py` — PROVENANCE MULTIFUENTE CERRADA



```python
"""Generic provenance primitives for Phase 2 enrichment.

These are NOT a replacement for V3.5 CapabilityEvidence. They model resolved
claims that combine multiple evidence records for presentation/knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


class EvidenceOrigin(Enum):
    SYSFS = "sysfs"
    USB_DESCRIPTOR = "usb_descriptor"
    ALSA = "alsa"
    UDEV_HWDB = "udev_hwdb"
    USB_IDS = "usb_ids"
    KERNEL_KNOWLEDGE = "kernel_knowledge"
    MICHI_KB = "michi_kb"
    PHYSICAL_QUALIFICATION = "physical_qualification"
    RUNTIME = "runtime"
    MANUFACTURER_DECLARED = "manufacturer_declared"


class EvidenceConfidence(Enum):
    AUTHORITATIVE = "authoritative"
    STRONG = "strong"
    CORROBORATED = "corroborated"
    WEAK = "weak"
    UNKNOWN = "unknown"


class EvidenceResolution(Enum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"
    STALE = "stale"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class EvidenceRecord(Generic[T]):
    evidence_id: str
    origin: EvidenceOrigin
    value: T
    confidence: EvidenceConfidence
    observed_at_ns: int | None = None
    generation: int | None = None
    environment_fingerprint: str | None = None
    source_version: str | None = None
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedEvidenceValue(Generic[T]):
    value: T | None
    resolution: EvidenceResolution
    evidence: tuple[EvidenceRecord[T], ...]
    explanation_code: str

    @property
    def is_known(self) -> bool:
        return self.resolution is EvidenceResolution.RESOLVED and self.value is not None


class ConfigurationOrigin(Enum):
    DEFAULT = "default"
    RECOMMENDED_PROFILE = "recommended_profile"
    USER = "user"
    MIGRATED = "migrated"


@dataclass(frozen=True, slots=True)
class ConfiguredValue(Generic[T]):
    value: T
    origin: ConfigurationOrigin
    differs_from_recommended: bool


def resolve_exact_agreement(records: tuple[EvidenceRecord[T], ...]) -> ResolvedEvidenceValue[T]:
    if not records:
        return ResolvedEvidenceValue(None, EvidenceResolution.UNKNOWN, (), "NO_EVIDENCE")
    values = {record.value for record in records}
    if len(values) != 1:
        return ResolvedEvidenceValue(None, EvidenceResolution.CONFLICTED, records, "EVIDENCE_CONFLICT")
    return ResolvedEvidenceValue(next(iter(values)), EvidenceResolution.RESOLVED, records, "EXACT_AGREEMENT")
```


---

# 127. `domain/signal_path.py` — GRAFO DE SEÑAL IMPLEMENTABLE



```python
"""Structured, generation-safe Signal Path graph."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_signal import SignalFormat


class SignalStage(Enum):
    SOURCE_CONTAINER = "source_container"
    DECODED_SOURCE = "decoded_source"
    ENGINE = "engine"
    PROCESSING = "processing"
    DSD_TO_PCM = "dsd_to_pcm"
    DOP_PACKER = "dop_packer"
    VOLUME = "volume"
    TRANSPORT = "transport"
    DEVICE_NEGOTIATION = "device_negotiation"
    PHYSICAL_LINK = "physical_link"
    NETWORK_TRANSPORT = "network_transport"
    NETWORK_ENDPOINT = "network_endpoint"
    DEVICE = "device"


class TransformationState(Enum):
    NOT_PRESENT = "not_present"
    PRESENT_PASS_THROUGH = "present_pass_through"
    ACTIVE = "active"
    PRESENT_STATE_UNKNOWN = "present_state_unknown"
    NOT_OBSERVABLE = "not_observable"
    NOT_APPLICABLE = "not_applicable"


class ObservabilityState(Enum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    NOT_OBSERVABLE = "not_observable"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONFLICTED = "conflicted"


class SignalPathLifecycle(Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"
    TERMINATED = "terminated"


@dataclass(frozen=True, slots=True)
class SignalPathIdentity:
    session_id: str
    plan_id: str | None
    execution_generation: int
    binding_generation: int | None
    processing_graph_id: str | None
    processing_graph_revision: int | None


@dataclass(frozen=True, slots=True)
class SignalEvidenceRef:
    evidence_id: str
    origin: str
    summary: str


@dataclass(frozen=True, slots=True)
class SignalNode:
    node_id: str
    stage: SignalStage
    provider: str
    input_signal: SignalFormat | None
    output_signal: SignalFormat | None
    transformation: TransformationState
    observability: ObservabilityState
    evidence: tuple[SignalEvidenceRef, ...]
    generation: int
    title: str
    summary: str


@dataclass(frozen=True, slots=True)
class SignalEdge:
    source_node_id: str
    target_node_id: str


@dataclass(frozen=True, slots=True)
class SignalPathSnapshot:
    identity: SignalPathIdentity
    nodes: tuple[SignalNode, ...]
    edges: tuple[SignalEdge, ...]
    lifecycle: SignalPathLifecycle
    revision: int
    path_verdict: str
    proof_state: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        ids = {node.node_id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("signal path node ids must be unique")
        for edge in self.edges:
            if edge.source_node_id not in ids or edge.target_node_id not in ids:
                raise ValueError("signal path edge references unknown node")

    def node(self, node_id: str) -> SignalNode | None:
        return next((node for node in self.nodes if node.node_id == node_id), None)
```

## 127.1 Taxonomía visual derivada, no persistida

```text
path_verdict examples:
  DIRECT
  NATIVE_DSD
  DOP
  PROCESSED
  RESAMPLED
  REMIXED
  DSD_TO_PCM
  SHARED
  UNKNOWN
  CONTRADICTED

proof_state examples (M11.5-owned):
  VERIFIED
  UNVERIFIED
  BROKEN
  NOT_APPLICABLE
```

Nunca fusionar ambos ejes en un único enum.


---

# 128. CONTRATO DE COMPATIBILIDAD CON V3.5 — ADAPTER, NO BIG-BANG REWRITE

No se reemplaza inmediatamente `PcmTuple`, `DecodedSourceSignal` ni `OutputPlan`. La migración
se hace en dos etapas para preservar los tests sellados.

```text
Stage A
V3.5 PCM types stay intact
        ↓
PcmSignalFormatAdapter
        ↓
Phase 2 signal algebra

Stage B, only after parity gates
family-neutral OutputSignalPlan
        ├── PcmOutputPlan
        ├── NativeDsdOutputPlan
        └── DopOutputPlan
```

Contrato del adapter inicial:

```python
from michi.domain.audio_evidence import DecodedSourceSignal, PcmTuple
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat


def pcm_tuple_to_signal(value: PcmTuple) -> PcmSignalFormat:
    return PcmSignalFormat(
        rate_hz=value.rate_hz,
        transport_format=value.transport_format,
        significant_bits=value.significant_bits,
        layout=ChannelLayout.stereo() if value.channels == 2 else ChannelLayout(
            kind=ChannelLayoutKind.CUSTOM,
            positions=tuple(f"CH{index + 1}" for index in range(value.channels)),
        ),
    )


def decoded_pcm_to_signal(value: DecodedSourceSignal) -> PcmSignalFormat:
    if value.encoding.strip().upper() != "PCM":
        raise ValueError("decoded source is not PCM")
    positions = value.channel_positions or tuple(
        "FL" if index == 0 else "FR" if index == 1 else f"CH{index + 1}"
        for index in range(value.channels)
    )
    return PcmSignalFormat(
        rate_hz=value.rate_hz,
        transport_format="UNKNOWN_RUNTIME_CONTAINER",
        significant_bits=value.significant_bits,
        layout=ChannelLayout(
            ChannelLayoutKind.STEREO if value.channels == 2 else ChannelLayoutKind.CUSTOM,
            tuple(positions),
        ),
    )
```

## 128.1 Gate de paridad PCM

Antes de permitir DSD/DSP productivo:

```text
PARITY-PCM-01 every existing Stable PCM Direct fixture produces same OutputPlan
PARITY-PCM-02 strict sink caps unchanged for S16_LE and S32_LE
PARITY-PCM-03 existing SignalTruth verdicts unchanged with Phase2 disabled
PARITY-PCM-04 full DAC V3.5 suite remains green
PARITY-PCM-05 startup/reconnect semantics unchanged
PARITY-PCM-06 volume authority unchanged
PARITY-PCM-07 no new polling
PARITY-PCM-08 wheel/install smoke remains green
```


---

# 129. `application/audio_processing_ports.py` — PUERTOS DE EJECUCIÓN DSP



```python
"""Application ports for Audio Phase 2 processing.

Ports express Michi semantics only. Concrete GStreamer/Camilla/PipeWire types
never cross this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from michi.domain.audio_processing import CompiledProcessingPlan
from michi.domain.audio_processing_evidence import ProcessingRuntimeSnapshot
from michi.domain.audio_signal import SignalFormat


@dataclass(frozen=True, slots=True)
class ProcessingRuntimeHandle:
    handle_id: str
    graph_id: str
    graph_revision: int
    execution_generation: int


@dataclass(frozen=True, slots=True)
class ProcessingInstallResult:
    handle: ProcessingRuntimeHandle
    accepted_input: SignalFormat
    expected_output: SignalFormat
    expected_latency_samples: int


@dataclass(frozen=True, slots=True)
class ProcessingCommitResult:
    handle: ProcessingRuntimeHandle
    active_revision: int


class ProcessingRuntimeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@runtime_checkable
class AudioProcessingRuntimePort(Protocol):
    @property
    def backend_id(self) -> str: ...

    def prepare(
        self,
        plan: CompiledProcessingPlan,
        input_signal: SignalFormat,
        *,
        execution_generation: int,
    ) -> ProcessingInstallResult: ...

    def preroll(self, handle: ProcessingRuntimeHandle) -> ProcessingRuntimeSnapshot: ...

    def commit(self, handle: ProcessingRuntimeHandle) -> ProcessingCommitResult: ...

    def abort(self, handle: ProcessingRuntimeHandle, reason: str) -> None: ...

    def replace(
        self,
        current: ProcessingRuntimeHandle,
        plan: CompiledProcessingPlan,
        input_signal: SignalFormat,
        *,
        execution_generation: int,
    ) -> ProcessingInstallResult: ...

    def bypass(self, handle: ProcessingRuntimeHandle) -> None: ...

    def release(self, reason: str) -> None: ...

    def snapshot(self) -> ProcessingRuntimeSnapshot | None: ...


@runtime_checkable
class ImpulseResponseStorePort(Protocol):
    def load_float32_mono(self, ir_id: str) -> tuple[float, ...]: ...

    def metadata(self, ir_id: str) -> dict[str, object]: ...


@runtime_checkable
class ProcessingProfileRepositoryPort(Protocol):
    def load_profiles(self): ...
    def save_profile(self, profile) -> None: ...
    def delete_profile(self, profile_id: str) -> None: ...
    def load_selected_profile_id(self) -> str | None: ...
    def save_selected_profile_id(self, profile_id: str | None) -> None: ...
```


---

# 130. `application/processing_graph_compiler.py` — COMPILADOR DETERMINISTA R10

> **R11 CORRECTION:** el compilador selecciona estrategias semánticas; nunca
> inventa factories. La documentación oficial de GStreamer sí define
> `equalizer-nbands` como ecualizador plenamente paramétrico de 1–64 bandas con
> `freq`, `bandwidth` y `gain`, por lo que es candidato sólido para Graphic EQ y
> peak-band EQ. Eso **no prueba** por sí solo la familia completa de filtros RBJ
> de Michi (shelves/LP/HP/notch/band-pass/all-pass). Para esa familia el candidato
> inicial es una cascada `audioiirfilter`, capability-gated. R11 conserva el
> compilador por estrategias y corrige la negación excesiva de R10.

```python
"""Compile ProcessingGraph into a deterministic backend-strategy plan."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from michi.domain.audio_processing import (
    BalanceNode,
    BiquadType,
    ChannelDelayNode,
    ChannelMapNode,
    CompiledProcessingNode,
    CompiledProcessingPlan,
    ConvolutionNode,
    CrossfeedNode,
    DitherMode,
    DitherNode,
    FirNode,
    LoudnessNode,
    ParametricEqNode,
    PolarityNode,
    PreampNode,
    ProcessingGraph,
    ProcessingNodeKind,
    ResampleNode,
)
from michi.domain.audio_signal import PcmSignalFormat


class ProcessingCompilationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ProcessingBackendCapabilities:
    """Probe result supplied by infrastructure; never guessed by QML/compiler."""
    backend_id: str
    strategies: frozenset[str]
    factories: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProcessingCompileFacts:
    backend: ProcessingBackendCapabilities
    input_signal: PcmSignalFormat
    graph: ProcessingGraph
    ir_metadata: tuple[tuple[str, int, int, str], ...] = ()
    # ir_id, rate_hz, channels, sha256


STRATEGY_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "gain": ("volume",),
    # Legacy research showed audioiirfilter is a viable PEQ primitive; R10 does
    # NOT assume it works until F05 probes the installed runtime.
    "biquad_cascade": ("audioiirfilter",),
    "fir": ("audiofirfilter",),
    "resample": ("audioresample",),
    # The remaining strategies require a deliberately implemented adapter.
    "convolution": (),
    "balance": (),
    "polarity": (),
    "channel_delay": (),
    "channel_map": (),
    "dither": (),
    "crossfeed": (),
    "loudness": (),
}


class ProcessingGraphCompiler:
    """Pure compiler: domain facts in, immutable strategy plan out."""

    def compile(self, facts: ProcessingCompileFacts) -> CompiledProcessingPlan:
        graph = facts.graph
        signal = facts.input_signal

        if graph.bypassed or not graph.nodes:
            return CompiledProcessingPlan(
                plan_id=self._plan_id(facts, ()),
                graph_id=graph.graph_id,
                graph_revision=graph.revision,
                backend_id=facts.backend.backend_id,
                input_rate_hz=signal.rate_hz,
                input_channels=signal.layout.channels,
                output_rate_hz=signal.rate_hz,
                output_channels=signal.layout.channels,
                nodes=(),
                total_latency_samples=0,
                changes_rate=False,
                changes_channels=False,
                changes_sample_values=False,
                changes_timing=False,
                changes_channel_assignment=False,
                evidence_refs=("PROCESSING_BYPASSED",),
            )

        current_rate = signal.rate_hz
        current_channels = signal.layout.channels
        compiled_nodes: list[CompiledProcessingNode] = []
        changes_rate = False
        changes_channels = False
        changes_values = False
        changes_timing = False
        changes_channel_assignment = False
        latency = 0

        for node in graph.nodes:
            self._validate_node_for_signal(
                node, current_rate=current_rate,
                current_channels=current_channels,
            )
            strategy, props, node_latency = self._compile_semantics(
                node, current_rate=current_rate,
                current_channels=current_channels,
                ir_metadata=facts.ir_metadata,
            )
            self._require_strategy(facts.backend, strategy)
            required = STRATEGY_REQUIREMENTS[strategy]
            missing = tuple(
                factory for factory in required
                if factory not in facts.backend.factories
            )
            if missing:
                raise ProcessingCompilationError(
                    "DSP_FACTORY_UNAVAILABLE",
                    f"{strategy}: missing {missing!r}",
                )

            compiled_nodes.append(
                CompiledProcessingNode(
                    node_id=node.node_id,
                    kind=node.kind,
                    backend_strategy=strategy,
                    required_factories=required,
                    properties=tuple(props),
                    expected_latency_samples=node_latency,
                )
            )
            latency += node_latency

            # Mutation semantics are evaluated against the signal ENTERING the
            # node, before current_rate/current_channels are advanced.
            changes_values |= self._changes_values(
                node,
                current_rate=current_rate,
                current_channels=current_channels,
            )
            changes_timing |= isinstance(node, ChannelDelayNode) and any(
                value != 0 for value in node.delays_us
            )
            if isinstance(node, ChannelMapNode):
                identity = tuple(range(current_channels))
                changes_channel_assignment |= node.output_to_input != identity

            if isinstance(node, ResampleNode):
                changes_rate |= node.target_rate_hz != current_rate
                current_rate = node.target_rate_hz
            if isinstance(node, ChannelMapNode):
                next_channels = len(node.output_to_input)
                changes_channels |= next_channels != current_channels
                current_channels = next_channels

        nodes = tuple(compiled_nodes)
        return CompiledProcessingPlan(
            plan_id=self._plan_id(facts, nodes),
            graph_id=graph.graph_id,
            graph_revision=graph.revision,
            backend_id=facts.backend.backend_id,
            input_rate_hz=signal.rate_hz,
            input_channels=signal.layout.channels,
            output_rate_hz=current_rate,
            output_channels=current_channels,
            nodes=nodes,
            total_latency_samples=latency,
            changes_rate=changes_rate,
            changes_channels=changes_channels,
            changes_sample_values=changes_values,
            changes_timing=changes_timing,
            changes_channel_assignment=changes_channel_assignment,
            evidence_refs=(f"graph:{graph.graph_id}:{graph.revision}",),
        )

    @staticmethod
    def _require_strategy(
        backend: ProcessingBackendCapabilities,
        strategy: str,
    ) -> None:
        if strategy not in backend.strategies:
            raise ProcessingCompilationError(
                "DSP_STRATEGY_UNAVAILABLE",
                f"{backend.backend_id!r} does not implement {strategy!r}",
            )

    @staticmethod
    def _validate_node_for_signal(
        node,
        *,
        current_rate: int,
        current_channels: int,
    ) -> None:
        if isinstance(node, ParametricEqNode):
            nyquist = current_rate / 2.0
            for band in node.bands:
                if band.enabled and not (0.0 < band.frequency_hz < nyquist):
                    raise ProcessingCompilationError(
                        "DSP_PEQ_NYQUIST_VIOLATION",
                        f"{band.band_id}: {band.frequency_hz} >= Nyquist {nyquist}",
                    )

        if isinstance(node, ChannelMapNode):
            for source_index in node.output_to_input:
                if source_index is not None and not (0 <= source_index < current_channels):
                    raise ProcessingCompilationError(
                        "DSP_CHANNEL_MAP_INVALID",
                        repr(node.output_to_input),
                    )

    @staticmethod
    def _compile_semantics(
        node,
        *,
        current_rate: int,
        current_channels: int,
        ir_metadata,
    ):
        if isinstance(node, PreampNode):
            return "gain", (("gain-db", node.gain_db),), 0

        if isinstance(node, ParametricEqNode):
            # Keep typed PEQ semantics. Infrastructure computes/normalizes
            # coefficients for the proven backend; compiler never fabricates
            # GObject child-property syntax.
            bands = tuple(
                (
                    band.band_id,
                    band.filter_type.value,
                    band.frequency_hz,
                    band.q,
                    band.gain_db,
                    band.enabled,
                )
                for band in node.bands
            )
            return "biquad_cascade", (("bands", bands), ("rate-hz", current_rate)), 0

        if isinstance(node, FirNode):
            return "fir", (
                ("coefficients", node.coefficients),
                ("normalize", node.normalize),
            ), node.latency_samples

        if isinstance(node, ConvolutionNode):
            ir = next((item for item in ir_metadata if item[0] == node.ir_id), None)
            if ir is None:
                raise ProcessingCompilationError("DSP_IR_UNKNOWN", node.ir_id)
            _, ir_rate, ir_channels, ir_sha256 = ir
            if ir_rate != current_rate:
                raise ProcessingCompilationError(
                    "DSP_IR_RATE_MISMATCH",
                    f"{ir_rate} != {current_rate}",
                )
            return "convolution", (
                ("ir-id", node.ir_id),
                ("ir-sha256", ir_sha256),
                ("ir-channels", ir_channels),
                ("channel-map", node.channel_mapping),
                ("gain-db", node.gain_db),
            ), node.latency_hint_samples or 0

        if isinstance(node, BalanceNode):
            return "balance", (
                ("left-db", node.left_gain_db),
                ("right-db", node.right_gain_db),
            ), 0

        if isinstance(node, PolarityNode):
            return "polarity", (("channels", node.inverted_channels),), 0

        if isinstance(node, ChannelDelayNode):
            latency = max(
                (round(current_rate * value / 1_000_000) for value in node.delays_us),
                default=0,
            )
            return "channel_delay", (("delays-us", node.delays_us),), latency

        if isinstance(node, ChannelMapNode):
            return "channel_map", (("output-to-input", node.output_to_input),), 0

        if isinstance(node, ResampleNode):
            return "resample", (
                ("target-rate", node.target_rate_hz),
                ("quality", node.quality.value),
            ), 0

        if isinstance(node, DitherNode):
            return "dither", (
                ("mode", node.mode.value),
                ("target-bits", node.target_bits),
            ), 0

        if isinstance(node, CrossfeedNode):
            return "crossfeed", (
                ("amount", node.amount),
                ("feed-delay-us", node.feed_delay_us),
            ), 0

        if isinstance(node, LoudnessNode):
            return "loudness", (
                ("reference-phon", node.reference_phon),
                ("strength", node.strength),
            ), 0

        raise ProcessingCompilationError(
            "DSP_NODE_UNSUPPORTED", type(node).__name__
        )

    @staticmethod
    def _changes_values(
        node,
        *,
        current_rate: int,
        current_channels: int,
    ) -> bool:
        """Conservative, exhaustive mutation semantics for Signal Truth."""
        if isinstance(node, PreampNode):
            return node.gain_db != 0.0

        if isinstance(node, ParametricEqNode):
            for band in node.bands:
                if not band.enabled:
                    continue
                if band.filter_type in {
                    BiquadType.LOW_PASS,
                    BiquadType.HIGH_PASS,
                    BiquadType.NOTCH,
                    BiquadType.BAND_PASS,
                    BiquadType.ALL_PASS,
                }:
                    return True
                if band.gain_db != 0.0:
                    return True
            return False

        if isinstance(node, FirNode):
            # Never guess that an arbitrary kernel is mathematically identity.
            return True

        if isinstance(node, ConvolutionNode):
            return True

        if isinstance(node, BalanceNode):
            return node.left_gain_db != 0.0 or node.right_gain_db != 0.0

        if isinstance(node, PolarityNode):
            return bool(node.inverted_channels)

        if isinstance(node, ChannelDelayNode):
            # Timing mutation is reported separately by `changes_timing`.
            return False

        if isinstance(node, ChannelMapNode):
            # Routing/channel assignment mutation is reported separately.
            return False

        if isinstance(node, ResampleNode):
            return node.target_rate_hz != current_rate

        if isinstance(node, DitherNode):
            return node.mode is not DitherMode.NONE

        if isinstance(node, CrossfeedNode):
            return node.amount > 0.0

        if isinstance(node, LoudnessNode):
            return node.strength > 0.0

        # Fail closed for any future node not added to this exhaustive table.
        return True

    @staticmethod
    def _plan_id(facts, nodes) -> str:
        payload = repr((
            facts.backend.backend_id,
            facts.input_signal,
            facts.graph.graph_id,
            facts.graph.revision,
            nodes,
        )).encode("utf-8")
        return "dsp:" + hashlib.sha256(payload).hexdigest()[:24]
```

## 130.1 Backend strategy admission gate

No `ProcessingNodeKind` queda implementado porque aparezca en el enum.

```text
domain node
-> compiler strategy
-> backend capability probe
-> infrastructure strategy adapter
-> runtime readback
-> falsification test
-> Signal Truth
-> UI capability
```

Si falta cualquier capa:

```text
DSP_STRATEGY_UNAVAILABLE
```

y el control correspondiente permanece oculto/deshabilitado con causa real.

## 130.2 Validaciones adicionales

```text
Nyquist validation before compile
deterministic PEQ ordering
no silent frequency clamp
no unknown filter -> identity fallback
channel-map indices validated
FIR NaN/Inf + bounded coefficient count
convolution immutable IR hash verified
explicit resampling only
no PCM graph accepts Native DSD / DoP carrier
no auto-headroom claim without algorithm/version
no limiter/mixer until typed end-to-end support exists
```

---

# 131. `application/audio_processing_service.py` — OWNER Y TRANSACCIÓN DSP



```python
"""Application owner for selected processing profile and runtime graph."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable

from michi.application.audio_processing_ports import (
    AudioProcessingRuntimePort,
    ProcessingRuntimeError,
    ProcessingRuntimeHandle,
)
from michi.application.processing_graph_compiler import (
    ProcessingCompileFacts,
    ProcessingGraphCompiler,
)
from michi.domain.audio_processing import ProcessingProfile
from michi.domain.audio_signal import PcmSignalFormat


class ProcessingLifecycle(Enum):
    IDLE = "idle"
    PREPARING = "preparing"
    PREROLLING = "prerolling"
    READY = "ready"
    ACTIVE = "active"
    RECONFIGURING = "reconfiguring"
    BYPASSED = "bypassed"
    FAILED = "failed"
    RELEASING = "releasing"


@dataclass(frozen=True, slots=True)
class AudioProcessingState:
    selected_profile_id: str | None = None
    active_profile_id: str | None = None
    active_graph_id: str | None = None
    active_graph_revision: int | None = None
    lifecycle: ProcessingLifecycle = ProcessingLifecycle.IDLE
    bypassed: bool = True
    error_code: str | None = None
    latency_samples: int = 0


class AudioProcessingService:
    def __init__(
        self,
        *,
        profiles,
        compiler: ProcessingGraphCompiler,
        runtime: AudioProcessingRuntimePort,
        available_factories: Callable[[], frozenset[str]],
        ir_metadata: Callable[[], tuple[tuple[str, int, int], ...]],
    ) -> None:
        self._profiles = profiles
        self._compiler = compiler
        self._runtime = runtime
        self._available_factories = available_factories
        self._ir_metadata = ir_metadata
        self._state = AudioProcessingState(
            selected_profile_id=profiles.load_selected_profile_id()
        )
        self._handle: ProcessingRuntimeHandle | None = None
        self._generation = 0
        self._subscribers: list[Callable[[], None]] = []

    @property
    def state(self) -> AudioProcessingState:
        return self._state

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def select_profile(self, profile_id: str | None) -> None:
        if profile_id is not None and self._profile(profile_id) is None:
            raise ProcessingRuntimeError("DSP_PROFILE_UNKNOWN", profile_id)
        self._profiles.save_selected_profile_id(profile_id)
        self._state = replace(self._state, selected_profile_id=profile_id)
        self._notify()

    def prepare_for_pcm(self, signal: PcmSignalFormat) -> None:
        profile = self._profile(self._state.selected_profile_id)
        if profile is None or not profile.enabled or profile.graph.bypassed:
            self._release_runtime("processing bypassed")
            self._state = replace(
                self._state,
                active_profile_id=None,
                active_graph_id=None,
                active_graph_revision=None,
                lifecycle=ProcessingLifecycle.BYPASSED,
                bypassed=True,
                error_code=None,
                latency_samples=0,
            )
            self._notify()
            return

        self._generation += 1
        generation = self._generation
        plan = self._compiler.compile(
            ProcessingCompileFacts(
                backend_id=self._runtime.backend_id,
                input_signal=signal,
                graph=profile.graph,
                available_factories=self._available_factories(),
                ir_metadata=self._ir_metadata(),
            )
        )
        self._state = replace(
            self._state,
            lifecycle=ProcessingLifecycle.PREPARING,
            error_code=None,
        )
        self._notify()
        try:
            result = self._runtime.prepare(
                plan, signal, execution_generation=generation
            )
            self._state = replace(self._state, lifecycle=ProcessingLifecycle.PREROLLING)
            self._notify()
            evidence = self._runtime.preroll(result.handle)
            self._validate_preroll(plan, evidence, generation)
            committed = self._runtime.commit(result.handle)
        except Exception as exc:
            with _suppress_runtime_error():
                if 'result' in locals():
                    self._runtime.abort(result.handle, "prepare failed")
            code = getattr(exc, "code", "DSP_PREPARE_FAILED")
            self._state = replace(
                self._state,
                lifecycle=ProcessingLifecycle.FAILED,
                error_code=code,
            )
            self._notify()
            raise

        self._handle = committed.handle
        self._state = AudioProcessingState(
            selected_profile_id=profile.profile_id,
            active_profile_id=profile.profile_id,
            active_graph_id=plan.graph_id,
            active_graph_revision=plan.graph_revision,
            lifecycle=ProcessingLifecycle.ACTIVE,
            bypassed=False,
            error_code=None,
            latency_samples=plan.total_latency_samples,
        )
        self._notify()

    def reconfigure(self, profile: ProcessingProfile, signal: PcmSignalFormat) -> None:
        """Atomic live reconfiguration. Old graph remains authoritative until commit."""
        current = self._handle
        if current is None:
            self._profiles.save_profile(profile)
            self.select_profile(profile.profile_id)
            self.prepare_for_pcm(signal)
            return
        self._generation += 1
        generation = self._generation
        plan = self._compiler.compile(
            ProcessingCompileFacts(
                backend_id=self._runtime.backend_id,
                input_signal=signal,
                graph=profile.graph,
                available_factories=self._available_factories(),
                ir_metadata=self._ir_metadata(),
            )
        )
        self._state = replace(self._state, lifecycle=ProcessingLifecycle.RECONFIGURING)
        self._notify()
        candidate = None
        try:
            candidate = self._runtime.replace(
                current, plan, signal, execution_generation=generation
            )
            evidence = self._runtime.preroll(candidate.handle)
            self._validate_preroll(plan, evidence, generation)
            committed = self._runtime.commit(candidate.handle)
        except Exception:
            if candidate is not None:
                with _suppress_runtime_error():
                    self._runtime.abort(candidate.handle, "reconfigure failed")
            self._state = replace(self._state, lifecycle=ProcessingLifecycle.ACTIVE)
            self._notify()
            raise
        self._profiles.save_profile(profile)
        self._handle = committed.handle
        self._state = replace(
            self._state,
            active_profile_id=profile.profile_id,
            active_graph_id=plan.graph_id,
            active_graph_revision=plan.graph_revision,
            lifecycle=ProcessingLifecycle.ACTIVE,
            bypassed=False,
            error_code=None,
            latency_samples=plan.total_latency_samples,
        )
        self._notify()

    def set_bypassed(self, bypassed: bool) -> None:
        if bypassed:
            if self._handle is not None:
                self._runtime.bypass(self._handle)
            self._state = replace(
                self._state,
                lifecycle=ProcessingLifecycle.BYPASSED,
                bypassed=True,
            )
            self._notify()
            return
        raise ProcessingRuntimeError(
            "DSP_UNBYPASS_REQUIRES_SIGNAL",
            "unbypass requires compile/prepare with the current PCM signal",
        )

    def release(self, reason: str) -> None:
        self._release_runtime(reason)
        self._state = replace(
            self._state,
            active_profile_id=None,
            active_graph_id=None,
            active_graph_revision=None,
            lifecycle=ProcessingLifecycle.IDLE,
            bypassed=True,
            latency_samples=0,
        )
        self._notify()

    def _profile(self, profile_id: str | None) -> ProcessingProfile | None:
        if profile_id is None:
            return None
        return next(
            (item for item in self._profiles.load_profiles() if item.profile_id == profile_id),
            None,
        )

    def _release_runtime(self, reason: str) -> None:
        if self._handle is None:
            return
        self._runtime.release(reason)
        self._handle = None

    @staticmethod
    def _validate_preroll(plan, evidence, generation: int) -> None:
        if evidence.execution_generation != generation:
            raise ProcessingRuntimeError("DSP_STALE_GENERATION", "stale preroll evidence")
        if evidence.graph_id != plan.graph_id or evidence.graph_revision != plan.graph_revision:
            raise ProcessingRuntimeError("DSP_GRAPH_MISMATCH", "runtime graph != compiled plan")
        if not evidence.graph_inspection_complete:
            raise ProcessingRuntimeError("DSP_GRAPH_NOT_OBSERVABLE", "runtime graph incomplete")

    def _notify(self) -> None:
        for callback in tuple(self._subscribers):
            callback()


class _suppress_runtime_error:
    def __enter__(self): return self
    def __exit__(self, *_): return True
```

## 131.1 Transacción DSP normativa

```text
CURRENT ACTIVE GRAPH A
        │
        ├── Draft B
        │    ↓
        │  Validate
        │    ↓
        │  Compile B
        │    ↓
        │  Prepare B
        │    ↓
        │  Preroll B
        │    ↓
        │  Verify B runtime evidence
        │    ↓
        ├── COMMIT B ───────────────► B becomes active
        │
        └── any failure ────────────► abort B; A stays authoritative
```

No se modifica A antes del commit destructivo autorizado por el runtime backend.


---

# 132. `application/dsd_policy_service.py` — RESOLUCIÓN DSD/DSP



```python
"""Resolve DSD mode using explicit policy and qualified capabilities."""
from __future__ import annotations

from michi.domain.dsd import (
    DSD_DOP_NOT_EXPLICITLY_ALLOWED,
    DSD_DOP_SELECTED,
    DSD_DSP_REQUIRES_PCM,
    DSD_NATIVE_SELECTED,
    DSD_NO_SAFE_PATH,
    DSD_PCM_CONVERSION_SELECTED,
    DsdCapabilityMatrix,
    DsdCapabilityState,
    DsdPlaybackDecision,
    DsdPlaybackMode,
    DsdPolicy,
    DsdRuntimeMode,
)


class DsdPolicyService:
    def decide(
        self,
        policy: DsdPolicy,
        capabilities: DsdCapabilityMatrix,
        *,
        dsp_required: bool,
    ) -> DsdPlaybackDecision:
        refs = capabilities.evidence_refs

        if dsp_required:
            if not policy.allow_pcm_conversion:
                return DsdPlaybackDecision(
                    DsdRuntimeMode.UNKNOWN,
                    (DSD_DSP_REQUIRES_PCM, DSD_NO_SAFE_PATH), refs,
                    True, False, False,
                )
            return DsdPlaybackDecision(
                DsdRuntimeMode.PCM_CONVERSION,
                (DSD_DSP_REQUIRES_PCM, DSD_PCM_CONVERSION_SELECTED), refs,
                True, False, True,
            )

        preferred = policy.preferred_mode
        native_ok = (
            policy.allow_native
            and capabilities.native is DsdCapabilityState.SUPPORTED
        )
        dop_ok = (
            policy.allow_dop
            and capabilities.dop is DsdCapabilityState.SUPPORTED
        )

        if preferred is DsdPlaybackMode.DISABLED:
            return DsdPlaybackDecision(
                DsdRuntimeMode.NOT_ACTIVE, ("DSD_DISABLED",), refs, True, False, False
            )

        if preferred is DsdPlaybackMode.NATIVE:
            if native_ok:
                return DsdPlaybackDecision(
                    DsdRuntimeMode.NATIVE, (DSD_NATIVE_SELECTED,), refs,
                    True, True, False,
                )
            return self._fallback(policy, native_ok=native_ok, dop_ok=dop_ok, refs=refs)

        if preferred is DsdPlaybackMode.DOP:
            if not policy.allow_dop:
                return DsdPlaybackDecision(
                    DsdRuntimeMode.UNKNOWN,
                    (DSD_DOP_NOT_EXPLICITLY_ALLOWED,), refs, True, True, False,
                )
            if dop_ok:
                return DsdPlaybackDecision(
                    DsdRuntimeMode.DOP, (DSD_DOP_SELECTED,), refs, True, True, False
                )
            return self._fallback(policy, native_ok=native_ok, dop_ok=False, refs=refs)

        if preferred is DsdPlaybackMode.PCM_CONVERSION:
            if policy.allow_pcm_conversion:
                return DsdPlaybackDecision(
                    DsdRuntimeMode.PCM_CONVERSION,
                    (DSD_PCM_CONVERSION_SELECTED,), refs, True, False, True,
                )
            return DsdPlaybackDecision(
                DsdRuntimeMode.UNKNOWN, (DSD_NO_SAFE_PATH,), refs, True, False, False
            )

        # AUTO: Native first, then explicitly allowed+qualified DoP, then PCM conversion.
        if native_ok:
            return DsdPlaybackDecision(
                DsdRuntimeMode.NATIVE, (DSD_NATIVE_SELECTED,), refs, True, True, False
            )
        if dop_ok:
            return DsdPlaybackDecision(
                DsdRuntimeMode.DOP, (DSD_DOP_SELECTED,), refs, True, True, False
            )
        return self._fallback(policy, native_ok=False, dop_ok=False, refs=refs)

    @staticmethod
    def _fallback(policy, *, native_ok: bool, dop_ok: bool, refs):
        if native_ok:
            return DsdPlaybackDecision(
                DsdRuntimeMode.NATIVE, (DSD_NATIVE_SELECTED,), refs, True, True, False
            )
        if dop_ok:
            return DsdPlaybackDecision(
                DsdRuntimeMode.DOP, (DSD_DOP_SELECTED,), refs, True, True, False
            )
        if policy.allow_pcm_conversion:
            return DsdPlaybackDecision(
                DsdRuntimeMode.PCM_CONVERSION,
                (DSD_PCM_CONVERSION_SELECTED,), refs, True, False, True,
            )
        return DsdPlaybackDecision(
            DsdRuntimeMode.UNKNOWN, (DSD_NO_SAFE_PATH,), refs, True, False, False
        )
```


---

# 133. `application/dsd_output_planner.py` — PLANES NATIVE DSD



```python
"""Pure planner for Native DSD output."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from michi.domain.audio_signal import DsdSignalFormat
from michi.domain.dsd import DsdPlaybackDecision, DsdRuntimeMode


@dataclass(frozen=True, slots=True)
class NativeDsdQualification:
    stable_device_id: str
    binding_generation: int
    grouping: str
    bit_rate_hz: int
    channels: int
    supported: bool | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NativeDsdOutputPlan:
    plan_id: str
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    engine_id: str
    source: DsdSignalFormat
    target: DsdSignalFormat
    sink_factory: str
    fallback: str
    evidence_refs: tuple[str, ...]
    decision_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DsdPlannerFacts:
    active_engine_id: str
    stable_device_id: str | None
    binding_locator: str | None
    binding_generation: int | None
    source: DsdSignalFormat
    decision: DsdPlaybackDecision
    qualifications: tuple[NativeDsdQualification, ...]
    device_available: bool


class DsdPlannerRefusal(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class DsdOutputPlanner:
    def plan_native(self, facts: DsdPlannerFacts) -> NativeDsdOutputPlan:
        if facts.decision.mode is not DsdRuntimeMode.NATIVE:
            raise DsdPlannerRefusal("DSD_MODE_NOT_NATIVE", facts.decision.mode.value)
        if facts.active_engine_id != "gstreamer":
            raise DsdPlannerRefusal("ENGINE_UNSUPPORTED_FOR_NATIVE_DSD", facts.active_engine_id)
        if not facts.device_available or not facts.stable_device_id:
            raise DsdPlannerRefusal("DSD_DEVICE_UNAVAILABLE", "selected DAC unavailable")
        if not facts.binding_locator or facts.binding_generation is None:
            raise DsdPlannerRefusal("DSD_ALSA_BINDING_MISSING", "exact ALSA binding required")

        matches = tuple(
            item for item in facts.qualifications
            if item.stable_device_id == facts.stable_device_id
            and item.binding_generation == facts.binding_generation
            and item.bit_rate_hz == facts.source.bit_rate_hz
            and item.channels == facts.source.layout.channels
            and item.grouping == facts.source.grouping.value
        )
        if not matches:
            raise DsdPlannerRefusal("DSD_EXACT_TUPLE_UNKNOWN", "no exact Native DSD evidence")
        if not any(item.supported is True for item in matches):
            if any(item.supported is False for item in matches):
                raise DsdPlannerRefusal("DSD_EXACT_TUPLE_UNSUPPORTED", "ALSA rejected exact DSD tuple")
            raise DsdPlannerRefusal("DSD_EXACT_TUPLE_INCONCLUSIVE", "qualification inconclusive")

        refs = tuple(ref for item in matches if item.supported is True for ref in item.evidence_refs)
        payload = repr((
            facts.stable_device_id,
            facts.binding_locator,
            facts.binding_generation,
            facts.source,
            refs,
        )).encode()
        return NativeDsdOutputPlan(
            plan_id="dsd:" + hashlib.sha256(payload).hexdigest()[:24],
            stable_device_id=facts.stable_device_id,
            binding_locator=facts.binding_locator,
            binding_generation=facts.binding_generation,
            engine_id="gstreamer",
            source=facts.source,
            target=facts.source,
            sink_factory="alsasink",
            fallback="stop",
            evidence_refs=refs,
            decision_codes=(
                "ENGINE_GSTREAMER_NATIVE_DSD",
                "BINDING_ALSA_HW_SELECTED",
                "EXACT_NATIVE_DSD_TUPLE_PROVEN",
                "DSP_BYPASS_REQUIRED",
                "FALLBACK_STOP",
            ),
        )
```


---

# 134. `application/dop_planner.py` — PLAN DoP EXPLÍCITO

> **KILLCRITIC CORRECTION:** el planner de referencia de esta sección queda **superseded por §§215–217** porque la qualification DoP debe separar capability del carrier de evidencia de interpretación DoP por el DAC, y debe declarar el layout físico 24/32-bit del carrier.




```python
"""Pure DoP transport planner."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from michi.domain.audio_signal import DopCarrierFormat, DsdSignalFormat
from michi.domain.dop import DopMarkerConvention, expected_carrier_rate


@dataclass(frozen=True, slots=True)
class DopQualification:
    stable_device_id: str
    source_bit_rate_hz: int
    carrier_rate_hz: int
    carrier_format: str
    supported: bool | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DopOutputPlan:
    plan_id: str
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    source: DsdSignalFormat
    carrier: DopCarrierFormat
    packer_id: str
    sink_factory: str
    evidence_refs: tuple[str, ...]
    decision_codes: tuple[str, ...]


class DopPlannerRefusal(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class DopPlanner:
    def plan(
        self,
        *,
        stable_device_id: str,
        binding_locator: str,
        binding_generation: int,
        source: DsdSignalFormat,
        explicit_dop_enabled: bool,
        qualification: tuple[DopQualification, ...],
        carrier_transport_format: str = "S32_LE",
    ) -> DopOutputPlan:
        if not explicit_dop_enabled:
            raise DopPlannerRefusal(
                "DOP_NOT_EXPLICITLY_ENABLED",
                "DoP requires an explicit qualified/user policy; never auto-enable from PCM capability",
            )
        carrier_rate = expected_carrier_rate(source.bit_rate_hz)
        matches = tuple(
            item for item in qualification
            if item.stable_device_id == stable_device_id
            and item.source_bit_rate_hz == source.bit_rate_hz
            and item.carrier_rate_hz == carrier_rate
            and item.carrier_format == carrier_transport_format
        )
        if not matches:
            raise DopPlannerRefusal("DOP_CAPABILITY_UNKNOWN", "no DoP qualification for exact carrier")
        if not any(item.supported is True for item in matches):
            if any(item.supported is False for item in matches):
                raise DopPlannerRefusal("DOP_UNSUPPORTED", "exact DoP carrier rejected")
            raise DopPlannerRefusal("DOP_QUALIFICATION_INCONCLUSIVE", "DoP qualification inconclusive")

        carrier = DopCarrierFormat(
            source_dsd=source,
            carrier_rate_hz=carrier_rate,
            carrier_transport_format=carrier_transport_format,
            carrier_container_bits=32 if carrier_transport_format == "S32_LE" else 24,
            payload_bits_per_channel_frame=16,
            marker=DopMarkerConvention.DOP_1_0,
            layout=source.layout,
        )
        refs = tuple(ref for item in matches if item.supported is True for ref in item.evidence_refs)
        payload = repr((stable_device_id, binding_locator, binding_generation, source, carrier, refs)).encode()
        return DopOutputPlan(
            plan_id="dop:" + hashlib.sha256(payload).hexdigest()[:24],
            stable_device_id=stable_device_id,
            binding_locator=binding_locator,
            binding_generation=binding_generation,
            source=source,
            carrier=carrier,
            packer_id="michi-dop-v1",
            sink_factory="alsasink",
            evidence_refs=refs,
            decision_codes=(
                "DOP_EXPLICIT_POLICY",
                "DOP_EXACT_CARRIER_PROVEN",
                "DOP_PACKER_REQUIRED",
                "PCM_DSP_FORBIDDEN_ON_CARRIER",
                "SOFTWARE_VOLUME_FORBIDDEN_ON_CARRIER",
            ),
        )
```


---

# 135. `application/signal_path_service.py` — CONSTRUCCIÓN DEL GRAFO



```python
"""Application projection service that correlates existing truth sources."""
from __future__ import annotations

from dataclasses import replace
from typing import Callable

from michi.domain.signal_path import (
    ObservabilityState,
    SignalEdge,
    SignalEvidenceRef,
    SignalNode,
    SignalPathIdentity,
    SignalPathLifecycle,
    SignalPathSnapshot,
    SignalStage,
    TransformationState,
)


class SignalPathService:
    def __init__(self) -> None:
        self._snapshot: SignalPathSnapshot | None = None
        self._revision = 0
        self._subscribers: list[Callable[[], None]] = []

    @property
    def snapshot(self) -> SignalPathSnapshot | None:
        return self._snapshot

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def rebuild(
        self,
        *,
        identity: SignalPathIdentity,
        source_node: SignalNode | None,
        decoded_node: SignalNode | None,
        engine_node: SignalNode | None,
        processing_nodes: tuple[SignalNode, ...],
        transport_nodes: tuple[SignalNode, ...],
        device_node: SignalNode | None,
        path_verdict: str,
        proof_state: str,
        reason_codes: tuple[str, ...],
        lifecycle: SignalPathLifecycle = SignalPathLifecycle.ACTIVE,
    ) -> SignalPathSnapshot:
        ordered = tuple(
            node for node in (
                source_node,
                decoded_node,
                engine_node,
                *processing_nodes,
                *transport_nodes,
                device_node,
            ) if node is not None
        )
        edges = tuple(
            SignalEdge(left.node_id, right.node_id)
            for left, right in zip(ordered, ordered[1:])
        )
        self._revision += 1
        snapshot = SignalPathSnapshot(
            identity=identity,
            nodes=ordered,
            edges=edges,
            lifecycle=lifecycle,
            revision=self._revision,
            path_verdict=path_verdict,
            proof_state=proof_state,
            reason_codes=reason_codes,
        )
        self._snapshot = snapshot
        self._notify()
        return snapshot

    def retire(self, identity: SignalPathIdentity) -> None:
        current = self._snapshot
        if current is None or current.identity != identity:
            return
        self._revision += 1
        self._snapshot = replace(
            current,
            lifecycle=SignalPathLifecycle.RETIRED,
            revision=self._revision,
        )
        self._notify()

    def clear(self) -> None:
        self._snapshot = None
        self._revision += 1
        self._notify()

    def _notify(self) -> None:
        for callback in tuple(self._subscribers):
            callback()


def evidence_ref(evidence_id: str, origin: str, summary: str) -> SignalEvidenceRef:
    return SignalEvidenceRef(evidence_id, origin, summary)


def make_node(
    *,
    node_id: str,
    stage: SignalStage,
    provider: str,
    input_signal,
    output_signal,
    transformation: TransformationState,
    observability: ObservabilityState,
    evidence: tuple[SignalEvidenceRef, ...],
    generation: int,
    title: str,
    summary: str,
) -> SignalNode:
    return SignalNode(
        node_id=node_id,
        stage=stage,
        provider=provider,
        input_signal=input_signal,
        output_signal=output_signal,
        transformation=transformation,
        observability=observability,
        evidence=evidence,
        generation=generation,
        title=title,
        summary=summary,
    )
```


---

# 136. `infrastructure/audio_processing/gstreamer_processing.py` — RUNTIME DSP

> **KILLCRITIC R10 CORRECTION:** este código se conserva sólo como prototipo histórico de la interfaz y **NO DEBE COPIARSE**. Además de las correcciones transaccionales de §§218–220, §130 R10 elimina la falsa premisa «un node = un factory Gst». La implementación productiva debe usar `backend_strategy` + adapters capability-gated; PEQ puede requerir una cascada de biquads y varias features no tienen hoy factory productivo.




```python
"""GStreamer implementation of AudioProcessingRuntimePort.

All Gst objects stay in infrastructure. The real implementation executes on
GStreamerAudioPort's owned GLib context; this module never creates a second
uncoordinated MainLoop.
"""
from __future__ import annotations

from dataclasses import dataclass
import uuid

from michi.application.audio_processing_ports import (
    ProcessingCommitResult,
    ProcessingInstallResult,
    ProcessingRuntimeError,
    ProcessingRuntimeHandle,
)
from michi.domain.audio_processing_evidence import (
    ProcessingActivity,
    ProcessingNodeRuntimeEvidence,
    ProcessingRuntimeSnapshot,
)


@dataclass
class _Candidate:
    handle: ProcessingRuntimeHandle
    plan: object
    bin: object
    predecessor: object | None
    committed: bool = False


class GStreamerProcessingRuntime:
    backend_id = "gstreamer"

    def __init__(self, *, bindings, context, pipeline_provider) -> None:
        self._bindings = bindings
        self._context = context
        self._pipeline_provider = pipeline_provider
        self._candidate: _Candidate | None = None
        self._active: _Candidate | None = None

    def prepare(self, plan, input_signal, *, execution_generation: int):
        def work():
            pipeline = self._pipeline_provider()
            if pipeline is None:
                raise ProcessingRuntimeError("DSP_PIPELINE_UNAVAILABLE", "no active Gst pipeline")
            dsp_bin = self._build_bin(plan)
            handle = ProcessingRuntimeHandle(
                handle_id=str(uuid.uuid4()),
                graph_id=plan.graph_id,
                graph_revision=plan.graph_revision,
                execution_generation=execution_generation,
            )
            self._candidate = _Candidate(handle, plan, dsp_bin, self._active)
            self._install_candidate_filter(pipeline, dsp_bin)
            return ProcessingInstallResult(
                handle=handle,
                accepted_input=input_signal,
                expected_output=input_signal,
                expected_latency_samples=plan.total_latency_samples,
            )
        return self._bindings.invoke_context_sync(self._context, work)

    def preroll(self, handle):
        def work():
            candidate = self._require_candidate(handle)
            return self._inspect(candidate)
        return self._bindings.invoke_context_sync(self._context, work)

    def commit(self, handle):
        def work():
            candidate = self._require_candidate(handle)
            candidate.committed = True
            predecessor = candidate.predecessor
            self._active = candidate
            self._candidate = None
            if predecessor is not None:
                self._dispose_bin(predecessor.bin)
            return ProcessingCommitResult(handle, candidate.plan.graph_revision)
        return self._bindings.invoke_context_sync(self._context, work)

    def abort(self, handle, reason: str):
        def work():
            candidate = self._candidate
            if candidate is None or candidate.handle != handle:
                return
            pipeline = self._pipeline_provider()
            if candidate.predecessor is not None and pipeline is not None:
                self._install_candidate_filter(pipeline, candidate.predecessor.bin)
            elif pipeline is not None:
                self._clear_audio_filter(pipeline)
            self._dispose_bin(candidate.bin)
            self._candidate = None
        return self._bindings.invoke_context_sync(self._context, work)

    def replace(self, current, plan, input_signal, *, execution_generation: int):
        if self._active is None or self._active.handle != current:
            raise ProcessingRuntimeError("DSP_STALE_HANDLE", "active graph changed")
        return self.prepare(plan, input_signal, execution_generation=execution_generation)

    def bypass(self, handle):
        def work():
            if self._active is None or self._active.handle != handle:
                raise ProcessingRuntimeError("DSP_STALE_HANDLE", "cannot bypass stale graph")
            pipeline = self._pipeline_provider()
            self._clear_audio_filter(pipeline)
        return self._bindings.invoke_context_sync(self._context, work)

    def release(self, reason: str):
        def work():
            pipeline = self._pipeline_provider()
            if pipeline is not None:
                self._clear_audio_filter(pipeline)
            if self._candidate is not None:
                self._dispose_bin(self._candidate.bin)
            if self._active is not None:
                self._dispose_bin(self._active.bin)
            self._candidate = None
            self._active = None
        return self._bindings.invoke_context_sync(self._context, work)

    def snapshot(self):
        def work():
            if self._active is None:
                return None
            return self._inspect(self._active)
        return self._bindings.invoke_context_sync(self._context, work)

    def _build_bin(self, plan):
        gst = self._bindings._gst
        dsp_bin = gst.Bin.new(f"michi_dsp_{plan.graph_revision}")
        if dsp_bin is None:
            raise ProcessingRuntimeError("DSP_BIN_CREATE_FAILED", "Gst.Bin.new returned None")

        previous = None
        first = None
        for index, node in enumerate(plan.nodes):
            element = self._make_node(node, index)
            if not dsp_bin.add(element):
                raise ProcessingRuntimeError("DSP_BIN_ADD_FAILED", node.node_id)
            if previous is not None and not previous.link(element):
                raise ProcessingRuntimeError(
                    "DSP_NODE_LINK_FAILED", f"{previous.name} -> {element.name}"
                )
            first = first or element
            previous = element

        if first is None or previous is None:
            identity = gst.ElementFactory.make("identity", "michi_dsp_identity")
            if identity is None or not dsp_bin.add(identity):
                raise ProcessingRuntimeError("DSP_IDENTITY_CREATE_FAILED", "identity unavailable")
            first = previous = identity

        sink_pad = first.get_static_pad("sink")
        src_pad = previous.get_static_pad("src")
        if sink_pad is None or src_pad is None:
            raise ProcessingRuntimeError("DSP_GHOST_PAD_FAILED", "node pads unavailable")
        if not dsp_bin.add_pad(gst.GhostPad.new("sink", sink_pad)):
            raise ProcessingRuntimeError("DSP_GHOST_PAD_FAILED", "sink ghost pad")
        if not dsp_bin.add_pad(gst.GhostPad.new("src", src_pad)):
            raise ProcessingRuntimeError("DSP_GHOST_PAD_FAILED", "src ghost pad")
        return dsp_bin

    def _make_node(self, node, index: int):
        gst = self._bindings._gst
        factory = node.backend_factory
        element = gst.ElementFactory.make(factory, f"michi_dsp_{index}_{node.node_id}")
        if element is None:
            raise ProcessingRuntimeError("DSP_FACTORY_UNAVAILABLE", factory)
        for key, value in node.properties:
            self._apply_property(element, key, value)
        return element

    def _apply_property(self, element, key: str, value) -> None:
        # Production implementation expands semantic PEQ/IR properties via a
        # dedicated factory adapter; direct arbitrary property injection is forbidden.
        if "." in key or key.startswith("band"):
            return
        prop = key.replace("-", "_")
        if element.find_property(prop) is not None:
            element.set_property(prop, value)

    def _install_candidate_filter(self, pipeline, dsp_bin) -> None:
        pipeline.set_property("audio-filter", dsp_bin)
        installed = pipeline.get_property("audio-filter")
        if installed != dsp_bin:
            raise ProcessingRuntimeError("DSP_FILTER_INSTALL_FAILED", "playbin3 rejected audio-filter")

    @staticmethod
    def _clear_audio_filter(pipeline) -> None:
        if pipeline is not None:
            pipeline.set_property("audio-filter", None)

    @staticmethod
    def _dispose_bin(dsp_bin) -> None:
        if dsp_bin is not None:
            try:
                dsp_bin.set_state(0)  # actual implementation uses Gst.State.NULL
            except Exception:
                pass

    def _require_candidate(self, handle):
        candidate = self._candidate
        if candidate is None or candidate.handle != handle:
            raise ProcessingRuntimeError("DSP_STALE_HANDLE", "candidate no longer current")
        return candidate

    def _inspect(self, candidate):
        plan = candidate.plan
        nodes = tuple(
            ProcessingNodeRuntimeEvidence(
                graph_id=plan.graph_id,
                graph_revision=plan.graph_revision,
                execution_generation=candidate.handle.execution_generation,
                node_id=node.node_id,
                kind=node.kind,
                activity=ProcessingActivity.ACTIVE,
                input_signal=None,
                output_signal=None,
                latency_samples=node.expected_latency_samples,
                backend_factory=node.backend_factory,
                evidence_refs=(f"gst-element:{node.node_id}",),
            )
            for node in plan.nodes
        )
        return ProcessingRuntimeSnapshot(
            graph_id=plan.graph_id,
            graph_revision=plan.graph_revision,
            execution_generation=candidate.handle.execution_generation,
            backend_id="gstreamer",
            input_signal=None,
            output_signal=None,
            nodes=nodes,
            graph_inspection_complete=True,
            xruns=0,
            measured_latency_frames=None,
            peak_dbfs=None,
            clipped_samples_observed=None,
        )
```

## 136.1 Corrección requerida antes de implementación real

El código anterior fija el contrato, pero la implementación productiva debe **compartir el
mismo ownership GLib** de `GStreamerAudioPort`; no debe acceder privadamente a `_gst`. El
refactor permitido en Phase 2 introduce una facade pública de infraestructura:

```text
GStreamerBindings.make_element(...)
GStreamerBindings.make_bin(...)
GStreamerBindings.set_property_checked(...)
GStreamerBindings.install_audio_filter(...)
GStreamerBindings.inspect_processing_bin(...)
```

El objetivo es mantener GI confinado y testeable sin romper encapsulación.


---

# 137. `infrastructure/audio_output/strict_dsd_sink.py` — SINK NATIVE DSD

> **KILLCRITIC CORRECTION:** la receta aquí mostrada queda **superseded por §214**. GStreamer `audio/x-dsd rate` representa bytes DSD/segundo/canal, no bit-rate de la fuente; `alsasink` además exige `reversed-bytes=false` en sus caps actuales.




```python
"""Strict Native DSD sink recipe; pure and GI-free."""
from __future__ import annotations

from dataclasses import dataclass

from michi.application.dsd_output_planner import NativeDsdOutputPlan


class StrictDsdSinkError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class StrictDsdSinkRecipe:
    plan_id: str
    sink_factory: str
    device: str
    media_type: str
    dsd_format: str
    bit_rate_hz: int
    channels: int
    layout: str
    reversed_bytes: bool

    def caps_string(self) -> str:
        reversed_value = "true" if self.reversed_bytes else "false"
        return (
            f"audio/x-dsd,format={self.dsd_format},rate={self.bit_rate_hz},"
            f"channels={self.channels},layout={self.layout},"
            f"reversed-bytes={reversed_value}"
        )


def recipe_from_native_dsd_plan(plan: NativeDsdOutputPlan) -> StrictDsdSinkRecipe:
    if plan.engine_id != "gstreamer":
        raise StrictDsdSinkError("DSD_DIRECT_PLAN_INVALID", "Native DSD requires GStreamer")
    if plan.sink_factory != "alsasink":
        raise StrictDsdSinkError("DSD_DIRECT_PLAN_INVALID", "Native DSD requires alsasink")
    source = plan.target
    return StrictDsdSinkRecipe(
        plan_id=plan.plan_id,
        sink_factory="alsasink",
        device=plan.binding_locator,
        media_type="audio/x-dsd",
        dsd_format=source.grouping.value,
        bit_rate_hz=source.bit_rate_hz,
        channels=source.layout.channels,
        layout="interleaved",
        reversed_bytes=source.bit_order.value == "reversed_bytes",
    )
```

## 137.1 Builder GStreamer objetivo

La implementación GI del sink debe ser equivalente a Strict PCM Direct, pero con caps DSD:

```python
def build_strict_dsd_sink(self, recipe):
    self.ensure_loaded()
    gst = self._gst
    sink_bin = gst.Bin.new("michi_direct_dsd_sink")
    capsfilter = gst.ElementFactory.make("capsfilter", "michi_direct_dsd_caps")
    alsa = gst.ElementFactory.make("alsasink", "michi_direct_dsd_alsa")
    if sink_bin is None or capsfilter is None or alsa is None:
        raise DirectSinkBuildError("DIRECT_DSD_SINK_CREATE_FAILED", "required Gst element unavailable")
    caps = gst.Caps.from_string(recipe.caps_string())
    if caps is None or caps.get_size() == 0:
        raise DirectSinkBuildError("DIRECT_DSD_CAPS_INVALID", recipe.caps_string())
    capsfilter.set_property("caps", caps)
    alsa.set_property("device", recipe.device)
    if not sink_bin.add(capsfilter) or not sink_bin.add(alsa):
        raise DirectSinkBuildError("DIRECT_DSD_SINK_ADD_FAILED", "cannot add elements")
    if not capsfilter.link(alsa):
        raise DirectSinkBuildError("DIRECT_DSD_SINK_LINK_FAILED", "capsfilter -> alsasink")
    sink_pad = capsfilter.get_static_pad("sink")
    ghost = gst.GhostPad.new("sink", sink_pad) if sink_pad is not None else None
    if ghost is None or not sink_bin.add_pad(ghost):
        raise DirectSinkBuildError("DIRECT_DSD_GHOST_PAD_FAILED", "sink ghost pad")
    return sink_bin
```


---

# 138. `infrastructure/audio_output/dop_runtime.py` — PACKER Y FRONTERA NATIVA



## 138.1 Implementación Python de referencia para tests y validación



```python
from dataclasses import dataclass

from michi.domain.dop import DopState, pack_dop_interleaved_stereo


@dataclass
class DopStreamPacker:
    state: DopState = DopState()

    def reset(self) -> None:
        self.state = DopState()

    def pack_stereo(self, left: bytes, right: bytes, *, reverse_bits: bool = False) -> bytes:
        result = pack_dop_interleaved_stereo(
            left, right, state=self.state, reverse_bits=reverse_bits
        )
        self.state = result.next_state
        return result.payload
```

## 138.2 Decisión productiva recomendada: plugin GStreamer Rust

Si los benchmarks muestran que el packer Python/GI no cumple el presupuesto de jitter/CPU,
crear `companion/michi-gst-dop` como plugin Rust **sólo tras ADR**. La API conceptual del
elemento queda fijada así:

```text
factory            michidop
sink caps          audio/x-dsd
src caps           audio/x-raw compatible carrier
properties         reset-marker-on-discont=true
                   reverse-payload-bits=false
messages           marker-continuity-error
                   payload-alignment-error
                   discontinuity-reset
```

Referencia Rust del núcleo de framing:

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct DopState {
    pub marker_phase: u8,
}

impl Default for DopState {
    fn default() -> Self { Self { marker_phase: 0 } }
}

const MARKERS: [u8; 2] = [0x05, 0xFA];

#[derive(Debug)]
pub enum DopError {
    ChannelLengthMismatch,
    OddPayloadLength,
    InvalidMarkerPhase,
}

pub fn pack_stereo(
    left: &[u8],
    right: &[u8],
    state: &mut DopState,
    reverse_bits: bool,
    out: &mut Vec<u8>,
) -> Result<usize, DopError> {
    if left.len() != right.len() {
        return Err(DopError::ChannelLengthMismatch);
    }
    if left.len() % 2 != 0 {
        return Err(DopError::OddPayloadLength);
    }
    if state.marker_phase > 1 {
        return Err(DopError::InvalidMarkerPhase);
    }

    out.reserve(left.len() / 2 * 6);
    let mut frames = 0usize;
    for offset in (0..left.len()).step_by(2) {
        let marker = MARKERS[state.marker_phase as usize];
        for channel in [left, right] {
            let mut a = channel[offset];
            let mut b = channel[offset + 1];
            if reverse_bits {
                a = a.reverse_bits();
                b = b.reverse_bits();
            }
            out.extend_from_slice(&[a, b, marker]);
        }
        state.marker_phase ^= 1;
        frames += 1;
    }
    Ok(frames)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn vector_01() {
        let left = [0x11, 0x22, 0x33, 0x44];
        let right = [0x55, 0x66, 0x77, 0x88];
        let expected = [
            0x11, 0x22, 0x05, 0x55, 0x66, 0x05,
            0x33, 0x44, 0xFA, 0x77, 0x88, 0xFA,
        ];
        let mut state = DopState::default();
        let mut out = Vec::new();
        let frames = pack_stereo(&left, &right, &mut state, false, &mut out).unwrap();
        assert_eq!(frames, 2);
        assert_eq!(out, expected);
        assert_eq!(state.marker_phase, 0);
    }

    #[test]
    fn chunking_does_not_change_stream() {
        let left = [1,2,3,4,5,6,7,8];
        let right = [9,10,11,12,13,14,15,16];

        let mut full_state = DopState::default();
        let mut full = Vec::new();
        pack_stereo(&left, &right, &mut full_state, false, &mut full).unwrap();

        let mut split_state = DopState::default();
        let mut split = Vec::new();
        pack_stereo(&left[..4], &right[..4], &mut split_state, false, &mut split).unwrap();
        pack_stereo(&left[4..], &right[4..], &mut split_state, false, &mut split).unwrap();
        assert_eq!(split, full);
        assert_eq!(split_state, full_state);
    }
}
```


---

# 139. ALSA DSD / DoP QUALIFICATION — CONTRATO EXACTO

> **KILLCRITIC CORRECTION:** conservar el principio de exact-open/readback, pero usar §§211, 213 y 215 para unidades y evidence types. El campo histórico `bit_rate_hz` no es suficiente para representar la rate ALSA agrupada.




## 139.1 Native DSD probe

El probe Native DSD no puede inferirse de un PCM probe. Debe abrir el **exact binding** con
un `snd_pcm_format_t` DSD exacto y leer back la configuración efectiva. El resultado se
normaliza a un tipo separado para impedir confusión con `CapabilityEvidence[PcmTuple]`.

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DsdProbeTuple:
    bit_rate_hz: int
    alsa_format: str
    channels: int
    reversed_bytes: bool


@dataclass(frozen=True, slots=True)
class DsdExactProbeResult:
    requested: DsdProbeTuple
    negotiated: DsdProbeTuple | None
    supported: bool | None
    disposition: str
    alsa_error_code: int | None
    evidence_ref: str
    environment_fingerprint: str


# Mapping normative; use actual ALSA enum values through the existing ctypes facade.
ALSA_DSD_FORMATS = {
    "DSDU8": "SND_PCM_FORMAT_DSD_U8",
    "DSDU16LE": "SND_PCM_FORMAT_DSD_U16_LE",
    "DSDU16BE": "SND_PCM_FORMAT_DSD_U16_BE",
    "DSDU32LE": "SND_PCM_FORMAT_DSD_U32_LE",
    "DSDU32BE": "SND_PCM_FORMAT_DSD_U32_BE",
}
```

## 139.2 DoP qualification

DoP posee dos niveles distintos de evidencia:

```text
carrier-capability evidence
    exact 176.4/352.8/... carrier tuple can be opened and preserved

DoP-device capability evidence
    device is explicitly known/qualified to interpret DoP
```

Nunca deducir `DoP-device capability` sólo porque un DAC acepte PCM 176.4/24.

Estados permitidos:

```text
DECLARED_ONLY
USER_CONFIRMED
PHYSICALLY_QUALIFIED
UNKNOWN
CONTRADICTED
```


---

# 140. DSD SOURCE CHARACTERIZER — IMPLEMENTACIÓN OBJETIVO

> **KILLCRITIC CORRECTION:** el fakesink final no prueba por sí solo una ruta DSD first-class; esta implementación queda **superseded por §212**, que separa container facts, elementary-stream truth y decoded/output truth.




```python
def characterize_local_audio(self, path: Path, timeout_ns: int):
    """Return first-class PcmSignalFormat or DsdSignalFormat.

    Unlike the V3.5 PCM-only characterizer this function never rejects
    audio/x-dsd solely because it is non-PCM.
    """
    self.ensure_loaded()
    source = Path(path)
    if not source.is_file():
        raise SourceCharacterizationError("SOURCE_FILE_UNAVAILABLE", str(source))

    gst = self._gst
    pipeline = gst.ElementFactory.make("playbin3", "michi_phase2_characterizer")
    audio_sink = gst.ElementFactory.make("fakesink", "michi_phase2_audio_sink")
    video_sink = gst.ElementFactory.make("fakesink", "michi_phase2_video_sink")
    text_sink = gst.ElementFactory.make("fakesink", "michi_phase2_text_sink")
    if None in (pipeline, audio_sink, video_sink, text_sink):
        raise SourceCharacterizationError("SOURCE_CHARACTERIZER_UNAVAILABLE", "GStreamer elements missing")

    for sink in (audio_sink, video_sink, text_sink):
        sink.set_property("sync", False)
    pipeline.set_property("audio-sink", audio_sink)
    pipeline.set_property("video-sink", video_sink)
    pipeline.set_property("text-sink", text_sink)
    pipeline.set_property("uri", source.resolve().as_uri())

    try:
        requested = pipeline.set_state(gst.State.PAUSED)
        if requested == gst.StateChangeReturn.FAILURE:
            raise SourceCharacterizationError("SOURCE_CHARACTERIZATION_FAILED", "PAUSED rejected")
        result, current, _pending = pipeline.get_state(max(1, int(timeout_ns)))
        if result == gst.StateChangeReturn.FAILURE or current != gst.State.PAUSED:
            raise SourceCharacterizationError("SOURCE_CHARACTERIZATION_TIMEOUT", "no bounded preroll")

        pad = audio_sink.get_static_pad("sink")
        caps = pad.get_current_caps() if pad is not None else None
        if caps is None or caps.get_size() == 0:
            raise SourceCharacterizationError("SOURCE_DECODED_CAPS_UNKNOWN", "no decoded caps")
        structure = caps.get_structure(0)
        media_type = structure.get_name()

        if media_type == "audio/x-raw":
            return self._normalized_pcm_signal(structure)
        if media_type == "audio/x-dsd":
            return self._normalized_dsd_signal(structure)
        raise SourceCharacterizationError(
            "SOURCE_ENCODING_UNSUPPORTED", f"unsupported decoded media type {media_type!r}"
        )
    finally:
        pipeline.set_state(gst.State.NULL)


def _normalized_dsd_signal(self, structure):
    from michi.domain.audio_signal import (
        ChannelLayout,
        ChannelLayoutKind,
        DsdBitOrder,
        DsdGrouping,
        DsdSignalFormat,
    )
    fmt = structure.get_value("format")
    rate = structure.get_value("rate")
    channels = structure.get_value("channels")
    reversed_bytes = bool(structure.get_value("reversed-bytes")) if structure.has_field("reversed-bytes") else False
    try:
        grouping = DsdGrouping(str(fmt))
    except ValueError as exc:
        raise SourceCharacterizationError("SOURCE_DSD_GROUPING_UNKNOWN", str(fmt)) from exc
    if not isinstance(rate, int) or rate <= 0 or not isinstance(channels, int) or channels <= 0:
        raise SourceCharacterizationError("SOURCE_DSD_CAPS_UNKNOWN", "rate/channels unavailable")
    positions = ("FL", "FR") if channels == 2 else tuple(f"CH{i+1}" for i in range(channels))
    return DsdSignalFormat(
        bit_rate_hz=rate,
        grouping=grouping,
        layout=ChannelLayout(
            ChannelLayoutKind.STEREO if channels == 2 else ChannelLayoutKind.CUSTOM,
            positions,
        ),
        bit_order=DsdBitOrder.REVERSED_BYTES if reversed_bytes else DsdBitOrder.NATIVE,
    )
```


---

# 141. CAMILLADSP ADAPTER — LÍMITE Y CONFIGURACIÓN CONCRETA

CamillaDSP se usa sólo para PCM y como executor opcional. Nunca recibe Native DSD ni carrier
DoP. La primera integración autorizada debe ser local, explícita y con lifecycle Michi-owned.

Contrato:

```text
Michi owns process lifecycle
Michi owns profile/graph authority
CamillaDSP executes compiled PCM graph
CamillaDSP config is generated, not hand-edited runtime truth
WebSocket/control plane is localhost/private
process crash => typed DSP failure; playback policy decides bypass/stop
no automatic network binding
no DSD/DoP passthrough claim
```

## 141.1 Config generada de referencia



```yaml
---
devices:
  samplerate: 96000
  chunksize: 1024
  capture:
    type: Stdin
    channels: 2
    format: F32_LE
  playback:
    type: Stdout
    channels: 2
    format: F32_LE

filters:
  preamp:
    type: Gain
    parameters:
      gain: -5.5
      scale: dB
      inverted: false

  peq_01:
    type: Biquad
    parameters:
      type: Peaking
      freq: 105.0
      q: 0.80
      gain: -3.2

  peq_02:
    type: Biquad
    parameters:
      type: Highshelf
      freq: 9000.0
      q: 0.70
      gain: 1.5

pipeline:
  - type: Filter
    channel: 0
    names: [preamp, peq_01, peq_02]
  - type: Filter
    channel: 1
    names: [preamp, peq_01, peq_02]
```

## 141.2 Estado del sidecar

```text
STOPPED
STARTING
READY
RUNNING
RECONFIGURING
FAILED
STOPPING
```

El adapter debe emitir generation-scoped evidence y nunca modificar
`AudioProcessingService.state` desde el thread/process observer directamente.


---

# 142. PIPEWIRE FILTER-CHAIN — MODO SHARED DSP



## 142.1 Configuración generada de referencia



```text
context.modules = [
  { name = libpipewire-module-filter-chain
    args = {
      node.description = "Michi DSP Shared Output"
      media.name = "Michi DSP Shared Output"
      filter.graph = {
        nodes = [
          { type = builtin
            name = preamp_l
            label = bq_raw
            config = {
              coefficients = [
                { rate = 44100 b0 = 0.55 b1 = 0.0 b2 = 0.0 a0 = 1.0 a1 = 0.0 a2 = 0.0 }
                { rate = 48000 b0 = 0.55 b1 = 0.0 b2 = 0.0 a0 = 1.0 a1 = 0.0 a2 = 0.0 }
                { rate = 96000 b0 = 0.55 b1 = 0.0 b2 = 0.0 a0 = 1.0 a1 = 0.0 a2 = 0.0 }
              ]
            }
          }
          { type = builtin
            name = eq_l_01
            label = bq_peaking
            control = { Freq = 105.0 Q = 0.8 Gain = -3.2 }
          }
          { type = builtin
            name = eq_r_01
            label = bq_peaking
            control = { Freq = 105.0 Q = 0.8 Gain = -3.2 }
          }
        ]
        links = [
          { output = "preamp_l:Out" input = "eq_l_01:In" }
        ]
        inputs = [ "preamp_l:In" "eq_r_01:In" ]
        outputs = [ "eq_l_01:Out" "eq_r_01:Out" ]
      }
      capture.props = {
        node.name = "michi_dsp_shared_input"
        media.class = "Audio/Sink"
        audio.channels = 2
        audio.position = [ FL FR ]
      }
      playback.props = {
        node.name = "michi_dsp_shared_output"
        node.passive = true
        audio.channels = 2
        audio.position = [ FL FR ]
      }
    }
  }
]
```

## 142.2 Restricciones

```text
PipeWire filter-chain is Shared-path only initially
its session-manager behavior is observable but not equivalent to hardware Direct
no bit-perfect VERIFIED claim through active DSP
no Native DSD or DoP through this adapter
PipeWire graph mutation must be generation-scoped
Michi keeps processing profile authority
```


---

# 143. LV2 HOST — CONTRATO FUTURO CERRADO

LV2 no entra en el MVP del DSP core, pero el plan deja cerrado el boundary para evitar que
una futura integración rompa ownership.

```python
class Lv2HostPort(Protocol):
    def discover(self) -> tuple[Lv2PluginDescriptor, ...]: ...
    def validate_plugin(self, uri: str) -> Lv2PluginCapability: ...
    def instantiate(self, spec: Lv2InstanceSpec) -> Lv2InstanceHandle: ...
    def load_state(self, handle, state: bytes) -> None: ...
    def save_state(self, handle) -> bytes: ...
    def set_control(self, handle, port_symbol: str, value: float) -> None: ...
    def destroy(self, handle) -> None: ...
```

Seguridad mínima:

```text
plugins disabled by default
explicit user enablement
bounded search paths
state size limits
no plugin owns filesystem paths without mediated resource mapping
LV2 Worker required/used for non-RT tasks when applicable
crash isolation strategy decided before arbitrary third-party loading
plugin URI + binary hash recorded in diagnostics
```


---

# 144. ESTADO Y TRANSICIONES AUDIO PHASE 2 — MAPAS COMPLETOS



## 144.1 PCM sin DSP

```text
SOURCE_PCM
  → CHARACTERIZED_PCM
  → OUTPUT_PLAN_PCM
  → DIRECT/SHARED PREPARE
  → PREROLL
  → COMMIT
  → RUNNING
```

## 144.2 PCM con DSP

```text
SOURCE_PCM
  → CHARACTERIZED_PCM
  → PROCESSING_PROFILE_RESOLVE
  → DSP_COMPILE
  → DSP_PREPARE
  → DSP_PREROLL
  → DSP_COMMIT
  → OUTPUT_PLAN_PCM
  → OUTPUT_PREPARE
  → OUTPUT_COMMIT
  → RUNNING_PROCESSED
```

## 144.3 Native DSD

```text
SOURCE_DSD
  → CHARACTERIZED_DSD
  → DSD_POLICY_RESOLVE
  → DSP_BYPASS_ASSERTED
  → NATIVE_DSD_QUALIFICATION_RESOLVE
  → DSD_OUTPUT_PLAN
  → DSD_SINK_PREPARE
  → DSD_PREROLL
  → DSD_RUNTIME_VERIFY
  → COMMIT
  → RUNNING_NATIVE_DSD
```

## 144.4 DoP

```text
SOURCE_DSD
  → CHARACTERIZED_DSD
  → DSD_POLICY_RESOLVE
  → EXPLICIT_DOP_GATE
  → DOP_DEVICE_CAPABILITY_RESOLVE
  → DOP_CARRIER_QUALIFICATION
  → DOP_PLAN
  → PACKER_PREPARE
  → CARRIER_SINK_PREPARE
  → MARKER/PAYLOAD PREROLL VERIFY
  → COMMIT
  → RUNNING_DOP
```

## 144.5 DSD→PCM + DSP

```text
SOURCE_DSD
  → CHARACTERIZED_DSD
  → DSD_POLICY_RESOLVE
  → DSD_TO_PCM_REQUIRED
  → CONVERTER_PREPARE
  → PCM_FORMAT_ESTABLISHED
  → DSP_COMPILE
  → DSP_PREPARE
  → OUTPUT_PLAN_PCM
  → COMMIT
  → RUNNING_DSD_CONVERTED_PROCESSED
```


---

# 145. REGLAS DE THREADING — MAPA EJECUTABLE

```text
Qt owner thread
    owns semantic state transitions
    commits application state
    emits bridge notifications

GLib/GStreamer pump thread
    owns Gst pipeline/GSource lifecycle
    observes runtime
    produces immutable normalized snapshots
    NEVER mutates application state

qualification worker
    exact-open / potentially blocking ALSA operations
    returns immutable result
    owner revalidates device+environment+generation before cache/commit

IR loader worker
    reads/decodes impulse response
    verifies hash/rate/channels
    never touches Gst graph directly

CamillaDSP observer thread/process
    observes process/control plane
    emits immutable events
    owner validates generation before state transition

QML thread
    reads bridge projections
    emits semantic user intents
    performs no hardware I/O and no DB I/O
```

Forbidden:

```text
QML -> ALSA direct call
QML -> Gst object
GStreamer callback -> ProcessingState mutation
worker result -> cache write without stale check
popup open -> blocking qualification
position timer -> SignalPath graph rebuild
per-audio-buffer Python callbacks for DSP
```


---

# 146. UI/UX MASTER SPEC — DISEÑO VISUAL Y DE INTERACCIÓN CERRADO


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Esta sección sustituye cualquier wireframe meramente conceptual anterior. Define la
experiencia objetivo con estructura, estados, jerarquía, acciones y reglas responsive.

Principios de producto:

```text
1. NowPlayingBar = estado de sesión + accesos rápidos, no panel de ingeniería.
2. Audio Lab = editar procesamiento.
3. Device Setup = configurar/diagnosticar dispositivo.
4. Signal Path = explicar lo que realmente ocurre.
5. Settings > Audio Engine = seleccionar motor.
6. Cada quick surface conduce a su surface completa sin duplicar autoridad.
7. Un control sólo existe si la capability/policy lo permite.
8. UNKNOWN debe verse como estado válido, no como error rojo.
9. CONTRADICTED/BROKEN sí es error visible.
10. DSD/DoP/DSP nunca se representan con una sola etiqueta ambigua de “Hi-Res”.
```

## 146.1 NowPlayingBar — layout definitivo full

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ┌──────── TRACK CARD ────────┐ ┌──────────────── PLAYBACK / TIMELINE ───────────────┐ ┌ OUTPUT ─┐ │
│ │ cover  Title               │ │ 00:42 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ -03:18 │ │ vol ━━━ │ │
│ │        Artist              │ │         [shuffle] [prev] [ PLAY ] [next] [repeat] │ │ DSP  NET│ │
│ │        Album               │ │                                                    │ │ PATH QLT│ │
│ └────────────────────────────┘ └────────────────────────────────────────────────────┘ │ DAC QUE │ │
│                                                                                       └─────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Output grid definitivo:

```text
row 0   [ VOLUME span 2 ] [ DSP ] [ NETWORK ]
row 1   [ SIGNAL PATH ]    [ QUALITY ] [ DAC ] [ QUEUE ]
```

Mientras Network Output no exista:

```text
NETWORK button visible = false
```

y el grid no inventa un endpoint de red. La posición se reserva por layout contract pero
puede compactarse visualmente.

## 146.2 Prioridad responsive

```text
FULL >= 1200 px window
  volume slider
  DSP icon + state dot
  Signal Path icon + state dot
  Quality text badge
  DAC icon
  Queue icon

COMPACT 900..1199
  shorter volume
  DSP icon
  Signal Path icon
  compact Quality: FLAC 24/96 or DSD64
  DAC icon
  Queue icon

NARROW < 900
  volume icon/popover
  Signal Path icon
  Quality mini badge
  DAC icon in overflow if necessary
  Queue icon
  DSP icon remains visible when active, otherwise can enter overflow

NEVER HIDE
  play/pause
  seek timeline when duration known
  active processing warning/state
  contradictory Signal Path warning
```


---

# 147. `NowPlayingBar.qml` — CAMBIO OBJETIVO DEL OUTPUT GRID


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.



```qml
// Phase 2 target fragment. Preserve canonical 154 px bar geometry.
GridLayout {
    id: outputZone
    objectName: "outputZone"
    columns: 4
    columnSpacing: MichiSpacing.xs
    rowSpacing: MichiSpacing.sm
    Layout.preferredWidth: root.compact ? 286 : 330
    Layout.minimumWidth: 270
    Layout.maximumWidth: 350
    Layout.preferredHeight: root.height - 40
    Layout.fillHeight: true
    Layout.alignment: Qt.AlignTop

    DacVolumeControl {
        objectName: "dacVolumeControl"
        Layout.row: 0
        Layout.column: 0
        Layout.columnSpan: 2
        Layout.fillWidth: true
        Layout.minimumWidth: 130
        Layout.preferredHeight: 34
        volume: root.volume
        muted: root.muted
        volumeAdjustable: root.volumeAdjustable
        volumeMode: root.volumeMode
        volumeModeLabel: root.volumeModeLabel
        onVolumeChangeRequested: value => root.volumeRequested(value)
        onMuteToggleRequested: value => root.muteRequested(value)
    }

    MichiIconButton {
        id: processingButton
        objectName: "audioProcessingButton"
        Layout.row: 0
        Layout.column: 2
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        iconName: root.processingActive ? "equalizer" : "equalizer"
        selected: root.processingActive
        accessibleName: root.processingAccessibleName
        onClicked: {
            processingPopup.open()
            root.audioProcessingRefreshRequested()
        }
    }

    MichiIconButton {
        id: networkOutputButton
        objectName: "networkOutputButton"
        Layout.row: 0
        Layout.column: 3
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        visible: root.networkOutputAvailable
        enabled: root.networkOutputSelectable
        iconName: "network-audio"
        accessibleName: root.networkOutputAccessibleName
        onClicked: root.networkOutputRequested()
    }

    MichiIconButton {
        id: signalPathButton
        objectName: "signalPathButton"
        Layout.row: 1
        Layout.column: 0
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        iconName: "signal-path"
        selected: root.signalPathEmphasized
        accessibleName: root.signalPathAccessibleName
        onClicked: {
            signalPathPopup.open()
            root.signalPathRefreshRequested()
        }
    }

    Rectangle {
        id: qualityBadge
        objectName: "qualityBadge"
        Layout.row: 1
        Layout.column: 1
        Layout.fillWidth: true
        Layout.minimumWidth: 84
        Layout.preferredHeight: 34
        radius: MichiRadius.sm
        color: MichiSemanticColors.contentSurface
        border.width: 1
        border.color: root.sourceHighResolution
            ? MichiSemanticColors.auroraPurpleBorder
            : MichiSemanticColors.borderSubtle

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: MichiSpacing.sm
            anchors.rightMargin: MichiSpacing.sm
            spacing: MichiSpacing.xs

            Rectangle {
                Layout.preferredWidth: 7
                Layout.preferredHeight: 7
                radius: 4
                color: root.hasTrack
                    ? MichiPalette.auroraGreen
                    : MichiPalette.textDisabled
            }
            MichiText {
                Layout.fillWidth: true
                text: root.qualityText()
                role: "technical"
                technical: true
                elide: Text.ElideRight
            }
            MichiStatusChip {
                visible: root.sourceResolutionBadge !== ""
                text: root.sourceResolutionBadge
                tone: root.sourceResolutionBadge === "DSD" ? "active" : "neutral"
            }
        }
    }

    MichiIconButton {
        id: dacButton
        objectName: "dacQuickButton"
        Layout.row: 1
        Layout.column: 2
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        iconName: "audio-output"
        enabled: root.dacQuickAvailable
        accessibleName: root.dacQuickAccessibleName
        onClicked: {
            dacQuickPopup.open()
            root.audioOutputRefreshRequested()
        }
    }

    MichiIconButton {
        id: queueButton
        objectName: "queueButton"
        Layout.row: 1
        Layout.column: 3
        Layout.preferredWidth: 34
        Layout.preferredHeight: 34
        iconName: "queue"
        accessibleName: qsTr("Queue")
        onClicked: root.queueRequested()
    }
}
```

## 147.1 Propiedades nuevas requeridas en NowPlayingBar



```qml
property bool processingActive: false
property bool processingBypassed: true
property string processingProfileName: ""
property string processingSummary: qsTr("DSP off")
property string processingAccessibleName: processingSummary

property string signalPathVerdict: "unknown"
property string signalProofState: "unverified"
property string signalPathAccessibleName: qsTr("Signal Path: %1, %2")
    .arg(signalPathVerdict).arg(signalProofState)
property bool signalPathEmphasized:
    signalPathVerdict === "contradicted" || signalProofState === "broken"

property bool sourceHighResolution: false
property string sourceResolutionClass: "unknown"
property string sourceResolutionBadge:
    sourceResolutionClass === "dsd" ? "DSD"
    : sourceResolutionClass === "high_res_pcm" ? "HD" : ""

property bool dacQuickAvailable: true
property string dacQuickAccessibleName: qsTr("DAC setup")

property bool networkOutputAvailable: false
property bool networkOutputSelectable: false
property string networkOutputAccessibleName: qsTr("Network output")

signal audioProcessingRefreshRequested()
signal signalPathRefreshRequested()
signal networkOutputRequested()
```


---

# 148. `AudioProcessingPopup.qml` — DISEÑO COMPLETO


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.



```qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

Popup {
    id: root
    objectName: "AudioProcessingPopup"

    property bool processingAvailable: true
    property bool processingActive: false
    property bool bypassed: true
    property string profileName: qsTr("No processing")
    property string lifecycle: "idle"
    property string preampLabel: "0.0 dB"
    property string peqLabel: qsTr("Off")
    property string convolutionLabel: qsTr("Off")
    property string resamplingLabel: qsTr("Off")
    property string latencyLabel: "0 ms"
    property string signalImpactLabel: qsTr("Unchanged")
    property bool dsdSource: false
    property string dsdPolicyLabel: ""
    property var profiles: []
    property var focusReturnTarget: null

    signal bypassRequested(bool bypassed)
    signal profileRequested(string profileId)
    signal openAudioLabRequested()

    width: 390
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: MichiSpacing.md

    onOpened: profileSelector.forceActiveFocus()
    onClosed: {
        if (root.focusReturnTarget)
            root.focusReturnTarget.forceActiveFocus()
    }

    background: MichiGlassSurface {
        radius: MichiRadius.lg
        elevation: "elevated"
        textured: true
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        RowLayout {
            Layout.fillWidth: true
            MichiIcon {
                Layout.preferredWidth: 22
                Layout.preferredHeight: 22
                name: "equalizer"
                iconColor: root.processingActive
                    ? MichiPalette.auroraCyan : MichiPalette.textSecondary
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                MichiText {
                    text: qsTr("Audio Processing")
                    role: "heading"
                }
                MichiText {
                    text: root.processingActive
                        ? qsTr("Active signal processing")
                        : qsTr("Signal processing bypassed")
                    role: "secondary"
                }
            }
            MichiStatusChip {
                text: root.processingActive ? qsTr("ACTIVE") : qsTr("BYPASS")
                tone: root.processingActive ? "active" : "neutral"
            }
        }

        MichiDivider { Layout.fillWidth: true }

        ComboBox {
            id: profileSelector
            objectName: "processingQuickProfileSelector"
            Layout.fillWidth: true
            model: root.profiles
            textRole: "displayName"
            valueRole: "profileId"
            enabled: root.processingAvailable && count > 0
            Accessible.name: qsTr("Processing profile")
            onActivated: root.profileRequested(currentValue)
            Keys.onEscapePressed: root.close()
        }

        Button {
            id: bypassToggle
            objectName: "processingBypassToggle"
            Layout.fillWidth: true
            enabled: root.processingAvailable
            focusPolicy: Qt.StrongFocus
            onClicked: root.bypassRequested(!root.bypassed)
            Accessible.name: root.bypassed
                ? qsTr("Enable audio processing")
                : qsTr("Bypass audio processing")
            contentItem: RowLayout {
                MichiText {
                    Layout.fillWidth: true
                    text: root.bypassed ? qsTr("Processing bypassed") : qsTr("Processing enabled")
                    role: "primary"
                }
                MichiStatusChip {
                    text: root.bypassed ? qsTr("OFF") : qsTr("ON")
                    tone: root.bypassed ? "neutral" : "active"
                }
            }
            background: Rectangle {
                radius: MichiRadius.md
                color: bypassToggle.hovered
                    ? MichiSemanticColors.surfaceHover
                    : MichiSemanticColors.contentSurface
                border.width: bypassToggle.visualFocus ? 1 : 0
                border.color: MichiSemanticColors.focusRing
            }
        }

        Rectangle {
            visible: root.dsdSource
            Layout.fillWidth: true
            implicitHeight: dsdInfo.implicitHeight + 2 * MichiSpacing.sm
            radius: MichiRadius.md
            color: MichiSemanticColors.contentSurface
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
            RowLayout {
                id: dsdInfo
                anchors.fill: parent
                anchors.margins: MichiSpacing.sm
                spacing: MichiSpacing.sm
                MichiIcon {
                    Layout.preferredWidth: 18
                    Layout.preferredHeight: 18
                    name: "info"
                    iconColor: MichiPalette.auroraPurple
                }
                MichiText {
                    Layout.fillWidth: true
                    text: root.dsdPolicyLabel
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
            }
        }

        GridLayout {
            columns: 2
            columnSpacing: MichiSpacing.lg
            rowSpacing: MichiSpacing.xs
            Layout.fillWidth: true

            MichiText { text: qsTr("Profile"); role: "secondary" }
            MichiText { text: root.profileName; role: "technical"; technical: true }

            MichiText { text: qsTr("Preamp"); role: "secondary" }
            MichiText { text: root.preampLabel; role: "technical"; technical: true }

            MichiText { text: qsTr("PEQ"); role: "secondary" }
            MichiText { text: root.peqLabel; role: "technical"; technical: true }

            MichiText { text: qsTr("Convolution"); role: "secondary" }
            MichiText { text: root.convolutionLabel; role: "technical"; technical: true }

            MichiText { text: qsTr("Resampling"); role: "secondary" }
            MichiText { text: root.resamplingLabel; role: "technical"; technical: true }

            MichiText { text: qsTr("Latency"); role: "secondary" }
            MichiText { text: root.latencyLabel; role: "technical"; technical: true }

            MichiText { text: qsTr("Signal impact"); role: "secondary" }
            MichiStatusChip {
                text: root.signalImpactLabel
                tone: root.processingActive ? "warning" : "neutral"
            }
        }

        MichiDivider { Layout.fillWidth: true }

        MichiButton {
            objectName: "openAudioLabButton"
            Layout.fillWidth: true
            text: qsTr("Open Audio Lab")
            accessibleName: qsTr("Open full Audio Lab")
            onClicked: {
                root.close()
                root.openAudioLabRequested()
            }
        }
    }
}
```

## 148.1 Estados del popup

```text
NO TRACK
  controls disabled
  “No active signal”

PCM + DSP OFF
  BYPASS
  profile visible
  “Signal impact: Unchanged”

PCM + DSP ACTIVE
  ACTIVE
  profile/preamp/PEQ/FIR/resample summary
  “Signal impact: Processed”

DSD + PRESERVE
  BYPASS forced by policy
  explanatory card “DSP bypassed to preserve Native DSD/DoP”

DSD + DSD→PCM + DSP
  ACTIVE
  explanatory card “DSD converted to PCM before processing”

DSP ERROR
  status ERROR
  last typed error, action “Open Audio Lab”
  no auto-disable unless policy explicitly authorizes safe bypass
```


---

# 149. `SignalPathPopup.qml` — QUICK SIGNAL PATH DESARROLLADO


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.



```qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"
import "../components"

Popup {
    id: root
    objectName: "SignalPathPopup"

    property string pathVerdict: "unknown"
    property string proofState: "unverified"
    property string summary: qsTr("Signal path unavailable")
    property var nodes: []
    property var reasonCodes: []
    property var focusReturnTarget: null

    signal openDetailedRequested()

    width: 430
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: MichiSpacing.md

    function verdictTone() {
        if (root.pathVerdict === "contradicted" || root.proofState === "broken")
            return "error"
        if (root.pathVerdict === "processed" || root.pathVerdict === "resampled"
                || root.pathVerdict === "dsd_to_pcm")
            return "warning"
        if (root.pathVerdict === "direct" || root.pathVerdict === "native_dsd"
                || root.pathVerdict === "dop")
            return "active"
        return "neutral"
    }

    onOpened: detailedButton.forceActiveFocus()
    onClosed: {
        if (root.focusReturnTarget)
            root.focusReturnTarget.forceActiveFocus()
    }

    background: MichiGlassSurface {
        radius: MichiRadius.lg
        elevation: "elevated"
        textured: true
    }

    contentItem: ColumnLayout {
        spacing: MichiSpacing.md

        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 1
                MichiText { text: qsTr("Michi Signal Path"); role: "heading" }
                MichiText { text: root.summary; role: "secondary"; wrapMode: Text.WordWrap }
            }
            ColumnLayout {
                spacing: MichiSpacing.xxs
                MichiStatusChip {
                    text: root.pathVerdict.toUpperCase().replaceAll("_", " ")
                    tone: root.verdictTone()
                }
                MichiStatusChip {
                    text: root.proofState.toUpperCase().replaceAll("_", " ")
                    tone: root.proofState === "verified" ? "active"
                        : root.proofState === "broken" ? "error" : "neutral"
                }
            }
        }

        MichiDivider { Layout.fillWidth: true }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0

            Repeater {
                model: root.nodes
                delegate: ColumnLayout {
                    id: nodeDelegate
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 0

                    SignalPathNode {
                        Layout.fillWidth: true
                        compact: true
                        title: nodeDelegate.modelData.title || ""
                        summary: nodeDelegate.modelData.summary || ""
                        stage: nodeDelegate.modelData.stage || ""
                        transformation: nodeDelegate.modelData.transformation || ""
                        observability: nodeDelegate.modelData.observability || ""
                        evidenceCount: (nodeDelegate.modelData.evidence || []).length
                    }

                    SignalPathConnector {
                        visible: index < root.nodes.length - 1
                        Layout.alignment: Qt.AlignHCenter
                        stateName: nodeDelegate.modelData.transformation || ""
                    }
                }
            }
        }

        Rectangle {
            visible: root.reasonCodes.length > 0
            Layout.fillWidth: true
            implicitHeight: reasonText.implicitHeight + MichiSpacing.md * 2
            radius: MichiRadius.md
            color: MichiSemanticColors.contentSurface
            border.width: 1
            border.color: MichiSemanticColors.borderSubtle
            MichiText {
                id: reasonText
                anchors.fill: parent
                anchors.margins: MichiSpacing.md
                text: qsTr("Evidence: %1").arg(root.reasonCodes.join(" · "))
                role: "technical"
                technical: true
                wrapMode: Text.WordWrap
            }
        }

        MichiButton {
            id: detailedButton
            objectName: "openDetailedSignalPathButton"
            Layout.fillWidth: true
            text: qsTr("Open Detailed Signal Path")
            accessibleName: qsTr("Open detailed signal path and evidence")
            onClicked: {
                root.close()
                root.openDetailedRequested()
            }
        }
    }
}
```


---

# 150. `SignalPathNode.qml` — NODO VISUAL



```qml
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../primitives"
import "../theme"

Rectangle {
    id: root
    property bool compact: false
    property string title: ""
    property string summary: ""
    property string stage: ""
    property string transformation: ""
    property string observability: ""
    property int evidenceCount: 0
    property bool expanded: false

    signal evidenceRequested()

    implicitHeight: content.implicitHeight + MichiSpacing.sm * 2
    radius: MichiRadius.md
    color: MichiSemanticColors.contentSurface
    border.width: 1
    border.color: root.transformation === "active"
        ? MichiSemanticColors.auroraPurpleBorder
        : root.observability === "conflicted"
            ? MichiPalette.error : MichiSemanticColors.borderSubtle

    RowLayout {
        id: content
        anchors.fill: parent
        anchors.margins: MichiSpacing.sm
        spacing: MichiSpacing.sm

        Rectangle {
            Layout.preferredWidth: 9
            Layout.preferredHeight: 9
            radius: 5
            color: root.observability === "observed"
                ? (root.transformation === "active"
                    ? MichiPalette.auroraPurple : MichiPalette.auroraGreen)
                : root.observability === "conflicted"
                    ? MichiPalette.error : MichiPalette.textMuted
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1
            MichiText {
                text: root.title
                role: "primary"
                font.weight: Font.DemiBold
            }
            MichiText {
                Layout.fillWidth: true
                text: root.summary
                role: "technical"
                technical: true
                wrapMode: Text.WordWrap
                elide: root.compact ? Text.ElideRight : Text.ElideNone
                maximumLineCount: root.compact ? 2 : 99
            }
        }

        MichiStatusChip {
            visible: root.transformation === "active"
            text: qsTr("Processed")
            tone: "warning"
        }

        MichiIconButton {
            visible: root.evidenceCount > 0 && !root.compact
            iconName: "info"
            accessibleName: qsTr("Show evidence for %1").arg(root.title)
            onClicked: root.evidenceRequested()
        }
    }
}
```


---

# 151. `SignalPathConnector.qml` — CONECTOR SEMÁNTICO



```qml
import QtQuick
import QtQuick.Layouts
import "../theme"

Item {
    id: root
    property string stateName: "not_present"
    implicitWidth: 22
    implicitHeight: 20

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        width: 1
        height: parent.height - 5
        color: root.stateName === "active"
            ? MichiPalette.auroraPurple
            : MichiSemanticColors.borderStrong
    }
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        width: 6
        height: 6
        rotation: 45
        color: root.stateName === "active"
            ? MichiPalette.auroraPurple
            : MichiSemanticColors.borderStrong
    }
}
```


---

# 152. DETAILED SIGNAL PATH — VISTA COMPLETA


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.



## 152.1 Layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ SIGNAL PATH                                            Direct · Verified     │
│ Track: ...                                             Generation 1842       │
├──────────────────────────────────────────────────────────────────────────────┤
│ SOURCE                                                                       │
│ FLAC · 96 kHz · 24-bit · Stereo                                             │
│ metadata facts · not runtime proof                          [Evidence ▾]      │
│      │                                                                       │
│      ▼                                                                       │
│ DECODE                                                                       │
│ PCM · 96 kHz · 24 significant bits · Stereo                                 │
│ observed at selected decoder GstPad                         [Evidence ▾]      │
│      │                                                                       │
│      ▼                                                                       │
│ AUDIO ENGINE                                                                 │
│ GStreamer · selected branch observed                                         │
│      │                                                                       │
│      ▼                                                                       │
│ PROCESSING                                                                   │
│ Bypassed / PEQ + FIR / DSD→PCM                                               │
│      │                                                                       │
│      ▼                                                                       │
│ VOLUME                                                                       │
│ Fixed / Unity                                                                │
│      │                                                                       │
│      ▼                                                                       │
│ TRANSPORT                                                                    │
│ ALSA Direct / Native DSD / DoP                                               │
│      │                                                                       │
│      ▼                                                                       │
│ DEVICE NEGOTIATION                                                           │
│ S32_LE · 96 kHz · 24 sig bits · 2 ch                                         │
│      │                                                                       │
│      ▼                                                                       │
│ DAC                                                                          │
│ Topping DX5 · USB Audio Class 2                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Integrity: VERIFIED  |  Missing evidence: 0  |  Contradictions: 0           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 152.2 Evidence drawer

Cada nodo se expande sin navegar fuera de la vista:

```text
EVIDENCE — DEVICE NEGOTIATION

Rate                    96,000 Hz
Origin                  ALSA runtime
Source                   /proc/asound/.../hw_params or equivalent observer
Generation              1842
Environment fingerprint qenv:v2:...
Observed                 2026-...
Confidence               AUTHORITATIVE

Container format         S32_LE
Origin                    ALSA runtime

Significant bits         24
Origin                    qualified/runtime authority
Conflict                  none
```

Nunca mostrar rutas personales completas en modo normal; diagnósticos avanzados pueden
mostrar locators bounded/anonymized según política.


---

# 153. `AudioLabView.qml` — DISEÑO COMPLETO DE AUDIO LAB


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.



```qml
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"
import "../components"

Item {
    id: root
    objectName: "audioLabView"

    property var profiles: []
    property string selectedProfileId: ""
    property string activeProfileId: ""
    property bool bypassed: true
    property string lifecycle: "idle"
    property var bands: []
    property real preampDb: 0.0
    property string convolutionIrName: ""
    property bool convolutionEnabled: false
    property bool resamplingEnabled: false
    property int targetRateHz: 0
    property string latencyLabel: "0 ms"
    property string currentSignalLabel: "—"
    property string outputSignalLabel: "—"
    property string validationMessage: ""
    property bool draftDirty: false
    property bool draftValid: true
    property bool canPreview: true
    property bool canCommit: true

    signal profileSelected(string profileId)
    signal createProfileRequested(string name)
    signal duplicateProfileRequested(string profileId)
    signal deleteProfileRequested(string profileId)
    signal bypassRequested(bool bypassed)
    signal preampChanged(real db)
    signal bandChanged(string bandId, var patch)
    signal addBandRequested()
    signal removeBandRequested(string bandId)
    signal convolutionRequested(bool enabled, string irId)
    signal importIrRequested()
    signal resamplingRequested(bool enabled, int targetRateHz, string quality)
    signal validateDraftRequested()
    signal previewDraftRequested()
    signal commitDraftRequested()
    signal discardDraftRequested()

    RowLayout {
        anchors.fill: parent
        anchors.margins: MichiSpacing.lg
        spacing: MichiSpacing.lg

        MichiGlassSurface {
            Layout.preferredWidth: 270
            Layout.fillHeight: true
            radius: MichiRadius.lg
            elevation: "raised"
            textured: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.md
                spacing: MichiSpacing.md

                MichiText { text: qsTr("Audio Lab"); role: "display" }
                MichiText {
                    Layout.fillWidth: true
                    text: qsTr("Processing profiles")
                    role: "secondary"
                }

                ListView {
                    id: profileList
                    objectName: "audioLabProfileList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: MichiSpacing.xs
                    model: root.profiles
                    delegate: Button {
                        id: profileButton
                        required property var modelData
                        width: profileList.width
                        height: 52
                        focusPolicy: Qt.StrongFocus
                        onClicked: root.profileSelected(modelData.profileId)
                        Accessible.name: modelData.displayName
                        contentItem: ColumnLayout {
                            MichiText {
                                Layout.fillWidth: true
                                text: profileButton.modelData.displayName
                                role: "primary"
                                elide: Text.ElideRight
                            }
                            MichiText {
                                Layout.fillWidth: true
                                text: profileButton.modelData.summary || qsTr("No processing")
                                role: "secondary"
                                elide: Text.ElideRight
                            }
                        }
                        background: Rectangle {
                            radius: MichiRadius.md
                            color: profileButton.modelData.profileId === root.selectedProfileId
                                ? MichiSemanticColors.surfaceSelected
                                : profileButton.hovered
                                    ? MichiSemanticColors.surfaceHover
                                    : "transparent"
                            border.width: profileButton.visualFocus ? 1 : 0
                            border.color: MichiSemanticColors.focusRing
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    MichiIconButton {
                        iconName: "add"
                        accessibleName: qsTr("Create processing profile")
                        onClicked: root.createProfileRequested(qsTr("New Profile"))
                    }
                    MichiIconButton {
                        iconName: "copy"
                        accessibleName: qsTr("Duplicate selected profile")
                        enabled: root.selectedProfileId !== ""
                        onClicked: root.duplicateProfileRequested(root.selectedProfileId)
                    }
                    Item { Layout.fillWidth: true }
                    MichiIconButton {
                        iconName: "delete"
                        accessibleName: qsTr("Delete selected profile")
                        enabled: root.selectedProfileId !== ""
                        onClicked: root.deleteProfileRequested(root.selectedProfileId)
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: MichiSpacing.md

            MichiGlassSurface {
                Layout.fillWidth: true
                implicitHeight: 92
                radius: MichiRadius.lg
                elevation: "raised"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.md
                    spacing: MichiSpacing.lg

                    ColumnLayout {
                        Layout.fillWidth: true
                        MichiText { text: qsTr("Current Signal"); role: "secondary" }
                        MichiText { text: root.currentSignalLabel; role: "technical"; technical: true }
                    }
                    MichiIcon { name: "arrow-right"; iconColor: MichiPalette.textSecondary }
                    ColumnLayout {
                        Layout.fillWidth: true
                        MichiText { text: qsTr("After Processing"); role: "secondary" }
                        MichiText { text: root.outputSignalLabel; role: "technical"; technical: true }
                    }
                    ColumnLayout {
                        MichiText { text: qsTr("Latency"); role: "secondary" }
                        MichiStatusChip { text: root.latencyLabel; tone: "neutral" }
                    }
                    Button {
                        id: bypassButton
                        text: root.bypassed ? qsTr("Enable DSP") : qsTr("Bypass DSP")
                        onClicked: root.bypassRequested(!root.bypassed)
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    width: parent.width
                    spacing: MichiSpacing.lg

                    MichiGlassSurface {
                        Layout.fillWidth: true
                        implicitHeight: preampContent.implicitHeight + MichiSpacing.lg * 2
                        radius: MichiRadius.lg
                        ColumnLayout {
                            id: preampContent
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.lg
                            spacing: MichiSpacing.sm
                            RowLayout {
                                Layout.fillWidth: true
                                MichiText { text: qsTr("Headroom / Preamp"); role: "heading" }
                                Item { Layout.fillWidth: true }
                                MichiText {
                                    text: Number(root.preampDb).toFixed(1) + " dB"
                                    role: "technical"; technical: true
                                }
                            }
                            Slider {
                                id: preampSlider
                                objectName: "audioLabPreampSlider"
                                Layout.fillWidth: true
                                from: -24
                                to: 6
                                stepSize: 0.1
                                value: root.preampDb
                                onMoved: root.preampChanged(value)
                                Accessible.name: qsTr("Preamp gain")
                            }
                            MichiText {
                                Layout.fillWidth: true
                                text: qsTr("Use negative preamp to preserve headroom when EQ bands boost the signal.")
                                role: "secondary"
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    MichiGlassSurface {
                        Layout.fillWidth: true
                        implicitHeight: peqContent.implicitHeight + MichiSpacing.lg * 2
                        radius: MichiRadius.lg
                        ColumnLayout {
                            id: peqContent
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.lg
                            spacing: MichiSpacing.sm
                            RowLayout {
                                Layout.fillWidth: true
                                MichiText { text: qsTr("Parametric EQ"); role: "heading" }
                                Item { Layout.fillWidth: true }
                                MichiButton {
                                    text: qsTr("Add Band")
                                    onClicked: root.addBandRequested()
                                }
                            }
                            PeqEditor {
                                objectName: "audioLabPeqEditor"
                                Layout.fillWidth: true
                                bands: root.bands
                                onBandChanged: (bandId, patch) => root.bandChanged(bandId, patch)
                                onRemoveBandRequested: bandId => root.removeBandRequested(bandId)
                            }
                        }
                    }

                    MichiGlassSurface {
                        Layout.fillWidth: true
                        implicitHeight: convolutionContent.implicitHeight + MichiSpacing.lg * 2
                        radius: MichiRadius.lg
                        ColumnLayout {
                            id: convolutionContent
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.lg
                            spacing: MichiSpacing.sm
                            RowLayout {
                                Layout.fillWidth: true
                                MichiText { text: qsTr("Convolution / FIR"); role: "heading" }
                                Item { Layout.fillWidth: true }
                                Switch {
                                    checked: root.convolutionEnabled
                                    onToggled: root.convolutionRequested(checked, "")
                                    Accessible.name: qsTr("Enable convolution")
                                }
                            }
                            MichiText {
                                Layout.fillWidth: true
                                text: root.convolutionIrName === ""
                                    ? qsTr("No impulse response selected")
                                    : root.convolutionIrName
                                role: "technical"
                                technical: true
                            }
                            MichiButton {
                                text: qsTr("Import Impulse Response")
                                onClicked: root.importIrRequested()
                            }
                        }
                    }

                    MichiGlassSurface {
                        Layout.fillWidth: true
                        implicitHeight: resampleContent.implicitHeight + MichiSpacing.lg * 2
                        radius: MichiRadius.lg
                        ColumnLayout {
                            id: resampleContent
                            anchors.fill: parent
                            anchors.margins: MichiSpacing.lg
                            spacing: MichiSpacing.sm
                            RowLayout {
                                Layout.fillWidth: true
                                MichiText { text: qsTr("Explicit Resampling"); role: "heading" }
                                Item { Layout.fillWidth: true }
                                Switch {
                                    checked: root.resamplingEnabled
                                    Accessible.name: qsTr("Enable explicit resampling")
                                    onToggled: root.resamplingRequested(checked, root.targetRateHz, "high")
                                }
                            }
                            MichiText {
                                Layout.fillWidth: true
                                text: qsTr("Disabled by default. When enabled, the rate change appears explicitly in Signal Path.")
                                role: "secondary"
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            Rectangle {
                visible: root.validationMessage !== ""
                Layout.fillWidth: true
                implicitHeight: validationText.implicitHeight + MichiSpacing.md * 2
                radius: MichiRadius.md
                color: MichiSemanticColors.contentSurface
                border.width: 1
                border.color: root.draftValid ? MichiSemanticColors.borderSubtle : MichiPalette.error
                MichiText {
                    id: validationText
                    anchors.fill: parent
                    anchors.margins: MichiSpacing.md
                    text: root.validationMessage
                    role: "secondary"
                    wrapMode: Text.WordWrap
                }
            }

            RowLayout {
                Layout.fillWidth: true
                MichiText {
                    Layout.fillWidth: true
                    text: root.draftDirty ? qsTr("Unsaved processing changes") : qsTr("Profile is up to date")
                    role: "secondary"
                }
                MichiButton {
                    text: qsTr("Discard")
                    enabled: root.draftDirty
                    onClicked: root.discardDraftRequested()
                }
                MichiButton {
                    text: qsTr("Validate")
                    enabled: root.draftDirty
                    onClicked: root.validateDraftRequested()
                }
                MichiButton {
                    text: qsTr("Preview")
                    enabled: root.draftDirty && root.draftValid && root.canPreview
                    onClicked: root.previewDraftRequested()
                }
                MichiButton {
                    text: qsTr("Apply")
                    primary: true
                    enabled: root.draftDirty && root.draftValid && root.canCommit
                    onClicked: root.commitDraftRequested()
                }
            }
        }
    }
}
```


---

# 154. `PeqEditor.qml` — EDITOR PEQ DESARROLLADO



```qml
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "../controls"
import "../primitives"
import "../theme"

ColumnLayout {
    id: root
    property var bands: []
    signal bandChanged(string bandId, var patch)
    signal removeBandRequested(string bandId)
    spacing: MichiSpacing.xs

    RowLayout {
        Layout.fillWidth: true
        MichiText { Layout.preferredWidth: 34; text: qsTr("On"); role: "secondary" }
        MichiText { Layout.preferredWidth: 110; text: qsTr("Type"); role: "secondary" }
        MichiText { Layout.preferredWidth: 110; text: qsTr("Frequency"); role: "secondary" }
        MichiText { Layout.preferredWidth: 90; text: qsTr("Q"); role: "secondary" }
        MichiText { Layout.preferredWidth: 100; text: qsTr("Gain"); role: "secondary" }
        Item { Layout.fillWidth: true }
        Item { Layout.preferredWidth: 34 }
    }

    Repeater {
        model: root.bands
        delegate: Rectangle {
            id: bandRow
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: 46
            radius: MichiRadius.sm
            color: MichiSemanticColors.contentSurface

            RowLayout {
                anchors.fill: parent
                anchors.margins: MichiSpacing.xs
                spacing: MichiSpacing.sm

                CheckBox {
                    Layout.preferredWidth: 34
                    checked: bandRow.modelData.enabled
                    Accessible.name: qsTr("Enable band %1").arg(index + 1)
                    onToggled: root.bandChanged(
                        bandRow.modelData.bandId, {"enabled": checked}
                    )
                }

                ComboBox {
                    Layout.preferredWidth: 110
                    model: ["Peak", "Low Shelf", "High Shelf", "Low Pass", "High Pass", "Notch"]
                    currentIndex: Math.max(0, model.indexOf(bandRow.modelData.typeLabel))
                    Accessible.name: qsTr("Filter type band %1").arg(index + 1)
                    onActivated: root.bandChanged(
                        bandRow.modelData.bandId, {"typeLabel": currentText}
                    )
                }

                SpinBox {
                    id: freq
                    Layout.preferredWidth: 110
                    from: 10
                    to: 50000
                    value: Math.round(bandRow.modelData.frequencyHz)
                    editable: true
                    Accessible.name: qsTr("Frequency band %1 hertz").arg(index + 1)
                    onValueModified: root.bandChanged(
                        bandRow.modelData.bandId, {"frequencyHz": value}
                    )
                }

                SpinBox {
                    id: qValue
                    Layout.preferredWidth: 90
                    from: 10
                    to: 2000
                    value: Math.round(bandRow.modelData.q * 100)
                    stepSize: 5
                    editable: true
                    textFromValue: value => (value / 100).toFixed(2)
                    valueFromText: text => Math.round(Number(text) * 100)
                    Accessible.name: qsTr("Q band %1").arg(index + 1)
                    onValueModified: root.bandChanged(
                        bandRow.modelData.bandId, {"q": value / 100}
                    )
                }

                SpinBox {
                    id: gain
                    Layout.preferredWidth: 100
                    from: -360
                    to: 360
                    value: Math.round(bandRow.modelData.gainDb * 10)
                    stepSize: 1
                    editable: true
                    textFromValue: value => (value / 10).toFixed(1) + " dB"
                    valueFromText: text => Math.round(parseFloat(text) * 10)
                    Accessible.name: qsTr("Gain band %1 decibels").arg(index + 1)
                    onValueModified: root.bandChanged(
                        bandRow.modelData.bandId, {"gainDb": value / 10}
                    )
                }

                Item { Layout.fillWidth: true }

                MichiIconButton {
                    Layout.preferredWidth: 34
                    iconName: "delete"
                    accessibleName: qsTr("Remove band %1").arg(index + 1)
                    onClicked: root.removeBandRequested(bandRow.modelData.bandId)
                }
            }
        }
    }
}
```

## 154.1 Frequency response graph

La primera versión productiva no debe intentar realizar FFT en QML. El gráfico consume una
proyección precomputada por una query service framework-free:

```python
@dataclass(frozen=True, slots=True)
class FrequencyResponsePoint:
    frequency_hz: float
    magnitude_db: float

@dataclass(frozen=True, slots=True)
class FrequencyResponseCurve:
    sample_rate_hz: int
    points: tuple[FrequencyResponsePoint, ...]
    min_db: float
    max_db: float
```

La curva se recalcula sólo al editar el draft, no durante playback ni por position ticks.


---

# 155. DEVICE SETUP — UI COMPLETA DSD/DOP/DSP



## 155.1 General

```text
TOPPING D90SE                                             Connected
USB DAC · Direct available

CURRENT SIGNAL
Native DSD128 · Stereo

PLAYBACK
Path                 Direct
Rate policy           Source Native
Volume                Fixed
DSD policy            Automatic
DSP policy            Preserve DSD
Buffer                Automatic

SIGNAL INTEGRITY
Path                  Native DSD
Proof                 Unverified / Verified according to M11.5

[Advanced] [Diagnostics]
```

## 155.2 Advanced

```text
PCM
  declared            up to 768 kHz / 32-bit
  observed            ALSA tuples ...
  qualified           44.1/16, 48/24, 96/24, 192/24
  runtime             —

DSD
  declared            DSD512
  observed            native DSD formats exposed by ALSA
  qualified           DSD64 / DSD128
  runtime             DSD128

DoP
  declared            Supported
  observed carrier    176.4 / 352.8 ...
  qualified           DSD64 / DSD128 over DoP
  runtime             —

PROCESSING
  Native DSD policy   Bypass PCM DSP
  DSD→PCM fallback    Allowed
  profile after PCM   Headphones
```

## 155.3 Expert

```text
Stable device identity
VID / PID
USB descriptors
controller family
USB Audio Class
ALSA binding
binding generation
kernel driver
firmware hint when evidenced
qualification environment fingerprint
native DSD exact tuples
DoP device evidence origin
current hw_params
processing graph id/revision
Signal Path generation
conflicts / stale evidence
```


---

# 156. DSD TRANSPORT CARD — UI COMPONENT



```qml
import QtQuick
import QtQuick.Layouts
import "../primitives"
import "../theme"

MichiGlassSurface {
    id: root
    property string policy: "auto"
    property string nativeState: "unknown"
    property string dopState: "unknown"
    property string currentMode: "not_active"
    property string maxNative: "—"
    property string maxDop: "—"
    property string explanation: ""

    signal policyRequested(string policy)

    implicitHeight: content.implicitHeight + MichiSpacing.lg * 2
    radius: MichiRadius.lg

    ColumnLayout {
        id: content
        anchors.fill: parent
        anchors.margins: MichiSpacing.lg
        spacing: MichiSpacing.md

        RowLayout {
            Layout.fillWidth: true
            MichiText { text: qsTr("DSD / DoP"); role: "heading" }
            Item { Layout.fillWidth: true }
            MichiStatusChip {
                text: root.currentMode.toUpperCase().replaceAll("_", " ")
                tone: root.currentMode === "native" || root.currentMode === "dop"
                    ? "active" : "neutral"
            }
        }

        GridLayout {
            columns: 3
            Layout.fillWidth: true
            rowSpacing: MichiSpacing.xs
            columnSpacing: MichiSpacing.md

            MichiText { text: qsTr("Mode"); role: "secondary" }
            MichiText { text: qsTr("Evidence"); role: "secondary" }
            MichiText { text: qsTr("Limit"); role: "secondary" }

            MichiText { text: qsTr("Native DSD"); role: "primary" }
            MichiStatusChip { text: root.nativeState; tone: root.nativeState === "qualified" ? "active" : "neutral" }
            MichiText { text: root.maxNative; role: "technical"; technical: true }

            MichiText { text: qsTr("DoP"); role: "primary" }
            MichiStatusChip { text: root.dopState; tone: root.dopState === "qualified" ? "active" : "neutral" }
            MichiText { text: root.maxDop; role: "technical"; technical: true }
        }

        MichiText {
            visible: root.explanation !== ""
            Layout.fillWidth: true
            text: root.explanation
            role: "secondary"
            wrapMode: Text.WordWrap
        }
    }
}
```


---

# 157. MATRIZ DE INTERACCIÓN R11 — DIRECT NUNCA CONTIENE DSP

Esta sección retira cualquier tabla anterior donde aparezca
`PCM + DSP + Direct`. El contrato productivo heredado es inequívoco:

```text
HARDWARE_DIRECT
HARDWARE_DIRECT_COMPATIBLE
    allow_processing = false
    allow_resample   = false
    allow_remix      = false
```

DSP pertenece a una familia **Processed / Managed PCM**, nunca a Direct.

| Fuente | Procesamiento | Ruta solicitada | Resultado R11 |
|---|---|---|---|
| PCM | OFF | Shared/Desktop | Shared PCM |
| PCM | OFF | Direct strict | Direct PCM si se prueba exact tuple |
| PCM | OFF | Direct compatible | Direct/container-adapted si se prueba |
| PCM | Basic/PEQ/FIR ON | Shared/Desktop | Processed Shared PCM |
| PCM | Basic/PEQ/FIR ON | Managed DAC | Processed Managed PCM |
| PCM | Basic/PEQ/FIR ON | Direct | `PROCESSING_DIRECT_CONFLICT` |
| DSD | OFF | Native DSD | sólo si F07/F08 lo prueban |
| DSD | OFF | DoP | sólo si F07/F09 lo prueban |
| DSD | DSP ON | Native DSD/DoP | `DSD_PROCESSING_CONFLICT` |
| DSD | DSP ON | DSD→PCM | conversión explícita → Processed PCM |

Resolución UX de `PROCESSING_DIRECT_CONFLICT`:

```text
User enables EQ while Direct is selected
    -> no hidden path switch
    -> present two explicit intents:
       [Use Processed output] [Keep Direct / cancel EQ]
```

Resolución inversa:

```text
User selects Direct while processing is active
    -> present:
       [Disable processing and use Direct]
       [Keep Processed output]
```

No existe:

```text
"Direct with EQ"
"Bit-perfect with EQ"
"Direct but only one harmless filter"
```

El label `Processed` no es una degradación: describe una ruta deliberadamente
transformativa y auditable.

---

# 158. PERSISTENCIA PHASE 2 — SCHEMA SQL DESARROLLADO



```sql
-- Schema version owned by the existing Michi SQLite migration framework.
-- Tables are illustrative names but normative semantics.

CREATE TABLE IF NOT EXISTS audio_processing_profiles (
    profile_id TEXT PRIMARY KEY NOT NULL,
    display_name TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    enabled INTEGER NOT NULL CHECK (enabled IN (0,1)),
    auto_headroom INTEGER NOT NULL CHECK (auto_headroom IN (0,1)),
    target_device_id TEXT NULL,
    graph_json TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_processing_selection (
    singleton_id INTEGER PRIMARY KEY NOT NULL CHECK (singleton_id = 1),
    selected_profile_id TEXT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_ir_assets (
    ir_id TEXT PRIMARY KEY NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    storage_relpath TEXT NOT NULL,
    sample_rate_hz INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    frames INTEGER NOT NULL,
    sample_format TEXT NOT NULL,
    imported_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_dsd_policy (
    stable_device_id TEXT PRIMARY KEY NOT NULL,
    schema_version INTEGER NOT NULL,
    preferred_mode TEXT NOT NULL,
    allow_native INTEGER NOT NULL CHECK (allow_native IN (0,1)),
    allow_dop INTEGER NOT NULL CHECK (allow_dop IN (0,1)),
    allow_pcm_conversion INTEGER NOT NULL CHECK (allow_pcm_conversion IN (0,1)),
    conversion_quality TEXT NOT NULL,
    preserve_dsd_when_dsp_bypassed INTEGER NOT NULL CHECK (preserve_dsd_when_dsp_bypassed IN (0,1)),
    updated_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_dsd_qualification_cache (
    evidence_id TEXT PRIMARY KEY NOT NULL,
    stable_device_id TEXT NOT NULL,
    environment_fingerprint TEXT NOT NULL,
    binding_generation INTEGER NOT NULL,
    bit_rate_hz INTEGER NOT NULL,
    alsa_format TEXT NOT NULL,
    channels INTEGER NOT NULL,
    reversed_bytes INTEGER NOT NULL CHECK (reversed_bytes IN (0,1)),
    supported INTEGER NULL CHECK (supported IN (0,1) OR supported IS NULL),
    disposition TEXT NOT NULL,
    observed_at_ns INTEGER NOT NULL,
    evidence_ref TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_dop_qualification_cache (
    evidence_id TEXT PRIMARY KEY NOT NULL,
    stable_device_id TEXT NOT NULL,
    environment_fingerprint TEXT NOT NULL,
    source_dsd_rate_hz INTEGER NOT NULL,
    carrier_rate_hz INTEGER NOT NULL,
    carrier_format TEXT NOT NULL,
    device_support_state TEXT NOT NULL,
    supported INTEGER NULL CHECK (supported IN (0,1) OR supported IS NULL),
    observed_at_ns INTEGER NOT NULL,
    evidence_ref TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dsd_qualification_device_env
ON audio_dsd_qualification_cache(stable_device_id, environment_fingerprint);

CREATE INDEX IF NOT EXISTS idx_dop_qualification_device_env
ON audio_dop_qualification_cache(stable_device_id, environment_fingerprint);
```

## 158.1 Persistencia prohibida

Nunca persistir como verdad vigente:

```text
current SignalPathSnapshot
runtime processing node activity
active Gst object identity
ALSA card index as canonical identity
DoP marker phase across application restart
current negotiated hw_params as durable capability
proof VERIFIED as durable truth
current XRUN state as capability
```

## 158.2 Persistencia y caducidad

| Dato | Persistente | Rebuildable | Invalidation |
|---|---:|---:|---|
| Processing profile | sí | no | user delete/migration |
| IR asset | sí | no | hash mismatch/user delete |
| DSD policy | sí | no | user change |
| DSD qualification | cache | sí | environment fingerprint change |
| DoP physical qualification | cache | sí | device/env/firmware evidence invalidation |
| Signal Path | no | — | end generation |
| runtime graph evidence | no | — | graph/generation retirement |
| commercial identity resolution | cache opcional | sí | KB/source version change |
| recommended profile | derivado | sí | MAHKB/version change |


---

# 159. IMPULSE RESPONSE STORE — CONTRATO IMPLEMENTABLE



```python
"""Content-addressed local IR store."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
import shutil


@dataclass(frozen=True, slots=True)
class IrAsset:
    ir_id: str
    sha256: str
    display_name: str
    relative_path: str
    sample_rate_hz: int
    channels: int
    frames: int
    sample_format: str


class IrImportError(ValueError):
    pass


class ImpulseResponseStore:
    def __init__(self, root: Path, decoder) -> None:
        self._root = root
        self._decoder = decoder
        root.mkdir(parents=True, exist_ok=True)

    def import_file(self, source: Path) -> IrAsset:
        if not source.is_file():
            raise IrImportError("IR source does not exist")
        size = source.stat().st_size
        if size <= 0 or size > 512 * 1024 * 1024:
            raise IrImportError("IR file size outside allowed bounds")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        metadata = self._decoder.inspect(source)
        if metadata.sample_rate_hz <= 0 or metadata.channels <= 0:
            raise IrImportError("invalid IR audio metadata")
        if metadata.frames <= 0:
            raise IrImportError("empty impulse response")
        ir_id = f"ir:{digest[:24]}"
        suffix = source.suffix.casefold()
        target = self._root / f"{digest}{suffix}"
        if not target.exists():
            temporary = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(source, temporary)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                temporary.unlink(missing_ok=True)
                raise IrImportError("IR copy hash mismatch")
            temporary.replace(target)
        return IrAsset(
            ir_id=ir_id,
            sha256=digest,
            display_name=source.stem,
            relative_path=target.name,
            sample_rate_hz=metadata.sample_rate_hz,
            channels=metadata.channels,
            frames=metadata.frames,
            sample_format=metadata.sample_format,
        )
```

## 159.1 IR UX

Import flow:

```text
[Import Impulse Response]
        ↓
file picker
        ↓
inspect + hash + validate
        ↓
IMPORT PREVIEW
  Name           Dirac Live L
  Rate           48 kHz
  Channels       2
  Length         131072 frames
  SHA-256        1a2b…
        ↓
[Import] [Cancel]
```

Si el profile trabaja a otra tasa, no resamplear el IR silenciosamente. Opciones:

```text
1. reject and explain rate mismatch
2. explicitly create derived IR asset at target rate with provenance
```

La primera versión usa (1) para reducir ambigüedad.


---

# 160. ERROR TAXONOMY — CÓDIGOS ESTABLES DE PRODUCTO



| Domain | Code | Normal-mode copy |
|---|---|---|
| DSP | `DSP_PROFILE_UNKNOWN` | Selected processing profile no longer exists |
| DSP | `DSP_FACTORY_UNAVAILABLE` | Required GStreamer DSP factory is missing |
| DSP | `DSP_IR_UNKNOWN` | Impulse response asset is unavailable |
| DSP | `DSP_IR_RATE_MISMATCH` | IR sample rate differs from processing graph rate |
| DSP | `DSP_GRAPH_INVALID` | Processing graph failed deterministic validation |
| DSP | `DSP_GRAPH_MISMATCH` | Runtime graph does not match compiled plan |
| DSP | `DSP_GRAPH_NOT_OBSERVABLE` | Runtime graph cannot be inspected completely |
| DSP | `DSP_STALE_GENERATION` | DSP result belongs to stale generation |
| DSP | `DSP_PREPARE_FAILED` | DSP candidate could not be prepared |
| DSP | `DSP_PREROLL_FAILED` | DSP candidate failed preroll |
| DSP | `DSP_COMMIT_FAILED` | DSP transaction failed at commit boundary |
| DSP | `DSP_RUNTIME_LOST` | Active DSP runtime disappeared |
| DSP | `DSP_CLIPPING_OBSERVED` | Runtime evidence observed clipping |
| DSP | `DSP_UNBYPASS_REQUIRES_SIGNAL` | Cannot rebuild DSP without current signal facts |
| DSD | `DSD_DEVICE_UNAVAILABLE` | Selected DSD DAC is unavailable |
| DSD | `DSD_ALSA_BINDING_MISSING` | No exact ALSA hardware binding |
| DSD | `DSD_EXACT_TUPLE_UNKNOWN` | Native DSD tuple is not qualified |
| DSD | `DSD_EXACT_TUPLE_UNSUPPORTED` | Native DSD exact tuple rejected |
| DSD | `DSD_EXACT_TUPLE_INCONCLUSIVE` | Native DSD qualification inconclusive |
| DSD | `DSD_SOURCE_CAPS_UNKNOWN` | Source DSD caps unavailable |
| DSD | `DSD_GROUPING_UNKNOWN` | Unsupported/unknown DSD grouping |
| DSD | `DSD_RUNTIME_MISMATCH` | Runtime Native DSD does not match plan |
| DSD | `DSD_TO_PCM_REQUIRED` | Selected DSP requires explicit DSD to PCM conversion |
| DOP | `DOP_NOT_EXPLICITLY_ENABLED` | DoP is not explicitly enabled |
| DOP | `DOP_CAPABILITY_UNKNOWN` | DoP device capability unknown |
| DOP | `DOP_UNSUPPORTED` | DoP explicitly unsupported for this device |
| DOP | `DOP_QUALIFICATION_INCONCLUSIVE` | DoP qualification inconclusive |
| DOP | `DOP_MARKER_DISCONTINUITY` | DoP marker sequence broken |
| DOP | `DOP_PAYLOAD_ALIGNMENT_ERROR` | DoP payload alignment invalid |
| DOP | `DOP_CARRIER_MISMATCH` | Negotiated carrier differs from plan |
| DOP | `DOP_SOFTWARE_GAIN_FORBIDDEN` | Software gain cannot modify DoP carrier |
| DOP | `DOP_DSP_FORBIDDEN` | PCM DSP cannot process DoP carrier |
| SIGNAL | `SIGNAL_PATH_STALE` | Signal Path snapshot belongs to stale generation |
| SIGNAL | `SIGNAL_PATH_CONFLICT` | Evidence sources conflict |
| SIGNAL | `SIGNAL_PATH_NOT_OBSERVABLE` | Required stage cannot be observed |
| SIGNAL | `SIGNAL_PROOF_UNAVAILABLE` | M11.5 proof is unavailable |
| SIGNAL | `SIGNAL_RUNTIME_CONTRADICTION` | Runtime evidence contradicts selected plan |

## 160.1 Error presentation rules

```text
UNKNOWN / NOT_OBSERVABLE
  neutral/informational
  never red by default

INCONCLUSIVE
  warning
  user may retry qualification

UNSUPPORTED
  normal refusal
  explain alternative path

CONTRADICTED / BROKEN
  error
  stop or fail-closed according path contract

STALE
  normally not surfaced to user
  diagnostic only unless it causes user-visible operation cancellation

RUNTIME LOST
  visible error
  no silent reroute from Direct to Shared
```


---

# 161. PRESENTATION BRIDGES — CONTRATOS COMPLETOS

Los bridges traducen snapshots a tipos Qt simples; no compilan DSP, no prueban DACs y no
resuelven DSD policy. Toda mutación llega a servicios/coordinators.

## 161.1 `presentation/audio_processing_bridge.py`



```python
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class AudioProcessingBridge(QObject):
    state_changed = Signal()
    action_failed = Signal(str, str, str)

    def __init__(self, service, profiles, query_service, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._profiles = profiles
        self._query = query_service
        self._projection = {}
        self._disposed = False
        service.subscribe_changed(self._on_changed)
        profiles.subscribe_changed(self._on_changed)
        self._rebuild()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._service.unsubscribe_changed(self._on_changed)
        self._profiles.unsubscribe_changed(self._on_changed)

    def _on_changed(self) -> None:
        if self._disposed:
            return
        self._rebuild()
        self.state_changed.emit()

    def _rebuild(self) -> None:
        self._projection = self._query.processing_projection(
            self._service.state,
            self._profiles.load_profiles(),
        )

    def _get(self, key, default=None):
        return self._projection.get(key, default)

    profiles = Property(list, lambda self: self._get("profiles", []), notify=state_changed)
    selectedProfileId = Property(str, lambda self: self._get("selectedProfileId", ""), notify=state_changed)
    activeProfileId = Property(str, lambda self: self._get("activeProfileId", ""), notify=state_changed)
    profileName = Property(str, lambda self: self._get("profileName", "No processing"), notify=state_changed)
    lifecycle = Property(str, lambda self: self._get("lifecycle", "idle"), notify=state_changed)
    active = Property(bool, lambda self: self._get("active", False), notify=state_changed)
    bypassed = Property(bool, lambda self: self._get("bypassed", True), notify=state_changed)
    summary = Property(str, lambda self: self._get("summary", "DSP off"), notify=state_changed)
    preampLabel = Property(str, lambda self: self._get("preampLabel", "0.0 dB"), notify=state_changed)
    peqLabel = Property(str, lambda self: self._get("peqLabel", "Off"), notify=state_changed)
    convolutionLabel = Property(str, lambda self: self._get("convolutionLabel", "Off"), notify=state_changed)
    resamplingLabel = Property(str, lambda self: self._get("resamplingLabel", "Off"), notify=state_changed)
    latencyLabel = Property(str, lambda self: self._get("latencyLabel", "0 ms"), notify=state_changed)
    signalImpactLabel = Property(str, lambda self: self._get("signalImpactLabel", "Unchanged"), notify=state_changed)
    dsdSource = Property(bool, lambda self: self._get("dsdSource", False), notify=state_changed)
    dsdPolicyLabel = Property(str, lambda self: self._get("dsdPolicyLabel", ""), notify=state_changed)
    bands = Property(list, lambda self: self._get("bands", []), notify=state_changed)
    draftDirty = Property(bool, lambda self: self._get("draftDirty", False), notify=state_changed)
    draftValid = Property(bool, lambda self: self._get("draftValid", True), notify=state_changed)
    validationMessage = Property(str, lambda self: self._get("validationMessage", ""), notify=state_changed)

    @Slot(str)
    def select_profile(self, profile_id: str) -> None:
        try:
            self._service.select_profile(profile_id or None)
        except Exception as exc:
            self._emit_failure(exc)

    @Slot(bool)
    def set_bypassed(self, bypassed: bool) -> None:
        try:
            self._service.set_bypassed(bypassed)
        except Exception as exc:
            self._emit_failure(exc)

    @Slot()
    def refresh(self) -> None:
        self._rebuild()
        self.state_changed.emit()

    def _emit_failure(self, exc) -> None:
        code = getattr(exc, "code", "DSP_ACTION_FAILED")
        title, explanation = self._query.failure_copy(code, str(exc))
        self.action_failed.emit(code, title, explanation)
```

## 161.2 `presentation/signal_path_bridge.py`



```python
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class SignalPathBridge(QObject):
    state_changed = Signal()

    def __init__(self, service, query_service, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._query = query_service
        self._projection = {}
        self._disposed = False
        service.subscribe(self._on_changed)
        self._rebuild()

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._service.unsubscribe(self._on_changed)

    def _on_changed(self) -> None:
        if self._disposed:
            return
        self._rebuild()
        self.state_changed.emit()

    def _rebuild(self) -> None:
        self._projection = self._query.signal_path_projection(self._service.snapshot)

    def _get(self, key, default=None):
        return self._projection.get(key, default)

    pathVerdict = Property(str, lambda self: self._get("pathVerdict", "unknown"), notify=state_changed)
    proofState = Property(str, lambda self: self._get("proofState", "unverified"), notify=state_changed)
    summary = Property(str, lambda self: self._get("summary", "Signal path unavailable"), notify=state_changed)
    nodes = Property(list, lambda self: self._get("nodes", []), notify=state_changed)
    reasonCodes = Property(list, lambda self: self._get("reasonCodes", []), notify=state_changed)
    emphasized = Property(bool, lambda self: self._get("emphasized", False), notify=state_changed)
    generationLabel = Property(str, lambda self: self._get("generationLabel", "—"), notify=state_changed)

    @Slot()
    def refresh(self) -> None:
        self._rebuild()
        self.state_changed.emit()
```


---

# 162. QUERY SERVICE — PROYECCIONES DETERMINISTAS



```python
from __future__ import annotations

from michi.domain.audio_processing import (
    ConvolutionNode,
    ParametricEqNode,
    PreampNode,
    ResampleNode,
)


class AudioPhase2QueryService:
    def processing_projection(self, state, profiles) -> dict[str, object]:
        selected = next(
            (item for item in profiles if item.profile_id == state.selected_profile_id),
            None,
        )
        graph = selected.graph if selected is not None else None
        nodes = graph.active_nodes if graph is not None else ()
        preamp = next((node for node in nodes if isinstance(node, PreampNode)), None)
        peq = next((node for node in nodes if isinstance(node, ParametricEqNode)), None)
        conv = next((node for node in nodes if isinstance(node, ConvolutionNode)), None)
        resample = next((node for node in nodes if isinstance(node, ResampleNode)), None)
        profiles_projection = [
            {
                "profileId": item.profile_id,
                "displayName": item.display_name,
                "summary": self._profile_summary(item),
                "enabled": item.enabled,
            }
            for item in profiles
        ]
        return {
            "profiles": profiles_projection,
            "selectedProfileId": state.selected_profile_id or "",
            "activeProfileId": state.active_profile_id or "",
            "profileName": selected.display_name if selected else "No processing",
            "lifecycle": state.lifecycle.value,
            "active": state.lifecycle.value == "active" and not state.bypassed,
            "bypassed": state.bypassed,
            "summary": self._profile_summary(selected) if selected else "DSP off",
            "preampLabel": f"{preamp.gain_db:.1f} dB" if preamp else "0.0 dB",
            "peqLabel": f"{len(peq.bands)} bands" if peq else "Off",
            "convolutionLabel": "On" if conv else "Off",
            "resamplingLabel": f"{resample.target_rate_hz / 1000:g} kHz" if resample else "Off",
            "latencyLabel": f"{state.latency_samples} samples",
            "signalImpactLabel": "Processed" if not state.bypassed else "Unchanged",
            "dsdSource": False,
            "dsdPolicyLabel": "",
            "bands": self._bands(peq),
            "draftDirty": False,
            "draftValid": True,
            "validationMessage": "",
        }

    def signal_path_projection(self, snapshot) -> dict[str, object]:
        if snapshot is None:
            return {
                "pathVerdict": "unknown",
                "proofState": "unverified",
                "summary": "Signal path unavailable",
                "nodes": [],
                "reasonCodes": [],
                "emphasized": False,
                "generationLabel": "—",
            }
        nodes = [
            {
                "nodeId": node.node_id,
                "stage": node.stage.value,
                "title": node.title,
                "summary": node.summary,
                "provider": node.provider,
                "transformation": node.transformation.value,
                "observability": node.observability.value,
                "evidence": [
                    {"id": ref.evidence_id, "origin": ref.origin, "summary": ref.summary}
                    for ref in node.evidence
                ],
            }
            for node in snapshot.nodes
        ]
        emphasized = snapshot.path_verdict in {"contradicted"} or snapshot.proof_state == "broken"
        return {
            "pathVerdict": snapshot.path_verdict,
            "proofState": snapshot.proof_state,
            "summary": self._path_summary(snapshot),
            "nodes": nodes,
            "reasonCodes": list(snapshot.reason_codes),
            "emphasized": emphasized,
            "generationLabel": str(snapshot.identity.execution_generation),
        }

    @staticmethod
    def _bands(peq):
        if peq is None:
            return []
        return [
            {
                "bandId": band.band_id,
                "enabled": band.enabled,
                "typeLabel": band.filter_type.value,
                "frequencyHz": band.frequency_hz,
                "q": band.q,
                "gainDb": band.gain_db,
            }
            for band in peq.bands
        ]

    @staticmethod
    def _profile_summary(profile) -> str:
        if profile is None or profile.graph.bypassed or not profile.graph.nodes:
            return "DSP off"
        names = [node.kind.value.replace("_", " ").title() for node in profile.graph.nodes]
        return " + ".join(names[:3]) + (" + …" if len(names) > 3 else "")

    @staticmethod
    def _path_summary(snapshot) -> str:
        return f"{snapshot.path_verdict.replace('_',' ').title()} · {snapshot.proof_state.replace('_',' ').title()}"

    @staticmethod
    def failure_copy(code: str, detail: str) -> tuple[str, str]:
        mapping = {
            "DSP_FACTORY_UNAVAILABLE": ("Processing component unavailable", "A required audio processing component is not installed."),
            "DSP_IR_RATE_MISMATCH": ("Impulse response rate mismatch", "The impulse response must match the active processing rate."),
            "DSP_STALE_GENERATION": ("Processing changed", "The processing graph changed before the operation completed."),
            "DOP_CAPABILITY_UNKNOWN": ("DoP not verified", "Michi cannot confirm DoP support for this DAC."),
        }
        return mapping.get(code, ("Audio processing unavailable", detail))
```


---

# 163. BOOTSTRAP WIRING — ORDEN DE CONSTRUCCIÓN



```python
# Pseudocode with concrete ownership order. Reconcile names with frozen baseline.

def build_audio_phase2_graph(container, existing_graph):
    # Pure/shared infrastructure
    ir_store = ImpulseResponseStore(container.paths.audio_ir_dir, container.ir_decoder)
    phase2_repo = SqliteAudioPhase2Repository(existing_graph.sqlite_connection_factory)

    # Application profile authorities
    processing_profiles = ProcessingProfileService(repository=phase2_repo)
    processing_compiler = ProcessingGraphCompiler()
    dsd_policy = DsdPolicyService()
    signal_path = SignalPathService()
    query = AudioPhase2QueryService()

    # Runtime processing adapter reuses existing GStreamer owner/context.
    gst_processing = GStreamerProcessingRuntime(
        bindings=existing_graph.gstreamer_bindings,
        context=existing_graph.gstreamer_port.owned_context,
        pipeline_provider=existing_graph.gstreamer_port.current_pipeline,
    )

    processing = AudioProcessingService(
        profiles=processing_profiles,
        compiler=processing_compiler,
        runtime=gst_processing,
        available_factories=existing_graph.gstreamer_registry.audio_processing_factories,
        ir_metadata=ir_store.compilation_metadata,
    )

    # Presentation bridges are constructed last.
    processing_bridge = AudioProcessingBridge(processing, processing_profiles, query)
    signal_path_bridge = SignalPathBridge(signal_path, query)

    return AudioPhase2Graph(
        processing_profiles=processing_profiles,
        processing=processing,
        dsd_policy=dsd_policy,
        signal_path=signal_path,
        processing_bridge=processing_bridge,
        signal_path_bridge=signal_path_bridge,
    )


def install_context_properties(qml_context, phase2):
    qml_context.setContextProperty("audioProcessing", phase2.processing_bridge)
    qml_context.setContextProperty("signalPath", phase2.signal_path_bridge)
```

## 163.1 Shutdown order

```text
1 disable Phase2 recovery/event acceptance
2 close QML surfaces logically / dispose bridges
3 processing service release
4 DoP/native DSD candidate invalidation
5 SignalPath retire/clear
6 existing OutputSession release
7 router detach
8 engine provider close
9 GLib context/pump teardown
10 persistence repository close
```

No se destruye un backend mientras una authority superior todavía puede emitir comandos.


---

# 164. MIGRATION STRATEGY — VERSIONES Y ROLLBACK



## 164.1 Schema versions

```text
processing profile schema v1
  preamp + PEQ + FIR/convolution + explicit resampling

v2 future
  channel tools / crossfeed / loudness

DSD policy schema v1
  native/dop/pcm_conversion flags + quality

Signal Path
  runtime only, no DB migration
```

## 164.2 Migration code shape



```python
class ProcessingProfileMigrationError(RuntimeError):
    pass


def migrate_profile_document(document: dict) -> dict:
    version = int(document.get("schema_version", 0))
    if version == 1:
        return document
    if version == 0:
        migrated = {
            "schema_version": 1,
            "profile_id": document["profile_id"],
            "display_name": document.get("display_name", "Migrated Profile"),
            "enabled": bool(document.get("enabled", True)),
            "auto_headroom": False,
            "target_device_id": None,
            "graph": {
                "graph_id": document.get("graph_id", document["profile_id"]),
                "revision": 1,
                "bypassed": bool(document.get("bypassed", False)),
                "nodes": document.get("nodes", []),
            },
            "notes": "Migrated from pre-v1 draft",
        }
        return migrated
    raise ProcessingProfileMigrationError(f"unsupported processing profile schema {version}")
```

## 164.3 Rollback contract

Una nueva app puede migrar schema sólo con backup/recovery del modelo de persistencia Michi.
Un downgrade que no entiende el schema nuevo **no debe reinterpretar** JSON parcialmente.
Debe:

```text
recognize unsupported version
keep bytes intact
refuse profile load with typed diagnostic
leave playback usable with DSP bypassed
```


---

# 165. TEST IMPLEMENTATION — DOMAIN



```python
import pytest

from michi.domain.audio_signal import (
    ChannelLayout,
    DopCarrierFormat,
    DopMarkerConvention,
    DsdGrouping,
    DsdSignalFormat,
    PcmSignalFormat,
)
from michi.domain.dop import DopState, pack_dop_interleaved_stereo


def test_dop_is_not_pcm_type():
    dsd = DsdSignalFormat(2_822_400, DsdGrouping.U8, ChannelLayout.stereo())
    dop = DopCarrierFormat(
        source_dsd=dsd,
        carrier_rate_hz=176_400,
        carrier_transport_format="S32_LE",
        carrier_container_bits=32,
        payload_bits_per_channel_frame=16,
        marker=DopMarkerConvention.DOP_1_0,
        layout=ChannelLayout.stereo(),
    )
    assert not isinstance(dop, PcmSignalFormat)


def test_dsd64_label():
    dsd = DsdSignalFormat(2_822_400, DsdGrouping.U8, ChannelLayout.stereo())
    assert dsd.rate_label == "DSD64"


def test_dop_reference_vector():
    result = pack_dop_interleaved_stereo(
        bytes([0x11,0x22,0x33,0x44]),
        bytes([0x55,0x66,0x77,0x88]),
    )
    assert result.payload == bytes([
        0x11,0x22,0x05, 0x55,0x66,0x05,
        0x33,0x44,0xFA, 0x77,0x88,0xFA,
    ])
    assert result.next_state == DopState(0)


def test_dop_chunking_preserves_marker_phase():
    left = bytes(range(8))
    right = bytes(range(8,16))
    whole = pack_dop_interleaved_stereo(left, right)
    first = pack_dop_interleaved_stereo(left[:4], right[:4])
    second = pack_dop_interleaved_stereo(left[4:], right[4:], state=first.next_state)
    assert first.payload + second.payload == whole.payload
    assert second.next_state == whole.next_state


def test_odd_dop_payload_refused():
    with pytest.raises(ValueError):
        pack_dop_interleaved_stereo(b"abc", b"def")
```

## 165.1 Processing domain tests



```python
from michi.domain.audio_processing import (
    BiquadType,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
)


def test_graph_rejects_duplicate_node_ids():
    with pytest.raises(ValueError):
        ProcessingGraph(
            graph_id="g",
            revision=1,
            nodes=(PreampNode("x", -3.0), PreampNode("x", -6.0)),
        )


def test_peq_rejects_more_than_64_bands():
    bands = tuple(
        PeqBand(str(i), BiquadType.PEAK, 100 + i * 10, 1.0, 0.0)
        for i in range(65)
    )
    with pytest.raises(ValueError):
        ParametricEqNode("peq", bands)


def test_bypassed_graph_has_no_active_nodes():
    graph = ProcessingGraph("g", 1, (PreampNode("p", -3.0),), bypassed=True)
    assert graph.active_nodes == ()
```


---

# 166. TEST IMPLEMENTATION — PROCESSING COMPILER R10

```python
import pytest

from michi.application.processing_graph_compiler import (
    ProcessingBackendCapabilities,
    ProcessingCompileFacts,
    ProcessingCompilationError,
    ProcessingGraphCompiler,
)
from michi.domain.audio_processing import (
    BiquadType,
    ChannelDelayNode,
    ChannelMapNode,
    ParametricEqNode,
    PeqBand,
    PreampNode,
    ProcessingGraph,
    ResampleNode,
    ResampleQuality,
)
from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat


def pcm96():
    return PcmSignalFormat(96_000, "S32_LE", 24, ChannelLayout.stereo())


def gst_caps(*strategies, factories=()):
    return ProcessingBackendCapabilities(
        backend_id="gstreamer",
        strategies=frozenset(strategies),
        factories=frozenset(factories),
    )


def facts(graph, backend=None):
    return ProcessingCompileFacts(
        backend=backend or gst_caps(),
        input_signal=pcm96(),
        graph=graph,
    )


def test_compiler_bypass_is_identity_plan():
    graph = ProcessingGraph("g", 1, (), bypassed=True)
    plan = ProcessingGraphCompiler().compile(facts(graph))
    assert plan.nodes == ()
    assert plan.changes_sample_values is False
    assert plan.changes_timing is False
    assert plan.changes_channel_assignment is False
    assert plan.output_rate_hz == 96_000


def test_peq_requires_strategy_not_a_fictional_factory():
    graph = ProcessingGraph(
        "g", 1,
        (ParametricEqNode(
            "peq",
            (PeqBand("b", BiquadType.PEAK, 1000, 1.0, -3.0),),
        ),),
    )
    with pytest.raises(ProcessingCompilationError) as exc:
        ProcessingGraphCompiler().compile(facts(graph))
    assert exc.value.code == "DSP_STRATEGY_UNAVAILABLE"


def test_peq_strategy_requires_probed_audioiirfilter():
    graph = ProcessingGraph(
        "g", 1,
        (ParametricEqNode(
            "peq",
            (PeqBand("b", BiquadType.PEAK, 1000, 1.0, -3.0),),
        ),),
    )
    backend = gst_caps("biquad_cascade", factories=())
    with pytest.raises(ProcessingCompilationError) as exc:
        ProcessingGraphCompiler().compile(facts(graph, backend))
    assert exc.value.code == "DSP_FACTORY_UNAVAILABLE"


def test_peq_nyquist_violation_fails_closed():
    graph = ProcessingGraph(
        "g", 1,
        (ParametricEqNode(
            "peq",
            (PeqBand("b", BiquadType.PEAK, 50_000, 1.0, -3.0),),
        ),),
    )
    backend = gst_caps("biquad_cascade", factories=("audioiirfilter",))
    with pytest.raises(ProcessingCompilationError) as exc:
        ProcessingGraphCompiler().compile(facts(graph, backend))
    assert exc.value.code == "DSP_PEQ_NYQUIST_VIOLATION"


def test_zero_gain_notch_still_changes_samples():
    graph = ProcessingGraph(
        "g", 1,
        (ParametricEqNode(
            "peq",
            (PeqBand("notch", BiquadType.NOTCH, 1000, 4.0, 0.0),),
        ),),
    )
    backend = gst_caps("biquad_cascade", factories=("audioiirfilter",))
    plan = ProcessingGraphCompiler().compile(facts(graph, backend))
    assert plan.changes_sample_values is True


def test_channel_delay_is_timing_not_gain_mutation():
    graph = ProcessingGraph("g", 1, (ChannelDelayNode("d", (0, 1000)),))
    backend = gst_caps("channel_delay")
    plan = ProcessingGraphCompiler().compile(facts(graph, backend))
    assert plan.changes_timing is True
    assert plan.changes_sample_values is False


def test_identity_channel_map_is_not_assignment_change():
    graph = ProcessingGraph("g", 1, (ChannelMapNode("m", (0, 1)),))
    backend = gst_caps("channel_map")
    plan = ProcessingGraphCompiler().compile(facts(graph, backend))
    assert plan.changes_channel_assignment is False


def test_explicit_resampler_compares_against_pre_node_rate():
    graph = ProcessingGraph(
        "g", 1,
        (ResampleNode("rs", 48_000, ResampleQuality.HIGH),),
    )
    backend = gst_caps("resample", factories=("audioresample",))
    plan = ProcessingGraphCompiler().compile(facts(graph, backend))
    assert plan.changes_rate is True
    assert plan.input_rate_hz == 96_000
    assert plan.output_rate_hz == 48_000
```

Additional gates:

```text
unknown future node -> conservative mutation / unsupported
effective graph excludes above-Nyquist saved bands with evidence
stored profile remains unchanged after rate-specific adaptation
all-pass is classified as a transform
FIR/convolution never assumed identity without proof
```

---

# 167. TEST IMPLEMENTATION — DSD POLICY MATRIX



```python
from michi.application.dsd_policy_service import DsdPolicyService
from michi.domain.dsd import (
    DsdCapabilityMatrix,
    DsdCapabilityState,
    DsdPlaybackMode,
    DsdPolicy,
    DsdRuntimeMode,
)


def caps(native, dop):
    return DsdCapabilityMatrix(native, dop, 2, 2, ("fixture",))


def test_auto_prefers_native_when_qualified():
    result = DsdPolicyService().decide(
        DsdPolicy(allow_dop=True),
        caps(DsdCapabilityState.SUPPORTED, DsdCapabilityState.SUPPORTED),
        dsp_required=False,
    )
    assert result.mode is DsdRuntimeMode.NATIVE


def test_dop_never_selected_when_not_explicitly_allowed():
    result = DsdPolicyService().decide(
        DsdPolicy(allow_native=False, allow_dop=False, allow_pcm_conversion=True),
        caps(DsdCapabilityState.UNSUPPORTED, DsdCapabilityState.SUPPORTED),
        dsp_required=False,
    )
    assert result.mode is DsdRuntimeMode.PCM_CONVERSION


def test_dsp_forces_explicit_pcm_conversion():
    result = DsdPolicyService().decide(
        DsdPolicy(allow_dop=True, allow_pcm_conversion=True),
        caps(DsdCapabilityState.SUPPORTED, DsdCapabilityState.SUPPORTED),
        dsp_required=True,
    )
    assert result.mode is DsdRuntimeMode.PCM_CONVERSION
    assert result.requires_dsd_to_pcm is True


def test_dsp_refused_if_pcm_conversion_forbidden():
    result = DsdPolicyService().decide(
        DsdPolicy(
            preferred_mode=DsdPlaybackMode.NATIVE,
            allow_native=True,
            allow_dop=False,
            allow_pcm_conversion=False,
        ),
        caps(DsdCapabilityState.SUPPORTED, DsdCapabilityState.UNKNOWN),
        dsp_required=True,
    )
    assert result.mode is DsdRuntimeMode.UNKNOWN
```


---

# 168. TEST IMPLEMENTATION — SIGNAL PATH



```python
import pytest

from michi.domain.signal_path import (
    ObservabilityState,
    SignalEdge,
    SignalNode,
    SignalPathIdentity,
    SignalPathLifecycle,
    SignalPathSnapshot,
    SignalStage,
    TransformationState,
)


def node(node_id, stage):
    return SignalNode(
        node_id=node_id,
        stage=stage,
        provider="test",
        input_signal=None,
        output_signal=None,
        transformation=TransformationState.NOT_PRESENT,
        observability=ObservabilityState.OBSERVED,
        evidence=(),
        generation=1,
        title=node_id,
        summary=node_id,
    )


def identity():
    return SignalPathIdentity("session", "plan", 1, 1, None, None)


def test_graph_rejects_edge_to_unknown_node():
    with pytest.raises(ValueError):
        SignalPathSnapshot(
            identity=identity(),
            nodes=(node("source", SignalStage.SOURCE_CONTAINER),),
            edges=(SignalEdge("source", "missing"),),
            lifecycle=SignalPathLifecycle.ACTIVE,
            revision=1,
            path_verdict="direct",
            proof_state="unverified",
            reason_codes=(),
        )


def test_path_verdict_and_proof_are_independent_axes():
    snap = SignalPathSnapshot(
        identity=identity(),
        nodes=(node("source", SignalStage.SOURCE_CONTAINER),),
        edges=(),
        lifecycle=SignalPathLifecycle.ACTIVE,
        revision=1,
        path_verdict="direct",
        proof_state="unverified",
        reason_codes=("SIGNIFICANT_BITS_UNKNOWN",),
    )
    assert snap.path_verdict == "direct"
    assert snap.proof_state == "unverified"
```


---

# 169. TEST IMPLEMENTATION — TRANSACTIONAL DSP



```python
class FakeProcessingRuntime:
    backend_id = "gstreamer"

    def __init__(self):
        self.active = None
        self.candidate = None
        self.fail_preroll = False
        self.calls = []

    def prepare(self, plan, input_signal, *, execution_generation):
        self.calls.append(("prepare", plan.graph_revision))
        handle = ProcessingRuntimeHandle(
            f"h{execution_generation}", plan.graph_id, plan.graph_revision, execution_generation
        )
        self.candidate = handle
        return ProcessingInstallResult(handle, input_signal, input_signal, plan.total_latency_samples)

    def preroll(self, handle):
        self.calls.append(("preroll", handle.graph_revision))
        if self.fail_preroll:
            raise ProcessingRuntimeError("DSP_PREROLL_FAILED", "fixture")
        return ProcessingRuntimeSnapshot(
            graph_id=handle.graph_id,
            graph_revision=handle.graph_revision,
            execution_generation=handle.execution_generation,
            backend_id="gstreamer",
            input_signal=None,
            output_signal=None,
            nodes=(),
            graph_inspection_complete=True,
            xruns=0,
            measured_latency_frames=None,
            peak_dbfs=None,
            clipped_samples_observed=False,
        )

    def commit(self, handle):
        self.calls.append(("commit", handle.graph_revision))
        self.active = handle
        self.candidate = None
        return ProcessingCommitResult(handle, handle.graph_revision)

    def abort(self, handle, reason):
        self.calls.append(("abort", handle.graph_revision))
        self.candidate = None

    def replace(self, current, plan, input_signal, *, execution_generation):
        return self.prepare(plan, input_signal, execution_generation=execution_generation)

    def bypass(self, handle): self.calls.append(("bypass", handle.graph_revision))
    def release(self, reason): self.calls.append(("release", reason)); self.active = None
    def snapshot(self): return None


def test_failed_reconfigure_keeps_predecessor_authority(service_fixture):
    service, runtime, profile_v1, profile_v2, signal = service_fixture
    service.select_profile(profile_v1.profile_id)
    service.prepare_for_pcm(signal)
    old = runtime.active
    runtime.fail_preroll = True
    with pytest.raises(ProcessingRuntimeError):
        service.reconfigure(profile_v2, signal)
    assert runtime.active == old
    assert service.state.active_graph_revision == profile_v1.graph.revision
```


---

# 170. TEST MATRIX GENERADA — FORMATOS Y TRANSICIONES

Todas las celdas siguientes se convierten en fixtures parametrizados; no son sólo checklist.

### 170.1 PCM tuples

| ID | Source | DSP | Expected |
|---|---|---|---|
| PCM-001 | 44100 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-002 | 44100 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-003 | 44100 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-004 | 44100 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-005 | 44100 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-006 | 44100 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-007 | 44100 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-008 | 44100 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-009 | 44100 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-010 | 44100 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-011 | 48000 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-012 | 48000 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-013 | 48000 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-014 | 48000 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-015 | 48000 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-016 | 48000 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-017 | 48000 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-018 | 48000 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-019 | 48000 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-020 | 48000 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-021 | 88200 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-022 | 88200 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-023 | 88200 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-024 | 88200 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-025 | 88200 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-026 | 88200 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-027 | 88200 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-028 | 88200 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-029 | 88200 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-030 | 88200 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-031 | 96000 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-032 | 96000 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-033 | 96000 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-034 | 96000 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-035 | 96000 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-036 | 96000 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-037 | 96000 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-038 | 96000 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-039 | 96000 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-040 | 96000 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-041 | 176400 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-042 | 176400 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-043 | 176400 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-044 | 176400 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-045 | 176400 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-046 | 176400 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-047 | 176400 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-048 | 176400 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-049 | 176400 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-050 | 176400 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-051 | 192000 Hz / 16-bit stereo | OFF | same rate/precision |
| PCM-052 | 192000 Hz / 16-bit stereo | PREAMP | same rate/precision |
| PCM-053 | 192000 Hz / 16-bit stereo | PEQ | same rate/precision |
| PCM-054 | 192000 Hz / 16-bit stereo | FIR | same rate/precision |
| PCM-055 | 192000 Hz / 16-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |
| PCM-056 | 192000 Hz / 24-bit stereo | OFF | same rate/precision |
| PCM-057 | 192000 Hz / 24-bit stereo | PREAMP | same rate/precision |
| PCM-058 | 192000 Hz / 24-bit stereo | PEQ | same rate/precision |
| PCM-059 | 192000 Hz / 24-bit stereo | FIR | same rate/precision |
| PCM-060 | 192000 Hz / 24-bit stereo | RESAMPLE_EXPLICIT | explicit target rate; processed |

### 170.2 DSD/DoP tuples

| ID | Source | Mode | DSP | Expected |
|---|---|---|---|---|
| DSD-001 | DSD64 | NATIVE | OFF | execute explicit selected mode |
| DSD-002 | DSD64 | NATIVE | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-003 | DSD64 | DOP | OFF | execute explicit selected mode |
| DSD-004 | DSD64 | DOP | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-005 | DSD64 | PCM_CONVERSION | OFF | execute explicit selected mode |
| DSD-006 | DSD64 | PCM_CONVERSION | PEQ | execute explicit selected mode |
| DSD-007 | DSD128 | NATIVE | OFF | execute explicit selected mode |
| DSD-008 | DSD128 | NATIVE | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-009 | DSD128 | DOP | OFF | execute explicit selected mode |
| DSD-010 | DSD128 | DOP | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-011 | DSD128 | PCM_CONVERSION | OFF | execute explicit selected mode |
| DSD-012 | DSD128 | PCM_CONVERSION | PEQ | execute explicit selected mode |
| DSD-013 | DSD256 | NATIVE | OFF | execute explicit selected mode |
| DSD-014 | DSD256 | NATIVE | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-015 | DSD256 | DOP | OFF | execute explicit selected mode |
| DSD-016 | DSD256 | DOP | PEQ | refuse direct combination; require explicit DSD→PCM |
| DSD-017 | DSD256 | PCM_CONVERSION | OFF | execute explicit selected mode |
| DSD-018 | DSD256 | PCM_CONVERSION | PEQ | execute explicit selected mode |

## 170.3 Transition fixtures



| From | To | Required behavior |
|---|---|---|
| PCM44 | PCM44 | same tuple candidate gapless |
| PCM44 | PCM48 | controlled rate transition |
| PCM96 DSP | PCM96 DSP | same graph/revision no-op where safe |
| PCM96 DSP | PCM96 bypass | atomic DSP bypass |
| PCM96 | DSD64 Native | family reopen |
| DSD64 Native | PCM96 | family reopen |
| DSD64 Native | DSD128 Native | reopen unless physically proved safe |
| DSD64 Native | DSD64 DoP | family transport reopen |
| DSD64 DoP | DSD64 Native | family transport reopen |
| DSD64 Native | DSD64→PCM+PEQ | converter+DSP build |
| DSD64→PCM+PEQ | DSD64 Native | DSP teardown+native requalify |


---

# 171. QML TEST GATES — CÓDIGO



```python
from pathlib import Path

QML = Path("src/michi/presentation/qml")


def source(path):
    return (QML / path).read_text()


def test_now_playing_phase2_slots_are_unique():
    bar = source("player/NowPlayingBar.qml")
    assert bar.count('objectName: "audioProcessingButton"') == 1
    assert bar.count('objectName: "signalPathButton"') == 1
    assert bar.count('objectName: "dacQuickButton"') == 1
    assert bar.count('objectName: "qualityBadge"') == 1
    assert bar.count('objectName: "queueButton"') == 1


def test_engine_quick_selector_removed_after_contract_migration():
    bar = source("player/NowPlayingBar.qml")
    assert 'objectName: "audioEngineButton"' not in bar
    assert "AudioEnginePopup" not in bar
    settings = source("views/AudioEngineSettingsSection.qml")
    assert "switch_engine" in source("shell/AppShell.qml") or "selectionRequested" in settings


def test_signal_path_popup_has_dual_axes():
    popup = source("player/SignalPathPopup.qml")
    assert "pathVerdict" in popup
    assert "proofState" in popup
    assert "Open Detailed Signal Path" in popup


def test_processing_popup_is_quick_surface_only():
    popup = source("player/AudioProcessingPopup.qml")
    assert "profileRequested" in popup
    assert "bypassRequested" in popup
    assert "openAudioLabRequested" in popup
    assert "PeqEditor" not in popup
    assert "ConvolutionSetup" not in popup


def test_audio_lab_contains_full_edit_surfaces():
    lab = source("views/AudioLabView.qml")
    assert "PeqEditor" in lab
    assert "Headroom / Preamp" in lab
    assert "Convolution / FIR" in lab
    assert "Explicit Resampling" in lab
    assert "Preview" in lab
    assert "Apply" in lab


def test_new_popups_restore_focus():
    for file in ("player/AudioProcessingPopup.qml", "player/SignalPathPopup.qml"):
        content = source(file)
        assert "focusReturnTarget" in content
        assert "forceActiveFocus()" in content
        assert "Popup.CloseOnEscape" in content
```


---

# 172. ACCESSIBILITY CONTRACT



## 172.1 Keyboard

```text
Tab / Shift+Tab      deterministic focus order
Enter / Space        activate focused button/toggle
Esc                  close popup and restore opener focus
Up/Down              popup/list navigation
Left/Right           sliders or graph navigation where semantically appropriate
Ctrl+Z                undo current Audio Lab draft action (future gate if implemented)
Ctrl+Shift+Z          redo
```

## 172.2 Screen reader copy

No usar sólo “HD”, “Direct” o un color. Ejemplos:

```text
Quality: FLAC, 24 bit, 96 kilohertz, high-resolution source
Signal Path: Direct path, integrity verified
Audio Processing: Headphones profile, active, preamp minus 5.5 decibels, 8 PEQ bands
DSD: Native DSD128 active, processing bypassed to preserve DSD
DoP: DSD64 over DoP, carrier 176.4 kilohertz, DAC interpretation unverified
```

## 172.3 Reduced motion

```text
No animated flowing signal line required.
No perpetual pulsing node.
Transitions <= existing MichiMotion tokens and disabled under reducedMotion.
Signal state communicated with text/icon/shape, never animation only.
```


---

# 173. PERFORMANCE BUDGETS — GATES CUANTITATIVOS INICIALES

Los valores son objetivos de ingeniería que deben medirse y podrán ajustarse antes del freeze,
pero cualquier ajuste debe quedar documentado con hardware de prueba.

| Métrica | Objetivo inicial | Gate |
|---|---:|---|
| DSP graph compile, 10 PEQ bands | < 25 ms p95 | desktop reference |
| DSP live replace prepare+preroll | < 150 ms p95 | no XRUN attributable |
| Quick popup open | < 50 ms perceived / cached | no I/O blocking |
| Signal Path projection rebuild | < 5 ms p95 | no position-driven rebuild |
| 10-band PEQ CPU | < 2% one reference core | 96k stereo |
| FIR 131k taps CPU | measured, bounded | publish reference hardware |
| DoP packer overhead | < 2% one reference core | DSD128 stereo target |
| owner-thread event handler | < 2 ms p99 | no native blocking |
| QML steady animation | 60 fps target | reduced motion honored |
| XRUN introduced by DSP | 0 in qualification run | mandatory |

Reference hardware matrix must include at least one mid-range CPU, not only developer high-end hardware.


---

# 174. CI / VERIFIER — SCRIPT CONTRACT



```python
# scripts/verify_audio_phase2.py
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]
    mandatory: bool = True


GATES = (
    Gate("ruff", (sys.executable, "-m", "ruff", "check", "src", "tests")),
    Gate("format", (sys.executable, "-m", "ruff", "format", "--check", "src", "tests")),
    Gate("phase2-domain", (sys.executable, "-m", "pytest", "-q", "tests/audio_phase2/test_audio_signal.py", "tests/audio_phase2/test_processing_domain.py")),
    Gate("phase2-dsp", (sys.executable, "-m", "pytest", "-q", "tests/audio_phase2/test_processing_compiler.py", "tests/audio_phase2/test_processing_transactions.py")),
    Gate("phase2-dsd", (sys.executable, "-m", "pytest", "-q", "tests/audio_phase2/test_dsd_domain.py", "tests/audio_phase2/test_dsd_planner.py")),
    Gate("phase2-dop", (sys.executable, "-m", "pytest", "-q", "tests/audio_phase2/test_dop_vectors.py", "tests/audio_phase2/test_dop_transitions.py")),
    Gate("phase2-signal", (sys.executable, "-m", "pytest", "-q", "tests/audio_phase2/test_signal_path_graph.py")),
    Gate("phase2-qml", (sys.executable, "-m", "pytest", "-q", "tests/qml")),
    Gate("v35-regression", (sys.executable, "scripts/verify_dac_m11_4.py")),
    Gate("full-suite", (sys.executable, "-m", "pytest", "-q")),
    Gate("build", (sys.executable, "-m", "build")),
)


def run_gate(gate: Gate) -> int:
    print(f"=== {gate.name} ===", flush=True)
    completed = subprocess.run(gate.command, check=False)
    return completed.returncode


def main() -> int:
    failed = []
    for gate in GATES:
        code = run_gate(gate)
        if code != 0 and gate.mandatory:
            failed.append((gate.name, code))
    if failed:
        for name, code in failed:
            print(f"NO-GO {name}: exit {code}")
        return 1
    print("AUDIO PHASE 2 AUTOMATED VERDICT: GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## 174.1 Artifact manifest

El verifier genera un artifact ignorado por git con:

```json
{
  "schema": 1,
  "repository_sha": "...",
  "python": "...",
  "qt": "...",
  "gstreamer": "...",
  "alsa": "...",
  "camilladsp": "... or not installed",
  "dop_backend": "python-reference|rust-plugin|none",
  "gates": {},
  "test_counts": {},
  "skips": {},
  "physical": "NOT_RUN|PARTIAL|GO",
  "performance": "NOT_RUN|PARTIAL|GO",
  "verdict": "GO|NO_GO"
}
```


---

# 175. PACKAGING — FEATURE DISCOVERY Y DEPENDENCIAS



## 175.1 Base wheel

El wheel Python sigue siendo utilizable sin componentes opcionales pesados. Discovery:

```text
feature                 implemented    runtime available
PCM Qt                  yes            probe
PCM GStreamer           yes            GI/Gst probe
MPD                     yes            binary/plugin probe
DSP GStreamer           yes            required factory probe
Native DSD              yes            Gst>=required + alsasink DSD caps + ALSA probe
DoP                      yes/optional   packer backend + explicit DAC qualification
CamillaDSP               optional       binary/version probe
PipeWire DSP             optional       pipewire + filter-chain probe
LV2                      post-core      host + plugin discovery
```

## 175.2 Distro dependencies target

Package documentation must name capability groups instead of pretending every distro uses the same package names:

```text
GStreamer core/playback/base/audiofx/equalizer/alsa
PyGObject + Gst typelib
ALSA userspace library
MPD binary for MPD engine
optional CamillaDSP binary
optional PipeWire filter-chain module
optional LV2 host dependencies
```

At runtime Michi reports truthful capability blockers, not “feature broken”.


---

# 176. HARDWARE QUALIFICATION PROTOCOL — COMPLETE



## 176.1 Required device classes

```text
HW-A  class-compliant UAC2 PCM DAC
HW-B  commercial DAC with strong descriptors
HW-C  generic XMOS-style descriptor DAC
HW-D  multi-endpoint USB audio interface
HW-E  Native DSD capable DAC
HW-F  DoP capable DAC
HW-G  Native DSD + DoP capable DAC
HW-H  DAC accepting high-rate PCM but known NOT to support DoP
```

## 176.2 Per-device run sheet

```text
1. record kernel / ALSA / GStreamer / firmware environment
2. discover stable identity
3. disconnect/reconnect generation check
4. PCM exact qualification matrix
5. source-native PCM playback
6. rate switching
7. fixed/software volume semantics as applicable
8. Native DSD exact probe where applicable
9. Native DSD playback + runtime capture
10. DoP qualification where applicable
11. DoP byte/carrier verification
12. stop/pause DSD behavior
13. DSD64→DSD128 transition
14. DSD→PCM fallback
15. DSP PEQ at 44.1/96/192
16. FIR/convolution load and transition
17. DSP bypass identity
18. hotplug during DSP
19. hotplug during Native DSD
20. hotplug during DoP
21. BUSY injection
22. suspend/resume
23. app shutdown while active
24. restart persistence
25. export diagnostic bundle
```


---

# 177. KILLCRITIC — ADVERSARIAL REVIEW CHECKLIST



## 177.1 Authority

- [ ] **AUTHORITY-01** Can any QML property become a second DSP truth?
- [ ] **AUTHORITY-02** Can CamillaDSP state override Michi profile authority?
- [ ] **AUTHORITY-03** Can PipeWire graph state mutate OutputPlan policy?
- [ ] **AUTHORITY-04** Can DoP qualification overwrite PCM capability evidence?
- [ ] **AUTHORITY-05** Can MAHKB become runtime truth?
- [ ] **AUTHORITY-06** Can SignalPathGraph decide M11.5 proof instead of projecting it?

## 177.2 Staleness

- [ ] **STALENESS-01** What happens if DAC generation changes during DSD qualification?
- [ ] **STALENESS-02** What happens if graph revision changes during DSP preroll?
- [ ] **STALENESS-03** What happens if a late GStreamer bus event belongs to predecessor graph?
- [ ] **STALENESS-04** What happens if IR import completes after profile was deleted?
- [ ] **STALENESS-05** What happens if DoP candidate completes after Stop?
- [ ] **STALENESS-06** What happens if engine switch invalidates active processing runtime?

## 177.3 DSP

- [ ] **DSP-01** Does bypass actually remove/identity-process the branch?
- [ ] **DSP-02** Can audioresample appear without an explicit ResampleNode?
- [ ] **DSP-03** Can audioconvert remix silently?
- [ ] **DSP-04** Can positive gain clip without visibility?
- [ ] **DSP-05** Can FIR latency be omitted?
- [ ] **DSP-06** Can IR rate mismatch be silently resampled?
- [ ] **DSP-07** Can dither appear without explicit node?
- [ ] **DSP-08** Can sample precision change without evidence?

## 177.4 DSD

- [ ] **DSD-01** Can Native DSD be decoded to PCM by playbin autoplugging?
- [ ] **DSD-02** Can dsdconvert alter rate/channels?
- [ ] **DSD-03** Can unsupported grouping be guessed?
- [ ] **DSD-04** Can DSD significant semantics be shown as PCM bit depth?
- [ ] **DSD-05** Can DSP be accidentally attached to audio/x-dsd?
- [ ] **DSD-06** Can a pause/stop send unsafe noise to a DAC needing DSD silence handling?

## 177.5 DoP

- [ ] **DOP-01** Can marker phase reset mid-stream without DISCONT evidence?
- [ ] **DOP-02** Can channel markers diverge?
- [ ] **DOP-03** Can software volume touch carrier bytes?
- [ ] **DOP-04** Can resampler touch carrier rate?
- [ ] **DOP-05** Can a generic high-rate PCM DAC be mislabeled DoP-capable?
- [ ] **DOP-06** Can seek produce incorrect marker continuity?
- [ ] **DOP-07** Can buffer splitting alter bytes?
- [ ] **DOP-08** Can endianness/24-in-32 alignment be wrong?

## 177.6 Persistence

- [ ] **PERSISTENCE-01** Can stale qualification survive environment change?
- [ ] **PERSISTENCE-02** Can unsupported future profile schema be partially loaded?
- [ ] **PERSISTENCE-03** Can missing IR asset make startup fail globally?
- [ ] **PERSISTENCE-04** Can custom settings be overwritten by updated recommendation?
- [ ] **PERSISTENCE-05** Can raw ALSA locator become persistent identity?

## 177.7 UX

- [ ] **UX-01** Does UNKNOWN look like an error?
- [ ] **UX-02** Does processed audio ever show VERIFIED bit-perfect?
- [ ] **UX-03** Can user enable DSP on DSD without seeing conversion consequence?
- [ ] **UX-04** Can user select Direct while non-GStreamer engine is active without an actionable path?
- [ ] **UX-05** Can popup open block on hardware I/O?
- [ ] **UX-06** Are color-only states avoided?

## 177.8 Security

- [ ] **SECURITY-01** Can malformed IR exhaust memory?
- [ ] **SECURITY-02** Can MAHKB regex cause pathological work?
- [ ] **SECURITY-03** Can LV2 scan arbitrary writable directories by default?
- [ ] **SECURITY-04** Can CamillaDSP control socket bind externally?
- [ ] **SECURITY-05** Can diagnostic bundle leak music paths or DAC serial by default?


---

# 178. IMPLEMENTATION ORDER — COMMITS PEQUEÑOS Y CERRADOS

> **Esta lista es granularidad de commits, no secuencia global.** La fase primaria (`AP2-Fxx`) y sus dependencias se determinan exclusivamente mediante BIBLIA B y las tarjetas 182–201.

No implementar todo en una rama gigantesca. Cada paquete debe producir un commit/PR auditable
y un conjunto de gates antes del siguiente.

```text
AUDIO2-000  Baseline reconciliation + ADR set
AUDIO2-001  Generic evidence primitives
AUDIO2-002  SignalFormat algebra + V3.5 adapters
AUDIO2-003  SignalPath domain without UI
AUDIO2-004  SignalPath query/read model

DSP-010     Processing domain/profile persistence
DSP-020     Compiler + tests
DSP-030     GStreamer processing runtime identity/bypass
DSP-040     preamp + PEQ
DSP-050     IR store + FIR/convolution
DSP-060     resampling/dither explicit nodes
DSP-070     runtime evidence + SignalPath integration
DSP-110     Audio Lab + quick popup
DSP-120     performance/physical qualification
DSP-130     seal

DSD-010     first-class DSD source characterization
DSD-020     exact ALSA DSD qualification
DSD-030     Strict Native DSD sink + runtime inspection
DSD-040     DoP ADR/technology decision
DSD-050     packer + vectors + carrier plan
DSD-060     explicit DSD→PCM seam
DSD-070     family transition coordinator
DSD-080     SignalPath evidence
DSD-090     Device Setup DSD UI
DSD-100     physical qualification
DSD-110     DSP interoperability
DSD-120     seal

UI2-010     NowPlaying quality classification
UI2-020     DAC quick surface
UI2-030     Signal Path quick surface
UI2-040     remove engine selector from NowPlaying + migrate tests
UI2-050     responsive/accessibility/golden seal

AUDIO2-070  full physical/performance qualification
AUDIO2-080  KILLCRITIC audit
AUDIO2-090  final Phase 2 freeze
```

## 178.1 Commit rule

Cada commit de implementación debe declarar:

```text
Purpose
Authorities touched
Files touched
New invariants
Tests added
Tests removed/replaced and why
Backward-compatibility statement
Known limitations
Rollback behavior
Exact suite result
```


---

# 179. DEFINITION OF DONE — PRODUCTO COMPLETO



| Area | Exit criterion |
|---|---|
| Architecture | No duplicate playback/output/volume/proof authorities |
| Architecture | AudioPort remains transport-only |
| Architecture | DSP runtime is replaceable behind application port |
| PCM | Stable PCM Direct regression suite unchanged/green |
| PCM | No hidden resampling/remix/processing |
| DSP | Bypass proven with runtime graph evidence |
| DSP | PEQ compiled and runtime-observed |
| DSP | FIR/convolution asset identity and latency proven |
| DSP | Explicit resampling shown in Signal Path |
| DSP | Live graph replacement failure leaves predecessor coherent |
| DSP | No per-sample Python hot path |
| DSD | DSD source remains first-class after characterization |
| DSD | Native DSD exact ALSA tuple qualification implemented |
| DSD | Native DSD runtime caps observed |
| DSD | Native path cannot silently become PCM |
| DoP | DoP is explicit and never auto-enabled from PCM capability |
| DoP | Byte-for-byte vectors pass |
| DoP | Chunk-boundary invariance passes |
| DoP | Carrier runtime negotiation matches plan |
| DoP | PCM DSP and software volume cannot touch carrier |
| DoP | Device interpretation claim never exceeds evidence |
| DSD→PCM | Conversion is explicit and visible |
| Signal Path | Path verdict and proof state separated |
| Signal Path | Every rendered node has observability semantics |
| Signal Path | Stale generation cannot replace active graph |
| UI | NowPlaying uses DSP/Signal/Quality/DAC/Queue roles without engine quick selector |
| UI | Audio Lab has draft/validate/preview/commit transaction |
| UI | Device Setup has General/Advanced/Expert disclosure |
| UI | Keyboard/focus/reduced-motion contracts pass |
| Persistence | Schemas are versioned and migration-tested |
| Persistence | Runtime truth not persisted as durable proof |
| Security | IR/KB/plugin inputs bounded and validated |
| Performance | No XRUN attributable in declared physical matrix |
| Performance | Published CPU/latency artifact exists |
| Physical | Real Native DSD DAC tested |
| Physical | Real DoP DAC tested |
| Physical | Negative DoP device tested |
| CI | Exact-head verifier GO |
| CI | Full suite green with classified skips only |
| Docs | User-facing semantics match runtime claims |


---

# 180. IMPLEMENTATION COMPLETENESS MAP — QUÉ CÓDIGO EXISTE EN ESTE DOCUMENTO

A diferencia de las primeras versiones, esta especificación ya no se limita a enumerar
componentes. Incluye implementaciones de referencia y contratos concretos para:

```text
✓ SignalFormat algebra
✓ Native DSD signal type
✓ DoP carrier type
✓ DoP pure reference packer
✓ ProcessingGraph domain
✓ PEQ/FIR/convolution/resample/dither nodes
✓ Processing runtime evidence
✓ Generic multi-source evidence resolution
✓ SignalPath graph/domain
✓ V3.5 PCM adapter strategy
✓ processing application port
✓ deterministic ProcessingGraphCompiler
✓ AudioProcessingService transactional owner
✓ DsdPolicyService
✓ Native DSD output planner
✓ DoP output planner
✓ SignalPathService
✓ GStreamer processing runtime contract
✓ Strict Native DSD sink
✓ Rust DoP packer reference
✓ ALSA DSD qualification types
✓ Phase2 source characterizer
✓ CamillaDSP config and boundary
✓ PipeWire filter-chain config and boundary
✓ LV2 future host boundary
✓ NowPlaying QML target grid
✓ AudioProcessingPopup QML
✓ SignalPathPopup QML
✓ SignalPathNode/Connector QML
✓ AudioLabView QML
✓ PeqEditor QML
✓ DSD Device Setup component
✓ SQLite Phase2 schema
✓ IR store implementation
✓ bridge classes
✓ query/projection service
✓ bootstrap order
✓ migration strategy
✓ domain/compiler/policy/transaction/QML tests
✓ CI verifier design
✓ physical qualification protocol
✓ performance budgets
✓ error taxonomy
✓ KILLCRITIC adversarial gate
```

Aun así, la implementación productiva sólo puede comenzar después del gate temporal y debe
reconciliarse con la baseline congelada, especialmente M11.5.


---

# 181. MAPA FINAL DE PRODUCTO — DESDE ARCHIVO HASTA DAC

```text
                                      MICHI MUSIC PLAYER

  LIBRARY / FILE FACTS
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ FLAC / WAV / MP3 / DSF / DFF                                           │
  │ codec · container · nominal rate · bit depth · DSD rate                 │
  └─────────────────────────────────┬───────────────────────────────────────┘
                                    │
                                    ▼
  SOURCE CHARACTERIZATION
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ PCM → PcmSignalFormat                                                   │
  │ DSD → DsdSignalFormat                                                   │
  │ no forced DSD→PCM just to discover the source                           │
  └─────────────────────────────────┬───────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
                    PCM                           DSD
                     │                             │
        ┌────────────┴─────────────┐      ┌────────┼────────────┐
        │                          │      │        │            │
        ▼                          ▼      ▼        ▼            ▼
     DSP OFF                  DSP ACTIVE Native   DoP       DSD→PCM
        │                          │      DSD      │            │
        │                          │      │        │            ▼
        │                          │      │        │        PCM FORMAT
        │                          │      │        │            │
        │                          ▼      │        │            ▼
        │                  ProcessingGraph│        │       ProcessingGraph
        │                  PEQ/FIR/etc    │        │       PEQ/FIR/etc
        │                          │      │        │            │
        └──────────────┬───────────┘      │        │            │
                       │                  │        │            │
                       ▼                  ▼        ▼            ▼
                 OUTPUT PLANNING      Native    DoP carrier   PCM output
                       │               DSD          │            │
                       └───────────────┬────────────┴────────────┘
                                       │
                                       ▼
                               OUTPUT TRANSACTION
                                       │
                                       ▼
                           GStreamer / ALSA / device
                                       │
                                       ▼
                             RUNTIME OBSERVABILITY
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
            SignalTruth          M11.5 Proof        Processing Evidence
                 │                     │                     │
                 └─────────────────────┼─────────────────────┘
                                       ▼
                                SignalPathGraph
                                       │
                     ┌─────────────────┼──────────────────┐
                     ▼                 ▼                  ▼
                NowPlaying          Audio Lab        Device Setup
                     │                 │                  │
                     └─────────────────┴──────────────────┘
                                       │
                                       ▼
                       ONE EXPLAINABLE AUDIO EXPERIENCE
```

Regla final:

```text
SOURCE QUALITY tells what the file is.
PROCESSING tells what Michi intentionally changed.
TRANSPORT tells how the signal is carried.
SIGNAL TRUTH tells what runtime evidence observed.
M11.5 tells whether preservation claims are justified.
SIGNAL PATH explains all of it to the user.
```

------------------------------------------------------------------------

# 182. MANUAL DE EJECUCIÓN POR FASES — AUTORIDAD SOBRE EL ORDEN DE IMPLEMENTACIÓN

Esta sección convierte los work packages distribuidos a lo largo del documento
en **fases ejecutables por agentes con contexto limitado**. El mapa BIBLIA B al
principio del archivo es el índice rápido; las tarjetas de esta sección son el
contrato operativo detallado.

Reglas:

```text
PHASE CARD > memoria del agente
MUST_READ > resumen conversacional
ENTRY GATE no cumplido > fase LOCKED
EXIT GATE incompleto > fase no CLOSED
OPTIONAL subtrack != blocker del core salvo que se active explícitamente
```

Cada tarjeta contiene un `CONTEXT CAPSULE`. Ese capsule permite a un modelo
pequeño recuperar orientación, pero **no sustituye** la lectura de las secciones
`MUST_READ_SECTIONS` relevantes al cambio concreto.

El número de sección es un índice humano y **no es una API de máquina**. El ID `AP2-Fxx` identifica la fase y los `R11-*` contract anchors identifican el contexto normativo estable.

# 183. `phase2_context.py` R11 — CONTEXTO POR ANCHORS ESTABLES, FAIL-CLOSED

<!-- MICHI_PHASE2:CONTRACT:R11-G12-CONTEXT-TOOL:BEGIN -->

R10 indexaba `dict[int, str]` por número de sección. La auditoría encontró dos
headings numerados duplicados; Python habría conservado sólo el último bloque.
Además, varias tarjetas `MUST_READ_SECTIONS` no incluían §§361–380 aunque esas
secciones tenían precedencia superior. Esto es un defecto P0 del mecanismo de
contexto.

R11 deja de usar números de sección como API de máquina.

## 183.1 Formato canónico

```text
&lt;!-- MICHI_PHASE2:CONTRACT:&lt;CONTRACT-ID&gt;:BEGIN --&gt;
... literal contract ...
&lt;!-- MICHI_PHASE2:CONTRACT:&lt;CONTRACT-ID&gt;:END --&gt;
```

Cada tarjeta de fase usa:

```text
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G03-OUTPUT-FAMILIES, R11-F05
```

Los números de sección quedan para navegación humana / trazabilidad histórica.

## 183.2 Modos

```text
orientation
    bootstrap + phase index + phase card
    NO autoriza mutación productiva

implementation [DEFAULT]
    orientation + TODOS los MUST_READ_ANCHORS
    modo mínimo autorizado para editar

deep
    implementation + dependency phase packets
```

No existe un modo productivo que omita el contrato normativo.

## 183.3 Implementación de referencia

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

CANONICAL_NAME = "MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md"
CANONICAL_PATH = Path("docs/audio") / CANONICAL_NAME

PHASE_RE = re.compile(
    r"<!-- MICHI_PHASE2:PHASE:(AP2-F\d{2}):BEGIN -->(.*?)"
    r"<!-- MICHI_PHASE2:PHASE:\1:END -->",
    re.DOTALL,
)
CONTRACT_RE = re.compile(
    r"<!-- MICHI_PHASE2:CONTRACT:([A-Z0-9-]+):BEGIN -->(.*?)"
    r"<!-- MICHI_PHASE2:CONTRACT:\1:END -->",
    re.DOTALL,
)
TOP_SECTION_RE = re.compile(r"^# (\d+)\. ", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class PlanIndex:
    path: Path
    sha256: str
    text: str
    phase_blocks: dict[str, str]
    contracts: dict[str, str]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_spec(repo: Path) -> Path:
    preferred = repo / CANONICAL_PATH
    if preferred.is_file():
        return preferred
    completed = subprocess.run(
        ["git", "-C", str(repo), "ls-files", f"*{CANONICAL_NAME}"],
        check=True, capture_output=True, text=True,
    )
    matches = [
        repo / line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    if len(matches) != 1:
        raise SystemExit(
            "STOP_SPEC_NOT_FOUND" if not matches else "STOP_SPEC_AMBIGUOUS"
        )
    return matches[0]


def _unique_matches(regex: re.Pattern, text: str, kind: str) -> dict[str, str]:
    result: dict[str, str] = {}
    counts: dict[str, int] = {}
    for match in regex.finditer(text):
        key = match.group(1)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 1:
            raise SystemExit(f"STOP_{kind}_DUPLICATE:{key}")
        result[key] = match.group(2).strip()
    return result


def validate_unique_top_level_numbers(text: str) -> None:
    # R11 itself is normalized to unique top-level numeric headings.
    # Fail instead of silently overwriting if a future edit reintroduces one.
    found: dict[int, int] = {}
    for match in TOP_SECTION_RE.finditer(text):
        number = int(match.group(1))
        if number in found:
            raise SystemExit(f"STOP_SPEC_DUPLICATE_SECTION:{number}")
        found[number] = match.start()


def build_index(repo: Path) -> PlanIndex:
    path = resolve_spec(repo)
    data = path.read_bytes()
    text = data.decode("utf-8")
    validate_unique_top_level_numbers(text)
    phases = _unique_matches(PHASE_RE, text, "PHASE")
    contracts = _unique_matches(CONTRACT_RE, text, "CONTRACT")
    if not contracts:
        raise SystemExit("STOP_CONTRACT_INDEX_EMPTY")
    return PlanIndex(
        path=path,
        sha256=digest_bytes(data),
        text=text,
        phase_blocks=phases,
        contracts=contracts,
    )


def bounded_block(text: str, begin: str, end: str, code: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise SystemExit(code)
    return text.split(begin, 1)[1].split(end, 1)[0].strip()


def parse_csv_field(block: str, key: str) -> tuple[str, ...]:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", block, re.MULTILINE)
    if match is None:
        return ()
    return tuple(x.strip() for x in match.group(1).split(",") if x.strip())


def must_read_anchors(block: str) -> tuple[str, ...]:
    anchors = parse_csv_field(block, "MUST_READ_ANCHORS")
    if not anchors:
        raise SystemExit("STOP_PHASE_MUST_READ_ANCHORS_EMPTY")
    return anchors


def dependencies(block: str) -> tuple[str, ...]:
    return tuple(
        x for x in parse_csv_field(block, "DEPENDENCIES")
        if x.startswith("AP2-F")
    )


def emit_contract(index: PlanIndex, anchor: str) -> str:
    block = index.contracts.get(anchor)
    if block is None:
        raise SystemExit(f"STOP_CONTRACT_MISSING:{anchor}")
    return f"## CONTRACT {anchor}\n{block}"


def emit_context(index: PlanIndex, phase: str, mode: str) -> str:
    phase_block = index.phase_blocks.get(phase)
    if phase_block is None:
        raise SystemExit("STOP_PHASE_UNKNOWN")

    chunks = [
        "# PHASE2 R11 CONTEXT PACK",
        f"SPEC_PATH: {index.path}",
        f"SPEC_SHA256: {index.sha256}",
        "MODE: " + mode,
        "\n## BOOTSTRAP\n" + bounded_block(
            index.text,
            "<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->",
            "<!-- MICHI_PHASE2:BOOTSTRAP:END -->",
            "STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID",
        ),
        f"\n## PRIMARY PHASE {phase}\n{phase_block}",
    ]

    if mode == "orientation":
        chunks.append(
            "\n# ORIENTATION_ONLY\n"
            "PRODUCTIVE_MUTATION_ALLOWED: FALSE\n"
            "Run --mode implementation before editing."
        )
        return "\n\n".join(chunks)

    seen: set[str] = set()
    for anchor in must_read_anchors(phase_block):
        if anchor in seen:
            continue
        chunks.append("\n" + emit_contract(index, anchor))
        seen.add(anchor)

    if mode == "deep":
        for dep in dependencies(phase_block):
            dep_block = index.phase_blocks.get(dep)
            if dep_block is None:
                raise SystemExit(f"STOP_DEPENDENCY_PHASE_MISSING:{dep}")
            chunks.append(f"\n## DEPENDENCY PHASE {dep}\n{dep_block}")
            for anchor in must_read_anchors(dep_block):
                if anchor not in seen:
                    chunks.append("\n" + emit_contract(index, anchor))
                    seen.add(anchor)

    chunks.append("\nPRODUCTIVE_MUTATION_ALLOWED: TRUE")
    return "\n\n".join(chunks)


def receipt(index: PlanIndex, phase: str) -> dict[str, object]:
    block = index.phase_blocks.get(phase)
    if block is None:
        raise SystemExit("STOP_PHASE_UNKNOWN")
    anchors = must_read_anchors(block)
    for anchor in anchors:
        if anchor not in index.contracts:
            raise SystemExit(f"STOP_CONTRACT_MISSING:{anchor}")
    contract_material = "\n".join(
        f"{anchor}\n{index.contracts[anchor]}" for anchor in anchors
    ).encode()
    return {
        "spec_path": str(index.path),
        "spec_sha256": index.sha256,
        "primary_phase": phase,
        "dependencies": dependencies(block),
        "must_read_anchors": anchors,
        "contract_set_sha256": digest_bytes(contract_material),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--mode",
        choices=("orientation", "implementation", "deep"),
        default="implementation",
    )
    parser.add_argument("--receipt-json", action="store_true")
    args = parser.parse_args()

    index = build_index(Path(args.repo).resolve())
    if args.receipt_json:
        print(json.dumps(receipt(index, args.phase), indent=2))
        return
    print(emit_context(index, args.phase, args.mode))


if __name__ == "__main__":
    main()
```

## 183.4 Mandatory extractor gates

```text
CTX-01 duplicate top-level number -> STOP_SPEC_DUPLICATE_SECTION
CTX-02 duplicate contract anchor -> STOP_CONTRACT_DUPLICATE
CTX-03 duplicate phase anchor -> STOP_PHASE_DUPLICATE
CTX-04 missing MUST_READ anchor -> STOP_CONTRACT_MISSING
CTX-05 orientation emits PRODUCTIVE_MUTATION_ALLOWED=FALSE
CTX-06 implementation contains every declared anchor exactly once
CTX-07 deep includes dependencies without duplicate contract material
CTX-08 deterministic byte-for-byte output for same spec/phase/mode
CTX-09 receipt contract_set_sha256 changes when any required contract changes
CTX-10 no `dict[int, section]` lookup remains
```

`MUST_READ_SECTIONS` may remain in historical cards only as traceability. It is
not an execution interface after R11.

---
<!-- MICHI_PHASE2:CONTRACT:R11-G12-CONTEXT-TOOL:END -->

# 184. `PHASE2_STATE.json` — ESTADO PEQUEÑO, BIBLIA GRANDE

Cuando F00 se active, crear un archivo de estado deliberadamente pequeño y
parseable con Python stdlib, sin introducir una dependencia YAML sólo para la
gobernanza del agente:

```text
docs/audio/phase2/PHASE2_STATE.json
```

Ejemplo:

```json
{
  "schema_version": 1,
  "spec": {
    "path": "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md",
    "sha256_at_last_transition": "runtime-computed"
  },
  "baseline": {
    "git_commit": "<frozen commit>",
    "manifest": "docs/audio/phase2/audio_phase2_baseline.json"
  },
  "active_phases": ["AP2-F01"],
  "phases": {
    "AP2-F00": "CLOSED",
    "AP2-F01": "ACTIVE",
    "AP2-F02": "LOCKED",
    "AP2-F03": "LOCKED",
    "AP2-F04": "LOCKED",
    "AP2-F05": "LOCKED",
    "AP2-F06": "LOCKED",
    "AP2-F07": "LOCKED",
    "AP2-F08": "LOCKED",
    "AP2-F09": "LOCKED",
    "AP2-F10": "LOCKED",
    "AP2-F11": "LOCKED",
    "AP2-F12": "LOCKED",
    "AP2-F13": "LOCKED",
    "AP2-F14": "LOCKED",
    "AP2-F15": "LOCKED"
  }
}
```

`PHASE2_STATE.json` **no contiene requisitos**. Sólo indica dónde está la Biblia,
qué baseline está activa y qué fases están abiertas/cerradas. Si contradice este
archivo, se detiene la implementación.

Estados se cambian en commits explícitos y sólo después de que el exit gate de
la fase anterior haya producido evidencia. Un agente no puede desbloquear su
propia siguiente fase simplemente porque necesita tocar esos archivos.

# 185. PROTOCOLO DE HANDOFF ENTRE MODELOS / AGENTES

Un handoff correcto debe incluir:

```text
HANDOFF_PHASE2
PRIMARY_PHASE=<AP2-Fxx>
SPEC_PATH=<...>
SPEC_SHA256=<...>
BASELINE_SHA=<...>
COMPLETED_WORK=<commits/files>
TESTS_RUN=<commands/results>
OPEN_FAILURES=<typed list>
NEXT_ALLOWED_STEP=<one bounded intent>
MUST_REREAD=<phase card + normative sections>
```

El receptor debe ignorar cualquier afirmación del handoff que contradiga una
relectura del plan o del código actual.

Un handoff **no** debe incluir una copia resumida del contrato como sustituto de
la Biblia. Debe apuntar a ella.


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F00:BEGIN -->

# 186. AP2-F00 — ACTIVATION, BASELINE FREEZE Y MANIFEST DE AUTORIDAD

PHASE_ID: AP2-F00
DEPENDENCIES: NONE
MUST_READ_SECTIONS: 0, 26, 67, 118, 128, 174, 176, 177, 178, 179
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G01-CURRENT-REPO, R11-G08-TEST-AUTHORITY, R11-G11-PATCH-PROTOCOL, R11-G12-CONTEXT-TOOL, R11-G13-ALIGNMENT, R11-F00
WORK_PACKAGES: P2-000

## 186.1 Propósito

Congelar la única baseline desde la cual Audio Phase 2 puede existir. Esta fase no agrega DSP, DSD, DoP ni UI; establece el suelo factual, las versiones, las suites y las autoridades que las fases posteriores tienen prohibido reabrir.

## 186.2 Entry gate

- M11.4 reconciliado contra V3.5 vigente: software PCM closure preservada y gates físicos requeridos por la baseline cerrados con evidencia machine-readable.
- Bounded SMSL DAC-V35-110 preservado; R24/R25/R32/R35/R36 nunca se promueven desde `NOT_RUN`.
- M11.5 IMPLEMENTED / TESTED con proof/gapless/DSD transition contracts congelados.
- DAC-V35-140 vs Audio Phase2 DSD/DoP ownership reconciliado; zero duplicate runtime.
- Cero P0/P1 heredados y full suite verde en el commit exacto.

Si una condición no se puede demostrar:

```text
AP2-F00 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 186.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F00
MUST_READ_SECTIONS = 0, 26, 67, 118, 128, 174, 176, 177, 178, 179
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md`
- `docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md`
- `docs/STATUS_MATRIX.md`
- `docs/MASTER_ROADMAP_1.0.md`
- `docs/ARCHITECTURE.md`
- `docs/adr/0007-multi-engine-audio-runtime.md`
- `scripts/verify_dac_m11_4.py`
- `pyproject.toml`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 186.4 Outputs obligatorios

- `audio_phase2_baseline.json` con commit, versiones, suites y artefactos.
- `AGENTS.md` actualizado con el hook obligatorio de lectura Phase 2 (sólo al activar F00).
- `scripts/verify_audio_phase2_repository_alignment.py` instalado y verde.
- ADR de activación que cambia el plan de DEFERRED a READY.
- Ruta canónica del plan registrada y verificada.
- Estado inicial de fases con AP2-F01 READY y el resto LOCKED.

## 186.5 Cambios prohibidos en esta fase

- No modificar playback/output para “preparar” Phase 2.
- No migrar schemas productivos.
- No crear clases Phase 2 conectadas en bootstrap.
- No declarar capacidades que no estén en artefactos de baseline.

## 186.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 186.7 Acceptance / exit gate

- El manifest reproduce el mismo HEAD y entorno declarado.
- Los verificadores cerrados de V3.5/M11.5 siguen verdes.
- El plan y ADR no contienen contradicciones sin resolver.
- Se puede reconstruir exactamente qué baseline fue congelada.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 186.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> La fase F00 es puramente de gobernanza y congelación. Si el agente está escribiendo lógica de audio en esta fase, está fuera de scope. El producto de F00 es una baseline auditable, no una feature.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 186.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F00
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F00:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F01:BEGIN -->

# 187. AP2-F01 — FOUNDATION DE AUTORIDADES, TIPOS Y COMPATIBILIDAD CON V3.5

PHASE_ID: AP2-F01
DEPENDENCIES: AP2-F00
MUST_READ_SECTIONS: 3, 20, 28, 67, 69, 70, 94, 118, 119, 121, 126, 128, 129
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G08-TEST-AUTHORITY, R11-F01
WORK_PACKAGES: DSP-000; DSD-000 (tipos); P2-020 (primitivas compartidas)

## 187.1 Propósito

Crear las fronteras de dominio que permiten PCM, DSD, DoP, DSP y provenance sin reescribir V3.5. Aquí se decide quién posee cada estado, cómo se adaptan los tipos legacy y qué contratos siguen siendo inmutables.

## 187.2 Entry gate

- Baseline F00 identificada por commit y manifest.
- Todos los tipos legacy relevantes inspeccionados en el HEAD congelado.
- No hay work package de V3.5 abierto.

Si una condición no se puede demostrar:

```text
AP2-F01 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 187.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F01
MUST_READ_SECTIONS = 3, 20, 28, 67, 69, 70, 94, 118, 119, 121, 126, 128, 129
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/domain/audio_output.py`
- `src/michi/domain/audio_evidence.py`
- `src/michi/domain/signal_truth.py`
- `src/michi/application/audio_output_ports.py`
- `src/michi/application/audio_output_planner.py`
- `src/michi/application/output_session_service.py`
- `docs/ARCHITECTURE.md`
- `docs/adr/0007-multi-engine-audio-runtime.md`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 187.4 Outputs obligatorios

- ADR “Audio Processing no es un cuarto AudioEngine”.
- `SignalFormat` algebra first-class y adapters desde `PcmTuple`.
- Primitive de evidencia multifuentе sin colisión con `CapabilityEvidence`.
- Puertos futuros separados de `AudioPort`.
- Mapa de ownership validado por tests de arquitectura.

## 187.5 Cambios prohibidos en esta fase

- No big-bang rewrite de `OutputPlan`.
- No meter DSD/DSP en `AudioPort`.
- No crear un segundo `SignalTruthRecorder`.
- No crear un segundo planner o volume authority.

## 187.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 187.7 Acceptance / exit gate

- Paridad PCM legacy probada.
- Imports mantienen dirección de capas.
- Tipos nuevos son Python puro en domain.
- Ningún wiring productivo nuevo aún requerido.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 187.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F01 establece lenguaje y ownership. Debe ser posible compilar y testear los nuevos tipos sin que cambie un solo comportamiento PCM productivo de V3.5.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 187.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F01
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F01:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F02:BEGIN -->

# 188. AP2-F02 — DEVICE KNOWLEDGE, CLASIFICACIÓN, IDENTIDAD Y CAPABILITIES

PHASE_ID: AP2-F02
DEPENDENCIES: AP2-F01
MUST_READ_SECTIONS: 4, 5, 6, 7, 8, 9, 31, 32, 33, 35, 36, 39, 40, 41, 42, 43, 45, 46, 47, 94, 126, 158
MUST_READ_ANCHORS: R11-G01-CURRENT-REPO, R11-G02-AUTHORITY-MAP, R11-G09-LEGACY-RESEARCH, R11-F02
WORK_PACKAGES: P2-010, P2-020, P2-030, P2-040, P2-050, P2-060

## 188.1 Propósito

Convertir el discovery técnico amplio de Linux en una representación de hardware estricta, explicable y reusable, sin cambiar stable identity ni usar una base externa como runtime authority.

## 188.2 Entry gate

- F01 primitives cerradas.
- Identidad V3.5 y generation semantics entendidas.
- Licencias de datasets a importar investigadas antes de P2-030.

Si una condición no se puede demostrar:

```text
AP2-F02 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 188.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F02
MUST_READ_SECTIONS = 4, 5, 6, 7, 8, 9, 31, 32, 33, 35, 36, 39, 40, 41, 42, 43, 45, 46, 47, 94, 126, 158
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/application/audio_device_registry.py`
- `src/michi/domain/audio_device.py`
- `src/michi/application/dac_qualification_service.py`
- `src/michi/infrastructure/audio_devices/`
- `src/michi/infrastructure/sqlite_audio_output_repository.py`
- `resources/audio_hardware/ (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 188.4 Outputs obligatorios

- `AudioDeviceClassifier`.
- `EvidenceRecord`/`ResolvedEvidenceValue` consumidos por device intelligence.
- MAHKB versionada y fail-soft.
- `DacIdentityResolver`.
- `ResolvedCapability` con DECLARED/OBSERVED/QUALIFIED/RUNTIME.
- Fingerprinting versionado y no autoritativo.

## 188.5 Cambios prohibidos en esta fase

- No cambiar `stable_device_id` por commercial identity.
- No ocultar un DAC sólo porque aún no esté cualificado.
- No usar `USER_OVERRIDE` como hardware evidence.
- No promover community reports a configuración automática.

## 188.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 188.7 Acceptance / exit gate

- Fixtures de USB DAC, HDMI, internal, virtual, capture-only y multi-endpoint.
- Dos DAC idénticos con/sin serial se resuelven sin inventar certeza.
- MAHKB corrupta no bloquea playback.
- Una capability runtime no destruye conocimiento histórico de capability.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 188.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F02 trata conocimiento de hardware, no playback. “Visible como DAC” y “habilitado para Direct” son decisiones distintas. Runtime tiene autoridad sobre el estado actual, no sobre el máximo histórico del dispositivo.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 188.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F02
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F02:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F03:BEGIN -->

# 189. AP2-F03 — SIGNAL PATH GRAPH Y PROYECCIÓN DE PROOF

PHASE_ID: AP2-F03
DEPENDENCIES: AP2-F01
MUST_READ_SECTIONS: 10, 11, 12, 16, 24, 37, 57, 60, 91, 92, 93, 94, 127, 135, 149, 150, 151, 152, 161, 162, 228, 252
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-F03
WORK_PACKAGES: P2-070, P2-080, P2-090, P2-100

## 189.1 Propósito

Crear una explicación estructurada, generation-safe y multifase del camino de señal. M11.5 sigue verificando preservación; Phase 2 correlaciona evidencia y la hace navegable.

## 189.2 Entry gate

- F01 types/authority cerrados.
- Contrato final M11.5 disponible.
- Signal Truth baseline estable y sin work packages abiertos.

Si una condición no se puede demostrar:

```text
AP2-F03 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 189.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F03
MUST_READ_SECTIONS = 10, 11, 12, 16, 24, 37, 57, 60, 91, 92, 93, 94, 127, 135, 149, 150, 151, 152, 161, 162
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/domain/signal_truth.py`
- `src/michi/infrastructure/audio_output/runtime_inspector.py`
- `src/michi/infrastructure/audio_output/direct_output_executor.py`
- `src/michi/presentation/audio_output_bridge.py`
- `src/michi/presentation/qml/components/SignalTruthPanel.qml`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 189.4 Outputs obligatorios

- `SignalPathIdentity`, `SignalNode`, `SignalEdge`, `SignalPathSnapshot`.
- Observability states distintos de UNKNOWN.
- Adapter desde Signal Truth/M11.5 proof a graph, sin segunda autoridad.
- `SignalPathService` framework-free.
- Read model inicial sin QML final.

## 189.5 Cambios prohibidos en esta fase

- No decidir `BitPerfectState` de nuevo.
- No inventar nodos para completar una cadena estética.
- No confundir path verdict con proof state.
- No usar metadata para rellenar runtime significant bits.

## 189.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 189.7 Acceptance / exit gate

- Stale generations nunca reemplazan snapshot activo.
- Missing evidence queda visible.
- Qt/MPD pueden declarar NOT_OBSERVABLE honestamente.
- Direct/GStreamer preserva provenance por nodo.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 189.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> SignalTruth clasifica hechos runtime; M11.5 decide proof; SignalPathGraph explica. Estas tres responsabilidades permanecen separadas aunque se presenten juntas.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 189.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F03
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F03:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F04:BEGIN -->

# 190. AP2-F04 — DSP DOMAIN, PROCESSING GRAPH Y COMPILADOR DETERMINISTA

PHASE_ID: AP2-F04
DEPENDENCIES: AP2-F01
MUST_READ_SECTIONS: 48, 69, 71, 72, 73, 75, 76, 77, 78, 79, 124, 125, 129, 130, 131
MUST_READ_ANCHORS: R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-G09-LEGACY-RESEARCH, R11-F04
WORK_PACKAGES: DSP-000, DSP-010, DSP-020

## 190.1 Propósito

Definir DSP como una política/graph independiente del engine, compilarla a un plan inmutable y cerrar semántica antes de tocar GStreamer.

## 190.2 Entry gate

- F01 ownership cerrado.
- PCM compatibility adapter disponible.
- No runtime executor conectado.

Si una condición no se puede demostrar:

```text
AP2-F04 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 190.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F04
MUST_READ_SECTIONS = 48, 69, 71, 72, 73, 75, 76, 77, 78, 79, 124, 125, 129, 130, 131
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/domain/audio_processing.py (target)`
- `src/michi/domain/audio_processing_evidence.py (target)`
- `src/michi/application/audio_processing_ports.py (target)`
- `src/michi/application/processing_graph_compiler.py (target)`
- `src/michi/application/audio_processing_service.py (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 190.4 Outputs obligatorios

- `ProcessingProfile`, `ProcessingGraph`, node types y IDs estables.
- `ProcessingPlan` determinista.
- Validación de orden, canales, sample-rate y headroom.
- Transacción del `AudioProcessingService` con revision/generation.
- Puertos de ejecución sin tipos Gst.

## 190.5 Cambios prohibidos en esta fase

- No crear `AudioEngine.DSP`.
- No hacer I/O en compiler/domain.
- No aceptar DoP carrier como PCM DSP.
- No modificar runtime desde QML.

## 190.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 190.7 Acceptance / exit gate

- Mismo profile + mismas facts = mismo plan.
- Graph inválido falla antes del runtime.
- Bypass explícito conserva identidad.
- DSD Preserve DSD rechaza DSP en policy layer.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 190.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F04 es dominio y aplicación pura. La salida es un ProcessingPlan, no sonido. Si GStreamer aparece en imports de domain/application contracts, el diseño está roto.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 190.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F04
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F04:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F05:BEGIN -->

# 191. AP2-F05 — PCM DSP RUNTIME EN GSTREAMER Y EVIDENCIA TRANSACCIONAL

PHASE_ID: AP2-F05
DEPENDENCIES: AP2-F04
MUST_READ_SECTIONS: 74, 75, 76, 77, 78, 79, 91, 96, 97, 98, 103, 107, 136, 145, 165, 166, 169, 218, 219, 220, 223, 224, 248, 249, 250
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-G08-TEST-AUTHORITY, R11-F05
WORK_PACKAGES: DSP-030, DSP-040, DSP-050, DSP-060, DSP-070

## 191.1 Propósito

Ejecutar ProcessingPlan PCM mediante GStreamer sin comprometer el owner thread, sin reemplazar AudioPort y con swap atómico/bypass verificable.

F05 ejecuta la fase nativa DENTRO del proceso GStreamer Output Host
(`gstreamer_host_process`), que ya es la frontera productiva de todo el
lifecycle nativo. El parent conserva la autoridad semántica (ProcessingGraph,
Compiler, CompiledProcessingPlan, AudioProcessingService, Signal Truth, Signal
Path) y NO instancia objetos Gst productivos.

## 191.2 Entry gate

- F04 plan/compiler cerrado.
- GStreamer baseline exacta identificada.
- Threading rules y custom MainContext baseline revisados.

Si una condición no se puede demostrar:

```text
AP2-F05 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 191.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F05
MUST_READ_SECTIONS = 74, 75, 76, 77, 78, 79, 91, 96, 97, 98, 103, 107, 136, 145, 165, 166, 169
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/infrastructure/audio_engines/gstreamer.py` — CHILD-NATIVE: corre
  únicamente dentro del host.
- `src/michi/infrastructure/audio_processing/gstreamer_processing.py (target)`
  — CHILD-NATIVE: builder/runtime del candidate nativo.
- `src/michi/infrastructure/audio_processing/gstreamer_capabilities.py (target)`
  — CHILD-NATIVE: probe real de factories dentro del host.
- `src/michi/infrastructure/audio_engines/gstreamer_host_protocol.py`
- `src/michi/infrastructure/audio_engines/gstreamer_host_session.py`
- `src/michi/infrastructure/audio_engines/gstreamer_host_process.py`
  — superficie de integración IPC del processing (contrato DTO + comandos).
- `src/michi/application/audio_processing_service.py (target)` — PARENT:
  autoridad semántica; nunca toca Gst.
- `src/michi/infrastructure/audio_output/runtime_inspector.py`
- `src/michi/domain/signal_truth.py`
- `tests/test_gstreamer_audio_port.py`
- `tests/audio_phase2/` (targets host-aware de processing)

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio. La regla de ownership es:

```text
PRODUCTIVE PARENT Gst OBJECT COUNT = 0
```

Ningún módulo marcado CHILD-NATIVE puede importarse en la composición
productiva del parent ni instanciar Gst.Element/Gst.Bin.

## 191.4 Outputs obligatorios

- GStreamer processing bin/builder.
- Transacción prepare→preroll→validate→commit→retire.
- Runtime evidence por node.
- BYPASS y ACTIVE truth observables.
- Rollback seguro cuando el candidate falla.

## 191.5 Cambios prohibidos en esta fase

- No mutar graph desde callback RT.
- No hacer filesystem/SQLite en pump thread.
- No autoinsertar resampler/converter sin evidencia/policy.
- No reutilizar `Strict Direct` como si processing estuviera permitido.
- No instanciar Gst.Element/Gst.Bin/igualadores/converters productivos en el
  proceso parent: la ejecución nativa vive en el GStreamer Output Host.
- No crear un segundo AudioPort, un segundo host GStreamer, ni un segundo
  SignalTruthRecorder.
- No commitear estado efectivo de processing en el child: el child sólo
  construye, prerollea y REPORTAt hechos; el parent compara y commitea.

## 191.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 191.7 Acceptance / exit gate

- Golden signals PEQ/FIR/gain pasan.
- Swap de graph no publica candidate antes de commit.
- Stale completion descartado.
- No XRUN/teardown regression en suite declarada.
- Readback-first ATRAVIESA la frontera de proceso: el parent commitea la
  revisión efectiva sólo después de comparar expected vs observed reportado
  por el host (nunca "IPC enviado = éxito").
- Pérdida del host durante playback procesado invalida la evidencia runtime
  (requested != effective) y nunca deja EQ/Convolution/Processing ACTIVE en
  Signal Truth.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 191.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F05 convierte un ProcessingPlan ya validado en runtime. El executor ejecuta; nunca inventa policy. Toda transformación activa debe producir evidencia y verse en Signal Path.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 191.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F05
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

## 191.10 Ejecución host-aware (preflight seal 2026-10-05)

El GST_LIFECYCLE_GATE quedó PASS con el GStreamer Output Host supervisado: todo
el lifecycle nativo productivo (pipeline, playbin3, sink, GLib/GstBus, teardown)
corre en un proceso hijo killable y el parent conserva la autoridad semántica.
F05 se ejecuta SOBRE esa frontera, nunca alrededor de ella.

Autoridad (freeze):

```text
PARENT (semántica)
  ProcessingProfile / ProcessingGraph
  ProcessingGraphCompiler -> CompiledProcessingPlan
  AudioProcessingService
  ProcessingSampleContract
  validación, expected graph
  comparación expected/observed
  commit de revisión efectiva
  Signal Truth / Signal Path
  política de persistencia

CHILD (GStreamer Output Host)
  Gst.Elements del processing graph
  Gst.Bin / pads / caps nativos
  preroll nativo
  property/caps readback nativo
  observaciones runtime primitivas

CHILD NO POSEE
  policy de processing, perfil efectivo, SignalTruthRecorder,
  PlaybackService, OutputSessionService, selección de usuario,
  compilación semántica del plan
```

Secuencia transaccional (readback-first a través de IPC):

```text
PARENT  compila candidate + asigna processing_generation
PARENT  -> CHILD: PREPARE_PROCESSING_CANDIDATE (DTO bounded, sin audio)
CHILD   construye el graph nativo en quiescent, prerollea
CHILD   inspecciona runtime (factories, caps negociados, properties)
CHILD   -> PARENT: observación runtime primitiva
PARENT  compara expected vs observed
        mismatch -> ABORT del candidate (predecessor intacto si no cruzó
                    el boundary destructivo)
        match    -> autoriza COMMIT
CHILD   activa el candidate
CHILD   -> PARENT: receipt de commit
PARENT  publica revisión efectiva (nunca antes)
```

Modelo de generaciones (sin ambigüedad):

```text
HOST_GENERATION        encarnación del proceso host
PIPELINE_GENERATION    ejecución de transporte vigente
PROCESSING_GENERATION  candidate/revisión de processing
```

Un resultado de evidencia es vigente sólo si las TRES autoridades siguen
coincidiendo; una intención nueva del usuario siempre gana.

Seam IPC (vocabulario reservado; implementar sólo cuando la fase lo requiera):

```text
PREPARE_PROCESSING_CANDIDATE
INSPECT_PROCESSING_CANDIDATE
COMMIT_PROCESSING_CANDIDATE
ABORT_PROCESSING_CANDIDATE
BYPASS_PROCESSING
QUERY_PROCESSING_RUNTIME
```

Reglas del seam:

- protocol version + host_generation + pipeline_generation +
  processing_generation + candidate identity + payload bounded.
- NUNCA transporta muestras PCM/DSD, objetos Gst/QObject ni callbacks.
- rechazo tipado y evidencia con identidad de readback.

Pérdida del host durante processing activo:

```text
evidencia runtime deja de ser vigente
parent retira/invalida la revisión efectiva
requested != effective
no autoplay, no falso ACTIVE
```

La caracterización de fuente productiva (preflight 2026-10-05) queda sellada
como single-flight, cancelable y owner-responsive; su flip completamente
asíncrono pertenece a la implementación F05 junto con su propio contrato.


<!-- MICHI_PHASE2:PHASE:AP2-F05:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F06:BEGIN -->

# 192. AP2-F06 — DSP FEATURE COMPLETENESS Y EXECUTORS OPCIONALES

PHASE_ID: AP2-F06
DEPENDENCIES: AP2-F05
MUST_READ_SECTIONS: 75, 76, 77, 78, 79, 80, 81, 82, 98, 103, 107, 141, 142, 143, 153, 154, 159, 218, 219, 220, 223, 224, 248, 249, 250, 262
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-F06
WORK_PACKAGES: DSP-040..DSP-100; DSP-110 sólo UI en F11

## 192.1 Propósito

Cerrar el core audiófilo de procesamiento: PEQ, headroom, FIR/convolution, resampling explícito, dither y adapters opcionales detrás del mismo contrato.

## 192.2 Entry gate

- PCM DSP runtime estable.
- Evidence y latency model activos.
- IR store contract definido antes de convolution.

Si una condición no se puede demostrar:

```text
AP2-F06 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 192.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F06
MUST_READ_SECTIONS = 75, 76, 77, 78, 79, 80, 81, 82, 98, 103, 107, 141, 142, 143, 153, 154, 159
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/infrastructure/audio_processing/gstreamer_processing.py (target)`
- `src/michi/infrastructure/audio_processing/camilladsp.py (target/optional)`
- `src/michi/infrastructure/audio_processing/pipewire_filter_chain.py (target/optional)`
- `src/michi/application/ir_store.py (target)`
- `resources/ir/ (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 192.4 Outputs obligatorios

- PEQ con frecuencia/Q/gain tipados.
- FIR/convolution con IR content-addressed.
- Resampling explícito con quality policy.
- Dither sólo en reducciones justificadas.
- Feasibility/adapter CamillaDSP y Shared PipeWire sin asumir paridad.
- LV2 queda detrás de research gate.

## 192.5 Cambios prohibidos en esta fase

- No procesamiento creativo por defecto.
- No procesar Native DSD/DoP.
- No descargar IRs ni plugins durante playback.
- No hacer que un sidecar posea PlaybackState.

## 192.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 192.7 Acceptance / exit gate

- BYPASS identity tests.
- Convolution contra referencia numérica.
- Resampler sólo aparece cuando policy lo solicita.
- Adapter opcional ausente no rompe core.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 192.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F06 completa funciones DSP sin cambiar ownership. GStreamer sigue siendo core recomendado; CamillaDSP/PipeWire/LV2 son executors o research gates, nunca nuevas autoridades.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 192.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F06
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F06:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F07:BEGIN -->

# 193. AP2-F07 — DSD FIRST-CLASS: SOURCE TRUTH Y QUALIFICATION

PHASE_ID: AP2-F07
DEPENDENCIES: AP2-F01, AP2-F02, AP2-F03
MUST_READ_SECTIONS: 13, 70, 83, 85, 88, 94, 104, 106, 121, 122, 123, 139, 140, 210, 211, 212, 213, 214, 245, 246, 262
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-F07
WORK_PACKAGES: DSD-000, DSD-010, DSD-020

## 193.1 Propósito

Dejar de caracterizar DSD como “algo que termina en PCM”. La fuente, capabilities y probes DSD deben existir como tipos y evidencia propios antes de construir Native DSD o DoP.

## 193.2 Entry gate

- F01 SignalFormat estable.
- GStreamer runtime target revalidado para `audio/x-dsd`.
- ALSA enums/formats revalidados en el sistema soportado.

Si una condición no se puede demostrar:

```text
AP2-F07 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 193.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F07
MUST_READ_SECTIONS = 13, 70, 83, 85, 88, 94, 104, 106, 121, 122, 123, 139, 140
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/domain/audio_signal.py (target)`
- `src/michi/domain/dsd.py (target)`
- `src/michi/infrastructure/audio_engines/gstreamer.py`
- `src/michi/application/dac_qualification_service.py`
- `src/michi/infrastructure/audio_devices/alsa_ctypes.py`
- `tests/dsd/ (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 193.4 Outputs obligatorios

- `DsdSignalFormat` normalizado.
- Source characterizer DSD que no fuerza DSD→PCM.
- Qualification exacta de DSD transport cuando sea observable.
- DSD rates/grouping/layout explícitos.
- Evidence separa support unknown de unsupported.

## 193.5 Cambios prohibidos en esta fase

- No inferir DSD support desde filename.
- No llamar PCM a DSD después de demux.
- No promover marketing a capability.
- No iniciar todavía playback Native DSD.

## 193.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 193.7 Acceptance / exit gate

- DSF/DFF fixtures dan DSD source truth.
- Source characterization PCM legacy conserva paridad.
- Busy/timeout/remove no producen negative capability.
- Unsupported real y Unknown quedan diferenciados.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 193.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F07 crea verdad DSD antes del output. Ningún sink Native DSD ni DoP debe construirse sobre una fuente cuya codificación real no esté demostrada.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 193.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F07
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F07:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F08:BEGIN -->

# 194. AP2-F08 — NATIVE DSD RUNTIME ESTRICTO

PHASE_ID: AP2-F08
DEPENDENCIES: AP2-F07
MUST_READ_SECTIONS: 84, 88, 90, 101, 102, 104, 106, 137, 139, 144, 210, 211, 213, 214, 225, 246
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-F08
WORK_PACKAGES: DSD-030

## 194.1 Propósito

Ejecutar DSD nativo como un path separado, con caps DSD reales, exact binding y fail-closed si aparece una conversión o negociación no demostrada.

## 194.2 Entry gate

- DSD source truth y qualification cerradas.
- Device seleccionado con capability evidence suficiente.
- GStreamer/ALSA support del entorno demostrado.

Si una condición no se puede demostrar:

```text
AP2-F08 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 194.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F08
MUST_READ_SECTIONS = 84, 88, 90, 101, 102, 104, 106, 137, 139, 144
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/infrastructure/audio_output/strict_dsd_sink.py (target)`
- `src/michi/application/dsd_output_planner.py (target)`
- `src/michi/infrastructure/audio_engines/gstreamer.py`
- `src/michi/infrastructure/audio_output/direct_output_executor.py`
- `tests/dsd/test_native_dsd_* (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 194.4 Outputs obligatorios

- `NativeDsdOutputPlan`.
- `StrictDsdSinkRecipe`.
- GStreamer branch inspector para `audio/x-dsd`.
- Runtime evidence DSD.
- Lifecycle stop/pause/reconfigure definido.

## 194.5 Cambios prohibidos en esta fase

- No reutilizar `PcmTuple` como identidad DSD.
- No convertir a PCM silenciosamente.
- No insertar DSP.
- No asumir que `dsdconvert` implica pérdida si sólo cambia grouping/layout/bit order preservando DSD.

## 194.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 194.7 Acceptance / exit gate

- Selected branch sigue siendo DSD hasta sink.
- Binding/device generation validada.
- Conversión inesperada produce refusal/contradiction.
- Hotplug y stop no dejan stale DSD truth.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 194.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> Native DSD es una ruta de transporte propia. “GStreamer puede DSD” no prueba que el branch actual sea DSD: Michi debe observarlo y validar exactamente el sink seleccionado.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 194.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F08
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F08:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F09:BEGIN -->

# 195. AP2-F09 — DOP: PACKER, CARRIER, PLANNER Y RUNTIME

PHASE_ID: AP2-F09
DEPENDENCIES: AP2-F07, AP2-F08
MUST_READ_SECTIONS: 86, 87, 88, 101, 105, 106, 123, 134, 138, 139, 144, 210, 215, 216, 217, 226, 247, 262
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-G09-LEGACY-RESEARCH, R11-F09
WORK_PACKAGES: DSD-040, DSD-050

## 195.1 Propósito

Implementar DoP como carrier explícito y byte-verificado, sin confundir framing PCM-compatible con contenido PCM ni asumir que el DAC cambió a modo DSD.

## 195.2 Entry gate

- DSD source truth cerrada.
- Native DSD semantics y device capability model estabilizados.
- ADR del packer decide Python/C/Rust/GStreamer productivo antes de native code.

Si una condición no se puede demostrar:

```text
AP2-F09 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 195.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F09
MUST_READ_SECTIONS = 86, 87, 88, 101, 105, 106, 123, 134, 138, 139, 144
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/domain/dop.py (target)`
- `src/michi/application/dop_planner.py (target)`
- `src/michi/infrastructure/audio_output/dop_runtime.py (target)`
- `native/michi-dop/ (candidate, only after ADR)`
- `tests/dop/ (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 195.4 Outputs obligatorios

- `DopCarrierFormat`.
- Packer de referencia pure-Python para conformance.
- Planner que deriva carrier rate/format.
- Runtime productivo aprobado por ADR.
- Evidence separa software carrier verified de DAC-mode verified.

## 195.5 Cambios prohibidos en esta fase

- No procesar frames DoP con PEQ/FIR.
- No usar DoP automático sólo porque ALSA abre un PCM tuple.
- No afirmar DAC DSD mode sin evidencia externa suficiente.
- No meter markers como metadata decorativa.

## 195.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 195.7 Acceptance / exit gate

- Vectores byte-for-byte 0x05/0xFA.
- Chunk/buffer boundaries preservan phase.
- Canales no cruzan payload.
- Carrier negotiated exacto y generation-safe.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 195.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> DoP no es “PCM convertido”. Es DSD transportado en framing compatible. La implementación debe probar bytes y carrier, y mantener separada la interpretación final del DAC.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 195.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F09
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F09:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F10:BEGIN -->

# 196. AP2-F10 — DSD→PCM, DSP INTEROP Y TRANSICIONES ENTRE FAMILIAS

PHASE_ID: AP2-F10
DEPENDENCIES: AP2-F06, AP2-F08, AP2-F09
MUST_READ_SECTIONS: 89, 90, 91, 92, 93, 101, 102, 103, 104, 105, 114, 132, 133, 134, 144, 157, 167, 170, 210, 221, 222, 223, 224, 227, 251, 262
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-F10
WORK_PACKAGES: DSD-060, DSD-070, DSD-080, DSD-110

## 196.1 Propósito

Cerrar la matriz de política: Preserve DSD, Native DSD, DoP, explicit DSD→PCM y DSP. Toda transición debe ser intencional, observable y reversible mediante una nueva reproducción/reconfiguración segura.

## 196.2 Entry gate

- PCM DSP, Native DSD y DoP individualmente estables.
- Policy owner único definido.
- Signal Path puede representar ambas familias.

Si una condición no se puede demostrar:

```text
AP2-F10 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 196.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F10
MUST_READ_SECTIONS = 89, 90, 91, 92, 93, 101, 102, 103, 104, 105, 114, 132, 133, 134, 144, 157, 167, 170
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/application/dsd_policy_service.py (target)`
- `src/michi/application/dsd_output_planner.py (target)`
- `src/michi/application/dop_planner.py (target)`
- `src/michi/application/audio_processing_service.py (target)`
- `src/michi/application/signal_path_service.py (target)`
- `tests/dsd/test_dsd_dsp_matrix.py (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 196.4 Outputs obligatorios

- `DsdPolicyService`.
- Transform node DSD→PCM explícito.
- State machine de transitions.
- Rules para DSP request sobre DSD.
- Cross-format/gapless degradation honesta.

## 196.5 Cambios prohibidos en esta fase

- No Native DSD con DSP activo.
- No DoP con DSP activo.
- No auto-convertir DSD a PCM sin policy/consentimiento.
- No mantener badge bit-perfect cuando processing hace NOT_APPLICABLE/BROKEN según contrato M11.5.

## 196.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 196.7 Acceptance / exit gate

- Decision table completa ejecutada.
- Cada transition produce path snapshot nuevo.
- Rollback/failure no deja policy y runtime divergentes.
- Stop/pause/replay convergen.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 196.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F10 es la convergencia semántica de familias. DSD + DSP significa DSD→PCM explícito primero; Preserve DSD significa DSP bypass/rechazo, nunca procesamiento de DSD/DoP como PCM.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 196.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F10
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F10:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F11:BEGIN -->

# 197. AP2-F11 — CONVERGENCIA UI/UX: NOWPLAYING, SIGNAL PATH, AUDIO LAB Y DEVICE SETUP


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

PHASE_ID: AP2-F11
DEPENDENCIES: AP2-F02, AP2-F03, AP2-F06, AP2-F10
MUST_READ_SECTIONS: 15, 16, 31, 37, 53, 54, 55, 56, 57, 58, 60, 62, 63, 64, 99, 100, 115, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 161, 162, 171, 172, 254, 255, 270, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G06-UI-FILE-MAP, R11-G10-STOP-CODES, R11-F11
WORK_PACKAGES: P2-130, P2-135, P2-140, P2-145, P2-146, P2-147, P2-245; DSP-110; DSD-090; CANON-UI-01..CANON-UI-08

## 197.1 Propósito

Exponer toda la arquitectura mediante read models compartidos y progressive disclosure. La UI debe poder explicar source quality, processing, transport, proof y device sin poseer ninguna de esas verdades.

## 197.2 Entry gate

- Backends y read models estables.
- No hay placeholders que requieran inventar capability.
- Golden geometry actual inspeccionada.

Si una condición no se puede demostrar:

```text
AP2-F11 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 197.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F11
MUST_READ_SECTIONS = 15, 16, 31, 37, 53, 54, 55, 56, 57, 58, 60, 62, 63, 64, 99, 100, 115, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 161, 162, 171, 172, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/presentation/qml/player/NowPlayingBar.qml`
- `src/michi/presentation/qml/primitives/MichiIcon.qml` (existing icon authority)
- `src/michi/presentation/qml/controls/MichiIconButton.qml`
- `src/michi/presentation/qml/theme/MichiPalette.qml`
- `src/michi/presentation/qml/theme/MichiSemanticColors.qml`
- `src/michi/presentation/qml/theme/MichiSpacing.qml`
- `src/michi/presentation/qml/theme/MichiRadius.qml`
- `src/michi/presentation/qml/theme/MichiMetrics.qml`
- `src/michi/presentation/qml/theme/MichiMotion.qml`
- `src/michi/presentation/qml/theme/MichiAccessibility.qml`
- `src/michi/presentation/qml/player/AudioEnginePopup.qml`
- `src/michi/presentation/qml/player/AudioOutputPopup.qml`
- `src/michi/presentation/qml/player/EqualizerPopup.qml (target)`
- `src/michi/presentation/qml/player/AdvancedEqualizerPopup.qml (target)`
- `src/michi/presentation/qml/player/SignalTruthPopup.qml (target)`
- `src/michi/presentation/qml/components/SignalTruthPanel.qml` (preimage/reuse candidate)
- `src/michi/presentation/qml/components/MichiPopupShell.qml (target)`
- `src/michi/presentation/qml/components/MichiEqSlider.qml (target)`
- `src/michi/presentation/audio_output_bridge.py`
- `src/michi/presentation/audio_processing_bridge.py (target)`
- `src/michi/presentation/signal_path_bridge.py (target)`
- `src/michi/presentation/qml/views/AudioLabView.qml` (historical/optional expert surface; not CORE quick flow)
- `src/michi/presentation/qml/views/AudioOutputSettingsSection.qml`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 197.4 Outputs obligatorios

- NowPlayingBar R8: Equalizer, Queue, Audio Engine, quality capsule/Signal Truth y Audio Output universal.
- `EqualizerPopup` básico de 10 bandas + `AdvancedEqualizerPopup` audiófilo.
- `AudioEnginePopup` contextual conservado; Settings queda para configuración profunda.
- `SignalTruthPopup` como única superficie visual de Signal Path/Truth desde la cápsula de calidad.
- `AudioOutputPopup` universal con DAC/local/Michi Music Stream/display; sin botones separados DAC/Stream.
- Device Setup General/Advanced/Expert conserva diagnóstico profundo sin duplicar selector quick.

## 197.5 Cambios prohibidos en esta fase

- No business rules en QML.
- No parsing de quality strings para decidir HD.
- No cambiar engine automáticamente desde DAC popup.
- No mostrar controles que backend/capability no justifica.

## 197.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 197.7 Acceptance / exit gate

- Keyboard/screen-reader/reduced-motion gates.
- Full/compact/narrow layouts.
- Golden NowPlaying actualizado conscientemente.
- Selected != active visible donde aplique.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 197.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F11 presenta; no decide. Un badge jamás puede crear verdad. La misma source of truth debe alimentar Quick Surface, Detailed Signal Path y Device Setup.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 197.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F11
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F11:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F12:BEGIN -->

# 198. AP2-F12 — HIGH-END DEVICE INTELLIGENCE, HEALTH, NATIVE PROFILES Y CONTROL OPCIONAL

PHASE_ID: AP2-F12
DEPENDENCIES: AP2-F02, AP2-F10
MUST_READ_SECTIONS: 30, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 100, 155, 156, 215, 221, 229, 270
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G09-LEGACY-RESEARCH, R11-F12
WORK_PACKAGES: P2-160..P2-300 core; P2-310..P2-330 OPTIONAL native-control subtrack

## 198.1 Propósito

Construir una experiencia de hardware high-end sobre datos reales: setup adaptativo, health, recommended/custom, Native Profiles y, sólo cuando sea legal/técnicamente seguro, Native Control por plugin.

## 198.2 Entry gate

- Device knowledge F02 cerrado.
- Persistencia de policy separada de evidence.
- QualificationService baseline sigue siendo única autoridad de exact probe.

Si una condición no se puede demostrar:

```text
AP2-F12 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 198.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F12
MUST_READ_SECTIONS = 30, 31, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 50, 51, 52, 100, 155, 156
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/application/audio_hardware/ (target)`
- `src/michi/infrastructure/audio_hardware/ (target)`
- `resources/audio_hardware/ (target)`
- `src/michi/application/dac_qualification_service.py`
- `src/michi/application/volume_policy_service.py`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 198.4 Outputs obligatorios

- Device health como orquestación, no segundo probe engine.
- Automatic setup explicable/reversible.
- Recommended vs Custom diff.
- Native Profile resolver.
- Plugin boundary de control con readback y generation safety.

## 198.5 Cambios prohibidos en esta fase

- No segundo DacQualificationService.
- No sobrescribir custom config tras actualizar perfil.
- No Native Control genérico por ingeniería inversa indiscriminada.
- No plugin controlando PlaybackState/OutputPlan global.

## 198.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 198.7 Acceptance / exit gate

- Profile unavailable no rompe playback.
- Runtime contradiction siempre gana sobre recomendación.
- Control write requiere device/generation match y readback.
- Subtrack Native Control puede quedar NOT_ACTIVATED sin bloquear core.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 198.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F12 hace Michi “consciente” del DAC, pero conocimiento y control siguen subordinados a runtime truth. Native Control es opcional por dispositivo y jamás una condición para playback normal.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 198.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F12
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F12:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F13:BEGIN -->

# 199. AP2-F13 — PERSISTENCIA, MIGRACIONES, SEGURIDAD Y PACKAGING

PHASE_ID: AP2-F13
DEPENDENCIES: AP2-F11, AP2-F12
MUST_READ_SECTIONS: 17, 20, 21, 38, 43, 44, 45, 46, 95, 108, 113, 158, 159, 160, 164, 175, 230, 231, 253, 256
MUST_READ_ANCHORS: R11-G05-PERSISTENCE, R11-G08-TEST-AUTHORITY, R11-F13
WORK_PACKAGES: cross-cutting closure; no inventar una nueva authority

## 199.1 Propósito

Hacer durable y distribuible Audio Phase 2: schemas versionados, caches rebuildable, IR store, migrations, feature discovery, dependency reporting y rollback seguro.

## 199.2 Entry gate

- Modelos/fields de producto estabilizados; no migrar un schema que aún cambia diariamente.
- UI y runtime consumen APIs, no tablas directamente.

Si una condición no se puede demostrar:

```text
AP2-F13 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 199.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F13
MUST_READ_SECTIONS = 17, 20, 21, 38, 43, 44, 45, 46, 95, 108, 113, 158, 159, 160, 164, 175
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `src/michi/infrastructure/sqlite_audio_output_repository.py`
- `src/michi/infrastructure/sqlite_settings.py`
- `src/michi/application/persistence_coordinator.py`
- `pyproject.toml`
- `scripts/verify_audio_phase2.py (target)`
- `resources/audio_hardware/ (target)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 199.4 Outputs obligatorios

- Schema Phase 2 versionado.
- Migrations forward + rollback policy.
- IR store content-addressed.
- MAHKB update integrity checks.
- Packaging feature probes para GStreamer/DSD/CamillaDSP/etc.
- Error taxonomy productiva.

## 199.5 Cambios prohibidos en esta fase

- No persistir runtime SignalPath como autoridad.
- No persistir ALSA hw:N como identity.
- No ejecutar regex/datasets no validados.
- No hacer que dependencia opcional vuelva obligatorio el wheel base.

## 199.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 199.7 Acceptance / exit gate

- Upgrade/downgrade fixtures.
- DB corrupta degrada sin romper playback core.
- Optional dependency missing produce capability reason estable.
- Fresh install + migrated install pasan misma suite funcional.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 199.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F13 solidifica datos y distribución después de estabilizar contratos. Persistir menos es preferible a persistir runtime truth obsoleta.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 199.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F13
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F13:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F14:BEGIN -->

# 200. AP2-F14 — CUALIFICACIÓN FÍSICA, PERFORMANCE Y CALIDAD

PHASE_ID: AP2-F14
DEPENDENCIES: AP2-F13
MUST_READ_SECTIONS: 22, 23, 103, 104, 105, 106, 107, 110, 111, 112, 120, 173, 176, 232, 233, 264, 267
MUST_READ_ANCHORS: R11-G07-REALTIME-SAFETY, R11-G08-TEST-AUTHORITY, R11-F14
WORK_PACKAGES: P2-110; DSP-120; DSD-100

## 200.1 Propósito

Someter PCM, DSP, Native DSD y DoP a hardware real, medir latencia/CPU/XRUN y separar evidencia física de mocks o simuladores.

## 200.2 Entry gate

- Software gates verdes.
- Packaging reproducible.
- Hardware matrix declarada disponible o explícitamente NOT_RUN.

Si una condición no se puede demostrar:

```text
AP2-F14 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 200.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F14
MUST_READ_SECTIONS = 22, 23, 103, 104, 105, 106, 107, 110, 111, 112, 120, 173, 176
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `scripts/verify_audio_phase2.py (target)`
- `tests/physical/ (target)`
- `tests/audio_processing/ (target)`
- `tests/dsd/ (target)`
- `artifacts/qualification/ (runtime output, not source)`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 200.4 Outputs obligatorios

- Per-device run sheets.
- Artifacts SHA-bound a commit/entorno.
- Benchmarks CPU/RAM/latency/XRUN.
- Transitions sample-rate/format/DSD/DoP probadas.
- Lista explícita de hardware no probado.

## 200.5 Cambios prohibidos en esta fase

- No declarar VERIFIED basado sólo en fakes.
- No sustituir un DAC faltante con mock y llamarlo physical.
- No borrar resultados fallidos para “cerrar” la fase.
- No generalizar capability de un DAC a todos.

## 200.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 200.7 Acceptance / exit gate

- Matriz mínima del plan ejecutada.
- Regresiones de baseline inexistentes.
- Budgets quantitative gates cumplidos o revisados explícitamente.
- Artifacts preservados y vinculados a HEAD exacto.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 200.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F14 es donde las afirmaciones high-end dejan de ser software-only. NOT_RUN es válido y honesto; simular hardware y llamarlo verificación física no lo es.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 200.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F14
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F14:END -->


------------------------------------------------------------------------

<!-- MICHI_PHASE2:PHASE:AP2-F15:BEGIN -->

# 201. AP2-F15 — FINAL ADVERSARIAL SEAL, VERIFIER Y FREEZE

PHASE_ID: AP2-F15
DEPENDENCIES: AP2-F14
MUST_READ_SECTIONS: 20, 23, 26, 47, 64, 107, 113, 115, 116, 117, 174, 177, 178, 179, 180, 181, 210, 234, 235, 236, 257, 258, 259, 260, 261, 270
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G08-TEST-AUTHORITY, R11-G10-STOP-CODES, R11-G11-PATCH-PROTOCOL, R11-G13-ALIGNMENT, R11-F15
WORK_PACKAGES: P2-150; DSP-130; DSD-120; optional native-control seal sólo si activado

## 201.1 Propósito

Intentar destruir las afirmaciones del sistema antes de declararlo cerrado: authorities, staleness, DSP, DSD, DoP, persistencia, UI, seguridad, packaging y hardware.

## 201.2 Entry gate

- Todas las fases obligatorias previas CLOSED.
- P0/P1=0.
- Physical artifacts presentes.

Si una condición no se puede demostrar:

```text
AP2-F15 = LOCKED | BLOCKED
IMPLEMENTATION_ALLOWED = FALSE
```

## 201.3 Context pack obligatorio

Antes de editar, OpenCode debe leer:

```text
BIBLIA A
BIBLIA B
esta tarjeta AP2-F15
MUST_READ_SECTIONS = 20, 23, 26, 47, 64, 107, 113, 115, 116, 117, 174, 177, 178, 179, 180, 181
```

Archivos del repositorio que deben inspeccionarse/revalidarse según existan:

- `scripts/verify_audio_phase2.py (target)`
- `docs/STATUS_MATRIX.md`
- `docs/MASTER_ROADMAP_1.0.md`
- `docs/ARCHITECTURE.md`
- `.github/workflows/ (relevant CI)`
- `entire Phase 2 production/test surface`

Un archivo marcado `(target)` puede no existir todavía. Su ausencia no autoriza
al agente a cambiar el nombre/ownership propuesto sin reconciliarlo con el
árbol real del repositorio.

## 201.4 Outputs obligatorios

- Verifier aggregate exact-head.
- KILLCRITIC firmado por resultados reproducibles.
- Status/roadmap/docs alineados.
- Final baseline/freeze commit.
- Manifest de capacidades realmente soportadas.

## 201.5 Cambios prohibidos en esta fase

- No reducir tests para obtener verde.
- No convertir failures en xfail sin decisión explícita.
- No reescribir historia de artifacts.
- No promocionar optional Native Control no probado.

## 201.6 Estrategia de implementación

Cada work package de esta fase debe seguir:

```text
READ SPEC
  ↓
INSPECT BASELINE CODE
  ↓
WRITE/UPDATE RED TEST OR CONTRACT TEST
  ↓
IMPLEMENT MINIMUM CLOSED SLICE
  ↓
RUN FOCUSED TESTS
  ↓
RUN PHASE REGRESSION FIREWALL
  ↓
REREAD PRE_COMMIT CONTRACT
  ↓
COMMIT WITH PHASE TRAILERS
```

No se mezclan correcciones oportunistas de otras fases. Bugs preexistentes que
bloqueen la fase se registran como blocker con owner explícito.

## 201.7 Acceptance / exit gate

- Full suite + Phase2 verifier green en HEAD exacto.
- Cero P0/P1.
- Docs y código no se contradicen.
- Reinstalación limpia y migration path validados.
- Audio Phase 2 pasa a CLOSED/FROZEN.

Para cerrar la fase debe existir evidencia machine-readable o reproducible de
cada punto anterior; «parece funcionar» no es un gate.

## 201.8 CONTEXT CAPSULE — para modelos con ventana pequeña

> F15 no agrega features. Falsifica, corrige y sella. Cualquier feature nueva descubierta aquí vuelve a su fase propietaria; no se “arregla rápido” dentro del seal.

Un modelo pequeño puede empezar con este capsule para orientarse, pero antes de
cambiar código debe cargar las secciones concretas relacionadas con el símbolo
que va a tocar.

## 201.9 Handoff mínimo

El cierre parcial o total debe reportar:

```text
phase=AP2-F15
state=ACTIVE | VERIFYING | CLOSED | BLOCKED
spec_sha256=<runtime>
repo_head=<exact commit>
files_changed=<list>
tests=<list + result>
remaining=<bounded list>
next_phase_unlocked=<id or NONE>
```

<!-- MICHI_PHASE2:PHASE:AP2-F15:END -->


------------------------------------------------------------------------

# 202. PLANTILLA DE PROMPT PARA OPENCODE — NO SUSTITUYE LA BIBLIA

Cuando el usuario quiera ejecutar un slice, el prompt mínimo recomendado es:

```text
PRIMARY_PHASE=AP2-Fxx.
Antes de tocar código, resuelve y lee la Biblia canónica de Audio Phase 2.
Ejecuta el bootstrap BIBLIA A, lee BIBLIA B y la tarjeta AP2-Fxx, luego carga
sus MUST_READ_SECTIONS relevantes y los archivos actuales del repositorio.
Emite PHASE2_SPEC_ACK. Si cualquier gate, authority o scope es ambiguo, detente
con el STOP_* correspondiente. Implementa un único slice cerrado, ejecuta sus
tests y relee el contrato antes del commit. No uses memoria/resúmenes como
fuente de verdad.
```

Para modelos con contexto pequeño:

```text
python scripts/phase2_context.py --phase AP2-Fxx --mode minimum
```

Para cambios de contratos públicos:

```text
python scripts/phase2_context.py --phase AP2-Fxx --mode standard
```

Para auditoría/revisión final:

```text
python scripts/phase2_context.py --phase AP2-Fxx --mode deep
```

# 203. REGLA DE CIERRE DE SESIÓN OPENCODE

Antes de finalizar una sesión que haya modificado Audio Phase 2:

```text
1. git diff --check
2. tests focales de la fase
3. regression firewall indicado por la fase
4. releer la tarjeta AP2-Fxx
5. verificar que no se tocó una fase LOCKED
6. generar PHASE2_SPEC_ACK final
7. registrar blockers reales, no hipótesis
8. dejar un handoff que obligue al siguiente agente a releer la Biblia
```

Nunca terminar con:

```text
"el siguiente agente puede continuar desde este resumen"
```

La frase correcta es conceptualmente:

```text
"el siguiente agente debe releer la Biblia, usar este handoff sólo como índice
de trabajo y revalidar el HEAD actual antes de continuar."
```

# 204. PRINCIPIO FINAL DE LA BIBLIA

```text
THE FILE IS THE MAP.
THE REPOSITORY IS THE TERRAIN.
THE FROZEN BASELINE IS THE FACTUAL STARTING POINT.
TESTS ARE EVIDENCE.
RUNTIME IS TRUTH ABOUT THE CURRENT SESSION.
NO MODEL MEMORY OVERRIDES ANY OF THEM.
```

La Biblia debe crecer cuando una decisión nueva se vuelve normativa, pero no
puede convertirse en una colección desordenada de ideas. Cada nueva decisión
debe indicar:

```text
OWNER
PHASE
INPUTS
OUTPUTS
FAILURE MODE
EVIDENCE
TEST GATE
UI CONSEQUENCE, si existe
```

Sólo así un agente con 16k, 32k, 64k, 128k o una ventana aún mayor puede
implementar el mismo producto sin depender de cuánto de la conversación
anterior conserve en memoria.

------------------------------------------------------------------------

# 205. INTEGRACIÓN OBLIGATORIA CON `AGENTS.md` — HACER QUE OPENCODE ENCUENTRE LA BIBLIA

El repositorio ya utiliza `AGENTS.md` para obligar a los agentes a consultar la
especificación DAC V3.5 antes de trabajar en M11.4. Audio Phase 2 debe reutilizar
ese patrón y **no depender de que el usuario recuerde mencionar esta Biblia en
cada prompt**.

Esta integración sólo se instala cuando `AP2-F00` se activa. Antes de ese gate,
`AGENTS.md` debe seguir apuntando a la especificación vigente de V3.5/M11.5 sin
crear la impresión falsa de que Phase 2 está autorizado.

Bloque normativo a agregar en F00:

```markdown
<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_BEGIN -->
## Audio Phase 2 work: mandatory implementation Bible

Audio Phase 2 is governed by:
`docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md`.

For ANY task that touches Phase 2 audio signal types, DSP, PEQ, FIR,
convolution, resampling, dither, Signal Path, Native DSD, DoP, DSD-to-PCM,
Phase 2 Device Setup, Audio Lab, Phase 2 NowPlaying audio controls, MAHKB,
native DAC profiles, Phase 2 persistence, Phase 2 physical qualification, or
related presentation bridges:

1. Resolve and open the canonical Audio Phase 2 Bible before changing code.
2. Read `BIBLIA A`, `BIBLIA B`, and the complete `AP2-Fxx` phase card for the
   current task.
3. Declare exactly one `PRIMARY_PHASE=AP2-Fxx`.
4. Run `python scripts/phase2_context.py --phase AP2-Fxx --receipt-json` and
   keep the resulting spec hash in the work log.
5. Read the governing `MUST_READ_SECTIONS` for the concrete symbols being
   changed. A prior-chat summary or agent memory is never sufficient.
6. Run `python scripts/verify_audio_phase2_repository_alignment.py --phase AP2-Fxx`
   before the first productive patch and again before the phase commit.
7. Do not mutate a phase whose state in `docs/audio/phase2/PHASE2_STATE.json`
   is `LOCKED` or `BLOCKED`.
8. Preserve the frozen V3.5/M11.5 authorities. If code, state, ADR and Bible
   disagree, stop with `STOP_SPEC_DRIFT`; do not improvise a new authority.
9. After context compaction, model change, subagent handoff, or resumed session,
   reread the phase card and affected normative sections before continuing.
10. No context → no code. Unknown ownership → no code. Unknown evidence →
    fail closed for fidelity claims.
<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_END -->
```

La ventaja de este diseño es que el agente recibe la instrucción **antes de
entrar al código de audio**. El plan deja de ser un PDF mental o un documento
que sólo sirve durante una conversación: se convierte en parte del contrato de
repositorio.

## 205.1 Scope detector para `AGENTS.md`

El bloque debe considerarse aplicable cuando una tarea toque al menos una de
estas superficies:

```text
src/michi/domain/audio_signal.py
src/michi/domain/audio_processing.py
src/michi/domain/audio_processing_evidence.py
src/michi/domain/dsd.py
src/michi/domain/dop.py
src/michi/domain/signal_path.py
src/michi/application/audio_processing_*
src/michi/application/dsd_*
src/michi/application/dop_*
src/michi/application/signal_path_*
src/michi/infrastructure/audio_processing/
src/michi/infrastructure/audio_output/strict_dsd_sink.py
src/michi/infrastructure/audio_output/dop_*
src/michi/presentation/audio_processing_bridge.py
src/michi/presentation/signal_path_bridge.py
src/michi/presentation/qml/**/AudioLab*
src/michi/presentation/qml/**/SignalPath*
src/michi/presentation/qml/**/Dsd*
resources/audio_hardware/
docs/audio/phase2/
tests/audio_processing/
tests/dsd/
tests/dop/
```

También aplica a archivos legacy V3.5 si se modifican **por una necesidad de
Phase 2**, aunque el path no esté en la lista.

# 206. `verify_audio_phase2_repository_alignment.py` — GATE DE ALINEACIÓN DEL AGENTE

F00 debe crear un verificador pequeño que pruebe que OpenCode no está
implementando contra una copia equivocada o una fase bloqueada.

Objetivos:

```text
- Biblia canónica existe;
- anchors BIBLIA A/B existen exactamente una vez;
- AP2-F00..AP2-F15 tienen BEGIN/END exactamente una vez;
- AGENTS.md contiene el bloque mandatory;
- PHASE2_STATE.json existe después de la activación;
- baseline manifest existe;
- phase solicitada es conocida;
- phase solicitada no está LOCKED/BLOCKED para --require-mutable;
- dependencias declaradas están CLOSED;
- el state apunta al mismo spec path;
- el spec SHA puede calcularse;
- el current repo HEAD no está antes del baseline commit en una historia
  incompatible;
- el agente recibe un receipt reproducible.
```

Implementación de referencia:

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SPEC = Path("docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md")
STATE = Path("docs/audio/phase2/PHASE2_STATE.json")
BASELINE = Path("docs/audio/phase2/audio_phase2_baseline.json")
AGENTS = Path("AGENTS.md")
PHASE_IDS = tuple(f"AP2-F{index:02d}" for index in range(16))
MUTABLE_STATES = {"READY", "ACTIVE", "VERIFYING"}
AGENT_BEGIN = "<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_BEGIN -->"
AGENT_END = "<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_END -->"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def fail(code: str, detail: str) -> None:
    raise SystemExit(f"{code}: {detail}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail("STOP_PHASE2_STATE_INVALID", f"{path}: {exc}")


def phase_dependencies(spec_text: str, phase: str) -> tuple[str, ...]:
    begin = f"<!-- MICHI_PHASE2:PHASE:{phase}:BEGIN -->"
    end = f"<!-- MICHI_PHASE2:PHASE:{phase}:END -->"
    if spec_text.count(begin) != 1 or spec_text.count(end) != 1:
        fail("STOP_PHASE_ANCHOR_INVALID", phase)
    block = spec_text.split(begin, 1)[1].split(end, 1)[0]
    match = re.search(r"^DEPENDENCIES:\s*(.+)$", block, re.MULTILINE)
    if match is None:
        return ()
    return tuple(re.findall(r"AP2-F\d{2}", match.group(1)))


def verify(phase: str, require_mutable: bool) -> dict[str, object]:
    if phase not in PHASE_IDS:
        fail("STOP_PHASE_UNKNOWN", phase)
    for path in (SPEC, STATE, BASELINE, AGENTS):
        if not path.is_file():
            fail("STOP_PHASE2_REQUIRED_FILE_MISSING", str(path))

    spec_text = SPEC.read_text(encoding="utf-8")

    def anchor_count(anchor: str) -> int:
        return len(re.findall(rf"^{re.escape(anchor)}$", spec_text, re.MULTILINE))

    if anchor_count("<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->") != 1:
        fail("STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID", "BEGIN")
    if anchor_count("<!-- MICHI_PHASE2:BOOTSTRAP:END -->") != 1:
        fail("STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID", "END")
    if anchor_count("<!-- MICHI_PHASE2:PHASE_INDEX:BEGIN -->") != 1:
        fail("STOP_PHASE_INDEX_ANCHOR_INVALID", "BEGIN")
    if anchor_count("<!-- MICHI_PHASE2:PHASE_INDEX:END -->") != 1:
        fail("STOP_PHASE_INDEX_ANCHOR_INVALID", "END")

    for phase_id in PHASE_IDS:
        if anchor_count(f"<!-- MICHI_PHASE2:PHASE:{phase_id}:BEGIN -->") != 1:
            fail("STOP_PHASE_ANCHOR_INVALID", f"{phase_id}:BEGIN")
        if anchor_count(f"<!-- MICHI_PHASE2:PHASE:{phase_id}:END -->") != 1:
            fail("STOP_PHASE_ANCHOR_INVALID", f"{phase_id}:END")

    agents_text = AGENTS.read_text(encoding="utf-8")
    if agents_text.count(AGENT_BEGIN) != 1 or agents_text.count(AGENT_END) != 1:
        fail("STOP_AGENT_CONTRACT_MISSING", "AGENTS.md")

    state = load_json(STATE)
    baseline = load_json(BASELINE)
    state_spec = state.get("spec", {}).get("path")
    if state_spec != str(SPEC):
        fail("STOP_SPEC_PATH_DRIFT", repr(state_spec))

    phase_states = state.get("phases", {})
    status = phase_states.get(phase)
    if status is None:
        fail("STOP_PHASE_STATE_MISSING", phase)
    if require_mutable and status not in MUTABLE_STATES:
        fail("STOP_PHASE_NOT_MUTABLE", f"{phase}={status}")

    for dependency in phase_dependencies(spec_text, phase):
        if phase_states.get(dependency) != "CLOSED":
            fail(
                "STOP_ENTRY_GATE_UNSATISFIED",
                f"{phase} requires {dependency}=CLOSED",
            )

    baseline_commit = baseline.get("git_commit") or state.get("baseline", {}).get("git_commit")
    if not baseline_commit:
        fail("STOP_BASELINE_MANIFEST_INVALID", "git_commit missing")
    head = run_git("rev-parse", "HEAD")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_commit, head],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        fail("STOP_BASELINE_DRIFT", f"baseline {baseline_commit} is not ancestor of {head}")

    return {
        "phase": phase,
        "phase_state": status,
        "spec_path": str(SPEC),
        "spec_sha256": sha256(SPEC),
        "baseline_commit": baseline_commit,
        "repo_head": head,
        "dependencies": phase_dependencies(spec_text, phase),
        "verdict": "GO",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--require-mutable", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.phase, args.require_mutable), indent=2))


if __name__ == "__main__":
    main()
```

Uso:

```bash
python scripts/verify_audio_phase2_repository_alignment.py \
  --phase AP2-F05 --require-mutable
```

Este verificador no demuestra que el código sea correcto. Demuestra que el
agente está trabajando **sobre la Biblia, baseline y fase correctas**.

# 207. PROTOCOLO DE CONSULTA CONTINUA — CUÁNTO RELEER Y CUÁNDO

«Consultar siempre» no significa cargar 15 000 líneas antes de cada función.
Significa que el agente nunca toma una decisión normativa sin revalidar la
porción de Biblia que la gobierna.

Matriz operativa:

| Evento | Lectura mínima |
|---|---|
| Nueva sesión | BIBLIA A + B + phase card |
| Primer patch | phase card + secciones que gobiernan símbolos tocados |
| Nuevo archivo | ownership + árbol objetivo + phase card |
| Tipo de dominio | domain sections + compatibility rules |
| Nuevo port | authority map + application port section |
| Runtime GStreamer | threading + transaction + runtime evidence |
| DSD/DoP | SignalFormat + DSD/DoP phase + evidence rules |
| DSP | ProcessingGraph + compiler + runtime phase |
| Persistencia | schema + invalidation + migration phase |
| QML | UI master spec + read model + accessibility |
| Test falla y cambia diseño | phase card + affected contract, antes de reescribir |
| Commit | phase card + exit gate + no-regression contract |
| Handoff | BIBLIA A handoff rule + phase card |
| Context compactado | bootstrap + phase card nuevamente |

La frecuencia correcta de relectura es por **decisión normativa**, no por
cantidad arbitraria de minutos o tokens.

## 207.1 Read-before-write por archivo

Antes de modificar un archivo nuevo dentro de una sesión, el agente debe poder
asociarlo a:

```text
FILE
  ↓
OWNER
  ↓
PRIMARY_PHASE
  ↓
NORMATIVE SECTION(S)
  ↓
TEST GATE
```

Si no puede completar esa cadena, el archivo no se modifica todavía.

## 207.2 Consultas focales con `rg`

Cuando no esté instalado `phase2_context.py` aún, usar búsquedas literales:

```bash
rg -n '^# (70|86|87|88|123|134|138)\.' "$SPEC"
rg -n 'AP2-F09|DopCarrierFormat|DoP|0x05|0xFA' "$SPEC"
rg -n 'AudioProcessingService|ProcessingGraph|ProcessingPlan' "$SPEC"
rg -n 'SignalPathSnapshot|SignalTruth|BitPerfectState' "$SPEC"
```

Después leer el bloque completo de la sección encontrada; no implementar desde
la línea coincidente aislada.

# 208. MODELO DE SESIÓN PARA OPENCODE — EJEMPLO COMPLETO

Ejemplo de una tarea futura:

```text
Usuario:
"Implementa el primer slice de AP2-F09: el packer DoP puro y sus vectores."
```

OpenCode debe realizar conceptualmente:

```text
1. Resolver SPEC.
2. Leer BIBLIA A/B.
3. Leer tarjeta AP2-F09.
4. Verificar AP2-F07= CLOSED y AP2-F08 = CLOSED.
5. Leer secciones 86, 87, 88, 123, 134, 138.
6. Inspeccionar domain/dop.py si ya existe y tests/dop actuales.
7. Emitir PHASE2_SPEC_ACK.
8. Crear primero vectores RED.
9. Implementar sólo pure framing; no GStreamer plugin todavía si el slice no
   lo autoriza.
10. Ejecutar tests focales.
11. Releer AP2-F09 acceptance.
12. Commit pequeño con trailers.
13. Handoff obliga a releer Biblia.
```

Un modelo con 16–32k de contexto puede hacer esto sin conocer las otras 14 000
líneas. Un modelo con una ventana extensa puede leer más, pero llega a la misma
decisión porque las autoridades son iguales.

# 209. CONDICIÓN DE ÉXITO DE LA «BIBLIA»

Este documento cumple su función sólo si un agente que llega sin contexto de
conversaciones anteriores puede determinar, leyendo el repositorio:

```text
qué está permitido ahora;
qué está bloqueado;
qué fase posee el cambio;
qué autoridad existente no puede duplicar;
qué código debe inspeccionar;
qué código debe producir;
qué evidence necesita;
qué tests cierran el slice;
qué UI cambia;
qué persistencia cambia;
qué sucede si algo falla;
y qué debe releer antes de continuar.
```

La métrica de calidad no es únicamente el número de líneas. Es **reducir a cero
la necesidad de que OpenCode adivine arquitectura entre dos ventanas de
contexto distintas**.

------------------------------------------------------------------------

# 210. KILLCRITIC V2 — SELLO CORRECTIVO NORMATIVO Y MATRIZ DE PRECEDENCIA

Esta sección cierra las debilidades detectadas después de la primera expansión integral. No agrega “features por entusiasmo”; corrige unidades, fronteras, transacciones y pruebas que podían producir una implementación aparentemente funcional pero semánticamente falsa.

## 210.1 Precedencia dentro de esta misma Biblia

```text
BIBLIA A / B
    ↓
AP2-Fxx phase card
    ↓
KILLCRITIC CORRECTIVE SEAL §§210–236
    ↓
Implementation Blueprint §§118–181
    ↓
secciones de diseño tempranas §§0–117
    ↓
notas históricas / superseded
```

Regla:

```text
IF earlier_reference != corrective_seal:
    corrective_seal wins
    older snippet must be treated as historical
```

## 210.2 Hallazgos P0 corregidos por este sello

```text
KC-P0-DSD-UNITS          §§211,213,214
KC-P0-DSD-BIT-ORDER      §214
KC-P0-DSD-CHARACTERIZER  §212
KC-P0-DOP-EVIDENCE       §215
KC-P0-DOP-LAYOUT         §§216,217
KC-P0-DSP-ATOMICITY      §218
KC-P0-DSP-EVIDENCE       §§219,220
KC-P1-DSD2PCM            §§221,222
KC-P1-STATEFUL-AUDIO     §§223,224
KC-P1-GRAPH-INVARIANTS   §228
KC-P1-SECURITY           §§230,231
KC-P1-PHYSICAL           §§232,233
KC-P1-KILLCRITIC-CI      §§234–236
```

## 210.3 Regla de “100% implementado”

En esta Biblia, “100%” NO significa “el código compila”. Significa simultáneamente:

```text
DOMAIN CONTRACT          closed
APPLICATION AUTHORITY    closed
RUNTIME IMPLEMENTATION   closed
EVIDENCE                 observed, not fabricated
FAILURE SEMANTICS        typed
PERSISTENCE              versioned where applicable
UI                       read-model only
TESTS                    unit + integration + adversarial
PHYSICAL                 executed where hardware claim exists
PERFORMANCE              measured
PACKAGING                 reproducible
DOCUMENTATION             aligned with HEAD
```

Un componente con cualquiera de esas filas `UNKNOWN`, `TODO`, `NOT_IMPLEMENTED` o “investigar durante coding” no puede ser marcado `CLOSED`.


------------------------------------------------------------------------

# 211. DSD RATE ALGEBRA V2 — UNIDADES CANÓNICAS SIN AMBIGÜEDAD

La primera versión del blueprint utilizaba `bit_rate_hz` en lugares donde GStreamer y ALSA esperan unidades distintas. Esta sección reemplaza esa ambigüedad por tipos incompatibles deliberadamente.

Fuentes técnicas revalidadas al redactar este sello:

```text
GStreamer GstDsdInfo:
  DSD rate = bytes DSD consumed per second per channel.

Linux UAPI ALSA:
  DSD_U8     = 1-byte samples DSD (x8)
  DSD_U16_*  = 2-byte samples DSD (x16)
  DSD_U32_*  = 4-byte samples DSD (x32)

DoP v1:
  two DSD payload bytes = 16 DSD bits per channel carrier frame.
```

## 211.1 Tipos normativos

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class DsdSourceBitRate:
    bits_per_second_per_channel: int

    def __post_init__(self) -> None:
        if self.bits_per_second_per_channel <= 0:
            raise ValueError("DSD source bit rate must be positive")
        if self.bits_per_second_per_channel % 8:
            raise ValueError("DSD source rate must be byte-addressable")

    @property
    def gst_byte_rate_per_channel(self) -> int:
        return self.bits_per_second_per_channel // 8

    @property
    def dop_carrier_frames_per_second(self) -> int:
        if self.bits_per_second_per_channel % 16:
            raise ValueError("DoP v1 requires source rate divisible by 16")
        return self.bits_per_second_per_channel // 16


@dataclass(frozen=True, slots=True)
class GstDsdRate:
    bytes_per_second_per_channel: int


class AlsaDsdGrouping(Enum):
    DSD_U8 = ("SND_PCM_FORMAT_DSD_U8", 8)
    DSD_U16_LE = ("SND_PCM_FORMAT_DSD_U16_LE", 16)
    DSD_U16_BE = ("SND_PCM_FORMAT_DSD_U16_BE", 16)
    DSD_U32_LE = ("SND_PCM_FORMAT_DSD_U32_LE", 32)
    DSD_U32_BE = ("SND_PCM_FORMAT_DSD_U32_BE", 32)

    @property
    def bits_per_alsa_sample(self) -> int:
        return int(self.value[1])

    @property
    def alsa_format_name(self) -> str:
        return str(self.value[0])


@dataclass(frozen=True, slots=True)
class AlsaDsdTransportRate:
    frames_per_second: int
    grouping: AlsaDsdGrouping


@dataclass(frozen=True, slots=True)
class DopCarrierRate:
    frames_per_second: int


def source_to_gst_rate(source: DsdSourceBitRate) -> GstDsdRate:
    return GstDsdRate(source.bits_per_second_per_channel // 8)


def source_to_alsa_rate(
    source: DsdSourceBitRate,
    grouping: AlsaDsdGrouping,
) -> AlsaDsdTransportRate:
    width = grouping.bits_per_alsa_sample
    if source.bits_per_second_per_channel % width:
        raise ValueError("source DSD rate not divisible by ALSA grouping width")
    return AlsaDsdTransportRate(
        frames_per_second=source.bits_per_second_per_channel // width,
        grouping=grouping,
    )


def source_to_dop_rate(source: DsdSourceBitRate) -> DopCarrierRate:
    return DopCarrierRate(source.dop_carrier_frames_per_second)
```

## 211.2 Invariantes

```text
DSD-UNIT-01 source bit rate is never passed directly to Gst caps `rate`.
DSD-UNIT-02 Gst caps `rate` is bytes/s/channel.
DSD-UNIT-03 ALSA hw rate depends on DSD grouping width.
DSD-UNIT-04 DoP carrier rate = source bit-rate / 16.
DSD-UNIT-05 UI labels may show DSD64/128/etc, but planners use typed units.
DSD-UNIT-06 no field named only `rate_hz` is allowed in new DSD transport types.
```

## 211.3 Canonical examples

| Family | Source per-channel | GstDsd rate | ALSA U8 | ALSA U16 | ALSA U32 | DoP carrier |
|---|---:|---:|---:|---:|---:|---:|
| DSD64 | 2,822,400 bit/s | 352,800 B/s | 352,800 Hz | 176,400 Hz | 88,200 Hz | 176,400 Hz |
| DSD128 | 5,644,800 bit/s | 705,600 B/s | 705,600 Hz | 352,800 Hz | 176,400 Hz | 352,800 Hz |
| DSD256 | 11,289,600 bit/s | 1,411,200 B/s | 1,411,200 Hz | 705,600 Hz | 352,800 Hz | 705,600 Hz |
| DSD512 | 22,579,200 bit/s | 2,822,400 B/s | 2,822,400 Hz | 1,411,200 Hz | 705,600 Hz | 1,411,200 Hz |
| DSD1024 | 45,158,400 bit/s | 5,644,800 B/s | 5,644,800 Hz | 2,822,400 Hz | 1,411,200 Hz | 2,822,400 Hz |


La tabla NO implica que un dispositivo soporte cada grouping. Sólo define unidades y mappings matemáticos. La capability real continúa requiriendo exact-open/readback.

## 211.4 Tests obligatorios

```python
import pytest

@pytest.mark.parametrize(
    "bits,gst,u8,u16,u32,dop",
    [
        (2_822_400, 352_800, 352_800, 176_400, 88_200, 176_400),
        (5_644_800, 705_600, 705_600, 352_800, 176_400, 352_800),
        (11_289_600, 1_411_200, 1_411_200, 705_600, 352_800, 705_600),
    ],
)
def test_dsd_rate_units(bits, gst, u8, u16, u32, dop):
    src = DsdSourceBitRate(bits)
    assert source_to_gst_rate(src).bytes_per_second_per_channel == gst
    assert source_to_alsa_rate(src, AlsaDsdGrouping.DSD_U8).frames_per_second == u8
    assert source_to_alsa_rate(src, AlsaDsdGrouping.DSD_U16_LE).frames_per_second == u16
    assert source_to_alsa_rate(src, AlsaDsdGrouping.DSD_U32_LE).frames_per_second == u32
    assert source_to_dop_rate(src).frames_per_second == dop
```


------------------------------------------------------------------------

# 212. DSD SOURCE CHARACTERIZATION V2 — CONTAINER, ELEMENTARY STREAM Y DECODE SON VERDADES DISTINTAS

La caracterización no puede inferir “source is PCM” simplemente porque el sink final reciba PCM. Se separan tres observaciones:

```text
FILE FACTS
    container/metadata
        ↓
ELEMENTARY STREAM TRUTH
    stream after demux / before decode-conversion
        ↓
DECODED / RUNTIME OUTPUT TRUTH
    what the selected runtime branch actually outputs
```

## 212.1 Contratos

```python
from dataclasses import dataclass
from enum import Enum

class ElementaryEncoding(Enum):
    PCM = "pcm"
    DSD = "dsd"
    COMPRESSED = "compressed"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class ContainerAudioFacts:
    container: str | None
    codec: str | None
    channels: int | None
    nominal_dsd_bits_per_second_per_channel: int | None
    evidence_ref: str

@dataclass(frozen=True, slots=True)
class ElementaryStreamObservation:
    encoding: ElementaryEncoding
    caps_media_type: str | None
    caps_fields: tuple[tuple[str, str], ...]
    provider: str
    evidence_ref: str

@dataclass(frozen=True, slots=True)
class DsdSourceCharacterization:
    container_facts: ContainerAudioFacts
    elementary: ElementaryStreamObservation
    signal: "DsdSignalFormatV2"
    native_branch_available: bool
    dsd_to_pcm_branch_available: bool
    runtime_requirements: tuple[str, ...]
    evidence_refs: tuple[str, ...]
```

## 212.2 Estrategia GStreamer

La implementación F07 debe construir un probe aislado que observe la rama seleccionada **antes** de un decoder DSD→PCM. El algoritmo normativo es:

```text
A. typefind / container discovery
B. demux stage
C. intercept dynamic elementary audio pad
D. inspect current/template caps
E. if DSD -> record DSD elementary truth
F. only then allow a chosen decode/output strategy
G. separately inspect final branch caps
```

Para DSF, el runtime puede disponer de `avdemux_dsf`. Para DFF/DSDIFF y otros contenedores, la fase debe registrar el demuxer realmente seleccionado en el environment manifest. No se permite hardcodear un demuxer inexistente.

## 212.3 Regla autoplug

```text
playbin3/uridecodebin3 final audio/x-raw
    != proof source was PCM

playbin3/uridecodebin3 final audio/x-dsd
    = useful runtime evidence, but still record upstream elementary identity
```

## 212.4 Pseudocódigo productivo

```python
class GStreamerDsdSourceProbe:
    def characterize(self, path: Path) -> DsdSourceCharacterization:
        container = self._container_probe(path)
        branch = self._elementary_branch_probe(path)
        if branch.encoding is not ElementaryEncoding.DSD:
            raise SourceCharacterizationError(
                "SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN",
                f"elementary encoding={branch.encoding.value}",
            )
        signal = self._normalize_dsd_caps(branch)
        return DsdSourceCharacterization(
            container_facts=container,
            elementary=branch,
            signal=signal,
            native_branch_available=self._native_route_available(signal),
            dsd_to_pcm_branch_available=self._dsd_decoder_available(signal),
            runtime_requirements=self._requirements(signal),
            evidence_refs=(container.evidence_ref, branch.evidence_ref),
        )
```

## 212.5 Failure semantics

```text
SOURCE_DSD_CONTAINER_UNKNOWN
SOURCE_DSD_DEMUXER_UNAVAILABLE
SOURCE_DSD_ELEMENTARY_STREAM_NOT_PROVEN
SOURCE_DSD_CAPS_INCOMPLETE
SOURCE_DSD_GROUPING_UNKNOWN
SOURCE_DSD_RATE_UNIT_INVALID
SOURCE_DSD_CHANNEL_LAYOUT_UNKNOWN
SOURCE_DSD_PROBE_TIMEOUT
SOURCE_DSD_PROBE_CLEANUP_FAILED
```

`SOURCE_DSD_DEMUXER_UNAVAILABLE` no significa que el archivo sea inválido; significa que este runtime no puede demostrar la ruta first-class requerida.


------------------------------------------------------------------------

# 213. ALSA NATIVE DSD TRANSPORT V2 — EXACT TUPLE POR GROUPING Y READBACK

El probe ALSA deja de usar un `bit_rate_hz` ambiguo y negocia un tuple físico específico.

```python
@dataclass(frozen=True, slots=True)
class AlsaDsdTuple:
    format_name: str
    frame_rate_hz: int
    channels: int
    sample_width_bits: int
    source_bits_per_second_per_channel: int

    def __post_init__(self) -> None:
        if self.frame_rate_hz <= 0 or self.channels <= 0:
            raise ValueError("invalid ALSA DSD tuple")
        if self.sample_width_bits not in {8, 16, 32}:
            raise ValueError("invalid DSD grouping width")
        if self.frame_rate_hz * self.sample_width_bits != self.source_bits_per_second_per_channel:
            raise ValueError("ALSA grouping/rate does not preserve source DSD bit rate")

@dataclass(frozen=True, slots=True)
class AlsaDsdProbeEvidence:
    stable_device_id: str
    requested: AlsaDsdTuple
    negotiated: AlsaDsdTuple | None
    supported: bool | None
    disposition: str
    errno: int | None
    environment_fingerprint: str
    binding_generation: int
    evidence_ref: str
```

## 213.1 Candidate generation

```python
def native_dsd_candidates(source: DsdSourceBitRate, channels: int):
    for grouping in AlsaDsdGrouping:
        rate = source_to_alsa_rate(source, grouping)
        yield AlsaDsdTuple(
            format_name=grouping.alsa_format_name,
            frame_rate_hz=rate.frames_per_second,
            channels=channels,
            sample_width_bits=grouping.bits_per_alsa_sample,
            source_bits_per_second_per_channel=source.bits_per_second_per_channel,
        )
```

No existe prioridad universal U32 > U16 > U8. La selección debe basarse en exact qualification + driver/device policy; si varios tuples son válidos, el planner aplica una policy documentada y registrable.

## 213.2 Negativos válidos

Sólo un rechazo exacto de parámetros puede producir `supported=False`. Mantener la regla V3.5:

```text
BUSY       -> UNKNOWN
TIMEOUT    -> UNKNOWN
REMOVED    -> UNKNOWN
EPIPE/XRUN -> runtime failure, not static unsupported
EINVAL on exact hw_params candidate, after binding validation -> may support negative evidence
```

## 213.3 Cache invalidation

DSD qualification se invalida por:

```text
kernel identity change
ALSA library major/minor policy change when declared relevant
device firmware/profile revision change if observable
USB topology/binding identity change that changes stable endpoint signature
Michi probe algorithm revision
manual purge
```


------------------------------------------------------------------------

# 214. NATIVE DSD STRICT PATH V2 — `dsdconvert` DE NORMALIZACIÓN Y `alsasink` REAL

GStreamer `alsasink` publica actualmente `audio/x-dsd` con `reversed-bytes=false`. Por tanto el strict path debe normalizar bit order antes del sink si la fuente llega reversed.

## 214.1 `DsdSignalFormatV2`

```python
@dataclass(frozen=True, slots=True)
class DsdSignalFormatV2:
    source_rate: DsdSourceBitRate
    gst_grouping: str
    channels: int
    positions: tuple[str, ...]
    reversed_bytes: bool
```

## 214.2 Strict recipe

```python
@dataclass(frozen=True, slots=True)
class StrictDsdSinkRecipeV2:
    plan_id: str
    device: str
    gst_dsd_format: str
    gst_rate_bytes_per_second_per_channel: int
    channels: int
    normalize_reversed_bytes: bool
    target_reversed_bytes: bool = False

    def caps_string(self) -> str:
        if self.target_reversed_bytes:
            raise ValueError("alsasink target must remain reversed-bytes=false")
        return (
            "audio/x-dsd,"
            f"format={self.gst_dsd_format},"
            f"rate={self.gst_rate_bytes_per_second_per_channel},"
            f"channels={self.channels},"
            "layout=interleaved,"
            "reversed-bytes=false"
        )
```

## 214.3 Graph permitido

```text
source audio/x-dsd reversed=false
    ↓
capsfilter
    ↓
alsasink
```

O:

```text
source audio/x-dsd reversed=true / different grouping
    ↓
dsdconvert
    ↓ prove:
       rate bytes/s/channel unchanged
       channels unchanged
       only grouping/bit-order changed
    ↓
capsfilter reversed-bytes=false
    ↓
alsasink
```

`dsdconvert` activo aquí se clasifica como `DSD_REPRESENTATION_ADAPTATION`; no como DSD→PCM.

## 214.4 Runtime validation

Debe observar:

```text
upstream media type == audio/x-dsd
post-dsdconvert media type == audio/x-dsd
post-dsdconvert rate == source gst byte rate
post-dsdconvert channels == source channels
sink caps reversed-bytes == false
sink device == planned ALSA binding
no audio/x-raw node exists in selected Native branch
no PCM DSP nodes exist
software gain == unity/fixed according to output policy
```

Cualquier `audio/x-raw` en la selected Native branch produce `NATIVE_DSD_PCM_CONVERSION_DETECTED` y termina el candidate.


------------------------------------------------------------------------

# 215. DOP EVIDENCE MODEL V2 — CARRIER CAPABILITY ≠ DAC INTERPRETATION

Se eliminan los booleanos ambiguos de `DopQualification`.

```python
class DopCarrierSupport(Enum):
    QUALIFIED = "qualified"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    INCONCLUSIVE = "inconclusive"

class DopInterpretationState(Enum):
    UNKNOWN = "unknown"
    DECLARED = "declared"
    USER_CONFIRMED = "user_confirmed"
    DEVICE_OBSERVED = "device_observed"
    PHYSICALLY_QUALIFIED = "physically_qualified"
    CONTRADICTED = "contradicted"

@dataclass(frozen=True, slots=True)
class DopCarrierQualification:
    stable_device_id: str
    carrier_layout_id: str
    carrier_rate_hz: int
    alsa_format: str
    channels: int
    support: DopCarrierSupport
    environment_fingerprint: str
    evidence_refs: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class DopDeviceInterpretationEvidence:
    stable_device_id: str
    source_dsd_multiplier: int | None
    state: DopInterpretationState
    source: str
    device_revision: str | None
    evidence_refs: tuple[str, ...]
```

## 215.1 Planner gate

Para `AUTO`:

```text
carrier QUALIFIED
AND interpretation in {DEVICE_OBSERVED, PHYSICALLY_QUALIFIED}
    -> DoP may auto-select if policy allows
```

Para selección explícita del usuario:

```text
carrier QUALIFIED
AND interpretation in {DECLARED, USER_CONFIRMED, DEVICE_OBSERVED, PHYSICALLY_QUALIFIED}
    -> may execute
    -> UI confidence remains truthful
```

Nunca:

```text
carrier QUALIFIED alone -> DoP-capable DAC
```

## 215.2 UI truth

```text
Carrier         Verified
DAC interpretation   User confirmed
```

no debe renderizarse como:

```text
DoP Verified
```

sin aclarar qué capa fue verificada.


------------------------------------------------------------------------

# 216. DOP CARRIER LAYOUT V2 — BYTE LAYOUT, 24-IN-32 Y ENDIANNESS EXPLÍCITOS

DoP no queda completamente especificado hasta definir cómo los 24 bits `[payload0,payload1,marker]` ocupan la memoria que GStreamer/ALSA transmite.

```python
class DopCarrierLayout(Enum):
    PACKED_24_LE = "packed_24_le"
    S32_LE_LSB24 = "s32_le_lsb24"
    S32_LE_MSB24 = "s32_le_msb24"

@dataclass(frozen=True, slots=True)
class DopCarrierMemoryContract:
    layout: DopCarrierLayout
    alsa_format: str
    container_bits: int
    significant_transport_bits: int
    payload_byte_offsets: tuple[int, int]
    marker_byte_offset: int
    padding_byte_offsets: tuple[int, ...]
    padding_value: int
```

## 216.1 Canonical byte encoders

```python
def encode_dop24(payload0: int, payload1: int, marker: int, layout: DopCarrierLayout) -> bytes:
    values = (payload0 & 0xFF, payload1 & 0xFF, marker & 0xFF)
    if layout is DopCarrierLayout.PACKED_24_LE:
        return bytes(values)
    if layout is DopCarrierLayout.S32_LE_LSB24:
        return bytes((*values, 0x00))
    if layout is DopCarrierLayout.S32_LE_MSB24:
        return bytes((0x00, *values))
    raise AssertionError(layout)
```

No se activa un layout porque “parece lógico”. Cada binding/layout necesita qualification específica y vectores físicos cuando la interpretación final del DAC forme parte del claim.

## 216.2 Contract matrix

| Layout | Candidate ALSA representation | Bytes por canal/frame | Estado inicial |
|---|---|---:|---|
| `PACKED_24_LE` | `S24_3LE` cuando endpoint lo acepte | 3 | qualified-only |
| `S32_LE_LSB24` | `S32_LE`, DoP in low 24 bits | 4 | qualified-only |
| `S32_LE_MSB24` | `S32_LE`, DoP in high 24 bits | 4 | disabled until a real target requires/proves it |

## 216.3 Forbidden ambiguity

No se permite un campo único:

```text
carrier_format="S32_LE"
```

Debe existir además:

```text
carrier_layout_id
significant_transport_bits
marker_byte_offset
padding rule
```


------------------------------------------------------------------------

# 217. DOP RUNTIME V2 — PACKER STREAMING, DISCONT, SEEK Y ABI DE PLUGIN NATIVO

## 217.1 Estado streaming

El packer productivo debe soportar chunks arbitrarios. El contrato pure-Python de conformance se amplía para conservar bytes sobrantes en vez de exigir siempre input par por llamada.

```python
@dataclass(slots=True)
class DopStreamingState:
    marker_phase: int = 0
    pending_left: bytearray = field(default_factory=bytearray)
    pending_right: bytearray = field(default_factory=bytearray)
    discontinuity_generation: int = 0

    def reset_for_discontinuity(self) -> None:
        self.marker_phase = 0
        self.pending_left.clear()
        self.pending_right.clear()
        self.discontinuity_generation += 1
```

Regla:

```text
arbitrary input buffer boundary
    MUST NOT alter output byte stream
```

## 217.2 Seek

```text
SEEK REQUEST
    ↓
block/flush old branch
    ↓
seek DSD source to a byte/group boundary proven by demuxer
    ↓
issue DISCONT generation
    ↓
reset DoP marker phase to canonical stream-start phase
    ↓
record SignalPath reason=DOP_MARKER_RESET_AFTER_SEEK
    ↓
resume
```

No continuar la marker phase antigua después de un discontinuity que descarta source bytes.

## 217.3 Rust/GStreamer ABI mínimo si F09 aprueba plugin nativo

```text
factory:            michidop
minimum API:        GStreamer stable Rust bindings selected by ADR
sink:               audio/x-dsd
src:                exact negotiated carrier caps
property:
  carrier-layout    enum
  reverse-payload-bits bool
  reset-on-discont  true (v1 mandatory)
messages:
  dop-discont-reset
  dop-alignment-error
  dop-layout-error
  dop-marker-state
```

Hot transform rules:

```text
NO filesystem
NO network
NO SQLite
NO unbounded allocation per transform call
NO Python callback per frame
NO logging per audio frame
NO blocking mutex shared with UI
NO panic/exception crossing plugin boundary
```

## 217.4 Cross-language conformance

Python reference and native plugin consume the same vector corpus. The artifact must include:

```text
vectors.schema.json
vectors/*.json
sha256 manifest
python result digest
native result digest
```

Both digests must match.


------------------------------------------------------------------------

# 218. DSP TRANSACTION V2 — COMMIT REAL, SIN MODIFICAR EL GRAPH ACTIVO EN PREPARE

La implementación histórica instalaba `audio-filter=B` durante `prepare(B)`, cruzando el límite destructivo antes del commit. Se sustituye por dos modos explícitos.

## 218.1 Modo CORE obligatorio: `QUIESCENT_REBUILD`

Primera implementación productiva, prioriza coherencia sobre “live magic”.

```text
capture playback logical snapshot
        ↓
PAUSE or controlled STOP according to backend state contract
        ↓
freeze acceptance epoch
        ↓
build candidate graph B off the live path
        ↓
validate factories/properties/assets
        ↓
install B while transport is quiescent
        ↓
preroll
        ↓
inspect real runtime B
        ↓
COMMIT application state
        ↓
restore position/state according to explicit no-autoplay policy
```

Ante fallo después de retirar A pero antes de commit B:

```text
attempt restore A from immutable compiled plan + assets
if restore proven -> predecessor restored
else -> playback STOPPED + DSP_FAILED_SAFE
```

Nunca reportar A como activo si el runtime no pudo restaurarlo.

## 218.2 Modo opcional posterior: `DUAL_BRANCH_SWITCH`

Sólo tras performance/physical gate:

```text
always-owned processing container
        ├─ active branch A
        └─ candidate branch B
                ↓ preroll/inspect
pad block / selector switch / controlled envelope
                ↓
commit B
                ↓
retire A
```

No se habilita hasta demostrar ausencia de XRUN/clicks en F14.

## 218.3 State machine

```python
class ProcessingTransitionState(Enum):
    IDLE = "idle"
    COMPILING = "compiling"
    PREPARING_OFFLINE = "preparing_offline"
    QUIESCING_TRANSPORT = "quiescing_transport"
    INSTALLING = "installing"
    PREROLLING = "prerolling"
    VERIFYING = "verifying"
    COMMITTING = "committing"
    ACTIVE = "active"
    RESTORING_PREDECESSOR = "restoring_predecessor"
    FAILED_SAFE = "failed_safe"
```

## 218.4 Receipt

```python
@dataclass(frozen=True, slots=True)
class ProcessingTransitionReceipt:
    transition_id: str
    predecessor_graph_id: str | None
    predecessor_revision: int | None
    candidate_graph_id: str
    candidate_revision: int
    playback_request_epoch: int
    output_generation: int
    processing_generation: int
    destructive_boundary_crossed: bool
```

Todo abort debe decidir usando `destructive_boundary_crossed`, nunca asumir rollback gratuito.


------------------------------------------------------------------------

# 219. DSP BACKEND ADAPTERS V2 — CADA NODO TIENE COMPILADOR, FACTORY Y VERIFICADOR

No se permite un genérico `_apply_property` que silencie parámetros desconocidos. Cada node kind posee adapter tipado.

```python
class ProcessingNodeAdapter(Protocol):
    kind: ProcessingNodeKind
    def validate(self, node, input_signal, assets) -> None: ...
    def compile_properties(self, node, input_signal, assets) -> tuple[tuple[str, object], ...]: ...
    def build(self, gst, compiled_node): ...
    def inspect(self, element, expected, generation): ...
```

## 219.1 Registry cerrado

```text
PREAMP       -> GStreamerGainAdapter
PEQ          -> GStreamerParametricEqAdapter
FIR          -> GStreamerFirAdapter
CONVOLUTION  -> GStreamerConvolutionAdapter
RESAMPLE     -> GStreamerResampleAdapter
DITHER       -> GStreamerDitherAdapter or NOT_SUPPORTED
BALANCE      -> GStreamerBalanceAdapter
POLARITY     -> GStreamerPolarityAdapter
DELAY        -> GStreamerDelayAdapter
CHANNEL_MAP  -> GStreamerChannelMapAdapter
CROSSFEED    -> adapter only after algorithm ADR
LOUDNESS     -> adapter only after loudness model ADR
```

No arbitrary plugin property names cross from profile JSON to GStreamer.

## 219.2 PEQ

PEQ adapter must map each band deterministically and fail if backend cannot represent a requested filter type. No silent approximation.

```python
@dataclass(frozen=True, slots=True)
class PeqBackendBand:
    backend_index: int
    type_name: str
    frequency_hz: float
    q: float
    gain_db: float
```

## 219.3 FIR / convolution

Compiled plan contains:

```text
ir_content_sha256
source_sample_rate
compiled_sample_rate
channels
frames
normalization policy
latency frames
asset schema version
```

IR mismatch never causes hidden resampling; explicit policy either rejects or inserts an explicit `ResampleNode` for the IR preparation stage before playback, producing a new content-addressed asset.

## 219.4 Dither

Dither is permitted only when there is an explicit precision reduction boundary. The compiler refuses:

```text
dither with no precision reduction
multiple dithers on same terminal chain
noise shaping not represented by a selected algorithm/version
```


------------------------------------------------------------------------

# 220. DSP RUNTIME EVIDENCE V2 — OBSERVAR CAPS, ACTIVIDAD, LATENCIA Y PARÁMETROS REALES

El runtime no puede construir evidence marcando todos los nodos `ACTIVE` por el mero hecho de existir.

## 220.1 Snapshot por nodo

```python
@dataclass(frozen=True, slots=True)
class ProcessingNodeRuntimeEvidenceV2:
    node_id: str
    adapter_id: str
    backend_factory: str
    element_identity: str
    expected_parameter_digest: str
    observed_parameter_digest: str | None
    sink_signal: SignalFormat | None
    src_signal: SignalFormat | None
    activity: ProcessingActivity
    latency_frames_reported: int | None
    generation: int
    evidence_refs: tuple[str, ...]
```

## 220.2 Activity resolution

```text
node absent                              NOT_PRESENT
node present + input/output prove delta  ACTIVE
node present + pass-through proved       PRESENT_PASS_THROUGH
node present + insufficient observation  PRESENT_STATE_UNKNOWN
backend cannot expose state              NOT_OBSERVABLE
```

PEQ/gain/FIR are sample-value transforms even when caps do not change. Para ellos `activity` se prueba por:

```text
actual element present
AND observed parameters == compiled parameters
AND graph generation current
AND runtime branch owns element
```

No por caps delta.

Resampler/remixer/converter sí requieren comparar caps.

## 220.3 Graph inspection completeness

```text
all planned node IDs located exactly once
no unplanned transform factory in selected branch
parameter digests match
sink/src caps observed where applicable
latency query captured or explicitly NOT_OBSERVABLE
unexpected factory -> CONTRADICTED
missing planned node -> CONTRADICTED
```

## 220.4 XRUN truth

`xruns=0` may only be emitted from an actual counter/observer. Absence of a counter = `None/NOT_OBSERVABLE`, never zero.


------------------------------------------------------------------------

# 221. DSD→PCM V2 — BACKEND PRODUCTIVO SELECCIONADO Y CONTRATO DE CONVERSIÓN

La fase deja de decir “investigar una ruta”. El backend CORE para Linux/GStreamer será el decoder DSD de `gst-libav` cuando las factories requeridas estén presentes. GStreamer expone actualmente `avdec_dsd_lsbf`, `avdec_dsd_msbf` y variantes planar, con salida `audio/x-raw` float; el runtime exacto se descubre en F00/F10.

## 221.1 Backend policy

```text
CORE preferred: GStreamer gst-libav avdec_dsd_* inside Michi-owned pipeline
OPTIONAL reference: direct FFmpeg/libswresample offline conformance harness
FORBIDDEN: invisible decoder auto-selected without node/evidence
```

## 221.2 Port

```python
class DsdToPcmRuntimePort(Protocol):
    @property
    def backend_id(self) -> str: ...
    def capabilities(self) -> "DsdToPcmCapabilities": ...
    def prepare(self, plan: "DsdToPcmPlan", generation: int) -> str: ...
    def inspect(self, receipt: str) -> "DsdToPcmRuntimeEvidence": ...
    def release(self, receipt: str, reason: str) -> None: ...
```

## 221.3 Plan

```python
@dataclass(frozen=True, slots=True)
class DsdToPcmPlan:
    plan_id: str
    source: DsdSignalFormatV2
    decoder_factory: str
    target_rate_hz: int
    target_format: str       # core: F32LE processing domain
    channels: int
    quality_profile: str
    lowpass_profile_id: str
    backend_version: str
    evidence_refs: tuple[str, ...]
```

## 221.4 Decoder selection

```text
source bit order/grouping
    ↓
select exact avdec_dsd_* factory
    ↓
DSD decoder
    ↓
audio/x-raw F32LE
    ↓
explicit resample only if target policy requires
    ↓
ProcessingGraph
```

El decoder mismo constituye el nodo `DSD_TO_PCM`; cualquier resampling posterior es otro nodo separado.

## 221.5 Quality profiles become actual contracts

```text
FAST       developer/test profile; not default audiophile
BALANCED   bounded CPU; documented response
HIGH       default if conversion chosen
REFERENCE  highest validated quality; may use larger latency/CPU
```

No se cierra cada profile hasta que §222 asigne filtros/response/latency reproducibles.


------------------------------------------------------------------------

# 222. DSD→PCM QUALITY / CONFORMANCE V2 — RESPUESTA, RUIDO, LATENCIA Y TARGET-RATE POLICY

## 222.1 Target-rate family policy

Default conservative mapping remains in the 44.1 kHz family:

```text
DSD64   -> 176.4 kHz PCM candidate
DSD128  -> 176.4 or 352.8 kHz according to device/DSP capability policy
DSD256  -> 352.8 kHz candidate when pipeline/device supports; otherwise explicit bounded fallback
DSD512+ -> no implicit support; capability/benchmark gate required
```

No target rate is chosen merely because the DAC advertises a maximum. The policy combines:

```text
source family
processing backend max validated rate
device exact qualification
CPU/performance budget
user policy
```

## 222.2 Conformance metrics

Cada quality profile publica:

```text
passband edge
passband ripple
gain normalization
stopband onset
minimum stopband attenuation
ultrasonic noise policy
latency samples
initial transient handling
flush tail frames
CPU p95 reference
backend/version
```

## 222.3 Reference fixtures

```text
DSD constant +1/-1 patterns
known low-frequency sine encoded to DSD fixture
near-Nyquist audio-band tones
ultrasonic-heavy DSD fixture
impulse-like transition fixture
silence/noise-shaped fixture
```

## 222.4 Acceptance

A DSD→PCM backend passes only when its captured float output is compared against a versioned reference harness within documented tolerance. “Sounds fine” is not evidence.


------------------------------------------------------------------------

# 223. STATEFUL AUDIO SEMANTICS V2 — SEEK, PAUSE, EOS, FLUSH Y GAPLESS

Cada stateful component declares reset/drain semantics.

```python
class StatefulAudioAction(Enum):
    PRESERVE = "preserve"
    FLUSH = "flush"
    DRAIN = "drain"
    RESET = "reset"
    REBUILD = "rebuild"
    REOPEN_OUTPUT = "reopen_output"
    STOP_REQUIRED = "stop_required"
```

## 223.1 Canonical state table

| Component | Seek | Pause | Resume | EOS | Track boundary same format | Format-family change |
|---|---|---|---|---|---|---|
| Preamp/PEQ | preserve params, flush buffers | preserve | preserve | drain none | preserve graph | rebuild/reopen if required |
| FIR | flush convolution history | preserve state | continue | drain tail by gapless policy | reset history at exact track boundary unless album-continuous policy | rebuild |
| Resampler | flush phase/history | preserve | continue | drain algorithmic tail | reset according to gapless transition policy | rebuild |
| DoP packer | reset marker on DISCONT | preserve marker if no data discarded | continue | close frame cleanly | new logical stream resets marker phase | reopen |
| DSD→PCM | flush decoder/filter history | preserve | continue | drain documented tail | reset decoder at new source | rebuild |
| Native DSD | source-position alignment | keep device mode where qualified | resume | stop policy | preserve only if exact safe transition proven | reopen |

## 223.2 Gapless levels

```text
GAPLESS_EXACT
GAPLESS_SAME_GRAPH
GAPLESS_DEGRADED_REOPEN
NOT_GAPLESS_BY_POLICY
```

UI/Signal Path diagnostics may expose degradation reasons, but playback never fabricates gaplessness.

## 223.3 FIR tail policy

Music playback default:

```text
track boundary in same album/session
    -> no artificial reverberant tail appended across next track unless convolution profile explicitly defines continuous room-correction behavior
```

Room correction FIR is a continuous linear system and generally retains filter state across contiguous gapless tracks when sample format/graph are unchanged. A seek or discontinuity flushes history.


------------------------------------------------------------------------

# 224. CLICK/POP PREVENTION Y PARAMETER-SMOOTHING POLICY

Un producto audiófilo no puede limitarse a “state changed successfully”; también debe evitar discontinuidades audibles introducidas por su propio control plane.

## 224.1 Mutation classes

```python
class AudioMutationClass(Enum):
    LIVE_SAFE = "live_safe"
    RAMP_REQUIRED = "ramp_required"
    COEFFICIENT_MORPH_REQUIRED = "coefficient_morph_required"
    GRAPH_REBUILD_REQUIRED = "graph_rebuild_required"
    OUTPUT_REOPEN_REQUIRED = "output_reopen_required"
    STOP_REQUIRED = "stop_required"
```

Default classification:

```text
preamp gain              RAMP_REQUIRED
mute/unmute              RAMP_REQUIRED unless hardware authority handles pop-free transition
PEQ band enable/gain     COEFFICIENT_MORPH_REQUIRED or graph rebuild in v1
FIR/IR replacement       GRAPH_REBUILD_REQUIRED
resample target          GRAPH_REBUILD_REQUIRED
channel map              GRAPH_REBUILD_REQUIRED
PCM ↔ Native DSD         OUTPUT_REOPEN_REQUIRED
Native DSD ↔ DoP         OUTPUT_REOPEN_REQUIRED
DoP layout change        OUTPUT_REOPEN_REQUIRED
```

## 224.2 Core v1 safe policy

Si el backend no ofrece coefficient morphing demostrado:

```text
quiesce
short output envelope where software gain is semantically allowed
replace graph
preroll
restore
```

No aplicar software envelope sobre bit-perfect/Native DSD/DoP paths donde tocar samples/carrier viola la política. En esos paths se usa device-safe stop/reopen policy cualificada.

## 224.3 Physical gate

F14 debe registrar click/pop observations con al menos:

```text
headphone/line output listening safety protocol
audio interface loopback capture when possible
peak transient analysis around transitions
repeat count
exact mutation event timestamp
```


------------------------------------------------------------------------

# 225. NATIVE DSD EXECUTOR V2 — TRANSACTION Y VALIDACIÓN END-TO-END

Native DSD no es sólo un sink recipe. Necesita la misma disciplina de `prepare/commit/abort/release` que PCM Direct.

```python
@dataclass(frozen=True, slots=True)
class NativeDsdExecutionHandle:
    plan_id: str
    execution_generation: int
    binding_generation: int
    receipt: str

@dataclass(frozen=True, slots=True)
class NativeDsdRuntimeEvidence:
    handle: NativeDsdExecutionHandle
    source_signal: DsdSignalFormatV2
    sink_caps_rate_bytes_per_channel: int
    sink_caps_format: str
    sink_caps_channels: int
    reversed_bytes: bool
    selected_branch_factories: tuple[str, ...]
    contains_audio_x_raw: bool
    device_locator: str
    graph_inspection_complete: bool
```

Candidate fail conditions:

```text
binding generation changed
sink device changed
caps rate uses wrong unit
post-normalization reversed-bytes != false
any audio/x-raw on selected Native branch
unplanned decoder/converter
processing graph attached
software volume mutation active
runtime branch not fully inspectable
```

Commit only after all are false and ALSA exact qualification evidence matches the plan.


------------------------------------------------------------------------

# 226. DOP PLANNER / EXECUTOR V2 — DOBLE GATE Y CARRIER EXACTO

```python
@dataclass(frozen=True, slots=True)
class DopExecutionPlanV2:
    plan_id: str
    source: DsdSignalFormatV2
    carrier_rate: DopCarrierRate
    memory_contract: DopCarrierMemoryContract
    binding_generation: int
    stable_device_id: str
    carrier_evidence_refs: tuple[str, ...]
    interpretation_evidence_refs: tuple[str, ...]
    interpretation_state: DopInterpretationState
    packer_revision: str
```

Planner algorithm:

```text
1 source DSD truth current
2 explicit/user/auto DoP policy valid
3 exact carrier layout qualification QUALIFIED
4 device interpretation evidence acceptable for selected policy
5 binding generation current
6 no DSP active
7 volume authority cannot mutate carrier
8 build immutable plan
```

Runtime commit:

```text
install packer
set exact carrier caps
preroll
inspect caps/layout
verify no resampler/remix/audioconvert mutation
verify packer revision
verify current generation
commit
```

`interpretation_state=USER_CONFIRMED` remains visible after successful software runtime; it is not promoted automatically to `PHYSICALLY_QUALIFIED`.


------------------------------------------------------------------------

# 227. DSD ↔ PCM ↔ DSP POLICY V2 — DECISION TABLE CERRADA

No existe policy implícita. La aplicación resuelve con una función pura sobre:

```text
source family
user DSD policy
selected DSP profile
Native capability
DoP carrier capability
DoP interpretation evidence
DSD→PCM backend capability
output device capability
active engine capability
```

## 227.1 Canonical decisions

| Source | DSP request | Preferred DSD mode | Evidence | Decision |
|---|---|---|---|---|
| PCM | OFF | n/a | PCM exact | PCM Direct candidate |
| PCM | ON | n/a | DSP backend | PCM Processed |
| DSD | OFF | AUTO | Native qualified | Native DSD |
| DSD | OFF | AUTO | Native no, DoP physical qualified | DoP |
| DSD | OFF | AUTO | Native/DoP unavailable, conversion allowed | DSD→PCM |
| DSD | ON | any preserve mode | DSD→PCM available | explicit DSD→PCM + DSP |
| DSD | ON | preserve-only | — | refuse DSP with actionable reason |
| DSD | OFF | DOP | carrier qualified + policy evidence | DoP |
| DSD | OFF | NATIVE | Native unknown | refuse/fallback only if explicit fallback policy |

## 227.2 No silent fallback

Every fallback has a code:

```text
DSD_FALLBACK_NATIVE_TO_DOP_EXPLICIT
DSD_FALLBACK_NATIVE_TO_PCM_EXPLICIT
DSD_DSP_FORCES_PCM_EXPLICIT
DSD_NO_SAFE_OUTPUT_PATH
```

The NowPlaying/Signal Path UI shows the resulting path, not merely the requested preference.


------------------------------------------------------------------------

# 228. SIGNAL PATH GRAPH V2 — TOPOLOGÍA VÁLIDA, CONTINUIDAD Y ENUMS TIPADOS

`SignalPathSnapshot` debe ser un DAG válido, no sólo una colección de IDs.

```python
class PathVerdict(Enum):
    DIRECT = "direct"
    NATIVE_DSD = "native_dsd"
    DOP = "dop"
    PROCESSED = "processed"
    RESAMPLED = "resampled"
    REMIXED = "remixed"
    DSD_TO_PCM = "dsd_to_pcm"
    SHARED = "shared"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"

class ProofProjectionState(Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    BROKEN = "broken"
    NOT_APPLICABLE = "not_applicable"
```

## 228.1 Graph invariants

```text
GRAPH-01 node ids unique
GRAPH-02 edges reference existing nodes
GRAPH-03 DAG acyclic
GRAPH-04 exactly one active source root for a single-output session
GRAPH-05 exactly one terminal output/device path unless future zone graph explicitly selected
GRAPH-06 every ACTIVE node reachable from root
GRAPH-07 no disconnected evidence-bearing active node
GRAPH-08 node generation matches snapshot identity unless explicitly historical
GRAPH-09 edge output_signal compatible with next input_signal
GRAPH-10 stage transitions belong to allowed transition matrix
GRAPH-11 proof state originates from M11.5 adapter, not graph heuristics
GRAPH-12 candidate graph cannot replace ACTIVE snapshot before commit
```

## 228.2 Cycle validation

```python
def assert_acyclic(nodes, edges):
    outgoing = {n.node_id: [] for n in nodes}
    indegree = {n.node_id: 0 for n in nodes}
    for e in edges:
        outgoing[e.source_node_id].append(e.target_node_id)
        indegree[e.target_node_id] += 1
    queue = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while queue:
        current = queue.pop()
        visited += 1
        for nxt in outgoing[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if visited != len(nodes):
        raise ValueError("SignalPathGraph contains a cycle")
```


------------------------------------------------------------------------

# 229. DEVICE INTELLIGENCE V2 — RECOMENDACIÓN NO ES VERDAD RUNTIME

Native Profiles y MAHKB pueden sugerir configuración sólo después de que F10 cierre transportes y DSP. Esto justifica la dependencia `AP2-F12 -> AP2-F10`.

```text
Knowledge says      "prefer Native DSD"
Runtime says        Native unavailable
Result              runtime wins; recommendation marked unavailable

Knowledge says      "DoP supported"
Physical evidence   contradicted on current revision
Result              DoP forbidden; contradiction visible
```

## 229.1 Recommendation type

```python
@dataclass(frozen=True, slots=True)
class AudioRecommendation:
    recommendation_id: str
    device_match_id: str
    desired_policy: dict[str, object]
    rationale_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    reversible: bool
    algorithm_version: str
```

Applying recommendation creates user/configuration state, never capability evidence.


------------------------------------------------------------------------

# 230. SECURITY V2 — IR, MAHKB, NATIVE PLUGINS Y DIAGNÓSTICOS

## 230.1 IR import threat model

Mandatory guards:

```text
max file bytes
max decoded frames
max channels
max sample rate
finite numeric samples only
no NaN/Inf
content hash before durable install
copy into owned store, never execute/read mutable original at playback time
symlink resolved and rejected when escaping allowed root
atomic temp-file + fsync + rename
no archive extraction in core v1
```

## 230.2 MAHKB update model

```text
signed manifest
schema version
content SHA-256
minimum app version
maximum compatible schema
generation/version monotonicity
atomic staging
verify before replace
rollback to previous verified snapshot
anti-downgrade policy after a security-relevant revocation
```

## 230.3 Native plugin supply chain

If `michi-dop` or future native DSP is shipped:

```text
reproducible build target where feasible
source revision embedded
binary hash surfaced in diagnostics
SBOM entry
license manifest
architecture triplet
ABI version handshake
fail closed on ABI mismatch
Flatpak/AppImage/deb packaging tests
```

## 230.4 Diagnostic redaction

Default bundle redacts:

```text
absolute music paths
user names/home directory
DAC serial numbers unless explicit opt-in
network addresses
IR source filenames outside Michi store
```

Stable pseudonymous device IDs may be included only if they cannot trivially expose raw serials.


------------------------------------------------------------------------

# 231. REAL-TIME SAFETY CONTRACT — AUDIO CALLBACK / GST TRANSFORM BOUNDARY

Every component that can execute on a streaming thread must satisfy:

```text
RT-01 no filesystem I/O
RT-02 no SQLite
RT-03 no network
RT-04 no blocking UI synchronization
RT-05 no unbounded queue growth
RT-06 no per-frame logging
RT-07 no Python per-sample loop in productive path
RT-08 no dynamic plugin discovery during streaming
RT-09 no arbitrary allocation proportional to untrusted frame count without bound
RT-10 no FFI exception/panic escapes
RT-11 control-plane parameter update delivered as bounded immutable snapshot
RT-12 telemetry aggregated outside hot path
```

## 231.1 Control-plane handoff

```text
UI intent
   ↓ owner thread validates
immutable compiled parameter block
   ↓ generation/revision tagged
streaming thread swaps pointer/state at safe boundary
   ↓
ack event
   ↓ owner commits presentation state
```

No streaming callback calls QML or persistence.


------------------------------------------------------------------------

# 232. PHYSICAL QUALIFICATION V2 — PROTOCOLO DE LABORATORIO REPRODUCIBLE

Cada run sheet contiene al menos:

```text
artifact_schema
repository_sha
spec_sha
phase
host_id pseudonymous
CPU/model
kernel
ALSA library
GStreamer version + plugin registry hash
Michi package/build id
DAC commercial identity
USB VID/PID
firmware if observable
stable endpoint signature
USB topology
power mode
cable/interface notes
fixture SHA-256
requested path
requested format
expected result
actual runtime evidence refs
start timestamp
run duration
repeat index
XRUN count/method
failure code
operator note
artifact hashes
```

## 232.1 Durations

Minimum qualification classes:

```text
SMOKE        60 s per tuple
STABILITY    30 min per representative tuple/path
SOAK         8 h for at least one PCM Direct path and one DSP representative path
DSD SOAK     2 h Native DSD if supported
DOP SOAK     2 h DoP if supported
TRANSITION   >=100 repeated transitions for selected critical boundary
```

Budgets may be increased, not silently reduced.

## 232.2 NOT_RUN

Hardware unavailable remains `NOT_RUN`. Final Phase 2 can only claim support families represented by executed physical evidence according to product scope.


------------------------------------------------------------------------

# 233. PERFORMANCE V2 — MÉTODO DE MEDICIÓN Y BASELINE COMPARABLE

A number without methodology is not a gate.

Each benchmark records:

```text
warmup duration
measurement duration
sample count
CPU affinity policy if any
power governor
background-load policy
buffer/period configuration
input fixture hash
output device/path
mean/p50/p95/p99/max
raw artifact
```

## 233.1 Relative regression gates

In addition to absolute budgets, compare against frozen PCM baseline:

```text
startup latency regression
seek latency regression
idle RSS regression
PCM Direct CPU regression
XRUN regression
```

A new machine may establish its own baseline profile; cross-machine absolute comparisons are informational unless hardware is standardized.


------------------------------------------------------------------------

# 234. KILLCRITIC V3 — CHECKLIST SE CONVIERTE EN TEST MANIFEST EJECUTABLE

Checkboxes are insufficient for final seal. Create:

```text
docs/audio/phase2/KILLCRITIC_MANIFEST.json
```

Schema:

```json
{
  "schema": 1,
  "cases": [
    {
      "id": "DOP-03",
      "owner_phase": "AP2-F09",
      "severity": "P0",
      "kind": "AUTOMATED",
      "test": "tests/dop/test_dop_volume_guard.py::test_software_volume_cannot_mutate_carrier",
      "expected": "DOP_CARRIER_VOLUME_FORBIDDEN",
      "artifact": null,
      "status": "NOT_RUN"
    }
  ]
}
```

Verifier rules:

```text
all mandatory IDs present
no duplicate IDs
P0/P1 mandatory case cannot be SKIPPED without BLOCKED phase
AUTOMATED test must resolve to an actual collected pytest node
PHYSICAL case must reference SHA-bound artifact
MANUAL case must explain why automation is impossible
status belongs to exact HEAD/spec SHA
```


------------------------------------------------------------------------

# 235. ERROR TAXONOMY V2 — CÓDIGOS NUEVOS OBLIGATORIOS DEL SELLO CORRECTIVO

New stable codes:

```text
DSD_RATE_UNIT_MISMATCH
DSD_GST_RATE_INVALID
DSD_ALSA_GROUPING_RATE_MISMATCH
DSD_SOURCE_ELEMENTARY_STREAM_NOT_PROVEN
DSD_REVERSED_BYTES_NOT_NORMALIZED
NATIVE_DSD_PCM_CONVERSION_DETECTED
DOP_CARRIER_LAYOUT_UNKNOWN
DOP_CARRIER_LAYOUT_UNQUALIFIED
DOP_DEVICE_INTERPRETATION_UNKNOWN
DOP_DEVICE_INTERPRETATION_CONTRADICTED
DOP_PADDING_MUTATED
DOP_MARKER_OFFSET_MISMATCH
DOP_DISCONTINUITY_STATE_INVALID
DSP_PREPARE_CROSSED_DESTRUCTIVE_BOUNDARY
DSP_PREDECESSOR_RESTORE_FAILED
DSP_NODE_PARAMETER_MISMATCH
DSP_UNPLANNED_TRANSFORM_PRESENT
DSP_XRUN_NOT_OBSERVABLE
DSD_PCM_DECODER_UNAVAILABLE
DSD_PCM_QUALITY_PROFILE_UNQUALIFIED
SIGNAL_PATH_CYCLE
SIGNAL_PATH_DISCONNECTED_ACTIVE_NODE
SIGNAL_PATH_SIGNAL_CONTINUITY_MISMATCH
RT_POLICY_VIOLATION
PHYSICAL_ARTIFACT_SCHEMA_INVALID
KILLCRITIC_CASE_MISSING
KILLCRITIC_ARTIFACT_STALE
```

Every code maps to:

```text
owner phase
user-facing title
user-facing explanation
recoverability
whether retry is safe
whether capability evidence changes
whether diagnostics should include raw detail
```


------------------------------------------------------------------------

# 236. FINAL COMPLETENESS GATE V2 — NO TODO, NO PLACEHOLDER, NO “INVESTIGAR DURANTE CODING”

Before AP2-F15 can close, an automated scanner checks the Phase 2 production surface and canonical spec for unresolved implementation markers.

Forbidden in productive code unless allowlisted with issue/phase:

```text
TODO
FIXME
pass  # placeholder
NotImplementedError
raise AssertionError("TODO")
mock-only branch in production
hard-coded evidence success
xruns=0 without observer
activity=ACTIVE without inspection
```

The spec may retain historical research notes, but every open decision must have one of:

```text
RESOLVED by ADR
OPTIONAL / NOT_ACTIVATED and excluded from core DoD
BLOCKED with explicit external requirement
POST-PHASE2 scope
```

No core path may remain “research gate” at final freeze.


------------------------------------------------------------------------

# 237. CONFORMANCE MATRIX EXHAUSTIVA — GENERACIÓN SISTEMÁTICA DE CASOS

Esta matriz amplía §170. Su propósito no es inflar líneas: cada ID se convierte en un test parametrizado o un run-sheet concreto. OpenCode puede dividirla por fase, pero no inventar casos ad hoc en lugar de estos mínimos.

## 237.1 DSP PCM matrix

| ID | Source rate | Precision | Layout | Processing | Expected |
|---|---:|---:|---|---|---|
| PCM2-0001 | 44100 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0002 | 44100 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0003 | 44100 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0004 | 44100 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0005 | 44100 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0006 | 44100 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0007 | 44100 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0008 | 44100 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0009 | 44100 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0010 | 44100 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0011 | 44100 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0012 | 44100 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0013 | 44100 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0014 | 44100 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0015 | 44100 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0016 | 44100 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0017 | 44100 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0018 | 44100 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0019 | 44100 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0020 | 44100 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0021 | 44100 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0022 | 44100 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0023 | 44100 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0024 | 44100 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0025 | 48000 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0026 | 48000 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0027 | 48000 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0028 | 48000 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0029 | 48000 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0030 | 48000 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0031 | 48000 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0032 | 48000 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0033 | 48000 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0034 | 48000 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0035 | 48000 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0036 | 48000 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0037 | 48000 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0038 | 48000 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0039 | 48000 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0040 | 48000 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0041 | 48000 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0042 | 48000 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0043 | 48000 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0044 | 48000 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0045 | 48000 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0046 | 48000 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0047 | 48000 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0048 | 48000 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0049 | 88200 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0050 | 88200 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0051 | 88200 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0052 | 88200 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0053 | 88200 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0054 | 88200 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0055 | 88200 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0056 | 88200 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0057 | 88200 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0058 | 88200 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0059 | 88200 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0060 | 88200 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0061 | 88200 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0062 | 88200 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0063 | 88200 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0064 | 88200 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0065 | 88200 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0066 | 88200 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0067 | 88200 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0068 | 88200 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0069 | 88200 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0070 | 88200 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0071 | 88200 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0072 | 88200 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0073 | 96000 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0074 | 96000 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0075 | 96000 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0076 | 96000 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0077 | 96000 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0078 | 96000 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0079 | 96000 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0080 | 96000 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0081 | 96000 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0082 | 96000 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0083 | 96000 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0084 | 96000 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0085 | 96000 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0086 | 96000 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0087 | 96000 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0088 | 96000 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0089 | 96000 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0090 | 96000 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0091 | 96000 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0092 | 96000 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0093 | 96000 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0094 | 96000 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0095 | 96000 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0096 | 96000 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0097 | 176400 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0098 | 176400 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0099 | 176400 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0100 | 176400 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0101 | 176400 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0102 | 176400 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0103 | 176400 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0104 | 176400 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0105 | 176400 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0106 | 176400 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0107 | 176400 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0108 | 176400 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0109 | 176400 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0110 | 176400 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0111 | 176400 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0112 | 176400 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0113 | 176400 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0114 | 176400 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0115 | 176400 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0116 | 176400 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0117 | 176400 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0118 | 176400 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0119 | 176400 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0120 | 176400 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0121 | 192000 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0122 | 192000 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0123 | 192000 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0124 | 192000 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0125 | 192000 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0126 | 192000 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0127 | 192000 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0128 | 192000 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0129 | 192000 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0130 | 192000 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0131 | 192000 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0132 | 192000 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0133 | 192000 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0134 | 192000 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0135 | 192000 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0136 | 192000 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0137 | 192000 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0138 | 192000 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0139 | 192000 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0140 | 192000 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0141 | 192000 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0142 | 192000 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0143 | 192000 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0144 | 192000 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0145 | 352800 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0146 | 352800 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0147 | 352800 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0148 | 352800 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0149 | 352800 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0150 | 352800 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0151 | 352800 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0152 | 352800 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0153 | 352800 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0154 | 352800 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0155 | 352800 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0156 | 352800 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0157 | 352800 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0158 | 352800 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0159 | 352800 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0160 | 352800 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0161 | 352800 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0162 | 352800 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0163 | 352800 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0164 | 352800 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0165 | 352800 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0166 | 352800 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0167 | 352800 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0168 | 352800 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0169 | 384000 Hz | 16-bit | stereo | OFF | identity transport |
| PCM2-0170 | 384000 Hz | 16-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0171 | 384000 Hz | 16-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0172 | 384000 Hz | 16-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0173 | 384000 Hz | 16-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0174 | 384000 Hz | 16-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0175 | 384000 Hz | 16-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0176 | 384000 Hz | 16-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0177 | 384000 Hz | 16-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0178 | 384000 Hz | 16-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0179 | 384000 Hz | 16-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0180 | 384000 Hz | 16-bit | stereo | BALANCE | processed; source rate preserved |
| PCM2-0181 | 384000 Hz | 24-bit | stereo | OFF | identity transport |
| PCM2-0182 | 384000 Hz | 24-bit | stereo | PREAMP | processed; source rate preserved |
| PCM2-0183 | 384000 Hz | 24-bit | stereo | PEQ_10 | processed; source rate preserved |
| PCM2-0184 | 384000 Hz | 24-bit | stereo | PEQ_64 | processed; source rate preserved |
| PCM2-0185 | 384000 Hz | 24-bit | stereo | FIR_SHORT | processed; source rate preserved |
| PCM2-0186 | 384000 Hz | 24-bit | stereo | FIR_131K | processed; source rate preserved |
| PCM2-0187 | 384000 Hz | 24-bit | stereo | CONVOLUTION | processed; source rate preserved |
| PCM2-0188 | 384000 Hz | 24-bit | stereo | RESAMPLE_EXPLICIT | explicit target rate |
| PCM2-0189 | 384000 Hz | 24-bit | stereo | DITHER_REDUCTION | processed; source rate preserved |
| PCM2-0190 | 384000 Hz | 24-bit | stereo | CHANNEL_DELAY | processed; source rate preserved |
| PCM2-0191 | 384000 Hz | 24-bit | stereo | POLARITY | processed; source rate preserved |
| PCM2-0192 | 384000 Hz | 24-bit | stereo | BALANCE | processed; source rate preserved |

## 237.2 Native DSD matrix

| ID | Source | Grouping | Gst rate | ALSA rate | Gate |
|---|---|---|---:|---:|---|
| NDSD-001 | DSD64 | DSDU8 | Gst 352800 B/s/ch | ALSA 352800 Hz | exact qualification required |
| NDSD-002 | DSD64 | DSDU16LE | Gst 352800 B/s/ch | ALSA 176400 Hz | exact qualification required |
| NDSD-003 | DSD64 | DSDU32LE | Gst 352800 B/s/ch | ALSA 88200 Hz | exact qualification required |
| NDSD-004 | DSD128 | DSDU8 | Gst 705600 B/s/ch | ALSA 705600 Hz | exact qualification required |
| NDSD-005 | DSD128 | DSDU16LE | Gst 705600 B/s/ch | ALSA 352800 Hz | exact qualification required |
| NDSD-006 | DSD128 | DSDU32LE | Gst 705600 B/s/ch | ALSA 176400 Hz | exact qualification required |
| NDSD-007 | DSD256 | DSDU8 | Gst 1411200 B/s/ch | ALSA 1411200 Hz | exact qualification required |
| NDSD-008 | DSD256 | DSDU16LE | Gst 1411200 B/s/ch | ALSA 705600 Hz | exact qualification required |
| NDSD-009 | DSD256 | DSDU32LE | Gst 1411200 B/s/ch | ALSA 352800 Hz | exact qualification required |
| NDSD-010 | DSD512 | DSDU8 | Gst 2822400 B/s/ch | ALSA 2822400 Hz | exact qualification required |
| NDSD-011 | DSD512 | DSDU16LE | Gst 2822400 B/s/ch | ALSA 1411200 Hz | exact qualification required |
| NDSD-012 | DSD512 | DSDU32LE | Gst 2822400 B/s/ch | ALSA 705600 Hz | exact qualification required |

## 237.3 DoP carrier matrix

| ID | Source | Carrier rate | Layout | Gate |
|---|---|---:|---|---|
| DOP2-001 | DSD64 | 176400 Hz | PACKED_24_LE | exact qualification |
| DOP2-002 | DSD64 | 176400 Hz | S32_LE_LSB24 | exact qualification |
| DOP2-003 | DSD64 | 176400 Hz | S32_LE_MSB24 | disabled-until-qualified |
| DOP2-004 | DSD128 | 352800 Hz | PACKED_24_LE | exact qualification |
| DOP2-005 | DSD128 | 352800 Hz | S32_LE_LSB24 | exact qualification |
| DOP2-006 | DSD128 | 352800 Hz | S32_LE_MSB24 | disabled-until-qualified |
| DOP2-007 | DSD256 | 705600 Hz | PACKED_24_LE | exact qualification |
| DOP2-008 | DSD256 | 705600 Hz | S32_LE_LSB24 | exact qualification |
| DOP2-009 | DSD256 | 705600 Hz | S32_LE_MSB24 | disabled-until-qualified |

## 237.4 Transition matrix

| ID | From | To | Required action | Invariant |
|---|---|---|---|---|
| TR2-001 | PCM_DIRECT | PCM_DIRECT | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |
| TR2-002 | PCM_DIRECT | PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-003 | PCM_DIRECT | NATIVE_DSD | controlled output reopen | generation + request epoch must change/validate |
| TR2-004 | PCM_DIRECT | DOP | controlled output reopen | generation + request epoch must change/validate |
| TR2-005 | PCM_DIRECT | DSD_TO_PCM | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-006 | PCM_DIRECT | DSD_TO_PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-007 | PCM_DSP | PCM_DIRECT | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-008 | PCM_DSP | PCM_DSP | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |
| TR2-009 | PCM_DSP | NATIVE_DSD | controlled output reopen | generation + request epoch must change/validate |
| TR2-010 | PCM_DSP | DOP | controlled output reopen | generation + request epoch must change/validate |
| TR2-011 | PCM_DSP | DSD_TO_PCM | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-012 | PCM_DSP | DSD_TO_PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-013 | NATIVE_DSD | PCM_DIRECT | controlled output reopen | generation + request epoch must change/validate |
| TR2-014 | NATIVE_DSD | PCM_DSP | controlled output reopen | generation + request epoch must change/validate |
| TR2-015 | NATIVE_DSD | NATIVE_DSD | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |
| TR2-016 | NATIVE_DSD | DOP | controlled output reopen | generation + request epoch must change/validate |
| TR2-017 | NATIVE_DSD | DSD_TO_PCM | controlled output reopen | generation + request epoch must change/validate |
| TR2-018 | NATIVE_DSD | DSD_TO_PCM_DSP | controlled output reopen | generation + request epoch must change/validate |
| TR2-019 | DOP | PCM_DIRECT | controlled output reopen | generation + request epoch must change/validate |
| TR2-020 | DOP | PCM_DSP | controlled output reopen | generation + request epoch must change/validate |
| TR2-021 | DOP | NATIVE_DSD | controlled output reopen | generation + request epoch must change/validate |
| TR2-022 | DOP | DOP | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |
| TR2-023 | DOP | DSD_TO_PCM | controlled output reopen | generation + request epoch must change/validate |
| TR2-024 | DOP | DSD_TO_PCM_DSP | controlled output reopen | generation + request epoch must change/validate |
| TR2-025 | DSD_TO_PCM | PCM_DIRECT | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-026 | DSD_TO_PCM | PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-027 | DSD_TO_PCM | NATIVE_DSD | controlled output reopen | generation + request epoch must change/validate |
| TR2-028 | DSD_TO_PCM | DOP | controlled output reopen | generation + request epoch must change/validate |
| TR2-029 | DSD_TO_PCM | DSD_TO_PCM | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |
| TR2-030 | DSD_TO_PCM | DSD_TO_PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-031 | DSD_TO_PCM_DSP | PCM_DIRECT | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-032 | DSD_TO_PCM_DSP | PCM_DSP | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-033 | DSD_TO_PCM_DSP | NATIVE_DSD | controlled output reopen | generation + request epoch must change/validate |
| TR2-034 | DSD_TO_PCM_DSP | DOP | controlled output reopen | generation + request epoch must change/validate |
| TR2-035 | DSD_TO_PCM_DSP | DSD_TO_PCM | controlled graph/output transaction | generation + request epoch must change/validate |
| TR2-036 | DSD_TO_PCM_DSP | DSD_TO_PCM_DSP | preserve/reconfigure only if format/profile changed | generation + request epoch must change/validate |

## 237.5 Failure-injection matrix

| ID | Path | Injection | Scenario | Expected safety property |
|---|---|---|---|---|
| FI2-0001 | PCM_DIRECT | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0002 | PCM_DIRECT | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0003 | PCM_DIRECT | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0004 | PCM_DIRECT | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0005 | PCM_DIRECT | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0006 | PCM_DIRECT | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0007 | PCM_DIRECT | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0008 | PCM_DIRECT | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0009 | PCM_DIRECT | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0010 | PCM_DIRECT | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0011 | PCM_DIRECT | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0012 | PCM_DIRECT | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0013 | PCM_DIRECT | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0014 | PCM_DIRECT | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0015 | PCM_DIRECT | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0016 | PCM_DIRECT | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0017 | PCM_DIRECT | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0018 | PCM_DIRECT | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0019 | PCM_DIRECT | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0020 | PCM_DIRECT | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0021 | PCM_DSP | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0022 | PCM_DSP | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0023 | PCM_DSP | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0024 | PCM_DSP | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0025 | PCM_DSP | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0026 | PCM_DSP | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0027 | PCM_DSP | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0028 | PCM_DSP | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0029 | PCM_DSP | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0030 | PCM_DSP | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0031 | PCM_DSP | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0032 | PCM_DSP | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0033 | PCM_DSP | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0034 | PCM_DSP | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0035 | PCM_DSP | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0036 | PCM_DSP | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0037 | PCM_DSP | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0038 | PCM_DSP | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0039 | PCM_DSP | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0040 | PCM_DSP | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0041 | NATIVE_DSD | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0042 | NATIVE_DSD | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0043 | NATIVE_DSD | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0044 | NATIVE_DSD | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0045 | NATIVE_DSD | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0046 | NATIVE_DSD | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0047 | NATIVE_DSD | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0048 | NATIVE_DSD | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0049 | NATIVE_DSD | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0050 | NATIVE_DSD | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0051 | NATIVE_DSD | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0052 | NATIVE_DSD | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0053 | NATIVE_DSD | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0054 | NATIVE_DSD | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0055 | NATIVE_DSD | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0056 | NATIVE_DSD | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0057 | NATIVE_DSD | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0058 | NATIVE_DSD | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0059 | NATIVE_DSD | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0060 | NATIVE_DSD | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0061 | DOP | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0062 | DOP | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0063 | DOP | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0064 | DOP | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0065 | DOP | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0066 | DOP | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0067 | DOP | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0068 | DOP | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0069 | DOP | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0070 | DOP | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0071 | DOP | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0072 | DOP | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0073 | DOP | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0074 | DOP | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0075 | DOP | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0076 | DOP | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0077 | DOP | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0078 | DOP | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0079 | DOP | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0080 | DOP | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0081 | DSD_TO_PCM | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0082 | DSD_TO_PCM | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0083 | DSD_TO_PCM | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0084 | DSD_TO_PCM | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0085 | DSD_TO_PCM | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0086 | DSD_TO_PCM | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0087 | DSD_TO_PCM | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0088 | DSD_TO_PCM | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0089 | DSD_TO_PCM | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0090 | DSD_TO_PCM | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0091 | DSD_TO_PCM | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0092 | DSD_TO_PCM | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0093 | DSD_TO_PCM | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0094 | DSD_TO_PCM | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0095 | DSD_TO_PCM | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0096 | DSD_TO_PCM | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0097 | DSD_TO_PCM | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0098 | DSD_TO_PCM | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0099 | DSD_TO_PCM | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0100 | DSD_TO_PCM | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0101 | DSD_TO_PCM_DSP | DEVICE_REMOVED | device disappears during prepare | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0102 | DSD_TO_PCM_DSP | BINDING_GENERATION_CHANGE | binding changes before commit | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0103 | DSD_TO_PCM_DSP | GST_PREROLL_FAILURE | candidate never prerolls | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0104 | DSD_TO_PCM_DSP | GST_GRAPH_INSPECTION_FAILURE | selected branch cannot be fully traversed | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0105 | DSD_TO_PCM_DSP | ALSA_BUSY | exact open reports busy | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0106 | DSD_TO_PCM_DSP | ALSA_TIMEOUT | probe timeout | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0107 | DSD_TO_PCM_DSP | DSP_FACTORY_MISSING | planned filter factory absent | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0108 | DSD_TO_PCM_DSP | DSP_PARAMETER_MISMATCH | runtime property differs from compiled digest | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0109 | DSD_TO_PCM_DSP | IR_ASSET_REMOVED | asset missing after profile load | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0110 | DSD_TO_PCM_DSP | DOP_MARKER_CORRUPTION | native packer test hook corrupts marker | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0111 | DSD_TO_PCM_DSP | DOP_PADDING_CORRUPTION | carrier padding differs | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0112 | DSD_TO_PCM_DSP | DSD_DECODER_UNEXPECTED | Native branch contains PCM decoder | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0113 | DSD_TO_PCM_DSP | CONTEXT_PUMP_DIES | GLib owner pump terminates | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0114 | DSD_TO_PCM_DSP | ENGINE_SWITCH | engine switch during phase2 candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0115 | DSD_TO_PCM_DSP | STOP_DURING_PREPARE | stop request invalidates candidate | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0116 | DSD_TO_PCM_DSP | SEEK_DURING_DOP | seek while DoP streaming | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0117 | DSD_TO_PCM_DSP | PROFILE_DELETE_DURING_IMPORT | IR import completes after profile delete | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0118 | DSD_TO_PCM_DSP | DB_CORRUPT | Phase2 persistence unreadable | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0119 | DSD_TO_PCM_DSP | MAHKB_BAD_SIGNATURE | knowledge update signature invalid | fail closed / predecessor truth preserved or STOPPED safe |
| FI2-0120 | DSD_TO_PCM_DSP | NATIVE_PLUGIN_ABI_MISMATCH | michi-dop ABI incompatible | fail closed / predecessor truth preserved or STOPPED safe |


------------------------------------------------------------------------

# 238. TEST FILE MAP V2 — CADA CONTRATO TIENE UN HOGAR

```text
tests/audio_phase2/
  test_dsd_rate_units.py
  test_dsd_source_characterizer_contract.py
  test_alsa_dsd_tuple_mapping.py
  test_native_dsd_recipe_v2.py
  test_native_dsd_runtime_validation.py
  test_dop_evidence_split.py
  test_dop_carrier_layouts.py
  test_dop_streaming_chunks.py
  test_dop_seek_discont.py
  test_dop_planner_v2.py
  test_processing_transaction_quiescent.py
  test_processing_predecessor_restore.py
  test_processing_adapter_registry.py
  test_processing_runtime_introspection.py
  test_dsd_to_pcm_planner.py
  test_dsd_to_pcm_conformance.py
  test_stateful_audio_semantics.py
  test_signal_path_graph_invariants.py
  test_security_ir_import.py
  test_mahkb_update_integrity.py
  test_realtime_policy_static.py
  test_killcritic_manifest.py
```

No mega-test file con 4.000 líneas. Cada family conserva ownership y failure vocabulary claros.


------------------------------------------------------------------------

# 239. PHASE CARDS V2 — EXIT GATES ADICIONALES DEL SELLO CORRECTIVO

Además de los exit gates ya definidos:

```text
F03: SignalPath acyclic/continuity invariants pass.
F05: prepare cannot mutate live graph before destructive boundary is explicitly entered.
F06: every core DSP node has typed adapter + real inspection; no generic property injection.
F07: DSD source units + elementary-stream proof + ALSA grouping mapping pass.
F08: Native DSD selected branch proves no audio/x-raw and reversed-bytes normalized.
F09: carrier layout qualified + interpretation evidence separate + streaming chunk invariance.
F10: gst-libav DSD→PCM backend selected/validated or phase BLOCKED; no unresolved core research gate.
F12: recommendations cannot outrank runtime/physical contradiction.
F13: IR/MAHKB/native plugin supply-chain gates pass.
F14: declared soak durations completed for supported claims.
F15: KILLCRITIC_MANIFEST has no mandatory NOT_RUN/SKIP for claimed core capabilities.
```


------------------------------------------------------------------------

# 240. OPEN DECISION REGISTER — ÚNICO LUGAR DONDE PUEDE QUEDAR INCERTIDUMBRE

La Biblia puede contener incertidumbre sólo aquí y sólo si no bloquea una fase marcada READY/CLOSED.

Formato:

```text
ODR-ID
owner_phase
question
why_not_resolved_yet
required_evidence
blocking = yes/no
allowed_state
expiry_phase
```

Core decisions introduced by this corrective seal:

```text
ODR-DOP-NATIVE-001
owner_phase=AP2-F09
question=Rust plugin vs alternative native implementation
required_evidence=benchmark + packaging + ADR
blocking=yes before F09 ACTIVE productive runtime
allowed_state=RESEARCH while F09 LOCKED
expiry_phase=F09

ODR-DSD2PCM-001
owner_phase=AP2-F10
question=exact gst-libav decoder/factory availability on supported distro matrix
required_evidence=feature discovery artifact + conformance
blocking=yes before F10 close
expiry_phase=F10

ODR-LV2-001
owner_phase=AP2-F06
question=activate third-party LV2 host
blocking=no
allowed_state=NOT_ACTIVATED
expiry_phase=POST_CORE
```

No other “TODO research” is permitted outside this register after F00 activation.


------------------------------------------------------------------------

# 241. OPENCODE CONTEXT UPDATE — CORRECTIVE SEAL OBLIGATORIO

`scripts/phase2_context.py` debe incorporar `CORRECTIVE_SECTIONS` por fase además de `MUST_READ_SECTIONS`.

```python
CORRECTIVE_SECTIONS = {
    "AP2-F03": (228, 252),
    "AP2-F05": (218, 219, 220, 223, 224, 248, 249, 250),
    "AP2-F06": (218, 219, 220, 223, 224, 248, 249, 250, 262),
    "AP2-F07": (210, 211, 212, 213, 214, 245, 246, 262),
    "AP2-F08": (210, 211, 213, 214, 225, 246),
    "AP2-F09": (210, 215, 216, 217, 226, 247, 262),
    "AP2-F10": (210, 221, 222, 223, 224, 227, 251, 262),
    "AP2-F11": (254, 255, 270),
    "AP2-F12": (215, 221, 229, 270),
    "AP2-F13": (230, 231, 253, 256),
    "AP2-F14": (232, 233, 264, 267),
    "AP2-F15": (234, 235, 236, 257, 258, 259, 260, 261, 270),
}
```

`--mode minimum` incluye automáticamente estas secciones. Así un modelo con poco contexto no puede leer el snippet DSD antiguo sin recibir también su corrección normativa.


------------------------------------------------------------------------

# 242. DEFINITION OF DONE V3 — CRITERIOS QUE ELEVAN EL PLAN A IMPLEMENTACIÓN INTEGRAL

Además de §179, el producto no está al 100% hasta que:

```text
[ ] DSD rate unit types are used across domain/planner/runtime; no ambiguous new `rate_hz` field.
[ ] Source DSD elementary truth is proven independently of final decoder output.
[ ] Native DSD sink always normalizes to reversed-bytes=false before alsasink.
[ ] ALSA DSD exact tuples preserve source bit rate mathematically and by readback.
[ ] DoP carrier and DAC interpretation evidence are separate types and UI fields.
[ ] Every DoP carrier layout has byte vectors and exact endpoint qualification.
[ ] DoP streaming handles arbitrary chunk boundaries and seek discontinuities.
[ ] DSP core does not mutate live graph in prepare before declared destructive boundary.
[ ] Every DSP node has a typed adapter; unknown properties fail, never disappear.
[ ] Runtime DSP evidence comes from actual graph/element/property/caps inspection.
[ ] XRUN zero is never fabricated from absence of telemetry.
[ ] DSD→PCM has a selected productive backend, version discovery and numeric conformance artifacts.
[ ] DSD→PCM quality profiles have measured response/latency/CPU contracts.
[ ] Stateful seek/pause/EOS/gapless semantics are tested for all core paths.
[ ] Click/pop mutation classes are enforced.
[ ] SignalPathGraph validates DAG, reachability, continuity and generation coherence.
[ ] IR/MAHKB/native plugin security tests pass.
[ ] Physical run sheets meet minimum durations and bind artifacts to exact HEAD/spec.
[ ] KILLCRITIC manifest is machine-verifiable and all mandatory claimed cases PASS.
[ ] Open decision register contains no blocking core decision at F15.
[ ] No superseded section can be selected as phase authority by phase2_context.py.
```


------------------------------------------------------------------------

# 243. IMPLEMENTATION LEDGER V2 — FILE / OWNER / PHASE / CONTRACT / TEST

This ledger is intended to be converted to `docs/audio/phase2/IMPLEMENTATION_LEDGER.json` at F00. It prevents agents from creating duplicate modules.

| File | Owner | Phase | Contract | Primary tests |
|---|---|---|---|---|
| `src/michi/domain/audio_signal.py` | domain types | F01/F07/F09 | SignalFormat + DSD unit-safe types | `test_audio_signal.py;test_dsd_rate_units.py` |
| `src/michi/domain/dop.py` | domain framing | F09 | DoP state/vector/layout contracts | `test_dop_carrier_layouts.py;test_dop_streaming_chunks.py` |
| `src/michi/domain/signal_path.py` | domain graph | F03 | DAG + typed verdicts | `test_signal_path_graph_invariants.py` |
| `src/michi/application/audio_processing_service.py` | AudioProcessingService | F05/F06 | processing selection/runtime transaction | `test_processing_transaction_quiescent.py` |
| `src/michi/application/dsd_policy_service.py` | DsdPolicyService | F10 | DSD/DSP decision policy | `test_dsd_dsp_matrix.py` |
| `src/michi/application/dsd_output_planner.py` | planner component under output authority | F08 | Native DSD plan | `test_native_dsd_planner.py` |
| `src/michi/application/dop_planner.py` | planner component under output authority | F09 | DoP double-gate plan | `test_dop_planner_v2.py` |
| `src/michi/infrastructure/audio_output/strict_dsd_sink.py` | infrastructure | F08 | Gst DSD strict recipe | `test_native_dsd_recipe_v2.py` |
| `src/michi/infrastructure/audio_output/dop_runtime.py` | infrastructure | F09 | DoP streaming/native bridge | `test_dop_seek_discont.py` |
| `src/michi/infrastructure/audio_processing/gstreamer_processing.py` | infrastructure | F05/F06 | Gst processing transaction | `test_processing_runtime_introspection.py` |
| `src/michi/infrastructure/audio_processing/gstreamer_filter_factory.py` | infrastructure | F06 | typed node adapters | `test_processing_adapter_registry.py` |
| `src/michi/infrastructure/audio_processing/ir_store.py` | infrastructure | F06/F13 | immutable IR store | `test_security_ir_import.py` |
| `src/michi/application/signal_path_service.py` | SignalPathService | F03 | snapshot projection | `test_signal_path_graph.py` |
| `scripts/phase2_context.py` | agent tooling | F00 | literal context extraction | `test_phase2_context.py` |
| `scripts/verify_audio_phase2_repository_alignment.py` | agent gate | F00/F15 | spec/phase alignment | `test_phase2_alignment.py` |
| `scripts/verify_audio_phase2.py` | aggregate verifier | F14/F15 | full software/perf artifact | `test_verify_audio_phase2_contract.py` |


------------------------------------------------------------------------

# 244. FINAL ARCHITECTURAL MAP V3 — CÓMO QUEDA EL SISTEMA DESPUÉS DE TODAS LAS CORRECCIONES

```text
LIBRARY / FILE FACTS
        │
        ├──────────────► SOURCE QUALITY (presentation only)
        │
        ▼
ELEMENTARY STREAM CHARACTERIZATION
        │
        ├── PCM ─────────────────────────────────────┐
        │                                             │
        └── DSD                                      │
             │                                        │
             ├── Preserve Native ──► DSD normalization│
             │                      ► Strict DSD       │
             │                      ► ALSA DSD         │
             │                                        │
             ├── DoP ─► DoP packer/layout ─► carrier │
             │                               ─► ALSA   │
             │                                        │
             └── Explicit DSD→PCM ─► F32 PCM ─────────┤
                                                      ▼
                                           PROCESSING POLICY
                                                │
                              ┌─────────────────┴────────────────┐
                              │                                  │
                            BYPASS                              DSP
                              │                         typed ProcessingGraph
                              │                         typed node adapters
                              │                         runtime inspection
                              │                                  │
                              └─────────────────┬────────────────┘
                                                ▼
                                         OUTPUT PLANNING
                                                │
                                                ▼
                                      OUTPUT TRANSACTION OWNER
                                                │
                                      ┌─────────┴──────────┐
                                      ▼                    ▼
                                 PCM/processed         Native/DoP
                                      │                    │
                                      └─────────┬──────────┘
                                                ▼
                                        RUNTIME EVIDENCE
                                 ┌──────────────┼──────────────┐
                                 ▼              ▼              ▼
                            SignalTruth      M11.5 proof     DSP evidence
                                 └──────────────┼──────────────┘
                                                ▼
                                        SignalPathGraph DAG
                                                │
                         ┌──────────────────────┼───────────────────────┐
                         ▼                      ▼                       ▼
                    NowPlaying              Audio Lab              Device Setup
```

Final ownership sentence:

```text
No UI owns truth.
No knowledge base owns runtime.
No DSP backend owns playback.
No carrier capability proves DAC interpretation.
No native path is “bit-perfect” by name alone.
Every claim is typed, generation-scoped, evidence-backed and falsifiable.
```


<!-- MICHI_PHASE2:KILLCRITIC_CORRECTIVE_SEAL:END -->

------------------------------------------------------------------------

# 245. DSD SOURCE PROBE V3 — IMPLEMENTACIÓN DE INFRAESTRUCTURA SIN CONFUNDIR DEMUX Y DECODE

Esta sección baja §212 a una implementación suficientemente cerrada para que OpenCode no invente el mecanismo de observación.

## 245.1 Port framework-free

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

@runtime_checkable
class ElementaryAudioProbePort(Protocol):
    def probe(self, path: Path) -> "ElementaryAudioProbeResult": ...
    def cancel(self) -> None: ...

@dataclass(frozen=True, slots=True)
class ElementaryAudioProbeResult:
    container_media_type: str | None
    elementary_media_type: str | None
    elementary_fields: tuple[tuple[str, object], ...]
    selected_demuxer: str | None
    selected_decoder: str | None
    decoded_media_type: str | None
    decoded_fields: tuple[tuple[str, object], ...]
    dsd_before_decode_observed: bool
    probe_generation: int
    evidence_refs: tuple[str, ...]
```

## 245.2 Infrastructure facade

GI objects stay confined. Add to `GStreamerBindings` only methods that return normalized data:

```python
@dataclass(frozen=True, slots=True)
class GstCapsSnapshot:
    media_type: str
    fields: tuple[tuple[str, object], ...]

@dataclass(frozen=True, slots=True)
class GstBranchElementSnapshot:
    factory_name: str
    klass: str
    sink_caps: GstCapsSnapshot | None
    src_caps: GstCapsSnapshot | None

@dataclass(frozen=True, slots=True)
class GstElementaryProbeSnapshot:
    container_caps: GstCapsSnapshot | None
    demuxer_factory: str | None
    elementary_caps: GstCapsSnapshot | None
    decoder_factory: str | None
    decoded_caps: GstCapsSnapshot | None
    branch: tuple[GstBranchElementSnapshot, ...]
    complete: bool
```

## 245.3 Probe lifecycle

```text
CREATE isolated pipeline/context
  ↓
SET source URI
  ↓
observe typefind/container
  ↓
observe demuxer dynamic pad before decoder
  ↓
record elementary caps
  ↓
allow bounded preroll far enough to observe chosen decoder/output
  ↓
record decoded caps and branch factories
  ↓
NULL + detach source/watch
  ↓
return normalized immutable snapshot
```

## 245.4 Acceptance algorithm

```python
def normalize_probe(snapshot: GstElementaryProbeSnapshot) -> ElementaryAudioProbeResult:
    if not snapshot.complete:
        raise SourceCharacterizationError(
            "SOURCE_BRANCH_INSPECTION_INCOMPLETE", "GStreamer branch not fully observable"
        )
    elementary = snapshot.elementary_caps
    decoded = snapshot.decoded_caps
    dsd_before_decode = elementary is not None and elementary.media_type == "audio/x-dsd"
    return ElementaryAudioProbeResult(
        container_media_type=snapshot.container_caps.media_type if snapshot.container_caps else None,
        elementary_media_type=elementary.media_type if elementary else None,
        elementary_fields=elementary.fields if elementary else (),
        selected_demuxer=snapshot.demuxer_factory,
        selected_decoder=snapshot.decoder_factory,
        decoded_media_type=decoded.media_type if decoded else None,
        decoded_fields=decoded.fields if decoded else (),
        dsd_before_decode_observed=dsd_before_decode,
        probe_generation=0,  # assigned by owner
        evidence_refs=(),
    )
```

## 245.5 Native eligibility

```text
DSD file facts only                        insufficient
DSD elementary caps before decoder        required
Native sink support                       required
exact device qualification                required
selected runtime branch remains x-dsd     required at execution
```

This gives two firewalls: pre-planning source truth and post-preroll execution truth.


------------------------------------------------------------------------

# 246. NATIVE DSD PLANNER V3 — CÓDIGO COMPLETO CON UNIDADES CORRECTAS

```python
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True, slots=True)
class NativeDsdQualification:
    stable_device_id: str
    binding_generation: int
    requested: AlsaDsdTuple
    supported: bool | None
    evidence_ref: str

@dataclass(frozen=True, slots=True)
class NativeDsdOutputPlanV3:
    plan_id: str
    stable_device_id: str
    binding_locator: str
    binding_generation: int
    source: DsdSignalFormatV2
    alsa_tuple: AlsaDsdTuple
    gst_format: str
    gst_rate_bytes_per_second_per_channel: int
    normalize_reversed_bytes: bool
    sink_factory: str
    decision_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]

class NativeDsdPlannerRefusal(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail

class NativeDsdPlannerV3:
    def plan(
        self,
        *,
        stable_device_id: str,
        binding_locator: str,
        binding_generation: int,
        source: DsdSignalFormatV2,
        qualifications: tuple[NativeDsdQualification, ...],
        active_engine_id: str,
        processing_active: bool,
    ) -> NativeDsdOutputPlanV3:
        if active_engine_id != "gstreamer":
            raise NativeDsdPlannerRefusal(
                "DSD_ENGINE_UNSUPPORTED", "Native DSD core requires GStreamer"
            )
        if processing_active:
            raise NativeDsdPlannerRefusal(
                "DSD_PCM_PROCESSING_ACTIVE", "PCM DSP cannot be attached to Native DSD"
            )
        if binding_generation < 0:
            raise NativeDsdPlannerRefusal("DSD_BINDING_INVALID", "invalid binding generation")

        source_rate = source.source_rate
        candidates: list[tuple[NativeDsdQualification, AlsaDsdTuple]] = []
        for item in qualifications:
            if item.stable_device_id != stable_device_id:
                continue
            if item.binding_generation != binding_generation:
                continue
            req = item.requested
            if req.source_bits_per_second_per_channel != source_rate.bits_per_second_per_channel:
                continue
            if req.channels != source.channels:
                continue
            if item.supported is True:
                candidates.append((item, req))

        if not candidates:
            negatives = [q for q in qualifications if q.supported is False]
            if negatives:
                raise NativeDsdPlannerRefusal(
                    "DSD_EXACT_TUPLE_UNSUPPORTED", "no qualified Native DSD tuple"
                )
            raise NativeDsdPlannerRefusal(
                "DSD_EXACT_TUPLE_UNKNOWN", "Native DSD tuple has not been proven"
            )

        # Deterministic preference is policy, not a capability claim.
        preference = {32: 0, 16: 1, 8: 2}
        chosen_q, chosen = sorted(
            candidates,
            key=lambda pair: (
                preference.get(pair[1].sample_width_bits, 99),
                pair[1].format_name,
            ),
        )[0]

        gst_rate = source_rate.gst_byte_rate_per_channel
        payload = repr((
            stable_device_id,
            binding_locator,
            binding_generation,
            source,
            chosen,
            gst_rate,
            source.reversed_bytes,
        )).encode("utf-8")
        return NativeDsdOutputPlanV3(
            plan_id="native-dsd:" + hashlib.sha256(payload).hexdigest()[:24],
            stable_device_id=stable_device_id,
            binding_locator=binding_locator,
            binding_generation=binding_generation,
            source=source,
            alsa_tuple=chosen,
            gst_format=source.gst_grouping,
            gst_rate_bytes_per_second_per_channel=gst_rate,
            normalize_reversed_bytes=source.reversed_bytes,
            sink_factory="alsasink",
            decision_codes=(
                "DSD_SOURCE_FIRST_CLASS",
                "DSD_EXACT_ALSA_TUPLE_PROVEN",
                "DSD_GST_BYTE_RATE_DERIVED",
                "DSD_PCM_DSP_FORBIDDEN",
            ),
            evidence_refs=(chosen_q.evidence_ref,),
        )
```

## 246.1 Planner invariants

```text
plan id changes on binding generation
plan id changes on source bit order/grouping/rate
plan id changes on selected ALSA tuple
no fallback to PCM inside this planner
no fallback to DoP inside this planner
policy coordinator selects family before calling planner
```


------------------------------------------------------------------------

# 247. DOP PLANNER V3 — IMPLEMENTACIÓN COMPLETA DEL DOBLE GATE

```python
@dataclass(frozen=True, slots=True)
class DopPolicyDecision:
    explicit_requested: bool
    auto_allowed: bool
    minimum_interpretation_state: DopInterpretationState

class DopPlannerV3:
    def plan(
        self,
        *,
        stable_device_id: str,
        binding_generation: int,
        source: DsdSignalFormatV2,
        carrier_qualifications: tuple[DopCarrierQualification, ...],
        interpretation: tuple[DopDeviceInterpretationEvidence, ...],
        policy: DopPolicyDecision,
        layout_preference: tuple[DopCarrierLayout, ...],
    ) -> DopExecutionPlanV2:
        acceptable_interpretation = self._resolve_interpretation(
            stable_device_id, source, interpretation, policy
        )
        rate = source_to_dop_rate(source.source_rate)
        qualified = [
            q for q in carrier_qualifications
            if q.stable_device_id == stable_device_id
            and q.carrier_rate_hz == rate.frames_per_second
            and q.support is DopCarrierSupport.QUALIFIED
        ]
        if not qualified:
            raise DopPlannerRefusal(
                "DOP_CARRIER_LAYOUT_UNQUALIFIED",
                f"no exact carrier layout qualified at {rate.frames_per_second} Hz",
            )

        by_layout = {q.carrier_layout_id: q for q in qualified}
        selected_layout = None
        selected_q = None
        for layout in layout_preference:
            item = by_layout.get(layout.value)
            if item is not None:
                selected_layout = layout
                selected_q = item
                break
        if selected_layout is None or selected_q is None:
            raise DopPlannerRefusal("DOP_CARRIER_LAYOUT_UNKNOWN", "no preferred qualified layout")

        memory = memory_contract_for(selected_layout)
        plan_id = stable_plan_hash(
            stable_device_id,
            binding_generation,
            source,
            rate,
            memory,
            selected_q.evidence_refs,
            acceptable_interpretation.evidence_refs,
        )
        return DopExecutionPlanV2(
            plan_id=plan_id,
            source=source,
            carrier_rate=rate,
            memory_contract=memory,
            binding_generation=binding_generation,
            stable_device_id=stable_device_id,
            carrier_evidence_refs=selected_q.evidence_refs,
            interpretation_evidence_refs=acceptable_interpretation.evidence_refs,
            interpretation_state=acceptable_interpretation.state,
            packer_revision="dop-v1-layout-v2",
        )

    def _resolve_interpretation(self, stable_device_id, source, evidence, policy):
        matches = [e for e in evidence if e.stable_device_id == stable_device_id]
        if any(e.state is DopInterpretationState.CONTRADICTED for e in matches):
            raise DopPlannerRefusal(
                "DOP_DEVICE_INTERPRETATION_CONTRADICTED", "DoP interpretation contradicted"
            )
        order = {
            DopInterpretationState.UNKNOWN: 0,
            DopInterpretationState.DECLARED: 1,
            DopInterpretationState.USER_CONFIRMED: 2,
            DopInterpretationState.DEVICE_OBSERVED: 3,
            DopInterpretationState.PHYSICALLY_QUALIFIED: 4,
        }
        required = order[policy.minimum_interpretation_state]
        accepted = [e for e in matches if order.get(e.state, -1) >= required]
        if not accepted:
            raise DopPlannerRefusal(
                "DOP_DEVICE_INTERPRETATION_UNKNOWN", "insufficient device interpretation evidence"
            )
        return sorted(accepted, key=lambda e: order[e.state], reverse=True)[0]
```

`memory_contract_for()` is a closed map; no user-provided arbitrary offsets are allowed.


------------------------------------------------------------------------

# 248. DSP RUNTIME V3 — IMPLEMENTACIÓN CORE QUIESCENT TRANSACTION

The first productive DSP runtime deliberately chooses correctness over seamless live mutation.

```python
@dataclass(frozen=True, slots=True)
class QuiescentPlaybackLease:
    request_epoch: int
    media_id: str | None
    position_ms: int
    status_before: str
    output_generation: int

class ProcessingTransitionCoordinator:
    def __init__(self, playback, processing, transport, output_session):
        self._playback = playback
        self._processing = processing
        self._transport = transport
        self._output = output_session

    def apply_graph(self, profile, signal):
        lease = self._playback.acquire_processing_transition_lease()
        candidate = self._processing.compile_candidate(profile, signal, lease)

        # Candidate is only Python/domain state and assets so far.
        self._processing.validate_candidate_offline(candidate)

        quiesced = False
        try:
            self._playback.quiesce_for_processing_transition(lease)
            quiesced = True
            runtime_receipt = self._processing.install_candidate_quiescent(candidate, lease)
            evidence = self._processing.preroll_and_inspect(runtime_receipt, lease)
            self._processing.verify_candidate(candidate, evidence, lease)
            self._processing.commit_candidate(runtime_receipt, evidence, lease)
            self._playback.restore_after_processing_transition(lease)
        except Exception:
            if quiesced:
                restoration = self._processing.restore_predecessor_or_fail_safe(lease)
                if restoration.predecessor_restored:
                    self._playback.restore_after_processing_transition(lease)
                else:
                    self._playback.converge_stopped_after_processing_failure(lease)
            raise
        finally:
            self._playback.release_processing_transition_lease(lease)
```

## 248.1 Lease invariants

```text
request epoch unchanged between acquire and commit
output generation unchanged unless transition explicitly owns output reopen
engine active identity unchanged for PCM DSP-only reconfiguration
Stop from user invalidates lease
new Play invalidates lease
engine switch invalidates lease
DAC removal invalidates lease
```

## 248.2 No autoplay surprise

If the original playback was STOPPED, transition ends STOPPED. If PAUSED, it ends PAUSED. For PLAYING, whether playback resumes automatically is a frozen product policy and must match existing transition semantics; the coordinator must not invent new autoplay behavior.


------------------------------------------------------------------------

# 249. GSTREAMER DSP FACTORY V3 — CÓDIGO DE ADAPTERS TIPADOS

```python
class GStreamerFilterFactory:
    def __init__(self, bindings):
        self._gst = bindings
        self._adapters = {
            ProcessingNodeKind.PREAMP: PreampGstAdapter(),
            ProcessingNodeKind.PEQ: ParametricEqGstAdapter(),
            ProcessingNodeKind.FIR: FirGstAdapter(),
            ProcessingNodeKind.CONVOLUTION: ConvolutionGstAdapter(),
            ProcessingNodeKind.RESAMPLE: ResampleGstAdapter(),
            ProcessingNodeKind.POLARITY: PolarityGstAdapter(),
            ProcessingNodeKind.BALANCE: BalanceGstAdapter(),
            ProcessingNodeKind.DELAY: DelayGstAdapter(),
            ProcessingNodeKind.CHANNEL_MAP: ChannelMapGstAdapter(),
        }

    def build(self, compiled_node):
        adapter = self._adapters.get(compiled_node.kind)
        if adapter is None:
            raise ProcessingRuntimeError(
                "DSP_NODE_ADAPTER_UNAVAILABLE", compiled_node.kind.value
            )
        return adapter.build(self._gst, compiled_node)

class PreampGstAdapter:
    adapter_id = "gst-preamp-v1"

    def build(self, gst, node):
        element = gst.make_element("volume", node.backend_name)
        props = dict(node.properties)
        gain_linear = float(props["gain_linear"])
        if not 0.0 <= gain_linear <= 16.0:
            raise ProcessingRuntimeError("DSP_PREAMP_RANGE_INVALID", str(gain_linear))
        gst.set_property_checked(element, "volume", gain_linear)
        return element

class ResampleGstAdapter:
    adapter_id = "gst-audioresample-v1"

    def build(self, gst, node):
        resample = gst.make_element("audioresample", node.backend_name)
        capsfilter = gst.make_element("capsfilter", node.backend_name + "_caps")
        props = dict(node.properties)
        target = int(props["target_rate_hz"])
        gst.set_caps_checked(capsfilter, f"audio/x-raw,rate={target}")
        return gst.make_linked_bin(node.backend_name + "_bin", (resample, capsfilter))
```

PEQ, FIR and convolution adapters follow the same rule: domain semantic parameters are transformed by the adapter; no raw QML/JSON property reaches GStreamer.

## 249.1 Adapter conformance

Each adapter declares:

```text
adapter_id
supported node schema versions
required factories
parameter ranges
expected caps behavior
expected latency behavior
inspection strategy
```


------------------------------------------------------------------------

# 250. DSP PARAMETER DIGEST / PROVENANCE — DETECTAR QUE EL RUNTIME ES EL PLAN COMPILADO

```python
import hashlib, json

def canonical_parameter_digest(adapter_id: str, properties: tuple[tuple[str, object], ...]) -> str:
    payload = {
        "adapter": adapter_id,
        "properties": [[k, v] for k, v in sorted(properties)],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()
```

At runtime adapter inspection reconstructs the semantic property snapshot and computes the same digest. If backend normalization means values change representation, the adapter canonicalizes both planned and observed values before hashing.

Never hash opaque object reprs containing memory addresses.

## 250.1 Evidence chain

```text
profile revision
  ↓
compiled node semantic parameters
  ↓ digest A
backend element actual properties
  ↓ normalize
  ↓ digest B
A == B -> parameter match evidence
A != B -> DSP_NODE_PARAMETER_MISMATCH
```


------------------------------------------------------------------------

# 251. DSD→PCM GSTREAMER RUNTIME V3 — EXPLICIT `avdec_dsd_*` NODE

A productive conversion branch must name the decoder, not let decodebin hide it.

```python
DSD_DECODER_FACTORY = {
    ("DSDU8", False, "interleaved"): "avdec_dsd_msbf",
    ("DSDU8", True,  "interleaved"): "avdec_dsd_lsbf",
    ("DSDU8", False, "non-interleaved"): "avdec_dsd_msbf_planar",
    ("DSDU8", True,  "non-interleaved"): "avdec_dsd_lsbf_planar",
}
```

The actual supported sink caps for each factory are feature-discovered at F10; this mapping is validated, not assumed.

```python
class GStreamerDsdToPcmRuntime:
    backend_id = "gstreamer-gst-libav-dsd2pcm-v1"

    def build_bin(self, plan: DsdToPcmPlan):
        decoder = self._gst.make_element(plan.decoder_factory, "michi_dsd2pcm_decoder")
        out_caps = self._gst.make_element("capsfilter", "michi_dsd2pcm_caps")
        self._gst.set_caps_checked(
            out_caps,
            f"audio/x-raw,format={plan.target_format},rate={plan.target_rate_hz},channels={plan.channels}",
        )
        return self._gst.make_linked_bin("michi_dsd2pcm", (decoder, out_caps))
```

If decoder native output rate differs from requested target, an explicit resampler node is inserted **after** DSD_TO_PCM and visible in Signal Path. The decoder node and resampler node never collapse into one presentation stage.


------------------------------------------------------------------------

# 252. SIGNAL PATH BUILDER V3 — CONTINUIDAD DE FORMATOS Y ORDEN DETERMINISTA

```python
ALLOWED_STAGE_EDGES = {
    SignalStage.SOURCE_CONTAINER: {SignalStage.DECODED_SOURCE},
    SignalStage.DECODED_SOURCE: {
        SignalStage.ENGINE,
        SignalStage.DSD_TO_PCM,
        SignalStage.DOP_PACKER,
        SignalStage.TRANSPORT,
    },
    SignalStage.DSD_TO_PCM: {SignalStage.PROCESSING, SignalStage.ENGINE, SignalStage.TRANSPORT},
    SignalStage.DOP_PACKER: {SignalStage.TRANSPORT},
    SignalStage.ENGINE: {SignalStage.PROCESSING, SignalStage.VOLUME, SignalStage.TRANSPORT},
    SignalStage.PROCESSING: {SignalStage.PROCESSING, SignalStage.VOLUME, SignalStage.TRANSPORT},
    SignalStage.VOLUME: {SignalStage.TRANSPORT},
    SignalStage.TRANSPORT: {SignalStage.DEVICE_NEGOTIATION, SignalStage.NETWORK_TRANSPORT},
    SignalStage.DEVICE_NEGOTIATION: {SignalStage.PHYSICAL_LINK, SignalStage.DEVICE},
    SignalStage.PHYSICAL_LINK: {SignalStage.DEVICE},
    SignalStage.NETWORK_TRANSPORT: {SignalStage.NETWORK_ENDPOINT},
    SignalStage.NETWORK_ENDPOINT: {SignalStage.DEVICE},
}

def assert_stage_edges(snapshot):
    node_by_id = {n.node_id: n for n in snapshot.nodes}
    for edge in snapshot.edges:
        left = node_by_id[edge.source_node_id]
        right = node_by_id[edge.target_node_id]
        allowed = ALLOWED_STAGE_EDGES.get(left.stage, set())
        if right.stage not in allowed:
            raise ValueError(f"illegal SignalPath edge {left.stage}->{right.stage}")

def assert_signal_continuity(snapshot):
    node_by_id = {n.node_id: n for n in snapshot.nodes}
    for edge in snapshot.edges:
        left = node_by_id[edge.source_node_id]
        right = node_by_id[edge.target_node_id]
        if left.output_signal is None or right.input_signal is None:
            continue
        if not signal_contract_compatible(left.output_signal, right.input_signal):
            raise ValueError(
                f"signal discontinuity {left.node_id}->{right.node_id}: "
                f"{left.output_signal!r} != {right.input_signal!r}"
            )
```

Deterministic node order is topological order with stable tie-break by stage rank then node_id. QML receives this ordered projection; it does not traverse arbitrary graph structure itself.


------------------------------------------------------------------------

# 253. PERSISTENCE V3 — SCHEMA CORRECTIVO, REVISIONES Y ASSETS

The storage contract must distinguish durable user intent from rebuildable evidence.

```sql
CREATE TABLE IF NOT EXISTS audio_processing_profiles_v1 (
    profile_id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    display_name TEXT NOT NULL,
    document_json TEXT NOT NULL,
    document_sha256 TEXT NOT NULL,
    revision INTEGER NOT NULL,
    created_at_ns INTEGER NOT NULL,
    updated_at_ns INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_processing_selection_v1 (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    selected_profile_id TEXT NULL,
    revision INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio_ir_assets_v1 (
    ir_id TEXT PRIMARY KEY,
    content_sha256 TEXT NOT NULL UNIQUE,
    sample_rate_hz INTEGER NOT NULL,
    channels INTEGER NOT NULL,
    frames INTEGER NOT NULL,
    storage_relpath TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    imported_at_ns INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dsd_user_policy_v1 (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    document_json TEXT NOT NULL,
    revision INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dop_user_confirmations_v1 (
    stable_device_id TEXT NOT NULL,
    source_multiplier INTEGER NULL,
    device_revision TEXT NULL,
    confirmed_at_ns INTEGER NOT NULL,
    confirmation_schema INTEGER NOT NULL,
    PRIMARY KEY(stable_device_id, source_multiplier, device_revision)
);
```

Do NOT persist active SignalPath, current runtime caps, selected ALSA `hw:N`, active graph handles or current GStreamer element identities.

## 253.1 Evidence cache

Physical/qualification evidence may be cached only with:

```text
algorithm_version
environment_fingerprint
stable_device_id
binding signature when relevant
timestamp
raw artifact ref
```

Cache load never turns evidence from an incompatible environment into current proof.


------------------------------------------------------------------------

# 254. UI/UX V3 — ESTADOS DE ERROR Y CONSECUENCIAS EXPLÍCITAS, NO SÓLO HAPPY PATH


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

## 254.1 Signal Path quick surface

States:

```text
DIRECT · VERIFIED
PROCESSED · NOT APPLICABLE
NATIVE DSD · VERIFIED/UNVERIFIED according to M11.5 contract
DOP · carrier verified / DAC interpretation user-confirmed|physical|unknown
DSD→PCM · converted
UNKNOWN · evidence incomplete
CONTRADICTED · output mismatch
```

## 254.2 DSD + DSP confirmation

When user enables DSP while DSD is playing and policy would require conversion:

```text
Title: Process DSD as PCM?
Body: This profile requires PCM processing. Michi will convert DSD to PCM before PEQ/FIR processing. The Signal Path will show the conversion and bit-perfect DSD preservation will no longer apply.
Actions:
  Convert and enable processing
  Keep DSD unchanged
  Open DSD settings
```

No modal is shown repeatedly after a saved explicit policy exists; policy revision remains user-owned.

## 254.3 DoP states

```text
DoP unavailable
  reason: carrier not qualified

DoP available — device not verified
  carrier exact
  interpretation user-confirmed/declared

DoP physically qualified
  exact hardware artifact available in diagnostics

DoP contradicted
  disabled regardless of recommendation
```

## 254.4 DAC quick popup

Never shows “DSD512” simply from marketing metadata. Capability rows include provenance badges only in Advanced/Expert disclosure.


------------------------------------------------------------------------

# 255. RESPONSIVE / ACCESSIBILITY V3 — FULL, COMPACT, NARROW Y KEYBOARD MAP


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Canonical NowPlaying hierarchy:

| Control | FULL | COMPACT | NARROW |
|---|---|---|---|
| Volume | slider + authority | short slider | icon/popup |
| DSP | icon + active dot | icon | icon |
| Stream endpoint | icon/name if implemented | icon | overflow if necessary |
| Signal Path | compact verdict | icon+tooltip | icon |
| Quality | technical label + HD/DSD | abbreviated | badge |
| DAC | device icon/name | icon | icon |
| Queue | icon | icon | icon |

Keyboard:

```text
Tab/Shift+Tab  deterministic focus order
Enter/Space    activate focused button
Escape         close popup and restore focus to opener
Up/Down        move among menu/list rows
Left/Right     PEQ numeric step only when field/editor owns focus
Home/End       optional first/last list item
Ctrl+Z         draft editor undo only if implemented locally; never global playback action
```

Screen-reader labels include units in words, not abbreviations only.


------------------------------------------------------------------------

# 256. PACKAGING V3 — LINUX RUNTIME FEATURE MANIFEST

At startup create an immutable capability manifest, not repeated probes during playback:

```json
{
  "gstreamer": {
    "version": "...",
    "playbin3": true,
    "audio_x_dsd": true,
    "dsdconvert": true,
    "avdec_dsd_msbf": true,
    "avdec_dsd_lsbf": true,
    "equalizer_nbands": true,
    "audiofirfilter": true,
    "audioresample": true
  },
  "native_dop": {
    "backend": "rust-plugin|none",
    "abi": "...",
    "hash": "..."
  },
  "camilladsp": {
    "available": false,
    "version": null
  }
}
```

Packaging gates for each deliverable:

```text
AppImage  plugin discovery path tested
Flatpak   GI/GStreamer plugins and permissions tested
.deb      dependencies/recommends split tested
source    optional native build documented
```

Base player remains functional when all Phase2 optional components are absent; feature discovery explains unavailability without import-time crash.


------------------------------------------------------------------------

# 257. CI V3 — JOB GRAPH Y ARTIFACTS

Recommended jobs:

```text
phase2-domain
phase2-dsp-fake
phase2-gstreamer-real
phase2-dsd-feature-discovery
phase2-dop-reference
phase2-dop-native-if-built
phase2-qml
phase2-persistence-migrations
phase2-security-static
phase2-packaging-smoke
v35-regression
full-suite
```

Real GStreamer job must use the same supported minimum runtime family policy as packaging. It does not pretend to replace physical DAC qualification.

Artifacts:

```text
phase2-software-verdict.json
gstreamer-feature-manifest.json
dop-vector-digest.json
migration-report.json
qml-golden-diffs/
benchmark-smoke.json
```


------------------------------------------------------------------------

# 258. PHASE2_STATE V2 — STATE MACHINE VALIDATED, NO EDICIÓN ARBITRARIA

```json
{
  "schema": 2,
  "spec_path": "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md",
  "baseline_sha": "<frozen>",
  "phases": {
    "AP2-F00": {"state": "LOCKED", "closed_sha": null, "evidence": []}
  }
}
```

Allowed transitions:

```text
LOCKED -> READY
READY -> ACTIVE
ACTIVE -> VERIFYING
VERIFYING -> CLOSED
ACTIVE|VERIFYING -> BLOCKED
BLOCKED -> READY only after blocker resolution artifact
CLOSED -> no mutation; reopening requires explicit amendment record
```

A JSON edit cannot close a phase by itself. `closed_sha` is written only by a closing command after gates pass.


------------------------------------------------------------------------

# 259. IMPLEMENTATION SLICE TEMPLATE V3 — LO QUE OPENCODE DEBE HACER EN CADA PR

```text
SLICE_ID=
PRIMARY_PHASE=
SPEC_SHA=
BASELINE_SHA=

INTENT
  one sentence

AUTHORITIES TOUCHED
  exact services/types

FILES
  allowed list

PRECONDITIONS
  executable gates

RED TESTS
  exact pytest nodes

IMPLEMENTATION
  bounded change

FAILURE SEMANTICS
  codes + rollback

EVIDENCE
  what runtime can actually observe

REGRESSION FIREWALL
  exact commands

PHYSICAL IMPACT
  none | run sheet IDs required

DOC UPDATE
  section/ADR/status changes

EXIT
  all green + spec reread
```

A PR that cannot fit this template is too broad and must be split.


------------------------------------------------------------------------

# 260. TRACEABILITY MATRIX V3 — REQUIREMENT → PHASE → FILE → TEST → EVIDENCE

The following matrix is generated from the normative requirement families and is intended to become machine-readable at F00.

| ID | Requirement | Owner phase | Primary surface | Primary test/artifact | Evidence class |
|---|---|---|---|---|---|
| REQ3-0001 | DSD_UNIT.source_bitrate | AP2-F07 | `audio_signal.py` | `test_dsd_unit_source_bitrate.py` | automated |
| REQ3-0002 | DSD_UNIT.gst_byte_rate | AP2-F07 | `audio_signal.py` | `test_dsd_unit_gst_byte_rate.py` | automated |
| REQ3-0003 | DSD_UNIT.alsa_group_rate | AP2-F07 | `audio_signal.py` | `test_dsd_unit_alsa_group_rate.py` | automated |
| REQ3-0004 | DSD_UNIT.dop_carrier_rate | AP2-F07 | `audio_signal.py` | `test_dsd_unit_dop_carrier_rate.py` | automated |
| REQ3-0005 | DSD_SOURCE.container | AP2-F07 | `gstreamer.py` | `test_dsd_source_container.py` | automated |
| REQ3-0006 | DSD_SOURCE.elementary | AP2-F07 | `gstreamer.py` | `test_dsd_source_elementary.py` | automated |
| REQ3-0007 | DSD_SOURCE.decoded | AP2-F07 | `gstreamer.py` | `test_dsd_source_decoded.py` | automated |
| REQ3-0008 | DSD_SOURCE.branch_complete | AP2-F07 | `gstreamer.py` | `test_dsd_source_branch_complete.py` | automated |
| REQ3-0009 | DSD_SOURCE.cleanup | AP2-F07 | `gstreamer.py` | `test_dsd_source_cleanup.py` | automated |
| REQ3-0010 | NATIVE_DSD.planner | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_planner.py` | automated |
| REQ3-0011 | NATIVE_DSD.sink | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_sink.py` | automated |
| REQ3-0012 | NATIVE_DSD.normalize | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_normalize.py` | automated |
| REQ3-0013 | NATIVE_DSD.runtime_caps | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_runtime_caps.py` | automated |
| REQ3-0014 | NATIVE_DSD.no_pcm | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_no_pcm.py` | automated |
| REQ3-0015 | NATIVE_DSD.volume_guard | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_volume_guard.py` | automated |
| REQ3-0016 | NATIVE_DSD.generation | AP2-F08 | `strict_dsd_sink.py` | `test_native_dsd_generation.py` | automated |
| REQ3-0017 | DOP.carrier_qualification | AP2-F09 | `dop_runtime.py` | `test_dop_carrier_qualification.py` | automated |
| REQ3-0018 | DOP.interpretation | AP2-F09 | `dop_runtime.py` | `test_dop_interpretation.py` | automated |
| REQ3-0019 | DOP.layout | AP2-F09 | `dop_runtime.py` | `test_dop_layout.py` | automated |
| REQ3-0020 | DOP.packer | AP2-F09 | `dop_runtime.py` | `test_dop_packer.py` | automated |
| REQ3-0021 | DOP.chunking | AP2-F09 | `dop_runtime.py` | `test_dop_chunking.py` | automated |
| REQ3-0022 | DOP.seek | AP2-F09 | `dop_runtime.py` | `test_dop_seek.py` | automated |
| REQ3-0023 | DOP.volume_guard | AP2-F09 | `dop_runtime.py` | `test_dop_volume_guard.py` | automated |
| REQ3-0024 | DOP.resample_guard | AP2-F09 | `dop_runtime.py` | `test_dop_resample_guard.py` | automated |
| REQ3-0025 | DOP.padding | AP2-F09 | `dop_runtime.py` | `test_dop_padding.py` | automated |
| REQ3-0026 | DOP.generation | AP2-F09 | `dop_runtime.py` | `test_dop_generation.py` | automated |
| REQ3-0027 | DSP.compiler | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_compiler.py` | automated |
| REQ3-0028 | DSP.adapter | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_adapter.py` | automated |
| REQ3-0029 | DSP.transaction | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_transaction.py` | automated |
| REQ3-0030 | DSP.rollback | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_rollback.py` | automated |
| REQ3-0031 | DSP.caps | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_caps.py` | automated |
| REQ3-0032 | DSP.parameters | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_parameters.py` | automated |
| REQ3-0033 | DSP.latency | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_latency.py` | automated |
| REQ3-0034 | DSP.xrun | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_xrun.py` | automated |
| REQ3-0035 | DSP.bypass | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_bypass.py` | automated |
| REQ3-0036 | DSP.asset | AP2-F05/F06 | `gstreamer_processing.py` | `test_dsp_asset.py` | automated |
| REQ3-0037 | DSD2PCM.decoder | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_decoder.py` | automated |
| REQ3-0038 | DSD2PCM.target_rate | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_target_rate.py` | automated |
| REQ3-0039 | DSD2PCM.quality | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_quality.py` | automated |
| REQ3-0040 | DSD2PCM.response | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_response.py` | automated |
| REQ3-0041 | DSD2PCM.latency | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_latency.py` | automated |
| REQ3-0042 | DSD2PCM.flush | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_flush.py` | automated |
| REQ3-0043 | DSD2PCM.eos | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_eos.py` | automated |
| REQ3-0044 | DSD2PCM.signalpath | AP2-F10 | `dsd_to_pcm_runtime.py` | `test_dsd2pcm_signalpath.py` | automated |
| REQ3-0045 | SIGNALPATH.dag | AP2-F03 | `signal_path.py` | `test_signalpath_dag.py` | automated |
| REQ3-0046 | SIGNALPATH.root | AP2-F03 | `signal_path.py` | `test_signalpath_root.py` | automated |
| REQ3-0047 | SIGNALPATH.terminal | AP2-F03 | `signal_path.py` | `test_signalpath_terminal.py` | automated |
| REQ3-0048 | SIGNALPATH.reachability | AP2-F03 | `signal_path.py` | `test_signalpath_reachability.py` | automated |
| REQ3-0049 | SIGNALPATH.continuity | AP2-F03 | `signal_path.py` | `test_signalpath_continuity.py` | automated |
| REQ3-0050 | SIGNALPATH.generation | AP2-F03 | `signal_path.py` | `test_signalpath_generation.py` | automated |
| REQ3-0051 | SIGNALPATH.proof_projection | AP2-F03 | `signal_path.py` | `test_signalpath_proof_projection.py` | automated |
| REQ3-0052 | SIGNALPATH.ordering | AP2-F03 | `signal_path.py` | `test_signalpath_ordering.py` | automated |
| REQ3-0053 | SECURITY.ir_bounds | AP2-F13 | `ir_store.py / updater` | `test_security_ir_bounds.py` | automated |
| REQ3-0054 | SECURITY.ir_symlink | AP2-F13 | `ir_store.py / updater` | `test_security_ir_symlink.py` | automated |
| REQ3-0055 | SECURITY.mahkb_signature | AP2-F13 | `ir_store.py / updater` | `test_security_mahkb_signature.py` | automated |
| REQ3-0056 | SECURITY.rollback | AP2-F13 | `ir_store.py / updater` | `test_security_rollback.py` | automated |
| REQ3-0057 | SECURITY.plugin_abi | AP2-F13 | `ir_store.py / updater` | `test_security_plugin_abi.py` | automated |
| REQ3-0058 | SECURITY.redaction | AP2-F13 | `ir_store.py / updater` | `test_security_redaction.py` | automated |
| REQ3-0059 | PHYSICAL.pcm | AP2-F14 | `tests/physical` | `test_physical_pcm.py` | physical artifact |
| REQ3-0060 | PHYSICAL.dsp | AP2-F14 | `tests/physical` | `test_physical_dsp.py` | physical artifact |
| REQ3-0061 | PHYSICAL.native_dsd | AP2-F14 | `tests/physical` | `test_physical_native_dsd.py` | physical artifact |
| REQ3-0062 | PHYSICAL.dop | AP2-F14 | `tests/physical` | `test_physical_dop.py` | physical artifact |
| REQ3-0063 | PHYSICAL.negative_dop | AP2-F14 | `tests/physical` | `test_physical_negative_dop.py` | physical artifact |
| REQ3-0064 | PHYSICAL.transition | AP2-F14 | `tests/physical` | `test_physical_transition.py` | physical artifact |
| REQ3-0065 | PHYSICAL.soak | AP2-F14 | `tests/physical` | `test_physical_soak.py` | physical artifact |


------------------------------------------------------------------------

# 261. FINAL ZERO-AMBIGUITY CHECKLIST — PREGUNTAS QUE DEBEN TENER RESPUESTA ANTES DE CODIFICAR

For any concrete change, OpenCode must be able to answer:

```text
What exact signal family enters this component?
What are the units of every rate field?
What owner can mutate this state?
What generation/revision invalidates it?
What evidence can the runtime actually observe?
What cannot be observed and must remain UNKNOWN?
Does this transformation change samples, representation, transport, or only presentation?
What happens on Stop, Seek, Pause, EOS and device removal?
What happens if prepare succeeds but commit fails?
What happens if rollback also fails?
Can this run on the audio streaming thread?
Which operation is allowed to block?
Which durable data survives restart?
Which data is rebuildable cache?
Which UI action can trigger it?
Which UI labels are forbidden without evidence?
What exact test falsifies the happy path?
What exact test falsifies stale-event handling?
Does the feature require physical evidence before being advertised?
What package/runtime feature makes it unavailable?
```

Any unanswered item relevant to the change means `NO CONTEXT → NO CODE`.

------------------------------------------------------------------------

# 262. SCOPE CLOSURE V4 — ESTÉREO CORE, MULTICANAL EXPLÍCITAMENTE POST-CORE HASTA NUEVO GATE

Para eliminar la ambigüedad detectada por KILLCRITIC, el alcance CORE de Audio Phase 2 se congela así:

```text
PCM playback core           1–2 channels
PCM DSP core                stereo
Native DSD core             stereo
DoP core                    stereo
DSD→PCM core                stereo
Signal Path domain          channel-count generic
MAHKB/device identity       channel-count generic
multichannel execution      POST-CORE / NOT_ACTIVATED
```

Esto no prohíbe multicanal; impide que un tipo `CUSTOM` haga creer a OpenCode que debe improvisar DSD/DoP multicanal durante F07–F10.

## 262.1 Multichannel activation gate futuro

Antes de activar >2 canales se requiere un ADR con:

```text
channel position canonical vocabulary
ALSA channel-map readback
GStreamer channel-mask semantics
PCM remix policy
multichannel PEQ/FIR/IR routing
DoP channel interleave specification
DSD multichannel physical hardware
HDMI vs USB DAC classification
per-channel latency
UI routing matrix
physical matrix
```

Hasta entonces cualquier source >2 channels returns a typed unsupported/needs-shared-path decision according to product policy; no silent downmix in Direct.


------------------------------------------------------------------------

# 263. SOURCE LEDGER V4 — DOCUMENTACIÓN OFICIAL QUE FUNDAMENTA LOS CORRECTIVOS

Revalidar al activar F00. Estas URLs son evidence de diseño, no runtime truth:

```text
GStreamer DSD types / rate semantics
https://gstreamer.freedesktop.org/documentation/audio/gstdsd.html

GStreamer ALSA sink DSD caps
https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html

GStreamer playbin3 audio-filter/audio-sink
https://gstreamer.freedesktop.org/documentation/playback/playbin3.html

GStreamer plugin registry / avdec_dsd_*
https://gstreamer.freedesktop.org/documentation/plugins_doc.html

GStreamer DSF demuxer
https://gstreamer.freedesktop.org/documentation/libav/avdemux_dsf.html

Linux ALSA UAPI DSD formats
https://github.com/torvalds/linux/blob/master/include/uapi/sound/asound.h

FFmpeg DSD decoder
https://ffmpeg.org/doxygen/trunk/dsddec_8c_source.html

CamillaDSP
https://github.com/HEnquist/camilladsp

MPD DSD/DoP user documentation
https://mpd.readthedocs.io/en/stable/user.html
```

Each external fact used by code must be copied into a testable local contract; code must not query documentation websites at runtime.


------------------------------------------------------------------------

# 264. EVENT MATRIX V4 — STOP / SEEK / PAUSE / EOS / HOTPLUG / ENGINE SWITCH POR PATH

Cada fila es un integration test family. “safe” means no stale state or unowned runtime survives.

| ID | Path | Event | Expected invariant |
|---|---|---|---|
| EVT4-0001 | PCM_DIRECT | PLAY | canonical playback semantics preserved |
| EVT4-0002 | PCM_DIRECT | PAUSE | canonical playback semantics preserved |
| EVT4-0003 | PCM_DIRECT | RESUME | canonical playback semantics preserved |
| EVT4-0004 | PCM_DIRECT | STOP | canonical playback semantics preserved |
| EVT4-0005 | PCM_DIRECT | SEEK_FORWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0006 | PCM_DIRECT | SEEK_BACKWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0007 | PCM_DIRECT | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0008 | PCM_DIRECT | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0009 | PCM_DIRECT | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0010 | PCM_DIRECT | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0011 | PCM_DIRECT | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0012 | PCM_DIRECT | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0013 | PCM_DIRECT | PROFILE_CHANGE | policy intent recorded; no PCM DSP attached to Native/DoP |
| EVT4-0014 | PCM_DIRECT | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0015 | PCM_DSP | PLAY | canonical playback semantics preserved |
| EVT4-0016 | PCM_DSP | PAUSE | canonical playback semantics preserved |
| EVT4-0017 | PCM_DSP | RESUME | canonical playback semantics preserved |
| EVT4-0018 | PCM_DSP | STOP | canonical playback semantics preserved |
| EVT4-0019 | PCM_DSP | SEEK_FORWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0020 | PCM_DSP | SEEK_BACKWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0021 | PCM_DSP | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0022 | PCM_DSP | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0023 | PCM_DSP | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0024 | PCM_DSP | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0025 | PCM_DSP | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0026 | PCM_DSP | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0027 | PCM_DSP | PROFILE_CHANGE | quiescent candidate transaction; predecessor truth or fail-safe STOP |
| EVT4-0028 | PCM_DSP | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0029 | NATIVE_DSD | PLAY | canonical playback semantics preserved |
| EVT4-0030 | NATIVE_DSD | PAUSE | canonical playback semantics preserved |
| EVT4-0031 | NATIVE_DSD | RESUME | canonical playback semantics preserved |
| EVT4-0032 | NATIVE_DSD | STOP | canonical playback semantics preserved |
| EVT4-0033 | NATIVE_DSD | SEEK_FORWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0034 | NATIVE_DSD | SEEK_BACKWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0035 | NATIVE_DSD | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0036 | NATIVE_DSD | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0037 | NATIVE_DSD | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0038 | NATIVE_DSD | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0039 | NATIVE_DSD | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0040 | NATIVE_DSD | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0041 | NATIVE_DSD | PROFILE_CHANGE | policy intent recorded; no PCM DSP attached to Native/DoP |
| EVT4-0042 | NATIVE_DSD | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0043 | DOP | PLAY | canonical playback semantics preserved |
| EVT4-0044 | DOP | PAUSE | canonical playback semantics preserved |
| EVT4-0045 | DOP | RESUME | canonical playback semantics preserved |
| EVT4-0046 | DOP | STOP | canonical playback semantics preserved |
| EVT4-0047 | DOP | SEEK_FORWARD | flush; source seek; DISCONT; marker reset; generation-safe resume |
| EVT4-0048 | DOP | SEEK_BACKWARD | flush; source seek; DISCONT; marker reset; generation-safe resume |
| EVT4-0049 | DOP | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0050 | DOP | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0051 | DOP | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0052 | DOP | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0053 | DOP | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0054 | DOP | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0055 | DOP | PROFILE_CHANGE | policy intent recorded; no PCM DSP attached to Native/DoP |
| EVT4-0056 | DOP | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0057 | DSD_TO_PCM | PLAY | canonical playback semantics preserved |
| EVT4-0058 | DSD_TO_PCM | PAUSE | canonical playback semantics preserved |
| EVT4-0059 | DSD_TO_PCM | RESUME | canonical playback semantics preserved |
| EVT4-0060 | DSD_TO_PCM | STOP | canonical playback semantics preserved |
| EVT4-0061 | DSD_TO_PCM | SEEK_FORWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0062 | DSD_TO_PCM | SEEK_BACKWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0063 | DSD_TO_PCM | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0064 | DSD_TO_PCM | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0065 | DSD_TO_PCM | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0066 | DSD_TO_PCM | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0067 | DSD_TO_PCM | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0068 | DSD_TO_PCM | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0069 | DSD_TO_PCM | PROFILE_CHANGE | policy intent recorded; no PCM DSP attached to Native/DoP |
| EVT4-0070 | DSD_TO_PCM | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0071 | DSD_TO_PCM_DSP | PLAY | canonical playback semantics preserved |
| EVT4-0072 | DSD_TO_PCM_DSP | PAUSE | canonical playback semantics preserved |
| EVT4-0073 | DSD_TO_PCM_DSP | RESUME | canonical playback semantics preserved |
| EVT4-0074 | DSD_TO_PCM_DSP | STOP | canonical playback semantics preserved |
| EVT4-0075 | DSD_TO_PCM_DSP | SEEK_FORWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0076 | DSD_TO_PCM_DSP | SEEK_BACKWARD | flush stateful nodes; seek; rebuild/preroll only if backend contract requires |
| EVT4-0077 | DSD_TO_PCM_DSP | EOS | drain/flush according to §223; next-track policy explicit |
| EVT4-0078 | DSD_TO_PCM_DSP | NEXT_TRACK | canonical playback semantics preserved |
| EVT4-0079 | DSD_TO_PCM_DSP | PREVIOUS_TRACK | canonical playback semantics preserved |
| EVT4-0080 | DSD_TO_PCM_DSP | DEVICE_REMOVE | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0081 | DSD_TO_PCM_DSP | DEVICE_RECONNECT | canonical playback semantics preserved |
| EVT4-0082 | DSD_TO_PCM_DSP | ENGINE_SWITCH | invalidate generation; release/stop safely; no late event acceptance |
| EVT4-0083 | DSD_TO_PCM_DSP | PROFILE_CHANGE | quiescent candidate transaction; predecessor truth or fail-safe STOP |
| EVT4-0084 | DSD_TO_PCM_DSP | APP_SHUTDOWN | invalidate generation; release/stop safely; no late event acceptance |


------------------------------------------------------------------------

# 265. UI STATE MATRIX V4 — PRODUCT COPY / ACTION / DISABLED REASON

No disabled control exists without a reason accessible by tooltip/screen reader/Advanced details.

| ID | State | Primary copy | Action | Reason contract |
|---|---|---|---|---|
| UI4-001 | DSP_OFF | Processing off | Open Audio Lab | none |
| UI4-002 | DSP_ACTIVE | Processing active | Open profile | none |
| UI4-003 | DSP_FAILED | Processing unavailable | Open diagnostics | typed failure |
| UI4-004 | NATIVE_AVAILABLE | Native DSD available | Select Native | qualified tuple |
| UI4-005 | NATIVE_UNKNOWN | Native DSD not verified | Qualify / choose another mode | missing evidence |
| UI4-006 | NATIVE_UNSUPPORTED | Native DSD unsupported | Choose DoP/PCM | exact negative evidence |
| UI4-007 | DOP_CARRIER_ONLY | DoP carrier verified; DAC interpretation not verified | Confirm/qualify device | interpretation evidence missing |
| UI4-008 | DOP_USER_CONFIRMED | DoP enabled by user confirmation | Play / review warning | not physical verification |
| UI4-009 | DOP_PHYSICAL | DoP physically qualified | Select DoP | artifact available |
| UI4-010 | DOP_CONTRADICTED | DoP disabled for this device/revision | Open diagnostics | contradiction |
| UI4-011 | DSD_PCM | DSD converted to PCM | Open Signal Path | explicit conversion |
| UI4-012 | SIGNAL_UNKNOWN | Signal path not fully verified | Open details | missing/not-observable evidence |
| UI4-013 | SIGNAL_CONTRADICTED | Output mismatch | Stop/retry/open diagnostics | contradiction |
| UI4-014 | DIRECT_ENGINE_BLOCKED | Direct requires GStreamer | Open Audio Engine Settings | engine incompatible |
| UI4-015 | IR_MISSING | Impulse response unavailable | Choose another profile / repair asset | asset missing |


------------------------------------------------------------------------

# 266. PHASE EXECUTION CHECKLIST V4 — 16 FASES CON PRE/POST CONTRACT UNIFORME

OpenCode must satisfy the following generic checklist in every phase; phase-specific cards add more.

## 266.1 AP2-F00

- [ ] `AP2-F00-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F00-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F00-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F00-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F00-CHK-05` declare authorities touched.
- [ ] `AP2-F00-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F00-CHK-07` write/identify red tests.
- [ ] `AP2-F00-CHK-08` implement one reversible slice.
- [ ] `AP2-F00-CHK-09` run focused tests.
- [ ] `AP2-F00-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F00-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F00-CHK-12` re-read phase exit contract.
- [ ] `AP2-F00-CHK-13` run diff check/lint.
- [ ] `AP2-F00-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F00-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.2 AP2-F01

- [ ] `AP2-F01-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F01-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F01-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F01-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F01-CHK-05` declare authorities touched.
- [ ] `AP2-F01-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F01-CHK-07` write/identify red tests.
- [ ] `AP2-F01-CHK-08` implement one reversible slice.
- [ ] `AP2-F01-CHK-09` run focused tests.
- [ ] `AP2-F01-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F01-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F01-CHK-12` re-read phase exit contract.
- [ ] `AP2-F01-CHK-13` run diff check/lint.
- [ ] `AP2-F01-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F01-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.3 AP2-F02

- [ ] `AP2-F02-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F02-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F02-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F02-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F02-CHK-05` declare authorities touched.
- [ ] `AP2-F02-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F02-CHK-07` write/identify red tests.
- [ ] `AP2-F02-CHK-08` implement one reversible slice.
- [ ] `AP2-F02-CHK-09` run focused tests.
- [ ] `AP2-F02-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F02-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F02-CHK-12` re-read phase exit contract.
- [ ] `AP2-F02-CHK-13` run diff check/lint.
- [ ] `AP2-F02-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F02-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.4 AP2-F03

- [ ] `AP2-F03-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F03-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F03-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F03-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F03-CHK-05` declare authorities touched.
- [ ] `AP2-F03-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F03-CHK-07` write/identify red tests.
- [ ] `AP2-F03-CHK-08` implement one reversible slice.
- [ ] `AP2-F03-CHK-09` run focused tests.
- [ ] `AP2-F03-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F03-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F03-CHK-12` re-read phase exit contract.
- [ ] `AP2-F03-CHK-13` run diff check/lint.
- [ ] `AP2-F03-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F03-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.5 AP2-F04

- [ ] `AP2-F04-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F04-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F04-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F04-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F04-CHK-05` declare authorities touched.
- [ ] `AP2-F04-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F04-CHK-07` write/identify red tests.
- [ ] `AP2-F04-CHK-08` implement one reversible slice.
- [ ] `AP2-F04-CHK-09` run focused tests.
- [ ] `AP2-F04-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F04-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F04-CHK-12` re-read phase exit contract.
- [ ] `AP2-F04-CHK-13` run diff check/lint.
- [ ] `AP2-F04-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F04-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.6 AP2-F05

- [ ] `AP2-F05-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F05-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F05-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F05-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F05-CHK-05` declare authorities touched.
- [ ] `AP2-F05-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F05-CHK-07` write/identify red tests.
- [ ] `AP2-F05-CHK-08` implement one reversible slice.
- [ ] `AP2-F05-CHK-09` run focused tests.
- [ ] `AP2-F05-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F05-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F05-CHK-12` re-read phase exit contract.
- [ ] `AP2-F05-CHK-13` run diff check/lint.
- [ ] `AP2-F05-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F05-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.7 AP2-F06

- [ ] `AP2-F06-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F06-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F06-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F06-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F06-CHK-05` declare authorities touched.
- [ ] `AP2-F06-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F06-CHK-07` write/identify red tests.
- [ ] `AP2-F06-CHK-08` implement one reversible slice.
- [ ] `AP2-F06-CHK-09` run focused tests.
- [ ] `AP2-F06-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F06-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F06-CHK-12` re-read phase exit contract.
- [ ] `AP2-F06-CHK-13` run diff check/lint.
- [ ] `AP2-F06-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F06-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.8 AP2-F07

- [ ] `AP2-F07-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F07-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F07-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F07-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F07-CHK-05` declare authorities touched.
- [ ] `AP2-F07-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F07-CHK-07` write/identify red tests.
- [ ] `AP2-F07-CHK-08` implement one reversible slice.
- [ ] `AP2-F07-CHK-09` run focused tests.
- [ ] `AP2-F07-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F07-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F07-CHK-12` re-read phase exit contract.
- [ ] `AP2-F07-CHK-13` run diff check/lint.
- [ ] `AP2-F07-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F07-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.9 AP2-F08

- [ ] `AP2-F08-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F08-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F08-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F08-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F08-CHK-05` declare authorities touched.
- [ ] `AP2-F08-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F08-CHK-07` write/identify red tests.
- [ ] `AP2-F08-CHK-08` implement one reversible slice.
- [ ] `AP2-F08-CHK-09` run focused tests.
- [ ] `AP2-F08-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F08-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F08-CHK-12` re-read phase exit contract.
- [ ] `AP2-F08-CHK-13` run diff check/lint.
- [ ] `AP2-F08-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F08-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.10 AP2-F09

- [ ] `AP2-F09-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F09-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F09-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F09-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F09-CHK-05` declare authorities touched.
- [ ] `AP2-F09-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F09-CHK-07` write/identify red tests.
- [ ] `AP2-F09-CHK-08` implement one reversible slice.
- [ ] `AP2-F09-CHK-09` run focused tests.
- [ ] `AP2-F09-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F09-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F09-CHK-12` re-read phase exit contract.
- [ ] `AP2-F09-CHK-13` run diff check/lint.
- [ ] `AP2-F09-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F09-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.11 AP2-F10

- [ ] `AP2-F10-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F10-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F10-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F10-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F10-CHK-05` declare authorities touched.
- [ ] `AP2-F10-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F10-CHK-07` write/identify red tests.
- [ ] `AP2-F10-CHK-08` implement one reversible slice.
- [ ] `AP2-F10-CHK-09` run focused tests.
- [ ] `AP2-F10-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F10-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F10-CHK-12` re-read phase exit contract.
- [ ] `AP2-F10-CHK-13` run diff check/lint.
- [ ] `AP2-F10-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F10-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.12 AP2-F11

- [ ] `AP2-F11-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F11-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F11-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F11-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F11-CHK-05` declare authorities touched.
- [ ] `AP2-F11-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F11-CHK-07` write/identify red tests.
- [ ] `AP2-F11-CHK-08` implement one reversible slice.
- [ ] `AP2-F11-CHK-09` run focused tests.
- [ ] `AP2-F11-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F11-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F11-CHK-12` re-read phase exit contract.
- [ ] `AP2-F11-CHK-13` run diff check/lint.
- [ ] `AP2-F11-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F11-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.13 AP2-F12

- [ ] `AP2-F12-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F12-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F12-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F12-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F12-CHK-05` declare authorities touched.
- [ ] `AP2-F12-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F12-CHK-07` write/identify red tests.
- [ ] `AP2-F12-CHK-08` implement one reversible slice.
- [ ] `AP2-F12-CHK-09` run focused tests.
- [ ] `AP2-F12-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F12-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F12-CHK-12` re-read phase exit contract.
- [ ] `AP2-F12-CHK-13` run diff check/lint.
- [ ] `AP2-F12-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F12-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.14 AP2-F13

- [ ] `AP2-F13-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F13-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F13-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F13-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F13-CHK-05` declare authorities touched.
- [ ] `AP2-F13-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F13-CHK-07` write/identify red tests.
- [ ] `AP2-F13-CHK-08` implement one reversible slice.
- [ ] `AP2-F13-CHK-09` run focused tests.
- [ ] `AP2-F13-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F13-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F13-CHK-12` re-read phase exit contract.
- [ ] `AP2-F13-CHK-13` run diff check/lint.
- [ ] `AP2-F13-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F13-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.15 AP2-F14

- [ ] `AP2-F14-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F14-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F14-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F14-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F14-CHK-05` declare authorities touched.
- [ ] `AP2-F14-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F14-CHK-07` write/identify red tests.
- [ ] `AP2-F14-CHK-08` implement one reversible slice.
- [ ] `AP2-F14-CHK-09` run focused tests.
- [ ] `AP2-F14-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F14-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F14-CHK-12` re-read phase exit contract.
- [ ] `AP2-F14-CHK-13` run diff check/lint.
- [ ] `AP2-F14-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F14-CHK-15` emit handoff with exact HEAD + spec SHA.

## 266.16 AP2-F15

- [ ] `AP2-F15-CHK-01` resolve canonical spec and compute SHA.
- [ ] `AP2-F15-CHK-02` run repository-alignment verifier.
- [ ] `AP2-F15-CHK-03` read BIBLIA A/B + phase card + corrective sections.
- [ ] `AP2-F15-CHK-04` inspect actual HEAD files before proposing names.
- [ ] `AP2-F15-CHK-05` declare authorities touched.
- [ ] `AP2-F15-CHK-06` declare files allowed and cross-phase blockers.
- [ ] `AP2-F15-CHK-07` write/identify red tests.
- [ ] `AP2-F15-CHK-08` implement one reversible slice.
- [ ] `AP2-F15-CHK-09` run focused tests.
- [ ] `AP2-F15-CHK-10` run stale-generation/failure injection relevant to slice.
- [ ] `AP2-F15-CHK-11` run V3.5/M11.5 regression firewall if audio-output semantics touched.
- [ ] `AP2-F15-CHK-12` re-read phase exit contract.
- [ ] `AP2-F15-CHK-13` run diff check/lint.
- [ ] `AP2-F15-CHK-14` update state/artifacts only through verified closure path.
- [ ] `AP2-F15-CHK-15` emit handoff with exact HEAD + spec SHA.


------------------------------------------------------------------------

# 267. TEST ORACLE V4 — QUÉ CUENTA COMO VERDAD EN CADA CLASE DE TEST

```text
PURE DOMAIN TEST
  oracle = deterministic value/invariant

FAKE APPLICATION TEST
  oracle = state machine + calls + rollback semantics
  cannot prove GStreamer/ALSA behavior

REAL GST TEST
  oracle = actual plugin/caps/graph runtime
  cannot prove physical DAC interpretation

ALSA EXACT PROBE
  oracle = kernel/ALSA negotiated parameters for exact binding
  cannot prove analog output quality

PHYSICAL DAC TEST
  oracle = bounded claim tied to exact device/revision/environment

LISTENING OBSERVATION
  useful for click/pop/user experience
  never substitutes byte/caps/tuple conformance
```

A test report must state its oracle class. `PASS` without class is insufficient in final artifacts.


------------------------------------------------------------------------

# 268. FAILURE RECOVERY V4 — SEGUNDO FALLO DURANTE ROLLBACK

The plan must define failure-of-recovery, not only primary failure.

```text
candidate fails before destructive boundary
  -> discard candidate; predecessor untouched

candidate fails after destructive boundary
  -> attempt predecessor restore
       ├ success -> predecessor active, report primary failure
       └ failure -> invalidate predecessor claim, converge STOPPED/FAILED_SAFE

cleanup fails after state logically invalidated
  -> preserve logical safety
  -> emit cleanup diagnostic
  -> do not resurrect old active identity
```

Error precedence:

```text
1 primary operation failure is user-facing root cause
2 rollback failure escalates safety state and is attached diagnostic
3 cleanup failure is diagnostic unless it makes ownership unsafe
4 stale late errors never replace current-generation root cause
```


------------------------------------------------------------------------

# 269. AUDIO ASSET VERSIONING V4 — IR, PROFILES, VECTOR CORPUS Y REFERENCE OUTPUTS

All files used to prove deterministic DSP/DoP behavior are content-addressed.

```text
resources/audio_phase2/test_vectors/
  dop/
  dsd/
  pcm/
  dsp/
  README.md
  MANIFEST.sha256
```

Each vector metadata document records:

```json
{
  "schema": 1,
  "id": "dop-dsd64-stereo-0001",
  "source_sha256": "...",
  "expected_sha256": "...",
  "channels": 2,
  "source_family": "DSD64",
  "operation": "DoP PACKED_24_LE",
  "algorithm_revision": "dop-v1-layout-v2"
}
```

Reference outputs may change only with an explicit algorithm-version change and review; tests never rewrite goldens automatically.


------------------------------------------------------------------------

# 270. RELEASE CLAIM MATRIX V4 — QUÉ PUEDE DECIR MICHI Y QUÉ EVIDENCIA LO AUTORIZA

| Product claim | Minimum evidence |
|---|---|
| “High-resolution source” | file/source facts satisfying documented source criterion |
| “Direct” | runtime path evidence matching Direct semantics |
| “Bit-perfect verified” | M11.5 canonical proof VERIFIED |
| “Processing active” | committed ProcessingGraph + real runtime inspection |
| “Native DSD” | first-class source + Native runtime x-dsd + ALSA tuple evidence |
| “DoP carrier verified” | byte packer + exact carrier negotiation + no mutation |
| “DAC DoP physically verified” | physical/device-observed evidence, not carrier alone |
| “DSD converted to PCM” | explicit converter node + runtime evidence |
| “No resampling” | selected branch inspection proving no active rate change |
| “No remix” | channel layout/count evidence across branch |
| “0 XRUN in qualification run” | measured counter/method over stated duration |

Marketing copy can be weaker than evidence, never stronger.




------------------------------------------------------------------------

# 271. KILLCRITIC V5 — FINAL SPECIFICATION CLOSURE SEAL

Esta sección inicia el **sello final de completitud de especificación**. Su propósito es cerrar las brechas que todavía impedían declarar que el plan, como plan, estuviera al 100 %: perfiles DSD→PCM no totalmente numéricos, decisión productiva DoP todavía abierta, semántica temporal DSP demasiado abstracta, failure-injection sin applicability formal, responsive/DPI sin breakpoints exactos, supply-chain sin key lifecycle completo y physical click/pop sin oracle cuantitativo.

> **Importante:** `SPEC_COMPLETENESS = 100%` significa que ninguna decisión CORE requerida para implementar Audio Phase 2 queda librada al criterio improvisado de OpenCode. **No significa** que el repositorio esté implementado, probado físicamente o liberado. El estado productivo sólo puede alcanzar `IMPLEMENTATION_COMPLETENESS = 100%` después de AP2-F15 con evidencia real.

## 271.1 Precedencia V5

```text
BIBLIA A / B
    ↓
AP2-Fxx phase card
    ↓
FINAL CLOSURE §§271–313
    ↓
KILLCRITIC CORRECTIVE §§210–270
    ↓
Implementation Blueprint §§118–181
    ↓
early design / historical notes
```

Cuando una sección 271–300 resuelve una decisión que en §§210–270 estaba declarada como `ODR`, `research gate`, `candidate`, `preferencia`, `may` o `optional core`, prevalece la decisión V5.

## 271.2 Definición final de 100 % del plan

El plan sólo obtiene 100 % cuando todas las áreas siguientes cumplen simultáneamente:

```text
A01 agent governance              CLOSED
A02 phase DAG / gates             CLOSED
A03 ownership / baseline compat   CLOSED
A04 signal algebra / units        CLOSED
A05 DSP domain/compiler           CLOSED
A06 DSP runtime/transactions      CLOSED
A07 Native DSD                    CLOSED
A08 DoP                           CLOSED
A09 DSD→PCM                       CLOSED
A10 SignalPath / evidence         CLOSED
A11 UI/UX/accessibility           CLOSED
A12 persistence/security/package  CLOSED
A13 tests/CI/traceability         CLOSED
A14 physical/performance spec     CLOSED
```

`CLOSED` en este contexto significa *especificado sin ambigüedad*, no ejecutado.


------------------------------------------------------------------------

# 272. RESEARCH REFRESH V5 — FUENTES TÉCNICAS REVALIDADAS Y DECISIONES QUE SE DERIVAN

Research refresh realizado para cerrar los últimos indicadores.

## 272.1 FFmpeg DSD→PCM

La implementación de referencia actual de FFmpeg/libswresample documenta explícitamente que:

```text
- DSD→PCM usa un low-pass simétrico de 96 taps.
- El filtro tiene ~17 µs de delay en DSD64.
- La respuesta es plana hasta aproximadamente 48 kHz.
- Tras decimar por 8, el espectro por debajo de ~70 kHz es prácticamente libre de alias.
- El rechazo de stopband es aproximadamente 160 dB.
- La conversión genera float PCM a 1/8 de la tasa binaria DSD.
```

Esto convierte la etapa `avdec_dsd_*` / dsd2pcm en una transformación auditable con una base DSP conocida, no en una caja negra genérica.

## 272.2 GStreamer libav DSD decoder

Los elementos `avdec_dsd_lsbf`, `avdec_dsd_msbf` y variantes planar pertenecen a `gst-libav`. La documentación actual de GStreamer muestra que los decoders DSD producen `audio/x-raw` en `F32LE`; las variantes planar anuncian layout `non-interleaved`.

Por tanto el contrato CORE pasa a ser:

```text
DSD elementary
  ↓ explicit avdec_dsd_* selected by source bit order/layout
F32LE PCM at decoder-native rate (= source DSD bit-rate / 8)
  ↓ explicit layout normalizer only if processing backend requires interleaved
  ↓ optional explicit resampler
  ↓ DSP
```

## 272.3 GStreamer resampling

`audioresample` documenta:

```text
quality                    0..10
resample-method            nearest|linear|cubic|blackman-nuttall|kaiser
sinc-filter-mode           interpolated|full|auto
sinc-filter-interpolation  none|linear|cubic
```

El CORE V5 congela:

```text
quality = 10
resample-method = kaiser
sinc-filter-mode = full
sinc-filter-interpolation = none
```

No se confía en valores por defecto si el nodo forma parte de un profile DSD→PCM o un `ResampleNode` de alta calidad.

## 272.4 DoP native implementation stack

GStreamer mantiene bindings Rust oficiales y `gst-plugins-rs`; `GstBaseTransform` está diseñado para filtros de un sink-pad/un src-pad donde tamaño/caps de salida pueden derivarse del input. `gst-plugins-rs` usa `cargo-c` para plugins compartidos instalables en `lib/gstreamer-1.0`.

**Decisión final CORE:** el packer DoP productivo es un plugin Rust/GStreamer Michi-owned. Python queda exclusivamente como oracle/reference implementation de tests.

## 272.5 Parameter smoothing

GStreamer Controller aporta `InterpolationControlSource`, valores time-stamped y modo LINEAR MT-safe. Se adopta sólo para propiedades que el adapter declara `CONTROLLABLE` y cuya mutación no invalida bit-perfect/native/carrier semantics.

## 272.6 Qt High DPI

Qt Quick opera en device-independent pixels y Qt permite simular escalado con `QT_SCALE_FACTOR`. Por ello los breakpoints de UI se definen en **logical/device-independent px**, y la matriz golden debe ejecutarse también a varios scale factors.

## 272.7 MPD como referencia conservadora para DoP

MPD separa Native DSD, DoP y DSD→PCM, mantiene DoP deshabilitado por defecto y exige habilitación explícita porque no puede deducir de forma genérica que el DAC interprete el carrier. Esto refuerza el doble gate ya adoptado por Michi.

## 272.8 Version pinning policy

Las referencias anteriores definen la arquitectura, pero el build real fija versiones:

```text
GStreamer minimum feature baseline     >= 1.24 for first-class DSD contracts
GStreamer Rust bindings                exact Cargo.lock selected at F09
FFmpeg/gst-libav                       package/runtime version captured in manifest
Qt                                     repository baseline requirement
CamillaDSP                             optional, exact discovered version
Rust                                   rust-toolchain.toml pinned channel
cargo-c                                CI pinned version or container image digest
```

No se codifica contra “latest” en CI release.

## 272.9 Repository refresh observado durante V5

Durante esta revisión, `main` fue observado en:

```text
repository  pitydah/michi-music-player
branch      main
observed    2026-09-21
sha         0d6907e72fcc56655f326278844897a29bb9e509
message     fix(qml): prevent shutdown render race
```

Este SHA es **observacional**, no sustituye `baseline_sha`. AP2-F00 debe volver a resolver HEAD y congelar formalmente la baseline después de los gates V3.5/M11.5.


------------------------------------------------------------------------

# 273. DSD→PCM V5 — PIPELINE NORMATIVO COMPLETO

`DSD_TO_PCM_CORE_V1` queda cerrado así:

```text
Elementary DSD truth
      ↓
DsdSignalFormatV2
      ↓
select avdec_dsd_* by:
  bit order
  planar/interleaved source organization
      ↓
F32LE non-interleaved PCM
rate = source_bits_per_second_per_channel / 8
      ↓
explicit audioconvert/layout normalizer if required
      ↓
optional audioresample ONLY when target_rate != decoder_native_rate
      ↓
F32LE processing domain
      ↓
ProcessingGraph
      ↓
terminal precision/output planning
```

## 273.1 Decoder factory table

```text
DSD LSBF interleaved      avdec_dsd_lsbf
DSD MSBF interleaved      avdec_dsd_msbf
DSD LSBF planar           avdec_dsd_lsbf_planar
DSD MSBF planar           avdec_dsd_msbf_planar
```

Si la factory exacta requerida no está instalada:

```text
DSD_PCM_DECODER_UNAVAILABLE
```

No se permite autoplug invisible como sustituto.

## 273.2 Decoder native-rate function

```python
def dsd_decoder_native_rate_hz(source_bps_per_channel: int) -> int:
    if source_bps_per_channel <= 0 or source_bps_per_channel % 8:
        raise ValueError("DSD source rate must be divisible by 8")
    return source_bps_per_channel // 8
```

Examples:

```text
DSD64   2,822,400 bps  -> 352,800 Hz float PCM
DSD128  5,644,800 bps  -> 705,600 Hz float PCM
DSD256 11,289,600 bps  -> 1,411,200 Hz float PCM
DSD512 22,579,200 bps  -> 2,822,400 Hz float PCM
```

## 273.3 Mandatory Signal Path nodes

```text
SOURCE_DSD
DSD_TO_PCM_DECODER
PCM_LAYOUT_NORMALIZER   only if active
RESAMPLER               only if active
DSP_NODE(S)             only if active
OUTPUT_NEGOTIATION
DEVICE
```

`DSD_TO_PCM_DECODER` is always a sample-value transformation; proof relative to original DSD is `NOT_APPLICABLE` after this node.


------------------------------------------------------------------------

# 274. DSD→PCM V5 — QUALITY PROFILES TOTALMENTE DETERMINISTAS

La versión anterior listaba `FAST/BALANCED/HIGH/REFERENCE` pero no cerraba completamente target-rate selection y resampler configuration. V5 lo hace.

## 274.1 Candidate-rate ladders

```python
QUALITY_RATE_LADDERS = {
    "FAST":      (88_200,),
    "BALANCED":  (176_400, 88_200),
    "HIGH":      (352_800, 176_400, 88_200),
    "REFERENCE": (705_600, 352_800, 176_400, 88_200),
}
```

Algorithm:

```text
1. compute decoder_native_rate = source_bps / 8
2. take profile ladder in declared order
3. drop rates > decoder_native_rate
4. drop rates not validated by DSD→PCM backend test matrix
5. drop rates not accepted by active DSP backend if DSP requested
6. drop rates not exactly qualified on selected output path
7. choose first remaining rate
8. if none -> DSD_PCM_NO_QUALIFIED_TARGET_RATE
```

No “best guess”, no maximum-rate marketing inference.

## 274.2 Product exposure

```text
FAST       diagnostics/developer only; never audiophile default
BALANCED   user-visible low-CPU option
HIGH       default when user explicitly chooses DSD→PCM
REFERENCE  user-visible expert option, conditional on benchmark/device qualification
```

## 274.3 Resampler settings

When `target_rate != decoder_native_rate`:

```text
factory                    audioresample
quality                    10
resample-method            kaiser
sinc-filter-mode           full
sinc-filter-interpolation  none
```

If the installed GStreamer version cannot set all four properties with exact readback:

```text
DSD_PCM_RESAMPLER_CONTRACT_UNAVAILABLE
```

and that profile is unavailable rather than degraded silently.

## 274.4 Numeric conformance thresholds — Michi product contract

These are **Michi acceptance criteria**, not claims that upstream libraries guarantee them without measurement.

```text
PCM numeric type after decoder        F32LE
NaN/Inf                               0 allowed
DC gain error                         <= 0.05 dB
20 Hz..20 kHz magnitude error         <= 0.10 dB vs versioned reference
20 kHz..40 kHz magnitude error        <= 0.25 dB when target Nyquist permits
added resampler stopband rejection    >= 80 dB measured
inter-channel gain mismatch           <= 0.01 dB
inter-channel latency mismatch        0 samples
unexpected clipping                   0 samples
```

Because FFmpeg's DSD low-pass is documented as ~160 dB stopband and flat to ~48 kHz for DSD64, Michi's downstream acceptance threshold is intentionally looser than the upstream theoretical filter characteristic; the measured end-to-end chain remains the oracle.

## 274.5 Latency

```text
decoder_filter_delay_us      measured and compared with upstream expectation
resampler_latency_frames     queried/measured
processing_latency_frames    summed from active nodes
reported_total_latency       measured/projection difference <= 1 processing block
```

No hard-coded latency from documentation is used as runtime truth.


------------------------------------------------------------------------

# 275. DSD→PCM V5 — CONFORMANCE HARNESS COMPLETO

Create:

```text
tools/audio_phase2/dsd2pcm_conformance.py
resources/audio_phase2/test_vectors/dsd2pcm/
docs/audio/phase2/dsd2pcm_profiles_v1.json
```

## 275.1 Profile manifest schema

```json
{
  "schema": 1,
  "algorithm": "gst-libav+audioresample",
  "profiles": {
    "HIGH": {
      "rate_ladder_hz": [352800,176400,88200],
      "resampler": {
        "quality": 10,
        "method": "kaiser",
        "filter_mode": "full",
        "interpolation": "none"
      },
      "max_passband_error_db_20k": 0.10,
      "max_passband_error_db_40k": 0.25,
      "min_stopband_rejection_db": 80.0
    }
  }
}
```

All profile constants live in one versioned manifest; QML never duplicates them.

## 275.2 Reference capture process

```text
fixture DSD
  ↓ exact decoder pipeline
appsink float capture
  ↓
SHA256 raw float stream
  ↓
FFT / frequency-response / gain / channel checks
  ↓
JSON measurement artifact
  ↓
compare to profile thresholds
```

## 275.3 Mandatory DSD fixture corpus

```text
DSD64 silence pattern
DSD64 1 kHz
DSD64 10 kHz
DSD64 20 kHz
DSD64 ultrasonic-heavy
DSD128 same family
DSD256 same family
LSBF/MSBF pairs
interleaved/planar equivalent pairs
left-only/right-only
phase inversion
impulse-like transition
random deterministic seeded bitstream
```

## 275.4 Determinism

Same build + same fixture + same profile must produce either:

```text
bit-identical float capture
```

or, if upstream SIMD implementation prevents bit identity:

```text
numeric-equivalent capture within frozen tolerance
```

The selected oracle is recorded per backend/version and never chosen dynamically to hide a regression.


------------------------------------------------------------------------

# 276. DOP V5 — ADR CERRADO: RUST/GSTREAMER ES EL BACKEND CORE PRODUCTIVO

`ODR-DOP-NATIVE-001` queda **RESOLVED**.

## 276.1 Decision

```text
Productive DoP packer       companion/michi-gst-dop
Language                    Rust
Framework                   gstreamer-rs / gstreamer-base
Base class                  GstBaseTransform subclass
Build                       Cargo + cargo-c
Distribution                GStreamer shared plugin
Python implementation       tests/reference only
C implementation            rejected for core unless Rust becomes technically impossible
MPD DoP                     reference behavior only, not execution authority
```

## 276.2 Why this closes the decision

The required transform has:

```text
one input stream
one output stream
output size deterministically derived from input payload/layout
explicit caps transform
deterministic per-buffer state
flush/discontinuity handling
```

which fits `BaseTransform`'s intended filter model.

## 276.3 Repository location

```text
companion/michi-gst-dop/
  Cargo.toml
  Cargo.lock
  rust-toolchain.toml
  src/lib.rs
  src/imp.rs
  src/packer.rs
  src/layout.rs
  tests/vectors.rs
  README.md
```

## 276.4 Version policy

F09 pins a stable `gstreamer-rs` release in Cargo.lock. No git-main dependency in release builds.

## 276.5 Failure of native build

If Rust/cargo-c/plugin packaging cannot satisfy supported release environments:

```text
AP2-F09 = BLOCKED
DoP product feature = unavailable
```

It does **not** fall back to Python streaming.


------------------------------------------------------------------------

# 277. DOP V5 — BUILD, ABI, CAPS Y PACKAGING CONTRACT

## 277.1 Cargo contract

Normative shape:

```toml
[package]
name = "michi-gst-dop"
version = "0.1.0"
edition = "2024"
rust-version = "<pinned-by-rust-toolchain>"
license = "GPL-3.0-or-later"

[lib]
name = "gstmichidop"
crate-type = ["cdylib", "rlib"]

[dependencies]
glib = "<pinned-compatible>"
gstreamer = "<pinned-compatible>"
gstreamer-base = "<pinned-compatible>"

[dev-dependencies]
sha2 = "<pinned-compatible>"
```

Exact numbers are written by F09 after reconciling the frozen distro/toolchain; semantic selection is no longer open.

## 277.2 Plugin ABI

```text
plugin name        michidop
factory            michidop
ABI major          1
metadata key       michi-dop-abi=1
packer revision    dop-v1-layout-v2
sink caps          audio/x-dsd, stereo core
src caps           exact carrier representation selected by plan
```

## 277.3 Events

Must implement/test:

```text
CAPS
SEGMENT
FLUSH_START
FLUSH_STOP
EOS
STREAM_START
DISCONT buffer flag
```

`FLUSH_STOP` and accepted discontinuity reset marker state and pending source bytes.

## 277.4 Build commands

```text
cargo test --locked
cargo cbuild --release --locked
GST_PLUGIN_PATH=<artifact-dir> gst-inspect-1.0 michidop
```

## 277.5 Packaging

```text
AppImage   plugin placed in app-owned GStreamer plugin directory
Flatpak    plugin built in manifest, no runtime compiler
.deb       plugin installed in architecture-specific gstreamer-1.0 path
source     cargo-c build documented and reproducible
```

No Rust compiler is required on an end-user machine.


------------------------------------------------------------------------

# 278. DOP V5 — PERFORMANCE AND STREAMING ORACLES

## 278.1 Hot-path budgets

Michi-defined acceptance:

```text
DSD64 stereo CPU             <= 1.0 % of one reference core p95
DSD128 stereo CPU            <= 2.0 % of one reference core p95
DSD256 stereo CPU            <= 4.0 % of one reference core p95
transform p99 execution      <= 25 % of represented buffer duration
stream underruns attributable to packer  0
per-frame heap allocation    0
per-frame logging            0
unbounded internal buffer    forbidden
```

If target hardware cannot meet these budgets, DoP is not claimed on that performance tier.

## 278.2 Vector parity

```text
Python oracle digest == Rust plugin digest
```

for every supported layout, source bit order, chunk segmentation and discontinuity fixture.

## 278.3 Property-based cases

Generate random but deterministic:

```text
chunk sizes 1..8192 bytes/channel
stream lengths including odd boundaries
marker reset positions
LSBF reversal flag
PACKED_24_LE and S32_LE_LSB24
```

Invariants:

```text
concatenate(pack(chunks)) == pack(concatenated source)
except at explicit DISCONT boundaries where canonical reset is required
```


------------------------------------------------------------------------

# 279. DSP V5 — MUTATION SEMANTICS CERRADAS: DRAFT VS LIVE

The simplest way to guarantee correctness is to stop pretending every DSP edit is safely live.

## 279.1 Core interaction model

```text
PEQ frequency/Q/gain edit      DRAFT
band add/remove                DRAFT
FIR/IR select                  DRAFT
convolution replace            DRAFT
resample target                DRAFT
channel map/delay              DRAFT
polarity                       DRAFT
processing profile switch      APPLY transaction
preamp gain                    LIVE-RAMPED if path is PCM processed
bypass entire DSP              APPLY transaction
```

Audio Lab therefore has:

```text
working/draft graph
active/committed graph
dirty indicator
Apply
Revert
```

No QML slider mutation directly writes GStreamer PEQ parameters in CORE v1.

## 279.2 Apply transaction

```text
validate draft
compile candidate
freeze immutable candidate
quiesce transport
install
preroll
inspect
commit
resume
```

If any step fails, restore predecessor or converge `FAILED_SAFE` as §268 specifies.

## 279.3 Expert live-edit future mode

Coefficient morphing/live PEQ is `POST_CORE`. It cannot lower CORE completeness because it is explicitly excluded from claimed scope.


------------------------------------------------------------------------

# 280. DSP V5 — PREAMP/MUTE RAMP CONSTANTS Y GST CONTROLLER

Only PCM-processed paths may use software ramps.

## 280.1 Ramp policy

```text
normal preamp change <= 6 dB      25 ms linear amplitude ramp
preamp change > 6 dB              50 ms linear amplitude ramp
mute                              20 ms to zero
unmute                            40 ms from zero
quiescent DSP graph swap          20 ms fade-out + swap + 40 ms fade-in
```

The ramp duration is in stream time and is scheduled through GStreamer Controller when the target property is controllable. A direct `g_object_set()` step change is not acceptable for these operations.

## 280.2 Bit-perfect/native exception

No software ramp is inserted on:

```text
PCM Direct bit-perfect candidate
Native DSD
DoP carrier
```

because changing sample/carrier values would invalidate the claimed path. For those transitions, use stop/reopen/device policy; click/pop qualification remains physical.

## 280.3 Ramp verification

Tests capture float PCM before output and verify:

```text
monotonicity for linear ramp
no overshoot
first value == predecessor value within tolerance
last value == requested value within tolerance
actual duration within ±1 processing block
no discontinuous step > configured per-block maximum
```


------------------------------------------------------------------------

# 281. DSP V5 — GRAPH APPLY TIMING AND USER-PERCEIVED BUDGETS

## 281.1 Timing targets

```text
draft validation                 < 10 ms p95
compile 10-band PEQ              < 25 ms p95
quiesce request acknowledged     < 50 ms p95
candidate install+preroll        < 150 ms p95 typical
full Apply interaction           < 300 ms p95 on reference desktop
rollback restore                 < 300 ms p95
```

These are product performance gates; failure does not justify skipping verification.

## 281.2 Slow graph policy

For large FIR/convolution where preroll exceeds 300 ms:

```text
UI shows Applying…
transport state remains truthful
operation may exceed target but remains bounded by 2 s timeout
>2 s -> DSP_APPLY_TIMEOUT and predecessor restoration
```

## 281.3 Asset preparation

IR decode/resample/hash occurs **before** entering the quiescent portion. Quiescent audio time never performs filesystem reads.


------------------------------------------------------------------------

# 282. FAILURE-INJECTION V5 — APPLICABILITY ES PARTE DEL ORACLE

The v2 Cartesian matrix is retained as attack inventory but every case gains an applicability class.

```python
class FailureApplicability(Enum):
    APPLICABLE = "applicable"
    FORBIDDEN_STATE = "forbidden_state"
    NOT_APPLICABLE = "not_applicable"
```

Semantics:

```text
APPLICABLE
    injection can occur on this path; test recovery behavior.

FORBIDDEN_STATE
    architecture says this component must never exist on path;
    test that injection hook cannot be reached/armed.

NOT_APPLICABLE
    no meaningful relation; exclude from execution count but retain rationale.
```

## 282.1 Rules

```text
DoP marker/padding corruption on non-DoP path        FORBIDDEN_STATE
DSP parameter mismatch on Native DSD/DoP             FORBIDDEN_STATE
IR asset removal on DSP path with convolution        APPLICABLE
IR asset removal on pure PCM Direct                   NOT_APPLICABLE
DSD decoder unexpected on Native DSD                  APPLICABLE
DSD decoder unexpected on PCM source                  NOT_APPLICABLE
ALSA busy on any Direct/native/carrier output         APPLICABLE
MAHKB signature failure during playback               NOT_APPLICABLE to audio continuity; APPLICABLE to update subsystem
```

A `FORBIDDEN_STATE` test passes only when the architecture prevents the illegal component from being installed; merely ignoring the injected error is not a pass.


------------------------------------------------------------------------

# 283. UI/UX V5 — BREAKPOINTS EXACTOS EN LOGICAL PIXELS


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Qt Quick geometry is interpreted in device-independent pixels. V5 freezes the breakpoints:

```text
FULL       width >= 1440 logical px
COMPACT    1180 <= width < 1440
NARROW     1024 <= width < 1180
MINIMAL    width < 1024, only if host window policy permits it
```

The historical 1920×154 NowPlaying golden remains the canonical FULL reference.

## 283.1 NowPlaying priorities

```text
P0 transport/play-pause/timeline   never hidden
P0 volume authority               never semantically lost
P1 quality source                 badge may abbreviate
P1 Signal Path                    icon always available
P1 DAC                            icon always available
P1 queue                          icon always available
P2 DSP                            icon always available when feature compiled
P3 network endpoint               overflow/hide until subsystem exists
```

## 283.2 Sizes

```text
NowPlaying height FULL/COMPACT     154 logical px
NARROW                             154 logical px
MINIMAL                            138 logical px if enabled by future host policy
icon hit target desktop            >= 36×36 logical px
popup row hit target               >= 40 logical px high
keyboard focus ring                >= 2 logical px visible contrast
```

No hard-coded physical-pixel compensation; Qt high-DPI scaling handles device ratio.


------------------------------------------------------------------------

# 284. UI/UX V5 — GOLDEN/DPI/ACCESSIBILITY MATRIX


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Golden jobs are generated for logical width and Qt scale factor.

```text
widths       1920, 1440, 1280, 1180, 1024
scale        1.00, 1.25, 1.50, 2.00
```

For each combination validate:

```text
no clipping
no overlap
no text elision hiding active-state semantics
focus order stable
popup opener focus restoration
accessible name non-empty
accessible description includes state where required
reduced motion disables decorative motion
Signal Path state distinguishable without color
HD/DSD badge not sole source of technical information
```

`QT_SCALE_FACTOR` may be used in automated visual tests because Qt documents it specifically as a high-DPI testing mechanism.

## 284.1 Popup geometry

```text
SignalPath quick popup preferred width     420 logical px
DAC quick popup preferred width            420 logical px
DSP quick popup preferred width            420 logical px
maximum popup height                       min(640, availableHeight - 32)
minimum edge margin                        16 logical px
```

Long evidence belongs to Advanced disclosure / detailed view, not forced into the quick popup.


------------------------------------------------------------------------

# 285. PHYSICAL V5 — CLICK/POP ORACLE CUANTITATIVO

Listening remains useful, but F14 gains a reproducible loopback metric when a capture interface is available.

## 285.1 Baseline acquisition

```text
capture 10 s digital silence / device idle
compute RMS noise floor and peak distribution
record interface gain and sample rate
```

## 285.2 Silent-transition threshold

For stop/reopen/profile transition with zero source:

```text
allowed_peak_dbfs = max(-80 dBFS, baseline_peak_dbfs + 12 dB)
```

Any transient above threshold is `PHYSICAL_CLICK_POP_FAIL`, unless the DAC itself produces a documented unavoidable artifact that causes the path to be marked incompatible with seamless transition.

## 285.3 Steady-tone residual

With -20 dBFS 1 kHz source:

```text
capture transition
construct expected ramp/reopen envelope
subtract aligned expected signal
residual peak threshold = max(-60 dBFS, baseline_peak_dbfs + 20 dB)
```

Unexpected residual above threshold fails the mutation class.

## 285.4 Repeatability

```text
>= 100 repetitions per critical transition
report worst, p95, p99 residual peak
zero unclassified audible events
```

The analog measurement does not replace digital correctness tests; it adds a product-quality gate.


------------------------------------------------------------------------

# 286. SECURITY V5 — KEY LIFECYCLE, UPDATE TRUST Y REVOCATION

## 286.1 MAHKB signed-manifest scheme

Normative cryptographic model:

```text
signature algorithm       Ed25519
manifest canonicalization UTF-8 canonical JSON defined by updater implementation
hash                       SHA-256 per payload
key id                     explicit 16+ byte identifier
network at playback        none required
```

The implementation may use a vetted platform/library primitive; it must not implement Ed25519 arithmetic itself.

## 286.2 Root keys

Ship at least two public keys:

```text
PRIMARY
RECOVERY
```

Private keys never ship with the application.

## 286.3 Rotation

A new trusted key is accepted only by a manifest signed with an already trusted non-revoked key. Key records contain:

```text
key_id
public_key
valid_from
valid_until optional
status ACTIVE|REVOKED
introduced_by_manifest
```

## 286.4 Revocation

A security release can revoke a key. After revocation:

```text
payload signed only by revoked key -> reject
rollback to manifest predating revocation -> reject unless recovery procedure explicitly allows
```

## 286.5 Native plugin verification

Release package records:

```text
plugin file SHA-256
Cargo.lock SHA-256
source commit
ABI major
build target triple
SBOM component id
```

Diagnostics compare loaded plugin file against release manifest where packaging format permits exact verification.


------------------------------------------------------------------------

# 287. PACKAGING V5 — SUPPORTED RUNTIME CONTRACT

A build advertised as Audio Phase 2 CORE must include or prove availability of:

```text
GStreamer core/base
GStreamer >= feature baseline with audio/x-dsd support
ALSA backend on Linux
GStreamer libav with avdec_dsd_* factories
GStreamer audioresample
GStreamer audiofx elements required by enabled DSP nodes
michi-gst-dop native plugin if DoP is advertised
```

Feature-disabled builds remain valid Michi builds but cannot advertise the missing Phase2 capability.

## 287.1 Release feature states

```text
BUILT_AND_VERIFIED
BUILT_NOT_PHYSICALLY_QUALIFIED
NOT_BUILT
UNAVAILABLE_RUNTIME
```

No boolean `available` collapses those meanings.

## 287.2 Required release smoke

```text
gst-inspect-1.0 playbin3

gst-inspect-1.0 alsasink

gst-inspect-1.0 audioresample

gst-inspect-1.0 equalizer-nbands

gst-inspect-1.0 audiofirfilter

gst-inspect-1.0 avdec_dsd_lsbf

gst-inspect-1.0 avdec_dsd_msbf

gst-inspect-1.0 michidop     if DoP feature built
```

Command results become release artifacts, not console-only evidence.


------------------------------------------------------------------------

# 288. CI V5 — FINAL GATING GRAPH

A release candidate cannot merge/signal `CORE_READY` until all software gates applicable to that platform pass.

```text
spec-integrity
phase-state-integrity
traceability-schema
python-lint-format
phase2-domain
phase2-dsp-pure
phase2-dsp-real-gstreamer
phase2-dsd-source
phase2-native-dsd-software
phase2-dsd2pcm-conformance
phase2-dop-python-vectors
phase2-dop-rust-vectors
phase2-dop-cross-language-parity
phase2-signalpath
phase2-qml-unit
phase2-qml-golden-dpi
phase2-persistence-migration
phase2-security
phase2-packaging
v35-regression
m11_5-regression
full-suite
```

## 288.1 Merge vs release distinction

```text
MERGE_READY
    all software gates green for the slice

CORE_SOFTWARE_READY
    all software Phase2 gates green

PRODUCT_CLAIM_READY
    required physical gates green for each advertised hardware claim
```

A CI service without DAC hardware can never emit `PRODUCT_CLAIM_READY` by itself.


------------------------------------------------------------------------

# 289. OPEN DECISION REGISTER V5 — CORE DECISIONS CLOSED

This section supersedes §240 for CORE scope.

```text
ODR-DOP-NATIVE-001
status=RESOLVED
resolution=Rust/GStreamer michi-gst-dop plugin
owner_phase=AP2-F09
normative_sections=276,277,278

ODR-DSD2PCM-001
status=RESOLVED
resolution=gst-libav avdec_dsd_* + explicit F32 processing + explicit audioresample when needed
owner_phase=AP2-F10
normative_sections=273,274,275

ODR-LV2-001
status=POST_CORE_NOT_ACTIVATED
blocking=no
owner_phase=POST_CORE

ODR-LIVE-PEQ-MORPH-001
status=POST_CORE_NOT_ACTIVATED
blocking=no
resolution=CORE uses draft+Apply quiescent transaction
normative_sections=279,280,281

ODR-MULTICHANNEL-001
status=POST_CORE_NOT_ACTIVATED
blocking=no
resolution=CORE stereo as §262
```

At AP2-F15 CORE closure:

```text
blocking_core_open_decisions == 0
```

is mandatory.


------------------------------------------------------------------------

# 290. FINAL PLAN COMPLETENESS SCORECARD V5 — 100 % EN TODOS LOS INDICADORES

The percentages below score **specification closure**, not implementation progress.

| Indicator | Weight | V5 score | Closure evidence |
|---|---:|---:|---|
| Biblia / OpenCode governance | 7 | **100%** | mandatory context receipts, phase reads, V5 corrective map |
| Phase DAG / gates / handoff | 7 | **100%** | 16 phase cards + validated state machine + final exit gates |
| Ownership / baseline compatibility | 7 | **100%** | unique-authority maps + adapter migration + regression firewall |
| Signal algebra / PCM / DSD units | 7 | **100%** | incompatible unit types + exact mappings + tests |
| DSP domain / compiler | 7 | **100%** | typed graph/nodes/adapters + deterministic compiler |
| DSP runtime / transactions / evidence | 9 | **100%** | quiescent transaction + rollback + real introspection + draft/apply policy |
| Native DSD | 8 | **100%** | source proof + normalization + exact ALSA + executor + evidence |
| DoP | 8 | **100%** | double gate + byte layouts + Rust backend + parity + packaging |
| DSD→PCM | 7 | **100%** | selected backend + exact rate algorithm + profiles + numeric conformance |
| Signal Path / proof / evidence | 7 | **100%** | DAG invariants + typed verdicts + proof projection ownership |
| UI/UX / accessibility | 6 | **100%** | exact breakpoints + popup geometry + DPI/golden matrix + keyboard/a11y |
| Persistence / security / packaging | 7 | **100%** | versioned schema + key lifecycle + plugin/SBOM + runtime manifest |
| Testing / CI / traceability / KILLCRITIC | 8 | **100%** | oracles + applicability + machine-readable manifests + CI graph |
| Physical / performance specification | 5 | **100%** | run-sheet schema + durations + CPU budgets + click/pop quantitative oracle |

Weighted specification score:

```text
SPEC_COMPLETENESS = 100.00%
```

Again:

```text
SPEC_COMPLETENESS          100%
IMPLEMENTATION_COMPLETENESS depends on actual AP2 work
PHYSICAL_QUALIFICATION     depends on actual hardware runs
PRODUCT_CLAIM_READINESS    depends on evidence
```

The score is not allowed to conceal missing implementation.


------------------------------------------------------------------------

# 291. SPEC_COMPLETENESS.json — MACHINE-READABLE 100 % CONTRACT

Create at F00:

```text
docs/audio/phase2/SPEC_COMPLETENESS.json
```

Schema:

```json
{
  "schema": 1,
  "spec_sha256": "<runtime>",
  "indicators": {
    "agent_governance": 100,
    "phase_dag": 100,
    "ownership": 100,
    "signal_algebra": 100,
    "dsp_domain": 100,
    "dsp_runtime": 100,
    "native_dsd": 100,
    "dop": 100,
    "dsd_to_pcm": 100,
    "signal_path": 100,
    "ui_ux": 100,
    "persistence_security_packaging": 100,
    "testing_ci_traceability": 100,
    "physical_performance_spec": 100
  },
  "blocking_core_open_decisions": 0,
  "implementation_progress": 0,
  "physical_qualification": "NOT_RUN"
}
```

The verifier rejects any indicator <100 for spec freeze, but it never infers implementation progress from these fields.


------------------------------------------------------------------------

# 292. OPENCODE CONTEXT MAP V5 — FINAL CORRECTIVE SECTIONS BY PHASE

This map supersedes §241.

```python
CORRECTIVE_SECTIONS_V5 = {
    "AP2-F00": (271, 272, 287, 288, 289, 290, 291, 299, 300),
    "AP2-F01": (271, 299, 300),
    "AP2-F02": (271, 286, 299, 300),
    "AP2-F03": (228, 271, 299, 300),
    "AP2-F04": (271, 279, 299, 300),
    "AP2-F05": (218, 219, 220, 271, 279, 280, 281, 299, 300),
    "AP2-F06": (218, 219, 220, 271, 279, 280, 281, 299, 300),
    "AP2-F07": (211, 212, 213, 214, 245, 246, 271, 272, 299, 300),
    "AP2-F08": (214, 225, 246, 271, 272, 299, 300),
    "AP2-F09": (215, 216, 217, 226, 247, 271, 272, 276, 277, 278, 299, 300),
    "AP2-F10": (221, 222, 227, 251, 271, 272, 273, 274, 275, 299, 300),
    "AP2-F11": (53, 54, 55, 56, 57, 58, 59, 254, 255, 271, 283, 284, 299, 300, 306, 307, 308, 309, 310, 311, 312, 313),
    "AP2-F12": (229, 271, 299, 300),
    "AP2-F13": (230, 231, 253, 256, 271, 286, 287, 299, 300),
    "AP2-F14": (232, 233, 264, 267, 271, 278, 281, 285, 299, 300),
    "AP2-F15": (234, 235, 236, 257, 258, 259, 260, 261, 270, 271, 288, 289, 290, 291, 299, 300),
}
```

`phase2_context.py` must prefer `CORRECTIVE_SECTIONS_V5` when present.


------------------------------------------------------------------------

# 293. PHASE EXIT GATES V5 — ÚLTIMA CAPA DE CIERRE

Additional non-negotiable exit gates:

```text
F00  source/runtime manifest captured; V5 spec score validates 100
F01  no ambiguous rate/unit aliases enter new domain
F02  no recommendation can become evidence
F03  SignalPath DAG and transition matrix validated
F04  draft/active processing graph semantics implemented in domain
F05  quiescent apply transaction + predecessor restore tests green
F06  all CORE DSP adapters + runtime inspection + ramp policy green
F07  elementary DSD proof and exact unit algebra green
F08  Native branch proves x-dsd end-to-end and no software processing
F09  Rust DoP plugin builds; Python/Rust vector parity 100%; package smoke green
F10  gst-libav decoder family + numeric DSD→PCM profile conformance green
F11  all defined widths/scales golden/a11y gates green
F12  recommendation/runtime contradiction tests green
F13  signing/key lifecycle + plugin integrity + migrations green
F14  performance/physical run sheets complete for advertised claims
F15  no blocking ODR, no mandatory KILLCRITIC NOT_RUN, release claim matrix consistent
```


------------------------------------------------------------------------

# 294. SOURCE FACT VS MICHI PRODUCT POLICY — NEVER CONFUNDIR

| Topic | External/source fact | Michi product decision |
|---|---|---|
| FFmpeg DSD FIR | 96-tap symmetric LPF; documented response properties | accept only via measured end-to-end conformance |
| gst-libav DSD output | F32 raw PCM | normalize into Michi F32 processing domain explicitly |
| GStreamer resampler | configurable quality/method/filter table | force quality=10, Kaiser, full, no interpolation for Phase2 high-quality resampling |
| GStreamer controller | timed interpolation available | use only for PCM processed preamp/mute ramps |
| gst-plugins-rs | Rust plugins supported; cargo-c build | select Rust plugin as DoP CORE backend |
| Qt high DPI | device-independent coordinates, scale simulation | freeze breakpoints in logical px and golden 1.00–2.00 scales |
| MPD DoP | explicit enable due unknown DAC support | keep carrier/device-interpretation double gate |
| CamillaDSP ramps | ramp facilities available | optional backend cannot override Michi profile/transaction authority |

This table prevents an upstream capability from being mistaken for a Michi product guarantee.


------------------------------------------------------------------------

# 295. FINAL IMPLEMENTATION ORDER V5 — CLOSED DAG WITH CONVERGENCE POINTS

```text
F00  freeze + manifests + spec verifier
  ↓
F01  compatibility/domain foundation
  ├─────────► F02 device knowledge
  ├─────────► F03 SignalPath foundation
  └─────────► F04 DSP domain/compiler
                 ↓
               F05 PCM DSP runtime
                 ↓
               F06 DSP completeness

F01+F02+F03
      ↓
    F07 DSD truth/qualification
      ↓
    F08 Native DSD
      ↓
    F09 DoP Rust plugin

F06 + F08 + F09
      ↓
    F10 DSD↔PCM↔DSP convergence
      ↓
    F11 UI/UX convergence
      ↓
    F12 high-end device intelligence
      ↓
    F13 persistence/security/packaging
      ↓
    F14 physical/performance qualification
      ↓
    F15 adversarial/final release seal
```

No F09 coding begins before the Rust build ADR content from §§276–278 has been reconciled with the frozen distro matrix.


------------------------------------------------------------------------

# 296. DSD→PCM TARGET SELECTION — REFERENCE IMPLEMENTATION

```python
from dataclasses import dataclass
from enum import Enum


class DsdPcmProfile(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    HIGH = "high"
    REFERENCE = "reference"


RATE_LADDERS = {
    DsdPcmProfile.FAST: (88_200,),
    DsdPcmProfile.BALANCED: (176_400, 88_200),
    DsdPcmProfile.HIGH: (352_800, 176_400, 88_200),
    DsdPcmProfile.REFERENCE: (705_600, 352_800, 176_400, 88_200),
}


@dataclass(frozen=True, slots=True)
class DsdPcmRateFacts:
    source_bps_per_channel: int
    backend_validated_rates: frozenset[int]
    dsp_validated_rates: frozenset[int] | None
    device_qualified_rates: frozenset[int]
    dsp_requested: bool


def choose_dsd_pcm_target(profile: DsdPcmProfile, facts: DsdPcmRateFacts) -> int:
    if facts.source_bps_per_channel <= 0 or facts.source_bps_per_channel % 8:
        raise ValueError("DSD_PCM_SOURCE_RATE_INVALID")
    decoder_rate = facts.source_bps_per_channel // 8
    candidates = [r for r in RATE_LADDERS[profile] if r <= decoder_rate]
    candidates = [r for r in candidates if r in facts.backend_validated_rates]
    if facts.dsp_requested:
        if facts.dsp_validated_rates is None:
            raise ValueError("DSD_PCM_DSP_RATE_UNKNOWN")
        candidates = [r for r in candidates if r in facts.dsp_validated_rates]
    candidates = [r for r in candidates if r in facts.device_qualified_rates]
    if not candidates:
        raise ValueError("DSD_PCM_NO_QUALIFIED_TARGET_RATE")
    return candidates[0]
```

Tests enumerate every profile × DSD64/128/256/512 × capability subset.


------------------------------------------------------------------------

# 297. MICHI-DOP RUST CORE — PACKER CONTRACT DE REFERENCIA

The plugin wrapper is version-specific to the pinned gstreamer-rs API, but the packer core is pure Rust and stable.

```rust
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CarrierLayout {
    Packed24Le,
    S32LeLsb24,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct StreamState {
    marker_phase: u8,
    pending: Vec<Vec<u8>>,
    discontinuity_generation: u64,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PackError {
    InvalidChannelCount,
    InvalidMarkerPhase,
    ChannelLengthMismatch,
}

const MARKERS: [u8; 2] = [0x05, 0xFA];

#[inline]
fn emit_sample(out: &mut Vec<u8>, a: u8, b: u8, marker: u8, layout: CarrierLayout) {
    match layout {
        CarrierLayout::Packed24Le => out.extend_from_slice(&[a, b, marker]),
        CarrierLayout::S32LeLsb24 => out.extend_from_slice(&[a, b, marker, 0x00]),
    }
}

pub fn pack_complete_frames(
    channels: &[&[u8]],
    marker_phase: &mut u8,
    reverse_bits: bool,
    layout: CarrierLayout,
    out: &mut Vec<u8>,
) -> Result<usize, PackError> {
    if channels.is_empty() || channels.len() > 2 {
        return Err(PackError::InvalidChannelCount);
    }
    if *marker_phase > 1 {
        return Err(PackError::InvalidMarkerPhase);
    }
    let len = channels[0].len();
    if channels.iter().any(|ch| ch.len() != len) {
        return Err(PackError::ChannelLengthMismatch);
    }
    let usable = len & !1usize;
    let mut frames = 0usize;
    for off in (0..usable).step_by(2) {
        let marker = MARKERS[*marker_phase as usize];
        for ch in channels {
            let mut a = ch[off];
            let mut b = ch[off + 1];
            if reverse_bits {
                a = a.reverse_bits();
                b = b.reverse_bits();
            }
            emit_sample(out, a, b, marker, layout);
        }
        *marker_phase ^= 1;
        frames += 1;
    }
    Ok(frames)
}
```

The productive plugin adds bounded pending-byte state because GStreamer buffers need not align to 2 source bytes/channel.


------------------------------------------------------------------------

# 298. NOWPLAYING RESPONSIVE POLICY — QML REFERENCE


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

```qml
readonly property int layoutModeFull: 0
readonly property int layoutModeCompact: 1
readonly property int layoutModeNarrow: 2
readonly property int layoutModeMinimal: 3

readonly property int responsiveMode: width >= 1440
    ? layoutModeFull
    : width >= 1180
        ? layoutModeCompact
        : width >= 1024
            ? layoutModeNarrow
            : layoutModeMinimal

readonly property bool showQualityText: responsiveMode <= layoutModeCompact
readonly property bool showDacText: responsiveMode === layoutModeFull
readonly property bool showSignalVerdictText: responsiveMode === layoutModeFull
readonly property bool useShortVolume: responsiveMode >= layoutModeCompact
```

The exact component names must reconcile with the frozen QML baseline, but these breakpoint semantics are normative.


------------------------------------------------------------------------

# 299. FINAL ZERO-AMBIGUITY RULES V5

No CORE implementer is allowed to choose any of the following during coding:

```text
DoP language/backend                     already Rust/GStreamer
DoP carrier/device evidence relationship already double-gated
DSD→PCM backend                          already gst-libav avdec_dsd_*
DSD→PCM target-rate algorithm            already §274/§296
DSD→PCM resampler settings               already fixed
DSP edit semantics                       draft+Apply, preamp only live-ramped
DSP ramp timings                         already §280
UI breakpoints                           already §283
high-DPI test scales                     already §284
click/pop oracle                         already §285
MAHKB signature algorithm                already Ed25519
Phase2 core multichannel                 excluded, stereo core
LV2                                      post-core not activated
live PEQ coefficient morph               post-core not activated
```

The only things implementation may discover are **facts about the environment**:

```text
factory present or absent
actual runtime caps
actual ALSA tuple support
actual DAC behavior
actual performance
actual physical noise/click behavior
```

Those discoveries select among already-defined states; they do not authorize a new architecture.


------------------------------------------------------------------------

# 300. FINAL SPEC FREEZE CONTRACT — CUÁNDO ESTA BIBLIA PUEDE LLAMARSE COMPLETA


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

After incorporating §§271–313, the design document itself is considered `SPEC_CLOSED_V6` when a verifier proves:

```text
1. canonical file exists exactly once
2. all section anchors needed by phase2_context.py resolve
3. no duplicate phase BEGIN/END markers
4. all 14 SPEC_COMPLETENESS indicators == 100
5. blocking_core_open_decisions == 0
6. every CORE technology has a selected implementation or explicit unsupported state
7. every CORE claim has a minimum evidence class
8. every CORE phase has entry/exit gates
9. every CORE runtime mutation has failure/rollback semantics
10. every hardware-specific claim is gated by physical evidence
11. historical/superseded snippets cannot outrank V5
12. no unresolved CORE TODO/FIXME/research marker exists outside historical text
```

At this point:

```text
PLAN_STATUS = SPEC_CLOSED_V6
SPEC_COMPLETENESS = 100%
IMPLEMENTATION_STATUS = DEFERRED until baseline activation
```

The implementation can still fail tests. That is expected and useful: the plan's job is to make failures converge to a predefined state rather than force an agent to invent what should happen.


------------------------------------------------------------------------
# 301. FAILURE-INJECTION APPLICABILITY MATRIX V5 — EXHAUSTIVE CORE

| ID | Path | Injection | Applicability | Required oracle |
|---|---|---|---|---|
| FIA5-0001 | PCM_DIRECT | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0002 | PCM_DIRECT | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0003 | PCM_DIRECT | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0004 | PCM_DIRECT | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0005 | PCM_DIRECT | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0006 | PCM_DIRECT | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0007 | PCM_DIRECT | DSP_FACTORY_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0008 | PCM_DIRECT | DSP_PARAMETER_MISMATCH | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0009 | PCM_DIRECT | IR_ASSET_REMOVED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0010 | PCM_DIRECT | DOP_MARKER_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0011 | PCM_DIRECT | DOP_PADDING_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0012 | PCM_DIRECT | DSD_DECODER_UNEXPECTED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0013 | PCM_DIRECT | DSD_PCM_DECODER_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0014 | PCM_DIRECT | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0015 | PCM_DIRECT | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0016 | PCM_DIRECT | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0017 | PCM_DIRECT | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0018 | PCM_DIRECT | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0019 | PCM_DIRECT | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0020 | PCM_DIRECT | NATIVE_PLUGIN_ABI_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0021 | PCM_DSP | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0022 | PCM_DSP | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0023 | PCM_DSP | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0024 | PCM_DSP | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0025 | PCM_DSP | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0026 | PCM_DSP | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0027 | PCM_DSP | DSP_FACTORY_MISSING | APPLICABLE | typed failure + safe convergence |
| FIA5-0028 | PCM_DSP | DSP_PARAMETER_MISMATCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0029 | PCM_DSP | IR_ASSET_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0030 | PCM_DSP | DOP_MARKER_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0031 | PCM_DSP | DOP_PADDING_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0032 | PCM_DSP | DSD_DECODER_UNEXPECTED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0033 | PCM_DSP | DSD_PCM_DECODER_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0034 | PCM_DSP | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0035 | PCM_DSP | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0036 | PCM_DSP | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0037 | PCM_DSP | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0038 | PCM_DSP | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0039 | PCM_DSP | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0040 | PCM_DSP | NATIVE_PLUGIN_ABI_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0041 | NATIVE_DSD | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0042 | NATIVE_DSD | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0043 | NATIVE_DSD | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0044 | NATIVE_DSD | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0045 | NATIVE_DSD | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0046 | NATIVE_DSD | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0047 | NATIVE_DSD | DSP_FACTORY_MISSING | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0048 | NATIVE_DSD | DSP_PARAMETER_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0049 | NATIVE_DSD | IR_ASSET_REMOVED | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0050 | NATIVE_DSD | DOP_MARKER_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0051 | NATIVE_DSD | DOP_PADDING_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0052 | NATIVE_DSD | DSD_DECODER_UNEXPECTED | APPLICABLE | typed failure + safe convergence |
| FIA5-0053 | NATIVE_DSD | DSD_PCM_DECODER_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0054 | NATIVE_DSD | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0055 | NATIVE_DSD | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0056 | NATIVE_DSD | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0057 | NATIVE_DSD | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0058 | NATIVE_DSD | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0059 | NATIVE_DSD | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0060 | NATIVE_DSD | NATIVE_PLUGIN_ABI_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0061 | DOP | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0062 | DOP | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0063 | DOP | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0064 | DOP | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0065 | DOP | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0066 | DOP | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0067 | DOP | DSP_FACTORY_MISSING | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0068 | DOP | DSP_PARAMETER_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0069 | DOP | IR_ASSET_REMOVED | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0070 | DOP | DOP_MARKER_CORRUPTION | APPLICABLE | typed failure + safe convergence |
| FIA5-0071 | DOP | DOP_PADDING_CORRUPTION | APPLICABLE | typed failure + safe convergence |
| FIA5-0072 | DOP | DSD_DECODER_UNEXPECTED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0073 | DOP | DSD_PCM_DECODER_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0074 | DOP | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0075 | DOP | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0076 | DOP | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0077 | DOP | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0078 | DOP | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0079 | DOP | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0080 | DOP | NATIVE_PLUGIN_ABI_MISMATCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0081 | DSD_TO_PCM | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0082 | DSD_TO_PCM | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0083 | DSD_TO_PCM | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0084 | DSD_TO_PCM | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0085 | DSD_TO_PCM | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0086 | DSD_TO_PCM | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0087 | DSD_TO_PCM | DSP_FACTORY_MISSING | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0088 | DSD_TO_PCM | DSP_PARAMETER_MISMATCH | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0089 | DSD_TO_PCM | IR_ASSET_REMOVED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0090 | DSD_TO_PCM | DOP_MARKER_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0091 | DSD_TO_PCM | DOP_PADDING_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0092 | DSD_TO_PCM | DSD_DECODER_UNEXPECTED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0093 | DSD_TO_PCM | DSD_PCM_DECODER_MISSING | APPLICABLE | typed failure + safe convergence |
| FIA5-0094 | DSD_TO_PCM | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0095 | DSD_TO_PCM | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0096 | DSD_TO_PCM | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0097 | DSD_TO_PCM | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0098 | DSD_TO_PCM | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0099 | DSD_TO_PCM | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0100 | DSD_TO_PCM | NATIVE_PLUGIN_ABI_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0101 | DSD_TO_PCM_DSP | DEVICE_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0102 | DSD_TO_PCM_DSP | BINDING_GENERATION_CHANGE | APPLICABLE | typed failure + safe convergence |
| FIA5-0103 | DSD_TO_PCM_DSP | GST_PREROLL_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0104 | DSD_TO_PCM_DSP | GST_GRAPH_INSPECTION_FAILURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0105 | DSD_TO_PCM_DSP | ALSA_BUSY | APPLICABLE | typed failure + safe convergence |
| FIA5-0106 | DSD_TO_PCM_DSP | ALSA_TIMEOUT | APPLICABLE | typed failure + safe convergence |
| FIA5-0107 | DSD_TO_PCM_DSP | DSP_FACTORY_MISSING | APPLICABLE | typed failure + safe convergence |
| FIA5-0108 | DSD_TO_PCM_DSP | DSP_PARAMETER_MISMATCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0109 | DSD_TO_PCM_DSP | IR_ASSET_REMOVED | APPLICABLE | typed failure + safe convergence |
| FIA5-0110 | DSD_TO_PCM_DSP | DOP_MARKER_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0111 | DSD_TO_PCM_DSP | DOP_PADDING_CORRUPTION | FORBIDDEN_STATE | installation/arming structurally refused |
| FIA5-0112 | DSD_TO_PCM_DSP | DSD_DECODER_UNEXPECTED | NOT_APPLICABLE | excluded with machine-readable rationale |
| FIA5-0113 | DSD_TO_PCM_DSP | DSD_PCM_DECODER_MISSING | APPLICABLE | typed failure + safe convergence |
| FIA5-0114 | DSD_TO_PCM_DSP | CONTEXT_PUMP_DIES | APPLICABLE | typed failure + safe convergence |
| FIA5-0115 | DSD_TO_PCM_DSP | ENGINE_SWITCH | APPLICABLE | typed failure + safe convergence |
| FIA5-0116 | DSD_TO_PCM_DSP | STOP_DURING_PREPARE | APPLICABLE | typed failure + safe convergence |
| FIA5-0117 | DSD_TO_PCM_DSP | SEEK_DURING_STREAM | APPLICABLE | typed failure + safe convergence |
| FIA5-0118 | DSD_TO_PCM_DSP | DB_CORRUPT | APPLICABLE | typed failure + safe convergence |
| FIA5-0119 | DSD_TO_PCM_DSP | MAHKB_BAD_SIGNATURE | APPLICABLE | typed failure + safe convergence |
| FIA5-0120 | DSD_TO_PCM_DSP | NATIVE_PLUGIN_ABI_MISMATCH | FORBIDDEN_STATE | installation/arming structurally refused |


------------------------------------------------------------------------

# 302. DSD→PCM PROFILE DECISION MATRIX V5 — SOURCE × PROFILE

| Source | Decoder native | FAST | BALANCED | HIGH | REFERENCE |
|---|---:|---|---|---|---|
| DSD64 | 352800 Hz | 88200 | 176400/88200 | 352800/176400/88200 | 352800/176400/88200 |
| DSD128 | 705600 Hz | 88200 | 176400/88200 | 352800/176400/88200 | 705600/352800/176400/88200 |
| DSD256 | 1411200 Hz | 88200 | 176400/88200 | 352800/176400/88200 | 705600/352800/176400/88200 |
| DSD512 | 2822400 Hz | 88200 | 176400/88200 | 352800/176400/88200 | 705600/352800/176400/88200 |

Each cell is an ordered candidate ladder; capability/evidence filtering chooses the first qualified value.


------------------------------------------------------------------------

# 303. QML GOLDEN MATRIX V5 — WIDTH × SCALE

| ID | Logical width | QT_SCALE_FACTOR | Mode | Required result |
|---|---:|---:|---|---|
| QML5-001 | 1920 | 1.00 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-002 | 1920 | 1.25 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-003 | 1920 | 1.50 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-004 | 1920 | 2.00 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-005 | 1440 | 1.00 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-006 | 1440 | 1.25 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-007 | 1440 | 1.50 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-008 | 1440 | 2.00 | FULL | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-009 | 1280 | 1.00 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-010 | 1280 | 1.25 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-011 | 1280 | 1.50 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-012 | 1280 | 2.00 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-013 | 1180 | 1.00 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-014 | 1180 | 1.25 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-015 | 1180 | 1.50 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-016 | 1180 | 2.00 | COMPACT | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-017 | 1024 | 1.00 | NARROW | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-018 | 1024 | 1.25 | NARROW | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-019 | 1024 | 1.50 | NARROW | no clip/overlap; stable focus/a11y; golden reviewed |
| QML5-020 | 1024 | 2.00 | NARROW | no clip/overlap; stable focus/a11y; golden reviewed |


------------------------------------------------------------------------

# 304. PHASE CLOSURE ARTIFACT MATRIX V5

| Phase | Mandatory artifacts | Mandatory regression | Cannot close while |
|---|---|---|---|
| AP2-F00 | phase-receipt.json; test-report-ap2-f00.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F01 | phase-receipt.json; test-report-ap2-f01.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F02 | phase-receipt.json; test-report-ap2-f02.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F03 | phase-receipt.json; test-report-ap2-f03.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F04 | phase-receipt.json; test-report-ap2-f04.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F05 | phase-receipt.json; test-report-ap2-f05.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F06 | phase-receipt.json; test-report-ap2-f06.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F07 | phase-receipt.json; test-report-ap2-f07.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F08 | phase-receipt.json; test-report-ap2-f08.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F09 | phase-receipt.json; test-report-ap2-f09.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F10 | phase-receipt.json; test-report-ap2-f10.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F11 | phase-receipt.json; test-report-ap2-f11.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F12 | phase-receipt.json; test-report-ap2-f12.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F13 | phase-receipt.json; test-report-ap2-f13.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F14 | phase-receipt.json; test-report-ap2-f14.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |
| AP2-F15 | phase-receipt.json; test-report-ap2-f15.json; spec-sha.txt | focused + phase firewall + full suite when shared contracts touched | mandatory gate NOT_RUN; stale spec SHA; unresolved P0/P1; blocking ODR |


------------------------------------------------------------------------

# 305. V5 CLOSURE REQUIREMENT CATALOG

| ID | Requirement | Owner | Verification |
|---|---|---|---|
| V5REQ-0001 | DSD2PCM.decoder-factory | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0002 | DSD2PCM.native-rate | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0003 | DSD2PCM.profile-ladder | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0004 | DSD2PCM.resampler-settings | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0005 | DSD2PCM.numeric-response | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0006 | DSD2PCM.latency | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0007 | DSD2PCM.fixture-corpus | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0008 | DSD2PCM.determinism | F10 | automated/physical oracle defined by §§271–300 |
| V5REQ-0009 | DOP.rust-backend | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0010 | DOP.cargo-lock | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0011 | DOP.abi | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0012 | DOP.caps | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0013 | DOP.events | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0014 | DOP.vector-parity | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0015 | DOP.chunking | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0016 | DOP.performance | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0017 | DOP.packaging | F09 | automated/physical oracle defined by §§271–300 |
| V5REQ-0018 | DSP.draft-active-separation | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0019 | DSP.quiescent-apply | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0020 | DSP.preamp-ramp | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0021 | DSP.mute-ramp | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0022 | DSP.rollback | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0023 | DSP.timeout | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0024 | DSP.asset-preparation | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0025 | DSP.runtime-evidence | F05/F06 | automated/physical oracle defined by §§271–300 |
| V5REQ-0026 | UI.breakpoints | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0027 | UI.hit-targets | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0028 | UI.popup-geometry | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0029 | UI.dpi-matrix | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0030 | UI.focus | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0031 | UI.screen-reader | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0032 | UI.reduced-motion | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0033 | UI.golden | F11 | automated/physical oracle defined by §§271–300 |
| V5REQ-0034 | SEC.ed25519 | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0035 | SEC.key-rotation | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0036 | SEC.revocation | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0037 | SEC.plugin-hash | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0038 | SEC.sbom | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0039 | SEC.redaction | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0040 | SEC.ir-bounds | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0041 | SEC.atomic-update | F13 | automated/physical oracle defined by §§271–300 |
| V5REQ-0042 | PHYS.noise-baseline | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0043 | PHYS.silent-transient | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0044 | PHYS.steady-tone-residual | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0045 | PHYS.repeat-count | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0046 | PHYS.soak | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0047 | PHYS.xrun | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0048 | PHYS.artifact-schema | F14 | automated/physical oracle defined by §§271–300 |
| V5REQ-0049 | PHYS.claim-binding | F14 | automated/physical oracle defined by §§271–300 |

------------------------------------------------------------------------

# 306. NOWPLAYINGBAR VISUAL CONTRACT V6 — REFERENCIA DEL PRODUCT OWNER


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Esta sección corrige una omisión del plan: las secciones 53–59 definían bien la
**semántica** de Quality, Signal Path, DAC y Network Output, pero no congelaban
con suficiente precisión la **posición visual exacta** de las cuatro funciones
marcadas por el product owner en la maqueta final.

La referencia visual aprobada es la captura entregada por el product owner con
los números rojos `1`, `2`, `3`, `4`.

```text
reference_asset_name   NOWPLAYINGBAR_PHASE2_TARGET_REFERENCE.png
reference_source       product-owner supplied mockup
reference_sha256       6c464510d03505a8b129cdd969c9f0b75c3fa2ea0ac7a7b597c163cccaa33eb3
reference_canvas       1260 x 313 px
content_bbox           x=10..1249, y=10..302
white_outer_border     ANNOTATION / NOT PRODUCT UI
```

La captura actual del producto se utiliza sólo como **before-state visual**.
La maqueta numerada es el **target-state visual** para este subcomponente.

Regla de autoridad:

```text
V6 slot contract §§306–313
    > §53.2 generic row diagram
    > historical NowPlaying descriptions
```

El blanco exterior de la maqueta es margen de la imagen y se ignora por completo.
No debe producir:

```text
NO white frame
NO extra Rectangle around NowPlayingBar
NO new outer padding
NO change to player-surface backplane
```


------------------------------------------------------------------------

# 307. NOWPLAYINGBAR V6 — MAPEO NORMATIVO EXACTO DE LOS NÚMEROS 1–4


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

Los cuatro números rojos significan exactamente:

| Nº | Posición visual | Función final | Estado actual que reemplaza/evoluciona | Autoridad |
|---:|---|---|---|---|
| **1** | dentro del extremo derecho del `qualityBadge` | indicador factual `HD` o `DSD` | el badge actual sólo contiene dot + texto | `SourceResolutionClass` / source facts |
| **2** | fila inferior, inmediatamente a la derecha del `qualityBadge` | **DAC Quick Surface** | ocupa la celda que hoy usa `queueButton`; Queue se desplaza una columna a la derecha | `DeviceSetupReadModel` + autoridades DAC existentes |
| **3** | fila superior, extremo derecho | **Michi Music Stream / Network Output** | evoluciona la posición del actual `outputDeviceButton` | futuro `NetworkOutputBridge` / endpoint authority |
| **4** | fila inferior, extremo izquierdo | **Signal Truth / Signal Path Quick Surface** | reemplaza el selector rápido `audioEngineButton` | `SignalTruth + SignalPathGraph + SignalPathReadModel` |

Consecuencia espacial obligatoria:

```text
CURRENT
ROW 0  [ DacVolumeControl span 2 ] [ settingsButton ] [ outputDeviceButton ]
ROW 1  [ audioEngineButton       ] [ qualityBadge   ] [ queueButton    ] [ empty ]

TARGET V6
ROW 0  [ DacVolumeControl span 2 ] [ settingsButton ] [ #3 networkOutputButton ]
ROW 1  [ #4 signalPathButton     ] [ qualityBadge+#1] [ #2 dacQuickButton     ] [ queueButton ]
```

Ésta es la interpretación canónica de la maqueta. No intercambiar `#2` y `#4`.


------------------------------------------------------------------------

# 308. NOWPLAYINGBAR V6 — CONTRATO QML DE GRID, GEOMETRÍA Y OBJECT NAMES


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

El layout final conserva la macrogeometría actual del repositorio:

```text
NowPlayingBar.implicitHeight = 154
outputZone.columns = 4
button preferred size = 34 x 34 logical px
qualityBadge preferred height = 34 logical px
DacVolumeControl spans columns 0..1 on row 0
```

Blueprint normativo de placement:

```qml
DacVolumeControl {
    objectName: "dacVolumeControl"
    Layout.row: 0
    Layout.column: 0
    Layout.columnSpan: 2
}

MichiIconButton {
    objectName: "settingsButton"
    Layout.row: 0
    Layout.column: 2
    iconName: "equalizer"
}

MichiIconButton {
    objectName: "networkOutputButton"
    Layout.row: 0
    Layout.column: 3
    iconName: "audio-output"
}

MichiIconButton {
    objectName: "signalPathButton"
    Layout.row: 1
    Layout.column: 0
    iconName: "audio-engine"   // chip + waveform, matches approved mockup
}

Rectangle {
    id: qualityBadge
    objectName: "qualityBadge"
    Layout.row: 1
    Layout.column: 1
    Layout.fillWidth: true
}

MichiIconButton {
    objectName: "dacQuickButton"
    Layout.row: 1
    Layout.column: 2
    iconName: "sparkles"       // exact visual language of approved mockup
}

MichiIconButton {
    objectName: "queueButton"
    Layout.row: 1
    Layout.column: 3
    iconName: "queue"
}
```

Los `objectName` anteriores son el **target contract** para tests V6. Si el
repositorio congelado ya introdujo nombres equivalentes, AP2-F11 debe reconciliar
sin duplicar controles.

No se permite resolver la maqueta mediante anchors absolutos o offsets mágicos.
El `GridLayout` sigue siendo la autoridad geométrica.


------------------------------------------------------------------------

# 309. SLOT #1 V6 — HD/DSD DENTRO DEL QUALITY BADGE, NO COMO BOTÓN SEPARADO


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

La maqueta muestra `HD` **dentro** del pill de calidad. Éste es un detalle visual
normativo que faltaba en el plan.

Estructura final:

```text
┌──────────────────────────────────────────┐
│ ●  FLAC · 24-bit · 96 kHz        [ HD ] │
└──────────────────────────────────────────┘
```

Para DSD:

```text
┌──────────────────────────────────────────┐
│ ●  DSF · DSD64                  [ DSD ]  │
└──────────────────────────────────────────┘
```

Para MP3 o PCM estándar:

```text
┌──────────────────────────────────────────┐
│ ●  MP3 · 320 kbps                        │
└──────────────────────────────────────────┘
```

Reglas:

```text
LOSSY              -> no mini badge
LOSSLESS_STANDARD  -> no mini badge
HIGH_RES_PCM       -> mini badge HD
DSD                -> mini badge DSD
UNKNOWN            -> no mini badge
NO TRACK           -> no mini badge
```

El mini badge:

```text
is NOT clickable
is NOT a new GridLayout column
is NOT a Signal Truth verdict
is NOT a bit-perfect indicator
is NOT a DAC capability indicator
```

QML objetivo interno:

```qml
RowLayout {
    anchors.fill: parent
    anchors.leftMargin: MichiSpacing.md
    anchors.rightMargin: MichiSpacing.sm

    Rectangle { /* status dot */ }

    MichiText {
        Layout.fillWidth: true
        text: root.qualityText()
        elide: Text.ElideRight
    }

    Rectangle {
        id: sourceResolutionBadge
        objectName: "sourceResolutionBadge"
        visible: root.sourceResolutionClass === "high_res_pcm"
              || root.sourceResolutionClass === "dsd"
        // compact outlined badge; no layout expansion outside qualityBadge
    }
}
```

Accessible name combines facts without marketing overclaim:

```text
"File quality: FLAC, 24 bit, 96 kilohertz, high-resolution source"
"File quality: DSD64 source"
```


------------------------------------------------------------------------

# 310. SLOT #2 V6 — DAC QUICK BUTTON EN LA CELDA LIBERADA POR QUEUE


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

`#2` es **DAC Quick**, no Signal Path.

Final placement:

```text
ROW 1 / COLUMN 2
icon = sparkles
objectName = dacQuickButton
popup opens upward
```

La celda se obtiene moviendo `queueButton` de `column=2` a `column=3`.

El botón `#2` debe:

```text
open the compact Device Setup / DAC popup
show selected != active truthfully
show Direct/Shared profile truthfully
show current local DAC identity/status
provide link to full Device Setup
never expose Network Output authority
never expose engine selection
never infer DSD/DoP from marketing metadata
```

Migración recomendada desde el estado actual:

```text
current outputDeviceButton + AudioOutputPopup
             │
             ├── local DAC/output responsibilities ──► #2 dacQuickButton
             │                                         DacQuick/DeviceSetup popup
             │
             └── remote/network responsibility ─────► #3 networkOutputButton
                                                       only when backend exists
```

Esto evita perder la funcionalidad local actual al reasignar `outputDeviceButton`
a Michi Stream.


------------------------------------------------------------------------

# 311. SLOT #3 V6 — MICHI MUSIC STREAM / NETWORK OUTPUT EN TOP-RIGHT


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

`#3` conserva la **posición** del actual icono `audio-output`, pero cambia su
semántica final: representa destino/zone de red, especialmente Michi Music Stream.

Final placement:

```text
ROW 0 / COLUMN 3
objectName = networkOutputButton
icon = audio-output
```

Estados UI permitidos:

```text
HIDDEN                 backend not built and product policy chooses no affordance
DISABLED_UNAVAILABLE   backend absent but product wants discoverability
READY                  discovery authority available
CONNECTED              selected endpoint active
RECONNECTING            endpoint/session state says reconnecting
FAILED                 typed network-output failure
```

Antes de existir un `NetworkOutputBridge` real:

```text
NO fake Stream popup
NO fake device list
NO fake zones
NO fake connected indicator
NO stealing local DAC selection from #2
```

Durante una transición incremental es válido que la posición #3 conserve
**temporalmente** la acción de output actual, pero sólo hasta que #2 haya absorbido
completamente la selección/configuración local del DAC y los tests de regresión
sean verdes.


------------------------------------------------------------------------

# 312. SLOT #4 V6 — SIGNAL TRUTH / SIGNAL PATH REEMPLAZA AUDIO ENGINE QUICK SELECTOR


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

`#4` ocupa exactamente el slot del actual `audioEngineButton`.

Final placement:

```text
ROW 1 / COLUMN 0
objectName = signalPathButton
icon = audio-engine   // visual aprobado: microchip + waveform
accessibleName = "Signal path"
```

La reutilización visual del glyph `audio-engine` es intencional porque la
maqueta aprobada mantiene ese icono; su **semántica cambia** de selector a
observabilidad de la cadena.

Comportamiento final:

```text
click #4
  ↓
SignalPathQuickSurface
  ↓
verdict + compact chain + evidence state
  ↓
[ Detailed Signal Path ]
```

Nunca:

```text
click #4 -> engine selection
```

El selector de motor migra a:

```text
Settings > Audio Engine
```

El `SignalPathQuickSurface` debe mostrar el engine activo como **nodo observado**,
no como control de selección.

Transición contractual:

```text
1. prove Settings can select/change engine completely
2. add SignalPath read model + popup
3. replace audioEngineButton semantics/objectName in NowPlaying
4. migrate/remove AudioEnginePopup quick wiring
5. keep engine settings tests
6. replace old NowPlaying selector tests with Signal Path tests
```


------------------------------------------------------------------------

# 313. NOWPLAYINGBAR V6 — GOLDEN, ACCESSIBILITY, TRANSITION TESTS Y CONTEXT GATE


> **R8 CANONICAL UI NOTE:** la composición visual, placement, navegación y nombres de superficies de esta sección son históricos cuando contradicen §§331–350. Conservar únicamente invariantes técnicos/evidence/rollback que no entren en conflicto con el contrato canónico de popups R1.

La referencia visual no se acepta por “parecido”. AP2-F11 debe tener tests
explícitos de estructura y golden.

## 313.1 Structural QML gates

```text
NPB6-001  NowPlayingBar implicitHeight remains 154
NPB6-002  outputZone has 4 columns
NPB6-003  dacVolumeControl row0 col0 span2
NPB6-004  settingsButton row0 col2
NPB6-005  networkOutputButton row0 col3
NPB6-006  signalPathButton row1 col0
NPB6-007  qualityBadge row1 col1
NPB6-008  dacQuickButton row1 col2
NPB6-009  queueButton row1 col3
NPB6-010  no empty row1 col3 placeholder remains
NPB6-011  sourceResolutionBadge is child/descendant of qualityBadge
NPB6-012  no second audio-engine selector exists in NowPlayingBar
NPB6-013  no second local DAC selector authority exists
```

## 313.2 Semantic gates

```text
NPB6-020  MP3 320 -> no HD badge
NPB6-021  FLAC 16/44.1 -> no HD badge
NPB6-022  FLAC 24/96 -> HD
NPB6-023  DSD64 -> DSD
NPB6-024  #2 opens local DAC quick surface
NPB6-025  #3 never claims network endpoint when backend absent
NPB6-026  #4 opens Signal Path, not AudioEnginePopup
NPB6-027  Queue still opens after moving from column2 to column3
NPB6-028  settingsButton behavior unchanged
NPB6-029  volume behavior unchanged
```

## 313.3 Interaction/accessibility gates

```text
Tab order remains deterministic
Enter/Space activates #2/#3/#4 when enabled
Escape closes popup and returns focus to opener
reduced-motion respected
screen-reader names describe semantic action, not old object purpose
no color-only status encoding
all 34x34 controls retain the existing MichiIconButton hit-area policy
```

## 313.4 Golden target

Golden comparison must ignore:

```text
external white border of product-owner mockup
red annotation numbers
annotation-only red marks
```

Golden comparison must preserve:

```text
relative slot order
quality pill position/shape
HD/DSD mini-badge inside pill
speaker/network icon at top-right
chip/wave Signal Path icon at bottom-left
sparkles DAC icon immediately right of quality pill
Queue at bottom-right
154px bar height
existing premium material/background
```

## 313.5 Context loading

Any OpenCode task touching `NowPlayingBar.qml` for Audio Phase 2 MUST load at
minimum:

```text
§§53–59
§§254–255
§§283–284
§§306–313
```

plus the AP2-F11 card and the frozen repository version of:

```text
NowPlayingBar.qml
AppShell.qml
AudioOutputPopup.qml
AudioEnginePopup.qml
SignalTruthPanel.qml
MichiIcon.qml
```

Rule:

```text
VISUAL TARGET UNKNOWN -> NO NOWPLAYING PATCH
SLOT NUMBER SEMANTICS UNKNOWN -> NO NOWPLAYING PATCH
```

---

# 314. REPOSITORY RECONCILIATION V8 — CURRENT MAIN IS THE FACTUAL INPUT

```text
repository      pitydah/michi-music-player
branch          main
head            aa8a8d3a884f465766a85313417262195089fac2
head_date       2026-09-28T01:06:43Z
head_message    fix(dac): qualify cold output handovers
```

R10 delta material sobre `7bd4f5a`:

```text
aa8 handover
  selected target can differ from active predecessor
  cold qualification is asynchronous and bounded
  active candidate is not published before backend acceptance
  stale completion loses to newer selection
  Fixed/Unity visual label removed while semantic/accessibility truth remains
```

Este SHA es el **audit head de esta revisión**, no el futuro baseline AP2.
`AP2-F00` debe volver a resolver `HEAD`, specs y gates en runtime.

Cambio material desde el snapshot V7 (`bc536...`):

```text
M11.4 implementation/tooling/finalization
    -> cerrados técnicamente para el feature-set PCM entregado

physical execution
    -> todavía INCOMPLETE

R25
    -> first-sample evidence es per-delay; el mínimo se deriva sólo de esos hechos

R32
    -> USB health usa ABI genérica documentada (busnum/devnum/urbnum)
       + kernel journal filtrado por topología/ventana

R36
    -> ledger acumulativo cases{}; ningún caso individual promueve PASS global

manifest identity
    -> usb_descriptor_sha256 se propaga como descriptor_hash y se valida
```

La reconciliación no convierte tooling completo en evidencia física completa.

---

# 315. CURRENT ROADMAP STATE V8

| Área | Verdad actual a `aa8a8d3` | Consecuencia |
|---|---|---|
| M11.3 | DONE / TESTED / FROZEN | heredar; no reabrir |
| M11.4 PCM runtime | implementación productiva completa | heredar |
| M11.4 tooling/finalization | complete para contratos R25/R32/R35/R36 | heredar tooling, no fabricar evidencia |
| DAC-V35-110 | PASS acotado previo en SMSL | preservar, no universalizar |
| Physical closure execution | **INCOMPLETE** | R25/R32/R35/R36 aplicables siguen pendientes en manifests reales |
| bit-perfect | **NOT CLAIMED** | Signal Truth no puede mostrarlo como estado actual |
| exclusivity | **NOT CLAIMED** | no inferir por `ALSA Direct` |
| M11.5 | **NOT STARTED / NOT IMPLEMENTED** | AP2 sigue bloqueado |
| DAC-V35-120 | DO NOT START / conditional | no duplicar hardware volume |
| DAC-V35-130 | POST-STABLE ONLY | fuera de core |
| DAC-V35-140 | separate DSD/DoP promotion; not started | ownership ADR requerido |
| NowPlaying | preimage productivo existente; R8 target no implementado | migración staged |
| AudioEnginePopup | existente/productivo | refactor in-place |
| AudioOutputPopup | existente/productivo | refactor in-place |
| SignalTruthPanel | existente, compacto/read-only | preimage para futuro popup |
| Equalizer/Advanced EQ | no productivos | dependen de DSP authority |
| Michi Stream rows | no integradas en Player output model | requieren adapter/authority Michi Link |

**No se fija un conteo de tests como verdad permanente dentro de esta tabla.**
Cada agente debe obtener un receipt reproducible en el SHA real que va a mutar.
La ausencia de un status remoto adjunto al commit no permite inventar CI verde.

---

# 316. M11.4 PCM INHERITANCE V8 — DELETE DUPLICATE PHASE2 WORK

```text
Linux observation
→ AudioDeviceRegistry
→ AudioDeviceClassification
→ Output profile/path policy
→ PCM source characterization
→ CandidateCarrierResolver
→ exact DacQualificationService
→ OutputPlanner
→ OutputSessionService
→ DirectOutputExecutor
→ strict GStreamer sink / authorized converter
→ ALSA readback
→ SignalTruthRecorder
→ AudioOutputBridge / existing QML
```

Phase 2 no crea copias de registry, PCM qualifier, carrier resolver, output
planner, session service, Signal Truth recorder o local-output coordinator.

El cierre de tooling reciente también se hereda: Phase 2 no vuelve a inventar
R25/R32/R35/R36; consume sus contratos/evidencia cuando corresponda.

---

# 317. DEVICE KNOWLEDGE V8 — CLASSIFICATION IS ENRICHMENT, NOT ICON GUESSING

```text
AudioDeviceRegistry / AudioDeviceSnapshot
→ AudioDeviceClassification
→ Phase2 DeviceKnowledgeResolver
   ├ commercial identity
   ├ MAHKB matches
   ├ provenance/conflicts
   └ derived fingerprint [not stable identity]
→ ResolvedDeviceKnowledge
```

Categorías productivas actuales observadas por `AudioOutputBridge`:

```text
system
external_audio
audio_interface
local_audio
display_audio
other_audio
```

La UI puede proyectar iconos a partir de un `iconType` **emitido por la capa de
presentación**. QML no parsea `displayName`, `alsaLocator` o nombres ALSA para
decidir si algo es jack/optical/DAC.

Si el tipo físico no está demostrado:

```text
UNKNOWN PORT TYPE -> generic device/speaker icon
```

Nunca mostrar jack u óptico por estética solamente.

---

# 318. CAPABILITY V8 — TUPLE-SCOPED QUALIFICATION IS NON-NEGOTIABLE

Una tupla probada no es una matriz cartesiana. `QUALIFIED` sólo puede provenir
de la autoridad de qualification/runtime vigente.

La UI compacta puede resumir:

```text
USB DAC · Direct
PCM 96 kHz · 24 bit
```

sólo cuando esos campos proceden de evidencia actual y generation-safe.
MAHKB, marketing o nombre comercial pueden enriquecer copy/identity, pero no
promueven capability truth.

---

# 319. CARRIER / SIGNAL TRUTH V8

La política PCM vigente sigue siendo propiedad de V3.5. Native DSD y DoP
requieren modelos tipados/promoción separada.

`DIRECT_CONTAINER_ADAPTED` continúa siendo un verdict/evidence fact del sistema
vigente; no se reescribe como una conclusión inventada por `SignalPathGraph`.

A `aa8a8d3`:

```text
Direct != bit-perfect
ALSA Direct != exclusive
container adapted != source-native carrier
```

Signal Truth R8 debe conservar esas distinciones.

---

# 320. PHYSICAL EVIDENCE V8 — TOOLING COMPLETE != CAMPAIGN COMPLETE

La reconciliación más reciente cerró los contratos del field lab, no las
ejecuciones físicas archivadas.

Pendiente por hardware/manifest cuando aplique:

```text
R25  per-delay first-sample evidence + derived minimum
R32  8 h soak + bounded resources + USB ABI health + kernel diagnostics
R35  four canonical tail/drain observations with fixture/capture hashes
R36  cumulative required recovery cases
```

El SMSL conserva su PASS físico anterior dentro de su alcance registrado, pero
ese PASS no cubre automáticamente los laboratorios pendientes ni a KINMAX.

`PASS_MULTI_HARDWARE` sigue requiriendo evidencia completa en al menos dos
dispositivos materialmente distintos según el contrato activo.

---

# 321. NOWPLAYING V8 — CURRENT PREIMAGE EXACTO Y TARGET R8

Preimage verificado en `NowPlayingBar.qml` a `aa8a8d3`:

```text
GridLayout columns = 4

ROW 0
col0-1  DacVolumeControl
col2    settingsButton
        iconName = "equalizer"
        action   = settingsRequested()
col3    outputDeviceButton
        iconName = "audio-output"
        opens    = AudioOutputPopup

ROW 1
col0    audioEngineButton
        iconName = "audio-engine"
        opens    = AudioEnginePopup
col1    qualityBadge
        Rectangle / Accessible.StaticText
col2    queueButton
col3    empty Item
```

Target canónico:

```text
ROW 0
col0-1  DacVolumeControl
col2    equalizerButton -> EqualizerPopup
col3    queueButton

ROW 1
col0    audioEngineButton -> AudioEnginePopup
col1    qualityBadge -> SignalTruthPopup
col2    audioOutputButton -> AudioOutputPopup
col3    spacer
```

**Delta mínimo; no rewrite del NowPlayingBar.**

El control `audio-output` ya es un speaker-cabinet frontal en
`primitives/MichiIcon.qml`; se preserva para evitar confusión con volumen.

La cápsula de calidad cambia de StaticText a control accesible/clickable sin
dejar de mostrar el mismo source-quality truth.

---

# 322. UPDATED REUSE ESTIMATE V8

| Capability | Reusable | Missing / cambio |
|---|---:|---:|
| Device admission / identity | 95% | 5% |
| Device presentation classification | 85% | iconType/port semantics |
| PCM qualification / carrier | 97% | Phase2 extensions only |
| PCM Signal Truth authority | 94% | popup/read model richer |
| AudioOutputBridge | 92% | compact projection + future network adapter |
| AudioOutputPopup | 72% | canonical rows/icons/sections/footer; preserve recovery |
| AudioEngineBridge | 95% | quickSubtitle/icon metadata only |
| AudioEnginePopup | 78% | canonical cards/icons/focus restoration |
| SignalTruthPanel | 45% | useful preimage, not final SignalTruthPopup |
| NowPlaying slot wiring | 70% | swap/rebind 3 slots + clickable quality |
| Icon system | 85% | add DAC/jack/optical/display/engine-specific/stream-cat |
| Theme/tokens | 98% | **reuse existing tokens; no new theme stack** |
| Basic EQ UI | 15% | new surface; DSP authority prerequisite |
| Advanced EQ UI | 35% | historical AudioLab concepts reusable |
| DSP runtime | 20% | 80% |
| Native DSD | 15% | 85% |
| DoP | 10% | 90% |
| DSD→PCM | 15% | 85% |
| Michi Stream output projection | 10% | cross-authority adapter + handover |

Los porcentajes son planificación, no test verdicts.

---

# 323. AP2 PHASE DELTA V8

```text
F00 freeze future exact baseline, never hardcode the audit-head SHA
F01 adapt existing V3.5 contracts
F02 enrich current semantics; no registry fork
F03 graph/read projection over current Signal Truth + future proof
F04-F06 build DSP authority/compiler/runtime
F07-F10 DSD/DoP/DSD→PCM after ownership seal
F11 converge UI using exact current preimage + §§331–380
F12 device intelligence builds on tuple-scoped evidence
F13 persists only new Phase2 state
F14 extends existing field-evidence discipline
F15 seals PCM regression firewall + Phase2 claims
```

Visual-only maintenance of existing popups before F11, if explicitly authorized
outside Audio Phase 2, must preserve all runtime contracts and may not be
mislabelled as Phase2 implementation.

---

# 324. M11.5 / DAC-V35-140 / PHASE2 DSD OWNERSHIP BLOCKER V8

Antes de F00, un ADR/authority amendment debe asignar exactamente un owner para:

```text
DSD source characterization
Native DSD execution
DoP packing/execution
DSD→PCM
format transitions
proof/verdict generation
physical qualification
```

M11.5 puede verificar garantías, pero no debe coexistir con una segunda
implementación de transporte.

```text
PATCHSET_DSD_DOP_GENERATION_ALLOWED = FALSE
```

hasta que esa ownership esté congelada.

---

# 325. CURRENT REPOSITORY FILE MAP V8 — VERIFIED PREIMAGE

Archivos verificados en `main @ aa8a8d3` y relevantes para R8:

```text
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioOutputPopup.qml
src/michi/presentation/qml/player/AudioEnginePopup.qml
src/michi/presentation/qml/components/SignalTruthPanel.qml
src/michi/presentation/qml/components/DacDeviceCard.qml
src/michi/presentation/qml/views/AudioOutputSettingsSection.qml
src/michi/presentation/qml/primitives/MichiIcon.qml
src/michi/presentation/qml/controls/MichiIconButton.qml
src/michi/presentation/qml/theme/MichiPalette.qml
src/michi/presentation/qml/theme/MichiSemanticColors.qml
src/michi/presentation/qml/theme/MichiSpacing.qml
src/michi/presentation/qml/theme/MichiRadius.qml
src/michi/presentation/qml/theme/MichiMetrics.qml
src/michi/presentation/qml/theme/MichiMotion.qml
src/michi/presentation/qml/theme/MichiBreakpoints.qml
src/michi/presentation/qml/theme/MichiAccessibility.qml
src/michi/presentation/audio_output_bridge.py
src/michi/presentation/audio_engine_bridge.py
```

No existe actualmente, bajo el path canónico preferido comprobado, el archivo:

```text
docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md
```

Por tanto, si se pretendiera ejecutar Phase2 hoy, la propia regla
`STOP_SPEC_NOT_FOUND` debe dispararse hasta que esta Biblia revisada se incorpore
al repositorio en un único path versionado.

Targets que pueden no existir todavía:

```text
EqualizerPopup.qml
AdvancedEqualizerPopup.qml
SignalTruthPopup.qml
audio_processing_bridge.py
```

Su ausencia no autoriza nombres/ownership improvisados.

---

# 326. AP2-F00 ENTRY GATE V8 — CURRENT BLOCKERS

```text
M11.4 productive PCM implementation       SATISFIED / preserve
M11.4 closure tooling/finalization        SATISFIED / preserve
bounded SMSL physical evidence            SATISFIED within recorded scope
physical R25/R32/R35/R36 campaigns        BLOCKING where required by active close
M11.5                                     BLOCKING: NOT STARTED
DSD/DoP ownership                         BLOCKING: not frozen
canonical Phase2 spec in repository       BLOCKING for implementation sessions
AP2_BASELINE_SHA                          BLOCKING: future freeze
```

F00 exige:

```text
current V3.5 GO at exact future head
all mandatory inherited physical gates resolved
M11.5 IMPLEMENTED + TESTED
zero inherited DAC P0/P1
accepted DSD/DoP ownership amendment
full required suite/gates reproducible
exact AP2 baseline SHA
one unique versioned Phase2 spec
final repository reconciliation
```

Ninguna mejora estética del mockup modifica estos gates.

---

# 327. PATCH-READINESS EFFECT V8

```text
GENERATE_MEGA_PATCH_NOW = NO
GENERATE_PHASE2_PATCHSET_AFTER_F00 = YES
```

La madurez actual reduce el patchset futuro: Audio Engine, Audio Output, theme,
icon framework y parte de Signal Truth ya tienen preimage productivo.

Un patch futuro debe ser **delta sobre aa8a8d3-or-later**, no una reproducción
del blueprint histórico.

---

# 328. REPOSITORY-DRIFT VERIFIER V8

Antes de cada tarea de implementación:

```text
git status --short
git rev-parse HEAD
git branch --show-current
git ls-files '*MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md'
```

Verificar además:

- V3.5/M11.5 state;
- current AudioDeviceRegistry/semantics/carrier contracts;
- current SignalTruthRecorder contract;
- AudioOutputBridge shape;
- AudioEngineBridge shape;
- exact NowPlaying grid/objectNames;
- existing theme/icon tokens;
- tests/goldens at the exact head.

Si `HEAD` cambia respecto del audit head y la tarea depende de repository state:

```text
STOP_REPOSITORY_RECONCILIATION_REQUIRED
```

No tratar ningún SHA histórico como baseline activo.

---

# 329. OPENCODE CONTEXT MAP V8

```python
CORRECTIVE_SECTIONS_V8 = {
    "AP2-F00": (314,315,320,324,325,326,328,329,330,351,358,360),
    "AP2-F01": (314,316,318,319,323,325,330,351,360),
    "AP2-F02": (314,317,318,323,325,330,351,353,360),
    "AP2-F03": (314,319,323,325,330,351,355,360),
    "AP2-F04": (314,323,325,330,351,357,360),
    "AP2-F05": (314,323,325,330,351,357,360),
    "AP2-F06": (314,323,325,330,351,357,360),
    "AP2-F07": (314,319,323,324,325,330,351,355,360),
    "AP2-F08": (314,323,324,325,330,351,355,360),
    "AP2-F09": (314,323,324,325,330,351,355,360),
    "AP2-F10": (314,323,324,325,330,351,355,357,360),
    "AP2-F11": (
        314,321,323,325,330,
        331,332,333,334,335,336,337,338,339,340,
        341,342,343,344,345,346,347,348,349,350,
        351,352,353,354,355,356,357,358,359,360
    ),
    "AP2-F12": (314,317,318,320,323,325,330,351,353,360),
    "AP2-F13": (314,316,323,325,328,330,351,357,360),
    "AP2-F14": (314,320,323,325,326,330,351,355,360),
    "AP2-F15": (314,315,320,324,326,327,328,330,351,360),
}
```

`SUMMARY_IS_NOT_AUTHORITY = TRUE` sigue vigente.

---

# 330. PRECEDENCE V8 — REPOSITORY TERRAIN + CANONICAL DESIGN

Para repository state:

```text
current exact repository at task HEAD
→ V3.5 / accepted ADRs / frozen inherited contracts
→ §§314–330 + §§351–380 reconciliation
→ older repository snapshots
```

Para UI/UX:

```text
BIBLIA A / B temporal + ownership
→ AP2-Fxx phase gate
→ §§351–380 current-repo corrective
→ §§331–350 canonical popups R1/R9
→ historical UI blueprints
```

Para audio truth:

```text
runtime/domain authorities
→ evidence/proof models
→ bridge/read projection
→ QML
```

```text
UI MAY PRESENT TRUTH
UI MUST NOT CREATE TRUTH
```

La siguiente reconciliación es obligatoria inmediatamente antes de F00 y ante
cualquier HEAD drift material.

---

# 331. CANONICAL POPUPS R9 — AUTORIDAD VISUAL/FUNCIONAL

Esta sección congela el diseño aprobado de las quick surfaces de audio.

**No cambia el gate temporal de Phase2.** El hecho de que Audio Engine y Audio
Output ya existan productivamente no autoriza DSP/DSD/DoP ni la convergencia F11.

Preguntas canónicas:

| Superficie | Pregunta |
|---|---|
| Equalizer | ¿Cómo quiero moldear el sonido? |
| Audio Engine | ¿Qué backend está reproduciendo? |
| Signal Truth | ¿Qué está ocurriendo realmente con la señal? |
| Audio Output | ¿Dónde está sonando? |
| Queue | ¿Qué sigue? |

Regla:

```text
NEW TECHNOLOGY != NEW NOWPLAYING BUTTON
```

Michi Stream es destination, no botón. DAC es destination, no botón. Signal
Path es contenido de Signal Truth, no botón paralelo.

---

# 332. NOWPLAYING R9 — COMPOSICIÓN FINAL SOBRE EL PREIMAGE REAL

Target:

```text
ROW0  [ DacVolumeControl span 2 ] [ Equalizer ] [ Queue ]
ROW1  [ Audio Engine ] [ Quality / Signal Truth ] [ Audio Output ] [ spacer ]
```

## 332.1 Equalizer

El actual `settingsButton` (row0 col2, icon `equalizer`) migra a
`equalizerButton`.

No navegar a Settings:

```text
click -> EqualizerPopup
       -> Open Advanced EQ
          -> AdvancedEqualizerPopup
```

Durante la etapa previa a DSP funcional, **no cambiar el wiring productivo a un
popup vacío**. El slot se activa sólo junto con la autoridad DSP correspondiente.

## 332.2 Queue

`queueButton` migra de row1 col2 a row0 col3. Mantiene su signal/semántica.

## 332.3 Audio Engine

El actual `audioEngineButton` se conserva en row1 col0, con el icono
`audio-engine` **sin rediseño global**.

## 332.4 Quality -> Signal Truth

La cápsula existente en row1 col1 conserva source quality y se vuelve
`Accessible.Button`.

```text
click -> SignalTruthPopup
```

El badge `HD`/`DSD` es source-format/quality metadata, nunca prueba de path.

## 332.5 Audio Output

El actual `outputDeviceButton` migra row0 col3 -> row1 col2.

Conserva `iconName: "audio-output"`: el repositorio ya implementa un monitor
speaker/cabinet frontal, distinto del icono `volume`.

## 332.6 Spacer

row1 col3 permanece vacío. No rellenarlo por oportunismo.

---

# 333. DESIGN TOKENS R9 — REUTILIZAR EL THEME REAL, NO CREAR OTRO

**Prohibido crear `MichiColors.qml`, un segundo `MichiMetrics.qml` o un segundo
`MichiMotion.qml`.**

Autoridades existentes:

```text
MichiPalette
MichiSemanticColors
MichiSpacing
MichiRadius
MichiMetrics
MichiMotion
MichiBreakpoints
MichiAccessibility
MichiTypography
```

## 333.1 Palette factual del repositorio

Base:

```text
obsidian       #090B11
obsidianDeep   #07090E
graphite       #14171C
smoke          #1F232A
smokeRaised    #282D36
textPrimary    #ECEEF3
textSecondary  #9CA1AE  [normal mode]
textMuted      #8A90A0  [normal mode]
auroraBlue     #4CA6FF
auroraCyan     #21D6E6
auroraPurple   #9A7CFF
auroraGreen    #5DE3A2
warning        #E4B866
error          #FF6B7A
```

Estados se toman de `MichiSemanticColors`:

```text
surfaceHover
surfacePressed
surfaceSelected
borderSubtle
borderStrong
focusRing
auroraCyanBorder*
auroraPurpleSurface*
```

High contrast se obtiene de los tokens existentes; no hardcodear variantes.

## 333.2 Playback/EQ slider palette — EXACT SAME SOURCE TOKENS

La autoridad visual es el slider actual de `NowPlayingBar.qml`:

```qml
GradientStop { position: 0.00; color: MichiPalette.auroraBlue }
GradientStop { position: 0.72; color: MichiPalette.auroraCyan }
GradientStop { position: 1.00; color: MichiPalette.auroraPurple }
```

Handle actual:

```text
fill                    MichiPalette.textPrimary
pressed / visualFocus   border auroraCyan
hover                   border auroraBlue
idle                    border auroraPurple
pressed scale            1.08
hover scale              1.04
```

**MichiEqSlider debe consumir esos mismos tokens.**

Vertical EQ:

```text
bottom -> top:
auroraBlue -> auroraCyan (72%) -> auroraPurple
```

Preamp horizontal: misma orientación del playback slider.

No duplicar hex ni definir una paleta EQ paralela.

## 333.3 Geometry

Usar tokens existentes:

```text
MichiSpacing.*
MichiRadius.*
MichiMetrics.*
```

Popup floating radius = `MichiRadius.floating` cuando visualmente aplique.
Icon buttons = `MichiMetrics.controlMedium` salvo golden que demuestre necesidad
de preservar 34 px en NowPlaying.

---

# 334. INTERACTION R9 — HOVER, FOCUS, MOTION, EXCLUSIVITY

## 334.1 Rows

```text
idle       transparent / canonical row surface
hover      MichiSemanticColors.surfaceHover
pressed    MichiSemanticColors.surfacePressed
selected   MichiSemanticColors.surfaceSelected + semantic accent border
focus      MichiFocusRing / MichiSemanticColors.focusRing
disabled   existing disabled token/opacity
busy       spinner/status, no second authority
```

No escalar filas completas.

## 334.2 Icon buttons

Reutilizar `MichiIconButton`:

```text
hover scale   1.02
pressed scale 0.985
motion        MichiMotion.micro
```

No crear una segunda interacción para los botones de audio.

## 334.3 Popups

Usar `Popup` QML dentro de la misma window. No `Window`/top-level hacks.

Motion objetivo:

```text
open  MichiMotion.popupOpen
close MichiMotion.popupClose
```

Si se añade translateY 6 px, debe respetar `MichiAccessibility.reducedMotion`.

## 334.4 One technical popup at a time

Exclusividad es **estado de presentación**, no servicio de dominio.

Preferencia de implementación en el preimage actual:

```qml
function closeOtherAudioPopups(exceptId) { ... }
```

dentro de `NowPlayingBar`, o un helper presentation-only local. No crear un
global singleton authority sólo para cuatro booleans.

## 334.5 Wayland

Preservar el patrón que ya corrigió Audio Output:

```text
Popup parent = opener
coordinates relative to opener
open upward
no explicit Overlay reparent + global move hack
```

Un shell compartido puede encapsular clamp/margins, pero no convertir los popups
en top-level windows.

---

# 335. ICON TAXONOMY R9 — EXTENDER `primitives/MichiIcon.qml`

El repo actual usa Canvas vectorial en `MichiIcon.qml`. **No migrar a SVG sólo
por este plan.**

Ya existen y se reutilizan:

```text
equalizer
audio-output
audio-engine
cat
settings
queue
sliders
device
```

Añadir sólo los glifos requeridos:

```text
dac
audio-jack
optical
display-audio
stream-cat
engine-qt
engine-gstreamer
engine-mpd
```

## 335.1 `stream-cat`

No cambiar globalmente `cat`, porque puede tener otros usos de branding.

`stream-cat`:

- silueta/outline de cabeza de gato;
- sin ojos ni detalle ornamental;
- mismo stroke que MichiIcon;
- no Wi-Fi como símbolo principal.

## 335.2 DAC

Chassis Hi-Fi frontal:

```text
LED | display/slot | knob
```

No monitor, no tarjeta genérica.

## 335.3 Dynamic local/system icon

El bridge emite `iconType`.

```text
proven analog jack    -> audio-jack
proven IEC958/SPDIF   -> optical
display transport     -> display-audio
external DAC          -> dac
unknown physical port -> audio-output/device fallback
```

**No inferir jack/optical por nombre textual.**

System Output actualmente no expone necesariamente el puerto físico real; si no
hay evidencia, usar fallback `audio-output`.

## 335.4 Engine icons

```text
Qt Multimedia -> engine-qt
GStreamer     -> engine-gstreamer
MPD           -> engine-mpd
```

La identidad técnica sigue viniendo de `AudioEngineBridge`.

---

# 336. EQUALIZER POPUP R9 — QUICK DSP SIN NUEVA AUTHORITY

## 336.1 Domain mapping

El EQ gráfico básico **no crea `GraphicEqNode`**.

Se proyecta al dominio DSP ya planificado como:

```text
PreampNode
ParametricEqNode
  └─ 10 fixed PEAK bands
```

Centros canónicos guardados:

```text
31.25
62.5
125
250
500
1000
2000
4000
8000
16000 Hz
```

Labels UI:

```text
31  62  125  250  500  1K  2K  4K  8K  16K
```

Gain:

```text
-12.0 .. +12.0 dB
step 0.5 dB
```

El Q conceptual es de banda de una octava (`~1.4142`) y su mapping exacto al
backend se sella en F06 mediante las pruebas de respuesta ya exigidas por §75.
La UI no conoce la conversión backend.

Si una banda queda por encima/fuera de Nyquist para el rate efectivo:

```text
saved value is preserved
runtime row/band becomes inactive with explicit reason
Signal Truth reports the inactive/adapted processing fact
no silent clamp
```

## 336.2 Surface

```text
Equalizer                               [ On ]
Shape the playback sound

10 vertical bands

Presets  [Flat] [Warm] [Vocal] [Bass Lift] [...]
Preamp   ━━━━━━━━━━━  0.0 dB

[Reset]                        [Open Advanced EQ >]
```

## 336.3 Presets

`Flat` es canónico: todos 0 dB.

Los presets con voicing (`Warm`, `Vocal`, `Bass Lift`) deben residir en un
asset/versioned factory-preset document con arrays explícitos. No inventar
curvas dentro de QML.

Gate de cierre CANON-UI-03:

```text
factory preset curves reviewed/versioned
OR non-Flat chips hidden
```

Manual band edit -> `Custom`.

Bypass conserva bandas, preamp y profile selection.

Reset:

```text
bands -> Flat
preamp -> 0
enabled state unchanged
```

## 336.4 Live interaction

No recompilar indiscriminadamente el pipeline por cada pixel.

```text
drag:
  presentation draft updates immediately
  preview updates are coalesced/bounded if runtime supports it

release:
  validate
  compile/prepare
  commit atomically

failure:
  rollback runtime
  keep editable draft + error
```

Si live parameter mutation segura no existe, aplicar sólo al release.

---

# 337. ADVANCED EQUALIZER R9 — CONSERVA TODO EL AUDIO LAB ÚTIL

El diseño canónico cambia la **superficie**, no elimina features del histórico
Audio Lab.

`AdvancedEqualizerPopup` es un popup grande/responsive sobre la misma
`ProcessingGraph` authority.

Tabs/sections mínimas:

```text
Graphic
Parametric
Convolution / FIR
Signal / Resampling
Profiles
```

Capability-gated extras derivados de ProcessingNodeKind:

```text
Channel / polarity / delay
Crossfeed
Loudness
Dither
Limiter [FUTURE RESERVED; hidden until typed node/backend + evidence exists]
```

## 337.1 Parametric

Hasta 64 bandas según el contrato de dominio; UI inicial puede presentar 12
filas visibles/configurables y permitir añadir hasta el máximo autorizado.

Campos:

```text
enabled
type
frequency
gain
Q
channel/target where supported
```

## 337.2 Convolution/FIR

Preservar:

- managed IR assets;
- hash/metadata;
- explicit rate policy;
- import/validation;
- latency display.

## 337.3 Explicit resampling

Preservar las policies del plan DSP. Nunca activar automáticamente.

## 337.4 Draft transaction

La semántica histórica de Audio Lab se conserva:

```text
Edit Draft
-> Validate
-> Preview [if supported]
-> Apply/Commit

or

Discard
```

No mutar `ProcessingGraph` live nodo por nodo desde QML.

## 337.5 Profiles

Persistir por IDs estables.

Per-output association usa `stable_device_id`/destination identity, **nunca**
display name.

Funciones:

```text
Create / Rename / Duplicate / Delete
Import / Export
Set default
Associate per-output
A/B
Bypass
Reset
```

---

# 338. AUDIO ENGINE POPUP R9 — REFRACTOR IN-PLACE

Archivo existente:

```text
src/michi/presentation/qml/player/AudioEnginePopup.qml
```

Authority/adaptor existente:

```text
src/michi/presentation/audio_engine_bridge.py
```

**No crear `AudioEngineViewModel` paralelo.**

Preservar del preimage:

```text
live bindings
selectionAllowed
selectionAction
selectionBlocker
switching
selectedEngineId
activeEngineId
fallbackFrom
statusSummary
keyboard skip of disabled rows
async availability probes off UI thread
```

Añadir sólo presentación:

```text
quickSubtitle
iconType
focusReturnTarget
canonical card geometry
```

Copy recomendado:

```text
Qt Multimedia  / System media framework
GStreamer      / Flexible media pipeline
MPD            / Music Player Daemon
```

Ese copy debe ser proyectado por el bridge o por metadata declarativa de
presentación centralizada; no reconstruir backend policy en QML.

Status matrix:

```text
active     -> Active badge
selected != active with fallback -> Preferred
switching  -> Switching…
blocked    -> visible blocker
unavailable-> Not available
```

---

# 339. SIGNAL TRUTH POPUP R9 — PATH HI-FI + CURRENT PROOF LIMITS

## 339.1 Current repo truth

A `aa8a8d3`, el repo ya tiene:

```text
SignalTruthRecorder
AudioOutputBridge.signalPath
SignalTruthPanel.qml
verdict labels:
  Direct path
  Direct · container adapted
  Resampled
  Channel remix
  Processing active
  Output mismatch
  Not verified
```

No hay autoridad actual para mostrar `Bit-perfect playback`.

Por tanto el mockup con banner verde **es future-state** hasta que M11.5/proof
authority lo demuestre.

## 339.2 Presentation migration

Fase inicial:

```text
existing SignalTruthRecorder
-> read-only projection
-> SignalTruthPopup
```

F03/F11 puede extraer un `SignalTruthBridge`/read model dedicado si elimina
acoplamiento con AudioOutputBridge, pero sigue siendo projection-only.

No crear un segundo recorder/proof engine.

## 339.3 Path

```text
Source
Decode
Processing
Output
DAC / Device
```

Nodos adicionales sólo si realmente existen:

```text
DSD packing
DSD->PCM
Convolution
SRC
Volume
Transport
```

## 339.4 Configuration affordance contract

Cada node lleva opcionalmente:

```text
configAction: NONE | OPEN_ENGINE | OPEN_PROCESSING | OPEN_OUTPUT | OPEN_DEVICE_SETUP
```

Renderizar sliders/chevron **sólo si configAction != NONE**.

Routing:

```text
Source       -> NONE
Decode       -> OPEN_ENGINE only when backend exposes relevant policy
Processing   -> OPEN_PROCESSING (Equalizer/Advanced EQ)
Output       -> OPEN_OUTPUT (AudioOutputPopup or deep output settings)
DAC/Device   -> OPEN_DEVICE_SETUP
```

No mostrar un control falso para cumplir el mockup.

Al navegar a otra quick surface:

```text
close SignalTruthPopup
open target popup / navigate settings
```

Nunca solapar.

---

# 340. AUDIO OUTPUT POPUP R9 — REFRACTOR IN-PLACE, RECOVERY INTACT

Archivos productivos actuales:

```text
AudioOutputPopup.qml
audio_output_bridge.py
AudioOutputSettingsSection.qml
DacDeviceCard.qml
```

**No crear `AudioOutputViewModel` paralelo.**

## 340.1 Canonical sections

```text
SYSTEM
EXTERNAL AUDIO
BUILT-IN / LOCAL AUDIO
MICHI STREAM          [only when adapter has rows]
DISPLAY AUDIO
OTHER AUDIO           [conditional fallback for other_audio]
```

No ocultar playback-capable `other_audio` sólo porque el mockup no lo muestra.

## 340.2 Compact projection

Agregar campos presentation-only sin romper Settings:

```text
quickSubtitle
iconType
activeLabel
```

Conservar los campos diagnósticos existentes (`statusLabel`,
`capabilityEvidenceLabel`, qualification data, etc.) para Settings/cards.

## 340.3 Selected vs active

```text
radio / selected card = user selected preference
active/playing badge  = actual committed route
```

Durante handover:

```text
old output stays Active until commit
target shows Connecting…
commit -> active transfers
failure -> old route remains/restores
```

## 340.4 Failure/recovery — MUST PRESERVE

El popup actual ya muestra:

```text
failureTitle
recoveryActions
Try Compatible Direct
Use Shared
Cancel
```

La refacción visual no puede eliminar esta capacidad.

Recovery rows se muestran debajo del fallo, con el mismo explicit-user-intent
semantics vigente.

## 340.5 Display Audio expansion — MUST PRESERVE

Conservar:

```text
displayAudioExpanded
collapsed group row with count + chevron
expanded child outputs
```

El section header no debe convertirse en Button salvo el row de expansión.

## 340.6 Footer

`Audio Output Settings` se rediseña como footer navigation row:

```text
gear | Audio Output Settings | >
```

pero conserva `settingsRequested()`.

---

# 341. SHARED QML COMPONENTS R9 — SIN DUPLICAR PRIMITIVES/THEME

Targets permitidos:

```text
src/michi/presentation/qml/components/
  MichiPopupShell.qml
  MichiSectionLabel.qml
  MichiSelectableRow.qml
  MichiRadioIndicator.qml
  MichiPopupFooterAction.qml
  MichiEqSlider.qml
  MichiPresetChip.qml
  MichiSignalNode.qml
  MichiConfigureAffordance.qml
```

Reutilizar existentes:

```text
primitives/MichiIcon.qml
controls/MichiIconButton.qml
components/MichiStatusChip.qml [si existe en preimage]
MichiGlassSurface
MichiText
MichiFocusRing
theme singletons existentes
```

**No crear:**

```text
components/MichiIcon.qml
theme/MichiColors.qml
theme/MichiMetrics.qml    [ya existe]
theme/MichiMotion.qml     [ya existe]
```

`MichiPopupShell` sólo unifica presentation:

- background/glass;
- title/subtitle;
- focus restoration;
- anchor placement;
- close policy;
- safe margins;
- motion.

No contiene audio/business logic.

---

# 342. BRIDGES / READ MODELS R9 — REUSE FIRST

Authority chain:

```text
domain/application service
-> existing bridge/read projection
-> QML
```

Reuse:

```text
AudioEngineBridge     -> AudioEnginePopup
AudioOutputBridge     -> AudioOutputPopup + current Settings
SignalTruthRecorder   -> SignalTruth read projection
```

New only where absent:

```text
AudioProcessingBridge       [projection/actions over AudioProcessingService]
SignalTruthBridge optional  [projection-only extraction if needed]
MichiStreamOutputAdapter    [read/action adapter over Michi Link authority]
```

No generic `AudioEngineViewModel`/`AudioOutputViewModel` alongside existing
bridges.

QML may own only ephemeral presentation state.

---

# 343. CROSS-SURFACE TRUTH R9

## 343.1 EQ -> Signal Truth

Basic EQ:

```text
Processing
Graphic EQ · 10 bands
Preset Custom/Flat/...
Preamp X.X dB
```

Advanced:

```text
Processing
Parametric EQ · N filters
Convolution/FIR if active
Resampling if active
Headroom/preamp
```

## 343.2 Audio Output -> Signal Truth

Actualizar Output/DAC nodes **después del committed route**, no al click.

## 343.3 Audio Engine -> Signal Truth

Actualizar engine/decode projection después de committed handover.

## 343.4 DSD/DoP

Preservar source/transport distinction:

```text
DSD source
DoP packing
PCM carrier [carrier only]
device interpretation/evidence
```

## 343.5 Bypass

EQ/DSP bypass conserva profile state y Signal Truth muestra bypass explícito.

---

# 344. AP2-F11 R9 — WORK PACKAGES RECONCILIADOS

```text
CANON-UI-00  exact-preimage/repository seal
CANON-UI-01  shared popup shell + row components using existing theme
CANON-UI-02  NowPlaying slot migration
CANON-UI-03  EqualizerPopup + factory preset asset gate
CANON-UI-04  AdvancedEqualizerPopup + AudioLab feature migration
CANON-UI-05  AudioEnginePopup visual refactor in-place
CANON-UI-06  SignalTruthPopup projection/config routing
CANON-UI-07  AudioOutputPopup visual refactor + composite destinations
CANON-UI-08  accessibility/golden/visual regression
CANON-UI-09  cross-surface truth + rollback adversarial seal
```

Dependency nuance:

```text
AudioEngine visual refactor:
  can be done as normal UI maintenance if separately authorized pre-Phase2

AudioOutput visual refactor:
  can be done as normal UI maintenance if semantics/recovery remain unchanged

NowPlaying R8 activation:
  MUST NOT expose dead Equalizer/SignalTruth/Michi Stream affordances

Equalizer/Advanced EQ:
  require DSP domain/runtime gates

future proof verdicts:
  require M11.5/F03 proof authority

Michi Stream rows:
  require Michi Link/output adapter + handover authority
```

No partial UI pretending future capability exists.

---

# 345. RESPONSIVE / ACCESSIBILITY / PERFORMANCE R9

Current NowPlaying preimage uses:

```text
compact = width < 1320
narrow  = width < 980
outputZone preferred width = 286 compact / 330 normal
button slots currently 34 px
```

Do not replace these thresholds silently with `MichiBreakpoints` during popup
work.

Final R8 may migrate buttons to `MichiMetrics.controlMedium` (36 px) only if
goldens prove the geometry remains correct.

Popup preferred/min widths:

```text
Equalizer basic       440 / 420
Audio Engine          360 / 320
Signal Truth          440 / 400
Audio Output          380 / 340
Advanced EQ           760 / 680
```

Keyboard:

```text
Esc / click-outside close
Tab/Shift+Tab focus traversal
Enter/Space activate
Up/Down selectable rows
```

Preserve reduced motion/high contrast via existing `MichiAccessibility`.

Performance:

```text
no hardware enumeration on UI thread
no per-sample Python DSP
bounded/coalesced live EQ preview
lazy-load Advanced EQ
no aggressive polling
```

---

# 346. SUPERSESSION MATRIX R9

| Histórico | R9 |
|---|---|
| DAC Quick button | eliminado; Audio Output universal |
| Network/Michi Stream button | eliminado; Michi Stream section |
| Signal Path quick button | eliminado; quality capsule -> Signal Truth |
| Engine migration only to Settings | revertido; quick Engine stays |
| settingsButton/equalizer icon -> Settings | migra a Equalizer when DSP is real |
| AudioProcessingPopup summary | Equalizer basic |
| AudioLabView CORE | AdvancedEqualizerPopup CORE; features preserved |
| SignalPathPopup + separate SignalTruth | one SignalTruthPopup |
| new theme/color files | prohibited; existing theme reused |
| SVG-only icon rule | superseded; extend current Canvas MichiIcon |
| new AudioEngine/Output ViewModels | prohibited duplication; reuse bridges |

Historical domain/evidence/rollback rules survive unless explicitly superseded.

---

# 347. TEST PLAN R9 — ADDITIVE TO CURRENT GATES

NowPlaying:

```text
test_r8_grid_exact_slots
test_equalizer_replaces_settings_slot_only_when_feature_ready
test_queue_moves_to_row0_col3
test_engine_slot_and_icon_unchanged
test_quality_badge_becomes_accessible_button
test_output_moves_to_row1_col2
test_spacer_remains_empty
test_only_one_audio_popup_open
```

Audio Engine:

```text
existing live-binding tests remain green
selectionAllowed/selectionBlocker preserved
selected_vs_active
switching/fallback
focus_return
canonical icons/subtitles
```

Audio Output:

```text
existing recovery-action tests remain green
display expansion preserved
other_audio never silently disappears
selected_vs_active/connecting/rollback
iconType comes from projection, not name parsing
stream-cat only for Michi Stream rows
```

Signal Truth:

```text
current repo never renders bit-perfect without new proof
verdict projection generation-safe
config affordance capability-gated
output updates after commit
DSP/DSD/DoP facts explicit
```

EQ:

```text
10 fixed centers
domain maps to PreampNode + ParametricEqNode
no GraphicEqNode fork
range/step
bypass preserves draft
manual -> Custom
preset asset versioned
Nyquist-inactive band explicit
same slider tokens as playback
live update bounded
rollback on failed apply
```

---

# 348. GOLDEN / VISUAL REGRESSION R9

Goldens:

```text
nowplaying_preimage_aa8a8d3.png
nowplaying_r8_idle.png
equalizer_flat.png
equalizer_custom.png
advanced_eq_parametric.png
advanced_eq_convolution.png
audio_engine_active.png
audio_engine_fallback.png
signal_truth_current_not_verified.png
signal_truth_future_verified.png
signal_truth_dsp.png
signal_truth_dsd_dop.png
audio_output_local_dac.png
audio_output_failure_recovery.png
audio_output_display_collapsed.png
audio_output_display_expanded.png
audio_output_michi_stream.png
```

Visual diff checks:

- existing theme tokens;
- no duplicate color drift;
- icon optical bounds;
- hover/focus/pressed;
- current NowPlaying geometry;
- popup safe positioning on Plasma Wayland.

---

# 349. CONTEXT PACK R9

Every F11 task loads:

```text
BIBLIA A
BIBLIA B
AP2-F11
§§314–330
§§331–380
```

Surface packs:

```python
CANONICAL_UI_CONTEXT_R9 = {
  "nowplaying": (321,331,332,333,334,335,345,347,348,351,352,353,358,359,360),
  "equalizer":  (333,334,336,337,341,342,343,347,348,352,357,358,359,360),
  "engine":     (321,333,334,335,338,341,342,347,348,351,352,353,354,358,360),
  "signal":     (319,333,334,339,341,342,343,347,348,351,354,355,357,358,360),
  "output":     (317,318,321,333,334,335,340,341,342,343,347,348,351,352,353,354,356,358,360),
}
```

---

# 350. PRECEDENCE R9 — UI CANONICAL

```text
current repository facts / frozen authorities
-> phase gates
-> §§351–380 repo-context corrective
-> §§331–350 canonical design
-> older UI blueprints
```

`UI MAY PRESENT TRUTH; UI MUST NOT CREATE TRUTH`.

---

# 351. CURRENT REPOSITORY DELTA — WHAT ALREADY EXISTS

At `aa8a8d3`:

| Target R9 | Current reality |
|---|---|
| Audio Engine opener | exists |
| AudioEnginePopup | exists, live-bound, keyboard-aware |
| AudioEngineBridge | exists, async probes + coordinator delegation |
| Audio Output opener | exists |
| AudioOutputPopup | exists, grouped, scroll-bounded, recovery actions |
| AudioOutputBridge | exists, local authority projection + signal path |
| Audio Output Settings | exists, advanced path/profile/recovery UI |
| quality capsule | exists but static |
| SignalTruthPanel | exists, compact read-only |
| Equalizer opener icon | icon exists but currently opens Settings |
| Equalizer runtime popup | absent |
| Advanced EQ popup | absent |
| `audio_processing_bridge.py` | absent at inspected path |
| Michi Stream rows in output | absent |
| shared theme system | mature/existing |
| relevant icon framework | mature/existing |

Implementation strategy = evolve, not rebuild.

---

# 352. CURRENT THEME CONTRACT — NON-DUPLICATION SEAL

KILLCRITIC:

```text
create MichiColors.qml             FAIL
recreate MichiMetrics.qml          FAIL
recreate MichiMotion.qml           FAIL
hardcode alternate EQ gradient     FAIL
ignore highContrast/reducedMotion  FAIL
```

If a missing semantic token is truly required, add the **smallest semantic
alias** to the existing appropriate singleton and migrate both old/new consumers
where justified.

---

# 353. CURRENT ICON CONTRACT — MINIMUM DELTA

Existing icons that already meet the canonical direction:

```text
equalizer
audio-output        # studio monitor speaker
audio-engine        # chip/wave
settings
queue
cat
```

Do not redraw these unless a golden/user review identifies a defect.

New icons are appended to existing `MichiIcon.qml`, with Canvas geometry and the
same 24-unit coordinate system/stroke.

`stream-cat` is separate from `cat` to avoid changing unrelated branding.

---

# 354. EXISTING POPUP INVARIANTS — PRESERVE DURING RESTYLE

## AudioEnginePopup

Must retain:

- live projection while open;
- disabled/unavailable skip in keyboard navigation;
- visible switch blocker;
- Active/Preferred/Switching semantics;
- no provider I/O in QML/UI thread.

## AudioOutputPopup

Must retain:

- grouping/scroll bounds;
- keyboard navigation;
- focus return;
- `failureTitle`;
- `recoveryActions`;
- explicit Shared/device intents;
- display expand/collapse;
- settings footer intent;
- no hidden fallback.

These are functional contracts, not styling details.

---

# 355. SIGNAL TRUTH CURRENT/FUTURE STATE SEPARATION

Current allowed headline vocabulary comes from existing evidence, e.g.:

```text
Direct path
Direct · container adapted
Resampled
Channel remix
Processing active
Output mismatch
Not verified
```

Future-only until proof authority lands:

```text
Bit-perfect playback
Exclusive verified
Native DSD preserved
DoP verified end-to-end
```

A golden may show future verified states, but product code at current baseline
must not surface them as current truth.

---

# 356. MICHI STREAM OWNERSHIP BOUNDARY

`AudioOutputPopup` is a unified **presentation**, not permission to merge local
ALSA devices and network endpoints into one registry.

Recommended composition:

```text
AudioOutputBridge
  -> local rows/actions (current authority)

MichiStreamOutputAdapter
  -> Michi Link endpoint rows/actions (future authority)

AudioDestinationProjection
  -> presentation-only concatenation/grouping
  -> AudioOutputPopup
```

Common row schema:

```text
destinationId
authorityKind: local | michi_stream
displayName
quickSubtitle
iconType
selected
active
available
actionEnabled
status
```

Dispatch by authorityKind.

No network discovery inside QML.
No remote endpoint inserted into `AudioDeviceRegistry` merely to reuse a popup.

---

# 357. DSP / ADVANCED EQ AUTHORITY CLOSURE

Basic and Advanced EQ are editors over the same:

```text
ProcessingProfile
ProcessingGraph
ProcessingPlan
AudioProcessingService
runtime executor
```

No second DSP state.

Historical AudioLab capabilities that must survive the surface migration:

```text
preamp/headroom
PEQ
FIR/convolution
explicit resampling
profiles
draft validation
preview
commit/discard
latency/evidence
```

Additional node kinds appear only when their F06 capability exists.

---

# 358. STAGED ACTIVATION — WHAT MAY CHANGE NOW VS LATER

## NOW / current baseline maintenance

Allowed only under the active non-Phase2 authority and independent review:

```text
visual restyle AudioEnginePopup
visual restyle AudioOutputPopup
add presentation-only iconType/quickSubtitle
add missing Canvas icons
preserve every existing signal/action/test
```

Not allowed under Phase2 while F00 locked:

```text
DSP runtime
Advanced EQ authority
new proof authority
DSD/DoP runtime
network output authority
schema mutation for Phase2
```

## R8/R9 activation point

Do not perform the NowPlaying slot swap until all newly visible controls are
functional:

```text
Equalizer slot -> working basic EQ
quality capsule -> working SignalTruthPopup
Audio Output -> existing working popup
Audio Engine -> existing working popup
Queue -> existing working queue
```

Michi Stream section may appear later conditionally without adding a new button.

---

# 359. AMBIGUITY CLOSURE TABLE

| Ambigüedad detectada en R8 | Resolución R9 |
|---|---|
| new color/token files vs existing theme | reuse existing theme only |
| SVG icon requirement vs Canvas icon engine | extend existing Canvas MichiIcon |
| new AudioEngineViewModel vs existing bridge | reuse AudioEngineBridge |
| new AudioOutputViewModel vs existing bridge | reuse AudioOutputBridge |
| System Output always jack | dynamic only with evidence; generic fallback |
| Michi Stream ownership | separate adapter; presentation merge only |
| Other Audio omitted | conditional `OTHER AUDIO` preserved |
| output recovery missing from mockup spec | mandatory preserved |
| display collapse behavior unspecified | preserve current expand/collapse |
| config glyph on every Signal Truth node | capability/configAction gated |
| Bit-perfect banner looks current | explicitly future-only until proof |
| basic Graphic EQ domain type unclear | fixed editor over ParametricEqNode |
| old AudioLab features risked loss | migrated into Advanced EQ |
| EQ preset curves unspecified | versioned asset gate; no QML invention |
| slider palette hardcoded incorrectly | exact current playback tokens |
| popup manager risked global authority | local presentation exclusivity |
| all UI deferred vs existing popup restyle | staged maintenance vs F11 activation |
| stale repository SHA/state | reconciled to `aa8a8d3` |

---

# 360. FINAL KILLCRITIC R9 — RELEASE CONDITIONS FOR THE PLAN ITSELF

The plan is internally acceptable only if all are true:

```text
[ ] current repo head documented as audit snapshot, not future baseline
[ ] M11.4 tooling complete / physical execution incomplete distinction preserved
[ ] M11.5 not started
[ ] Phase2 spec must be versioned before implementation
[ ] no duplicate theme stack
[ ] no duplicate icon system
[ ] no duplicate Engine/Output bridges/viewmodels
[ ] existing recovery/focus/keyboard behavior preserved
[ ] no false bit-perfect current-state UI
[ ] Michi Stream not inserted into local registry by convenience
[ ] basic EQ maps to existing DSP graph
[ ] Advanced EQ retains AudioLab functional scope
[ ] exact playback slider palette reused
[ ] NowPlaying migration is delta, not rewrite
[ ] no dead affordance ships before its authority exists
[ ] F00 remains locked until inherited gates really close
```

Any failure above -> `STOP_SPEC_AMBIGUOUS` / amend the Bible before code.

<!-- MICHI_PHASE2:CANONICAL_POPUPS_R9:END -->
<!-- MICHI_PHASE2:CANONICAL_POPUPS_R1:END -->

---

# 361. REPOSITORY DELTA R10 — `main @ aa8a8d3`

Audit head:

```text
repository   pitydah/michi-music-player
branch       main
head         aa8a8d3a884f465766a85313417262195089fac2
date         2026-09-28T02:42:11Z
message      fix(dac): qualify cold output handovers
```

El delta desde `7bd4f5a` no es cosmético. El runtime de output ahora tiene una
semántica de handover más fuerte que R9 debe heredar:

```text
select B
-> B puede quedar selected inmediatamente
-> si falta evidencia de tuple, qualification async bounded
-> A permanece accepted/playing/active mientras la qualification no cruza
   el destructive boundary
-> READY candidate B NO es active todavía
-> B sólo se vuelve active después de media acceptance/commit
-> un resultado B tardío pierde contra una selección C posterior
-> timeout / busy / inconclusive / device loss preservan A
```

Nuevos gates productivos heredados:

```text
NDP-13 cold B qualifies before live handover
NDP-14 typed qualification failure preserves A
NDP-15 late B completion cannot beat newer C
NDP-16 B loss during qualification preserves A
```

Audio Phase 2 y `AudioOutputPopup` **consumen** esta semántica. No crean otro
handover coordinator local.

---

# 362. AUDIO OUTPUT R10 — STATE MACHINE DE PRESENTACIÓN SOBRE HANDOVER REAL

El popup debe representar tres identidades distintas cuando existan:

```text
selectedDestination   user intent
activeDestination     committed/audible runtime truth
pendingDestination    candidate under prepare/qualification/acceptance
```

Para local DAC, `selected` y `active` ya vienen de `OutputSessionService` /
`AudioOutputBridge`. La UI no deduce ownership.

## 362.1 Matriz

| Runtime | B selected | A active | B row | A row |
|---|---:|---:|---|---|
| before switch | no | yes | normal | `Playing` |
| ACQUIRING/CONFIGURING B | yes | yes | `Preparing…` | `Playing` |
| B READY, predecessor still owns receipt | yes | yes | `Ready · awaiting handover` | `Playing` |
| destructive boundary crossed, B not accepted | yes | no | `Switching…` | no active badge |
| B accepted/committed | yes | no | `Playing` | normal |
| typed B failure before destructive loss | yes | yes | error/preferred intent | `Playing` |
| B disappears | yes | yes when preserved | `Unavailable` | `Playing` |
| B stale because C newer | no/obsolete | yes until C commit | no stale activity | `Playing` |

No fabricar `Active` a partir de radio selection.

## 362.2 Bridge delta

No destruir `statusLabel` usado por Settings. Agregar projection fields
presentation-only:

```text
quickStatus
pending
pendingReason
iconType
quickSubtitle
```

La fuente sigue siendo `audio_output_bridge.py`.

---

# 363. VOLUME PRESENTATION R10 — FIXED/UNITY ES SEMÁNTICA, NO DECORACIÓN

`aa8a8d3` retiró el label visual permanente `Fixed / Unity`.

Contrato:

```text
VolumePolicy.FIXED
    -> slider no ajustable
    -> porcentaje visual oculto
    -> accessibility/diagnostics conserva "Fixed / Unity"

adjustable gain
    -> percentage visible
```

El mockup canónico donde aparece `100%` representa un estado **adjustable**.
No reintroducir `100%` o `Fixed / Unity` para Direct FIXED sólo para igualar una
captura.

Esto no cambia la posición ni el icono de Audio Output.

---

# 364. MICHI LEGACY AUDIT SNAPSHOT — CANTERA, NO AUTHORITY

Repo inspeccionado:

```text
repository   pitydah/michi-legacy
branch       main
head         2332a45c7a645d645e4b4882ef30aedeb2d7ef07
```

Los commits de audio estudiados son ancestros del HEAD actual, pero Legacy no
es autoridad del Player moderno. Regla:

```text
LEGACY_CODE != DROP-IN CODE
LEGACY_TEST_PASS != CURRENT_PLAYER_EVIDENCE
LEGACY_PROFILE_NAME != AUDIOPHILE_PROOF
```

Toda recuperación se clasifica:

```text
A PORT/ADAPT      algoritmo o contrato útil, reescrito contra autoridades actuales
B TEST SEED       invariant/test concept reusable
C UX SEED         interaction/information architecture only
D REJECT          architecture/semantics unsafe for current Player
```

---

# 365. LEGACY RECYCLE LEDGER — RESULTADO

| Legacy artifact | Clase | Destino R10 | Decisión |
|---|---|---|---|
| `core/equalizer_service.py` | A/B | F04/F06 service semantics | **PORT PATTERN**, not class |
| `tests/architecture/test_eq_state_requires_backend_readback.py` | B | DSP authority gates | **PORT invariant** |
| `tests/integration/test_equalizer_apply_readback.py` | B | DSP integration tests | **PORT behavior** |
| `audio/eq_presets.py` | A | factory preset asset seed | **PORT data after review** |
| `audio/eq_biquad.py` | A/B | pure biquad math + response tests | **PORT algorithm, remove NumPy core dependency** |
| `audio/eq_convert.py` | A/C | import/preview conversion | **PORT as lossy utility only** |
| `audio/eq_autoeq.py` local parser/cache | A/C | future headphone preset importer | **PORT parser concept** |
| `audio/eq_autoeq.py` downloader URL | D | none | **REJECT until fresh upstream/provenance review** |
| `ui_qml_bridge/eq_bridge.py` | C/D | API idea only | **DO NOT COPY implementation** |
| `EqualizerPage.qml` | C | Advanced EQ interaction ideas | **UX SEED** |
| `EqualizerPresetBrowser.qml` | C | Profiles tab | **UX SEED** |
| `EqualizerGraph.qml` | C | optional response preview | **UX SEED, recolor/redesign** |
| `DSPChainPage.qml` | C/D | processing chain concept | **UX SEED, not state logic** |
| `audio/pipeline_factory.py` EQ snippets | A/D | backend research | **FACTORY CANDIDATES ONLY** |
| `audio/pipeline_factory.py` DoP path | D | none | **REJECT** |
| `OutputProfilesPage.qml` | C | requested/effective/fallback UX | **UX SEED** |
| `OutputCapabilityView.qml` | D/C | none as truth | **DO NOT COPY capability claims** |
| `home_audio_bridge.py` | A/C | future Michi Stream adapter concepts | **PATTERN ONLY** |
| test-authority T0/T1/T2/T3 docs | B | AP2 gate taxonomy | **ADAPT concepts** |

---

# 366. EQUALIZER R10 — RECYCLE WITHOUT IMPORTING LEGACY AUTHORITY

Legacy aporta dos modelos distintos:

```text
EqBridge quick model         10 bands
EqualizerService/backend     31 bands
```

Además, Legacy contiene una contradicción real:

```text
ui_qml_bridge/eq_bridge.py
  GRAPHIC_BAND_COUNT = 10

audio/eq_presets.py
  built-ins = 31 values

applyPreset()
  can send 31 to backend
  but local bridge accepts internal 10 only
```

Por tanto `EqBridge` **no se copia**.

## 366.1 Basic EQ canónico

La UI aprobada permanece 10-band:

```python
BASIC_EQ_CENTERS_HZ = (
    31.25, 62.5, 125.0, 250.0, 500.0,
    1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
)
BASIC_EQ_LABELS = ("31", "62", "125", "250", "500", "1K", "2K", "4K", "8K", "16K")
```

```text
UI gain range  -12 .. +12 dB
step            0.5 dB
```

Se proyecta al `ParametricEqNode` canónico como 10 `PEAK` filters; no introduce
`GraphicEqNode`.

## 366.2 Advanced graphic canónico

Legacy aporta una grilla ISO de 31 bandas útil:

```python
ADVANCED_GRAPHIC_31_HZ = (
    20, 25, 31, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000,
)
```

También se expresa como PEQ/profile semantics o como strategy backend validada;
la UI no crea una segunda authority.

Advanced Graphic permanece opcional/capability-gated.

---

# 367. FACTORY PRESETS R10 — MIGRATION CON PROVENANCE

Legacy trae datos concretos de 31 bandas:

```text
Flat
Rock
Pop
Jazz
Classical
Bass Boost
Vocal Boost
Treble Boost
```

y PEQ seeds:

```text
Rock / Pop / Jazz / Classical
```

Esto es mejor que inventar curvas dentro de QML.

## 367.1 Regla de migración

Crear en el Player moderno un asset versionado, por ejemplo:

```text
src/michi/resources/audio/factory_eq_presets_v1.json
```

Cada preset incluye:

```json
{
  "schema": 1,
  "id": "bass_lift",
  "display_name": "Bass Lift",
  "mode": "advanced_graphic_31",
  "frequencies_hz": [20, 25, 31],
  "gains_db": [8.0, 7.5, 7.0],
  "source_provenance": "michi-legacy/audio/eq_presets.py",
  "review_state": "REVIEWED"
}
```

No importar el repo Legacy en runtime.

## 367.2 Mapping al mockup

```text
Flat       -> direct reviewed migration
Bass Lift  -> seed from Legacy "Bass Boost", renamed only after review
Vocal      -> seed from Legacy "Vocal Boost", renamed only after review
Warm       -> NO equivalent exacto en Legacy
```

`Warm` se oculta hasta que exista una curva explícita y revisada.

No afirmar que estos presets son target curves científicas. Son factory voicings.

---

# 368. BIQUAD / RESPONSE R10 — QUÉ RECICLAR DE `eq_biquad.py`

Legacy tiene fórmulas RBJ útiles para:

```text
Peak
LowShelf
HighShelf
LowPass
HighPass
Notch
BandPass
frequency-response evaluation
```

Se pueden portar como módulo puro con estas correcciones:

```text
1. no unknown filter -> identity silencioso
2. unknown filter -> typed validation error
3. no silent clamp de freq a Nyquist
4. validation ocurre antes de coefficient generation
5. normalize/finite coefficient validation
6. deterministic float serialization for plan hashing
7. tests against known RBJ vectors
```

## 368.1 Dependency budget

El Player moderno no declara NumPy/Scipy como dependencia core.

```text
DO NOT add numpy only for EQ coefficient math.
```

`compute_biquad` se implementa con `math`.

La response preview:

```text
pure-Python bounded worker
OR future optional optimized adapter
```

Nunca calcula una curva grande en QML ni en el audio callback.

---

# 369. LEGACY READBACK-FIRST — INVARIANTE QUE SÍ DEBE SOBREVIVIR

La mejor pieza de Legacy no es una clase: es la secuencia:

```text
validate
-> apply backend
-> readback
-> compare
-> publish effective state
-> persist
-> event
```

Legacy además tenía tests específicos de:

```text
READBACK_MISMATCH
BACKEND_APPLY_FAILED
state unchanged after failed readback
backend/profile EQ capability conflict
```

R10 la adapta al modelo Phase2:

```text
Draft graph
-> validate
-> compile
-> runtime prepare/preroll
-> runtime evidence/readback
-> commit
-> AudioProcessingState.active_profile/revision
-> persist committed revision
```

**Diferencia importante:** Legacy permitía `LOCAL_ONLY ACCEPTED` sin player. En
Phase2 eso no se presenta como estado efectivo:

```text
offline edit -> DRAFT SAVED
runtime applied -> FALSE
Signal Truth -> no active processing claim
```

No mezclar draft con effective state.

---

# 370. LEGACY EQ QML — UX QUE SE RECICLA, DISEÑO QUE NO

De `EqualizerPage.qml`:

**Reciclar:**

```text
graphic vs parametric separation
bypass/reset
preamp
backend/capability warning
bit-perfect conflict warning pattern
preset browser
import/export
keyboard/accessibility intent
```

**No reciclar:**

```text
full-page visual design
legacy colors/components
±24 dB basic range
one horizontal row per graphic band
direct QML -> old EqBridge authority
```

De `EqualizerGraph.qml`:

```text
response/shape visualization concept -> Advanced EQ only
```

No usar sus colores rojo/azul por signo en Basic EQ; el diseño canónico conserva
la paleta playback.

---

# 371. GRAPHIC↔PARAMETRIC CONVERSION — LOSSY TOOL, NEVER HIDDEN RUNTIME

`audio/eq_convert.py` es útil como cantera porque ya tiene:

```text
31-band -> sparse PEQ heuristic
PEQ -> 31-band sampled response
roundtrip shape tests
```

Pero la conversión es heurística/losy.

Contrato moderno:

```text
Switch tab for VIEW
    -> no automatic destructive conversion

User chooses "Convert to Parametric…"
    -> build candidate
    -> preview source vs converted response
    -> show error metric
    -> explicit Accept
    -> new profile revision
```

Preservar siempre el preset original.

No usar los thresholds Legacy (`0.2`, `0.15` correlation) como quality gate
audiophile. R10 exige una métrica/tolerancia definida antes de promoción.

---

# 372. AUTOEQ LEGACY — PARSER SÍ, DOWNLOADER NO TODAVÍA

Reutilizable:

```text
local cache search
model-name normalization concept
parse filters {type, frequency, gain, Q}
tests for missing model / fallback Q / filter shape
```

No reutilizar sin investigación fresca:

```text
hard-coded GitHub raw URL
assumption about upstream directory layout
license/provenance assumptions
network in core EQ path
```

Target futuro:

```text
Advanced EQ > Profiles > Headphones
Import AutoEQ file / managed provider
-> validate schema
-> normalize filter types
-> preserve upstream provenance/version
-> preview
-> save native Michi profile
```

No es requisito para AP2 CORE.

---

# 373. BACKEND DSP R10 — LEGACY COMO PROBE CANDIDATE, NO FACTORY AUTHORITY

Legacy muestra candidatos técnicos reales:

```text
volume
audioiirfilter
equalizer-nbands
audiofirfilter
audioresample
```

También demuestra que una implementación anterior usó cascadas
`audioiirfilter` para PEQ.

Esto **no** prueba disponibilidad/correctitud en el runtime moderno.

F05 debe generar `ProcessingBackendCapabilities` mediante probe controlado:

```text
strategy          candidate
gain              volume
biquad_cascade    audioiirfilter
graphic_31        equalizer-nbands [optional optimization]
fir               audiofirfilter
resample          audioresample
```

Para:

```text
convolution
balance
polarity
channel_delay
channel_map
dither
crossfeed
loudness
```

no asumir factories `michi-*`.

Cada feature necesita:

```text
chosen implementation
capability probe
parameter mapping
measured/inspected runtime
failure code
tests
```

Hasta entonces:

```text
strategy unavailable
UI hidden/disabled with reason
```

---

# 374. PROCESSING TRUTH R10 — CORRECCIONES DE SEMÁNTICA

R10 corrige tres bugs conceptuales encontrados en el plan.

## 374.1 `MIXER` y `LIMITER`

No existen como CORE hasta tener end-to-end contract. Un nombre en enum no es
capability.

## 374.2 `_changes_values`

Debe ser exhaustivo y conservador.

En particular:

```text
PEAK/shelf with gain 0               can be pass-through
LOW_PASS/HIGH_PASS/NOTCH/BAND_PASS   mutate even with gain 0
FIR/convolution                      mutate unless identity is actually proven
delay > 0                            mutates timing/sample relationship
non-identity channel map             mutates
dither != NONE                       mutates
resample to different rate           mutates
unknown future node                  assume mutation
```

No volver al fallback antiguo:

```python
return not isinstance(node, ChannelMapNode) or bool(node.output_to_input)
```

porque una identity map no es mutación y varios filtros sí lo son aunque su gain
sea cero.

## 374.3 Bypass

```text
no ACTIVE nodes != bypass proven
```

`ProcessingRuntimeSnapshot.graph_bypassed` es explícito. `UNKNOWN` /
`NOT_OBSERVABLE` nunca se transforma en `BYPASSED`.

## 374.4 Saved graph vs effective graph at Nyquist boundaries

The stored profile is immutable user intent. Runtime may need an
input-rate-specific effective graph.

```text
ProcessingProfile.graph            saved intent
        ↓
EffectiveGraphResolver(input PCM)
        ↓
EffectiveProcessingGraph           runtime candidate
        ↓
ProcessingGraphCompiler
```

Example:

```text
saved band: 20 kHz enabled
current source: 32 kHz PCM
Nyquist: 16 kHz

DO NOT:
  clamp 20 kHz -> 15.9 kHz
  delete the saved band
  fail the entire profile without explanation

DO:
  preserve saved 20 kHz band
  mark effective band INACTIVE_ABOVE_NYQUIST
  omit it from executable PEQ strategy
  expose reason in Advanced EQ and Signal Truth
```

The compiler still rejects any **enabled executable** band at/above Nyquist.
Adaptation happens before compilation and is evidence-bearing.

## 374.5 Transform dimensions are not one boolean

R10 separates:

```text
changes_sample_values
changes_rate
changes_channels
changes_timing
changes_channel_assignment
```

Signal Truth/proof consumes all dimensions.

Examples:

```text
channel delay          timing=true, sample_values=false
same-count channel swap channel_assignment=true
resample               rate=true (+ sample transform as backend evidence dictates)
PEQ                     sample_values=true
```

No proof layer may decide “unaltered” by checking only
`changes_sample_values`.

---

# 375. ADVANCED EQ R10 — SCOPE FINAL DESPUÉS DE LEGACY AUDIT

`AdvancedEqualizerPopup` conserva profundidad sin convertirse en otra authority.

Tabs:

```text
Graphic
Parametric
Convolution / FIR
Signal / Resampling
Profiles
```

## Graphic

```text
31-band ISO optional
factory/custom presets
preamp/headroom
response preview
```

## Parametric

```text
typed PEQ
add/remove/enable
Peak / shelves / LP / HP / notch / band-pass / all-pass if backend proven
frequency / gain / Q
response preview
```

## Convolution / FIR

```text
managed IR
hash
rate/channel validation
latency
explicit enable/bypass
```

## Signal / Resampling

```text
explicit resampler only
quality policy
current input/output rate
dither only if backend/node promoted
```

## Profiles

```text
factory
custom
import/export
per-output stable-id association
AutoEQ import [post-core]
A/B
draft/commit/discard
```

No mostrar:

```text
Limiter
Mixer
Crossfeed/Loudness/etc.
```

hasta que su capability end-to-end sea real.

---

# 376. MICHI STREAM — QUÉ APORTA LEGACY Y QUÉ NO

`michi-legacy/ui_qml_bridge/home_audio_bridge.py` aporta patrones útiles:

```text
sources / destinations / routes as separate concepts
coherent snapshot replacement
orphan route reconciliation
bounded retry
operation generation / stale completion fencing
offline/error projection
```

No aporta la autoridad correcta para el ecosistema actual:

```text
Home Assistant / Snapcast bridge != Michi Link
legacy receiver != current Michi Music Stream protocol
```

Portar patrones, no clase.

## 376.1 Player modern target

```text
MichiLink/Michi Control authority
-> MichiStreamOutputAdapter
-> DestinationProjection
-> AudioOutputPopup
```

Cross-authority handover requiere un contrato específico:

```text
Local A active
-> select Stream B
-> B discovery/readiness
-> prepare transfer
-> commit remote authority
-> retire local A
```

No reutilizar a ciegas `OutputSessionService` local para endpoint de red.

El popup sí comparte:

```text
selected / pending / active / failed
```

como lenguaje de presentación.

---

# 377. LEGACY TEST RECYCLING — PORTAR CONTRATOS, NO NÚMEROS VERDES

Tests Legacy valiosos como seeds:

```text
EQ readback must precede effective-state update
backend apply failure leaves effective state unchanged
readback mismatch is typed failure
preset persistence roundtrip
invalid band count/range rejected
graphic<->parametric conversion is explicit/tested
AutoEQ parser handles missing/partial fields
```

No copiar tests que escanean fuente como gate final cuando se pueda probar
behavior productivo.

## 377.1 Gate taxonomy

Legacy `Development Convergence Mode` aporta un modelo útil:

```text
T0 safety/blocking
T1 stable regressions/blocking
T2 development/advisory
T3 hardware/environment/performance/manual
```

Adaptación Phase2:

```text
AP2-T0 architecture/authority/smoke
AP2-T1 deterministic DSP/compiler/runtime unit+integration
AP2-T2 feature development/golden
AP2-T3 real GStreamer/hardware/DSD/DoP/latency/soak
```

No heredar counts ni maturity declarations de Legacy.

---

# 378. AP2 WORK PACKAGES R10 — DELTA DE IMPLEMENTACIÓN REAL

Agregar a F04–F11:

```text
DSP-LEG-01  port pure biquad math without NumPy core dependency
DSP-LEG-02  port/review factory preset dataset into versioned asset
DSP-LEG-03  adapt readback-first invariants into AudioProcessingService tests
DSP-LEG-04  optional 31-band Advanced Graphic projection
DSP-LEG-05  lossy conversion tool behind explicit preview/accept
DSP-LEG-06  AutoEQ local/native importer research [post-core]
DSP-CAP-01  GStreamer processing strategy capability probe
DSP-CAP-02  prove PEQ strategy response vs theoretical fixtures
DSP-CAP-03  prove FIR strategy + latency
UI-R10-01   aa8 handover-state projection in AudioOutputPopup
UI-R10-02   Fixed/Unity current presentation regression
UI-R10-03   current-vs-future Signal Truth copy gate
STREAM-R10  Michi Link adapter contract before Stream rows ship
```

Order:

```text
authority/domain corrections
-> pure compiler
-> capability probe
-> runtime
-> readback/evidence
-> Basic EQ
-> Advanced EQ
-> cross-surface Signal Truth
-> optional migration/import features
```

---

# 379. AMBIGUITY CLOSURE R10 — NUEVOS HALLAZGOS

| Ambigüedad | R10 |
|---|---|
| current HEAD moved after R9 | audit head -> `aa8a8d3` |
| selected output == active? | explicitly NO |
| active predecessor during async qualification | preserved and displayed |
| active can become None during destructive gap | YES, honest state |
| Fixed/Unity visual copy | hidden when gain locked; accessibility preserved |
| `MIXER` enum without class/runtime | removed from CORE |
| Limiter described but no node | reserved/hidden |
| PEQ gain=0 means no mutation for all filter types | corrected |
| empty ACTIVE evidence means bypass | corrected; explicit graph_bypassed |
| one DSP node == one Gst factory | rejected |
| invented `michi-*` factories | rejected until implemented/probed |
| `equalizer-nbands` automatically proves PEQ | rejected |
| NumPy added for biquad | rejected as CORE dependency |
| Legacy 10-band vs 31-band conflict | Basic=10; Advanced Graphic=31 |
| Legacy preset data | review + versioned migration |
| Warm preset source | absent; hide until defined |
| Legacy local-only EQ state | draft only, not effective |
| AutoEQ network downloader | deferred pending fresh upstream/provenance |
| Legacy DoP | rejected as non-DoP architecture |
| local DAC handover reused for stream | rejected; cross-authority contract required |

---

# 380. FINAL PRECEDENCE / KILLCRITIC R10

Repository state precedence:

```text
current exact task HEAD
-> V3.5 / frozen inherited authorities
-> §§361–380
-> §§314–360
-> older snapshots
```

DSP implementation precedence:

```text
typed domain
-> compiler strategy
-> capability probe
-> runtime adapter
-> runtime evidence/readback
-> Signal Truth
-> QML
```

Legacy precedence:

```text
current Player authority
-> R10 contract
-> reviewed Legacy salvage
```

Nunca:

```text
Legacy implementation
-> overwrite current authority
```

Final rejection gates:

```text
[ ] no duplicate Engine/Output authority
[ ] no second theme/icon stack
[ ] no static selected==active assumption
[ ] no handover regression vs NDP-13..16
[ ] no Fixed/Unity decorative regression
[ ] no phantom MIXER/LIMITER capability
[ ] no fictional Gst factory
[ ] no silent unknown-filter passthrough
[ ] no silent Nyquist clamp
[ ] no "no active node => bypass"
[ ] no NumPy dependency added solely for basic EQ
[ ] no Legacy DoP port
[ ] no Legacy bit-perfect label imported as proof
[ ] no local-only draft shown as effective DSP
[ ] no Michi Stream endpoint inserted into local audio registry for convenience
[ ] no Warm/Vocal/Bass Lift curve invented in QML
[ ] no dead popup affordance before authority is functional
```

Failing any item:

```text
STOP_SPEC_AMBIGUOUS
```

before production code.

<!-- MICHI_PHASE2:R10_DEEP_RECONCILIATION:END -->

---

# R11 CANONICAL EXECUTION LAYER — §§381–431

> **AGENT RULE:** productive implementation reads this layer through stable `MUST_READ_ANCHORS`. §§0–380 are supporting rationale unless an R11 packet explicitly points there.

# 381. R11 KILLCRITIC — RESULTADO Y PRECEDENCIA EJECUTABLE

<!-- MICHI_PHASE2:CONTRACT:R11-G00-PRECEDENCE:BEGIN -->
R11 changes the execution model, not merely the prose.

```text
IMPLEMENTATION AUTHORITY
1. current repository facts frozen by F00
2. inherited M11.3 + M11.4 software gates + R11.1 restricted-entry gates
3. R11 contract anchors required by active phase
4. active R11 phase packet
5. historical §§0–380 only for rationale when explicitly requested
```

Hard rules:

```text
NO_CONTEXT_NO_CODE
NO_UNREAD_CONTRACT_NO_CODE
NO_UNKNOWN_OWNER_NO_CODE
NO_FICTIONAL_FACTORY
NO_SILENT_FALLBACK
NO_LOCAL_UI_AUTHORITY
NO_TEST_APPEASEMENT
NO_DIRECT_WITH_PROCESSING
NO_PHYSICAL_CLAIM_WITHOUT_PHYSICAL_EVIDENCE
```

A code agent does NOT solve contradictions by choosing the later-looking
paragraph. It runs `phase2_context.py --mode implementation`, whose anchors are
unique and validated.

`orientation` mode is non-productive by definition.

When implementation eventually starts, F00 freezes a new exact baseline. The
audit head `8bea498b` is evidence for this specification, not a permanent
implementation base.

If current main differs from the frozen F00 baseline before productive mutation:

```text
STOP_BASELINE_DRIFT
```

and the plan must be reconciled again.
<!-- MICHI_PHASE2:CONTRACT:R11-G00-PRECEDENCE:END -->

---

# 382. CURRENT REPOSITORY TRUTH R11

<!-- MICHI_PHASE2:CONTRACT:R11-G01-CURRENT-REPO:BEGIN -->
Audited repository:

```text
pitydah/michi-music-player
main @ 8bea498b0c2838b962352e09aa70da73088ced23
```

Observed authorities that Phase2 inherits:

```text
PlaybackService                    media/playback state authority
AudioEngineService                 selected/active engine state
AudioTransportRouter               physically bound engine/port
AudioDeviceRegistry                current audio-device identity/bindings
DacQualificationService            exact ALSA qualification + cache mutation
AudioOutputProfileService          persisted output profile/selection
AudioOutputSelectionCoordinator    explicit output selection intents
OutputSessionService               current Shared/Direct output transaction
GStreamerDirectOutputExecutor      Direct execution
SignalTruthRecorder                existing PCM Direct runtime truth
VolumePolicyService                volume authority/effective result
SQLiteSettingsRepository           canonical DB lifecycle/migration/recovery
SqliteAudioOutputRepository        output profile + qualification persistence
QtAsyncCallExecutor                bounded worker -> owner-thread completion
```

Current Direct profile/pipeline invariants:

```text
HARDWARE_DIRECT / HARDWARE_DIRECT_COMPATIBLE
allow_resample   = false
allow_remix      = false
allow_processing = false
sink             = exact ALSA hardware path
```

Current output handover truth at this head:

```text
selected B may differ from active A
cold B qualification is bounded async
A stays active while safe
B READY is not active until media/backend acceptance
stale B completion loses to newer selection
typed qualification failure preserves A when predecessor still owns runtime
```

Current QML canonical names:

```text
NowPlayingBar.qml
AudioOutputPopup.qml
AudioEnginePopup.qml
```

Current composition root is:

```text
src/michi/bootstrap/__init__.py
```

Do not create `src/michi/bootstrap.py`.

Current mandatory Python dependencies do not include NumPy/SciPy. Phase2 must
not add them merely to implement basic coefficient math.
<!-- MICHI_PHASE2:CONTRACT:R11-G01-CURRENT-REPO:END -->

---

# 383. R11 CONTEXT ARCHITECTURE — LARGE SPEC, SMALL WORKING SET

<!-- MICHI_PHASE2:CONTRACT:R11-G11-PATCH-PROTOCOL:BEGIN -->
The document may be large; the agent packet must be small.

Per productive work unit:

```text
1 phase
1 explicit objective
1 bounded file set
1 red/green test cluster
1 rollback/failure contract
1 context receipt
1 commit
```

Before mutation:

```bash
python scripts/phase2_context.py \
  --phase AP2-F05 \
  --mode implementation \
  > /tmp/ap2-context.md

python scripts/phase2_context.py \
  --phase AP2-F05 \
  --receipt-json \
  > /tmp/ap2-context-receipt.json

python scripts/verify_audio_phase2_repository_alignment.py --phase AP2-F05
```

The implementation prompt should contain only:

```text
context pack
current diff
directly touched source snippets
failing focused tests
```

It should NOT retransmit the complete mega-plan.

Patch discipline:

```text
SEARCH exact symbol
READ complete owning method/class
ASSERT preimage
EDIT smallest authority surface
RUN focused gates
RUN architecture gates
INSPECT diff
COMMIT
```

Never produce a 40-file speculative patch because a phase contains 40 future
files. A phase is decomposed into numbered work units; each work unit must be
green before the next begins.

Recommended diff ceiling for ordinary work units:

```text
productive files <= 8
test files       <= 8
generated/docs   excluded from this heuristic
```

Crossing the ceiling requires the phase packet to explicitly say why atomicity
requires it.

Every patch includes a preimage guard:

```text
EXPECTED_SYMBOLS
EXPECTED_EXISTING_TESTS
EXPECTED_AUTHORITY
```

If any guard is false:

```text
STOP_PREIMAGE_DRIFT
```

No blind search/replace on stale source.
<!-- MICHI_PHASE2:CONTRACT:R11-G11-PATCH-PROTOCOL:END -->

---

# 384. AUTHORITY MAP R11 — ONE OWNER PER FACT

<!-- MICHI_PHASE2:CONTRACT:R11-G02-AUTHORITY-MAP:BEGIN -->
Authority map:

| Fact | Owner | Observers may cache? |
|---|---|---|
| accepted media / position / transport | `PlaybackService` | snapshot only |
| selected engine | `AudioEngineService` | yes, presentation |
| physically bound engine | `AudioTransportRouter` | no competing owner |
| selected output intent | `AudioOutputProfileService` persistence | projection only |
| active Direct execution | `OutputSessionService` + executor receipt | projection |
| device identity/binding generation | `AudioDeviceRegistry` | projection |
| exact tuple capability | `DacQualificationService` evidence | cache is rebuildable |
| current PCM Direct truth | `SignalTruthRecorder` | projection |
| DSP profile document | `AudioProcessingService` / repository | yes |
| effective DSP graph | runtime + `AudioProcessingService` commit | no QML authority |
| IR bytes | content-addressed asset store | metadata may persist |
| family-neutral Signal Path | `SignalPathService` projection over authorities | projection, not execution authority |
| QML selection/highlight | bridge projection | never canonical |

Prohibitions:

```text
QML never owns effective EQ state.
Bridge never owns a second profile copy.
ProcessingService never decides physical DAC identity.
Compiler never does I/O.
Runtime never changes user profile intent.
SignalPathService never commands playback.
```

Draft versus effective is explicit:

```text
DRAFT
  user edits not yet committed to runtime

EFFECTIVE
  backend readback/evidence confirmed active graph

PERSISTED
  durable profile revision

These can differ transiently and must be labeled.
```

Offline profile editing is legal, but:

```text
offline_saved = true
runtime_applied = false
```

No UI may call an offline draft “Active”.
<!-- MICHI_PHASE2:CONTRACT:R11-G02-AUTHORITY-MAP:END -->

---

# 385. OUTPUT FAMILIES R11 — CONTRACT THAT REMOVES DIRECT+DSP

<!-- MICHI_PHASE2:CONTRACT:R11-G03-OUTPUT-FAMILIES:BEGIN -->
Canonical route vocabulary:

```python
class AudioExecutionFamily(StrEnum):
    SHARED_PCM = "shared_pcm"
    DIRECT_PCM = "direct_pcm"
    MANAGED_PCM = "managed_pcm"
    NATIVE_DSD = "native_dsd"
    DOP = "dop"
```

Semantics:

```text
SHARED_PCM
  desktop/system managed sink
  processing may be active
  no Direct claim

DIRECT_PCM
  existing Stable strict/compatible path
  processing/resample/remix forbidden
  current OutputSessionService semantics preserved

MANAGED_PCM
  Michi owns an explicit processed PCM graph
  may target a specific DAC
  may contain explicit DSP/resample/remix
  never called Direct / bit-perfect

NATIVE_DSD
  DSD remains DSD through transport
  PCM DSP forbidden

DOP
  DSD payload carried in DoP PCM frames
  PCM DSP forbidden
```

Do not overload current `OutputPlan`. Introduce `ManagedPcmOutputPlan` rather
than setting `allow_processing=True` on a Direct plan.

Migration staging:

```text
Stage 0 current
  PlaybackService -> OutputSessionService [Shared/Direct]

Stage 1 F05
  processing runtime proven on SHARED_PCM / GStreamer

Stage 2 F06
  explicit MANAGED_PCM planner/executor to target a selected DAC

Stage 3 F10
  family transition coordinator for PCM/DSD/DoP
```

No cross-family change is implicit.

Conflict resolution:

```text
enable processing while DIRECT_PCM selected
  -> PROCESSING_DIRECT_CONFLICT
  -> explicit user choice to move to MANAGED_PCM

select DIRECT_PCM while processing effective
  -> DIRECT_PROCESSING_CONFLICT
  -> explicit user choice to bypass processing first
```

A route label is based on effective runtime:

```text
Direct
Direct · container adapted
Processed
Processed · resampled
Native DSD
DoP
Shared
Unknown
Contradicted
```

`Processed` is not a quality ranking; it is a factual transform state.
<!-- MICHI_PHASE2:CONTRACT:R11-G03-OUTPUT-FAMILIES:END -->

---

# 386. MANAGED PCM R11 — SPECIFIC DAC WITHOUT CORRUPTING DIRECT

Managed PCM is introduced only after F05 proves DSP on a non-Direct path.

```python
@dataclass(frozen=True, slots=True)
class ManagedPcmOutputPlan:
    plan_id: str
    stable_device_id: str | None
    binding_generation: int | None
    input_pcm: PcmSignalFormat
    working_format: str
    output_pcm: PcmSignalFormat | None
    processing_plan: CompiledProcessingPlan
    sink_factory: str
    sink_device: str | None
    explicit_resampling: bool
    explicit_remix: bool
    volume_policy: str
    evidence_refs: tuple[str, ...]
```

If `stable_device_id is None`, sink may be desktop/shared.

If a specific local DAC is targeted:

```text
stable id
-> exact current ALSA binding
-> bounded capability evidence
-> managed planner chooses terminal PCM representation
-> explicit processing graph
-> alsasink to that binding
```

The final PCM carrier policy is not source-significant-bit preservation because
DSP has changed sample values. The planner instead uses a **terminal format
policy** with current positive capability evidence. No capability matrix is
guessed.

Initial allowed terminal formats:

```text
F64/F32 are INTERNAL only
terminal integer target must be explicitly qualified
prefer no rate change unless graph contains ResampleNode
preserve channel count unless graph contains ChannelMapNode
```

Do not reuse Direct Signal Truth wording for managed playback.

This feature has an explicit rollback boundary. If managed preparation fails
before destructive replacement, keep predecessor. After destructive loss,
restore predecessor only if runtime ownership/readback proves restoration;
otherwise STOPPED + typed failure.

---

# 387. PROCESSING DOMAIN R11 — ONE GRAPH, GRAPHIC AND PARAMETRIC BOTH FIRST-CLASS

Graphic EQ is no longer forced through an artificial PEQ conversion.

```python
class ProcessingNodeKind(StrEnum):
    PREAMP = "preamp"
    GRAPHIC_EQ = "graphic_eq"
    PARAMETRIC_EQ = "parametric_eq"
    CONVOLUTION = "convolution"
    CHANNEL_DELAY = "channel_delay"
    CHANNEL_MAP = "channel_map"
    RESAMPLE = "resample"
    DITHER = "dither"
```

Core R11 excludes until separately promoted:

```text
LIMITER
MIXER
CROSSFEED
LOUDNESS
generic dynamics
```

They may appear in research appendix only.

Graphic node:

```python
class GraphicEqLayoutId(StrEnum):
    MICHI_10_V1 = "michi_10_v1"
    ISO_31_V1 = "iso_31_v1"

@dataclass(frozen=True, slots=True)
class GraphicEqNode:
    node_id: str
    layout_id: GraphicEqLayoutId
    gains_db: tuple[float, ...]
    enabled: bool = True
```

Parametric node remains typed bands.

Convolution/FIR is one core abstraction, not two competing profile nodes:

```python
@dataclass(frozen=True, slots=True)
class ConvolutionNode:
    node_id: str
    asset_id: str
    asset_sha256: str
    gain_db: float = 0.0
    enabled: bool = True
```

`audiofirfilter` is one possible executor for bounded kernels. A future
FFT-convolution backend can execute the same semantic node after capability and
performance gates.

The profile document contains intent, not backend property names.

---

# 388. GRAPHIC EQ R11 — BASIC 10 + ADVANCED 31, SAME AUTHORITY

<!-- MICHI_PHASE2:CONTRACT:R11-G09-LEGACY-RESEARCH:BEGIN -->
Research inputs are evidence, not authority.

Michi Legacy salvage:

```text
use:
  ISO 31 center-frequency list
  preset curves after review/provenance
  readback-first failure tests
  pure RBJ math concepts
  import/export UX concepts

do not use:
  Legacy EqBridge state ownership
  Legacy 10-vs-31 mismatch
  Legacy DoP
  Legacy bit-perfect labels as proof
  hard-coded AutoEQ URL assumptions
```

Fresh official GStreamer findings incorporated in R11:

```text
equalizer-nbands
  official docs: 1..64 bands
  center frequency + bandwidth + gain per band
  accepted raw formats include S16LE/F32LE/F64LE
  candidate for Graphic EQ and peak-style bands

audioiirfilter
  generic coefficient IIR
  F32LE/F64LE
  rate-changed callback is called from streaming thread and blocks processing

audiofirfilter
  generic FIR kernel + latency in samples
  F32LE/F64LE
  rate-changed callback is streaming-thread/blocking

audioconvert
  can convert integer/float formats and channel layout
  dithering default is TPDF at/below threshold unless configured
  noise shaping has explicit property

dsdconvert
  converts DSD grouping/layout/byte representation
  it is NOT DSD->PCM conversion

CamillaDSP
  remains optional post-core sidecar candidate
  it already models IIR/FIR/convolution/mix/delay/dither/resampling
  adoption requires an ADR; core does not depend on it
```

Research URLs recorded for reproducibility:

```text
https://gstreamer.freedesktop.org/documentation/equalizer/equalizer-nbands.html
https://gstreamer.freedesktop.org/documentation/audiofx/audioiirfilter.html
https://gstreamer.freedesktop.org/documentation/audiofx/audiofirfilter.html
https://gstreamer.freedesktop.org/documentation/audioconvert/index.html
https://gstreamer.freedesktop.org/documentation/audio/gstdsd.html
https://github.com/HEnquist/camilladsp
https://github.com/jaakkopasanen/AutoEq
```
<!-- MICHI_PHASE2:CONTRACT:R11-G09-LEGACY-RESEARCH:END -->

Canonical Basic layout:

```python
MICHI_BASIC_10_CENTERS_HZ = (
    31.25, 62.5, 125.0, 250.0, 500.0,
    1000.0, 2000.0, 4000.0, 8000.0, 16000.0,
)
```

Product gain range:

```text
-12.0 .. +12.0 dB
step 0.5 dB
```

Advanced layout uses reviewed ISO 31 centers already documented in R10.

Do not hardcode Q for graphic bands. Compute deterministic bandwidth from
geometric boundaries between adjacent center frequencies:

```python
def graphic_bandwidths(centers: tuple[float, ...]) -> tuple[float, ...]:
    if len(centers) < 2:
        raise ValueError("at least two centers required")
    if any(a <= 0 or b <= a for a, b in zip(centers, centers[1:])):
        raise ValueError("centers must be strictly increasing and positive")

    boundaries = [centers[0] / math.sqrt(centers[1] / centers[0])]
    boundaries.extend(math.sqrt(a * b) for a, b in zip(centers, centers[1:]))
    boundaries.append(centers[-1] * math.sqrt(centers[-1] / centers[-2]))
    return tuple(
        boundaries[i + 1] - boundaries[i]
        for i in range(len(centers))
    )
```

The backend response must be measured against theoretical fixtures before
promotion. The geometric construction is configuration intent, not proof that
GStreamer's exact curve matches an RBJ-Q interpretation.

Factory presets live in a versioned resource asset. No curve values are
invented in QML.

---

# 389. PARAMETRIC EQ / BIQUAD R11

Full PEQ filter vocabulary:

```text
PEAK
LOW_SHELF
HIGH_SHELF
LOW_PASS
HIGH_PASS
NOTCH
BAND_PASS
ALL_PASS
```

Backend CORE candidate:

```text
one audioiirfilter per enabled biquad
```

because this gives explicit coefficient semantics for types beyond simple
center/bandwidth/gain.

Coefficient module requirements:

```text
pure Python math/cmath
no mandatory NumPy
finite input validation
0 < frequency < Nyquist
Q > 0 when applicable
gain bounded by product contract
normalize all coefficients by a0
reject a0 == 0
reject NaN/Inf
deterministic rounding only for serialization, not computation
```

Unknown filter:

```text
DSP_FILTER_TYPE_UNSUPPORTED
```

never identity pass-through.

Coefficient vectors must have golden tests derived from the RBJ cookbook and
frequency-response spot checks.

Saved profile versus runtime:

```text
saved 20 kHz band
32 kHz source -> above Nyquist

saved profile remains unchanged
effective graph marks band INACTIVE_ABOVE_NYQUIST
compiler receives only executable bands + adaptation evidence
```

No silent clamp.

---

# 390. PCM WORKING FORMAT / QUANTIZATION / DITHER R11

<!-- MICHI_PHASE2:CONTRACT:R11-G04-PROCESSING-SAMPLE:BEGIN -->
R10 did not make the internal PCM representation explicit. R11 does.

`audioiirfilter` and `audiofirfilter` officially accept F32LE/F64LE, not S32LE.
Therefore a processed graph must specify conversion boundaries.

Core model:

```python
@dataclass(frozen=True, slots=True)
class ProcessingSampleContract:
    input_format: str
    working_format: str
    output_format: str | None
    input_rate_hz: int
    output_rate_hz: int
    channels_in: int
    channels_out: int
    input_conversion: bool
    output_quantization: bool
    dither_mode: str
    noise_shaping_mode: str
```

Initial implementation policy:

```text
working format = F64LE when the required factories support it
F32LE may be selected only by an explicit capability/performance decision
rate stays source-native unless ResampleNode exists
channels stay unchanged unless ChannelMapNode exists
```

Why explicit:

```text
S32LE -> F64LE is a representation conversion
F64LE -> S32LE is quantization/conversion
neither is "bit-perfect"
neither is silently ignored by Signal Path
```

`audioconvert` defaults are NOT accepted blindly. Official documentation states
dithering defaults to TPDF under its threshold. Therefore every converter is
configured explicitly.

Internal converter policy:

```text
dithering = none
noise-shaping = none
no channel reorder
identity mix only
```

Terminal converter policy:

```text
if reducing to an integer target:
  dither behavior comes from explicit DitherPolicy
else:
  dithering = none
```

R11 core default:

```text
DITHER_OFF unless an explicit terminal precision-reduction policy requests it
```

No claim that OFF is sonically optimal; it is a deterministic default. A
future dither algorithm is a typed node/policy with Signal Path evidence.

`CompiledProcessingPlan` must carry the complete sample contract and transform
dimensions:

```text
changes_sample_values
changes_rate
changes_channels
changes_timing
changes_channel_assignment
changes_representation
quantization_boundary
```

Signal Truth cannot decide “unaltered” by checking one boolean.
<!-- MICHI_PHASE2:CONTRACT:R11-G04-PROCESSING-SAMPLE:END -->

---

# 391. CONVOLUTION / IR ASSETS R11

One semantic node covers FIR/convolution.

IR import pipeline:

```text
user selects file
-> parse off audio thread
-> validate finite PCM
-> normalize according to explicit import policy
-> compute SHA-256
-> write temp file
-> fsync
-> atomic rename to content-addressed store
-> persist metadata
```

Asset id:

```text
ir:sha256:<digest>
```

Never persist a mutable arbitrary external path as the execution authority.

Metadata:

```text
sha256
sample_rate_hz
channels
frames
encoding
normalization_policy
import_schema_version
```

Rate mismatch:

```text
no hidden IR resample

choice A: reject profile for current rate
choice B: explicit offline "Prepare IR for this rate"
          -> new content-addressed asset + provenance
```

`audiofirfilter` can be used only for kernels that pass F14 CPU/latency budgets.
Long-room-correction convolution may need another backend; do not force a
pathologically large kernel through an unsuitable real-time implementation.

Missing/corrupt asset:

```text
DSP_ASSET_MISSING
DSP_ASSET_HASH_MISMATCH
```

Profile remains saved but unavailable; it is never silently deleted or bypassed.

---

# 392. COMPILER R11 — PURE PLAN, BACKEND STRATEGIES, NO FACTORY FICTION

Compiler input:

```text
effective graph
input signal
backend capability snapshot
asset metadata snapshots
processing sample contract policy
```

Compiler output:

```text
immutable plan
no Gst objects
no file handles
no callbacks
no QObjects
```

Strategy set for CORE:

```text
graphic_eq_nbands
biquad_cascade
gain
convolution_fir
resample
channel_delay
channel_map
dither_terminal
```

Factory candidates are infrastructure facts, not domain enum values.

Example capability:

```python
@dataclass(frozen=True, slots=True)
class ProcessingStrategyCapability:
    strategy_id: str
    available: bool
    factories: tuple[str, ...]
    supported_formats: tuple[str, ...]
    reason: str | None
```

Plan hash includes every execution-significant fact:

```text
graph id/revision
effective graph digest
input rate/channels/format
working format
output rate/channels/format
each node semantic params
asset content hashes
backend strategy ids
latency expectation
terminal conversion/dither policy
```

It does not include presentation names.

Compiler errors are typed and stable. No catch-all “fallback to flat”.

---

# 393. PROCESSING TRANSACTION R11 — APPLY/READBACK/COMMIT

<!-- MICHI_PHASE2:CONTRACT:R11-G07-REALTIME-SAFETY:BEGIN -->
Real-time rule:

```text
NO network I/O in streaming callback
NO filesystem I/O in streaming callback
NO coefficient generation in streaming callback
NO JSON parse in streaming callback
NO Python per-sample/per-frame production DSP loops
NO blocking wait on GUI thread
```

Official GStreamer `audioiirfilter` and `audiofirfilter` `rate-changed` callbacks
run on the streaming thread and stop processing until handled. R11 therefore
does not use those callbacks to calculate kernels in Python.

Per-track preparation knows source rate before commit:

```text
characterize source
-> EffectiveGraphResolver(rate)
-> compile coefficients/kernel references for that rate
-> build candidate with rate caps
-> preroll
-> inspect
-> commit
```

Unexpected runtime rate renegotiation:

```text
publish typed RATE_RENEGOTIATION
invalidate candidate/current processing execution
rebuild outside streaming hot path
never compute a new filter inside callback
```

Core transition mode remains `QUIESCENT_REBUILD`.

Cancellation fence uses existing media/output lifecycle facts:

```text
new Play/load request
Stop
engine switch
output switch
device loss
shutdown
newer processing apply
```

any of these supersedes the candidate.

Resume contract:

```text
predecessor PLAYING -> may resume only after successful candidate commit
predecessor PAUSED  -> remains PAUSED
predecessor STOPPED -> remains STOPPED
```

No autoplay.

Position:

```text
capture confirmed position
seek after accepted media/candidate
display backend-confirmed position only
```

Failure before destructive boundary preserves predecessor.
Failure after it restores predecessor only with runtime proof; otherwise STOP.
<!-- MICHI_PHASE2:CONTRACT:R11-G07-REALTIME-SAFETY:END -->

Readback-first sequence:

```text
validate draft
compile
prepare candidate
preroll
inspect runtime
compare expected/observed
commit runtime
commit effective state
persist selected revision if policy says so
publish
```

No local state update before backend confirmation.

Basic Graphic EQ may later receive a hot-property-update optimization, but it is
not CORE until a dedicated test proves:

```text
property readback
generation safety
no XRUN
no stale update
bounded UI rate
```

Until then a debounced/quiescent transaction is the safe implementation.

---

# 394. SIGNAL TRUTH R11 — EXTEND, DO NOT FORK

Existing `SignalTruthRecorder` remains authoritative for the PCM Direct evidence
it already owns.

Phase2 adds a family-neutral projection layer; it must not introduce a second
Direct classifier.

New path facts:

```text
SOURCE
DECODE
REPRESENTATION_CONVERSION
PROCESSING nodes
RESAMPLE / CHANNEL_MAP if explicit
TRANSPORT
DEVICE NEGOTIATED
```

Current Direct snapshots are adapted losslessly into this graph.

Managed snapshots carry:

```text
processing plan id/revision
working format
node parameter digests
observed Gst factories
input/output caps
terminal format
latency evidence
XRUN/error evidence
```

Labels are factual:

```text
Processing active
Resampled
Channel mapping
Representation converted
Not verified
Contradicted
```

No “bit-perfect” label is inferred from profile intent.

Bypass truth is explicit:

```text
graph_bypassed: bool
```

`no ACTIVE nodes` is not proof of bypass.

---

# 395. PERSISTENCE R11 — SAME CANONICAL DATABASE, SCHEMA v3

<!-- MICHI_PHASE2:CONTRACT:R11-G05-PERSISTENCE:BEGIN -->
Phase2 does NOT create an independent settings database.

Existing authority:

```text
SQLiteSettingsRepository
CURRENT_SCHEMA_VERSION = 2 at audit head
same DB already contains output profile/selection tables
```

F13 migration target:

```text
2 -> 3
```

in `src/michi/infrastructure/sqlite_settings.py`, one transaction.

Stable table names:

```sql
audio_processing_profiles
audio_processing_selection
audio_ir_assets
dsd_user_policy
dop_user_confirmations
```

Do not suffix table names `_v1`; schema evolution belongs in DB/document schema
versions.

Durable user-authoritative tables must be added to:

```text
_AUTHORITATIVE_TABLES
_AUTHORITATIVE_QUERIES
_PHASE2_ERA_TABLES
```

with a Phase2 era marker. Once the marker exists, missing sibling Phase2
authoritative tables are corruption, not “empty”.

Rebuildable runtime/evidence caches stay OUT of LKG logical equality.

Never persist:

```text
ALSA card index as identity
Gst element pointer/name as durable state
active runtime handle
current caps snapshot
current Signal Path
temporary candidate plan
```

Processing profile persistence:

```text
profile_id
display_name
document_schema_version
document_json
document_sha256
revision
created/updated timestamps
```

Selection points to a profile id/revision, not a duplicated graph JSON.

IR metadata is authoritative user state; bytes live in content-addressed
app-data storage. Missing bytes degrade the profile with a typed error; DB
recovery never fabricates them.

Migration gates:

```text
fresh -> v3
v2 -> v3 preserving all existing rows
v3 missing Phase2 required table -> fail closed
future version -> fail closed
LKG equality includes Phase2 user intent
rebuildable evidence divergence does not invalidate LKG
migration rollback on injected SQL failure
```
<!-- MICHI_PHASE2:CONTRACT:R11-G05-PERSISTENCE:END -->

---

# 396. UI FILE MAP R11 — EXACT SURFACES

<!-- MICHI_PHASE2:CONTRACT:R11-G06-UI-FILE-MAP:BEGIN -->
Canonical NowPlaying audio controls after F11:

```text
settings/equalizer icon -> EqualizerPopup.qml
audio-output icon       -> existing AudioOutputPopup.qml
audio-engine icon       -> existing AudioEnginePopup.qml
quality/signal affordance -> SignalTruthPopup.qml
queue icon              -> existing queue
```

Exact new popup files:

```text
EqualizerPopup.qml
AdvancedEqualizerPopup.qml
SignalTruthPopup.qml
```

Exact existing popup to MODIFY:

```text
AudioOutputPopup.qml
```

Retired names:

```text
DacQuickPopup.qml
AudioProcessingPopup.qml
SignalPathPopup.qml
```

`SignalTruthPopup` contains the Signal Path; it is not a second concept.

No new theme namespace. Use current:

```text
MichiSpacing
MichiRadius
MichiPalette
MichiSemanticColors
MichiMotion
MichiAccessibility
MichiGlassSurface
MichiText
MichiButton
MichiIconButton
```

Bridges project immutable/readback-derived state. QML does not retain its own
copy of active graph/device/engine truth.

Accessibility:

```text
all icon-only controls accessibleName
keyboard traversal deterministic
Escape closes and returns focus
reducedMotion respected
no status conveyed only by color
```
<!-- MICHI_PHASE2:CONTRACT:R11-G06-UI-FILE-MAP:END -->

---

# 397. AUDIO OUTPUT POPUP R11 — aa8 HANDOVER TRUTH

Modify the existing row model; do not replace the popup.

Projection adds presentation-only fields:

```text
selected
active
pending
pendingReason
quickStatus
quickSubtitle
```

Do not remove existing settings-oriented fields that other surfaces consume.

Rendering priority:

```text
active          -> filled active indicator + truthful Signal Truth label
pending         -> progress/preparing affordance
selected only   -> selection border, not active dot
unavailable     -> disabled/error presentation
```

During cold DAC handover:

```text
B selected + pending
A active
```

must be visible simultaneously.

After destructive boundary, if no executor proves predecessor ownership:

```text
active = none
```

Never keep A highlighted just because it was previously active.

`Fixed / Unity` remains accessibility/diagnostic semantics but is not restored as
permanent visual copy in NowPlaying when gain is locked.

---

# 398. BASIC EQUALIZER POPUP R11 — MINIMAL AND PRODUCTIVE

Quick popup contains only:

```text
On/Bypass
10 Graphic EQ bands
Preamp / headroom summary
Factory preset
Reset
Advanced…
conflict/error copy
```

It does not expose:

```text
FIR
DSD
DoP
resampler
backend factories
raw coefficients
```

Sliders edit a draft revision.

Interaction:

```text
drag -> draft update / visual value
debounced preview request if runtime policy allows
release -> explicit transaction apply
backend readback -> effective state
failure -> draft remains, effective state remains predecessor
```

Do not emit one full pipeline rebuild for every pointer pixel.

Factory preset identifiers are stable machine ids; localized display names are
presentation only.

`Advanced…` opens `AdvancedEqualizerPopup.qml`, not a new route in Sidebar.

---

# 399. ADVANCED EQUALIZER R11

Tabs:

```text
Graphic 31
Parametric
Convolution
Signal / Output
Profiles
```

Graphic 31 and Basic 10 are two layouts of the same `GraphicEqNode` concept.

Parametric tab exposes typed filters; unsupported filter types are disabled with
a capability reason, not approximated.

Convolution tab shows:

```text
asset name
hash short form
source rate
channels
frames
latency
availability
```

Signal / Output shows factual processing working format and terminal conversion,
not a “quality score”.

Profiles supports:

```text
factory
custom
duplicate
rename
import/export native Michi schema
A/B draft compare
per-output association post-core
```

AutoEQ is post-core. Local/native import can be added only after current
upstream schema/provenance is re-reviewed.

---

# 400. SIGNAL TRUTH POPUP R11

SignalTruthPopup is a read-only diagnostic/explanation surface.

Example Processed PCM:

```text
Source
  FLAC · 44.1 kHz · 24-bit
      ↓
Decode
  PCM · 44.1 kHz · 24 significant bits
      ↓
Representation
  F64LE working format
      ↓
Graphic EQ
  Michi 10 · active
      ↓
Preamp
  -3.5 dB
      ↓
Terminal conversion
  S32LE · dither off
      ↓
Output
  Topping ... · ALSA hw
```

Each node has:

```text
state
reason/evidence
requested
effective
```

Unknown facts render as Unknown/Not observed; never guessed.

For existing Direct playback, the popup renders the current SignalTruthRecorder
evidence without reclassification.

For DSD/DoP, it uses their dedicated evidence only after their phases close.

---

# 401. REAL-TIME SAFETY R11 — HOT PATH BUDGET

The audio callback/streaming thread may:

```text
process buffers in native backend
read immutable already-prepared parameters
perform bounded native element operations
emit minimal lock-free/native telemetry where already supported
```

It may not:

```text
open files
hash files
parse JSON/YAML
perform HTTP
query GitHub/AutoEQ
access SQLite
wait for QThreadPool
run Python coefficient loops
allocate unbounded lists
rebuild a large IR
```

Rate-dependent DSP material is compiled before preroll.

UI spectrum/response rendering is not audio truth and never runs in the audio
hot path.

Performance failure is functional failure for a realtime feature:

```text
XRUN
unbounded callback
missed generation fence
stale element mutation
memory growth
```

all block F14 promotion.

---

# 402. DEPENDENCY POLICY R11

CORE dependency policy:

```text
prefer stdlib + existing PySide/GStreamer system runtime
no NumPy merely for biquads/response preview
no SciPy core dependency
no web dependency for playback
```

Optional heavy DSP engine:

```text
CamillaDSP sidecar
```

requires its own ADR answering:

```text
why GStreamer core is insufficient
process ownership
IPC protocol
sample-rate handoff
crash/fallback behavior
latency
packaging
license
resource cost
Signal Truth evidence
```

It cannot be slipped into F05 as a convenience.

AutoEQ network/provider support is optional and post-core. Playback must be
fully functional offline.

---

# 403. TEST AUTHORITY R11

<!-- MICHI_PHASE2:CONTRACT:R11-G08-TEST-AUTHORITY:BEGIN -->
Test principle:

```text
tests are evidence of a chosen contract
tests do not become product authority by being old
```

R11 gate tiers:

```text
AP2-T0  architecture/safety; blocks every Phase2 commit
AP2-T1  deterministic unit/integration; regressions block
AP2-T2  active feature development; must be green to close its work unit
AP2-T3  real runtime/hardware/performance; required only for declared closure
```

Every work unit follows:

```text
RED contract test
minimal implementation
GREEN focused test
architecture gates
affected regression suite
diff review
commit
```

Prohibited:

```text
weaken assertion to match bug
delete failing test without contract decision
mock the very behavior claimed as productive evidence
count skipped hardware test as physical PASS
```

For DSP response tests distinguish:

```text
math golden            theoretical coefficient/response
backend functional     real Gst element behavior
runtime integration    real graph/readback/generation
physical audio         hardware/loopback/capture where required
```

One level does not substitute for another.
<!-- MICHI_PHASE2:CONTRACT:R11-G08-TEST-AUTHORITY:END -->

---

# 404. FILE OWNERSHIP / CROSS-PHASE RULES R11

A phase may modify only files listed by its manifest packet unless it records a
cross-phase exception in the work-unit receipt.

Exception format:

```json
{
  "phase": "AP2-F05",
  "extra_path": "src/michi/application/playback_service.py",
  "owner_phase": "AP2-F10",
  "reason": "specific seam required",
  "contract_anchor": "R11-F05",
  "tests": ["..."]
}
```

The alignment verifier rejects unrecorded cross-phase files.

Shared high-risk files:

```text
bootstrap/__init__.py
playback_service.py
output_session_service.py
gstreamer.py
signal_truth.py
sqlite_settings.py
NowPlayingBar.qml
```

touches must include direct regression gates for existing behavior.

Never use “while here” cleanup inside a Phase2 patch.

---

# 405. AP2-F00 — ACTIVATION / BASELINE FREEZE

<!-- MICHI_PHASE2:CONTRACT:R11-F00:BEGIN -->
PHASE_ID: AP2-F00
TITLE: ACTIVATION / BASELINE FREEZE
DEPENDENCIES: NONE
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G01-CURRENT-REPO, R11-G08-TEST-AUTHORITY, R11-G11-PATCH-PROTOCOL, R11-G12-CONTEXT-TOOL, R11-G13-ALIGNMENT, R11-F00

## File ownership
CREATE:
```text
docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md
docs/audio/PHASE2_BASELINE.json
docs/audio/PHASE2_STATE.json
scripts/phase2_context.py
scripts/verify_audio_phase2_repository_alignment.py
tests/architecture/test_phase2_spec_contract.py
```
MODIFY:
```text
AGENTS.md
```
FORBIDDEN:
```text
src/michi/**
```

## Implementation contract
Exact order:

```text
1 verify PRE-AP2-01 restricted-entry prerequisites: M11.4 software closed, physical blockers classified, M11.5A FROZEN, exact-head regression green
2 git status --porcelain=v1
3 capture HEAD + branch + tool/runtime versions
4 install exactly one canonical spec
5 compute spec SHA after installation
6 create PHASE2_BASELINE.json
7 create PHASE2_STATE.json with every phase LOCKED except F00 ACTIVE
8 install context extractor from R11-G12
9 install alignment verifier from R11-G13
10 add AGENTS discovery block
11 add structural tests
12 rerun alignment; then and only then close F00
```

Baseline JSON minimum fields:

```json
{
  "schema": 1,
  "baseline_head": "<40-hex>",
  "spec_sha256": "<64-hex>",
  "python": "...",
  "qt": "...",
  "gstreamer": "...",
  "kernel": "...",
  "alsa_library": "...",
  "inherited_gate_receipts": [],
  "created_at_utc": "..."
}
```

State is orchestration, not duplicated design:

```json
{
  "schema": 1,
  "spec_path": "docs/audio/...",
  "spec_sha256": "...",
  "baseline_head": "...",
  "active_phase": "AP2-F00",
  "phases": {"AP2-F00":"ACTIVE","AP2-F01":"LOCKED"}
}
```

Do not modify product code in F00.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
one tracked canonical spec
spec/context/alignment structural tests green
baseline exact-head receipt stored
zero product-code diff
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F00:END -->

---

# 406. AP2-F01 — DOMAIN FOUNDATION / PARITY

<!-- MICHI_PHASE2:CONTRACT:R11-F01:BEGIN -->
PHASE_ID: AP2-F01
TITLE: SIGNAL DOMAIN / EXECUTION FAMILY / PCM PARITY
DEPENDENCIES: AP2-F00
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G08-TEST-AUTHORITY, R11-F01

## File ownership
CREATE:
```text
src/michi/domain/audio_signal.py
src/michi/domain/audio_execution.py
tests/audio_phase2/test_audio_signal_domain.py
tests/audio_phase2/test_audio_execution_domain.py
```
MODIFY:
```text
NONE
```
FORBIDDEN:
```text
playback_service.py
output_session_service.py
gstreamer.py
QML
SQLite schema
```

## Implementation contract
Create only pure immutable types.

`audio_signal.py` minimum:

```python
class SignalFamily(StrEnum):
    PCM = "pcm"
    DSD = "dsd"

@dataclass(frozen=True, slots=True)
class ChannelLayout:
    positions: tuple[str, ...]

    @property
    def channels(self) -> int:
        return len(self.positions)

@dataclass(frozen=True, slots=True)
class PcmSignalFormat:
    rate_hz: int
    transport_format: str
    significant_bits: int | None
    layout: ChannelLayout
```

`audio_execution.py`:

```python
class AudioExecutionFamily(StrEnum):
    SHARED_PCM = "shared_pcm"
    DIRECT_PCM = "direct_pcm"
    MANAGED_PCM = "managed_pcm"
    NATIVE_DSD = "native_dsd"
    DOP = "dop"
```

Adapter tests must prove current `PcmTuple` / `DecodedSourceSignal` semantics do
not change. Do not modify those current classes yet.

No routing, DSP or persistence in this phase.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
pure types deterministic
existing PCM adapter fixtures parity
current DAC suite unaffected
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F01:END -->

---

# 407. AP2-F02 — DEVICE KNOWLEDGE / CAPABILITY PROJECTION

<!-- MICHI_PHASE2:CONTRACT:R11-F02:BEGIN -->
PHASE_ID: AP2-F02
TITLE: DEVICE KNOWLEDGE WITHOUT ADMISSION AUTHORITY
DEPENDENCIES: AP2-F01
MUST_READ_ANCHORS: R11-G01-CURRENT-REPO, R11-G02-AUTHORITY-MAP, R11-G09-LEGACY-RESEARCH, R11-F02

## File ownership
CREATE:
```text
src/michi/domain/audio_device_knowledge.py
src/michi/application/audio_device_knowledge_service.py
tests/audio_phase2/test_device_knowledge.py
```
MODIFY:
```text
src/michi/presentation/audio_output_bridge.py
```
FORBIDDEN:
```text
device allowlists that control admission
writes to USB/ALSA controls
qualification cache ownership change
```

## Implementation contract
Knowledge is descriptive enrichment only.

```python
@dataclass(frozen=True, slots=True)
class DeviceKnowledge:
    stable_device_id: str
    manufacturer_label: str | None
    product_label: str | None
    capability_hints: tuple[str, ...]
    sources: tuple[EvidenceSource, ...]
    resolution: EvidenceResolution
```

No knowledge row can make an unavailable/non-playback USB object enter the
AudioDeviceRegistry. Current ALSA playback admission stays authoritative.

Conflict:

```text
knowledge says supports DSD
physical/current qualification unknown
=> UI may show documented hint
=> planner still treats runtime capability as UNKNOWN
```

No background web lookup in playback.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
unknown devices remain selectable if current registry admits them
knowledge never mutates qualification
every displayed enrichment has provenance
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F02:END -->

---

# 408. AP2-F03 — FAMILY-NEUTRAL SIGNAL PATH PROJECTION

<!-- MICHI_PHASE2:CONTRACT:R11-F03:BEGIN -->
PHASE_ID: AP2-F03
TITLE: FAMILY-NEUTRAL SIGNAL PATH PROJECTION
DEPENDENCIES: AP2-F01, AP2-F02
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-F03

## File ownership
CREATE:
```text
src/michi/domain/signal_path.py
src/michi/application/signal_path_service.py
tests/audio_phase2/test_signal_path_service.py
```
MODIFY:
```text
src/michi/domain/signal_truth.py
```
FORBIDDEN:
```text
new Direct truth recorder
I/O from SignalPathService
QML inference of signal state
```

## Implementation contract
First close parity for existing Direct snapshots.

`SignalPathService` is a pure projection over snapshots. It never commands
runtime.

Canonical node:

```python
@dataclass(frozen=True, slots=True)
class SignalPathNode:
    node_id: str
    kind: str
    label: str
    state: str
    requested: tuple[tuple[str, object], ...]
    effective: tuple[tuple[str, object], ...]
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
```

Direct adapter maps existing `SignalTruthRecorder` snapshot 1:1. Every current
verdict/reason code gets a parity test before adding processing/DSD nodes.

Unknown remains an explicit node state; missing evidence never drops a node in
a way that implies success.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
all existing Direct truth fixtures unchanged
projection deterministic
no execution authority added
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F03:END -->

---

# 409. AP2-F04 — DSP GRAPH / COMPILER

<!-- MICHI_PHASE2:CONTRACT:R11-F04:BEGIN -->
PHASE_ID: AP2-F04
TITLE: PROCESSING DOMAIN / EFFECTIVE GRAPH / COMPILER
DEPENDENCIES: AP2-F01, AP2-F03
MUST_READ_ANCHORS: R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-G09-LEGACY-RESEARCH, R11-F04

## File ownership
CREATE:
```text
src/michi/domain/audio_processing.py
src/michi/domain/audio_processing_evidence.py
src/michi/application/audio_processing_ports.py
src/michi/application/effective_processing_graph.py
src/michi/application/processing_graph_compiler.py
src/michi/infrastructure/audio_processing/biquad.py
tests/audio_phase2/test_processing_domain.py
tests/audio_phase2/test_processing_compiler.py
tests/audio_phase2/test_biquad.py
```
MODIFY:
```text
NONE
```
FORBIDDEN:
```text
GStreamer import in domain/compiler
NumPy mandatory dependency
backend property names in persisted profile
```

## Implementation contract
CORE node kinds are exactly:

```text
PREAMP
GRAPHIC_EQ
PARAMETRIC_EQ
CONVOLUTION
CHANNEL_DELAY
CHANNEL_MAP
RESAMPLE
DITHER
```

No Mixer/Limiter/Crossfeed/Loudness in CORE.

`GraphicEqNode` stores layout id + gains, not Q values.
`ParametricEqNode` stores typed RBJ bands.
`ConvolutionNode` stores immutable asset id/hash, not an unbounded coefficient
tuple.

`EffectiveProcessingGraphResolver` is the only runtime adaptation seam:

```text
saved graph + current signal
-> effective graph + adaptation reasons
```

Above-Nyquist PEQ bands become non-executable with reason; saved intent is not
rewritten.

Compiler is pure:

```text
effective graph + capabilities + asset metadata + sample policy
-> CompiledProcessingPlan
```

The plan includes:

```text
working format
terminal format
node strategies
expected latency
asset hashes
changes_sample_values
changes_representation
changes_rate
changes_channels
changes_timing
changes_channel_assignment
```

Unknown strategy -> typed refusal. No fallback-to-flat.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
domain immutable
compiler deterministic hash
golden biquad vectors green
Nyquist and identity-transform tests green
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F04:END -->

---

# 410. AP2-F05 — GSTREAMER PCM PROCESSING RUNTIME

<!-- MICHI_PHASE2:CONTRACT:R11-F05:BEGIN -->
PHASE_ID: AP2-F05
TITLE: GSTREAMER SHARED/PROCESSED PCM RUNTIME
DEPENDENCIES: AP2-F04
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-G08-TEST-AUTHORITY, R11-F05

## Execution ownership (host-aware, MANDATORY)
```text
PRODUCTIVE PARENT Gst OBJECT COUNT = 0
```
The GStreamer Output Host (supervised child process, GST_LIFECYCLE_GATE = PASS)
owns ALL native GStreamer objects. F05 extends that host; it never installs a
processing element in the parent process.

PARENT (semantic authority):
```text
ProcessingProfile / ProcessingGraph
ProcessingGraphCompiler -> CompiledProcessingPlan
AudioProcessingService (validate/compile/prepare/commit/publish)
ProcessingSampleContract
expected graph + readback comparison
effective processing revision
Signal Truth / Signal Path projection
```

CHILD (native authority, inside gstreamer_host_process):
```text
Gst.Elements of the processing graph
Gst.Bin / native pads / negotiated caps
native preroll
native property/caps readback
primitive runtime observations
```

CHILD never owns: processing policy, effective profile truth,
SignalTruthRecorder, PlaybackService, OutputSessionService, user selection,
semantic plan compilation.

## File ownership
CREATE:
```text
src/michi/infrastructure/audio_processing/__init__.py
src/michi/infrastructure/audio_processing/gstreamer_capabilities.py   [CHILD-NATIVE]
src/michi/infrastructure/audio_processing/gstreamer_graph_builder.py  [CHILD-NATIVE]
src/michi/infrastructure/audio_processing/gstreamer_runtime.py        [CHILD-NATIVE]
src/michi/application/audio_processing_service.py                     [PARENT-SAFE]
tests/audio_phase2/test_gstreamer_processing_runtime.py
tests/audio_phase2/test_processing_host_seam.py
```
MODIFY:
```text
src/michi/infrastructure/audio_engines/gstreamer.py            [CHILD-NATIVE port]
src/michi/infrastructure/audio_engines/gstreamer_host_protocol.py  [IPC seam]
src/michi/infrastructure/audio_engines/gstreamer_host_session.py   [IPC seam]
src/michi/infrastructure/audio_engines/gstreamer_host_process.py   [IPC seam]
src/michi/bootstrap/__init__.py                                [semantic composition]
```
FORBIDDEN:
```text
strict Direct sink builder semantics
per-sample Python
coefficient computation in rate-changed callback
implicit audioconvert defaults
productive Gst.Element/Gst.Bin creation in the PARENT process
second AudioPort / second GStreamer host / second SignalTruthRecorder
semantic processing commit inside the child host
```

## Implementation contract
Capability probe runs INSIDE the GStreamer host (or another disposable child
runtime with the same real environment): the parent sends a capability query,
the child checks real factories and returns primitive facts; the parent decides
capability state. Never instantiate factories in the productive parent.

Factories to probe (child side):

```text
equalizer-nbands
audioiirfilter
audiofirfilter
audioconvert
audioresample
volume
```

Do not mark a strategy available from package/version alone; instantiate and
inspect required properties/pad formats inside the host.

CORE Shared processing uses playbin3's documented `audio-filter` property or a
tested custom bin seam, installed by the CHILD while quiescent and verified
before commit. Do not modify the Direct strict sink construction.

Processing transaction across the process boundary:

```text
PARENT  compile candidate; assign processing_generation
PARENT  -> CHILD: PREPARE_PROCESSING_CANDIDATE (bounded DTO; no audio ever)
CHILD   build native graph quiescent; preroll; inspect runtime
CHILD   -> PARENT: primitive runtime evidence
PARENT  compare expected vs observed
        mismatch -> abort candidate (predecessor intact if boundary not crossed)
        match    -> authorize commit
CHILD   activate candidate; -> PARENT: commit receipt
PARENT  publish effective revision (Signal Truth / Signal Path)
```

Generation model (three authorities; all must match for a result to be
current): HOST_GENERATION, PIPELINE_GENERATION, PROCESSING_GENERATION.
Newer user intent always wins. IPC transports commands, compiled semantic
configuration, IDs, generations, properties, readback and typed errors — NEVER
PCM/DSD samples, Gst objects, QObjects or callbacks.

Canonical processing bin shape for full PEQ/FIR path:

```text
ghost sink
-> audioconvert [dither=none, noise-shaping=none]
-> capsfilter F64LE, source rate/channels
-> typed DSP chain
-> terminal conversion as policy requires
-> ghost src / sink integration
```

For Basic/Graphic-only, `equalizer-nbands` may accept S16/F32/F64, but R11 does
not create a second precision policy: it still follows the compiled sample
contract.

`AudioProcessingService` sequence:

```text
validate draft
compile
prepare
preroll
inspect/readback
commit
publish effective revision
```

A failure leaves effective predecessor unchanged if the destructive boundary
was not crossed.

No runtime claim is emitted merely because an element object exists.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
real GStreamer runtime gate green
readback mismatch fails
Shared PCM EQ audible/runtime-observed
Direct regression unchanged
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F05:END -->

---

# 411. AP2-F06 — MANAGED PCM TO LOCAL DAC + ADVANCED PROCESSING

<!-- MICHI_PHASE2:CONTRACT:R11-F06:BEGIN -->
PHASE_ID: AP2-F06
TITLE: MANAGED PCM TO SPECIFIC DAC / ADVANCED DSP
DEPENDENCIES: AP2-F05
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-F06

## File ownership
CREATE:
```text
src/michi/domain/managed_pcm_output.py
src/michi/application/managed_pcm_output_planner.py
src/michi/infrastructure/audio_output/managed_pcm_executor.py
tests/audio_phase2/test_managed_pcm_output.py
```
MODIFY:
```text
src/michi/application/output_session_service.py
src/michi/presentation/audio_output_bridge.py
src/michi/bootstrap/__init__.py
```
FORBIDDEN:
```text
allow_processing=True on current Direct OutputPlan
Direct labels on managed execution
silent terminal-format fallback
```

## Implementation contract
Implement `OutputPathPreference.MANAGED` as a real specific-DAC processed path;
today it is not one.

Create a separate `ManagedPcmOutputPlan`. Do not reuse Direct `OutputPlan` with
different booleans.

Managed planner inputs:

```text
selected stable device
single current ALSA playback binding
source PCM
compiled processing plan
current positive terminal-format evidence
explicit volume policy
```

Managed sink may be `alsasink` to the selected binding, but the path is
`MANAGED_PCM`, not Direct.

Initial rate policy:

```text
output rate = source rate unless ResampleNode explicitly changes it
```

Channel policy:

```text
output channels = source channels unless ChannelMapNode explicitly changes it
```

Terminal container is selected only from proven current capability. If no safe
terminal format is proven, refuse and preserve predecessor.

Integration with `OutputSessionService` must preserve all existing Direct
tests byte-for-byte semantically; new branch is additive and tagged.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
processed specific-DAC route works
Direct test matrix green
Signal Path says Processed not Direct
device loss/stale selection fail safely
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F06:END -->

---

# 412. AP2-F07 — DSD SOURCE TRUTH / QUALIFICATION

<!-- MICHI_PHASE2:CONTRACT:R11-F07:BEGIN -->
PHASE_ID: AP2-F07
TITLE: DSD SOURCE TRUTH / CAPABILITY
DEPENDENCIES: AP2-F03
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-F07

## File ownership
CREATE:
```text
src/michi/domain/dsd_signal.py
src/michi/application/dsd_source_characterizer.py
tests/audio_phase2/test_dsd_source_truth.py
```
MODIFY:
```text
NONE
```
FORBIDDEN:
```text
extension-only truth
Legacy DoP path
PCM bit-depth fields reused as DSD rate
```

## Implementation contract
Define DSD with explicit units:

```python
@dataclass(frozen=True, slots=True)
class DsdSignalFormat:
    bit_rate_hz: int
    channels: int
    packing: str
    layout: tuple[str, ...]
```

`DSD64` etc are presentation labels derived from exact bit rate, never the
stored authority.

Characterization requires parser/runtime evidence sufficient to distinguish
DSF/DFF container facts from actual decoded/transport facts.

GStreamer `dsdconvert` may normalize grouping/layout; it does not prove Native
DSD device support and is not DSD->PCM.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
DSF/DFF fixtures typed
DSD units tests green
unknown source fails closed
no output claim yet
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F07:END -->

---

# 413. AP2-F08 — NATIVE DSD RUNTIME

<!-- MICHI_PHASE2:CONTRACT:R11-F08:BEGIN -->
PHASE_ID: AP2-F08
TITLE: NATIVE DSD
DEPENDENCIES: AP2-F07
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-F08

## File ownership
CREATE:
```text
src/michi/domain/dsd_output.py
src/michi/application/dsd_output_planner.py
src/michi/infrastructure/dsd/native_dsd_executor.py
tests/audio_phase2/test_native_dsd_runtime.py
```
MODIFY:
```text
src/michi/bootstrap/__init__.py
```
FORBIDDEN:
```text
PCM decoder/converter in Native path
DSP
software volume unless DSD-native semantics explicitly proven
```

## Implementation contract
Native DSD is not enabled by a vendor hint. Planner requires current device /
transport evidence.

Pipeline inspection must prove:

```text
source DSD
no PCM decode element
no PCM DSP/resampler
DSD grouping conversions only if explicitly represented
target device/binding current
runtime carrier matches plan
```

If backend/GStreamer stack cannot provide this proof on the target system, the
feature remains unavailable. Do not invent a native path just to satisfy UI.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
native fixture/runtime gate
no PCM element in inspected branch
failure is typed unavailable, never silent PCM
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F08:END -->

---

# 414. AP2-F09 — DOP

<!-- MICHI_PHASE2:CONTRACT:R11-F09:BEGIN -->
PHASE_ID: AP2-F09
TITLE: DOP PACKER / CARRIER / RUNTIME
DEPENDENCIES: AP2-F07
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G07-REALTIME-SAFETY, R11-G09-LEGACY-RESEARCH, R11-F09

## File ownership
CREATE:
```text
src/michi/application/dop_output_planner.py
src/michi/infrastructure/dop/dop_packer.py
src/michi/infrastructure/dop/dop_executor.py
tests/audio_phase2/test_dop_vectors.py
tests/audio_phase2/test_dop_runtime.py
```
MODIFY:
```text
src/michi/bootstrap/__init__.py
```
FORBIDDEN:
```text
DSD decoder->PCM named DoP
Python per-frame production hot loop
audioresample in carrier
```

## Implementation contract
Start with pure conformance vectors:

```text
marker bytes
channel alternation
payload placement
carrier width/endian
DSD64/128 mapping to carrier rate
boundary continuity
```

Only after vectors pass may the productive packer exist.

Production packing must be native/bounded; Python can generate fixtures but is
not the per-frame hot path.

Inspected DoP path must show:

```text
DSD source
DoP packer
PCM carrier representation
no ordinary PCM DSP
no resampler
qualified terminal tuple
```

Legacy `filesrc -> DSD decoder -> audioconvert -> audioresample` is explicitly
rejected.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
golden DoP vectors exact
carrier runtime inspected
no resampling/DSP
unsupported target fails closed
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F09:END -->

---

# 415. AP2-F10 — DSD→PCM / CROSS-FAMILY TRANSITIONS

<!-- MICHI_PHASE2:CONTRACT:R11-F10:BEGIN -->
PHASE_ID: AP2-F10
TITLE: DSD→PCM / FAMILY TRANSITIONS
DEPENDENCIES: AP2-F05, AP2-F07, AP2-F08, AP2-F09
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G03-OUTPUT-FAMILIES, R11-G04-PROCESSING-SAMPLE, R11-G07-REALTIME-SAFETY, R11-F10

## File ownership
CREATE:
```text
src/michi/application/audio_family_transition.py
src/michi/infrastructure/dsd/dsd_to_pcm.py
tests/audio_phase2/test_family_transitions.py
```
MODIFY:
```text
src/michi/application/playback_service.py
src/michi/bootstrap/__init__.py
```
FORBIDDEN:
```text
silent Native/DoP -> PCM fallback
autoplay after non-playing predecessor
second playback-state authority
```

## Implementation contract
DSD->PCM is an explicit conversion family, never fallback camouflage.

User intent must name the conversion policy/version. If no validated conversion
backend/policy exists, keep this route unavailable.

Family transition receipt includes:

```text
media identity
confirmed position if representable
predecessor playback status
source family
target family
request epoch
output generation
processing generation
destructive boundary
```

The aa8 rule generalizes:

```text
newer Play/Stop/output/engine/family request wins
late candidate aborts
PLAYING may resume only after commit
PAUSED stays paused
STOPPED stays stopped
```

No callback may restore stale media.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
cross-family stale gates
no-autoplay gates
explicit conversion visible in Signal Path
predecessor restoration truth-tested
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F10:END -->

---

# 416. AP2-F11 — UI CONVERGENCE

<!-- MICHI_PHASE2:CONTRACT:R11-F11:BEGIN -->
PHASE_ID: AP2-F11
TITLE: NOWPLAYING / POPUPS / ACCESSIBILITY
DEPENDENCIES: AP2-F03, AP2-F05, AP2-F06, AP2-F10
MUST_READ_ANCHORS: R11-G03-OUTPUT-FAMILIES, R11-G06-UI-FILE-MAP, R11-G10-STOP-CODES, R11-F11

## File ownership
CREATE:
```text
src/michi/presentation/audio_processing_bridge.py
src/michi/presentation/signal_path_bridge.py
src/michi/presentation/qml/player/EqualizerPopup.qml
src/michi/presentation/qml/player/AdvancedEqualizerPopup.qml
src/michi/presentation/qml/player/SignalTruthPopup.qml
```
MODIFY:
```text
src/michi/presentation/audio_output_bridge.py
src/michi/presentation/qml/player/NowPlayingBar.qml
src/michi/presentation/qml/player/AudioOutputPopup.qml
src/michi/bootstrap/__init__.py
```
FORBIDDEN:
```text
DacQuickPopup.qml
AudioProcessingPopup.qml
SignalPathPopup.qml
second theme/token system
UI-owned effective state
```

## Implementation contract
Do not redesign NowPlayingBar wholesale.

Reuse current slots:

```text
settings/equalizer button -> EqualizerPopup
audio-output button       -> existing AudioOutputPopup
audio-engine button       -> existing AudioEnginePopup
quality/signal affordance -> SignalTruthPopup
```

Output popup row model explicitly supports:

```text
selected
pending
active
unavailable
```

B selected while A active is legal and must render as such.

Basic EQ:
10 sliders + bypass + preamp/headroom + preset + Reset + Advanced.
Advanced popup owns 31-band/PEQ/convolution/profile views.

No control is visible as functional before its bridge capability is real.
Disabled-with-reason is acceptable; fake success is not.

Use existing QML tokens/components. New reusable component only if there are at
least two semantic consumers.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
QML runtime warning gate zero
keyboard/focus/reduced-motion tests
selected/pending/active screenshot/runtime tests
no dead controls
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F11:END -->

---

# 417. AP2-F12 — HIGH-END DEVICE INTELLIGENCE

<!-- MICHI_PHASE2:CONTRACT:R11-F12:BEGIN -->
PHASE_ID: AP2-F12
TITLE: HIGH-END DEVICE INTELLIGENCE / OPTIONAL CONTROLS
DEPENDENCIES: AP2-F02, AP2-F06, AP2-F11
MUST_READ_ANCHORS: R11-G02-AUTHORITY-MAP, R11-G09-LEGACY-RESEARCH, R11-F12

## File ownership
CREATE:
```text
src/michi/domain/device_native_capability.py
src/michi/application/device_native_capability_service.py
tests/audio_phase2/test_native_device_capability.py
```
MODIFY:
```text
NONE
```
FORBIDDEN:
```text
undocumented vendor write
driver equivalence claim
knowledge->physical proof promotion
```

## Implementation contract
Separate:

```text
documentation knowledge
observed descriptors
qualified playback tuples
optional control capability
```

Optional USB/vendor controls require:

```text
known protocol source
exact device match
read-before-write
bounded values
write result
readback confirmation
rollback where possible
explicit user action
```

Anything lacking that chain is read-only metadata at most.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
provenance and conflict tests
no uncontrolled writes
device knowledge remains non-authoritative for playback
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F12:END -->

---

# 418. AP2-F13 — PERSISTENCE / MIGRATION / ASSETS / PACKAGING

<!-- MICHI_PHASE2:CONTRACT:R11-F13:BEGIN -->
PHASE_ID: AP2-F13
TITLE: PERSISTENCE / MIGRATION / ASSETS / PACKAGING
DEPENDENCIES: AP2-F06, AP2-F10
MUST_READ_ANCHORS: R11-G05-PERSISTENCE, R11-G08-TEST-AUTHORITY, R11-F13

## File ownership
CREATE:
```text
src/michi/infrastructure/audio_processing/ir_asset_store.py
src/michi/infrastructure/sqlite_audio_phase2_repository.py
tests/audio_phase2/test_phase2_persistence.py
tests/audio_phase2/test_ir_asset_store.py
```
MODIFY:
```text
src/michi/infrastructure/sqlite_settings.py
src/michi/bootstrap/__init__.py
pyproject.toml
```
FORBIDDEN:
```text
new Phase2 DB
version-suffixed table names
runtime pointer persistence
unhashed IR asset execution
```

## Implementation contract
Perform a single atomic schema `2 -> 3` migration in current settings DB.

Tables:

```text
audio_processing_profiles
audio_processing_selection
audio_ir_assets
dsd_user_policy
dop_user_confirmations
```

Update current recovery provenance tables/queries and define Phase2 era
requirements. Rebuildable evidence stays excluded.

`sqlite_audio_phase2_repository.py` is another repository boundary over the SAME
DB path; it is not another database lifecycle owner.

IR bytes use temp+fsync+atomic rename and SHA-256. Profile references immutable
content hash.

Update `pyproject.toml` package-data only after checking its current patterns;
wheel smoke must import QML and resource assets from the built wheel, not source
tree.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
fresh/v2/v3/future-schema tests
injected migration rollback
LKG parity
wheel/install smoke with Phase2 QML/assets
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F13:END -->

---

# 419. AP2-F14 — PHYSICAL / PERFORMANCE QUALIFICATION

<!-- MICHI_PHASE2:CONTRACT:R11-F14:BEGIN -->
PHASE_ID: AP2-F14
TITLE: PHYSICAL / PERFORMANCE / SOAK
DEPENDENCIES: AP2-F08, AP2-F09, AP2-F10, AP2-F13
MUST_READ_ANCHORS: R11-G07-REALTIME-SAFETY, R11-G08-TEST-AUTHORITY, R11-F14

## File ownership
CREATE:
```text
scripts/audio_phase2_lab.py
tests/audio_phase2/test_phase2_lab_contract.py
```
MODIFY:
```text
NONE
```
FORBIDDEN:
```text
nominal PASS without raw evidence
one DAC -> universal claim
performance threshold invented after run
```

## Implementation contract
F00/F14 freeze the test host and budget profile before the run.

Record:

```text
CPU baseline and DSP p50/p95/max
RSS baseline/checkpoints/final
XRUN/underrun evidence
latency method + result
pipeline generations
device/binding identity
source fixtures
graph/profile hashes
GStreamer/ALSA/kernel versions
```

Thresholds live in a versioned lab profile before measurement; do not choose a
passing threshold after seeing results.

Separate:

```text
functional software PASS
real GStreamer PASS
single-hardware PASS
multi-hardware evidence
```

No promotion across those levels.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
declared soak complete
zero forbidden XRUN/stale transitions
CPU/memory/latency within predeclared budget
raw artifacts retained
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F14:END -->

---

# 420. AP2-F15 — FINAL ADVERSARIAL SEAL

<!-- MICHI_PHASE2:CONTRACT:R11-F15:BEGIN -->
PHASE_ID: AP2-F15
TITLE: FINAL ADVERSARIAL SEAL
DEPENDENCIES: AP2-F00, AP2-F01, AP2-F02, AP2-F03, AP2-F04, AP2-F05, AP2-F06, AP2-F07, AP2-F08, AP2-F09, AP2-F10, AP2-F11, AP2-F12, AP2-F13, AP2-F14
MUST_READ_ANCHORS: R11-G00-PRECEDENCE, R11-G08-TEST-AUTHORITY, R11-G10-STOP-CODES, R11-G11-PATCH-PROTOCOL, R11-G13-ALIGNMENT, R11-F15

## File ownership
CREATE:
```text
scripts/verify_audio_phase2_closure.py
tests/audio_phase2/test_phase2_closure_contract.py
```
MODIFY:
```text
docs/audio/PHASE2_STATE.json
```
FORBIDDEN:
```text
self-awarded evidence
stale spec/context receipt
optional feature promoted by UI presence
```

## Implementation contract
Closure verifier consumes immutable receipts; it does not execute ad-hoc repair.

Required equality:

```text
receipt.spec_sha256 == current spec sha
receipt.baseline_head == PHASE2_BASELINE.baseline_head
tested_head == HEAD for software closure
phase state == CLOSED for every mandatory dependency
```

Physical closure requires referenced artifacts to validate independently.

Run adversarial checks for:

```text
stale callback
device unplug
engine loss
IR missing/corrupt
unknown Gst factory/property
readback mismatch
SQLite migration failure
future schema
QML teardown
wheel install
Direct regression
```

Only then set AP2 final state CLOSED/FROZEN.

## Mandatory work-unit sequence
```text
0 context receipt + alignment
1 preimage/source read
2 failing contract test
3 smallest pure/domain change
4 infrastructure integration only when prior layer green
5 readback/evidence integration
6 presentation last
7 focused tests
8 architecture/current-regression tests
9 diff inspection
10 pre-commit alignment + receipt
11 commit
```

## Exit gate
```text
all mandatory phase receipts valid
all closure gates exact-head PASS
claims scoped to evidence
state frozen
```

## Universal failure semantics
```text
unknown -> unknown/unavailable
stale -> abort stale candidate
newer user intent wins
no false success
no silent fallback
unproven post-destructive restore -> STOP safe
host loss during active processing -> runtime evidence invalid; retire
  effective revision; requested != effective; never leave EQ/Convolution/
  Processing ACTIVE in Signal Truth
child graph build failure -> predecessor effective state remains if the
  destructive boundary was not crossed
readback mismatch -> candidate abort
unsupported native strategy -> typed unavailable/refusal
```
<!-- MICHI_PHASE2:CONTRACT:R11-F15:END -->

---

# 421. PATCH PROTOCOL R11 — IMPLEMENTAR CASI COMO `.patch`

Each work unit must be expressible as a compact mutation map:

```text
PATCH_ID
PREIMAGE
CREATE
MODIFY
DELETE = normally NONE
SYMBOLS
INVARIANTS
RED_TESTS
IMPLEMENTATION_STEPS
GREEN_TESTS
ROLLBACK
STOP_CONDITIONS
```

Example:

```text
PATCH_ID: AP2-F04-WU02-GRAPHIC-DOMAIN

PREIMAGE:
  audio_processing.py exists from WU01
  no GraphicEqNode exists

MODIFY:
  src/michi/domain/audio_processing.py

CREATE:
  tests/audio_phase2/test_graphic_eq_domain.py

SYMBOLS:
  GraphicEqLayoutId
  GraphicEqNode

DO NOT TOUCH:
  gstreamer.py
  QML
  SQLite

RED:
  length/layout mismatch rejected
  gain > product bound rejected
  non-finite gain rejected

GREEN:
  immutable valid 10-band graph
  immutable valid 31-band graph

STOP:
  existing symbol with incompatible meaning
```

The prompt sent to a small coding model should contain this patch map and the
corresponding R11 contract anchor, not thousands of unrelated lines.

---

# 422. CODE GENERATION RULES R11

Generated implementation must prefer:

```text
frozen dataclasses for immutable plans/evidence
StrEnum/Enum for closed vocabulary
Protocol for application ports
typed error codes
pure functions for planners/compilers
composition root wiring
owner-thread state mutation
```

Avoid:

```text
dict[str, Any] across domain boundaries
magic string factory names in profile JSON
catch Exception: pass
contextlib.suppress around required backend mutation
implicit None == success
QML business logic
sleep-based synchronization
polling when subscription/event exists
global singleton created by import side effect
```

Every `except Exception` at an infrastructure isolation boundary must convert to
a typed failure or re-raise; it may not turn failure into effective success.

Every asynchronous callback carries enough identity to reject stale completion.

---

# 423. TEST COMMAND MATRIX R11

Exact commands are frozen in F00 based on the future repository state. The
minimum shape is:

```bash
python -m pytest -q tests/architecture/test_phase2_spec_contract.py
python -m pytest -q tests/audio_phase2/<work-unit-test>.py
python -m pytest -q tests/dac/<affected-current-contracts>.py
ruff check <changed-python-files>
python -m compileall -q src/michi
git diff --check
```

For GStreamer runtime:

```bash
python -m pytest -q -m gstreamer_runtime <phase2-runtime-tests>
```

For hardware:

```bash
python scripts/audio_phase2_lab.py ...
python scripts/verify_audio_phase2_closure.py ...
```

A plan must never bake an old total test count into a future definition of
correctness. Record exact commit + commands + result in receipts.

---

# 424. STOP / REFUSAL CODES R11

<!-- MICHI_PHASE2:CONTRACT:R11-G10-STOP-CODES:BEGIN -->
Specification/alignment:

```text
STOP_SPEC_NOT_FOUND
STOP_SPEC_AMBIGUOUS
STOP_SPEC_DUPLICATE_SECTION
STOP_CONTRACT_DUPLICATE
STOP_CONTRACT_MISSING
STOP_PHASE_DUPLICATE
STOP_PHASE_UNKNOWN
STOP_BASELINE_DRIFT
STOP_PREIMAGE_DRIFT
STOP_CROSS_PHASE_MUTATION
STOP_DEPENDENCY_OPEN
```

Processing:

```text
DSP_CAPABILITY_UNAVAILABLE
DSP_STRATEGY_UNAVAILABLE
DSP_FACTORY_UNAVAILABLE
DSP_FILTER_TYPE_UNSUPPORTED
DSP_GAIN_OUT_OF_RANGE
DSP_NYQUIST_VIOLATION
DSP_ASSET_MISSING
DSP_ASSET_HASH_MISMATCH
DSP_READBACK_MISMATCH
DSP_RUNTIME_STALE
DSP_RUNTIME_CONTRADICTED
PROCESSING_DIRECT_CONFLICT
DIRECT_PROCESSING_CONFLICT
```

DSD/DoP:

```text
DSD_SOURCE_UNPROVEN
DSD_NATIVE_UNSUPPORTED
DSD_PROCESSING_CONFLICT
DOP_UNSUPPORTED
DOP_CARRIER_UNPROVEN
DOP_MARKER_MISMATCH
```

Do not proliferate synonyms. Before adding a code, search this vocabulary and
existing product codes.
<!-- MICHI_PHASE2:CONTRACT:R11-G10-STOP-CODES:END -->

---

# 425. LEGACY SALVAGE R11 — FINAL DECISION

PORT:

```text
readback-first semantics
RBJ coefficient concepts
ISO31 center list
reviewed factory preset data
conversion-preview UX concept
generation/snapshot patterns from Home Audio
```

DO NOT COPY:

```text
EqBridge
legacy output profile proof semantics
legacy DoP
legacy Home Assistant authority
legacy test counts
```

Legacy code is not imported as a runtime package. Anything salvaged is rewritten
into current namespaces with current tests and provenance.

---

# 426. EXTERNAL RESEARCH R11 — IMPLEMENTATION CONSEQUENCES

Verified public documentation changes concrete choices:

```text
equalizer-nbands
  use as CORE candidate for Basic 10 / Advanced Graphic 31
  do not pretend its band API expresses every RBJ filter type

audioiirfilter
  candidate for full PEQ biquad cascade
  forces float working representation
  do not calculate coefficients in rate-changed callback

audiofirfilter
  candidate for bounded FIR/convolution
  explicit latency
  float working representation
  long kernels require performance gate

audioconvert
  configure dither/noise-shaping explicitly
  never accept defaults as hidden policy

dsdconvert
  representation/grouping tool only
  never call it DSD->PCM
```

Research can change a backend adapter without changing the semantic domain, which
is precisely why the compiler targets strategies rather than factories.

---

# 427. RETIRED R10 CONTRADICTIONS

R11 explicitly retires:

```text
numeric sections as machine context keys
minimum mode as productive context
Direct + DSP interaction rows
DacQuickPopup.qml
AudioProcessingPopup.qml
SignalPathPopup.qml
generic fictional michi-* Gst factories
"equalizer-nbands cannot be parametric" overcorrection
Basic Graphic -> mandatory lossy PEQ conversion
separate inline FIR node + convolution node duplication
implicit audioconvert dither defaults
new standalone Phase2 DB implication
no explicit internal PCM working format
```

These are not “alternative implementation options”. They are removed.

---

# 428. END-TO-END GOLDEN SCENARIOS R11

S1 Shared PCM, processing OFF:

```text
load -> Shared -> no processing -> playback
Signal Path: Shared / no processing claim
```

S2 Shared PCM, Basic EQ:

```text
draft -> compile -> F64 processing -> terminal shared conversion
-> readback -> commit
Signal Path: Processing active
```

S3 Direct DAC, processing OFF:

```text
existing qualification/plan/executor path unchanged
current Signal Truth parity
```

S4 user enables EQ during Direct:

```text
typed conflict
no path mutation
explicit user chooses Processed
managed/shared transaction
```

S5 specific DAC, Managed PCM + PEQ:

```text
stable identity -> binding -> terminal capability
-> processing graph -> managed sink
-> runtime evidence -> Processed
never Direct
```

S6 change DAC A->B while A playing:

```text
aa8 predecessor semantics preserved
B selected/pending
A active until destructive/commit rules say otherwise
```

S7 PEQ preset has band above current Nyquist:

```text
saved intent preserved
effective band inactive with reason
remaining graph runs
```

S8 IR missing:

```text
profile saved
apply refused
predecessor remains
no silent bypass
```

S9 Native DSD + EQ requested:

```text
typed conflict
explicit DSD->PCM option only
```

S10 DoP:

```text
DSD payload -> proven DoP packer -> carrier
no PCM DSP/resample
markers/carrier inspected
```

S11 newer media request during processing candidate:

```text
candidate stale -> abort
new request wins
```

S12 shutdown during worker prepare:

```text
late callback inert
no QObject resurrection
no background playback
```

These scenarios receive executable integration tests as their owning phases
close.

---

# 429. DEFINITION OF DONE R11

Phase2 CORE is not done because UI looks complete.

Required closure:

```text
spec alignment
authority parity
PCM Direct regression parity
Graphic EQ productive
PEQ productive
readback/evidence productive
Managed PCM productive if enabled in scope
Signal Truth coherent
persistence/migration
packaging
shutdown
runtime performance
declared physical gates
```

DSD/DoP closure is separate and cannot borrow PCM evidence.

Optional/post-core features do not block core unless explicitly activated:

```text
AutoEQ online provider
CamillaDSP sidecar
crossfeed
loudness
limiter
mixer
live dual-branch clickless switching
```

They must remain invisible/non-claiming until implemented.

---

# 430. FINAL KILLCRITIC R11 SEAL

Before any implementation commit, the reviewer asks:

```text
Does this preserve current Direct semantics?
Does a new fact have exactly one authority?
Could a stale callback win?
Could a default plugin behavior silently transform audio?
Is any capability inferred from absence?
Is any UI state ahead of backend readback?
Can an unavailable optional feature look functional?
Can a saved user graph be mutated by runtime adaptation?
Does persistence survive recovery/migration?
Does packaging include the new QML/assets?
Does a failure after destructive boundary converge safe?
```

If any answer is unknown:

```text
STOP_SPEC_AMBIGUOUS
```

R11 objective:

```text
not maximum code
not maximum features
not maximum line count

maximum executable certainty per token
```

The mega-plan can remain large for research depth while the implementation
packet stays bounded, deterministic and difficult to misread.

---

# 431. ALIGNMENT VERIFIER R11 — MACHINE GATE BEFORE EVERY PATCH

<!-- MICHI_PHASE2:CONTRACT:R11-G13-ALIGNMENT:BEGIN -->

`verify_audio_phase2_repository_alignment.py` must validate structure before it
validates implementation state.

Inputs:

```text
--repo
--phase
--mode pre-mutation|pre-commit|closure
```

Mandatory checks:

```text
ALIGN-01 exactly one tracked canonical spec
ALIGN-02 spec SHA == PHASE2_STATE.spec_sha256 once F00 is frozen
ALIGN-03 every top-level numeric section is unique
ALIGN-04 every CONTRACT id is unique and balanced
ALIGN-05 every PHASE id is unique and balanced
ALIGN-06 every MUST_READ_ANCHORS id exists exactly once
ALIGN-07 dependency phase states are CLOSED
ALIGN-08 frozen baseline commit is ancestor of HEAD
ALIGN-09 current branch/worktree file set obeys active-phase ownership
ALIGN-10 no retired Phase2 target filename has been created
ALIGN-11 required existing authority symbols still exist
ALIGN-12 current head has not drifted from an un-reconciled baseline
```

File-scope gate:

```python
def changed_paths(repo, baseline):
    committed = git("diff", "--name-only", f"{baseline}..HEAD")
    staged = git("diff", "--cached", "--name-only")
    unstaged = git("diff", "--name-only")
    untracked = git("ls-files", "--others", "--exclude-standard")
    return sorted(set(
        committed.splitlines()
        + staged.splitlines()
        + unstaged.splitlines()
        + untracked.splitlines()
    ))
```

The verifier loads `MICHI_AUDIO_PHASE2_R11_EXECUTION_MANIFEST.json` semantics
from the installed plan/state implementation, not from a conversational copy.

A changed path is legal iff:

```text
matches active phase CREATE/MODIFY scope
OR
has an explicit cross-phase exception receipt
```

`pre-mutation` additionally requires that the work unit has a recorded preimage
and that no unknown pre-existing dirty path overlaps the target files.

`pre-commit` requires:

```text
context receipt current
focused test receipt current
git diff --check clean
no STOP_* condition
```

`closure` requires every mandatory phase CLOSED and delegates physical claims
to the dedicated closure verifier; alignment cannot self-award hardware proof.

Failure prints one stable code and exits non-zero. It never edits files.

<!-- MICHI_PHASE2:CONTRACT:R11-G13-ALIGNMENT:END -->

---

# R11.1 CANONICAL RESTRICTED-ACTIVATION LAYER — §§432–440

> **PRECEDENCE:** §§432–440 override any earlier statement that requires
> exhaustive R32/R35/R36 physical closure or complete M11.5 runtime conformance
> before AP2-F00. They do **not** upgrade M11.4 physical evidence. They only
> redefine what is required to begin bounded Phase2 work.

# 432. R11.1 — WHY RESTRICTED ACTIVATION EXISTS

Current physical truth:

```text
R24 SMSL   PASS
R24 HA01   PASS
R25 SMSL   PASS
R25 HA01   PENDING
R32        DEFERRED_UPSTREAM_BLOCKER
R35        PENDING
R36        PENDING / XRUN environment blocker
PHYSICAL_VERDICT = INCOMPLETE
```

R32 is not merely interrupted by external power events. Multiple controlled
attempts reproduced a GStreamer 1.28.x lifecycle deadlock. Characterization has
been isolated into a disposable subprocess, but the Direct pipeline state
lifecycle remains in-process and can wedge under churn.

Therefore:

```text
DO NOT claim R32 PASS
DO NOT claim M11.4 physical closure
DO NOT launch repeated 8-hour soaks as a development gate
```

At the same time, F01–F04 are pure/domain/projection/compiler work and do not
need the unresolved Direct lifecycle path to be exercised productively.

# 433. PRE-AP2-01 — RESTRICTED ENTRY GATE

`PRE-AP2-01 PASS` requires all of:

```text
M11.3 = FROZEN
M11.4 software implementation = CLOSED
M11.4 tooling/finalization = CLOSED
R24 = PASS on both currently qualified DACs
at least one complete R25 physical campaign = PASS
all incomplete physical gates are explicitly classified
R32 = DEFERRED_UPSTREAM_BLOCKER, never PASS
R36/XRUN = DEFERRED_ENVIRONMENT when injection is unavailable
subprocess characterizer packaging/verifier gap = CLOSED
R32 receipt-sidecar integrity verifier gap = CLOSED
short development-readiness smoke = PASS
exact-head DAC/playback regression = PASS
unknown inherited P0/P1 = 0
M11.5A contract = FROZEN
R11.1 reconciled to exact implementation HEAD
worktree = understood/clean for baseline freeze
```

Not required for restricted F00:

```text
R32 8-hour PASS
R35 complete
R36 XRUN PASS where environment cannot inject
PASS_MULTI_HARDWARE
M11.5B runtime conformance
Native DSD runtime
DoP runtime
```

# 434. SHORT DEVELOPMENT-READINESS SMOKE — NOT R32

The short smoke is **not** a substitute for R32 and must never mutate R32 facts.

Purpose:

```text
prove the exact HEAD selected for Phase2 baseline has no immediate
DAC/playback regression under representative bounded use
```

Recommended bounded scenarios:

```text
A. steady Direct playback: 15–20 min
B. canonical sample-rate transitions: >= 50 controlled transitions
C. load/stop cycles: >= 20
D. Direct -> System -> Direct: >= 10 round trips where supported
```

Observe:

```text
XRUN
runtime errors
stale generation
Signal Truth contradiction introduced by current HEAD
USB/kernel errors
pipeline ownership
pump liveness
RSS before/after
UI/main-thread responsiveness
```

Verdict name:

```text
AP2_PREFLIGHT_SMOKE = PASS | FAIL | BLOCKED
```

Never:

```text
R32 = PASS
```

from this smoke.

# 435. REQUIRED CORRECTIVES BEFORE THE SMOKE

## 435.1 R32 sidecar independent verification

The semantic evaluator must verify, streaming:

```text
sidecar exists
gzip stream is readable OR explicitly marked partial for aborted run
actual SHA-256 == manifest SHA-256
actual JSONL receipt count == receipts_total
actual failed receipts == receipts_failed
sample rows are consistent with sidecar
```

A 64-hex string is not proof that the artifact exists.

## 435.2 Subprocess characterizer closure coverage

The canonical M11.4 verifier/wheel smoke must include:

```text
michi/infrastructure/audio_engines/subprocess_characterizer.py
michi/infrastructure/audio_engines/characterize_cli.py
tests/dac/test_v35_subprocess_characterizer.py
```

The installed-wheel gate must execute at least one real CLI characterization
fixture, not merely import the modules.

## 435.3 Cancellation / responsiveness

`SubprocessSourceCharacterizer` isolation prevents an infinite whole-process
freeze, but productive prepare must not block the Qt owner thread for the full
worker timeout.

Before F05, and preferably during PRE-AP2-01:

```text
characterization wait moved off owner/UI thread
newer prepare/Stop/output intent cancels or supersedes worker promptly
stale worker result cannot commit
concurrency policy is explicit
```

If this is not completed before F00, it becomes an explicit blocker for F05;
it cannot be silently forgotten.

# 436. M11.5A CONTRACT FREEZE — REQUIRED BEFORE F00

M11.5A freezes semantics, not full runtime implementation.

It must define:

```text
BitPerfectState vocabulary
proof ownership
Direct != bit-perfect
gapless ownership and same-format definition
cross-format transition semantics
Signal Truth vs conformance responsibility
DSD/DoP ownership
DSD->PCM ownership
failure/unknown vocabulary
physical evidence boundaries
```

Recommended ownership:

```text
Audio Phase 2:
  source-family runtime characterization extensions
  Native DSD execution
  DoP execution
  DSD->PCM execution
  family transition runtime

M11.5:
  conformance/proof semantics
  bit-perfect verdict rules
  gapless guarantee semantics
  transition verification rules

DAC-V35-140:
  qualification/promotion evidence or formally superseded scope
```

No second Signal Truth recorder, planner or transport authority is created.

# 437. AP2 PHASE ACCESS UNDER RESTRICTED ACTIVATION

After F00 closes:

```text
F01 ALLOWED
F02 ALLOWED
F03 ALLOWED
F04 ALLOWED
```

Hard gate:

```text
GST_LIFECYCLE_GATE != PASS
    -> F05 LOCKED
    -> F06 LOCKED
```

F07–F10 additionally require their DSD/DoP ownership and runtime prerequisites.

F11 UI may not expose dead controls for locked runtime capabilities.

# 438. GST_LIFECYCLE_GATE

This gate closes only after a short reproducer demonstrates that the chosen
mitigation prevents the known GStreamer state-transition wedge under the
declared stress envelope.

Acceptable mitigation classes:

```text
state-transition serialization with proven settled-state protocol
lifecycle owner isolation
process isolation for hazardous lifecycle branch
upstream-fixed GStreamer version with reproducer regression proof
```

Not sufficient:

```text
arbitrary sleep
lowering R32 churn until it "passes"
ignoring stuck thread
catching Python exception around a C call that never returns
```

Required result:

```text
short reproducer no longer wedges
normal playback regression green
Direct semantics unchanged
newer intent/stale generation gates green
main/UI thread not exposed to unbounded lifecycle call
```

# 439. AP2-F00 R11.1 ENTRY

F00 is governance/baseline only. Product code remains forbidden.

Required:

```text
PRE-AP2-01 = PASS
M11.5A = FROZEN
exact HEAD captured
one canonical R11.1 spec installed
spec SHA frozen
phase2_context.py installed
alignment verifier installed
full relevant software regression green
```

F00 records physical debt honestly:

```json
{
  "m11_4_physical_verdict": "INCOMPLETE",
  "deferred_gates": [
    "R32_UPSTREAM_GSTREAMER_LIFECYCLE",
    "R35_PENDING",
    "R36_PENDING_OR_ENVIRONMENT"
  ],
  "restricted_phase2_limit": "AP2-F04"
}
```

# 440. R11.1 FINAL RULE

Restricted activation means:

```text
we start safe independent Phase2 work sooner
```

It does not mean:

```text
we erase failed/unfinished physical evidence
we call an upstream-blocked soak PASS
we build DSP runtime on top of a known lifecycle defect
```

The next implementation boundary is:

```text
PRE-AP2-01
-> AP2-F00
-> F01–F04
-> GST_LIFECYCLE_GATE
-> F05+
```

