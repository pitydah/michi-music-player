"""Tests for TranscodeService — ffmpeg-based audio conversion."""
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from legacy_widgets.ui_archive.services.transcode_service import TranscodeService


@pytest.fixture
def service():
    return TranscodeService()


class TestTranscodeService:
    def test_available_checks_ffmpeg(self, service):
        """available property reflects ffmpeg installation."""
        result = service.available
        assert isinstance(result, bool)

    def test_get_profile_known(self, service):
        p = service.get_profile("opus_balanced")
        assert p["name"] == "OPUS 160"

    def test_get_profile_unknown(self, service):
        p = service.get_profile("nonexistent")
        assert p["name"] == "Original"

    def test_needs_transcode_true(self, service):
        assert service.needs_transcode("/tmp/a.mp3", "opus_balanced") is True

    def test_needs_transcode_original_false(self, service):
        assert service.needs_transcode("/tmp/a.mp3", "original") is False


class TestTranscodeOriginal:
    def test_original_copies_file(self, service):
        tmpdir = tempfile.mkdtemp()
        try:
            src = os.path.join(tmpdir, "src.flac")
            dst = os.path.join(tmpdir, "out", "dst.flac")
            with open(src, "wb") as f:
                f.write(b"audio data")
            result = service.transcode(src, dst, "original")
            assert result["ok"] is True
            assert result["destination"] == dst
            assert os.path.isfile(dst)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_original_source_missing(self, service):
        result = service.transcode("/nonexistent/file.flac", "/tmp/out.flac", "original")
        assert result["ok"] is False
        assert "not found" in result["error"]


class TestTranscodeFfmpeg:
    def test_missing_source(self, service):
        result = service.transcode("/nonexistent.mp3", "/tmp/out.opus", "opus_balanced")
        assert result["ok"] is False

    def test_unknown_profile(self, service):
        src = "/tmp/test.flac"
        with open(src, "w") as f:
            f.write("data")
        try:
            result = service.transcode(src, "/tmp/out.opus", "invalid_profile")
            assert result["ok"] is False
        finally:
            os.remove(src)

    def test_ffmpeg_not_found(self, service):
        tmpdir = tempfile.mkdtemp()
        try:
            src = os.path.join(tmpdir, "test.flac")
            with open(src, "w") as f:
                f.write("audio")
            with patch("shutil.which", return_value=None):
                result = service.transcode(src, os.path.join(tmpdir, "out.opus"), "opus_balanced")
                assert result["ok"] is False
                assert "ffmpeg" in result["error"].lower() or "No ffmpeg" in result["error"]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_transcode_success_op(self, service):
        """Mock ffmpeg to simulate successful transcode."""
        tmpdir = tempfile.mkdtemp()
        try:
            src = os.path.join(tmpdir, "src.flac")
            dst = os.path.join(tmpdir, "dst.opus")
            with open(src, "wb") as f:
                f.write(b"audio")

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stderr = ""

            def mock_run_side_effect(cmd, **kwargs):
                out_file = cmd[-1]
                os.makedirs(os.path.dirname(out_file) if os.path.dirname(out_file) else ".", exist_ok=True)
                with open(out_file, "wb") as f:
                    f.write(b"transcoded")
                return mock_proc

            with (
                patch("subprocess.run", side_effect=mock_run_side_effect),
                patch("shutil.which", return_value="/usr/bin/ffmpeg"),
            ):
                    result = service.transcode(src, dst, "opus_balanced")
                    assert result["ok"] is True
                    assert os.path.isfile(dst)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_transcode_ffmpeg_error(self, service):
        """ffmpeg returns non-zero exit code."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "Invalid data found"

        tmpdir = tempfile.mkdtemp()
        try:
            src = os.path.join(tmpdir, "src.flac")
            with open(src, "w") as f:
                f.write("audio")
            with patch("subprocess.run", return_value=mock_proc):
                result = service.transcode(src, os.path.join(tmpdir, "dst.opus"), "opus_balanced")
                assert result["ok"] is False
                assert "Invalid data" in result["error"]
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_flac_mobile_profile_exists(self, service):
        profile = service.get_profile("flac_mobile")
        assert profile["name"] == "FLAC móvil"

    def test_build_command_flac_mobile(self, service):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            cmd = service._build_command("/tmp/src.flac", "flac_mobile")
            assert "-c:a" in cmd
            assert "flac" in cmd

    def test_build_command_opus_balanced(self, service):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            cmd = service._build_command("/tmp/src.flac", "opus_balanced")
            assert "libopus" in cmd
            assert "160k" in cmd

    def test_build_command_unknown_profile(self, service):
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            cmd = service._build_command("/tmp/src.flac", "bogus")
            assert cmd is None
