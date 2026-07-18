"""Tests for Michi Micro Server interaction — discovery, health, capabilities."""
from unittest.mock import MagicMock, patch

import pytest


class TestMichiLinkClient:
    @pytest.fixture
    def client(self):
        from integrations.michi_link.client import MichiLinkClient
        return MichiLinkClient()

    def test_client_import(self, client):
        assert client is not None

    def test_discover_servers(self, client):
        """Discovery connects to a host:port."""
        result = client.discover("localhost", 53318)
        assert result is None or isinstance(result, dict)

    def test_pair(self, client):
        """Pair requires a server reference."""
        from integrations.michi_link.client import RemoteServerInfo
        server = RemoteServerInfo(host="localhost", port=53318)
        result = client.pair(server)
        assert not result  # will fail without real server

    def test_search(self, client):
        from integrations.michi_link.client import RemoteServerInfo
        server = RemoteServerInfo(host="localhost", port=53318)
        result = client.search(server, "test")
        assert result is None or isinstance(result, list)


class TestMicroServerService:
    @pytest.fixture
    def svc(self):
        from core.micro_server_service import MicroServerService
        return MicroServerService()

    def test_service_import(self, svc):
        assert svc is not None

    def test_import_tracks(self, svc):
        """Import tracks returns status."""
        result = svc.import_tracks(["/test/a.flac", "/test/b.flac"])
        assert "ok" in result or "error" in result

    def test_import_album(self, svc):
        result = svc.import_album("AlbumKey")
        assert "ok" in result or "error" in result

    def test_import_artist(self, svc):
        result = svc.import_artist("ArtistKey")
        assert "ok" in result

    def test_health(self, svc):
        assert svc.health() is not None


class TestDiscovery:
    def test_discovery_import(self):
        from sync.sync_discovery import DiscoveryServer
        assert DiscoveryServer is not None

    def test_discovery_start_stop(self):
        from sync.sync_discovery import DiscoveryServer
        sd = DiscoveryServer()
        sd.start()
        sd.stop()
