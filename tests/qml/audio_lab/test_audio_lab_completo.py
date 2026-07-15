from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.audio_lab_bridge import AudioLabBridge


@pytest.fixture
def mock_services():
    al_svc = MagicMock()
    al_svc.analysis = MagicMock()
    al_svc.conversion = MagicMock()
    al_svc.normalization = MagicMock()
    al_svc.replaygain = MagicMock()
    al_svc.integrity = MagicMock()
    al_svc.comparison = MagicMock()
    al_svc.batch = MagicMock()
    al_svc.profiles = MagicMock()
    al_svc.probe = MagicMock()

    al_svc.analysis.analyze_file.return_value = {
        "filepath": "/test.flac", "format": "flac", "sample_rate": 44100,
        "bit_depth": 16, "channels": 2, "bitrate": 1411000,
        "duration": 180.0, "status": "ok", "codec": "FLAC",
    }
    al_svc.conversion.preview.return_value = {
        "ok": True, "source": "/test.flac", "target": "/out/test.wav",
        "estimated_size": 1000000, "space_ok": True, "format": "WAV", "collision": False,
    }
    al_svc.normalization.measure_loudness.return_value = MagicMock(
        status="completed", filepath="/test.flac", integrated_loudness=-14.0,
        true_peak=0.5, loudness_range=8.0,
    )
    al_svc.replaygain.analyze_track.return_value = MagicMock(
        status="completed", filepath="/test.flac", track_gain=-5.2,
        track_peak=0.8, album_gain=-4.8, album_peak=0.75,
    )
    al_svc.integrity.check.return_value = MagicMock(
        is_valid=True, filepath="/test.flac", status="VALID",
        issues=[], duration=180.0, file_size=10000000, checksum="abc123",
    )
    al_svc.comparison.compare.return_value = MagicMock(
        identical=False, dimensions=[], error="",
    )
    al_svc.capability_map.return_value = {
        "probe": True, "analysis": True, "conversion": True,
        "normalization": True, "replaygain": True, "integrity": True,
        "comparison": True, "batch": True, "profiles": True,
    }

    job_svc = MagicMock()
    job_svc.cancel.return_value = {"ok": True}
    job_svc.status.return_value = {"ok": True, "status": "completed"}

    pc = MagicMock()
    confirm = MagicMock()
    nav = MagicMock()
    cap = MagicMock()

    return al_svc, job_svc, pc, confirm, nav, cap


@pytest.fixture
def bridge(mock_services):
    al_svc, job_svc, pc, confirm, nav, cap = mock_services
    return AudioLabBridge(
        audio_lab_service=al_svc, job_service=job_svc,
        process_controller=pc, confirmation_service=confirm,
        navigation_bridge=nav, capability_bridge=cap,
    )


class TestAudioLabCompleto:

    def test_service_available_property(self, bridge):
        assert bridge.serviceAvailable is True

    def test_service_unavailable(self):
        b = AudioLabBridge()
        assert b.serviceAvailable is False

    def test_capability_map(self, bridge):
        caps = bridge.capabilityMap()
        assert caps.get("analysis") is True
        assert caps.get("conversion") is True

    def test_preview_analysis(self, bridge):
        result = bridge.previewAnalysis("/test.flac")
        assert result.get("ok") is True
        assert result.get("format") == "flac"

    def test_preview_analysis_no_service(self):
        b = AudioLabBridge()
        result = b.previewAnalysis("/test.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"

    def test_validate_analysis_valid(self, bridge):
        result = bridge.validateAnalysis("/test.flac")
        assert result.get("ok") is True

    def test_start_analysis_returns_job_id(self, bridge):
        job_id = bridge.startAnalysis("/test.flac")
        assert job_id.startswith("analysis_")

    def test_preview_conversion(self, bridge):
        result = bridge.previewConversion("/test.flac", "wav")
        assert result.get("ok") is True

    def test_start_conversion_returns_job_id(self, bridge):
        job_id = bridge.startConversion("/test.flac", "wav")
        assert job_id.startswith("conv_")

    def test_preview_normalization(self, bridge):
        result = bridge.previewNormalization("/test.flac")
        assert result.get("ok") is True
        assert "integrated_loudness" in result

    def test_start_normalization(self, bridge):
        result = bridge.startNormalization("/test.flac")
        assert result.get("ok") is True

    def test_preview_replaygain(self, bridge):
        result = bridge.previewReplayGain("/test.flac")
        assert result.get("ok") is True
        assert result.get("track_gain") == -5.2

    def test_validate_replaygain(self, bridge):
        result = bridge.validateReplayGain("/test.flac")
        assert result.get("ok") is True

    def test_start_replaygain_returns_job_id(self, bridge):
        job_id = bridge.startReplayGain("/test.flac")
        assert job_id.startswith("rg_")

    def test_preview_integrity(self, bridge):
        result = bridge.previewIntegrity("/test.flac")
        assert result.get("ok") is True
        assert result.get("is_valid") is True

    def test_validate_integrity(self, bridge):
        result = bridge.validateIntegrity("/test.flac")
        assert result.get("ok") is True

    def test_start_integrity_returns_job_id(self, bridge):
        job_id = bridge.startIntegrity("/test.flac")
        assert job_id.startswith("integrity_")

    def test_preview_comparison(self, bridge):
        result = bridge.previewComparison("/a.flac", "/b.flac")
        assert result.get("ok") is True

    def test_start_comparison_returns_job_id(self, bridge):
        job_id = bridge.startComparison("/a.flac", "/b.flac")
        assert job_id.startswith("compare_")

    def test_cancel_job_active(self, bridge):
        job_id = bridge.startAnalysis("/test.flac")
        result = bridge.cancelJob(job_id)
        assert result.get("ok") is True

    def test_cancel_job_unknown(self, bridge):
        bridge._jobs = None
        result = bridge.cancelJob("nonexistent")
        assert result.get("ok") is False
        assert result.get("error_code") == "JOB_NOT_FOUND"

    def test_retry_job(self, bridge):
        job_id = bridge.startAnalysis("/test.flac")
        result = bridge.retryJob(job_id)
        assert result.get("ok") is True
        assert "new_job_id" in result

    def test_cleanup_completed(self, bridge):
        bridge._pc = None
        bridge._svc = None
        bridge._active_jobs["test1"] = {"type": "analysis", "filepath": "/a.flac", "status": "completed"}
        bridge._active_jobs["test2"] = {"type": "integrity", "filepath": "/b.flac", "status": "completed"}
        result = bridge.cleanupCompleted()
        assert result.get("ok") is True
        assert result.get("cleaned") == 2

    def test_job_status_active(self, bridge):
        job_id = bridge.startAnalysis("/test.flac")
        result = bridge.jobStatus(job_id)
        assert result.get("ok") is True
        assert result.get("status") in ("running", "completed")

    def test_job_status_unknown(self, bridge):
        bridge._jobs = None
        result = bridge.jobStatus("nonexistent")
        assert result.get("ok") is False

    def test_active_jobs(self, bridge):
        bridge.startAnalysis("/test.flac")
        jobs = bridge.activeJobs()
        assert len(jobs) > 0

    def test_refresh(self, bridge):
        result = bridge.refresh()
        assert result.get("ok") is True

    def test_partial_failure_report_no_failures(self, bridge):
        result = bridge.partialFailureReport()
        assert result.get("has_failures") is False

    def test_require_confirmation(self, bridge):
        bridge._confirm.request.return_value = {"ok": True}
        result = bridge.requireConfirmation("delete")
        assert result.get("ok") is True

    def test_navigate_to(self, bridge):
        bridge._nav.navigate.return_value = {"ok": True}
        result = bridge.navigateTo("audio_lab")
        assert result.get("ok") is True

    def test_job_progress_signal(self, bridge):
        signals = []
        bridge.jobProgress.connect(lambda *a: signals.append(a))
        bridge.jobProgress.emit("jid", "analysis", 0.5)
        assert len(signals) == 1

    def test_job_completed_signal(self, bridge):
        signals = []
        bridge.jobCompleted.connect(lambda *a: signals.append(a))
        bridge.jobCompleted.emit("jid", "analysis", {"ok": True})
        assert len(signals) == 1

    def test_job_failed_signal(self, bridge):
        signals = []
        bridge.jobFailed.connect(lambda *a: signals.append(a))
        bridge.jobFailed.emit("jid", "error")
        assert len(signals) == 1

    def test_preview_analysis_captures_error(self, bridge):
        bridge._svc.analysis.analyze_file.side_effect = RuntimeError("fail")
        result = bridge.previewAnalysis("/test.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "PREVIEW_FAILED"

    def test_preview_normalization_no_service(self):
        b = AudioLabBridge()
        result = b.previewNormalization("/test.flac")
        assert result.get("ok") is False
        assert result.get("error_code") == "SERVICE_UNAVAILABLE"
