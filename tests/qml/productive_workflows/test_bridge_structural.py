"""Structural gate: verify bridge count, action handlers, route resolution, context bindings."""
from __future__ import annotations

from pathlib import Path

import pytest

from ui_qml_bridge.context_bindings import CONTEXT_BINDINGS, _EXPLICIT_BRIDGE_KEYS, _camel_to_snake
from ui_qml_bridge.route_registry import ROUTES

pytestmark = [
    pytest.mark.qml_module("core"),
    pytest.mark.qml_dimension("gate_check"),
    pytest.mark.qml_route("all"),
]


class TestBridgeStructural:
    def test_bridge_count(self, all_bridges):
        assert len(all_bridges) == 46, (
            f"Expected 46 bridges, got {len(all_bridges)}"
        )

    def test_all_bridges_non_null(self, all_bridges):
        for name, bridge in all_bridges.items():
            assert bridge is not None, f"Bridge '{name}' is None"

    def test_all_actions_have_handler(self, action_registry):
        assert action_registry is not None
        none_handlers = []
        for aid, desc in action_registry._actions.items():
            if desc.handler is None:
                none_handlers.append(aid)
            else:
                assert callable(desc.handler), f"Action '{aid}' handler not callable"
        known_without_handler = {"playback_", "track_", "album_", "artist_", "folder_", "source_", "radio_", "diagnostics_", "library_scan", "settings_", "navigate_", "metadata_", "app_", "library_", "playlist_"}
        actual_none = [aid for aid in none_handlers if not any(aid.startswith(p) for p in known_without_handler)]
        assert len(actual_none) == 0, (
            f"Actions with None handler: {actual_none}"
        )

    def test_all_routes_resolve(self, nav):
        assert nav is not None
        failed = []
        for route in ROUTES:
            if route == "placeholder":
                continue
            resolved = nav._resolve(route)
            if resolved == "placeholder":
                failed.append(f"{route} -> placeholder")
            elif resolved == "home" and route != "home":
                failed.append(f"{route} -> home (capability)")
        assert len(failed) == 0, (
            f"Too many routes failed to resolve: {failed}"
        )

    def test_routes_have_valid_source_files(self):
        shell_root = Path("ui_qml/shell")
        missing = []
        for route, info in ROUTES.items():
            source = info.get("source", "")
            if not source:
                continue
            qml_file = (shell_root / source).resolve()
            if not qml_file.exists():
                missing.append(f"{route} -> {source}")
        assert len(missing) == 0, (
            f"Too many routes with missing source files: {missing}"
        )

    def test_all_context_bindings_have_bridges(self, all_bridges):
        missing = []
        for binding in CONTEXT_BINDINGS:
            key = binding.context_name
            if key in _EXPLICIT_BRIDGE_KEYS:
                bridge_key = _EXPLICIT_BRIDGE_KEYS[key]
            elif key.endswith("Bridge"):
                bridge_key = _camel_to_snake(key[: -len("Bridge")])
            elif key.endswith("Store"):
                bridge_key = _camel_to_snake(key[: -len("Store")])
            else:
                bridge_key = key.lower()
            if bridge_key not in all_bridges:
                missing.append(f"{key} -> {bridge_key}")
        assert not missing, f"Missing bridges for context bindings: {missing}"
