#!/usr/bin/env python3
"""Audit QML composition: verify SERVICE_ORDER coverage, dependency satisfaction, and bridge completeness."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.dependency_graph import SERVICE_ORDER, SERVICE_DEPENDENCIES, resolve_order  # noqa: E402


def audit_service_order() -> list[str]:
    errors = []
    if not SERVICE_ORDER:
        errors.append("SERVICE_ORDER is empty")
    if len(SERVICE_ORDER) != len(set(SERVICE_ORDER)):
        errors.append("SERVICE_ORDER contains duplicates")
    return errors


def audit_dependencies() -> list[str]:
    errors = []
    order_set = set(SERVICE_ORDER)
    for svc, deps in SERVICE_DEPENDENCIES.items():
        if svc not in order_set:
            errors.append(f"Service '{svc}' has dependencies but is not in SERVICE_ORDER")
        for dep in deps:
            if dep not in order_set:
                errors.append(f"Dependency '{dep}' (required by '{svc}') not in SERVICE_ORDER")
            if dep == svc:
                errors.append(f"'{svc}' depends on itself")
    return errors


def audit_topological_order() -> list[str]:
    errors = []
    try:
        ordered = resolve_order()
    except ValueError as e:
        errors.append(str(e))
        return errors
    pos = {svc: i for i, svc in enumerate(ordered)}
    for svc, deps in SERVICE_DEPENDENCIES.items():
        for dep in deps:
            if dep in pos and svc in pos and pos[dep] >= pos[svc]:
                errors.append(f"'{dep}' should come before '{svc}' in resolved order")
    return errors


def audit_bridge_coverage() -> list[str]:
    errors = []
    bridge_dir = REPO / "ui_qml_bridge"
    bridge_files = sorted(f.stem for f in bridge_dir.glob("*_bridge.py") if f.stem != "__init__")
    expected_bridges = {"navigation", "theme", "notification", "accessibility", "library",
                        "playback", "nowplaying", "queue", "history", "mix", "lyrics",
                        "radio", "global_search", "settings", "eq", "output_profiles",
                        "audio_lab", "metadata", "smart_tagging", "disc_lab",
                        "library_doctor", "diagnostics", "michi_ai", "connections",
                        "home_audio", "devices", "home"}
    for eb in expected_bridges:
        if eb not in bridge_files and eb + "_bridge" not in bridge_files:
            errors.append(f"Expected bridge '{eb}' not found in ui_qml_bridge/")
    return errors


def main() -> int:
    errors = []
    errors.extend(audit_service_order())
    errors.extend(audit_dependencies())
    errors.extend(audit_topological_order())
    errors.extend(audit_bridge_coverage())

    print("QML Composition Audit")
    print("=" * 60)
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("All composition checks passed.")
    print(f"Services in SERVICE_ORDER: {len(SERVICE_ORDER)}")
    print(f"Services with explicit dependencies: {len(SERVICE_DEPENDENCIES)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
