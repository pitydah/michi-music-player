# ADR 0007 — Multi-Engine Audio Runtime

**Status:** Accepted (2026-08-22, M11.3A)
**Supersedes:** n/a — extends ADR 0001 (stack decision; the original
"no GStreamer integration" note is superseded by this ADR per the
2026-08-21 product-owner realignment).

## Context

Michi targets exactly three independently selectable audio engines behind its
existing playback contracts: `QT_MULTIMEDIA` (reference/safe), `GSTREAMER`
(full pipeline) and `MPD` (managed private transport). PlaybackService owns
PlaybackState; QueueService owns QueueState. Engine switching must not
reconstruct services nor turn AudioPort into a God interface.

## Decision

1. **AudioPort remains transport-only, forever.** No engine-selection,
   device, DSD or bit-perfect methods ever enter AudioPort.
2. **AudioEngineService owns engine state/lifecycle** (AudioEngineState):
   SELECTED (intent) is distinct from ACTIVE (bound engine).
3. **AudioTransportRouter provides a stable AudioPort identity** across
   switches: services subscribe once to the router; only the router's bound
   concrete AudioPort changes (attach/detach with event re-routing).
4. **Three independent engines; no hybrid.** They are transports, never a
   merged engine.
5. **Qt Multimedia is the safe/reference default** (current working backend,
   tested semantics). GStreamer/MPD are never automatic defaults in M11.3.
6. **GStreamer binding: PyGObject / GObject Introspection** (`gi.repository.Gst`),
   lazy and infrastructure-only. GI/GStreamer are system/runtime capabilities,
   NOT mandatory base dependencies; the base wheel stays usable without them.
7. **MPD client: in-repo minimal MPD protocol client** (no python-mpd2):
   private managed daemon, intentionally small command surface, direct Unix
   socket control, less packaging surface, Michi owns lifecycle semantics.
8. **MPD is a private managed process only**: Michi-owned runtime directory,
   generated config, private Unix socket, no system-daemon or foreign-socket
   adoption, process fully reaped on close. MPD NEVER owns Michi Queue.
9. **Engine selection != DAC/output selection.** M11.4 owns devices, profiles,
   DSD/DoP and volume policies.
10. **No bit-perfect claims in M11.3.** Engine identity is not proof of signal
    preservation; M11.4/M11.5 own that evidence.
11. **Quiescent runtime switching only for 1.0** (PlaybackStatus.STOPPED + no
    pending acceptance/rejection/resume). No seamless mid-track switching.
12. **Queue remains Michi-owned.** Engine-local queues/pipelines are
    implementation mechanisms only.

## Consequences

- PlaybackService/PlaybackCoordinator subscribe once to the router; switching
  never reconstructs services.
- Providers own engine lifecycle (probe/open/close); open() returns the
  transport AudioPort.
- Registry owns exactly one provider per canonical id (deterministic order:
  QT_MULTIMEDIA, GSTREAMER, MPD).
- GStreamer/MPD availability probes are truthful: `installed` (dependency
  present) is distinct from `implemented` (adapter ready).
- M13 owns distro/package delivery policy for GStreamer/MPD runtime pieces.

## Alternatives rejected

- **GStreamer via ctypes/subprocess-only**: rejects GI typelib surface used by
  the ecosystem; PyGObject/GI is the maintainable binding.
- **python-mpd2 dependency**: extra packaging surface and less control over
  the private daemon lifecycle; an in-repo minimal client is smaller and
  Michi-owned.
- **Engines as subclasses of one hybrid AudioPort**: couples engine internals;
  rejected in favor of independent transports behind the same port.
- **Replacing the AudioPort object on switch**: would force reconstruction of
  PlaybackService/Coordinator/bridges; the stable router avoids this.
