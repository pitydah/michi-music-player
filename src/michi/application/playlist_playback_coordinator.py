"""Playlist playback intent coordinator (M4-R1).

Coordinates PlaylistService + PlaybackSessionService + QueueService. NO
state authority. PLAY and QUEUE are DISTINCT user intents:
- PLAY: playlist snapshot → PlaybackSession (PLAYLIST context).
- QUEUE: playlist tracks → QueueService.add_many (explicit Queue mutation).
"""

import logging
from pathlib import Path

from michi.application.playback_session_service import PlaybackSessionService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.playback_session import (
    PlaybackContextType,
    PlaybackSequenceEntry,
)

logger = logging.getLogger(__name__)


class PlaylistPlaybackCoordinator:
    """Playlist → PlaybackSession / Queue intent seam."""

    def __init__(
        self,
        playlist_service: PlaylistService,
        playback_session: PlaybackSessionService,
        queue_service: QueueService,
    ) -> None:
        self._playlists = playlist_service
        self._session = playback_session
        self._queue = queue_service

    def play_playlist(self, playlist_id: str, start_index: int = 0) -> None:
        """PLAYLIST snapshot context (never copies into Queue). The snapshot
        is taken at intent time: later persistent edits do not rewrite the
        running session; a future Play uses the updated playlist."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        entries = [
            PlaybackSequenceEntry(file_path=Path(path), title="")
            for path in playlist.track_paths
        ]
        if not entries:
            return
        if not (0 <= start_index < len(entries)):
            start_index = 0
        self._session.play_context(
            PlaybackContextType.PLAYLIST, playlist_id, entries, start_index
        )

    def play_playlist_track(self, playlist_id: str, index: int) -> None:
        """Playlist Detail track click → PLAYLIST context at the clicked
        index (NOT SINGLE, NOT Queue)."""
        self.play_playlist(playlist_id, start_index=index)

    def queue_playlist(self, playlist_id: str) -> None:
        """EXPLICIT Queue intent: append playlist tracks to the Queue.
        Never commands playback."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        self._queue.add_many([Path(path) for path in playlist.track_paths])
