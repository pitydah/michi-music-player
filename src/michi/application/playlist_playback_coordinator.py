"""Playlist playback intent coordinator (M4-R1 → M6-EXT-R4 freeze gate).

Coordinates PlaylistService + PlaybackSessionService + QueueService. NO
state authority. PLAY and QUEUE are DISTINCT user intents:
- PLAY: playlist snapshot → PlaybackSession (PLAYLIST context).
- QUEUE: playlist tracks → QueueService (explicit Queue mutation).

M6-EXT-R4 freeze gate: membership resolves through ``LibraryTrackResolver``
by stable TrackId FIRST — the current resolved path is used; the persisted
fallback path is used ONLY when the identity is unresolved/legacy. A moved
file therefore plays from its NEW location while the playlist membership
(and its TrackId) never changes.
"""

import logging
from pathlib import Path

from michi.application.library_track_resolver import LibraryTrackResolver
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
        resolver: LibraryTrackResolver | None = None,
    ) -> None:
        self._playlists = playlist_service
        self._session = playback_session
        self._queue = queue_service
        self._resolver = resolver

    def _resolve_entries(self, playlist_id: str) -> list[PlaybackSequenceEntry]:
        """Resolve membership: TrackId → current resolved path; fallback
        path only when the identity is unresolved/legacy. Unavailable
        tracks keep their membership (never silently removed)."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            return []
        entries: list[PlaybackSequenceEntry] = []
        for ref in playlist.references():
            resolved_path: Path | None = None
            if ref.track_id:
                # Known identity: the CURRENT playable path decides. An
                # unavailable/unresolved identity is SKIPPED (membership
                # stays intact) — never a fallback that plays a missing
                # file.
                if self._resolver is not None:
                    resolved_path = self._resolver.resolve_playable_path(ref.track_id)
                if resolved_path is None:
                    continue
            else:
                # LEGACY/unresolved record: the location snapshot is the
                # honest projection.
                resolved_path = Path(ref.fallback_path) if ref.fallback_path else None
            if resolved_path is None:
                continue
            entries.append(
                PlaybackSequenceEntry(
                    file_path=resolved_path,
                    title="",
                    library_track_id=ref.track_id or None,
                )
            )
        return entries

    def play_playlist(self, playlist_id: str, start_index: int = 0) -> None:
        """PLAYLIST snapshot context (never copies into Queue). The snapshot
        is taken at intent time: later persistent edits do not rewrite the
        running session; a future Play uses the updated playlist."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        entries = self._resolve_entries(playlist_id)
        if not entries:
            return
        if not (0 <= start_index < len(entries)):
            start_index = 0
        self._session.play_context(
            PlaybackContextType.PLAYLIST, playlist_id, entries, start_index
        )

    def play_playlist_track(self, playlist_id: str, index: int) -> None:
        """Playlist Detail track click → PLAYLIST context (P1-04).

        ``index`` is the PLAYLIST MEMBERSHIP index. The resolved playback
        sequence may be SHORTER (unavailable members are filtered out), so
        the membership index is mapped to the playback entry BY IDENTITY —
        never by accidental positional coincidence. An unavailable selected
        member produces an explicit no-play (nothing else starts)."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        refs = playlist.references()
        if not (0 <= index < len(refs)):
            return
        selected = refs[index]
        entries = self._resolve_entries(playlist_id)
        if not entries:
            return
        entry_index = self._entry_index_for(selected, entries)
        if entry_index is None:
            # Explicit no-play for an unavailable member: never a silent
            # substitution of another track.
            logger.info(
                "playlist member %s (index %d) is unavailable; no playback",
                selected.track_id or selected.fallback_path,
                index,
            )
            return
        self._session.play_context(
            PlaybackContextType.PLAYLIST, playlist_id, entries, entry_index
        )

    @staticmethod
    def _entry_index_for(selected, entries) -> int | None:
        """Membership reference → playback entry index by IDENTITY.

        Stable TrackId equality wins when both sides carry it; the path is
        the fallback ONLY for legacy/path-only members."""
        for position, entry in enumerate(entries):
            if selected.track_id and entry.library_track_id:
                if selected.track_id == entry.library_track_id:
                    return position
            elif (
                not selected.track_id
                and selected.fallback_path
                and str(entry.file_path) == selected.fallback_path
            ):
                return position
        return None

    def queue_playlist(self, playlist_id: str) -> None:
        """EXPLICIT Queue intent: append playlist tracks to the Queue.
        Never commands playback. Entries carry the stable identity."""
        playlist = self._playlists.get_playlist(playlist_id)
        if playlist is None:
            logger.warning("playlist no encontrada: %s", playlist_id)
            return
        entries = self._resolve_entries(playlist_id)
        if entries:
            self._queue.add_many_entries(
                [(entry.file_path, entry.library_track_id) for entry in entries]
            )
