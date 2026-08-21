# RESEARCH-01 — Audio & Playlists Reference Study (CLOSED / ACCEPTED)

Status: **CLOSED / ACCEPTED** (product-owner realignment, 2026-08-21).

## Purpose

Reference study preceding the playlists and audiophile multi-engine milestones.
The study answered: playlist first-class navigation patterns, multi-engine
audio runtimes, DAC discovery/selection, audiophile output profiles, bit-perfect
verification, native DSD/DoP, PCM negotiation, gapless strategies, hotplug and
signal-path telemetry.

## Evidence workspace (external, isolated)

- Root: `/home/cristian/repos-estudiar/` (outside the Michi repository).
- **15 reference repositories** (shallow, single-branch):
  - Players (7): strawberry, mpd, squeezelite, moode, audacious,
    audacious-plugins, deadbeef.
  - Audio stack (5): gstreamer, pipewire, wireplumber, alsa-lib, alsa-utils.
  - DSP future (2): camilladsp, camilladsp-controller.
  - Documentation (1): moode-docs.
- Analysis documents (11) live in `/home/cristian/repos-estudiar/_analysis/`:
  REFERENCE_REPO_MANIFEST.md, LICENSE_BOUNDARIES.md,
  PLAYLISTS_REFERENCE_AUDIT.md, AUDIO_ENGINE_REFERENCE_AUDIT.md,
  DAC_DEVICE_REFERENCE_AUDIT.md, AUDIOPHILE_FEATURE_MATRIX.md,
  OUTPUT_PROFILE_PROPOSAL.md, BIT_PERFECT_CONTRACT_PROPOSAL.md,
  REFERENCE_FEATURE_MATRIX.md, MICHI_REUSE_MAP.md,
  MICHI_ROADMAP_REALIGNMENT_PROPOSAL.md.
- Isolation verified: no third-party `.git` inside the Michi repository; no
  production changes made during the study; Michi `git status` identical
  before/after.

## Key accepted findings

1. **Bit-perfect**: no studied player claims a verified bit-perfect state;
   they expose configuration knobs and the negotiated format. Michi's
   VERIFIED/UNVERIFIED contract is a differentiator: VERIFIED only when
   SOURCE == ENGINE == DEVICE with resampling/remix/DSP/softvol OFF and the
   device confirms the exact format.
2. **Identity**: `hw:N`/card index is ephemeral. PipeWire's
   vendor/product/serial/bus-path model is the canonical stable-identity
   pattern; engine-specific device strings stay in adapter bindings.
3. **MPD**: queue == active playlist by design — Michi MUST NOT adopt that;
   MPD is a managed/private transport engine behind AudioPort only.
4. **Format transitions**: DeaDBeeF's `setformat`-style reconfigure contract
   is the clean pattern for sample-rate/format switching.
5. **Gapless**: same-format gapless is universal in mature players → promoted
   to Required-1.0; cross-format boundaries degrade honestly; crossfade stays
   Post-1.0 (distinct capability).
6. **Playlists**: opaque stable identity (Audacious), pinned/recent persistence
   (Strawberry `favorite`/`last_played`), and one canonical playlist screen
   (never two competing authorities).

## Reuse policy

Reference repositories are **evidence, not runtime dependencies**. Default
classification: **REIMPLEMENT** (ideas/contracts/patterns only; no source
copying). Licensing firewall recorded in `LICENSE_BOUNDARIES.md` (GPL-2/3
repos = study only; MIT/LGPL repos = pattern reuse; GStreamer/ALSA used as
runtime dependencies; CamillaDSP future = external process).

## Consumed by

- `docs/MASTER_ROADMAP_1.0.md` — Canonical 1.0 Contract + Current Execution
  Order (M8-R1, M9-R1, M11.3, M11.4, M9-R2, M11.5).
- `docs/M11_3_MULTI_ENGINE_AUDIO_RUNTIME.md`
- `docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md`
- `docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md`

Correction note: the RESEARCH-01 report initially said "16/16" repositories;
the enumerated manifest contains **15** (7 players + 5 audio stack + 2 DSP
future + 1 documentation). 15 is the canonical count.
