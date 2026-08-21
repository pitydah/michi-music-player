# M11.3 — Multi-Engine Audio Runtime (contract)

Implementation contract for the multi-engine audio runtime. Status: **NOT
STARTED** (authorized by the 2026-08-21 product-owner realignment; scheduled
after M9-R1 refreeze). This document defines contracts, not implementation.

## Purpose

Ship a runtime that can play through Qt Multimedia (reference/safe), GStreamer
(full pipeline), or MPD (managed transport) behind the existing `AudioPort`,
with honest availability, selection, lifecycle and failure semantics — while
preserving the established Michi domain contracts (PlaybackState, QueueState).

## Architecture

```
PlaybackService  (sole PlaybackState owner — unchanged)
      │
   AudioPort  (ABC — boundary unchanged in shape; may gain engine-capability
      │         and quiescent-reconfigure slots per M11.3A)
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
- **M11.3D — MPD AudioPort Adapter**: managed/private MPD instance; Michi →
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
  QUIESCENT/STOPPED: STOP → close active engine → initialize target → bind
  output → validate → ready. No seamless handover while playing. Selection
  persisted.
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
