"""Pure Python tests for Playlist Hub M3U/M3U8 import/export logic.
Tests parse_playlist_entries and export_m3u directly from core.playlist_io.
No QML or bridge initialization required.
"""
from __future__ import annotations

import os
import tempfile

from core.playlist_io import parse_playlist_entries, export_m3u


def _make_m3u(path: str, lines: list[str]):
    with open(path, "w", encoding="latin-1") as f:
        for line in lines:
            f.write(line + "\n")


def _make_m3u8(path: str, lines: list[str]):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


class TestPlaylistHubParse:
    """Test M3U/M3U8 parsing logic (pure Python, no bridge)."""

    def test_parse_m3u_with_paths(self, tmp_path):
        m3u = tmp_path / "test.m3u"
        track1 = tmp_path / "song1.flac"
        track2 = tmp_path / "song2.mp3"
        track1.write_text("dummy")
        track2.write_text("dummy")
        _make_m3u(str(m3u), [str(track1), str(track2)])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 2
        assert entries[0].exists is True
        assert entries[0].resolved_path == str(track1)
        assert entries[1].resolved_path == str(track2)

    def test_parse_m3u8_utf8(self, tmp_path):
        m3u8 = tmp_path / "test.m3u8"
        track = tmp_path / "canción.flac"
        track.write_text("dummy")
        _make_m3u8(str(m3u8), [str(track)])
        entries = parse_playlist_entries(str(m3u8))
        assert len(entries) == 1
        assert entries[0].exists is True
        assert "canción" in entries[0].resolved_path

    def test_parse_m3u_relative_paths(self, tmp_path):
        m3u = tmp_path / "relative.m3u"
        (tmp_path / "track_a.ogg").write_text("dummy")
        _make_m3u(str(m3u), ["track_a.ogg"])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 1
        assert entries[0].exists is True
        assert entries[0].resolved_path == str(tmp_path / "track_a.ogg")

    def test_parse_skips_comments_and_extinf(self, tmp_path):
        m3u = tmp_path / "extinf.m3u"
        track = tmp_path / "track.flac"
        track.write_text("dummy")
        _make_m3u(str(m3u), [
            "#EXTM3U",
            "#EXTINF:123,Test Artist - Test Title",
            str(track),
            "# comment",
        ])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 1
        assert entries[0].resolved_path == str(track)

    def test_parse_skips_empty_lines(self, tmp_path):
        m3u = tmp_path / "empty_lines.m3u"
        track = tmp_path / "track.flac"
        track.write_text("dummy")
        _make_m3u(str(m3u), ["", str(track), "", ""])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 1

    def test_parse_recognizes_remote_urls(self, tmp_path):
        m3u = tmp_path / "remote.m3u"
        _make_m3u(str(m3u), [
            "http://example.com/stream.mp3",
            "https://radio.example.org/stream.ogg",
        ])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 2
        assert all(e.is_remote for e in entries)
        assert all(not e.exists for e in entries)

    def test_parse_nonexistent_file_returns_empty(self):
        entries = parse_playlist_entries("/nonexistent/path.m3u")
        assert entries == []

    def test_parse_missing_tracks_reported_as_not_exists(self, tmp_path):
        m3u = tmp_path / "missing.m3u"
        _make_m3u(str(m3u), ["/path/does/not/exist.flac"])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 1
        assert entries[0].exists is False

    def test_malformed_binary_data_does_not_crash(self, tmp_path):
        m3u = tmp_path / "garbage.m3u"
        m3u.write_bytes(b"\x00\xff\xfe\xfd\x00\x01\x02\xff")
        entries = parse_playlist_entries(str(m3u))
        assert isinstance(entries, list)

    def test_malformed_control_chars_does_not_crash(self, tmp_path):
        m3u = tmp_path / "control.m3u"
        m3u.write_bytes(b"\x01\x02\x03\x04\x05\x06")
        entries = parse_playlist_entries(str(m3u))
        assert isinstance(entries, list)

    def test_parse_empty_file_returns_empty(self, tmp_path):
        m3u = tmp_path / "empty.m3u"
        m3u.write_text("")
        entries = parse_playlist_entries(str(m3u))
        assert entries == []

    def test_export_m3u_absolute_paths(self, tmp_path):
        dest = tmp_path / "export.m3u"
        filepaths = ["/music/track1.flac", "/music/track2.mp3"]
        export_m3u(str(dest), filepaths)
        content = dest.read_text(encoding="utf-8")
        assert "#EXTM3U" in content
        assert "/music/track1.flac" in content
        assert "/music/track2.mp3" in content

    def test_export_m3u_relative_paths(self, tmp_path):
        dest = tmp_path / "export_relative.m3u"
        filepaths = ["relative/track1.flac", "../track2.mp3"]
        export_m3u(str(dest), filepaths)
        content = dest.read_text(encoding="utf-8")
        assert "relative/track1.flac" in content
        assert "../track2.mp3" in content

    def test_export_m3u_utf8_paths(self, tmp_path):
        dest = tmp_path / "utf8_export.m3u"
        filepaths = ["/music/canción.flac", "/music/über.mp3"]
        export_m3u(str(dest), filepaths)
        content = dest.read_text(encoding="utf-8")
        assert "canción" in content
        assert "über" in content

    def test_export_m3u_empty_list_writes_header(self, tmp_path):
        dest = tmp_path / "empty_export.m3u"
        export_m3u(str(dest), [])
        assert dest.exists()
        content = dest.read_text()
        assert "#EXTM3U" in content or content.strip() == ""

    def test_roundtrip_absolute_paths(self, tmp_path):
        src = tmp_path / "original.m3u"
        track = tmp_path / "roundtrip.flac"
        track.write_text("dummy")
        _make_m3u(str(src), [str(track)])
        entries = parse_playlist_entries(str(src))
        dest = tmp_path / "roundtrip.m3u"
        export_m3u(str(dest), [e.resolved_path for e in entries if e.exists])
        content = dest.read_text(encoding="utf-8")
        assert str(track) in content

    def test_playlist_with_mixed_absolute_relative_remote(self, tmp_path):
        m3u = tmp_path / "mixed.m3u"
        (tmp_path / "local.flac").write_text("dummy")
        _make_m3u(str(m3u), [
            "local.flac",
            "/absolute/path/track.flac",
            "https://stream.example.com/radio",
        ])
        entries = parse_playlist_entries(str(m3u))
        assert len(entries) == 3
        assert entries[0].exists is True
        assert entries[0].is_remote is False
        assert entries[1].is_remote is False
        assert entries[2].is_remote is True
