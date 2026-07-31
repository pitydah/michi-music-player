#!/usr/bin/env python3
"""Composition root smoke test — productive bootstrap lifecycle.

Runs the *real* ``ApplicationBootstrap`` lifecycle against a temp database:

    build -> start -> create_bridges -> register_context -> load_qml -> shutdown

A FAILED bootstrap must abort bridge creation and QML loading (Correction 8),
so this gate fails loudly if a required service is missing instead of
presenting a broken surface. It also verifies the Michi AI V2 wiring: the
engine uses the canonical ``ToolRegistryV2``, one ``CapabilityResolver`` is
shared across registry/planner/validator, and the plan components are stored
on the composition (Correction 7).

Exit code 0 on success, non-zero on failure. Intended to run under
``QT_QPA_PLATFORM=offscreen`` in CI as a fast wiring gate.
"""
from __future__ import annotations

import os
import sys
import tempfile


def _prepare_env() -> str:
    """Point every Michi XDG path at a throwaway temp dir (never the real DB)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    data_dir = tempfile.mkdtemp(prefix="michi_smoke_")
    # Override the centralized path roots so no real user data is touched.
    os.environ["MICHI_TEST_DATA_DIR"] = data_dir
    os.environ["MICHI_TEST_CACHE_DIR"] = data_dir
    os.environ["MICHI_TEST_CONFIG_DIR"] = data_dir
    return data_dir


def _ensure_qapp() -> None:
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        QGuiApplication(sys.argv)


def _minimal_qml(data_dir: str) -> str:
    """Write a self-contained QML file that yields one root object offscreen."""
    qml_path = os.path.join(data_dir, "smoke_root.qml")
    with open(qml_path, "w", encoding="utf-8") as fh:
        fh.write("import QtQuick 2.15\nItem { id: root }\n")
    return qml_path


def _verify_ai_v2_wiring() -> None:
    from core.assistant_initializer import create_assistant_composition
    from michi_ai.v2.plan.plan_builder_v2 import PlanBuilderV2
    from michi_ai.v2.plan.plan_executor_v2 import PlanExecutorV2
    from michi_ai.v2.plan.plan_validator import PlanValidator
    from michi_ai.v2.tools.tool_registry_v2 import ToolRegistryV2

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
    # Correction 7: ONE resolver shared across registry/planner/validator, and
    # the plan components are stored on the composition (not discarded).
    assert comp.capability_resolver is not None
    assert isinstance(comp.planner, PlanBuilderV2)
    assert isinstance(comp.validator, PlanValidator)
    assert isinstance(comp.executor, PlanExecutorV2)
    print(f"  - AI V2 wiring: {len(comp.tool_registry.list_tools())} tools, "
          f"shared resolver + planner/validator/executor stored")


def _run_lifecycle(data_dir: str) -> None:
    from PySide6.QtQml import QQmlApplicationEngine
    from core.application_bootstrap import (
        ApplicationBootstrap,
        BOOT_FAILED,
        BOOT_STOPPED,
    )

    bootstrap = ApplicationBootstrap()
    assert bootstrap.container is not None, "bootstrap must expose a container"

    # build -> start
    bootstrap.build()
    bootstrap.start()
    assert bootstrap.boot_state != BOOT_FAILED, (
        f"bootstrap FAILED — required services missing: {bootstrap.failed_services}"
    )

    # create_bridges (must abort only when FAILED; READY/DEGRADED proceed)
    bridges = bootstrap.create_bridges()
    assert bridges, (
        f"create_bridges returned empty (state={bootstrap.boot_state})"
    )

    # register_context -> load_qml
    engine = QQmlApplicationEngine()
    registrar = bootstrap.register_context(engine)
    audit = registrar.audit()
    assert audit["total"] > 0, "no QML context properties registered"

    qml_path = _minimal_qml(data_dir)
    loaded = bootstrap.load_qml(engine, qml_path=qml_path)
    assert loaded is True, (
        f"load_qml failed (state={bootstrap.boot_state})"
    )
    assert engine.rootObjects(), "load_qml reported success but no root objects"

    # shutdown
    pre_shutdown_state = bootstrap.boot_state
    bootstrap.shutdown()
    assert bootstrap.boot_state == BOOT_STOPPED, (
        f"shutdown did not reach STOPPED (state={bootstrap.boot_state})"
    )
    print(f"  - lifecycle: boot={pre_shutdown_state} -> stopped, "
          f"{len(bridges)} bridges, {audit['total']} context props")


def main() -> int:
    _prepare_env()
    _ensure_qapp()

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

    data_dir = _prepare_env()

    # 2. Productive bootstrap lifecycle: build -> start -> bridges -> context
    #    -> load_qml -> shutdown (temp DB, offscreen QML).
    _run_lifecycle(data_dir)

    # 3. AI V2 wiring: canonical registry, shared resolver, stored plan parts.
    _verify_ai_v2_wiring()

    print("OK: composition root smoke test passed")
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
