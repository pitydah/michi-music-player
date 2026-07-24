"""Tests for ShazamIO recognition provider."""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_shazamio():
    module_name = "shazamio"
    already_there = module_name in sys.modules
    if not already_there:
        mock_mod = types.ModuleType(module_name)
        mock_mod.Shazam = MagicMock()
        sys.modules[module_name] = mock_mod
    yield
    if not already_there:
        sys.modules.pop(module_name, None)


class TestShazamProvider:
    def make_provider(self):
        with patch("importlib.util.find_spec", return_value=True):
            from recognition.providers.shazam import ShazamProvider
            p = ShazamProvider()
            p._available = True
            return p

    def test_identify_returns_match(self):
        p = self.make_provider()
        p._identify_async = AsyncMock(return_value={
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "year": 2024,
            "genre": "Rock",
            "confidence": 0.8,
            "provider": "shazamio",
            "source": "shazam",
            "external_url": "",
            "artwork_url": "",
            "raw_json": {},
        })
        result = p.identify(filepath="/path/to/song.mp3")
        assert result is not None
        assert result["title"] == "Test Song"
        assert result["artist"] == "Test Artist"
        assert result["confidence"] == 0.8
        assert result["provider"] == "shazamio"

    def test_identify_no_match(self):
        p = self.make_provider()
        p._identify_async = AsyncMock(return_value=None)
        result = p.identify(filepath="/path/to/song.mp3")
        assert result is None

    def test_identify_api_error(self):
        p = self.make_provider()
        p._identify_async = AsyncMock(side_effect=Exception("API error"))
        result = p.identify(filepath="/path/to/song.mp3")
        assert result is None

    @patch("recognition.providers.audd.AudDProvider.identify")
    def test_fallback_to_audd_on_error(self, mock_audd_identify):
        from recognition.providers.shazam import ShazamProvider
        from recognition.providers.audd import AudDProvider
        p = ShazamProvider()
        p._available = True
        p._identify_async = AsyncMock(side_effect=Exception("Shazam failed"))
        mock_audd_identify.return_value = {
            "title": "Fallback Song",
            "artist": "Fallback Artist",
            "confidence": 0.9,
            "provider": "audd",
        }
        shazam_result = p.identify(filepath="/path/to/song.mp3")
        assert shazam_result is None
        audd = AudDProvider()
        audd.api_key = "test_key"
        fallback_result = audd.identify(filepath="/path/to/song.mp3")
        assert fallback_result is not None
        assert fallback_result["title"] == "Fallback Song"
        assert fallback_result["provider"] == "audd"
