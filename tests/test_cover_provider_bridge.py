import base64
import sqlite3
from unittest.mock import MagicMock

from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge


class TestCoverProviderBridge:
    def test_create_without_delegate(self):
        bridge = CoverProviderBridge()
        assert bridge.cacheSize == 0
        assert bridge.maxCacheSize == 128

    def test_prefers_injected_delegate(self):
        delegate = MagicMock()
        delegate.get_cover_data_url.return_value = "data:image/png;base64,AAA="
        bridge = CoverProviderBridge(cover_bridge=delegate)

        result = bridge.requestCover("album-1", 200)

        assert result == "data:image/png;base64,AAA="
        assert bridge.isCached("album-1") is True
        delegate.get_cover_data_url.assert_called_once_with("album-1")

    def test_reads_canonical_album_art_cache(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MICHI_TEST_DATA_DIR", str(tmp_path))
        database = tmp_path / "library.db"
        connection = sqlite3.connect(database)
        connection.execute(
            "CREATE TABLE album_art_cache (album_hash TEXT PRIMARY KEY, mime TEXT, data BLOB)"
        )
        payload = b"minimal-image-payload"
        connection.execute(
            "INSERT INTO album_art_cache(album_hash, mime, data) VALUES (?, ?, ?)",
            ("album-key", "image/png", payload),
        )
        connection.commit()
        connection.close()

        bridge = CoverProviderBridge()
        result = bridge.requestCover("album-key", 180)

        assert result.startswith("data:image/png;base64,")
        assert base64.b64decode(result.split(",", 1)[1]) == payload
        assert bridge.cacheStats()["resolved"] == 1

    def test_miss_is_cached_and_can_be_invalidated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MICHI_TEST_DATA_DIR", str(tmp_path))
        connection = sqlite3.connect(tmp_path / "library.db")
        connection.execute(
            "CREATE TABLE album_art_cache (album_hash TEXT PRIMARY KEY, mime TEXT, data BLOB)"
        )
        connection.commit()
        connection.close()

        bridge = CoverProviderBridge()
        assert bridge.requestCover("missing", 180) == ""
        assert bridge.isCached("missing") is True
        assert bridge.cacheStats()["misses"] == 1
        assert bridge.invalidateCover("missing") == {"ok": True, "removed": True}
        assert bridge.isCached("missing") is False

    def test_clear_cache_reports_count(self):
        delegate = MagicMock()
        delegate.get_cover_data_url.return_value = "data:image/jpeg;base64,AAA="
        bridge = CoverProviderBridge(cover_bridge=delegate)
        bridge.requestCover("one", 180)
        bridge.requestCover("two", 180)

        assert bridge.clearCache() == {"ok": True, "cleared": 2}
        assert bridge.cacheSize == 0
