"""Michi Micro Server client — future integration.

Michi Music Player can act as client to a Michi Micro Server (lightweight
headless server running on Raspberry Pi, NAS, etc.).

Phase 1 (current): Player acts as server.
Phase 2 (next): Player discovers and pairs with Micro Server.
Phase 3 (future): Player sends music to Micro Server for playback.

This module is a stub for Phase 2. Do not connect to UI yet.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.link.micro_client")


class MicroServerClient:
    """Client for discovering, pairing, and consuming a Michi Micro Server.

    Usage (future):
        client = MicroServerClient()
        info = client.discover("192.168.1.100")
        client.pair(info, username="admin", password="...")
        tracks = client.get_library(info)
        client.send_tracks(info, track_ids)
    """
    def __init__(self):
        pass
