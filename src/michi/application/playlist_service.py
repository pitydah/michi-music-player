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

from michi.application.ports import PlaylistArtworkStorePort, PlaylistsPort
from michi.domain.playlist import (
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
    PlaylistPersistenceError,
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
    (pinned/recent); mutates, persists (best effort) and notifies. M4-R1:
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

    def _persist(self) -> None:
        """P0-02 TRUTHFUL persistence: the candidate collection is saved
        BEFORE publication. On failure the in-memory state rolls back to
        the last persisted snapshot and PlaylistPersistenceError
        propagates — no false success."""
        candidate = tuple(self._playlists)
        if self._port is not None:
            try:
                self._port.save(candidate)
            except PlaylistPersistenceError:
                self._playlists = list(self._persisted)
                raise
        self._persisted = candidate

    def _persist_nav(self) -> None:
        if self._port is not None:
            try:
                self._port.save_navigation(self._nav)
            except PlaylistPersistenceError:
                self._nav = self._persisted_nav
                raise
        self._persisted_nav = self._nav

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
            raise ValueError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        playlist = Playlist(playlist_id=new_playlist_id(), name=cleaned)
        self._playlists.append(playlist)
        self._persist()
        self._notify()
        return playlist

    def delete_playlist(self, playlist_id: str) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        doomed = self._playlists[index]
        del self._playlists[index]
        # Prune navigation metadata (never dangling ids).
        self._nav = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=tuple(i for i in self._nav.recent_ids if i != playlist_id),
        )
        self._persist()
        self._persist_nav()
        if self._on_playlist_deleted is not None:
            self._on_playlist_deleted(playlist_id)
        self._notify()
        # DB COMMIT CONFIRMED — retire managed assets best-effort.
        if self._artwork_store is not None:
            for asset_path in (
                doomed.custom_cover_path,
                doomed.appearance.hero_image_path,
            ):
                if asset_path:
                    try:
                        self._artwork_store.delete_managed_asset(asset_path)
                    except OSError as exc:
                        logger.warning("playlist teardown cleanup debt: %s", exc)

    def rename_playlist(self, playlist_id: str, new_name: str) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        cleaned = new_name.strip()
        if not cleaned:
            raise ValueError("playlist name must not be empty")
        if any(
            p.name == cleaned and p.playlist_id != playlist_id for p in self._playlists
        ):
            raise ValueError(f"playlist already exists: {cleaned!r}")
        playlist = self._playlists[index]
        self._playlists[index] = replace(playlist, name=cleaned)
        self._persist()
        self._notify()

    def add_track(self, playlist_id: str, file_path) -> None:
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        path = str(Path(file_path))
        playlist = self._playlists[index]
        if path in playlist.track_paths:
            return  # dedupe
        self._playlists[index] = replace(
            playlist, track_paths=(*playlist.track_paths, path)
        )
        self._persist()
        self._notify()

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
        self._playlists[playlist_index] = replace(playlist, track_paths=tuple(paths))
        self._persist()
        self._notify()
        return True

    def remove_track(self, playlist_id: str, index: int) -> None:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return
        playlist = self._playlists[playlist_index]
        if not (0 <= index < len(playlist.track_paths)):
            return
        paths = list(playlist.track_paths)
        del paths[index]
        self._playlists[playlist_index] = replace(playlist, track_paths=tuple(paths))
        self._persist()
        self._notify()

    def move_track(self, playlist_id: str, from_index: int, to_index: int) -> None:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return
        playlist = self._playlists[playlist_index]
        paths = list(playlist.track_paths)
        if not (0 <= from_index < len(paths)):
            return
        to_index = max(0, min(to_index, len(paths) - 1))
        track = paths.pop(from_index)
        paths.insert(to_index, track)
        self._playlists[playlist_index] = replace(playlist, track_paths=tuple(paths))
        self._persist()
        self._notify()

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
        self._playlists[index] = replace(playlist, custom_cover_path=candidate)
        try:
            self._persist()
        except PlaylistPersistenceError:
            # P0-03: candidate never became durable — remove it best-effort.
            if self._artwork_store is not None:
                try:
                    self._artwork_store.delete_managed_asset(candidate)
                except OSError as exc:
                    logger.warning("orphan candidate cleanup debt: %s", exc)
            raise
        # COMMIT CONFIRMED: retire the superseded old asset best-effort.
        if self._artwork_store is not None and old_path and old_path != candidate:
            try:
                self._artwork_store.delete_managed_asset(old_path)
            except OSError as exc:
                logger.warning("old asset cleanup debt: %s", exc)
        self._notify()
        return candidate

    def remove_custom_cover(self, playlist_id: str) -> None:
        """Removes custom cover, reverts to auto mosaic, deletes the managed
        file AFTER the database commit (P0-03: never a dangling reference)."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return
        playlist = self._playlists[index]
        old_path = playlist.custom_cover_path
        self._playlists[index] = replace(playlist, custom_cover_path="")
        self._persist()
        self._notify()
        if self._artwork_store is not None and old_path:
            try:
                self._artwork_store.delete_managed_asset(old_path)
            except OSError as exc:
                logger.warning("old cover cleanup debt: %s", exc)

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
        self._playlists[index] = replace(self._playlists[index], appearance=appearance)
        self._persist()
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
                self._artwork_store.delete_managed_asset(old_path)
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
                self._artwork_store.delete_managed_asset(old_path)
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
                self._artwork_store.delete_managed_asset(old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
        return result

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
                    self._artwork_store.delete_managed_asset(candidate)
                except OSError as exc:
                    logger.warning("orphan candidate cleanup debt: %s", exc)
            raise
        if self._artwork_store is not None and old_path and old_path != candidate:
            try:
                self._artwork_store.delete_managed_asset(old_path)
            except OSError as exc:
                logger.warning("old hero cleanup debt: %s", exc)
        return candidate

    def pin_playlist(self, playlist_id: str) -> None:
        if self._find_by_id(playlist_id) < 0:
            return
        if playlist_id in self._nav.pinned_ids:
            return  # duplicate pin: no-op
        self._nav = PlaylistNavigationState(
            pinned_ids=(*self._nav.pinned_ids, playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._persist_nav()
        self._notify()

    def unpin_playlist(self, playlist_id: str) -> None:
        if playlist_id not in self._nav.pinned_ids:
            return  # unpin missing id: no-op
        self._nav = PlaylistNavigationState(
            pinned_ids=tuple(i for i in self._nav.pinned_ids if i != playlist_id),
            recent_ids=self._nav.recent_ids,
        )
        self._persist_nav()
        self._notify()

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
        self._nav = PlaylistNavigationState(
            pinned_ids=self._nav.pinned_ids,
            recent_ids=tuple(recent),
        )
        self._persist_nav()
        self._notify()
