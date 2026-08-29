"""Library playback intent coordinator (M4-R1).

Coordinates LibraryService + PlaybackSessionService. NO state authority —
it only translates LIBRARY USER INTENTS into session requests. Generic
track clicks are SINGLE; Album Detail track clicks are ALBUM context at the
clicked index; artist tracks are SINGLE (no ARTIST context yet).
"""

import logging
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
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
        resolver: "LibraryTrackResolver | None" = None,
    ) -> None:
        self._library = library_service
        self._session = playback_session
        self._resolver = resolver or LibraryTrackResolver(library_service)

    def play_track(self, file_path: Path, title: str = "") -> None:
        """LEGACY path intent → SINGLE (never mutates Queue).

        New callers prefer ``play_track_by_id`` (M6-EXT-R4-J canonical
        intent). TD-013 (M4-R1 final seal): every Library-origin playback
        intent resolves the TrackRef and validates the filesystem through
        the LibraryService gate BEFORE requesting the session. A missing
        track removes the exact stale reference / sets the diagnostic;
        ACCESS/IO/UNKNOWN preserve the reference. No validation → no
        playback request.
        """
        ref = self._library.resolve_trackref(file_path)
        if ref is None:
            return  # not a library track: no playback request
        self.play_track_by_id(
            ref.track_id or f"legacy-path::{ref.file_path}", title=title
        )

    def play_track_by_id(self, track_id: str, title: str = "") -> None:
        """CANONICAL intent (M6-EXT-R4-J): play a stable TrackId.

        The current path is resolved from the catalog projection; the
        sequence entry carries the stable library identity so History and
        session V3 never depend on the filesystem location."""
        ref = self._resolver.resolve_ref(track_id)
        if ref is None:
            return
        if not self._library.validate_track_for_playback(ref):
            return
        entry = PlaybackSequenceEntry(
            file_path=ref.file_path,
            title=ref.title or title,
            library_track_id=ref.track_id or None,
        )
        self._session.play_single(entry)

    def play_album(self, album_key: str, start_index: int = 0) -> None:
        """Album context from the canonical AlbumRef ordering (M6 owns the
        order — the coordinator never re-sorts). CORRECTIVE SEAL §14:
        modern membership resolves from TrackIds through the resolver
        (current resolved paths; identity on every entry); the legacy path
        projection is the explicit pre-migration fallback. Unavailable
        members are skipped without removal — membership stays intact."""
        album = self._library.album_by_key(album_key)
        if album is None:
            logger.warning("album no encontrado: %s", album_key)
            return
        entries, selected_entry_index = self._resolve_album_entries(album, start_index)
        if not entries or selected_entry_index is None:
            # The clicked member is unavailable: truthful no-play — never a
            # silent neighbor substitution (P1-08).
            return
        # TD-013: validate the SELECTED track through the library filesystem
        # gate (never removes identity — availability is marked instead).
        selected = entries[selected_entry_index]
        ref = None
        if selected.library_track_id:
            ref = self._resolver.resolve_ref(selected.library_track_id)
        if ref is None:
            # Legacy path-only entry: validate through the path projection.
            ref = self._library.resolve_trackref(selected.file_path)
        if ref is None or not self._library.validate_track_for_playback(ref):
            return
        self._session.play_context(
            PlaybackContextType.ALBUM,
            album_key,
            entries,
            selected_entry_index,
        )

    def _resolve_album_entries(self, album, requested_index: int):
        """P1-08: membership index → playback entry index BY IDENTITY.

        Modern membership (track_ids) resolves through the resolver; every
        unavailable/unresolved member is SKIPPED (membership intact) while
        the requested membership index maps to the resolved entry position.
        A requested unavailable member yields ``selected_entry_index=None``
        (no playback). Legacy albums fall back to track_paths with the
        historical index semantics."""
        if album.track_ids:
            membership_ids = album.track_ids
            if not (0 <= requested_index < len(membership_ids)):
                return [], None
            entries = []
            selected_entry_index = None
            for membership_index, track_id in enumerate(membership_ids):
                ref = self._resolver.resolve_ref(track_id)
                if ref is None:
                    continue  # identity unresolved: membership stays intact
                playable_path = self._resolver.resolve_playable_path(track_id)
                if playable_path is None:
                    continue  # unavailable: filtered, not removed
                if membership_index == requested_index:
                    selected_entry_index = len(entries)
                entries.append(
                    PlaybackSequenceEntry(
                        file_path=playable_path,
                        title=ref.title,
                        library_track_id=ref.track_id or None,
                    )
                )
            return entries, selected_entry_index
        # LEGACY pre-migration album: path projection with index semantics.
        entries = []
        for path in album.track_paths:
            ref = self._library.resolve_trackref(path)
            entries.append(
                PlaybackSequenceEntry(
                    file_path=Path(path),
                    title=ref.title if ref is not None else "",
                    library_track_id=ref.track_id if ref is not None else None,
                )
            )
        if not (0 <= requested_index < len(entries)):
            requested_index = 0
        return entries, requested_index

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
