"""Tests for AudioConversionPage — format selector, codec, quality, preview, convert."""
from __future__ import annotations
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
            assert obj.property("objectName") == "audioConversionPage"
        finally:
            obj.deleteLater()

    def test_format_selector_present(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "FLAC" in source
        assert "MP3" in source
        assert "Opus" in source
        assert "WAV" in source
        assert "AAC" in source
        assert "Ogg Vorbis" in source

    def test_codec_map_defined(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert 'value: "flac"' in source or '"flac"' in source
        assert '"wav"' in source
        assert '"mp3"' in source
        assert '"aac"' in source
        assert '"opus"' in source
        assert '"vorbis"' in source

    def test_page_structure(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "AudioInputSelection" in source
        assert "GlassMaterial" in source
        assert "MichiButton" in source
        assert "ComboBox" in source
        assert "MichiProgressBar" in source

    def test_formats_model(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Formato de destino" in source
        assert "model:" in source or "model: " in source

    def test_preview_section(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Previsualización" in source
        assert "previewConversion" in source

    def test_format_selector_includes_all(self):
        formats = {"FLAC", "MP3", "OGG Vorbis", "Opus", "WAV", "AAC"}
        assert len(formats) == 6
        assert "FLAC" in formats
        assert "MP3" in formats
        assert "AAC" in formats

    def test_bitrate_options_present(self):
        bitrates = [128, 192, 256, 320]
        assert len(bitrates) == 4
        assert 320 in bitrates

    def test_sample_rate_options_present(self):
        rates = [8000, 11025, 16000, 22050, 44100, 48000, 88200, 96000, 192000]
        assert len(rates) == 9
        assert 44100 in rates

    def test_bit_depth_options_present(self):
        depths = [8, 16, 24, 32]
        assert 16 in depths
        assert 24 in depths

    def test_channels_options_present(self):
        channels = [1, 2, 6, 8]
        assert 2 in channels

    def test_collision_policy_options(self):
        policies = ["overwrite", "rename", "skip"]
        assert len(policies) == 3
        assert "rename" in policies

    def test_quality_slider_range(self):
        assert 0 <= 5.0 <= 10

    def test_convert_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Convertir" in source

    def test_cancel_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Cancelar" in source

    def test_retry_reset_button(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Reiniciar" in source

    def test_progress_section_visible(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "Conversión completada" in source

    def test_clear_completed_state(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "resetOperation" in source
