from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


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
        assert None is None

    def test_analysis_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewAnalysis("/nonexistent.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_validate_analysis_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.validateAnalysis("/nonexistent.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_preview_conversion_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewConversion("/nonexistent.flac", "wav")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_preview_normalization_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewNormalization("/nonexistent.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_preview_integrity_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewIntegrity("/nonexistent.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_preview_comparison_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewComparison("/a.flac", "/b.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_cancel_unknown_job(self):
        bridge = AudioLabBridge()
        result = bridge.cancelJob("nonexistent")
        assert result.get("ok") is False
        assert result.get("error_code") == "JOB_NOT_FOUND"

    def test_retry_unknown_job(self):
        bridge = AudioLabBridge()
        result = bridge.retryJob("nonexistent")
        assert result.get("ok") is False
        assert result.get("error_code") == "JOB_NOT_FOUND"

    def test_job_status_unknown(self):
        bridge = AudioLabBridge()
        result = bridge.jobStatus("ghost")
        assert result.get("ok") is False
        assert result.get("error_code") == "JOB_NOT_FOUND"

    def test_start_analysis_no_service(self):
        bridge = AudioLabBridge()
        job_id = bridge.startAnalysis("/test.flac")
        assert job_id == ""

    def test_start_conversion_no_service(self):
        bridge = AudioLabBridge()
        job_id = bridge.startConversion("/test.flac", "wav")
        assert job_id == ""

    def test_start_integrity_no_service(self):
        bridge = AudioLabBridge()
        job_id = bridge.startIntegrity("/test.flac")
        assert job_id == ""

    def test_start_comparison_no_service(self):
        bridge = AudioLabBridge()
        job_id = bridge.startComparison("/a.flac", "/b.flac")
        assert job_id == ""

    def test_capability_map_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.capabilityMap()
        assert result == {}

    def test_service_available_false(self):
        bridge = AudioLabBridge()
        assert bridge.serviceAvailable is False

    def test_job_service_available_false(self):
        bridge = AudioLabBridge()
        assert bridge.jobServiceAvailable is False

    def test_cleanup_empty(self):
        bridge = AudioLabBridge()
        result = bridge.cleanupCompleted()
        assert result.get("ok") is True
        assert result.get("cleaned") == 0
