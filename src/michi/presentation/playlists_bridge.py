"""PlaylistsBridge — canonical presentation projection for the first-class
Playlists shell feature (M9-R1).

Owns NO business state. It adapts:

- PlaylistService (collection + pinned/recent + CRUD)
- PlaylistNavigationCoordinator (validated open intent)
- LibraryService (optional: TrackRef resolution for track rows)

LibraryBridge no longer owns canonical playlist presentation; this bridge
is the single presentation projection for All Playlists, pinned/recent,
selection and detail tracks."""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from michi.application.audio_quality import make_track_quality_label
from michi.application.library_service import LibraryService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService


class PlaylistsBridge(QObject):
    """PlaylistService + coordinator → QML. No playlist business rule lives
    in QML; selection is identity-driven; name is display-only."""

    playlists_changed = Signal()

    def __init__(
        self,
        playlist_service: PlaylistService | None = None,
        playlist_navigation: PlaylistNavigationCoordinator | None = None,
        library: LibraryService | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._coordinator = playlist_navigation
        self._library = library
        self._selected_playlist_id: str = ""
        self._selected_playlist_index: int = -1
        if playlist_service is not None:
            playlist_service.subscribe_changed(self._on_service_changed)

    def dispose(self) -> None:
        if self._playlist_service is not None:
            self._playlist_service.unsubscribe_changed(self._on_service_changed)

    def _on_service_changed(self) -> None:
        # Identity-driven selection: a selected playlist that disappears
        # (any delete path) clears the selection safely.
        if (
            self._selected_playlist_id
            and self._playlist_service is not None
            and self._playlist_service.get_playlist(self._selected_playlist_id) is None
        ):
            self._selected_playlist_id = ""
            self._selected_playlist_index = -1
        self.playlists_changed.emit()

    # ------------------------------------------------------------------
    # Row projection (canonical playlist row shape)
    # ------------------------------------------------------------------

    def _rows(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        nav = self._playlist_service.navigation
        recent_rank = {pid: rank for rank, pid in enumerate(nav.recent_ids)}
        return [
            {
                "playlistId": p.playlist_id,
                "name": p.name,
                "trackCount": len(p.track_paths),
                "pinned": p.playlist_id in nav.pinned_ids,
                "recentRank": recent_rank.get(p.playlist_id, -1),
            }
            for p in self._playlist_service.playlists
        ]

    def _get_playlists(self) -> list[dict]:
        return self._rows()

    def _get_pinned_playlists(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        pinned = set(self._playlist_service.navigation.pinned_ids)
        return [row for row in self._rows() if row["playlistId"] in pinned]

    def _get_recent_playlists(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        # Recent projection ordered by recentRank; excludes playlists already
        # visible in Pinned (presentation policy — never mutates state).
        pinned = set(self._playlist_service.navigation.pinned_ids)
        ranked = [
            row
            for row in self._rows()
            if row["recentRank"] >= 0 and row["playlistId"] not in pinned
        ]
        ranked.sort(key=lambda row: row["recentRank"])
        return ranked

    def _get_selected_playlist_id(self) -> str:
        return self._selected_playlist_id

    def _get_selected_playlist_name(self) -> str:
        if not self._selected_playlist_id or self._playlist_service is None:
            return ""
        playlist = self._playlist_service.get_playlist(self._selected_playlist_id)
        return playlist.name if playlist is not None else ""

    def _selected(self):
        if self._playlist_service is None or not self._selected_playlist_id:
            return None
        return self._playlist_service.get_playlist(self._selected_playlist_id)

    def _get_playlist_tracks(self) -> list[dict]:
        playlist = self._selected()
        if playlist is None:
            return []
        rows = []
        for path in playlist.track_paths:
            ref = (
                self._library.resolve_trackref(Path(path))
                if self._library is not None
                else None
            )
            rows.append(
                {
                    "displayName": (
                        ref.display_name if ref is not None else Path(path).stem
                    ),
                    "path": path,
                }
            )
        return rows

    def _get_playlist_track_rows(self) -> list[dict]:
        playlist = self._selected()
        if playlist is None:
            return []
        rows = []
        for path in playlist.track_paths:
            ref = (
                self._library.resolve_trackref(Path(path))
                if self._library is not None
                else None
            )
            if ref is not None:
                rows.append(self._track_row(ref))
                continue
            rows.append(
                {
                    "displayName": Path(path).stem,
                    "title": Path(path).stem,
                    "artist": "",
                    "album": "",
                    "durationMs": 0,
                    "path": path,
                    "qualityLabel": "",
                    "codec": "",
                    "sampleRateHz": 0,
                    "bitDepth": 0,
                    "channels": 0,
                    "fileSize": 0,
                }
            )
        return rows

    def _track_row(self, ref) -> dict:
        return {
            "displayName": ref.display_name,
            "title": ref.title or ref.display_name,
            "artist": ref.artist,
            "album": ref.album,
            "durationMs": ref.duration_ms,
            "path": str(ref.file_path),
            "qualityLabel": make_track_quality_label(ref),
            "codec": ref.codec,
            "sampleRateHz": ref.sample_rate_hz,
            "bitDepth": ref.bit_depth,
            "channels": ref.channels,
            "fileSize": ref.file_size,
        }

    def _get_search_playlists(self) -> list[dict]:
        """Local playlist-name matches kept separate from the frozen M7
        ranker. Rows carry the canonical playlistId (M8-R1F)."""
        if self._playlist_service is None:
            return []
        query = ""
        if self._library is not None and self._library.state.search_active:
            query = " ".join(self._library.state.query.casefold().split())
        if not query:
            return []
        return [
            row
            for row in self._rows()
            if query in " ".join(row["name"].casefold().split())
        ]

    def _get_search_playlist_count(self) -> int:
        return len(self._get_search_playlists())

    playlists = Property(list, _get_playlists, notify=playlists_changed)
    pinnedPlaylists = Property(list, _get_pinned_playlists, notify=playlists_changed)
    recentPlaylists = Property(list, _get_recent_playlists, notify=playlists_changed)
    selectedPlaylistId = Property(
        str, _get_selected_playlist_id, notify=playlists_changed
    )
    selectedPlaylistName = Property(
        str, _get_selected_playlist_name, notify=playlists_changed
    )
    playlistTracks = Property(list, _get_playlist_tracks, notify=playlists_changed)
    playlistTrackRows = Property(
        list, _get_playlist_track_rows, notify=playlists_changed
    )
    searchPlaylists = Property(list, _get_search_playlists, notify=playlists_changed)
    searchPlaylistCount = Property(
        int, _get_search_playlist_count, notify=playlists_changed
    )

    # ------------------------------------------------------------------
    # Intents — playlist service CRUD by id (no name-based production path)
    # ------------------------------------------------------------------

    @Slot(str)
    def select_playlist(self, playlist_id: str) -> None:
        """Identity-driven selection. Legacy name-based callers resolve via
        the service compatibility lookup (DEPRECATED path)."""
        if self._playlist_service is None:
            return
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            playlist = next(
                (p for p in self._playlist_service.playlists if p.name == playlist_id),
                None,
            )
        if playlist is None:
            return
        self._selected_playlist_id = playlist.playlist_id
        self._selected_playlist_index = next(
            (
                i
                for i, p in enumerate(self._playlist_service.playlists)
                if p.playlist_id == playlist.playlist_id
            ),
            -1,
        )
        self.playlists_changed.emit()

    @Slot()
    def clear_playlist_selection(self) -> None:
        self._selected_playlist_id = ""
        self._selected_playlist_index = -1
        self.playlists_changed.emit()

    @Slot(str)
    def open_playlist(self, playlist_id: str) -> None:
        """Validated open (recent + navigation) through the coordinator."""
        if self._coordinator is not None:
            self._coordinator.open_playlist(playlist_id)

    @Slot()
    def open_all_playlists(self) -> None:
        if self._coordinator is not None:
            self._coordinator.open_all_playlists()

    @Slot(str)
    def create_playlist(self, name: str) -> None:
        if self._playlist_service is None:
            return
        try:
            self._playlist_service.create_playlist(name)
        except ValueError:
            return

    @Slot(str, result=bool)
    def create_and_open_playlist(self, name: str) -> bool:
        """Create + open (M9-R1 workflow): returns True when the playlist was
        created and opened (route → PLAYLISTS/<new id>, Recent updated)."""
        if self._playlist_service is None or self._coordinator is None:
            return False
        try:
            playlist = self._playlist_service.create_playlist(name)
        except ValueError:
            return False
        self._coordinator.open_playlist(playlist.playlist_id)
        return True

    @Slot(str)
    def delete_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is None:
            return
        self._playlist_service.delete_playlist(playlist_id)

    @Slot(str, str)
    def rename_playlist(self, playlist_id: str, new_name: str) -> None:
        if self._playlist_service is None:
            return
        try:
            self._playlist_service.rename_playlist(playlist_id, new_name)
        except ValueError:
            return

    @Slot(str)
    def pin_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.pin_playlist(playlist_id)

    @Slot(str)
    def unpin_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.unpin_playlist(playlist_id)

    @Slot(str, str)
    def add_track(self, playlist_id: str, path: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.add_track(playlist_id, Path(path))

    @Slot(int)
    def remove_track(self, index: int) -> None:
        if self._playlist_service is not None and self._selected_playlist_id:
            self._playlist_service.remove_track(self._selected_playlist_id, index)

    @Slot(int, int)
    def move_track(self, from_index: int, to_index: int) -> None:
        if self._playlist_service is not None and self._selected_playlist_id:
            self._playlist_service.move_track(
                self._selected_playlist_id, from_index, to_index
            )

    @Slot()
    def play_selected_playlist(self) -> None:
        if self._playlist_service is not None and self._selected_playlist_id:
            self._playlist_service.play_playlist(self._selected_playlist_id)

    @Slot(str)
    def play_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.play_playlist(playlist_id)

    @Slot(str)
    def add_track_to_playlist(self, playlist_id: str, path: str) -> None:
        """Cross-feature (Library → Playlist): add a track by id."""
        if self._playlist_service is not None:
            self._playlist_service.add_track(playlist_id, Path(path))
