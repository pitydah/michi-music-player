# M11.3 — Multi-Engine Audio Runtime (contract)

Implementation contract for the multi-engine audio runtime. Status: **IN
PROGRESS — M11.3A + M11.3B + M11.3C + M11.3D + M11.3E + M11.3F DONE / TESTED / FROZEN (M11.3F:
quiescent engine selection + persistence — persisted SELECTED preference
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
| M11.3A AudioEngineService | IMPLEMENTED FOUNDATION — NO SWITCHING YET |
| Qt provider | IMPLEMENTED — **PRODUCTIVE REFERENCE ENGINE (M11.3B + M11.3B-R1)**; single canonical provider (registry identity), transactional startup, backend ownership + exception-safe close |
| GStreamer provider | **IMPLEMENTED (M11.3C + M11.3C-R1 + M11.3C-R2 + M11.3C-R3 + M11.3C-R4 + M11.3C-R5 + M11.3C-R5.1 + M11.3C-R6)** — R4: bus watch lifecycle seal — Gst.Bus.remove_watch() con contrato real (SIN watch-id; el id de add_watch es bookkeeping only), falla de remoción truthfully observable (sin suppress; load no arma B; close lo compone en first-error-wins), ciclo real repetido A→B→C→close verificado (add 3 / remove 3 / 0 activos). R6: transport lifecycle & arm transaction seal — stop() con dos semánticas (candidato pendiente = cancelación; fuente aceptada = transporte detenido con replay sin load), EOS converge a STOPPED antes de EOM (replay same-source, late-EOS guardado), ARM de pipeline exception-atomic (rollback + excepción original primaria), convergencia STOPPED tras teardown del source activo. R5: terminal cleanup seal — close() best-effort (un fallo del bus watch NUNCA salta el request NULL; pipeline liberado solo con NULL OK; timer/pump siempre continúan), orden de errores en preroll fallido (NULL cleanup PRIMARIO; detach SECUNDARIO que nunca lo reemplaza). R3: load() transactional (old pipeline canonical hasta NULL exitoso; replacement fallido preserva pipeline/bus/generation/intención y nunca crea B), preroll cleanup failure-atomic (NULL fallido retiene ownership + raise), close first-error-wins (teardown antes que pump), bus watch real via bus.add_watch (create_watch+set_callback perdía TODO mensaje real), smoke real truthful (SKIP solo con dependency probada ausente; timeout con deps = FAIL). R2: ASYNC_DONE acepta sin publicar PLAYING (estado solo por STATE_CHANGED), state requests failure-atomic (preroll/play/pause/stop/teardown), pump join-timeout retiene ownership, real adapter smoke (fakesink), probe real ejercitado por monkeypatch.  operational GStreamerAudioPort (playbin3), lazy GI runtime; R1: symbolic Gst.State semantics (no raw ints), ONE GLib MainContext/MainLoop/pump per port; position timer as explicit GSource, bus watch via Gst.Bus.add_watch()/remove_watch(), generation-aware TYPE-BASED provenance (child-element errors accepted; stale generations ignored), truthful probe (GI + Gst + playbin3 factory); availability runtime-dependent; NOT default |
| MPD provider | **IMPLEMENTED / TESTED / REAL-RUNTIME VERIFIED / FROZEN (M11.3D)** — managed private child process, private Unix socket, in-repo protocol client, MPDAudioPort transport adapter, synchronous acceptance, honest crash/transport/status.error convergence, real MPD 0.24.14 startup + natural EOS + explicit stop verified. No engine switching/persistence/fallback (M11.3E/F/G). |
| Engine availability runtime | foundation now — full discovery M11.3E |
| Selection / persistence | M11.3F |
| Failure convergence | M11.3G |

**CURRENT PRODUCTIVE PATH (since M11.3B):**

```
QtEngineProvider
      ↓
QtMultimediaBackend           (ONE owned backend)
      ↓
AudioTransportRouter          (ONE instance for both consumers)
     ↙                    ↘
PlaybackService         PlaybackCoordinator
```

The SAME router instance is injected into both consumers; the provider owns
the single Qt backend. M11.3C (GStreamer) and M11.3D (MPD) added their
adapters behind the same router (both DONE / TESTED / FROZEN).

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
current concrete AudioPort  (QtMultimediaBackend today)
```

- Router forwards commands and callbacks; on switch it detaches the old
  backend and attaches the new one — no duplicate delivery, no stale
  callbacks, no loss.
- Commands with no bound backend raise `AudioTransportUnavailableError`
  (deterministic failure; never silent no-op; never fabricated 0).
- `AudioEngineService` owns AudioEngineState (SELECTED != ACTIVE);
  `AudioEngineRegistry` owns the provider set (one per canonical id);
  providers own engine lifecycle (probe/open/close).
- Default selected engine: QT_MULTIMEDIA. Runtime switching belongs to
  M11.3F (quiescent only).

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
