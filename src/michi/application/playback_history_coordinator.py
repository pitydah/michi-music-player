"""Playback history coordinator (M4-R1 → M6-EXT-R4-J).

History is PLAYBACK-COMMIT DRIVEN: a History entry is recorded only when a
NEW playback request is ACCEPTED by the backend (PlaybackSessionService
track_committed / entry_committed events). Queue mutations and startup
session restore NEVER record History.

M6-EXT-R4-J: the rich ``entry_committed`` event carries the stable
``library_track_id``; History keys by TrackId when the track belongs to the
Library. Non-library tracks fall back to the legacy path surface; a
Library track whose id cannot be resolved records nothing (no invented
identity).
"""

import logging
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.playback_session_service import PlaybackSessionService
from michi.domain.playback_session import PlaybackSequenceEntry

logger = logging.getLogger(__name__)


class PlaybackHistoryCoordinator:
    """Session commit → Library history seam. No Queue dependency."""

    def __init__(
        self,
        playback_session: PlaybackSessionService,
        library_service: LibraryService,
        resolver: LibraryTrackResolver | None = None,
    ) -> None:
        self._session = playback_session
        self._library = library_service
        self._resolver = resolver or LibraryTrackResolver(library_service)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._session.subscribe_track_committed(self._on_committed)
        self._session.subscribe_entry_committed(self._on_entry_committed)

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._session.unsubscribe_track_committed(self._on_committed)
        self._session.unsubscribe_entry_committed(self._on_entry_committed)

    def _on_committed(self, path: Path) -> None:
        """LEGACY event surface — keep recording path history verbatim.

        The rich entry event ALSO fires on the same commit; consecutive
        dedupe makes the double write a single history entry. This handler
        guarantees path-only session implementations keep working."""
        self._library.record_history(path)

    def _on_entry_committed(self, entry: PlaybackSequenceEntry) -> None:
        """CANONICAL history path: stable TrackId first, resolved path
        fallback second, honest nothing for unknown library identity."""
        if entry.library_track_id:
            self._library.record_history_for_track(entry.library_track_id)
            return
        track_id = self._resolver.find_track_id_by_path(entry.file_path)
        if track_id is None:
            # Not a Library track: legacy path surface only.
            self._library.record_history(entry.file_path)
            return
        self._library.record_history_for_track(track_id)
