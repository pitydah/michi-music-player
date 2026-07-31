#!/usr/bin/env python3
"""Composition root smoke test.

Verifies that the service composition imports cleanly and that the Michi AI V2
architecture is what actually runs: the assistant engine uses the canonical
``ToolRegistryV2`` (not a legacy registry) and the builtin tools are registered.

Exit code 0 on success, non-zero on failure. Intended to run under
``QT_QPA_PLATFORM=offscreen`` in CI as a fast wiring gate.
"""
from __future__ import annotations

import os
import sys


def _ensure_offscreen() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.instance() is None:
            QGuiApplication(sys.argv)
    except Exception:
        # The wiring checks below do not require a running GUI; only create the
        # app when the offscreen platform is available.
        pass


def main() -> int:
    _ensure_offscreen()

    # 1. Every composition builder must import without errors.
    from core.composition import (  # noqa: F401
        audio_lab,
        ecosystem,
        infrastructure,
        intelligence,
        library,
        playback,
        settings,
    )
    from core.application_bootstrap import ApplicationBootstrap
    from core.assistant_initializer import create_assistant_composition
    from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

    # 2. The bootstrap composition root instantiates.
    bootstrap = ApplicationBootstrap()
    assert bootstrap.container is not None, "bootstrap must expose a container"

    # 3. AI V2 wiring: the engine must use the canonical ToolRegistryV2, not a
    #    legacy/empty registry.
    comp = create_assistant_composition()
    assert isinstance(comp.tool_registry, ToolRegistryV2), (
        "assistant tool_registry must be ToolRegistryV2"
    )
    assert comp.core_service.tool_registry is comp.tool_registry, (
        "MichiAIEngine must use the canonical ToolRegistryV2, not a legacy registry"
    )
    assert comp.tool_registry.list_tools(), (
        "builtin tools must be registered in the V2 registry"
    )

    print("OK: composition root smoke test passed")
    print(f"  - AI V2 registry: {len(comp.tool_registry.list_tools())} tools wired")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"SMOKE FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - defensive
        print(f"SMOKE ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
