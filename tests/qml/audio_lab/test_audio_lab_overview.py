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
            assert obj.property("objectName") == "audioLabOverviewPage"
        finally:
            obj.deleteLater()

    def test_loading_state(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "LoadingState" in source

    def test_error_state(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "ErrorState" in source
        assert "Audio Lab no está disponible" in source

    def test_area_cards_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "AudioLabAreaCard" in source
        assert "diagnostics" in source
        assert "identifier" in source
        assert "backup" in source
        assert "local_intelligence" in source

    def test_status_badges(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "StatusBadge" in source
        assert "FFmpeg" in source

    def test_page_title(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Audio Lab" in source

    def test_michitheme_references(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "MichiTheme" in source

    def test_accessible_role(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Accessible.Pane" in source

    def test_no_static_demo_text(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "static" not in source.lower()

    def test_page_description(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Herramientas para analizar" in source

    def test_flow_layout(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "Flow" in source

    def test_grid_layout_cards(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "GridLayout" in source

    def test_banner_error(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioLabOverviewPage.qml").read_text()
        assert "MichiBanner" in source
        assert "errorMessage" in source
