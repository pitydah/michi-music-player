# Michi Music Player — agent contract

## DAC work: mandatory canonical specification

M11.4 DAC integration is **current pre-Stable work**. Do not wait for the player to become Stable before implementing it; the mandatory DAC core is one of the prerequisites for Player Stable.

For any task that touches USB DACs, ALSA, GStreamer Direct output, device discovery,
audio output profiles, sample-rate switching, DAC volume, Signal Truth, output
reconnect, bit-perfect claims, or M11.4/M11.5 output guarantees:

1. Open `docs/dac/MICHI_DAC_CANONICAL_EFFECTIVE_SPEC_KERNEL_DRIVER_METHOD_V3_5.md`.
2. Read §0AA–§0K and §396–§410 before changing code.
3. Search that entire file for the exact topic and read the governing sections in full.
4. Run `python scripts/verify_dac_repository_alignment.py` before the first patch of a work package.
5. Execute only `DAC-V35-*` work packages from §0E. `DAC-V35-000` through `DAC-V35-100` are current pre-Stable implementation work. Older `DAC-*`, `DISC-*`, `DAC-PREMIUM-*`, V3.2–V3.4 slices are historical/reference unless V3.5 maps them explicitly.
6. Preserve current ownership: PlaybackSessionService owns sequence/navigation; PlaybackService owns PlaybackState; AudioEngineService owns engine state; DAC/output services must not fork those authorities.
7. Never invent hardware support. Exact runtime evidence outranks profiles and cached claims.
8. Never silently fall back from Direct DAC semantics to Shared/default-speaker semantics.
9. If current HEAD contradicts the V3.5 repository assumptions, update the canonical spec before implementing a new architecture.
10. A green automated suite is not physical DAC verification. Start physical qualification as soon as the first real Direct vertical exists; do not defer it merely because the rest of the application is pre-Stable.
11. “Stable”, “Stable core”, or “Stable blocker” in the DAC spec names an acceptance/release gate. It never means “implement after Stable”. Only items explicitly marked `POST-STABLE ONLY` are deferred beyond the first Stable release.
