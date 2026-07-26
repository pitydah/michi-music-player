from __future__ import annotations

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


class TestAudioNegative:
    def test_analysis_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.previewAnalysis("/nonexistent.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_validate_analysis_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.validateAnalysis("/nonexistent.flac")
        assert result.get("ok") is False

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
        assert result.get("error_code") == "NOT_FAILED"

    def test_job_status_unknown(self):
        bridge = AudioLabBridge()
        result = bridge.jobStatus("ghost")
        assert result.get("ok") is False
        assert result.get("error_code") == "JOB_NOT_FOUND"

    def test_start_analysis_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.startAnalysis("/test.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_start_conversion_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.startConversion("/test.flac", "wav")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_start_integrity_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.startIntegrity("/test.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_start_comparison_no_service(self):
        bridge = AudioLabBridge()
        result = bridge.startComparison("/a.flac", "/b.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

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
