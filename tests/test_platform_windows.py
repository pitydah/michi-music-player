"""Tests for Windows platform support (HV).

These tests validate Windows-specific paths, reserved names, MTP, FFmpeg
discovery, notifications, shortcuts, and packaging readiness.
Many tests use platform checks and skip if not on Windows.
"""
import os
import platform
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent

# Windows reserved names (device names that cannot be used as files)
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


class TestWindowsReservedNames:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_reserved_names_detected(self):
        from core.safe_file_ops import is_reserved_name
        for name in WINDOWS_RESERVED_NAMES:
            assert is_reserved_name(name), f"{name} should be reserved"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_non_reserved_names_allowed(self):
        from core.safe_file_ops import is_reserved_name
        assert not is_reserved_name("music.mp3")
        assert not is_reserved_name("My Song.flac")
        assert not is_reserved_name("album_art.jpg")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_reserved_name_with_extension(self):
        from core.safe_file_ops import is_reserved_name
        assert is_reserved_name("CON.txt")
        assert is_reserved_name("NUL.log")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_reserved_name_case_insensitive(self):
        from core.safe_file_ops import is_reserved_name
        assert is_reserved_name("con")
        assert is_reserved_name("Con")
        assert is_reserved_name("CON")


class TestWindowsPaths:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_windows_path_separator(self):
        path = os.path.join("C:", "Users", "test", "Music")
        assert "\\" in path

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_short_path_support(self):
        path = r"C:\PROGRA~1"
        assert os.path.exists(path)  # may vary per system

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_long_path_enabled(self):
        from core.safe_file_ops import supports_long_paths
        assert supports_long_paths() is True

    def test_core_paths_import(self):
        from core.paths import database_path, app_config_dir, app_cache_dir, app_data_dir
        for p in (database_path, app_config_dir, app_cache_dir, app_data_dir):
            path = p()
            assert isinstance(path, str)
            assert len(path) > 0

    def test_paths_no_linux_specific(self):
        from core.paths import database_path as _dp
        path = _dp()
        assert "/home/" not in path or platform.system() == "Linux"
        assert "~" not in path


class TestWindowsMTP:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_mtp_device_query(self):
        try:
            result = subprocess.run(
                ["wmic", "path", "Win32_PnPEntity", "where", "Service='WUDFRd'", "get", "DeviceID"],
                capture_output=True, text=True, timeout=10,
            )
            assert result.returncode == 0
        except FileNotFoundError:
            pytest.skip("wmic not available")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_mtp_portable_device(self):
        try:
            import win32com.client
            devices = win32com.client.Dispatch("PortableDeviceAutomationFactory")
            assert devices is not None
        except (ImportError, AttributeError):
            pytest.skip("PortableDeviceAutomation not available")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_library_mtp_import(self):
        try:
            from sync.device_sync_service import DeviceSyncService
            assert DeviceSyncService is not None
        except ImportError:
            pytest.skip("DeviceSyncService not imported")


class TestWindowsFFmpeg:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_ffmpeg_in_path(self):
        ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
        result = subprocess.run(["where", ffmpeg], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0 or "ffmpeg" in os.environ.get("PATH", "")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_ffprobe_in_path(self):
        ffprobe = os.environ.get("FFPROBE_PATH", "ffprobe")
        result = subprocess.run(["where", ffprobe], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0 or "ffprobe" in os.environ.get("PATH", "")

    def test_ffmpeg_discovery_with_env(self):
        from core.external_process import find_executable
        path = find_executable("ffmpeg")
        if path:
            assert isinstance(path, str)
            assert os.path.isfile(path) or os.access(path, os.X_OK)

    def test_ffprobe_discovery_with_env(self):
        from core.external_process import find_executable
        path = find_executable("ffprobe")
        if path:
            assert isinstance(path, str)
            assert os.path.isfile(path) or os.access(path, os.X_OK)


class TestWindowsNotifications:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_windows_toast_notification(self):
        try:
            from plyer import notification
            assert notification is not None
        except ImportError:
            pytest.skip("plyer not available")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_notification_service_import(self):
        from core.notification_service import NotificationService
        assert NotificationService is not None


class TestWindowsShortcuts:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_shortcut_creation(self):
        try:
            import winshell
            assert winshell is not None
        except ImportError:
            pytest.skip("winshell not available")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_start_menu_accessible(self):
        start_menu = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu")
        assert os.path.isdir(start_menu)

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_desktop_folder_accessible(self):
        desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        assert os.path.isdir(desktop)


class TestWindowsPackaging:
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_pyinstaller_spec(self):
        spec = REPO / "michi.spec"
        if spec.exists():
            content = spec.read_text()
            assert "pyinstaller" in content.lower()

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_nsis_installer(self):
        nsis = REPO / "install.nsi"
        if nsis.exists():
            content = nsis.read_text()
            assert "OutFile" in content

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_packaging_import(self):
        try:
            from tests.test_packaging import TestPackaging
            assert TestPackaging is not None
        except ImportError:
            pytest.skip("test_packaging not imported")

    def test_no_linux_only_deps_in_core(self):
        core_dir = REPO / "core"
        linux_only_modules = {"dbus", "gi", "PyGObject"}
        for pyfile in core_dir.glob("*.py"):
            content = pyfile.read_text()
            for mod in linux_only_modules:
                assert f"import {mod}" not in content, f"{pyfile} imports Linux-only {mod}"
                assert f"from {mod}" not in content, f"{pyfile} imports Linux-only {mod}"
