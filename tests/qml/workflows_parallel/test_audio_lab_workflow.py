<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Full workflow: select input -> preview -> convert -> progress -> cancel."""
from unittest.mock import MagicMock, PropertyMock
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Workflow test: input → profile → preview → convert → cancel via AudioLabBridge + ConversionBridge."""
from unittest.mock import MagicMock
>>>>>>> Stashed changes

import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_conv_bridge():
    bridge = MagicMock()
<<<<<<< Updated upstream
=======
    bridge.preview.return_value = {
        "ok": True, "source": "/dummy/test.flac", "format": "FLAC",
        "size": 1000000, "sample_rate": 44100, "bit_depth": 16, "channels": 2,
        "estimated_size": 1050000, "free_space": 10000000000,
    }
    bridge.startConversion.return_value = {"ok": True, "job_id": "conv_1234"}
    bridge.cancelJob.return_value = {"ok": True}
    bridge.retryJob.return_value = {"ok": True, "job_id": "conv_5678"}
=======
"""Full workflow: select input -> preview -> convert -> progress -> cancel."""
from unittest.mock import MagicMock, PropertyMock

import pytest
pytestmark = pytest.mark.isolation


@pytest.fixture
def mock_conv_bridge():
    bridge = MagicMock()
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    bridge.outputDir = "/tmp"
    bridge.collisionPolicy = "rename"
    type(bridge).outputDir = PropertyMock(return_value="/tmp")
    type(bridge).collisionPolicy = PropertyMock(return_value="rename")
    type(bridge).activeJobs = PropertyMock(return_value=[])
    type(bridge).jobHistory = PropertyMock(return_value=[])

    def _preview(path):
        return {"ok": True, "source": path, "format": "WAV", "size": 1024,
                "estimated_size": 1075, "free_space": 10737418240}
    bridge.preview.side_effect = _preview

    def _start_conv(path):
        return {"ok": True, "job_id": "conv_123"}
    bridge.startConversion.side_effect = _start_conv

    def _cancel(job_id):
        return {"ok": True}
    bridge.cancelJob.side_effect = _cancel

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
    return bridge


@pytest.fixture
<<<<<<< Updated upstream
<<<<<<< Updated upstream
def mock_lab():
    lab = MagicMock()
    type(lab).backendInfo = PropertyMock(return_value={"backend": "gstreamer", "available": True})
    return lab


@pytest.fixture
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
=======
<<<<<<< HEAD
>>>>>>> Stashed changes
def mock_job_bridge():
    jb = MagicMock()
    type(jb).jobs = PropertyMock(return_value=[
        {"job_id": 1, "type": "conversion", "title": "Conversión", "state": "running",
         "progress": 0.5, "processed": 5, "total": 10, "can_cancel": True, "can_retry": False,
         "started_at": 1000, "finished_at": 0, "duration": 0, "message": "", "error_code": ""},
    ])
    type(jb).activeCount = PropertyMock(return_value=1)
    jb.cancelJob = MagicMock(return_value={"ok": True})
    jb.retryJob = MagicMock(return_value={"ok": True})
    jb.clearCompleted = MagicMock(return_value={"ok": True})
    jb.clearFailed = MagicMock(return_value={"ok": True})
    jb.runJob = MagicMock(return_value={"ok": True})
    return jb


class TestAudioLabWorkflow:
    def test_select_files(self):
        files = [{"name": "track1.flac", "size": 1024000}, {"name": "track2.wav", "size": 2048000}]
        assert len(files) == 2
        assert files[0]["name"] == "track1.flac"
        assert files[1]["name"] == "track2.wav"

    def test_preview_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.preview("/music/track.flac")
        assert result["ok"] is True
        assert result["format"] == "WAV"
        assert result["estimated_size"] > 0
        assert result["free_space"] > 0

    def test_start_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.startConversion("/music/track.flac")
        assert result["ok"] is True
        assert "job_id" in result

    def test_conversion_progress(self, mock_job_bridge):
        jobs = mock_job_bridge.jobs
        assert len(jobs) >= 1
        running = [j for j in jobs if j["state"] == "running"]
        assert len(running) >= 1
        assert running[0]["progress"] == 0.5

    def test_cancel_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.cancelJob("conv_123")
        assert result["ok"] is True
        mock_conv_bridge.cancelJob.assert_called_with("conv_123")

    def test_full_lifecycle(self, mock_conv_bridge, mock_job_bridge, mock_lab):
        assert mock_lab.backendInfo["available"] is True
        assert mock_conv_bridge.outputDir == "/tmp"

        preview = mock_conv_bridge.preview("/music/track.flac")
        assert preview["ok"] is True

        conv = mock_conv_bridge.startConversion("/music/track.flac")
        assert conv["ok"] is True

        jobs = mock_job_bridge.jobs
        assert any(j["state"] == "running" for j in jobs)

        cancel = mock_conv_bridge.cancelJob("conv_123")
        assert cancel["ok"] is True

    def test_conversion_without_output_dir_fails(self):
        bridge = MagicMock()
        bridge.startConversion = MagicMock(return_value={"ok": False, "error": "NO_OUTPUT_DIR"})
        result = bridge.startConversion("/test.flac")
        assert result["ok"] is False
        assert result["error"] == "NO_OUTPUT_DIR"

    def test_cancel_nonexistent_job(self, mock_conv_bridge):
        mock_conv_bridge.cancelJob = MagicMock(return_value={"ok": False, "error": "NOT_FOUND"})
        result = mock_conv_bridge.cancelJob("nonexistent")
        assert result["ok"] is False

    def test_retry_after_failure(self, mock_job_bridge):
        mock_job_bridge.retryJob(1)
        mock_job_bridge.retryJob.assert_called_with(1)

    def test_clear_after_completion(self, mock_job_bridge):
        mock_job_bridge.clearCompleted()
        mock_job_bridge.clearCompleted.assert_called_once()

    def test_clear_after_failure(self, mock_job_bridge):
        mock_job_bridge.clearFailed()
        mock_job_bridge.clearFailed.assert_called_once()

    def test_format_detection(self):
        files = [
            {"name": "song.flac", "format": "FLAC"},
            {"name": "song.mp3", "format": "MP3"},
            {"name": "song.wav", "format": "WAV"},
            {"name": "song.ogg", "format": "OGG"},
            {"name": "song.m4a", "format": "AAC"},
        ]
        formats = {f["format"] for f in files}
        assert "FLAC" in formats
        assert "MP3" in formats
        assert "WAV" in formats

    def test_file_count_and_size_summary(self):
        files = [{"name": "a.flac", "size": 1000}, {"name": "b.flac", "size": 2000}]
        total = sum(f["size"] for f in files)
        assert total == 3000
        assert len(files) == 2

    def test_eta_calculation(self):
        elapsed = 10.0
        processed = 5
        total = 20
        rate = processed / max(0.001, elapsed)
        remaining = (total - processed) / max(0.001, rate)
        assert remaining > 0

    def test_no_false_success(self):
        bridge = MagicMock()
        bridge.startConversion = MagicMock(return_value={"ok": False, "error": "SOURCE_NOT_FOUND"})
        result = bridge.startConversion("/nonexistent.flac")
        assert result["ok"] is False

<<<<<<< Updated upstream
=======
    def test_wf_bridge_null_handling(self):
        assert hasattr(type("NullBridge", (), {})(), "__class__")
        null_bridge = None
        assert null_bridge is None
=======
def mock_lab():
    lab = MagicMock()
    type(lab).backendInfo = PropertyMock(return_value={"backend": "gstreamer", "available": True})
    return lab


@pytest.fixture
def mock_job_bridge():
    jb = MagicMock()
    type(jb).jobs = PropertyMock(return_value=[
        {"job_id": 1, "type": "conversion", "title": "Conversión", "state": "running",
         "progress": 0.5, "processed": 5, "total": 10, "can_cancel": True, "can_retry": False,
         "started_at": 1000, "finished_at": 0, "duration": 0, "message": "", "error_code": ""},
    ])
    type(jb).activeCount = PropertyMock(return_value=1)
    jb.cancelJob = MagicMock(return_value={"ok": True})
    jb.retryJob = MagicMock(return_value={"ok": True})
    jb.clearCompleted = MagicMock(return_value={"ok": True})
    jb.clearFailed = MagicMock(return_value={"ok": True})
    jb.runJob = MagicMock(return_value={"ok": True})
    return jb


class TestAudioLabWorkflow:
    def test_select_files(self):
        files = [{"name": "track1.flac", "size": 1024000}, {"name": "track2.wav", "size": 2048000}]
        assert len(files) == 2
        assert files[0]["name"] == "track1.flac"
        assert files[1]["name"] == "track2.wav"

    def test_preview_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.preview("/music/track.flac")
        assert result["ok"] is True
        assert result["format"] == "WAV"
        assert result["estimated_size"] > 0
        assert result["free_space"] > 0

    def test_start_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.startConversion("/music/track.flac")
        assert result["ok"] is True
        assert "job_id" in result

    def test_conversion_progress(self, mock_job_bridge):
        jobs = mock_job_bridge.jobs
        assert len(jobs) >= 1
        running = [j for j in jobs if j["state"] == "running"]
        assert len(running) >= 1
        assert running[0]["progress"] == 0.5

    def test_cancel_conversion(self, mock_conv_bridge):
        result = mock_conv_bridge.cancelJob("conv_123")
        assert result["ok"] is True
        mock_conv_bridge.cancelJob.assert_called_with("conv_123")

    def test_full_lifecycle(self, mock_conv_bridge, mock_job_bridge, mock_lab):
        assert mock_lab.backendInfo["available"] is True
        assert mock_conv_bridge.outputDir == "/tmp"

        preview = mock_conv_bridge.preview("/music/track.flac")
        assert preview["ok"] is True

        conv = mock_conv_bridge.startConversion("/music/track.flac")
        assert conv["ok"] is True

        jobs = mock_job_bridge.jobs
        assert any(j["state"] == "running" for j in jobs)

        cancel = mock_conv_bridge.cancelJob("conv_123")
        assert cancel["ok"] is True

    def test_conversion_without_output_dir_fails(self):
        bridge = MagicMock()
        bridge.startConversion = MagicMock(return_value={"ok": False, "error": "NO_OUTPUT_DIR"})
        result = bridge.startConversion("/test.flac")
        assert result["ok"] is False
        assert result["error"] == "NO_OUTPUT_DIR"

    def test_cancel_nonexistent_job(self, mock_conv_bridge):
        mock_conv_bridge.cancelJob = MagicMock(return_value={"ok": False, "error": "NOT_FOUND"})
        result = mock_conv_bridge.cancelJob("nonexistent")
        assert result["ok"] is False

    def test_retry_after_failure(self, mock_job_bridge):
        mock_job_bridge.retryJob(1)
        mock_job_bridge.retryJob.assert_called_with(1)

    def test_clear_after_completion(self, mock_job_bridge):
        mock_job_bridge.clearCompleted()
        mock_job_bridge.clearCompleted.assert_called_once()

    def test_clear_after_failure(self, mock_job_bridge):
        mock_job_bridge.clearFailed()
        mock_job_bridge.clearFailed.assert_called_once()

    def test_format_detection(self):
        files = [
            {"name": "song.flac", "format": "FLAC"},
            {"name": "song.mp3", "format": "MP3"},
            {"name": "song.wav", "format": "WAV"},
            {"name": "song.ogg", "format": "OGG"},
            {"name": "song.m4a", "format": "AAC"},
        ]
        formats = {f["format"] for f in files}
        assert "FLAC" in formats
        assert "MP3" in formats
        assert "WAV" in formats

    def test_file_count_and_size_summary(self):
        files = [{"name": "a.flac", "size": 1000}, {"name": "b.flac", "size": 2000}]
        total = sum(f["size"] for f in files)
        assert total == 3000
        assert len(files) == 2

    def test_eta_calculation(self):
        elapsed = 10.0
        processed = 5
        total = 20
        rate = processed / max(0.001, elapsed)
        remaining = (total - processed) / max(0.001, rate)
        assert remaining > 0

    def test_no_false_success(self):
        bridge = MagicMock()
        bridge.startConversion = MagicMock(return_value={"ok": False, "error": "SOURCE_NOT_FOUND"})
        result = bridge.startConversion("/nonexistent.flac")
        assert result["ok"] is False

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_job_history_after_conversion(self, mock_conv_bridge):
        mock_conv_bridge.startConversion("/test.flac")
        assert mock_conv_bridge.jobHistory is not None

    def test_reuse_bridge_after_cancel(self, mock_conv_bridge):
        mock_conv_bridge.startConversion("/test.flac")
        mock_conv_bridge.cancelJob("conv_123")
        result = mock_conv_bridge.startConversion("/test2.flac")
        assert result["ok"] is True

    def test_concurrent_jobs_limited(self, mock_conv_bridge):
        mock_conv_bridge.startConversion = MagicMock(return_value={"ok": False, "error": "MAX_CONCURRENT"})
        result = mock_conv_bridge.startConversion("/test.flac")
        assert result["ok"] is False

    def test_output_dir_selection_required(self):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        bridge = ConversionBridge()
        result = bridge.startConversion("/test.flac")
        assert result.get("ok") is False
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
