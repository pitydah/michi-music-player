from unittest.mock import MagicMock

from ui_qml_bridge.cover_provider_bridge import CoverProviderBridge


class TestCoverProviderBridge:
    def test_create_without_service(self):
        bridge = CoverProviderBridge()
        assert bridge.cacheSize == 0
        assert bridge.maxCacheSize == 128

    def test_uses_injected_service(self):
        service = MagicMock()
        service.resolve_cover_with_mime.return_value = ("image/png", b"AAA")
        bridge = CoverProviderBridge(artwork_service=service)

        result = bridge.requestCover("album-1", 200)

        assert result == "data:image/png;base64,QUFB"
        assert bridge.isCached("album-1") is True
        service.resolve_cover_with_mime.assert_called_once_with("album-1")

    def test_handles_service_miss(self):
        service = MagicMock()
        service.resolve_cover_with_mime.return_value = (None, None)
        bridge = CoverProviderBridge(artwork_service=service)

        result = bridge.requestCover("missing", 180)

        assert result == ""
        assert bridge.isCached("missing") is True
        assert bridge.cacheStats()["misses"] == 1

    def test_miss_is_cached_and_can_be_invalidated(self):
        bridge = CoverProviderBridge()
        assert bridge.requestCover("missing", 180) == ""
        assert bridge.isCached("missing") is True
        assert bridge.cacheStats()["misses"] == 1
        assert bridge.invalidateCover("missing") == {"ok": True, "removed": True}
        assert bridge.isCached("missing") is False

    def test_clear_cache_reports_count(self):
        service = MagicMock()
        service.resolve_cover_with_mime.return_value = ("image/jpeg", b"AAA")
        bridge = CoverProviderBridge(artwork_service=service)
        bridge.requestCover("one", 180)
        bridge.requestCover("two", 180)

        assert bridge.clearCache() == {"ok": True, "cleared": 2}
        assert bridge.cacheSize == 0

    def test_handles_missing_service_gracefully(self):
        bridge = CoverProviderBridge(artwork_service=None)
        assert bridge.requestCover("any-key", 180) == ""

    def test_handles_service_exception(self):
        service = MagicMock()
        service.resolve_cover_with_mime.side_effect = RuntimeError("db error")
        bridge = CoverProviderBridge(artwork_service=service)

        result = bridge.requestCover("broken", 180)

        assert result == ""
        assert bridge.isCached("broken") is True
