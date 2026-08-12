# ADR 0001: Python 3.11+ with PySide6 / Qt 6 stack

## Title

Python 3.11+ with PySide6 (Qt 6, Qt Multimedia with FFmpeg backend) and QML as the implementation stack for Michi Music Player.

## Date

2026-08-12

## Context

The repository was reset for a from-scratch reconstruction (commit `b2c697b`, empty workspace). Two distinct prior authorities exist and MUST NOT be conflated:

- **Legacy repository** — pitydah/michi-legacy, frozen for evidence at commit `63914a00f381104299fa50147220e05c04d5ad7e`, a Python/PySide6/QML application with a much larger product scope (AI assistant, audio lab, lyrics, radio, recognition, sync) and historical audio architecture involving GStreamer/MPD concepts. It is read-only evidence under the LEGACY EVIDENCE policy and is never copied or adapted.
- **Superseded clean-rebuild governance draft** — M0 Foundation v2 governance artifacts of this rebuild (Proposed ADRs D1–D10, dated 2026-08-10) that anticipated a C++20/Qt 6 architecture with a native build system, CTest, and C++ test frameworks (Catch2/doctest), imposing heavy build infrastructure before any product capability existed. That anticipated direction was never implemented; this ADR supersedes it.

Python 3.11+ with PySide6 provides direct access to the same Qt 6 runtime (Qt Quick for QML, Qt Multimedia with FFmpeg backend for audio) without a compile/link cycle. The standard library (dataclasses, enums, abc) supports a clean domain layer with zero Qt dependencies, matching the original layering intent.

## Decision

- The entire implementation is Python 3.11+. No C++ source exists in this repository.
- GUI and audio run on PySide6: Qt 6, Qt Multimedia (FFmpeg backend), QML.
- The domain layer is pure Python with no Qt imports. The application layer depends on domain only. Infrastructure implements application ports using PySide6, SQLite, and the filesystem.
- Build/packaging uses setuptools + `python -m build`. Tests use pytest. Linting and formatting use Ruff. CI is GitHub Actions running lint, tests (QT_QPA_PLATFORM=offscreen), and build.
- No native-code build system, no C++ test frameworks, no GStreamer integration. Prettier remains the Markdown formatter for governance docs in the SDD workflow; it is a documentation-pipeline tool, not part of the product stack.

## Consequences

- Positive: no compile/link step; iteration is edit-and-run. pytest + Ruff give a fast, enforced quality loop in CI.
- Positive: domain purity is enforced by convention and by tests (no Qt imports in domain/application), not by a linker, so the invariant needs explicit test coverage.
- Negative: Qt C++-specific idioms (Q_PROPERTY registration, moc) do not apply; the QML bridge is implemented via PySide6 property/signal declaration.
- Negative: startup and runtime performance are bounded by CPython; acceptable for an audio-only desktop player, but heavy per-frame Python work in QML bindings must be avoided.

## Alternatives considered

- **C++20 + Qt 6 (the superseded clean-rebuild governance draft)**: full type safety and performance, but the build/test infrastructure cost (CMake, CTest, Catch2/doctest) dominated early milestones. Rejected for the clean rebuild.
- **Rust with a Qt binding**: memory safety and performance, but ecosystem maturity for QML integration was weaker and team iteration speed lower. Rejected.
- **Electron / web UI**: large dependency footprint and poor fit for a lightweight local-first player. Rejected.
- **PySide6 (Qt Widgets) instead of QML**: simpler bridge but less flexible theming and less declarative UI foundation. QML chosen for the token/primitives design system.

## Status

Accepted
