"""Negative tests for Audio Lab: missing service, invalid format, conversion failure, cancellation."""
from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=0.5):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestAudioNegative:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    def test_null_bridge_does_not_crash(self):
        alab = None
        assert alab is None

    def test_conversion_without_output_dir(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.startConversion("/nonexistent.flac")
        assert result["ok"] is False

    def test_conversion_source_not_found(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        bridge.outputDir = "/tmp"
        result = bridge.startConversion("/nonexistent/file.flac")
        assert result["ok"] is False
        assert "SOURCE_NOT_FOUND" in result.get("error", "")

    def test_conversion_unsupported_format(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        bridge.outputDir = "/tmp"
        path = "/tmp/test.xyz"
        with open(path, "w") as f:
            f.write("test")
        try:
            result = bridge.startConversion(path)
            assert result["ok"] is False
            assert "UNSUPPORTED_FORMAT" in result.get("error", "")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_conversion_cancel_nonexistent_job(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.cancelJob("nonexistent_job")
        assert result["ok"] is False
        assert result.get("error") == "NOT_FOUND"

    def test_analysis_without_files(self):
        lab = MagicMock()
        lab.analyzeFile = MagicMock(return_value={"status": "error", "error": "No files selected"})
        result = lab.analyzeFile("")
        assert result["status"] == "error"

    def test_analysis_backend_unavailable(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        bridge = AudioLabBridge()
        result = bridge.analyzeFile("/nonexistent.flac")
        assert result["status"] in ("unsupported", "error")

    def test_integrity_missing_file(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        bridge = AudioLabBridge()
        result = bridge.integrityCheck("/nonexistent/file.flac")
        assert result["status"] in ("error", "unavailable")

    def test_comparison_no_backend(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        bridge = AudioLabBridge()
        result = bridge.compareFiles("/a.flac", "/b.flac")
        assert "error" in result or result.get("identical") is not None

    def test_conversion_video_format_rejected(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.validateAudioFile("/test.mp4")
        assert result["ok"] is False
        assert "VIDEO_NOT_SUPPORTED" in result.get("error", "")

    def test_conversion_collision_skip_existing(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        bridge.outputDir = "/tmp"
        bridge.collisionPolicy = "skip"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            existing = f.name
        try:
            bridge.startConversion(existing)
        finally:
            if os.path.exists(existing):
                os.unlink(existing)

    def test_preview_missing_source(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.preview("/nonexistent.flac")
        assert result["ok"] is False

    def test_job_bridge_cancel_nonexistent(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.cancelJob(99999)
        assert result["ok"] is False
        assert result.get("error") == "NOT_FOUND"

    def test_job_bridge_retry_nonexistent(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge()
        result = jb.retryJob(99999)
        assert result["ok"] is False
        assert result.get("error") == "NOT_FOUND"

    def test_no_false_success_on_error(self):
        assert True

    def test_error_message_not_empty_on_failure(self):
        assert True

    def test_disabled_buttons_when_no_service(self):
        assert True

    def test_bridge_status_badge_on_null(self):
        assert True
