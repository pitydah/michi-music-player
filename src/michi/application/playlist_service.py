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

import contextlib
import logging
import math
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from michi.application.errors import (
    PlaylistNameConflictError,
    PlaylistNameInvalidError,
    PlaylistPersistenceError,
)
from michi.application.ports import PlaylistArtworkStorePort, PlaylistsPort
from michi.domain.playlist import (
    MAX_DESCRIPTION_LENGTH,
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
    PreparedPlaylistAsset,
    new_playlist_id,
    normalize_navigation_state,
)

logger = logging.getLogger(__name__)

_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _canonical_color(value: str) -> str:
    color = value.strip()
    if not _HEX_COLOR.fullmatch(color):
        raise ValueError("color must use #RRGGBB format")
    return color.upper()


class PlaylistService:
    """Owns the ordered playlist collection and its navigation metadata
    (pinned/recent); mutates and persists truthfully (authoritative writes). M4-R1:
    playback authority lives in PlaybackSessionService + PlaylistPlaybackCoordinator;
    QueueService owns temporary Queue content only (never referenced here)."""

    def __init__(
        self,
        *,
        playlists_port: PlaylistsPort | None = None,
        artwork_store: PlaylistArtworkStorePort | None = None,
    ) -> None:
        self._port = playlists_port
        self._artwork_store = artwork_store
        self._playlists: list[Playlist] = list(
            playlists_port.load() if playlists_port is not None else ()
        )
        # Truthful persistence baseline: rollback target on storage failure.
        self._persisted: tuple[Playlist, ...] = tuple(self._playlists)
        self._persisted_nav = PlaylistNavigationState()
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
        self._persisted_nav = self._nav
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

    def _commit_playlists(self, candidate: tuple[Playlist, ...]) -> bool:
        """PUBLISH AFTER DURABILITY (R2 P1-03): the immutable candidate is
        written BEFORE it becomes published state.

        R3-12: an identical candidate is a NO-OP — zero persistence, zero
        publish, zero notify. Returns True only when something changed."""
        if candidate == tuple(self._playlists):
            return False
        if self._port is not None:
            self._port.save(candidate)  # raises PlaylistPersistenceError
        self._playlists = list(candidate)
        self._persisted = candidate
        return True

    def _commit_navigation(self, candidate: PlaylistNavigationState) -> bool:
        if candidate == self._nav:
            return False
        if self._port is not None:
            self._port.save_navigation(candidate)
        self._nav = candidate
        self._persisted_nav = candidate
        return True

    def _commit_state(
        self,
        candidate_playlists: tuple[Playlist, ...],
        candidate_navigation: PlaylistNavigationState,
    ) -> bool:
        """ATOMIC compound commit (R2 P1-02): collection + navigation are
        ONE durable transaction (the port contract REQUIRES save_state).
        R3-12: an identical compound state is a NO-OP."""
        if (
            candidate_playlists == tuple(self._playlists)
            and candidate_navigation == self._nav
        ):
            return False
        if self._port is not None:
            self._port.save_state(candidate_playlists, candidate_navigation)
        self._playlists = list(candidate_playlists)
        self._persisted = candidate_playlists
        self._nav = candidate_navigation
        self._persisted_nav = candidate_navigation
        return True

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
            raise PlaylistNameInvalidError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists):
            raise PlaylistNameConflictError(f"playlist already exists: {cleaned!r}")
        playlist = Playlist(playlist_id=new_playlist_id(), name=cleaned)
        self._commit_playlists((*tuple(self._playlists), playlist))
        self._notify()
        return playlist

    def delete_playlist(self, playlist_id: str) -> bool:
        """R2 P1-02 ATOMIC delete: playlists + navigation commit in ONE
        durable transaction. The published state changes ONLY after the
        write is confirmed — there is never an observable moment where only
        one of the two authorities was updated. True only when deleted."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        doomed = self._playlists[index]
        candidate_playlists = tuple(
            p for p in self._playlists if p.playlist_id != playlist_id
        )
        candidate_navigation = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=tuple(i for i in self._nav.recent_ids if i != playlist_id),
        )
        self._commit_state(candidate_playlists, candidate_navigation)
        # PUBLICATION AFTER DURABILITY.
        if self._on_playlist_deleted is not None:
            self._on_playlist_deleted(playlist_id)
        self._notify()
        # DB COMMIT CONFIRMED — retire managed assets best-effort.
        if self._artwork_store is not None:
            for role, asset_path in (
                ("cover", doomed.custom_cover_path),
                ("hero", doomed.appearance.hero_image_path),
            ):
                if asset_path:
                    try:
                        self._artwork_store.delete_managed_asset(
                            playlist_id, role, asset_path
                        )
                    except OSError as exc:
                        logger.warning("playlist teardown cleanup debt: %s", exc)
        return True

    def rename_playlist(self, playlist_id: str, new_name: str) -> bool:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        cleaned = new_name.strip()
        if not cleaned:
            raise PlaylistNameInvalidError("playlist name must not be empty")
        if any(
            p.name == cleaned and p.playlist_id != playlist_id for p in self._playlists
        ):
            raise PlaylistNameConflictError(f"playlist already exists: {cleaned!r}")
        candidate = tuple(
            replace(p, name=cleaned) if p.playlist_id == playlist_id else p
            for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def set_playlist_description(self, playlist_id: str, description: str) -> bool:
        """PL-FINAL-05: real playlist description metadata (NOT appearance).
        Trims pathological whitespace while preserving intentional text;
        bounded by MAX_DESCRIPTION_LENGTH. True only when durably changed;
        False for unknown id or identical text (zero write + zero notify)."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        cleaned = description.strip()
        if len(cleaned) > MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"description exceeds {MAX_DESCRIPTION_LENGTH} characters")
        playlist = self._playlists[index]
        if playlist.description == cleaned:
            return False
        candidate = tuple(
            replace(p, description=cleaned) if p.playlist_id == playlist_id else p
            for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def add_track(self, playlist_id: str, file_path) -> bool:
        """Returns True when the track was actually added; False when the
        playlist is unknown or the path was ALREADY present (dedupe) —
        callers can distinguish 'Added' from 'Already in playlist'."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        path = str(Path(file_path))
        playlist = self._playlists[index]
        if path in playlist.track_paths:
            return False  # dedupe
        updated = replace(playlist, track_paths=(*playlist.track_paths, path))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def insert_track(self, playlist_id: str, index: int, file_path) -> bool:
        """RESTORE REMOVED TRACK AT ITS EXACT ORIGINAL POSITION (P0-01).

        The caller supplies the FROZEN original playlist_id + index +
        path captured at removal time — this operation NEVER consults any
        "selected" playlist. Safe degradation: a playlist deleted before
        Undo is a no-op (False). Exact-position restore never duplicates:
        an already-present path is skipped (False)."""
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False  # playlist deleted before Undo: safe degradation
        playlist = self._playlists[playlist_index]
        key = str(Path(file_path))
        if key in playlist.track_paths:
            return False  # duplicate policy: exact path already present
        paths = list(playlist.track_paths)
        clamped = max(0, min(index, len(paths)))
        paths.insert(clamped, key)
        updated = replace(playlist, track_paths=tuple(paths))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def add_tracks(self, playlist_id: str, file_paths) -> tuple[int, int]:
        """PL-FINAL-13: BATCH add — dedupe input preserving deterministic
        first-seen order, skip already-present tracks, produce ONE new
        Playlist candidate, persist ONCE, notify ONCE.

        Returns (added_count, already_present_count). Unknown playlist
        returns (0, 0). Zero new tracks → (0, already) with ZERO durable
        writes and ZERO notifications."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return (0, 0)
        playlist = self._playlists[index]
        existing = set(playlist.track_paths)
        added: list[str] = []
        already = 0
        seen: set[str] = set()
        for raw in file_paths:
            path = str(Path(raw))
            if path in seen:
                continue
            seen.add(path)
            if path in existing:
                already += 1
                continue
            added.append(path)
        if not added:
            return (0, already)
        updated = replace(playlist, track_paths=(*playlist.track_paths, *added))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return (0, already)
        self._notify()
        return (len(added), already)

    def remove_tracks(self, playlist_id: str, indices) -> bool:
        """PL-FINAL-15: BATCH remove — resolves valid indices BEFORE
        mutating, removes from HIGHEST to LOWEST so canonical positions of
        remaining rows never shift mid-operation, ONE candidate, ONE
        persist, ONE notify. Invalid indices are skipped (never corrupt
        positions)."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        playlist = self._playlists[index]
        valid = sorted(
            {i for i in indices if 0 <= i < len(playlist.track_paths)},
            reverse=True,
        )
        if not valid:
            return False
        paths = list(playlist.track_paths)
        for i in valid:
            del paths[i]
        updated = replace(playlist, track_paths=tuple(paths))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def remove_track(self, playlist_id: str, index: int) -> bool:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False
        playlist = self._playlists[playlist_index]
        if not (0 <= index < len(playlist.track_paths)):
            return False
        paths = list(playlist.track_paths)
        del paths[index]
        updated = replace(playlist, track_paths=tuple(paths))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def move_track(self, playlist_id: str, from_index: int, to_index: int) -> bool:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False
        playlist = self._playlists[playlist_index]
        paths = list(playlist.track_paths)
        if not (0 <= from_index < len(paths)):
            return False
        to_index = max(0, min(to_index, len(paths) - 1))
        track = paths.pop(from_index)
        paths.insert(to_index, track)
        updated = replace(playlist, track_paths=tuple(paths))
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def _prepare_asset(
        self, playlist_id: str, source_path, role: str
    ) -> PreparedPlaylistAsset | None:
        """PL-FINAL-01: prepared candidate with content-addressed truth.
        The production store implements ``prepare_candidate`` (reused files
        are marked created_by_operation=False); test doubles only implement
        the frozen legacy protocol and are assumed to create their
        synthetic candidates."""
        store = self._artwork_store
        if store is None:
            return None
        prepare_candidate = getattr(store, "prepare_candidate", None)
        if prepare_candidate is not None:
            return prepare_candidate(playlist_id, source_path, role)
        prepare = store.prepare_cover if role == "cover" else store.prepare_hero
        path = prepare(playlist_id, source_path)
        if path is None:
            return None
        return PreparedPlaylistAsset(path=path, role=role, created_by_operation=True)

    def set_custom_cover(self, playlist_id: str, cover_path: Path | str) -> str | None:
        """Sets managed custom cover. Validates, copies to app storage and persists."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return None
        playlist = self._playlists[index]
        old_path = playlist.custom_cover_path
        candidate = str(cover_path)
        prepared: PreparedPlaylistAsset | None = None
        if self._artwork_store is not None:
            prepared = self._prepare_asset(playlist_id, cover_path, "cover")
            if prepared is None:
                return None
            candidate = prepared.path
        if candidate == old_path:
            return old_path
        updated = replace(playlist, custom_cover_path=candidate)
        candidate_tuple = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        try:
            self._commit_playlists(candidate_tuple)
        except PlaylistPersistenceError:
            # P0-03/PL-FINAL-01: candidate never became durable — remove it
            # ONLY when THIS operation truly created the file.
            self._cleanup_prepared_candidate(playlist_id, prepared)
            raise
        # COMMIT CONFIRMED: retire the superseded old asset best-effort.
        if self._artwork_store is not None and old_path and old_path != candidate:
            self._retire_superseded_asset(playlist_id, "cover", old_path)
        self._notify()
        return candidate

    def remove_custom_cover(self, playlist_id: str) -> bool:
        """Removes custom cover, reverts to auto mosaic, deletes the managed
        file AFTER the database commit (P0-03: never a dangling reference).
        True only when the removal was durably committed."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        playlist = self._playlists[index]
        old_path = playlist.custom_cover_path
        updated = replace(playlist, custom_cover_path="")
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        if self._artwork_store is not None and old_path:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "cover", old_path)
            except OSError as exc:
                logger.warning("old cover cleanup debt: %s", exc)
        return True

    # ------------------------------------------------------------------
    # Per-playlist hero appearance. Cover and hero mutations are strictly
    # independent; every update uses dataclasses.replace so future metadata
    # cannot disappear during an unrelated playlist mutation.
    # ------------------------------------------------------------------

    def _replace_appearance(
        self, playlist_id: str, appearance: PlaylistAppearance
    ) -> bool:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        updated = replace(self._playlists[index], appearance=appearance)
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def _delete_hero_asset(self, playlist_id: str) -> str:
        """Returns the path to retire AFTER the DB commit (P0-03)."""
        playlist = self.get_playlist(playlist_id)
        if playlist is None or self._artwork_store is None:
            return ""
        return playlist.appearance.hero_image_path

    def set_hero_auto(self, playlist_id: str) -> bool:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return False
        old_path = self._delete_hero_asset(playlist_id)
        result = self._replace_appearance(
            playlist_id,
            replace(
                playlist.appearance,
                hero_mode=PlaylistHeroMode.AUTO,
                hero_image_path="",
            ),
        )
        if result and self._artwork_store is not None and old_path:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "hero", old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
        return result

    def set_hero_solid(self, playlist_id: str, color: str) -> bool:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return False
        canonical = _canonical_color(color)
        old_path = self._delete_hero_asset(playlist_id)
        result = self._replace_appearance(
            playlist_id,
            replace(
                playlist.appearance,
                hero_mode=PlaylistHeroMode.SOLID,
                hero_solid_color=canonical,
                hero_image_path="",
            ),
        )
        if result and self._artwork_store is not None and old_path:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "hero", old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
        return result

    def set_hero_gradient(
        self, playlist_id: str, colors: tuple[str, ...], angle: float
    ) -> bool:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return False
        if len(colors) not in (2, 3):
            raise ValueError("hero gradient requires two or three colors")
        canonical_colors = tuple(_canonical_color(color) for color in colors)
        numeric_angle = float(angle)
        if not math.isfinite(numeric_angle):
            raise ValueError("hero gradient angle must be finite")
        normalized_angle = numeric_angle % 360.0
        old_path = self._delete_hero_asset(playlist_id)
        result = self._replace_appearance(
            playlist_id,
            replace(
                playlist.appearance,
                hero_mode=PlaylistHeroMode.GRADIENT,
                hero_gradient_colors=canonical_colors,
                hero_gradient_angle=normalized_angle,
                hero_image_path="",
            ),
        )
        if result and self._artwork_store is not None and old_path:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "hero", old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
        return result

    @staticmethod
    def _normalize_visual_appearance_request(
        *,
        cover_action: str,
        cover_source_path,
        hero_mode: str,
        hero_solid_color: str,
        hero_gradient_colors: tuple[str, ...],
        hero_gradient_angle: float,
        hero_image_source,
        hero_focal_x: float | None = None,
        hero_focal_y: float | None = None,
    ):
        """R5-01 PHASE 1 — PURE VALIDATION / NORMALIZATION.

        No filesystem, no service state, no artwork_store, no persist, no
        notify. Returns the normalized tuple or None when the REQUEST is
        logically invalid (zero side effects guaranteed)."""
        if cover_action not in ("keep", "auto", "replace"):
            return None
        if hero_mode not in ("auto", "solid", "gradient", "image"):
            return None

        # PL-FINAL-09: focal must be finite and is clamped to 0..1; missing
        # values keep the backward-compatible center default.
        def _normalized_focal(value: float | None, fallback: float) -> float:
            if value is None:
                return fallback
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return fallback
            if not math.isfinite(numeric):
                return fallback
            return max(0.0, min(1.0, numeric))

        focal_x = _normalized_focal(hero_focal_x, 0.5)
        focal_y = _normalized_focal(hero_focal_y, 0.5)
        solid_color = ""
        gradient_colors: tuple[str, ...] = ()
        gradient_angle = 0.0
        if hero_mode == "solid":
            try:
                solid_color = _canonical_color(hero_solid_color)
            except ValueError:
                return None
        elif hero_mode == "gradient":
            if len(hero_gradient_colors) not in (2, 3):
                return None
            try:
                gradient_colors = tuple(
                    _canonical_color(color) for color in hero_gradient_colors
                )
            except ValueError:
                return None
            try:
                numeric_angle = float(hero_gradient_angle)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(numeric_angle):
                return None
            gradient_angle = numeric_angle % 360.0
        cover_source = (
            Path(cover_source_path) if cover_source_path is not None else None
        )
        hero_source = Path(hero_image_source) if hero_image_source is not None else None
        return (
            cover_action,
            hero_mode,
            solid_color,
            gradient_colors,
            gradient_angle,
            cover_source,
            hero_source,
            focal_x,
            focal_y,
        )

    def apply_visual_appearance(
        self,
        playlist_id: str,
        *,
        cover_action: str,
        cover_source_path: Path | str | None = None,
        hero_mode: str = "auto",
        hero_solid_color: str = "",
        hero_gradient_colors: tuple[str, ...] = (),
        hero_gradient_angle: float = 135.0,
        hero_image_source: Path | str | None = None,
        hero_focal_x: float | None = None,
        hero_focal_y: float | None = None,
    ) -> str:
        """R3-06 ONE editorial transaction for the whole appearance.

        ``cover_action``: "keep" | "auto" | "replace".
        ``hero_mode``: "auto" | "solid" | "gradient" | "image".

        Flow: validate ALL → prepare candidates → build ONE complete
        immutable Playlist candidate → if equal to current: cleanup new
        candidates, NO_CHANGE (zero writes) → persist ONCE → publish →
        notify ONCE → retire superseded assets AFTER commit. Any
        preparation failure cleans ONLY new candidates and changes
        nothing. Returns "updated" | "no_change" | "asset_rejected"."""
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return "not_found"

        # PHASE 1 — PURE VALIDATION / NORMALIZATION (R5-01): cero
        # filesystem antes de saber si la petición completa es válida.
        normalized = self._normalize_visual_appearance_request(
            cover_action=cover_action,
            cover_source_path=cover_source_path,
            hero_mode=hero_mode,
            hero_solid_color=hero_solid_color,
            hero_gradient_colors=hero_gradient_colors,
            hero_gradient_angle=hero_gradient_angle,
            hero_image_source=hero_image_source,
            hero_focal_x=hero_focal_x,
            hero_focal_y=hero_focal_y,
        )
        if normalized is None:
            return "invalid"
        (
            norm_cover_action,
            norm_hero_mode,
            norm_solid_color,
            norm_gradient_colors,
            norm_gradient_angle,
            norm_cover_source,
            norm_hero_source,
            norm_focal_x,
            norm_focal_y,
        ) = normalized

        # PHASE 2 — PREPARE ASSETS (solo candidates de ESTA operación).
        new_cover = playlist.custom_cover_path
        new_hero_path = playlist.appearance.hero_image_path
        # PL-FINAL-01: (role, PreparedPlaylistAsset) — el cleanup solo
        # toca candidates con created_by_operation == True.
        prepared_candidates: list[tuple[str, PreparedPlaylistAsset]] = []

        if norm_cover_action == "auto":
            new_cover = ""
        elif norm_cover_action == "replace":
            if norm_cover_source is None:
                return "invalid"
            prepared = None
            if self._artwork_store is not None:
                prepared = self._prepare_asset(playlist_id, norm_cover_source, "cover")
            if prepared is None:
                return "asset_rejected"
            new_cover = prepared.path
            prepared_candidates.append(("cover", prepared))

        appearance = playlist.appearance
        if norm_hero_mode == "image":
            if norm_hero_source is not None:
                prepared_hero = None
                if self._artwork_store is not None:
                    prepared_hero = self._prepare_asset(
                        playlist_id, norm_hero_source, "hero"
                    )
                if prepared_hero is None:
                    self._cleanup_prepared_candidates(playlist_id, prepared_candidates)
                    return "asset_rejected"
                new_hero_path = prepared_hero.path
                prepared_candidates.append(("hero", prepared_hero))
            else:
                # Un persisted missing hero NO puede ser un "keep image".
                try:
                    hero_exists = bool(new_hero_path) and Path(new_hero_path).is_file()
                except OSError:
                    hero_exists = False
                if not hero_exists:
                    self._cleanup_prepared_candidates(playlist_id, prepared_candidates)
                    return "asset_rejected"
        else:
            new_hero_path = ""

        # PHASE 3 — BUILD DOMAIN CANDIDATE (usa valores NORMALIZADOS).
        if norm_hero_mode == "solid":
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.SOLID,
                hero_solid_color=norm_solid_color,
                hero_image_path="",
            )
        elif norm_hero_mode == "gradient":
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.GRADIENT,
                hero_gradient_colors=norm_gradient_colors,
                hero_gradient_angle=norm_gradient_angle,
                hero_image_path="",
            )
        elif norm_hero_mode == "image":
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.IMAGE,
                hero_image_path=new_hero_path,
                # PL-FINAL-09: el focal del hero image se persiste SOLO con
                # la transacción de apariencia (Apply).
                hero_focal_x=norm_focal_x,
                hero_focal_y=norm_focal_y,
            )
        else:
            # R4-03: AUTO limpia TODO el estado específico de IMAGE.
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.AUTO,
                hero_image_path="",
            )

        updated = replace(playlist, custom_cover_path=new_cover, appearance=appearance)
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )

        # NO_CHANGE: limpiar SOLO candidates frescos de ESTA operación.
        if candidate == tuple(self._playlists):
            self._cleanup_prepared_candidates(playlist_id, prepared_candidates)
            return "no_change"

        # PHASE 4 — COMMIT (una sola durabilidad).
        try:
            self._commit_playlists(candidate)
        except PlaylistPersistenceError:
            # DB fail: limpiar SOLO candidates nuevos; old assets intactos.
            self._cleanup_prepared_candidates(playlist_id, prepared_candidates)
            raise
        self._notify()

        # PHASE 5 — RETIRE SUPERSEDED (post-commit, best-effort; V1 o V2).
        if new_cover != playlist.custom_cover_path and playlist.custom_cover_path:
            self._retire_superseded_asset(
                playlist_id, "cover", playlist.custom_cover_path
            )
        if (
            new_hero_path != playlist.appearance.hero_image_path
            and playlist.appearance.hero_image_path
        ):
            self._retire_superseded_asset(
                playlist_id, "hero", playlist.appearance.hero_image_path
            )
        return "updated"

    def _retire_superseded_asset(self, playlist_id: str, role: str, path: str) -> None:
        """PL-FINAL-01/04: retira UN asset SUPERSEDIDO (V2 o legacy V1/V2-
        digest) DESPUÉS del commit durable. V2 usa ownership por token;
        legacy usa la gramática exacta con fail-closed. Es una operación
        DISTINTA de _cleanup_prepared_candidate: aquí el asset ya estuvo
        commiteado y es seguro retirarlo; un fallo solo deja deuda de
        cleanup, NUNCA revierte el estado commiteado."""
        if not path:
            return
        store = self._artwork_store
        if store is None:
            return
        try:
            deleted = store.delete_managed_asset(playlist_id, role, path)
        except (OSError, TypeError) as exc:
            logger.warning("asset retirement debt: %s", exc)
            deleted = False
        if deleted:
            return
        legacy = getattr(store, "delete_legacy_managed_asset", None)
        if legacy is not None:
            with contextlib.suppress(OSError):
                legacy(playlist_id, role, path)

    def _cleanup_prepared_candidate(
        self, playlist_id: str, candidate: PreparedPlaylistAsset | None
    ) -> None:
        """PL-FINAL-01: cleanup de UN candidato preparado por ESTA
        operación. NUNCA borra: assets commiteados previos, assets
        reutilizados por content-addressing (created_by_operation=False),
        assets de otra playlist, ni paths no gestionados."""
        if candidate is None or not candidate.created_by_operation:
            return
        store = self._artwork_store
        if store is None:
            return
        try:
            store.delete_managed_asset(playlist_id, candidate.role, candidate.path)
        except OSError as exc:
            logger.warning("orphan candidate cleanup debt: %s", exc)

    def _cleanup_prepared_candidates(
        self,
        playlist_id: str,
        candidates: list[tuple[str, PreparedPlaylistAsset]],
    ) -> None:
        for _role, candidate in candidates:
            self._cleanup_prepared_candidate(playlist_id, candidate)

    def _cleanup_prepared_cover(self, playlist_id, new_cover, old_cover) -> None:
        if self._artwork_store is not None and new_cover and new_cover != old_cover:
            with contextlib.suppress(OSError):
                self._artwork_store.delete_managed_asset(
                    playlist_id, "cover", new_cover
                )

    def set_custom_hero_image(
        self, playlist_id: str, image_path: Path | str
    ) -> str | None:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return None
        old_path = playlist.appearance.hero_image_path
        candidate = str(image_path)
        prepared: PreparedPlaylistAsset | None = None
        if self._artwork_store is not None:
            prepared = self._prepare_asset(playlist_id, image_path, "hero")
            if prepared is None:
                return None
            candidate = prepared.path
        if candidate == old_path:
            return old_path
        appearance = replace(
            playlist.appearance,
            hero_mode=PlaylistHeroMode.IMAGE,
            hero_image_path=candidate,
        )
        try:
            self._replace_appearance(playlist_id, appearance)
        except PlaylistPersistenceError:
            # PL-FINAL-01: solo candidates realmente creados por ESTA
            # operación entran al cleanup de rollback.
            self._cleanup_prepared_candidate(playlist_id, prepared)
            raise
        if self._artwork_store is not None and old_path and old_path != candidate:
            self._retire_superseded_asset(playlist_id, "hero", old_path)
        return candidate

    def pin_playlist(self, playlist_id: str) -> bool:
        if self._find_by_id(playlist_id) < 0:
            return False
        if playlist_id in self._nav.pinned_ids:
            return False  # duplicate pin: no-op
        candidate = PlaylistNavigationState(
            pinned_ids=(*self._nav.pinned_ids, playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._commit_navigation(candidate)
        self._notify()
        return True

    def unpin_playlist(self, playlist_id: str) -> bool:
        if playlist_id not in self._nav.pinned_ids:
            return False  # unpin missing id: no-op
        candidate = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._commit_navigation(candidate)
        self._notify()
        return True

    def mark_recent(self, playlist_id: str) -> bool:
        """MRU semantics: most recently opened/navigated first, bounded by
        MAX_RECENT_PLAYLISTS, no duplicates. Unknown ids never enter.

        Idempotent: opening the already-most-recent playlist is a no-op
        (no persistence, no notification) — the MRU order did not change."""
        if self._find_by_id(playlist_id) < 0:
            return False
        if self._nav.recent_ids and self._nav.recent_ids[0] == playlist_id:
            return False  # already MRU rank 0: order unchanged
        recent = [i for i in self._nav.recent_ids if i != playlist_id]
        recent.insert(0, playlist_id)
        recent = recent[:MAX_RECENT_PLAYLISTS]
        candidate = PlaylistNavigationState(
            pinned_ids=self._nav.pinned_ids,
            recent_ids=tuple(recent),
        )
        # R5-05: NO_CHANGE = cero write + cero notify.
        changed = self._commit_navigation(candidate)
        if not changed:
            return False
        self._notify()
        return True
