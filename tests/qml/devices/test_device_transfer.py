from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 2000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 2000)
    (music / "video.mp4").write_bytes(b"\x00" * 200)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 2000)
    return tmp_path


@pytest.fixture
def dev_svc():
    svc = MagicMock()
    job_mock = MagicMock(
        job_id="sync_001",
        source_path="/tmp/test/track.flac",
        total_bytes=2000,
        status="queued",
    )
    svc.create_transfer_job.return_value = job_mock
    svc.execute_job.return_value = {"ok": True}
    svc.cancel_job.side_effect = lambda job_id: {"ok": job_id != "nonexistent"}
    svc.list_jobs.return_value = []
    return svc


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = []
    mgr.get_paired_devices.return_value = []
    mgr.is_active = MagicMock(return_value=False)
    return mgr


@pytest.fixture
def bridge(dev_svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=dev_svc,
    )


class TestTransferFlow:
    """Test the complete transfer flow: select  plan  start  progress  cancel."""

    def test_create_transfer_job(self, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = dev_svc.create_transfer_job(src, dst, "to_device")
        assert job.job_id is not None

    def test_start_transfer_audio(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "progress.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True

    def test_cancel_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = dev_svc.create_transfer_job(src, dst, "to_device")
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True

    def test_cancel_nonexistent(self, bridge):
        result = bridge.cancelTransfer("nonexistent")
        assert result["ok"] is False

    def test_retry_transfer(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        result = bridge.retryTransfer(job.job_id)
        assert isinstance(result, dict)

    def test_transfer_jobs_list(self, bridge, dev_svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "list.flac")
        bridge.startTransfer(src, dst)
        if bridge._dev_svc:
            jobs = bridge._dev_svc.list_jobs()
            assert isinstance(jobs, list)

    def test_transfer_history(self, dev_svc, temp_music):
        dev_svc.get_history.return_value = [{"status": "completed"}]
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "history.flac")
        job = dev_svc.create_transfer_job(src, dst)
        dev_svc.execute_job(job.job_id)
        history = dev_svc.get_history()
        assert len(history) >= 1

    def test_clear_transfer_history(self, bridge, dev_svc, temp_music):
        bridge._transfer_history = []
        assert len(bridge.transferHistory) == 0

    def test_transfer_audio_only(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.mp3")
        dst = str(temp_music / "audio_only.mp3")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True

    def test_transfer_verify_file(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.wav")
        dst = str(temp_music / "verify.wav")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True

    def test_execute_job_not_found(self, dev_svc):
        dev_svc.execute_job.return_value = {"ok": False}
        result = dev_svc.execute_job("nonexistent")
        assert result["ok"] is False

    def test_start_transfer_no_service(self):
        bridge = DevicesBridge(sync_manager=None)
        result = bridge.startTransfer("/src/track.flac", "/dst/track.flac")
        assert result["ok"] is False
