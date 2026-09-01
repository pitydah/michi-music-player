"""Application coordinators for Library-origin Queue and Playlist intents.

M6-EXT-R4 freeze gate: selection resolution is STABLE-IDENTITY based. The
legacy ``_LibrarySelectionResolver`` treated TrackId as a path; it now
resolves every identity through ``LibraryTrackResolver`` and carries
``library_track_id`` into Queue/Playlist runtime objects. Paths are only the
derived current projection.
"""

from collections.abc import Iterable
from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackRef, make_artist_key
from michi.domain.playlist import Playlist


class _LibrarySelectionResolver:
    """Resolve opaque Library identities through the ONE resolver authority.

    NEVER treats a TrackId as a filesystem path. Album membership is
    TrackId-based; artist membership derives canonical refs."""

    def __init__(
        self, library: LibraryService, resolver: LibraryTrackResolver | None = None
    ) -> None:
        self._library = library
        self._resolver = resolver or LibraryTrackResolver(library)

    @staticmethod
    def _legacy_path_reference(library, value: str) -> Path | None:
        """EXPLICIT legacy discriminator (CORRECTIVE SEAL §13): a raw path
        input is accepted ONLY when the LibraryService already resolves the
        EXACT value as one of its known current paths. Path(string).parts
        is never used as type inference — an unknown UUID can never become
        a path."""
        if not value or value.startswith("legacy-path::"):
            return None
        candidate = Path(value)
        if library.resolve_trackref(candidate) is not None:
            return candidate
        return None

    def tracks(self, track_ids: Iterable[str]) -> list[TrackRef]:
        """Resolved canonical TrackRefs (stable identity); unresolved ids
        are skipped honestly. LEGACY seam (explicit): a RAW PATH input
        (pre-R4 callers) resolves ONLY when the library knows that exact
        path — a UUID is never inferred to be a path."""
        refs: list[TrackRef] = []
        seen: set[str] = set()
        for track_id in track_ids:
            if track_id in seen:
                continue
            seen.add(track_id)
            ref = self._resolver.resolve_ref(track_id)
            if ref is None:
                legacy_path = self._legacy_path_reference(self._library, track_id)
                if legacy_path is not None:
                    ref = self._library.resolve_trackref(legacy_path)
            if ref is not None:
                refs.append(ref)
        return refs

    def album(self, album_key: str) -> list[TrackRef]:
        album = next(
            (item for item in self._library.state.albums if item.key == album_key),
            None,
        )
        if album is None:
            return []
        # CANONICAL membership is TrackIds; a pre-migration AlbumRef with
        # empty track_ids falls back to the derived path projection.
        if album.track_ids:
            return self.tracks(album.track_ids)
        return [
            ref
            for path in album.track_paths
            if (ref := self._library.resolve_trackref(path)) is not None
        ]

    def artist(self, artist_key: str) -> list[TrackRef]:
        return [
            ref
            for ref in self._library.state.tracks
            if make_artist_key(ref.artist.strip() or "Unknown Artist") == artist_key
        ]

    @staticmethod
    def _playable_paths(refs: list[TrackRef]) -> list[Path]:
        return [ref.file_path for ref in refs]


class LibraryQueueCoordinator:
    """Translate validated Library selections into atomic Queue appends.

    Queue entries from the Library carry their stable ``library_track_id``
    (M6-EXT-R4 freeze gate) so a moved track resolves at playback time.
    Queue stays temporary content authority; PlaybackSession stays playback
    context authority."""

    def __init__(self, library: LibraryService, queue: QueueService) -> None:
        self._selection = _LibrarySelectionResolver(library)
        self._queue = queue

    def queue_tracks(self, track_ids: Iterable[str]) -> int:
        refs = self._selection.tracks(track_ids)
        if refs:
            self._queue.add_many_entries(
                [(ref.file_path, ref.track_id or None) for ref in refs]
            )
        return len(refs)

    def queue_album(self, album_key: str) -> int:
        refs = self._selection.album(album_key)
        if refs:
            self._queue.add_many_entries(
                [(ref.file_path, ref.track_id or None) for ref in refs]
            )
        return len(refs)

    def queue_artist(self, artist_key: str) -> int:
        refs = self._selection.artist(artist_key)
        if refs:
            self._queue.add_many_entries(
                [(ref.file_path, ref.track_id or None) for ref in refs]
            )
        return len(refs)


class LibraryPlaylistCoordinator:
    """Translate Library selections into identity-based Playlist mutations.

    Every membership intent resolves through the canonical selection
    resolver and mutates PlaylistService by track_paths (SEMANTIC
    INTEGRATION: main's playlist authority is path-based)."""

    def __init__(self, library: LibraryService, playlists: PlaylistService) -> None:
        self._selection = _LibrarySelectionResolver(library)
        self._playlists = playlists

    @staticmethod
    def _paths(refs: list[TrackRef]) -> list[str]:
        """SEMANTIC INTEGRATION: main's playlist authority is
        track_paths — paths, not R4-era references."""
        return [str(ref.file_path) for ref in refs]

    def add_tracks(self, playlist_id: str, track_ids: Iterable[str]) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        added, _ = self._playlists.add_tracks(
            playlist_id, self._paths(self._selection.tracks(track_ids))
        )
        return added

    def add_album(self, playlist_id: str, album_key: str) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        added, _ = self._playlists.add_tracks(
            playlist_id, self._paths(self._selection.album(album_key))
        )
        return added

    def add_artist(self, playlist_id: str, artist_key: str) -> int:
        if not self._playlists.contains_playlist(playlist_id):
            return 0
        added, _ = self._playlists.add_tracks(
            playlist_id, self._paths(self._selection.artist(artist_key))
        )
        return added

    def _create_with_paths(self, name: str, refs) -> Playlist | None:
        playlist = self._playlists.create_playlist(name)
        if playlist is None:
            return None
        if refs:
            self._playlists.add_tracks(playlist.playlist_id, self._paths(refs))
        # El create devolvió la instancia pre-mutación (frozen replace):
        # devolver la autoridad actual del service.
        return self._playlists.get_playlist(playlist.playlist_id) or playlist

    def create_from_tracks(
        self, name: str, track_ids: Iterable[str]
    ) -> Playlist | None:
        refs = self._selection.tracks(track_ids)
        if not refs:
            return None
        return self._create_with_paths(name, refs)

    def create_from_album(self, name: str, album_key: str) -> Playlist | None:
        refs = self._selection.album(album_key)
        if not refs:
            return None
        return self._create_with_paths(name, refs)

    def create_from_artist(self, name: str, artist_key: str) -> Playlist | None:
        refs = self._selection.artist(artist_key)
        if not refs:
            return None
        return self._create_with_paths(name, refs)
