"""Route registry contract tests.

Validates that every route in the registry has a well-formed params spec.
Each params entry must be None or a dict where each value is a dict with
at least 'required' (bool) and 'type' (string) keys.
"""
from __future__ import annotations

import pytest

from ui_qml_bridge.route_registry import ROUTES, resolve_route, get_sidebar_sections


class TestRouteRegistryContract:
    def test_every_route_has_valid_params_spec(self):
        bad = []
        for route, info in ROUTES.items():
            params = info.get("params")
            if params is None:
                continue
            if not isinstance(params, dict):
                bad.append(f"{route}: params is {type(params).__name__}, not dict")
                continue
            for key, spec in params.items():
                if not isinstance(spec, dict):
                    bad.append(f"{route}.params.{key}: spec is {type(spec).__name__}, not dict")
                    continue
                if "required" not in spec:
                    bad.append(f"{route}.params.{key}: missing 'required' key")
                if "type" not in spec:
                    bad.append(f"{route}.params.{key}: missing 'type' key")
        assert bad == [], "Invalid params specs:\n" + "\n".join(bad)

    def test_every_route_has_source(self):
        missing = [r for r, info in ROUTES.items() if not info.get("source")]
        assert missing == [], f"Routes missing source: {missing}"

    def test_every_route_has_title(self):
        missing = [r for r, info in ROUTES.items() if not info.get("title")]
        assert missing == [], f"Routes missing title: {missing}"

    def test_resolve_route_returns_canonical(self):
        for route in ROUTES:
            resolved = resolve_route(route)
            assert resolved == route, f"resolve_route({route}) returned {resolved}"

    def test_sidebar_sections_are_well_formed(self):
        sections, fixed = get_sidebar_sections()
        for section in sections:
            assert "route" in section
            assert "title" in section
            assert "icon" in section
            assert isinstance(section.get("children", []), list)
        for item in fixed:
            assert "route" in item
            assert "title" in item

    @pytest.mark.parametrize("route", [
        "audio_lab.capture",
        "audio_lab.cd_ripper",
        "audio_lab.adc_recorder",
        "audio_lab.analysis",
        "audio_lab.backup",
        "home_audio",
        "home_audio.stream",
        "settings",
    ])
    def test_critical_routes_exist(self, route):
        assert route in ROUTES, f"Route {route} not found in registry"

    def test_audio_lab_routes_have_valid_parents(self):
        for route, info in ROUTES.items():
            if route.startswith("audio_lab."):
                parent = info.get("parent")
                if parent is not None:
                    assert parent in ROUTES or parent == "audio_lab", \
                        f"{route} has invalid parent {parent}"
