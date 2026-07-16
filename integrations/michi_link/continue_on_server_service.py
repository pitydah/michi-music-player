"""Continue on server service — contractual stub for handoff to Micro Server."""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo

logger = logging.getLogger("michi.link.continue_on_server")


class ContinueOnServerService:
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
