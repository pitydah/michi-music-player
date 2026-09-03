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
        running session; a future Play uses the updated playlist.

        PL-FINAL-A05: callers MUST pass an already availability-filtered
        path list through play_playlist_paths; this legacy entry point
        keeps the raw snapshot for compatibility callers."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        self.play_playlist_paths(playlist_id, list(playlist.track_paths), start_index)

    def play_playlist_paths(
        self,
        playlist_id: str,
        available_paths: list[str],
        start_index: int = 0,
    ) -> None:
        """PL-FINAL-A05: PLAYLIST snapshot over the AVAILABLE subset only.
        The presentation layer resolves availability (library truth); the
        coordinator never guesses it. Never sends missing paths to the
        engine; a future Play uses the updated playlist."""
        entries = [
            PlaybackSequenceEntry(file_path=Path(path), title="")
            for path in available_paths
        ]
        self.play_playlist_entries(playlist_id, entries, start_index)

    def play_playlist_entries(
        self,
        playlist_id: str,
        entries: list[PlaybackSequenceEntry],
        start_index: int = 0,
    ) -> None:
        """PLAYLIST snapshot over RESOLVED sequence entries (identity
        recovery, Iteración 2): every entry carries its CURRENT factual
        path plus the stable ``library_track_id`` when the library knows
        it — relocation-safe playback (the library resolves TrackId →
        current TrackRef → current path at intent time)."""
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
        Never commands playback. PL-FINAL-A05: la presentación pasa la
        lista ya filtrada por disponibilidad vía queue_playlist_paths."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        self.queue_playlist_paths(playlist_id, list(playlist.track_paths))

    def queue_playlist_paths(
        self, playlist_id: str, available_paths: list[str]
    ) -> None:
        """PL-FINAL-A05: EXPLICIT Queue intent over the AVAILABLE subset."""
        if not available_paths:
            return
        self._queue.add_many([Path(path) for path in available_paths])

    def queue_playlist_entries(
        self,
        playlist_id: str,
        path_id_pairs: list[tuple[Path, str | None]],
    ) -> None:
        """EXPLICIT Queue intent carrying (current path, stable TrackId)
        pairs (identity recovery, Iteración 2): Queue content stays
        temporary but each entry preserves its library identity for
        history/session consumers. El path se resuelve a la ubicación
        ACTUAL al insertar (el caller resuelve; no hay re-resolución
        tardía en Queue/Session — late relocation es deuda separada).
        Uses QueueService.add_many_entries (one batch notification)."""
        del playlist_id
        if not path_id_pairs:
            return
        self._queue.add_many_entries(path_id_pairs)
