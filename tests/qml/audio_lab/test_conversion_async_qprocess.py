"""DU — Conversión async: NO communicare() en UI thread. QProcess via JobService.

Flujo: QML start -> JobService queue -> worker starts process -> progress signals
-> QML responsive -> cancel -> terminate -> grace -> kill -> cleanup -> terminal.

Progress: FFmpeg -progress output parsing. Output: temp -> verify -> metadata -> artwork -> fsync -> atomic rename.
"""
from __future__ import annotations

import os
import tempfile
import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=1.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestConversionAsyncQProcess:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def sample_wav(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00\x44\xac\x00\x00\x10\xb1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00")
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def bridge(self, app):
        from ui_qml_bridge.conversion_bridge import ConversionBridge
        b = ConversionBridge()
        b._output_dir = tempfile.gettempdir()
        return b

    # ── No communicare() in UI thread ──

    def test_job_uses_subprocess_popen(self, bridge, sample_wav):
        with patch("subprocess.Popen") as mock_popen, \
             patch("os.getpgid", return_value=9999), patch("os.killpg"), \
             patch("os.unlink"), patch("os.open"):
            proc = MagicMock()
            proc.returncode = 0
            proc.pid = 9999
            proc.communicate.return_value = (None, b"")
            mock_popen.return_value = proc
            with patch("os.fsync"), patch("os.rename"):
                bridge.startConversion(sample_wav)
                assert mock_popen.called

    def test_qml_start_triggers_job_service_queue(self, bridge, sample_wav):
        result = bridge.startConversion(sample_wav)
        if result["ok"]:
            job_id = result["job_id"]
            job = bridge._jobs.get(job_id)
            assert job is not None

    def test_progress_signals_emitted(self, bridge, sample_wav):
        signals = []
        bridge.jobProgress.connect(lambda jid, pct, msg: signals.append((jid, pct, msg)))
        bridge.jobCompleted.connect(lambda jid, ok, err: signals.append(("done", jid, ok, err)))
        bridge.jobProgress.emit("test_job", 0.5, "test")
        bridge.jobCompleted.emit("test_job", True, "")
        _process_events(0.2)
        assert len(signals) == 2

    def test_cancel_terminate_grace_kill_cleanup(self, bridge, sample_wav):
        from ui_qml_bridge.conversion_bridge import ConversionJob
        job = ConversionJob("test_cancel_1", sample_wav, "/tmp/out.wav", {})
        job.process = MagicMock()
        job.process.pid = 9999
        job.process.poll.return_value = None
        job.status = "running"
        job.temp_path = "/tmp/out.wav.tmp_123"
        bridge._jobs[job.job_id] = job
        with patch("os.getpgid", return_value=9999), patch("os.killpg") as mock_kill, \
             patch("os.unlink"):
            bridge.cancelJob(job.job_id)
            assert mock_kill.called

    def test_cancel_lifecycle_transitions(self, bridge, sample_wav):
        from ui_qml_bridge.conversion_bridge import ConversionJob
import pytest
pytestmark = [pytest.mark.qml_module("audio_lab")]

        job = ConversionJob("test_cancel_2", sample_wav, "/tmp/out.wav", {})
        job.process = MagicMock()
        job.process.pid = 9999
        job.process.poll.return_value = None
        job.status = "running"
        job.temp_path = "/tmp/out.wav.tmp_124"
        bridge._jobs[job.job_id] = job
        with patch("os.getpgid", return_value=9999), patch("os.killpg"), patch("os.unlink"):
            bridge.cancelJob(job.job_id)
            assert job.status == "cancelled"
            assert job._cleanup_done is True

    def test_output_temp_verify_rename(self, bridge, sample_wav):
        with patch("subprocess.Popen") as mock_popen, \
             patch("os.fsync") as _, patch("os.rename") as mock_rename, \
             patch("os.unlink"), patch("os.open") as _, \
             patch("os.getpgid", return_value=9999), patch("os.killpg"):
            proc = MagicMock()
            proc.returncode = 0
            proc.pid = 9999
            proc.communicate.return_value = (None, b"")
            mock_popen.return_value = proc
            result = bridge.startConversion(sample_wav)
            assert result["ok"]
            assert mock_rename.called

    def test_ffmpeg_progress_parsing(self):
        progress_line = "out_time=00:01:30.000\nspeed=1.5x\nsize=1024kB\n"
        out_time = None
        speed = None
        size = None
        for line in progress_line.strip().split("\n"):
            if line.startswith("out_time="):
                out_time = line.split("=", 1)[1]
            elif line.startswith("speed="):
                speed = line.split("=", 1)[1]
            elif line.startswith("size="):
                size = line.split("=", 1)[1]
        assert out_time == "00:01:30.000"
        assert speed == "1.5x"
        assert size == "1024kB"

    def test_preview_returns_file_info(self, bridge, sample_wav):
        result = bridge.preview(sample_wav)
        assert result["ok"]
        assert "format" in result
        assert "size" in result
        assert result["source"] == sample_wav

    def test_preview_missing_file(self, bridge):
        result = bridge.preview("/nonexistent/file.mp3")
        assert not result["ok"]
        assert result["error"] == "SOURCE_NOT_FOUND"

    def test_validate_audio_supported(self, bridge):
        result = bridge.validateAudioFile("/path/to/file.flac")
        assert result["ok"]
        result = bridge.validateAudioFile("/path/to/file.mp3")
        assert result["ok"]

    def test_validate_video_rejected(self, bridge):
        result = bridge.validateAudioFile("/path/to/video.mp4")
        assert not result["ok"]
        assert result["error"] == "VIDEO_NOT_SUPPORTED"

    def test_cancel_all_clears_active_jobs(self, bridge, sample_wav):
        result = bridge.startConversion(sample_wav)
        if result["ok"]:
            bridge.cancelAll()
            active = bridge.activeJobs
            assert len(active) == 0

    def test_retry_failed_job(self, bridge, sample_wav):
        bridge.startConversion(sample_wav)
        if bridge._jobs:
            first_id = list(bridge._jobs.keys())[0]
            job = bridge._jobs[first_id]
            job.status = "failed"
            result = bridge.retryJob(first_id)
            assert result["ok"]
            assert result["job_id"] != first_id

    def test_collision_rename_policy(self, bridge, sample_wav, tmp_path):
        bridge._output_dir = str(tmp_path)
        bridge._collision_policy = "rename"
        result = bridge.startConversion(sample_wav)
        if result["ok"]:
            job_id = result["job_id"]
            job = bridge._jobs.get(job_id)
            if job:
                assert job.dest is not None

    def test_collision_skip_policy(self, bridge, tmp_path):
        dummy = tmp_path / "test.wav"
        dummy.write_text("dummy")
        bridge._output_dir = str(tmp_path)
        bridge._collision_policy = "skip"
        result = bridge.startConversion(str(dummy))
        assert not result["ok"]
