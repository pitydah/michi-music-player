"""CD Ripper simulation tests — command building, detection with mocks, cancellation, progress."""
import subprocess
from unittest.mock import MagicMock, patch

import pytest


class TestCDRipperDetection:
    def test_detect_drives_linux(self):
        from core.audio_lab.cd_ripper_service import CDRipperService
        ripper = CDRipperService()
        with patch("os.name", "posix"), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "drive: 'DVD+-RW Drive'"
            mock_run.return_value = mock_result
            drives = ripper.detect_drives()
            assert len(drives) > 0
            assert drives[0].device == "/dev/sr0"

    def test_detect_drives_windows(self):
        from core.audio_lab.cd_ripper_service import CDRipperService
        ripper = CDRipperService()
        with patch("os.name", "nt"), \
             patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "D:"
            mock_run.return_value = mock_result
            drives = ripper.detect_drives()
            assert isinstance(drives, list)


class TestCDRipperCommands:
    @pytest.fixture
    def ripper(self):
        from core.audio_lab.cd_ripper_service import CDRipperService
        return CDRipperService()

    def test_rip_flac_command(self, ripper):
        cmd = ripper._build_command("flac", "/dev/sr0", 1, "/out/track01.flac")
        assert cmd is not None
        assert "ffmpeg" in str(cmd)
        assert "flac" in str(cmd)
        assert "/dev/sr0:1" in str(cmd)

    def test_rip_wav_command(self, ripper):
        cmd = ripper._build_command("wav", "/dev/sr0", 2, "/out/track02.wav")
        assert cmd is not None
        assert "pcm_s16le" in str(cmd)

    def test_rip_mp3_command(self, ripper):
        cmd = ripper._build_command("mp3", "/dev/sr0", 3, "/out/track03.mp3")
        assert cmd is not None
        assert "libmp3lame" in str(cmd)

    def test_unsupported_format(self, ripper):
        cmd = ripper._build_command("wma", "/dev/sr0", 1, "/out/track.wma")
        assert cmd is None

    def test_command_no_shell(self, ripper):
        cmd = ripper._build_command("flac", "/dev/sr0", 1, "/out/t.flac")
        assert isinstance(cmd, list)
        cmd_str = " ".join(cmd)
        assert ";" not in cmd_str
        assert "&&" not in cmd_str


class TestCDRipperLifecycle:
    @pytest.fixture
    def ripper(self):
        from core.audio_lab.cd_ripper_service import CDRipperService
        return CDRipperService()

    def test_rip_cancellation_flag(self, ripper):
        assert not ripper._cancel_requested
        ripper.cancel_rip()
        assert ripper._cancel_requested

    def test_rip_timeout(self, ripper):
        with patch("core.audio_lab.cd_ripper_service.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 300)
            mock_popen.return_value = mock_proc
            result = ripper.rip_track("/dev/sr0", 1, "/out.flac", "flac")
            assert "espera" in result.get("error", "") or "timeout" in result.get("error", "").lower()
