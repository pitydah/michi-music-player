# ADR 0001: Python 3.11+ with PySide6 / Qt 6 stack

## Title

Python 3.11+ with PySide6 (Qt 6, Qt Multimedia with FFmpeg backend) and QML as the implementation stack for Michi Music Player.

## Date

2026-08-12

## Context

The previous codebase (Legacy) was built on a C++20/Qt 6 architecture plan — the historical superseded plan — which required a native build system, CTest, and a C++ test framework (Catch2/doctest), imposing heavy build infrastructure before any product capability existed.

Python 3.11+ with PySide6 provides direct access to the same Qt 6 runtime (Qt Quick for QML, Qt Multimedia with FFmpeg backend for audio) without a compile/link cycle. The standard library (dataclasses, enums, abc) supports a clean domain layer with zero Qt dependencies, matching the original layering intent.

## Decision

- The entire implementation is Python 3.11+. No C++ source exists in this repository.
- GUI and audio run on PySide6: Qt 6, Qt Multimedia (FFmpeg backend), QML.
- The domain layer is pure Python with no Qt imports. The application layer depends on domain only. Infrastructure implements application ports using PySide6, SQLite, and the filesystem.
- Build/packaging uses setuptools + `python -m build`. Tests use pytest. Linting and formatting use Ruff. CI is GitHub Actions running lint, tests (QT_QPA_PLATFORM=offscreen), and build.
- No native-code build system, no C++ test frameworks, no Prettier, no GStreamer integration.

## Consequences

- Positive: no compile/link step; iteration is edit-and-run. pytest + Ruff give a fast, enforced quality loop in CI.
- Positive: domain purity is enforced by convention and by tests (no Qt imports in domain/application), not by a linker, so the invariant needs explicit test coverage.
- Negative: Qt C++-specific idioms (Q_PROPERTY registration, moc) do not apply; the QML bridge is implemented via PySide6 property/signal declaration.
- Negative: startup and runtime performance are bounded by CPython; acceptable for an audio-only desktop player, but heavy per-frame Python work in QML bindings must be avoided.

## Alternatives considered

- **C++20 + Qt 6 (the historical superseded plan)**: full type safety and performance, but the build/test infrastructure cost (CMake, CTest, Catch2/doctest) dominated early milestones. Rejected for the clean rebuild.
- **Rust with a Qt binding**: memory safety and performance, but ecosystem maturity for QML integration was weaker and team iteration speed lower. Rejected.
- **Electron / web UI**: large dependency footprint and poor fit for a lightweight local-first player. Rejected.
- **PySide6 (Qt Widgets) instead of QML**: simpler bridge but less flexible theming and less declarative UI foundation. QML chosen for the token/primitives design system.

## Status

Accepted
