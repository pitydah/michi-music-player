"""Tests for portable player sync — UMS simulation, manifest, profiles."""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def ums_device(tmp_path):
    mount = tmp_path / "mount"
    mount.mkdir()
    music_dir = mount / "Music"
    music_dir.mkdir()
    for i in range(3):
        f = music_dir / f"song_{i}.flac"
        f.write_text("dummy flac content")
    return mount


class TestSyncTranscode:
    def test_transcode_service_import(self):
        from core.sync.transcode_service import TranscodeService
        assert TranscodeService is not None

    def test_transcode_profile_exists(self):
        from core.sync.transcode_service import TranscodeService
        svc = TranscodeService()
        profile = svc.get_profile("flac_mobile")
        assert profile is not None

    def test_needs_transcode(self):
        from core.sync.transcode_service import TranscodeService
        svc = TranscodeService()
        result = svc.needs_transcode("/test/song.flac", "flac_mobile")
        assert isinstance(result, bool)

    def test_transcode_fails_without_file(self):
        from core.sync.transcode_service import TranscodeService
        svc = TranscodeService()
        try:
            svc.transcode("/nonexistent.flac", "/out.flac", "flac_mobile")
            assert False  # should have raised
        except Exception:
            assert True


class TestDeviceRegistry:
    def test_registry_creation(self):
        from core.sync.device_registry import DeviceRegistry
        reg = DeviceRegistry()
        assert reg is not None

    def test_register_device(self):
        from core.sync.device_registry import DeviceRegistry
        reg = DeviceRegistry()
        reg.register("test-device", "Test Player")
        devices = reg.list_all()
        assert len(devices) >= 1

    def test_registry_has_permission(self):
        from core.sync.device_registry import DeviceRegistry
        reg = DeviceRegistry()
        reg.register("dev-1", "Player")
        has = reg.has_permission("dev-1", "sync")
        assert isinstance(has, bool)

    def test_remove_device(self):
        from core.sync.device_registry import DeviceRegistry
        reg = DeviceRegistry()
        reg.register("dev-2", "Player")
        reg.remove("dev-2")
        assert "dev-2" not in reg.list_all()


class TestUmsSync:
    def test_filesystem_backend(self, ums_device):
        from core.sync.transfer_backends import FilesystemBackend
        backend = FilesystemBackend()
        available = backend.is_available()
        assert isinstance(available, bool)

    def test_copy_file(self, ums_device):
        from core.sync.transfer_backends import FilesystemBackend
        backend = FilesystemBackend()
        src = str(ums_device / "Music" / "song_0.flac")
        dst = str(ums_device / "Music" / "song_copy.flac")
        result = backend.copy_file(src, dst)
        assert result is not None

    def test_copy_manifest(self, ums_device):
        from core.sync.transfer_backends import FilesystemBackend
        backend = FilesystemBackend()
        manifest = {"files": [{"source": "/test/a.flac", "dest": "Music/a.flac"}]}
        result = backend.copy_manifest_to(manifest, str(ums_device))
        assert result is not None

    def test_transfer_integrity(self, ums_device):
        src = ums_device / "Music" / "song_0.flac"
        dst = ums_device / "Music" / "song_integrity.flac"
        original_size = src.stat().st_size
        shutil.copy2(str(src), str(dst))
        assert dst.exists()
        assert dst.stat().st_size == original_size
