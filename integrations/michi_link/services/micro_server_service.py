"""MicroServerService — manages Player ↔ Micro Server interactions.

Full lifecycle: discover, pair, test_connection, read library, stats, search.
Returns Result objects — never raises to caller.
"""
from __future__ import annotations

import json
import logging
import urllib.error
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
        import time
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/status",
                method="GET",
            )
            start = time.time()
            with urllib.request.urlopen(req, timeout=5) as r:
                elapsed_ms = round((time.time() - start) * 1000, 1)
                if r.status == 200:
                    return Result.success({"latency_ms": elapsed_ms}, "Connection OK")
        except urllib.error.URLError as e:
            return Result.fail("CONNECTION_FAILED", f"Cannot reach server: {e.reason}")
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

    def get_playlists(self, server: RemoteServerInfo) -> Result:
        """Fetch playlists from the remote server (real readback).

        Returns ``Result`` with ``data={"playlists": [...], "total": N}`` on
        success; a remote that is unreachable or lacks the endpoint fails
        explicitly (never an empty success list).
        """
        import json
        import urllib.error
        import urllib.request

        headers = {"Content-Type": "application/json"}
        if server.device_token:
            headers["Authorization"] = f"Bearer {server.device_token}"
            headers["X-Michi-Device-Id"] = server.device_id
        try:
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/playlists",
                method="GET", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return Result.fail("PLAYLISTS_ENDPOINT_MISSING",
                                   "Server does not expose /api/v1/playlists")
            return Result.fail("PLAYLISTS_FAILED", f"HTTP {e.code}: {e.reason}")
        except Exception as e:
            return Result.fail("REMOTE_UNAVAILABLE",
                               f"Cannot fetch playlists: {e}")
        playlists = data.get("playlists", []) if isinstance(data, dict) else []
        return Result.success({
            "playlists": playlists,
            "total": len(playlists),
        }, f"{len(playlists)} playlists")

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

    def create_import_session(self, server: RemoteServerInfo) -> Result:
        """Tell Micro Server to prepare for receiving tracks (pull model)."""
        body = json.dumps({"source": "michi-music-player"}).encode()
        try:
            headers = {"Content-Type": "application/json"}
            if server.device_token:
                headers["Authorization"] = f"Bearer {server.device_token}"
                headers["X-Michi-Device-Id"] = server.device_id
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/import/session/create",
                data=body, method="POST", headers=headers,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                resp = json.loads(r.read().decode())
            return Result.success(resp, "Import session created on Micro Server")
        except Exception as e:
            return Result.fail("IMPORT_SESSION_FAILED", str(e))
