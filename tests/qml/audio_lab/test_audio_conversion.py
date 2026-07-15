"""Tests for AudioConversionPage — format selector, codec, quality, preview, convert."""
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
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/audio_lab/AudioConversionPage.qml")))
    return component


class TestAudioConversion:
    def test_instantiate(self, engine):
        component = _load_page(engine)
        assert component.isReady(), component.errorString()

    def test_object_name(self, engine):
        component = _load_page(engine)
        assert component.isReady()
        obj = component.create()
        try:
            assert obj.property("objectName") == "audioConversion.page"
        finally:
            obj.deleteLater()

    def test_format_selector_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "FLAC" in source
        assert "MP3" in source
        assert "OGG" in source
        assert "Opus" in source
        assert "WAV" in source
        assert "AAC" in source

    def test_codec_map_defined(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "flac" in source
        assert "libmp3lame" in source
        assert "libvorbis" in source
        assert "libopus" in source
        assert "pcm_s16le" in source
        assert "aac" in source

    def test_quality_slider_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "MichiSlider" in source
        assert "Calidad VBR" in source

    def test_sample_rate_selector(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "sampleRateModel" in source
        assert "44100" in source

    def test_bit_depth_selector(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "bitDepthModel" in source
        assert "16" in source

    def test_channels_selector(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "channelsModel" in source
        assert "2" in source

    def test_metadata_options(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Conservar metadatos" in source
        assert "Conservar carátula" in source

    def test_output_options(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "namingTemplate" in source
        assert "collisionPolicy" in source
        assert "collisionModel" in source

    def test_preview_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Previsualización" in source
        assert "estimated_size" in source
        assert "free_space" in source

    def test_page_states(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "INPUT_READY" in source
        assert "PREVIEWING" in source
        assert "CONVERTING" in source
        assert "CANCELLING" in source
        assert "COMPLETED" in source
        assert "FAILED" in source

    def test_convert_cancel_retry_buttons(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "startConvert" in source
        assert "cancelConvert" in source
        assert "retryConvert" in source

    def test_start_preview_function(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "startPreview" in source

    def test_status_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Requiere ffmpeg" in source
        assert "Experimental" in source

    def test_conversion_progress_bar(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "MichiProgressBar" in source
        assert "convProgress" in source

    def test_accessible_attributes(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Accessible.Button" in source or "Accessible" in source

    def test_page_state_property(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "property string pageState" in source

    def test_no_static_demo_data(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "static" not in source.lower()
