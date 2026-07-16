"""Workflow: Startup → Home page renders with correct state."""
from __future__ import annotations

import pytest
from PySide6.QtCore import QUrl


pytestmark = [
    pytest.mark.qml_module("home"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("home"),
]


class TestHomeWorkflow:
    def test_home_page_loads(self, qml_app, bootstrap, engine):
        main_qml = str(bootstrap._bridges.get("app", "ui_qml/Main.qml"))
        engine.load(QUrl.fromLocalFile(main_qml))
        assert engine.rootObjects(), "QML root objects should load"

    def test_home_page_has_bridge(self, bootstrap):
        home_bridge = bootstrap._bridges.get("home")
        assert home_bridge is not None, "HomeBridge should be registered"

    def test_home_page_capabilities(self, bootstrap):
        cap = bootstrap._bridges.get("capability")
        assert cap is not None, "CapabilityBridge should be registered"
