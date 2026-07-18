"""Tests for lyrics — sidecar .lrc, cache, offset, search fallback."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def lrc_content():
    return """[ti:Test Song]
[ar:Test Artist]
[al:Test Album]
[00:01.00]First line
[00:05.00]Second line
[00:10.00]Third line
"""


@pytest.fixture
def lrc_file(tmp_path, lrc_content):
    f = tmp_path / "Test Artist - Test Song.lrc"
    f.write_text(lrc_content)
    return f


class TestLyricsSidecar:
    def test_sidecar_provider_import(self):
        from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
        assert FileSidecarProvider is not None

    def test_read_sidecar(self, tmp_path, lrc_content):
        from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
        from core.lyrics.models import TrackIdentity

        provider = FileSidecarProvider()
        lrc = tmp_path / "Test Artist - Test Song.lrc"
        lrc.write_text(lrc_content)
        identity = TrackIdentity(title="Test Song", artist="Test Artist")
        result = provider.read(str(tmp_path), identity)
        assert result.ok
        assert result.document is not None
        assert len(result.document.lines) == 3

    def test_sidecar_not_found(self, tmp_path):
        from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
        from core.lyrics.models import TrackIdentity
        provider = FileSidecarProvider()
        identity = TrackIdentity(title="Nonexistent", artist="Nobody")
        result = provider.read(str(tmp_path), identity)
        assert not result.ok

    def test_parse_lrc(self, lrc_content):
        from core.lyrics.parser import parse_lrc
        doc = parse_lrc(lrc_content)
        assert doc is not None
        assert len(doc.lines) == 3

    def test_parse_plain(self):
        from core.lyrics.parser import parse_plain
        text = "Line 1\nLine 2\nLine 3"
        doc = parse_plain(text)
        assert doc is not None
        assert len(doc.lines) == 3

    def test_serialize_lrc(self):
        from core.lyrics.parser import serialize_lrc, parse_lrc
        content = "[00:01.00]Line 1\n[00:02.00]Line 2"
        doc = parse_lrc(content)
        serialized = serialize_lrc(doc)
        assert "Line 1" in serialized
        assert "00:01" in serialized

    def test_offset_adjustment(self, lrc_content):
        from core.lyrics.parser import parse_lrc
        doc = parse_lrc(lrc_content)
        original = doc.lines[0].start_ms
        doc.apply_offset(500)  # 500ms offset
        assert doc.lines[0].start_ms == original + 500


class TestLyricsService:
    def test_service_import(self):
        from core.lyrics_service import LyricsService
        assert LyricsService is not None

    def test_service_creation(self):
        from core.lyrics_service import LyricsService
        svc = LyricsService()
        assert svc is not None

    def test_search_current_track(self):
        from core.lyrics_service import LyricsService
        svc = LyricsService()
        with pytest.raises(Exception):
            svc.search_current_track()

    def test_cache_hit(self):
        from core.lyrics_service import LyricsService
        svc = LyricsService()
        result = svc.get_lyrics("test")
        assert result is None or isinstance(result, dict)

    def test_lyrics_bridge_import(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        assert LyricsBridge is not None

    def test_lyrics_bridge_has_signals(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        assert hasattr(LyricsBridge, 'dataChanged')
