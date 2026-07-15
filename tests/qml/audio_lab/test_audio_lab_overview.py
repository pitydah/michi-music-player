"""Tests for AudioLabOverviewPage — tool hub with status and keyboard navigation."""
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = pytest.mark.qml_module("audio_lab")

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_page(engine) -> QQmlComponent:
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml")))
    return component


class TestAudioLabOverview:
    def test_instantiate(self, engine):
        component = _load_page(engine)
        assert component.isReady(), component.errorString()

    def test_object_names(self, engine):
        component = _load_page(engine)
        assert component.isReady()
        obj = component.create()
        try:
            assert obj.property("objectName") == "audioLab.page"
        finally:
            obj.deleteLater()

    def test_hero_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "HeroMaterial" in source

    def test_section_headers(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Sección de herramientas" in source
        assert "Sección de estado del backend" in source

    def test_tool_cards_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "analysis" in source
        assert "conversion" in source
        assert "normalization" in source
        assert "replaygain" in source
        assert "integrity" in source
        assert "comparison" in source
        assert "jobs" in source
        assert "profiles" in source

    def test_repeater_tool_model(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "ListModel" in source
        assert "toolId" in source
        assert "toolState" in source

    def test_tool_states_defined(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "LOADING" in source
        assert "READY" in source
        assert "ERROR" in source

    def test_status_badge_for_non_ready(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "StatusBadge" in source
        assert "No disponible" in source or "Cargando" in source

    def test_keyboard_navigation(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "KeyNavigation" in source

    def test_escape_navigates_home(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Keys.onEscapePressed" in source

    def test_accessible_roles(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Accessible.Panel" in source
        assert "Accessible.Heading" in source

    def test_backend_info_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "backendInfo" in source
        assert "pipelineInfo" in source

    def test_status_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Experimental" in source
        assert "Requiere ffmpeg" in source

    def test_glass_card_interactive_property(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "interactive" in source

    def test_no_static_demo_text(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "static" not in source.lower()

    def test_michitheme_references(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "MichiTheme" in source

    def test_glass_card_focus_policy(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "focusPolicy: Qt.StrongFocus" in source

    def test_enter_space_activation(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Keys.onReturnPressed" in source
        assert "Keys.onSpacePressed" in source
