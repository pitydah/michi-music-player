# M13 native DoP evaluation — decision request

Status: **APPROVED — GATE A ONLY**  
M13 packaging gate (Gate B): **NO-GO**  
Date: 2026-10-24  
Related: ADR 0012, AP2-F09, `M13_DOP_PACKAGING_GATE.json`

## 1. Authority

The repository does not delegate approval of a native artifact to the agent.
The product owner is the only authority for this request. This document is a
request, not an approval, a signature, or a gate transition.

## 2. Decision requested

Authorize **Gate A only: a scoped, non-distributed native evaluation artifact**:

- build an experimental Rust/GStreamer `michidop` element from
  `native/michi-dop/`;
- pin the Rust and GStreamer toolchains and commit `Cargo.lock`;
- load it only from a private, isolated evaluation prefix (venv/container),
  never from the checkout or a global `GST_PLUGIN_PATH`;
- run the shared golden corpus at three levels (Python, Rust, installed
  plugin) and capture carrier bytes/digests;
- keep it disabled in production selection and in all shipped packaging.

This does **not** authorize AppImage/Flatpak/deb distribution, release
publication, default plugin discovery, or a stable/productivity claim. Those
remain **Gate B**, requiring separate approval after Gate A evidence.

## 3. Recorded authorization

On 2026-10-24 the product owner explicitly selected **“Sí, autorizo Gate A”**
for the scope in this document: `native/michi-dop`, `--locked` build, private
prefix, shared-corpus conformance, with Gate B distribution/production
selection still prohibited. This is a recorded owner decision, not a signature
attributed to an absent authority.

## 4. Exact approval text

If the owner accepts, the recorded decision must be:

> I authorize M13 Gate A: a scoped, non-distributed Rust/GStreamer `michidop`
> evaluation artifact under `native/michi-dop/`, with pinned toolchains,
> Cargo.lock, private-prefix discovery, shared-corpus conformance and captured
> evidence. I do not authorize Gate B distribution or production selection.

Without that (or an equivalent explicit written decision), the agent must not
add native code and M13 remains NO-GO.

## 5. Evidence available before approval

- ADR 0012 architecture and rejected alternatives.
- Python reference packer and 9-vector conformance corpus with SHA-256.
- Planner V3 double gate and exact carrier/DAC evidence separation.
- Exact ALSA qualification adapter and process-supervised probe (timeout,
  cancellation, bounded concurrency, honest provenance).
- Toolchain inventory: Rust 1.96 and GStreamer 1.28 present.
- No native artifact, Cargo.lock, ABI claim or installed plugin exists.

## 6. Evidence after Gate A (recorded)

- Reproducible `cargo build --release --locked`: two clean builds produced
  SHA-256 `c4dffb6dfede48feff040e3e4af36032d2c57975afd182ae3ecdad3ccd00abcc`.
- Registered factory `michidop`; inspected plugin revision/ABI.
- Python/Rust/installed-plugin shared-corpus conformance: PASS.
- Private-prefix discovery and supervised host fakesink vertical: PASS.
- Native CI job `dop-native-gate-a`: PASS (run 40120607660).
- Not yet present: wheel/AppImage/Flatpak/deb packaging, release SBOM/manifest,
  default discovery and productive selection.

## 7. Operations enabled by Gate A

Created `native/michi-dop/` and its tests; added a private-prefix
build/install script; added native CI; added the shared-corpus conformance
runner; added the supervised host evaluation path (not selected in production).
No production packaging or default selection is enabled by Gate A.

## 8. Gate B (not approved)

Gate B remains **NO-GO**: no distribution artifact, no default discovery, no
production selection and no productive DoP playback. The Gate A host path is
an isolated evaluation vertical, not a user-facing feature. F09 cannot be
CLOSED until Gate B and the selected-ALSA F09-G4 evidence exist.
