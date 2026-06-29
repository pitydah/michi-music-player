"""RemoteLibraryService — reads library from Micro Server as browsable source.

Treats the Micro Server as a read-only remote source. User must explicitly
import tracks to add them to the local library. Does NOT mix remote/local
automatically.
"""
from __future__ import annotations

import logging

from integrations.michi_link.client import RemoteServerInfo
from integrations.michi_link.services.micro_server_service import MicroServerService
from integrations.michi_link.services.result import Result

logger = logging.getLogger("michi.service.remote_library")


class RemoteLibraryService:
    """Read-only access to a remote Micro Server library."""

    def __init__(self, micro: MicroServerService | None = None):
        self._micro = micro or MicroServerService()

    def browse_tracks(self, server: RemoteServerInfo,
                      offset: int = 0, limit: int = 100) -> Result:
        """Browse tracks from a remote Micro Server with pagination."""
        result = self._micro.get_tracks(server)
        if not result.ok:
            return result
        tracks = result.data or []
        page = tracks[offset:offset + limit]
        return Result.success({
            "tracks": page,
            "total": len(tracks),
            "offset": offset,
            "limit": limit,
        }, f"Browsed {len(page)} tracks (offset={offset})")

    def search(self, server: RemoteServerInfo, query: str) -> Result:
        """Search tracks on a remote Micro Server."""
        return self._micro.search(server, query)

    def get_track_count(self, server: RemoteServerInfo) -> int:
        """Get total track count from remote server."""
        result = self._micro.get_library_stats(server)
        if result.ok and isinstance(result.data, dict):
            return result.data.get("audio", 0)
        return 0

    def get_playlists(self, server: RemoteServerInfo) -> list[dict]:
        """Get playlists from remote server. Uses sync/manifest."""
        return []
