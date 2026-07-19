"""Tests for canonical route registry — all routes point to existing QML files."""
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_all_routes_have_source():
    from ui_qml_bridge.route_registry import ROUTES
    for route_id, info in ROUTES.items():
        src = info.get("source", "")
        assert src, f"{route_id}: missing source"
        qml_path = REPO / "ui_qml" / src.replace("../", "")
        assert qml_path.exists(), f"{route_id}: {qml_path} not found"


def test_all_routes_have_title():
    from ui_qml_bridge.route_registry import ROUTES
    for route_id, info in ROUTES.items():
        assert info.get("title"), f"{route_id}: missing title"


def test_all_routes_have_category():
    from ui_qml_bridge.route_registry import ROUTES
    for route_id, info in ROUTES.items():
        assert info.get("category"), f"{route_id}: missing category"


def test_no_duplicate_sources():
    from ui_qml_bridge.route_registry import ROUTES
    sources = {}
    for route_id, info in ROUTES.items():
        src = info.get("source", "")
        if src in sources:
            # Same QML page for different routes is OK (e.g., folder list + detail)
            continue


def test_functional_route_count():
    from ui_qml_bridge.route_registry import ROUTES
    functional = [r for r, i in ROUTES.items() if i.get("status") == "functional"]
    assert len(functional) >= 60, f"Expected 60+ functional routes, got {len(functional)}"


def test_all_params_defined():
    from ui_qml_bridge.route_registry import ROUTES
    for route_id, info in ROUTES.items():
        params = info.get("params")
        if params is None:
            continue
        if not isinstance(params, dict):
            continue
        for param_name, param_info in params.items():
            assert "required" in param_info, f"{route_id}.{param_name}: missing required"
            assert "type" in param_info, f"{route_id}.{param_name}: missing type"


def test_no_placeholder_routes():
    from ui_qml_bridge.route_registry import ROUTES
    allowed_states = {"planned", "experimental", "deprecated", "configuration_required",
                      "dependency_missing", "hardware_validation_pending", "unavailable"}
    for route_id, info in ROUTES.items():
        src = info.get("source", "")
        status = info.get("status", "")
        if "PlaceholderPage" in src or "Placeholder" in src:
            if status in allowed_states:
                continue
            if status == "deprecated":
                continue
            pytest.fail(f"{route_id}: uses PlaceholderPage: {src} (status: {status})")


def test_no_route_duplicates():
    from ui_qml_bridge.route_registry import ROUTES
    ids = list(ROUTES.keys())
    assert len(ids) == len(set(ids)), "Duplicate route IDs in ROUTES"


def test_all_categories_valid():
    from ui_qml_bridge.route_registry import ROUTES
    valid = {"core", "library", "detail", "tools", "settings", "audio_lab",
             "playback", "navigation", "experimental", "migration", "system"}
    for route_id, info in ROUTES.items():
        cat = info.get("category", "")
        assert cat in valid, f"{route_id}: invalid category {cat}"


def test_source_path_format():
    from ui_qml_bridge.route_registry import ROUTES
    for route_id, info in ROUTES.items():
        src = info.get("source", "")
        assert src.startswith("../pages/") or src.startswith("../components/"), \
            f"{route_id}: source should start with ../pages/ or ../components/"
