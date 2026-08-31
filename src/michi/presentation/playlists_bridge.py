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
from michi.domain.playlist import MAX_DESCRIPTION_LENGTH, PlaylistHeroMode

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
    # PL-FINAL-B02: palette del DRAFT cover para el preview WYSIWYG del
    # editor (generation token QML; nunca se persiste). Nombre camelCase:
    # PySide6 expone señales Python con su nombre exacto en QML.
    draftPaletteReady = Signal(int, list)

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
        # PL-FINAL-18: duration-by-path index — resolve_trackref is
        # O(library); the index makes a playlist projection O(tracks).
        self._duration_index: dict[str, int] | None = None
        # PL-FINAL-A12: path → TrackRef index over the CURRENT Library
        # revision. resolve_trackref() is O(library) PER LOOKUP — every
        # detail projection (rows, unavailable count, playback filtering)
        # goes through THIS index. Rebuilt exactly once per library change.
        self._trackref_index: dict[str, object] | None = None
        self._rows_cache: list[dict] | None = None
        # PL-FINAL-14: playlist-LOCAL search (detail toolbar). Never
        # touches LibraryService search state; the query only filters the
        # current playlist projection.
        self._playlist_search_query: str = ""
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
        """PL-FINAL-A02/A03: la búsqueda local es TRANSIENT — nunca
        sobrevive al cambio de playlist ni a la salida del detalle."""
        self._playlist_search_query = ""
        self._rows_cache = None
        self.playlists_changed.emit()

    def _on_library_changed(self) -> None:
        """M9-R1J: playlist search projection reads LibraryService search
        state (query/active) and track metadata — react to library changes
        so searchPlaylists/searchPlaylistCount/playlistTrackRows recompute.
        The artwork index is rebuilt lazily ONCE on the next rows refresh."""
        self._artwork_index_dirty = True
        self._duration_index = None  # PL-FINAL-18: rebuild lazily
        self._trackref_index = None  # PL-FINAL-A12: rebuild lazily
        self._rows_cache = None
        self.playlists_changed.emit()

    def _build_trackref_index(self) -> dict[str, object]:
        """PL-FINAL-A12: canonical path → TrackRef, rebuilt EXACTLY ONCE
        per Library revision. All playlist detail projections are O(P)
        against this index — never O(P × T) linear resolve_trackref."""
        if self._trackref_index is None:
            index: dict[str, object] = {}
            if self._library is not None:
                for track in self._library.state.tracks:
                    index.setdefault(str(track.file_path), track)
            self._trackref_index = index
        return self._trackref_index

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
        index = self._build_duration_index()
        total = 0
        for path_str in track_paths:
            total += index.get(path_str, 0)
        return total

    def _build_duration_index(self) -> dict[str, int]:
        """PL-FINAL-18: path → duration_ms index, rebuilt ONLY when the
        Library revision changed (resolve_trackref is O(library) per
        lookup; the index makes playlist projections O(playlist tracks))."""
        if self._library is None:
            return {}
        if self._duration_index is None:
            index: dict[str, int] = {}
            for track in self._library.state.tracks:
                key = str(track.file_path)
                if key not in index:
                    index[key] = track.duration_ms
            self._duration_index = index
        return self._duration_index

    def _trackref_for_path(self, path: str):
        """PL-FINAL-A12: O(1) canonical lookup via the revision index."""
        return self._build_trackref_index().get(path)

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
            "heroFocalX": appearance.hero_focal_x,
            "heroFocalY": appearance.hero_focal_y,
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

    @Slot(str, int)
    def request_draft_palette(self, cover_path: str, generation: int) -> None:
        """PL-FINAL-B02: palette del DRAFT cover para el preview del editor
        de apariencia. La extracción es async; el QML dueño del generation
        token descarta callbacks stale (draft A que termina después de B
        nunca gana). NUNCA se persiste — es preview puro. Sin archivo
        válido: no request (el preview usa la palette neutral)."""
        if self._palette_extractor is None or not cover_path:
            return
        local = local_path_from_url(cover_path)
        if local is None:
            return
        try:
            if not Path(local).is_file():
                return
        except OSError:
            return
        sources = (str(local),)
        self._palette_extractor.request_palette(
            sources,
            lambda colors: self.draftPaletteReady.emit(generation, list(colors)),
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
                "description": playlist.description,
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

    def _get_selected_playlist_description(self) -> str:
        """PL-FINAL-DESCRIPTION: proyección SEGURA — un payload legacy
        corrupto/enorme nunca entra a QML; se clamp a la longitud máxima
        SIN reescribir el DB en load."""
        playlist = self._selected()
        if playlist is None:
            return ""
        description = playlist.description
        if not isinstance(description, str):
            return ""
        return description[:MAX_DESCRIPTION_LENGTH]

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
            ref = self._trackref_for_path(path) if self._library is not None else None
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
        """PL-FINAL-14/16/17: canonical detail projection. Every row
        carries ``canonicalIndex`` (its position in the canonical playlist
        — NEVER the filtered-list index) and explicit availability
        metadata. When a local search query is active the rows are FILTERED
        (title/artist/album, case-insensitive) but every visible row keeps
        its canonicalIndex; missing rows are never silently dropped."""
        playlist = self._selected()
        if playlist is None:
            return []
        index = self._build_artwork_index()
        query = " ".join(self._playlist_search_query.casefold().split())
        rows = []
        for canonical_index, path in enumerate(playlist.track_paths):
            ref = self._trackref_for_path(path) if self._library is not None else None
            if ref is not None:
                row = self._track_row(ref, index, canonical_index)
                row["available"] = True
                row["unavailableReason"] = ""
            else:
                stem = Path(path).stem
                row = {
                    "displayName": stem,
                    "title": stem,
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
                    "artworkPath": "",
                    "canonicalIndex": canonical_index,
                    "available": False,
                    "unavailableReason": "not_in_library",
                }
            if query:
                haystack = " ".join(
                    [row["title"], row["artist"], row["album"]]
                ).casefold()
                if query not in haystack:
                    continue
            rows.append(row)
        return rows

    def _track_row(
        self, ref, index: dict[str, str] | None = None, canonical_index: int = 0
    ) -> dict:
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
            "canonicalIndex": canonical_index,
        }

    def _get_playlist_search_query(self) -> str:
        return self._playlist_search_query

    @Slot(str)
    def set_playlist_search_query(self, query: str) -> None:
        """PL-FINAL-14: playlist-LOCAL search filter (never touches the
        global Library search). Empty/whitespace query clears the filter."""
        cleaned = " ".join(str(query).casefold().split())
        if cleaned == self._playlist_search_query:
            return
        self._playlist_search_query = cleaned
        self.playlists_changed.emit()

    def _get_playlist_unavailable_count(self) -> int:
        """PL-FINAL-16: honest count of tracks the library cannot resolve —
        the hero summary must explain '10 tracks · 36 min · 2 unavailable'.
        PL-FINAL-A12: O(P) against the revision index."""
        playlist = self._selected()
        if playlist is None or self._library is None:
            return 0
        index = self._build_trackref_index()
        return sum(1 for path in playlist.track_paths if path not in index)

    def _get_playlist_available_count(self) -> int:
        """PL-FINAL-A05: count of tracks the library CAN resolve — the
        hero Play/Shuffle contract operates only on playable tracks."""
        playlist = self._selected()
        if playlist is None or self._library is None:
            return 0
        index = self._build_trackref_index()
        return sum(1 for path in playlist.track_paths if path in index)

    def _get_playlist_track_paths(self) -> list[str]:
        """PL-FINAL-A08: CANONICAL membership paths — NEVER filtered by
        the local search. The Add Tracks picker derives 'In playlist'
        from THIS property, not from the filtered rows projection."""
        playlist = self._selected()
        if playlist is None:
            return []
        return list(playlist.track_paths)

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
    selectedPlaylistDescription = Property(
        str, _get_selected_playlist_description, notify=playlists_changed
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
    playlistSearchQuery = Property(
        str,
        _get_playlist_search_query,
        set_playlist_search_query,
        notify=playlists_changed,
    )
    playlistUnavailableCount = Property(
        int, _get_playlist_unavailable_count, notify=playlists_changed
    )
    playlistAvailableTrackCount = Property(
        int, _get_playlist_available_count, notify=playlists_changed
    )
    # PL-FINAL-A08: membership canónica SIN filtro (picker / undo / etc).
    selectedPlaylistTrackPaths = Property(
        list, _get_playlist_track_paths, notify=playlists_changed
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
        result = self._run_mutation(
            "delete", lambda: self._playlist_service.delete_playlist(playlist_id)
        )
        if result is None:
            return "persistence_failed"
        return "deleted" if result else "no_change"

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

    @Slot(str, str, str, str, str, list, float, str, float, float, result=str)
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
        hero_focal_x: float = 0.5,
        hero_focal_y: float = 0.5,
    ) -> str:
        """R3-06/PL-FINAL-02 ONE application transaction for the whole
        appearance. Codes: "updated" | "no_change" | "invalid" |
        "asset_rejected" | "not_found" | "persistence_failed".

        PL-FINAL-02: the QUrl boundary lives HERE — cover and hero sources
        are normalized to pure local filesystem paths BEFORE PlaylistService
        sees them. A file:/// URL from QML never reaches the filesystem as a
        raw string; remote/malformed schemes are rejected ("invalid")."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        cover_source = (
            local_path_from_url(cover_source_path) if cover_source_path else None
        )
        hero_source = (
            local_path_from_url(hero_image_source) if hero_image_source else None
        )
        if cover_source_path and cover_source is None:
            return "invalid"  # remote/malformed URL: never reaches the FS
        if hero_image_source and hero_source is None:
            return "invalid"
        try:
            result = self._playlist_service.apply_visual_appearance(
                playlist_id,
                cover_action=cover_action,
                cover_source_path=cover_source,
                hero_mode=hero_mode,
                hero_solid_color=hero_solid_color,
                hero_gradient_colors=tuple(hero_gradient_colors),
                hero_gradient_angle=float(hero_gradient_angle),
                hero_image_source=hero_source,
                hero_focal_x=float(hero_focal_x),
                hero_focal_y=float(hero_focal_y),
            )
        except ValueError:
            return "invalid"
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("appearance")
            return "persistence_failed"
        return result

    @Slot(str, str, result=str)
    def set_playlist_description(self, playlist_id: str, description: str) -> str:
        """PL-FINAL-05: real playlist description metadata. Codes:
        "updated" | "no_change" | "invalid" | "not_found" |
        "persistence_failed"."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        try:
            changed = self._playlist_service.set_playlist_description(
                playlist_id, description
            )
        except ValueError:
            return "invalid"
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("description")
            return "persistence_failed"
        return "updated" if changed else "no_change"

    @Slot(str, str, result=str)
    def add_track(self, playlist_id: str, path: str) -> str:
        if self._playlist_service is None:
            return "not_found"
        result = self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track(playlist_id, Path(path)),
        )
        if result is None:
            return "persistence_failed"
        return "added" if result else "already_present"

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
        result = self._run_mutation(
            "insert_track",
            lambda: self._playlist_service.insert_track(playlist_id, index, path),
        )
        if result is None:
            return "persistence_failed"
        return "restored" if result else "already_present"

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
        result = self._run_mutation(
            "remove_track",
            lambda: self._playlist_service.remove_track(playlist_id, index),
        )
        if result is None:
            return "persistence_failed"
        return "removed" if result else "no_change"

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
        """PL-FINAL-A05: PLAYLIST playback operates ONLY on tracks the
        library can resolve. Missing/unavailable paths NEVER reach the
        audio engine — the coordinator receives the available snapshot.
        Without a library (tests/headless) there is no availability truth
        — the raw snapshot is used."""
        if self._playback_coordinator is not None:
            playlist = (
                self._playlist_service.get_playlist(playlist_id)
                if self._playlist_service is not None
                else None
            )
            if playlist is None:
                return
            paths = list(playlist.track_paths)
            if self._library is not None:
                index = self._build_trackref_index()
                available = [p for p in paths if p in index]
                if not available:
                    return
                paths = available
            self._playback_coordinator.play_playlist_paths(playlist_id, paths)

    @Slot(int)
    def play_playlist_track(self, index: int) -> None:
        """Playlist Detail track click → PLAYLIST context at index N.
        PL-FINAL-A05: un track no resoluble (unavailable) nunca se envía
        al motor (cuando hay library truth)."""
        if self._playback_coordinator is not None:
            playlist_id = self._current_playlist_id()
            playlist = (
                self._playlist_service.get_playlist(playlist_id)
                if playlist_id and self._playlist_service is not None
                else None
            )
            if playlist is None:
                return
            if not (0 <= index < len(playlist.track_paths)):
                # Legacy contract: un índice fuera de rango clamp a 0
                # (comportamiento histórico del coordinator).
                index = 0
            paths = list(playlist.track_paths)
            if self._library is not None:
                path = paths[index]
                index_map = self._build_trackref_index()
                if path not in index_map:
                    return
                available = [p for p in paths if p in index_map]
                start = available.index(path)
                self._playback_coordinator.play_playlist_paths(
                    playlist_id, available, start_index=start
                )
                return
            self._playback_coordinator.play_playlist_paths(
                playlist_id, paths, start_index=index
            )

    @Slot(str)
    def queue_playlist(self, playlist_id: str) -> None:
        """EXPLICIT Queue intent through the coordinator (no private
        _queue access). PL-FINAL-A05: solo paths disponibles (con library
        truth); sin library, snapshot crudo."""
        if self._playback_coordinator is not None:
            playlist = (
                self._playlist_service.get_playlist(playlist_id)
                if self._playlist_service is not None
                else None
            )
            if playlist is None:
                return
            paths = list(playlist.track_paths)
            if self._library is not None:
                index_map = self._build_trackref_index()
                paths = [p for p in paths if p in index_map]
            if paths:
                self._playback_coordinator.queue_playlist_paths(playlist_id, paths)

    @Slot()
    def queue_selected_playlist(self) -> None:
        pid = self._current_playlist_id()
        if pid:
            self.queue_playlist(pid)

    @Slot(str, list, result=dict)
    def add_tracks(self, playlist_id: str, paths: list) -> dict:
        """PL-FINAL-13: BATCH add tracks (one candidate, one persist, one
        notify). Structured result for QML:

            {"status": "updated"|"no_change"|"not_found"|"persistence_failed",
             "addedCount": n, "alreadyPresentCount": m}

        A persistence failure NEVER reports success: status is
        "persistence_failed" and no partial mutation exists."""
        if self._playlist_service is None:
            return {"status": "not_found", "addedCount": 0, "alreadyPresentCount": 0}
        if not self._playlist_service.contains_playlist(playlist_id):
            return {"status": "not_found", "addedCount": 0, "alreadyPresentCount": 0}
        try:
            added, already = self._playlist_service.add_tracks(playlist_id, paths)
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("add_tracks")
            return {
                "status": "persistence_failed",
                "addedCount": 0,
                "alreadyPresentCount": 0,
            }
        if added == 0:
            return {
                "status": "no_change",
                "addedCount": 0,
                "alreadyPresentCount": already,
            }
        return {
            "status": "updated",
            "addedCount": added,
            "alreadyPresentCount": already,
        }

    @Slot(list, result=str)
    def remove_tracks(self, indices: list) -> str:
        """PL-FINAL-15: BATCH remove on the CURRENT playlist (single
        candidate, single persist). Codes: "removed" | "no_change" |
        "invalid_index" | "not_found" | "persistence_failed"."""
        playlist_id = self._current_playlist_id()
        if self._playlist_service is None or not playlist_id:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        valid = [i for i in indices if 0 <= i < len(playlist.track_paths)]
        if not valid:
            return "invalid_index"
        result = self._run_mutation(
            "remove_tracks",
            lambda: self._playlist_service.remove_tracks(playlist_id, valid),
        )
        if result is None:
            return "persistence_failed"
        return "removed" if result else "no_change"

    @Slot(list, result=str)
    def remove_tracks_by_paths(self, paths: list) -> str:
        """PL-FINAL-A01: BATCH remove by PATH IDENTITY (the multiselect
        contract). Positions are resolved from the CURRENT canonical
        playlist.track_paths snapshot AT INTENT TIME — never from stale
        visual indices, never from a filtered projection. Paths that
        vanished from the playlist are skipped truthfully (they are
        already gone). ONE persist, ONE notify. Codes: "removed" |
        "no_change" | "invalid" | "not_found" | "persistence_failed"."""
        playlist_id = self._current_playlist_id()
        if self._playlist_service is None or not playlist_id:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        unique = list(dict.fromkeys(str(p) for p in paths))
        if not unique:
            return "invalid"
        canonical = list(playlist.track_paths)
        position_by_path = {path: i for i, path in enumerate(canonical)}
        indices = [
            position_by_path[path] for path in unique if path in position_by_path
        ]
        if not indices:
            return "no_change"
        result = self._run_mutation(
            "remove_tracks",
            lambda: self._playlist_service.remove_tracks(playlist_id, indices),
        )
        if result is None:
            return "persistence_failed"
        return "removed" if result else "no_change"

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
        result = self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track(playlist_id, Path(path)),
        )
        if result is None:
            return "persistence_failed"
        return "added" if result else "already_present"
