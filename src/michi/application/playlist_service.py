"""PlaylistService — user-defined playlists (LOCAL-06 → M8-R1).

M8-R1 canonical rules:
- playlist_id is the canonical identity; name is display-only metadata.
- All core mutations are identity-based (name NEVER canonical identity).
- create_playlist returns the created Playlist (identity immediately
  available to callers without a second lookup).
- Delete prunes navigation metadata (pinned/recent) via on_playlist_deleted.

Temporary compatibility wrappers (name-based, DEPRECATED) exist only while
presentation migrates to ids; they delegate name → id and must not be used
by new code.
"""

import logging
from collections.abc import Callable
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.application.queue_service import QueueService
from michi.domain.playlist import (
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistNavigationState,
    new_playlist_id,
    normalize_navigation_state,
)

logger = logging.getLogger(__name__)


class PlaylistService:
    """Owns the ordered playlist collection and its navigation metadata
    (pinned/recent); mutates, persists (best effort) and notifies. Playback
    goes through the queue (queue direction only)."""

    def __init__(
        self,
        queue_service: QueueService,
        playlists_port: PlaylistsPort | None = None,
    ) -> None:
        self._queue = queue_service
        self._port = playlists_port
        self._playlists: list[Playlist] = list(
            playlists_port.load() if playlists_port is not None else ()
        )
        # M8-R1F: SAFE READ normalization — reconcile persisted pinned/recent
        # against the actual collection (stale ids pruned, duplicates
        # first-wins, recent bounded). NO writeback during load: disk may
        # keep stale payloads until the next legitimate navigation mutation.
        loaded_nav = (
            playlists_port.load_navigation()
            if playlists_port is not None
            else PlaylistNavigationState()
        )
        self._nav = normalize_navigation_state(
            loaded_nav, tuple(p.playlist_id for p in self._playlists)
        )
        self._subscribers: list[Callable[[], None]] = []
        self._on_playlist_deleted: Callable[[str], None] | None = None

    @property
    def playlists(self) -> tuple[Playlist, ...]:
        return tuple(self._playlists)

    @property
    def navigation(self) -> PlaylistNavigationState:
        return self._nav

    def set_on_playlist_deleted(self, callback: Callable[[str], None] | None) -> None:
        """Application-level hook invoked AFTER a playlist is removed (with
        its id), so navigation/selection state can converge. Not a
        subscriber — no notification semantics."""
        self._on_playlist_deleted = callback

    def subscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe_changed(self, callback: Callable[[], None]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify(self) -> None:
        for cb in list(self._subscribers):
            cb()

    def _persist(self) -> None:
        if self._port is not None:
            self._port.save(tuple(self._playlists))

    def _persist_nav(self) -> None:
        if self._port is not None:
            self._port.save_navigation(self._nav)

    def _find_by_id(self, playlist_id: str) -> int:
        for i, playlist in enumerate(self._playlists):
            if playlist.playlist_id == playlist_id:
                return i
        return -1

    def get_playlist(self, playlist_id: str) -> Playlist | None:
        """Public query: returns the playlist for a valid id, None for an
        unknown id. No mutation, no notification, no persistence."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return None
        return self._playlists[index]

    def contains_playlist(self, playlist_id: str) -> bool:
        return self._find_by_id(playlist_id) >= 0

    # ------------------------------------------------------------------
    # Identity-based public API (canonical)
    # ------------------------------------------------------------------

    def create_playlist(self, name: str) -> Playlist:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        playlist = Playlist(playlist_id=new_playlist_id(), name=cleaned)
        self._playlists.append(playlist)
        self._persist()
        self._notify()
        return playlist

    def delete_playlist(self, playlist_id: str) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        del self._playlists[index]
        # Prune navigation metadata (never dangling ids).
        self._nav = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=tuple(i for i in self._nav.recent_ids if i != playlist_id),
        )
        self._persist()
        self._persist_nav()
        if self._on_playlist_deleted is not None:
            self._on_playlist_deleted(playlist_id)
        self._notify()

    def rename_playlist(self, playlist_id: str, new_name: str) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        cleaned = new_name.strip()
        if not cleaned:
            raise ValueError("playlist name must not be empty")
        if any(
            p.name == cleaned and p.playlist_id != playlist_id for p in self._playlists
        ):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        playlist = self._playlists[index]
        self._playlists[index] = Playlist(
            playlist_id=playlist.playlist_id,
            name=cleaned,
            track_paths=playlist.track_paths,
        )
        self._persist()
        self._notify()

    def add_track(self, playlist_id: str, file_path) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        path = str(Path(file_path))
        playlist = self._playlists[index]
        if path in playlist.track_paths:
            return  # dedupe
        self._playlists[index] = Playlist(
            playlist_id=playlist.playlist_id,
            name=playlist.name,
            track_paths=(*playlist.track_paths, path),
        )
        self._persist()
        self._notify()

    def remove_track(self, playlist_id: str, index: int) -> None:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return
        playlist = self._playlists[playlist_index]
        if not (0 <= index < len(playlist.track_paths)):
            return
        paths = list(playlist.track_paths)
        del paths[index]
        self._playlists[playlist_index] = Playlist(
            playlist_id=playlist.playlist_id,
            name=playlist.name,
            track_paths=tuple(paths),
        )
        self._persist()
        self._notify()

    def move_track(self, playlist_id: str, from_index: int, to_index: int) -> None:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return
        playlist = self._playlists[playlist_index]
        paths = list(playlist.track_paths)
        if not (0 <= from_index < len(paths)):
            return
        to_index = max(0, min(to_index, len(paths) - 1))
        track = paths.pop(from_index)
        paths.insert(to_index, track)
        self._playlists[playlist_index] = Playlist(
            playlist_id=playlist.playlist_id,
            name=playlist.name,
            track_paths=tuple(paths),
        )
        self._persist()
        self._notify()

    def play_playlist(self, playlist_id: str) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        was_empty = self._queue.state.count == 0
        for path in self._playlists[index].track_paths:
            self._queue.add(Path(path))
        if was_empty:
            self._queue.play_index(0)

    # ------------------------------------------------------------------
    # Navigation metadata (pinned / recent) — identity-based
    # ------------------------------------------------------------------

    def pin_playlist(self, playlist_id: str) -> None:
        if self._find_by_id(playlist_id) < 0:
            return
        if playlist_id in self._nav.pinned_ids:
            return  # duplicate pin: no-op
        self._nav = PlaylistNavigationState(
            pinned_ids=(*self._nav.pinned_ids, playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._persist_nav()
        self._notify()

    def unpin_playlist(self, playlist_id: str) -> None:
        if playlist_id not in self._nav.pinned_ids:
            return  # unpin missing id: no-op
        self._nav = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._persist_nav()
        self._notify()

    def mark_recent(self, playlist_id: str) -> None:
        """MRU semantics: most recently opened/navigated first, bounded by
        MAX_RECENT_PLAYLISTS, no duplicates. Unknown ids never enter.

        Idempotent: opening the already-most-recent playlist is a no-op
        (no persistence, no notification) — the MRU order did not change."""
        if self._find_by_id(playlist_id) < 0:
            return
        if self._nav.recent_ids and self._nav.recent_ids[0] == playlist_id:
            return  # already MRU rank 0: order unchanged
        recent = [i for i in self._nav.recent_ids if i != playlist_id]
        recent.insert(0, playlist_id)
        recent = recent[:MAX_RECENT_PLAYLISTS]
        self._nav = PlaylistNavigationState(
            pinned_ids=self._nav.pinned_ids,
            recent_ids=tuple(recent),
        )
        self._persist_nav()
        self._notify()

    # ------------------------------------------------------------------
    # Temporary compatibility wrappers (DEPRECATED — name is NOT identity).
    # Presentation migrates to ids in M8-R1E; remove after migration.
    # ------------------------------------------------------------------

    def _resolve_name_to_id(self, name: str) -> str | None:
        playlist = next((p for p in self._playlists if p.name == name), None)
        return playlist.playlist_id if playlist is not None else None

    def delete_playlist_by_name(self, name: str) -> None:
        """DEPRECATED compatibility: name-based delete delegates to id."""
        playlist_id = self._resolve_name_to_id(name)
        if playlist_id is not None:
            self.delete_playlist(playlist_id)

    def rename_playlist_by_name(self, old_name: str, new_name: str) -> None:
        """DEPRECATED compatibility: name-based rename delegates to id."""
        playlist_id = self._resolve_name_to_id(old_name)
        if playlist_id is not None:
            self.rename_playlist(playlist_id, new_name)

    def add_track_by_name(self, name: str, file_path) -> None:
        """DEPRECATED compatibility: name-based add delegates to id."""
        playlist_id = self._resolve_name_to_id(name)
        if playlist_id is not None:
            self.add_track(playlist_id, file_path)

    def remove_track_by_name(self, name: str, index: int) -> None:
        """DEPRECATED compatibility: name-based remove delegates to id."""
        playlist_id = self._resolve_name_to_id(name)
        if playlist_id is not None:
            self.remove_track(playlist_id, index)

    def move_track_by_name(self, name: str, from_index: int, to_index: int) -> None:
        """DEPRECATED compatibility: name-based move delegates to id."""
        playlist_id = self._resolve_name_to_id(name)
        if playlist_id is not None:
            self.move_track(playlist_id, from_index, to_index)

    def play_playlist_by_name(self, name: str) -> None:
        """DEPRECATED compatibility: name-based play delegates to id."""
        playlist_id = self._resolve_name_to_id(name)
        if playlist_id is not None:
            self.play_playlist(playlist_id)
