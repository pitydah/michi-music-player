# MICHI MUSIC PLAYER — DAC CANONICAL EFFECTIVE SPEC

**Status:** CANONICAL / IMPLEMENTATION-SEALED EXECUTABLE AUTHORITY  
**Engineering revision:** V3.5 — Pre-Stable Immediate DAC Integration Seal, Deterministic OpenCode Wiring & Release-Gate Contract  
**Platform:** Linux first  
**Primary target:** M11.4 DAC integration NOW, during pre-Stable development; this integration is a prerequisite for Player Stable, not a post-Stable feature  
**Language boundary:** Python 3.11+/PySide6/QML application, GStreamer primary playback, Python subprocess helper + ctypes/libasound for the current pre-Stable M11.4 implementation; no Rust/native build requirement for the DAC path required before Stable 1.0  
**Supersedes for implementation:** V3.4, V3.3, V3.2, V3.1, V3 and all contradictory or broader wording in the DAC Research Corpus. Historical execution slices remain rationale only unless mapped by §0E.

---

> [!NOTE]
> **V3.5 timing correction:** M11.4 DAC integration is current pre-Stable work. The application does not become Stable first and then receive DAC integration. Stable is the acceptance gate this work must help satisfy.


> [!IMPORTANT]
> This is the **only DAC implementation authority for the DAC work being implemented now, before Player Stable**. “Stable” in this document names an acceptance/release gate; it never means “wait until the application is Stable before implementing DAC support.”
>
> The Research Corpus is valuable for rationale, discarded alternatives, experiments,
> post-stable ideas, and provenance, but agents MUST NOT derive implementation authority
> from it.
>
> If this file and the Research Corpus differ, **this file wins**.

---

# 0AA. IMPLEMENTATION TIMING CONTRACT — DAC WORK HAPPENS NOW, PRE-STABLE

This section has temporal precedence over every older phrase in this document or Research Corpus.

```text
IMPLEMENTATION_PHASE        = NOW / PRE-STABLE
M11_4_DAC_STATUS            = REQUIRED CURRENT DEVELOPMENT WORK
PLAYER_STABLE_DEPENDENCY    = M11.4 DAC CORE MUST BE IMPLEMENTED BEFORE PLAYER STABLE
WAIT_UNTIL_STABLE           = FORBIDDEN
POST_STABLE_DEFAULT         = FALSE
```

Normative interpretation:

- **M11.4 is implemented now**, on the current pre-Stable codebase.
- “Stable core”, “Stable target”, “Stable blocker”, and similar wording describe the **quality bar that must be reached before the application can be declared Stable**. They do not schedule the work after Stable.
- `DAC-V35-000` through `DAC-V35-100` are current pre-Stable implementation work.
- `DAC-V35-110` physical qualification starts as soon as the first real Direct vertical exists and must be completed before any release/marketing claim that depends on that evidence; it is not deferred merely because the rest of the player is unfinished.
- Conditional additions such as qualified hardware volume or DSD/DoP may also be implemented during the same pre-Stable cycle after the mandatory PCM Direct path is sealed. They are not automatically post-Stable; they simply cannot block the mandatory PCM Direct path unless the product milestone explicitly promotes them.
- Only items explicitly labeled **POST-STABLE ONLY** remain deferred beyond the first Stable release.

Scheduling rule for agents:

```text
wrong:  finish Player Stable -> begin DAC integration
right:  current pre-Stable Player -> implement M11.4 DAC -> verify -> continue remaining pre-Stable work -> Player Stable
```

Any historical section that appears to defer discovery, Direct output, exact ALSA qualification, source-native switching, Signal Truth, reconnect, fixed-volume safety, first-sample integrity, tail integrity, or the premium DAC UI until after Stable is **SUPERSEDED by this section and §0E/§390/§409–§410**.

---

# 0A. MANDATORY AI RELOAD CONTRACT — THIS FILE IS EXTERNAL ENGINEERING MEMORY

This document is not merely a one-time implementation plan. It is the **persistent external memory** for Michi DAC engineering. Context-window loss, conversation truncation, agent hand-off, model changes, and long implementation sessions MUST NOT cause the DAC architecture to be reconstructed from memory.

Machine-oriented authority card:

```text
CANONICAL_FILE = docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md
CANONICAL_REVISION = V3.5
RELOAD_POLICY = REQUIRED_ON_EVERY_DAC_TASK
MEMORY_IS_AUTHORITY = FALSE
CONVERSATION_IS_AUTHORITY = FALSE
FILE_IS_AUTHORITY = TRUE
RESEARCH_REQUIRED_WHEN_UNRESOLVED = TRUE
SILENT_ASSUMPTION_ALLOWED = FALSE
```

For **every** DAC-related question, implementation request, bug, review, refactor, test failure, design discussion, or OpenCode task, the agent MUST perform this sequence before answering or editing code:

```text
1. REOPEN this canonical file from storage.
2. READ §0AA–§0K, then §396–§410 for the implementation seal.
3. SEARCH THE ENTIRE FILE for the exact topic and its synonyms.
4. READ the relevant normative section(s) in full.
5. READ the matching ACTIVE `DAC-V35-*` work package / NO-GO gate / Definition of Done; older slice namespaces are reference-only.
6. RECONCILE the plan with the current repository code before proposing a patch.
7. If the answer is not present or evidence has changed:
      classify the gap -> research upstream -> falsify -> update THIS file first.
8. Only then answer the user or implement.
```

**Important context-window rule:** “re-read the file” does **not** mean blindly injecting all 18k+ lines into a model context on every turn. It means the agent MUST reopen the current file, re-read this authority entrypoint, run full-file retrieval/search, and load the complete relevant sections. For architecture-changing decisions, contradictions, scope changes, or new features, the agent MUST additionally inspect all cross-references and global NO-GO gates that can affect the decision.

The agent MUST NOT:

```text
answer from remembered conversation state alone
use an old copied excerpt as if it were current authority
assume a previous agent's summary is complete
implement a feature because it appears in the Research Corpus
invent a missing DAC capability or Linux behavior
continue coding after discovering a contradiction without updating the plan
```

Before a code-changing response, the agent SHOULD state internally which canonical sections govern the change. If a new decision is required, the decision belongs in this file before it belongs in production code.

---

# 0B. AI RETRIEVAL MAP — WHAT TO RE-READ FOR COMMON QUESTIONS

Use this table as a retrieval index after reopening the file. Search terms are intentionally redundant so a new agent can recover the correct authority even with little conversational context.

| Question domain | Mandatory full-file searches | Minimum sections to read before answering |
|---|---|---|
| DAC identity / duplicate devices | `Stable DAC Identity`, `USB↔ALSA`, `correlation`, `deduplication`, `identity` | discovery/identity contract + evidence invalidation + current gates |
| Supported PCM rates / bit depth | `exact-open`, `rate_near`, `significant bits`, `capability truth`, `hw_params` | exact-open + readback + capability evidence sections |
| Direct / exclusive path | `DAC Direct`, `alsasink`, `audio-sink`, `exclusive`, `EBUSY` | Direct policy + sink seam + fallback policy |
| Volume | `VOLUME ARCHITECTURE`, `FIXED`, `DEVICE_HARDWARE`, `ALSA CONTROL` | volume contract + safety + hardware qualification |
| Sample-rate switching | `SAMPLE-RATE SWITCHING`, `transition`, `resync` | transition classifier + R25 + tail/drain rules |
| Gapless / clicks / truncation | `GAPLESS`, `FIRST-SAMPLE`, `DRAIN`, `TAIL` | gapless + first-sample + R35 |
| XRUN / stability | `XRUN`, `buffer`, `sw_params`, `soak` | recovery transparency + buffer policy + R32/R36 |
| DSD / DoP | `DSD`, `DoP`, `audio/x-dsd` | DSD architecture + DoP contract + R30; remember separate promotion gate |
| Signal path / bit-perfect | `SIGNAL TRUTH`, `BIT-PERFECT`, `contradiction` | evidence precedence + Signal Truth + verdicts + R28 |
| UI / Device Setup | `DEVICE SETUP`, `DAC CARD`, `progressive disclosure` | premium UX + safe defaults + read model |
| Profile / known DAC | `DAC PROFILE`, `MICHI VERIFIED`, `profile precedence` | profile tiers + evidence precedence + verified seal |
| Michi own hardware | `MICHI-NATIVE DAC CONTROL PLANE` | native control plane + canonical USB/ALSA boundary |
| Competitive benchmark | `CROSS-PLAYER`, `Roon`, `Audirvana`, `HQPlayer`, `JRiver`, `foobar2000` | V3.3 benchmark + quality filter |

If multiple rows apply, read all corresponding normative sections.

---

# 0C. QUALITY-FIRST FEATURE ADMISSION GATE — PREMIUM DOES NOT MEAN FEATURE-RICH

Michi DAC quality is measured by **correctness, determinism, transparency, safety, compatibility and refinement**, not by the number of switches in Settings.

Priority order is fixed:

```text
P0  signal correctness / no silent conversion
P0  deterministic ownership and lifecycle
P0  volume safety
P0  truthful runtime evidence
P1  robust device compatibility / reconnect / transition quality
P1  clear premium UX with excellent defaults
P1  diagnosability and reproducibility
P2  performance optimization after correctness is proved
P3  optional audiophile features
```

A new DAC feature is admitted to the current pre-Stable DAC implementation / Stable-release scope only when **all** are true:

```text
A. It solves a real user or hardware problem.
B. It improves at least one P0/P1 quality dimension.
C. It can be tested or falsified objectively.
D. It does not create a second playback/device authority.
E. It has a bounded failure mode and safe retreat.
F. Its maintenance burden is proportionate to its value.
G. Its UI can remain contextual or invisible when not needed.
```

If any item is false, the default disposition is:

```text
DEFER / LAB-ONLY / POST-STABLE / REJECT
```

Feature count is never a competitive KPI. A smaller path that is better tested and easier to explain outranks a broader path with ambiguous behavior.

---

# 0D. CURRENT PRODUCT DECISION SNAPSHOT — READ THIS AFTER EVERY RELOAD

This is the compact state vector for agents recovering from a short context window. It summarizes current authority but does not replace the detailed sections.

```text
IMPLEMENTATION TIME   NOW / PRE-STABLE; M11.4 is a prerequisite for Player Stable
PLATFORM             Linux first
PRIMARY DEVICE       local USB DAC
PRIMARY FORMAT       PCM stereo
PRIMARY ENGINE       existing GStreamer M11.3 runtime
DIRECT TRANSPORT     ALSA physical hw endpoint
DESKTOP MODE         Shared remains separate and honestly labeled
AUTHORITY MODEL      one canonical DAC model; no new DAC engine
CAPABILITY TRUTH     exact current runtime evidence > profile knowledge
RATE POLICY          source-native; no hidden global upsampling
VOLUME CORE          FIXED mandatory; qualified hardware volume conditional
DSP                   outside current M11.4 DAC core; separate pre-Stable/post-core work may follow
DSD / DoP            separate conditional promotion gate; may occur pre-Stable after mandatory PCM path
FALLBACK              never silent when semantics change
SIGNAL REPORTING      requested -> decoded -> effective -> negotiated
PROFILE ROLE          recommendation/known behavior, never runtime authority
VERIFICATION          physical hardware matrix required for Michi Verified
UX                    safe defaults + progressive disclosure + few controls
COMPETITIVE GOAL      quality density, not feature parity
AI BEHAVIOR           load root AGENTS.md -> reopen/search/read this file on every DAC task
```

If a future proposal contradicts this snapshot, the agent MUST locate the detailed governing sections and update the canonical document through the current V3.5 implementation-seal sections (§396–§410) before implementing the contradiction.


---

# 0E. ACTIVE EXECUTION MANIFEST — ONLY THESE WORK PACKAGES ARE EXECUTABLE

This section exists to prevent an agent with a short context window from executing an old but technically plausible slice.

**Normative rule:** only the V3.5 work packages listed below are executable now for the current pre-Stable M11.4 integration. `DAC-V35-000` through `DAC-V35-100` are mandatory work that must land before Player Stable. Every older implementation sequence — including `DAC-001…`, `DISC-*`, `DAC-PREMIUM-*`, and V3.2/V3.3 execution slices — is **HISTORICAL / REFERENCE ONLY** unless the V3.5 table explicitly maps it.

```text
ACTIVE_SERIES = DAC-V35-*
OLD_SERIES_EXECUTABLE = FALSE
SEARCH_RESULT_IS_AUTHORITY = FALSE
ACTIVE_MANIFEST_IS_AUTHORITY = TRUE
```

| Order | Work package | Status | Required before Player Stable | Canonical outcome |
|---:|---|---|---|---|
| 0 | `DAC-V35-000` Repository/agent alignment | REQUIRED FIRST | YES | baseline verified, `AGENTS.md` installed, active spec path fixed |
| 1 | `DAC-V35-010` Device identity + discovery | ACTIVE | YES | one stable physical DAC model + generation-safe ALSA binding |
| 2 | `DAC-V35-020` Exact ALSA qualification | ACTIVE | YES | subprocess-isolated exact `hw:` probe with post-commit readback |
| 3 | `DAC-V35-030` Persistence + output profile | ACTIVE | YES | schema v2, selected DAC/profile persisted, qualification cache rebuildable |
| 4 | `DAC-V35-040` Output planner + output transaction | ACTIVE | YES | deterministic plan before hardware/backend mutation |
| 5 | `DAC-V35-050` GStreamer Direct executor | ACTIVE | YES | existing `playbin3` + injected strict ALSA sink; no engine rewrite |
| 6 | `DAC-V35-060` Volume authority migration | ACTIVE | YES | FIXED Direct mode cannot silently use generic pipeline attenuation |
| 7 | `DAC-V35-070` Runtime evidence + Signal Truth | ACTIVE | YES | requested/decoded/effective/negotiated path with contradiction handling |
| 8 | `DAC-V35-080` Disconnect/reconnect + transitions | ACTIVE | YES | deterministic failure/rebind; no speaker fallback |
| 9 | `DAC-V35-090` Premium DAC UI | ACTIVE | YES | DAC controls separated from Audio Engine; mode-aware volume |
| 10 | `DAC-V35-100` Automated verification + documentation seal | ACTIVE | YES | one GO/NO-GO command + docs/status parity |
| 11 | `DAC-V35-110` Physical PCM promotion | PRE-STABLE PHYSICAL LAB | YES FOR DECLARED VERIFIED/RELEASE CLAIMS | R19–R29/R32–R36 applicable evidence on real hardware |
| 12 | `DAC-V35-120` Qualified hardware volume | CONDITIONAL | NO | only after R26/R27 on each supported mapping |
| 13 | `DAC-V35-130` Signed downloadable profile bundles | POST-STABLE ONLY | NO | remote update/signature machinery; not required for PCM Direct 1.0 |
| 14 | `DAC-V35-140` DSD / DoP | SEPARATE PROMOTION; MAY BE PRE-STABLE | NO | R30 and separate implementation/QA gate |

### Supersession map

```text
DISC-001..005
    -> rationale/input for DAC-V35-010/020 only

DAC-PREMIUM-001..009
    -> rationale/input only
    -> execution replaced by DAC-V35-030..110

DAC-001..012 and older numbered sequences
    -> historical rationale only

V3.2/V3.3 signed-profile work
    -> DAC-V35-130 POST-STABLE ONLY

V3.2/V3.3 DSD/DoP work
    -> DAC-V35-140 separate promotion; timing may be pre-Stable after PCM core
```

An agent MUST NOT start work package `N+1` while a required gate from package `N` is red, waived implicitly, or unknown.

---

# 0F. REPOSITORY BASELINE SEAL — NEVER PATCH AN UNKNOWN MAIN

V3.5 was reconciled against:

```text
repository     = https://github.com/pitydah/michi-music-player
branch         = main
observed_head  = 1b5e3f84d84d45873147ae7ad1a633de086a7e85
observed_date  = 2026-09-11
```

Important baseline facts at that HEAD:

```text
PlaybackSessionService is the sole active playback sequence/navigation authority.
PlaybackService is the sole PlaybackState mutation authority.
PlaybackBridge.set_volume() delegates to PlaybackService.set_volume().
PlaybackService.set_volume()/restore_volume() currently call AudioPort.set_volume().
AudioTransportRouter.set_volume() delegates to the bound engine.
GStreamerAudioPort still owns a generic playbin3 pipeline-volume surface.
SettingsView.qml still renders a generic 0..100 playback volume slider + mute button.
AudioEngineSettingsSection is already a separate engine-management surface.
ApplicationContainer/bootstrap is the only composition root allowed to wire presentation + infrastructure.
CURRENT_SCHEMA_VERSION in sqlite_settings.py is 1 at this baseline.
```

## Mandatory repository-alignment gate

Before the first code change in **every** V3.5 work package:

```bash
git status --short
git rev-parse HEAD
```

Then:

```text
IF HEAD == observed_head:
    continue using this exact V3.5 mapping.

IF HEAD != observed_head:
    DO NOT blindly apply line-oriented or filename-oriented patches.
    Re-read these critical files from current HEAD:
      src/michi/application/playback_service.py
      src/michi/application/playback_session_service.py
      src/michi/application/audio_transport_router.py
      src/michi/application/audio_engine_service.py
      src/michi/application/audio_engine_registry.py
      src/michi/application/ports.py
      src/michi/infrastructure/audio_engines/gstreamer.py
      src/michi/infrastructure/audio_engines/mpd.py
      src/michi/infrastructure/sqlite_settings.py
      src/michi/bootstrap/__init__.py
      src/michi/presentation/playback_bridge.py
      src/michi/presentation/qml/views/SettingsView.qml
      src/michi/presentation/qml/views/AudioEngineSettingsSection.qml
      pyproject.toml
    Compare ownership/lifecycle/API assumptions with §0F–§0K and §396–§410.
    Update THIS canonical spec first if a governing assumption changed.
```

A changed HEAD is not automatically a blocker. An **unreconciled** changed HEAD is.

---

# 0G. FINAL STABLE TECHNOLOGY DECISIONS — NO IMPLEMENTER CHOICE REMAINS

The following choices are CLOSED for PCM Direct Stable 1.0.

## 0G.1 ALSA exact-open helper

`michi-alsa-probe` remains the process-isolation boundary, but **it is not a Rust binary in Stable 1.0**.

Canonical implementation:

```text
product process
  -> MichiAlsaProbeAdapter
  -> subprocess using the SAME Python interpreter
  -> python -m michi.infrastructure.audio_devices.alsa_probe_cli
  -> ctypes bindings in alsa_ctypes.py
  -> libasound.so.2
  -> ALSA hw:CARD,DEV
```

Why this is final:

```text
+ preserves process isolation for risky/native ALSA calls
+ preserves versioned JSON protocol
+ needs no Cargo/maturin/native wheel build pipeline
+ respects the repository's Python/setuptools architecture
+ uses ALSA's native API instead of parsing aplay text
+ can later be replaced by a Rust helper behind the same JSON protocol without changing application contracts
```

Product invocation MUST use:

```python
[
    sys.executable,
    "-m",
    "michi.infrastructure.audio_devices.alsa_probe_cli",
    ...,
]
```

The optional console-script alias:

```toml
[project.scripts]
michi = "michi.__main__:main"
michi-alsa-probe = "michi.infrastructure.audio_devices.alsa_probe_cli:main"
```

exists for diagnostics. Product code MUST NOT depend on `$PATH` resolution of that alias.

Stable **forbids**:

```text
Rust/Cargo as a required build dependency
maturin/PyO3 solely for DAC probing
shelling out to aplay and parsing localized human output
using pyalsaaudio as an undeclared native extension shortcut
running exact-open probes in the GUI/Qt owner process
```

If `libasound.so.2` cannot be loaded:

```text
Direct DAC availability = UNAVAILABLE
reason = ALSA_RUNTIME_MISSING
Shared/reference engines remain usable.
Application startup must not crash solely because Direct DAC support is unavailable.
```

## 0G.2 Hotplug

Stable Linux hotplug uses:

```text
pyudev monitor -> normalized DeviceObservation -> AudioDeviceRegistry
```

Add Linux-only dependency:

```toml
"pyudev>=0.24; sys_platform == 'linux'"
```

`pyudev` is observation only. It never decides canonical identity, output policy, supported formats, or playback behavior.

## 0G.3 Stable Direct executor

```text
GStreamer = ONLY Stable 1.0 Direct executor
Qt Multimedia = Shared/reference engine only
MPD = existing managed engine; no premium Direct parity claim in Stable 1.0
```

Selecting Direct while the active engine is not GStreamer returns:

```text
ENGINE_UNSUPPORTED_FOR_DIRECT
```

Michi MUST NOT silently switch engines as a side effect of selecting a DAC.

---

# 0H. CLOSED OWNERSHIP / API SEAL — ESPECIALLY VOLUME

## 0H.1 Existing owners remain owners

```text
PlaybackSessionService -> playback sequence/navigation authority
PlaybackService        -> PlaybackState authority
AudioEngineService     -> selected/active engine authority
AudioDeviceRegistry    -> physical DAC identity + current binding read model
AudioOutputProfileService -> user output-profile persistence authority
OutputSessionService   -> active output plan/session transaction authority
VolumePolicyService    -> volume execution policy authority
OutputSessionEvidenceRecorder -> append/current session evidence authority
```

No new service may own Queue, Playlist, PlaybackState, AudioEngineState, or duplicate the current playback session.

## 0H.2 Exact pre-playback integration seam

Do **not** make `PlaybackSessionService` understand DACs.

Add one application port injected into `PlaybackService`:

```python
class PlaybackOutputTransactionPort(Protocol):
    def prepare_for_media(self, path: Path) -> str:
        """Return opaque transaction token or raise typed output error."""
        ...

    def commit_media(self, token: str, path: Path) -> None:
        ...

    def abort_media(self, token: str, reason: str) -> None:
        ...

    def release_active(self, reason: str) -> None:
        ...
```

Canonical request order:

```text
PlaybackSessionService._request(candidate)
  -> PlaybackService.load_and_play(path)
       1. output_tx.prepare_for_media(path)
       2. AudioPort.load(path)
       3. AudioPort.play()
       4. backend media accepted
       5. output_tx.commit_media(token, path)
       6. PlaybackService commits existing playback acceptance semantics

Any failure before commit:
       output_tx.abort_media(token, typed_reason)
       existing PlaybackService request transaction terminates normally

stop()/terminal engine loss:
       AudioPort stop semantics first as currently required for safety
       output_tx.release_active(reason)
```

The output transaction prepares/executes the output path but **does not select the next track and does not mutate PlaybackState**.

For Shared/reference mode use a `SharedOutputTransaction` implementation that is intentionally minimal/no-op with truthful mode evidence. This keeps `PlaybackService` constructor deterministic in production; there is no `None`/optional behavior branch.

## 0H.3 Exact volume migration

The current direct chain:

```text
QML -> PlaybackBridge -> PlaybackService -> AudioPort -> engine pipeline volume
```

MUST become:

```text
QML -> PlaybackBridge -> PlaybackService
                         |
                         v
                  VolumePolicyService
                         |
          +--------------+------------------+
          |                                 |
       Shared                          Direct DAC
          |                                 |
 AudioPort.set_volume          FIXED / qualified HW policy
```

`PlaybackService` remains the sole writer of `PlaybackState.volume` and `PlaybackState.muted`, but it stops choosing the execution mechanism.

New port:

```python
@dataclass(frozen=True, slots=True)
class AppliedVolume:
    requested_percent: int
    effective_percent: int
    muted: bool
    mode: str
    signal_mutated: bool
    device_db: float | None = None

class PlaybackVolumePort(Protocol):
    def apply_volume(self, value: int) -> AppliedVolume: ...
    def apply_muted(self, muted: bool) -> AppliedVolume: ...
    def restore(self, value: int, muted: bool) -> AppliedVolume: ...
```

Production `PlaybackService` constructor becomes conceptually:

```python
def __init__(
    self,
    audio_port: AudioPort,
    output_tx: PlaybackOutputTransactionPort,
    volume_port: PlaybackVolumePort,
) -> None:
    ...
```

No long-term optional fallback parameter is allowed in production wiring. Tests may use explicit fakes.

### Shared/reference mode

```text
VolumePolicyService delegates to AudioPort.set_volume()/set_muted().
Effective volume is confirmed by successful command semantics available today.
No Direct/bit-perfect claim is made.
```

### Direct + FIXED

```text
pipeline gain = unity / 100%
slider = disabled in UI
PlaybackState.volume = 100
attempt to set volume != 100 through stale/programmatic UI -> OutputVolumeLockedError
no hidden attenuation
mute remains an explicit user command; while muted, Signal Truth verdict is MUTED/NO-AUDIBLE-SIGNAL, never BIT_PERFECT_ACTIVE
unmute restores unity before the path can regain Direct-verification status
```

### Direct + DEVICE_HARDWARE

Not mandatory for the first Player-Stable PCM Direct core. It may still be implemented during the current pre-Stable cycle after R26/R27 qualify an exact ALSA control mapping for the exact physical device/profile/environment.

```text
requested percent -> qualified mapping -> ALSA control write -> mandatory readback
PlaybackState uses effective readback projection
external knob event -> readback -> VolumePolicyService -> PlaybackService convergence callback
stale generation/control identity -> reject event
```

### Direct + DSP_SOFTWARE

Outside the current M11.4 DAC slice, but **not automatically post-Stable**. Its timing is owned by the separate DSP roadmap; if DSP is scheduled before Player Stable, it follows after the DAC playback path is sufficiently stable. When enabled it must explicitly set `signal_mutated=True`; it can never inherit a fixed-output bit-perfect verdict.


## 0H.4 Composition root and lifecycle — exact production wiring

`src/michi/bootstrap/__init__.py` remains the **only** place allowed to construct the concrete graph.

Construction order after persistence preflight:

```text
01 SQLiteSettingsRepository.open_for_startup() + existing recovery preflight
02 existing SettingsService / Library / Queue foundations
03 existing engine providers -> AudioEngineRegistry -> AudioEngineService -> AudioTransportRouter
04 SysfsSnapshot + UdevObserver objects (constructed, NOT started yet)
05 AudioDeviceRegistry
06 SQLiteAudioOutputRepository -> AudioOutputProfileService
07 MichiAlsaProbeAdapter -> DacQualificationService
08 GStreamerDirectOutputExecutor + executor mapping {GSTREAMER: executor}
09 AudioOutputPlanner
10 OutputSessionEvidenceRecorder
11 OutputSessionService(executor mapping, planner, device/profile/qualification/engine read ports)
12 VolumePolicyService(router, OutputSessionService read model, optional qualified ALSA control port)
13 PlaybackService(router, output_tx=OutputSessionService, volume_port=VolumePolicyService)
14 existing Queue/PlaybackSession/coordinators using that SAME PlaybackService
15 PlaybackBridge + NEW AudioOutputBridge + existing bridges
16 register context properties/QML
17 start existing PlaybackSessionService lifecycle
18 start UdevObserver LAST, after every consumer/subscriber exists
```

`GStreamerDirectOutputExecutor` must be wired to the same canonical GStreamer provider/backend instance used by the engine registry. Never instantiate a second hidden GStreamer player for DAC output.

New executor protocol:

```python
class AudioOutputExecutorPort(Protocol):
    @property
    def engine_id(self) -> AudioEngineId: ...

    def prepare(self, plan: OutputPlan) -> str:
        """Configure executor and return opaque receipt; no playback command."""
        ...

    def commit(self, receipt: str) -> None: ...
    def abort(self, receipt: str, reason: str) -> None: ...
    def release(self, reason: str) -> None: ...
```

`OutputSessionService` receives an immutable mapping of engine id -> executor. Stable contains one Direct-capable entry: GStreamer. Missing mapping is a typed `ENGINE_UNSUPPORTED_FOR_DIRECT`, not a fallback.

Shutdown order:

```text
01 stop accepting new presentation intents / dispose DAC bridge subscriptions
02 PlaybackSessionService.stop() (existing subscription ownership)
03 issue existing PlaybackService.stop() safety command when transport is active
04 OutputSessionService.release_active("shutdown")
05 stop ALSA control observer if DAC-V35-120 is active
06 stop UdevObserver and discard queued generations
07 close/unbind engines through existing M11.3 lifecycle/router/provider contracts
08 close persistence through existing application shutdown path
```

Every start/stop/close method added by M11.4 MUST be idempotent. Constructors subscribe to nothing that can emit before the graph is complete unless the existing architecture already guarantees that behavior.

---

# 0I. PERSISTENCE / SCHEMA SEAL — USER AUTHORITY VS REBUILDABLE EVIDENCE

At baseline HEAD, `CURRENT_SCHEMA_VERSION = 1`. V3.5 Stable adds migration **v1 -> v2**.

If repository alignment discovers that `CURRENT_SCHEMA_VERSION` is no longer 1, the agent MUST allocate the next sequential migration and update this section before implementation. Never reuse a schema version.

## Authoritative user tables

```sql
CREATE TABLE IF NOT EXISTS audio_output_profiles (
    profile_id TEXT PRIMARY KEY,
    stable_device_id TEXT,
    path TEXT NOT NULL CHECK(path IN ('desktop','managed','hardware_direct')),
    rate_policy TEXT NOT NULL CHECK(rate_policy IN ('source_native','system')),
    volume_policy TEXT NOT NULL CHECK(volume_policy IN ('fixed','software','hardware')),
    fallback_kind TEXT NOT NULL CHECK(fallback_kind IN ('stop','ask','desktop_default','specific_device')),
    fallback_device_id TEXT,
    resync_delay_ms INTEGER NOT NULL DEFAULT 0 CHECK(resync_delay_ms >= 0),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_audio_output_profiles_device
ON audio_output_profiles(stable_device_id)
WHERE stable_device_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS audio_output_selection (
    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
    selected_profile_id TEXT,
    selected_device_id TEXT,
    updated_at_ms INTEGER NOT NULL,
    FOREIGN KEY(selected_profile_id) REFERENCES audio_output_profiles(profile_id)
);
```

These tables are **authoritative user state** and therefore join the recovery/provenance model in `sqlite_settings.py`.

Rules:

```text
a pre-v2 database may legitimately lack them during migration
an already-v2 database missing either table is structurally invalid
recovery/LKG logical provenance must include them once schema v2 is installed
no ALSA card index may be stored in either table
stable_device_id may be stored
```

## Rebuildable qualification cache

```sql
CREATE TABLE IF NOT EXISTS dac_qualification_cache (
    stable_device_id TEXT NOT NULL,
    environment_fingerprint TEXT NOT NULL,
    rate_hz INTEGER NOT NULL,
    transport_format TEXT NOT NULL,
    channels INTEGER NOT NULL,
    significant_bits INTEGER,
    supported INTEGER,
    strength TEXT NOT NULL,
    source TEXT NOT NULL,
    observed_at_ns INTEGER NOT NULL,
    evidence_json TEXT NOT NULL,
    PRIMARY KEY (
        stable_device_id,
        environment_fingerprint,
        rate_hz,
        transport_format,
        channels,
        significant_bits
    )
);
```

`dac_qualification_cache` is **rebuildable evidence**:

```text
exclude from authoritative/LKG logical equality
invalidate/ignore on environment fingerprint mismatch
never let cached positive evidence override current exact-open rejection
never let cached negative evidence override BUSY/REMOVED/TIMEOUT ambiguity
```

## Static Michi profile knowledge

Stable 1.0 profiles are package resources, not remotely updated bundles:

```text
src/michi/resources/dac_profiles/*.json
```

Add package-data explicitly. Signed downloadable bundles remain `DAC-V35-130` **POST-STABLE ONLY**.

---

# 0J. PRESENTATION WIRING SEAL — EXACT SURFACES

DAC settings MUST NOT be folded into `AudioEngineSettingsSection.qml`.

Canonical settings order:

```text
Settings
  Appearance and accessibility
  Playback
  Audio Engine          <- existing M11.3 section, engine only
  Audio Output / DAC    <- NEW M11.4 section
  Library
```

Create:

```text
src/michi/presentation/audio_output_bridge.py
src/michi/presentation/qml/views/AudioOutputSettingsSection.qml
src/michi/presentation/qml/components/DacDeviceCard.qml
src/michi/presentation/qml/components/DacVolumeControl.qml
src/michi/presentation/qml/components/SignalTruthPanel.qml
src/michi/presentation/qml/components/DacDiagnosticsDisclosure.qml
```

Modify `SettingsView.qml`:

```text
1. Keep AudioEngineSettingsSection intact.
2. Insert AudioOutputSettingsSection immediately AFTER AudioEngineSettingsSection and BEFORE Library.
3. Remove the generic Volume/Mute rows from the generic Playback panel once DacVolumeControl becomes canonical.
4. DacVolumeControl renders Shared/FIXED/HARDWARE semantics from AudioOutputBridge; it does not infer them from engine id in QML.
```

`PlaybackBridge` remains the canonical QML command surface for actual volume/mute intents so NowPlayingBar and Settings do not create two command paths. `AudioOutputBridge` exposes DAC/output-policy read models and output-policy intents; it does not mutate `PlaybackState`.

Required `AudioOutputBridge` read model fields:

```text
devices
selectedDeviceId
activeDeviceId
selectedProfileId
pathMode
availability
availabilityReason
volumeMode
volumeAdjustable
volumeLabel
currentRateHz
currentFormat
significantBits
signalTruthVerdict
signalTruthSummary
isDirect
isExclusiveObserved
isBusy
isReconnecting
diagnosticsAvailable
```

Required intents:

```text
refresh_devices()
select_device(stable_device_id)
select_path_mode(mode)
select_volume_mode(mode)
set_resync_delay_ms(value)
open_diagnostics()
```

No QML surface may accept raw ALSA `hw:N,M` as persisted identity.

---

# 0K. ONE EXECUTABLE DEFINITION OF DONE — NO “TESTS LOOK GREEN” VERDICT

V3.5 requires a repository command:

```bash
python scripts/verify_dac_m11_4.py
```

The script is an aggregator, not a fake proof generator. It MUST:

```text
1. verify repository alignment metadata exists
2. run DAC domain/unit tests
3. run AudioPort/engine regression tests
4. run PlaybackService/PlaybackSessionService regression tests
5. run GStreamer strict-sink fake/runtime tests where environment supports it
6. run persistence migration/recovery/provenance tests
7. run QML structural + offscreen runtime tests for AudioOutputSettingsSection
8. build the wheel
9. verify required DAC QML/resources are present in the wheel
10. run installed-wheel import/smoke for DAC Python modules
11. validate the canonical spec invariants relevant to filenames/forbidden calls
12. emit machine-readable `artifacts/dac_m11_4_verdict.json`
13. emit human-readable `artifacts/dac_m11_4_verdict.md`
```

Required JSON top-level shape:

```json
{
  "schema_version": 1,
  "commit": "<git sha>",
  "spec_revision": "V3.5",
  "automated_verdict": "GO|NO_GO",
  "physical_verdict": "NOT_RUN|PARTIAL|GO|NO_GO",
  "gates": [],
  "artifacts": [],
  "generated_at_utc": "..."
}
```

`automated_verdict=GO` MUST NOT be rendered to users as “Michi Verified”. Physical promotion remains separate.

### Stable PCM Direct release wording

Allowed after automated GO but before multi-hardware physical seal:

```text
IMPLEMENTATION COMPLETE — PHYSICAL QUALIFICATION PENDING
```

Allowed only after required physical matrix:

```text
PCM DIRECT VERIFIED FOR DECLARED HARDWARE / ENVIRONMENT MATRIX
```

Never:

```text
fully verified on all DACs
universal bit-perfect support
Roon-equivalent hardware compatibility
```


---

# 0. PURPOSE

The M11.4 DAC integration being implemented now, before Player Stable, must solve one bounded problem extremely well:

```text
A user connects a USB DAC.
Michi identifies it reliably.
Michi knows which Linux endpoint currently represents it.
Michi can prove whether an exact PCM configuration is openable.
Michi plans an output path before execution.
Michi executes one GStreamer → ALSA hw path.
Michi observes what Linux actually negotiated.
Michi refuses silent signal-policy degradation.
Michi survives disconnect/reconnect honestly.
Michi explains the evidence it actually has.
```

The Stable target is **not**:

```text
a universal USB Audio debugger
a UAC parser suite
a Linux audio policy manager
an automatic multi-engine recovery system
a community DAC database
a multi-DAC synchronizer
a subjective sound-quality optimizer
```

---

# 1. DOCUMENT AUTHORITY

Canonical hierarchy:

```text
1. docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md
2. §0E ACTIVE EXECUTION MANIFEST + the current V3.5 work package
3. Accepted ADR/DER referenced by the slice
4. Source code + current tests
5. Research Corpus for rationale only
```

Never:

```text
search the 30k+ line Corpus
find the most convenient old snippet
implement it
```

---

# 2. EPISTEMIC CLASSIFICATION

Every relevant statement is one of:

```python
from enum import Enum

class EpistemicKind(Enum):
    NORMATIVE_AXIOM = "normative_axiom"
    DEDUCTIVE_INVARIANT = "deductive_invariant"
    EMPIRICAL_HYPOTHESIS = "empirical_hypothesis"
```

Examples:

```text
AudioPort remains transport-only
→ NORMATIVE_AXIOM

OutputPlanner is deterministic
→ DEDUCTIVE_INVARIANT

A specific buffer reduces XRUNs on a DAC
→ EMPIRICAL_HYPOTHESIS
```

Empirical pioneer features require:

```text
prediction
falsification experiment
kill criterion
safe retreat
```

---

# 3. TEST / EVIDENCE TAXONOMY

Use these exact levels:

```python
class TestEvidenceLevel(Enum):
    DOMAIN_REFERENCE_TESTED = "domain_reference_tested"
    BACKEND_FAKE_TESTED = "backend_fake_tested"
    VIRTUAL_STACK_TESTED = "virtual_stack_tested"
    LINUX_INTEGRATION_TESTED = "linux_integration_tested"
    USB_GADGET_STACK_TESTED = "usb_gadget_stack_tested"
    PHYSICAL_HARDWARE_TESTED = "physical_hardware_tested"
    MULTI_HARDWARE_TESTED = "multi_hardware_tested"
```

Meaning:

```text
DOMAIN_REFERENCE_TESTED
Pure semantics/code model only.

BACKEND_FAKE_TESTED
Real adapter/service logic against deterministic fake backend.

VIRTUAL_STACK_TESTED
Real Linux audio stack with virtual PCM target.

LINUX_INTEGRATION_TESTED
Real Linux ALSA/GStreamer/PipeWire integration.

USB_GADGET_STACK_TESTED
Real USB host/HCD/snd-usb-audio path exercised against a controlled Linux UAC2 gadget.
This does not imply compatibility with a commercial physical DAC.

PHYSICAL_HARDWARE_TESTED
Real physical DAC in declared environment.

MULTI_HARDWARE_TESTED
Behavior reproduced across materially different hardware/environments.
```

A lower level never implies a higher one.

---

# 4. PRE-STABLE M11.4 SCOPE REQUIRED FOR PLAYER STABLE

First sealed hardware target being implemented now:

```text
Linux
USB DAC
PCM stereo
GStreamer
ALSA hw
44.1 / 48 / 96 / 192 kHz if device supports
16-bit
24 significant bits
S32 carrier where appropriate
Fixed output policy
Hotplug/reconnect
Strict no-silent-fallback
Core Signal Conformance
```

Not mandatory blockers for the first PCM Direct Stable-release gate (some may still be implemented pre-Stable):

```text
PipeWire Managed
MPD parity
DSD/DoP
hardware volume
Digital Twin
UAC raw parser
Clock Observatory
USB Feedback Observatory
Atlas
multi-DAC
adaptive learning
extended tail laboratory beyond bounded R35
pre-sink hashing
```

---

# 5. CANONICAL INVARIANTS

1. `AudioPort` remains transport-only.
2. Queue/Playlist never owns DAC/output policy.
3. A physical/logical `AudioDevice` is distinct from runtime backend bindings.
4. Numeric ALSA card index is never canonical identity.
5. PipeWire object ID is never canonical identity.
6. `OutputPlan` exists before backend/hardware mutation.
7. `OutputPlanner` never opens hardware.
8. Capability claims always carry provenance.
9. User overrides can restrict capability; they never invent capability.
10. Active ALSA probing is isolated in `michi-alsa-probe`.
11. `aplay` is diagnostics only, never the product capability API.
12. Strict Direct forbids silent resampling, remixing, device fallback, and hidden mode downgrade.
13. DAC loss never silently moves playback to speakers unless explicit policy permits.
14. Selected output and active output are distinct state.
15. Session lifecycle is distinct from playback transport state.
16. 24-bit source may use S32 carrier only when significant precision is preserved.
17. DSD/DoP is not inferred from PCM support.
18. Direct path semantics and exclusive ownership semantics are independent claims.
19. Channel count never proves channel ordering/topology.
20. Exact tuple openability never proves stable executor behavior.
21. `UNKNOWN` is a first-class truthful state.
22. Observers are non-authoritative.
23. Reference-model tests never count as physical evidence.
24. Stable signal verification scope is bounded to the Linux hardware PCM boundary.
25. Empirical optional features can be killed without harming the core.

---

# 6. MINIMAL AUDIOPHILE SPINE

Everything the mandatory pre-Stable M11.4 DAC core depends on must reduce to:

```text
AudioDevice
    │
    ├── current AudioDeviceBinding
    └── minimal identity confidence

CapabilityEvidence
    │
AudioOutputProfile
    │
    ▼
OutputPlanner
    │
    ▼
OutputPlan
    │
    ▼
OutputSession
    │
    ▼
GStreamer
    │
    ▼
ALSA hw
    │
    ▼
Linux hardware PCM boundary

Runtime Evidence
    │
    ▼
Core Signal Conformance
```

Required architecture test:

```text
T-SPINE-WITHOUT-SATELLITES

Disable all optional/post-core/post-stable/research modules.
Use supported USB DAC.
Plan 24/96 Direct.
Open and play.
Observe negotiated rate and significant bits.
Stop and release.

PASS:
Mandatory pre-Stable DAC core works.

FAIL:
An optional subsystem accidentally became authority/dependency.
```

---

# 7. DOMAIN — DEVICE IDENTITY

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class IdentityConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class AudioDeviceIdentity:
    stable_device_id: str

    vendor_id: str | None
    product_id: str | None
    serial: str | None

    manufacturer: str | None
    product: str | None

    physical_path: str | None
    bus: str | None

    confidence: IdentityConfidence
```

Identity precedence:

```text
1. VID + PID + useful unique serial
2. VID + PID + stable physical path
3. driver/sysfs stable facts
4. deterministic local fallback
```

Never merge two simultaneously observed devices solely because:

```text
VID/PID match
product string matches
serial is blank/generic/suspiciously duplicated
```

---

# 8. DOMAIN — RUNTIME BINDING

```python
class BindingKind(Enum):
    ALSA_PCM = "alsa_pcm"
    PIPEWIRE_NODE = "pipewire_node"
    OTHER = "other"


@dataclass(frozen=True)
class AudioDeviceBinding:
    kind: BindingKind
    locator: str

    generation: int
    currently_available: bool

    card_index: int | None = None
    pcm_device: int | None = None
    pcm_subdevice: int | None = None
```

Examples:

```text
stable_device_id
→ persistent logical identity

hw:CARD=DX5,DEV=0
→ current ALSA binding

card 2
→ temporary runtime observation
```

---

# 9. DEVICE OBSERVATIONS

Adapters emit observations.

They do not decide canonical identity globally.

```python
@dataclass(frozen=True)
class DeviceObservation:
    source: str
    observed_at_ns: int

    vendor_id: str | None
    product_id: str | None
    serial: str | None

    manufacturer: str | None
    product: str | None

    physical_path: str | None

    binding: AudioDeviceBinding | None
```

Initial Stable sources:

```text
udev/sysfs
ALSA
```

PipeWire observation is not required to block first Direct milestone.

---

# 10. AUDIO DEVICE REGISTRY

Responsibilities:

```text
collect observations
correlate them
maintain stable identity
update bindings
track availability
generation-safe rescan
preserve selected intent across disconnect
```

Non-responsibilities:

```text
probe formats
choose output profile
open PCM
decide GStreamer
manage Queue
```

Canonical interface:

```python
from typing import Protocol

class AudioDeviceRegistryPort(Protocol):
    def snapshot(self) -> tuple[AudioDeviceIdentity, ...]:
        ...

    def binding_for(
        self,
        stable_device_id: str,
        kind: BindingKind,
    ) -> AudioDeviceBinding | None:
        ...
```

---

# 11. ACCESS SEMANTICS — DIRECT != EXCLUSIVE

```python
class PathSemantics(Enum):
    HARDWARE_RAW = "hardware_raw"
    ALSA_PLUGIN = "alsa_plugin"
    SYSTEM_SERVER = "system_server"
    UNKNOWN = "unknown"


class OwnershipSemantics(Enum):
    UNKNOWN = "unknown"
    UNRESERVED = "unreserved"
    COOPERATIVE_RESERVED = "cooperative_reserved"
    EXCLUSIVE_OBSERVED = "exclusive_observed"
    SHARED_OBSERVED = "shared_observed"


class OwnershipScope(Enum):
    PCM_SUBSTREAM = "pcm_substream"
    PCM_DEVICE = "pcm_device"
    AUDIO_CARD = "audio_card"
    PHYSICAL_DEVICE = "physical_device"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OutputAccessSemantics:
    path: PathSemantics
    ownership: OwnershipSemantics
    ownership_scope: OwnershipScope
```

Canonical interpretation:

```text
ALSA hw
→ HARDWARE_RAW

ALSA hw
≠ automatic EXCLUSIVE_OBSERVED
```

UI may say:

```text
Direct
```

when hardware raw is known.

UI may say:

```text
Exclusive
```

only when ownership evidence supports the declared scope.

---

# 12. CAPABILITY EVIDENCE

```python
class EvidenceStrength(Enum):
    DECLARED = "declared"
    DISCOVERED = "discovered"
    PROBED = "probed"
    OPENED = "opened"
    NEGOTIATED = "negotiated"
    RUNTIME_VERIFIED = "runtime_verified"


@dataclass(frozen=True)
class PcmTuple:
    rate_hz: int
    transport_format: str
    channels: int
    significant_bits: int | None


@dataclass(frozen=True)
class CapabilityEvidence:
    stable_device_id: str
    tuple: PcmTuple

    supported: bool | None
    strength: EvidenceStrength

    source: str
    observed_at_ns: int

    environment_fingerprint: str
    evidence_refs: tuple[str, ...]
```

Critical error rule:

```text
BUSY != UNSUPPORTED
REMOVED != UNSUPPORTED
TIMEOUT != UNSUPPORTED
```

Only a sufficiently specific exact-format rejection may produce negative capability evidence.

---

# 13. `michi-alsa-probe` — FINAL STABLE IMPLEMENTATION CONTRACT

This section is implementation authority and supersedes older Rust-helper wording elsewhere in this document.

Architecture:

```text
Python application
        │
        ▼
MichiAlsaProbeAdapter
        │ subprocess + timeout + versioned JSON
        ▼
sys.executable -m michi.infrastructure.audio_devices.alsa_probe_cli
        │
        ▼
alsa_ctypes.py
        │
        ▼
libasound.so.2
        │
        ▼
ALSA hw:CARD,DEV
```

Audio samples never travel through JSON. The helper performs low-frequency exact-open/control-plane qualification only.

Canonical module paths:

```text
src/michi/infrastructure/audio_devices/alsa_ctypes.py
src/michi/infrastructure/audio_devices/alsa_probe_cli.py
src/michi/infrastructure/audio_devices/alsa_probe_adapter.py
```

Product subprocess command:

```text
<sys.executable> -m michi.infrastructure.audio_devices.alsa_probe_cli version --json
<sys.executable> -m michi.infrastructure.audio_devices.alsa_probe_cli enumerate --json
<sys.executable> -m michi.infrastructure.audio_devices.alsa_probe_cli probe \
    --device hw:CARD=DX5,DEV=0 \
    --rate 96000 \
    --format S32_LE \
    --channels 2 \
    --json
```

Strict probe sequence inside the worker:

```text
1. validate that locator begins with exact physical `hw:` semantics
2. snd_pcm_open(..., SND_PCM_STREAM_PLAYBACK, NONBLOCK only when required by probe policy)
3. snd_pcm_hw_params_any
4. snd_pcm_hw_params_set_rate_resample(pcm, params, 0)
5. set access = RW_INTERLEAVED
6. set channels EXACTLY; no *_near substitute
7. set format EXACTLY
8. set rate EXACTLY; never use set_rate_near as support proof
9. apply snd_pcm_hw_params
10. read back selected access/channels/format/rate
11. read snd_pcm_hw_params_get_sbits
12. optionally capture period/buffer facts as diagnostics only
13. close handle in finally path
14. emit exactly one JSON object on stdout
15. technical logging goes to stderr only
```

Minimal response:

```json
{
  "schema_version": 1,
  "tool": "michi-alsa-probe",
  "implementation": "python-ctypes-libasound",
  "operation": "probe",
  "ok": true,
  "result": {
    "requested": {
      "device": "hw:CARD=DX5,DEV=0",
      "rate_hz": 96000,
      "format": "S32_LE",
      "channels": 2
    },
    "negotiated": {
      "rate_hz": 96000,
      "format": "S32_LE",
      "channels": 2,
      "significant_bits": 24
    }
  },
  "error": null
}
```

Required error categories:

```text
alsa_runtime_missing
device_busy
device_removed
unsupported_format
negotiation_failed
permission_denied
timeout
protocol_error
internal_error
unknown
```

Errno/ALSA classification is layer-aware. `EBUSY` is never cached as unsupported. Removal/disconnect errors are never cached as unsupported. Approximate-rate acceptance is never returned as exact support.

Subprocess contract:

```text
default timeout       1500 ms per exact tuple probe
kill grace            250 ms after terminate request
stdout                 one bounded JSON document only
stderr                 bounded diagnostic text
max stdout             64 KiB
max stderr             64 KiB
schema mismatch         protocol_error
non-zero exit + valid error JSON -> typed error JSON wins
non-zero exit + invalid/no JSON   -> protocol_error/internal_error
```

The optional installed alias `michi-alsa-probe` is for humans and CI; product code invokes the module with `sys.executable` so venv/wheel provenance is deterministic.

---

# 14. PROBE SAFETY — STABLE MINIMAL FORM

Stable Probe Safety does not require raw UAC parsing.

Rules:

```text
probe only the exact tuple currently required
do not brute-force exotic matrices on startup
never run active qualification during playback
cancel closes current handle
BUSY/REMOVED/TIMEOUT create no negative capability claim
full exhaustive matrix qualification is on-demand; it may run during pre-Stable qualification and is not a prerequisite for first discovery. It is never a reason to postpone M11.4 until after Stable
```

If a physical DAC demonstrates that safe ALSA probing itself is dangerous:

```text
block that exact target
record counterexample
widen safety model
consider promoting UAC diagnostics only then
```

---

# 15. OUTPUT PROFILE

```python
class OutputPathPreference(Enum):
    DESKTOP = "desktop"
    MANAGED = "managed"
    HARDWARE_DIRECT = "hardware_direct"


class RatePolicy(Enum):
    SOURCE_NATIVE = "source_native"
    SYSTEM = "system"


class VolumePolicy(Enum):
    FIXED = "fixed"
    SOFTWARE = "software"
    HARDWARE = "hardware"


class FallbackKind(Enum):
    STOP = "stop"
    ASK = "ask"
    DESKTOP_DEFAULT = "desktop_default"
    SPECIFIC_DEVICE = "specific_device"


@dataclass(frozen=True)
class AudioOutputProfile:
    profile_id: str
    stable_device_id: str | None

    path: OutputPathPreference
    rate_policy: RatePolicy
    volume_policy: VolumePolicy

    allow_resample: bool
    allow_remix: bool
    allow_processing: bool

    fallback: FallbackKind
```

Canonical Stable Direct preset:

```text
path                HARDWARE_DIRECT
rate_policy         SOURCE_NATIVE
volume_policy       FIXED
allow_resample      false
allow_remix         false
allow_processing    false
fallback            STOP
```

The profile expresses policy.

It does not fabricate hardware capability.

---

# 16. SOURCE SIGNAL

```python
@dataclass(frozen=True)
class DecodedSourceSignal:
    encoding: str
    rate_hz: int
    significant_bits: int | None
    channels: int
    channel_positions: tuple[str, ...] | None
```

Stable first target:

```text
PCM
stereo
```

No DSD branch is required before PCM Direct stabilizes.

---

# 17. OUTPUT PLAN

The most important Stable object:

```python
@dataclass(frozen=True)
class OutputPlan:
    plan_id: str

    stable_device_id: str
    binding: AudioDeviceBinding

    path_semantics: PathSemantics
    requested_pcm: PcmTuple

    engine_id: str

    volume_policy: VolumePolicy

    allow_resample: bool
    allow_remix: bool
    allow_processing: bool

    fallback: FallbackKind

    evidence_refs: tuple[str, ...]
    decision_codes: tuple[str, ...]
```

Planner input:

```text
DecodedSourceSignal
+
AudioDevice
+
current binding
+
CapabilityEvidence
+
AudioOutputProfile
+
engine output capability
```

Planner output:

```text
immutable OutputPlan
```

Planner never:

```text
opens ALSA
starts GStreamer
acquires device
changes PipeWire
starts MPD
```

---

# 18. OUTPUT PLANNER RULES

Strict Direct algorithm:

```text
1. Resolve selected stable device.
2. Resolve current ALSA hardware binding.
3. Require hardware-raw path.
4. Build exact source-native target.
5. Permit S32 carrier for 24-bit source only when significant precision is preserved.
6. Reject unsupported exact tuple.
7. Reject unknown exact tuple unless policy permits JIT exact probe.
8. No sample-rate fallback.
9. No channel remix.
10. No DSP.
11. No different-device fallback.
12. Emit decisions and evidence references.
```

Examples:

```text
source 24/96
device exact S32_LE / 96k / stereo / 24 sbits
→ READY
```

```text
source 24/192
device only 24/96
Strict Direct
→ REJECT
```

Never:

```text
24/192
→ silently 24/96
```

---

# 19. PLANNING DECISION CODES

Minimum:

```text
ENGINE_GSTREAMER_DIRECT
BINDING_ALSA_HW_SELECTED
SOURCE_NATIVE_RATE_REQUIRED
S32_CARRIER_PRESERVES_24_BITS
STRICT_NO_RESAMPLE
STRICT_NO_REMIX
FIXED_VOLUME_SELECTED
FALLBACK_STOP
```

Every decision must be explainable.

---

# 20. GStreamer STABLE EXECUTOR

Stable direct path:

```text
decoded PCM
    ↓
GStreamer
    ↓
alsasink
    ↓
device=hw:CARD=...,DEV=...
```

Never use:

```text
autoaudiosink
```

for Direct.

The sink factory consumes `OutputPlan`.

It does not decide policy.

Reference seam:

```python
@dataclass(frozen=True)
class GstSinkSpec:
    factory: str
    properties: dict[str, object]


def sink_spec_for(plan: OutputPlan) -> GstSinkSpec:
    if plan.path_semantics is not PathSemantics.HARDWARE_RAW:
        raise ValueError("Stable Direct requires hardware-raw path")

    return GstSinkSpec(
        factory="alsasink",
        properties={
            "device": plan.binding.locator,
        },
    )
```

Actual PyGObject integration must be `LINUX_INTEGRATION_TESTED`.

---

# 21. OUTPUT SESSION STATE MACHINE

```python
class OutputSessionState(Enum):
    IDLE = "idle"
    ACQUIRING = "acquiring"
    CONFIGURING = "configuring"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    RECONFIGURING = "reconfiguring"
    RECOVERING = "recovering"
    LOST = "lost"
    FAILED = "failed"
    RELEASING = "releasing"
```

Required identifiers:

```text
session_id
generation
plan_id
stable_device_id
binding generation
```

Late callbacks from old generations are discarded.

---

# 22. SELECTED VS ACTIVE OUTPUT

```python
@dataclass(frozen=True)
class OutputSelectionState:
    selected_device_id: str | None
    selected_profile_id: str | None

    active_device_id: str | None
    active_plan_id: str | None

    session_state: OutputSessionState
    error_code: str | None
```

If selected DAC disappears:

```text
selected_device_id
stays

active_device_id
becomes None

session
LOST

fallback
STOP unless explicit policy says otherwise
```

This preserves user intent.

---

# 23. FAILURE DOMAIN

Minimum exceptions/errors:

```text
OutputDeviceUnavailable
OutputDeviceBusy
OutputDeviceRemoved
OutputFormatUnsupported
OutputNegotiationFailed
OutputXrun
OutputSessionInvalidated
OutputAcquireFailed
OutputReleaseFailed
OutputBackendUnavailable
```

Never collapse:

```text
busy
removed
unsupported
```

into one generic failure.

---

# 24. HOTPLUG / RECONNECT

Disconnect during playback:

```text
device removal observed
→ invalidate active binding
→ invalidate active session generation
→ stop/lose according to policy
→ do not switch devices silently
→ retain selected identity intent
```

Reconnect:

```text
new observation
→ correlate stable identity
→ create fresh binding generation
→ selected intent resolves again
→ reacquire only when playback/user policy requires
```

Do not assume previous ALSA handle remains valid.

---

# 25. FORMAT TRANSITIONS

Stable PCM transitions:

```text
same exact tuple
→ preserve session where engine/backend supports safely

rate/format tuple changes
→ controlled stop/reconfigure/reopen
→ invalidate stale runtime evidence
→ do not claim gapless if hardware reopen is required
```

Initial rates:

```text
44.1
48
96
192
```

No hard-coded DAC lock timing claims.

---

# 26. VOLUME SAFETY — STABLE

Stable first policy:

```text
FIXED
```

But `FIXED` is not automatically safe.

Canonical concept:

```python
class VolumeAuthority(Enum):
    FIXED = "fixed"
    DEVICE_EXTERNAL = "device_external"
    ALSA_HARDWARE = "alsa_hardware"
    MICHI_SOFTWARE = "michi_software"
    UNKNOWN = "unknown"
```

Before first Fixed Direct activation:

```text
known fixed-safe device state
OR
explicit user acknowledgement that downstream/external volume controls loudness
```

If authority is unknown and full-scale output may be dangerous:

```text
SafeGain blocks activation
```

Stable does not require a persistent ALSA hardware-control watcher.

---

# 27. SIGNAL EVIDENCE — STABLE SCOPE

Canonical Stable scope:

```text
Michi → Linux hardware PCM boundary
```

This means Michi may use:

```text
decoded source facts
planned output facts
GStreamer effective facts
ALSA negotiated facts
significant bits
known processing flags
volume policy
```

to evaluate the path up to the Linux hardware PCM interface.

Stable does **not** claim:

```text
USB packet equality
physical DAC input bitstream equality
absence of DAC firmware processing
analog output identity
subjective sound quality
```

---

# 28. CORE SIGNAL CONFORMANCE

Stable required dimensions:

```python
class Verdict(Enum):
    VERIFIED = "verified"
    BROKEN = "broken"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class CoreSignalConformance:
    rate: Verdict
    significant_bits: Verdict
    channel_count: Verdict
    processing: Verdict
    gain: Verdict

    @property
    def global_verdict(self) -> Verdict:
        values = (
            self.rate,
            self.significant_bits,
            self.channel_count,
            self.processing,
            self.gain,
        )

        if any(v is Verdict.BROKEN for v in values):
            return Verdict.BROKEN

        if any(v is Verdict.UNKNOWN for v in values):
            return Verdict.UNKNOWN

        if all(v is Verdict.VERIFIED for v in values):
            return Verdict.VERIFIED

        return Verdict.UNKNOWN
```

Rule:

```text
UNKNOWN never becomes VERIFIED by convenience.
```

---

# 29. CORE SIGNAL VERIFIER

Reference algorithm:

```python
def verify_core_signal(
    source: DecodedSourceSignal,
    planned: OutputPlan,
    negotiated: PcmTuple | None,
    *,
    resampling_active: bool | None,
    remix_active: bool | None,
    processing_active: bool | None,
    software_gain_db: float | None,
) -> CoreSignalConformance:
    if negotiated is None:
        return CoreSignalConformance(
            rate=Verdict.UNKNOWN,
            significant_bits=Verdict.UNKNOWN,
            channel_count=Verdict.UNKNOWN,
            processing=Verdict.UNKNOWN,
            gain=Verdict.UNKNOWN,
        )

    rate = (
        Verdict.VERIFIED
        if source.rate_hz == negotiated.rate_hz
        else Verdict.BROKEN
    )

    if source.significant_bits is None or negotiated.significant_bits is None:
        significant_bits = Verdict.UNKNOWN
    else:
        significant_bits = (
            Verdict.VERIFIED
            if negotiated.significant_bits >= source.significant_bits
            else Verdict.BROKEN
        )

    channel_count = (
        Verdict.VERIFIED
        if source.channels == negotiated.channels
        else Verdict.BROKEN
    )

    transform_values = (
        resampling_active,
        remix_active,
        processing_active,
    )

    if any(v is True for v in transform_values):
        processing = Verdict.BROKEN
    elif any(v is None for v in transform_values):
        processing = Verdict.UNKNOWN
    else:
        processing = Verdict.VERIFIED

    if software_gain_db is None:
        gain = Verdict.UNKNOWN
    elif software_gain_db != 0.0:
        gain = Verdict.BROKEN
    else:
        gain = Verdict.VERIFIED

    return CoreSignalConformance(
        rate=rate,
        significant_bits=significant_bits,
        channel_count=channel_count,
        processing=processing,
        gain=gain,
    )
```

This is domain semantics only until backed by real runtime evidence.

---

# 30. PRODUCT LANGUAGE

Normal UI may show:

```text
24-bit / 96 kHz
Direct
Verified
```

only when:

```text
scope = Core Signal
global_verdict = VERIFIED
```

Inspector must expose:

```text
Verification scope:
Michi → Linux hardware PCM boundary

Rate:
Verified

Significant precision:
Verified

Channel count:
Verified

Processing:
Verified

Gain:
Verified
```

Do not show:

```text
Bit-perfect to DAC
```

as a Stable claim.

Recommended advanced language:

```text
Core Signal Verified
```

---

# 31. EXTENDED RUNTIME CONFORMANCE — CORE NOW, RICH OBSERVABILITY OPTIONAL LATER

The current pre-Stable M11.4 path already requires enough runtime conformance evidence to make honest Direct/Signal Truth claims. Rich observatories are optional extensions, not prerequisites for beginning implementation.

Current pre-Stable minimum:

```text
requested/effective/negotiated tuple
unexpected resampler/converter detection
minimal clock/slave-policy observation needed to rule out hidden rate adaptation
first-sample / transition / tail acceptance on promoted hardware
```

Richer later observability may add:

```text
full channel topology diagnostics
Clock Observatory UI/history
extended temporal telemetry
```

Canonical name remains `Extended Runtime Conformance`; never call it "Full Digital Conformance". It still does not prove physical DAC sample equality.

---

# 32. CHANNEL TOPOLOGY — CURRENT SEAM, OPTIONAL DEEP QUALIFICATION

The current pre-Stable domain may carry:

```text
channel_positions = None
```

for hardware topology. Do not block first stereo playback solely because a complete ALSA channel map is unavailable. After the first Direct vertical, pre-Stable lab work may query ALSA channel maps and validate L/R with loopback when needed.

Rule:

```text
channels == 2
does not prove
FL,FR ordering
```

---

# 33. CLOCK AUTHORITY — MINIMUM OBSERVATION REQUIRED NOW; FULL OBSERVATORY OPTIONAL

GStreamer clock observation can record:

```text
selected pipeline clock
sink clock provider
slave method
CLOCK_LOST
```

For the current pre-Stable Direct path, Michi MUST observe enough clock/slave-policy state to detect or refuse a hidden resampling policy where the chosen topology makes that relevant. A full Clock Observatory product feature is not required before Stable.

Do not force a GStreamer clock merely to satisfy a model. Observe first; fail the Direct verification claim if clock/slave behavior that could mutate rate remains materially unknown.

---

# 34. TAIL INTEGRITY — PRE-STABLE PHYSICAL ACCEPTANCE FOR PROMOTED DIRECT

Tail integrity is **not post-Stable work** for a DAC path that Michi intends to promote as premium Direct before release. It does not block the first code slice or the first audible physical playback, but it DOES block the corresponding Verified/release-quality Direct claim.

Required pre-Stable acceptance uses the bounded R35/transition fixtures defined later in this document. `perfect_drain` remains diagnostic rather than a universal product mechanism, but tail truncation/corruption must be tested and must not be knowingly shipped as Verified.

During early implementation only, before the relevant physical promotion gate runs:

```text
TailPolicy.UNKNOWN
```

may be an honest temporary state. It is not an excuse to defer R35 until after Player Stable.

---

# 35. CLAIM CONTEXT / SELECTIVE INVALIDATION

Static dependency flags are not sufficient.

Durable evidence should carry:

```python
@dataclass(frozen=True)
class EvidenceContextFingerprint:
    device_identity_revision: str
    descriptor_fingerprint: str | None

    kernel_release: str | None
    snd_usb_audio_parameters_digest: str | None
    alsa_lib_version: str | None

    engine_id: str | None
    engine_version: str | None

    pipewire_version: str | None
    wireplumber_version: str | None

    helper_schema_version: int | None
    helper_version: str | None

    physical_path_scope: str | None
```

Invalidation rule:

```text
known relevant context changed
→ STALE

unknown whether relevant context changed
→ STALE

proven unrelated component changed
→ MAY remain current
```

Never retain evidence merely because someone forgot to list a dependency.

---

# 36. EVIDENCE PRECEDENCE

For local runtime decisions:

```text
current negotiated runtime
>
current exact-open result
>
recent environment-matching qualification
>
historical qualification
>
driver/descriptor observations
>
community/manufacturer hints
```

A lower layer never overrides contradictory current runtime evidence.

---

# 37. PERSISTENCE — STABLE MINIMUM

Persist only what has durable product value:

```text
stable device identity record
selected device/profile intent
per-device Stable preferences
minimal capability evidence/cache
evidence context fingerprint
qualification timestamps
```

Do not persist giant predictive models before Stable.

No Digital Twin table required.

---

# 38. OBSERVABILITY — NON-INTERFERENCE

Stable observers:

```text
device events
session transitions
negotiated facts
errors/XRUN counts
minimal signal evidence
```

Rules:

```text
bounded queues
no blocking filesystem/database work in real-time callback path
no heavy polling
observer failure must not crash playback
observer failure degrades evidence to UNKNOWN
```

Advanced observers require explicit ON/OFF non-interference tests.

---

# 39. LOGGING LEVELS

```text
L0 user
L1 advanced
L2 diagnostics
L3 developer
```

User sees:

```text
DAC unavailable
Exact 192 kHz not supported
Output in use
Playback stopped to preserve Strict Direct policy
```

Developer can see:

```text
stable_device_id
binding generation
OutputPlan
ALSA errno
helper protocol result
session generation
evidence refs
```

---

# 40. NO AUTOMATIC ENGINE FAILOVER

Canonical rule for both the current pre-Stable implementation and later releases until explicitly reconsidered:

```text
automatic equivalent-engine failover = KILLED
```

If GStreamer Direct fails:

```text
report/stop/recover same engine according to policy
```

Do not silently hand the session to MPD.

Engine Parity may exist later as a Lab.

Explicit engine selection may exist later.

---

# 41. AUDIO POLICY SANDBOX

Canonical status:

```text
KILLED / RESEARCH ARCHIVE ONLY
```

The current pre-Stable M11.4 implementation does not temporarily mutate global system audio policy as a normal DAC mechanism.

Resurrection requires a new approved DER and concrete problem that cannot be solved locally.

---

# 42. DIGITAL TWIN

Canonical status:

```text
POST-STABLE ONLY / OPTIONAL READ MODEL
```

No `DacTwinService` before Stable.

If Inspector needs aggregate data:

```text
compose a DacInspectorSnapshot
```

first.

Do not create a new authority/god object.

---

# 43. `michi-uac-inspect`

Canonical status:

```text
RESEARCH / DIAGNOSTICS
```

Do not implement before Stable merely because USB descriptors are interesting.

Promotion requires:

```text
a real physical DAC case
where ALSA/kernel/runtime evidence is insufficient
and raw UAC evidence can resolve a concrete problem
```

---

# 44. VIRTUAL AUDIO TEST TARGET

Canonical name:

```text
Michi Virtual PCM Target
```

Possible implementation:

```text
snd-aloop
PipeWire virtual nodes
controlled capture/failure orchestration
```

It may validate:

```text
GStreamer integration
session lifecycle
sample handling
recovery state
```

It does not validate:

```text
USB Audio Class behavior
physical DAC firmware
USB feedback
clock selectors
hardware descriptors
```

---

# 45. HELPER BUDGET

Production Stable:

```text
michi-alsa-probe
```

Research/developer-only unless promoted:

```text
michi-uac-inspect
michi-alsa-watch
michi-vpcm-target controller
```

This prevents helper proliferation.

---

# 46. STABLE ROADMAP

Canonical sequence:

```text
DAC-001 AudioDevice Domain
DAC-002 Linux Device Observations
DAC-003 AudioDeviceRegistry
DAC-004 michi-alsa-probe
DAC-005 CapabilityEvidence
DAC-005A AccessSemantics
DAC-006 OutputProfile + OutputPlanner
DAC-006A Core Signal Conformance domain
DAC-007 GStreamer ALSA Direct PCM
DAC-008 OutputSession + lifecycle
DAC-009 PCM rate transitions
DAC-010 Hotplug/reconnect/recovery
DAC-011 SafeGain / Fixed output guard
DAC-012 Physical Hardware Seal
```

Do not insert research epics into this sequence.

---

# 47. DAC-001 — AudioDevice Domain

CREATE:

```text
src/michi/domain/audio_device.py
tests/unit/domain/test_audio_device.py
```

MAY modify:

```text
src/michi/domain/__init__.py
```

MUST NOT modify:

```text
AudioPort
GStreamer
MPD
Queue
QML
database schema
```

Acceptance:

```text
stable identity independent from numeric card index
two unique serials stay separate
no-serial devices use physical-path fallback
duplicate/generic serial ambiguity does not merge devices
domain is pure Python
```

Evidence:

```text
DOMAIN_REFERENCE_TESTED
```

---

# 48. DAC-002 — Linux Device Observations

CREATE:

```text
src/michi/infrastructure/audio_devices/udev_observer.py
src/michi/infrastructure/audio_devices/alsa_observer.py
tests/unit/infrastructure/audio_devices/...
```

Adapters emit:

```text
DeviceObservation
```

They do not deduplicate globally.

Acceptance:

```text
real fixture parsing
no runtime ID promoted to stable identity
missing fields remain None
```

---

# 49. DAC-003 — AudioDeviceRegistry

CREATE:

```text
src/michi/application/audio_device_registry.py
tests/unit/application/test_audio_device_registry.py
```

Acceptance:

```text
multi-source correlation
generation-safe scans
availability lifecycle
idempotent updates
reconnect restores stable identity
ambiguous units remain separate
```

---

# 50. DAC-004 — `michi-alsa-probe`

> **V3.5 SUPERSEDED EXECUTION SLICE:** historical rationale only. The Rust/tool-directory implementation below MUST NOT be executed. Stable implementation authority is §0G.1 + §13 + `DAC-V35-020`.

CREATE:

```text
tools/michi-alsa-probe/
src/michi/infrastructure/audio_devices/alsa_probe_adapter.py
contracts/audio/alsa-probe-v1.schema.json
tests/...
```

Rust helper principles:

```text
safe ALSA wrapper first
minimal isolated raw FFI only where necessary
versioned JSON
timeouts
malformed-output rejection
no playback sample transport
```

Acceptance must include:

```text
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
Python adapter tests
schema tests
real Linux smoke test
```

The helper is not complete at `DOMAIN_REFERENCE_TESTED`.

---

# 51. DAC-005 — CapabilityEvidence

CREATE:

```text
src/michi/domain/audio_capability.py
src/michi/application/dac_qualification_service.py
tests/...
```

Acceptance:

```text
exact tuple evidence
sbits evidence
BUSY does not become unsupported
REMOVED does not become unsupported
TIMEOUT does not become unsupported
runtime contradiction can supersede stale history
context fingerprint attached
```

---

# 52. DAC-005A — Access Semantics

CREATE:

```text
src/michi/domain/audio_access.py
tests/unit/domain/test_audio_access.py
```

Acceptance:

```text
ALSA hw => HARDWARE_RAW
ownership remains UNKNOWN without evidence
Direct can be true while Exclusive is false/unknown
ownership scope is explicit
```

No backend takeover mechanism in this PR.

---

# 53. DAC-006 — Output Profile + Planner

CREATE:

```text
src/michi/domain/audio_output.py
src/michi/application/audio_output_planner.py
tests/...
```

Acceptance:

```text
deterministic
no hardware open
Strict Direct exact target
S32 carrier preserves 24 sbits when evidenced
no hidden fallback
no hidden resample
no hidden remix
decision codes emitted
```

---

# 54. DAC-006A — Core Signal Conformance Domain

CREATE:

```text
src/michi/domain/audio_conformance.py
src/michi/domain/audio_signal.py
tests/unit/domain/...
```

Acceptance:

```text
Core scope only
UNKNOWN remains UNKNOWN
BROKEN dominates
no DAC-interface scope claim
channel topology not fabricated
```

---

# 55. DAC-007 — GStreamer ALSA Direct

CREATE/MODIFY only the minimum executor integration.

Target:

```text
GStreamer
→ alsasink
→ explicit hw binding
```

Acceptance:

```text
one physical USB DAC
PCM 24/96
actual ALSA hardware binding
no autoaudiosink
negotiated runtime facts observed
error mapped truthfully
```

Required level:

```text
LINUX_INTEGRATION_TESTED
+
PHYSICAL_HARDWARE_TESTED
```

before closing the physical vertical.

---

# 56. DAC-008 — OutputSession

CREATE:

```text
src/michi/domain/audio_session.py
src/michi/application/audio_output_session.py
tests/...
```

Acceptance:

```text
session_id/generation
acquire/configure/run/release
late callback discard
cleanup ownership
selected != active
busy/removal typed
```

---

# 57. DAC-009 — PCM Rate Transitions

Test at least:

```text
44.1 → 96
96 → 192
192 → 44.1
same-format adjacent tracks
```

Acceptance:

```text
stale conformance invalidated at transition
exact new tuple acquired
no hidden conversion
gap/relock behavior reported honestly
```

Do not claim gapless across hardware reopen without measurement.

---

# 58. DAC-010 — Hotplug / Reconnect / Recovery

Acceptance:

```text
unplug while running
unplug while paused
reconnect same stable identity
binding generation changes
selected intent preserved
no automatic speaker fallback
no stale evidence reused
```

Physical hardware required.

---

# 59. DAC-011 — SafeGain / Fixed Output Guard

Acceptance:

```text
first Fixed Direct activation cannot surprise user with unknown full-scale path
external volume acknowledgement supported
unknown authority is not auto-safe
safety decision logged
```

No hardware volume watcher required.

---

# 60. DAC-012 — PHYSICAL HARDWARE SEAL

The pre-Stable M11.4 DAC core is not sealed for Stable release until a real machine can reproducibly:

```text
1. Start with DAC disconnected.
2. Launch Michi.
3. Connect DAC.
4. Discover exactly one canonical device identity.
5. Select Direct.
6. Play 44.1 kHz.
7. Observe exact Linux hardware PCM negotiation.
8. Play 96 kHz.
9. Reconfigure honestly.
10. Play 192 kHz if qualified.
11. Pause/resume according to session policy.
12. Disconnect during playback.
13. Converge to truthful LOST/STOP state.
14. Reconnect.
15. Restore same stable identity.
16. Create fresh binding generation.
17. Resume only according to policy.
18. Export diagnostics.
19. Explain Core Signal Conformance.
20. Never claim more scope than the evidence supports.
```

Target evidence:

```text
PHYSICAL_HARDWARE_TESTED
```

Then reproduce on a materially different second DAC before claiming broader compatibility:

```text
MULTI_HARDWARE_TESTED
```

---

# 61. FIRST TWO PHYSICAL DACS

Hardware target A:

```text
UAC2 USB DAC
PCM stereo
44.1/48/96/192 as supported
24-bit source via correct carrier
```

Hardware target B should differ materially:

```text
different vendor/model
different supported-rate matrix
different runtime ordering/identity details
```

Do not tune architecture around one favorite DAC.

---

# 62. CI JOBS

Minimum:

```text
audio-domain
audio-device-registry
audio-contracts
audio-helper-rust
audio-fake-scenarios
audio-gstreamer-linux
```

Later:

```text
virtual-pcm-target
hardware-lab artifacts
```

---

# 63. DOMAIN PURITY GATE

No imports in domain from:

```text
PySide6
gi
pyudev
sqlite3
subprocess
ALSA FFI
PipeWire
GStreamer
```

Domain contains:

```text
immutable facts
policies
verdicts
pure decisions
```

---

# 64. FAILURE INJECTION

Before Stable close:

```text
device busy
device removed before acquire
removed during configure
removed during running
XRUN
negotiated different tuple
helper timeout
malformed JSON
schema mismatch
late session callback
release failure
```

Expected behavior must be deterministic.

---

# 65. GOLDEN SCENARIOS

Keep at least:

```text
direct_pcm_native
direct_rate_change
direct_unsupported
direct_busy
unplug_reconnect
s32_24sbits
direct_not_exclusive
core_verified_extended_unknown
```

Not required before Stable:

```text
DSD
multi-DAC
clock lab
UAC topology
community Atlas
```

---

# 66. EXECUTION SLICE FORMAT

Agents receive one slice, not the Research Corpus.

Every slice contains:

```text
OBJECTIVE

EPISTEMIC TYPE

BASELINE / PRECONDITIONS

CANONICAL CLAIMS

CREATE

MAY MODIFY

MUST NOT MODIFY

DOMAIN CONTRACTS

ERROR MAPPING

TESTS

EVIDENCE LEVEL REQUIRED

FALSIFICATION / NEGATIVE TESTS

STOP CONDITIONS

DEFINITION OF DONE

OUT-OF-SCOPE
```

If source code contradicts a slice materially:

```text
STOP
report the contradiction
do not improvise a new architecture
```

---

# 67. STOP CONDITIONS FOR CODING AGENTS

Stop rather than improvise if:

```text
solution requires DAC methods on AudioPort
Queue must become output authority
only solution silently resamples in Strict
only solution silently switches devices
stable identity requires numeric card ID
backend API cannot expose a claimed fact
schema cannot represent actual observation
physical runtime contradicts capability claim
requested PR would require a killed/research feature
```

---

# 68. OUTSIDE THE MANDATORY M11.4 CORE — TIMING IS EXPLICIT, NOT AUTOMATICALLY POST-STABLE

This older queue is superseded by §0AA and §0E. Do **not** interpret “outside the mandatory core” as “wait until the app is Stable.”

May be implemented **during the same pre-Stable cycle after the mandatory PCM Direct vertical is green**, when evidence/value justifies it:

```text
qualified hardware volume
DSD / DoP
channel-map deep validation
additional DAC Inspector diagnostics
Regression Lab / sanitized Bug Capsule
MPD parity experiments
```

Explicitly **POST-STABLE ONLY by current V3.5 decision**:

```text
signed downloadable profile distribution / remote profile update machinery
broad community/marketplace-style profile infrastructure
nonessential system-wide experimentation not required to close a real pre-Stable defect
```

`tail integrity` and the primary `qualification UI / premium DAC UI` are **not in this deferred queue**: their bounded forms are part of the pre-Stable M11.4 acceptance path.

Each optional extension still earns its own DER/PR and cannot destabilize the mandatory core.

---

# 69. RESEARCH ARCHIVE

No roadmap commitment:

```text
michi-uac-inspect
UAC4 parser
Clock Observatory
USB Feedback Observatory
Adaptive Suspend
Adaptive Resync learning
automatic buffer learning
Digital Twin
Open DAC Atlas
multi-DAC synchronized start
pre-sink sample hashing
hardware control watcher
```

Killed:

```text
Audio Policy Sandbox
Automatic Equivalent Engine Failover
```

---

# 70. SOURCE / CLAIM DISCIPLINE

The Research Corpus contains source-derived facts and Michi-derived architecture.

Implementation slices must distinguish:

```text
SOURCE-DERIVED
What ALSA/GStreamer/Linux actually exposes.

MICHI CONTRACT
How Michi chooses to model/use it.

EMPIRICAL CLAIM
What physical testing must still prove.
```

Never convert an architectural inference into an upstream API fact.

---

# 71. USER-FACING PRINCIPLE

Basic user experience remains:

```text
Plug DAC
Select DAC
Play
```

Advanced complexity belongs in Inspector.

The existence of sophisticated evidence machinery must not turn ordinary playback into a qualification wizard.

---

# 72. FINAL PRODUCT PROMISE — STABLE

Michi Stable may promise:

> Michi can identify the selected DAC, choose an explicit Linux output policy, attempt an exact native PCM hardware path, observe the Linux hardware PCM configuration it actually negotiated, refuse silent policy degradation, recover honestly from device loss, and show the evidence supporting its Core Signal verdict.

Michi Stable must **not** promise:

> We have proven every bit at the physical DAC input or internal DAC processing.

That stronger claim requires stronger evidence.

---

# 73. FINAL IMPLEMENTATION MANTRA

```text
IDENTIFY
↓
EVIDENCE
↓
PLAN
↓
EXECUTE
↓
OBSERVE
↓
CONFORM
↓
FAIL HONESTLY
```

Not:

```text
FEATURES
↓
MORE FEATURES
↓
MORE OBSERVERS
↓
MORE ABSTRACTIONS
```

---

# 74. FINAL KILLCRITIC ACCEPTANCE

The DAC plan is healthy only while all of these remain true:

```text
The mandatory pre-Stable DAC core is understandable without the Research Corpus.
The mandatory pre-Stable DAC core works with all pioneer satellites removed.
One exact hardware PCM vertical works during pre-Stable development before optional expansion.
No old superseded phrase can override this file.
No reference unit test masquerades as physical proof.
No feature is "Foundation" merely because it might be useful later.
No observer owns playback.
No automatic fallback hides a broken engine or device.
No signal claim exceeds its measurable boundary.
```

**END OF CANONICAL EFFECTIVE SPEC**

# PART II — RESEARCH-TO-IMPLEMENTATION BLUEPRINT

**Status:** CANONICAL RESEARCH INTEGRATION LAYER  
**Relationship to Stable:** does not expand Stable scope unless an experiment explicitly promotes a result  
**Primary goal:** turn current uncertainty into code, testable observations, and small auditable files.

---

# 75. WHY THIS PART EXISTS

The previous sections define the Stable architecture.

This part defines **how to investigate the unresolved empirical questions without polluting Stable authority**.

The central rule is:

```text
PRODUCT CODE
must remain simple and deterministic

LAB CODE
may be experimental, instrumented, comparative, and falsification-oriented
```

Research may promote a result into Stable only after:

```text
question
→ experiment
→ evidence
→ counterexample search
→ decision
→ Effective Spec amendment
```

---

# 76. CURRENT CONFIDENCE LEDGER

## 76.1 Safe / canonical

```text
AudioPort transport-only
Queue has no DAC authority
OutputPlan before mutation
Selected != Active
No silent Strict fallback
ALSA hw = hardware-raw ALSA path
Direct != Exclusive
Exact ALSA tuple configuration exists
ALSA significant bits are meaningful at the ALSA PCM boundary
GStreamer alsasink supports explicit ALSA device binding
UNKNOWN is a valid verdict
```

## 76.2 Plausible but not yet physically established

```text
Stable identity fallback behavior across hostile hardware cases
S24 source → S32 carrier / 24 sbits sample preservation through real GStreamer path
exact GStreamer runtime always matching OutputPlan
failure errno mapping across target DACs
pause/resume behavior across USB DACs
rate-transition lifecycle
```

## 76.3 Research hypotheses

```text
Strict Direct can omit audioresample entirely
real session can replace first-use pre-probe
audioconvert Strict settings are sample-preserving for target integer conversions
/proc ALSA runtime witness is sufficient as an independent Linux integration witness
Observed Output Stabilization Time is reproducible enough to guide later policy
```

## 76.4 Research only / not Stable

```text
Clock Authority
Channel-map physical proof
Tail Integrity Lab
UAC raw inspection
USB feedback
Digital Twin
Atlas
adaptive learning
```

---

# 77. RESEARCH IMPLEMENTATION TREE

> **V3.5 RESEARCH-ONLY TREE:** this historical research layout is not an executable file plan. The only executable CREATE/MODIFY/FORBID map is §397.

The intended repository layout is:

```text
src/michi/
├── domain/
│   ├── audio_device.py
│   ├── audio_capability.py
│   ├── audio_access.py
│   ├── audio_output.py
│   ├── audio_signal.py
│   ├── audio_conformance.py
│   ├── audio_runtime_evidence.py          # NEW
│   ├── audio_processing_evidence.py       # NEW
│   ├── audio_failure_evidence.py          # V3 — layer-aware, supersedes old classifier
│   ├── kernel_audio_environment.py         # V3
│   ├── usb_audio_driver_witness.py         # V3
│   └── audio_rate_evidence.py              # V3
├── application/
│   ├── audio_device_registry.py
│   ├── dac_qualification_service.py
│   ├── audio_output_planner.py
│   ├── audio_output_session.py
│   ├── pcm_evidence_recorder.py           # NEW
│   ├── direct_qualification_policy.py      # NEW / EXPERIMENTAL
│   └── kernel_context_correlation_service.py # V3
├── infrastructure/
│   ├── audio_devices/
│   │   ├── udev_observer.py
│   │   ├── alsa_observer.py
│   │   ├── alsa_probe_adapter.py
│   │   ├── proc_pcm_witness.py            # NEW
│   │   ├── linux_kernel_audio_snapshot.py  # V3
│   │   └── usb_audio_stream_proc.py        # V3
│   └── audio_engines/
│       └── gstreamer/
│           ├── direct_pipeline_spec.py     # NEW
│           ├── runtime_evidence.py         # NEW
│           └── output_sink_factory.py
└── presentation/
    └── ...                                 # no direct research authority

tools/
├── michi-alsa-probe/
└── michi_audio_lab/
    ├── sample_normalizer.py                # NEW
    ├── identity_chaos.py                   # NEW
    ├── transition_timeline.py              # NEW
    └── experiments/
        ├── R1_runtime_witness.yaml
        ├── R2_resampler_ab.yaml
        ├── R3_sample_preservation.yaml
        ├── R4_probe_vs_session.yaml
        ├── R5_identity_chaos.yaml
        ├── R6_failure_matrix.yaml
        └── R7_transition_lab.yaml

contracts/audio/
├── alsa-probe-v1.schema.json
├── pcm-runtime-evidence-v1.schema.json      # NEW
└── failure-observation-v1.schema.json       # NEW

tests/
├── unit/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── tools/
├── integration/audio/
└── hardware/audio/
```

The important boundary is:

```text
src/michi/
→ product/runtime code

tools/michi_audio_lab/
→ research code

tests/hardware/audio/
→ physical falsification
```

The Lab cannot own playback policy.

---

# 78. CODE STATUS TAGS

Use these tags directly above reference code in PRs and research notes:

```text
STATUS: DOMAIN_REFERENCE_TESTED
Pure logic has passing unit tests.

STATUS: BACKEND_FAKE_TESTED
Adapter/service tested against deterministic fake backend.

STATUS: LINUX_INTEGRATION_PENDING
API shape is designed; real Linux/GStreamer/ALSA integration not yet proven.

STATUS: PHYSICAL_HARDWARE_PENDING
Linux integration exists but physical DAC evidence is missing.

STATUS: FALSIFICATION_PENDING
Competing hypotheses exist and no canonical winner has been selected.

STATUS: KILLED
Do not implement without a new DER and canonical approval.
```

---

# 79. RUNTIME EVIDENCE ARCHITECTURE

New evidence chain:

```text
Decoded Source
      │
      ▼
OutputPlan
      │
      ▼
GStreamer current caps
      │
      ▼
alsasink(device=hw:...)
      │
      ▼
Linux PCM Runtime Witness
/proc/asound/.../hw_params
/proc/asound/.../sw_params
/proc/asound/.../status
      │
      ▼
ALSA significant-bits evidence
      │
      ▼
Core Signal Conformance
```

This is intentionally redundant.

The planner is not allowed to be its own witness.

---

# 80. IMPORTANT GStreamer EVIDENCE RULE

Runtime evidence must use:

```text
Gst.Pad.get_current_caps()
```

or equivalent actual negotiated state.

Do not use:

```text
query_caps()
```

as proof that a specific format is flowing.

`query_caps()` answers possibility.

`current_caps` answers negotiated runtime configuration.

---

# 81. `/proc/asound` POLICY

`/proc/asound/.../hw_params`, `sw_params`, and `status` are valuable Linux integration witnesses.

Stable policy:

```text
not required for playback
not a domain dependency
not an authority over planner/session
```

Research/testing policy:

```text
high-value independent witness
```

If procfs disappears or changes:

```text
evidence becomes unavailable
playback continues
```

---

# 82. PROCESSING EVIDENCE MUST BE FACTORED

Do not persist one unconstrained:

```python
processing_active = False
```

Persist facts:

```text
resampler_present
resampler_active
format_conversion_present
format_conversion_preserving
channel_remix_active
dither_active
noise_shaping_active
software_gain_db
```

Then derive the product verdict.

This prevents an adapter from asserting a conclusion it cannot observe.

---

# 83. STRICT `audioconvert` RESEARCH POLICY

Current research candidate:

```text
dithering = none
noise-shaping = none
input-channels-reorder-mode = none
```

This is **not yet promoted to Stable canonical configuration**.

Promotion requires R3 Sample Preservation.

Reason:

`audioconvert` is capable of transformations including:

```text
integer/float conversion
depth conversion
mixing/remixing
dithering
noise shaping
channel reordering
```

Therefore its presence must be empirically characterized.

---

# 84. STRICT `audioresample` HYPOTHESES

Two competing designs remain deliberately alive:

## H-A

```text
decoder
→ audioconvert
→ audioresample
→ exact caps
→ alsasink
```

Requirement:

```text
audioresample must remain passthrough
```

## H-B

```text
decoder
→ audioconvert
→ exact caps
→ alsasink
```

Property:

```text
resampling impossible by construction
```

R2 decides.

No coding agent may select one by taste.

---

# 85. PROBE VS REAL SESSION HYPOTHESES

## H-PROBE

```text
unknown exact tuple
→ michi-alsa-probe
→ close
→ real GStreamer session
```

Potential benefit:

```text
early rejection
clear diagnosis
```

Potential cost:

```text
double hardware configuration
startup delay
additional USB/firmware interaction
```

## H-EXECUTE

```text
unknown exact tuple
→ exact real GStreamer session
→ successful negotiation becomes evidence
```

Potential benefit:

```text
one real hardware transaction
execution itself proves the requested path
```

Potential cost:

```text
failure occurs in playback transaction
harder early UX
```

R4 decides.

Stable current policy is unchanged until R4.

---

# 86. IDENTITY POLICY MUST COME FROM CHAOS DATA

Do not freeze:

```text
serial > ID_PATH > ALSA longname
```

solely from theory.

R5 must measure:

```text
reconnect
reboot
port move
hub
suspend
identical devices
no serial
generic serial
```

Then `IdentityConfidence` rules can be promoted.

---

# 87. FAILURE MAPPING RULE

Architecture may define:

```text
BUSY
REMOVED
UNSUPPORTED
XRUN
NEGOTIATION_FAILED
```

But backend mapping remains empirical.

In particular:

```text
EINVAL != universally unsupported
```

until the context is strong enough.

R6 freezes the mapping.

---

# 88. TRANSITION TERMINOLOGY

Until stronger measurement exists:

```text
Observed Output Stabilization Time
```

is allowed.

Do not use:

```text
DAC lock time
PLL lock time
```

unless the measurement isolates that physical phenomenon.

R7 measures observable sub-components.

---

# 89. REFERENCE IMPLEMENTATION PACK

The following files were executed as a pure Python reference package.

Result:

```text
30 passed
0 failed
```

Evidence level:

```text
DOMAIN_REFERENCE_TESTED
```

This does **not** prove GStreamer, ALSA, USB, or physical DAC behavior.

---

# 90. FILE: `src/michi/domain/audio_runtime_evidence.py`

**Role:** immutable evidence DTOs only.

**Must not:**

```text
read /proc
call GStreamer
open ALSA
decide playback
```

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class EvidenceFreshness(Enum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class GstCapsSnapshot:
    element_name: str
    pad_name: str
    media_type: str
    format: str | None
    rate_hz: int | None
    channels: int | None
    layout: str | None
    channel_mask: int | None
    source: str = "gst_pad_get_current_caps"


@dataclass(frozen=True)
class AlsaHwParamsSnapshot:
    access: str | None
    format: str | None
    subformat: str | None
    channels: int | None
    rate_hz: int | None
    rate_num: int | None
    rate_den: int | None
    period_size: int | None
    buffer_size: int | None
    raw: Mapping[str, str]


@dataclass(frozen=True)
class AlsaSwParamsSnapshot:
    tstamp_mode: str | None
    period_step: int | None
    avail_min: int | None
    start_threshold: int | None
    stop_threshold: int | None
    silence_threshold: int | None
    silence_size: int | None
    boundary: int | None
    raw: Mapping[str, str]


@dataclass(frozen=True)
class AlsaStatusSnapshot:
    state: str | None
    owner_pid: int | None
    trigger_time: str | None
    tstamp: str | None
    delay_frames: int | None
    avail_frames: int | None
    avail_max_frames: int | None
    raw: Mapping[str, str]


@dataclass(frozen=True)
class RuntimePcmWitness:
    stable_device_id: str
    binding_locator: str
    session_id: str
    generation: int

    gstreamer_pre_sink: GstCapsSnapshot | None
    alsa_hw: AlsaHwParamsSnapshot | None
    alsa_sw: AlsaSwParamsSnapshot | None
    alsa_status: AlsaStatusSnapshot | None

    significant_bits: int | None
    freshness: EvidenceFreshness


@dataclass(frozen=True)
class RuntimeEvidenceBundle:
    source_rate_hz: int
    source_significant_bits: int | None
    source_channels: int

    requested_rate_hz: int
    requested_format: str
    requested_channels: int

    witness: RuntimePcmWitness
```

---

# 91. FILE: `src/michi/infrastructure/audio_devices/proc_pcm_witness.py`

**Role:** passive Linux PCM runtime witness.

**Authority:**

```text
diagnostic/integration evidence only
```

**Failure rule:**

```text
cannot read
→ return unavailable
→ never stop playback
```

```python
from __future__ import annotations

from pathlib import Path
from typing import Callable

from michi.domain.audio_runtime_evidence import (
    AlsaHwParamsSnapshot,
    AlsaStatusSnapshot,
    AlsaSwParamsSnapshot,
)


def _parse_key_value_lines(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    try:
        return int(value, 0)
    except ValueError:
        return None


def _parse_rate(value: str | None) -> tuple[int | None, int | None, int | None]:
    if value is None:
        return None, None, None

    # Common proc form:
    # "96000 (96000/1)"
    value = value.strip()
    first = value.split()[0]
    rate_hz = _parse_int(first)

    rate_num = None
    rate_den = None
    if "(" in value and "/" in value and ")" in value:
        ratio = value[value.find("(") + 1 : value.find(")")]
        num, den = ratio.split("/", 1)
        rate_num = _parse_int(num)
        rate_den = _parse_int(den)

    return rate_hz, rate_num, rate_den


def parse_hw_params(text: str) -> AlsaHwParamsSnapshot | None:
    if text.strip() in {"closed", "no setup"}:
        return None

    raw = _parse_key_value_lines(text)
    rate_hz, rate_num, rate_den = _parse_rate(raw.get("rate"))

    return AlsaHwParamsSnapshot(
        access=raw.get("access"),
        format=raw.get("format"),
        subformat=raw.get("subformat"),
        channels=_parse_int(raw.get("channels")),
        rate_hz=rate_hz,
        rate_num=rate_num,
        rate_den=rate_den,
        period_size=_parse_int(raw.get("period_size")),
        buffer_size=_parse_int(raw.get("buffer_size")),
        raw=raw,
    )


def parse_sw_params(text: str) -> AlsaSwParamsSnapshot | None:
    if text.strip() in {"closed", "no setup"}:
        return None

    raw = _parse_key_value_lines(text)
    return AlsaSwParamsSnapshot(
        tstamp_mode=raw.get("tstamp_mode"),
        period_step=_parse_int(raw.get("period_step")),
        avail_min=_parse_int(raw.get("avail_min")),
        start_threshold=_parse_int(raw.get("start_threshold")),
        stop_threshold=_parse_int(raw.get("stop_threshold")),
        silence_threshold=_parse_int(raw.get("silence_threshold")),
        silence_size=_parse_int(raw.get("silence_size")),
        boundary=_parse_int(raw.get("boundary")),
        raw=raw,
    )


def parse_status(text: str) -> AlsaStatusSnapshot | None:
    if text.strip() in {"closed", "no setup"}:
        return None

    raw = _parse_key_value_lines(text)
    return AlsaStatusSnapshot(
        state=raw.get("state"),
        owner_pid=_parse_int(raw.get("owner_pid")),
        trigger_time=raw.get("trigger_time"),
        tstamp=raw.get("tstamp"),
        delay_frames=_parse_int(raw.get("delay")),
        avail_frames=_parse_int(raw.get("avail")),
        avail_max_frames=_parse_int(raw.get("avail_max")),
        raw=raw,
    )


class ProcPcmWitnessReader:
    """
    Linux diagnostic/runtime witness adapter.

    This adapter is deliberately non-authoritative. Failure to read procfs must
    degrade evidence to unavailable; it must never fail playback.
    """

    def __init__(
        self,
        read_text: Callable[[Path], str] | None = None,
    ) -> None:
        self._read_text = read_text or (lambda path: path.read_text(encoding="utf-8"))

    def read(
        self,
        *,
        card_index: int,
        pcm_device: int,
        subdevice: int,
        stream: str = "p",
    ) -> tuple[
        AlsaHwParamsSnapshot | None,
        AlsaSwParamsSnapshot | None,
        AlsaStatusSnapshot | None,
    ]:
        base = Path(
            f"/proc/asound/card{card_index}/pcm{pcm_device}{stream}/sub{subdevice}"
        )

        def safe_read(name: str) -> str | None:
            try:
                return self._read_text(base / name)
            except (OSError, UnicodeError):
                return None

        hw_text = safe_read("hw_params")
        sw_text = safe_read("sw_params")
        status_text = safe_read("status")

        return (
            parse_hw_params(hw_text) if hw_text is not None else None,
            parse_sw_params(sw_text) if sw_text is not None else None,
            parse_status(status_text) if status_text is not None else None,
        )
```

---

# 92. FILE: `src/michi/infrastructure/audio_engines/gstreamer/runtime_evidence.py`

**Role:** normalize actual GStreamer negotiated caps.

**Critical implementation rule:**

```text
production uses get_current_caps()
not query_caps()
```

```python
from __future__ import annotations

from typing import Any, Mapping

from michi.domain.audio_runtime_evidence import GstCapsSnapshot


def normalize_caps_structure(
    *,
    element_name: str,
    pad_name: str,
    structure_name: str,
    fields: Mapping[str, Any],
) -> GstCapsSnapshot:
    """
    Pure adapter normalization.

    Real PyGObject integration must call Gst.Pad.get_current_caps(), not
    query_caps(), because capability possibility is not runtime negotiation.
    """
    channel_mask = fields.get("channel-mask")
    if isinstance(channel_mask, str):
        try:
            channel_mask = int(channel_mask, 0)
        except ValueError:
            channel_mask = None

    return GstCapsSnapshot(
        element_name=element_name,
        pad_name=pad_name,
        media_type=structure_name,
        format=fields.get("format"),
        rate_hz=_as_int(fields.get("rate")),
        channels=_as_int(fields.get("channels")),
        layout=fields.get("layout"),
        channel_mask=channel_mask if isinstance(channel_mask, int) else None,
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


class GstRuntimeEvidenceTap:
    """
    REFERENCE-ONLY PyGObject seam.

    Production implementation:
      1. locate the pad immediately before alsasink;
      2. call pad.get_current_caps();
      3. convert Gst.Structure fields to a Python mapping;
      4. normalize with normalize_caps_structure();
      5. never block playback if evidence capture fails.
    """

    def snapshot(self) -> GstCapsSnapshot | None:
        raise NotImplementedError("Bind to PyGObject in DAC-007 integration work.")
```

---

# 93. FILE: `src/michi/infrastructure/audio_engines/gstreamer/direct_pipeline_spec.py`

**Role:** describe the two falsifiable Strict Direct pipeline variants.

It does not itself instantiate GStreamer.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrictResamplerPolicy(Enum):
    ABSENT = "absent"
    PRESENT_PASSTHROUGH_REQUIRED = "present_passthrough_required"


@dataclass(frozen=True)
class AudioconvertPolicy:
    dithering: str = "none"
    noise_shaping: str = "none"
    input_channels_reorder_mode: str = "none"


@dataclass(frozen=True)
class DirectPipelineSpec:
    include_audioconvert: bool
    resampler_policy: StrictResamplerPolicy
    exact_caps: str
    alsa_device: str
    audioconvert: AudioconvertPolicy


def build_strict_direct_spec(
    *,
    alsa_device: str,
    gst_format: str,
    rate_hz: int,
    channels: int,
    include_audioresample: bool,
) -> DirectPipelineSpec:
    if not alsa_device.startswith("hw:"):
        raise ValueError("Strict Direct requires an explicit ALSA hw binding.")

    exact_caps = (
        f"audio/x-raw,format={gst_format},rate={rate_hz},"
        f"channels={channels},layout=interleaved"
    )

    return DirectPipelineSpec(
        include_audioconvert=True,
        resampler_policy=(
            StrictResamplerPolicy.PRESENT_PASSTHROUGH_REQUIRED
            if include_audioresample
            else StrictResamplerPolicy.ABSENT
        ),
        exact_caps=exact_caps,
        alsa_device=alsa_device,
        audioconvert=AudioconvertPolicy(),
    )


def describe_pipeline(spec: DirectPipelineSpec) -> tuple[str, ...]:
    chain = ["decoder"]

    if spec.include_audioconvert:
        chain.append("audioconvert")

    if spec.resampler_policy is StrictResamplerPolicy.PRESENT_PASSTHROUGH_REQUIRED:
        chain.append("audioresample")

    chain.extend(
        [
            f"capsfilter({spec.exact_caps})",
            f"alsasink(device={spec.alsa_device})",
        ]
    )

    return tuple(chain)
```

---

# 94. FILE: `src/michi/domain/audio_processing_evidence.py`

**Role:** keep observed processing facts separate from the derived verdict.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceVerdict(Enum):
    VERIFIED = "verified"
    BROKEN = "broken"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProcessingEvidence:
    resampler_present: bool | None
    resampler_active: bool | None

    format_conversion_present: bool | None
    format_conversion_preserving: bool | None

    channel_remix_active: bool | None

    dither_active: bool | None
    noise_shaping_active: bool | None

    software_gain_db: float | None


def processing_verdict(e: ProcessingEvidence) -> EvidenceVerdict:
    known_breakers = (
        e.resampler_active is True,
        e.channel_remix_active is True,
        e.dither_active is True,
        e.noise_shaping_active is True,
        (
            e.format_conversion_present is True
            and e.format_conversion_preserving is not True
        ),
        (
            e.software_gain_db is not None
            and e.software_gain_db != 0.0
        ),
    )

    if any(known_breakers):
        return EvidenceVerdict.BROKEN

    required = (
        e.resampler_active,
        e.channel_remix_active,
        e.dither_active,
        e.noise_shaping_active,
        e.software_gain_db,
    )

    if any(value is None for value in required):
        return EvidenceVerdict.UNKNOWN

    if (
        e.format_conversion_present is True
        and e.format_conversion_preserving is None
    ):
        return EvidenceVerdict.UNKNOWN

    return EvidenceVerdict.VERIFIED
```

---

# 95. FILE: `src/michi/application/pcm_evidence_recorder.py`

**Role:** combine non-authoritative GStreamer + Linux PCM evidence for one active session.

The observer can fail.

Playback must not.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from michi.domain.audio_runtime_evidence import (
    EvidenceFreshness,
    GstCapsSnapshot,
    RuntimePcmWitness,
)


class GstEvidencePort(Protocol):
    def snapshot(self) -> GstCapsSnapshot | None:
        ...


class ProcWitnessPort(Protocol):
    def read(self, *, card_index: int, pcm_device: int, subdevice: int, stream: str = "p"):
        ...


@dataclass(frozen=True)
class ActiveAlsaBinding:
    locator: str
    card_index: int
    pcm_device: int
    subdevice: int


class PcmEvidenceRecorder:
    """
    Non-authoritative evidence aggregation.

    Failure to capture any observer never changes playback policy. It only
    changes evidence from CURRENT/known to UNKNOWN.
    """

    def __init__(
        self,
        gst: GstEvidencePort,
        proc: ProcWitnessPort,
    ) -> None:
        self._gst = gst
        self._proc = proc

    def capture(
        self,
        *,
        stable_device_id: str,
        binding: ActiveAlsaBinding,
        session_id: str,
        generation: int,
        significant_bits: int | None,
    ) -> RuntimePcmWitness:
        gst_snapshot = None
        try:
            gst_snapshot = self._gst.snapshot()
        except Exception:
            # Deliberately evidence-only.
            gst_snapshot = None

        try:
            hw, sw, status = self._proc.read(
                card_index=binding.card_index,
                pcm_device=binding.pcm_device,
                subdevice=binding.subdevice,
            )
        except Exception:
            hw = sw = status = None

        freshness = (
            EvidenceFreshness.CURRENT
            if gst_snapshot is not None or hw is not None
            else EvidenceFreshness.UNKNOWN
        )

        return RuntimePcmWitness(
            stable_device_id=stable_device_id,
            binding_locator=binding.locator,
            session_id=session_id,
            generation=generation,
            gstreamer_pre_sink=gst_snapshot,
            alsa_hw=hw,
            alsa_sw=sw,
            alsa_status=status,
            significant_bits=significant_bits,
            freshness=freshness,
        )
```

---

# 96. FILE: `src/michi/application/direct_qualification_policy.py`

**Status:** `FALSIFICATION_PENDING`

This file encodes the R4 research branch.

It must not be merged into Stable policy until R4 decides Probe-vs-Session.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class QualificationAction(Enum):
    EXECUTE_EXACT_SESSION = "execute_exact_session"
    PRE_PROBE_EXACT_TUPLE = "pre_probe_exact_tuple"
    REJECT = "reject"


@dataclass(frozen=True)
class QualificationDecision:
    action: QualificationAction
    reason: str
    empirical_status: str


def decide_unknown_tuple_experiment(
    *,
    user_pressed_play: bool,
    explicit_test_requested: bool,
    known_probe_hard_reset_incident: bool,
) -> QualificationDecision:
    """
    EXPERIMENTAL / FALSIFICATION-PENDING.

    This is NOT yet the Stable canonical policy. It encodes the A/B research
    branch that asks whether real exact execution can safely become first-use
    qualification evidence.
    """
    if known_probe_hard_reset_incident:
        return QualificationDecision(
            action=QualificationAction.REJECT,
            reason="Known probing incident blocks automatic qualification.",
            empirical_status="blocked_by_local_evidence",
        )

    if explicit_test_requested:
        return QualificationDecision(
            action=QualificationAction.PRE_PROBE_EXACT_TUPLE,
            reason="User explicitly requested Test DAC / qualification.",
            empirical_status="research_supported_use",
        )

    if user_pressed_play:
        return QualificationDecision(
            action=QualificationAction.EXECUTE_EXACT_SESSION,
            reason=(
                "Research branch: attempt the exact real session once and "
                "let negotiated runtime become evidence."
            ),
            empirical_status="falsification_pending",
        )

    return QualificationDecision(
        action=QualificationAction.REJECT,
        reason="No explicit playback or test intent.",
        empirical_status="conservative_default",
    )
```

---

# 97. FILE: `src/michi/domain/audio_failure_evidence.py` — V3 CANONICAL CORRECTION

**Supersedes:** former V2 unscoped failure classifier.

The V2 classifier contained an unsafe simplification:

```text
EPIPE → XRUN
```

That mapping is valid only when the error is observed at the ALSA PCM API/state layer.
At the USB URB/kernel layer, `-EPIPE` means endpoint stall.

Therefore every low-level failure now carries a layer/origin before semantic classification.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureLayer(Enum):
    APPLICATION = "application"
    GSTREAMER = "gstreamer"
    ALSA_PCM_API = "alsa_pcm_api"
    KERNEL_USB_URB = "kernel_usb_urb"
    USB_POWER = "usb_power"
    UNKNOWN = "unknown"


class FailureKind(Enum):
    DEVICE_BUSY = "device_busy"
    DEVICE_REMOVED = "device_removed"
    XRUN = "xrun"
    DEVICE_SUSPENDED = "device_suspended"
    USB_ENDPOINT_STALL = "usb_endpoint_stall"
    USB_BANDWIDTH_EXHAUSTED = "usb_bandwidth_exhausted"
    FORMAT_UNSUPPORTED = "format_unsupported"
    NEGOTIATION_FAILED = "negotiation_failed"
    BACKEND_FAILURE = "backend_failure"
    UNKNOWN = "unknown"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class FailureEvidence:
    layer: FailureLayer
    errno_name: str | None
    message: str | None
    alsa_pcm_state: str | None
    udev_device_present: bool | None
    exact_tuple_was_being_configured: bool


@dataclass(frozen=True)
class FailureCandidate:
    kind: FailureKind
    confidence: Confidence
    reason: str


def classify_failure(
    evidence: FailureEvidence,
) -> tuple[FailureCandidate, ...]:
    out: list[FailureCandidate] = []

    if (
        evidence.udev_device_present is False
        or evidence.errno_name in {"ENODEV", "ESHUTDOWN"}
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_REMOVED,
                Confidence.HIGH,
                "Device absence/removal evidence observed.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "EBUSY"
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_BUSY,
                Confidence.HIGH,
                "ALSA PCM open/configure returned EBUSY.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and (
            evidence.errno_name == "EPIPE"
            or evidence.alsa_pcm_state == "XRUN"
        )
    ):
        out.append(
            FailureCandidate(
                FailureKind.XRUN,
                Confidence.HIGH,
                "ALSA PCM API/state reports XRUN semantics.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "ESTRPIPE"
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_SUSPENDED,
                Confidence.HIGH,
                "ALSA PCM API reports suspended stream.",
            )
        )

    if evidence.layer is FailureLayer.KERNEL_USB_URB:
        if evidence.errno_name == "EPIPE":
            out.append(
                FailureCandidate(
                    FailureKind.USB_ENDPOINT_STALL,
                    Confidence.HIGH,
                    "USB URB EPIPE means endpoint stalled in this layer.",
                )
            )
        elif evidence.errno_name == "ENOSPC":
            out.append(
                FailureCandidate(
                    FailureKind.USB_BANDWIDTH_EXHAUSTED,
                    Confidence.HIGH,
                    "USB URB ENOSPC reports insufficient periodic bandwidth.",
                )
            )
        elif evidence.errno_name == "EHOSTUNREACH":
            out.append(
                FailureCandidate(
                    FailureKind.DEVICE_SUSPENDED,
                    Confidence.HIGH,
                    "USB layer reports suspended/unreachable device.",
                )
            )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "EINVAL"
        and evidence.exact_tuple_was_being_configured
        and evidence.udev_device_present is not False
    ):
        out.append(
            FailureCandidate(
                FailureKind.FORMAT_UNSUPPORTED,
                Confidence.MEDIUM,
                (
                    "Exact ALSA tuple configuration returned EINVAL; "
                    "physical/backend evidence is still required before "
                    "generalizing this mapping."
                ),
            )
        )

    if not out:
        out.append(
            FailureCandidate(
                FailureKind.UNKNOWN,
                Confidence.LOW,
                "No layer-specific classification is justified.",
            )
        )

    return tuple(out)
```

**Canonical invariant:**

```text
errno without origin/layer
≠ enough evidence for a semantic failure kind
```

---

# 98. FILE: `tools/michi_audio_lab/sample_normalizer.py`

**Role:** compare integer sample-domain values across different containers.

Important:

```text
caller supplies correct bit alignment
```

The helper must not guess packing rules.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SignificantBitAlignment(Enum):
    LSB = "lsb"
    MSB = "msb"


@dataclass(frozen=True)
class IntegerPcmFormat:
    container_bits: int
    significant_bits: int
    signed: bool
    little_endian: bool
    alignment: SignificantBitAlignment


def canonicalize_sample(
    raw_value: int,
    fmt: IntegerPcmFormat,
) -> int:
    """
    Canonicalize one integer PCM container to its signed significant sample value.

    Caller must provide correct alignment derived from the actual audio format.
    This intentionally does not guess GStreamer/ALSA packing rules.
    """
    if fmt.container_bits <= 0:
        raise ValueError("container_bits must be positive")
    if not (0 < fmt.significant_bits <= fmt.container_bits):
        raise ValueError("invalid significant_bits")

    container_mask = (1 << fmt.container_bits) - 1
    value = raw_value & container_mask

    if fmt.alignment is SignificantBitAlignment.MSB:
        value >>= fmt.container_bits - fmt.significant_bits
    else:
        value &= (1 << fmt.significant_bits) - 1

    if fmt.signed:
        sign_bit = 1 << (fmt.significant_bits - 1)
        if value & sign_bit:
            value -= 1 << fmt.significant_bits

    return value


def canonicalize_frames(
    frames: tuple[tuple[int, ...], ...],
    fmt: IntegerPcmFormat,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(canonicalize_sample(sample, fmt) for sample in frame)
        for frame in frames
    )
```

---

# 99. FILE: `tools/michi_audio_lab/identity_chaos.py`

**Role:** analyze measured identity-field stability.

It does not decide canonical identity by itself.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IdentitySnapshot:
    run_id: str
    scenario: str

    vendor_id: str | None
    product_id: str | None
    serial: str | None
    id_serial: str | None
    id_serial_short: str | None
    id_path: str | None
    sysfs_path: str | None

    alsa_card_id: str | None
    alsa_card_index: int | None
    alsa_longname: str | None


@dataclass(frozen=True)
class FieldStability:
    field_name: str
    distinct_non_null_values: tuple[str, ...]
    stable: bool
    missing_count: int


def analyze_field_stability(
    snapshots: Iterable[IdentitySnapshot],
    field_name: str,
) -> FieldStability:
    values = []
    missing = 0

    for snapshot in snapshots:
        value = getattr(snapshot, field_name)
        if value is None:
            missing += 1
        else:
            values.append(str(value))

    distinct = tuple(sorted(set(values)))
    return FieldStability(
        field_name=field_name,
        distinct_non_null_values=distinct,
        stable=len(distinct) <= 1,
        missing_count=missing,
    )
```

---

# 100. FILE: `tools/michi_audio_lab/transition_timeline.py`

**Role:** preserve measured transition components without calling them DAC lock.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransitionEvent:
    name: str
    monotonic_ns: int


@dataclass(frozen=True)
class TransitionTimingReport:
    reconfigure_to_hw_ready_ms: float | None
    reconfigure_to_first_audio_ms: float | None
    hw_ready_to_first_audio_ms: float | None


def _delta_ms(
    events: dict[str, TransitionEvent],
    start: str,
    end: str,
) -> float | None:
    if start not in events or end not in events:
        return None
    delta = events[end].monotonic_ns - events[start].monotonic_ns
    if delta < 0:
        return None
    return delta / 1_000_000.0


def summarize_transition(
    events: tuple[TransitionEvent, ...],
) -> TransitionTimingReport:
    by_name = {event.name: event for event in events}

    return TransitionTimingReport(
        reconfigure_to_hw_ready_ms=_delta_ms(
            by_name, "reconfigure_started", "alsa_hw_params_visible"
        ),
        reconfigure_to_first_audio_ms=_delta_ms(
            by_name, "reconfigure_started", "first_audio_observed"
        ),
        hw_ready_to_first_audio_ms=_delta_ms(
            by_name, "alsa_hw_params_visible", "first_audio_observed"
        ),
    )
```

---

# 101. TEST FILES

These tests are included so an agent can reproduce the reference semantics immediately.

## `tests/unit/infrastructure/test_proc_pcm_witness.py`

```python
from michi.infrastructure.audio_devices.proc_pcm_witness import (
    parse_hw_params,
    parse_status,
    parse_sw_params,
)


def test_parse_hw_params_runtime_witness():
    text = """
access: RW_INTERLEAVED
format: S32_LE
subformat: STD
channels: 2
rate: 96000 (96000/1)
period_size: 1024
buffer_size: 4096
"""
    snap = parse_hw_params(text)
    assert snap is not None
    assert snap.format == "S32_LE"
    assert snap.channels == 2
    assert snap.rate_hz == 96000
    assert snap.rate_num == 96000
    assert snap.rate_den == 1
    assert snap.period_size == 1024
    assert snap.buffer_size == 4096


def test_parse_hw_params_closed_returns_none():
    assert parse_hw_params("closed\n") is None


def test_parse_sw_params():
    snap = parse_sw_params(
        """
tstamp_mode: ENABLE
period_step: 1
avail_min: 512
start_threshold: 1024
stop_threshold: 4096
silence_threshold: 0
silence_size: 0
boundary: 4611686018427387904
"""
    )
    assert snap is not None
    assert snap.avail_min == 512
    assert snap.start_threshold == 1024


def test_parse_status():
    snap = parse_status(
        """
state: RUNNING
owner_pid: 1234
trigger_time: 123.000000000
tstamp: 124.000000000
delay: 1024
avail: 2048
avail_max: 4096
"""
    )
    assert snap is not None
    assert snap.state == "RUNNING"
    assert snap.owner_pid == 1234
    assert snap.delay_frames == 1024
```

## `tests/unit/infrastructure/test_gstreamer_specs.py`

```python
import pytest

from michi.infrastructure.audio_engines.gstreamer.direct_pipeline_spec import (
    StrictResamplerPolicy,
    build_strict_direct_spec,
    describe_pipeline,
)
from michi.infrastructure.audio_engines.gstreamer.runtime_evidence import (
    normalize_caps_structure,
)


def test_strict_pipeline_without_resampler_has_no_audioresample():
    spec = build_strict_direct_spec(
        alsa_device="hw:CARD=DX5,DEV=0",
        gst_format="S32LE",
        rate_hz=96000,
        channels=2,
        include_audioresample=False,
    )
    assert spec.resampler_policy is StrictResamplerPolicy.ABSENT
    assert "audioresample" not in describe_pipeline(spec)


def test_strict_pipeline_with_resampler_marks_passthrough_requirement():
    spec = build_strict_direct_spec(
        alsa_device="hw:CARD=DX5,DEV=0",
        gst_format="S32LE",
        rate_hz=96000,
        channels=2,
        include_audioresample=True,
    )
    assert spec.resampler_policy is StrictResamplerPolicy.PRESENT_PASSTHROUGH_REQUIRED
    assert "audioresample" in describe_pipeline(spec)


def test_strict_pipeline_requires_hw_binding():
    with pytest.raises(ValueError):
        build_strict_direct_spec(
            alsa_device="default",
            gst_format="S32LE",
            rate_hz=96000,
            channels=2,
            include_audioresample=False,
        )


def test_default_audioconvert_policy_is_explicitly_signal_conservative():
    spec = build_strict_direct_spec(
        alsa_device="hw:CARD=DX5,DEV=0",
        gst_format="S32LE",
        rate_hz=96000,
        channels=2,
        include_audioresample=False,
    )
    assert spec.audioconvert.dithering == "none"
    assert spec.audioconvert.noise_shaping == "none"
    assert spec.audioconvert.input_channels_reorder_mode == "none"


def test_normalize_runtime_caps():
    caps = normalize_caps_structure(
        element_name="capsfilter0",
        pad_name="src",
        structure_name="audio/x-raw",
        fields={
            "format": "S32LE",
            "rate": 96000,
            "channels": 2,
            "layout": "interleaved",
            "channel-mask": "0x3",
        },
    )
    assert caps.rate_hz == 96000
    assert caps.channels == 2
    assert caps.channel_mask == 3
```

## `tests/unit/application/test_pcm_evidence_recorder.py`

```python
from michi.application.pcm_evidence_recorder import (
    ActiveAlsaBinding,
    PcmEvidenceRecorder,
)
from michi.domain.audio_runtime_evidence import (
    AlsaHwParamsSnapshot,
    EvidenceFreshness,
    GstCapsSnapshot,
)


class FakeGst:
    def snapshot(self):
        return GstCapsSnapshot(
            element_name="capsfilter0",
            pad_name="src",
            media_type="audio/x-raw",
            format="S32LE",
            rate_hz=96000,
            channels=2,
            layout="interleaved",
            channel_mask=3,
        )


class FakeProc:
    def read(self, **kwargs):
        return (
            AlsaHwParamsSnapshot(
                access="RW_INTERLEAVED",
                format="S32_LE",
                subformat="STD",
                channels=2,
                rate_hz=96000,
                rate_num=96000,
                rate_den=1,
                period_size=1024,
                buffer_size=4096,
                raw={},
            ),
            None,
            None,
        )


class FailingGst:
    def snapshot(self):
        raise RuntimeError("observer failed")


class FailingProc:
    def read(self, **kwargs):
        raise OSError("proc unavailable")


def test_recorder_combines_gstreamer_and_kernel_witness():
    recorder = PcmEvidenceRecorder(FakeGst(), FakeProc())
    witness = recorder.capture(
        stable_device_id="dac-1",
        binding=ActiveAlsaBinding(
            locator="hw:CARD=DX5,DEV=0",
            card_index=2,
            pcm_device=0,
            subdevice=0,
        ),
        session_id="session-1",
        generation=3,
        significant_bits=24,
    )
    assert witness.freshness is EvidenceFreshness.CURRENT
    assert witness.gstreamer_pre_sink.rate_hz == 96000
    assert witness.alsa_hw.rate_hz == 96000
    assert witness.significant_bits == 24


def test_observer_failures_do_not_fail_playback_evidence_aggregator():
    recorder = PcmEvidenceRecorder(FailingGst(), FailingProc())
    witness = recorder.capture(
        stable_device_id="dac-1",
        binding=ActiveAlsaBinding(
            locator="hw:CARD=X,DEV=0",
            card_index=0,
            pcm_device=0,
            subdevice=0,
        ),
        session_id="session",
        generation=1,
        significant_bits=None,
    )
    assert witness.freshness is EvidenceFreshness.UNKNOWN
    assert witness.gstreamer_pre_sink is None
    assert witness.alsa_hw is None
```

## `tests/unit/domain/test_processing_evidence.py`

```python
from michi.domain.audio_processing_evidence import (
    EvidenceVerdict,
    ProcessingEvidence,
    processing_verdict,
)


def base(**overrides):
    data = dict(
        resampler_present=False,
        resampler_active=False,
        format_conversion_present=False,
        format_conversion_preserving=True,
        channel_remix_active=False,
        dither_active=False,
        noise_shaping_active=False,
        software_gain_db=0.0,
    )
    data.update(overrides)
    return ProcessingEvidence(**data)


def test_clean_processing_evidence_verifies():
    assert processing_verdict(base()) is EvidenceVerdict.VERIFIED


def test_active_resampler_breaks():
    assert processing_verdict(base(resampler_active=True)) is EvidenceVerdict.BROKEN


def test_non_preserving_format_conversion_breaks():
    assert (
        processing_verdict(
            base(
                format_conversion_present=True,
                format_conversion_preserving=False,
            )
        )
        is EvidenceVerdict.BROKEN
    )


def test_unknown_dither_state_blocks_verified():
    assert processing_verdict(base(dither_active=None)) is EvidenceVerdict.UNKNOWN
```

## `tests/unit/application/test_direct_qualification_policy.py`

```python
from michi.application.direct_qualification_policy import (
    QualificationAction,
    decide_unknown_tuple_experiment,
)


def test_explicit_test_uses_probe_branch():
    decision = decide_unknown_tuple_experiment(
        user_pressed_play=False,
        explicit_test_requested=True,
        known_probe_hard_reset_incident=False,
    )
    assert decision.action is QualificationAction.PRE_PROBE_EXACT_TUPLE


def test_play_research_branch_uses_real_exact_session():
    decision = decide_unknown_tuple_experiment(
        user_pressed_play=True,
        explicit_test_requested=False,
        known_probe_hard_reset_incident=False,
    )
    assert decision.action is QualificationAction.EXECUTE_EXACT_SESSION
    assert decision.empirical_status == "falsification_pending"


def test_known_probe_incident_blocks_automatic_qualification():
    decision = decide_unknown_tuple_experiment(
        user_pressed_play=True,
        explicit_test_requested=False,
        known_probe_hard_reset_incident=True,
    )
    assert decision.action is QualificationAction.REJECT
```

## `tests/unit/domain/test_audio_failure_evidence.py` — V3

```python
from michi.domain.audio_failure_evidence import (
    Confidence,
    FailureEvidence,
    FailureKind,
    FailureLayer,
    classify_failure,
)


def ev(layer, errno=None, state=None, present=True, exact=False):
    return FailureEvidence(
        layer=layer,
        errno_name=errno,
        message=None,
        alsa_pcm_state=state,
        udev_device_present=present,
        exact_tuple_was_being_configured=exact,
    )


def test_alsa_epipe_is_xrun():
    result = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EPIPE")
    )
    assert result[0].kind is FailureKind.XRUN
    assert result[0].confidence is Confidence.HIGH


def test_kernel_usb_epipe_is_endpoint_stall_not_xrun():
    result = classify_failure(
        ev(FailureLayer.KERNEL_USB_URB, "EPIPE")
    )
    assert result[0].kind is FailureKind.USB_ENDPOINT_STALL


def test_kernel_enospc_is_usb_bandwidth():
    result = classify_failure(
        ev(FailureLayer.KERNEL_USB_URB, "ENOSPC")
    )
    assert result[0].kind is FailureKind.USB_BANDWIDTH_EXHAUSTED


def test_alsa_estrpipe_is_suspended():
    result = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "ESTRPIPE")
    )
    assert result[0].kind is FailureKind.DEVICE_SUSPENDED


def test_einval_requires_exact_alsa_context():
    unknown = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EINVAL", exact=False)
    )
    assert unknown[0].kind is FailureKind.UNKNOWN

    supported_candidate = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EINVAL", exact=True)
    )
    assert supported_candidate[0].kind is FailureKind.FORMAT_UNSUPPORTED
    assert supported_candidate[0].confidence is Confidence.MEDIUM
```

## `tests/unit/tools/test_sample_normalizer.py`

```python
from tools.michi_audio_lab.sample_normalizer import (
    IntegerPcmFormat,
    SignificantBitAlignment,
    canonicalize_frames,
    canonicalize_sample,
)


def test_signed_16_lsb():
    fmt = IntegerPcmFormat(
        container_bits=16,
        significant_bits=16,
        signed=True,
        little_endian=True,
        alignment=SignificantBitAlignment.LSB,
    )
    assert canonicalize_sample(0x0001, fmt) == 1
    assert canonicalize_sample(0xFFFF, fmt) == -1
    assert canonicalize_sample(0x8000, fmt) == -32768


def test_s32_container_with_24_lsb_significant_bits():
    fmt = IntegerPcmFormat(
        container_bits=32,
        significant_bits=24,
        signed=True,
        little_endian=True,
        alignment=SignificantBitAlignment.LSB,
    )
    assert canonicalize_sample(0x00000001, fmt) == 1
    assert canonicalize_sample(0x00FFFFFF, fmt) == -1
    assert canonicalize_sample(0x00800000, fmt) == -(1 << 23)


def test_s32_container_with_24_msb_significant_bits():
    fmt = IntegerPcmFormat(
        container_bits=32,
        significant_bits=24,
        signed=True,
        little_endian=True,
        alignment=SignificantBitAlignment.MSB,
    )
    assert canonicalize_sample(0x00000100, fmt) == 1
    assert canonicalize_sample(0xFFFFFF00, fmt) == -1


def test_frame_canonicalization_preserves_channel_order():
    fmt = IntegerPcmFormat(
        container_bits=16,
        significant_bits=16,
        signed=True,
        little_endian=True,
        alignment=SignificantBitAlignment.LSB,
    )
    frames = ((1, 2), (3, 4))
    assert canonicalize_frames(frames, fmt) == frames
```

## `tests/unit/tools/test_identity_chaos.py`

```python
from tools.michi_audio_lab.identity_chaos import (
    IdentitySnapshot,
    analyze_field_stability,
)


def snap(run, path, index):
    return IdentitySnapshot(
        run_id=run,
        scenario="reconnect",
        vendor_id="1234",
        product_id="5678",
        serial="ABC",
        id_serial="Vendor_Product_ABC",
        id_serial_short="ABC",
        id_path=path,
        sysfs_path=path,
        alsa_card_id="DAC",
        alsa_card_index=index,
        alsa_longname="Reference DAC",
    )


def test_card_index_is_unstable_across_runs():
    snapshots = (snap("a", "usb-1", 2), snap("b", "usb-1", 5))
    result = analyze_field_stability(snapshots, "alsa_card_index")
    assert not result.stable


def test_serial_can_be_stable_across_runs():
    snapshots = (snap("a", "usb-1", 2), snap("b", "usb-1", 5))
    result = analyze_field_stability(snapshots, "serial")
    assert result.stable
```

## `tests/unit/tools/test_transition_timeline.py`

```python
from tools.michi_audio_lab.transition_timeline import (
    TransitionEvent,
    summarize_transition,
)


def test_transition_summary_keeps_observed_components_separate():
    events = (
        TransitionEvent("reconfigure_started", 1_000_000_000),
        TransitionEvent("alsa_hw_params_visible", 1_120_000_000),
        TransitionEvent("first_audio_observed", 1_180_000_000),
    )
    report = summarize_transition(events)
    assert report.reconfigure_to_hw_ready_ms == 120.0
    assert report.reconfigure_to_first_audio_ms == 180.0
    assert report.hw_ready_to_first_audio_ms == 60.0
```

---

# 102. EXPERIMENT MANIFESTS

The Lab manifests are deliberately machine-readable.

They define the question before the implementation.

An agent must not silently change the question to make its implementation pass.

---

# 103. R1 — Linux PCM Runtime Witness

File:

```text
tools/michi_audio_lab/experiments/R1_runtime_witness.yaml
```

```yaml
schema_version: 1
experiment_id: R1_RUNTIME_WITNESS
status: required_before_signal-proof-freeze

question: >
  Does the real GStreamer Direct session produce the Linux hardware PCM
  configuration that Michi planned?

variants:
  - rate_hz: 44100
    source_bits: 16
  - rate_hz: 96000
    source_bits: 24
  - rate_hz: 192000
    source_bits: 24

capture:
  - output_plan
  - gst_current_caps_pre_sink
  - proc_hw_params
  - proc_sw_params
  - proc_status
  - alsa_significant_bits
  - gst_bus_errors

pass:
  - requested_rate_equals_proc_rate
  - requested_channels_equals_proc_channels
  - carrier_format_is_expected
  - significant_bits_preserved
  - no_observer_failure_affects_playback

falsifier:
  - proc_runtime_differs_from_plan
  - gstreamer_caps_differs_from_proc_without_explanation
```

Promotion outcome:

If R1 repeatedly shows:

```text
OutputPlan
=
GStreamer current caps
=
Linux PCM hw_params
```

for the declared dimensions, Runtime Evidence can be promoted to:

```text
LINUX_INTEGRATION_TESTED
```

Physical DAC repetition promotes the exact target to:

```text
PHYSICAL_HARDWARE_TESTED
```

---

# 104. R2 — Strict Resampler A/B

File:

```text
tools/michi_audio_lab/experiments/R2_resampler_ab.yaml
```

```yaml
schema_version: 1
experiment_id: R2_STRICT_RESAMPLER_AB
status: falsification-required

question: >
  Can Strict Direct remove audioresample entirely without losing robust
  playback, seek, transition, and reconnect behavior?

variant_a:
  audioresample: present
  requirement: passthrough_only

variant_b:
  audioresample: absent

matrix:
  rates: [44100, 48000, 96000, 192000]
  operations:
    - first_play
    - seek
    - pause_resume
    - same_rate_track_change
    - rate_change
    - reconnect

prefer_variant_b_if:
  - all_required_cases_pass
  - no_hidden_resampling
  - failure_rate_not_worse
  - transition_behavior_not_worse

kill_variant_b_if:
  - reproducible_negotiation_failure
  - reproducible_transition_regression
```

Canonical decision rule:

```text
If resampler-free Strict is not worse and passes the complete matrix:
→ prefer absence by construction.

If it fails reproducibly:
→ keep audioresample and prove passthrough.
```

---

# 105. R3 — Sample Preservation

File:

```text
tools/michi_audio_lab/experiments/R3_sample_preservation.yaml
```

```yaml
schema_version: 1
experiment_id: R3_SAMPLE_PRESERVATION
status: required-before-strong-processing-verdict

question: >
  Which GStreamer integer-format conversions are sample-preserving under
  Michi's Strict configuration?

cases:
  - input: S16LE
    output: S16LE
  - input: S24LE
    output: S24LE
  - input: S24LE
    output: S32LE
    significant_bits: 24
  - input: S32LE
    significant_bits: 24
    output: S32LE
    output_significant_bits: 24

strict_audioconvert:
  dithering: none
  noise_shaping: none
  input_channels_reorder_mode: none

compare:
  mode: canonical_significant_sample_values
  preserve_channel_order: true

pass:
  - canonical_samples_equal
  - channel_order_equal
```

This experiment decides:

```text
which integer conversions may be called preserving
whether Strict must force explicit audioconvert properties
how S24→S32/24 carrier is verified
```

---

# 106. R4 — Probe vs Real Session

File:

```text
tools/michi_audio_lab/experiments/R4_probe_vs_session.yaml
```

```yaml
schema_version: 1
experiment_id: R4_PROBE_VS_REAL_SESSION
status: falsification-required

question: >
  Does a pre-probe provide enough benefit to justify opening/configuring the
  hardware before the real playback session?

variant_a:
  sequence:
    - alsa_probe_exact
    - close_probe
    - gstreamer_exact_session

variant_b:
  sequence:
    - gstreamer_exact_session
    - successful_runtime_becomes_evidence

measure:
  - time_to_first_audio
  - open_failures
  - usb_resets
  - kernel_errors
  - session_failures
  - rate_transition_failures

hardware_minimum: 2

decision:
  keep_preprobe_only_if: measurable_reliability_or_safety_benefit
  otherwise: prefer_real_session_evidence
```

This experiment is allowed to simplify the architecture.

If pre-probe shows no meaningful benefit:

```text
normal Play path
→ exact execution first

michi-alsa-probe
→ explicit qualification / Test DAC / diagnostics
```

---

# 107. R5 — Identity Chaos

File:

```text
tools/michi_audio_lab/experiments/R5_identity_chaos.yaml
```

```yaml
schema_version: 1
experiment_id: R5_IDENTITY_CHAOS
status: required-before-identity-policy-freeze

scenarios:
  - reconnect_same_port
  - reboot_same_port
  - move_usb_port
  - hub_same_port
  - move_hub
  - suspend_resume
  - two_identical_dacs
  - no_serial_device
  - generic_serial_device

capture:
  - vid
  - pid
  - serial
  - id_serial
  - id_serial_short
  - id_path
  - sysfs_path
  - alsa_card_id
  - alsa_card_index
  - alsa_longname

output:
  - field_stability_matrix
  - collision_matrix
  - identity_confidence_rules
```

Result must be a measured:

```text
field stability matrix
collision matrix
confidence policy
```

not another theoretical identity hierarchy.

---

# 108. R6 — Failure Semantics Matrix

File:

```text
tools/michi_audio_lab/experiments/R6_failure_matrix.yaml
```

```yaml
schema_version: 1
experiment_id: R6_FAILURE_SEMANTICS
status: required-before-error-mapper-freeze

cases:
  - device_busy
  - unsupported_exact_tuple
  - unplug_before_acquire
  - unplug_during_configure
  - unplug_while_running
  - injected_xrun
  - helper_timeout
  - malformed_helper_json
  - release_failure

capture:
  - failure_layer
  - errno_name
  - gst_error_domain
  - gst_error_code
  - gst_error_message
  - udev_presence
  - proc_status
  - session_state
  - exact_tuple_context

rule:
  - never_freeze_errno_mapping_before_reproduction
  - errno_semantics_are_layer_specific
  - ALSA_PCM_EPIPE_is_XRUN_but_KERNEL_USB_URB_EPIPE_is_ENDPOINT_STALL
  - EINVAL_is_not_universal_unsupported
```

Freeze production error mapping only after physical reproduction.

---

# 109. R7 — Rate Transition Lab

File:

```text
tools/michi_audio_lab/experiments/R7_transition_lab.yaml
```

```yaml
schema_version: 1
experiment_id: R7_RATE_TRANSITION_LAB
status: required-before-transition-policy-freeze

transitions:
  - [44100, 96000]
  - [96000, 192000]
  - [192000, 44100]
  - [48000, 96000]

events:
  - reconfigure_started
  - previous_pcm_closed
  - new_pipeline_configured
  - alsa_hw_params_visible
  - playback_running
  - first_audio_observed

report:
  - reconfigure_to_hw_ready_ms
  - reconfigure_to_first_audio_ms
  - hw_ready_to_first_audio_ms

terminology:
  use: observed_output_stabilization_time
  forbid_without_stronger_evidence: dac_lock_time
```

R7 initially answers only:

```text
what observable transition phases exist?
how long do they take?
are they repeatable?
```

It does not create Adaptive Resync automatically.

---

# 110. IMPLEMENTATION ORDER FOR THIS RESEARCH LAYER

Do not implement every lab at once.

Recommended order:

```text
R1 Runtime Witness
↓
R3 Sample Preservation
↓
R2 Resampler A/B
↓
R4 Probe vs Session
↓
R5 Identity Chaos
↓
R6 Failure Matrix
↓
R7 Transition Lab
```

Reason:

R1 and R3 create the evidence machinery needed to interpret later experiments.

---

# 111. DAC-007 INTEGRATION DELTA AFTER R1

When implementing DAC-007, add these **non-authoritative** seams:

```text
GstRuntimeEvidenceTap
ProcPcmWitnessReader
PcmEvidenceRecorder
```

But enforce:

```text
observer failure
≠ playback failure
```

If evidence capture fails:

```text
Core Signal dimension
→ UNKNOWN where necessary
```

Not:

```text
stop audio
```

---

# 112. DAC-006A CONFORMANCE DELTA

`processing` should become a derived product dimension.

Internal evidence should preserve:

```text
resampler_present
resampler_active
format_conversion_present
format_conversion_preserving
channel_remix_active
dither_active
noise_shaping_active
software_gain_db
```

This does not require exposing every field in normal UI.

Inspector can.

---

# 113. SOURCE SIGNIFICANT BITS VS HARDWARE SIGNIFICANT BITS

Do not keep one ambiguous:

```text
significant_bits
```

without provenance.

Use conceptually:

```text
source_significant_bits
alsa_hardware_significant_bits
```

and compare them.

Future sources such as UAC descriptors must have their own provenance rather than overwrite ALSA evidence.

---

# 114. HARDWARE-LAB ARTIFACT

Every physical R1/R4/R6/R7 run should export one directory:

```text
artifacts/audio-lab/<run-id>/
├── environment.json
├── identity.json
├── output-plan.json
├── gst-current-caps.json
├── alsa-hw-params.txt
├── alsa-sw-params.txt
├── alsa-status.txt
├── significant-bits.json
├── events.jsonl
├── result.json
└── README.md
```

This makes failures auditable after the fact.

---

# 115. `result.json` MINIMUM

```json
{
  "schema_version": 1,
  "experiment_id": "R1_RUNTIME_WITNESS",
  "run_id": "uuid",
  "hardware": {
    "stable_device_id": "redacted-or-local",
    "identity_confidence": "high"
  },
  "requested": {
    "rate_hz": 96000,
    "significant_bits": 24,
    "channels": 2
  },
  "observed": {
    "gst_format": "S32LE",
    "gst_rate_hz": 96000,
    "alsa_format": "S32_LE",
    "alsa_rate_hz": 96000,
    "alsa_channels": 2,
    "alsa_significant_bits": 24
  },
  "verdict": "pass",
  "evidence_level": "physical_hardware_tested"
}
```

---

# 116. LAB NON-INTERFERENCE

All instrumentation must eventually be tested:

```text
observer OFF
vs
observer ON
```

Compare:

```text
XRUN count
time to first audio
rate transition failures
CPU impact
callback duration
```

If an observer materially worsens playback:

```text
do not ship it as always-on product instrumentation
```

It may remain Lab-only.

---

# 117. RESEARCH KILL CRITERIA

## Runtime Witness

Kill as product feature if:

```text
procfs format is too unstable for target distributions
or observer overhead/reliability is poor
```

Keep as test-only witness.

## Resampler-free Strict

Kill if:

```text
real GStreamer transitions/seek/reconnect regress reproducibly
```

## Sample Normalizer

Kill generic abstraction if:

```text
packing semantics become too easy to misuse
```

Replace with explicit format-specific converters.

## Execution-first qualification

Kill if:

```text
pre-probe demonstrates measurable safety/reliability advantage
```

## Identity confidence automation

Weaken if:

```text
two identical devices cannot be distinguished safely
```

Require user-assisted linking.

## Failure classifier

Never promote ambiguous rules.

Unknown remains allowed.

---

# 118. WEB/UPSTREAM RESEARCH REGISTER

Primary upstream areas for this implementation layer:

```text
Linux ALSA procfs runtime files
https://docs.kernel.org/sound/designs/procfile.html

ALSA PCM plugins / hw semantics
https://www.alsa-project.org/alsa-doc/alsa-lib/pcm_plugins.html

ALSA hardware parameters / significant bits
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___h_w___params.html

GStreamer GstPad current caps
https://gstreamer.freedesktop.org/documentation/gstreamer/gstpad.html

GStreamer audioconvert
https://gstreamer.freedesktop.org/documentation/audioconvert/index.html

GStreamer GstAudioConverter
https://gstreamer.freedesktop.org/documentation/audio/gstaudioconverter.html

GStreamer GstHarness
https://gstreamer.freedesktop.org/documentation/check/gstharness.html

GStreamer alsasink
https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html

Linux snd-usb-audio rate parsing/validation
https://github.com/torvalds/linux/blob/master/sound/usb/format.c

Linux snd-usb-audio clocks
https://github.com/torvalds/linux/blob/master/sound/usb/clock.c

PortAudio QA / hotplug / buffering methodology
https://github.com/PortAudio/portaudio

DeaDBeeF ALSA transition history
https://github.com/DeaDBeeF-Player/deadbeef

systemd udev USB identity
https://github.com/systemd/systemd
```

---

# 119. FINAL RESEARCH-TO-CODE RULE

Do not answer an empirical question with another service class.

Answer it with:

```text
observable fact
+
small adapter
+
artifact
+
experiment
+
counterexample search
```

Only after that may the architecture grow.

---

# 120. FINAL QUICK-IMPLEMENTATION CONTRACT

A coding agent implementing this layer should be able to proceed file-by-file:

```text
1. create immutable evidence DTOs
2. create pure proc parsers
3. create GStreamer current-caps normalizer
4. create Direct pipeline specs
5. create non-authoritative evidence recorder
6. run unit tests
7. wire real PyGObject adapter
8. run R1
9. run R3
10. decide R2
11. run R4
12. freeze only the conclusions that survive
```

This ordering is intentionally more important than adding new DAC features.

**END OF RESEARCH-TO-IMPLEMENTATION BLUEPRINT**

# PART III — MAYÉUTICA → ANÁLISIS TÉCNICO → FALSACIONISMO → RESULTADO DE IMPLEMENTACIÓN

**Status:** CANONICAL ENGINEERING METHOD FOR DAC RESEARCH AND PIONEER FEATURES  
**Purpose:** prevent OpenCode/DeepSeek/humans from converting an attractive hypothesis into product behavior without the required engineering evidence.

---

# 121. THE FOUR-STAGE ENGINEERING METHOD

The method is now:

```text
MAYÉUTICA
    ↓
ANÁLISIS TÉCNICO DE INGENIERÍA
    ↓
FALSACIONISMO
    ↓
RESULTADO DE IMPLEMENTACIÓN
```

The stages are not optional labels.

Each stage has a different authority.

---

# 122. STAGE 1 — MAYÉUTICA

The mayeutic stage asks:

```text
What are we really trying to achieve?
What do we think is already true?
Which premise makes the current answer look obvious?
What would change if that premise were false?
```

Output:

```text
question
hidden assumptions
desired user outcome
```

It must not output production code.

Example:

```text
Question:
Does Strict Direct need audioresample?

Hidden assumption:
GStreamer rate transitions require a resampler element.

Desired outcome:
Source-native playback where resampling is impossible unless explicitly allowed.
```

---

# 123. STAGE 2 — TECHNICAL ANALYSIS

The engineer translates the philosophical question into system facts.

Every statement becomes exactly one of:

```text
UPSTREAM_DOCUMENTED
LOCALLY_OBSERVED
DEDUCED
HYPOTHESIS
UNKNOWN
```

This is the anti-speculation ledger.

---

# 124. FACT AUTHORITY

## `UPSTREAM_DOCUMENTED`

Example:

```text
GstBaseTransform exposes is_passthrough().
```

Can be used to design the adapter.

It does not prove Michi's runtime instance is passthrough.

## `LOCALLY_OBSERVED`

Example:

```text
audioresample.is_passthrough() == True
during R8 run abc.
```

May support a claim only within its declared environment/scope.

## `DEDUCED`

Example:

```text
If audioresample is absent from the Direct branch,
that branch cannot perform rate conversion through audioresample.
```

Valid only if the topology observation is complete for the relevant branch.

## `HYPOTHESIS`

Example:

```text
Removing audioresample will not regress rate transitions.
```

May produce an experiment.

It may not produce canonical behavior yet.

## `UNKNOWN`

Example:

```text
Whether this specific DAC needs a long hardware settling time.
```

Must remain UNKNOWN.

No default may be invented.

---

# 125. STAGE 2 OUTPUT

Technical analysis records:

```text
owning layer
upstream APIs
candidate files
facts
failure modes
unknowns
```

Only after ownership/API boundaries exist may falsification begin.

---

# 126. STAGE 3 — FALSACIONISM

The falsification stage must define before implementation promotion:

```text
hypothesis
prediction
experiment ID
falsifiers
kill criterion
safe retreat
required evidence level
```

An experiment that only defines "success" is invalid.

A falsifier is not:

```text
test failed because code has a syntax error
```

A falsifier is:

```text
a valid observation that contradicts the engineering hypothesis
```

---

# 127. STAGE 4 — IMPLEMENTATION RESULT

Only four dispositions exist:

```text
PROMOTE
PROMOTE_WITH_LIMITS
REJECT
INCONCLUSIVE
```

`INCONCLUSIVE` is a valid result.

OpenCode must not convert `INCONCLUSIVE` into its preferred implementation.

---

# 128. NO-SPECULATION PROMOTION RULE

An implementation cannot be promoted when:

```text
a critical fact is HYPOTHESIS
or
a critical fact is UNKNOWN
or
required evidence level is not reached
or
a declared falsifier was observed
or
the result still contains unresolved unknowns
```

The allowed response is:

```text
implement measurement/tooling
keep product behavior unchanged
report INCONCLUSIVE
```

---

# 129. MACHINE MODEL — `engineering_method.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EngineeringFactKind(Enum):
    UPSTREAM_DOCUMENTED = "upstream_documented"
    LOCALLY_OBSERVED = "locally_observed"
    DEDUCED = "deduced"
    HYPOTHESIS = "hypothesis"
    UNKNOWN = "unknown"


class EngineeringPhase(Enum):
    MAYEUTIC = "mayeutic"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FALSIFICATION = "falsification"
    IMPLEMENTATION_RESULT = "implementation_result"


class ImplementationDisposition(Enum):
    PROMOTE = "promote"
    PROMOTE_WITH_LIMITS = "promote_with_limits"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class EngineeringFact:
    fact_id: str
    statement: str
    kind: EngineeringFactKind
    critical: bool
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class MayeuticRecord:
    question: str
    hidden_assumptions: tuple[str, ...]
    desired_user_outcome: str


@dataclass(frozen=True)
class TechnicalAnalysisRecord:
    owning_layer: str
    upstream_apis: tuple[str, ...]
    candidate_files: tuple[str, ...]
    facts: tuple[EngineeringFact, ...]
    failure_modes: tuple[str, ...]
    unknowns: tuple[str, ...]


@dataclass(frozen=True)
class FalsificationRecord:
    hypothesis: str
    prediction: str
    experiment_id: str
    falsifiers: tuple[str, ...]
    kill_criterion: str
    safe_retreat: str


@dataclass(frozen=True)
class ImplementationResult:
    disposition: ImplementationDisposition
    summary: str
    implementation_files: tuple[str, ...]
    evidence_level: str
    constraints: tuple[str, ...]
    unresolved_unknowns: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngineeringInquiry:
    inquiry_id: str
    mayeutic: MayeuticRecord
    technical: TechnicalAnalysisRecord
    falsification: FalsificationRecord
    result: ImplementationResult | None = None


def critical_speculation_blockers(
    facts: tuple[EngineeringFact, ...],
) -> tuple[EngineeringFact, ...]:
    return tuple(
        fact
        for fact in facts
        if fact.critical
        and fact.kind in {
            EngineeringFactKind.HYPOTHESIS,
            EngineeringFactKind.UNKNOWN,
        }
    )


def technical_analysis_ready_for_falsification(
    record: TechnicalAnalysisRecord,
) -> bool:
    return bool(record.owning_layer and record.candidate_files)


def can_promote_implementation(
    inquiry: EngineeringInquiry,
) -> bool:
    if inquiry.result is None:
        return False

    if inquiry.result.disposition not in {
        ImplementationDisposition.PROMOTE,
        ImplementationDisposition.PROMOTE_WITH_LIMITS,
    }:
        return False

    if critical_speculation_blockers(inquiry.technical.facts):
        return False

    if inquiry.result.unresolved_unknowns:
        return False

    return True
```

---

# 130. MACHINE MODEL — `implementation_promotion_gate.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.engineering_method import (
    EngineeringInquiry,
    ImplementationDisposition,
    can_promote_implementation,
)


class EvidenceLevel(Enum):
    DOMAIN_REFERENCE_TESTED = 10
    BACKEND_FAKE_TESTED = 20
    VIRTUAL_STACK_TESTED = 30
    LINUX_INTEGRATION_TESTED = 40
    USB_GADGET_STACK_TESTED = 45
    PHYSICAL_HARDWARE_TESTED = 50
    MULTI_HARDWARE_TESTED = 60


@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    reason: str


def promotion_gate(
    inquiry: EngineeringInquiry,
    *,
    achieved_evidence: EvidenceLevel,
    required_evidence: EvidenceLevel,
    falsifier_observed: bool,
) -> PromotionDecision:
    if falsifier_observed:
        return PromotionDecision(
            allowed=False,
            reason="A declared falsifier was observed.",
        )

    if achieved_evidence.value < required_evidence.value:
        return PromotionDecision(
            allowed=False,
            reason=(
                f"Evidence {achieved_evidence.name} is below required "
                f"{required_evidence.name}."
            ),
        )

    if not can_promote_implementation(inquiry):
        return PromotionDecision(
            allowed=False,
            reason=(
                "Critical speculation or unresolved unknowns remain, "
                "or the disposition is not promotable."
            ),
        )

    if inquiry.result is None:
        return PromotionDecision(False, "No implementation result exists.")

    if inquiry.result.disposition is ImplementationDisposition.PROMOTE_WITH_LIMITS:
        return PromotionDecision(
            allowed=True,
            reason="Promotion allowed only within declared constraints.",
        )

    return PromotionDecision(
        allowed=True,
        reason="Promotion requirements satisfied.",
    )
```

This is deliberately conservative.

It is acceptable for the gate to delay a pioneer feature.

It is not acceptable for the gate to permit speculation because implementation is convenient.

---

# 131. OPENCODE ACTION MATRIX

| Fact type | OpenCode may do | OpenCode may NOT do |
|---|---|---|
| UPSTREAM_DOCUMENTED | implement adapter/API boundary | claim local runtime behavior |
| LOCALLY_OBSERVED | implement within tested scope | generalize beyond evidence |
| DEDUCED | implement pure consequence | silently expand premises |
| HYPOTHESIS | build experiment/instrumentation | choose hypothesis as product behavior |
| UNKNOWN | represent UNKNOWN | invent fallback/default |

This table is canonical.

---

# 132. NEW GStreamer RESEARCH FINDING — PASSTHROUGH IS OBSERVABLE

GStreamer officially exposes:

```text
GstBaseTransform.is_passthrough()
```

including a Python wrapper.

This means R2/R8 no longer need to infer passthrough only from equal caps.

For an actual `audioresample` or `audioconvert` instance:

```text
element exists
+
element is GstBaseTransform
+
element.is_passthrough() == true
```

is stronger runtime evidence.

It is still not physical-DAC evidence.

---

# 133. NEW GStreamer RESEARCH FINDING — PIPELINE TOPOLOGY IS OBSERVABLE

`Gst.Bin` can recursively enumerate child elements.

It can also search recursively by element factory name.

Therefore the Lab can ask:

```text
How many audioresample elements actually exist?
How many audioconvert elements?
Is a volume element hidden in a child bin?
Which alsasink is active?
```

This reduces topology speculation.

---

# 134. NEW GStreamer RESEARCH FINDING — DOT GRAPH AS AUDIT ARTIFACT

GStreamer can generate a Graphviz DOT representation containing:

```text
pipeline topology
caps on links
element states
modified parameters
```

via:

```text
Gst.debug_bin_to_dot_data()
Gst.debug_bin_to_dot_file_with_ts()
```

DOT graphs are a **Lab artifact**, not playback authority.

They are valuable because a human auditor can inspect exactly what pipeline existed in the failing run.

---

# 135. NEW GStreamer RESEARCH FINDING — LATENCY TRACER

GStreamer ships a latency tracer that can report:

```text
pipeline latency
per-element latency
reported element latency
```

The tracer can help R9/R10.

It must not be enabled permanently until Observer Effect testing proves acceptable overhead.

---

# 136. STREAMING-THREAD SAFETY

GStreamer pad-probe callbacks run in the streaming thread.

Therefore:

```text
NO filesystem write
NO SQLite
NO GUI call
NO pipeline state change
NO long JSON serialization
```

inside a data pad probe.

Allowed pattern:

```text
read minimal immutable fact
→ enqueue tiny record
→ return immediately
→ process elsewhere
```

This is a hard implementation rule.

---

# 137. CURRENT GStreamer REFERENCE POINT

As of 2026-09 research:

```text
current stable GStreamer: 1.28.6
```

The `audioconvert` input channel reorder properties exist since 1.26.

Michi must not hard-code:

```text
if gst_version >= (1, 26):
```

when property/API feature detection can answer the question directly.

Preferred:

```text
element.find_property("input-channels-reorder-mode")
```

If absent:

```text
record feature unavailable
do not invent a property
```

---

# 138. PIPELINE RUNTIME EVIDENCE DOMAIN

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransformRole(Enum):
    FORMAT_CONVERTER = "format_converter"
    RESAMPLER = "resampler"
    VOLUME = "volume"
    DSP = "dsp"
    CAPS = "caps"
    SINK = "sink"
    DECODER = "decoder"
    QUEUE = "queue"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ElementRuntimeSnapshot:
    element_name: str
    factory_name: str | None
    role: TransformRole
    base_transform_passthrough: bool | None
    properties: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SinkClockSnapshot:
    provide_clock: bool | None
    slave_method: str | None
    selected_pipeline_clock_name: str | None
    clock_lost_events: int


@dataclass(frozen=True)
class PipelineRuntimeSnapshot:
    elements: tuple[ElementRuntimeSnapshot, ...]
    sink_clock: SinkClockSnapshot | None
    dot_graph: str | None = None

    def factories(self) -> tuple[str, ...]:
        return tuple(
            item.factory_name
            for item in self.elements
            if item.factory_name is not None
        )

    def by_factory(
        self,
        factory_name: str,
    ) -> tuple[ElementRuntimeSnapshot, ...]:
        return tuple(
            item
            for item in self.elements
            if item.factory_name == factory_name
        )


def classify_factory(factory_name: str | None) -> TransformRole:
    mapping = {
        "audioconvert": TransformRole.FORMAT_CONVERTER,
        "audioresample": TransformRole.RESAMPLER,
        "volume": TransformRole.VOLUME,
        "capsfilter": TransformRole.CAPS,
        "alsasink": TransformRole.SINK,
        "queue": TransformRole.QUEUE,
        "queue2": TransformRole.QUEUE,
    }
    if factory_name is None:
        return TransformRole.UNKNOWN
    return mapping.get(factory_name, TransformRole.UNKNOWN)
```

---

# 139. FILE — `pipeline_inspector.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from michi.domain.audio_pipeline_evidence import (
    ElementRuntimeSnapshot,
    PipelineRuntimeSnapshot,
    SinkClockSnapshot,
    classify_factory,
)


@dataclass(frozen=True)
class ElementObservation:
    name: str
    factory_name: str | None
    is_base_transform: bool
    is_passthrough: bool | None
    properties: tuple[tuple[str, str], ...]


class GstPipelineProbePort(Protocol):
    def enumerate_elements(self) -> tuple[ElementObservation, ...]:
        ...

    def sink_clock_snapshot(self) -> SinkClockSnapshot | None:
        ...

    def dot_graph(self) -> str | None:
        ...


class PipelineInspector:
    def __init__(self, probe: GstPipelineProbePort) -> None:
        self._probe = probe

    def snapshot(self) -> PipelineRuntimeSnapshot:
        elements = tuple(
            ElementRuntimeSnapshot(
                element_name=item.name,
                factory_name=item.factory_name,
                role=classify_factory(item.factory_name),
                base_transform_passthrough=(
                    item.is_passthrough
                    if item.is_base_transform
                    else None
                ),
                properties=item.properties,
            )
            for item in self._probe.enumerate_elements()
        )

        return PipelineRuntimeSnapshot(
            elements=elements,
            sink_clock=self._probe.sink_clock_snapshot(),
            dot_graph=self._probe.dot_graph(),
        )


def signal_transform_summary(
    snapshot: PipelineRuntimeSnapshot,
) -> dict[str, Any]:
    resamplers = snapshot.by_factory("audioresample")
    converters = snapshot.by_factory("audioconvert")
    volumes = snapshot.by_factory("volume")

    return {
        "audioresample_count": len(resamplers),
        "audioresample_all_passthrough": (
            all(item.base_transform_passthrough is True for item in resamplers)
            if resamplers
            else True
        ),
        "audioconvert_count": len(converters),
        "audioconvert_all_passthrough": (
            all(item.base_transform_passthrough is True for item in converters)
            if converters
            else True
        ),
        "volume_count": len(volumes),
    }
```

The inspector is passive.

It cannot mutate the pipeline.

---

# 140. FILE — `pygobject_probe_reference.py`

```python
from __future__ import annotations

"""
STATUS: LINUX_INTEGRATION_PENDING

Near-production PyGObject blueprint.

The plan-generation environment does not provide gi.repository/GStreamer,
therefore this file must be integration-tested on Michi's Linux target before
promotion.

Upstream APIs:
- Gst.Bin.iterate_recurse()
- GstBase.BaseTransform.is_passthrough()
- GstAudio.AudioBaseSink.get_provide_clock()
- GstAudio.AudioBaseSink.get_slave_method()
- Gst.debug_bin_to_dot_data()
"""


def _property_as_string(element, name: str) -> str | None:
    try:
        pspec = element.find_property(name)
    except Exception:
        return None

    if pspec is None:
        return None

    try:
        value = element.get_property(name)
    except Exception:
        return None

    return str(value)


class GstPyGObjectPipelineProbe:
    def __init__(
        self,
        *,
        pipeline,
        sink,
        Gst,
        GstBase,
        GstAudio,
    ) -> None:
        self._pipeline = pipeline
        self._sink = sink
        self._Gst = Gst
        self._GstBase = GstBase
        self._GstAudio = GstAudio
        self._clock_lost_events = 0

    def note_clock_lost(self) -> None:
        self._clock_lost_events += 1

    def enumerate_elements(self):
        from michi.infrastructure.audio_engines.gstreamer.pipeline_inspector import (
            ElementObservation,
        )

        iterator = self._pipeline.iterate_recurse()
        observations = []

        while True:
            result, value = iterator.next()

            if result == self._Gst.IteratorResult.OK:
                element = value

                factory = element.get_factory()
                factory_name = (
                    factory.get_name()
                    if factory is not None
                    else None
                )

                is_transform = isinstance(
                    element,
                    self._GstBase.BaseTransform,
                )

                passthrough = None
                if is_transform:
                    try:
                        passthrough = bool(element.is_passthrough())
                    except Exception:
                        passthrough = None

                properties = []
                for property_name in (
                    "dithering",
                    "dithering-threshold",
                    "noise-shaping",
                    "input-channels-reorder-mode",
                    "volume",
                    "mute",
                    "device",
                    "buffer-time",
                    "latency-time",
                    "provide-clock",
                    "slave-method",
                ):
                    value_string = _property_as_string(
                        element,
                        property_name,
                    )
                    if value_string is not None:
                        properties.append(
                            (property_name, value_string)
                        )

                observations.append(
                    ElementObservation(
                        name=element.get_name(),
                        factory_name=factory_name,
                        is_base_transform=is_transform,
                        is_passthrough=passthrough,
                        properties=tuple(properties),
                    )
                )

            elif result == self._Gst.IteratorResult.RESYNC:
                observations.clear()
                iterator.resync()

            elif result == self._Gst.IteratorResult.DONE:
                break

            else:
                raise RuntimeError(
                    "GStreamer element iteration failed."
                )

        return tuple(observations)

    def sink_clock_snapshot(self):
        from michi.domain.audio_pipeline_evidence import (
            SinkClockSnapshot,
        )

        provide_clock = None
        slave_method = None

        if isinstance(self._sink, self._GstAudio.AudioBaseSink):
            try:
                provide_clock = bool(
                    self._sink.get_provide_clock()
                )
            except Exception:
                pass

            try:
                slave_method = str(
                    self._sink.get_slave_method()
                )
            except Exception:
                pass

        selected_clock_name = None
        try:
            clock = self._pipeline.get_clock()
            if clock is not None:
                selected_clock_name = clock.get_name()
        except Exception:
            pass

        return SinkClockSnapshot(
            provide_clock=provide_clock,
            slave_method=slave_method,
            selected_pipeline_clock_name=selected_clock_name,
            clock_lost_events=self._clock_lost_events,
        )

    def dot_graph(self):
        details = (
            self._Gst.DebugGraphDetails.MEDIA_TYPE
            | self._Gst.DebugGraphDetails.CAPS_DETAILS
            | self._Gst.DebugGraphDetails.NON_DEFAULT_PARAMS
            | self._Gst.DebugGraphDetails.STATES
        )
        try:
            return self._Gst.debug_bin_to_dot_data(
                self._pipeline,
                details,
            )
        except Exception:
            return None
```

**Status:** `LINUX_INTEGRATION_PENDING`.

The plan-generation environment does not have PyGObject/GStreamer installed.

OpenCode must run the real integration test before calling this implementation complete.

---

# 141. WHY `is_passthrough()` CHANGES R2/R3

Before this research:

```text
same caps
→ maybe passthrough
```

Now:

```text
same caps
+
BaseTransform.is_passthrough()
→ much stronger runtime evidence
```

R3 still matters because a legitimate preserving container conversion may require `audioconvert` not to be passthrough.

Example:

```text
source representation
S24LE

hardware carrier
S32LE / 24 significant bits
```

A non-passthrough converter is not automatically a failure.

It becomes:

```text
UNKNOWN
until sample-preservation evidence exists.
```

---

# 142. STRICT PIPELINE AUDIT

`StrictPipelineAudit` encodes this rule.

It does **not** define:

```text
audioconvert present = bad
```

It defines:

```text
software volume present
→ BLOCKER

forbidden audioresample present
→ BLOCKER

allowed audioresample not proven passthrough
→ BLOCKER

audioconvert non-passthrough
+ preserving evidence unknown
→ UNKNOWN

audioconvert non-passthrough
+ preserving evidence false
→ BLOCKER

audioconvert non-passthrough
+ preserving evidence true
→ acceptable within evidence scope
```

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_pipeline_evidence import PipelineRuntimeSnapshot


class AuditSeverity(Enum):
    INFO = "info"
    UNKNOWN = "unknown"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class PipelineAuditFinding:
    code: str
    severity: AuditSeverity
    message: str


@dataclass(frozen=True)
class StrictPipelineAudit:
    findings: tuple[PipelineAuditFinding, ...]

    @property
    def has_blocker(self) -> bool:
        return any(
            item.severity is AuditSeverity.BLOCKER
            for item in self.findings
        )

    @property
    def has_unknown(self) -> bool:
        return any(
            item.severity is AuditSeverity.UNKNOWN
            for item in self.findings
        )


def _props(item) -> dict[str, str]:
    return dict(item.properties)


def audit_strict_pipeline(
    snapshot: PipelineRuntimeSnapshot,
    *,
    resampler_allowed_if_passthrough: bool,
    preserving_converter_evidence: bool | None,
) -> StrictPipelineAudit:
    findings: list[PipelineAuditFinding] = []

    sinks = snapshot.by_factory("alsasink")
    if len(sinks) != 1:
        findings.append(
            PipelineAuditFinding(
                "ALSA_SINK_COUNT",
                AuditSeverity.BLOCKER,
                f"Strict Direct expected exactly one alsasink, found {len(sinks)}.",
            )
        )

    volumes = snapshot.by_factory("volume")
    if volumes:
        findings.append(
            PipelineAuditFinding(
                "SOFTWARE_VOLUME_PRESENT",
                AuditSeverity.BLOCKER,
                "A GStreamer volume element is present in Strict Direct.",
            )
        )

    resamplers = snapshot.by_factory("audioresample")
    for item in resamplers:
        if not resampler_allowed_if_passthrough:
            findings.append(
                PipelineAuditFinding(
                    "RESAMPLER_PRESENT",
                    AuditSeverity.BLOCKER,
                    "audioresample is present although this Strict variant forbids it.",
                )
            )
        elif item.base_transform_passthrough is not True:
            findings.append(
                PipelineAuditFinding(
                    "RESAMPLER_NOT_PROVEN_PASSTHROUGH",
                    AuditSeverity.BLOCKER,
                    "audioresample is present but passthrough is not proven.",
                )
            )

    converters = snapshot.by_factory("audioconvert")
    for item in converters:
        props = _props(item)

        if props.get("dithering") not in {None, "none", "<enum GST_AUDIO_DITHER_NONE of type GstAudioDitherMethod>"}:
            findings.append(
                PipelineAuditFinding(
                    "DITHER_NOT_DISABLED",
                    AuditSeverity.BLOCKER,
                    f"audioconvert dithering is {props.get('dithering')!r}.",
                )
            )

        if props.get("noise-shaping") not in {None, "none", "<enum GST_AUDIO_NOISE_SHAPING_NONE of type GstAudioNoiseShapingMethod>"}:
            findings.append(
                PipelineAuditFinding(
                    "NOISE_SHAPING_NOT_DISABLED",
                    AuditSeverity.BLOCKER,
                    f"audioconvert noise-shaping is {props.get('noise-shaping')!r}.",
                )
            )

        if item.base_transform_passthrough is True:
            findings.append(
                PipelineAuditFinding(
                    "AUDIOCONVERT_PASSTHROUGH",
                    AuditSeverity.INFO,
                    "audioconvert reports BaseTransform passthrough.",
                )
            )
        elif preserving_converter_evidence is True:
            findings.append(
                PipelineAuditFinding(
                    "AUDIOCONVERT_PRESERVING_EVIDENCE",
                    AuditSeverity.INFO,
                    "audioconvert is not passthrough, but sample-preserving conversion evidence exists.",
                )
            )
        elif preserving_converter_evidence is False:
            findings.append(
                PipelineAuditFinding(
                    "AUDIOCONVERT_NON_PRESERVING",
                    AuditSeverity.BLOCKER,
                    "Observed conversion is known not to preserve significant samples.",
                )
            )
        else:
            findings.append(
                PipelineAuditFinding(
                    "AUDIOCONVERT_PRESERVATION_UNKNOWN",
                    AuditSeverity.UNKNOWN,
                    "audioconvert is not passthrough and preserving conversion has not been proven.",
                )
            )

    return StrictPipelineAudit(tuple(findings))
```

---

# 143. PIPELINE AUDIT TESTS

```python
from michi.application.strict_pipeline_audit import (
    AuditSeverity,
    audit_strict_pipeline,
)
from michi.domain.audio_pipeline_evidence import (
    ElementRuntimeSnapshot,
    PipelineRuntimeSnapshot,
    SinkClockSnapshot,
    TransformRole,
)


def element(factory, role, passthrough=None, props=()):
    return ElementRuntimeSnapshot(
        element_name=factory,
        factory_name=factory,
        role=role,
        base_transform_passthrough=passthrough,
        properties=props,
    )


def snapshot(*items):
    return PipelineRuntimeSnapshot(
        elements=tuple(items),
        sink_clock=None,
    )


def test_clean_resampler_free_strict_has_no_blocker():
    snap = snapshot(
        element(
            "audioconvert",
            TransformRole.FORMAT_CONVERTER,
            True,
            (
                ("dithering", "none"),
                ("noise-shaping", "none"),
            ),
        ),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=None,
    )
    assert not audit.has_blocker


def test_forbidden_resampler_is_blocker_even_if_passthrough():
    snap = snapshot(
        element(
            "audioresample",
            TransformRole.RESAMPLER,
            True,
        ),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=None,
    )
    assert audit.has_blocker


def test_allowed_resampler_requires_real_passthrough():
    snap = snapshot(
        element(
            "audioresample",
            TransformRole.RESAMPLER,
            False,
        ),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=True,
        preserving_converter_evidence=None,
    )
    assert audit.has_blocker


def test_non_passthrough_converter_is_unknown_until_r3():
    snap = snapshot(
        element(
            "audioconvert",
            TransformRole.FORMAT_CONVERTER,
            False,
            (
                ("dithering", "none"),
                ("noise-shaping", "none"),
            ),
        ),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=None,
    )
    assert not audit.has_blocker
    assert audit.has_unknown


def test_non_preserving_converter_is_blocker():
    snap = snapshot(
        element(
            "audioconvert",
            TransformRole.FORMAT_CONVERTER,
            False,
            (
                ("dithering", "none"),
                ("noise-shaping", "none"),
            ),
        ),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=False,
    )
    assert audit.has_blocker


def test_software_volume_is_blocker():
    snap = snapshot(
        element("volume", TransformRole.VOLUME),
        element("alsasink", TransformRole.SINK),
    )
    audit = audit_strict_pipeline(
        snap,
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=None,
    )
    assert audit.has_blocker


def test_missing_or_multiple_alsa_sink_is_blocker():
    audit = audit_strict_pipeline(
        snapshot(),
        resampler_allowed_if_passthrough=False,
        preserving_converter_evidence=None,
    )
    assert audit.has_blocker
```

---

# 144. CLOCK OBSERVATION SEAM

GStreamer exposes:

```text
AudioBaseSink.get_provide_clock()
AudioBaseSink.get_slave_method()
Pipeline.get_clock()
NEW_CLOCK
CLOCK_LOST
```

This is enough to build a truthful observation seam.

It is not enough to change clock policy automatically.

Current product rule:

```text
observe
do not force
```

Automatic clock-policy manipulation remains out of the current core. Minimal clock/slave-policy observation required to validate Direct happens now, pre-Stable; a full Clock Observatory may remain optional later.

---

# 145. IMPORTANT CLOCK DETAIL

`GstAudioBaseSink` supports slave methods:

```text
RESAMPLE
SKEW
NONE
CUSTOM
```

When its internal audio clock is not selected as pipeline master.

Current documentation reports `provide-clock=true` and a default `slave-method=skew`
for audio base sinks, but Michi must observe actual runtime properties rather than
treat defaults as evidence.

---

# 146. ALSA TIMING RESEARCH NOTE

ALSA exposes additional status/timing primitives including:

```text
snd_pcm_avail_delay()
snd_pcm_status_get_trigger_htstamp()
snd_pcm_status_get_htstamp()
snd_pcm_status_get_audio_htstamp()
snd_pcm_status_get_driver_htstamp()
```

These are potentially useful for a later timing laboratory.

Do not add a second PCM handle merely to collect them while GStreamer owns the device.

For Stable/R7:

```text
proc status
GStreamer events
monotonic application timestamps
```

are sufficient starting points.

Promote deeper ALSA timestamp integration only if a real timing question requires it.

---

# 147. DETERMINISTIC XRUN INJECTION

The Linux ALSA proc interface documents:

```text
card*/pcm*/sub*/xrun_injection
```

Writing a value triggers an XRUN on a running stream.

This gives R6 a deterministic falsification tool.

Developer-only implementation:

```python
from __future__ import annotations

from pathlib import Path


class XrunInjectionError(RuntimeError):
    pass


def validate_xrun_injection_path(path: Path) -> None:
    parts = path.parts

    if not path.is_absolute():
        raise XrunInjectionError("Path must be absolute.")

    if len(parts) < 6:
        raise XrunInjectionError("Path is too short.")

    if parts[:3] != ("/", "proc", "asound"):
        raise XrunInjectionError("Only /proc/asound is allowed.")

    if path.name != "xrun_injection":
        raise XrunInjectionError(
            "Target must be the ALSA xrun_injection proc file."
        )


def inject_xrun(path: Path) -> None:
    validate_xrun_injection_path(path)

    try:
        path.write_text("1\n", encoding="ascii")
    except OSError as exc:
        raise XrunInjectionError(
            f"XRUN injection failed: {exc}"
        ) from exc
```

Never expose this in product UI.

---

# 148. GStreamer LAB ARTIFACT PLAN

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GstLabArtifactPlan:
    capture_dot_graph: bool = True
    capture_latency_tracer: bool = False
    capture_element_latency: bool = False
    capture_reported_latency: bool = False

    def environment(self) -> dict[str, str]:
        env: dict[str, str] = {}

        flags = []
        if self.capture_latency_tracer:
            flags.append("pipeline")
        if self.capture_element_latency:
            flags.append("element")
        if self.capture_reported_latency:
            flags.append("reported")

        if flags:
            env["GST_TRACERS"] = (
                f"latency(flags={'+'.join(flags)})"
            )
            env["GST_DEBUG"] = "GST_TRACER:7"

        return env
```

Tracer activation remains opt-in per experiment.

---

# 149. ARTIFACT BUNDLE WRITER

Every physical/integration experiment should be replay-auditable.

```python
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import json
import os
import tempfile
from typing import Any


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _jsonable(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


class ArtifactBundleWriter:
    def __init__(self, root: Path) -> None:
        self.root = root

    def prepare(self) -> None:
        self.root.mkdir(parents=True, exist_ok=False)

    def write_json(
        self,
        relative_path: str,
        payload: Any,
    ) -> Path:
        path = self._resolve(relative_path)
        data = json.dumps(
            _jsonable(payload),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ) + "\n"
        self._atomic_write(path, data)
        return path

    def write_text(
        self,
        relative_path: str,
        text: str,
    ) -> Path:
        path = self._resolve(relative_path)
        self._atomic_write(path, text)
        return path

    def _resolve(self, relative_path: str) -> Path:
        rel = Path(relative_path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Artifact path must stay inside bundle.")
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            dir=path.parent,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise
```

The writer uses atomic replace so a crash does not leave a half-written `result.json`
masquerading as a completed run.

---

# 150. EXPERIMENT CONTRACT

Every new experiment should become machine-validatable.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExperimentLifecycle(Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    INCONCLUSIVE = "inconclusive"
    SURVIVES = "survives"
    FALSIFIED = "falsified"
    KILLED = "killed"


@dataclass(frozen=True)
class ExperimentContract:
    experiment_id: str
    question: str
    hypothesis: str
    prediction: str

    required_inputs: tuple[str, ...]
    capture: tuple[str, ...]

    pass_criteria: tuple[str, ...]
    falsifiers: tuple[str, ...]

    required_evidence_level: str
    kill_criterion: str
    safe_retreat: str

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []

        required_text = {
            "experiment_id": self.experiment_id,
            "question": self.question,
            "hypothesis": self.hypothesis,
            "prediction": self.prediction,
            "required_evidence_level": self.required_evidence_level,
            "kill_criterion": self.kill_criterion,
            "safe_retreat": self.safe_retreat,
        }

        for name, value in required_text.items():
            if not value.strip():
                errors.append(f"{name} must not be empty")

        if not self.capture:
            errors.append("capture must not be empty")
        if not self.pass_criteria:
            errors.append("pass_criteria must not be empty")
        if not self.falsifiers:
            errors.append("falsifiers must not be empty")

        return tuple(errors)
```

An experiment without:

```text
capture
pass criteria
falsifiers
```

is invalid.

---

# 151. EXPERIMENT RESULT EVALUATOR

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tools.michi_audio_lab.experiment_contract import (
    ExperimentContract,
    ExperimentLifecycle,
)


class CriterionState(Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CriterionResult:
    criterion: str
    state: CriterionState
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    achieved_evidence_level: str

    pass_results: tuple[CriterionResult, ...]
    falsifier_results: tuple[CriterionResult, ...]

    notes: tuple[str, ...] = ()


def evaluate_experiment(
    contract: ExperimentContract,
    result: ExperimentResult,
) -> ExperimentLifecycle:
    if contract.validate():
        raise ValueError("Invalid experiment contract.")

    if contract.experiment_id != result.experiment_id:
        raise ValueError("Experiment ID mismatch.")

    if any(
        item.state is CriterionState.PASS
        for item in result.falsifier_results
    ):
        return ExperimentLifecycle.FALSIFIED

    if any(
        item.state is CriterionState.UNKNOWN
        for item in result.pass_results
    ):
        return ExperimentLifecycle.INCONCLUSIVE

    if any(
        item.state is CriterionState.FAIL
        for item in result.pass_results
    ):
        return ExperimentLifecycle.INCONCLUSIVE

    if all(
        item.state is CriterionState.PASS
        for item in result.pass_results
    ):
        return ExperimentLifecycle.SURVIVES

    return ExperimentLifecycle.INCONCLUSIVE
```

Critical rule:

```text
observed falsifier
→ FALSIFIED
```

even if all happy-path checks also passed.

This prevents cherry-picking successful evidence.

---

# 152. NEW EXPERIMENT R8 — PIPELINE RUNTIME AUDIT

```yaml
schema_version: 1
experiment_id: R8_PIPELINE_RUNTIME_AUDIT
status: required-before-strict-pipeline-freeze

question: >
  Can Michi observe the real Strict Direct output branch well enough to prove
  which signal-affecting elements exist and whether GstBaseTransform elements
  are actually in passthrough?

mayeutic:
  hidden_assumptions:
    - matching caps imply no transformation
    - the pipeline contains only the elements we intended to create
    - audioresample/audioconvert state can be inferred from names alone

technical_analysis:
  upstream_apis:
    - Gst.Bin.iterate_recurse
    - Gst.Bin.iterate_all_by_element_factory_name
    - GstBase.BaseTransform.is_passthrough
    - Gst.debug_bin_to_dot_data
    - GObject property inspection
  capture:
    - recursive_element_factories
    - base_transform_passthrough
    - audioconvert_properties
    - alsasink_properties
    - current_caps
    - pipeline_dot_graph

variants:
  - strict_with_audioresample
  - strict_without_audioresample

pass:
  - exactly_one_alsasink
  - no_software_volume_element
  - forbidden_resampler_absent
  - allowed_resampler_is_passthrough
  - no_unexplained_signal_transform
  - dot_graph_matches_runtime_inventory

falsifiers:
  - hidden_signal_affecting_element
  - audioresample_not_passthrough_when_required
  - pipeline_inventory_and_dot_graph_contradict
  - observer_changes_pipeline_behavior_materially

implementation_result:
  promote_if: all required cases survive
  safe_retreat: keep verdict UNKNOWN and retain inspector as lab-only
```

R8 must run before freezing Strict pipeline semantics.

---

# 153. NEW EXPERIMENT R9 — OBSERVER EFFECT BUDGET

```yaml
schema_version: 1
experiment_id: R9_OBSERVER_EFFECT_BUDGET
status: required-before-always-on-runtime-evidence

question: >
  Do Michi's runtime observers change the behavior they are intended to
  measure?

mayeutic:
  hidden_assumptions:
    - reading current caps is free
    - procfs sampling is free
    - recursive pipeline inspection is free
    - dot/tracer capture is free

technical_analysis:
  variants:
    - instrumentation_off
    - current_caps_plus_proc
    - pipeline_inventory_snapshot
    - dot_snapshot
    - latency_tracer

measure:
  - xrun_count
  - playback_failure_count
  - time_to_first_audio
  - rate_transition_duration
  - cpu_time
  - max_callback_duration
  - observer_failures

pass:
  - no_material_xrun_regression
  - no_material_failure_regression
  - no_blocking_work_in_streaming_thread
  - snapshot_observers_complete_outside_realtime_path

falsifiers:
  - instrumentation_causes_reproducible_xrun
  - instrumentation_increases_transition_failure_rate
  - pad_probe_or_tracer_blocks_streaming_thread

implementation_result:
  if_light_observers_survive: allow current_caps/proc observer
  if_heavy_observers_fail: keep dot/tracer lab-only
  safe_retreat: evidence UNKNOWN without affecting playback
```

Expected likely product result:

```text
lightweight snapshots
→ potentially always-on

dot graphs/tracers
→ likely Lab-on-demand
```

But R9 decides.

---

# 154. NEW EXPERIMENT R10 — CLOCK POLICY OBSERVATION

```yaml
schema_version: 1
experiment_id: R10_CLOCK_POLICY_OBSERVATION
status: historical_deep_clock_research__minimum_pre_stable_observation_promoted_to_section_33

question: >
  What clock does the real Michi GStreamer pipeline select, and what
  GstAudioBaseSink slave policy is actually configured?

mayeutic:
  hidden_assumptions:
    - the ALSA sink is always the pipeline clock master
    - matching sample rates prove temporal continuity
    - default slave policy is harmless for Strict claims

technical_analysis:
  upstream_apis:
    - GstAudio.AudioBaseSink.get_provide_clock
    - GstAudio.AudioBaseSink.get_slave_method
    - Gst.Pipeline.get_clock
    - Gst.MessageType.NEW_CLOCK
    - Gst.MessageType.CLOCK_LOST
    - GStreamer latency tracer
  capture:
    - provide_clock
    - slave_method
    - selected_pipeline_clock_name
    - new_clock_events
    - clock_lost_events
    - reported_pipeline_latency

matrix:
  rates: [44100, 48000, 96000, 192000]
  operations:
    - first_play
    - pause_resume
    - same_rate_transition
    - rate_change
    - reconnect

falsifiers:
  - selected_clock_differs_from_expected_reproducibly
  - clock_lost_event_does_not_invalidate_temporal_claim
  - resample_slave_method_active_under_strict_temporal_claim

implementation_result:
  do_not_change_clock_policy_in_this_experiment: true
  safe_retreat: keep temporal dimensions UNKNOWN
```

The **full R10 deep clock experiment is optional later work**. Its minimum observation requirement has already been promoted into the current pre-Stable path by §33/R24.

Its purpose is discovery, not tuning.

---

# 155. UPDATED RESEARCH ORDER

The order becomes:

```text
R1  Runtime Witness
↓
R8  Pipeline Runtime Audit
↓
R3  Sample Preservation
↓
R2  Resampler A/B
↓
R9  Observer Effect Budget
↓
R4  Probe vs Session
↓
R5  Identity Chaos
↓
R6  Failure Semantics
↓
R7  Transition Lab
↓
R10 Deep Clock Policy Observation (optional later; minimum observation is pre-Stable per §33/R24)
```

Reason:

```text
R1 tells us hardware PCM state.
R8 tells us actual GStreamer topology and passthrough.
R3 tells us sample preservation.
Only then can R2 choose the Strict topology rationally.
```

---

# 156. FILE-BY-FILE OPENCODE IMPLEMENTATION ORDER

OpenCode must follow this order for the research layer:

```text
1. audio_runtime_evidence.py
2. proc_pcm_witness.py
3. runtime_evidence.py
4. audio_pipeline_evidence.py
5. pipeline_inspector.py
6. pygobject_probe_reference.py → integrate on real Linux
7. pcm_evidence_recorder.py
8. engineering_method.py
9. implementation_promotion_gate.py
10. experiment_contract.py
11. experiment_result.py
12. artifact_bundle.py
13. strict_pipeline_audit.py
14. sample_normalizer.py
15. xrun_injector.py
16. run R1
17. run R8
18. run R3
19. run R2
```

Do not start at item 13 because it looks like the product result.

The observer/instrumentation must exist first.

---

# 157. OPENCODE IMPLEMENTATION REPORT FORMAT

Every research PR must end with:

```text
MAYEUTIC QUESTION
<exact question>

TECHNICAL FACT LEDGER
UPSTREAM_DOCUMENTED:
...

LOCALLY_OBSERVED:
...

DEDUCED:
...

HYPOTHESIS:
...

UNKNOWN:
...

FALSIFICATION
experiment:
falsifiers:
observed:

RESULT
PROMOTE / PROMOTE_WITH_LIMITS / REJECT / INCONCLUSIVE

EVIDENCE LEVEL
...

FILES CHANGED
...

PRODUCT BEHAVIOR CHANGED?
YES / NO

UNRESOLVED UNKNOWN
...
```

If the report omits `UNKNOWN`, the PR is incomplete.

---

# 158. OPENCODE NO-SPECULATION STOP CONDITIONS

Stop and report instead of improvising if:

```text
PyGObject wrapper behavior differs from the reference blueprint.
The actual pipeline contains an unexpected transform.
A property expected by the plan is absent.
is_passthrough() cannot be queried reliably.
The proc PCM binding cannot be correlated safely.
GStreamer and proc witness contradict.
A failure produces a new errno/event combination.
A physical DAC resets or disappears during qualification.
An experiment produces both supporting and contradictory evidence.
```

These are research discoveries.

Not implementation annoyances.

---

# 159. GStreamer SOURCE-DERIVED FACTS NOW SAFE TO USE

The following can be treated as `UPSTREAM_DOCUMENTED`:

```text
GstBaseTransform has is_passthrough().
GstBin can iterate recursively through elements.
GstBin can find elements recursively by factory name.
GStreamer can export DOT pipeline graphs including negotiated caps/details.
The latency tracer can report pipeline/element/reported latency.
Pad data probes execute in streaming-thread context and must not block.
AudioBaseSink exposes provide-clock and slave-method observation.
audioconvert can dither, noise-shape and reorder/mix channels.
input-channels-reorder-mode is available since GStreamer 1.26.
```

They do not prove any specific Michi session behavior.

---

# 160. EXTERNAL ENGINEERING LESSON — FORMAT TRANSITIONS

DeaDBeeF documents that it changed its ALSA output to fully reinitialize the device
when the output format changes for compatibility with more DACs.

This is not proof Michi must always do the same.

It is evidence that:

```text
format transition behavior is hardware-sensitive
```

Therefore R7 remains mandatory before trying clever partial reconfiguration.

---

# 161. EXTERNAL ENGINEERING LESSON — IDENTITY

Strawberry changed ALSA device handling to use card ID instead of card index.

This supports the already canonical rule:

```text
numeric card index
≠ persistent identity
```

It does not prove card ID is globally unique.

R5 still decides Michi's real identity-confidence policy.

---

# 162. CURRENT REFERENCE PACK STATUS

The V2 reference pack now contains:

```text
47 source/test/support files
58 passing tests
```

Evidence level:

```text
DOMAIN_REFERENCE_TESTED
```

The PyGObject probe remains:

```text
LINUX_INTEGRATION_PENDING
```

because the plan-generation runtime does not have `gi.repository`.

This distinction is intentional.

---

# 163. V2 TEST ADDITIONS — ENGINEERING METHOD

```python
from michi.domain.engineering_method import (
    EngineeringFact,
    EngineeringFactKind,
    EngineeringInquiry,
    ImplementationDisposition,
    ImplementationResult,
    MayeuticRecord,
    TechnicalAnalysisRecord,
    FalsificationRecord,
    can_promote_implementation,
    critical_speculation_blockers,
)


def make_inquiry(facts, result):
    return EngineeringInquiry(
        inquiry_id="I-1",
        mayeutic=MayeuticRecord(
            question="Do we need a resampler?",
            hidden_assumptions=("Transitions require one.",),
            desired_user_outcome="Exact native playback.",
        ),
        technical=TechnicalAnalysisRecord(
            owning_layer="gstreamer output executor",
            upstream_apis=("GstBaseTransform.is_passthrough",),
            candidate_files=("direct_pipeline_spec.py",),
            facts=tuple(facts),
            failure_modes=("rate transition fails",),
            unknowns=(),
        ),
        falsification=FalsificationRecord(
            hypothesis="Strict can omit audioresample.",
            prediction="All required transitions still work.",
            experiment_id="R2",
            falsifiers=("reproducible transition regression",),
            kill_criterion="Any reproducible required-case regression.",
            safe_retreat="Keep resampler and prove passthrough.",
        ),
        result=result,
    )


def test_critical_unknown_blocks_promotion():
    fact = EngineeringFact(
        fact_id="F1",
        statement="Unknown behavior.",
        kind=EngineeringFactKind.UNKNOWN,
        critical=True,
    )
    result = ImplementationResult(
        disposition=ImplementationDisposition.PROMOTE,
        summary="Promote.",
        implementation_files=("x.py",),
        evidence_level="linux_integration_tested",
        constraints=(),
    )
    inquiry = make_inquiry((fact,), result)
    assert critical_speculation_blockers(inquiry.technical.facts) == (fact,)
    assert not can_promote_implementation(inquiry)


def test_documented_and_observed_facts_can_promote():
    facts = (
        EngineeringFact(
            "F1",
            "API exists.",
            EngineeringFactKind.UPSTREAM_DOCUMENTED,
            True,
            ("official-doc",),
        ),
        EngineeringFact(
            "F2",
            "Experiment passed.",
            EngineeringFactKind.LOCALLY_OBSERVED,
            True,
            ("run-1",),
        ),
    )
    result = ImplementationResult(
        disposition=ImplementationDisposition.PROMOTE_WITH_LIMITS,
        summary="Promote only for tested matrix.",
        implementation_files=("x.py",),
        evidence_level="physical_hardware_tested",
        constraints=("tested rates only",),
    )
    assert can_promote_implementation(make_inquiry(facts, result))


def test_unresolved_result_unknown_blocks_promotion():
    facts = (
        EngineeringFact(
            "F1",
            "API exists.",
            EngineeringFactKind.UPSTREAM_DOCUMENTED,
            True,
        ),
    )
    result = ImplementationResult(
        disposition=ImplementationDisposition.PROMOTE,
        summary="Promote.",
        implementation_files=("x.py",),
        evidence_level="physical_hardware_tested",
        constraints=(),
        unresolved_unknowns=("second DAC not tested",),
    )
    assert not can_promote_implementation(make_inquiry(facts, result))
```

---

# 164. V2 TEST ADDITIONS — PROMOTION GATE

```python
from michi.application.implementation_promotion_gate import (
    EvidenceLevel,
    promotion_gate,
)
from michi.domain.engineering_method import (
    EngineeringFact,
    EngineeringFactKind,
    EngineeringInquiry,
    FalsificationRecord,
    ImplementationDisposition,
    ImplementationResult,
    MayeuticRecord,
    TechnicalAnalysisRecord,
)


def inquiry():
    return EngineeringInquiry(
        inquiry_id="I",
        mayeutic=MayeuticRecord("Q", (), "Outcome"),
        technical=TechnicalAnalysisRecord(
            owning_layer="layer",
            upstream_apis=("api",),
            candidate_files=("x.py",),
            facts=(
                EngineeringFact(
                    "F",
                    "Observed.",
                    EngineeringFactKind.LOCALLY_OBSERVED,
                    True,
                    ("run",),
                ),
            ),
            failure_modes=(),
            unknowns=(),
        ),
        falsification=FalsificationRecord(
            "H", "P", "R", ("X",), "K", "Retreat"
        ),
        result=ImplementationResult(
            ImplementationDisposition.PROMOTE,
            "Promote",
            ("x.py",),
            "physical_hardware_tested",
            (),
        ),
    )


def test_evidence_below_required_blocks():
    decision = promotion_gate(
        inquiry(),
        achieved_evidence=EvidenceLevel.DOMAIN_REFERENCE_TESTED,
        required_evidence=EvidenceLevel.PHYSICAL_HARDWARE_TESTED,
        falsifier_observed=False,
    )
    assert not decision.allowed


def test_observed_falsifier_blocks_even_with_high_evidence():
    decision = promotion_gate(
        inquiry(),
        achieved_evidence=EvidenceLevel.MULTI_HARDWARE_TESTED,
        required_evidence=EvidenceLevel.PHYSICAL_HARDWARE_TESTED,
        falsifier_observed=True,
    )
    assert not decision.allowed


def test_matching_evidence_allows():
    decision = promotion_gate(
        inquiry(),
        achieved_evidence=EvidenceLevel.PHYSICAL_HARDWARE_TESTED,
        required_evidence=EvidenceLevel.PHYSICAL_HARDWARE_TESTED,
        falsifier_observed=False,
    )
    assert decision.allowed
```

---

# 165. V2 TEST ADDITIONS — PIPELINE INSPECTOR

```python
from michi.domain.audio_pipeline_evidence import (
    SinkClockSnapshot,
    TransformRole,
)
from michi.infrastructure.audio_engines.gstreamer.pipeline_inspector import (
    ElementObservation,
    PipelineInspector,
    signal_transform_summary,
)


class FakeProbe:
    def enumerate_elements(self):
        return (
            ElementObservation(
                "convert",
                "audioconvert",
                True,
                True,
                (("dithering", "none"),),
            ),
            ElementObservation(
                "resample",
                "audioresample",
                True,
                True,
                (),
            ),
            ElementObservation(
                "sink",
                "alsasink",
                False,
                None,
                (("device", "hw:CARD=X,DEV=0"),),
            ),
        )

    def sink_clock_snapshot(self):
        return SinkClockSnapshot(
            provide_clock=True,
            slave_method="skew",
            selected_pipeline_clock_name="GstAudioClock",
            clock_lost_events=0,
        )

    def dot_graph(self):
        return "digraph pipeline {}"


def test_pipeline_inspector_preserves_factory_and_passthrough():
    snap = PipelineInspector(FakeProbe()).snapshot()
    assert snap.factories() == (
        "audioconvert",
        "audioresample",
        "alsasink",
    )
    assert snap.elements[0].role is TransformRole.FORMAT_CONVERTER
    assert snap.elements[0].base_transform_passthrough is True


def test_transform_summary_reports_passthrough():
    snap = PipelineInspector(FakeProbe()).snapshot()
    summary = signal_transform_summary(snap)
    assert summary["audioresample_count"] == 1
    assert summary["audioresample_all_passthrough"] is True
    assert summary["audioconvert_all_passthrough"] is True


def test_absent_resampler_is_structurally_clean():
    class NoResamplerProbe(FakeProbe):
        def enumerate_elements(self):
            return tuple(
                item
                for item in super().enumerate_elements()
                if item.factory_name != "audioresample"
            )

    snap = PipelineInspector(NoResamplerProbe()).snapshot()
    summary = signal_transform_summary(snap)
    assert summary["audioresample_count"] == 0
    assert summary["audioresample_all_passthrough"] is True
```

---

# 166. V2 TEST ADDITIONS — EXPERIMENT CONTRACT

```python
from dataclasses import replace
from tools.michi_audio_lab.experiment_contract import ExperimentContract


def valid():
    return ExperimentContract(
        experiment_id="R1",
        question="What happened?",
        hypothesis="A equals B.",
        prediction="They match.",
        required_inputs=("track",),
        capture=("a", "b"),
        pass_criteria=("equal",),
        falsifiers=("different",),
        required_evidence_level="linux_integration_tested",
        kill_criterion="different",
        safe_retreat="unknown",
    )


def test_valid_contract_has_no_errors():
    assert valid().validate() == ()


def test_empty_capture_is_invalid():
    c = replace(valid(), capture=())
    assert "capture must not be empty" in c.validate()
```

---

# 167. V2 TEST ADDITIONS — EXPERIMENT RESULT

```python
from tools.michi_audio_lab.experiment_contract import (
    ExperimentContract,
    ExperimentLifecycle,
)
from tools.michi_audio_lab.experiment_result import (
    CriterionResult,
    CriterionState,
    ExperimentResult,
    evaluate_experiment,
)


def contract():
    return ExperimentContract(
        "R",
        "Q",
        "H",
        "P",
        ("input",),
        ("capture",),
        ("pass-a",),
        ("falsifier-a",),
        "physical_hardware_tested",
        "kill",
        "retreat",
    )


def test_falsifier_wins():
    result = ExperimentResult(
        "R",
        "physical_hardware_tested",
        pass_results=(
            CriterionResult("pass-a", CriterionState.PASS),
        ),
        falsifier_results=(
            CriterionResult("falsifier-a", CriterionState.PASS),
        ),
    )
    assert evaluate_experiment(contract(), result) is ExperimentLifecycle.FALSIFIED


def test_unknown_pass_criterion_is_inconclusive():
    result = ExperimentResult(
        "R",
        "physical_hardware_tested",
        pass_results=(
            CriterionResult("pass-a", CriterionState.UNKNOWN),
        ),
        falsifier_results=(
            CriterionResult("falsifier-a", CriterionState.FAIL),
        ),
    )
    assert evaluate_experiment(contract(), result) is ExperimentLifecycle.INCONCLUSIVE


def test_all_pass_and_no_falsifier_survives():
    result = ExperimentResult(
        "R",
        "physical_hardware_tested",
        pass_results=(
            CriterionResult("pass-a", CriterionState.PASS),
        ),
        falsifier_results=(
            CriterionResult("falsifier-a", CriterionState.FAIL),
        ),
    )
    assert evaluate_experiment(contract(), result) is ExperimentLifecycle.SURVIVES
```

---

# 168. V2 TEST ADDITIONS — ARTIFACT BUNDLE

```python
import pytest

from tools.michi_audio_lab.artifact_bundle import ArtifactBundleWriter


def test_bundle_writes_json_atomically(tmp_path):
    root = tmp_path / "run"
    writer = ArtifactBundleWriter(root)
    writer.prepare()
    path = writer.write_json("result.json", {"ok": True})
    assert path.read_text(encoding="utf-8").startswith('{')


def test_bundle_rejects_parent_escape(tmp_path):
    root = tmp_path / "run"
    writer = ArtifactBundleWriter(root)
    writer.prepare()
    with pytest.raises(ValueError):
        writer.write_text("../escape.txt", "bad")
```

---

# 169. V2 TEST ADDITIONS — XRUN PATH SAFETY

```python
from pathlib import Path
import pytest

from tools.michi_audio_lab.xrun_injector import (
    XrunInjectionError,
    validate_xrun_injection_path,
)


def test_valid_proc_xrun_path():
    validate_xrun_injection_path(
        Path("/proc/asound/card0/pcm0p/sub0/xrun_injection")
    )


def test_non_proc_path_rejected():
    with pytest.raises(XrunInjectionError):
        validate_xrun_injection_path(
            Path("/tmp/xrun_injection")
        )


def test_wrong_proc_file_rejected():
    with pytest.raises(XrunInjectionError):
        validate_xrun_injection_path(
            Path("/proc/asound/card0/pcm0p/sub0/status")
        )
```

---

# 170. V2 TEST ADDITIONS — GStreamer ARTIFACT PLAN

```python
from tools.michi_audio_lab.gstreamer_artifact_plan import GstLabArtifactPlan


def test_no_tracer_by_default():
    assert GstLabArtifactPlan().environment() == {}


def test_latency_flags_are_explicit():
    env = GstLabArtifactPlan(
        capture_latency_tracer=True,
        capture_element_latency=True,
    ).environment()
    assert env["GST_TRACERS"] == "latency(flags=pipeline+element)"
    assert env["GST_DEBUG"] == "GST_TRACER:7"
```

---

# 171. FINAL ENGINEERING LOOP

The new permanent loop is:

```text
MAYÉUTICA
"What assumption are we hiding?"
          ↓
ANÁLISIS TÉCNICO
"What do upstream APIs and current Michi ownership actually permit us to know?"
          ↓
FACT LEDGER
documented / observed / deduced / hypothesis / unknown
          ↓
FALSACIONISMO
"What observation would make this solution wrong?"
          ↓
EXPERIMENT
          ↓
PROMOTION GATE
          ↓
RESULTADO DE IMPLEMENTACIÓN

PROMOTE
or
PROMOTE_WITH_LIMITS
or
REJECT
or
INCONCLUSIVE
```

An `INCONCLUSIVE` result is superior to invented certainty.

---

# 172. FINAL RULE FOR PIONEER DAC ENGINEERING

Michi should be pioneering because it can:

```text
observe more carefully
explain more precisely
test more aggressively
fail more honestly
```

Not because it has the largest number of speculative services.

**END OF ENGINEERING METHOD V2**


# PART IV — KERNEL / DRIVER EVIDENCE & USB HOST INTEGRATION BLUEPRINT

**Status:** CANONICAL RESEARCH/IMPLEMENTATION EXTENSION  
**Stable authority impact:** only the explicitly promoted corrections below change Stable semantics  
**Reference implementation status:** `DOMAIN_REFERENCE_TESTED` — 75 tests passed  
**Physical/kernel behavior status:** requires the evidence levels declared by each experiment

---

# 173. WHY THE KERNEL/DRIVER LAYER MUST BE MODELED

V2 correctly stopped Signal Proof at:

```text
Michi → Linux hardware PCM boundary
```

But failures below that boundary can still explain why a valid user-space plan does not behave as expected:

```text
GStreamer
    ↓
ALSA-lib
    ↓
ALSA PCM kernel core
    ↓
snd-usb-audio
    ↓
USB endpoint / feedback scheduling
    ↓
USB host-controller driver
    ↓
physical USB device
```

The V3 rule is:

```text
Do not give these lower layers product authority.
Do collect enough evidence to stop blaming the wrong layer.
```

---

# 174. CONTRAST WITH V2 — GAPS CLOSED BY V3

V2 already had direct research links for `sound/usb/format.c` and `clock.c`, but lacked a complete implementation model for:

```text
snd-usb-audio module parameters and quirk flags
implicit-feedback mode
USB power/autosuspend context
USB host-controller/topology context
layer-specific errno semantics
snd-usb-audio decoded /proc stream witness
cached descriptor fingerprinting
rate readback vs momentary-feedback evidence
controlled UAC2 gadget host-stack testing
dynamic-debug escalation
usbmon escalation
```

V3 fills those gaps without making any of them playback authority.

---

# 175. SOURCE AUTHORITY LADDER FOR KERNEL/DRIVER RESEARCH

Use this order:

```text
1. Current Linux kernel documentation
2. Current Linux kernel source
3. ALSA / GStreamer / PipeWire upstream documentation/source
4. Reproducible local observation
5. Mature project implementation history
6. Maintainer/developer issue discussion
7. Community/forum anecdote
```

Forum/Reddit reports may create a hypothesis.

They may never create a Stable default by themselves.

---

# 176. KERNEL/DRIVER FACT LEDGER

## UPSTREAM_DOCUMENTED

```text
snd-usb-audio has autoclock, lowlatency, implicit_fb, quirk_flags and other parameters.
quirk_flags supports per-device named workarounds.
quirk_flags/quirk_alias are documented as testing/development mechanisms; proper known fixes belong upstream.
lowlatency can be disabled when it causes a regression.
implicit_fb activates generic implicit-feedback sync handling.
USB runtime PM is observable through sysfs power attributes.
USB host-controller/fault behavior can differ across HCDs.
usbmon observes requests between USB drivers and HCDs.
Linux configfs UAC2 gadget can expose a controlled UAC2 USB Audio peripheral.
```

## LOCALLY OBSERVABLE BUT NOT YET GENERALIZED

```text
/proc/asound/<card>/streamN decoded driver view
module parameter values
USB speed / sysfs topology
cached descriptors SHA-256
runtime power state
current host controller path
kernel log failure signatures
```

## HYPOTHESES

```text
a given crackle is caused by lowlatency mode
a given DAC needs implicit feedback forced
a given silent-resume bug is autosuspend
a bigger ALSA buffer fixes a USB scheduling problem
a rate readback mismatch means actual resampling
```

All five require falsification.

---

# 177. KDR-001 — `snd-usb-audio` PARAMETERS AND QUIRKS

## MAYÉUTICA

```text
Should Michi automatically apply kernel/module tweaks to make difficult DACs work?
```

Hidden premise:

```text
one parameter has one independent and universally beneficial effect
```

## TECHNICAL ANALYSIS

Current `snd-usb-audio` documentation exposes controls including:

```text
nrpacks
autoclock
lowlatency
implicit_fb
use_vmalloc
delayed_register
skip_validation
quirk_flags
```

Current quirk flags include workarounds for:

```text
sample-rate reads/validation
clock selectors/sources
control-message delays
interface delays
runtime autosuspend
implicit feedback force/skip
fixed rate
interface setup/reset
feedback silence handling
stuttering / playback URB scheduling
```

Some flags alter device-control sequencing and USB transfer behavior deeply.

Therefore they are not ordinary player preferences.

## FALSIFICATION

Any proposed workaround must run only after reproducing one concrete failure and must compare controlled variants.

Example:

```text
baseline
vs lowlatency=0
vs implicit_fb forced
vs lowlatency × implicit_fb interaction
```

## IMPLEMENTATION RESULT

```text
PROMOTE:
read-only parameter snapshot + artifact provenance

REJECT FOR STABLE:
automatic kernel/module parameter mutation

CONDITIONAL LAB:
R15 Driver Parameter Hypothesis
```

If a device repeatedly needs a kernel quirk:

```text
prepare an upstream-quality kernel report
```

rather than shipping a hidden permanent Michi tweak.

---

# 178. KDR-002 — USB POWER / AUTOSUSPEND

## MAYÉUTICA

```text
When a DAC disappears, wakes slowly, or goes silent after idle/resume, is USB autosuspend responsible?
```

## TECHNICAL ANALYSIS

USB runtime-PM state is visible through sysfs, including conceptually:

```text
power/control
power/runtime_status
power/autosuspend_delay_ms
power/wakeup
power/persist
power/active_duration
power/connected_duration
```

`power/control=on` prevents runtime autosuspend; `auto` permits it.

The USB subsystem documentation explicitly warns that some devices resume badly.

`snd-usb-audio` also has a device quirk that disables runtime autosuspend.

## FALSIFICATION

Do not begin by writing `power/control=on`.

First run R12 passively.

If failures occur without a corresponding PM transition:

```text
autosuspend hypothesis weakened/falsified
```

Only after a reproducible correlation may the Lab run an explicit A/B mutation.

## RESULT

```text
PROMOTE:
passive power evidence

REJECT:
global or automatic Stable power mutation
```

---

# 179. KDR-003 — FAILURE SEMANTICS ARE LAYER-SPECIFIC

This is a **canonical V3 correction**.

## MAYÉUTICA

```text
Does an errno number have one audio meaning everywhere?
```

No.

## TECHNICAL ANALYSIS

At ALSA PCM user-space API level:

```text
-EPIPE      → XRUN semantics
-ESTRPIPE   → suspended stream/system driver
```

At Linux USB URB level:

```text
-EPIPE        → endpoint stalled
-ENOSPC       → insufficient periodic USB bandwidth
-ESHUTDOWN    → device/controller path disabled/disconnected
-EHOSTUNREACH → suspended/unreachable USB device
-ENODEV       → device gone
```

Therefore:

```text
EPIPE without FailureLayer
→ ambiguous
```

## RESULT

```text
PROMOTE
```

The old V2 unscoped classifier is removed from the canonical file and reference pack.

---

# 180. KDR-004 — `snd-usb-audio` DRIVER-DECODED STREAM WITNESS

## MAYÉUTICA

```text
Must Michi parse raw UAC descriptors itself to understand endpoints, altsettings and feedback?
```

Not yet.

## TECHNICAL ANALYSIS

On many `snd-usb-audio` devices:

```text
/proc/asound/<card>/streamN
```

can expose driver-decoded information such as:

```text
active interface
active altsetting
packet size
momentary frequency
feedback format
PCM format
channels
endpoint
sync mode
advertised rates
packet interval
significant bits
channel map
sync endpoint
implicit-feedback mode
```

This is especially valuable because Linux has already interpreted the USB Audio descriptors and quirks.

## FALSIFICATION

R17 compares this witness against:

```text
michi-alsa-probe
/proc PCM hw_params
GStreamer current caps
```

If the parser proves too unstable across kernels/devices:

```text
keep it Lab-only
```

## RESULT

```text
PROMOTE_WITH_LIMITS:
Lab/diagnostic observer

DO NOT:
make playback depend on /proc stream text
```

This further delays the need for `michi-uac-inspect`.

---

# 181. KDR-005 — CACHED USB DESCRIPTOR FINGERPRINT

Sysfs can expose the cached binary USB descriptor set.

V3 uses only:

```text
SHA-256
byte length
provenance
```

for context/revision correlation.

It does not parse UAC topology in Stable.

```text
same logical device
+ descriptor fingerprint changed
→ prior capability evidence may be STALE
```

This is passive and requires no new USB control request.

---

# 182. KDR-006 — USB SPEED AND HOST-CONTROLLER CONTEXT

USB speed and topology are not identity.

They are execution context.

Examples:

```text
12 Mbps Full Speed
480 Mbps High Speed
5 Gbps SuperSpeed transport context
xHCI controller A
xHCI controller B
hub vs direct port
```

Kernel documentation warns that HCD implementations can differ in fault/recovery behavior.

Therefore every physical failure artifact should preserve controller/topology context.

---

# 183. KDR-007 — IMPLICIT FEEDBACK

## MAYÉUTICA

```text
Should Michi force implicit_fb because forums report it fixes crackling?
```

No.

## TECHNICAL ANALYSIS

The current driver has extensive generic and device-specific implicit-feedback logic.

Current documentation defines `implicit_fb` as forcing generic implicit-feedback synchronization when an async playback stream can use an adjacent async capture stream.

Kernel playback code also treats implicit-feedback sinks specially; the normal low-latency playback path is not simply an independent knob in that configuration.

## FALSIFICATION

Community reports are input to R15 only.

The experiment must separate:

```text
lowlatency
implicit_fb
lowlatency × implicit_fb interaction
```

## RESULT

```text
REJECT:
global implicit_fb Stable default

PROMOTE:
observe driver witness / parameter state
```

---

# 184. KDR-008 — URB SCHEDULING CAN DOMINATE STUTTER

Current `snd-usb-audio` includes a `playback_urb_fixup` quirk specifically for some stuttering devices; it changes URB depth/scheduling.

This is important epistemically:

```text
user-space buffer symptom
≠ proof user-space buffer is root cause
```

Therefore a crackle report must preserve:

```text
kernel release
quirk state
USB controller
runtime driver witness
ALSA/GStreamer state
```

before Michi recommends buffer changes.

---

# 185. KDR-009 — RATE EVIDENCE MUST HAVE PROVENANCE

USB Audio devices can fail rate readback or report a current rate that differs from the runtime rate while the kernel continues operation.

Therefore V3 distinguishes:

```text
SOURCE
REQUESTED
GSTREAMER_NEGOTIATED
ALSA_HW_PARAMS
DRIVER_MOMENTARY_FEEDBACK
DEVICE_CONTROL_READBACK
```

A device-control readback mismatch does not automatically mean:

```text
resampling
```

And a small momentary-feedback deviation around nominal rate is clock behavior, not semantic sample-rate conversion.

---

# 186. KDR-010 — UCM AS USER-SPACE TOPOLOGY EVIDENCE

ALSA UCM can define useful Direct and SplitPCM profiles, channel positions and device-specific topology.

But UCM configuration can itself contain errors or assumptions.

Therefore:

```text
UCM
= user-space topology evidence
≠ physical hardware truth
```

Stable Direct does not require UCM.

An optional advanced Inspector may use it with explicit provenance; this is not required for the current M11.4 core and is not a reason to defer that core.

---

# 187. KDR-011 — PIPEWIRE MANAGED MODE LESSONS

PipeWire exposes ALSA-node properties such as:

```text
api.alsa.period-size
api.alsa.period-num
api.alsa.headroom
api.alsa.start-delay
api.alsa.disable-mmap
api.alsa.disable-batch
api.alsa.use-chmap
api.alsa.multi-rate
api.alsa.htimestamp
```

Several exist precisely because drivers differ or report imperfect timing/channel information.

Result:

```text
Direct remains separate from Managed.
```

When Managed work resumes, capture these properties as provenance.

Do not mutate global PipeWire configuration from Stable Direct.

---

# 188. KDR-012 — MICHI USB DAC EMULATOR WITH LINUX UAC2 GADGET

This is the largest new laboratory capability from V3.

## MAYÉUTICA

```text
Can we test more than local ALSA loopback without needing a commercial DAC for every CI-like experiment?
```

Yes, on a second Linux device with USB Device Controller support.

## TECHNICAL ANALYSIS

Linux configfs UAC2 gadget can expose a real USB Audio Class 2 peripheral with configurable:

```text
playback/capture channel masks
sample-rate lists
sample sizes
sync type
USB interval
feedback bandwidth
mute/volume controls
request count
interface/terminal/clock names
```

The Michi host sees an actual USB Audio peripheral through:

```text
USB HCD
→ USB core
→ snd-usb-audio
→ ALSA
→ GStreamer
```

while the gadget side receives/provides the stream through a virtual ALSA card.

## EVIDENCE LEVEL

New:

```text
USB_GADGET_STACK_TESTED
```

It is stronger than local Linux integration because it crosses real USB host transport and `snd-usb-audio`.

It is weaker than:

```text
PHYSICAL_HARDWARE_TESTED
```

because a Linux gadget is not a commercial DAC firmware/clock implementation.

## RESULT

```text
PROMOTE:
Lab infrastructure

DO NOT:
ship as Stable product dependency
claim commercial DAC compatibility from it
```

---

# 189. KDR-013 — USBMON AS LAST-RESORT DEEP OBSERVER

`usbmon` exposes USB driver → HCD requests and completion information.

It is useful after higher-level evidence fails.

But:

```text
requires privileged/debug access
may capture unrelated devices on the same bus
must be sanitized
is not an electrical analyzer
HCD bugs can make trace semantics imperfect
```

Therefore:

```text
R16 only
```

Never normal product telemetry.

---

# 190. KDR-014 — DYNAMIC DEBUG BEFORE USBMON

Linux Dynamic Debug can selectively enable `pr_debug()` / `dev_dbg()` callsites by module/file/function.

For a reproduced `snd-usb-audio` issue, V3 escalation becomes:

```text
normal kernel log
↓
scoped dynamic_debug for snd_usb_audio
↓
usbmon only if still necessary
```

The Lab must snapshot and restore prior dynamic-debug state.

Logging that materially changes timing falsifies that diagnostic run.

---

# 191. KDR-015 — KERNEL/HCD REGRESSION AS A FIRST-CLASS POSSIBILITY

A problem that appears after a kernel update or only on one USB controller should not be automatically assigned to:

```text
PipeWire
GStreamer
Michi
```

R14 controls variables and compares:

```text
same Michi commit
same DAC
same track
same profile
kernel A vs kernel B
or controller/port A vs B
```

Only reproducible differences become evidence.

---

# 192. COMMUNITY / FORUM EVIDENCE — STRICTLY HYPOTHESIS-GENERATING

Recent and historical reports include:

```text
users claiming autoclock=0 solved crackling
users claiming lowlatency=0 + implicit_fb=1 solved crackling
other users reporting the same combination made symptoms worse
high-rate crackling changing after kernel updates
DAC behavior differing across USB ports/controllers
issues ultimately traced to cable quality
```

These reports prove only:

```text
there are plausible variables worth testing
```

They do not prove a Michi default.

The contradiction between community outcomes is itself evidence that universal tuning is a bad design.

---

# 193. V3 IMPLEMENTATION TREE DELTA

```text
src/michi/
├── domain/
│   ├── kernel_audio_environment.py
│   ├── usb_audio_driver_witness.py
│   ├── audio_failure_evidence.py
│   └── audio_rate_evidence.py
│
├── application/
│   └── kernel_context_correlation_service.py
│
└── infrastructure/audio_devices/
    ├── linux_kernel_audio_snapshot.py
    └── usb_audio_stream_proc.py

tools/michi_audio_lab/
├── driver_parameter_diff.py
├── kernel_log_evidence.py
├── dynamic_debug_plan.py
├── usbmon_capture_plan.py
├── usb_uac2_gadget_profile.py
└── experiments/
    ├── R11_kernel_environment_baseline.yaml
    ├── R12_usb_power_resume_correlation.yaml
    ├── R13_usb_gadget_host_stack.yaml
    ├── R14_kernel_hcd_regression_ab.yaml
    ├── R15_driver_parameter_hypothesis.yaml
    ├── R16_usbmon_deep_capture.yaml
    ├── R17_driver_stream_witness_consistency.yaml
    └── R18_dynamic_debug_escalation.yaml
```

---

# 194. FILE — `src/michi/domain/kernel_audio_environment.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ObservationAvailability(Enum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class UsbAudioDriverParameterSnapshot:
    """
    Read-only snapshot of snd-usb-audio module parameters.

    Values remain raw strings because several parameters are arrays or
    VID:PID-scoped expressions. This class does not claim that a configured
    parameter is an effective per-device static quirk.
    """
    values: Mapping[str, str]
    availability: ObservationAvailability


@dataclass(frozen=True)
class UsbPowerStateSnapshot:
    control: str | None
    runtime_status: str | None
    autosuspend_delay_ms: int | None
    usb_autosuspend_raw: str | None
    persist: bool | None
    supports_autosuspend_raw: str | None
    wakeup: str | None
    active_duration_ms: int | None
    connected_duration_ms: int | None
    usbcore_default_autosuspend_seconds: int | None


@dataclass(frozen=True)
class UsbTransportSnapshot:
    usb_sysfs_name: str
    speed_mbps: float | None
    busnum: int | None
    devnum: int | None
    device_version: str | None
    driver_name: str | None
    controller_path: str | None


@dataclass(frozen=True)
class UsbDescriptorFingerprint:
    sha256: str | None
    byte_length: int | None
    provenance: str = "sysfs_cached_descriptors"


@dataclass(frozen=True)
class KernelAudioEnvironmentSnapshot:
    kernel_release: str
    snd_usb_audio: UsbAudioDriverParameterSnapshot
    usb_transport: UsbTransportSnapshot
    usb_power: UsbPowerStateSnapshot
    descriptors: UsbDescriptorFingerprint


@dataclass(frozen=True)
class CapabilityContextFingerprint:
    """
    Context that may affect capability/openability claims.

    Deliberately excludes ephemeral runtime power status.
    """
    kernel_release: str
    snd_usb_audio_parameters_digest: str
    descriptor_sha256: str | None
    usb_speed_mbps: float | None


@dataclass(frozen=True)
class ExecutionEnvironmentFingerprint:
    """
    Broader context for playback stability/failure correlation.
    """
    capability: CapabilityContextFingerprint
    usb_controller_path: str | None
    power_control: str | None
    autosuspend_delay_ms: int | None
```

---

# 195. FILE — `src/michi/infrastructure/audio_devices/linux_kernel_audio_snapshot.py`

**Role:** passive sysfs/module-parameter observation.

**Must never:**

```text
write module parameters
write power/control
reload snd-usb-audio
change usbcore autosuspend
```

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import platform

from michi.domain.kernel_audio_environment import (
    CapabilityContextFingerprint,
    ExecutionEnvironmentFingerprint,
    KernelAudioEnvironmentSnapshot,
    ObservationAvailability,
    UsbAudioDriverParameterSnapshot,
    UsbDescriptorFingerprint,
    UsbPowerStateSnapshot,
    UsbTransportSnapshot,
)


SND_USB_AUDIO_PARAMETERS = (
    "autoclock",
    "lowlatency",
    "implicit_fb",
    "nrpacks",
    "use_vmalloc",
    "skip_validation",
    "quirk_flags",
    "ignore_ctl_error",
    "delayed_register",
)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def _int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 10)
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _bool01(value: str | None) -> bool | None:
    if value is None:
        return None
    if value in {"1", "Y", "y", "yes", "on"}:
        return True
    if value in {"0", "N", "n", "no", "off"}:
        return False
    return None


def read_snd_usb_audio_parameters(
    parameters_dir: Path = Path("/sys/module/snd_usb_audio/parameters"),
) -> UsbAudioDriverParameterSnapshot:
    values: dict[str, str] = {}

    for name in SND_USB_AUDIO_PARAMETERS:
        value = _read_text(parameters_dir / name)
        if value is not None:
            values[name] = value

    if not values:
        availability = ObservationAvailability.UNAVAILABLE
    elif len(values) < len(SND_USB_AUDIO_PARAMETERS):
        availability = ObservationAvailability.PARTIAL
    else:
        availability = ObservationAvailability.AVAILABLE

    return UsbAudioDriverParameterSnapshot(
        values=values,
        availability=availability,
    )


def _driver_name(device_path: Path) -> str | None:
    link = device_path / "driver"
    try:
        return link.resolve(strict=True).name
    except OSError:
        return None


def _controller_path(device_path: Path) -> str | None:
    """
    Return a stable-ish topology string for correlation, not identity.

    Walk toward the PCI/SoC parent and preserve the resolved sysfs path.
    This value must not become canonical AudioDevice identity.
    """
    try:
        resolved = device_path.resolve(strict=True)
    except OSError:
        return None

    for candidate in (resolved, *resolved.parents):
        uevent = _read_text(candidate / "uevent")
        if uevent and (
            "PCI_SLOT_NAME=" in uevent
            or "DRIVER=xhci_hcd" in uevent
            or "DRIVER=ehci-pci" in uevent
        ):
            return str(candidate)

    return str(resolved.parent)


def read_usb_device_snapshot(
    device_path: Path,
    *,
    kernel_release: str | None = None,
    parameters_dir: Path = Path("/sys/module/snd_usb_audio/parameters"),
) -> KernelAudioEnvironmentSnapshot:
    params = read_snd_usb_audio_parameters(parameters_dir)

    descriptor_bytes = _read_bytes(device_path / "descriptors")
    descriptors = UsbDescriptorFingerprint(
        sha256=(
            sha256(descriptor_bytes).hexdigest()
            if descriptor_bytes is not None
            else None
        ),
        byte_length=(
            len(descriptor_bytes)
            if descriptor_bytes is not None
            else None
        ),
    )

    autosuspend_delay_ms_raw = _read_text(
        device_path / "power/autosuspend_delay_ms"
    )

    power = UsbPowerStateSnapshot(
        control=_read_text(device_path / "power/control"),
        runtime_status=_read_text(device_path / "power/runtime_status"),
        autosuspend_delay_ms=_int(autosuspend_delay_ms_raw),
        # USB-specific `power/autosuspend` has had historical/documentation
        # unit differences; preserve it as raw evidence rather than guessing.
        usb_autosuspend_raw=_read_text(device_path / "power/autosuspend"),
        persist=_bool01(_read_text(device_path / "power/persist")),
        # `supports_autosuspend` semantics depend on the exact sysfs node
        # (device/interface/root-hub context). Keep raw until the path scope
        # is explicitly modeled.
        supports_autosuspend_raw=_read_text(
            device_path / "supports_autosuspend"
        ),
        wakeup=_read_text(device_path / "power/wakeup"),
        active_duration_ms=_int(
            _read_text(device_path / "power/active_duration")
        ),
        connected_duration_ms=_int(
            _read_text(device_path / "power/connected_duration")
        ),
        usbcore_default_autosuspend_seconds=_int(
            _read_text(Path("/sys/module/usbcore/parameters/autosuspend"))
        ),
    )

    transport = UsbTransportSnapshot(
        usb_sysfs_name=device_path.name,
        speed_mbps=_float(_read_text(device_path / "speed")),
        busnum=_int(_read_text(device_path / "busnum")),
        devnum=_int(_read_text(device_path / "devnum")),
        device_version=_read_text(device_path / "version"),
        driver_name=_driver_name(device_path),
        controller_path=_controller_path(device_path),
    )

    return KernelAudioEnvironmentSnapshot(
        kernel_release=kernel_release or platform.release(),
        snd_usb_audio=params,
        usb_transport=transport,
        usb_power=power,
        descriptors=descriptors,
    )


def _parameter_digest(snapshot: UsbAudioDriverParameterSnapshot) -> str:
    material = "\n".join(
        f"{key}={snapshot.values[key]}"
        for key in sorted(snapshot.values)
    )
    return sha256(material.encode("utf-8")).hexdigest()


def capability_context_fingerprint(
    snapshot: KernelAudioEnvironmentSnapshot,
) -> CapabilityContextFingerprint:
    return CapabilityContextFingerprint(
        kernel_release=snapshot.kernel_release,
        snd_usb_audio_parameters_digest=_parameter_digest(
            snapshot.snd_usb_audio
        ),
        descriptor_sha256=snapshot.descriptors.sha256,
        usb_speed_mbps=snapshot.usb_transport.speed_mbps,
    )


def execution_environment_fingerprint(
    snapshot: KernelAudioEnvironmentSnapshot,
) -> ExecutionEnvironmentFingerprint:
    return ExecutionEnvironmentFingerprint(
        capability=capability_context_fingerprint(snapshot),
        usb_controller_path=snapshot.usb_transport.controller_path,
        power_control=snapshot.usb_power.control,
        autosuspend_delay_ms=snapshot.usb_power.autosuspend_delay_ms,
    )
```

---

# 196. FILE — `src/michi/domain/usb_audio_driver_witness.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UsbSyncMode(Enum):
    ASYNC = "async"
    ADAPTIVE = "adaptive"
    SYNC = "sync"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class UsbAudioRuntimeStatus:
    state: str
    interface: int | None
    altset: int | None
    packet_size: int | None
    momentary_rate_hz: float | None
    feedback_format: str | None


@dataclass(frozen=True)
class UsbAudioAltsetting:
    interface: int
    altset: int
    format: str | None
    channels: int | None
    endpoint: str | None
    sync_mode: UsbSyncMode
    rates_hz: tuple[int, ...]
    data_packet_interval_us: float | None
    significant_bits: int | None
    channel_map: tuple[str, ...]
    sync_endpoint: str | None
    sync_interface: int | None
    sync_altset: int | None
    implicit_feedback: bool | None


@dataclass(frozen=True)
class UsbAudioDirectionWitness:
    direction: str
    runtime: UsbAudioRuntimeStatus | None
    altsettings: tuple[UsbAudioAltsetting, ...]


@dataclass(frozen=True)
class UsbAudioDriverWitness:
    header: str | None
    playback: UsbAudioDirectionWitness | None
    capture: UsbAudioDirectionWitness | None
    provenance: str = "snd_usb_audio_proc_stream"
```

---

# 197. FILE — `src/michi/infrastructure/audio_devices/usb_audio_stream_proc.py`

The parser is intentionally tolerant.

If kernel output evolves or cannot be parsed:

```text
return unavailable
never break playback
```

```python
from __future__ import annotations

import re

from michi.domain.usb_audio_driver_witness import (
    UsbAudioAltsetting,
    UsbAudioDirectionWitness,
    UsbAudioDriverWitness,
    UsbAudioRuntimeStatus,
    UsbSyncMode,
)


_RE_INTERFACE = re.compile(r"^Interface\s+(\d+)$")
_RE_ALTSET = re.compile(r"^Altset\s+(\d+)$")
_RE_ENDPOINT = re.compile(
    r"^(?:Endpoint:\s*)?(.+?)(?:\s+\((ASYNC|ADAPTIVE|SYNC)\))?$",
    re.IGNORECASE,
)
_RE_STATUS_KV = re.compile(r"^([A-Za-z ]+)\s*=\s*(.+)$")
_RE_INT = re.compile(r"-?\d+")


def _first_int(text: str | None) -> int | None:
    if not text:
        return None
    match = _RE_INT.search(text)
    return int(match.group()) if match else None


def _float(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def _sync_mode(value: str | None) -> UsbSyncMode:
    if value is None:
        return UsbSyncMode.UNKNOWN
    value = value.lower()
    if value == "async":
        return UsbSyncMode.ASYNC
    if value == "adaptive":
        return UsbSyncMode.ADAPTIVE
    if value == "sync":
        return UsbSyncMode.SYNC
    return UsbSyncMode.UNKNOWN


def _parse_endpoint(value: str) -> tuple[str, UsbSyncMode]:
    match = _RE_ENDPOINT.match(value.strip())
    if not match:
        return value.strip(), UsbSyncMode.UNKNOWN
    return match.group(1).strip(), _sync_mode(match.group(2))


def _parse_rates(value: str) -> tuple[int, ...]:
    return tuple(int(item) for item in re.findall(r"\d+", value))


def _parse_channel_map(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split() if item)


def _parse_interval_us(value: str) -> float | None:
    number = _float(value)
    if number is None:
        return None
    lowered = value.lower()
    if "ms" in lowered:
        return number * 1000.0
    if "us" in lowered or "µs" in lowered:
        return number
    return None


def _parse_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"yes", "true", "1"}:
        return True
    if lowered in {"no", "false", "0"}:
        return False
    return None


def _parse_runtime(lines: list[str], start: int) -> tuple[UsbAudioRuntimeStatus | None, int]:
    line = lines[start].strip()
    if not line.startswith("Status:"):
        return None, start

    state = line.split(":", 1)[1].strip()
    i = start + 1
    values: dict[str, str] = {}

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if not stripped:
            i += 1
            continue

        if _RE_INTERFACE.match(stripped) or stripped in {"Playback:", "Capture:"}:
            break

        # runtime detail lines are generally more deeply indented
        match = _RE_STATUS_KV.match(stripped)
        if match:
            values[match.group(1).strip().lower()] = match.group(2).strip()
        i += 1

    return (
        UsbAudioRuntimeStatus(
            state=state,
            interface=_first_int(values.get("interface")),
            altset=_first_int(values.get("altset")),
            packet_size=_first_int(values.get("packet size")),
            momentary_rate_hz=_float(values.get("momentary freq")),
            feedback_format=values.get("feedback format"),
        ),
        i,
    )


def _parse_direction(
    lines: list[str],
    start: int,
    direction: str,
) -> tuple[UsbAudioDirectionWitness, int]:
    i = start + 1
    runtime = None
    altsettings: list[UsbAudioAltsetting] = []

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped in {"Playback:", "Capture:"}:
            break

        if stripped.startswith("Status:"):
            runtime, i = _parse_runtime(lines, i)
            continue

        interface_match = _RE_INTERFACE.match(stripped)
        if not interface_match:
            i += 1
            continue

        interface = int(interface_match.group(1))
        i += 1
        if i >= len(lines):
            break

        alt_match = _RE_ALTSET.match(lines[i].strip())
        if not alt_match:
            continue
        altset = int(alt_match.group(1))
        i += 1

        fields: dict[str, str] = {}
        while i < len(lines):
            candidate = lines[i].strip()
            if (
                candidate in {"Playback:", "Capture:"}
                or _RE_INTERFACE.match(candidate)
                or candidate.startswith("Status:")
            ):
                break
            if ":" in candidate:
                key, value = candidate.split(":", 1)
                fields[key.strip()] = value.strip()
            i += 1

        endpoint, sync_mode = _parse_endpoint(fields.get("Endpoint", ""))

        altsettings.append(
            UsbAudioAltsetting(
                interface=interface,
                altset=altset,
                format=fields.get("Format"),
                channels=_first_int(fields.get("Channels")),
                endpoint=endpoint or None,
                sync_mode=sync_mode,
                rates_hz=_parse_rates(fields.get("Rates", "")),
                data_packet_interval_us=_parse_interval_us(
                    fields.get("Data packet interval", "")
                ),
                significant_bits=_first_int(fields.get("Bits")),
                channel_map=_parse_channel_map(fields.get("Channel map", "")),
                sync_endpoint=fields.get("Sync Endpoint"),
                sync_interface=_first_int(fields.get("Sync EP Interface")),
                sync_altset=_first_int(fields.get("Sync EP Altset")),
                implicit_feedback=_parse_bool(
                    fields.get("Implicit Feedback Mode", "")
                ),
            )
        )

    return UsbAudioDirectionWitness(
        direction=direction,
        runtime=runtime,
        altsettings=tuple(altsettings),
    ), i


def parse_usb_audio_stream(text: str) -> UsbAudioDriverWitness:
    lines = text.splitlines()
    header = next((line.strip() for line in lines if line.strip()), None)

    playback = None
    capture = None
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "Playback:":
            playback, i = _parse_direction(lines, i, "playback")
            continue
        if stripped == "Capture:":
            capture, i = _parse_direction(lines, i, "capture")
            continue
        i += 1

    return UsbAudioDriverWitness(
        header=header,
        playback=playback,
        capture=capture,
    )


from pathlib import Path


class UsbAudioStreamProcReader:
    """
    Tolerant diagnostic reader for snd-usb-audio's /proc/asound/<card>/streamN.

    This proc text is a driver diagnostic surface, not a domain contract.
    Parser failure degrades evidence; it must never fail playback.
    """

    def read(
        self,
        *,
        alsa_card_name: str,
        stream_index: int = 0,
        proc_root: Path = Path("/proc/asound"),
    ) -> UsbAudioDriverWitness | None:
        path = proc_root / alsa_card_name / f"stream{stream_index}"
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None

        try:
            return parse_usb_audio_stream(raw)
        except Exception:
            return None
```

---

# 198. FILE — `src/michi/domain/audio_failure_evidence.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureLayer(Enum):
    APPLICATION = "application"
    GSTREAMER = "gstreamer"
    ALSA_PCM_API = "alsa_pcm_api"
    KERNEL_USB_URB = "kernel_usb_urb"
    USB_POWER = "usb_power"
    UNKNOWN = "unknown"


class FailureKind(Enum):
    DEVICE_BUSY = "device_busy"
    DEVICE_REMOVED = "device_removed"
    XRUN = "xrun"
    DEVICE_SUSPENDED = "device_suspended"
    USB_ENDPOINT_STALL = "usb_endpoint_stall"
    USB_BANDWIDTH_EXHAUSTED = "usb_bandwidth_exhausted"
    FORMAT_UNSUPPORTED = "format_unsupported"
    NEGOTIATION_FAILED = "negotiation_failed"
    BACKEND_FAILURE = "backend_failure"
    UNKNOWN = "unknown"


class Confidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class FailureEvidence:
    layer: FailureLayer
    errno_name: str | None
    message: str | None
    alsa_pcm_state: str | None
    udev_device_present: bool | None
    exact_tuple_was_being_configured: bool


@dataclass(frozen=True)
class FailureCandidate:
    kind: FailureKind
    confidence: Confidence
    reason: str


def classify_failure(
    evidence: FailureEvidence,
) -> tuple[FailureCandidate, ...]:
    out: list[FailureCandidate] = []

    if (
        evidence.udev_device_present is False
        or evidence.errno_name in {"ENODEV", "ESHUTDOWN"}
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_REMOVED,
                Confidence.HIGH,
                "Device absence/removal evidence observed.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "EBUSY"
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_BUSY,
                Confidence.HIGH,
                "ALSA PCM open/configure returned EBUSY.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and (
            evidence.errno_name == "EPIPE"
            or evidence.alsa_pcm_state == "XRUN"
        )
    ):
        out.append(
            FailureCandidate(
                FailureKind.XRUN,
                Confidence.HIGH,
                "ALSA PCM API/state reports XRUN semantics.",
            )
        )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "ESTRPIPE"
    ):
        out.append(
            FailureCandidate(
                FailureKind.DEVICE_SUSPENDED,
                Confidence.HIGH,
                "ALSA PCM API reports suspended stream.",
            )
        )

    if evidence.layer is FailureLayer.KERNEL_USB_URB:
        if evidence.errno_name == "EPIPE":
            out.append(
                FailureCandidate(
                    FailureKind.USB_ENDPOINT_STALL,
                    Confidence.HIGH,
                    "USB URB EPIPE means endpoint stalled in this layer.",
                )
            )
        elif evidence.errno_name == "ENOSPC":
            out.append(
                FailureCandidate(
                    FailureKind.USB_BANDWIDTH_EXHAUSTED,
                    Confidence.HIGH,
                    "USB URB ENOSPC reports insufficient periodic bandwidth.",
                )
            )
        elif evidence.errno_name == "EHOSTUNREACH":
            out.append(
                FailureCandidate(
                    FailureKind.DEVICE_SUSPENDED,
                    Confidence.HIGH,
                    "USB layer reports suspended/unreachable device.",
                )
            )

    if (
        evidence.layer is FailureLayer.ALSA_PCM_API
        and evidence.errno_name == "EINVAL"
        and evidence.exact_tuple_was_being_configured
        and evidence.udev_device_present is not False
    ):
        out.append(
            FailureCandidate(
                FailureKind.FORMAT_UNSUPPORTED,
                Confidence.MEDIUM,
                (
                    "Exact ALSA tuple configuration returned EINVAL; "
                    "physical/backend evidence is still required before "
                    "generalizing this mapping."
                ),
            )
        )

    if not out:
        out.append(
            FailureCandidate(
                FailureKind.UNKNOWN,
                Confidence.LOW,
                "No layer-specific classification is justified.",
            )
        )

    return tuple(out)
```

---

# 199. FILE — `src/michi/application/kernel_context_correlation_service.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from michi.domain.audio_failure_evidence import FailureEvidence
from michi.domain.kernel_audio_environment import (
    ExecutionEnvironmentFingerprint,
    KernelAudioEnvironmentSnapshot,
)


@dataclass(frozen=True)
class FailureContextBundle:
    failure: FailureEvidence
    environment: KernelAudioEnvironmentSnapshot
    execution_fingerprint: ExecutionEnvironmentFingerprint
    session_id: str | None
    experiment_id: str | None


class KernelContextCorrelationService:
    """
    Attaches environmental evidence to a failure.

    It does not mutate kernel parameters and cannot decide playback policy.
    """

    def bundle(
        self,
        *,
        failure: FailureEvidence,
        environment: KernelAudioEnvironmentSnapshot,
        execution_fingerprint: ExecutionEnvironmentFingerprint,
        session_id: str | None,
        experiment_id: str | None,
    ) -> FailureContextBundle:
        return FailureContextBundle(
            failure=failure,
            environment=environment,
            execution_fingerprint=execution_fingerprint,
            session_id=session_id,
            experiment_id=experiment_id,
        )
```

---

# 200. FILE — `src/michi/domain/audio_rate_evidence.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RateEvidenceKind(Enum):
    SOURCE = "source"
    REQUESTED = "requested"
    GSTREAMER_NEGOTIATED = "gstreamer_negotiated"
    ALSA_HW_PARAMS = "alsa_hw_params"
    DRIVER_MOMENTARY_FEEDBACK = "driver_momentary_feedback"
    DEVICE_CONTROL_READBACK = "device_control_readback"


class RateEvidenceTrust(Enum):
    SEMANTIC_TARGET = "semantic_target"
    NEGOTIATED_RUNTIME = "negotiated_runtime"
    DRIVER_OBSERVATION = "driver_observation"
    DEVICE_READBACK = "device_readback"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RateEvidence:
    kind: RateEvidenceKind
    rate_hz: float | None
    trust: RateEvidenceTrust
    evidence_ref: str


@dataclass(frozen=True)
class RateComparison:
    source_matches_alsa: bool | None
    driver_momentary_close_to_alsa: bool | None
    device_readback_matches_alsa: bool | None
    warnings: tuple[str, ...]


def _close(a: float, b: float, ppm: float = 200.0) -> bool:
    if b == 0:
        return False
    return abs(a - b) / b * 1_000_000.0 <= ppm


def compare_rate_evidence(
    evidence: tuple[RateEvidence, ...],
) -> RateComparison:
    by_kind = {item.kind: item for item in evidence}

    source = by_kind.get(RateEvidenceKind.SOURCE)
    alsa = by_kind.get(RateEvidenceKind.ALSA_HW_PARAMS)
    momentary = by_kind.get(RateEvidenceKind.DRIVER_MOMENTARY_FEEDBACK)
    readback = by_kind.get(RateEvidenceKind.DEVICE_CONTROL_READBACK)

    source_matches = None
    if source and alsa and source.rate_hz is not None and alsa.rate_hz is not None:
        source_matches = int(round(source.rate_hz)) == int(round(alsa.rate_hz))

    momentary_matches = None
    if momentary and alsa and momentary.rate_hz is not None and alsa.rate_hz is not None:
        momentary_matches = _close(momentary.rate_hz, alsa.rate_hz)

    readback_matches = None
    warnings: list[str] = []
    if readback and alsa and readback.rate_hz is not None and alsa.rate_hz is not None:
        readback_matches = int(round(readback.rate_hz)) == int(round(alsa.rate_hz))
        if not readback_matches:
            warnings.append(
                "Device control readback differs from ALSA runtime rate; "
                "do not automatically classify this as resampling."
            )

    return RateComparison(
        source_matches_alsa=source_matches,
        driver_momentary_close_to_alsa=momentary_matches,
        device_readback_matches_alsa=readback_matches,
        warnings=tuple(warnings),
    )
```

---

# 201. FILE — `tools/michi_audio_lab/driver_parameter_diff.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ParameterChange:
    name: str
    before: str | None
    after: str | None


def diff_parameters(
    before: Mapping[str, str],
    after: Mapping[str, str],
) -> tuple[ParameterChange, ...]:
    keys = sorted(set(before) | set(after))
    return tuple(
        ParameterChange(
            name=key,
            before=before.get(key),
            after=after.get(key),
        )
        for key in keys
        if before.get(key) != after.get(key)
    )
```

---

# 202. FILE — `tools/michi_audio_lab/kernel_log_evidence.py`

This helper preserves kernel-origin evidence.

It is not a complete kernel log parser.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class KernelLogSubsystem(Enum):
    SND_USB_AUDIO = "snd_usb_audio"
    USB_CORE = "usb_core"
    XHCI = "xhci"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class KernelLogEvidence:
    raw_line: str
    subsystem: KernelLogSubsystem
    errno_name: str | None
    message: str


_ERRNO_BY_NUMBER = {
    -19: "ENODEV",
    -32: "EPIPE",
    -28: "ENOSPC",
    -108: "ESHUTDOWN",
    -113: "EHOSTUNREACH",
    -22: "EINVAL",
}


def classify_kernel_log_line(line: str) -> KernelLogEvidence:
    lowered = line.lower()

    if "snd-usb-audio" in lowered or "usb-audio" in lowered:
        subsystem = KernelLogSubsystem.SND_USB_AUDIO
    elif "xhci" in lowered:
        subsystem = KernelLogSubsystem.XHCI
    elif re.search(r"\busb\s+\d", lowered):
        subsystem = KernelLogSubsystem.USB_CORE
    else:
        subsystem = KernelLogSubsystem.UNKNOWN

    errno_name = None
    for match in re.finditer(r"(?<!\d)-\d+", line):
        number = int(match.group())
        if number in _ERRNO_BY_NUMBER:
            errno_name = _ERRNO_BY_NUMBER[number]
            break

    return KernelLogEvidence(
        raw_line=line,
        subsystem=subsystem,
        errno_name=errno_name,
        message=line.strip(),
    )
```

---

# 203. FILE — `tools/michi_audio_lab/dynamic_debug_plan.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DynamicDebugPlan:
    """Lab-only plan; never mutates dynamic_debug by itself."""
    module_name: str = "snd_usb_audio"
    enable_flags: str = "+pmf"
    require_control_file: bool = True
    require_root: bool = True
    restore_previous_state: bool = True

    def enable_command(self) -> str:
        return f"module {self.module_name} {self.enable_flags}"

    def disable_command(self) -> str:
        return f"module {self.module_name} -p"

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.module_name.strip():
            errors.append("module_name must not be empty")
        if " " in self.module_name:
            errors.append("module_name must not contain spaces")
        if not self.enable_flags.startswith("+"):
            errors.append("enable_flags must add flags explicitly")
        return tuple(errors)
```

---

# 204. FILE — `tools/michi_audio_lab/usbmon_capture_plan.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UsbMonCapturePlan:
    """
    Lab-only planning object.

    usbmon can expose traffic for unrelated devices on the same bus. The
    capture implementation must minimize scope and sanitize artifacts.
    """
    busnum: int
    devnum: int
    binary_api_required: bool = True
    requires_privileged_access: bool = True
    sanitize_before_sharing: bool = True

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.busnum <= 0:
            errors.append("busnum must be positive")
        if self.devnum <= 0:
            errors.append("devnum must be positive")
        return tuple(errors)
```

---

# 205. FILE — `tools/michi_audio_lab/usb_uac2_gadget_profile.py`

This is a declarative plan only.

The final UDC binding is deliberately separated as an explicit Lab action.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Uac2GadgetProfile:
    vendor_id: int = 0x1D6B
    product_id: int = 0x1040

    playback_channel_mask: int = 0x3
    playback_rates_hz: tuple[int, ...] = (44100, 48000, 96000, 192000)
    playback_sample_size_bytes: int = 4

    capture_channel_mask: int = 0x3
    capture_rates_hz: tuple[int, ...] = (44100, 48000, 96000, 192000)
    capture_sample_size_bytes: int = 4

    request_count: int = 8
    manufacturer: str = "Michi Lab"
    product: str = "Michi USB DAC Emulator"
    serial: str = "MICHI-UAC2-LAB-0001"

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []

        for name, value in (
            ("playback_sample_size_bytes", self.playback_sample_size_bytes),
            ("capture_sample_size_bytes", self.capture_sample_size_bytes),
        ):
            if value < 1 or value > 4:
                errors.append(f"{name} must be between 1 and 4")

        if not self.playback_rates_hz:
            errors.append("playback_rates_hz must not be empty")
        if not self.capture_rates_hz:
            errors.append("capture_rates_hz must not be empty")
        if self.request_count <= 0:
            errors.append("request_count must be positive")

        return tuple(errors)


@dataclass(frozen=True)
class ConfigfsOperation:
    operation: str
    relative_path: str
    value: str | None = None
    target: str | None = None


def build_uac2_configfs_plan(
    profile: Uac2GadgetProfile,
    *,
    gadget_name: str = "michi_uac2",
    function_name: str = "uac2.michi",
    config_name: str = "c.1",
) -> tuple[ConfigfsOperation, ...]:
    errors = profile.validate()
    if errors:
        raise ValueError("; ".join(errors))

    base = f"usb_gadget/{gadget_name}"
    function = f"{base}/functions/{function_name}"
    config = f"{base}/configs/{config_name}"

    rates_p = ",".join(str(x) for x in profile.playback_rates_hz)
    rates_c = ",".join(str(x) for x in profile.capture_rates_hz)

    return (
        ConfigfsOperation("mkdir", base),
        ConfigfsOperation("write", f"{base}/idVendor", f"0x{profile.vendor_id:04x}"),
        ConfigfsOperation("write", f"{base}/idProduct", f"0x{profile.product_id:04x}"),
        ConfigfsOperation("mkdir", f"{base}/strings/0x409"),
        ConfigfsOperation("write", f"{base}/strings/0x409/manufacturer", profile.manufacturer),
        ConfigfsOperation("write", f"{base}/strings/0x409/product", profile.product),
        ConfigfsOperation("write", f"{base}/strings/0x409/serialnumber", profile.serial),
        ConfigfsOperation("mkdir", config),
        ConfigfsOperation("mkdir", f"{config}/strings/0x409"),
        ConfigfsOperation("write", f"{config}/strings/0x409/configuration", "Michi UAC2 Lab"),
        ConfigfsOperation("mkdir", function),
        ConfigfsOperation("write", f"{function}/p_chmask", str(profile.playback_channel_mask)),
        ConfigfsOperation("write", f"{function}/p_srate", rates_p),
        ConfigfsOperation("write", f"{function}/p_ssize", str(profile.playback_sample_size_bytes)),
        ConfigfsOperation("write", f"{function}/c_chmask", str(profile.capture_channel_mask)),
        ConfigfsOperation("write", f"{function}/c_srate", rates_c),
        ConfigfsOperation("write", f"{function}/c_ssize", str(profile.capture_sample_size_bytes)),
        ConfigfsOperation("write", f"{function}/req_number", str(profile.request_count)),
        ConfigfsOperation(
            "symlink",
            f"{config}/{function_name}",
            target=f"../../functions/{function_name}",
        ),
        # UDC binding is intentionally a separate explicit lab action.
        ConfigfsOperation("bind_udc", f"{base}/UDC"),
    )
```

---

# 206. V3 UNIT TEST — KERNEL ENVIRONMENT

```python
from pathlib import Path

from michi.infrastructure.audio_devices.linux_kernel_audio_snapshot import (
    capability_context_fingerprint,
    read_snd_usb_audio_parameters,
    read_usb_device_snapshot,
)


def write(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def test_driver_parameters_are_feature_detected(tmp_path):
    params = tmp_path / "parameters"
    write(params / "autoclock", "Y\n")
    write(params / "lowlatency", "N\n")

    snap = read_snd_usb_audio_parameters(params)
    assert snap.values["autoclock"] == "Y"
    assert snap.values["lowlatency"] == "N"


def test_usb_snapshot_hashes_cached_descriptors_and_reads_power(tmp_path):
    dev = tmp_path / "1-2"
    dev.mkdir()
    (dev / "descriptors").write_bytes(b"descriptor-fixture")
    write(dev / "speed", "480\n")
    write(dev / "busnum", "1\n")
    write(dev / "devnum", "7\n")
    write(dev / "version", "2.00\n")
    write(dev / "power/control", "auto\n")
    write(dev / "power/runtime_status", "active\n")
    write(dev / "power/autosuspend_delay_ms", "2000\n")
    write(dev / "power/persist", "1\n")
    write(dev / "supports_autosuspend", "1\n")
    write(dev / "power/wakeup", "enabled\n")
    write(dev / "power/active_duration", "1234\n")
    write(dev / "power/connected_duration", "2345\n")

    params = tmp_path / "params"
    write(params / "autoclock", "Y\n")

    snap = read_usb_device_snapshot(
        dev,
        kernel_release="6.test",
        parameters_dir=params,
    )
    assert snap.kernel_release == "6.test"
    assert snap.usb_transport.speed_mbps == 480.0
    assert snap.usb_power.control == "auto"
    assert snap.usb_power.wakeup == "enabled"
    assert snap.usb_power.active_duration_ms == 1234
    assert snap.usb_power.connected_duration_ms == 2345
    assert snap.descriptors.sha256 is not None
    assert snap.descriptors.byte_length == len(b"descriptor-fixture")

    fingerprint = capability_context_fingerprint(snap)
    assert fingerprint.kernel_release == "6.test"
    assert fingerprint.usb_speed_mbps == 480.0
```

---

# 207. V3 UNIT TEST — DRIVER STREAM WITNESS

```python
from michi.domain.usb_audio_driver_witness import UsbSyncMode
from michi.infrastructure.audio_devices.usb_audio_stream_proc import (
    parse_usb_audio_stream,
)


FIXTURE = """
Reference USB DAC at usb-0000:06:00.0-1, high speed : USB Audio

Playback:
  Status: Running
    Interface = 1
    Altset = 1
    Packet Size = 192
    Momentary freq = 96000 Hz (0xc.0000)
    Feedback Format = 16.16
  Interface 1
    Altset 1
    Format: S32_LE
    Channels: 2
    Endpoint: 0x01 (1 OUT) (ASYNC)
    Rates: 44100, 48000, 96000, 192000
    Data packet interval: 125 us
    Bits: 24
    Channel map: FL FR
    Sync Endpoint: 0x81 (1 IN)
    Sync EP Interface: 1
    Sync EP Altset: 1
    Implicit Feedback Mode: No
  Interface 1
    Altset 2
    Format: S16_LE
    Channels: 2
    Endpoint: 0x01 (1 OUT) (ASYNC)
    Rates: 44100, 48000
    Data packet interval: 125 us
    Bits: 16
    Channel map: FL FR
    Sync Endpoint: 0x81 (1 IN)
    Sync EP Interface: 1
    Sync EP Altset: 2
    Implicit Feedback Mode: No

Capture:
  Status: Stop
  Interface 2
    Altset 1
    Format: S32_LE
    Channels: 2
    Endpoint: 0x82 (2 IN) (ASYNC)
    Rates: 44100, 48000, 96000, 192000
    Data packet interval: 125 us
    Bits: 24
    Channel map: FL FR
"""


def test_parse_driver_decoded_stream_capabilities_and_runtime():
    witness = parse_usb_audio_stream(FIXTURE)
    assert witness.playback is not None
    assert witness.playback.runtime is not None
    assert witness.playback.runtime.state == "Running"
    assert witness.playback.runtime.interface == 1
    assert witness.playback.runtime.altset == 1
    assert witness.playback.runtime.packet_size == 192
    assert witness.playback.runtime.momentary_rate_hz == 96000.0
    assert witness.playback.runtime.feedback_format == "16.16"

    first = witness.playback.altsettings[0]
    assert first.interface == 1
    assert first.altset == 1
    assert first.format == "S32_LE"
    assert first.channels == 2
    assert first.rates_hz == (44100, 48000, 96000, 192000)
    assert first.significant_bits == 24
    assert first.channel_map == ("FL", "FR")
    assert first.sync_mode is UsbSyncMode.ASYNC
    assert first.implicit_feedback is False
    assert first.data_packet_interval_us == 125.0


def test_capture_is_parsed_independently():
    witness = parse_usb_audio_stream(FIXTURE)
    assert witness.capture is not None
    assert witness.capture.runtime is not None
    assert witness.capture.runtime.state == "Stop"
    assert witness.capture.altsettings[0].endpoint.startswith("0x82")



def test_proc_reader_is_non_authoritative_and_returns_none_when_missing(tmp_path):
    from michi.infrastructure.audio_devices.usb_audio_stream_proc import (
        UsbAudioStreamProcReader,
    )

    reader = UsbAudioStreamProcReader()
    assert reader.read(
        alsa_card_name="Missing",
        proc_root=tmp_path,
    ) is None


def test_proc_reader_reads_fixture(tmp_path):
    from michi.infrastructure.audio_devices.usb_audio_stream_proc import (
        UsbAudioStreamProcReader,
    )

    card = tmp_path / "DAC"
    card.mkdir()
    (card / "stream0").write_text(FIXTURE, encoding="utf-8")

    witness = UsbAudioStreamProcReader().read(
        alsa_card_name="DAC",
        proc_root=tmp_path,
    )
    assert witness is not None
    assert witness.playback is not None
    assert witness.playback.altsettings[0].significant_bits == 24
```

---

# 208. V3 UNIT TEST — LAYER-AWARE FAILURES

```python
from michi.domain.audio_failure_evidence import (
    Confidence,
    FailureEvidence,
    FailureKind,
    FailureLayer,
    classify_failure,
)


def ev(layer, errno=None, state=None, present=True, exact=False):
    return FailureEvidence(
        layer=layer,
        errno_name=errno,
        message=None,
        alsa_pcm_state=state,
        udev_device_present=present,
        exact_tuple_was_being_configured=exact,
    )


def test_alsa_epipe_is_xrun():
    result = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EPIPE")
    )
    assert result[0].kind is FailureKind.XRUN
    assert result[0].confidence is Confidence.HIGH


def test_kernel_usb_epipe_is_endpoint_stall_not_xrun():
    result = classify_failure(
        ev(FailureLayer.KERNEL_USB_URB, "EPIPE")
    )
    assert result[0].kind is FailureKind.USB_ENDPOINT_STALL


def test_kernel_enospc_is_usb_bandwidth():
    result = classify_failure(
        ev(FailureLayer.KERNEL_USB_URB, "ENOSPC")
    )
    assert result[0].kind is FailureKind.USB_BANDWIDTH_EXHAUSTED


def test_alsa_estrpipe_is_suspended():
    result = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "ESTRPIPE")
    )
    assert result[0].kind is FailureKind.DEVICE_SUSPENDED


def test_einval_requires_exact_alsa_context():
    unknown = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EINVAL", exact=False)
    )
    assert unknown[0].kind is FailureKind.UNKNOWN

    supported_candidate = classify_failure(
        ev(FailureLayer.ALSA_PCM_API, "EINVAL", exact=True)
    )
    assert supported_candidate[0].kind is FailureKind.FORMAT_UNSUPPORTED
    assert supported_candidate[0].confidence is Confidence.MEDIUM
```

---

# 209. V3 UNIT TEST — RATE EVIDENCE

```python
from michi.domain.audio_rate_evidence import (
    RateEvidence,
    RateEvidenceKind,
    RateEvidenceTrust,
    compare_rate_evidence,
)


def ev(kind, rate):
    return RateEvidence(
        kind=kind,
        rate_hz=rate,
        trust=RateEvidenceTrust.DRIVER_OBSERVATION,
        evidence_ref="fixture",
    )


def test_momentary_feedback_allows_small_clock_drift():
    result = compare_rate_evidence(
        (
            ev(RateEvidenceKind.SOURCE, 96000),
            ev(RateEvidenceKind.ALSA_HW_PARAMS, 96000),
            ev(RateEvidenceKind.DRIVER_MOMENTARY_FEEDBACK, 95999.8),
        )
    )
    assert result.source_matches_alsa is True
    assert result.driver_momentary_close_to_alsa is True


def test_device_readback_mismatch_is_warning_not_resampling_proof():
    result = compare_rate_evidence(
        (
            ev(RateEvidenceKind.ALSA_HW_PARAMS, 96000),
            ev(RateEvidenceKind.DEVICE_CONTROL_READBACK, 48000),
        )
    )
    assert result.device_readback_matches_alsa is False
    assert result.warnings
```

---

# 210. V3 UNIT TEST — DRIVER PARAMETER DIFF

```python
from tools.michi_audio_lab.driver_parameter_diff import diff_parameters


def test_parameter_diff_reports_only_changes():
    changes = diff_parameters(
        {"autoclock": "Y", "lowlatency": "Y"},
        {"autoclock": "Y", "lowlatency": "N", "implicit_fb": "Y"},
    )
    assert [x.name for x in changes] == ["implicit_fb", "lowlatency"]
```

---

# 211. V3 UNIT TEST — KERNEL LOG EVIDENCE

```python
from tools.michi_audio_lab.kernel_log_evidence import (
    KernelLogSubsystem,
    classify_kernel_log_line,
)


def test_kernel_usb_audio_errno_is_preserved():
    evidence = classify_kernel_log_line(
        "snd-usb-audio 1-2: USB request error -32"
    )
    assert evidence.subsystem is KernelLogSubsystem.SND_USB_AUDIO
    assert evidence.errno_name == "EPIPE"


def test_xhci_is_classified_separately():
    evidence = classify_kernel_log_line(
        "xhci_hcd 0000:00:14.0: WARN Event TRB"
    )
    assert evidence.subsystem is KernelLogSubsystem.XHCI
```

---

# 212. V3 UNIT TEST — DYNAMIC DEBUG PLAN

```python
from tools.michi_audio_lab.dynamic_debug_plan import DynamicDebugPlan


def test_dynamic_debug_defaults_are_scoped_to_usb_audio_module():
    plan = DynamicDebugPlan()
    assert plan.validate() == ()
    assert plan.enable_command() == "module snd_usb_audio +pmf"
    assert plan.disable_command() == "module snd_usb_audio -p"
    assert plan.restore_previous_state is True


def test_invalid_module_name_is_rejected():
    assert DynamicDebugPlan(module_name="snd usb").validate()
```

---

# 213. V3 UNIT TEST — USBMON PLAN

```python
from tools.michi_audio_lab.usbmon_capture_plan import UsbMonCapturePlan


def test_usbmon_plan_requires_positive_bus_and_device():
    assert UsbMonCapturePlan(1, 2).validate() == ()
    assert UsbMonCapturePlan(0, 2).validate()
```

---

# 214. V3 UNIT TEST — UAC2 GADGET PROFILE

```python
import pytest

from tools.michi_audio_lab.usb_uac2_gadget_profile import (
    Uac2GadgetProfile,
    build_uac2_configfs_plan,
)


def test_default_uac2_profile_contains_target_rates():
    profile = Uac2GadgetProfile()
    assert profile.validate() == ()
    assert 44100 in profile.playback_rates_hz
    assert 192000 in profile.playback_rates_hz


def test_configfs_plan_is_declarative_and_udc_bind_is_last():
    plan = build_uac2_configfs_plan(Uac2GadgetProfile())
    assert plan[-1].operation == "bind_udc"
    assert any(
        op.relative_path.endswith("/p_srate")
        and op.value == "44100,48000,96000,192000"
        for op in plan
    )


def test_invalid_sample_size_is_rejected():
    with pytest.raises(ValueError):
        build_uac2_configfs_plan(
            Uac2GadgetProfile(playback_sample_size_bytes=8)
        )
```

---

# 215. R11 — KERNEL ENVIRONMENT BASELINE

```yaml
schema_version: 1
experiment_id: R11_KERNEL_ENVIRONMENT_BASELINE
status: prerequisite_for_physical_kernel_driver_runs

question: >
  Which kernel, snd-usb-audio, USB topology, descriptor, power, and driver-decoded
  facts were present when a playback result was produced?

mayeutic:
  hidden_assumptions:
    - the same DAC behaves the same under every kernel and USB controller
    - current module defaults are irrelevant to playback evidence
    - USB speed and descriptor revision never matter

technical_analysis:
  capture:
    - kernel_release
    - snd_usb_audio_parameters_raw
    - snd_usb_audio_parameters_digest
    - usb_descriptor_sha256
    - usb_speed_mbps
    - busnum
    - devnum
    - usb_controller_path
    - power_control
    - runtime_status
    - autosuspend_delay_ms
    - wakeup
    - active_duration_ms
    - connected_duration_ms
    - proc_stream_driver_witness

pass:
  - artifact_is_complete_or_marks_each_missing_field_unknown
  - no_sysfs_or_module_parameter_is_mutated

falsifiers:
  - observer_changes_driver_or_power_state
  - artifact_silently_substitutes_default_for_missing_value

implementation_result:
  promote: passive_environment_capture
  product_authority: none
```

R11 becomes a prerequisite artifact layer for physical kernel/driver experiments.

---

# 216. R12 — USB POWER / RESUME CORRELATION

```yaml
schema_version: 1
experiment_id: R12_USB_POWER_RESUME_CORRELATION
status: conditional_physical_lab

question: >
  Are playback-loss, delayed-start, or reconnect failures reproducibly correlated
  with USB runtime/system power transitions?

phase_1_passive_only: true
capture:
  - power_control
  - runtime_status
  - wakeup
  - autosuspend_delay_ms
  - active_duration_ms
  - connected_duration_ms
  - kernel_log
  - udev_presence
  - output_session_state
  - proc_stream_driver_witness

actions:
  - play_idle_play
  - pause_resume
  - system_suspend_resume
  - reconnect_after_resume

pass:
  - repeated_runs_converge_without_hidden_fallback

falsifiers:
  - failure_occurs_without_power_transition
  - power_transition_occurs_repeatedly_without_failure

conditional_phase_2:
  requirement: reproducible_phase_1_correlation
  mutation: compare power/control auto vs on under explicit lab approval
  product_default_change: forbidden

safe_retreat: do_not_blame_autosuspend
```

The passive phase must happen first.

No automatic power mutation is allowed.

---

# 217. R13 — USB GADGET HOST STACK

```yaml
schema_version: 1
experiment_id: R13_USB_GADGET_HOST_STACK
status: lab_infrastructure
required_evidence_level: USB_GADGET_STACK_TESTED

question: >
  Can Michi exercise the real Linux USB host, HCD, snd-usb-audio, ALSA and
  GStreamer path against a controlled UAC2 peripheral?

requirements:
  - second_linux_device_with_usb_device_controller
  - CONFIG_USB_CONFIGFS_F_UAC2
  - configfs
  - physical_usb_connection_between_gadget_and_michi_host

profile:
  channels: 2
  rates_hz: [44100, 48000, 96000, 192000]
  sample_size_bytes: 4

host_capture:
  - usb_enumeration
  - descriptor_sha256
  - stable_identity_observation
  - snd_usb_audio_parameters
  - proc_stream_driver_witness
  - gstreamer_current_caps
  - alsa_hw_params
  - kernel_logs

cases:
  - first_enumeration
  - exact_44100
  - exact_48000
  - exact_96000
  - exact_192000
  - gadget_udc_unbind_during_playback
  - gadget_udc_rebind

pass:
  - host_uses_snd_usb_audio
  - all_advertised_exact_rates_open_or_fail_truthfully
  - unplug_reconnect_state_converges

falsifiers:
  - host_path_bypasses_usb_audio_driver
  - advertised_gadget_rate_and_host_driver_witness_contradict_without_capture

claim_limit:
  - does_not_prove_commercial_dac_compatibility
  - does_not_prove_real_dac_firmware_behavior
```

This is the first Michi laboratory experiment that can exercise:

```text
physical USB cable
host controller
USB core
snd-usb-audio
ALSA
GStreamer
```

against a controlled peripheral.

---

# 218. R14 — KERNEL / HCD REGRESSION A/B

```yaml
schema_version: 1
experiment_id: R14_KERNEL_HCD_REGRESSION_AB
status: conditional_regression_lab

question: >
  Is a reproduced failure tied to kernel release, USB host controller, port,
  hub topology, or user-space?

controlled_variables:
  - same_dac
  - same_track
  - same_output_profile
  - same_michi_commit

variants:
  - kernel_a_vs_kernel_b
  - controller_or_port_a_vs_b
  - direct_connection_vs_hub_if_relevant

capture:
  - R11_environment_bundle
  - kernel_logs
  - failure_evidence_with_layer
  - proc_stream_driver_witness
  - output_session_timeline

pass:
  - differences_are_reported_without_auto_workaround

falsifiers:
  - uncontrolled_variables_changed
  - result_not_reproducible

safe_retreat: mark_kernel_or_hcd_correlation_unknown
```

Conditional unless a regression or hardware-seal discrepancy exists.

---

# 219. R15 — DRIVER PARAMETER HYPOTHESIS

```yaml
schema_version: 1
experiment_id: R15_DRIVER_PARAMETER_HYPOTHESIS
status: conditional_only_after_reproduced_failure

question: >
  Does a specific snd-usb-audio parameter or quirk materially change a reproduced
  failure for one identified device/environment?

forbidden_as_default: true
community_reports_are_hypothesis_only: true

factors:
  - lowlatency
  - autoclock
  - implicit_fb

method:
  - baseline_first
  - one_factor_at_a_time
  - explicit_lowlatency_x_implicit_fb_interaction
  - reboot_or_module_reload_when_required
  - record_raw_parameter_state_every_run

capture:
  - R11_environment_bundle
  - failure_count
  - xrun_count
  - kernel_logs
  - proc_stream_driver_witness
  - time_to_first_audio

pass:
  - effect_is_reproducible
  - no_new_regression_introduced

falsifiers:
  - effect_disappears_on_repeat
  - another_factor_explains_result
  - setting_improves_one_case_but_breaks_required_cases

implementation_result:
  product_hidden_mutation: forbidden
  if_repeatedly_required: prepare_upstream_kernel_report
```

Community workarounds may seed R15.

They may not skip the baseline.

---

# 220. R16 — USBMON DEEP CAPTURE

```yaml
schema_version: 1
experiment_id: R16_USBMON_DEEP_CAPTURE
status: deep_conditional_lab

question: >
  When higher-level evidence is insufficient, what USB requests/URBs are visible
  around the reproduced failure?

prerequisites:
  - R11_insufficient
  - R6_or_R14_failure_reproduced
  - explicit_privileged_lab_run

capture:
  - binary_usbmon_api_preferred
  - target_bus
  - target_device_number
  - synchronized_michi_event_timeline

privacy:
  - minimize_bus_scope
  - sanitize_before_sharing
  - never_capture_all_buses_by_default

interpretation_limit:
  - usbmon_records_driver_to_hcd_requests
  - trace_is_not_absolute_electrical_bus_truth

safe_retreat: remain_inconclusive
```

This is a deep-debug escalation, not normal telemetry.

---

# 221. R17 — DRIVER STREAM WITNESS CONSISTENCY

```yaml
schema_version: 1
experiment_id: R17_DRIVER_STREAM_WITNESS_CONSISTENCY
status: required_before_driver_witness_promotion

question: >
  Is snd-usb-audio's /proc/asound/<card>/streamN witness consistent with ALSA
  exact-open evidence and the active GStreamer runtime for tested formats?

rates_hz: [44100, 48000, 96000, 192000]

compare:
  - advertised_altsetting_supports_requested_tuple
  - runtime_interface_altset_is_advertised
  - runtime_format_matches_alsa_hw_params
  - runtime_channels_match_alsa_hw_params
  - momentary_freq_is_close_to_nominal_when_present
  - significant_bits_are_consistent_with_alsa_sbits_when_both_exist

contradiction_policy:
  - preserve_both_sources
  - mark_claim_unknown_or_contradicted
  - never_overwrite_one_source_with_the_other

falsifiers:
  - parser_misreads_real_driver_output
  - driver_witness_repeatedly_contradicts_known_runtime_without_explanation

safe_retreat: keep_proc_stream_parser_lab_only
```

R17 decides how much authority the `/proc/asound/.../streamN` observer deserves.

---

# 222. R18 — DYNAMIC DEBUG ESCALATION

```yaml
schema_version: 1
experiment_id: R18_DYNAMIC_DEBUG_ESCALATION
status: deep_conditional_lab

question: >
  Can scoped snd-usb-audio dynamic-debug output explain a reproduced kernel/driver
  failure before escalating to usbmon?

prerequisites:
  - dynamic_debug_control_exists
  - root_lab_access
  - reproduced_failure

scope:
  module: snd_usb_audio
  capture_prior_state: true
  restore_prior_state: true

capture:
  - enabled_callsites
  - kernel_log_window
  - R11_environment_bundle
  - failure_timeline

pass:
  - adds_explanatory_driver_evidence
  - prior_dynamic_debug_state_restored

falsifiers:
  - no_relevant_callsites
  - logging_materially_changes_failure_behavior

safe_retreat: escalate_to_R16_usbmon_only_if_justified
```

Escalation order:

```text
normal logs
→ R18 dynamic_debug
→ R16 usbmon
```

---

# 223. UPDATED RESEARCH ORDER — V3

Canonical order for unresolved DAC research:

```text
R11 Kernel Environment Baseline
        ↓
R1  Runtime Witness
        ↓
R17 Driver Stream Witness Consistency
        ↓
R8  Pipeline Runtime Audit
        ↓
R3  Sample Preservation
        ↓
R2  Resampler A/B
        ↓
R9  Observer Effect Budget
        ↓
R13 USB Gadget Host Stack
        ↓
R4  Probe vs Real Session
        ↓
R5  Identity Chaos
        ↓
R6  Failure Semantics — now layer-aware
        ↓
R12 Power / Resume Correlation
        ↓
R7  Rate Transition Lab
        ↓
R14 Kernel / HCD Regression A/B     CONDITIONAL
        ↓
R15 Driver Parameter Hypothesis     CONDITIONAL
        ↓
R18 Dynamic Debug                   DEEP CONDITIONAL
        ↓
R16 usbmon                          LAST-RESORT DEEP CONDITIONAL
        ↓
R10 Deep Clock Policy Observation   OPTIONAL LATER; minimum clock/slave observation is PRE-STABLE per §33/R24
```

R11 is intentionally early because every later physical result is easier to audit when its kernel/USB context is frozen.

---

# 224. OPENCODE EXECUTION SLICE — KDR-001 KERNEL ENVIRONMENT SNAPSHOT

```text
OBJECTIVE
Implement passive kernel/USB environment evidence.

CREATE
src/michi/domain/kernel_audio_environment.py
src/michi/infrastructure/audio_devices/linux_kernel_audio_snapshot.py

MUST
feature-detect files
preserve raw unknown values
hash cached descriptors
capture USB speed/topology/power context
remain non-authoritative

MUST NOT
write sysfs
reload modules
change power policy
change usbcore
use busnum/devnum as identity

EVIDENCE
DOMAIN_REFERENCE_TESTED first
LINUX_INTEGRATION_TESTED before claiming target-system coverage

STOP
if sysfs semantics differ from documented assumptions;
record raw evidence and update the model instead of guessing.
```

---

# 225. OPENCODE EXECUTION SLICE — KDR-002 DRIVER STREAM WITNESS

```text
OBJECTIVE
Parse snd-usb-audio's diagnostic stream witness tolerantly.

CREATE
src/michi/domain/usb_audio_driver_witness.py
src/michi/infrastructure/audio_devices/usb_audio_stream_proc.py

MUST
return None/unavailable when proc file is absent or unparseable
preserve runtime and advertised-altsetting facts separately
keep provenance=snd_usb_audio_proc_stream

MUST NOT
make playback depend on parser success
overwrite ALSA/GStreamer evidence when contradictory
promote proc text into a stable external schema

FALSIFICATION
R17 on multiple real devices/kernels.
```

---

# 226. OPENCODE EXECUTION SLICE — KDR-003 LAYER-AWARE FAILURE EVIDENCE

```text
OBJECTIVE
Replace unscoped errno mapping with layer-aware failure evidence.

CREATE
src/michi/domain/audio_failure_evidence.py

REMOVE/SUPERSEDE
former V2 unscoped failure classifier

MUST
carry FailureLayer
map ALSA PCM EPIPE to XRUN
map kernel USB URB EPIPE to endpoint stall
map USB ENOSPC to bandwidth exhaustion
map ALSA ESTRPIPE to suspended stream
leave unknown combinations UNKNOWN

MUST NOT
classify by errno number alone
```

---

# 227. OPENCODE EXECUTION SLICE — KDR-004 RATE EVIDENCE

```text
OBJECTIVE
Separate nominal semantic rate, negotiated rate, feedback-derived momentary rate,
and device-control readback.

MUST
preserve provenance
allow small feedback-clock drift without calling it resampling
flag device-readback contradiction without inventing a conversion

MUST NOT
use one global current_rate field for all evidence sources
```

---

# 228. OPENCODE LAB SLICE — USB-001 UAC2 GADGET EMULATOR

```text
OBJECTIVE
Create controlled Linux UAC2 peripheral infrastructure for host-stack tests.

REQUIRES
second Linux device with USB Device Controller
configfs UAC2 support
explicit privileged lab setup

FILES
tools/michi_audio_lab/usb_uac2_gadget_profile.py
R13 manifest
future executor only after configfs integration test

MUST NOT
run on the Michi host without an appropriate UDC
bind an arbitrary UDC automatically
claim PHYSICAL_HARDWARE_TESTED
```

---

# 229. OPENCODE LAB SLICE — KERNEL DEEP DEBUG ESCALATION

```text
NORMAL
R11 + kernel logs + R6

IF INSUFFICIENT
R18 scoped dynamic_debug

IF STILL INSUFFICIENT
R16 scoped usbmon

MUST
record privilege requirements
restore debug state
sanitize shareable artifacts

MUST NOT
turn deep-debug capture on permanently
```

---

# 230. COMMUNITY REPORT TRIAGE TEMPLATE

When a forum says:

```text
"set lowlatency=0"
```

OpenCode must translate it to:

```text
SOURCE TYPE
community anecdote

DEVICE
VID/PID/model if known

ENVIRONMENT
kernel / distro / controller if known

CLAIM
parameter correlated with improvement

CONFOUNDERS
other changes made by user

MAYEUTIC QUESTION
what driver path does the parameter actually change?

TECHNICAL ANALYSIS
read kernel docs/source

FALSIFICATION
R15 controlled baseline/A/B

RESULT
INCONCLUSIVE until reproduced
```

Never paste the forum command into Stable settings.

---

# 231. V3 REFERENCE TEST STATUS

The V3 pure reference pack was rebuilt from the last known-good pack and executed after the kernel/driver additions.

Result:

```text
75 passed
0 failed
```

This proves only:

```text
reference parsers/models/gates are internally coherent
```

It does not prove:

```text
actual target sysfs availability
actual /proc stream grammar on every kernel
real UAC2 gadget execution
real usbmon capture
real dynamic-debug callsites
physical DAC behavior
```

Those require their declared integration/hardware experiments.

---

# 232. V3 SOURCE REGISTER — UPSTREAM

Primary sources used by this extension:

```text
Linux snd-usb-audio configuration / quirks
https://docs.kernel.org/next/sound/alsa-configuration.html

Linux USB power management
https://docs.kernel.org/driver-api/usb/power-management.html

Linux stable USB sysfs ABI
https://github.com/torvalds/linux/blob/master/Documentation/ABI/stable/sysfs-bus-usb

Linux USB gadget testing / UAC2
https://docs.kernel.org/usb/gadget-testing.html
https://github.com/torvalds/linux/blob/master/Documentation/usb/gadget-testing.rst

Linux usbmon
https://docs.kernel.org/usb/usbmon.html

Linux dynamic debug
https://docs.kernel.org/admin-guide/dynamic-debug-howto.html

Linux USB host APIs / HCD behavior
https://docs.kernel.org/driver-api/usb/usb.html

Linux snd-usb-audio source
https://github.com/torvalds/linux/tree/master/sound/usb

MPD ALSA output source
https://github.com/MusicPlayerDaemon/MPD/blob/master/src/output/plugins/AlsaOutputPlugin.cxx

PipeWire ALSA properties
https://pipewire.pages.freedesktop.org/pipewire/page_man_pipewire-props_7.html
```

---

# 233. V3 SOURCE REGISTER — PROJECT/COMMUNITY EVIDENCE

Useful only as hypothesis generators or engineering-history evidence:

```text
DeaDBeeF ALSA output-format reinitialization history
https://github.com/DeaDBeeF-Player/deadbeef

Strawberry ALSA device enumeration history
https://github.com/strawberrymusicplayer/strawberry

Arch Linux forum USB-audio crackling reports
https://bbs.archlinux.org/

Fedora Discussion USB audio reports
https://discussion.fedoraproject.org/

Reddit r/linuxaudio / r/linuxquestions recent USB-audio reports
https://www.reddit.com/r/linuxaudio/
https://www.reddit.com/r/linuxquestions/
```

No community source overrides current kernel documentation/source.

---

# 234. FINAL KERNEL/DRIVER ENGINEERING RULE

Michi must distinguish:

```text
what the application requested
what GStreamer negotiated
what ALSA opened
what snd-usb-audio decoded
what the USB/kernel environment was
what failure layer reported an error
what a controlled experiment actually reproduced
```

Only then may it say **why** playback failed.

The pioneering feature is not automatic tweaking.

It is **layer-aware, falsifiable diagnosis without corrupting playback policy**.

**END OF KERNEL / DRIVER METHOD V3**


---

# 235. V3.1 AMENDMENT — DETERMINISTIC DAC AUTO-DISCOVERY

V3.1 closes the gap between **USB arrival** and **a truthful selectable DAC model**.

The discovery path is intentionally passive.

```text
USB/udev observation
→ correlate physical USB device to ALSA card/PCM endpoints
→ collect passive identity + driver/topology evidence
→ build a declared-capability summary when passive evidence exists
→ READY_FOR_SELECTION
```

It MUST NOT become:

```text
hotplug
→ open every PCM
→ test every rate/format
→ steal the device from another application
→ call the resulting matrix "capabilities"
```

Exact PCM support remains session/qualification evidence.

This distinction is normative.

---

# 236. DISCOVERY CLAIM TAXONOMY

Every field shown by discovery MUST carry one of these meanings:

```python
from enum import Enum


class CapabilityClaimKind(Enum):
    USB_DESCRIPTOR_DECLARED = "usb_descriptor_declared"
    DRIVER_REPORTED = "driver_reported"
    ALSA_CONFIGURATION_SPACE = "alsa_configuration_space"
    EXACT_OPEN_VERIFIED = "exact_open_verified"
    ACTIVE_RUNTIME_NEGOTIATED = "active_runtime_negotiated"
    UNKNOWN = "unknown"
```

Authority order:

```text
ACTIVE_RUNTIME_NEGOTIATED
>
EXACT_OPEN_VERIFIED for the same tuple/environment
>
ALSA_CONFIGURATION_SPACE observed from an explicitly opened PCM
>
DRIVER_REPORTED
>
USB_DESCRIPTOR_DECLARED
>
UNKNOWN
```

A lower claim is never silently promoted to a higher claim.

Examples:

```text
/proc/asound/card2/stream0 says 192000
→ DRIVER_REPORTED

USB class-specific descriptor advertises 384000
→ USB_DESCRIPTOR_DECLARED

snd_pcm_hw_params_test_rate() succeeds on an opened hw PCM
→ ALSA_CONFIGURATION_SPACE

exact hw params are installed successfully
→ EXACT_OPEN_VERIFIED

/proc/asound/card2/pcm0p/sub0/hw_params during playback says 96000
→ ACTIVE_RUNTIME_NEGOTIATED
```

---

# 237. HOTPLUG MUST REMAIN PASSIVE

During arrival/enumeration, product code MUST NOT call any operation whose purpose is
proving openability of a PCM tuple.

Forbidden during passive discovery:

```text
snd_pcm_open() for qualification
snd_pcm_hw_params_any() for matrix construction
snd_pcm_hw_params_test_rate()
snd_pcm_hw_params_test_format()
snd_pcm_hw_params_test_channels()
GStreamer PLAYING/PAUSED pipeline creation solely to probe a DAC
speaker-test style playback
silent sample injection
exclusive hw reservation
```

Allowed:

```text
udev/sysfs reads
ALSA control/card metadata reads
/proc/asound diagnostic reads
sysfs ancestry correlation
cached USB descriptor reads
existing non-invasive GStreamer device-monitor observation
```

`GstDeviceMonitor` may contribute discovery observations, but it MUST NOT be treated as
a substitute for exact ALSA tuple qualification.

---

# 238. DOMAIN — DISCOVERY STATE MACHINE

Create:

```text
src/michi/domain/dac_discovery.py
```

Reference implementation:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DiscoveryPhase(Enum):
    USB_OBSERVED = "usb_observed"
    WAITING_FOR_ALSA = "waiting_for_alsa"
    ALSA_CORRELATED = "alsa_correlated"
    READY_FOR_SELECTION = "ready_for_selection"
    REMOVED = "removed"
    FAILED = "failed"


class DiscoveryFailureKind(Enum):
    NONE = "none"
    CORRELATION_TIMEOUT = "correlation_timeout"
    AMBIGUOUS_TOPOLOGY = "ambiguous_topology"
    MALFORMED_OBSERVATION = "malformed_observation"
    INTERNAL = "internal"


@dataclass(frozen=True)
class DiscoveryGeneration:
    stable_device_id: str
    generation: int

    def __post_init__(self) -> None:
        if not self.stable_device_id:
            raise ValueError("stable_device_id must not be empty")
        if self.generation < 1:
            raise ValueError("generation must be >= 1")


@dataclass(frozen=True)
class DiscoveryState:
    key: DiscoveryGeneration
    phase: DiscoveryPhase
    failure: DiscoveryFailureKind = DiscoveryFailureKind.NONE
    detail: str | None = None
    endpoint_count: int = 0

    @property
    def selectable(self) -> bool:
        return self.phase is DiscoveryPhase.READY_FOR_SELECTION


_ALLOWED = {
    DiscoveryPhase.USB_OBSERVED: {
        DiscoveryPhase.WAITING_FOR_ALSA,
        DiscoveryPhase.ALSA_CORRELATED,
        DiscoveryPhase.REMOVED,
        DiscoveryPhase.FAILED,
    },
    DiscoveryPhase.WAITING_FOR_ALSA: {
        DiscoveryPhase.ALSA_CORRELATED,
        DiscoveryPhase.REMOVED,
        DiscoveryPhase.FAILED,
    },
    DiscoveryPhase.ALSA_CORRELATED: {
        DiscoveryPhase.READY_FOR_SELECTION,
        DiscoveryPhase.REMOVED,
        DiscoveryPhase.FAILED,
    },
    DiscoveryPhase.READY_FOR_SELECTION: {
        DiscoveryPhase.REMOVED,
    },
    DiscoveryPhase.REMOVED: set(),
    DiscoveryPhase.FAILED: {
        DiscoveryPhase.REMOVED,
    },
}


def transition(current: DiscoveryState, target: DiscoveryState) -> DiscoveryState:
    if current.key != target.key:
        raise ValueError("generation mismatch")
    if target.phase not in _ALLOWED[current.phase]:
        raise ValueError(
            f"illegal discovery transition {current.phase.value} -> {target.phase.value}"
        )
    return target
```

The phase name `READY_FOR_SELECTION` means only:

```text
the physical identity is usable,
at least one current playback endpoint is correlated,
and the UI may allow the user to select it.
```

It does NOT mean:

```text
all advertised sample rates were tested
exclusive open will succeed
bit-perfect is proven
the device is currently idle
```

---

# 239. DOMAIN — PHYSICAL USB IDENTITY VS CURRENT ALSA BINDING

The persistent physical device and the current ALSA endpoint are separate objects.

Create/update:

```text
src/michi/domain/audio_device.py
```

Reference model:

```python
from dataclasses import dataclass
from enum import Enum


class SerialTrust(Enum):
    TRUSTED_UNIQUE = "trusted_unique"
    PRESENT_UNPROVEN = "present_unproven"
    GENERIC_OR_DUPLICATED = "generic_or_duplicated"
    MISSING = "missing"


@dataclass(frozen=True)
class UsbPhysicalIdentity:
    stable_device_id: str
    vendor_id: str
    product_id: str
    serial_hash: str | None
    serial_trust: SerialTrust
    product: str | None
    manufacturer: str | None
    physical_path: str | None


@dataclass(frozen=True)
class AlsaPlaybackEndpoint:
    card_id: str
    card_index: int
    pcm_device: int
    pcm_subdevice: int
    hw_locator: str
    sysfs_pcm_path: str
    usb_sysfs_root: str
    generation: int

    def __post_init__(self) -> None:
        if self.card_index < 0:
            raise ValueError("card_index must be >= 0")
        if self.pcm_device < 0 or self.pcm_subdevice < 0:
            raise ValueError("PCM device/subdevice must be >= 0")
        if not self.hw_locator.startswith("hw:"):
            raise ValueError("Direct endpoint must be a hw: ALSA locator")
```

Normative relation:

```text
1 UsbPhysicalIdentity
→ 0..N current AlsaPlaybackEndpoint
```

Never model this as a mandatory one-to-one relation.

Reasons:

```text
one USB audio product may expose multiple playback PCMs
one physical DAC may expose PCM plus S/PDIF/alternate functions
composite USB products may expose several audio interfaces
ALSA card index may change after reconnect/reboot
```

---

# 240. SERIAL TRUST POLICY

A non-empty USB serial is evidence, not automatic proof of uniqueness.

Canonical preprocessing:

```python
import hashlib
import re

_GENERIC_SERIALS = {
    "0",
    "00",
    "00000000",
    "000000000000",
    "12345678",
    "serial",
    "default",
    "unknown",
    "none",
    "n/a",
}


def normalize_usb_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.replace("\x00", " ").split()).strip()
    return value or None


def serial_looks_generic(serial: str | None) -> bool:
    s = normalize_usb_string(serial)
    if s is None:
        return True
    folded = re.sub(r"[^a-z0-9]", "", s.casefold())
    if folded in {re.sub(r"[^a-z0-9]", "", x) for x in _GENERIC_SERIALS}:
        return True
    if len(set(folded)) <= 1 and len(folded) >= 4:
        return True
    return False


def privacy_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()
```

Rules:

```text
serial missing
→ MISSING

serial syntactically generic
→ GENERIC_OR_DUPLICATED

same VID/PID/serial observed simultaneously on >1 physical USB path
→ GENERIC_OR_DUPLICATED

otherwise present before chaos validation
→ PRESENT_UNPROVEN

only after R5/R20 evidence demonstrates stability + uniqueness
→ TRUSTED_UNIQUE
```

Raw hardware serials SHOULD NOT be embedded in telemetry/export identifiers by default.
Persist a privacy-preserving digest when a durable identifier needs serial contribution.

---

# 241. IDENTITY CONSTRUCTION V3.1

Create:

```text
src/michi/application/dac_identity_policy.py
```

Reference algorithm:

```python
from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class IdentityInput:
    vid: str
    pid: str
    serial: str | None
    physical_path: str | None
    session_instance_key: str
    serial_is_unique: bool
    serial_is_generic: bool

    def __post_init__(self) -> None:
        if not self.session_instance_key:
            raise ValueError("session_instance_key must not be empty")


def _digest(*parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8", "surrogatepass")
    return hashlib.sha256(payload).hexdigest()[:24]


def build_stable_device_id(item: IdentityInput) -> tuple[str, str]:
    vid = item.vid.casefold().zfill(4)
    pid = item.pid.casefold().zfill(4)

    if item.serial and item.serial_is_unique and not item.serial_is_generic:
        return (f"usb:{vid}:{pid}:serial:{_digest(item.serial)}", "high")

    if item.physical_path:
        return (
            f"usb:{vid}:{pid}:path:{_digest(item.physical_path)}",
            "medium",
        )

    # No durable discriminator exists. Keep the identity distinct only for the
    # current process/session; never pretend VID/PID alone is a durable identity.
    return (
        f"usb:{vid}:{pid}:session:{_digest(item.session_instance_key)}",
        "ambiguous",
    )
```

The session fallback is intentionally non-durable. It prevents simultaneous devices from
collapsing when neither a trustworthy serial nor a host physical path is available.

`session_instance_key` MUST be derived from a current-session observation that distinguishes
the two live instances (for example the resolved USB sysfs root plus the registry generation),
not from VID/PID alone.

Persistent preferences MUST NOT be auto-applied to an `ambiguous` identity.

---

# 242. SYSFS ANCESTRY IS THE CORRELATION BACKBONE

Do not correlate using display names.

Do not correlate using:

```text
"USB Audio" string equality
ALSA shortname equality
manufacturer text equality
card index persistence
VID/PID alone
GStreamer display-name equality
```

Preferred correlation:

```text
/sys/class/sound/cardN/device
→ resolve realpath / walk parents
→ find USB interface/device ancestor
→ identify the physical USB root
→ group all pcmCxDyp descendants whose card resolves to the same USB root
```

Create:

```text
src/michi/infrastructure/audio_devices/alsa_sysfs_correlator.py
```

Reference core:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CorrelatedCard:
    card_index: int
    card_sysfs_path: str
    usb_device_root: str


def _parents_including_self(path: Path):
    current = path.resolve()
    yield current
    yield from current.parents


def find_usb_device_root(card_device_link: Path) -> Path | None:
    for candidate in _parents_including_self(card_device_link):
        # A physical USB device node exposes idVendor + idProduct.
        if (candidate / "idVendor").is_file() and (candidate / "idProduct").is_file():
            return candidate
    return None


def correlate_card(card_index: int, sys_class_sound: Path = Path("/sys/class/sound")):
    device = sys_class_sound / f"card{card_index}" / "device"
    if not device.exists():
        return None
    usb_root = find_usb_device_root(device)
    if usb_root is None:
        return None
    return CorrelatedCard(
        card_index=card_index,
        card_sysfs_path=str(device.resolve()),
        usb_device_root=str(usb_root.resolve()),
    )
```

The existence test above is reference logic, not permission to assume every target distro
exposes an identical tree. KDR/R11 must retain raw evidence when topology differs.

---

# 243. ALSA CARD ID IS A BINDING ATTRIBUTE, NOT DEVICE IDENTITY

ALSA control metadata exposes card index, card ID, driver, name and longname.
These values are useful for current binding and diagnostics.

Rules:

```text
snd_ctl_card_info_get_card()
→ current runtime index only

snd_ctl_card_info_get_id()
→ useful current ALSA locator component

snd_ctl_card_info_get_longname()
→ diagnostic/display evidence

snd_ctl_card_info_get_driver()
→ driver evidence
```

None is sufficient by itself to define the persistent physical DAC identity.

When constructing a Direct locator, prefer the current correlated ALSA card ID when it is
valid in the running system:

```text
hw:CARD=<current-card-id>,DEV=<pcm-device>
```

The binding MUST be generation-checked against sysfs immediately before session start.

---

# 244. NAME HINTS ARE NOT PHYSICAL TRUTH

`snd_device_name_hint()` may return configured logical devices and user-defined hints.
Therefore:

```text
ALSA hint NAME/DESC/IOID
→ discovery convenience / display candidate
→ never canonical USB identity
→ never proof that the target is a raw hardware PCM
```

Direct mode MUST reject locators whose resolved path is a conversion/plugin graph when the
profile requires `hw:` semantics.

Examples that MUST NOT be silently treated as raw hardware:

```text
default
plughw:...
dmix:...
pulse
pipewire
custom user PCM aliases with conversion
```

---

# 245. PASSIVE CAPABILITY SUMMARY

Create:

```text
src/michi/domain/dac_capability_evidence.py
```

Reference model:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceAuthority(Enum):
    PASSIVE_DESCRIPTOR = 10
    PASSIVE_DRIVER = 20
    OPEN_CONFIGURATION_SPACE = 30
    EXACT_OPEN = 40
    ACTIVE_RUNTIME = 50


@dataclass(frozen=True)
class PcmTuple:
    format_name: str
    rate_hz: int
    channels: int
    significant_bits: int | None = None


@dataclass(frozen=True)
class CapabilityEvidence:
    pcm: PcmTuple
    authority: EvidenceAuthority
    source: str
    generation: int
    environment_fingerprint: str | None = None


@dataclass(frozen=True)
class CapabilitySummary:
    advertised_rates_hz: tuple[int, ...]
    advertised_formats: tuple[str, ...]
    advertised_channels: tuple[int, ...]
    verified_tuples: tuple[PcmTuple, ...]
    runtime_tuple: PcmTuple | None

    @property
    def has_verified_support(self) -> bool:
        return bool(self.verified_tuples) or self.runtime_tuple is not None
```

UI wording must preserve the distinction:

```text
"Driver reports: 44.1–192 kHz"
not
"Supports: 44.1–192 kHz"

"Verified on this system: 96 kHz / 24-bit / 2 ch"
only after exact-open/runtime evidence.
```

---

# 246. CONTAINER BITS != SIGNIFICANT BITS

This is a Stable correctness rule.

Do NOT infer:

```text
S32_LE == 32 significant bits
S24_32LE == 24 significant bits without evidence
USB subslot size == effective sample resolution in every software layer
```

ALSA exposes sample resolution through `snd_pcm_hw_params_get_sbits()` once a concrete
configuration exists.

Represent both:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class SampleRepresentation:
    alsa_format: str
    container_bits: int
    significant_bits: int | None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.container_bits <= 0:
            errors.append("container_bits must be > 0")
        if self.significant_bits is not None:
            if self.significant_bits <= 0:
                errors.append("significant_bits must be > 0")
            if self.significant_bits > self.container_bits:
                errors.append("significant_bits cannot exceed container_bits")
        return tuple(errors)
```

For UI and logs:

```text
S32_LE container + sbits=24
→ "24 significant bits in 32-bit container"
```

Never market that as native 32-bit DAC resolution.

---

# 247. MULTI-ENDPOINT DAC TOPOLOGY

Create:

```text
src/michi/domain/dac_topology.py
```

```python
from dataclasses import dataclass
from enum import Enum


class StreamDirection(Enum):
    PLAYBACK = "playback"
    CAPTURE = "capture"


@dataclass(frozen=True)
class AudioEndpoint:
    endpoint_id: str
    direction: StreamDirection
    card_id: str
    pcm_device: int
    pcm_subdevice: int
    label: str | None


@dataclass(frozen=True)
class DacTopology:
    stable_device_id: str
    generation: int
    endpoints: tuple[AudioEndpoint, ...]

    @property
    def playback(self) -> tuple[AudioEndpoint, ...]:
        return tuple(
            item for item in self.endpoints
            if item.direction is StreamDirection.PLAYBACK
        )
```

Selection UX:

```text
one playback endpoint
→ select DAC directly

multiple playback endpoints
→ select DAC + endpoint
→ remember endpoint intent by stable endpoint signature
→ never guess between semantically distinct outputs
```

Endpoint signature MUST NOT depend solely on `cardN`.

---

# 248. GENERATION TOKENS — HOTPLUG RACE KILL SWITCH

Every asynchronous discovery action MUST carry:

```text
stable_device_id
generation
```

On physical removal:

```text
mark generation REMOVED immediately
cancel or logically invalidate outstanding discovery jobs
remove current ALSA bindings
preserve durable user intent separately
```

On reconnect:

```text
same physical identity MAY be recognized
new generation = previous generation + 1
all old callbacks become stale
```

Reference guard:

```python
from dataclasses import dataclass


@dataclass
class GenerationGuard:
    current: dict[str, int]

    def is_current(self, stable_device_id: str, generation: int) -> bool:
        return self.current.get(stable_device_id) == generation

    def require_current(self, stable_device_id: str, generation: int) -> None:
        if not self.is_current(stable_device_id, generation):
            raise RuntimeError("stale DAC discovery callback")
```

No stale callback may recreate a removed binding.

---

# 249. EVENT CONVERGENCE WITHOUT GLOBAL `udevadm settle`

Discovery must tolerate event ordering such as:

```text
USB device add
USB interface add
sound card add
PCM nodes add
GStreamer provider add
```

Do not block the whole application waiting for global udev quiescence.

Use per-device convergence:

```text
on relevant event
→ re-evaluate only that physical USB root
→ if USB exists but no ALSA playback endpoint yet:
   WAITING_FOR_ALSA
→ schedule bounded retry
→ any related sound event triggers immediate re-evaluation
→ generation token invalidates stale retries
```

Reference retry plan:

```python
RETRY_DELAYS_MS = (0, 50, 100, 200, 400, 800)
```

This sequence is a product default hypothesis, not a hardware truth.
R19 must validate or tune it.

A timeout means:

```text
USB audio device observed but ALSA binding did not converge in the allowed window
```

It does NOT mean:

```text
device unsupported
broken DAC
bad cable
kernel bug
```

---

# 250. CACHE INVALIDATION CONTRACT

Persisted capability evidence is never valid merely because `stable_device_id` matches.

Create:

```text
src/michi/domain/dac_evidence_context.py
```

```python
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class EvidenceContext:
    descriptors_sha256: str | None
    bcd_device: str | None
    kernel_release: str
    snd_usb_audio_driver_fingerprint: str | None
    alsa_lib_version: str | None
    gstreamer_version: str | None

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.__dict__, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
```

Invalidation rules:

```text
new physical generation
→ current binding cache invalid

USB descriptor hash changed
→ passive capability cache invalid
→ exact-open qualification invalid

kernel release / snd-usb-audio fingerprint changed
→ driver-derived qualification becomes STALE until reconfirmed

ALSA/GStreamer version changed
→ user-space negotiation evidence becomes STALE until reconfirmed
```

Historical results may remain visible as historical evidence.
They MUST NOT be silently presented as current proof.

---

# 251. USB DESCRIPTOR HASHING IS PASSIVE EVIDENCE

Linux exposes cached USB descriptors through sysfs.

Use them only for:

```text
change detection
context fingerprinting
lab parsing when explicitly enabled
```

Stable does NOT require a universal UAC descriptor parser.
That would violate the bounded scope declared at the start of this specification.

Reference reader:

```python
from pathlib import Path
import hashlib


def hash_cached_usb_descriptors(usb_root: Path) -> str | None:
    path = usb_root / "descriptors"
    try:
        data = path.read_bytes()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    return hashlib.sha256(data).hexdigest()
```

Do not trust descriptor length arithmetic implemented ad hoc in product code.
If raw UAC parsing is later promoted, it receives its own fuzzed parser boundary and ADR.

---

# 252. DRIVER WITNESS MAY ENRICH DISCOVERY — NEVER BLOCK IT

`/proc/asound/card*/stream*` is documented as a useful USB-audio debugging witness.
It may expose assignments/current status and driver-decoded alternate-setting information.

V3.1 use:

```text
if parse succeeds
→ add DRIVER_REPORTED evidence

if file absent
→ continue discovery

if grammar unknown
→ preserve raw diagnostic reference
→ mark passive capabilities unknown
→ READY_FOR_SELECTION may still be reached
```

Parser success MUST NOT be a prerequisite for playback.

---

# 253. DISCOVERY COORDINATOR

Create:

```text
src/michi/application/dac_discovery_coordinator.py
```

Reference orchestration contract:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DiscoveryBackend(Protocol):
    def physical_usb_snapshot(self, usb_root: str): ...
    def playback_endpoints_for_usb_root(self, usb_root: str): ...
    def passive_driver_witness(self, endpoint): ...


@dataclass
class DacDiscoveryCoordinator:
    backend: DiscoveryBackend
    registry: object
    scheduler: object

    def on_usb_add(self, usb_root: str) -> None:
        identity = self.registry.observe_usb(
            self.backend.physical_usb_snapshot(usb_root)
        )
        generation = self.registry.begin_generation(identity.stable_device_id)
        self._converge(usb_root, identity.stable_device_id, generation, attempt=0)

    def on_related_sound_event(self, usb_root: str) -> None:
        current = self.registry.current_generation_for_usb_root(usb_root)
        if current is None:
            return
        stable_device_id, generation = current
        self._converge(usb_root, stable_device_id, generation, attempt=0)

    def on_usb_remove(self, usb_root: str) -> None:
        current = self.registry.current_generation_for_usb_root(usb_root)
        if current is None:
            return
        stable_device_id, generation = current
        self.registry.mark_removed(stable_device_id, generation)

    def _converge(
        self,
        usb_root: str,
        stable_device_id: str,
        generation: int,
        attempt: int,
    ) -> None:
        if not self.registry.is_generation_current(stable_device_id, generation):
            return

        endpoints = tuple(self.backend.playback_endpoints_for_usb_root(usb_root))
        if endpoints:
            self.registry.bind_endpoints(
                stable_device_id,
                generation,
                endpoints,
            )
            self.registry.mark_ready_for_selection(stable_device_id, generation)
            return

        delays = (0, 50, 100, 200, 400, 800)
        next_attempt = attempt + 1
        if next_attempt >= len(delays):
            self.registry.mark_correlation_timeout(stable_device_id, generation)
            return

        self.registry.mark_waiting_for_alsa(stable_device_id, generation)
        self.scheduler.call_later_ms(
            delays[next_attempt],
            lambda: self._converge(
                usb_root,
                stable_device_id,
                generation,
                next_attempt,
            ),
        )
```

Implementation note:

```text
The real coordinator must not capture strong references that prevent teardown.
Qt/PySide integration must marshal registry/UI mutations onto the owning thread.
```

---

# 254. PRE-SESSION REBIND CHECK

Between selection and playback, a USB DAC can disappear and another card can take the old
numeric index.

Therefore `AudioOutputSession` MUST validate:

```text
selected stable_device_id
selected generation
selected endpoint signature
current sysfs USB root
current ALSA card ID/device
```

before creating the Direct GStreamer pipeline.

If any binding changed:

```text
abort current start attempt
re-resolve through AudioDeviceRegistry
never reuse the stale hw locator blindly
```

This is a correctness/safety boundary, not merely a UI refresh.

---

# 255. UI CONTRACT — DEVICE DETAILS WITHOUT FALSE CERTAINTY

The DAC selector may show:

```text
Manufacturer
Product
Connection: USB
Current ALSA endpoint
Driver: snd-usb-audio
USB link speed
Passive driver-reported rates/formats when available
Last verified exact tuples
Current runtime tuple when playing
```

Status vocabulary:

```text
Detected
Initializing audio interface…
Ready
Ready — limited capability details
Disconnected
Needs re-verification
```

Forbidden labels unless supported by matching evidence:

```text
"Fully supported"
"Bit-perfect"
"Native 32-bit"
"384 kHz supported"
"Exclusive ready"
```

A capability row SHOULD expose provenance in advanced details:

```text
192 kHz — driver reported
96 kHz / S32_LE / sbits 24 — verified exact open
96 kHz / S32_LE / sbits 24 — active now
```

---

# 256. UNIT TESTS — DISCOVERY STATE MACHINE

Create:

```text
tests/unit/domain/test_dac_discovery.py
```

```python
import pytest

from michi.domain.dac_discovery import (
    DiscoveryFailureKind,
    DiscoveryGeneration,
    DiscoveryPhase,
    DiscoveryState,
    transition,
)


def state(phase, generation=1):
    return DiscoveryState(
        DiscoveryGeneration("usb:1234:5678:test", generation),
        phase,
    )


def test_ready_requires_correlation_path():
    with pytest.raises(ValueError):
        transition(
            state(DiscoveryPhase.USB_OBSERVED),
            state(DiscoveryPhase.READY_FOR_SELECTION),
        )


def test_correlated_can_become_selectable():
    result = transition(
        state(DiscoveryPhase.ALSA_CORRELATED),
        state(DiscoveryPhase.READY_FOR_SELECTION),
    )
    assert result.selectable


def test_generation_mismatch_rejected():
    with pytest.raises(ValueError):
        transition(
            state(DiscoveryPhase.WAITING_FOR_ALSA, 1),
            state(DiscoveryPhase.ALSA_CORRELATED, 2),
        )


def test_removed_is_terminal():
    with pytest.raises(ValueError):
        transition(
            state(DiscoveryPhase.REMOVED),
            state(DiscoveryPhase.READY_FOR_SELECTION),
        )
```

---

# 257. UNIT TESTS — SAMPLE RESOLUTION

Create:

```text
tests/unit/domain/test_sample_representation.py
```

```python
from michi.domain.sample_representation import SampleRepresentation


def test_24_significant_bits_in_32_container_is_valid():
    item = SampleRepresentation("S32_LE", 32, 24)
    assert item.validate() == ()


def test_significant_bits_cannot_exceed_container():
    item = SampleRepresentation("S24_LE", 24, 32)
    assert item.validate()


def test_unknown_significant_bits_is_not_invented():
    item = SampleRepresentation("S32_LE", 32, None)
    assert item.validate() == ()
    assert item.significant_bits is None
```

---

# 258. UNIT TESTS — IDENTITY POLICY

Create:

```text
tests/unit/application/test_dac_identity_policy.py
```

```python
from michi.application.dac_identity_policy import (
    IdentityInput,
    build_stable_device_id,
)


def test_unique_serial_has_high_confidence_and_ignores_port_move():
    a = IdentityInput("1234", "5678", "ABC", "pci-1/usb1/1-2", "usb-root-a", True, False)
    b = IdentityInput("1234", "5678", "ABC", "pci-1/usb1/1-3", "usb-root-b", True, False)
    assert build_stable_device_id(a)[0] == build_stable_device_id(b)[0]
    assert build_stable_device_id(a)[1] == "high"


def test_generic_serial_falls_back_to_path():
    item = IdentityInput("1234", "5678", "00000000", "usb-1-2", "usb-root-a", False, True)
    stable_id, confidence = build_stable_device_id(item)
    assert ":path:" in stable_id
    assert confidence == "medium"


def test_no_serial_and_no_path_is_session_scoped_ambiguous():
    a = IdentityInput("1234", "5678", None, None, "usb-root-a", False, False)
    b = IdentityInput("1234", "5678", None, None, "usb-root-b", False, False)
    a_id, a_confidence = build_stable_device_id(a)
    b_id, b_confidence = build_stable_device_id(b)
    assert a_id != b_id
    assert ":session:" in a_id
    assert a_confidence == b_confidence == "ambiguous"
```

---

# 259. UNIT TESTS — STALE CALLBACK REJECTION

Create:

```text
tests/unit/application/test_generation_guard.py
```

```python
import pytest

from michi.application.generation_guard import GenerationGuard


def test_old_generation_is_rejected_after_reconnect():
    guard = GenerationGuard({"dac": 2})
    assert not guard.is_current("dac", 1)
    assert guard.is_current("dac", 2)

    with pytest.raises(RuntimeError):
        guard.require_current("dac", 1)
```

---

# 260. INTEGRATION TEST — SYSFS CORRELATION FIXTURE

Create a deterministic fake sysfs tree in a temporary directory.

Test at minimum:

```text
one USB DAC → one ALSA card → one playback PCM
one USB DAC → one ALSA card → two playback PCMs
USB composite device whose device-level class is not Audio
reconnect where card2 becomes card5
identical VID/PID on two physical USB paths
no-serial device
symlink path normalization
sound card with no USB ancestor → excluded from USB DAC registry
```

Acceptance:

```text
correlation uses ancestry
not names
not card index persistence
not device-level USB class alone
```

---

# 261. R19 — ENUMERATION CONVERGENCE / HOTPLUG RACE

```yaml
schema_version: 1
experiment_id: R19_ENUMERATION_CONVERGENCE
status: required_before_auto_discovery_promotion

question: >
  Does per-device event convergence reach a truthful READY_FOR_SELECTION state across
  reconnect, boot, suspend/resume and hub scenarios without global udev blocking?

scenarios:
  - cold_boot_dac_connected
  - hotplug_direct_port
  - hotplug_hub
  - rapid_unplug_replug_same_port
  - unplug_during_waiting_for_alsa
  - suspend_resume
  - card_index_changes

capture:
  - monotonic_event_timeline
  - udev_usb_events
  - sound_subsystem_events
  - sysfs_ancestry_snapshots
  - generation_transitions
  - time_to_ready_ms

falsifiers:
  - stale_generation_becomes_ready
  - removed_endpoint_reappears_from_delayed_callback
  - global_ui_thread_block
  - persistent_failure_from_normal_event_reordering

safe_retreat: require_manual_refresh_without_active_pcm_probe
```

---

# 262. R20 — DUPLICATE SERIAL / IDENTICAL DEVICE COLLISION

```yaml
schema_version: 1
experiment_id: R20_IDENTICAL_DAC_COLLISION
status: required_before_serial_policy_promotion

question: >
  Can two physically distinct DACs with the same VID/PID and missing, generic, or
  duplicated serial remain separate without applying the wrong device preferences?

cases:
  - same_vid_pid_unique_serials
  - same_vid_pid_no_serial
  - same_vid_pid_same_generic_serial
  - same_vid_pid_same_serial_if_hardware_allows
  - port_swap
  - hub_port_swap

pass:
  - simultaneous_devices_never_merge
  - ambiguous_identity_is_exposed
  - preferences_not_auto_applied_to_ambiguous_peer

falsifiers:
  - collision_merges_devices
  - one_device_inherits_other_device_profile

safe_retreat: session_scoped_identity_only
```

---

# 263. R21 — PASSIVE CLAIM VS EXACT OPEN CONSISTENCY

```yaml
schema_version: 1
experiment_id: R21_PASSIVE_VS_EXACT_OPEN
status: required_before_capability_ui_promotion

question: >
  How often do passive driver-reported tuples agree with exact ALSA hw-open results on
  tested DACs and kernels?

method:
  - collect_passive_driver_witness_first
  - do_not_open_pcm_during_discovery
  - later_run_explicit_qualification
  - compare_same_generation_same_environment

compare:
  - format
  - rate
  - channels
  - significant_bits_when_available

result_policy:
  - passive_match_does_not_promote_to_exact_open
  - contradiction_preserves_both_sources
  - current_runtime_wins_for_current_session_truth

falsifiers:
  - ui_labels_driver_report_as_verified
  - passive_only_tuple_is_used_as_exclusive_support_guarantee
```

---

# 264. R22 — SIGNIFICANT-BIT DEPTH CONSISTENCY

```yaml
schema_version: 1
experiment_id: R22_SIGNIFICANT_BITS
status: required_before_bit_depth_marketing_claims

question: >
  For common USB DAC formats, what relationship is observed between GStreamer format,
  ALSA format container, ALSA sbits and snd-usb-audio driver witness?

cases:
  - S16_LE
  - S24_LE_when_available
  - S24_3LE_when_available
  - S24_32LE_or_equivalent_when_available
  - S32_LE_with_24_sbits
  - S32_LE_with_32_sbits_if_real_hardware_exists

pass:
  - container_and_significant_bits_are_reported_separately
  - unknown_sbits_remains_unknown

falsifiers:
  - S32_LE_automatically_displayed_as_32_bit_precision
```

---

# 265. R23 — MULTI-ENDPOINT / COMPOSITE USB AUDIO

```yaml
schema_version: 1
experiment_id: R23_MULTI_ENDPOINT_TOPOLOGY
status: required_before_general_usb_dac_claim

question: >
  Can Michi represent one physical USB identity with multiple ALSA playback endpoints
  without collapsing them or inventing semantic labels?

cases:
  - one_playback_pcm
  - two_playback_pcms_same_card
  - playback_and_capture
  - composite_usb_device
  - pcm_numbers_change_after_reconnect

pass:
  - physical_identity_remains_one
  - endpoint_count_is_truthful
  - endpoint_selection_is_explicit_when_ambiguous

safe_retreat: expose_raw_endpoint_labels_and_require_user_selection
```

---

# 266. OPENCODE EXECUTION SLICE — DISC-001 PASSIVE IDENTITY

```text
OBJECTIVE
Build the USB physical identity without opening PCM devices.

CREATE
src/michi/application/dac_identity_policy.py
src/michi/infrastructure/audio_devices/sysfs_usb_identity.py

UPDATE
src/michi/domain/audio_device.py
src/michi/application/audio_device_registry.py

MUST
normalize strings
hash serial contribution for persistent ID
track serial trust
preserve physical USB path separately
handle duplicate/generic serial ambiguity

MUST NOT
use card index as identity
use display name as identity
open PCM
```

---

# 267. OPENCODE EXECUTION SLICE — DISC-002 USB↔ALSA CORRELATION

```text
OBJECTIVE
Resolve current playback endpoints by sysfs ancestry.

CREATE
src/michi/infrastructure/audio_devices/alsa_sysfs_correlator.py
src/michi/domain/dac_topology.py

MUST
support one physical device to many endpoints
exclude sound cards with no matching USB ancestry from the USB DAC registry
carry generation on every endpoint
construct hw: locators only from current correlation

MUST NOT
match by name equality
assume cardN stability
assume bDeviceClass=Audio for composite devices
```

---

# 268. OPENCODE EXECUTION SLICE — DISC-003 DISCOVERY COORDINATOR

```text
OBJECTIVE
Converge asynchronous USB/sound events into READY_FOR_SELECTION.

CREATE
src/michi/domain/dac_discovery.py
src/michi/application/dac_discovery_coordinator.py
src/michi/application/generation_guard.py

MUST
be event-driven
use bounded per-device retry
reject stale generation callbacks
make removal terminal for that generation
remain non-blocking for QML/UI thread

MUST NOT
run udevadm settle globally
sleep on UI thread
actively probe PCM tuples
```

---

# 269. OPENCODE EXECUTION SLICE — DISC-004 PASSIVE CAPABILITY TRUTH

```text
OBJECTIVE
Expose useful capability information without converting passive observations into proof.

CREATE
src/michi/domain/dac_capability_evidence.py
src/michi/domain/sample_representation.py

UPDATE
src/michi/infrastructure/audio_devices/usb_audio_stream_proc.py
presentation DAC details model

MUST
carry source + authority
separate advertised/driver-reported from exact-open/runtime
separate container bits from significant bits
allow capability summary to be empty/unknown

MUST NOT
block READY_FOR_SELECTION when passive parser is unavailable
say "supported" when only passive evidence exists
```

---

# 270. OPENCODE EXECUTION SLICE — DISC-005 EVIDENCE INVALIDATION

```text
OBJECTIVE
Prevent stale qualifications from being treated as current truth.

CREATE
src/michi/domain/dac_evidence_context.py

UPDATE
qualification persistence
AudioDeviceRegistry
AudioOutputSession

MUST
fingerprint USB descriptors and relevant software/kernel context
mark mismatched evidence STALE
rebind immediately before playback
retain historical evidence without promoting it

MUST NOT
reuse old exact-open result after descriptor/context change as current proof
```

---

# 271. V3.1 REQUIRED GATES

Before auto-discovery is called Stable:

```text
G-DISC-01
No passive hotplug path calls snd_pcm_open for qualification.

G-DISC-02
Two simultaneous identical VID/PID devices never collapse into one registry record.

G-DISC-03
Card index change does not change physical identity.

G-DISC-04
One physical identity may own multiple playback endpoints.

G-DISC-05
Removal invalidates all callbacks from the old generation.

G-DISC-06
READY_FOR_SELECTION requires current endpoint correlation but not exact-open proof.

G-DISC-07
Driver-reported capability is never rendered as verified support.

G-DISC-08
S32_LE never implies 32 significant bits.

G-DISC-09
Cached qualification is stale when evidence context fingerprint changes.

G-DISC-10
Direct session revalidates endpoint→USB ancestry immediately before use.
```

Any failure is **NO-GO** for Stable DAC auto-discovery.

---

# 272. V3.1 SOURCE REGISTER — AUTO-DISCOVERY / CAPABILITY TRUTH

Primary sources:

```text
GStreamer GstDeviceMonitor
https://gstreamer.freedesktop.org/documentation/gstreamer/gstdevicemonitor.html

GStreamer ALSA sink
https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html

ALSA PCM hardware-parameter API
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___h_w___params.html

ALSA PCM interface / snd_pcm_set_params semantics
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m.html

ALSA name-hint interface
https://alsa-project.org/alsa-doc/alsa-lib/group___hint.html

ALSA control/card metadata
https://www.alsa-project.org/alsa-doc/alsa-lib/group___control.html

Linux ALSA proc files — USB audio stream witness
https://www.kernel.org/doc/html/latest/sound/designs/procfile.html

Linux stable USB sysfs ABI
https://www.kernel.org/doc/html/latest/admin-guide/abi-stable-files.html

Linux testing USB sysfs ABI — descriptor/device attributes
https://www.kernel.org/doc/html/next/admin-guide/abi-testing-files.html
```

Interpretation rules:

```text
Upstream API documentation establishes API semantics.
It does not prove one DAC behaves correctly.

Kernel diagnostic files establish available evidence surfaces.
They do not become product identity truth automatically.

ALSA test_* functions establish configuration-space queries only after a PCM is opened.
They therefore belong to qualification, not passive hotplug.
```

---

# 273. V3.1 ENGINEERING VERDICT

V3 already had the correct principle:

```text
identify → plan → execute → observe → refuse silent degradation
```

V3.1 makes the first verb implementable without speculation:

```text
observe physical USB identity
→ correlate current ALSA topology by ancestry
→ assign a generation
→ attach passive, provenance-labelled evidence
→ expose the device as selectable
→ qualify exact tuples only when qualification/playback requires it
→ revalidate binding before execution
```

The Stable product must be comfortable saying:

```text
"DAC detected; detailed capabilities not yet verified."
```

That is more correct than inventing certainty from descriptor strings, GStreamer device
caps, ALSA hints, or a stale qualification cache.

**END OF V3.1 AUTO-DISCOVERY AMENDMENT**

---

# 274. V3.1 REFERENCE VALIDATION STATUS

A separate executable V3.1 amendment harness was built directly from the new reference
contracts and executed after the identity/session-collision correction.

Result:

```text
11 passed
0 failed
```

Covered:

```text
discovery state transition legality
READY_FOR_SELECTION cannot be skipped to directly from USB_OBSERVED
generation mismatch rejection
REMOVED generation terminality
unique-serial identity across port move
generic-serial physical-path fallback
no-serial/no-path session-scoped collision separation
24 significant bits inside a 32-bit container
unknown significant bits remain unknown
invalid significant-bits > container rejection
stale-generation callback rejection
```

This is additive to the inherited V3 reference-pack status recorded in section 231.
It does not promote any physical-hardware claim.

Required next evidence remains:

```text
R19 enumeration convergence on Linux
R20 two-device collision hardware lab
R21 passive-vs-exact-open comparison
R22 significant-bit evidence on real DACs
R23 composite/multi-endpoint hardware coverage
```

**V3.1 DOCUMENT INTEGRITY CHECK**

```text
Markdown fences: balanced
V3.1 Python reference blocks parsed: 18/18
Python syntax errors: 0
V3.1 H1 duplicates: 0
DISC Stable gates: 10
V3.1 amendment reference tests: 11/11 passed
```

---

# 275. V3.2 — PREMIUM DAC INTEGRATION / ROON-CLASS QUALITY AMENDMENT

**Status:** CANONICAL ADDITIVE AUTHORITY OVER V3.1  
**Goal:** make Michi DAC integration product-grade, transparent, safe, measurable, and competitive with the quality of integration users expect from Roon-class systems, while remaining a Michi-native architecture.  
**Scope:** Linux-first USB DAC integration.  
**Non-goal:** cloning RAAT, copying Roon internals, or creating a second playback engine.

V3.2 keeps every V3/V3.1 invariant unless this amendment explicitly tightens it.

The product objective is not:

```text
"Roon compatibility"
```

It is:

```text
Roon-class integration quality
implemented with Michi-owned contracts,
Michi-owned runtime truth,
and Michi-owned validation.
```

The benchmark is the quality of the integration experience:

```text
connect
→ identify
→ configure safely
→ expose truthful capabilities
→ choose the right path
→ play source-native when possible
→ show what actually happened
→ survive transitions/reconnects
→ never hide degradation
→ retain hardware-specific knowledge without treating it as runtime truth
```

---

# 276. BENCHMARK — WHAT ROON GETS RIGHT, TRANSLATED INTO MICHI REQUIREMENTS

The benchmark must be functional, not cosmetic.

| Roon-class behavior | Michi V3.2 requirement | Michi differentiation |
|---|---|---|
| Automatic device identification | Stable physical identity + optional known-device profile | Runtime identity remains independent from profile branding |
| Recommended settings for known DACs | `MichiDacProfile` | Profile can suggest, never override contradictory current evidence |
| Exclusive/direct Linux output | ALSA `hw` Direct path | Direct is necessary, not sufficient, for integrity claims |
| Device / Fixed / DSP volume | Explicit `VolumeMode` | Hardware controls require verified ALSA control mapping + event convergence |
| Device capability limits | Runtime-probed limits + profile clamps | Current exact-open/active runtime outranks historical profile |
| DSD Native / DoP strategy | Explicit DSD transport policy | No DSD option appears as supported without evidence |
| Resync delay | Per-device measured workaround | Zero by default; never generalized by brand or VID/PID alone |
| Signal Path | `Michi Signal Truth` | Adds requested/decoded/effective/negotiated + kernel/driver evidence and contradictions |
| Product-tested devices | `Michi Verified` | Qualification seal carries environment + lab matrix hash |
| Real hardware regression | Michi DAC hardware shelf / matrix | Promotion tied to repeatable hardware evidence, not community anecdotes |
| Friendly device icon/name | Profile presentation metadata | Branding never participates in physical identity |
| Honest quality label | Evidence-derived signal verdict | `UNKNOWN` and `CONTRADICTED` are first-class outcomes |

Michi must not copy the weakest possible interpretation of these features.

Example:

```text
BAD:
"Known Topping DAC → supports 768 kHz → show 768 kHz forever"

GOOD:
profile says a model was validated historically
+ current environment fingerprint matches or differs
+ exact-open says whether this tuple works NOW
+ active runtime records what was actually negotiated
```

---

# 277. ROON IS A BENCHMARK, NOT AN IMPLEMENTATION AUTHORITY

Roon public behavior may inspire product requirements.

It may not become hidden engineering authority.

Forbidden:

```text
copy proprietary RAAT assumptions
invent undocumented Roon internals
model Michi around Roon terminology where Linux APIs differ
claim parity because the UI has equivalent switches
```

Required:

```text
public benchmark behavior
→ map to Linux/ALSA/GStreamer fact
→ derive Michi invariant
→ implement in Michi architecture
→ falsify with tests and hardware
```

---

# 278. CURRENT REPOSITORY REALITY — V3.2 MUST INTEGRATE, NOT FORK

Current `main` already has mature M11.3 playback ownership.

Relevant current files include:

```text
src/michi/application/playback_session_service.py
src/michi/application/playback_service.py
src/michi/application/audio_engine_service.py
src/michi/application/audio_engine_selection_coordinator.py
src/michi/application/audio_engine_convergence_coordinator.py
src/michi/application/audio_transport_router.py
src/michi/infrastructure/audio_engines/gstreamer.py
src/michi/infrastructure/audio_engines/mpd.py
src/michi/presentation/audio_engine_bridge.py
src/michi/presentation/qml/views/AudioEngineSettingsSection.qml
src/michi/presentation/qml/components/VolumeControl.qml

docs/M11_3_MULTI_ENGINE_AUDIO_RUNTIME.md
docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md
docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md
```

Canonical ownership remains:

```text
PlaybackSessionService
    owns WHICH track / session sequence

PlaybackService
    owns playback request / transition orchestration

AudioPort / engine adapter
    owns transport mechanics

M11.4 DAC services
    own device identity, binding, qualification, output policy and evidence
```

V3.2 MUST NOT create:

```text
DacPlaybackService that chooses tracks
DacQueue
DacAudioEngine competing with GStreamer
parallel playback state machine
parallel volume authority unaware of PlaybackService
```

---

# 279. TARGET ARCHITECTURE — MICHI PREMIUM DAC STACK

```text
┌───────────────────────────────────────────────────────────────┐
│ Presentation                                                  │
│                                                               │
│ DAC Card / Device Setup / Michi Signal Truth / Diagnostics    │
└──────────────────────────────┬────────────────────────────────┘
                               │ read models + commands
┌──────────────────────────────▼────────────────────────────────┐
│ Application                                                   │
│                                                               │
│ AudioDeviceRegistry                                           │
│ DacProfileService                                             │
│ DacQualificationService                                       │
│ AudioOutputProfileService                                     │
│ VolumePolicyService                                           │
│ OutputPlanner                                                 │
│ OutputSessionEvidenceRecorder                                 │
│ DeviceControlEventService                                     │
└───────────────┬───────────────────────────┬───────────────────┘
                │                           │
                │ policy/binding            │ evidence
┌───────────────▼────────────────┐  ┌──────▼────────────────────┐
│ Existing playback architecture │  │ Linux device infrastructure│
│                                 │  │                            │
│ PlaybackSessionService          │  │ udev/sysfs                 │
│ PlaybackService                 │  │ ALSA PCM                   │
│ AudioPort                       │  │ ALSA CTL/Mixer             │
│ GStreamerAudioPort              │  │ /proc snd-usb-audio        │
└───────────────┬────────────────┘  └────────────────────────────┘
                │
                ▼
       GStreamer strict output path
                │
                ▼
           ALSA hw:CARD,DEV
                │
                ▼
              USB DAC
```

Core invariant:

```text
DEVICE INTELLIGENCE informs playback.
It never becomes playback ownership.
```

---

# 280. MIGRATION SEAM — DO NOT REWRITE `gstreamer.py` IN ONE PR

The existing GStreamer adapter is a mature M11.3 transport implementation.

It currently uses `playbin3` and its generic volume surface.

V3.2 migration MUST be incremental.

Phase boundary:

```text
M11.3 behavior
playbin3 → default/shared sink

M11.4 Direct behavior
playbin3/controlled decode path
    → explicitly supplied strict audio sink graph
    → ALSA hw binding
    → runtime evidence observer
```

Do not replace the pump, bus-generation safety, owner-thread delivery, or existing
transport transaction semantics to implement DAC support.

Create seams around them.

Proposed additions:

```text
src/michi/domain/
    audio_device.py
    audio_capability.py
    audio_output_profile.py
    dac_profile.py
    signal_truth.py
    volume_policy.py
    output_transition.py

src/michi/application/
    audio_device_registry.py
    dac_profile_service.py
    dac_qualification_service.py
    audio_output_profile_service.py
    audio_output_planner.py
    volume_policy_service.py
    output_session_evidence_recorder.py
    device_control_event_service.py

src/michi/infrastructure/audio_devices/
    udev_observer.py
    alsa_observer.py
    alsa_probe_adapter.py
    alsa_control_adapter.py
    alsa_mixer_adapter.py
    proc_pcm_witness.py
    usb_audio_stream_proc.py

src/michi/infrastructure/audio_engines/gstreamer/
    strict_sink_builder.py
    pipeline_inspector.py
    runtime_evidence.py
    clock_evidence.py
```

Important migration note:

```text
If converting `audio_engines/gstreamer.py` into a package would create import churn,
keep the current file and place new implementation under:

src/michi/infrastructure/gstreamer_dac/

until a dedicated refactor PR proves the package migration safe.
```

OpenCode MUST NOT mechanically create a directory named `gstreamer/` beside an existing
`gstreamer.py` and leave ambiguous imports.

---

# 281. MICHI DAC PROFILE — PRODUCT KNOWLEDGE, NOT RUNTIME TRUTH

A `MichiDacProfile` is an optional knowledge package for a known DAC model/revision.

It MAY contain:

```text
presentation metadata
validated matcher
historically verified PCM tuples
historically verified DSD transports
verified ALSA hardware-volume control mapping
measured resync delay
known safe/unsafe quirks
manual/product links
lab matrix hash
profile version
```

It MUST NOT contain executable arbitrary code.

It MUST NOT silently mutate kernel module settings.

It MUST NOT override current exact-open or active runtime evidence.

Suggested schema:

```yaml
schema_version: 1
profile_id: topping.dx5.usb.v1
profile_version: 3
tier: michi_verified

match:
  usb_vid: "152a"
  usb_pid: "8750"
  product_string: "DX5"
  bcd_device:
    min: "0100"
    max: "0199"
  serial_policy: optional_unique

presentation:
  manufacturer: Topping
  product: DX5
  icon_asset: dac/topping-dx5.svg

verified:
  pcm:
    - { format: S32_LE, rate_hz: 44100, channels: 2, significant_bits: 24 }
    - { format: S32_LE, rate_hz: 48000, channels: 2, significant_bits: 24 }
    - { format: S32_LE, rate_hz: 96000, channels: 2, significant_bits: 24 }
    - { format: S32_LE, rate_hz: 192000, channels: 2, significant_bits: 24 }
  dsd:
    transports: [dop]

volume:
  mode_supported: device_hardware
  alsa_control:
    interface: MIXER
    name: PCM
    index: 0
  db_range:
    min_db_x100: -9000
    max_db_x100: 0

transition:
  resync_delay_ms: 0

qualification:
  lab_matrix_hash: sha256:...
  last_verified_kernel_family: "6.x"
  profile_evidence_id: MV-2026-...
```

The example above is schema illustration only.

No real product tuple may be marked `verified` without lab evidence.

---

# 282. PROFILE TIERS

Use exactly:

```python
class ProfileTier(Enum):
    UNKNOWN = "unknown"
    DETECTED = "detected"
    MICHI_PROFILED = "michi_profiled"
    MICHI_VERIFIED = "michi_verified"
```

Meaning:

```text
UNKNOWN
Physical output exists; no useful product match.

DETECTED
Identity is strong enough to present a stable DAC, no curated profile.

MICHI_PROFILED
Curated metadata/default knowledge exists, but full hardware seal is absent or stale.

MICHI_VERIFIED
Specified hardware/revision has passed the required Michi physical qualification matrix.
```

Never use:

```text
"Certified"
```

unless Michi has an actual manufacturer certification program with legal/product meaning.

`Michi Verified` is an engineering test seal, not a manufacturer endorsement.

---

# 283. EVIDENCE PRECEDENCE — PREMIUM INTEGRATION MUST BE HONEST

Canonical authority order:

```text
ACTIVE_RUNTIME_NEGOTIATED
    >
CURRENT_EXACT_OPEN
    >
CURRENT_DRIVER_REPORTED
    >
CURRENT_ENVIRONMENT_MATCHING_PROFILE
    >
HISTORICAL_PROFILE
    >
PASSIVE_HINT
    >
COMMUNITY_HINT
```

Equivalent code-level ordering:

```python
class EvidenceAuthority(IntEnum):
    HINT = 10
    PROFILE = 20
    DRIVER_REPORTED = 30
    EXACT_OPEN = 40
    ACTIVE_RUNTIME = 50
```

A profile contradiction is not resolved by deleting either source.

Example:

```text
Michi Verified profile:
192 kHz supported

Current ALSA exact-open:
EINVAL / unsupported

UI:
192 kHz — unavailable in current environment
Profile says verified; current ALSA qualification contradicts profile.
Advanced diagnostics → show evidence.
```

Never:

```text
retry forever
silently fall back to 96 kHz
silently route to PipeWire
hide the contradiction
```

---

# 284. ENVIRONMENT FINGERPRINT — VERIFIED DOES NOT MEAN ETERNAL

Qualification context MUST include at least:

```text
stable_device_id
USB VID/PID
bcdDevice
USB descriptor hash
kernel release
snd-usb-audio module version/identity when available
ALSA library version
GStreamer version
binding topology fingerprint
profile version
```

Recommended fingerprint:

```python
sha256(canonical_json(relevant_fields))
```

Changing the fingerprint does not mean the DAC stopped working.

It means:

```text
historical evidence != current evidence
```

UI distinction:

```text
Michi Verified        = current context satisfies seal policy
Previously Verified   = historical hardware evidence exists, current context needs revalidation
Profiled              = curated knowledge, no current verified seal
Detected              = runtime discovery only
```

---

# 285. VOLUME ARCHITECTURE — THREE MODES, THREE DIFFERENT SIGNAL SEMANTICS

Canonical modes:

```python
class VolumeMode(Enum):
    FIXED = "fixed"
    DEVICE_HARDWARE = "device_hardware"
    DSP_SOFTWARE = "dsp_software"
```

## FIXED

```text
GStreamer pipeline volume must remain unity.
No software attenuation.
No hidden ALSA softvol.
DAC/preamp controls loudness externally.
```

Default recommendation for strict audiophile Direct when hardware-volume semantics are
not verified.

## DEVICE_HARDWARE

```text
PCM sample stream remains unchanged.
Volume command targets a validated ALSA CTL/Mixer element that belongs to this DAC.
UI follows external hardware changes through ALSA control events.
```

This mode is **not** available merely because a mixer element named `PCM`, `Master`, or
`Speaker` exists.

## DSP_SOFTWARE

```text
Digital gain occurs in the signal path.
The path is not bit-perfect.
Signal Truth must show the gain stage.
```

It can still be high quality.

Honesty is the requirement.

---

# 286. CURRENT `playbin3` VOLUME IS NOT DIRECT-DAC VOLUME AUTHORITY

Current GStreamer transport exposes generic pipeline volume.

That remains valid for desktop/shared playback.

For DAC Direct:

```text
VolumeMode.FIXED
→ NEVER call pipeline.set_property("volume", user_gain)

VolumeMode.DEVICE_HARDWARE
→ NEVER map slider to playbin volume
→ map slider through VolumePolicyService → AlsaControlAdapter

VolumeMode.DSP_SOFTWARE
→ pipeline/software gain may be used intentionally
→ evidence marks sample mutation
```

Do not reuse one integer `0..100` as the domain truth for all three modes.

Presentation percentages are a projection.

Device volume domain must preserve:

```text
raw control value
actual dB value when available
min/max dB
step/granularity
mute state
channel coupling
control element identity
```

---

# 287. HARDWARE VOLUME QUALIFICATION

A device control is eligible only when all are established:

```text
control belongs to the selected physical DAC
control interface/name/index are stable enough under qualification
playback direction is correct
dB range is readable OR profile explicitly marks raw-only semantics
muting semantics are understood
channel semantics are understood
external changes can be observed
reconnect does not bind the mapping to the wrong card index
```

For premium Stable, prefer dB-capable controls.

Raw-only device controls MAY remain `PROFILED_UNVERIFIED` until hardware qualification.

Never assume:

```text
50% slider == -6 dB
```

ALSA devices can have non-linear mappings.

---

# 288. VOLUME SAFETY — THIS IS A PRODUCT SAFETY CONTRACT

A premium player cannot treat hardware volume as a trivial slider.

Persist per DAC:

```text
comfort_max
safety_min
safety_max
last_device_volume
startup_policy
```

Safety rules:

```text
1. Clamp every hardware-volume command to device limits.
2. Then clamp to user safety limits.
3. Reject NaN/out-of-domain values before adapter call.
4. Never restore saved volume until the SAME stable device and SAME verified control mapping are present.
5. Never copy a saved volume from one ambiguous DAC identity to another.
6. On profile/control mismatch, remain Fixed or require explicit user choice.
7. UI must display the effective value returned/read back from hardware, not merely the requested value.
```

Optional premium behavior:

```text
comfort limit
→ soft UI resistance / confirmation to exceed

safety limit
→ hard maximum/minimum that controls cannot exceed
```

---

# 289. EXTERNAL HARDWARE KNOB / REMOTE CONVERGENCE

ALSA CTL supports event subscription.

Michi should use that capability for verified hardware volume.

Target flow:

```text
physical DAC knob moves
→ kernel/ALSA control event
→ AlsaControlAdapter reads canonical current value
→ DeviceControlEventService validates stable binding generation
→ VolumePolicyService publishes effective dB/value
→ QML slider moves
```

The event is observational.

Never reflect UI value optimistically as truth before hardware readback when a device
control supports authoritative readback.

Generation requirement:

```text
control event generation != current device binding generation
→ discard stale event
```

---

# 290. GStreamer CLOCK DISCIPLINE — HIDDEN RESAMPLING KILL SWITCH

A Direct path is not proven by selecting `alsasink` alone.

`GstAudioBaseSink` has a clock-slaving policy.

The `resample` slave method can resample to match a master clock.

Therefore strict Direct MUST observe:

```text
actual sink factory
sink device property
provide-clock
slave-method
actual pipeline clock provider
presence/absence of audioresample
negotiated caps
```

Strict policy:

```text
slave-method=resample
→ BLOCK bit-perfect/direct verification

explicit audioresample active
→ BLOCK bit-perfect/direct verification unless a non-bit-perfect policy explicitly requested it

clock authority unknown
→ UNVERIFIED, never VERIFIED
```

Do not change clock behavior globally until R24 proves the correct configuration against
real hardware and the actual GStreamer graph.

---

# 291. SINK CLOCK POLICY — RESEARCH BEFORE DEFAULT

Hypothesis:

```text
For a USB DAC Direct sink, allowing the audio sink/device clock to become pipeline clock
can reduce the need for clock slaving against an unrelated master.
```

This is not promoted as a universal default without R24.

R24 must compare:

```text
sink provides clock + pipeline uses it
vs
pipeline uses another clock + slave skew
vs
pipeline uses another clock + slave none
```

Capture:

```text
clock identity
slave method
caps
ALSA hw_params
XRUN count
buffer/period
long-run drift
transition behavior
```

Kill criterion:

```text
configuration causes instability,
clock discontinuities,
or hidden conversion.
```

---

# 292. STRICT GStreamer OUTPUT GRAPH

Stable Direct MUST use an inspectable graph.

Conceptual target:

```text
source/decode
→ queue only if proven signal-neutral and operationally required
→ audioconvert ONLY under explicit preservation policy
→ capsfilter exact PCM tuple
→ alsasink(device="hw:CARD=...,DEV=...")
```

Preferred strict graph is the smallest graph that works correctly.

`audioresample` is absent by default in strict Direct.

If `audioconvert` exists:

```text
dithering = none
noise-shaping = none
channel reorder/remix disabled unless explicitly required
runtime evidence must establish whether the actual conversion is sample preserving
```

Do not rely on element names alone.

Inspect negotiated pads/caps and relevant transform state.

---

# 293. `playbin3` MIGRATION STRATEGY

`playbin3` is not forbidden.

What is forbidden is letting its auto-selected output graph become opaque while Michi
claims strict Direct.

Recommended implementation order:

```text
1. Preserve existing Shared `playbin3` path byte-for-byte behavior.
2. Add a sink-injection seam in GStreamerBindings / GStreamerAudioPort.
3. Build one explicit StrictSinkSpec from OutputPlanner.
4. Build the sink bin through StrictSinkBuilder.
5. Set that bin as the `audio-sink` for Direct sessions.
6. Instrument it with PipelineInspector.
7. Refuse VERIFIED if inspection cannot establish the required invariants.
```

This minimizes regression risk.

Do not begin by replacing `playbin3` with a completely custom decodebin pipeline.

That can be a later decision only if `playbin3` prevents a required invariant.

---

# 294. AUDIO SINK INJECTION CONTRACT

Proposed immutable domain input:

```python
@dataclass(frozen=True)
class StrictSinkSpec:
    alsa_device: str
    pcm_format: str
    rate_hz: int
    channels: int
    channel_mask: int | None
    volume_mode: VolumeMode
    allow_audioconvert: bool
    allow_resampler: bool
```

Validation:

```text
alsa_device must be hw:* for strict Linux Direct
rate/channels positive
volume FIXED/HARDWARE → software gain unity
allow_resampler must be false for strict bit-perfect target
```

`StrictSinkBuilder` returns an opaque sink object to the existing GStreamer adapter.

No GStreamer type enters domain/application code.

---

# 295. MICHI SIGNAL TRUTH — SIGNAL PATH, BUT EVIDENCE-FIRST

User-facing name:

```text
Michi Signal Truth
```

Internal model:

```text
SignalTruthSnapshot
```

Show these stages separately:

```text
1. SOURCE FILE FACTS
   FLAC / WAV / DSF / etc.
   nominal rate/bit depth/channels from file metadata

2. DECODED SOURCE SIGNAL
   actual PCM/DSD signal emitted by decoder

3. ENGINE EFFECTIVE SIGNAL
   caps/format/rate/channels
   resampling
   remix
   DSP
   software volume

4. OUTPUT PLAN
   selected device
   transport
   requested tuple
   volume mode
   DSD policy

5. DEVICE NEGOTIATED SIGNAL
   ALSA hw_params exact runtime
   container format
   significant bits where available
   rate
   channels
   period/buffer

6. DRIVER / USB WITNESS
   snd-usb-audio stream witness when available
   current interface/altset/frequency evidence when available

7. VERDICT
   Direct
   Direct — container adapted
   DSP
   Resampled
   Remixed
   Unknown
   Contradicted
```

This is more useful than a single colored badge.

A badge may summarize it.

The detail view must preserve the evidence.

---

# 296. SIGNAL TRUTH VERDICTS

Use:

```python
class SignalTruthVerdict(Enum):
    DIRECT = "direct"
    DIRECT_CONTAINER_ADAPTED = "direct_container_adapted"
    DSP = "dsp"
    RESAMPLED = "resampled"
    REMIXED = "remixed"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"
```

Important precision:

```text
S24_3LE decoded source
→ S32_LE transport container
→ 24 significant bits preserved
```

must not automatically be branded destructive solely because the container changed.

Conversely:

```text
S32_LE
```

does not prove 32 significant bits.

Use ALSA `sbits` evidence when available after a concrete configuration.

---

# 297. BIT-PERFECT CLAIM REFINEMENT

M11.4 currently requires exact signal preservation and no format conversion.

V3.2 refines the wording to distinguish:

```text
sample-significant preservation
vs
container representation equality
```

Do NOT weaken the claim casually.

For Stable, expose two internal facts:

```text
sample_values_preserved: true/false/unknown
container_representation_changed: true/false/unknown
```

Then product copy can remain conservative:

```text
Direct
Direct — container adapted
```

Promotion to a literal `BIT PERFECT = VERIFIED` across container adaptation requires R3
sample-preservation evidence and M11.5 conformance acceptance.

---

# 298. SAMPLE-RATE SWITCHING — SOURCE NATIVE, NOT GLOBAL UPSAMPLING

Strict Direct preference:

```text
44.1 source → request 44.1
48 source   → request 48
88.2 source → request 88.2
96 source   → request 96
176.4       → request 176.4
192         → request 192
```

Only deviate when policy explicitly requests conversion or the source tuple cannot be
opened and the user's fallback policy permits conversion.

No hidden:

```text
always 48 kHz
always 192 kHz
```

for convenience.

---

# 299. TRANSITION CLASSIFICATION

Before each next-track transition, compare:

```text
transport
format
rate
channels
significant-bit requirement
DSD strategy
output device generation
```

Canonical result:

```python
class TransitionKind(Enum):
    SAME_TUPLE_GAPLESS_ELIGIBLE = "same_tuple_gapless_eligible"
    REOPEN_REQUIRED = "reopen_required"
    TRANSPORT_CHANGE_REQUIRED = "transport_change_required"
```

Same tuple:

```text
may be gapless if the engine proves seamless transition
```

Different tuple:

```text
controlled reconfigure/reopen
```

PCM ↔ DoP/native DSD:

```text
transport rebuild
```

Never resample merely to keep the word "gapless" true.

---

# 300. GAPLESS CONTRACT — AUDIOPHILE HONESTY OVER CONTINUITY THEATER

Same-format album playback is the premium target.

Cross-format boundaries are different.

Example:

```text
track A: 24/96 PCM
track B: 16/44.1 PCM
```

Allowed:

```text
short truthful reconfiguration boundary
```

Forbidden:

```text
resample track B to 96 kHz only so the transition appears seamless
without telling the user
```

M11.5 already owns formal gapless conformance.

V3.2 supplies the DAC/output transition evidence.

---

# 301. RESYNC DELAY — DEVICE-SPECIFIC PROBLEM SOLVER

Default:

```text
0 ms
```

Non-zero resync delay requires one of:

```text
measured physical-lab evidence
user explicit override
Michi Verified profile carrying measured evidence
```

Never infer it from:

```text
manufacturer alone
VID/PID family alone
community comment alone
"audiophile DACs usually need..."
```

Application:

```text
reconfigure/open
→ DAC reaches ready state
→ optional bounded silent lead-in according to plan
→ content starts
```

The implementation must define whether silence is inserted before content timestamps or
as actual samples and prove that first source samples are neither dropped nor shifted
incorrectly.

R25 owns that proof.

---

# 302. FIRST-SAMPLE INTEGRITY

Premium integration must detect a classic DAC defect:

```text
new rate locks late
→ beginning of track is clipped
```

Experiment must use a fixture with an unmistakable impulse/marker at the beginning.

Measure:

```text
requested playback start
ALSA configured
GStreamer PLAYING/ASYNC_DONE
first buffer submitted
first hardware progress evidence
captured loopback / external ADC marker where available
```

Pass:

```text
first content sample/marker is preserved within measurement method limits
```

A non-zero resync delay is justified only if it improves this test reproducibly.

---

# 303. DSD ARCHITECTURE — DESIGN NOW, PROMOTE ONLY WITH HARDWARE PROOF

Keep canonical policy:

```python
class DsdStrategy(Enum):
    DISABLED = "disabled"
    PCM_CONVERSION = "pcm_conversion"
    DOP = "dop"
    NATIVE = "native"
```

Rules:

```text
NATIVE visible as available
→ kernel + ALSA + exact hardware evidence supports it

DOP visible as available
→ framing path implemented + DAC/profile/exact evidence supports carrier tuple

PCM_CONVERSION
→ explicit signal conversion, never reported as DSD transport

AUTO
→ may be a user-facing planner preference, but it resolves to one explicit strategy before execution
```

Do not ship fake Native DSD because a descriptor, product brochure, or profile claims it.

Linux native DSD support is device/kernel dependent.

---

# 304. DoP CONTRACT

DoP is not ordinary PCM content even though it travels in a PCM-like carrier.

Product telemetry must report:

```text
Source: DSD64
Transport: DoP 1.0
Carrier: PCM-like 176.4 kHz / required format
Device: DoP
```

Never:

```text
Source DSD → "PCM 176.4" → user assumes conversion occurred
```

DoP marker/framing correctness requires golden fixtures and hardware tests.

Do not make the generic PCM signal-truth comparator classify DoP as normal PCM Direct.

---

# 305. DIRECT ACCESS POLICY — EBUSY IS NOT PERMISSION TO LIE

Linux Direct target uses ALSA hardware access.

If opening the selected `hw:` endpoint returns `EBUSY`:

```text
Strict Direct profile
→ fail with DEVICE_BUSY
→ explain that another client owns the DAC
→ do not silently route to default/PipeWire/shared
```

Optional user-selected fallback profile MAY say:

```text
if Direct unavailable → Shared
```

But the transition must be explicit in runtime state and Signal Truth.

---

# 306. FALLBACK POLICY

Use an explicit enum, not scattered booleans:

```python
class DirectFallbackPolicy(Enum):
    FAIL_CLOSED = "fail_closed"
    ASK_USER = "ask_user"
    ALLOW_SHARED = "allow_shared"
```

Recommended audiophile profile default:

```text
FAIL_CLOSED
```

Shared desktop profile may choose system-managed output independently.

Never auto-fallback to another physical DAC under a Direct profile.

---

# 307. DISCONNECT / RECONNECT — SAME DAC OR NO AUTOMATIC RESUME

On disconnect during playback:

```text
active output generation becomes terminal
runtime evidence snapshot freezes
PlaybackService receives truthful output failure
selected profile remains intent, device becomes unavailable
```

On reconnect:

Auto-resume MAY occur only if all are true:

```text
user policy allows auto-resume
stable physical identity matches
new generation has converged
pre-session rebind passes
required tuple is requalified/currently valid
hardware volume mapping is safe OR output is Fixed
```

Forbidden:

```text
same product string appears → resume
same VID/PID appears → resume
same card index appears → resume
```

---

# 308. RECONNECT VOLUME SAFETY

The worst possible reconnect bug is:

```text
old device at -40 dB
→ reconnect/new binding
→ player writes 0 dB unexpectedly
```

Therefore:

```text
Volume restore transaction:

1. identify same stable device
2. validate current control mapping
3. read current device volume
4. apply safety limit
5. decide restore policy
6. write target
7. read back
8. publish effective state
```

If any step is unknown:

```text
do not restore automatically
```

---

# 309. DAC DEVICE SETUP — PREMIUM UX MODEL

Do NOT place DAC controls inside `AudioEngineSettingsSection.qml`.

That file correctly teaches:

```text
Engine != DAC
```

Preserve that distinction.

Create a dedicated section/page:

```text
Audio Output / DAC
```

Suggested hierarchy:

```text
Detected Outputs
    [DAC card]

Selected Output
    Product identity
    Connection
    Status
    Michi Verified/Profiled badge

Playback Mode
    Direct — recommended for critical listening
    Shared — desktop integration

Volume
    Fixed
    Device
    Software DSP

Format Handling
    Native PCM
    DSD strategy
    fallback policy

Device Compatibility
    resync delay
    known profile notes

Signal Truth
    live evidence

Advanced Diagnostics
    raw binding, ALSA, kernel, evidence provenance
```

---

# 310. DAC CARD — INFORMATION DENSITY WITHOUT TECHNICAL NOISE

Normal card shows:

```text
[device icon]
Manufacturer Product
USB · Direct capable / qualification pending
Michi Verified | Profiled | Detected
Available
```

When active:

```text
Playing · 24-bit significant / 96 kHz · Direct
```

Do not show:

```text
hw:2,0
VID:PID
sysfs path
kernel driver
```

on the primary card.

Those belong in diagnostics.

---

# 311. DEVICE SETUP — SAFE DEFAULTS FIRST, ADVANCED SECOND

Normal controls should be decision-oriented.

Recommended defaults:

```text
Playback Mode: Direct
Volume: Fixed
PCM: Source Native
Resampling: Off
DSD: Disabled/PCM conversion until qualified, then profile recommendation may be offered
Fallback: Fail Closed
Resync Delay: 0 ms
```

Do not surface internal buffer sizes as normal-user knobs unless evidence proves a need.

Problem-solving knobs belong under Advanced and should explain why they exist.

---

# 312. MICHI VERIFIED — HARDWARE REGRESSION PROGRAM

A serious Roon-class integration needs real hardware retention.

Minimum Michi lab shelf should eventually contain representative classes:

```text
A. simple class-compliant UAC2 stereo DAC
B. XMOS-based high-rate asynchronous USB DAC
C. DAC with verified USB hardware-volume control
D. composite/multi-endpoint USB audio device
E. DSD-capable DAC
F. deliberately problematic/quirky device once one is identified
```

Each device gets:

```text
asset_id
model/revision
VID/PID
bcdDevice
serial policy
firmware when observable
cable/topology notes
known control map
known issue log
```

A model cannot become `MICHI_VERIFIED` from emulator/gadget evidence alone.

---

# 313. MICHI VERIFIED TEST MATRIX

Required matrix per candidate DAC:

```text
DISCOVERY
cold plug
hotplug
replug same port
replug different port
hub
reboot
suspend/resume

PCM
44.1k
48k
88.2k where supported
96k
176.4k where supported
192k
highest claimed stable rate
16-bit significant
24-bit significant
32-bit significant only when truly supported

TRANSITIONS
44.1 → 48
48 → 44.1
44.1 → 96
96 → 44.1
96 → 192
same tuple gapless
album boundary
seek/pause/resume

CONTROL
Fixed
hardware volume if available
mute
external knob events
safety limits
reconnect volume restore

FAILURE
EBUSY
unplug during playback
unplug during transition
stale hotplug callback
negotiation failure
XRUN injection/observation where practical

LONG RUN
2 h mixed-rate playback
8 h soak before Verified promotion target where practical
repeated 100+ track transitions
```

DSD adds its own matrix.

---

# 314. VERIFIED SEAL IS VERSIONED EVIDENCE

Store:

```text
profile_id
profile_version
hardware_asset_id
michi_commit
kernel
alsa
gstreamer
matrix_version
matrix_result_hash
date
operator/lab run id
raw artifact bundle hash
```

The badge shown to users need not expose all this.

Advanced diagnostics should expose enough to explain why current status is Verified,
Previously Verified, or needs requalification.

---

# 315. PRIVACY — DEVICE PROFILES WITHOUT TELEMETRY

Michi does not need surveillance to have a premium DAC database.

Profile update model:

```text
signed static profile bundle
→ user/app downloads bundle
→ signature/hash verified
→ local matcher uses it
```

No default requirement to upload:

```text
serial numbers
USB topology
listening history
volume state
connected devices
```

User-submitted diagnostics must be explicit opt-in and sanitized.

---

# 316. SIGNED PROFILE BUNDLES

Suggested manifest:

```json
{
  "schema_version": 1,
  "bundle_version": "2026.09.1",
  "created_at": "2026-09-10T00:00:00Z",
  "profiles_sha256": "...",
  "signature_algorithm": "ed25519",
  "signature": "..."
}
```

Product behavior:

```text
signature invalid
→ reject whole bundle
→ keep previous known-good bundle

schema unsupported
→ reject

profile malformed
→ reject that bundle before activation
```

Never let remote profile data execute shell commands or modify kernel settings.

---

# 317. USER OVERRIDES ARE NOT VERIFIED PROFILE DATA

Separate namespaces:

```text
vendor/Michi profile facts
user override
runtime evidence
```

Example:

```text
Profile resync: 0 ms
User override: 750 ms
Runtime current: 750 ms
```

UI:

```text
Resync Delay: 750 ms · Custom
```

Do not write the override back into profile truth.

---

# 318. DIAGNOSTIC BUNDLE — PREMIUM SUPPORT WITHOUT GUESSING

Add an explicit local export:

```text
Michi DAC Diagnostic Bundle
```

Include only relevant/sanitized evidence:

```text
Michi version/commit
kernel
ALSA/GStreamer versions
DAC identity with serial redacted by default
current profile id/version
current binding
capability evidence summary
last output plan
last Signal Truth snapshot
ALSA hw_params snapshot
snd-usb-audio proc witness if available
recent DAC-specific errors
transition timeline
```

Do not include music filenames by default.

Do not include unrelated USB buses by default.

---

# 319. PERFORMANCE / LATENCY — DO NOT TURN AUDIOPHILE INTO LOW-LATENCY THEATER

For music playback:

```text
reliability + integrity > minimum latency
```

Do not arbitrarily force tiny buffers.

Collect:

```text
period_size
buffer_size
start threshold
avail minimum
XRUNs
startup time
transition time
```

Tune only from evidence.

A profile may carry a buffer workaround only if a lab experiment proves it is needed.

---

# 320. BUFFER POLICY

Proposed policy classes:

```python
class BufferPolicy(Enum):
    AUTO_STABLE = "auto_stable"
    DEVICE_PROFILED = "device_profiled"
    USER_ADVANCED = "user_advanced"
```

Default:

```text
AUTO_STABLE
```

Do not expose raw frames/period controls to normal users.

If hardware-specific tuning is needed, profile it and retain the baseline evidence.

---

# 321. FAILURE TAXONOMY — PREMIUM USER COPY + TECHNICAL EVIDENCE

Internal:

```text
DEVICE_BUSY
DEVICE_REMOVED
FORMAT_UNSUPPORTED
NEGOTIATION_FAILED
XRUN
DEVICE_SUSPENDED
USB_ENDPOINT_STALL
USB_BANDWIDTH_EXHAUSTED
CONTROL_MAPPING_INVALID
PROFILE_RUNTIME_CONTRADICTION
CLOCK_POLICY_UNVERIFIED
UNKNOWN
```

Primary UI copy:

```text
Michi couldn't open this DAC in Direct mode.
Another application may be using it.
```

Advanced:

```text
FailureKind: DEVICE_BUSY
Layer: ALSA_PCM_API
errno: EBUSY
Binding: hw:CARD=...,DEV=...
Evidence run: ...
```

Human-facing and engineering-facing layers must coexist.

---

# 322. NO AUTOMATIC KERNEL QUIRK MUTATION

Roon-class quality does not justify unsafe magic.

Michi product runtime MUST NOT automatically:

```text
reload snd-usb-audio
change lowlatency/autoclock/implicit_fb
write modprobe.d
patch kernel quirks
change USB autosuspend globally
```

Those remain lab hypotheses unless a future explicit privileged feature is designed.

A known profile may say:

```text
"This kernel/device combination has a known issue."
```

It may not silently mutate the host.

---

# 323. USB POWER MANAGEMENT — OBSERVE BEFORE BLAMING

When suspend/dropout evidence exists, capture:

```text
runtime PM status
USB power/control policy
resume events
kernel logs
port/hub topology
```

Do not disable autosuspend globally as a first response.

Any workaround must be scoped, reversible and evidence-backed.

---

# 324. DIRECT DAC MODE VS DESKTOP SHARED MODE

These are different products modes.

## Desktop Shared

```text
system mixer/session manager participates
other applications can coexist
sample conversion may occur outside Michi control
Signal Truth cannot claim Direct
```

## DAC Direct

```text
explicit physical DAC binding
exclusive ALSA hw open
Michi controls requested PCM tuple
no silent fallback
runtime evidence required
```

Do not present one as universally superior.

User chooses according to use case.

---

# 325. ENGINE PARITY DOES NOT MEAN FALSE FEATURE PARITY

M11.5 asks for multi-engine parity at service level.

Interpretation:

```text
same service semantics
same honest states
same selection/profile model
```

NOT:

```text
pretend Qt Multimedia can prove the same Direct invariants as GStreamer
```

If GStreamer supports `VERIFIED` Direct and Qt cannot expose required evidence:

```text
Qt → UNVERIFIED / Shared-only capability
```

That is correct parity of truthfulness.

---

# 326. MPD INTEGRATION BOUNDARY

MPD may support high-quality ALSA output, but Michi must not let MPD become a second
independent DAC-profile authority.

Michi owns:

```text
stable device identity
profile intent
device availability
user-visible truth model
```

MPD adapter owns:

```text
its transport/config execution
its observable effective output facts
```

Where MPD cannot expose equivalent evidence, verdict degrades to `UNVERIFIED` rather than
fabricating parity.

---

# 327. UI VOLUME CONTROL MUST BECOME MODE-AWARE

Current generic `VolumeControl.qml` projects one `0..100` slider and mute button.

For M11.4:

```text
presentation component remains reusable
BUT its model must carry semantic mode
```

Required projection fields:

```text
mode
control_enabled
slider_min
slider_max
slider_step
display_value
display_unit
muted
mute_supported
safety_limited
comfort_limited
reason_disabled
```

Examples:

```text
Fixed
→ slider disabled/hidden
→ "Fixed output"

Device hardware
→ slider maps to canonical dB/control projection
→ "-32.5 dB"

Software DSP
→ slider maps software gain
→ Signal Truth shows DSP Volume
```

Never let the QML decide signal semantics.

---

# 328. PREMIUM DEVICE SETUP READ MODEL

Create one application read model:

```python
@dataclass(frozen=True)
class DacSetupProjection:
    stable_device_id: str
    display_name: str
    profile_tier: str
    availability: str
    transport_options: tuple[str, ...]
    selected_transport: str
    volume_modes: tuple[str, ...]
    selected_volume_mode: str
    pcm_summary: str
    dsd_summary: str
    current_signal_verdict: str | None
    needs_requalification: bool
    user_override_flags: tuple[str, ...]
```

QML consumes projection.

QML does not query ALSA or profile files.

---

# 329. R24 — GSTREAMER CLOCK AUTHORITY / SLAVE METHOD

```yaml
schema_version: 1
experiment_id: R24_GSTREAMER_CLOCK_AUTHORITY
status: required_before_strict_direct_verified

question: >
  Can Michi prove that the selected GStreamer Direct configuration avoids hidden
  resampling caused by clock slaving and remains stable on real USB DACs?

variants:
  - sink_clock_pipeline_master
  - non_sink_clock_slave_skew
  - non_sink_clock_slave_none

forbidden_variant_for_verified:
  - slave_resample

capture:
  - pipeline_clock_identity
  - sink_clock_identity
  - provide_clock
  - slave_method
  - pipeline_elements
  - negotiated_caps
  - alsa_hw_params
  - xrun_count
  - long_run_drift_observation

falsifiers:
  - hidden_resampler
  - unstable_clocking
  - repeated_discontinuity
  - actual_rate_differs_from_requested_without_explicit_policy

safe_retreat: mark_direct_unverified
```

---

# 330. R25 — SAMPLE-RATE TRANSITION / RESYNC LAB

```yaml
schema_version: 1
experiment_id: R25_RATE_TRANSITION_RESYNC
status: required_before_profile_resync_values

matrix:
  - 44100_to_44100
  - 44100_to_48000
  - 48000_to_44100
  - 44100_to_96000
  - 96000_to_192000
  - 192000_to_44100

resync_delay_ms:
  - 0
  - 100
  - 250
  - 500
  - 1000

capture:
  - transition_timeline
  - first_sample_fixture_result
  - click_pop_observation
  - negotiation_result
  - xrun_count

pass:
  - minimal_delay_that_preserves_first_content_for_affected_device
  - zero_remains_default_when_no_problem_exists

falsifier:
  - delay_masks_but_does_not_fix_data_loss
```

---

# 331. R26 — HARDWARE VOLUME CONTROL QUALIFICATION

```yaml
schema_version: 1
experiment_id: R26_HARDWARE_VOLUME_CONTROL
status: required_before_device_volume_profile_promotion

capture:
  - control_interface
  - control_name
  - control_index
  - raw_range
  - db_range
  - step
  - mute_support
  - channels
  - external_knob_behavior
  - reconnect_behavior

cases:
  - min
  - max
  - midpoint
  - repeated_small_steps
  - mute_unmute
  - reconnect
  - reboot

falsifiers:
  - wrong_control_changes_unrelated_signal
  - mapping_changes_ambiguously
  - value_write_not_reflected_by_readback
  - unsafe_jump

safe_retreat: fixed_volume_only
```

---

# 332. R27 — ALSA CONTROL EVENT CONVERGENCE

```yaml
schema_version: 1
experiment_id: R27_ALSA_CONTROL_EVENT_CONVERGENCE
status: required_for_premium_device_volume_ux

question: >
  Does Michi converge its UI/read model to externally initiated DAC volume/mute
  changes without loops, stale-generation updates, or missed events?

cases:
  - external_knob_single_step
  - external_knob_fast_sweep
  - hardware_mute
  - app_write_then_event_echo
  - disconnect_with_queued_event
  - reconnect_new_generation

pass:
  - final_ui_value_equals_hardware_readback
  - no_feedback_loop
  - stale_generation_event_ignored
```

---

# 333. R28 — SIGNAL TRUTH CONTRADICTION MATRIX

```yaml
schema_version: 1
experiment_id: R28_SIGNAL_TRUTH_CONTRADICTIONS
status: required_before_signal_truth_ui_freeze

cases:
  - profile_192_runtime_rejects_192
  - gst_caps_96_alsa_hw_48
  - decoded_24_significant_device_24_in_s32_container
  - software_volume_active
  - unexpected_audioresample
  - proc_driver_witness_disagrees_with_alsa

pass:
  - stronger_current_evidence_wins
  - losing_evidence_is_preserved_as_contradiction
  - ui_never_labels_contradicted_path_direct_verified
```

---

# 334. R29 — MICHI VERIFIED PROFILE PRECEDENCE

```yaml
schema_version: 1
experiment_id: R29_PROFILE_PRECEDENCE
status: required_before_profile_bundle_product_use

cases:
  - verified_profile_current_runtime_matches
  - verified_profile_current_exact_open_rejects
  - profile_old_kernel_current_kernel_changed
  - profile_bcd_device_mismatch
  - user_override_resync
  - malformed_profile
  - invalid_bundle_signature

pass:
  - runtime_truth_never_overridden
  - profile_status_downgrades_truthfully
  - invalid_bundle_never_activates
```

---

# 335. R30 — DSD / DoP PHYSICAL LAB

```yaml
schema_version: 1
experiment_id: R30_DSD_DOP_PHYSICAL
status: post_pcm_stable_or_release_gate_if_dsd_is_required

requires:
  - physical_dsd_capable_dac
  - native_dsd_kernel_support_when_testing_native
  - known_dsd_fixtures

variants:
  - dop
  - native_if_supported
  - pcm_conversion

capture:
  - source_dsd_rate
  - selected_strategy
  - carrier_or_native_format
  - alsa_runtime
  - driver_witness
  - dac_display_or_external_witness_when_available

falsifiers:
  - dop_markers_corrupted
  - native_claim_is_pcm
  - unexpected_pcm_conversion
  - failed_attempt_leaves_device_unusable_without_recovery
```

---

# 336. R31 — KERNEL / ALSA / GSTREAMER UPGRADE REQUALIFICATION

```yaml
schema_version: 1
experiment_id: R31_ENVIRONMENT_UPGRADE_REQUALIFICATION
status: required_for_michi_verified_release_process

change_one_at_a_time:
  - kernel
  - alsa_lib
  - gstreamer

pass:
  - current_environment_fingerprint_changes
  - historical_profile_remains_historical
  - required_smoke_matrix_reexecutes
  - verified_badge_policy_is_deterministic
```

---

# 337. R32 — LONG-RUN USB DAC SOAK

```yaml
schema_version: 1
experiment_id: R32_USB_DAC_SOAK
status: required_before_top_tier_verified

duration_targets:
  smoke_hours: 2
  verified_hours: 8

playlist:
  - mixed_441_family
  - mixed_48_family
  - long_tracks
  - many_short_tracks

capture:
  - xruns
  - backend_failures
  - usb_errors
  - memory_growth
  - pump_health
  - transition_failures

pass:
  - no_unexplained_signal_policy_degradation
  - no_repeated_backend_failure
  - no_unbounded_resource_growth
```

---

# 338. R33 — RECONNECT / RESUME SAFETY

```yaml
schema_version: 1
experiment_id: R33_RECONNECT_RESUME_SAFETY
status: required_before_auto_resume

cases:
  - same_dac_same_port
  - same_dac_other_port
  - identical_model_other_serial
  - identical_model_no_serial
  - disconnect_during_volume_write
  - disconnect_during_rate_transition

pass:
  - resume_only_same_stable_identity
  - ambiguous_identity_never_auto_inherits_preferences
  - no_unsafe_volume_restore
  - stale_callbacks_ignored
```

---

# 339. OPENCODE EXECUTION SLICE — DAC-PREMIUM-001 PROFILE DOMAIN

CREATE:

```text
src/michi/domain/dac_profile.py
src/michi/domain/signal_truth.py
src/michi/domain/volume_policy.py
tests/unit/domain/test_dac_profile.py
tests/unit/domain/test_signal_truth.py
tests/unit/domain/test_volume_policy.py
```

MUST:

```text
pure Python
no ALSA imports
no GStreamer imports
profile validation
runtime-evidence precedence
volume mode semantics
signal truth enums
```

MUST NOT:

```text
modify playback
modify UI
load remote profile bundle
```

Gate:

```text
profile exact-open contradiction resolves to runtime
verified profile requires lab evidence id/hash
Fixed volume cannot permit software gain
```

---

# 340. OPENCODE EXECUTION SLICE — DAC-PREMIUM-002 ALSA CONTROL OBSERVER

CREATE:

```text
src/michi/infrastructure/audio_devices/alsa_control_adapter.py
src/michi/infrastructure/audio_devices/alsa_mixer_adapter.py
tests/unit/infrastructure/audio_devices/test_alsa_control_adapter.py
tests/unit/infrastructure/audio_devices/test_alsa_mixer_adapter.py
```

MUST:

```text
enumerate/read control metadata
dB range where available
subscribe/poll control events
retain control identity
close handles deterministically
return plain Python observations
```

MUST NOT:

```text
choose a control by fuzzy name and write it automatically
persist card index as stable identity
change volume during discovery
```

---

# 341. OPENCODE EXECUTION SLICE — DAC-PREMIUM-003 VOLUME POLICY SERVICE

CREATE:

```text
src/michi/application/volume_policy_service.py
src/michi/application/device_control_event_service.py
tests/unit/application/test_volume_policy_service.py
tests/unit/application/test_device_control_event_service.py
```

MUST:

```text
Fixed / Device Hardware / DSP Software distinction
safety clamping
requested vs effective readback
generation validation
external event convergence
```

MUST NOT:

```text
send pipeline gain in Fixed
send pipeline gain in Device Hardware
restore a volume to ambiguous identity
```

---

# 342. OPENCODE EXECUTION SLICE — DAC-PREMIUM-004 GSTREAMER SINK SEAM

MODIFY:

```text
src/michi/infrastructure/audio_engines/gstreamer.py
```

CREATE one non-conflicting module location:

```text
src/michi/infrastructure/gstreamer_dac/strict_sink_builder.py
src/michi/infrastructure/gstreamer_dac/pipeline_inspector.py
src/michi/infrastructure/gstreamer_dac/clock_evidence.py
src/michi/infrastructure/gstreamer_dac/runtime_evidence.py
```

MUST:

```text
preserve existing Shared path
inject explicit audio sink only for Direct plan
bind hw endpoint
configure signal-conservative converter settings when converter needed
observe sink clock/slave method
observe actual caps
```

MUST NOT:

```text
rewrite pump architecture
change Session authority
insert audioresample by default
reuse playbin generic volume for Fixed/Hardware Direct
```

---

# 343. OPENCODE EXECUTION SLICE — DAC-PREMIUM-005 OUTPUT PLANNER

CREATE/MODIFY according to V3.1 tree:

```text
src/michi/application/audio_output_planner.py
src/michi/domain/audio_output_profile.py
tests/unit/application/test_audio_output_planner.py
```

Input:

```text
source signal
selected stable device
current binding generation
current capability evidence
user output profile
Michi DAC profile hints
```

Output:

```text
one immutable executable OutputPlan
```

The planner never probes hardware.

The planner never starts playback.

---

# 344. OPENCODE EXECUTION SLICE — DAC-PREMIUM-006 SIGNAL TRUTH

CREATE:

```text
src/michi/application/output_session_evidence_recorder.py
src/michi/presentation/dac_output_bridge.py
```

MUST combine, without conflation:

```text
file facts
decoded source runtime
effective engine runtime
output plan
ALSA negotiated runtime
driver witness
profile provenance
```

The bridge publishes a presentation projection only.

QML does not classify bit-perfect state itself.

---

# 345. OPENCODE EXECUTION SLICE — DAC-PREMIUM-007 PREMIUM DAC UI

CREATE:

```text
src/michi/presentation/qml/views/AudioOutputSettingsSection.qml
src/michi/presentation/qml/components/DacDeviceCard.qml
src/michi/presentation/qml/components/DacVolumeControl.qml
src/michi/presentation/qml/components/SignalTruthPanel.qml
```

MUST preserve:

```text
Audio Engine section separate from DAC section
progressive disclosure
keyboard accessibility
human copy primary / raw evidence advanced
no fake control for unsupported feature
```

Do not add sliders for unsupported hardware controls.

---

# 346. OPENCODE EXECUTION SLICE — DAC-PREMIUM-008 PROFILE BUNDLE

Do only after local profile domain + runtime precedence are sealed.

CREATE:

```text
src/michi/infrastructure/dac_profiles/profile_bundle_loader.py
src/michi/infrastructure/dac_profiles/signature_verifier.py
resources/dac_profiles/
tests/unit/infrastructure/dac_profiles/
```

MUST:

```text
schema validation
signature validation
atomic swap
rollback to previous bundle
no executable profile content
```

MUST NOT:

```text
require telemetry
upload device inventory
```

---

# 347. OPENCODE EXECUTION SLICE — DAC-PREMIUM-009 VERIFIED LAB TOOLING

CREATE under lab, not product runtime:

```text
tools/michi_audio_lab/dac_matrix_runner.py
tools/michi_audio_lab/dac_asset_manifest.py
tools/michi_audio_lab/transition_capture.py
tools/michi_audio_lab/volume_control_capture.py
tools/michi_audio_lab/verified_seal.py
```

Output artifacts:

```text
machine-readable JSON
human-readable Markdown summary
raw evidence references
matrix hash
```

Lab tools never become playback policy authority.

---

# 348. REQUIRED V3.2 NO-GO GATES

Stable/premium promotion is NO-GO if any applies:

```text
G-PREM-01
A Direct session can use generic playbin software volume while profile says Fixed.

G-PREM-02
A known-device profile can override a contradictory current exact-open result.

G-PREM-03
A hardware-volume control is selected by name heuristics without verified identity/mapping.

G-PREM-04
External hardware control changes cannot converge to UI or are published without generation validation.

G-PREM-05
GStreamer clock/slave policy is unknown yet path is labelled VERIFIED.

G-PREM-06
slave-method=resample or active audioresample exists in Strict Direct without explicit conversion policy.

G-PREM-07
Cross-rate gapless is achieved by hidden resampling.

G-PREM-08
Non-zero resync delay becomes a global default without device evidence.

G-PREM-09
Reconnect can restore volume to a merely same-model DAC.

G-PREM-10
`S32_LE` is presented as 32-bit significant without sbits/equivalent evidence.

G-PREM-11
DSD Native/DoP is advertised as working without relevant transport evidence.

G-PREM-12
EBUSY silently falls back from Direct to Shared under FAIL_CLOSED policy.

G-PREM-13
QML or presentation code reads ALSA/profile files directly.

G-PREM-14
A profile bundle can execute commands or mutate kernel configuration.

G-PREM-15
Michi Verified can be awarded without physical hardware matrix evidence.

G-PREM-16
AudioOutput/DAC code creates a second track/session/queue authority.

G-PREM-17
Shared and Direct are shown with the same integrity claim.

G-PREM-18
User override overwrites profile evidence provenance.

G-PREM-19
Signal Truth suppresses contradictory evidence instead of preserving it.

G-PREM-20
Any current-runtime unknown is converted to a positive capability claim for UX convenience.
```

---

# 349. PREMIUM PRODUCT DEFAULTS

For a newly detected USB DAC with no verified profile:

```text
Device: Detected
Transport recommendation: Direct available if hw binding exists
Volume: Fixed
PCM: Source Native
Resampling: Off
DSD: Disabled / not verified
Resync: 0 ms
Fallback: Fail Closed
Auto-resume: Off until identity confidence permits it
Signal Truth: current evidence only
```

For a Michi Verified DAC:

```text
apply safe recommended defaults
show product branding/icon
expose verified modes
still revalidate current runtime
```

Known profile improves ergonomics.

It never reduces epistemic rigor.

---

# 350. PREMIUM DEFINITION OF DONE — PCM DIRECT 1.0

PCM Direct may be called production-ready only when:

```text
IDENTITY
[ ] R19 hardware convergence passed
[ ] R20 collision matrix passed
[ ] R23 multi-endpoint case covered

CAPABILITY
[ ] exact-open path implemented
[ ] significant-bit semantics correct
[ ] stale qualification invalidation implemented

GSTREAMER
[ ] explicit Direct sink injection implemented
[ ] hw binding verified
[ ] pipeline inspector implemented
[ ] R24 clock policy passed
[ ] no hidden resampler gate passed

VOLUME
[ ] Fixed cannot mutate pipeline gain
[ ] Hardware mode requires verified mapping
[ ] safety limits implemented
[ ] external control event convergence tested

TRANSITIONS
[ ] native rate switching works
[ ] same-tuple gapless tested by M11.5
[ ] cross-tuple reconfigure is honest
[ ] R25 first-sample/resync matrix passed

FAILURE
[ ] EBUSY fail-closed
[ ] disconnect/reconnect generation-safe
[ ] volume reconnect safety passed
[ ] no silent physical-device fallback

OBSERVABILITY
[ ] Signal Truth projection complete
[ ] requested vs effective vs negotiated preserved
[ ] contradiction state visible
[ ] diagnostic bundle export sanitized

QA
[ ] unit suite green
[ ] integration suite green
[ ] physical matrix green on minimum representative hardware set
[ ] soak test green
```

---

# 351. DSD DEFINITION OF DONE — SEPARATE PROMOTION GATE

Do not hold PCM Direct hostage to unfinished DSD if product scheduling says PCM comes first.

DSD becomes production-supported only when:

```text
[ ] DoP framing implemented and golden-tested
[ ] Native path implemented where Linux exposes it
[ ] physical DSD-capable DAC tested
[ ] DSD→PCM explicitly labelled conversion
[ ] DSD/DoP transitions tested
[ ] software volume/DSP policy interactions explicit
[ ] failed DSD attempt recovery tested
[ ] Signal Truth reports source and transport distinctly
```

Until then:

```text
architecture present
feature unavailable/experimental
no false capability claim
```

---

# 352. SOURCE REGISTER — V3.2 PREMIUM BENCHMARK / UPSTREAM FACTS

The following sources informed V3.2 requirements.

Roon public product behavior:

```text
https://help.roonlabs.com/portal/en/kb/articles/audio-setup-basics
https://help.roonlabs.com/portal/en/kb/articles/signal-path
https://help.roonlabs.com/portal/en/kb/articles/roon-ready
https://help.roonlabs.com/portal/en/kb/articles/roon-partner-programs
https://help.roonlabs.com/portal/en/kb/articles/audio-on-linux
https://help.roonlabs.com/portal/en/kb/articles/exclusive-mode
https://help.roonlabs.com/portal/en/kb/articles/volume-limits
```

GStreamer upstream:

```text
https://gstreamer.freedesktop.org/documentation/audio/gstaudiobasesink.html
```

ALSA upstream:

```text
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___h_w___params.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___control.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___simple_mixer.html
https://www.alsa-project.org/alsa-doc/alsa-lib/pcm.html
```

Linux kernel:

```text
https://docs.kernel.org/sound/alsa-configuration.html
```

Evidence limits:

```text
Roon documentation is used only to benchmark public product behavior.
Linux/GStreamer/ALSA documentation defines the relevant implementation facts.
Physical behavior still requires Michi experiments.
```

---

# 353. V3.2 EXECUTABLE REFERENCE — PREMIUM DOMAIN CONTRACT

The following executable reference is additive.

It is intentionally pure Python.

It does not replace product adapters.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import FrozenSet


class ProfileTier(Enum):
    UNKNOWN = "unknown"
    DETECTED = "detected"
    MICHI_PROFILED = "michi_profiled"
    MICHI_VERIFIED = "michi_verified"


class EvidenceAuthority(IntEnum):
    HINT = 10
    PROFILE = 20
    DRIVER_REPORTED = 30
    EXACT_OPEN = 40
    ACTIVE_RUNTIME = 50


class VolumeMode(Enum):
    FIXED = "fixed"
    DEVICE_HARDWARE = "device_hardware"
    DSP_SOFTWARE = "dsp_software"


class DsdStrategy(Enum):
    DISABLED = "disabled"
    PCM_CONVERSION = "pcm_conversion"
    DOP = "dop"
    NATIVE = "native"


class SignalTruthVerdict(Enum):
    DIRECT = "direct"
    DIRECT_CONTAINER_ADAPTED = "direct_container_adapted"
    DSP = "dsp"
    RESAMPLED = "resampled"
    REMIXED = "remixed"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


class TransitionKind(Enum):
    SAME_TUPLE_GAPLESS_ELIGIBLE = "same_tuple_gapless_eligible"
    REOPEN_REQUIRED = "reopen_required"
    TRANSPORT_CHANGE_REQUIRED = "transport_change_required"


@dataclass(frozen=True, slots=True)
class PcmTuple:
    format_name: str
    rate_hz: int
    channels: int
    container_bits: int
    significant_bits: int | None = None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.rate_hz <= 0:
            errors.append("rate_hz must be positive")
        if self.channels <= 0:
            errors.append("channels must be positive")
        if self.container_bits <= 0:
            errors.append("container_bits must be positive")
        if self.significant_bits is not None:
            if self.significant_bits <= 0:
                errors.append("significant_bits must be positive when known")
            elif self.significant_bits > self.container_bits:
                errors.append("significant_bits cannot exceed container_bits")
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class ProfileMatch:
    vendor_id: str
    product_id: str
    product_string: str | None = None
    bcd_device: str | None = None
    serial_prefix: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceVolumeControl:
    element_name: str
    element_index: int
    min_db_x100: int
    max_db_x100: int
    step_db_x100: int | None
    has_mute: bool

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.element_name.strip():
            errors.append("hardware volume element_name is required")
        if self.min_db_x100 > self.max_db_x100:
            errors.append("hardware volume min exceeds max")
        if self.step_db_x100 is not None and self.step_db_x100 <= 0:
            errors.append("hardware volume step must be positive")
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class MichiDacProfile:
    profile_id: str
    schema_version: int
    tier: ProfileTier
    match: ProfileMatch
    verified_pcm: FrozenSet[PcmTuple] = field(default_factory=frozenset)
    dsd_strategies: FrozenSet[DsdStrategy] = field(default_factory=frozenset)
    hardware_volume: DeviceVolumeControl | None = None
    resync_delay_ms: int = 0
    known_quirks: tuple[str, ...] = ()
    lab_matrix_hash: str | None = None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if self.schema_version < 1:
            errors.append("schema_version must be >= 1")
        if self.resync_delay_ms < 0 or self.resync_delay_ms > 5000:
            errors.append("resync_delay_ms outside safe schema range")
        if self.tier is ProfileTier.MICHI_VERIFIED and not self.lab_matrix_hash:
            errors.append("verified profile requires lab_matrix_hash")
        if self.hardware_volume is not None:
            errors.extend(self.hardware_volume.validate())
        for pcm in self.verified_pcm:
            errors.extend(pcm.validate())
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class RuntimeCapabilityEvidence:
    pcm: PcmTuple
    authority: EvidenceAuthority
    supported: bool
    context_fingerprint: str


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    supported: bool | None
    authority: EvidenceAuthority | None
    reason: str
    contradicted_profile: bool = False


def resolve_pcm_capability(
    pcm: PcmTuple,
    profile: MichiDacProfile | None,
    runtime_evidence: tuple[RuntimeCapabilityEvidence, ...],
    current_context_fingerprint: str,
) -> CapabilityDecision:
    current = [
        e for e in runtime_evidence
        if e.pcm == pcm and e.context_fingerprint == current_context_fingerprint
    ]
    if current:
        winner = max(current, key=lambda e: int(e.authority))
        profile_claim = bool(profile and pcm in profile.verified_pcm)
        return CapabilityDecision(
            supported=winner.supported,
            authority=winner.authority,
            reason=f"Current runtime evidence: {winner.authority.name}",
            contradicted_profile=profile_claim and not winner.supported,
        )
    if profile and pcm in profile.verified_pcm:
        return CapabilityDecision(
            supported=None,
            authority=EvidenceAuthority.PROFILE,
            reason="Profile says verified historically; current support remains unknown until runtime qualification.",
        )
    return CapabilityDecision(None, None, "No current evidence for tuple.")


@dataclass(frozen=True, slots=True)
class VolumeSafetyLimits:
    comfort_max_db_x100: int | None = None
    safety_min_db_x100: int | None = None
    safety_max_db_x100: int | None = None

    def clamp(self, requested_db_x100: int) -> int:
        out = requested_db_x100
        if self.safety_min_db_x100 is not None:
            out = max(out, self.safety_min_db_x100)
        if self.safety_max_db_x100 is not None:
            out = min(out, self.safety_max_db_x100)
        return out


@dataclass(frozen=True, slots=True)
class VolumePlan:
    mode: VolumeMode
    allow_pipeline_volume: bool
    target_device_db_x100: int | None
    mutates_samples: bool
    reason: str


def plan_volume(
    mode: VolumeMode,
    *,
    strict_direct: bool,
    hardware_control: DeviceVolumeControl | None,
    requested_device_db_x100: int | None = None,
    limits: VolumeSafetyLimits | None = None,
) -> VolumePlan:
    if mode is VolumeMode.FIXED:
        return VolumePlan(mode, False, None, False, "Fixed output: pipeline gain forbidden.")

    if mode is VolumeMode.DEVICE_HARDWARE:
        if hardware_control is None or hardware_control.validate():
            raise ValueError("Device hardware volume requested without a validated control mapping")
        if requested_device_db_x100 is None:
            raise ValueError("Device hardware volume requires a dB target")
        target = requested_device_db_x100
        if limits is not None:
            target = limits.clamp(target)
        target = max(hardware_control.min_db_x100, min(target, hardware_control.max_db_x100))
        return VolumePlan(mode, False, target, False, "ALSA device control; PCM samples unchanged.")

    if mode is VolumeMode.DSP_SOFTWARE:
        if strict_direct:
            # Strict Direct may still deliberately allow DSP volume only if the
            # caller changes the signal-integrity goal. It must never masquerade
            # as bit-perfect/direct.
            return VolumePlan(mode, True, None, True, "Software gain explicitly mutates samples; direct integrity is not VERIFIED.")
        return VolumePlan(mode, True, None, True, "Software gain mutates samples.")

    raise AssertionError(mode)


@dataclass(frozen=True, slots=True)
class GstClockObservation:
    sink_provides_clock: bool | None
    sink_clock_is_pipeline_clock: bool | None
    slave_method: str | None
    resampler_present: bool


@dataclass(frozen=True, slots=True)
class ClockAudit:
    blocker: bool
    unknown: bool
    reasons: tuple[str, ...]


def audit_gstreamer_clock(obs: GstClockObservation, *, strict_direct: bool) -> ClockAudit:
    reasons: list[str] = []
    blocker = False
    unknown = False

    if obs.resampler_present:
        blocker = strict_direct
        reasons.append("audioresample is present in strict direct path")

    if obs.slave_method == "resample":
        blocker = strict_direct
        reasons.append("GstAudioBaseSink slave-method=resample can alter sample timing by resampling")
    elif obs.slave_method is None:
        unknown = True
        reasons.append("sink slave-method not observed")

    if obs.sink_provides_clock is None or obs.sink_clock_is_pipeline_clock is None:
        unknown = True
        reasons.append("pipeline/sink clock authority not fully observed")

    return ClockAudit(blocker, unknown, tuple(reasons))


@dataclass(frozen=True, slots=True)
class SignalObservation:
    decoded: PcmTuple | None
    engine_effective: PcmTuple | None
    device_negotiated: PcmTuple | None
    dsp_active: bool
    software_volume_active: bool
    resampling_observed: bool
    remix_observed: bool
    evidence_complete: bool
    contradiction: bool = False


def classify_signal_truth(obs: SignalObservation) -> SignalTruthVerdict:
    if obs.contradiction:
        return SignalTruthVerdict.CONTRADICTED
    if not obs.evidence_complete or not all((obs.decoded, obs.engine_effective, obs.device_negotiated)):
        return SignalTruthVerdict.UNKNOWN
    if obs.resampling_observed or obs.decoded.rate_hz != obs.device_negotiated.rate_hz:
        return SignalTruthVerdict.RESAMPLED
    if obs.remix_observed or obs.decoded.channels != obs.device_negotiated.channels:
        return SignalTruthVerdict.REMIXED
    if obs.dsp_active or obs.software_volume_active:
        return SignalTruthVerdict.DSP

    # Container adaptation is not automatically destructive when significant
    # sample precision is preserved. This verdict deliberately differs from a
    # simplistic 'format string equality' test.
    exact_signal = (
        obs.decoded.rate_hz == obs.engine_effective.rate_hz == obs.device_negotiated.rate_hz
        and obs.decoded.channels == obs.engine_effective.channels == obs.device_negotiated.channels
        and obs.decoded.significant_bits == obs.engine_effective.significant_bits == obs.device_negotiated.significant_bits
    )
    if not exact_signal:
        return SignalTruthVerdict.UNKNOWN

    if (
        obs.decoded.container_bits != obs.engine_effective.container_bits
        or obs.engine_effective.container_bits != obs.device_negotiated.container_bits
        or obs.decoded.format_name != obs.device_negotiated.format_name
    ):
        return SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
    return SignalTruthVerdict.DIRECT


def classify_transition(
    current: PcmTuple,
    next_: PcmTuple,
    *,
    current_transport: str = "pcm",
    next_transport: str = "pcm",
) -> TransitionKind:
    if current_transport != next_transport:
        return TransitionKind.TRANSPORT_CHANGE_REQUIRED
    if current == next_:
        return TransitionKind.SAME_TUPLE_GAPLESS_ELIGIBLE
    return TransitionKind.REOPEN_REQUIRED

```

---

# 354. V3.2 EXECUTABLE REFERENCE TESTS

```python
import pytest

from premium_contract import (
    CapabilityDecision,
    DeviceVolumeControl,
    DsdStrategy,
    EvidenceAuthority,
    GstClockObservation,
    MichiDacProfile,
    PcmTuple,
    ProfileMatch,
    ProfileTier,
    RuntimeCapabilityEvidence,
    SignalObservation,
    SignalTruthVerdict,
    TransitionKind,
    VolumeMode,
    VolumeSafetyLimits,
    audit_gstreamer_clock,
    classify_signal_truth,
    classify_transition,
    plan_volume,
    resolve_pcm_capability,
)


def pcm(fmt="S32_LE", rate=96000, ch=2, container=32, sbits=24):
    return PcmTuple(fmt, rate, ch, container, sbits)


def profile(*tuples, volume=None, tier=ProfileTier.MICHI_VERIFIED):
    return MichiDacProfile(
        profile_id="example",
        schema_version=1,
        tier=tier,
        match=ProfileMatch("1234", "5678"),
        verified_pcm=frozenset(tuples),
        dsd_strategies=frozenset({DsdStrategy.DOP}),
        hardware_volume=volume,
        lab_matrix_hash="abc" if tier is ProfileTier.MICHI_VERIFIED else None,
    )


def test_verified_profile_requires_lab_matrix_hash():
    p = MichiDacProfile("x", 1, ProfileTier.MICHI_VERIFIED, ProfileMatch("1", "2"))
    assert "verified profile requires lab_matrix_hash" in p.validate()


def test_profile_cannot_override_current_exact_open_failure():
    t = pcm()
    p = profile(t)
    ev = RuntimeCapabilityEvidence(t, EvidenceAuthority.EXACT_OPEN, False, "ctx")
    d = resolve_pcm_capability(t, p, (ev,), "ctx")
    assert d.supported is False
    assert d.authority is EvidenceAuthority.EXACT_OPEN
    assert d.contradicted_profile is True


def test_old_context_evidence_does_not_override_current_profile():
    t = pcm()
    p = profile(t)
    old = RuntimeCapabilityEvidence(t, EvidenceAuthority.ACTIVE_RUNTIME, False, "old")
    d = resolve_pcm_capability(t, p, (old,), "new")
    assert d.supported is None
    assert d.authority is EvidenceAuthority.PROFILE


def test_no_evidence_is_unknown_not_false():
    d = resolve_pcm_capability(pcm(), None, (), "ctx")
    assert d.supported is None
    assert d.authority is None


def test_container_and_significant_bits_are_distinct():
    t = pcm(container=32, sbits=24)
    assert t.validate() == ()
    assert t.container_bits == 32
    assert t.significant_bits == 24


def test_significant_bits_cannot_exceed_container():
    assert pcm(container=24, sbits=32).validate()


def hw_volume():
    return DeviceVolumeControl("PCM", 0, -9000, 0, 50, True)


def test_fixed_volume_forbids_pipeline_gain():
    p = plan_volume(VolumeMode.FIXED, strict_direct=True, hardware_control=None)
    assert p.allow_pipeline_volume is False
    assert p.mutates_samples is False


def test_hardware_volume_requires_verified_mapping():
    with pytest.raises(ValueError):
        plan_volume(
            VolumeMode.DEVICE_HARDWARE,
            strict_direct=True,
            hardware_control=None,
            requested_device_db_x100=-2000,
        )


def test_hardware_volume_clamps_to_safety_limit():
    p = plan_volume(
        VolumeMode.DEVICE_HARDWARE,
        strict_direct=True,
        hardware_control=hw_volume(),
        requested_device_db_x100=-500,
        limits=VolumeSafetyLimits(safety_max_db_x100=-1200),
    )
    assert p.target_device_db_x100 == -1200
    assert p.allow_pipeline_volume is False


def test_hardware_volume_clamps_to_device_range():
    p = plan_volume(
        VolumeMode.DEVICE_HARDWARE,
        strict_direct=True,
        hardware_control=hw_volume(),
        requested_device_db_x100=500,
    )
    assert p.target_device_db_x100 == 0


def test_software_volume_marks_sample_mutation():
    p = plan_volume(VolumeMode.DSP_SOFTWARE, strict_direct=True, hardware_control=None)
    assert p.allow_pipeline_volume
    assert p.mutates_samples


def test_clock_resample_is_strict_blocker():
    a = audit_gstreamer_clock(
        GstClockObservation(True, False, "resample", False),
        strict_direct=True,
    )
    assert a.blocker


def test_resampler_element_is_strict_blocker():
    a = audit_gstreamer_clock(
        GstClockObservation(True, True, "none", True),
        strict_direct=True,
    )
    assert a.blocker


def test_unknown_clock_authority_is_not_silently_clean():
    a = audit_gstreamer_clock(
        GstClockObservation(None, None, None, False),
        strict_direct=True,
    )
    assert a.unknown


def test_direct_signal_truth():
    t = pcm()
    verdict = classify_signal_truth(SignalObservation(t, t, t, False, False, False, False, True))
    assert verdict is SignalTruthVerdict.DIRECT


def test_container_adaptation_can_remain_direct_signal():
    source = pcm("S24_3LE", container=24, sbits=24)
    engine = pcm("S32_LE", container=32, sbits=24)
    device = pcm("S32_LE", container=32, sbits=24)
    verdict = classify_signal_truth(SignalObservation(source, engine, device, False, False, False, False, True))
    assert verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_dsp_volume_never_reports_direct():
    t = pcm()
    verdict = classify_signal_truth(SignalObservation(t, t, t, False, True, False, False, True))
    assert verdict is SignalTruthVerdict.DSP


def test_rate_change_reports_resampled_if_runtime_rate_differs():
    src = pcm(rate=44100)
    dev = pcm(rate=48000)
    verdict = classify_signal_truth(SignalObservation(src, dev, dev, False, False, True, False, True))
    assert verdict is SignalTruthVerdict.RESAMPLED


def test_incomplete_evidence_is_unknown():
    t = pcm()
    verdict = classify_signal_truth(SignalObservation(t, None, t, False, False, False, False, False))
    assert verdict is SignalTruthVerdict.UNKNOWN


def test_contradiction_wins_over_other_labels():
    t = pcm()
    verdict = classify_signal_truth(SignalObservation(t, t, t, False, False, False, False, True, contradiction=True))
    assert verdict is SignalTruthVerdict.CONTRADICTED


def test_same_tuple_gapless_eligible():
    t = pcm()
    assert classify_transition(t, t) is TransitionKind.SAME_TUPLE_GAPLESS_ELIGIBLE


def test_rate_change_requires_reopen():
    assert classify_transition(pcm(rate=44100), pcm(rate=48000)) is TransitionKind.REOPEN_REQUIRED


def test_dsd_transport_change_requires_transport_rebuild():
    t = pcm()
    assert classify_transition(t, t, current_transport="pcm", next_transport="dop") is TransitionKind.TRANSPORT_CHANGE_REQUIRED

```

---

# 355. V3.2 ENGINEERING VERDICT

The premium DAC integration should not be designed as:

```text
"add an ALSA selector to Settings"
```

It is a complete output subsystem with six independent truths:

```text
1. WHICH physical DAC is this?
2. WHICH current endpoint represents it?
3. WHAT can current Linux/ALSA actually open?
4. WHAT output plan did Michi intend?
5. WHAT did GStreamer/ALSA actually negotiate?
6. DID any processing or fallback alter the signal policy?
```

Roon-class quality comes from making those questions disappear for ordinary users while
remaining answerable for advanced users and developers.

Michi's strongest differentiator should be:

```text
premium automation without opaque certainty
```

A known DAC feels effortless.

An unknown DAC still works safely.

A contradiction is visible.

A failure does not become a silent downgrade.

A profile accelerates correct setup but never overrules reality.

**END OF V3.2 PREMIUM DAC INTEGRATION AMENDMENT**

---

# 356. V3.2 REFERENCE VALIDATION STATUS

The additive V3.2 pure-Python reference harness was executed after writing the contracts.

Result:

```text
23 passed
0 failed
```

Covered:

```text
verified profile requires hardware matrix provenance
profile cannot override current exact-open failure
stale environment evidence does not masquerade as current
unknown capability remains unknown
container vs significant bits
Fixed volume forbids pipeline gain
hardware volume requires validated control mapping
hardware volume safety/device clamping
software volume marks sample mutation
GStreamer slave resample is Strict blocker
explicit resampler is Strict blocker
unknown clock authority remains unknown
Direct Signal Truth
container-adapted direct signal classification
DSP volume cannot report Direct
runtime rate mismatch reports Resampled
incomplete evidence reports Unknown
contradiction has priority
same-tuple gapless eligibility
rate change requires reopen
PCM/DoP transport change requires transport rebuild
```

This test count is additive to V3 and V3.1 reference validation.

It is not physical-hardware evidence.

---

# 357. V3.2 DSD RESEARCH ADDENDUM — GSTREAMER 1.24+ CHANGES THE DESIGN SPACE

Upstream GStreamer added first-class DSD representation to `GstAudio` in 1.24.

Relevant runtime facts:

```text
media type: audio/x-dsd
GstDsdInfo / GstDsdFormat exist in 1.24+
alsasink accepts audio/x-dsd in current upstream documentation
dsdconvert changes DSD grouping/byte representation without changing rate/channels
```

This means Michi MUST NOT hard-code the assumption:

```text
DSD source → PCM-like carrier or PCM conversion before alsasink
```

Instead the planner must discover the actual runtime path.

Required DSD runtime capability snapshot:

```python
@dataclass(frozen=True)
class GstDsdRuntimeCapability:
    gstreamer_version: tuple[int, int, int]
    gst_audio_dsd_api_available: bool
    alsasink_accepts_audio_x_dsd: bool
    dsdconvert_available: bool
    source_demux_path_available: bool
    source_preserves_dsd: bool | None
```

Native DSD candidate is allowed to proceed to qualification only if:

```text
GStreamer runtime can represent DSD
AND the source path preserves DSD instead of decoding to float PCM
AND alsasink current caps admit a compatible DSD representation
AND ALSA/kernel expose a native DSD format for this endpoint
AND exact-open/runtime hardware evidence succeeds
```

A GStreamer version check alone proves nothing about the DAC.

A DAC profile alone proves nothing about the current GStreamer source chain.

---

# 358. DSD SOURCE-CHAIN TRAP — DECODER SELECTION CAN DESTROY NATIVE INTENT

The existence of a DSF demuxer is not enough.

Some decoder paths can convert DSD to PCM.

Therefore a Native DSD session must inspect the negotiated source chain and reject a
pipeline that silently becomes `audio/x-raw` PCM before the native-output stage.

Required invariant:

```text
requested transport: NATIVE_DSD

if decoded/effective media type becomes audio/x-raw PCM
→ native_dsd_claim = BROKEN
→ either fail closed or execute an explicitly permitted PCM_CONVERSION plan
→ never continue while labelling output Native DSD
```

Required runtime evidence:

```text
source container
selected demuxer/parser/decoder elements
post-source negotiated media type
DSD format/grouping
DSD rate
channels
alsasink negotiated media type
ALSA native format
```

---

# 359. DoP MUST REMAIN A DISTINCT IMPLEMENTATION WORKSTREAM

Native `audio/x-dsd` support does not automatically provide DoP framing.

Michi MUST NOT infer:

```text
alsasink supports DSD
therefore DoP works
```

DoP requires a separately proven framing path.

The R30 lab therefore splits into:

```text
R30A_NATIVE_DSD
R30B_DOP_FRAMING
R30C_DSD_TO_PCM
```

Promotion of one does not promote the others.

---

# 360. PLAYBIN3 DIRECT-SINK SEAM IS UPSTREAM-SUPPORTED

GStreamer `playbin3` explicitly allows an application-supplied `audio-sink`.

It also allows a sink `GstBin` with a ghost pad, which gives Michi a migration path that
does not require discarding the mature M11.3 `playbin3` transport.

Canonical implementation consequence:

```text
KEEP:
existing playbin3 transport/pump/bus lifecycle

ADD:
Direct session → construct explicit Michi sink/bin → set playbin3 audio-sink

INSPECT:
negotiated caps and sink runtime
```

This is now the preferred first Direct implementation strategy.

A fully custom decode pipeline is NOT the default V3.2 plan.

It becomes justified only if experiments show that playbin3 inserts or forces behavior
that prevents Michi's required invariants.

---

# 361. KERNEL QUIRKS — UPSTREAM FIRST, PRODUCT MAGIC LAST

Current Linux kernel documentation explicitly describes `snd-usb-audio` quirk controls
and notes that some quirk options are intended for testing/development, with proper
support expected upstream when a device requires a workaround.

Michi policy therefore tightens to:

```text
known device problem
→ reproduce
→ capture environment/evidence
→ identify kernel/driver layer
→ test one scoped hypothesis in Michi Audio Lab
→ if driver quirk is genuinely required, prepare upstream-quality report/patch path
```

Never normalize a lab-only module parameter into hidden product configuration.

This is especially important for:

```text
implicit feedback
runtime PM
DSD raw quirks
interface reset behavior
fixed-rate quirks
mixer quirks
```

---

# 362. V3.2 SOURCE REGISTER ADDENDUM

Additional upstream sources used by sections 357–361:

```text
https://gstreamer.freedesktop.org/documentation/playback/playbin3.html
https://gstreamer.freedesktop.org/documentation/audio/gstdsd.html
https://gstreamer.freedesktop.org/documentation/dsd/index.html
https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html
https://gstreamer.freedesktop.org/releases/1.24/
https://cdn.kernel.org/doc/html/latest/sound/alsa-configuration.html
```

---

# 363. V3.2 FINAL PROMOTION RULE

The product target is now:

```text
Michi Premium DAC Integration
=
Roon-class ergonomics
+
Linux-native explicit evidence
+
Michi-owned device profiles
+
Michi-owned hardware regression
+
no telemetry requirement
+
no silent degradation
```

A polished DAC card is not completion.

A working `alsasink` is not completion.

A purple/green quality badge is not completion.

Completion means the user can connect a DAC and Michi can answer — correctly and with
provenance — all of these questions:

```text
What is it?
Is this the same physical device as before?
Which endpoint is it using now?
What does current hardware/driver say it can do?
What did the profile recommend?
What did Michi request?
What did GStreamer actually produce?
What did ALSA actually negotiate?
Was software gain active?
Was resampling active?
Was channel remix active?
Which clock policy was active?
Did the DAC need a device-specific transition workaround?
Did a fallback occur?
Is the current claim verified, historical, unknown, or contradicted?
```

Only then is the integration premium in the engineering sense.

---

# 364. STRICT ALSA EXACT-OPEN — NO APPROXIMATE RATE ACCEPTANCE

The qualification adapter must distinguish:

```text
"Can ALSA find something near 96 kHz?"
```

from:

```text
"Can this exact hw endpoint open this exact PCM tuple without rate conversion?"
```

Only the second question is relevant to Strict Direct qualification.

Canonical probe plan:

```python
class ProbeRatePolicy(Enum):
    EXACT_ONLY = "exact_only"
    NEAR_ALLOWED = "near_allowed"


@dataclass(frozen=True, slots=True)
class ExactPcmProbePlan:
    alsa_device: str
    pcm: PcmTuple
    rate_policy: ProbeRatePolicy = ProbeRatePolicy.EXACT_ONLY
    disable_rate_resample: bool = True
```

Strict validation:

```text
alsa_device starts with hw:
rate policy = EXACT_ONLY
ALSA rate resampling disabled
format exact
channels exact
rate exact
```

The adapter MUST NOT turn a `*_near()` result into exact capability evidence.

---

# 365. ALSA RATE RESAMPLING MUST BE EXPLICITLY DISABLED IN STRICT PROBES

ALSA exposes:

```text
snd_pcm_hw_params_set_rate_resample(..., 0)
```

for restricting the configuration to real hardware rates.

Strict qualification sequence should include this restriction before committing a
candidate configuration.

Conceptual sequence:

```text
snd_pcm_open("hw:...")
→ hw_params_any
→ set_rate_resample(..., 0)
→ set_access exact policy
→ set_format exact
→ set_channels exact
→ set_rate exact
→ apply hw_params
→ read back selected params
→ read rate_num/rate_den
→ read significant bits
→ record result
→ close
```

If an API/backend cannot express exact rate restriction, the result is not promoted to
`EXACT_OPEN` authority.

---

# 366. NEVER USE `rate_near` AS PROOF OF NATIVE-RATE SUPPORT

`set_rate_near()` is useful for applications willing to accept approximation.

Strict Direct is not such a case.

Example:

```text
requested = 44100
near result = 48000
```

That is:

```text
44100 unsupported under strict policy
```

not:

```text
44100 supported approximately
```

A conversion-capable profile may use a different planner path, but it must be labelled
as conversion/resampling.

---

# 367. POST-COMMIT READBACK IS PART OF THE PROOF

Calling setters successfully is not the final evidence.

After `snd_pcm_hw_params()` selects one configuration, record:

```text
access
format
subformat
channels
rate numerator/denominator
container width
significant bits
period size/time
buffer size/time
monotonic timestamp capability
perfect-drain capability
```

The `exact-open` artifact is the selected configuration, not merely the requested tuple.

If requested and selected differ in a forbidden dimension:

```text
qualification fails
```

---

# 368. ALSA SW PARAMS — OBSERVE FIRST, TUNE LATER

Software parameters include concepts such as:

```text
start_threshold
stop_threshold
avail_min
timestamp mode/type
silence threshold/size
```

Do not hard-code audiophile folklore values.

For Stable:

```text
GStreamer/alsasink owns its active PCM handle and runtime policy.
Michi observes the effective sink behavior where APIs expose it.
Lab tools may own a direct ALSA handle for controlled experiments.
```

Future tuning requires a measured failure or optimization target.

---

# 369. XRUN RECOVERY — OPERATIONAL RECOVERY IS NOT EVIDENCE OF PERFECT CONTINUITY

ALSA provides recovery helpers for errors such as:

```text
EPIPE     → underrun/overrun
ESTRPIPE  → suspended stream
```

A backend may recover and keep playing.

Michi evidence must preserve both facts:

```text
backend recovered = true
XRUN/discontinuity risk observed = true
```

Never rewrite history as:

```text
"playback was Direct Verified"
```

merely because recovery succeeded.

Reference:

```python
@dataclass(frozen=True, slots=True)
class RecoveryObservation:
    error_name: str
    recovered: bool
    continuity_proven: bool

    @property
    def degrades_session_integrity(self) -> bool:
        return self.error_name in {"EPIPE", "ESTRPIPE"} and not self.continuity_proven
```

---

# 370. GSTREAMER OWNS ITS ALSA HANDLE — DO NOT FIGHT THE SINK

When playback uses `alsasink`, Michi application code does not own that sink's private
`snd_pcm_t*` handle.

Therefore product runtime MUST NOT attempt to:

```text
call snd_pcm_prepare on a parallel handle to "fix" GStreamer
call snd_pcm_recover on another handle and assume GStreamer recovered
change hw/sw params behind the sink
```

Michi should instead:

```text
observe GStreamer bus/error/discontinuity state
observe ALSA/proc evidence when safely available
classify the failure
restart/rebuild the output session through the canonical transport lifecycle if policy allows
```

Direct ALSA recovery APIs belong in laboratory helpers or a future Michi-owned sink
implementation, not in a side-channel competing with `alsasink`.

---

# 371. DRAIN / END-OF-STREAM — GAPLESS AND TAIL INTEGRITY

ALSA drain semantics require explicit consideration.

Newer ALSA exposes whether hardware supports perfect drain and can configure drain
silencing.

Michi boundary policy:

```python
class StreamBoundaryAction(Enum):
    CHAIN_GAPLESS_NO_DRAIN = "chain_gapless_no_drain"
    RECONFIGURE_AT_BOUNDARY = "reconfigure_at_boundary"
    END_SESSION_DRAIN_ALLOWED = "end_session_drain_allowed"
```

Rules:

```text
same tuple + next track
→ chain/preload next track
→ NO explicit session-ending drain between tracks

different tuple + next track
→ complete current content honestly
→ controlled reconfiguration boundary
→ do not insert arbitrary drain silence as a gapless substitute

no next track / actual session end
→ final drain may be appropriate according to backend semantics
```

---

# 372. PERFECT-DRAIN EVIDENCE IS DIAGNOSTIC, NOT A UNIVERSAL REQUIREMENT

`snd_pcm_hw_params_is_perfect_drain()` reports whether hardware is guaranteed not to use
samples beyond the application pointer.

Use this to understand tail behavior.

Do not reject an otherwise good DAC merely because the capability is absent.

Instead test:

```text
last source sample preservation
unexpected repeated/stale DMA content
extra silence policy
audible click/pop
next-track boundary behavior
```

---

# 373. HARDWARE / DRIVER TIMESTAMPS — HIGH-VALUE LAB EVIDENCE

ALSA status can expose:

```text
trigger timestamp
high-resolution current timestamp
audio timestamp
driver timestamp
delay
available frames
```

These are valuable for:

```text
first-sample timing
transition timing
latency characterization
XRUN timeline correlation
```

But V3.2 does not require Michi product runtime to access GStreamer's private ALSA handle.

Use direct ALSA lab tooling where necessary.

If a future sink implementation exposes equivalent timing safely, promote it through a
new adapter contract rather than reaching into GStreamer internals.

---

# 374. R34 — STRICT EXACT-OPEN / NO-RESAMPLE PROBE

```yaml
schema_version: 1
experiment_id: R34_STRICT_EXACT_OPEN
status: required_before_exact_open_authority_freeze

matrix:
  rates_hz: [44100, 48000, 88200, 96000, 176400, 192000]
  channels: [2]
  formats:
    - S16_LE
    - S24_3LE
    - S32_LE

method:
  - open_hw_endpoint
  - disable_alsa_rate_resample
  - request_exact_format
  - request_exact_channels
  - request_exact_rate
  - commit_hw_params
  - read_back_selected_configuration

forbidden:
  - rate_near_as_success
  - plughw
  - default

pass:
  - supported_tuple_readback_matches_request
  - unsupported_tuple_fails_truthfully
```

---

# 375. R35 — TAIL / DRAIN INTEGRITY

```yaml
schema_version: 1
experiment_id: R35_TAIL_DRAIN_INTEGRITY
status: required_before_gapless_and_eos_seal

fixtures:
  - nonzero_final_samples
  - end_impulse
  - same_tuple_two_track_boundary
  - different_tuple_two_track_boundary

capture:
  - perfect_drain_capability
  - drain_silence_policy_where_observable
  - rendered_tail_capture_if_loopback_available
  - transition_timeline

falsifiers:
  - tail_truncated
  - stale_samples_after_application_pointer
  - extra_drain_gap_between_same_tuple_tracks
  - click_pop_introduced_by_teardown
```

---

# 376. R36 — XRUN RECOVERY TRANSPARENCY

```yaml
schema_version: 1
experiment_id: R36_XRUN_RECOVERY_TRANSPARENCY
status: required_before_recovery_policy_freeze

cases:
  - induced_underrun_lab
  - suspend_resume
  - device_failure_recovery_if_reproducible

pass:
  - recovered_state_is_reported
  - incident_remains_in_evidence
  - session_integrity_not_promoted_to_verified_without_continuity_proof
  - no_infinite_recovery_loop
```

---

# 377. V3.2 REFERENCE HARNESS — SECOND VALIDATION PASS

The executable premium harness was expanded with strict ALSA-probe and stream-boundary
contracts.

Current result:

```text
30 passed
0 failed
```

Additional cases:

```text
strict probe rejects non-hw endpoint
strict probe rejects rate-near policy
strict probe requires ALSA rate-resample disabled
valid exact probe plan passes
same-tuple boundary forbids session drain
different tuple requests controlled reconfiguration
recovered XRUN remains integrity evidence
```

---

# 378. V3.2 ADDITIONAL NO-GO GATES

```text
G-PREM-21
Exact-open uses `rate_near` and promotes the result as native exact support.

G-PREM-22
Exact-open permits ALSA rate resampling while claiming real hardware-rate support.

G-PREM-23
Requested hw_params are recorded without post-commit selected-parameter readback.

G-PREM-24
A recovered XRUN is erased from Signal Truth/session evidence.

G-PREM-25
Michi manipulates a side ALSA handle to repair GStreamer's private playback PCM state.

G-PREM-26
Same-tuple gapless playback performs a session-ending drain between tracks.

G-PREM-27
Tail/drain behavior is assumed correct without R35 when a backend/device issue is observed.
```

---

# 379. V3.2 SOURCE REGISTER — ALSA STREAM INTEGRITY ADDENDUM

```text
https://www.alsa-project.org/alsa-doc/alsa-lib/pcm.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___h_w___params.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___s_w___params.html
https://www.alsa-project.org/alsa-doc/alsa-lib/group___p_c_m___status.html
https://gstreamer.freedesktop.org/documentation/audio/gstaudiobasesink.html
```

**V3.2 now treats playback continuity, exact rate, tail integrity, and recovered failures
as evidence problems—not merely backend implementation details.**

---

# 380. MICHI-NATIVE DAC CONTROL PLANE — SEAM FOR MICHI HARDWARE, NOT A USB REQUIREMENT

Because the wider Michi ecosystem may eventually include Michi-controlled hardware,
V3.2 reserves a clean control-plane seam without contaminating generic USB DAC support.

Generic third-party USB DAC path:

```text
udev/sysfs + ALSA PCM + ALSA CTL/Mixer + snd-usb-audio evidence
```

Future Michi-owned endpoint path MAY additionally expose:

```text
model / hardware revision
firmware version
current physical sample rate
clock-lock state
hardware volume in dB
mute
standby/power state
selected input/output mode
thermal/fault status where meaningful
```

Canonical rule:

```text
Michi-native control-plane evidence is an additional device witness.
It does not overwrite contradictory current ALSA/kernel runtime evidence.
```

Example:

```text
Michi endpoint API says 192 kHz locked
ALSA hw_params says 96 kHz
→ CONTRADICTED
→ preserve both
→ do not invent a winner unless the evidence model defines which physical stage each
  witness measures
```

This seam is POST-PCM-STABLE unless a Michi hardware product requires it earlier.

Do not make generic DAC support depend on a network service, account, cloud, or telemetry.

---

# 381. FINAL V3.2 DOCUMENT / REFERENCE INTEGRITY

At this revision:

```text
V3.2 document line count: >17k
V3.2 Markdown fences: balanced
V3.2 Python reference blocks: syntax checked
V3.2 H1 duplicates: 0 in amendment region
Premium reference harness: 30 passed / 0 failed
```

The 30 tests are domain/reference validation only.

They do not replace:

```text
integration tests against current Michi main
Linux virtual-stack tests
USB gadget tests
physical DAC qualification
multi-hardware Michi Verified matrix
```

The next implementation authority remains the smallest execution slice whose prerequisites
are satisfied.

Do not ask OpenCode to implement V3.2 in one monolithic PR.

Recommended execution order:

```text
DISC-001..005                 identity/discovery foundation
→ DAC-PREMIUM-001             premium domain/profile truth
→ DAC-PREMIUM-002             ALSA control observation
→ DAC-PREMIUM-003             volume policy
→ DAC-PREMIUM-005             output planner
→ DAC-PREMIUM-004             GStreamer Direct sink seam
→ R24 + R34                   clock + exact-open falsification
→ DAC-PREMIUM-006             Signal Truth
→ DAC-PREMIUM-007             premium UI
→ R25/R35/R36                 transition/tail/recovery seal
→ DAC-PREMIUM-008             signed profiles
→ DAC-PREMIUM-009             Michi Verified lab program
→ R30                         DSD/DoP only when PCM foundation is sealed
```

This sequencing prevents premium UI or device databases from getting ahead of playback
truth.

---

# 382. V3.3 — CROSS-PLAYER PREMIUM QUALITY BENCHMARK

V3.2 used Roon as the main product-quality reference. V3.3 deliberately broadens the benchmark so Michi does not inherit one application's assumptions or blind spots.

The comparison set is intentionally small:

```text
Roon
Audirvāna
HQPlayer
JRiver Media Center
foobar2000
```

These products are not treated as feature checklists. Each is inspected for the **few engineering practices that materially improve local DAC playback**. Michi adopts a practice only when it passes §0C.

The target is therefore not:

```text
Roon + Audirvāna + HQPlayer + JRiver + foobar2000 features combined
```

The target is:

```text
best proven practice from each
        ↓
filtered through Michi architecture
        ↓
small coherent DAC subsystem
        ↓
stronger evidence + safer defaults + lower complexity
```

---

# 383. BENCHMARK MATRIX — WHAT MICHI SHOULD LEARN, AND WHAT IT MUST NOT IMPORT

| Reference | High-value lesson | Michi adoption | Explicit non-adoption for Stable |
|---|---|---|---|
| **Roon** | automatic device-oriented setup, distinct Fixed/Device/DSP volume semantics, honest Signal Path, problem-solving settings rather than mandatory tweaking, hardware regression culture | `Michi Signal Truth`, profile-assisted setup, Fixed/qualified hardware volume, evidence-first device knowledge, Michi Verified | RAAT cloning; zone/network architecture inside the local DAC workstream; broad DSP surface |
| **Audirvāna** | shortest-path philosophy, direct/exclusive DAC access, pre-decoding/prebuffering to reduce runtime work, DAC-aware output formatting, sample-rate transition tuning | short Direct path, bounded prebuffer experiment, transition-specific mute/resync only when measured necessary, no desktop mixer in Direct | subjective “computer optimization” claims as facts; scheduler/power tweaks without measurements; exposing many low-level knobs by default |
| **HQPlayer** | deep awareness of DAC-specific behavior, explicit output mode/rate handling, maintained DAC identification/correction knowledge, hardware-oriented development and measurements | stronger model/profile fingerprinting, versioned hardware knowledge, lab matrices, precise native-output classification | 70+ filters/modulators, DAC correction DSP, mandatory upsampling, conversion-centric playback as Stable DAC scope |
| **JRiver** | explicit Exclusive Access semantics, native rate/bit-depth control, failure when exclusivity cannot be obtained instead of pretending it was obtained, observable Audio Path behavior | Direct acquisition must be explicit; `EBUSY`/open failure is visible; no silent downgrade; native-rate policy | broad media-center configurability; global output-format matrices unrelated to native DAC playback |
| **foobar2000** | output backend modularity, exclusive output as a separable transport concern, event-driven compatibility work and isolation of risky output code | retain `AudioPort` boundaries, keep DAC policy outside transport, isolate backend-specific behavior, regression-test seek/pause/stop and USB edge cases | plugin sprawl; making users assemble the critical DAC path from optional components |

No row authorizes a feature by itself. It supplies evidence for an engineering principle; §0C decides whether the principle belongs in Stable.

---

# 384. ROON — KEEP THE DEVICE-INTEGRATION DISCIPLINE

Roon remains the strongest benchmark for **device integration UX and signal transparency**, not because every internal choice is applicable to Michi.

High-value lessons retained:

```text
a recognizable DAC should feel like a known product, not a raw ALSA string
default setup should be correct without requiring an audiophile tutorial
Fixed / Device / DSP volume are different signal semantics
advanced limits/workarounds exist to solve actual device problems
signal processing must be visible to the user
hardware knowledge must be backed by access to real devices where possible
```

Michi refinement over the benchmark remains unchanged:

```text
profile knowledge can suggest
runtime evidence decides
contradiction is shown, never hidden
```

This prevents a stale device database from becoming more authoritative than the current kernel/driver/DAC negotiation.

---

# 385. AUDIRVĀNA — ADOPT THE SHORTEST-PATH DISCIPLINE, NOT AUDIOPHILE FOLKLORE

Audirvāna's strongest transferable idea is architectural: local playback should minimize unnecessary layers between decoded media and the DAC. Its current product documentation emphasizes direct/exclusive access, bypass of the normal OS mixer, extended buffering/pre-processing before playback, and a stream prepared for the connected converter.

For Michi, translate that into testable requirements:

```text
DIRECT means a known physical ALSA endpoint, not merely a preferred desktop sink
no hidden desktop mixer in the Direct path
no resampling merely to make transitions convenient
format packing/significant-bit handling is explicit
prebuffering is bounded and measured, not mystical
transition latency workaround is per-device evidence, not a global delay
```

## 385.1 Prebuffering — bounded experiment only

Audirvāna preloads/decode-processes audio ahead of playback to reduce runtime activity. This is worth testing, but Michi MUST NOT assume that “more memory playback sounds better.”

Stable rule:

```text
prebuffering MAY improve operational robustness
prebuffering MUST NOT be marketed or classified as a signal-quality improvement without evidence
prebuffer size MUST remain bounded
large files / streams MUST degrade gracefully to streaming decode
prebuffering MUST NOT delay playback unreasonably
```

The research question is practical:

```text
Does bounded prebuffering measurably reduce XRUN risk / scheduling pressure
without harming start latency, memory use, gapless behavior or cancellation?
```

If not, keep the existing streaming path.

## 385.2 No SysOptimizer clone

Michi Stable MUST NOT add CPU-priority, daemon-killing, power-supply, scheduler, IRQ-affinity or “silent computer” modes simply because an audiophile product offers optimization controls.

Such changes are allowed only as lab experiments when there is a measurable failure mode and reproducible improvement. They are not DAC features by default.

---

# 386. HQPLAYER — LEARN HARDWARE DISCIPLINE, REJECT PROCESSING COMPLEXITY

HQPlayer is valuable as a reference precisely because it sits at the opposite end of the processing spectrum from Michi Stable. It demonstrates serious DAC-specific engineering, explicit output rates/modes, maintained device detection, hardware measurements and DAC-specific correction knowledge.

The lesson Michi should import is **hardware specificity**, not the processing surface.

Adopt:

```text
DAC model matters
firmware/environment matters
output mode/rate must be explicit
hardware knowledge must be versioned
test matrices should include actual device behavior
new releases can invalidate old assumptions
```

Do not adopt for Stable:

```text
large selectable filter catalog
large modulator catalog
mandatory PCM -> high-rate PCM conversion
mandatory PCM -> SDM conversion
DAC correction DSP
user-facing algorithm combinatorics
```

Those are valid HQPlayer product goals. They are not necessary to make Michi's DAC integration excellent.

Michi Stable optimizes **native playback certainty** before optional signal processing.

---

# 387. JRIVER — EXCLUSIVE ACCESS MUST HAVE HARD FAILURE SEMANTICS

JRiver documents an important behavior that matches Michi's fail-closed philosophy: when an application requests exclusive access and another client owns the device, exclusive acquisition can fail. That failure is preferable to silently changing the requested playback semantics.

For Michi Direct:

```text
request Direct target
        ↓
open exact physical endpoint
        ↓
SUCCESS -> Direct is real
FAIL EBUSY / permission / negotiation
        ↓
Direct is unavailable
        ↓
show reason
        ↓
user may explicitly choose Shared
```

Forbidden:

```text
Direct requested
        ↓
physical endpoint unavailable
        ↓
auto-route through PipeWire/shared sink
        ↓
continue displaying Direct / bit-perfect
```

This is both an audio-integrity requirement and a trust requirement.

---

# 388. FOOBAR2000 — BACKEND MODULARITY WITHOUT PLUGIN-SPRAWL UX

foobar2000's history of separate output implementations and compatibility fixes reinforces two Michi decisions:

```text
backend-specific behavior belongs behind a narrow transport boundary
output lifetime bugs deserve isolated regression tests
```

Its WASAPI work has historically dealt with event-driven output, seek/pause timing, USB Audio Class compatibility, channel layouts and isolation. The lesson is not that Michi needs interchangeable user-installed DAC plugins. The lesson is that **transport code must remain replaceable and testable without leaking backend semantics into the application domain**.

Therefore:

```text
AudioPort remains narrow
AudioOutputPolicy / DAC Profile / Signal Truth remain above it
GStreamer-specific mechanics remain in the GStreamer adapter
ALSA probing/control mechanics remain in ALSA adapters/helpers
QML never acquires transport authority
```

---

# 389. MICHI PREMIUM THESIS — QUALITY SYNTHESIS

The cross-player benchmark resolves to five product principles:

```text
1. ROON-CLASS DEVICE CLARITY
   The user knows what DAC is active and what the signal path is doing.

2. AUDIRVĀNA-CLASS PATH DISCIPLINE
   Direct local playback uses the shortest practical verified path.

3. JRIVER-CLASS EXCLUSIVITY SEMANTICS
   Exclusive/Direct either succeeds or visibly fails. It never becomes a label.

4. FOOBAR-CLASS TRANSPORT ISOLATION
   Backend mechanics stay replaceable and testable behind a narrow seam.

5. HQPLAYER-CLASS HARDWARE SERIOUSNESS
   Device-specific behavior is measured and versioned, without importing DSP complexity.
```

Michi's own differentiator is then:

```text
EVIDENCE PRECEDENCE
+
NATIVE MICHI HARDWARE CONTROL PLANE
+
PREMIUM DEFAULTS WITH MINIMAL USER TUNING
```

This is the design identity. New DAC work should make this synthesis more reliable, not broader.

---

# 390. PRE-STABLE M11.4 QUALITY BUDGET — IMPLEMENT NOW, FREEZE BEFORE PLAYER STABLE

To keep the plan implementable, the DAC work being implemented **now during pre-Stable development** is bounded to a small mandatory core. This core is a prerequisite for Player Stable.

## Mandatory pre-Stable M11.4 core

```text
USB DAC discovery
stable identity / truthful endpoint correlation
one canonical selected DAC
a clear Shared vs Direct distinction
GStreamer -> ALSA hw Direct path
exact PCM capability qualification
source-native sample-rate switching
correct significant-bit reporting
FIXED output that provably remains unity gain
no hidden resampling / remix / software volume in verified Direct
Signal Truth with requested/effective/negotiated evidence
hotplug loss + reconnect without stale-device lies
controlled same-tuple continuity / gapless conformance
first-sample and tail integrity on verified hardware
bounded diagnostics
premium Device Setup with safe defaults
```

## Conditional promotion after the mandatory PCM vertical; may still happen pre-Stable

```text
DEVICE_HARDWARE volume
Native DSD
DoP
per-device resync delay
bounded preload strategy
Michi-native vendor control extensions
```

Each conditional item ships only after its own hardware/evidence gate passes. These items MAY be implemented before Player Stable once the mandatory PCM Direct vertical is green; they are not deferred by default. Failure to promote one of them MUST NOT block a high-quality PCM Direct 1.0 unless the product milestone explicitly changes.

## Explicitly outside the current M11.4 mandatory DAC quality budget

```text
upsampling suites
selectable audiophile filter catalogs
noise-shaper/modulator catalogs
room correction
convolution
crossfeed
PEQ / Audio Lab
DAC correction DSP
system-wide scheduler/power “optimization”
IRQ tuning UI
multi-DAC synchronization
network audio protocol redesign
community profile editing marketplace
vendor-control support for arbitrary third-party protocols
```

This section overrides older scheduling language as well as aspirational scope. “Outside the current M11.4 mandatory budget” does not by itself mean post-Stable; only items explicitly labeled POST-STABLE ONLY are deferred beyond the first Stable release.

---

# 391. PREMIUM UX QUALITY GATE — FEWER CONTROLS, BETTER DECISIONS

Device Setup must not become an ALSA control panel.

Normal surface should answer only:

```text
Which DAC is selected?
Is it available?
Is playback Shared or Direct?
What volume mode is active?
What signal is currently reaching it?
Is Michi changing anything?
Is there a problem requiring action?
```

Advanced controls appear **only when the current device/evidence makes them relevant**.

Examples:

```text
resync delay hidden unless transition failures justify it
DSD controls hidden unless DSD is promoted and device evidence exists
hardware volume hidden unless a qualified control exists
rate/bit caps hidden unless needed as compatibility limits
raw ALSA identifiers live in diagnostics, not the primary card
```

Premium UX rule:

```text
AUTO WHEN PROVABLY SAFE
EXPLICIT WHEN SEMANTICS CHANGE
HIDDEN WHEN IRRELEVANT
DIAGNOSTIC WHEN TECHNICAL
```

No setting may exist merely because a competing application has an equivalent setting.

---

# 392. OBJECTIVE QUALITY SCORECARD — HOW MICHI EARNS “PREMIUM”

Feature count is removed from acceptance. Quality is judged with objective gates.

For a device entered into **Michi Verified**, the candidate build must demonstrate:

```text
IDENTITY
[ ] one physical DAC -> one canonical device
[ ] identity survives ordinary reconnect/reboot according to available stable identifiers
[ ] no stale ALSA card-index persistence

DIRECT PATH
[ ] Direct opens the intended physical endpoint
[ ] failed exclusivity/direct acquisition is visible
[ ] no silent Shared fallback while claiming Direct

SIGNAL
[ ] requested rate == negotiated rate for every verified PCM tuple
[ ] significant bits are reported correctly
[ ] no hidden resampler/remixer/software gain in VERIFIED path
[ ] Signal Truth explains every intentional transformation

VOLUME
[ ] FIXED cannot attenuate through playbin/software volume
[ ] hardware volume is exposed only after control qualification
[ ] reconnect never restores an unsafe gain blindly

TRANSITIONS
[ ] native-rate family changes use controlled reopen when required
[ ] verified transitions have no first-sample truncation
[ ] verified end-of-track behavior has no tail truncation
[ ] same-tuple gapless passes the golden fixture

RECOVERY
[ ] unplug produces unavailable state, not a ghost device
[ ] reconnect converges to the same canonical identity when evidence supports it
[ ] XRUNs are counted and remain visible even after successful recovery

LONG RUN
[ ] defined soak test completes without unbounded resource growth
[ ] no silent route mutation
[ ] no accumulating stale callbacks/handles
```

A device failing one gate may still work in Michi. It simply does not receive the **Michi Verified** claim for that environment/build.

---

# 393. AI CHANGE PROTOCOL — UPDATE THE PLAN BEFORE THE CODE WHEN THE ANSWER CHANGES

Because this file is intended for constant consultation across context windows, every future DAC change follows a document-first rule.

When an agent discovers that the canonical plan is wrong, incomplete or contradicted by current upstream/runtime evidence:

```text
DO NOT silently work around the document.
DO NOT leave the new truth only in chat.
DO NOT rely on the next agent seeing the previous reasoning.
```

Required sequence:

```text
1. Identify contradiction.
2. Locate affected canonical sections.
3. Gather current upstream/runtime evidence.
4. Apply Michi methodology:
      mayéutica
      -> engineering analysis
      -> falsification
      -> implementation decision
5. Update this .md with:
      decision
      evidence
      implementation consequence
      test consequence
      rollback/kill criterion where empirical
6. Then patch production code.
7. Then update/execute tests.
8. Record validation state truthfully.
```

Every agent hand-off should be recoverable from repository + this file without needing the historical chat.

## 393.1 Question-answer protocol

If the user asks a DAC question rather than requesting code:

```text
REOPEN canonical .md
SEARCH full file
READ governing sections
CHECK current external facts when time-sensitive / uncertain
ANSWER from the current authority
```

If the answer is not in the file, that is a **documentation gap**. Research it and add the conclusion here when it affects implementation.

---

# 394. V3.3 SOURCE REGISTER — CROSS-PLAYER BENCHMARK

Only official vendor/project documentation is used as authority for the benchmark claims below. Community posts may later be used as bug-discovery input, never as normative truth without reproduction.

## Roon

- Roon Labs, **Audio Setup Basics** — device setup, Device/DSP/Fixed volume, advanced settings as problem-solvers.  
  `https://help.roonlabs.com/portal/en/kb/articles/audio-setup-basics`
- Roon Labs, **Signal Path** — explicit philosophy of honest playback-path reporting and recognized hardware presentation.  
  `https://help.roonlabs.com/portal/en/kb/articles/signal-path`
- Roon Labs, **Sound Quality** — exclusive output and visibility of processing in Signal Path.  
  `https://help.roonlabs.com/portal/en/kb/articles/sound-quality`

## Audirvāna

- Audirvāna, **Exclusive Playback Technology** — direct/exclusive DAC access, mixer bypass, extended buffering/pre-processing, DAC-aware prepared stream.  
  `https://audirvana.com/exclusive-playback-technology/`
- Audirvāna Support, **How to play DSD over PCM (DoP) to my device?** — device-specific DoP configuration and carrier constraints.  
  `https://help.audirvana.com/en/support/solutions/articles/202000051129-how-to-play-dsd-over-pcm-dop-to-my-device-`

## HQPlayer / Signalyst

- Signalyst, **HQPlayer Desktop** — explicit large PCM/SDM processing surface and DAC-specific output correction; used here to separate hardware seriousness from processing scope.  
  `https://signalyst.com/hqplayer-desktop/`
- Signalyst, **DAC correction support** — maintained DAC-specific model/output knowledge.  
  `https://signalyst.com/dac-correction-support/`
- Signalyst, **Official news** — continuing DAC detection and NAA/DAC-driver development in 2026.  
  `https://signalyst.com/`

## JRiver

- JRiver Wiki, **Exclusive Access** — explicit exclusive-open semantics, native format control and failure when the device cannot be acquired.  
  `https://wiki.jriver.com/index.php/Exclusive_Access`
- JRiver Wiki, release notes — Audio Path reporting and memory-playback/output compatibility fixes are treated as evidence of sustained output-path regression work, not as a feature requirement.  
  `https://wiki.jriver.com/index.php/Release_Notes_Media_Center_v21_To_v34_(Windows)`

## foobar2000

- foobar2000, **WASAPI output support** — exclusive output, historical event-driven mode and compatibility/regression fixes.  
  `https://www.foobar2000.org/components/view/foo_out_WASAPI`
- foobar2000, **WASAPI shared output** — evidence that shared/exclusive output and resampling behavior should remain explicit, isolated transport concerns.  
  `https://www.foobar2000.org/components/view/foo_out_wasapis`

**Research snapshot:** 2026-09-10. Revalidate time-sensitive product behavior before using this benchmark for future architecture changes.

---

# 395. V3.3 ENGINEERING VERDICT — SMALLER THAN THE COMPETITION, BETTER DEFINED

The intended Michi DAC subsystem is now explicitly **not** a union of audiophile-player features.

The quality target is:

```text
Roon-level clarity
+ Audirvāna-level path discipline
+ HQPlayer-level hardware seriousness
+ JRiver-level exclusive-mode honesty
+ foobar-level backend isolation
------------------------------------------------
= Michi evidence-first DAC integration
```

The implementation remains intentionally constrained around native local playback.

A premium result means:

```text
less guessing
less hidden processing
less configuration
fewer failure ambiguities
fewer unsafe state transitions
more reproducible evidence
better hardware behavior
better explanations when something goes wrong
```

If a proposed feature makes this subsystem harder to reason about without materially improving those properties, **do not add it**.

V3.3 therefore promotes **quality density** over feature density.

---

# 396. V3.5 IMPLEMENTATION SEAL — WHY THIS REVISION EXISTS

V3.5 does not add another DAC feature layer. It closes the remaining degrees of freedom that could cause two competent agents to implement different architectures from the same document.

The following are now explicit and non-negotiable:

```text
one active work-package series
one observed repository baseline
one agent reload entrypoint
one Stable ALSA probe implementation technology
one pre-playback output transaction seam
one volume-policy authority path
one persistence schema migration
one composition-root lifecycle
one GStreamer Direct executor
one QML/bridge wiring model
one automated GO/NO-GO entrypoint
one physical-verification boundary
```

If a future implementation decision still has two materially different reasonable answers, that is a spec defect: stop and update V3.5 before choosing one in code.

---

# 397. V3.5 EXACT FILE PLAN — CREATE / MODIFY / FORBID

This plan is relative to baseline `1b5e3f84d84d45873147ae7ad1a633de086a7e85`. Repository-alignment rules in §0F apply if HEAD differs.

## CREATE

```text
AGENTS.md

docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md

tests/dac/
    test_v34_device_identity.py
    test_v34_registry_convergence.py
    test_v34_alsa_probe_protocol.py
    test_v34_alsa_probe_classification.py
    test_v34_output_profile_repository.py
    test_v34_output_planner.py
    test_v34_output_transaction.py
    test_v34_volume_policy.py
    test_v34_signal_truth.py
    test_v34_disconnect_reconnect.py
    test_v34_audio_output_bridge.py
    test_v34_qml_audio_output.py
    test_v34_packaging.py

src/michi/domain/
    audio_device.py
    audio_output.py
    audio_evidence.py
    volume_policy.py

src/michi/application/
    audio_device_registry.py
    dac_qualification_service.py
    audio_output_profile_service.py
    audio_output_planner.py
    output_session_service.py
    volume_policy_service.py
    output_session_evidence_recorder.py
    audio_output_ports.py

src/michi/infrastructure/audio_devices/
    __init__.py
    udev_observer.py
    sysfs_snapshot.py
    alsa_ctypes.py
    alsa_probe_cli.py
    alsa_probe_adapter.py
    proc_pcm_witness.py
    alsa_control_adapter.py       # created only in DAC-V35-120 or earlier as dormant interface + fake; no unqualified product use

src/michi/infrastructure/gstreamer_dac/
    __init__.py
    strict_sink.py
    direct_output_executor.py
    runtime_inspector.py

src/michi/infrastructure/
    sqlite_audio_output_repository.py

src/michi/presentation/
    audio_output_bridge.py

src/michi/presentation/qml/views/
    AudioOutputSettingsSection.qml

src/michi/presentation/qml/components/
    DacDeviceCard.qml
    DacVolumeControl.qml
    SignalTruthPanel.qml
    DacDiagnosticsDisclosure.qml

src/michi/resources/dac_profiles/
    schema.json
    generic_usb_audio.json

scripts/
    verify_dac_repository_alignment.py
    verify_dac_m11_4.py
```

## MODIFY

```text
pyproject.toml
src/michi/application/ports.py
src/michi/application/playback_service.py
src/michi/application/audio_engine_registry.py
src/michi/application/audio_engine_service.py            # read-only active-engine seam only if required; never DAC state ownership
src/michi/infrastructure/audio_engines/gstreamer.py
src/michi/infrastructure/audio_engines/__init__.py        # only if exports require it
src/michi/infrastructure/sqlite_settings.py
src/michi/bootstrap/__init__.py
src/michi/presentation/playback_bridge.py                 # preserve command path; friendly typed DAC command errors
src/michi/presentation/qml/views/SettingsView.qml
src/michi/presentation/qml/player/NowPlayingBar.qml       # only if its volume projection needs mode-aware disabled/label behavior

docs/ARCHITECTURE.md
docs/STATUS_MATRIX.md
docs/MASTER_ROADMAP_1.0.md
docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md
docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md              # status/cross-link only; do not prematurely claim M11.5 complete
```

## MUST NOT TOUCH FOR DAC OWNERSHIP

```text
QueueService / domain/queue.py ownership
PlaylistService / domain/playlist.py ownership
PlaybackSessionState ownership
Library identity semantics
Michi AI / Audio Lab production implementation
MPD queue semantics
Qt Multimedia shared/reference semantics except compatibility regression fixes
```

## Naming freeze

Do not create alternative synonymous modules such as:

```text
dac_manager.py
device_manager.py
dac_service.py
output_policy_manager.py
audio_output_profile.py alongside audio_output.py for the same domain type
signal_path_service.py alongside output_session_evidence_recorder.py for the same authority
```

If a V3.5 canonical filename becomes impossible due to a current-HEAD collision, update this section first.

---

# 398. ROOT `AGENTS.md` CONTRACT — REQUIRED FOR OPENCODE CONTEXT RECOVERY

The repository root MUST contain the following semantic contract before `DAC-V35-010` begins.

Canonical content:

```markdown
# Michi Music Player — agent contract

## DAC work: mandatory canonical specification

For any task that touches USB DACs, ALSA, GStreamer Direct output, device discovery,
audio output profiles, sample-rate switching, DAC volume, Signal Truth, output
reconnect, bit-perfect claims, or M11.4/M11.5 output guarantees:

1. Open `docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md`.
2. Read §0A–§0K and §396–§410 before changing code.
3. Search that entire file for the exact topic and read the governing sections in full.
4. Run `python scripts/verify_dac_repository_alignment.py` before the first patch of a work package.
5. Execute only `DAC-V35-*` work packages from §0E. Older `DAC-*`, `DISC-*`, `DAC-PREMIUM-*`, V3.2 and V3.3 slices are historical/reference unless V3.5 maps them explicitly.
6. Preserve current ownership: PlaybackSessionService owns sequence/navigation; PlaybackService owns PlaybackState; AudioEngineService owns engine state; DAC/output services must not fork those authorities.
7. Never invent hardware support. Exact runtime evidence outranks profiles and cached claims.
8. Never silently fall back from Direct DAC semantics to Shared/default-speaker semantics.
9. If current HEAD contradicts the V3.5 repository assumptions, update the canonical spec before implementing a new architecture.
10. A green automated suite is not physical DAC verification. Do not claim Michi Verified without the declared hardware matrix.
```

This file is intentionally short. It points the agent to the large external engineering memory instead of attempting to duplicate it.

---

# 399. `DAC-V35-000` — REPOSITORY / AGENT ALIGNMENT SLICE

## Inputs

```text
current git HEAD
V3.5 canonical file
docs/ARCHITECTURE.md
pyproject.toml
bootstrap/application/playback/GStreamer/persistence/QML critical files from §0F
```

## Implementation

1. Add root `AGENTS.md` from §398.
2. Place this file at the canonical `docs/dac/...V3_5.md` path.
3. Add `scripts/verify_dac_repository_alignment.py`.
4. The script records:
   - current HEAD,
   - whether working tree is dirty,
   - existence/hash of canonical critical files,
   - current schema version,
   - current minimum Python/PySide6 versions,
   - whether `AudioEngineSettingsSection` remains separate,
   - whether `PlaybackBridge -> PlaybackService -> AudioPort` is still the volume path,
   - whether GStreamer adapter remains `playbin3`-based.
5. Compare with the V3.5 baseline. Differences are emitted as `CHANGED_ASSUMPTION`, never silently ignored.

## Gate

```text
G-V35-000-A: AGENTS.md present
G-V35-000-B: canonical V3.5 path present
G-V35-000-C: repository alignment report emitted
G-V35-000-D: every changed governing assumption reconciled before next slice
```

---

# 400. `DAC-V35-010` — DEVICE IDENTITY / DISCOVERY CLOSED SLICE

Implement the existing V3 identity rules using the frozen files in §397.

Runtime pipeline:

```text
pyudev event
  -> UdevObserver (infrastructure)
  -> normalized DeviceObservation
  -> AudioDeviceRegistry (application)
  -> correlate USB physical ancestry + ALSA card/PCM sysfs ancestry
  -> publish immutable snapshot/read model
```

Required state per physical DAC:

```text
stable_device_id
identity_confidence
generation
availability
usb vid/pid/bcdDevice
trusted-or-null serial
manufacturer/product strings
physical path when usable
zero-or-more current ALSA bindings
selected intent is separate from availability
```

Generation rule:

```text
every topology-changing remove/re-add/rebind increments or replaces generation
all async probe/control callbacks carry the generation they started under
callback_generation != current_generation -> discard as STALE, no state mutation
```

Do not probe PCM during passive hotplug discovery.

Gate:

```text
same DAC replug -> same stable id when evidence allows
simultaneous identical VID/PID devices -> not merged without trusted identity evidence
card-index renumber -> stable id preserved, binding updated
remove -> unavailable without deleting selected intent
stale delayed observation/probe -> ignored
```

---

# 401. `DAC-V35-020` — EXACT ALSA QUALIFICATION CLOSED SLICE

Implement §13 exactly.

The application adapter must return a typed result, not raw JSON/dicts:

```python
@dataclass(frozen=True, slots=True)
class ExactProbeResult:
    requested: PcmTuple
    negotiated: PcmTuple | None
    disposition: str
    alsa_error_code: int | None
    detail: str | None
    evidence_ref: str
```

`DacQualificationService` decides whether the result can produce capability evidence.

Mapping:

```text
exact open + exact readback               -> supported=True, OPENED/PROBED
explicit exact format/rate rejection      -> supported=False, PROBED
BUSY                                      -> supported=None
REMOVED                                   -> supported=None
TIMEOUT                                   -> supported=None
permission/runtime/protocol failure       -> supported=None
requested != negotiated                   -> negotiation_failed / supported=None or explicit false only when ALSA proved exact mismatch semantics
```

No brute-force matrix at startup.

---

# 402. `DAC-V35-030` — PERSISTENCE / OUTPUT PROFILE CLOSED SLICE

Implement schema v2 from §0I in the same SQLite database and recovery model.

Repository boundary:

```python
class AudioOutputProfileRepository(Protocol):
    def load_profiles(self) -> tuple[AudioOutputProfile, ...]: ...
    def save_profile(self, profile: AudioOutputProfile) -> None: ...
    def load_selection(self) -> AudioOutputSelection: ...
    def save_selection(self, selection: AudioOutputSelection) -> None: ...
    def load_qualification_cache(self, stable_device_id: str) -> tuple[CapabilityEvidence, ...]: ...
    def replace_qualification_cache(self, stable_device_id: str, evidence: tuple[CapabilityEvidence, ...]) -> None: ...
```

`AudioOutputProfileService` is the only caller of authoritative profile/selection mutations. `DacQualificationService` owns cache mutation through an explicit cache port, not by calling profile mutations.

Migration tests MUST cover:

```text
fresh database -> schema v2
v1 database -> v2 preserving all previous authoritative rows
v2 missing authoritative DAC table -> health/provenance failure
qualification-cache loss -> rebuild allowed
LKG/recovery preserves output profiles + selection
future schema version -> fail closed
```

---

# 403. `DAC-V35-040` — OUTPUT PLAN / TRANSACTION CLOSED SLICE

`OutputPlanner` is pure/deterministic. It receives facts; it performs no I/O.

Input minimum:

```text
active_engine_id
selected output profile
selected stable device id
current binding + generation
source audio facts
current capability evidence
user override facts
```

Output minimum:

```text
plan_id
engine_id
stable_device_id
binding generation
path semantics
requested PCM tuple
strict sink specification
volume policy
fallback policy
resync delay
preconditions
evidence references used to decide
```

Planner refusal examples:

```text
selected DAC unavailable
no current ALSA hw binding
active engine != GStreamer for Direct
source sample rate unknown for strict source-native path
exact tuple unsupported or unknown where policy requires proof
binding generation changed
```

`OutputSessionService` implements `PlaybackOutputTransactionPort` and owns prepare/commit/abort/release.

No fallback occurs inside the planner or transaction service unless the persisted profile explicitly selected a fallback kind that allows it. Stable Direct default is STOP.

---

# 404. `DAC-V35-050` — GSTREAMER DIRECT EXECUTOR CLOSED SLICE

The existing `GStreamerAudioPort` remains the mature M11.3 transport adapter. Do not rewrite its GLib pump, generation guard, bus delivery, media acceptance contract, or playback-state convergence.

Add a sidecar executor:

```text
GStreamerDirectOutputExecutor
    -> obtains the currently-open GStreamer provider/port
    -> builds StrictSinkSpec
    -> injects custom playbin3 `audio-sink`
    -> verifies actual graph/properties before media load
    -> captures negotiated/runtime evidence after preroll/play
```

Strict sink baseline:

```text
playbin3
  -> supplied audio-sink bin
      [audioconvert only when explicitly required and configured preservation-safe]
      -> capsfilter exact requested tuple
      -> alsasink device=<current hw binding>
```

Default Direct graph contains **no `audioresample` element**.

If playbin3 or playsink inserts an unexpected resampler/converter that changes rate/channel semantics, the Direct verdict is blocked and Signal Truth becomes `CONTRADICTED`/`RESAMPLED` as applicable.

The executor receives an already-built `OutputPlan`; it does not select devices, policies, formats, or fallbacks.

---

# 405. `DAC-V35-060` — VOLUME AUTHORITY CLOSED SLICE

This slice is a **current pre-Stable M11.4 blocker** even though qualified hardware volume itself is conditional.

Code changes:

```text
PlaybackService:
  replace direct `_audio.set_volume()` policy decision with PlaybackVolumePort
  replace direct `_audio.set_muted()` policy decision with PlaybackVolumePort
  update PlaybackState only after successful AppliedVolume return
  preserve engine-switch lease guards

PlaybackBridge:
  keep set_volume/set_muted as canonical QML intents
  add friendly handling for OutputVolumeLockedError / DeviceControlUnavailableError

VolumePolicyService:
  Shared -> delegates generic commands to AudioPort
  Direct FIXED -> forces/validates unity; rejects non-unity volume request
  Direct HARDWARE -> disabled until qualified control mapping exists
  DSP SOFTWARE -> unavailable in the current M11.4 DAC core (separate work may follow before or after Stable according to the DSP roadmap)

SettingsView/QML:
  remove generic duplicate volume UI from Playback section when DAC volume component is active
  DacVolumeControl binds to playback.volume/muted for canonical effective state plus audioOutput.volumeMode/volumeAdjustable for presentation policy
```

Critical regression test:

```text
active Direct + FIXED
QML attempts playback.set_volume(37)
-> typed locked error
-> GStreamer pipeline volume remains exactly unity
-> PlaybackState.volume remains 100
-> no hardware mixer write
-> no Signal Truth Direct claim is silently retained after an unobserved attenuation
```

---

# 406. `DAC-V35-070` — SIGNAL TRUTH / RUNTIME EVIDENCE CLOSED SLICE

Runtime evidence recorder receives immutable evidence events. It does not infer device identity or policy.

For every active Direct session capture when observable:

```text
source facts
decoded caps
strict plan tuple
GStreamer effective caps
sink element/properties
ALSA negotiated tuple/readback
significant bits
binding generation
clock/slave policy
unexpected resampler/converter presence
runtime errors/XRUN evidence
```

Verdict precedence remains:

```text
CONTRADICTED > RESAMPLED/REMIXED/DSP > DIRECT_CONTAINER_ADAPTED > DIRECT > UNKNOWN
```

No UI “Lossless/Bit-perfect/Direct verified” label may be derived solely from the selected setting.

---

# 407. `DAC-V35-080` — TRANSITION / DISCONNECT / RECONNECT CLOSED SLICE

Required cases:

```text
same tuple next track
cross-rate next track
selected DAC unplug during STOPPED
unplug during PLAYING
replug same physical DAC with different card index
another similar DAC appears while selected one is absent
engine runtime failure while Direct active
application shutdown with Direct session active
```

Hard rules:

```text
no automatic speaker fallback under Stable Direct STOP policy
no reuse of stale ALSA card number
automatic resume only if same stable device + new generation converged + tuple still valid + existing product policy explicitly enables resume
otherwise remain stopped and surface reconnect state
```

Same-tuple gapless work remains bounded by M11.5, but any M11.5 guarantee selected as a Player-Stable requirement is also pre-Stable work. This slice must not fake gapless by global resampling.

---

# 408. `DAC-V35-090` — PREMIUM PRESENTATION CLOSED SLICE

`AudioOutputSettingsSection` is not a technical debug panel.

Normal collapsed DAC card shows:

```text
manufacturer + product (or truthful generic name)
connection/availability
selected vs active state
Direct/Shared path label
current source/device rate when active
volume mode
Signal Truth short verdict
```

Advanced disclosure may show:

```text
stable device id shortened
current ALSA locator (diagnostic, never persisted identity)
VID/PID/bcdDevice
identity confidence
environment fingerprint
capability evidence provenance
runtime sink graph summary
last typed failure
```

UX failure states must be explicit:

```text
Device busy
Device disconnected
Direct requires GStreamer
Format not verified
Output locked at fixed level
Reconnecting
Runtime path contradicted expected plan
```

No raw errno or GStreamer debug string is primary user copy.

---

# 409. `DAC-V35-100/110` — AUTOMATED + PHYSICAL PROMOTION SEAL

Automated completion requires `python scripts/verify_dac_m11_4.py` GO at exact commit.

Physical PCM Direct promotion requires applicable experiments from the existing R19–R29 and R32–R36 corpus plus V3.5 transaction/volume checks.

Minimum physical diversity for a top-tier general claim:

```text
DAC A: mainstream USB Audio Class 2 device
DAC B: materially different vendor/controller/clock/control topology
```

If only one physical DAC is available, wording MUST stay device-scoped.

Artifacts are bound to:

```text
git commit
kernel version
snd-usb-audio module/version-relevant params
alsa-lib version
gstreamer version
PySide6 version
DAC identity facts
spec revision V3.5
```

A later kernel/ALSA/GStreamer change invalidates universal reuse of the old “Verified” badge until the declared requalification policy passes.

---

# 410. V3.5 FINAL OPENCODE HANDOFF CONTRACT

The canonical instruction to OpenCode is **not**:

```text
Implement this entire 18k+ line file in one patch.
```

It is:

```text
You are implementing Michi DAC support NOW on the pre-Stable Michi codebase under V3.5.
Do not wait for Player Stable; M11.4 is a prerequisite for reaching Stable.
Read root AGENTS.md and the canonical V3.5 spec.
Run DAC-V35-000 first.
Then execute exactly one active DAC-V35 work package at a time, in manifest order.
For each package:
  1. align current HEAD,
  2. read governing sections,
  3. list exact files to change,
  4. implement only that ownership slice,
  5. run package gates + existing regressions,
  6. report commit/diff/tests/evidence,
  7. do not begin the next package while a required gate is red.
Never convert an unknown hardware fact into a positive capability claim.
Never silently downgrade Direct semantics.
Never duplicate PlaybackSessionService, PlaybackService, AudioEngineService, or Queue/Playlist authority.
```


### Documentation/status transitions are part of the same commit

```text
Before DAC-V35-010 code:
  docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md -> READY FOR IMPLEMENTATION / V3.5 authority linked

First productive DAC code merged:
  M11.4 -> IN PROGRESS

DAC-V35-100 automated GO:
  M11.4 -> IMPLEMENTED / PHYSICAL QUALIFICATION PENDING
  STATUS_MATRIX + MASTER_ROADMAP updated at same commit

DAC-V35-110 declared physical matrix GO:
  M11.4 -> VERIFIED FOR DECLARED PCM DIRECT MATRIX / FROZEN CORE

M11.5:
  remains NOT STARTED or PARTIAL unless its own gapless/transition guarantees are actually implemented and tested;
  M11.4 completion must never auto-promote M11.5.
```

A code-complete PR that leaves `M11_4_AUDIOPHILE_OUTPUT_DAC.md` saying `NOT STARTED` is NO-GO.

### Definition of “implementation complete”

Software implementation is complete only when:

```text
DAC-V35-000 through DAC-V35-100 are green
all existing audio-engine/playback regressions are green
wheel/package smoke is green
canonical docs/status are updated at the same commit
automated verdict artifact says GO
```

Premium physical integration is complete only when, additionally:

```text
DAC-V35-110 physical promotion gates pass for the declared matrix
no unresolved P0/P1 contradiction exists
Signal Truth matches observed runtime
first-sample/tail/XRUN/reconnect tests meet declared acceptance criteria
```

Hardware volume and DSD/DoP have their own promotion gates and may be pursued during pre-Stable development after the mandatory PCM path is green. Signed remote profile distribution remains POST-STABLE ONLY. None may be smuggled into the mandatory core merely to claim “100%”.

**V3.5 KILLCRITIC verdict:** after this seal, an implementation agent should not need to invent a module name, technology stack, ownership boundary, volume path, persistence schema, composition strategy, UI placement, execution order, or software completion criterion. Remaining uncertainty is intentionally empirical hardware evidence, which no Markdown plan can honestly pre-compute.

