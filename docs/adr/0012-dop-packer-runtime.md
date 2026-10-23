# ADR 0012 — DoP packer runtime decision (AP2-F09)

- **Status:** Accepted — production target Rust/GStreamer, packaging gate pending
- **Date:** 2026-10-23
- **Phase:** AP2-F09

## Context

DoP packs DSD source bytes into a PCM-compatible carrier (2 payload bytes +
0x05/0xFA marker per channel frame). The corpus forbids a Python per-sample
hot path and requires byte-for-byte conformance, exact carrier layout and
separate carrier vs DAC-interpretation evidence.

The repository stack is Python/PySide6 (ADR 0001) and has no native build
system. Rust 1.96.0 and GStreamer 1.28.8 development files are available in the
current environment, but M13 owns distribution/packaging and has not yet
approved a native artifact pipeline.

## Decision

1. The production DoP packer target is a Rust GStreamer element with factory
   `michidop`, built with the stable `gstreamer-rs` bindings selected for
   GStreamer 1.28.x.
2. Python remains the **reference/conformance** implementation and test oracle.
   It is never the productive per-sample hot path.
3. No Rust or C code is added until the packaging gate is approved:
   toolchain pinning, reproducible build, artifact discovery in installed
   wheel/AppImage, ABI check, cross-language vector digest parity, and a
   fallback that fails closed when the plugin is absent.
4. Until that gate passes: `DOP_EXECUTOR_STATUS = RESEARCH / NOT IMPLEMENTED`.
   F09 may implement domain, reference packer, streaming contracts and planner,
   but may not claim a productive DoP runtime.
5. Carrier and DAC interpretation stay separate. `DOP_CARRIER_VERIFIED` never
   implies `DAC_DSD_MODE_VERIFIED`.
6. Layout support: `PACKED_24_LE` and `S32_LE_LSB24` are candidate production
   layouts after exact ALSA qualification. `S32_LE_MSB24` remains disabled
   until a real target requires and proves it.
7. MPD remains a reference architecture only; it must not bypass
   OutputSessionService, ownership or generation contracts.

## Consequences

- F09 ACTIVATION is allowed for domain/reference/planner work.
- A native runtime PR is blocked on the packaging gate; its absence must be
  reported as `BLOCKED/NOT_IMPLEMENTED`, never as PASS.
- The Python reference and native plugin must consume the same vector corpus
  and produce identical SHA-256 digests.
