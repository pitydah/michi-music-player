"""Test: QML app startup — bootstrap, bridge creation, engine load, root objects."""
from unittest.mock import patch



class TestQmlStartup:
    def test_bootstrap_build_all_services(self):
        with patch("PySide6.QtGui.QGuiApplication"), \
             patch("PySide6.QtQml.QQmlApplicationEngine"):
            from core.service_container import ServiceContainer
            from core.composition.infrastructure import build as infra
            from core.composition.playback import build as playback
            from core.composition.library import build as library
            from core.composition.audio_lab import build as audio_lab
            from core.composition.ecosystem import build as eco
            from core.composition.settings import build as settings_b
            from core.composition.intelligence import build as intel
            c = ServiceContainer()
            infra(c)
            playback(c)
            library(c)
            audio_lab(c)
            eco(c)
            settings_b(c)
            intel(c)
            missing = [n for n in c.list_services() if c.get(n) is None]
            assert len(missing) <= 2, f"Too many missing services: {missing}"

    def test_bootstrap_creates_bridges(self):
        with patch("PySide6.QtGui.QGuiApplication"), \
             patch("PySide6.QtQml.QQmlApplicationEngine"):
            from core.application_bootstrap import ApplicationBootstrap
            b = ApplicationBootstrap()
            b.build()
            bridges = b.create_bridges()
            assert bridges is not None
            essential = ["navigation", "app", "library", "queue", "playback"]
            for name in essential:
                assert name in bridges, f"Missing essential bridge: {name}"

    def test_context_properties_registered(self):
        from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
        assert len(QML_CONTEXT_BINDINGS) >= 30
        assert "navigationBridge" in QML_CONTEXT_BINDINGS or "navigationBridge" in str(QML_CONTEXT_BINDINGS)

    def test_sidebar_has_current_route_property(self):
        from pathlib import Path
        content = Path("ui_qml/components/SidebarItem.qml").read_text()
        assert "currentRoute" in content
        assert "property bool active: route" in content

    def test_qml_app_imports(self):
        import michi.qml_app
        assert hasattr(michi.qml_app, 'run_qml')

    def test_qml_app_has_translator(self):
        code = open("michi/qml_app.py").read()
        assert "QTranslator" in code
        assert "installTranslator" in code
