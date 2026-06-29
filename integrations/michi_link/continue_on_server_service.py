"""Continue on server service — future: handoff playback queue to Micro Server.

Phase 3: Player sends its current playback queue to a paired Micro Server so
the server continues playing where the Player left off. This is a stub.

Do not connect to UI yet.
"""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo

logger = logging.getLogger("michi.link.continue_on_server")


class ContinueOnServerService:
    """Service for handing off playback to a remote Micro Server.

    Usage (Phase 3):
        service = ContinueOnServerService()
        service.transfer_queue(server, current_queue, position_ms)
        service.start_remote_playback(server)
    """
    def __init__(self):
        pass

    def transfer_queue(self, server: RemoteServerInfo, track_ids: list[str],
                       position_ms: float = 0.0) -> bool:
        """Transfer the current queue to a Micro Server for continued playback."""
        logger.info("transfer_queue stub — not yet implemented")
        return False

    def start_remote_playback(self, server: RemoteServerInfo) -> bool:
        """Tell the Micro Server to start playing the transferred queue."""
        logger.info("start_remote_playback stub — not yet implemented")
        return False

    def stop_remote_playback(self, server: RemoteServerInfo) -> bool:
        """Tell the Micro Server to stop playing."""
        logger.info("stop_remote_playback stub — not yet implemented")
        return False
