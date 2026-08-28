"""Application coordinators for Library-origin Queue and Playlist intents."""

from collections.abc import Iterable
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import make_artist_key


class _LibrarySelectionResolver:
    """Resolve opaque Library identities without leaking loops into QML."""

    def __init__(self, library: LibraryService) -> None:
        self._library = library

    def tracks(self, track_ids: Iterable[str]) -> list[Path]:
        paths: list[Path] = []
        seen: set[Path] = set()
        for track_id in track_ids:
            path = Path(str(track_id))
            if path in seen or self._library.resolve_trackref(path) is None:
                continue
            seen.add(path)
            paths.append(path)
        return paths

    def album(self, album_key: str) -> list[Path]:
        album = next(
            (item for item in self._library.state.albums if item.key == album_key),
            None,
        )
        return self.tracks(str(path) for path in album.track_paths) if album else []

    def artist(self, artist_key: str) -> list[Path]:
        return self.tracks(
            str(ref.file_path)
            for ref in self._library.state.tracks
            if make_artist_key(ref.artist.strip() or "Unknown Artist") == artist_key
        )


class LibraryQueueCoordinator:
    """Translate validated Library selections into atomic Queue appends."""

    def __init__(self, library: LibraryService, queue: QueueService) -> None:
        self._selection = _LibrarySelectionResolver(library)
        self._queue = queue

    def queue_tracks(self, track_ids: Iterable[str]) -> int:
        paths = self._selection.tracks(track_ids)
        if paths:
            self._queue.add_many(paths)
        return len(paths)

    def queue_album(self, album_key: str) -> int:
        paths = self._selection.album(album_key)
        if paths:
            self._queue.add_many(paths)
        return len(paths)

    def queue_artist(self, artist_key: str) -> int:
        paths = self._selection.artist(artist_key)
        if paths:
            self._queue.add_many(paths)
        return len(paths)


class LibraryPlaylistCoordinator:
    """Translate Library selections into one identity-based Playlist mutation."""

    def __init__(self, library: LibraryService, playlists: PlaylistService) -> None:
        self._selection = _LibrarySelectionResolver(library)
        self._playlists = playlists

    def add_tracks(self, playlist_id: str, track_ids: Iterable[str]) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        return self._playlists.add_tracks(
            playlist_id, self._selection.tracks(track_ids)
        )

    def add_album(self, playlist_id: str, album_key: str) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        return self._playlists.add_tracks(playlist_id, self._selection.album(album_key))

    def add_artist(self, playlist_id: str, artist_key: str) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        return self._playlists.add_tracks(
            playlist_id, self._selection.artist(artist_key)
        )
