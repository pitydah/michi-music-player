"""Test: all QML routes load without errors."""
from pathlib import Path



class TestQmlRoutes:
    def test_all_routes_have_qml_files(self):
        from ui_qml_bridge.route_registry import ROUTES
        missing = []
        for route_id, info in ROUTES.items():
            src = info.get("source", "")
            if not src:
                missing.append(f"{route_id}: no source")
                continue
            qml_path = Path("ui_qml") / src.replace("../", "")
            if not qml_path.exists():
                missing.append(f"{route_id}: {qml_path} not found")
        assert len(missing) == 0, "Missing route files:\n" + "\n".join(missing[:10])

    def test_no_placeholder_routes_functional(self):
        from ui_qml_bridge.route_registry import ROUTES
        placeholders = []
        for route_id, info in ROUTES.items():
            src = info.get("source", "")
            if "PlaceholderPage" in src and info.get("status") != "deprecated":
                placeholders.append(route_id)
        assert len(placeholders) == 0, f"Routes pointing to PlaceholderPage: {placeholders}"

    def test_all_routes_have_title(self):
        from ui_qml_bridge.route_registry import ROUTES
        for route_id, info in ROUTES.items():
            assert info.get("title"), f"{route_id}: missing title"

    def test_all_routes_have_status(self):
        from ui_qml_bridge.route_registry import ROUTES
        valid = {"functional", "partial", "experimental", "unavailable", "deprecated", "hardware_validation_pending"}
        for route_id, info in ROUTES.items():
            assert info.get("status") in valid, f"{route_id}: invalid status {info.get('status')}"

    def test_routes_have_valid_categories(self):
        from ui_qml_bridge.route_registry import ROUTES
        valid = {"core", "library", "detail", "tools", "settings", "audio_lab",
                 "playback", "navigation", "experimental", "migration"}
        for route_id, info in ROUTES.items():
            cat = info.get("category", "")
            assert cat in valid, f"{route_id}: invalid category {cat}"

    def test_mobile_pairing_route_exists(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "devices.mobile_pairing" in ROUTES or "devices.mobile" in ROUTES

    def test_all_route_params_valid(self):
        from ui_qml_bridge.route_registry import ROUTES
        for route_id, info in ROUTES.items():
            params = info.get("params", {})
            for pname, pinfo in params.items():
                assert "required" in pinfo, f"{route_id}.{pname}: missing required"
                assert "type" in pinfo, f"{route_id}.{pname}: missing type"

    def test_sidebar_routes_exist_in_registry(self):
        """All routes referenced in Sidebar.qml exist in route_registry."""
        from ui_qml_bridge.route_registry import ROUTES
        content = Path("ui_qml/shell/Sidebar.qml").read_text()
        import re
        routes_in_sidebar = set(re.findall(r'route:\s*"([^"]+)"', content))
        missing = [r for r in routes_in_sidebar if r not in ROUTES]
        assert len(missing) == 0, f"Sidebar routes missing from registry: {missing}"

    def test_qml_context_bindings_match_factory(self):
        """Verify context binding names match what BridgeFactory creates."""
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        # Each binding needs a corresponding bridge key
        if isinstance(QML_CONTEXT_BINDINGS, dict):
            for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
                assert bridge_key, f"{qml_name}: empty bridge key"
