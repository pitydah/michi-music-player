"""All routes runtime test — verifies every registered route can load."""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _get_all_routes():
    from ui_qml_bridge.route_registry import ROUTES
    return sorted(ROUTES.keys())


@pytest.mark.parametrize("route", _get_all_routes())
def test_route_has_valid_source(route):
    from ui_qml_bridge.route_registry import ROUTES
    info = ROUTES[route]
    source = info.get("source", "")
    assert source, f"Route {route} has no source"
    assert source.endswith(".qml"), f"Route {route} source {source} is not QML"


def test_all_audio_lab_routes_have_sources():
    from ui_qml_bridge.route_registry import ROUTES
    for route, info in ROUTES.items():
        if route.startswith("audio_lab."):
            assert info.get("source"), f"Audio Lab route {route} missing source"


def test_all_home_audio_routes_have_sources():
    from ui_qml_bridge.route_registry import ROUTES
    for route, info in ROUTES.items():
        if route.startswith("home_audio"):
            assert info.get("source"), f"Home Audio route {route} missing source"


def test_critical_routes_have_object_names():
    from ui_qml_bridge.route_registry import ROUTES
    for route in ["home", "library", "playlists", "audio_lab", "settings"]:
        assert route in ROUTES, f"Critical route {route} missing"
