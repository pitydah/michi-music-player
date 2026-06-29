"""Remote library provider — future integration with Michi Micro Server.

Phase 2: Player reads library from a remote Micro Server and displays it
as a browsable source alongside the local library.

This module is a stub. Do not connect to UI yet.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.link.remote_library")


class RemoteLibraryProvider:
    """Provides library data from a remote Michi Micro Server.

    Usage (future):
        provider = RemoteLibraryProvider(server_info)
        tracks = provider.get_tracks()
        results = provider.search("artist:Genesis")
    """
    def __init__(self):
        pass
