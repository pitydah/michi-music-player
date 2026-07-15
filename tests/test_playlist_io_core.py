"""Functional migration tests for playlist I/O in the core layer."""

from __future__ import annotations

from pathlib import Path

from core.playlist_io import export_m3u, parse_playlist_entries
from core.playlist_service import PlaylistService


def test_m3u_resolves_relative_tracks_and_preserves_missing(tmp_path):
    track = tmp_path / "track.flac"
    track.write_bytes(b"audio")
    playlist = tmp_path / "mix.m3u8"
    playlist.write_text("#EXTM3U\ntrack.flac\nmissing.flac\n", encoding="utf-8")

    entries = parse_playlist_entries(str(playlist))

    assert [Path(entry.resolved_path).name for entry in entries] == [
        "track.flac",
        "missing.flac",
    ]
    assert [entry.exists for entry in entries] == [True, False]


def test_export_is_atomic_and_round_trips(tmp_path):
    track = tmp_path / "song.flac"
    track.write_bytes(b"audio")
    destination = tmp_path / "exported.m3u"

    export_m3u(str(destination), [str(track)], title="Test")

    assert destination.exists()
    assert not (tmp_path / "exported.m3u.tmp").exists()
    entries = parse_playlist_entries(str(destination))
    assert len(entries) == 1
    assert entries[0].resolved_path == str(track)


def test_playlist_service_import_preview_has_no_legacy_dependency(tmp_path):
    track = tmp_path / "song.flac"
    track.write_bytes(b"audio")
    playlist = tmp_path / "mix.m3u"
    playlist.write_text(f"#EXTM3U\n{track}\n", encoding="utf-8")

    result = PlaylistService().import_preview(str(playlist))

    assert result == {
        "ok": True,
        "format": ".m3u",
        "name": "mix",
        "total_entries": 1,
        "valid_entries": 1,
        "missing_entries": 0,
    }
