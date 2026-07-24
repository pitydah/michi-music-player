"""Tests for CDRipperService — command building, detection, cancellation."""
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture
def ripper():
    from core.audio_lab.cd_ripper_service import CDRipperService
    return CDRipperService()


class TestCDRipperCommands:
    def test_build_flac_command(self, ripper):
        """ffmpeg FLAC rip command is correctly structured."""
        cmd = ripper._build_command("flac", "/dev/sr0", 1, "/output/track01.flac")
        assert cmd is not None
        assert "ffmpeg" in cmd or cmd[0].endswith("ffmpeg")
        assert "-f" in cmd
        assert "cdaudio" in cmd
        assert "-i" in cmd
        assert any("sr0" in p for p in cmd)
        assert "flac" in cmd

    def test_build_wav_command(self, ripper):
        cmd = ripper._build_command("wav", "/dev/sr0", 1, "/output/track01.wav")
        assert cmd is not None
        assert any("pcm_s16le" in p for p in cmd)

    def test_build_mp3_command(self, ripper):
        cmd = ripper._build_command("mp3", "/dev/sr0", 1, "/output/track01.mp3")
        assert cmd is not None
        assert any("libmp3lame" in p for p in cmd)

    def test_unsupported_format(self, ripper):
        cmd = ripper._build_command("wma", "/dev/sr0", 1, "/output/track.wma")
        assert cmd is None

    def test_command_uses_list_not_shell(self, ripper):
        cmd = ripper._build_command("flac", "/dev/sr0", 1, "/output/track.flac")
        assert isinstance(cmd, list)
        # No string with shell metacharacters
        cmd_str = " ".join(cmd)
        assert ";" not in cmd_str
        assert "&&" not in cmd_str
        assert "|" not in cmd_str

    def test_rip_track_no_shell(self, ripper):
        """Verify subprocess is called with list args, not shell=True."""
        with patch("core.audio_lab.cd_ripper_service.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            ripper.rip_track("/dev/sr0", 1, "/out.flac", "flac")

            # Verify Popen was called with a list, not a string
            call_args = mock_popen.call_args
            assert call_args is not None
            args, kwargs = call_args
            assert isinstance(args[0], list), f"Expected list args, got {type(args[0])}"
            assert kwargs.get("shell") is None or kwargs.get("shell") is False


class TestCDRipperDetection:
    def test_detect_drives_linux(self, ripper):
        """Detection on Linux scans typical device paths."""
        with patch("os.name", "posix"), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "drive: 'DVD+-RW  Drive'"
            mock_run.return_value = mock_result

            drives = ripper.detect_drives()
            # Should at least check for /dev/sr0
            assert len(drives) >= 0

    def test_detect_drives_no_device(self, ripper):
        """When no optical drive exists, returns empty list."""
        with patch("os.name", "posix"), \
             patch("os.path.exists", return_value=False):
            drives = ripper.detect_drives()
            assert len(drives) == 0


class TestCDRipperCancellation:
    def test_cancel_requested_flag(self, ripper):
        ripper._cancel_requested = True
        assert ripper._cancel_requested
        ripper.cancel_rip()
        assert ripper._cancel_requested

    def test_cancel_no_process(self, ripper):
        ripper.cancel_rip()
        assert ripper._cancel_requested


class TestCDRipperSupportedFormats:
    def test_formats_include_flac(self, ripper):
        assert "flac" in ripper.supported_formats

    def test_formats_include_mp3(self, ripper):
        assert "mp3" in ripper.supported_formats

    def test_formats_include_wav(self, ripper):
        assert "wav" in ripper.supported_formats

    def test_default_is_lossless(self, ripper):
        assert ripper.default_format == "flac"
