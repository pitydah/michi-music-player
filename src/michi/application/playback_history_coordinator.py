"""Playback history coordinator (M4-R1).

History is PLAYBACK-COMMIT DRIVEN: a History entry is recorded only when a
NEW playback request is ACCEPTED by the backend (PlaybackSessionService
track_committed event). Queue mutations and startup session restore NEVER
record History.
"""

import logging
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_session_service import PlaybackSessionService

logger = logging.getLogger(__name__)


class PlaybackHistoryCoordinator:
    """Session commit → Library history seam. No Queue dependency."""

    def __init__(
        self,
        playback_session: PlaybackSessionService,
        library_service: LibraryService,
    ) -> None:
        self._session = playback_session
        self._library = library_service
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._session.subscribe_track_committed(self._on_committed)

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._session.unsubscribe_track_committed(self._on_committed)

    def _on_committed(self, path: Path) -> None:
        self._library.record_history(path)
