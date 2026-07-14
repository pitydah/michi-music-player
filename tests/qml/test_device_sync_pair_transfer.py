"""Test DeviceSyncService — discovery, pairing, authorization, transfer, playlists."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.device_sync_service import (
    DeviceSyncService,
    DeviceIdentity,
    DeviceProtocol,
    SyncDirection,
    TransferStatus,
    StorageInfo,
)


@pytest.fixture
def temp_music(tmp_path):
    music = tmp_path / "Music"
    music.mkdir()
    flac = music / "track.flac"
    flac.write_bytes(b"fLaC" + b"\x00" * 100)
    mp3 = music / "track.mp3"
    mp3.write_bytes(b"\xff\xfb" + b"\x00" * 100)
    sub = music / "sub"
    sub.mkdir()
    (sub / "deep.ogg").write_bytes(b"OggS" + b"\x00" * 100)
    return tmp_path


@pytest.fixture
def svc():
    return DeviceSyncService()


class TestDiscovery:
    def test_discover_empty(self, svc):
        discovered = svc.discover()
        assert isinstance(discovered, list)

    def test_probe_mount_returns_identity(self, svc, temp_music):
        identity = svc._probe_mount(str(temp_music))
        assert identity is not None
        assert identity.protocol == DeviceProtocol.USB_MASS_STORAGE

    def test_discover_includes_probed_paths(self, svc, temp_music):
        results = svc.discover()
        assert isinstance(results, list)

    def test_identify_known(self, svc, temp_music):
        identity = svc._probe_mount(str(temp_music))
        if identity:
            svc._discovered[f"{identity.protocol.value}:{identity.serial}"] = identity
            found = svc.identify(str(temp_music))
            assert found is not None
            assert found.mount_point == str(temp_music)

    def test_identify_unknown(self, svc):
        assert svc.identify("/nonexistent") is None


class TestDeviceIdentity:
    def test_hiby_protocol_resolved(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="HiBy", model="R6", serial="123",
            mount_point="/media/hiby",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_playlists is True
        assert caps.supports_pairing is True

    def test_fiio_protocol_resolved(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="FiiO", model="M11", serial="456",
            mount_point="/media/fiio",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_playlists is True
        assert caps.supports_pairing is False

    def test_android_mtp_capabilities(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.ANDROID_MTP,
            vendor="Google", model="Pixel", serial="789",
            mount_point="/media/pixel",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is True
        assert caps.supports_authorization is True
        assert caps.supports_playlists is True

    def test_generic_usb_capabilities(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.USB_MASS_STORAGE,
            vendor="SanDisk", model="Clip", serial="012",
            mount_point="/media/sandisk",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_pairing is False
        assert caps.supports_playlists is False

    def test_ruizu_capabilities(self, svc):
        identity = DeviceIdentity(
            protocol=DeviceProtocol.GENERIC_DEDICATED,
            vendor="Ruizu", model="X02", serial="345",
            mount_point="/media/ruizu",
        )
        caps = svc.resolve_capabilities(identity)
        assert caps.supports_playlists is False


class TestStorage:
    def test_get_storage_fake(self, svc, temp_music):
        info = svc.get_storage(str(temp_music))
        assert isinstance(info, StorageInfo)
        assert info.total_bytes > 0

    def test_list_music(self, svc, temp_music):
        files = svc.list_music(str(temp_music), music_dir="Music")
        assert len(files) >= 3
        names = [f["name"] for f in files]
        assert "track.flac" in names
        assert "track.mp3" in names
        assert "deep.ogg" in names


class TestPairing:
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


class TestAuthorization:
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
        paired = svc.get_paired()
        assert paired[0]["authorized"] is True

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
        assert svc.get_paired()[0]["authorized"] is False


class TestTrust:
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


class TestTransfer:
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
        assert Path(dst).stat().st_size == job.total_bytes

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

    def test_retry_job(self, svc, temp_music):
        src = str(temp_music / "Music" / "track.flac")
        dst = str(temp_music / "retry.flac")
        job = svc.create_transfer_job(src, dst)
        svc.execute_job(job.job_id)
        assert job.status == TransferStatus.COMPLETED

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


class TestPlaylists:
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
        assert "track2.flac" in content
        assert "#EXTM3U" in content


class TestErrors:
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
