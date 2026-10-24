# M13 native DoP evaluation — decision request

Status: **AWAITING_EXTERNAL_DECISION**  
M13 packaging gate: **NO-GO** (unchanged)  
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

## 3. Exact approval text

If the owner accepts, the recorded decision must be:

> I authorize M13 Gate A: a scoped, non-distributed Rust/GStreamer `michidop`
> evaluation artifact under `native/michi-dop/`, with pinned toolchains,
> Cargo.lock, private-prefix discovery, shared-corpus conformance and captured
> evidence. I do not authorize Gate B distribution or production selection.

Without that (or an equivalent explicit written decision), the agent must not
add native code and M13 remains NO-GO.

## 4. Evidence available before approval

- ADR 0012 architecture and rejected alternatives.
- Python reference packer and 9-vector conformance corpus with SHA-256.
- Planner V3 double gate and exact carrier/DAC evidence separation.
- Exact ALSA qualification adapter and process-supervised probe (timeout,
  cancellation, bounded concurrency, honest provenance).
- Toolchain inventory: Rust 1.96 and GStreamer 1.28 present.
- No native artifact, Cargo.lock, ABI claim or installed plugin exists.

## 5. Evidence only possible after approval

- Reproducible `cargo build --release --locked` and artifact SHA-256.
- Registered factory and inspected plugin revision/ABI.
- Three-level byte-for-byte conformance and first-divergence diagnostics.
- Installed wheel/private-prefix discovery and missing-plugin/wrong-ABI tests.
- Native CI and SBOM/manifest.

## 6. Operations this approval would enable

Create `native/michi-dop/` and its tests; add a private-prefix build/install
script; add native CI; add conformance runner; add host integration behind an
explicit disabled-by-default switch. No production packaging or default
selection is enabled by Gate A.

## 7. If not approved

Record the explicit refusal or absence of decision. Do not implement Rust/C.
F09 remains ACTIVE/BLOCKED; the productive-runtime, host, playback and Signal
Truth work units remain unstarted. The Python reference and supervised probe
stay valid but cannot certify F09-G1/G4 at runtime.
