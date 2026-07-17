from unittest.mock import MagicMock
from sync.sync_discovery import DiscoveryServer


class TestSyncDiscovery:
    def test_create(self):
        ds = DiscoveryServer(alias="TestPlayer")
        assert ds._alias == "TestPlayer"
        assert ds._running is False
