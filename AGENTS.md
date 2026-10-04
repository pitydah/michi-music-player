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

<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_BEGIN -->
## Audio Phase 2 work: mandatory implementation Bible

Audio Phase 2 is governed by:
`docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md`.

For ANY task that touches Phase 2 audio signal types, DSP, PEQ, FIR,
convolution, resampling, dither, Signal Path, Native DSD, DoP, DSD-to-PCM,
Phase 2 Device Setup, Audio Lab, Phase 2 NowPlaying audio controls, MAHKB,
native DAC profiles, Phase 2 persistence, Phase 2 physical qualification, or
related presentation bridges:

1. Resolve and open the canonical Audio Phase 2 Bible before changing code.
2. Read `BIBLIA A`, `BIBLIA B`, and the complete `AP2-Fxx` phase card for the
   current task.
3. Declare exactly one `PRIMARY_PHASE=AP2-Fxx`.
4. Run `python scripts/phase2_context.py --phase AP2-Fxx --receipt-json` and
   keep the resulting spec hash in the work log.
5. Read the governing `MUST_READ_SECTIONS` for the concrete symbols being
   changed. A prior-chat summary or agent memory is never sufficient.
6. Run `python scripts/verify_audio_phase2_repository_alignment.py --phase AP2-Fxx`
   before the first productive patch and again before the phase commit.
7. Do not mutate a phase whose state in `docs/audio/phase2/PHASE2_STATE.json`
   is `LOCKED` or `BLOCKED`.
8. Preserve the frozen V3.5/M11.5 authorities. If code, state, ADR and Bible
   disagree, stop with `STOP_SPEC_DRIFT`; do not improvise a new authority.
9. After context compaction, model change, subagent handoff, or resumed session,
   reread the phase card and affected normative sections before continuing.
10. No context → no code. Unknown ownership → no code. Unknown evidence →
    fail closed for fidelity claims.
<!-- MICHI_AUDIO_PHASE2_AGENT_CONTRACT_END -->
