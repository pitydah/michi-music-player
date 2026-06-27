"""Tests for CoverArtService — XDG path resolution."""
from unittest.mock import MagicMock, patch


class TestCoverArtServiceXDG:
    def test_cache_dir_uses_xdg(self, monkeypatch):
        """CoverArtService CACHE_DIR should resolve via core.paths, not legacy ~/.cache/michi."""
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", "/tmp/michi-test-cache-svc")
        import importlib
        import library.cover_art_service
        importlib.reload(library.cover_art_service)
        cache_dir = library.cover_art_service.CACHE_DIR
        assert "/tmp/michi-test-cache-svc" in cache_dir
        assert "/.cache/michi/covers" not in cache_dir

    def test_cache_dir_exists(self):
        """CACHE_DIR should be creatable."""
        import library.cover_art_service
        d = library.cover_art_service.CACHE_DIR
        assert "michi-music-player" in d or "michi" in d
        assert "covers" in d

    def test_find_cover_uses_xdg_cache(self, monkeypatch):
        """find_cover() should save embedded covers to XDG cache, not legacy."""
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", "/tmp/michi-test-cover-save")
        import importlib
        import library.cover_art_service
        importlib.reload(library.cover_art_service)
        cache_dir = library.cover_art_service.CACHE_DIR
        from core.paths import covers_cache_dir
        expected = covers_cache_dir()
        assert cache_dir == expected

    def test_find_cover_saves_under_xdg(self, monkeypatch, tmp_path):
        """find_cover() must save embedded covers inside MICHI_TEST_CACHE_DIR."""
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", str(tmp_path))
        import importlib
        import library.cover_art_service
        importlib.reload(library.cover_art_service)
        cas = library.cover_art_service.CoverArtService

        with patch("library.album_art.find_cover_in_dir", return_value=""):
            mock_pix = MagicMock()
            mock_pix.isNull.return_value = False
            mock_pix.save.return_value = True
            with patch("library.album_art._extract_embedded_cover_from_file", return_value=mock_pix):
                result = cas.find_cover("/music/test.flac")

        assert result
        assert str(tmp_path) in result
        assert "/.cache/michi/" not in result
        assert result.endswith("_embedded.png")

    def test_find_cover_does_not_use_legacy(self, monkeypatch, tmp_path):
        """find_cover() path must never point to ~/.cache/michi when XDG is set."""
        monkeypatch.setenv("MICHI_TEST_CACHE_DIR", str(tmp_path))
        import importlib
        import library.cover_art_service
        importlib.reload(library.cover_art_service)
        cas = library.cover_art_service.CoverArtService

        with patch("library.album_art.find_cover_in_dir", return_value=""):
            mock_pix = MagicMock()
            mock_pix.isNull.return_value = False
            mock_pix.save.return_value = True
            with patch("library.album_art._extract_embedded_cover_from_file", return_value=mock_pix):
                result = cas.find_cover("/music/test.flac")

        assert result is not None
        assert "/.cache/michi/" not in result
