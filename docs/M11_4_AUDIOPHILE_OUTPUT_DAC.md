# M11.4 — Audiophile Output & DAC Management (contract)

Implementation contract for audiophile output infrastructure. Status: **IN
PROGRESS** (DAC-V35 implementation authorized 2026-09-11).

**Canonical implementation authority**: the normative V3.5 spec
`docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md`
(work packages `DAC-V35-*`, §0E manifest, §0F baseline seal, §0K DoD).
This document remains the M11.4 contract overview; where they differ, the
V3.5 spec governs implementation and acceptance.

## Implementation status (DAC-V35)

- `DAC-V35-000` repository/agent alignment — AGENTS.md + canonical spec
  installed + alignment gate (`scripts/verify_dac_repository_alignment.py`).
- `DAC-V35-010` device identity + discovery — Linux-real sysfs topology
  (`/sys/devices` + `/sys/bus/usb/devices` + `/sys/class/sound`
  symlinks), stable identity precedence, generation-safe registry,
  zero-or-more playback bindings (never synthesized `DEV=0`).
- `DAC-V35-020` exact ALSA qualification — `michi-alsa-probe` contract
  (§13): exact open/readback, layer-aware error classification,
  BUSY/REMOVED/TIMEOUT never negative evidence.
- `DAC-V35-030` persistence / output profile — schema v2 (§0I) in the
  same SQLite database and recovery/LKG model.
- `DAC-V35-040` output plan / transaction — immutable `OutputPlan`
  (§403 completeness), pure planner with significant-bit truth,
  `OutputSessionService` implementing `PlaybackOutputTransactionPort`.
- Corrective convergence pass `DAC-C01..C13` (2026-09-11) over
  DAC-V35-010..040.

**Explicitly NOT claimed**: no physical DAC qualification, no
"bit-perfect"/Michi-Verified claim, no Signal Truth runtime verdict, no
M11.5 promotion. `DAC-V35-050`+ are not started; physical qualification
(`DAC-V35-110`) remains pending.

Contracts, not implementation. This is playback/output infrastructure —
**not** Audio Lab.

## Canonical separation

- ENGINE = Qt / GStreamer / MPD (from M11.3).
- DEVICE = physical/logical DAC/output device.
- TRANSPORT = shared/direct output path.
- PROFILE = user-selected policy binding engine + device + playback/output
  rules.

```
AudioEngineService (M11.3)
        │
        ▼
AudioOutputService
        │
        ▼
AudioDeviceRegistry
        │
        ▼
AudioOutputProfile
        │
        ▼
DAC
```

One canonical DAC model; engines never invent their own.

## M11.4 Subphases

- **M11.4A — Device Discovery**: canonical registry with adapters (PipeWire,
  WirePlumber, ALSA, GStreamer DeviceMonitor). **Deduplication rule (fixed
  before implementation)**: multiple backends observe the SAME physical DAC —
  the registry merges observations into exactly ONE `AudioDevice` per stable
  identity (vendor/product/serial/bus-path; ALSA card longname/bus-path as
  fallback evidence). Each merged device records `provenance` (which backends
  observed it, with timestamps) and per-backend `bindings` (backend-specific
  device strings/ids: `hw:0,3`, `node.name`, `device.string`, …). A backend
  disappearing removes only its binding/provenance, never the canonical
  device, while at least one backend still observes it. No duplicate devices;
  no device invented from a single backend's ephemeral id.
- **M11.4B — Stable DAC Identity**: never persist only `hw:N`/card index
  (ephemeral). Stable identity from vendor, product, serial, bus, path and
  persistent identifiers. Backend-specific device strings stay in adapter
  bindings.
- **M11.4C — Capability Probing**: PCM (rates/formats/bit depths/channels),
  DSD (native/DoP/rates where determinable), output (hardware volume, direct/
  shared/exclusive). Never fabricate capability evidence.
- **M11.4D — DAC Selection**: explicit output-device selection; availability
  observable; an unavailable device never masquerades as selected/working.
- **M11.4E — AudioOutputProfile Domain**:
  - `AudioEngineId`: QT_MULTIMEDIA | GSTREAMER | MPD
  - `AudioTransportMode`: DESKTOP_SHARED | DIRECT
  - `VolumeMode`: SOFTWARE | HARDWARE | FIXED
  - `DsdPolicy`: AUTO | NATIVE | DOP | PCM_CONVERSION | DISABLED
  - `BitPerfectState`: VERIFIED | NOT_APPLICABLE | UNVERIFIED | BROKEN
    (runtime evidence, never a persisted boast)
  - `AudioOutputProfile`: profile_id, display_name, engine, stable_device_id,
    transport, PCM policy, DSD policy, volume mode, channel policy,
    resampling policy, remix policy, buffer policy, fallback policy.
- **M11.4F — Per-DAC Profile Persistence**: stable DAC identity → preferred
  OutputProfile → restore on startup/reconnect (WirePlumber pattern).
- **M11.4G — Shared vs Direct**: DESKTOP_SHARED (PipeWire/system-managed) vs
  DIRECT (hardware-oriented, normally ALSA `hw` where appropriate). Direct
  does NOT automatically imply bit-perfect.
- **M11.4H — PCM Format Policy**: source-native rate preference, actual
  negotiation, bit-depth preservation, channel preservation, explicit
  fallback policy.
- **M11.4I — Native DSD / DoP**: policy AUTO/NATIVE/DOP/PCM_CONVERSION/
  DISABLED; never claim DoP support automatically when it cannot be probed;
  per-DAC profiles may hold explicit user/configured capability evidence.
- **M11.4J — Volume / Mixer Policy**: SOFTWARE (digital attenuation),
  HARDWARE (physical mixer when supported), FIXED (digital attenuation bypass
  / fixed digital level). Bit-perfect verification accounts for this.
- **M11.4K — Automatic Sample-Rate Switching**: 44.1→44.1, 48→48, 96→96,
  192→192; no forced global 48 kHz in Direct/Audiophile mode unless required
  by capability/fallback policy.
- **M11.4L — Hotplug / Recovery / Fallback**: DAC added/removed/reconnected,
  selected DAC disappears, profile restore, fallback output, engine losing
  device, user-visible unavailable/error state. No silent rerouting that would
  falsify audio-state claims.

## Bit-perfect evidence model

BIT PERFECT = VERIFIED only if the **signal format after lossless decode**
is preserved end-to-end. The comparison chain has FOUR distinct stages — never
compare container/codec names to PCM names:

```
Container/Codec         e.g. FLAC 24/96      (file facts — M6 technical metadata)
    ↓ lossless decode
Decoded Source Signal   e.g. PCM S24_LE 96 kHz stereo   ← comparison reference
    ↓ engine
Engine Effective Signal e.g. PCM S24_LE 96 kHz stereo   (resampling/remix/DSP/softvol state)
    ↓ transport
Device Negotiated Signal e.g. PCM S24_LE 96 kHz         (hw_params/SPA truth)
```

VERIFIED requires: Decoded Source Signal == Engine Effective Signal == Device
Negotiated Signal (format, rate, bit depth, channel layout) AND resampling
OFF, channel remix OFF, DSP OFF, software volume OFF, format conversion OFF.
A FLAC 24/96 file and an S24_LE 96 kHz engine output ARE bit-perfect — the
codec name (FLAC) is irrelevant to the comparison; only the post-decode signal
matters.

Incomplete evidence → UNVERIFIED. Never infer VERIFIED because GStreamer/MPD/
ALSA/PipeWire/Direct is active — those are configuration conditions, not
proof. Qt Multimedia cannot produce a trustworthy DIRECT bit-perfect VERIFIED
claim; prefer UNVERIFIED over false confidence.

## Future DSP seam

```
Audio Engine → [ FUTURE DSP STAGE (post-Stable, CamillaDSP-style external
process) ] → Output Policy → DAC
```

The seam is preserved; the stage is NOT implemented. Audio Lab / PEQ /
convolution / room correction / crossfeed / loudness / upsampling remain
AFTER PLAYER STABLE (RETAINED, OUT OF SCOPE).

## Non-goals

- No Audio Lab / DSP implementation.
- No UI (M9-R2 owns presentation).
- No bit-perfect conformance enforcement (M11.5).
- No silent rerouting or fabricated capability claims.

## Exit criteria (DoD)

- Registry discovers devices across at least two adapters with stable
  identity and truthful capability probes.
- Per-DAC profile persistence round-trips across restart and reconnect.
- Direct/Shared, PCM policy, DSD/DoP policy, volume modes and automatic
  sample-rate switching work within engine capability.
- Hotplug/failure injection produces honest observable states.
- Full pytest suite green; M11.4 TESTED / FROZEN.
