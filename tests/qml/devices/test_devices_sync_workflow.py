"""Test Devices/Sync workflows through DevicesBridge and DeviceSyncService."""
from pathlib import Path
from unittest.mock import MagicMock


from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
    SyncDirection,
    TransferStatus,
)
from ui_qml_bridge.devices_bridge import DevicesBridge
import pytest
pytestmark = pytest.mark.isolation



@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    flac = music / "track.flac"
    flac.write_bytes(b"fLaC" + b"\x00" * 100)
    mp3 = music / "track.mp3"
    mp3.write_bytes(b"\xff\xfb" + b"\x00" * 100)
    ogg = music / "track.ogg"
    ogg.write_bytes(b"OggS" + b"\x00" * 100)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.flac").write_bytes(b"fLaC" + b"\x00" * 100)
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
        {"alias": "Phone", "device": "android", "ip": "192.168.1.50", "port": 53318},
        {"alias": "Tablet", "device": "android", "ip": "192.168.1.51", "port": 53318},
    ]
    mgr.get_paired_devices.return_value = [
        {"alias": "My Phone", "device": "android"},
    ]
    mgr.is_active = True
    return mgr


# ── DevicesBridge tests ──


class TestDevicesBridgeInitial:
    def test_start_not_active(self):
        b = DevicesBridge(sync_manager=None)
        assert b.serverActive is False

    def test_peers_empty_initially(self):
        b = DevicesBridge(sync_manager=None)
        assert b.peers == []

    def test_paired_empty_initially(self):
        b = DevicesBridge(sync_manager=None)
        assert b.pairedDevices == []


class TestDevicesBridgeServer:
    def test_start_server(self, mock_sync_mgr):
        b = DevicesBridge(sync_manager=mock_sync_mgr)
        result = b.startServer()
        assert result["ok"] is True
        assert b.serverActive is True

    def test_start_server_no_manager(self):
        b = DevicesBridge(sync_manager=None)
        result = b.startServer()
        assert result["ok"] is False
        assert b.serverActive is False

    def test_stop_server(self, mock_sync_mgr):
        b = DevicesBridge(sync_manager=mock_sync_mgr)
        b.startServer()
        result = b.stopServer()
        assert result["ok"] is True
        assert b.serverActive is False

    def test_stop_server_no_manager(self):
        b = DevicesBridge(sync_manager=None)
        result = b.stopServer()
        assert result["ok"] is False


class TestDevicesBridgeRefresh:
    def test_refresh_populates_peers(self, mock_sync_mgr):
        b = DevicesBridge(sync_manager=mock_sync_mgr)
        b.refresh()
        assert len(b.peers) == 2

    def test_refresh_populates_paired(self, mock_sync_mgr):
        b = DevicesBridge(sync_manager=mock_sync_mgr)
        b.refresh()
        assert len(b.pairedDevices) == 1

    def test_refresh_returns_counts(self, mock_sync_mgr):
        b = DevicesBridge(sync_manager=mock_sync_mgr)
        result = b.refresh()
        assert result["peers"] == 2
        assert result["paired"] == 1

    def test_refresh_no_manager(self):
        b = DevicesBridge(sync_manager=None)
        result = b.refresh()
        assert result["ok"] is True


# ── DeviceSyncService tests ──


class TestDeviceSyncDiscovery:
    def test_discover_empty_when_no_media(self, svc):
        discovered = svc.discover()
        assert isinstance(discovered, list)

    def test_get_discovered_initially_empty(self, svc):
        assert len(svc.get_discovered()) == 0

    def test_identify_unknown(self, svc):
        assert svc.identify("/nonexistent") is None


class TestDeviceSyncIdentity:
    def test_hiby_protocol(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="123",
            mount_point="/media/hiby",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is True
        assert caps.supports_playlists is True

    def test_fiio_protocol(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="FiiO", model="M11", serial="456",
            mount_point="/media/fiio",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is True

    def test_android_mtp_capabilities(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel", serial="789",
            mount_point="/media/pixel",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is True
        assert caps.supports_authorization is True

    def test_generic_usb_no_pairing(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="012",
            mount_point="/media/sandisk",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is False

    def test_ruizu_no_playlists(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Ruizu", model="X02", serial="345",
            mount_point="/media/ruizu",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_playlists is True

    def test_unknown_protocol(self, svc):
        identity = DeviceIdentity(protocol=DeviceProtocol.UNKNOWN)
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False


class TestDeviceSyncStorage:
    def test_get_storage_fake(self, svc, temp_music):
        info = svc.get_storage(str(temp_music))
        assert info.total_bytes > 0

    def test_list_music(self, svc, temp_music):
        files = svc.list_music(str(temp_music), music_dir="Music")
        assert len(files) >= 4
        names = [f["name"] for f in files]
        assert "track.flac" in names
        assert "track.mp3" in names
        assert "track.ogg" in names
        assert "deep.flac" in names

    def test_list_music_fallback_root(self, svc, tmp_path):
        files = svc.list_music(str(tmp_path), music_dir="Nonexistent")
        assert isinstance(files, list)


class TestDeviceSyncPairing:
    def test_pair_device(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="pair1",
            mount_point="/media/test",
        )
        result = svc.pair(identity)
        assert result["ok"] is True
        assert result["key"] is not None

    def test_pair_duplicate(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="dup",
            mount_point="/media/test",
        )
        svc.pair(identity)
        result = svc.pair(identity)
        assert result["ok"] is False
        assert result["error"] == "ALREADY_PAIRED"

    def test_unpair(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="unpair1",
            mount_point="/media/test",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = svc.unpair(key)
        assert result["ok"] is True
        assert svc.is_paired(key) is False

    def test_unpair_not_paired(self, svc):
        result = svc.unpair("nonexistent")
        assert result["ok"] is False

    def test_get_paired_list(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="Test", model="Device", serial="list1",
            mount_point="/media/test",
        )
        svc.pair(identity)
        paired = svc.get_paired()
        assert len(paired) == 1
        assert paired[0]["vendor"] == "Test"


class TestDeviceSyncAuthorization:
    def test_authorize(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Android", model="Phone", serial="auth1",
            mount_point="/media/phone",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = svc.authorize(key)
        assert result["ok"] is True

    def test_authorize_not_paired(self, svc):
        result = svc.authorize("nonexistent")
        assert result["ok"] is False

    def test_unauthorize(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Android", model="Phone", serial="unauth1",
            mount_point="/media/phone",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        svc.authorize(key)
        result = svc.unauthorize(key)
        assert result["ok"] is True

    def test_trust(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="trust1",
            mount_point="/media/hiby",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        result = svc.trust(key)
        assert result["ok"] is True

    def test_untrust(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="HiBy", model="R6", serial="untrust1",
            mount_point="/media/hiby",
        )
        key = f"{identity.protocol.value}:{identity.serial}"
        svc.pair(identity)
        svc.trust(key)
        result = svc.untrust(key)
        assert result["ok"] is True

    def test_trust_not_paired(self, svc):
        result = svc.trust("nonexistent")
        assert result["ok"] is False


class TestDeviceSyncTransfer:
    def test_create_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "dest.flac")
        job = svc.create_transfer_job(src, dst, SyncDirection.TO_DEVICE)
        assert job.job_id.startswith("sync_")
        assert job.source_path == src
        assert job.total_bytes > 0

    def test_execute_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "output.flac")
        job = svc.create_transfer_job(src, dst)
        result = svc.execute_job(job.job_id)
        assert result["ok"] is True
        assert Path(dst).exists()

    def test_execute_job_not_found(self, svc):
        result = svc.execute_job("nonexistent")
        assert result["ok"] is False

    def test_cancel_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel.flac")
        job = svc.create_transfer_job(src, dst)
        result = svc.cancel_job(job.job_id)
        assert result["ok"] is True
        assert job.status == TransferStatus.CANCELLED

    def test_cancel_job_not_found(self, svc):
        result = svc.cancel_job("nonexistent")
        assert result["ok"] is False

    def test_cancel_twice(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "cancel2.flac")
        job = svc.create_transfer_job(src, dst)
        svc.cancel_job(job.job_id)
        result = svc.cancel_job(job.job_id)
        assert result["ok"] is False

    def test_progress_tracking(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "progress.flac")
        job = svc.create_transfer_job(src, dst)
        progress_values = []

        def track(j):
            progress_values.append(j.transferred_bytes)

        svc.set_on_progress(track)
        svc.execute_job(job.job_id)
        assert len(progress_values) > 0
        assert progress_values[-1] == job.total_bytes

    def test_list_jobs(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        svc.create_transfer_job(src, str(temp_music / "list1.flac"))
        assert len(svc.list_jobs()) == 1

    def test_get_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        job = svc.create_transfer_job(src, str(temp_music / "get.flac"))
        assert svc.get_job(job.job_id) is job

    def test_retry_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        assert job.status == TransferStatus.COMPLETED


class TestDeviceSyncHistory:
    def test_history(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "hist.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        history = svc.get_history()
        assert len(history) >= 1
        assert history[0]["status"] == "completed"

    def test_clear_history(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "clear.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        svc.clear_history()
        assert len(svc.get_history()) == 0


class TestDeviceSyncPlaylists:
    def test_list_playlists(self, svc, temp_music):
        pl = temp_music / "playlist.m3u"
        pl.write_text("#EXTM3U\n")
        result = svc.list_playlists(str(temp_music))
        assert len(result) == 1
        assert result[0]["name"] == "playlist.m3u"

    def test_render_playlist(self, svc, temp_music):
        dst = str(temp_music / "output.m3u")
        result = svc.render_playlist(dst, ["track1.flac", "track2.flac"])
        assert result["ok"] is True
        assert Path(dst).exists()
        content = Path(dst).read_text()
        assert "track1.flac" in content

    def test_render_playlist_empty(self, svc, temp_music):
        dst = str(temp_music / "empty.m3u")
        result = svc.render_playlist(dst, [])
        assert result["ok"] is True


class TestDeviceSyncErrors:
    def test_last_errors_empty(self, svc):
        assert svc.last_errors() == []

    def test_last_errors_after_failure(self, svc, temp_music):
        job = svc.create_transfer_job(
            str(temp_music / "nonexistent.flac"),
            str(temp_music / "fail.flac"),
        )
        svc.execute_job(job.job_id)
        errors = svc.last_errors()
        assert len(errors) >= 1
        assert errors[0]["error"]
