# M13 Gate B — production decision request

Status: **APPROVED — 2026-10-24**  
Gate A: APPROVED_AND_VERIFIED  
Gate B: approved; packaging/integration pending  
Related: ADR 0012, AP2-F09, `M13_DOP_PACKAGING_GATE.json`

## Authority

The product owner is the only authority for distribution, default discovery and
productive DoP selection. The agent cannot derive Gate B from Gate A.

## Recorded authorization

On 2026-10-24 the product owner explicitly selected **“Sí, autorizo Gate B”**
for distribution, app-private default discovery, canonical service wiring and
selected-ALSA opt-in. Physical DSD-mode certification/F14 remain outside.

## Decision requested

Approve **Gate B** to:

1. package `michidop` in app-owned distribution artifacts;
2. enable app-private plugin discovery by default;
3. wire DoP into OutputSessionService, PlaybackService and SignalTruthRecorder;
4. run selected-ALSA DoP carrier tests under the explicit hardware opt-in.

This does not authorize a physical DSD-mode certification (F14) or a claim that
the DAC entered DSD mode.

## Exact approval text

> I authorize M13 Gate B: package the Rust/GStreamer `michidop` plugin in
> app-owned distribution artifacts, enable app-private default discovery, wire
> DoP into the canonical OutputSession/Playback/Signal Truth path, and run
> selected-ALSA DoP carrier tests under the explicit hardware opt-in. I do not
> authorize a physical DSD-mode certification or F14.

Without this explicit decision, packaging and productive selection remain
disabled.

## Evidence already available

- Gate A authorized and verified; plugin built reproducibly with `--locked`.
- Artifact SHA-256
  `72fce5983a765f8fa27deb9a1ea530619bb1d69548d178df3853ea2174dc1af8`.
- Cargo.lock, pinned Rust 1.96.0, GStreamer 1.28.8.
- Python/Rust/installed-plugin shared-corpus conformance.
- Supervised host DoP fakesink vertical, confirmed PLAYING/EOS.
- Canonical plugin path + installed manifest SHA-256/revision validation.
- Native CI job `dop-native-gate-a` passing.
- Full suite 6186 passed / 9 skipped / 0 failed.

## Required Gate B deliverables after approval

- Wheel/AppImage/Flatpak/deb packaging where applicable.
- SBOM and release manifest.
- Clean-install ABI/discovery/conformance.
- OutputSessionService DoP transaction family.
- PlaybackService end-to-end DoP selection.
- SignalTruthRecorder DoP lifecycle with carrier-vs-DAC-mode separation.
- Selected-ALSA host test with explicit hardware opt-in.
- F09-G1..G4 revalidation and formal closure.

## If not approved

No packaging, default discovery, production selection or physical test is
performed. F09 remains ACTIVE/BLOCKED at Gate B; Gate A evidence stays valid.
