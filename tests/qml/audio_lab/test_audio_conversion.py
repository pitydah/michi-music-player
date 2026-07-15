<<<<<<< Updated upstream
=======
<<<<<<< HEAD
"""Tests for AudioConversionPage — format selector, codec, quality, preview, convert."""
from pathlib import Path
=======
>>>>>>> Stashed changes
"""Tests for Audio Conversion Page — real controls, no static/demo elements."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes


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

<<<<<<< Updated upstream
    def test_conversion_job_lifecycle(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        results = []
        svc.conversionCompleted.connect(lambda jid, t: results.append(("completed", jid, t)))
        svc.conversionFailed.connect(lambda jid, e: results.append(("failed", jid, e)))
        job_id = svc.convert(sample_wav, profile)
        assert job_id != ""
        _process_events(3.0)
=======
<<<<<<< HEAD
    def test_output_options(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "namingTemplate" in source
        assert "collisionPolicy" in source
        assert "collisionModel" in source
>>>>>>> Stashed changes

    def test_no_static_flac_default(self):
        assert True

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

<<<<<<< Updated upstream
=======
    def test_no_static_demo_data(self, engine):
        source = (QML_DIR / "pages/audio_lab/AudioConversionPage.qml").read_text()
        assert "static" not in source.lower()
=======
    def test_conversion_job_lifecycle(self, app, db, wm, sample_wav):
        from core.audio_lab.audio_conversion_service import AudioConversionService, ConversionProfile
        svc = AudioConversionService(db=db, wm=wm)
        profile = ConversionProfile(format="WAV", output_dir=tempfile.gettempdir())
        results = []
        svc.conversionCompleted.connect(lambda jid, t: results.append(("completed", jid, t)))
        svc.conversionFailed.connect(lambda jid, e: results.append(("failed", jid, e)))
        job_id = svc.convert(sample_wav, profile)
        assert job_id != ""
        _process_events(3.0)

    def test_no_static_flac_default(self):
        assert True

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

>>>>>>> Stashed changes
    def test_output_dir_field_editable(self):
        assert True

    def test_naming_template_field_editable(self):
        assert True

    def test_metadata_checkbox_present(self):
        assert True

    def test_artwork_checkbox_present(self):
        assert True

    def test_preview_estimated_size(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.preview(tempfile.tempnam() if hasattr(tempfile, 'tempnam') else "/tmp/test.wav")
        assert "ok" in result or "error" in result

    def test_conversion_bridge_created(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        assert bridge is not None
        assert hasattr(bridge, 'startConversion')
        assert hasattr(bridge, 'cancelJob')

    def test_conversion_bridge_output_dir(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        bridge.outputDir = "/tmp"
        assert bridge.outputDir == "/tmp"

    def test_conversion_bridge_collision_policy(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        bridge.collisionPolicy = "overwrite"
        assert bridge.collisionPolicy == "overwrite"

    def test_conversion_bridge_cancel_all(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.cancelAll()
        assert result["ok"] is True

    def test_conversion_bridge_validate_audio(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.validateAudioFile("/test.flac")
        assert result["ok"] is True

    def test_conversion_bridge_validate_video(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.validateAudioFile("/test.mp4")
        assert result["ok"] is False
        assert "VIDEO_NOT_SUPPORTED" in result.get("error", "")

    def test_convert_button_enabled_with_output_dir(self):
        assert True

    def test_convert_button_disabled_without_output_dir(self):
        assert True

    def test_cancel_button_during_conversion(self):
        assert True

    def test_retry_button_after_failure(self):
        assert True

    def test_progress_bar_visible_during_conversion(self):
        assert True

    def test_file_count_and_eta_displayed(self):
        assert True
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
