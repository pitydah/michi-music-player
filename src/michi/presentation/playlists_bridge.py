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
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistPaletteExtractorPort
from michi.domain.library_catalog import (
    MediaAvailability,
    media_playback_blocked,
)
from michi.domain.playback_session import PlaybackSequenceEntry
from michi.domain.playlist import (
    MAX_DESCRIPTION_LENGTH,
    PlaylistHeroMode,
    PlaylistTrackReference,
)

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
    # PL-10-FINAL-02: el catálogo canónico de Add Tracks cambia SOLO cuando
    # cambia la Library real (nunca por la búsqueda global de Library UI).
    trackCatalogChanged = Signal()

    def __init__(
        self,
        playlist_service: PlaylistService | None = None,
        playlist_navigation: PlaylistNavigationCoordinator | None = None,
        navigation_service: NavigationService | None = None,
        library: LibraryService | None = None,
        playback_coordinator=None,
        track_resolver: LibraryTrackResolver | None = None,
        parent: QObject | None = None,
        palette_extractor: PlaylistPaletteExtractorPort | None = None,
    ) -> None:
        super().__init__(parent)
        self._playlist_service = playlist_service
        self._coordinator = playlist_navigation
        self._navigation = navigation_service
        self._library = library
        self._playback_coordinator = playback_coordinator
        # PLAYLISTS IDENTITY RECOVERY (2.1): LibraryTrackResolver es la ONE
        # authority de resolución TrackId ↔ path/availability — el bridge
        # NUNCA implementa una resolución paralela. Sin resolver inyectado
        # (tests/headless) se construye sobre la misma library.
        self._track_resolver = track_resolver
        if self._track_resolver is None and library is not None:
            self._track_resolver = LibraryTrackResolver(library)
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
        # PL-10-FINAL-02: catálogo canónico de Add Tracks — derivado de
        # LibraryService.state.tracks (NO visible_tracks/search state).
        self._add_track_candidate_rows_cache: list[dict] | None = None
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
        self._add_track_candidate_rows_cache = None  # PL-10-FINAL-02
        self._rows_cache = None
        self.playlists_changed.emit()
        self.trackCatalogChanged.emit()

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

    # PLAYLISTS POST-MERGE IDENTITY RECOVERY (2.1): LibraryTrackResolver
    # es la ÚNICA autoridad de resolución. Política (R4):
    #   track_id presente  → resolver.resolve_ref(track_id); si no resuelve
    #                       → UNAVAILABLE. El fallback path NUNCA se usa
    #                       para reidentificar (adversarial: T2 ocupando el
    #                       viejo path de T1 jamás se presenta como T1).
    #   track_id vacío     → miembro legacy (V1/V2): fallback path lookup.
    #
    # Playable = resolvable AND effective availability no bloqueada
    # (source observation + media observation compuestas por el resolver).

    @staticmethod
    def _stable_track_id(track) -> str:
        """Stable catalog identity of a TrackRef — '' when the record (or
        a legacy test harness fake) predates the catalog."""
        return getattr(track, "track_id", "") or ""

    def _resolve_member_track(self, ref) -> object | None:
        """TrackRef actual de UN miembro (identidad o legacy por path) —
        SIN considerar playability. None si la identidad no resuelve."""
        resolver = self._track_resolver
        if resolver is None:
            return None
        if ref.track_id:
            # NUNCA rebinding por fallback: identidad estable decide.
            return resolver.resolve_ref(ref.track_id)
        if ref.fallback_path:
            # Legacy path-only: lookup por el índice cache (O(P) — nunca
            # resolve lineal por miembro). El índice es la MISMA fuente
            # del resolver (state.tracks), no una autoridad paralela.
            return self._build_trackref_index().get(ref.fallback_path)
        return None

    def _track_playback_blocked(self, track) -> bool:
        """Availability compuesta vía resolver; para refs legacy/harness
        que no exponen source id, la observación media directa (UNKNOWN →
        no bloqueado). El resolver sigue siendo la autoridad para tracks
        con contrato TrackRef completo."""
        resolver = self._track_resolver
        if resolver is None:
            return False
        if not hasattr(track, "library_source_id"):
            availability = getattr(track, "availability", MediaAvailability.UNKNOWN)
            return media_playback_blocked(availability)
        return media_playback_blocked(resolver.effective_availability(track))

    def _member_is_playable(self, ref, track) -> bool:
        """Effective availability del miembro: el resolver compone media +
        source; un track con id que no es playable se marca unavailable."""
        resolver = self._track_resolver
        if resolver is None:
            return True  # sin library truth: snapshot crudo (headless)
        if ref.track_id:
            return resolver.resolve_playable_path(ref.track_id) is not None
        if track is not None:
            return not self._track_playback_blocked(track)
        return False

    def _resolve_playable_member(self, ref):
        """(track, current_path) cuando el miembro es PLAYABLE; None
        cuando no resuelve o su availability bloquea la reproducción
        (MISSING / SOURCE_OFFLINE / ACCESS_DENIED / IO_ERROR)."""
        resolver = self._track_resolver
        if resolver is None:
            return None
        if ref.track_id:
            path = resolver.resolve_playable_path(ref.track_id)
            if path is None:
                return None
            track = resolver.resolve_ref(ref.track_id)
            return track, str(path)
        track = (
            self._build_trackref_index().get(ref.fallback_path)
            if ref.fallback_path
            else None
        )
        if track is None:
            return None
        if self._track_playback_blocked(track):
            return None
        return track, str(track.file_path)

    def _playlist_member_paths(self, playlist) -> list[str]:
        """Membership paths WITH TrackId-first resolution: for every
        member the CURRENT track path wins (relocation-safe); a member the
        library cannot resolve keeps its persisted fallback path so the
        visual row/count stays truthful about the membership."""
        paths: list[str] = []
        for ref in playlist.references():
            track = self._resolve_member_track(ref)
            if track is not None:
                paths.append(str(track.file_path))
            else:
                paths.append(ref.fallback_path)
        return paths

    def _references_for_paths(self, paths) -> list[PlaylistTrackReference]:
        """Library → Playlist entry seam (identity recovery, Iteración 2):
        every incoming Library path becomes a REAL reference
        ``PlaylistTrackReference(track_id=..., fallback_path=current path)``
        — never a path-only member. A path the library cannot resolve stays
        a legacy path-only reference ("" id, honest fallback); the system
        never invents TrackIds."""
        references: list[PlaylistTrackReference] = []
        if self._library is None:
            for raw in paths:
                path = str(Path(raw))
                references.append(
                    PlaylistTrackReference(track_id="", fallback_path=path)
                )
            return references
        index = self._build_trackref_index()
        for raw in paths:
            path = str(Path(raw))
            track = index.get(path)
            if track is not None:
                references.append(
                    PlaylistTrackReference(
                        track_id=self._stable_track_id(track),
                        fallback_path=str(track.file_path),
                    )
                )
            else:
                references.append(
                    PlaylistTrackReference(track_id="", fallback_path=path)
                )
        return references

    def _play_entries_for_playlist(self, playlist) -> list[PlaybackSequenceEntry]:
        """Playable sequence entries for ONE playlist, TrackId-first:
        every member resolves through the LibraryTrackResolver to its
        CURRENT playable path (effective availability compuesta: source +
        media) and carries its stable ``library_track_id``. Members that
        do not resolve OR whose availability blocks playback (MISSING /
        SOURCE_OFFLINE / ACCESS_DENIED / IO_ERROR) are skipped — never
        sent to the engine; the membership itself is never deleted."""
        if self._library is None:
            return [
                PlaybackSequenceEntry(file_path=Path(path), title="")
                for path in playlist.track_paths
            ]
        entries: list[PlaybackSequenceEntry] = []
        for ref in playlist.references():
            resolved = self._resolve_playable_member(ref)
            if resolved is None:
                continue  # no resuelve o no playable → nunca al motor
            track, current_path = resolved
            entries.append(
                PlaybackSequenceEntry(
                    file_path=Path(current_path),
                    title=track.title or track.display_name,
                    library_track_id=self._stable_track_id(track)
                    or (ref.track_id or None),
                )
            )
        return entries

    def _playlist_queue_pairs(self, playlist) -> list[tuple[Path, str | None]]:
        """Queue pairs (current playable path, stable TrackId) — TrackId-
        first resolution through the resolver; relocation-safe. Members
        whose availability blocks playback are skipped (nunca entran a la
        Queue)."""
        if self._library is None:
            return [(Path(path), None) for path in playlist.track_paths]
        pairs: list[tuple[Path, str | None]] = []
        for ref in playlist.references():
            resolved = self._resolve_playable_member(ref)
            if resolved is None:
                continue
            track, current_path = resolved
            pairs.append(
                (
                    Path(current_path),
                    self._stable_track_id(track) or (ref.track_id or None),
                )
            )
        return pairs

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

    @Slot(list, int)
    def request_draft_palette(self, source_paths: list, generation: int) -> None:
        """PL-10-FINAL-07: palette del DRAFT cover para el preview WYSIWYG
        del editor. Las FUENTES vienen del draft (replace/keep/automatic
        mosaic) — nunca la palette persistida de otro artwork. Cada source:
        path local o file:/// serializado normalizado con local_path_from_url;
        remote URLs rechazadas; inexistentes ignoradas; orden preservado;
        dedupe. Sin fuentes válidas → emite de inmediato la palette neutral
        (QML nunca queda en pending eterno). El generation token QML
        descarta callbacks stale. NUNCA se persiste — preview puro."""
        if self._palette_extractor is None:
            return
        sources: list[str] = []
        seen: set[str] = set()
        for raw in source_paths or ():
            local = local_path_from_url(str(raw))
            if local is None:
                continue  # remote/malformed: never touches the filesystem
            path_str = str(local)
            if path_str in seen:
                continue
            try:
                if not Path(path_str).is_file():
                    continue
            except OSError:
                continue
            seen.add(path_str)
            sources.append(path_str)
        if not sources:
            self.draftPaletteReady.emit(generation, list(_DEFAULT_HERO_PALETTE))
            return
        self._palette_extractor.request_palette(
            tuple(sources),
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
            # Identity recovery: duración y mosaico resuelven la ubicación
            # ACTUAL de cada miembro (TrackId-first); el path persistido es
            # solo un snapshot.
            current_paths = tuple(self._playlist_member_paths(playlist))
            mosaic = self._mosaic_for_paths(current_paths, index)
            row = {
                "playlistId": playlist.playlist_id,
                "name": playlist.name,
                "description": playlist.description,
                "trackCount": len(playlist.references()),
                "durationMs": self._duration_for_paths(current_paths),
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
        return self._duration_for_paths(tuple(self._playlist_member_paths(playlist)))

    def _get_selected_playlist_mosaic_artworks(self) -> list[str]:
        playlist = self._selected()
        if playlist is None:
            return []
        return self._mosaic_for_paths(
            tuple(self._playlist_member_paths(playlist)),
            self._build_artwork_index(),
        )

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
        # 2.1: la paleta automática extrae del artwork ACTUAL de los
        # miembros (relocation-safe) — nunca de los fallbacks persistidos.
        mosaic = self._mosaic_for_paths(
            tuple(self._playlist_member_paths(playlist)),
            self._build_artwork_index(),
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
        for ref in playlist.references():
            track = (
                self._resolve_member_track(ref) if self._library is not None else None
            )
            current_path = (
                str(track.file_path) if track is not None else ref.fallback_path
            )
            rows.append(
                {
                    "displayName": (
                        track.display_name
                        if track is not None
                        else Path(current_path).stem
                    ),
                    "path": current_path,
                    "trackId": ref.track_id,
                }
            )
        return rows

    def _get_playlist_track_rows(self) -> list[dict]:
        """PL-FINAL-14/16/17: canonical detail projection. Every row
        carries ``canonicalIndex`` (its position in the canonical playlist
        — NEVER the filtered-list index) and explicit availability
        metadata. When a local search query is active the rows are FILTERED
        (title/artist/album, case-insensitive) but every visible row keeps
        its canonicalIndex; missing rows are never silently dropped.

        Identity recovery (Iteración 2): availability resolves TrackId-
        FIRST — a member whose stable TrackId the library resolves renders
        with the CURRENT track (path/title/artwork), even when its
        persisted fallback path moved."""
        playlist = self._selected()
        if playlist is None:
            return []
        index = self._build_artwork_index()
        query = " ".join(self._playlist_search_query.casefold().split())
        rows = []
        for canonical_index, ref in enumerate(playlist.references()):
            track = self._resolve_member_track(ref)
            if track is not None:
                row = self._track_row(track, index, canonical_index)
                row["trackId"] = self._stable_track_id(track)
                # 2.1: available = PLAYABLE (effective availability del
                # resolver): un track offline/missing sigue visible pero no
                # reproducible.
                playable = self._member_is_playable(ref, track)
                row["available"] = playable
                row["unavailableReason"] = "" if playable else "not_playable"
            else:
                fallback = ref.fallback_path
                stem = Path(fallback).stem if fallback else "Unknown track"
                row = {
                    "displayName": stem,
                    "title": stem,
                    "artist": "",
                    "album": "",
                    "durationMs": 0,
                    "path": fallback,
                    "trackId": ref.track_id,
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
        Identity recovery (Iteración 2): TrackId-first resolution."""
        playlist = self._selected()
        if playlist is None or self._library is None:
            return 0
        return sum(
            1
            for ref in playlist.references()
            if self._resolve_playable_member(ref) is None
        )

    def _get_playlist_available_count(self) -> int:
        """PL-FINAL-A05: count of tracks the library CAN resolve — the
        hero Play/Shuffle contract operates only on playable tracks.
        Identity recovery (Iteración 2): TrackId-first resolution."""
        playlist = self._selected()
        if playlist is None or self._library is None:
            return 0
        return sum(
            1
            for ref in playlist.references()
            if self._resolve_playable_member(ref) is not None
        )

    def _get_playlist_track_paths(self) -> list[str]:
        """PL-FINAL-A08: CANONICAL membership paths (legacy projection) —
        NEVER filtered by the local search. The Add Tracks picker derives
        'In playlist' from selectedPlaylistTrackIds PRIMERO (identidad) y
        de esta proyección solo como fallback legacy."""
        playlist = self._selected()
        if playlist is None:
            return []
        return list(playlist.track_paths)

    def _get_selected_playlist_track_ids(self) -> list[str]:
        """PLAYLISTS IDENTITY RECOVERY (2.1): membership UI truth =
        TrackId. Los ids estables de los miembros (sin "" legacy) — el Add
        Tracks picker decide 'already present' por identidad, no por path
        snapshot (un track relocado T1@/B sigue 'present' aunque su
        fallback persistido diga /A)."""
        playlist = self._selected()
        if playlist is None:
            return []
        return [ref.track_id for ref in playlist.references() if ref.track_id]

    def _get_selected_playlist_legacy_member_paths(self) -> list[str]:
        """REVIEW SEAL: paths de miembros LEGACY (track_id vacío) — el
        único caso en que el path decide 'already present' en el picker
        (un miembro con id que el catálogo conoce NUNCA se compara por
        snapshot: dos ids distintos pueden compartir path)."""
        playlist = self._selected()
        if playlist is None:
            return []
        return [
            ref.fallback_path
            for ref in playlist.references()
            if not ref.track_id and ref.fallback_path
        ]

    def _get_add_track_candidate_rows(self) -> list[dict]:
        """PL-10-FINAL-02: canonical Add Tracks catalog — LibraryService
        .state.tracks (the REAL library), never visible_tracks/search
        projection of the Library UI. Cached; rebuilt ONLY when the
        Library revision changes. O(T + artwork index)."""
        if self._library is None:
            return []
        if self._add_track_candidate_rows_cache is None:
            artwork_index = self._build_artwork_index()
            rows: list[dict] = []
            for track in self._library.state.tracks:
                path = str(track.file_path)
                rows.append(
                    {
                        "path": path,
                        "trackId": self._stable_track_id(track),
                        "displayName": track.display_name,
                        "title": track.title or track.display_name,
                        "artist": track.artist,
                        "album": track.album,
                        "durationMs": track.duration_ms,
                        "qualityLabel": make_track_quality_label(track),
                        "artworkPath": artwork_index.get(path, ""),
                    }
                )
            self._add_track_candidate_rows_cache = rows
        return self._add_track_candidate_rows_cache

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
    # 2.1: membership UI truth por TrackId (picker 'already present').
    selectedPlaylistTrackIds = Property(
        list, _get_selected_playlist_track_ids, notify=playlists_changed
    )
    # REVIEW SEAL: paths de miembros legacy (sin id) para el picker.
    selectedPlaylistLegacyMemberPaths = Property(
        list, _get_selected_playlist_legacy_member_paths, notify=playlists_changed
    )
    # PL-10-FINAL-02: catálogo canónico de Add Tracks (independiente de la
    # búsqueda global de Library).
    addTrackCandidateRows = Property(
        list, _get_add_track_candidate_rows, notify=trackCatalogChanged
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
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        reference = self._references_for_paths([path])[0]
        result = self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track_references(
                playlist_id, (reference,)
            ),
        )
        if result is None:
            return "persistence_failed"
        return "added" if result == 1 else "already_present"

    @Slot(str, int, str, result=str)
    def insert_track(self, playlist_id: str, index: int, path: str) -> str:
        """P0-01 LEGACY path-only: restore a removed track at its EXACT
        original position (sin identidad — el caller con TrackId debe usar
        insert_track_reference).
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

    @Slot(str, int, str, str, result=str)
    def insert_track_reference(
        self, playlist_id: str, index: int, track_id: str, path: str
    ) -> str:
        """P0-01 IDENTITY-SAFE restore (PLAYLISTS IDENTITY RECOVERY 2.1):
        el Undo restaura la REFERENCIA congelada (track_id + path actual)
        capturada al remover — tras una relocation el track recupera su
        MISMA identidad (T1), nunca un miembro path-only nuevo.
        R3-04 codes: "restored" | "already_present" | "not_found" |
        "persistence_failed"."""
        if self._playlist_service is None:
            return "not_found"
        if not self._playlist_service.contains_playlist(playlist_id):
            return "not_found"
        reference = PlaylistTrackReference(
            track_id=track_id or "", fallback_path=path or ""
        )
        result = self._run_mutation(
            "insert_track",
            lambda: self._playlist_service.insert_track_reference(
                playlist_id, index, reference
            ),
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
        Identity recovery (Iteración 2): cada miembro se resuelve TrackId-
        first a su ubicación ACTUAL y transporta su ``library_track_id``
        hasta la sesión (relocation-safe). Without a library (tests/
        headless) there is no availability truth — the raw snapshot is
        used."""
        if self._playback_coordinator is None:
            return
        playlist = (
            self._playlist_service.get_playlist(playlist_id)
            if self._playlist_service is not None
            else None
        )
        if playlist is None:
            return
        if self._library is None:
            self._playback_coordinator.play_playlist_paths(
                playlist_id, list(playlist.track_paths)
            )
            return
        entries = self._play_entries_for_playlist(playlist)
        if not entries:
            return
        self._playback_coordinator.play_playlist_entries(playlist_id, entries)

    @Slot(int)
    def play_playlist_track(self, index: int) -> None:
        """Playlist Detail track click → PLAYLIST context at index N.
        PL-FINAL-A05: un track no resoluble (unavailable) nunca se envía
        al motor (cuando hay library truth). Identity recovery: el índice
        es la posición CANÓNICA del miembro; la secuencia se resuelve
        TrackId-first con identidad hasta la sesión."""
        if self._playback_coordinator is None:
            return
        playlist_id = self._current_playlist_id()
        playlist = (
            self._playlist_service.get_playlist(playlist_id)
            if playlist_id and self._playlist_service is not None
            else None
        )
        if playlist is None:
            return
        count = len(playlist.references())
        if not (0 <= index < count):
            # Legacy contract: un índice fuera de rango clamp a 0
            # (comportamiento histórico del coordinator).
            index = 0
        if self._library is None:
            self._playback_coordinator.play_playlist_paths(
                playlist_id, list(playlist.track_paths), start_index=index
            )
            return
        entries = self._play_entries_for_playlist(playlist)
        if not entries:
            return
        # El miembro clickeado debe ser PLAYABLE para arrancar (2.1:
        # availability efectiva — un track offline/missing no arranca).
        references = playlist.references()
        if self._resolve_playable_member(references[index]) is None:
            return
        # start = posición del miembro clickeado DENTRO de la secuencia
        # playable (los unavailable previos no ocupan lugar en el motor).
        start = sum(
            1
            for previous in references[:index]
            if self._resolve_playable_member(previous) is not None
        )
        self._playback_coordinator.play_playlist_entries(
            playlist_id, entries, start_index=start
        )

    @Slot(str)
    def queue_playlist(self, playlist_id: str) -> None:
        """EXPLICIT Queue intent through the coordinator (no private
        _queue access). PL-FINAL-A05: solo tracks disponibles (con library
        truth); sin library, snapshot crudo. Identity recovery: cada track
        entra a la Queue con su path ACTUAL + library_track_id estable."""
        if self._playback_coordinator is None:
            return
        playlist = (
            self._playlist_service.get_playlist(playlist_id)
            if self._playlist_service is not None
            else None
        )
        if playlist is None:
            return
        if self._library is None:
            paths = list(playlist.track_paths)
            if paths:
                self._playback_coordinator.queue_playlist_paths(playlist_id, paths)
            return
        pairs = self._playlist_queue_pairs(playlist)
        if pairs:
            self._playback_coordinator.queue_playlist_entries(playlist_id, pairs)

    @Slot()
    def queue_selected_playlist(self) -> None:
        pid = self._current_playlist_id()
        if pid:
            self.queue_playlist(pid)

    @Slot(str, list, result=dict)
    def add_tracks(self, playlist_id: str, paths: list) -> dict:
        """PL-FINAL-13: BATCH add tracks (one candidate, one persist, one
        notify). Identity recovery (Iteración 2): cada path de Library se
        convierte en una REFERENCIA real (track_id + fallback_path actual)
        antes de entrar al servicio — nunca miembros path-only cuando la
        identidad es conocida. Structured result for QML:

            {"status": "updated"|"no_change"|"not_found"|"persistence_failed",
             "addedCount": n, "alreadyPresentCount": m}

        A persistence failure NEVER reports success: status is
        "persistence_failed" and no partial mutation exists."""
        if self._playlist_service is None:
            return {"status": "not_found", "addedCount": 0, "alreadyPresentCount": 0}
        if not self._playlist_service.contains_playlist(playlist_id):
            return {"status": "not_found", "addedCount": 0, "alreadyPresentCount": 0}
        references = self._references_for_paths(list(paths))
        # Dedupe first-seen del input (misma semántica que el batch legacy):
        # los duplicados internos no cuentan como already.
        seen: set[str] = set()
        unique_references = []
        for ref in references:
            identity = ref.track_id or ref.fallback_path
            if identity in seen:
                continue
            seen.add(identity)
            unique_references.append(ref)
        try:
            added = self._playlist_service.add_track_references(
                playlist_id, unique_references
            )
        except PlaylistPersistenceError:
            self.persistenceFailed.emit("add_tracks")
            return {
                "status": "persistence_failed",
                "addedCount": 0,
                "alreadyPresentCount": 0,
            }
        already = max(0, len(unique_references) - added)
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
        # Valida contra la membresía CANÓNICA (references) — una playlist
        # id-only (track_paths normalizado a ()) sigue siendo mutable.
        member_count = len(playlist.references())
        valid = [i for i in indices if 0 <= i < member_count]
        if not valid:
            return "invalid_index"
        result = self._run_mutation(
            "remove_tracks",
            lambda: self._playlist_service.remove_tracks(playlist_id, valid),
        )
        if result is None:
            return "persistence_failed"
        return "removed" if result else "no_change"

    @Slot(list, result=dict)
    def remove_tracks_by_paths(self, paths: list) -> dict:
        """PL-10-FINAL-05: BATCH remove by PATH IDENTITY with a TRUTHFUL
        structured result. Positions are resolved from the CURRENT
        canonical playlist.track_paths snapshot AT INTENT TIME — never
        stale visual indices, never a filtered projection. Paths that
        vanished from the playlist are counted as missing (already gone),
        NOT silently dropped from the feedback. ONE persist, ONE notify.

        Result (same keys for EVERY status):
            {"status": "removed"|"no_change"|"invalid"|"not_found"|
                        "persistence_failed",
             "removedCount": int, "missingCount": int}"""
        playlist_id = self._current_playlist_id()
        if self._playlist_service is None or not playlist_id:
            return {"status": "not_found", "removedCount": 0, "missingCount": 0}
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return {"status": "not_found", "removedCount": 0, "missingCount": 0}
        unique = list(dict.fromkeys(str(p) for p in paths))
        if not unique:
            return {"status": "invalid", "removedCount": 0, "missingCount": 0}
        # PLAYLISTS IDENTITY RECOVERY (2.1): la selección llega con los
        # paths PROYECTADOS (ubicación actual de cada miembro tras
        # relocation) — se resuelven contra la membership CANÓNICA
        # (referencias por índice), nunca contra el snapshot persistido.
        playlist_refs = playlist.references()
        current_by_member: dict[str, int] = {}
        for canonical_index, ref in enumerate(playlist_refs):
            track = self._resolve_member_track(ref)
            shown_path = (
                str(track.file_path) if track is not None else (ref.fallback_path)
            )
            if shown_path:
                current_by_member.setdefault(shown_path, canonical_index)
        canonical = list(playlist.track_paths)
        position_by_path = {path: i for i, path in enumerate(canonical)}
        indices = []
        missing = 0
        for path in unique:
            canonical_index = current_by_member.get(path, -1)
            if canonical_index >= 0:
                indices.append(canonical_index)
            elif path in position_by_path:
                # Legacy: el path ES la membresía (V1/V2 path-only).
                indices.append(position_by_path[path])
            else:
                missing += 1
        if not indices:
            return {
                "status": "no_change",
                "removedCount": 0,
                "missingCount": missing,
            }
        result = self._run_mutation(
            "remove_tracks",
            lambda: self._playlist_service.remove_tracks(playlist_id, indices),
        )
        if result is None:
            return {
                "status": "persistence_failed",
                "removedCount": 0,
                "missingCount": missing,
            }
        return {
            "status": "removed" if result else "no_change",
            "removedCount": len(indices) if result else 0,
            "missingCount": missing,
        }

    @Slot(str, str, result=str)
    def add_track_to_playlist(self, playlist_id: str, path: str) -> str:
        """Cross-feature (Library → Playlist): add a track by its factual
        path. Identity recovery (Iteración 2): el path se resuelve a una
        REFERENCIA real (track_id + fallback_path actual) — el miembro
        persistido lleva la identidad estable del catálogo, nunca queda
        path-only cuando la identidad es conocida. El dedupe por TrackId
        del servicio evita duplicar el mismo track aunque su path haya
        cambiado.
        R3-04 codes: "added" | "already_present" | "not_found" |
        "persistence_failed"."""
        if self._playlist_service is None:
            return "not_found"
        playlist = self._playlist_service.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"
        reference = self._references_for_paths([path])[0]
        result = self._run_mutation(
            "add_tracks",
            lambda: self._playlist_service.add_track_references(
                playlist_id, (reference,)
            ),
        )
        if result is None:
            return "persistence_failed"
        return "added" if result == 1 else "already_present"
