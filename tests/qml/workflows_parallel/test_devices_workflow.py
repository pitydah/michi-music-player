from __future__ import annotations
"""Workflow test: discover  select  inspect  profile  plan  transfer  progress  cancel."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
    SyncDirection,
    TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge

pytestmark = pytest.mark.isolation


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    (music / "track.flac").write_bytes(b"fLaC" + b"\x00" * 5000)
    (music / "track.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 3000)
    (music / "track.ogg").write_bytes(b"OggS" + b"\x00" * 2000)
    (music / "track.wav").write_bytes(b"RIFF" + b"\x00" * 4000)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 10000)
    return tmp_path


@pytest.fixture
def svc():
    return DeviceSyncService()


@pytest.fixture
def mock_sync_mgr():
    mgr = MagicMock()
    mgr.start.return_value = True
    mgr.stop.return_value = True
    mgr.get_all_peers.return_value = [
        {"alias": "HiBy R6", "device": "dedicated", "ip": "192.168.1.50", "port": 53318},
        {"alias": "Android Phone", "device": "android", "ip": "192.168.1.51", "port": 53318},
    ]
    mgr.get_paired_devices.return_value = [
        {"alias": "My Phone", "device": "android"},
    ]
    mgr.is_active = True
    return mgr


@pytest.fixture
def bridge(svc, mock_sync_mgr):
    return DevicesBridge(
        sync_manager=mock_sync_mgr,
        device_sync_service=svc,
    )


class TestDevicesWorkflow:
    """Complete workflow: discover  select  inspect  profile  plan  transfer  progress  cancel."""

    def test_wf_discover(self, bridge):
        bridge.refresh()
        assert bridge.serverActive is True
        assert len(bridge.peers) >= 2
        assert len(bridge.pairedDevices) >= 1

    def test_wf_select(self, bridge):
        bridge.refresh()
        peer = bridge.peers[0]
        assert peer["alias"] == "HiBy R6"
        assert peer["device"] == "dedicated"

    def test_wf_inspect_storage(self, bridge, svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="wf_hiby",
            mount_point=str(temp_music),
        )
        svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.deviceDetailStorage(str(temp_music))
        assert result["ok"] is True
        info = bridge.storageInfo[0]
        assert info["total_bytes"] > 0
        assert info["total_gb"] > 0

    def test_wf_inspect_compatibility(self, bridge, svc, temp_music):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="wf_comp",
            mount_point=str(temp_music),
        )
        svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
        result = bridge.deviceDetailCompatibility(str(temp_music))
        assert result["ok"] is True
        compat = bridge.compatibilityInfo[0]
        assert compat["supports_pairing"] is True
        assert "flac" in str(compat["supported_formats"]).lower()

    def test_wf_profile(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="wf_profile",
            mount_point="/media/hiby",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is True
        assert caps.supports_playlists is True
        assert caps.supports_authorization is False

    def test_wf_plan_transfer(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "planned.flac")
        job = svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.total_bytes > 0
        assert job.status == TransferStatus.QUEUED

    def test_wf_transfer(self, bridge, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "transferred.flac")
        result = bridge.startTransfer(src, dst)
        assert result["ok"] is True
        assert Path(dst).exists()
        assert Path(dst).stat().st_size > 0
        assert len(bridge.transferJobs) >= 1

    def test_wf_progress(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "sub" / "deep.flac")
        dst = str(temp_music / "progress_out.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        assert job.status == TransferStatus.COMPLETED, f"Job failed: {job.error}"
        assert job.transferred_bytes == job.total_bytes

    def test_wf_cancel(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancelled.flac")
        job = svc.create_transfer_job(src, dst)
        result = bridge.cancelTransfer(job.job_id)
        assert result["ok"] is True
        assert svc.get_job(job.job_id).status == TransferStatus.CANCELLED

    def test_wf_post_cancel_history(self, bridge, svc, temp_music):
        src = str(temp_music / "Music" / "track.mp3")
        dst = str(temp_music / "post_cancel.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        history = svc.get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"
        bridge.clearTransferHistory()
        assert bridge.transferHistory == []

    def test_wf_full_workflow(self, bridge, svc, temp_music):
        """Full end-to-end: discover  select  inspect  profile  plan  transfer  progress  cancel."""
        mgr = bridge._sync_mgr

        mgr.get_all_peers.return_value = [
            {"alias": "DAP", "device": "dedicated", "ip": "192.168.1.10", "port": 53318},
        ]

        bridge.refresh()
        assert len(bridge.peers) == 1

        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="e2e",
            mount_point=str(temp_music),
        )
        svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity

        storage_result = bridge.deviceDetailStorage(str(temp_music))
        assert storage_result["ok"] is True

        compat_result = bridge.deviceDetailCompatibility(str(temp_music))
        assert compat_result["ok"] is True
        compat = bridge.compatibilityInfo[0]
        assert compat["supports_pairing"] is True

        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "e2e_out.flac")
        job = svc.create_transfer_job(src, dst)
        assert job.total_bytes > 0

        exec_result = svc.execute_job(job.job_id)
        assert exec_result["ok"] is True
        assert Path(dst).exists()

        cancel_result = bridge.cancelTransfer("nonexistent")
        assert cancel_result["ok"] is False

        history = svc.get_history()
        assert len(history) >= 1
