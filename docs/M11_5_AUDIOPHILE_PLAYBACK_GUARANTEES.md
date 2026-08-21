# M11.5 — Audiophile Playback Guarantees (contract)

Implementation contract for audiophile playback guarantees. Status: **NOT
STARTED** (authorized 2026-08-21; scheduled after M9-R2 refreeze). Contracts,
not implementation.

## Purpose

Prove — with tests and observable telemetry — that the audiophile output
architecture (M11.3 + M11.4) delivers what it claims: no hidden resampling,
no hidden remix, bit-depth preservation, automatic sample-rate switching,
same-format gapless, honest cross-format degradation, and a trustworthy
bit-perfect verdict per the M11.4 evidence model.

## Scope

- Bit-perfect conformance (SOURCE == ENGINE == DEVICE; no conversion/DSP/
  softvol in path).
- No hidden resampling; no hidden channel remix.
- Bit-depth preservation where backend/device supports it.
- Automatic sample-rate switching (44.1/48/96/192 source-native).
- Same-format gapless (contiguous album playback, live/classical/concept
  albums).
- Honest cross-format degradation: sample-rate changes, format changes,
  PCM↔DSD, DSD transport changes → controlled reopen, optional warm-up,
  explicit non-gapless transition. No fabricated continuity.
- PCM transitions; Native DSD transitions; DoP transitions.
- Multi-engine parity (Qt / GStreamer / MPD behave identically at the service
  level; engine-specific capability differences are honest).
- Queue convergence; PlaybackState convergence; resume convergence.
- Persistence/restart; DAC disconnect/reconnect.
- Failure injection; actual output telemetry (requested vs negotiated vs
  effective).

## Gapless ownership (canonical)

- QueueService owns WHICH track is next.
- PlaybackService owns transition orchestration.
- AudioPort / engine owns prepare-next / preload / seamless media transition
  capability.
- Queue authority is NEVER transferred into the audio engine (MPD included).
- Crossfade remains Post-1.0; Gapless ≠ Crossfade.

## Telemetry contract

Expose (for M9-R2 and tests):

- SOURCE: decoder truth (format/rate/bit depth/channels — Michi M6 technical
  metadata).
- ENGINE OUTPUT: effective rate/format/channel layout + resampling/remix/DSP/
  softvol state.
- DEVICE OUTPUT: negotiated PCM/DSD mode, actual rate/format, DSD transport
  (NATIVE / DOP / PCM_CONVERSION).
- Verdict: BitPerfectState VERIFIED / UNVERIFIED / NOT_APPLICABLE / BROKEN.
- DoP carrier is reported as DoP, never as "PCM conversion".

## Exit criteria (DoD)

- Required audiophile playback invariants TESTED across all three engines
  (within each engine's honest capability).
- Same-format gapless verified by golden audio fixtures; cross-format
  degradation explicitly asserted (gap/warm-up acknowledged, never hidden).
- Failure injection suite: DAC loss/reconnect, engine failure, format
  negotiation failure → honest states.
- Convergence suite: queue/playback/resume/persistence across engine switches
  from quiescent state.
- Full pytest suite green; Required-1.0 audiophile invariants TESTED.
