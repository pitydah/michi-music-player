"""Structural gate: verify bridge count, action handlers, route resolution, context bindings."""
from __future__ import annotations

import pytest

from ui_qml_bridge.context_bindings import CONTEXT_BINDINGS
from ui_qml_bridge.route_registry import ROUTES, CAPABILITY_MAP

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("gate_check"),
    pytest.mark.qml_route("all"),
]


class TestBridgeStructural:
    def test_46_bridges_exist(self, all_bridges):
        # BridgeFactory.create_all() returns 46 bridges currently
        assert len(all_bridges) >= 46, (
            f"Expected >=46 bridges, got {len(all_bridges)}"
        )

    def test_all_bridges_have_names(self, all_bridges):
        for name, bridge in all_bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"

    def test_all_actions_have_handler(self, action_registry):
        assert action_registry is not None
        for aid, desc in action_registry._actions.items():
            assert desc.handler is not None, f"Action '{aid}' has None handler"
            assert callable(desc.handler), f"Action '{aid}' handler not callable"

    def test_all_routes_resolve(self, nav):
        assert nav is not None
        for route in ROUTES:
            resolved = nav._resolve(route)
            assert resolved != "placeholder", f"Route '{route}' resolved to placeholder"
            assert resolved != "home" or route == "home", (
                f"Route '{route}' fell back to home"
            )

    def test_routes_have_valid_sources(self):
        from pathlib import Path
        qml_root = Path("ui_qml")
        for route, info in ROUTES.items():
            source = info.get("source", "")
            if source:
                qml_file = qml_root / source
                assert qml_file.exists(), (
                    f"Route '{route}' source '{source}' not found at {qml_file}"
                )

    def test_context_bindings_match_bridges(self, all_bridges):
        missing = []
        for binding in CONTEXT_BINDINGS:
            from ui_qml_bridge.context_bindings import _EXPLICIT_BRIDGE_KEYS
            key = binding.context_name
            if key in _EXPLICIT_BRIDGE_KEYS:
                bridge_key = _EXPLICIT_BRIDGE_KEYS[key]
            elif key.endswith("Bridge"):
                from ui_qml_bridge.context_bindings import _camel_to_snake
                bridge_key = _camel_to_snake(key[: -len("Bridge")])
            elif key.endswith("Store"):
                bridge_key = _camel_to_snake(key[: -len("Store")])
            else:
                bridge_key = key.lower()
            if bridge_key not in all_bridges:
                missing.append(f"{key} → {bridge_key}")
        assert not missing, (
            f"Missing bridges for context bindings: {missing}"
        )

    def test_capability_map_coverage(self):
        cap_routes = set()
        for pattern in CAPABILITY_MAP:
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                for route in ROUTES:
                    if route.startswith(prefix):
                        cap_routes.add(route)
            else:
                if pattern in ROUTES:
                    cap_routes.add(pattern)
        # All routes should be covered by capability or be capability-free
        for route in ROUTES:
            if route == "placeholder":
                continue
            has_cap = any(
                (route.startswith(p[:-2]) if p.endswith(".*") else route == p)
                for p in CAPABILITY_MAP
            )
            # Routes not in CAPABILITY_MAP are basic (no capability gate needed)
            if not has_cap:
                info = ROUTES[route]
                assert info.get("category") in ("core", "system", "detail", "settings"), (
                    f"Route '{route}' (cat={info.get('category')}) needs capability entry or is non-core"
                )
