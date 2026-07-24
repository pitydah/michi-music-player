"""Tests for AcoustID recognition provider."""
import json
from unittest.mock import MagicMock, patch



class TestAcoustIDProvider:
    def make_provider(self, fpcalc_path="/usr/bin/fpcalc"):
        with patch("recognition.providers.acoustid.AcoustIDProvider._find_fpcalc",
                   return_value=fpcalc_path):
            from recognition.providers.acoustid import AcoustIDProvider
            p = AcoustIDProvider()
            p._fpcalc_path = fpcalc_path
            p._client_key = "test_key"
            return p

    def test_fpcalc_detection(self):
        with patch("shutil.which", return_value="/usr/local/bin/fpcalc"):
            from recognition.providers.acoustid import AcoustIDProvider
            with patch("recognition.providers.acoustid.AcoustIDProvider._find_fpcalc",
                       return_value="/usr/local/bin/fpcalc"):
                p = AcoustIDProvider()
                p._fpcalc_path = "/usr/local/bin/fpcalc"
                assert p._fpcalc_path is not None
                assert p.is_configured() is True

    def test_fpcalc_not_found(self):
        with patch("shutil.which", return_value=None), \
             patch("os.path.isfile", return_value=False):
            from recognition.providers.acoustid import AcoustIDProvider
            path = AcoustIDProvider._find_fpcalc()
            assert path is None
            with patch("recognition.providers.acoustid.AcoustIDProvider._find_fpcalc",
                       return_value=None):
                p = AcoustIDProvider()
                p._fpcalc_path = None
                assert p.is_configured() is False
                result = p.identify(filepath="/path/to/song.mp3")
                assert result is None

    @patch("urllib.request.urlopen")
    def test_identify_with_fingerprint(self, mock_urlopen):
        p = self.make_provider()
        p._fingerprint = MagicMock(return_value=("fp_known_abc123", 180.0))

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "status": "ok",
            "results": [{
                "score": 0.85,
                "id": "acoustid-known-1",
                "recordings": [{
                    "title": "Known Song",
                    "artists": [{"name": "Known Artist"}],
                    "releasegroups": [{"title": "Known Album"}],
                }]
            }]
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = p.identify(filepath="/path/to/song.mp3")
        assert result is not None
        assert result["title"] == "Known Song"
        assert result["artist"] == "Known Artist"
        assert result["album"] == "Known Album"
        assert result["confidence"] == 0.85
        assert result["provider"] == "acoustid"

    @patch("urllib.request.urlopen")
    def test_multiple_results(self, mock_urlopen):
        p = self.make_provider()
        p._fingerprint = MagicMock(return_value=("fp_multi", 200.0))

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "status": "ok",
            "results": [
                {
                    "score": 0.92,
                    "id": "acoustid-best",
                    "recordings": [{
                        "title": "Best Match",
                        "artists": [{"name": "Artist A"}],
                        "releasegroups": [{"title": "Album A"}],
                    }]
                },
                {
                    "score": 0.75,
                    "id": "acoustid-second",
                    "recordings": [{
                        "title": "Second Match",
                        "artists": [{"name": "Artist B"}],
                        "releasegroups": [{"title": "Album B"}],
                    }]
                },
            ]
        }).encode()
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_ctx

        result = p.identify(filepath="/path/to/song.mp3")
        assert result is not None
        assert result["title"] == "Best Match"
        assert result["artist"] == "Artist A"
        assert result["confidence"] == 0.92
