"""PlaylistService — user-defined playlists (LOCAL-06)."""

import logging
from collections.abc import Callable
from pathlib import Path

from michi.application.ports import PlaylistsPort
from michi.application.queue_service import QueueService
from michi.domain.playlist import Playlist

logger = logging.getLogger(__name__)


class PlaylistService:
    """Owns the ordered playlist collection; mutates, persists (best effort)
    and notifies. Playback goes through the queue (queue direction only)."""

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
        self._subscribers: list[Callable[[], None]] = []

    @property
    def playlists(self) -> tuple[Playlist, ...]:
        return tuple(self._playlists)

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

    def _find(self, name: str) -> int:
        for i, playlist in enumerate(self._playlists):
            if playlist.name == name:
                return i
        return -1

    def create_playlist(self, name: str) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        self._playlists.append(Playlist(name=cleaned))
        self._persist()
        self._notify()

    def delete_playlist(self, name: str) -> None:
        index = self._find(name)
        if index < 0:
            return
        del self._playlists[index]
        self._persist()
        self._notify()

    def rename_playlist(self, old_name: str, new_name: str) -> None:
        index = self._find(old_name)
        if index < 0:
            return
        cleaned = new_name.strip()
        if not cleaned:
            raise ValueError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists if p.name != old_name):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        playlist = self._playlists[index]
        self._playlists[index] = Playlist(
            name=cleaned, track_paths=playlist.track_paths
        )
        self._persist()
        self._notify()

    def add_track(self, name: str, file_path) -> None:
        index = self._find(name)
        if index < 0:
            return
        path = str(Path(file_path))
        playlist = self._playlists[index]
        if path in playlist.track_paths:
            return  # dedupe
        self._playlists[index] = Playlist(
            name=playlist.name, track_paths=(*playlist.track_paths, path)
        )
        self._persist()
        self._notify()

    def remove_track(self, name: str, index: int) -> None:
        playlist_index = self._find(name)
        if playlist_index < 0:
            return
        playlist = self._playlists[playlist_index]
        if not (0 <= index < len(playlist.track_paths)):
            return
        paths = list(playlist.track_paths)
        del paths[index]
        self._playlists[playlist_index] = Playlist(
            name=playlist.name, track_paths=tuple(paths)
        )
        self._persist()
        self._notify()

    def move_track(self, name: str, from_index: int, to_index: int) -> None:
        playlist_index = self._find(name)
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
            name=playlist.name, track_paths=tuple(paths)
        )
        self._persist()
        self._notify()

    def play_playlist(self, name: str) -> None:
        index = self._find(name)
        if index < 0:
            return
        was_empty = self._queue.state.count == 0
        for path in self._playlists[index].track_paths:
            self._queue.add(Path(path))
        if was_empty:
            self._queue.play_index(0)
