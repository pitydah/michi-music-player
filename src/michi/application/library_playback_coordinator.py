"""Library playback intent coordinator (M4-R1).

Coordinates LibraryService + PlaybackSessionService. NO state authority —
it only translates LIBRARY USER INTENTS into session requests. Generic
track clicks are SINGLE; Album Detail track clicks are ALBUM context at the
clicked index; artist tracks are SINGLE (no ARTIST context yet).
"""

import logging
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_session_service import PlaybackSessionService
from michi.domain.playback_session import (
    PlaybackContextType,
    PlaybackSequenceEntry,
)

logger = logging.getLogger(__name__)


class LibraryPlaybackCoordinator:
    """Library → PlaybackSession intent seam. No Queue dependency."""

    def __init__(
        self,
        library_service: LibraryService,
        playback_session: PlaybackSessionService,
    ) -> None:
        self._library = library_service
        self._session = playback_session

    def play_track(self, file_path: Path, title: str = "") -> None:
        """Generic track intent → SINGLE (never mutates Queue).

        TD-013 (M4-R1 final seal): every Library-origin playback intent
        resolves the TrackRef and validates the filesystem through the
        LibraryService gate BEFORE requesting the session. A missing track
        removes the exact stale reference / sets the diagnostic; ACCESS/IO/
        UNKNOWN preserve the reference. No validation → no playback request.
        """
        ref = self._library.resolve_trackref(file_path)
        if ref is None:
            return  # not a library track: no playback request
        if not self._library.validate_track_for_playback(ref):
            return
        entry = PlaybackSequenceEntry(file_path=ref.file_path, title=ref.title or title)
        self._session.play_single(entry)

    def play_album(self, album_key: str, start_index: int = 0) -> None:
        """Album context from the canonical AlbumRef ordering (M6 owns the
        order — the coordinator never re-sorts). TD-013 filesystem
        validation stays LibraryService-owned: a missing track removes the
        exact reference BEFORE any playback request."""
        album = self._library.album_by_key(album_key)
        if album is None:
            logger.warning("album no encontrado: %s", album_key)
            return
        entries = [
            PlaybackSequenceEntry(file_path=Path(path), title="")
            for path in album.track_paths
        ]
        if not entries:
            return
        if not (0 <= start_index < len(entries)):
            start_index = 0
        # TD-013: validate the clicked track through the library filesystem
        # gate (removes stale references / sets diagnostics).
        clicked = entries[start_index]
        ref = self._library.resolve_trackref(clicked.file_path)
        if ref is None or not self._library.validate_track_for_playback(ref):
            return
        self._session.play_context(
            PlaybackContextType.ALBUM, album_key, entries, start_index
        )

    def play_album_track(self, album_key: str, index: int) -> None:
        """Album Detail track click → ALBUM context at the clicked index
        (NOT SINGLE)."""
        self.play_album(album_key, start_index=index)

    def play_artist_track_as_single(self, file_path: Path, title: str = "") -> None:
        """Artist track click → SINGLE (no ARTIST context yet).

        Delegates to the same validated play_track path — TD-013 applies."""
        self.play_track(file_path, title=title)

    def play_visible_track(self, index: int) -> None:
        """Generic visible-list track click → SINGLE.

        P2-02 final seal: ONE validation gate. This method only resolves
        the visible TrackRef and delegates to play_track, which performs
        the canonical resolve + single TD-013 validation — never twice."""
        tracks = self._library.visible_tracks()
        if not (0 <= index < len(tracks)):
            return
        track = tracks[index]
        self.play_track(track.file_path, title=track.title or "")
