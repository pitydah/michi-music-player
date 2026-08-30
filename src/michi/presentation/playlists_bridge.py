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

import logging
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QUrl, Signal, Slot

from michi.application.audio_quality import make_track_quality_label
from michi.application.errors import (
    PlaylistNameConflictError,
    PlaylistNameInvalidError,
    PlaylistPersistenceError,
)
from michi.application.library_service import LibraryService
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistPaletteExtractorPort
from michi.domain.playlist import PlaylistHeroMode

logger = logging.getLogger(__name__)

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
    # R2 P1-05: presentation-safe persistence failure notification. The
    # human text lives in QML (qsTr); this carries a STABLE operation code.
    # R3-04: UNA SOLA autoridad de durable-write failure. El signal
    # significa EXACTAMENTE "DURABLE WRITE FAILED" — nunca un fallo lógico.
    persistenceFailed = Signal(str)
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
        # R2 P1-09: explicit cached projection. The artwork index is rebuilt
        # ONLY when the Library changes; playlist rows are rebuilt ONLY when
        # PlaylistService/navigation changes — never per getter call.
        self._artwork_index: dict[str, str] = {}
        self._artwork_index_dirty = True
        self._rows_cache: list[dict] | None = None
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

    def _run_mutation(self, operation: str, mutation):
        """R4-10 PRESENTATION BOUNDARY: traduce SOLO la excepción
        contractual PlaylistPersistenceError → persistenceFailed(operation)
        + None (PERSISTENCE_FAILURE_SENTINEL). NUNCA convierte False
        lógico (no-change/duplicate) en persistence failure — la semántica
        lógica proviene del Service/result del caller."""
        try:
            return mutation()
        except PlaylistPersistenceError:
            logger.warning("playlist mutation failed (%s)", operation)
            self.persistenceFailed.emit(operation)
            return None

    def _on_playlist_service_changed(self) -> None:
        """R2 P1-10: a PlaylistService change marks the ROW projection dirty
        but NEVER invalidates palettes globally. Palette source identity
        depends on the actual source paths (content-addressed managed files
        change their path when their content changes) — rename/pin/unpin/
        recent/open do not touch artwork and therefore trigger ZERO new
        palette requests."""
        self._rows_cache = None
        self.playlists_changed.emit()

    def _on_navigation_changed(self) -> None:
        self._rows_cache = None
        self.playlists_changed.emit()

    def _on_library_changed(self) -> None:
        """M9-R1J: playlist search projection reads LibraryService search
        state (query/active) and track metadata — react to library changes
        so searchPlaylists/searchPlaylistCount/playlistTrackRows recompute.
        The artwork index is rebuilt lazily ONCE on the next rows refresh."""
        self._artwork_index_dirty = True
        self._rows_cache = None
        self.playlists_changed.emit()

    # ------------------------------------------------------------------
    # Row projection (canonical playlist row shape)
    def _build_artwork_index(self) -> dict[str, str]:
        """path → artwork map (R2 P1-09). REBUILT ONLY when the Library
        changed; cached between refreshes. Never rebuilt per playlist."""
        if self._artwork_index_dirty:
            self._artwork_index = self._compute_artwork_index()
            self._artwork_index_dirty = False
        return self._artwork_index

    def _compute_artwork_index(self) -> dict[str, str]:
        if self._library is None:
            return {}
        index: dict[str, str] = {}
        for album in self._library.state.albums:
            art = self._library.artwork_path_for(album.key) or ""
            if not art:
                continue
            for track_path in album.track_paths:
                index.setdefault(str(track_path), art)
        return index

    def _artwork_for_path(
        self, path_str: str, index: dict[str, str] | None = None
    ) -> str:
        if self._library is None:
            return ""
        if index is not None:
            return index.get(path_str, "")
        for a in self._library.state.albums:
            if path_str in a.track_paths:
                return self._library.artwork_path_for(a.key) or ""
        return ""

    def _mosaic_for_paths(
        self, track_paths: tuple[str, ...], index: dict[str, str] | None = None
    ) -> list[str]:
        """R2 P1-09: uses the EXISTING artwork index — never builds one."""
        if index is None:
            index = self._build_artwork_index()
        artworks: list[str] = []
        seen: set[str] = set()
        for path_str in track_paths:
            art = self._artwork_for_path(path_str, index)
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

    def _appearance_row(self, playlist) -> dict:
        """R3-05: the row carries persisted + effective + missing facts.
        Rendering consumes effective*; editing/recovery consumes
        persisted* + missing flags. No ambiguous raw names."""
        appearance = playlist.appearance
        visual = self._visual_state(playlist)
        return {
            "persistedHeroMode": visual["persistedHeroMode"],
            "effectiveHeroMode": visual["effectiveHeroMode"],
            "persistedHeroImagePath": visual["persistedHeroImagePath"],
            "effectiveHeroImagePath": visual["effectiveHeroImagePath"],
            "heroImageMissing": visual["heroImageMissing"],
            "heroSolidColor": appearance.hero_solid_color,
            "heroGradientColors": list(appearance.hero_gradient_colors),
            "heroGradientAngle": appearance.hero_gradient_angle,
        }

    def _palette_source_key(self, paths: tuple[str, ...]) -> str:
        """R2 P1-10: resource identity ONLY — content-addressed managed
        assets change their path when their content changes, so the path
        list IS the freshness truth. No global epoch, no cross-playlist
        invalidation."""
        return "\n".join(paths)

    def _palette_sources_for(self, playlist, mosaic: list[str]) -> tuple[str, ...]:
        """R3-11: the palette extracts from the EFFECTIVE cover — a
        persisted-but-missing asset never feeds the extractor (dead file)."""
        effective = self._effective_cover_path(playlist)
        if effective:
            return (effective,)
        return tuple(mosaic[:4])

    def _auto_palette_for(self, playlist, mosaic: list[str]) -> list[str]:
        sources = self._palette_sources_for(playlist, mosaic)
        source_key = self._palette_source_key(sources)
        current_key = self._palette_sources.get(playlist.playlist_id)
        if current_key != source_key:
            self._palette_sources[playlist.playlist_id] = source_key
            if not sources:
                # An empty source set owns the canonical default palette.
                # Never retain colors extracted from artwork that has just
                # been removed from the playlist.
                self._auto_palettes.pop(playlist.playlist_id, None)
            elif self._palette_extractor is not None:
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
        # The cached rows snapshot autoHeroColors — invalidate so the
        # overview renders the freshly extracted palette.
        self._rows_cache = None
        self.playlists_changed.emit()

    def _rows(self) -> list[dict]:
        """R2 P1-09 CACHED projection: rebuilt only when marked dirty.
        Getters (playlists/pinned/recent) all consume the SAME rows — the
        full projection is never recomputed per getter."""
        if self._rows_cache is not None:
            return self._rows_cache
        self._rows_cache = self._compute_rows()
        return self._rows_cache

    def _compute_rows(self) -> list[dict]:
        if self._playlist_service is None:
            return []
        index = self._build_artwork_index()
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
            mosaic = self._mosaic_for_paths(playlist.track_paths, index)
            row = {
                "playlistId": playlist.playlist_id,
                "name": playlist.name,
                "trackCount": len(playlist.track_paths),
                "durationMs": self._duration_for_paths(playlist.track_paths),
                "persistedCustomCoverPath": playlist.custom_cover_path,
                "effectiveCustomCoverPath": self._effective_cover_path(playlist),
                "coverAssetMissing": bool(playlist.custom_cover_path)
                and not bool(self._effective_cover_path(playlist)),
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

    def _effective_cover_path(self, playlist) -> str:
        """R3-05: the resolvable cover path ("" when missing) — rendering
        ALWAYS uses this; the persisted intent stays untouched."""
        path = playlist.custom_cover_path
        if not path:
            return ""
        try:
            return path if Path(path).is_file() else ""
        except OSError:
            return ""

    def _effective_hero_mode(self, playlist) -> str:
        """R3-05: persisted hero mode degraded to "auto" when the managed
        image asset no longer exists."""
        if playlist.appearance.hero_mode is PlaylistHeroMode.IMAGE:
            path = playlist.appearance.hero_image_path
            if not path:
                return "auto"
            try:
                return "image" if Path(path).is_file() else "auto"
            except OSError:
                return "auto"
        return playlist.appearance.hero_mode.value

    def _effective_hero_image_path(self, playlist) -> str:
        mode = self._effective_hero_mode(playlist)
        if mode != "image":
            return ""
        return playlist.appearance.hero_image_path

    def _visual_state(self, playlist) -> dict:
        """R3-05: ONE canonical visual-state projection — persisted intent
        AND effective render facts AND missing flags. Rendering uses
        effective*; editing/recovery uses persisted* + missing flags."""
        persisted_cover = playlist.custom_cover_path
        effective_cover = self._effective_cover_path(playlist)
        persisted_mode = playlist.appearance.hero_mode.value
        persisted_hero = playlist.appearance.hero_image_path
        effective_mode = self._effective_hero_mode(playlist)
        effective_hero = self._effective_hero_image_path(playlist)
        return {
            "persistedCustomCoverPath": persisted_cover,
            "effectiveCustomCoverPath": effective_cover,
            "coverAssetMissing": bool(persisted_cover) and not bool(effective_cover),
            "persistedHeroMode": persisted_mode,
            "effectiveHeroMode": effective_mode,
            "persistedHeroImagePath": persisted_hero,
            "effectiveHeroImagePath": effective_hero,
            "heroImageMissing": (
                persisted_mode == "image"
                and bool(persisted_hero)
                and effective_mode != "image"
            ),
        }

    def _get_selected_playlist_custom_cover(self) -> str:
        """PERSISTED custom cover intent (R2 P1-11) — never mutated on
        load; the UI uses the EFFECTIVE projections for rendering."""
        playlist = self._selected()
        return playlist.custom_cover_path if playlist is not None else ""

    def _get_effective_custom_cover(self) -> str:
        """EFFECTIVE cover path: the persisted path when the managed asset
        still EXISTS, otherwise "" — the UI renders the automatic mosaic
        instead of a dead box. Persisted intent is preserved."""
        path = self._get_selected_playlist_custom_cover()
        if not path:
            return ""
        try:
            return path if Path(path).is_file() else ""
        except OSError:
            return ""

    def _get_cover_asset_missing(self) -> bool:
        return bool(self._get_selected_playlist_custom_cover()) and not bool(
            self._get_effective_custom_cover()
        )

    def _get_effective_hero_mode(self) -> str:
        """EFFECTIVE hero mode: persisted ``image`` degrades to ``auto``
        when the managed hero asset no longer exists."""
        playlist = self._selected()
        if playlist is None:
            return "auto"
        if playlist.appearance.hero_mode is PlaylistHeroMode.IMAGE:
            path = playlist.appearance.hero_image_path
            if not path:
                return "auto"
            try:
                return "image" if Path(path).is_file() else "auto"
            except OSError:
                return "auto"
        return playlist.appearance.hero_mode.value

    def _get_hero_image_missing(self) -> bool:
        playlist = self._selected()
        if playlist is None:
            return False
        return (
            playlist.appearance.hero_mode is PlaylistHeroMode.IMAGE
            and playlist.appearance.hero_image_path != ""
            and self._get_effective_hero_mode() == "auto"
        )

    def _get_selected_playlist_duration_ms(self) -> int:
        playlist = self._selected()
        if playlist is None:
            return 0
        return self._duration_for_paths(playlist.track_paths)

    def _get_selected_playlist_mosaic_artworks(self) -> list[str]:
        playlist = self._selected()
        if playlist is None:
            return []
        return self._mosaic_for_paths(playlist.track_paths, self._build_artwork_index())

    def _get_selected_playlist_pinned(self) -> bool:
        playlist_id = self._current_playlist_id()
        if not playlist_id or self._playlist_service is None:
            return False
        return playlist_id in self._playlist_service.navigation.pinned_ids

    def _get_selected_appearance(self) -> dict:
        """R3-05: selected-playlist appearance carries persisted AND
        effective visual facts (detail panel + hero rendering)."""
        playlist = self._selected()
        if playlist is None:
            return {}
        return self._appearance_row(playlist)
        playlist = self._selected()
        if playlist is None:
            return {
                "persistedHeroMode": "auto",
                "effectiveHeroMode": "auto",
                "persistedHeroImagePath": "",
                "effectiveHeroImagePath": "",
                "heroImageMissing": False,
                "heroSolidColor": "#152A45",
                "heroGradientColors": ["#152A45", "#13243D"],
                "heroGradientAngle": 135.0,
            }
        return self._appearance_row(playlist)

    def _get_selected_auto_hero_colors(self) -> list[str]:
        playlist = self._selected()
        if playlist is None:
            return list(_DEFAULT_HERO_PALETTE)
        mosaic = self._mosaic_for_paths(
            playlist.track_paths, self._build_artwork_index()
        )
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
        index = self._build_artwork_index()
        rows = []
        for path in playlist.track_paths:
            ref = (
                self._library.resolve_trackref(Path(path))
                if self._library is not None
                else None
            )
            if ref is not None:
                rows.append(self._track_row(ref, index))
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
                    "artworkPath": self._artwork_for_path(path, index),
                }
            )
        return rows

    def _track_row(self, ref, index: dict[str, str] | None = None) -> dict:
        return {
            "displayName": ref.display_name,
            "title": ref.title or ref.display_name,
            "artist": ref.artist,
            "album": ref.album,
            "durationMs": ref.duration_ms,
            "path": str(ref.file_path),
            "artworkPath": self._artwork_for_path(str(ref.file_path), index),
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
    # R2 P1-11: effective-resolvable asset projections (persisted intent
    # stays untouched; rendering never breaks).
    effectiveCustomCoverPath = Property(
        str, _get_effective_custom_cover, notify=playlists_changed
    )
    coverAssetMissing = Property(
        bool, _get_cover_asset_missing, notify=playlists_changed
    )
    effectiveHeroMode = Property(
        str, _get_effective_hero_mode, notify=playlists_changed
    )
    heroImageMissing = Property(bool, _get_hero_image_missing, notify=playlists_changed)
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

    @Slot(str, result=str)
    def open_playlist(self, playlist_id: str) -> str:
        """R3-03: validated open through the coordinator. Returns a stable
        result code:

            "opened"                  — navigated, Recent persisted
            "opened_recent_unsaved"   — navigated, Recent write failed
            "not_found"               — fell back to All Playlists

        A Recent persistence failure NEVER blocks navigation and NEVER
        escapes as a raw exception; it emits persistenceFailed("recent")."""
        if self._coordinator is None:
            return "not_found"
        result = self._coordinator.open_playlist(playlist_id)
        if not result.recent_persisted and result.opened:
            self.persistenceFailed.emit("recent")
        return result.code

    @Slot()
    def open_all_playlists(self) -> None:
        if self._coordinator is not None:
            self._coordinator.open_all_playlists()

    @Slot(str, result=str)
    def create_and_open_playlist(self, name: str) -> str:
        """R3-03/04 Create + open. Returns a stable result code:

            "created"                 — created + opened, Recent persisted
            "created_recent_unsaved"  — created + opened, Recent write failed
            "conflict"                — duplicate name (logical, no signal)
            "invalid"                 — invalid name (logical, no signal)
            "persistence_failed"      — durable create write failed
            "not_found"               — service/coordinator unavailable

        The EXACT Playlist returned by create_playlist is opened (never a
        re-fetch by position)."""
        if self._playlist_service is None or self._coordinator is None:
            return "not_found"
        try:
            created = self._playlist_service.create_playlist(name)
        except PlaylistNameConflictError:
            return "conflict"
        except PlaylistNameInvalidError:
            return "invalid"
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("create")
            return "persistence_failed"
        result = self._coordinator.open_playlist(created.playlist_id)
        if not result.recent_persisted and result.opened:
            self.persistenceFailed.emit("recent")
            return "created_recent_unsaved"
        return "created"

    @Slot(str, str, result=str)
    def rename_playlist(self, playlist_id: str, new_name: str) -> str:
        """R3-04 rename with stable result codes:

        "renamed"             — durable success
        "no_change"           — same name (no write, no notify)
        "invalid"             — invalid name (logical)
        "conflict"            — duplicate name (logical)
        "not_found"           — playlist missing
        "persistence_failed"  — durable write failed (signal emitted)
        """
        if self._playlist_service is None:
            return "not_found"
        if self._playlist_service.get_playlist(playlist_id) is None:
            return "not_found"
        try:
            changed = self._playlist_service.rename_playlist(playlist_id, new_name)
        except PlaylistNameConflictError:
            return "conflict"
        except PlaylistNameInvalidError:
            return "invalid"
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("rename")
            return "persistence_failed"
        return "renamed" if changed else "no_change"

    @Slot(str, result=str)
    def delete_playlist(self, playlist_id: str) -> str:
        """R3-04 delete codes: "deleted" | "not_found" | "persistence_failed".
        The Delete dialog closes ONLY on "deleted"."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        if not self._run_mutation(
            "delete", lambda: self._playlist_service.delete_playlist(playlist_id)
        ):
            return "persistence_failed"
        return "deleted"

    @Slot(str, result=str)
    def pin_playlist(self, playlist_id: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        result = self._run_mutation(
            "pin", lambda: self._playlist_service.pin_playlist(playlist_id)
        )
        if result is None:
            return "persistence_failed"
        return "updated" if result else "no_change"

    @Slot(str, result=str)
    def unpin_playlist(self, playlist_id: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        result = self._run_mutation(
            "unpin", lambda: self._playlist_service.unpin_playlist(playlist_id)
        )
        if result is None:
            return "persistence_failed"
        return "updated" if result else "no_change"

    @Slot(str, str, result=str)
    def set_custom_cover(self, playlist_id: str, path: str) -> str:
        """R3-04 appearance codes (cover)."""
        local_path = local_path_from_url(path)
        if local_path is None or self._playlist_service is None:
            return "invalid"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        if not self._run_mutation(
            "cover",
            lambda: (
                self._playlist_service.set_custom_cover(playlist_id, local_path)
                is not None
            ),
        ):
            return "persistence_failed"
        return "updated"

    @Slot(str, QUrl, result=str)
    def set_custom_cover_from_url(self, playlist_id: str, url: QUrl) -> str:
        path = local_path_from_url(url)
        if path is None or self._playlist_service is None:
            return "invalid"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        if not self._run_mutation(
            "cover",
            lambda: (
                self._playlist_service.set_custom_cover(playlist_id, path) is not None
            ),
        ):
            return "persistence_failed"
        return "updated"

    @Slot(str, result=str)
    def remove_custom_cover(self, playlist_id: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        result = self._run_mutation(
            "cover",
            lambda: self._playlist_service.remove_custom_cover(playlist_id),
        )
        if result is None:
            return "persistence_failed"
        return "updated" if result else "no_change"

    @Slot(str, str, str, str, str, list, float, str, result=str)
    def apply_visual_appearance(
        self,
        playlist_id: str,
        cover_action: str,
        cover_source_path: str,
        hero_mode: str,
        hero_solid_color: str,
        hero_gradient_colors: list,
        hero_gradient_angle: float,
        hero_image_source: str,
    ) -> str:
        """R3-06 ONE application transaction for the whole appearance.
        Codes: "updated" | "no_change" | "invalid" | "asset_rejected" |
        "not_found" | "persistence_failed"."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        try:
            result = self._playlist_service.apply_visual_appearance(
                playlist_id,
                cover_action=cover_action,
                cover_source_path=cover_source_path or None,
                hero_mode=hero_mode,
                hero_solid_color=hero_solid_color,
                hero_gradient_colors=tuple(hero_gradient_colors),
                hero_gradient_angle=float(hero_gradient_angle),
                hero_image_source=hero_image_source or None,
            )
        except ValueError:
            return "invalid"
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("appearance")
            return "persistence_failed"
        return result

    @Slot(str, result=str)
    def set_hero_auto(self, playlist_id: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        result = self._run_mutation(
            "hero", lambda: self._playlist_service.set_hero_auto(playlist_id)
        )
        if result is None:
            return "persistence_failed"
        return "updated" if result else "no_change"

    @Slot(str, str, result=str)
    def set_hero_solid(self, playlist_id: str, color: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        try:
            ok = self._run_mutation(
                "hero",
                lambda: self._playlist_service.set_hero_solid(playlist_id, color),
            )
        except ValueError:
            return "invalid"
        return "updated" if ok else "persistence_failed"

    @Slot(str, list, float, result=str)
    def set_hero_gradient(self, playlist_id: str, colors: list, angle: float) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        try:
            ok = self._run_mutation(
                "hero",
                lambda: self._playlist_service.set_hero_gradient(
                    playlist_id, tuple(str(color) for color in colors), angle
                ),
            )
        except (TypeError, ValueError):
            return "invalid"
        return "updated" if ok else "persistence_failed"

    @Slot(str, QUrl, result=str)
    def set_custom_hero_from_url(self, playlist_id: str, url: QUrl) -> str:
        path = local_path_from_url(url)
        if path is None or self._playlist_service is None:
            return "invalid"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        if not self._run_mutation(
            "hero",
            lambda: (
                self._playlist_service.set_custom_hero_image(playlist_id, path)
                is not None
            ),
        ):
            return "persistence_failed"
        return "updated"

    @Slot(str, str, result=str)
    def add_track(self, playlist_id: str, path: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        if not self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track(playlist_id, Path(path)),
        ):
            return "persistence_failed"
        return "added"

    @Slot(str, int, str, result=str)
    def insert_track(self, playlist_id: str, index: int, path: str) -> str:
        """P0-01: restore a removed track at its EXACT original position.
        R3-04 codes: "restored" | "already_present" | "not_found" |
        "persistence_failed". EXACTLY this single signature (R2 P1-01).

        The service returns False for a LOGICAL duplicate (already present)
        — that is never a persistence failure."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        try:
            restored = self._playlist_service.insert_track(playlist_id, index, path)
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("insert_track")
            return "persistence_failed"
        return "restored" if restored else "already_present"

    @Slot(int, result=str)
    def remove_track(self, index: int) -> str:
        """R3-04 remove codes: "removed" | "invalid_index" | "not_found" |
        "persistence_failed". Registered as ``remove_track(int)`` in the
        QObject metaobject (R2 P1-01)."""
        playlist_id = self._current_playlist_id()
        if self._playlist_service is None or not playlist_id:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        if not (0 <= index < len(playlist.track_paths)):
            return "invalid_index"
        if not self._run_mutation(
            "remove_track",
            lambda: self._playlist_service.remove_track(playlist_id, index),
        ):
            return "persistence_failed"
        return "removed"

    @Slot(int, int, result=str)
    def move_track(self, from_index: int, to_index: int) -> str:
        """R3-04 move codes: "moved" | "no_change" | "invalid_index" |
        "not_found" | "persistence_failed"."""
        playlist_id = self._current_playlist_id()
        if self._playlist_service is None or not playlist_id:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        if not (0 <= from_index < len(playlist.track_paths)):
            return "invalid_index"
        result = self._run_mutation(
            "move_track",
            lambda: self._playlist_service.move_track(
                playlist_id, from_index, to_index
            ),
        )
        if result is None:
            return "persistence_failed"
        return "moved" if result else "no_change"

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

    @Slot(str, str, result=str)
    def add_track_to_playlist(self, playlist_id: str, path: str) -> str:
        """Cross-feature (Library → Playlist): add a track by id.
        R3-04 codes: "added" | "already_present" | "not_found" |
        "persistence_failed"."""
        if self._playlist_service is None:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        if str(Path(path)) in playlist.track_paths:
            return "already_present"
        if not self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track(playlist_id, Path(path)),
        ):
            return "persistence_failed"
        return "added"
