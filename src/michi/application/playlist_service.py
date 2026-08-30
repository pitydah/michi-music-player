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
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
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
    (pinned/recent); mutates, persists truthfully (authoritative writes) and notifies. M4-R1:
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
        self._commit_playlists(candidate)
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
        self._commit_playlists(candidate)
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
        self._commit_playlists(candidate)
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
        self._commit_playlists(candidate)
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
        self._commit_playlists(candidate)
        self._notify()
        return True

    def set_custom_cover(self, playlist_id: str, cover_path: Path | str) -> str | None:
        """Sets managed custom cover. Validates, copies to app storage and persists."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return None
        playlist = self._playlists[index]
        old_path = playlist.custom_cover_path
        candidate = str(cover_path)
        if self._artwork_store is not None:
            prepared = self._artwork_store.prepare_cover(playlist_id, cover_path)
            if prepared is None:
                return None
            candidate = prepared
        if candidate == old_path:
            return old_path
        updated = replace(playlist, custom_cover_path=candidate)
        candidate_tuple = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        try:
            self._commit_playlists(candidate_tuple)
        except PlaylistPersistenceError:
            # P0-03: candidate never became durable — remove it best-effort.
            if self._artwork_store is not None:
                try:
                    self._artwork_store.delete_managed_asset(
                        playlist_id, "cover", candidate
                    )
                except OSError as exc:
                    logger.warning("orphan candidate cleanup debt: %s", exc)
            raise
        # COMMIT CONFIRMED: retire the superseded old asset best-effort.
        if self._artwork_store is not None and old_path and old_path != candidate:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "cover", old_path)
            except OSError as exc:
                logger.warning("old asset cleanup debt: %s", exc)
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
        self._commit_playlists(candidate)
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
        self._commit_playlists(candidate)
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
        if cover_action not in ("keep", "auto", "replace"):
            return "invalid"
        if hero_mode not in ("auto", "solid", "gradient", "image"):
            return "invalid"

        # --- 1. preparar candidates (cover) ---
        new_cover = playlist.custom_cover_path
        if cover_action == "auto":
            new_cover = ""
        elif cover_action == "replace":
            if cover_source_path is None:
                return "invalid"
            prepared = None
            if self._artwork_store is not None:
                prepared = self._artwork_store.prepare_cover(
                    playlist_id, cover_source_path
                )
            if prepared is None:
                return "asset_rejected"
            new_cover = prepared

        # --- 2. preparar candidates (hero) ---
        appearance = playlist.appearance
        new_hero_path = appearance.hero_image_path
        if hero_mode == "image":
            if hero_image_source is not None:
                prepared_hero = None
                if self._artwork_store is not None:
                    prepared_hero = self._artwork_store.prepare_hero(
                        playlist_id, hero_image_source
                    )
                if prepared_hero is None:
                    self._cleanup_prepared_cover(
                        playlist_id, new_cover, playlist.custom_cover_path
                    )
                    return "asset_rejected"
                new_hero_path = prepared_hero
            else:
                # Un persisted missing hero NO puede ser un "keep image".
                try:
                    hero_exists = bool(new_hero_path) and Path(new_hero_path).is_file()
                except OSError:
                    hero_exists = False
                if not hero_exists:
                    self._cleanup_prepared_cover(
                        playlist_id, new_cover, playlist.custom_cover_path
                    )
                    return "asset_rejected"
        else:
            new_hero_path = ""

        # --- 3. construir candidate completo ---
        # Cualquier fallo de validación retira los candidates preparados.
        try:
            return self._build_appearance_candidate(
                playlist_id,
                playlist,
                appearance,
                hero_mode,
                hero_solid_color,
                hero_gradient_colors,
                hero_gradient_angle,
                new_cover,
                new_hero_path,
            )
        except ValueError:
            self._cleanup_prepared_cover(
                playlist_id, new_cover, playlist.custom_cover_path
            )
            if new_hero_path and new_hero_path != playlist.appearance.hero_image_path:
                try:
                    self._artwork_store.delete_managed_asset(
                        playlist_id, "hero", new_hero_path
                    )
                except OSError:
                    pass
            raise

    def _build_appearance_candidate(
        self,
        playlist_id,
        playlist,
        appearance,
        hero_mode,
        hero_solid_color,
        hero_gradient_colors,
        hero_gradient_angle,
        new_cover,
        new_hero_path,
    ):
        if hero_mode == "solid":
            canonical = _canonical_color(hero_solid_color)
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.SOLID,
                hero_solid_color=canonical,
                hero_image_path="",
            )
        elif hero_mode == "gradient":
            if len(hero_gradient_colors) not in (2, 3):
                self._cleanup_prepared_cover(
                    playlist_id, new_cover, playlist.custom_cover_path
                )
                return "invalid"
            canonical_colors = tuple(
                _canonical_color(color) for color in hero_gradient_colors
            )
            numeric_angle = float(hero_gradient_angle)
            if not math.isfinite(numeric_angle):
                return "invalid"
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.GRADIENT,
                hero_gradient_colors=canonical_colors,
                hero_gradient_angle=numeric_angle % 360.0,
                hero_image_path="",
            )
        elif hero_mode == "image":
            appearance = replace(
                appearance,
                hero_mode=PlaylistHeroMode.IMAGE,
                hero_image_path=new_hero_path,
            )
        else:
            appearance = replace(appearance, hero_mode=PlaylistHeroMode.AUTO)

        updated = replace(playlist, custom_cover_path=new_cover, appearance=appearance)
        candidate = tuple(
            updated if p.playlist_id == playlist_id else p for p in self._playlists
        )
        if candidate == tuple(self._playlists):
            # NO_CHANGE: zero writes; cleanup any freshly prepared candidate.
            if self._artwork_store is not None:
                if new_cover != playlist.custom_cover_path and new_cover:
                    try:
                        self._artwork_store.delete_managed_asset(
                            playlist_id, "cover", new_cover
                        )
                    except OSError:
                        pass
                if (
                    new_hero_path != playlist.appearance.hero_image_path
                    and new_hero_path
                ):
                    try:
                        self._artwork_store.delete_managed_asset(
                            playlist_id, "hero", new_hero_path
                        )
                    except OSError:
                        pass
            return "no_change"

        # --- 4. persistir UNA vez, publicar, notificar ---
        try:
            self._commit_playlists(candidate)
        except PlaylistPersistenceError:
            # DB fail: cleanup ONLY new candidates; old assets preserved.
            if self._artwork_store is not None:
                if new_cover != playlist.custom_cover_path and new_cover:
                    try:
                        self._artwork_store.delete_managed_asset(
                            playlist_id, "cover", new_cover
                        )
                    except OSError:
                        pass
                if (
                    new_hero_path != playlist.appearance.hero_image_path
                    and new_hero_path
                ):
                    try:
                        self._artwork_store.delete_managed_asset(
                            playlist_id, "hero", new_hero_path
                        )
                    except OSError:
                        pass
            raise
        self._notify()

        # --- 5. retirar superseded post-commit (best-effort) ---
        if self._artwork_store is not None:
            if new_cover != playlist.custom_cover_path and playlist.custom_cover_path:
                try:
                    self._artwork_store.delete_managed_asset(
                        playlist_id, "cover", playlist.custom_cover_path
                    )
                except OSError as exc:
                    logger.warning("old cover cleanup debt: %s", exc)
            if (
                new_hero_path != playlist.appearance.hero_image_path
                and playlist.appearance.hero_image_path
            ):
                try:
                    self._artwork_store.delete_managed_asset(
                        playlist_id, "hero", playlist.appearance.hero_image_path
                    )
                except OSError as exc:
                    logger.warning("old hero cleanup debt: %s", exc)
        return "updated"

    def _cleanup_prepared_cover(self, playlist_id, new_cover, old_cover) -> None:
        if self._artwork_store is not None and new_cover and new_cover != old_cover:
            try:
                self._artwork_store.delete_managed_asset(
                    playlist_id, "cover", new_cover
                )
            except OSError:
                pass

    def set_custom_hero_image(
        self, playlist_id: str, image_path: Path | str
    ) -> str | None:
        playlist = self.get_playlist(playlist_id)
        if playlist is None:
            return None
        old_path = playlist.appearance.hero_image_path
        candidate = str(image_path)
        if self._artwork_store is not None:
            prepared = self._artwork_store.prepare_hero(playlist_id, image_path)
            if prepared is None:
                return None
            candidate = prepared
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
            if self._artwork_store is not None:
                try:
                    self._artwork_store.delete_managed_asset(
                        playlist_id, "hero", candidate
                    )
                except OSError as exc:
                    logger.warning("orphan candidate cleanup debt: %s", exc)
            raise
        if self._artwork_store is not None and old_path and old_path != candidate:
            try:
                self._artwork_store.delete_managed_asset(playlist_id, "hero", old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
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
        candidate = PlaylistNavigationState(
            pinned_ids=self._nav.pinned_ids,
            recent_ids=tuple(recent),
        )
        self._commit_navigation(candidate)
        self._notify()
