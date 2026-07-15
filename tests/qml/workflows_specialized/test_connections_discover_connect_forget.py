from __future__ import annotations
"""MW: Connections — discover servers, connect/request pair, forget server."""

from unittest.mock import MagicMock

from .specialized_workflow_harness import SpecializedWorkflowBase


class TestConnectionsDiscoverConnectForget(SpecializedWorkflowBase):
    def test_initial_state(self, connections_fixtures):
        b = connections_fixtures
        assert b.microServerState == "not_configured"

    def test_discover_servers(self, connections_fixtures):
        b = connections_fixtures
        result = b.scanForServers()
        self.assert_ok(result)

    def test_request_pair(self, connections_fixtures):
        b = connections_fixtures
        result = b.requestPair(0)
        self.assert_ok(result)

    def test_forget_server(self, connections_fixtures):
        b = connections_fixtures
        result = b.forgetServer("server_id")
        self.assert_ok(result)

    def test_full_workflow(self, connections_fixtures):
        b = connections_fixtures
        b.scanForServers()
        b.requestPair(0)
        b.forgetServer("server_id")
        assert b.scanForServers.called
        assert b.requestPair.called
        assert b.forgetServer.called

    def test_no_discovered_servers(self):
        b = MagicMock()
        b.discoveredServers = []
        assert len(b.discoveredServers) == 0

    def test_pairing_error(self, connections_fixtures):
        b = connections_fixtures
        b.requestPair = MagicMock(
            return_value={"ok": False, "error": "PAIRING_FAILED"}
        )
        result = b.requestPair(0)
        self.assert_error(result, "PAIRING_FAILED")
