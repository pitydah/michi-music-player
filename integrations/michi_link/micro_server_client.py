"""Michi Micro Server client — Player as client to a remote Micro Server.

Phase 2 (next): Player discovers, pairs, and reads library from Micro Server.
Phase 3 (future): Player sends tracks/playlists to Micro Server for playback.
This module is a stub ready for Phase 2. Do not connect to UI yet.
"""
from __future__ import annotations

import json
import logging

from integrations.michi_link.client import MichiLinkClient, RemoteServerInfo

logger = logging.getLogger("michi.link.micro_client")


class MicroServerClient:
    """Client for discovering, pairing, and consuming a Michi Micro Server."""

    def __init__(self):
        self._client = MichiLinkClient()
        self._servers: dict[str, RemoteServerInfo] = {}

    def get_server_info(self, host: str, port: int = 53318) -> RemoteServerInfo | None:
        return self._client.discover(host, port)

    def pair_start(self, server: RemoteServerInfo) -> dict | None:
        import secrets as _secrets
        body = json.dumps({
            "client_device_id": f"player_{_secrets.token_hex(4)}",
            "alias": "Michi Music Player",
            "device_model": "desktop",
            "client_version": "1.0",
        }).encode()
        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://{server.host}:{server.port}/api/v1/pair/start",
                data=body, method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            logger.warning("pair_start failed: %s", e)
            return None

    def pair_confirm(self, server: RemoteServerInfo, username: str = "",
                     password: str = "") -> bool:
        return self._client.pair(server, username=username, password=password)

    def get_tracks(self, server: RemoteServerInfo) -> list[dict] | None:
        return self._client.get_library(server)

    def get_library_stats(self, server: RemoteServerInfo) -> dict | None:
        return self._client._get(server, "/api/v1/library/stats")

    def create_import_session(self, server: RemoteServerInfo) -> dict | None:
        logger.info("create_import_session: DEFERRED_PHYSICAL")
        return None

    def upload_track(self, server: RemoteServerInfo, track_id: str) -> bool:
        logger.info("upload_track: DEFERRED_PHYSICAL — requires Michi Micro Server")
        return False

    def commit_import(self, server: RemoteServerInfo) -> bool:
        logger.info("commit_import: DEFERRED_PHYSICAL")
        return False

    def playback_session_continue_on_server(self, server: RemoteServerInfo,
                                            track_ids: list[str]) -> bool:
        logger.info("playback_session_continue_on_server: DEFERRED_PHYSICAL")
        return False
