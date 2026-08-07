# LEGACY: deprecated variant — see ADR-002 single domain authority
"""LEGACY: Michi import client — contractual stub. Requires network server hardware.

Deprecated by ADR-002 (single domain authority): the canonical
``integrations/michi_link/services/import_to_server_service.py`` (advanced
stack, Result-based) is the productive implementation. Never registered in
the composition.
"""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo

logger = logging.getLogger("michi.link.import_client")


class ImportClient:
    """LEGACY ImportClient (deprecated stub) — use
    ``integrations.michi_link.services.ImportToServerService`` instead.

    Deprecated since Slice 7 (ADR-002 single domain authority).
    """

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
