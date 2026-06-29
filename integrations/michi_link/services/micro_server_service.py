"""MicroServerService — manages Player ↔ Micro Server interactions.

Full lifecycle: discover, pair, test_connection, read library, stats, search.
Returns Result objects — never raises to caller.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from integrations.michi_link.client import MichiLinkClient, RemoteServerInfo
from integrations.michi_link.services.result import Result

logger = logging.getLogger("michi.service.micro_server")


class MicroServerService:
    """High-level service for interacting with a remote Michi Micro Server."""

    def __init__(self, client: MichiLinkClient | None = None):
        self._client = client or MichiLinkClient()
        self._servers: dict[str, RemoteServerInfo] = {}

    def discover(self, host: str, port: int = 53318) -> Result:
        info = self._client.discover(host, port)
        if info is None:
            return Result.fail("DISCOVERY_FAILED",
                               f"Cannot reach server at {host}:{port}")
        key = f"{host}:{port}"
        self._servers[key] = info
        return Result.success(info, f"Server '{info.alias}' at {host}:{port}")

    def discover_servers(self, hosts: list[tuple[str, int]]) -> Result:
        found = []
        for host, port in hosts:
            r = self.discover(host, port)
            if r.ok:
                found.append(r.data)
        return Result.success(found, f"Found {len(found)} servers")

    def get_server_info(self, server: RemoteServerInfo) -> Result:
        return Result.success({
            "alias": server.alias,
            "server_device_id": server.server_device_id,
            "requires_pairing": server.requires_pairing,
            "roles": server.roles,
            "features": server.features,
        })

    def test_connection(self, server: RemoteServerInfo) -> Result:
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/ping",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    return Result.success({"latency_ms": 0}, "Connection OK")
        except Exception as e:
            return Result.fail("CONNECTION_FAILED", str(e))
        return Result.fail("CONNECTION_FAILED", "Unexpected response")

    def get_capabilities(self, server: RemoteServerInfo) -> Result:
        return Result.success({
            "host": server.host,
            "port": server.port,
            "alias": server.alias,
            "has_token": bool(server.device_token),
            "roles": server.roles,
            "features": server.features,
        })

    def pair(self, server: RemoteServerInfo, username: str = "",
             password: str = "") -> Result:
        ok = self._client.pair(server, username=username, password=password)
        if not ok:
            return Result.fail("PAIR_FAILED", "Pairing rejected by server")
        return Result.success({
            "device_id": server.device_id,
            "device_token_prefix": server.device_token[:8] + "...",
        }, "Paired successfully")

    def pair_start(self, server: RemoteServerInfo) -> Result:
        import secrets
        body = json.dumps({
            "client_device_id": f"player_{secrets.token_hex(4)}",
            "alias": "Michi Music Player",
            "device_model": "desktop",
            "client_version": "1.0",
        }).encode()
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/pair/start",
                data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            return Result.success(data, "pair/start succeeded")
        except Exception as e:
            return Result.fail("PAIR_START_FAILED", str(e))

    def pair_confirm(self, server: RemoteServerInfo, username: str = "",
                     password: str = "") -> Result:
        return self.pair(server, username=username, password=password)

    def get_tracks(self, server: RemoteServerInfo) -> Result:
        tracks = self._client.get_library(server)
        if tracks is None:
            return Result.fail("LIBRARY_FAILED", "Cannot fetch library")
        return Result.success(tracks, f"{len(tracks)} tracks")

    def get_library_stats(self, server: RemoteServerInfo) -> Result:
        stats = self._client._get(server, "/api/v1/library/stats")
        if stats is None:
            return Result.fail("STATS_FAILED", "Cannot fetch library stats")
        return Result.success(stats)

    def search(self, server: RemoteServerInfo, query: str) -> Result:
        results = self._client.search(server, query)
        if results is None:
            return Result.fail("SEARCH_FAILED", "Search request failed")
        return Result.success(results, f"{len(results)} results")

    def get_playback_state(self, server: RemoteServerInfo) -> Result:
        state = self._client.get_playback_state(server)
        if state is None:
            return Result.fail("STATE_FAILED", "Cannot fetch playback state")
        return Result.success(state)

    def get_queue(self, server: RemoteServerInfo) -> Result:
        queue = self._client.get_queue(server)
        if queue is None:
            return Result.fail("QUEUE_FAILED", "Cannot fetch queue")
        return Result.success(queue)

    def control(self, server: RemoteServerInfo, command: str,
                **kwargs) -> Result:
        ok = self._client.control(server, command, **kwargs)
        if not ok:
            return Result.fail("CONTROL_FAILED", f"Command '{command}' failed")
        return Result.success({"command": command}, f"Command '{command}' executed")
