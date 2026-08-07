# LEGACY: deprecated variant — see ADR-002 single domain authority
"""LEGACY: Continue on server service — contractual stub for handoff to Micro Server.

Deprecated by ADR-002 (single domain authority): the canonical
``integrations/michi_link/services/continue_on_server_service.py`` (advanced
stack, Result-based) is the productive implementation. This stub is dead code
(imported nowhere) and is kept only to document the designation.
"""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo

logger = logging.getLogger("michi.link.continue_on_server")


class ContinueOnServerService:
    """LEGACY ContinueOnServerService (deprecated stub) — use
    ``integrations.michi_link.services.ContinueOnServerService`` instead.

    Deprecated since Slice 7 (ADR-002 single domain authority).
    """

    def __init__(self):
        pass

    def transfer_queue(self, server: RemoteServerInfo, track_ids: list[str],
                       position_ms: float = 0.0) -> bool:
        logger.info("transfer_queue: DEFERRED_PHYSICAL — requires Michi Micro Server")
        return False

    def start_remote_playback(self, server: RemoteServerInfo) -> bool:
        logger.info("start_remote_playback: DEFERRED_PHYSICAL")
        return False

    def stop_remote_playback(self, server: RemoteServerInfo) -> bool:
        logger.info("stop_remote_playback: DEFERRED_PHYSICAL")
        return False
