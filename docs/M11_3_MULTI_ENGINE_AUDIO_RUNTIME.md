# M11.3 — Multi-Engine Audio Runtime (contract)

Implementation contract for the multi-engine audio runtime. Status: **DONE /
TESTED / FROZEN** — M11.3A + M11.3B + M11.3C + M11.3D + M11.3E + M11.3F +
M11.3G DONE / TESTED / FROZEN — M11.3 OVERALL TESTED / FROZEN (M11.3G:
engine convergence — selected-first startup, ONE automatic fallback engine
(Qt Multimedia; no fallback chain, no auto-select of GStreamer/MPD, Qt
itself has no alternate), fatal runtime engine loss convergence, safe
explicit-switch recovery, Playback/Queue/resume/restart convergence,
fallback_from semantics, no silent resume, no background polling, shutdown
disables recovery before teardown; M11.3F:
quiescent engine selection + persistence — persisted SELECTED preference,
absolute final lifecycle seal: active-provider-aware shutdown (never
hard-coded Qt) with ownership RETAINED on failed teardown (retry-safe),
source unbind failure preserves active identity CONSERVATIVELY as FAILED
(router detach is not failure-atomic — READY is never assumed after an
unbind exception), synchronous switch reentrancy rejected (single
transaction guard), still-bound target never closed, router physical
identity == state active identity, first-error-wins preserved, no fallback;
(audio_engine_id, strict decode, field-level malformed fallback to Qt), explicit
switch transaction (preflight can_activate → quiescent → stop → revalidate →
persist-before-destructive → closing → router unbind → source close → invalidate
old backend acceptance → initializing → target open → bind+validate → restore
volume/mute → READY), SELECTED != ACTIVE truthful, no fallback/no reopen/no
auto-select (M11.3G owns recovery); F restart contract: selected restored,
active stays Qt READY until explicit switching; M11.3E:
runtime availability truth seal — fresh side-effect-free probes, implemented vs
available separated, canonical three-engine snapshot, no switching/persistence/
fallback; M11.3D: managed/private MPD adapter, REAL-RUNTIME VERIFIED with MPD
0.24.14; + M11.3C-R1 runtime convergence + M11.3C-R2 final runtime truth seal + M11.3C-R3 final failure-atomicity seal + M11.3C-R4 bus watch lifecycle seal + M11.3C-R5 terminal cleanup seal + M11.3C-R5.1 cleanup exception-boundary seal + M11.3C-R6 transport lifecycle & arm transaction seal + M11.3C-R6.1 resource ownership seal + M11.3C-R6.2 terminal runtime truth seal + M11.3C-R6.3 post-play-failure ownership seal + M11.3C-R6.4 state-change failure return seal + M11.3C-R6.5 owner-thread commit seal + M11.3C-R6.5.1 atomic publication seal + M11.3C-R6.5.2 reentrancy seal)** (authorized by
the 2026-08-21 product-owner realignment; foundation 2026-08-22, productive
Qt runtime 2026-08-22, GStreamer adapter 2026-08-22). This document defines
the M11.3 contracts and records implementation status for each subphase.

## Resolved binding decisions (M11.3A, ADR 0007)

- **GStreamer binding: PyGObject / GObject Introspection**
  (`gi.repository.Gst`, `gi.require_version("Gst", "1.0")`). Lazy,
  infrastructure-only imports; GI/GStreamer are system/runtime capabilities,
  NOT mandatory base dependencies — the base Michi wheel stays usable without
  them. M13 owns final distro/package delivery.
- **MPD client: in-repo minimal MPD protocol client** (no python-mpd2) over a
  private Unix socket; command surface implemented in M11.3D: `status`, `clear`, `addid`,
  `playid`, `pause`, `stop`, `seekid`/`seekcur`, `setvol`, `currentsong`,
  `idle`/`noidle` (if required for event convergence). No generic arbitrary
  command execution is exposed to the application layer.

## Implementation status — M11.3A vs productive runtime

| Subphase / piece | Status |
| --- | --- |
| M11.3A domain contracts | IMPLEMENTED / TESTED |
| M11.3A AudioTransportRouter | IMPLEMENTED / TESTED — **PRODUCTIVELY WIRED (M11.3B)** |
| M11.3A registry | IMPLEMENTED / TESTED |
| M11.3A AudioEngineService | IMPLEMENTED / TESTED — state authority; selection/switching SEALED in M11.3F (explicit quiescent switch transaction via AudioEngineSelectionCoordinator, SELECTED != ACTIVE, single-transaction reentrancy guard) |
| Qt provider | IMPLEMENTED — **PRODUCTIVE REFERENCE ENGINE (M11.3B + M11.3B-R1)**; single canonical provider (registry identity), transactional startup, backend ownership + exception-safe close |
| GStreamer provider | **IMPLEMENTED (M11.3C + M11.3C-R1 + M11.3C-R2 + M11.3C-R3 + M11.3C-R4 + M11.3C-R5 + M11.3C-R5.1 + M11.3C-R6)** — R4: bus watch lifecycle seal — Gst.Bus.remove_watch() con contrato real (SIN watch-id; el id de add_watch es bookkeeping only), falla de remoción truthfully observable (sin suppress; load no arma B; close lo compone en first-error-wins), ciclo real repetido A→B→C→close verificado (add 3 / remove 3 / 0 activos). R6: transport lifecycle & arm transaction seal — stop() con dos semánticas (candidato pendiente = cancelación; fuente aceptada = transporte detenido con replay sin load), EOS converge a STOPPED antes de EOM (replay same-source, late-EOS guardado), ARM de pipeline exception-atomic (rollback + excepción original primaria), convergencia STOPPED tras teardown del source activo. R5: terminal cleanup seal — close() best-effort (un fallo del bus watch NUNCA salta el request NULL; pipeline liberado solo con NULL OK; timer/pump siempre continúan), orden de errores en preroll fallido (NULL cleanup PRIMARIO; detach SECUNDARIO que nunca lo reemplaza). R3: load() transactional (old pipeline canonical hasta NULL exitoso; replacement fallido preserva pipeline/bus/generation/intención y nunca crea B), preroll cleanup failure-atomic (NULL fallido retiene ownership + raise), close first-error-wins (teardown antes que pump), bus watch real via bus.add_watch (create_watch+set_callback perdía TODO mensaje real), smoke real truthful (SKIP solo con dependency probada ausente; timeout con deps = FAIL). R2: ASYNC_DONE acepta sin publicar PLAYING (estado solo por STATE_CHANGED), state requests failure-atomic (preroll/play/pause/stop/teardown), pump join-timeout retiene ownership, real adapter smoke (fakesink), probe real ejercitado por monkeypatch.  operational GStreamerAudioPort (playbin3), lazy GI runtime; R1: symbolic Gst.State semantics (no raw ints), ONE GLib MainContext/MainLoop/pump per port; position timer as explicit GSource, bus watch via Gst.Bus.add_watch()/remove_watch(), generation-aware TYPE-BASED provenance (child-element errors accepted; stale generations ignored), truthful probe (GI + Gst + playbin3 factory); availability runtime-dependent; NOT default |
| MPD provider | **IMPLEMENTED / TESTED / REAL-RUNTIME VERIFIED / FROZEN (M11.3D)** — managed private child process, private Unix socket, in-repo protocol client, MPDAudioPort transport adapter, synchronous acceptance, honest crash/transport/status.error convergence, real MPD 0.24.14 startup + natural EOS + explicit stop verified. No engine switching/persistence/fallback (M11.3E/F/G). |
| Engine availability runtime | DONE / TESTED / FROZEN (M11.3E) — fresh side-effect-free probes, canonical three-engine snapshot, available != implemented, activation blocker priority, no state mutation |
| Selection / persistence | DONE / TESTED / FROZEN (M11.3F) — persisted SELECTED preference, quiescent switching, backend acceptance invalidation, volume/mute continuity, no fallback |
| Failure convergence | DONE / TESTED / FROZEN (M11.3G) |
| M11.3-UI presentation | DONE / TESTED / FROZEN (M11.3-UI + R1) — AudioEngineBridge (single UI authority over the sealed coordinator; no infra imports), NowPlayingBar quick selector + AudioEnginePopup (quick surface only, live-bound, real keyboard focus, reduced-motion gated), Settings > Audio Engine section (Preferred vs In use truth, fallback explanation, availability honesty, progressive technical details, no fake audiophile knobs), output device button preserved + disabled (DAC deferred to M11.4). R2 authorized reopening (MPD mixer compatibility correction): see below. |

**CURRENT PRODUCTIVE PATH (since M11.3B, multi-engine since M11.3F):**

```
<active engine provider>     (Qt | GStreamer | MPD — the ACTUAL active
      ↓                       provider, resolved at switch/shutdown time,
<owned backend / AudioPort>   NEVER hard-coded)
      ↓
AudioTransportRouter          (ONE stable instance for both consumers)
     ↙                    ↘
PlaybackService         PlaybackCoordinator
```

The SAME router instance is injected into both consumers; the provider owns
the concrete backend. Since M11.3F the router may be productively bound to
Qt, GStreamer or MPD: explicit quiescent switching (AudioEngineSelectionCoordinator)
transfers ownership, invalidates old-backend acceptance and restores
volume/mute; shutdown releases the ACTUALLY active provider (ownership
retained on failed teardown). All three adapters DONE / TESTED / FROZEN.

**SWITCH ORDER (recorded for M11.3F, validated for Qt in M11.3B):**
STOP → router detach/unbind → provider close → target provider open →
router bind → validation. The router MUST detach BEFORE the provider closes;
never close a provider while the router remains intentionally attached.

## Canonical Qt reference startup (M11.3B-R1)

PROBE → CAN_ACTIVATE → INITIALIZING → OPEN → ROUTER BIND → VALIDATE → READY.

- Pre-init blocker (probe can_activate False): UNAVAILABLE, active None,
  provider.open NEVER called, router unbound.
- Post-init failure (open/bind/validation): cleanup (router unbind +
  provider close best effort — each step suppresses secondary errors) then
  FAILED, active None, ORIGINAL error re-raised (bare raise, first-error-wins
  guaranteed even if router.unbind() itself raises). Secondary cleanup
  failures are diagnostic-only and NEVER replace the primary failure.
  No half-initialized runtime; FAILED state is guaranteed regardless of
  cleanup outcome.
- Registry identity: `registry.provider(QT_MULTIMEDIA) is qt_provider` —
  exactly ONE canonical Qt provider per service graph.

## Stable router architecture (M11.3A)

```
PlaybackService / PlaybackCoordinator      (subscribe ONCE)
      │
      ▼
AudioTransportRouter : AudioPort           (stable identity — never replaced)
      │   + AudioTransportBindingPort (bind/unbind)
      ▼
currently bound concrete AudioPort
(QtMultimediaBackend | GStreamerAudioPort | MPDAudioPort)
```

- Router forwards commands and callbacks; on switch it detaches the old
  backend and attaches the new one — no duplicate delivery, no stale
  callbacks, no loss.
- Commands with no bound backend raise `AudioTransportUnavailableError`
  (deterministic failure; never silent no-op; never fabricated 0).
- `AudioEngineService` owns AudioEngineState (SELECTED != ACTIVE);
  `AudioEngineRegistry` owns the provider set (one per canonical id);
  providers own engine lifecycle (probe/open/close).
- Default selected engine: QT_MULTIMEDIA. Runtime switching is implemented
  and sealed by M11.3F (explicit quiescent transaction); M11.3G owns
  involuntary convergence (startup selected-first, safe Qt fallback,
  runtime loss).

## M11.3G final ownership / generation seal (DONE / TESTED / FROZEN)

- Automatic Qt fallback happens ONLY after the failed runtime is PROVEN
  FULLY RELEASED (router unbound AND provider close completed). A
  still-bound provider never triggers fallback; a failed provider close is
  UNSAFE (never fallback).
- F→G explicit-switch recovery requires router detach AND successful
  target release; a target close failure after detach is recorded as
  secondary diagnostic truth (original activation error stays primary) and
  never authorizes fallback.
- MPD provider runtime generation is the canonical authority for G runtime
  events; the MPDAudioPort internal generation is a SEPARATE domain and is
  never compared against the provider generation. Stale events from a
  closed runtime incarnation are ignored; fatal events from the reopened
  current runtime are accepted exactly once.


## Purpose

Ship a runtime that can play through Qt Multimedia (reference/safe), GStreamer
(full pipeline), or MPD (managed transport) behind the existing `AudioPort`,
with honest availability, selection, lifecycle and failure semantics — while
preserving the established Michi domain contracts (PlaybackState, QueueState).

## Architecture

```
PlaybackService  (sole PlaybackState owner — unchanged)
      │
   AudioPort  (ABC — TRANSPORT ONLY, now and forever; ADR 0007)
      │
   ┌───┼───────────┐
   │   │           │
   ▼   ▼           ▼
 QtMultimedia   GStreamer    MPD
 (reference/    (full        (managed/private
  safe engine)   pipeline)    transport engine)
```

## Ownership (unchanged)

- PlaybackService → PlaybackState (sole authority).
- QueueService → QueueState (sole authority).
- PlaylistService → playlist collection (sole authority).
- **MPD MUST NOT own** Michi Queue / Repeat / Shuffle / Playlist semantics.
  MPD state is engine-local transport state only, never canonical.

## AudioPort boundary rule (strict)

`AudioPort` is **transport only**, now and forever. Its shape stays: load/play/
pause/resume/stop/seek/volume/mute + position/duration events + media
acceptance/error callbacks. M11.3 does NOT add "engine-capability" or
"quiescent-reconfigure" slots to it — that would grow a God interface.

- **Engine registry / availability / lifecycle / selection** live in a
  separate engine-management port/service (`AudioEngineService` →
  AudioEngineState), not in AudioPort.
- **DAC / output / profile configuration** live in their own ports/services
  (M11.4: `AudioOutputService`, `AudioDeviceRegistry`), not in AudioPort.
- Engines implement AudioPort; engine-specific capabilities are reported
  through the engine registry's capability contract, never through ad-hoc
  AudioPort methods.

## Engine roles

| Engine | Role | Notes |
|---|---|---|
| `QT_MULTIMEDIA` | REFERENCE / SAFE | Current backend; desktop-shared only; honest limitations (no DIRECT bit-perfect VERIFIED claim) |
| `GSTREAMER` | FULL PIPELINE CANDIDATE | ALSA/PipeWire sinks; caps truth for telemetry; no GStreamer types outside infrastructure |
| `MPD` | MANAGED AUDIO TRANSPORT | Private instance + generated config; engine-only semantics |

## M11.3 Subphases

- **M11.3A — Audio Runtime Contracts + ADR**: `AudioEngineId`, engine
  availability, lifecycle contract, capability contract, selection contract,
  failure contract, quiescent switch contract; AudioPort stays transport-only
  (see AudioPort boundary rule); resolves the GStreamer binding (PyGObject/GI
  vs alternatives) and the MPD client binding (own minimal protocol client vs
  dependency) with M13 packaging impact. No UI.
- **M11.3B — Qt Multimedia Reference Backend Normalization**: current backend
  conforms explicitly to the multi-engine contract without changing its
  established playback semantics.
- **M11.3C — GStreamer AudioPort Adapter**: Michi-native implementation,
  conforming to AudioPort; GStreamer confined to infrastructure (study
  evidence: Strawberry engine abstraction, GStreamer playbin/caps).
  **Binding decision (resolved in M11.3A, recorded here)**: PyGObject/GI
  (`gi.repository.Gst`) vs ctypes vs subprocess-only — the decision MUST
  consider M13 packaging (wheel shipping, GI typelib availability on target
  distros) and is made in M11.3A before any adapter code.
- **M11.3D — MPD AudioPort Adapter (IMPLEMENTED / TESTED / REAL-RUNTIME VERIFIED / FROZEN)**: managed/private MPD instance; Michi →
  MPD → output; arbitrary external MPD queue state never becomes Michi
  authority. **Private-process contract (fixed before implementation)**:
  - **Process ownership**: Michi spawns, supervises and reaps the MPD
    process; Michi owns the process lifecycle end-to-end.
  - **Private socket/port**: a private Unix socket (or localhost port) in a
    Michi-owned runtime dir; never the default `/run/mpd` or a system port.
  - **Config/state dir**: a Michi-owned directory (generated `mpd.conf`,
    database/state files); never user/system MPD directories.
  - **Dead-process detection**: liveness check (socket probe / PID check);
    a dead child is detected and handled deterministically.
  - **Cleanup**: on engine close/shutdown, terminate child (SIGTERM →
    timeout → SIGKILL) and remove Michi-owned runtime artifacts; no
    orphaned daemons.
  - **Crash recovery**: child death mid-playback routes to the failure
    contract (honest error state + clean fallback path), never silent
    resumption.
  - **No external-daemon adoption**: if an MPD process is already listening
    on the private socket, or the socket/dir already exists and belongs to
    an unexpected owner, MPD engine activation MUST fail closed rather than
    attach to a foreign daemon.
- **M11.3E — Engine Registry / Availability**: installed engines, unavailable
  states, initialization failures, runtime capability discovery.
  **MPD client binding decision (resolved in M11.3A, recorded here)**:
  in-repo minimal MPD protocol client (own implementation over the private
  socket) vs external dependency — the decision considers packaging surface
  and protocol stability; M11.3A fixes it before adapter code.
- **M11.3F — Engine Selection + Persistence**: 1.0 switches from
  QUIESCENT/STOPPED with the canonical sequence:
  VERIFY QUIESCENT → STOP → router UNBIND/DETACH → close active provider →
  open target provider → bind target AudioPort into router → validate
  transport → READY. There is NO "bind output": output/device binding
  belongs to M11.4. No seamless handover while playing. Selection persisted.
- **M11.3G — Lifecycle / Failure / Convergence**: pending media, rejection,
  stop, resume preparation, Queue convergence, engine startup failure, engine
  unavailable, target init failure, clean fallback, shutdown,
  persistence/restart.
- **M11.3-UI — Audio Engine Presentation & Settings (DONE / TESTED)**: the
  presentation layer for the frozen runtime. AudioEngineBridge is the ONE UI
  authority: it reads service/registry/coordinator state and is the only
  caller of `AudioEngineSelectionCoordinator.switch_to`; the bridge never
  opens/closes providers, never binds the router, never mutates state. Quick
  selection lives in the NowPlayingBar popup; configuration/diagnostics live
  in Settings > Audio Engine. Selected != active is always visible (Preferred
  vs In use); fallback is explained in plain language; unavailable engines
  show a truthful "cannot use on this system" reason; technical details
  (engine IDs, capability flags) are behind progressive disclosure. Engine
  configuration is managed automatically by Michi — no user-exposed
  tunables exist (audiophile audit: 0 truthful P1 knobs; DSD/DoP/bit-perfect/
  exclusive are M11.4/M11.5 scope). Output device selection stays visible but
  disabled (DAC work deferred).

## M11.3-UI-R2 authorized reopening — MPD mixer compatibility correction

Approved concrete reopening of the FROZEN M11.3 implementation, followed by
re-freeze (no new milestone). Observed on the real local runtime:

    RuntimeError: MPD setvol failed:
    ACK [5@0] {setvol} Failed to set mixer for "default detected output";
    no such mixer control: PCM

Root cause: the private MPD runtime rendered NO audio_output block, so MPD
auto-detected the default output and selected a hardware ALSA mixer control
("PCM") that the default device does not expose (host evidence: amixer
scontrols = Master/Capture only; aplay default routes through PipeWire).
restore_volume therefore failed and MPD could never reach READY.

Fix (transport boundary only, volume/mute contract guaranteed):

- `_discover_mpd_output_plugins(executable)` — bounded `mpd --version`
  inspection (argv, never shell=True) parsed for the compiled output
  plugins (MPD >= 0.23 prints them unbracketed on the "Output plugins:"
  line).
- `_select_default_mpd_output_plugin(...)` — deterministic preference
  pipewire > pulse > alsa among the COMPILED plugins only; raises a
  deterministic `MpdOutputPluginDiscoveryError` when none is available
  (implicit autodetection stays forbidden).
- `_render_mpd_conf(..., output_plugin=...)` — production config now emits
  exactly ONE explicit `audio_output` (default system output, no device
  identity, no mixer_control "PCM", no DSD/DoP/format) with
  `mixer_type "software"` which guarantees setvol/mute on any device.
  Software volume may alter samples at non-unity gain → M11.3 makes NO
  bit-perfect claim; M11.4/M11.5 own explicit output/mixer profiles.

Verified on the real local host (MPD 0.24.14, pipewire selected):
setvol(73) → volume 73, setvol(0) → 0, setvol(100) → 100, no ACK; real
Qt→MPD→Qt switch reaches READY with volume restored; 4-cycle switch leaves
no leaked child; a genuine mixer failure remains fatal (target FAILED, never
READY). F42 adapter hash updated for the authorized mpd.py reopening.

## AUDIO RUNTIME RELIABILITY SEAL (extraordinary authorized reopening)

M11.3 was temporarily reopened for an **Audio Runtime Reliability Seal**
(physical-truth corrective work) and is now re-frozen:

    M11.3      DONE / TESTED / FROZEN
    M11.3-UI   DONE / TESTED / FROZEN

No new milestone (no M11.3H). The seal made the existing three engines
physically truthful without redesigning the architecture:

- **Guaranteed shutdown** (AR-04): the entry point calls container
  shutdown on EVERY exit path (normal, run() exception, initialize()
  failure); first-error-wins on error paths.
- **Ownership invariants** (AR-05/AR-06/AR-08): a live child/thread ALWAYS
  keeps its ownership handle; failed termination raises an explicit
  teardown error and retains handle + runtime dir + diagnostics; MPD
  stderr is a runtime-owned log (no undrained pipe).
- **Command truth** (AR-02/AR-13/AR-15/AR-16/AR-17): typed
  AudioTransportError surface (CommandError/UnavailableError); GStreamer
  play/pause/stop/seek failures raise; PlaybackService stop commits only
  after the backend accepted and seek never fabricates position; MPD
  volume/mute commit only after protocol success.
- **Router transaction safety** (AR-10/AR-31/AR-32): per-binding
  generation provenance drops stale events from superseded backends even
  after a failed detach; partial attach failures roll back and never
  publish a clean binding.
- **Runtime health telemetry** (AR-11/AR-12): GStreamer activation now
  proves the runtime is genuinely operational (GI/Gst/playbin3/pump);
  unexpected pump death emits the canonical runtime-failure event;
  MPD's bounded poller converges state so edge-triggered idle loss
  cannot leave state stale.
- **Availability truth** (AR-09): MPD available=True requires at least
  one supported default-output plugin (pipewire/pulse/alsa) compiled in;
  probing stays side-effect free and cached by executable identity.
- **Cross-engine conformance** (AR-22): one semantic contract proven on
  REAL Qt, GStreamer and MPD (incl. 130-switch stress, 100 stop/play
  cycles, 25 close/reopen cycles per real engine, startup no-autoplay
  golden gate, zero leaks).

AR-01 (orphan MPD child) was REJECTED with evidence on this host: MPD >=
0.23 sets PR_SET_PDEATHSIG (SIGTERM) when not daemonized — a SIGKILLed
owner's child self-terminates within ~1s (proven via subprocess harness;
a plain `sleep` child survives and is reparented normally).

## Non-goals

- No UI (M9-R2 owns presentation).
- No DAC/output-profile management (M11.4).
- No bit-perfect verification runtime (M11.5).
- No seamless mid-track engine handover in 1.0.
- No MPD queue/playlist semantics adoption.

## Exit criteria (DoD)

- All three engines play the same fixture set behind AudioPort with identical
  service-level semantics.
- Engine registry reports availability truthfully.
- Quiescent switching converges (queue/playback state preserved per contract).
- Failure injection (startup failure, unavailable engine, device loss) routes
  to clean fallback or honest error state.
- Full pytest suite green; M11.3 TESTED / FROZEN.
