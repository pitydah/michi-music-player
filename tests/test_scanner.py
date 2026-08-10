"""Tests for filesystem scanner."""

from pathlib import Path

from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner


class TestFilesystemScanner:
    def test_scan_finds_audio_files(self, tmp_path):
        (tmp_path / "song.mp3").write_text("")
        (tmp_path / "song.flac").write_text("")
        (tmp_path / "readme.txt").write_text("")

        scanner = FilesystemLibraryScanner()
        result = scanner.scan(tmp_path)

        names = {p.name for p in result}
        assert "song.mp3" in names
        assert "song.flac" in names
        assert "readme.txt" not in names

    def test_scan_subdirectories(self, tmp_path):
        sub = tmp_path / "artist"
        sub.mkdir()
        (tmp_path / "root.mp3").write_text("")
        (sub / "deep.flac").write_text("")

        scanner = FilesystemLibraryScanner()
        result = scanner.scan(tmp_path)

        names = {p.name for p in result}
        assert "root.mp3" in names
        assert "deep.flac" in names

    def test_nonexistent_directory(self):
        scanner = FilesystemLibraryScanner()
        result = scanner.scan(Path("/nonexistent/path/xyz"))
        assert result == []

    def test_empty_directory(self, tmp_path):
        scanner = FilesystemLibraryScanner()
        result = scanner.scan(tmp_path)
        assert result == []
