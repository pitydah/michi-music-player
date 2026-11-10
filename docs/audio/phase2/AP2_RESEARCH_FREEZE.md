# AP2 research freeze during E14 publication

Date: 2026-11-09

The E14 Player/Ecosystem publication is a control-plane integration. It does not
change the Audio Phase 2 state machine and does not alter `PHASE2_STATE.json`:

- AP2-F03 through AP2-F10 remain CLOSED.
- AP2-F11 remains ACTIVE; productive audio work is paused for this publication.
- AP2-F12 through AP2-F15 remain LOCKED.

The integration adds no playback, queue, engine, DAC, DSP, library, Signal Truth,
firmware stream or Link identity authority. Those remain with their existing
Player owners. The Ecosystem host only exposes Home, Registry, Discovery, Stream,
Micro, Link, Mobile, Spaces, diagnostics and Home Assistant surfaces through the
single Player navigation authority.

## Verifiable guard

`scripts/verify_ap2_research_freeze.py` compares the current tree with the E14
merge baseline (`d2385fea2bd0a229ff8bce24000dcd07e895e0c1`) and fails when a
productive Audio Phase 2 or DAC file changes without an explicit owner-approved
exception. Tests, evidence under `docs/audio/phase2/evidence/`, artifacts,
shared Player shell/navigation and Ecosystem control-plane files are outside the
frozen surface.

The exception ledger is `docs/audio/phase2/AP2_RESEARCH_FREEZE_EXCEPTIONS.json`.
An exception requires the exact path, `authorization: OWNER_APPROVED`, a named
`authorized_by` and a non-empty reason. The CI `check` job runs the guard with
full history; a malformed ledger or any unapproved productive change fails.

This guard is policy evidence, not a substitute for GitHub branch protection.
It does not change any phase state: F03-F10 remain CLOSED, F11 remains ACTIVE
with productive work paused, and F12-F15 remain LOCKED.
