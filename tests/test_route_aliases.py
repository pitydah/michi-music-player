"""Test that all navigation calls in QML use valid routes from registry."""
from __future__ import annotations

import os


def _extract_navigate_calls(qml_file: str) -> list[str]:
    """Extract route strings from navigationBridge.navigate('...') calls in QML."""
    routes = []
    with open(qml_file, encoding="utf-8", errors="ignore") as f:
        content = f.read()
    import re
    # Match navigate("route") or navigate('route')
    for m in re.finditer(r'navigate(?:WithParams)?\s*\(\s*["\']([^"\']+)["\']', content):
        routes.append(m.group(1))
    # Match routeRequested('route')
    for m in re.finditer(r'routeRequested\s*\(\s*["\']([^"\']+)["\']', content):
        routes.append(m.group(1))
    return routes


def test_all_navigate_calls_exist_in_registry():
    from ui_qml_bridge.route_registry import ROUTES, ROUTE_ALIASES, resolve_route

    ui_qml_dir = os.path.join(os.path.dirname(__file__), "..", "ui_qml")

    missing = []
    for root, _dirs, files in os.walk(ui_qml_dir):
        for f in files:
            if not f.endswith(".qml"):
                continue
            fpath = os.path.join(root, f)
            calls = _extract_navigate_calls(fpath)
            for route in calls:
                resolved = resolve_route(route)
                if resolved not in ROUTES and route not in ROUTE_ALIASES:
                    rel = os.path.relpath(fpath, ui_qml_dir)
                    missing.append(f"{rel}: navigates to '{route}' (resolved: '{resolved}') not in registry")

    assert not missing, "Missing routes:\n" + "\n".join(missing[:20])
