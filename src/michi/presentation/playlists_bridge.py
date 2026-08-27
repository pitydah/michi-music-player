"""PlaylistsBridge — canonical presentation projection for the first-class
Playlists shell feature (M9-R1 / M9-R1I).

Owns NO business state. It adapts:

- PlaylistService (collection + pinned/recent + CRUD)
- PlaylistNavigationCoordinator (validated open intent)
- NavigationService (the SINGLE current-detail authority — M9-R1I)
- LibraryService (optional: TrackRef resolution for track rows)

M9-R1I invariant: NavigationState.playlist_id is the ONE AND ONLY current
playlist identity. The bridge keeps NO local selection state; every
selected* projection derives from navigation.state.playlist_id.
"""

from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QUrl, Signal, Slot

from michi.application.audio_quality import make_track_quality_label
from michi.application.library_service import LibraryService
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistPaletteExtractorPort

_DEFAULT_HERO_PALETTE = ["#152A45", "#13243D", "#0A0D14"]


def local_path_from_url(value: QUrl | str) -> Path | None:
    """Normalize a QML FileDialog URL or an already-local path.

    QUrl owns platform-specific URL decoding (including percent escapes and
    Windows drive/UNC rules); QML must never strip ``file://`` manually.
    Non-local URL schemes are rejected because managed artwork storage only
    accepts local files.
    """
    if isinstance(value, QUrl):
        if not value.isValid() or value.isEmpty() or not value.isLocalFile():
            return None
        local = value.toLocalFile()
        return Path(local) if local else None

    raw = str(value).strip()
    if not raw:
        return None
    parsed = QUrl(raw)
    if parsed.scheme():
        if not parsed.isLocalFile():
            return None
        local = parsed.toLocalFile()
        return Path(local) if local else None
    return Path(raw)


class PlaylistsBridge(QObject):
    """PlaylistService + coordinator + navigation → QML. No playlist
    business rule lives in QML; the current playlist is the navigation
    target; name is display-only."""

    playlists_changed = Signal()
    _palette_ready = Signal(str, str, list)

    def __init__(
        self,
        playlist_service: PlaylistService | None = None,
        playlist_navigation: PlaylistNavigationCoordinator | None = None,
        navigation_service: NavigationService | None = None,
        library: LibraryService | None = None,
        playback_coordinator=None,
        parent: QObject | None = None,
        palette_extractor: PlaylistPaletteExtractorPort | None = None,
    ) -> None:
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._coordinator = playlist_navigation
        self._navigation = navigation_service
        self._library = library
        self._playback_coordinator = playback_coordinator
        self._palette_extractor = palette_extractor
        self._auto_palettes: dict[str, list[str]] = {}
        self._palette_sources: dict[str, str] = {}
        self._palette_epoch = 0
        self._palette_ready.connect(self._apply_palette, Qt.QueuedConnection)
        if playlist_service is not None:
            playlist_service.subscribe_changed(self._on_playlist_service_changed)
        if navigation_service is not None:
            navigation_service.subscribe_changed(self._on_navigation_changed)
        if library is not None:
            library.subscribe_changed(self._on_library_changed)

    def dispose(self) -> None:
        if self._playlist_service is not None:
            self._playlist_service.unsubscribe_changed(
                self._on_playlist_service_changed
            )
        if self._navigation is not None:
            self._navigation.unsubscribe_changed(self._on_navigation_changed)
        if self._library is not None:
            self._library.unsubscribe_changed(self._on_library_changed)
        if self._palette_extractor is not None:
            self._palette_extractor.close()

    def _on_playlist_service_changed(self) -> None:
        # A managed cover can be atomically replaced at the SAME path. A
        # generation token ensures the old in-flight result cannot win and
        # lets the extractor's mtime-aware cache observe the replacement.
        self._palette_epoch += 1
        self._palette_sources.clear()
        self.playlists_changed.emit()

    def _on_navigation_changed(self) -> None:
        self.playlists_changed.emit()

    def _on_library_changed(self) -> None:
        """M9-R1J: playlist search projection reads LibraryService search
        state (query/active) and track metadata — react to library changes
        so searchPlaylists/searchPlaylistCount/playlistTrackRows recompute."""
        self._palette_epoch += 1
        self._palette_sources.clear()
        self.playlists_changed.emit()

    # ------------------------------------------------------------------
    # Row projection (canonical playlist row shape)
    def _artwork_for_path(self, path_str: str) -> str:
        if self._library is None:
            return ""
        for a in self._library.state.albums:
            if path_str in a.track_paths:
                return self._library.artwork_path_for(a.key) or ""
        return ""

    def _mosaic_for_paths(self, track_paths: tuple[str, ...]) -> list[str]:
        if self._library is None:
            return []
        artworks: list[str] = []
        seen: set[str] = set()
        for path_str in track_paths:
            art = self._artwork_for_path(path_str)
            if art and art not in seen:
                seen.add(art)
                artworks.append(art)
                if len(artworks) == 4:
                    break
        return artworks

    def _duration_for_paths(self, track_paths: tuple[str, ...]) -> int:
        if self._library is None:
            return 0
        total = 0
        for path_str in track_paths:
            ref = self._library.resolve_trackref(Path(path_str))
            if ref is not None:
                total += ref.duration_ms
        return total

    @staticmethod
    def _appearance_row(playlist) -> dict:
        appearance = playlist.appearance
        return {
            "heroMode": appearance.hero_mode.value,
            "heroSolidColor": appearance.hero_solid_color,
            "heroGradientColors": list(appearance.hero_gradient_colors),
            "heroGradientAngle": appearance.hero_gradient_angle,
            "heroImagePath": appearance.hero_image_path,
        }

    def _palette_source_key(self, paths: tuple[str, ...]) -> str:
        return f"{self._palette_epoch}\n" + "\n".join(paths)

    def _palette_sources_for(self, playlist, mosaic: list[str]) -> tuple[str, ...]:
        if playlist.custom_cover_path:
            return (playlist.custom_cover_path,)
        return tuple(mosaic[:4])

    def _auto_palette_for(self, playlist, mosaic: list[str]) -> list[str]:
        sources = self._palette_sources_for(playlist, mosaic)
        source_key = self._palette_source_key(sources)
        current_key = self._palette_sources.get(playlist.playlist_id)
        if current_key != source_key:
            self._palette_sources[playlist.playlist_id] = source_key
            if self._palette_extractor is not None and sources:
                playlist_id = playlist.playlist_id
                self._palette_extractor.request_palette(
                    sources,
                    lambda colors: self._palette_ready.emit(
                        playlist_id, source_key, list(colors)
                    ),
                )
        return self._auto_palettes.get(
            playlist.playlist_id, list(_DEFAULT_HERO_PALETTE)
        )

    @Slot(str, str, list)
    def _apply_palette(
        self, playlist_id: str, source_key: str, colors: list[str]
    ) -> None:
        if self._palette_sources.get(playlist_id) != source_key:
            return  # a newer cover/mosaic already owns this playlist
        normalized = [str(color) for color in colors[:3]]
        if len(normalized) < 2:
            return
        if normalized == self._auto_palettes.get(playlist_id):
            return
        self._auto_palettes[playlist_id] = normalized
        self.playlists_changed.emit()

    def _rows(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        nav = self._playlist_service.navigation
        valid_ids = {
            playlist.playlist_id for playlist in self._playlist_service.playlists
        }
        for stale_id in set(self._palette_sources) - valid_ids:
            self._palette_sources.pop(stale_id, None)
            self._auto_palettes.pop(stale_id, None)
        recent_rank = {pid: rank for rank, pid in enumerate(nav.recent_ids)}
        rows = []
        for playlist in self._playlist_service.playlists:
            mosaic = self._mosaic_for_paths(playlist.track_paths)
            row = {
                "playlistId": playlist.playlist_id,
                "name": playlist.name,
                "trackCount": len(playlist.track_paths),
                "durationMs": self._duration_for_paths(playlist.track_paths),
                "customCoverPath": playlist.custom_cover_path,
                "mosaicArtworkPaths": mosaic,
                "pinned": playlist.playlist_id in nav.pinned_ids,
                "recentRank": recent_rank.get(playlist.playlist_id, -1),
                "autoHeroColors": self._auto_palette_for(playlist, mosaic),
            }
            row.update(self._appearance_row(playlist))
            rows.append(row)
        return rows

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

    # ------------------------------------------------------------------
    # Single navigation truth (M9-R1I): every selected* projection derives
    # from NavigationState.playlist_id — NO bridge-local selection state.
    # ------------------------------------------------------------------

    def _current_playlist_id(self) -> str:
        if self._navigation is None:
            return ""
        return self._navigation.state.playlist_id or ""

    def _get_selected_playlist_id(self) -> str:
        return self._current_playlist_id()

    def _get_selected_playlist_name(self) -> str:
        playlist = self._selected()
        return playlist.name if playlist is not None else ""

    def _get_selected_playlist_custom_cover(self) -> str:
        playlist = self._selected()
        return playlist.custom_cover_path if playlist is not None else ""

    def _get_selected_playlist_duration_ms(self) -> int:
        playlist = self._selected()
        if playlist is None:
            return 0
        return self._duration_for_paths(playlist.track_paths)

    def _get_selected_playlist_mosaic_artworks(self) -> list[str]:
        playlist = self._selected()
        if playlist is None:
            return []
        return self._mosaic_for_paths(playlist.track_paths)

    def _get_selected_playlist_pinned(self) -> bool:
        playlist_id = self._current_playlist_id()
        if not playlist_id or self._playlist_service is None:
            return False
        return playlist_id in self._playlist_service.navigation.pinned_ids

    def _get_selected_appearance(self) -> dict:
        playlist = self._selected()
        if playlist is None:
            return {
                "heroMode": "auto",
                "heroSolidColor": "#152A45",
                "heroGradientColors": ["#152A45", "#13243D"],
                "heroGradientAngle": 135.0,
                "heroImagePath": "",
            }
        return self._appearance_row(playlist)

    def _get_selected_auto_hero_colors(self) -> list[str]:
        playlist = self._selected()
        if playlist is None:
            return list(_DEFAULT_HERO_PALETTE)
        mosaic = self._mosaic_for_paths(playlist.track_paths)
        return self._auto_palette_for(playlist, mosaic)

    def _selected(self):
        playlist_id = self._current_playlist_id()
        if not playlist_id or self._playlist_service is None:
            return None
        return self._playlist_service.get_playlist(playlist_id)

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
    selectedPlaylistPinned = Property(
        bool, _get_selected_playlist_pinned, notify=playlists_changed
    )
    selectedPlaylistCustomCoverPath = Property(
        str, _get_selected_playlist_custom_cover, notify=playlists_changed
    )
    selectedPlaylistDurationMs = Property(
        int, _get_selected_playlist_duration_ms, notify=playlists_changed
    )
    selectedPlaylistMosaicArtworkPaths = Property(
        list, _get_selected_playlist_mosaic_artworks, notify=playlists_changed
    )
    selectedPlaylistAppearance = Property(
        dict, _get_selected_appearance, notify=playlists_changed
    )
    selectedPlaylistAutoHeroColors = Property(
        list, _get_selected_auto_hero_colors, notify=playlists_changed
    )
    selectedPlaylistDescription = Property(
        str, lambda self: "", notify=playlists_changed
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
    def open_playlist(self, playlist_id: str) -> None:
        """Validated open (recent + navigation) through the coordinator."""
        if self._coordinator is not None:
            self._coordinator.open_playlist(playlist_id)

    @Slot()
    def open_all_playlists(self) -> None:
        if self._coordinator is not None:
            self._coordinator.open_all_playlists()

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

    @Slot(str, str, result=bool)
    def rename_playlist(self, playlist_id: str, new_name: str) -> bool:
        """Explicit success contract (M9-R1I): True only when the rename
        succeeded; False for missing playlist / invalid / duplicate name.
        Never raises into QML."""
        if self._playlist_service is None:
            return False
        if self._playlist_service.get_playlist(playlist_id) is None:
            return False  # missing playlist is a failure, not a silent no-op
        try:
            self._playlist_service.rename_playlist(playlist_id, new_name)
        except ValueError:
            return False
        return True

    @Slot(str)
    def delete_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.delete_playlist(playlist_id)

    @Slot(str)
    def pin_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.pin_playlist(playlist_id)

    @Slot(str)
    def unpin_playlist(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.unpin_playlist(playlist_id)

    @Slot(str, str, result=bool)
    def set_custom_cover(self, playlist_id: str, path: str) -> bool:
        local_path = local_path_from_url(path)
        if local_path is None or self._playlist_service is None:
            return False
        return (
            self._playlist_service.set_custom_cover(playlist_id, local_path) is not None
        )

    @Slot(str, QUrl, result=bool)
    def set_custom_cover_from_url(self, playlist_id: str, url: QUrl) -> bool:
        path = local_path_from_url(url)
        if path is None or self._playlist_service is None:
            return False
        return self._playlist_service.set_custom_cover(playlist_id, path) is not None

    @Slot(str)
    def remove_custom_cover(self, playlist_id: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.remove_custom_cover(playlist_id)

    @Slot(str, result=bool)
    def set_hero_auto(self, playlist_id: str) -> bool:
        if self._playlist_service is None:
            return False
        return self._playlist_service.set_hero_auto(playlist_id)

    @Slot(str, str, result=bool)
    def set_hero_solid(self, playlist_id: str, color: str) -> bool:
        if self._playlist_service is None:
            return False
        try:
            return self._playlist_service.set_hero_solid(playlist_id, color)
        except ValueError:
            return False

    @Slot(str, list, float, result=bool)
    def set_hero_gradient(self, playlist_id: str, colors: list, angle: float) -> bool:
        if self._playlist_service is None:
            return False
        try:
            return self._playlist_service.set_hero_gradient(
                playlist_id, tuple(str(color) for color in colors), angle
            )
        except (TypeError, ValueError):
            return False

    @Slot(str, QUrl, result=bool)
    def set_custom_hero_from_url(self, playlist_id: str, url: QUrl) -> bool:
        path = local_path_from_url(url)
        if path is None or self._playlist_service is None:
            return False
        return (
            self._playlist_service.set_custom_hero_image(playlist_id, path) is not None
        )

    @Slot(str, str)
    def add_track(self, playlist_id: str, path: str) -> None:
        if self._playlist_service is not None:
            self._playlist_service.add_track(playlist_id, Path(path))

    @Slot(int)
    def remove_track(self, index: int) -> None:
        playlist_id = self._current_playlist_id()
        if self._playlist_service is not None and playlist_id:
            self._playlist_service.remove_track(playlist_id, index)

    @Slot(int, int)
    def move_track(self, from_index: int, to_index: int) -> None:
        playlist_id = self._current_playlist_id()
        if self._playlist_service is not None and playlist_id:
            self._playlist_service.move_track(playlist_id, from_index, to_index)

    @Slot()
    def play_selected_playlist(self) -> None:
        playlist_id = self._current_playlist_id()
        if playlist_id:
            self.play_playlist(playlist_id)

    @Slot(str)
    def play_playlist(self, playlist_id: str) -> None:
        if self._playback_coordinator is not None:
            self._playback_coordinator.play_playlist(playlist_id)

    @Slot(int)
    def play_playlist_track(self, index: int) -> None:
        """Playlist Detail track click → PLAYLIST context at index N."""
        if self._playback_coordinator is not None:
            playlist_id = self._current_playlist_id()
            if playlist_id:
                self._playback_coordinator.play_playlist_track(playlist_id, index)

    @Slot(str)
    def queue_playlist(self, playlist_id: str) -> None:
        """EXPLICIT Queue intent through the coordinator (no private
        _queue access)."""
        if self._playback_coordinator is not None:
            self._playback_coordinator.queue_playlist(playlist_id)

    @Slot()
    def queue_selected_playlist(self) -> None:
        pid = self._current_playlist_id()
        if pid:
            self.queue_playlist(pid)

    @Slot(str, str)
    def add_track_to_playlist(self, playlist_id: str, path: str) -> None:
        """Cross-feature (Library → Playlist): add a track by id."""
        if self._playlist_service is not None:
            self._playlist_service.add_track(playlist_id, Path(path))
