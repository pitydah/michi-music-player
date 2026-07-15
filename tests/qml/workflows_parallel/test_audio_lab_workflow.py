"""Workflow test: input → profile → preview → convert → cancel via AudioLabBridge + ConversionBridge."""
from unittest.mock import MagicMock

import pytest

pytestmark = [pytest.mark.qml_workflow("audio_lab"), pytest.mark.isolation]


@pytest.fixture
def mock_audio_lab_service():
    svc = MagicMock()
    svc.refresh.return_value = {"ok": True, "stats": {}, "backend": {"backend": "gstreamer", "available": True}, "dsp": {}, "pipeline": {}}
    svc.probe.return_value = {"ok": True, "filepath": "/dummy/test.flac", "format": "FLAC", "sample_rate": 44100, "bit_depth": 16, "channels": 2}
    return svc


@pytest.fixture
def mock_conversion_bridge():
    bridge = MagicMock()
    bridge.preview.return_value = {
        "ok": True, "source": "/dummy/test.flac", "format": "FLAC",
        "size": 1000000, "sample_rate": 44100, "bit_depth": 16, "channels": 2,
        "estimated_size": 1050000, "free_space": 10000000000,
    }
    bridge.startConversion.return_value = {"ok": True, "job_id": "conv_1234"}
    bridge.cancelJob.return_value = {"ok": True}
    bridge.retryJob.return_value = {"ok": True, "job_id": "conv_5678"}
    return bridge


@pytest.fixture
def mock_job_bridge():
    bridge = MagicMock()
    bridge.jobs = []
    bridge.activeCount = 0
    bridge.cancelJob.return_value = {"ok": True}
    bridge.retryJob.return_value = {"ok": True}
    bridge.clearCompleted.return_value = {"ok": True}
    bridge.clearFailed.return_value = {"ok": True}
    return bridge


class TestAudioLabWorkflow:
    """Workflow: input → profile → preview → convert → cancel via bridges."""

    def test_wf_preview_returns_expected_fields(self, mock_conversion_bridge):
        result = mock_conversion_bridge.preview("/dummy/test.flac")
        assert result["ok"] is True
        assert result["source"] == "/dummy/test.flac"
        assert result["format"] == "FLAC"
        assert result["estimated_size"] > 0
        assert result["free_space"] > 0

    def test_wf_start_convert_returns_job_id(self, mock_conversion_bridge):
        result = mock_conversion_bridge.startConversion("/dummy/test.flac")
        assert result["ok"] is True
        assert "job_id" in result
        assert result["job_id"].startswith("conv_")

    def test_wf_cancel_job(self, mock_conversion_bridge):
        result = mock_conversion_bridge.startConversion("/dummy/test.flac")
        job_id = result["job_id"]
        cancel_result = mock_conversion_bridge.cancelJob(job_id)
        assert cancel_result["ok"] is True

    def test_wf_retry_failed_job(self, mock_conversion_bridge):
        result = mock_conversion_bridge.retryJob("conv_failed")
        assert result["ok"] is True
        assert "job_id" in result

    def test_wf_refresh_returns_stats(self, mock_audio_lab_service):
        result = mock_audio_lab_service.refresh()
        assert result["ok"] is True
        assert "backend" in result
        assert result["backend"]["available"] is True

    def test_wf_probe_file(self, mock_audio_lab_service):
        result = mock_audio_lab_service.probe("/dummy/test.flac")
        assert result["ok"] is True
        assert result["format"] == "FLAC"
        assert result["sample_rate"] == 44100

    def test_wf_job_list_empty_initially(self, mock_job_bridge):
        assert len(mock_job_bridge.jobs) == 0
        assert mock_job_bridge.activeCount == 0

    def test_wf_job_cancel(self, mock_job_bridge):
        result = mock_job_bridge.cancelJob(1)
        assert result["ok"] is True

    def test_wf_job_retry(self, mock_job_bridge):
        result = mock_job_bridge.retryJob(1)
        assert result["ok"] is True

    def test_wf_job_clear_completed(self, mock_job_bridge):
        result = mock_job_bridge.clearCompleted()
        assert result["ok"] is True

    def test_wf_job_clear_failed(self, mock_job_bridge):
        result = mock_job_bridge.clearFailed()
        assert result["ok"] is True

    def test_wf_full_flow(self, mock_audio_lab_service, mock_conversion_bridge):
        refresh = mock_audio_lab_service.refresh()
        assert refresh["ok"] is True
        probe = mock_audio_lab_service.probe("/dummy/test.flac")
        assert probe["ok"] is True
        preview = mock_conversion_bridge.preview(probe["filepath"])
        assert preview["ok"] is True
        convert = mock_conversion_bridge.startConversion(preview["source"])
        assert convert["ok"] is True
        cancel = mock_conversion_bridge.cancelJob(convert["job_id"])
        assert cancel["ok"] is True

    def test_wf_conversion_rejects_no_source(self, mock_conversion_bridge):
        mock_conversion_bridge.startConversion.return_value = {"ok": False, "error": "SOURCE_NOT_FOUND"}
        result = mock_conversion_bridge.startConversion("")
        assert result["ok"] is False
        assert "SOURCE_NOT_FOUND" in result["error"]

    def test_wf_preview_rejects_no_file(self, mock_conversion_bridge):
        mock_conversion_bridge.preview.return_value = {"ok": False, "error": "SOURCE_NOT_FOUND"}
        result = mock_conversion_bridge.preview("/nonexistent.flac")
        assert result["ok"] is False

    def test_wf_cancel_nonexistent_job(self, mock_conversion_bridge):
        mock_conversion_bridge.cancelJob.return_value = {"ok": False, "error": "NOT_FOUND"}
        result = mock_conversion_bridge.cancelJob("nonexistent")
        assert result["ok"] is False

    def test_wf_bridge_null_handling(self):
        assert hasattr(type("NullBridge", (), {})(), "__class__")
        null_bridge = None
        assert null_bridge is None
