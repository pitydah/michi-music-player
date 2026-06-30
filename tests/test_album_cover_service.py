"""Tests for AlbumCoverService — unified cover art resolution."""
from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch


def _make_track(filepath="/music/song.flac", album="Album", artist="Artist"):
    t = MagicMock()
    t.filepath = filepath
    t.album = album
    t.artist = artist
    return t


class TestAlbumCoverService:
    def test_resolve_cover_no_tracks(self):
        from library.album_cover_service import AlbumCoverService
        svc = AlbumCoverService()
        with patch("library.album_art.make_default_cover") as mock_fb:
            mock_fb.return_value = None
            result = svc.resolve_cover([])
            assert result is not None
            assert result.source == "fallback"

    def test_resolve_cover_with_external_file(self):
        from library.album_cover_service import AlbumCoverService
        svc = AlbumCoverService()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake_jpeg")
            cover_path = f.name
        try:
            with patch("library.album_cover_service._find_local_cover",
                       return_value=cover_path), \
                 patch("PySide6.QtGui.QPixmap") as mock_pix:
                mock_pix.return_value.isNull.return_value = False
                tracks = [_make_track(filepath="/music/song.flac")]
                result = svc.resolve_cover(tracks)
                assert result.source == "external_file"
                assert result.path == cover_path
        finally:
            os.unlink(cover_path)

    def test_resolve_cover_fallback(self):
        from library.album_cover_service import AlbumCoverService
        svc = AlbumCoverService()
        with patch("library.album_cover_service._find_local_cover", return_value=None), \
             patch("library.cover_art_service.extract_embedded_cover",
                   side_effect=ImportError("no module")), \
             patch("library.artwork_cache.get_cached", return_value=None), \
             patch("library.album_art.make_default_cover") as mock_fb:
            tracks = [_make_track(filepath="/nonexistent/song.flac")]
            svc.resolve_cover(tracks)
            mock_fb.assert_called_once()
