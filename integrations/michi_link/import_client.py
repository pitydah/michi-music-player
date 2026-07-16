"""Michi import client — contractual stub. Requires network server hardware."""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo

logger = logging.getLogger("michi.link.import_client")


class ImportClient:
    def __init__(self, server: RemoteServerInfo | None = None):
        self._server = server

    def fetch_tracks(self) -> list[dict]:
        logger.info("fetch_tracks: DEFERRED_PHYSICAL — requires Michi Micro Server")
        return []

    def fetch_playlists(self) -> list[dict]:
        logger.info("fetch_playlists: DEFERRED_PHYSICAL")
        return []

    def import_to_local(self, tracks: list[dict]) -> int:
        logger.info("import_to_local: DEFERRED_PHYSICAL")
        return 0
