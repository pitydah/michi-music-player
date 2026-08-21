# M11.4 — Audiophile Output & DAC Management (contract)

Implementation contract for audiophile output infrastructure. Status: **NOT
STARTED** (authorized 2026-08-21; scheduled after M11.3). Contracts, not
implementation. This is playback/output infrastructure — **not** Audio Lab.

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
  WirePlumber, ALSA, GStreamer DeviceMonitor).
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

BIT PERFECT = VERIFIED only if:

```
SOURCE FORMAT == ENGINE EFFECTIVE OUTPUT == DEVICE EFFECTIVE OUTPUT
```

AND resampling OFF, channel remix OFF, DSP OFF, software volume OFF,
format conversion OFF.

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
