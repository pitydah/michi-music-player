"""Tests for metadata rename engine — patterns, preview, apply, security."""
import os
import tempfile

import pytest


@pytest.fixture
def sample_tags():
    from metadata.tag_model import TrackTags
    return TrackTags(
        filepath="/music/Artist/Album/song.flac",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        albumartist="Test Artist",
        tracknumber="01",
        genre="Rock",
        date="2020",
    )


class TestRenameEngine:
    def test_render_basic_pattern(self, sample_tags):
        from metadata.rename_engine import render_pattern
        result = render_pattern(sample_tags, "%artist%/%album%/%track% - %title%")
        assert "Test Artist" in result
        assert "Test Album" in result
        assert "01" in result
        assert "Test Song" in result

    def test_render_simple(self, sample_tags):
        from metadata.rename_engine import render_pattern
        result = render_pattern(sample_tags, "%artist% - %title%")
        assert result == "Test Artist - Test Song"

    def test_preview_rename(self, sample_tags):
        from metadata.rename_engine import preview_rename
        results = preview_rename([sample_tags], "%artist%/%album%/%track% - %title%")
        assert len(results) == 1
        old, new = results[0]
        assert old == "/music/Artist/Album/song.flac"
        assert "Test Artist" in new
        assert "Test Album" in new

    def test_preview_multiple(self, sample_tags):
        from metadata.rename_engine import preview_rename
        from metadata.tag_model import TrackTags
        tags2 = TrackTags(
            filepath="/music/Artist/Album/song2.flac",
            title="Song 2", artist="Test Artist", album="Test Album", tracknumber="02",
        )
        results = preview_rename([sample_tags, tags2], "%artist%/%album%/%track% - %title%")
        assert len(results) == 2

    def test_sanitize_filename(self):
        from metadata.rename_engine import sanitize_filename_part
        result = sanitize_filename_part('AC/DC - "Back in Black"')
        assert "/" not in result
        assert '"' not in result

    def test_apply_rename(self, tmp_path):
        from metadata.rename_engine import apply_rename, preview_rename
        from metadata.tag_model import TrackTags
        old = tmp_path / "old_song.flac"
        old.write_text("dummy")
        tags = TrackTags(filepath=str(old), title="New Name", artist="Artist", album="Album")
        preview = preview_rename([tags], "%artist%/%album%/%title%")
        ok, fail = apply_rename(preview)
        assert ok == 1
        assert fail == 0
        assert not old.exists()  # renamed away

    def test_apply_rename_skip_existing(self, tmp_path):
        from metadata.rename_engine import apply_rename, preview_rename
        from metadata.tag_model import TrackTags
        old = tmp_path / "old.flac"
        old.write_text("old")
        existing = tmp_path / "Artist" / "Album" / "New Name.flac"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text("existing")
        tags = TrackTags(filepath=str(old), title="New Name", artist="Artist", album="Album")
        preview = preview_rename([tags], "%artist%/%album%/%title%")
        ok, fail = apply_rename(preview)
        assert ok == 0  # skipped because target exists

    def test_path_traversal_prevention(self, sample_tags):
        from metadata.rename_engine import preview_rename
        from metadata.tag_model import TrackTags
        bad_tags = TrackTags(
            filepath="/music/Artist/Album/song.flac",
            title="../Outside",
            artist="../../etc",
            album="passwd",
        )
        results = preview_rename([bad_tags], "%artist%/%album%/%title%")
        for old, new in results:
            assert ".." not in new or "Outside" not in new

    def test_pattern_keys(self):
        from metadata.rename_engine import render_pattern
        from metadata.tag_model import TrackTags
        tags = TrackTags(filepath="/test.flac", title="T", artist="A", album="Al", genre="G", date="2024")
        result = render_pattern(tags, "%genre%/%year%/%title%")
        assert "G" in result
        assert "2024" in result

    def test_all_known_patterns(self, sample_tags):
        from metadata.rename_engine import _PATTERNS
        from metadata.rename_engine import preview_rename
        for pattern in _PATTERNS:
            results = preview_rename([sample_tags], pattern)
            assert len(results) == 1, f"Pattern failed: {pattern}"
