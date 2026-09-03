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
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path

from michi.application.errors import (
    PlaylistNameConflictError,
    PlaylistNameInvalidError,
    PlaylistPersistenceError,
)
from michi.application.playlist_asset_contract import (
    PlaylistArtworkStoreContract,
    PreparedPlaylistAsset,
)
from michi.application.ports import PlaylistArtworkStorePort, PlaylistsPort
from michi.domain.playlist import (
    MAX_DESCRIPTION_LENGTH,
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistAppearance,
    PlaylistHeroMode,
    PlaylistNavigationState,
    PlaylistTrackReference,
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
        if artwork_store is not None and not isinstance(
            artwork_store, PlaylistArtworkStoreContract
        ):
            # PL-10-FINAL-01: fail fast — un store que no implementa el
            # contrato canónico NO puede usarse (nunca getattr fallback
            # que invente ownership).
            raise TypeError(
                "artwork_store must implement "
                "PlaylistArtworkStoreContract.prepare_candidate"
            )
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

    # ------------------------------------------------------------------
    # Identity recovery: aligned membership helpers (TrackId = identity,
    # path = location snapshot). Never skew the two collections.
    # ------------------------------------------------------------------

    @staticmethod
    def _aligned_membership(
        playlist: Playlist,
    ) -> tuple[list[str], list[str]]:
        """Position-aligned editable copies of (track_ids, track_paths).

        A path-only (V1/V2) record has track_ids == () — the shorter side
        is padded with "" so every index operation touches BOTH collections
        symmetrically (never skew)."""
        ids = list(playlist.track_ids)
        paths = list(playlist.track_paths)
        count = max(len(ids), len(paths))
        if len(ids) < count:
            ids.extend("" for _ in range(count - len(ids)))
        if len(paths) < count:
            paths.extend("" for _ in range(count - len(paths)))
        return ids, paths

    def _publish_membership(
        self, playlist_id: str, ids: list[str], paths: list[str]
    ) -> bool:
        """Replace the aligned membership of one playlist (persist once,
        notify once). False when nothing changed."""
        candidate = tuple(
            replace(p, track_ids=tuple(ids), track_paths=tuple(paths))
            if p.playlist_id == playlist_id
            else p
            for p in self._playlists
        )
        changed = self._commit_playlists(candidate)
        if not changed:
            return False
        self._notify()
        return True

    def create_playlist_with_references(
        self,
        name: str,
        references: Iterable[PlaylistTrackReference],
    ) -> Playlist:
        """Create one playlist and publish its initial ordered membership
        once (identity recovery contract: stable TrackIds + location
        snapshot). Dedupe by TrackId when present, else by path."""
        cleaned = name.strip()
        if not cleaned:
            raise PlaylistNameInvalidError("playlist name must not be empty")
        if any(p.name == cleaned for p in self._playlists):
            raise PlaylistNameConflictError(f"playlist already exists: {cleaned!r}")
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        track_ids: list[str] = []
        track_paths: list[str] = []
        for ref in references:
            if ref.track_id:
                if ref.track_id in seen_ids:
                    continue
                seen_ids.add(ref.track_id)
            elif ref.fallback_path and ref.fallback_path in seen_paths:
                # Solo un ref LEGACY (sin TrackId) dedupe por path: cuando
                # el TrackId estable está presente, la identidad decide —
                # un path compartido por dos tracks distintos (T1 y T2 en
                # el mismo snapshot) NUNCA los colapsa.
                continue
            seen_paths.add(ref.fallback_path)
            track_ids.append(ref.track_id)
            track_paths.append(ref.fallback_path)
        playlist = Playlist(
            playlist_id=new_playlist_id(),
            name=cleaned,
            track_ids=tuple(track_ids),
            track_paths=tuple(track_paths),
        )
        self._commit_playlists((*tuple(self._playlists), playlist))
        self._notify()
        return playlist

    def add_track_references(
        self, playlist_id: str, references: Iterable[PlaylistTrackReference]
    ) -> int:
        """Append a membership batch ONCE (identity recovery contract).

        Dedupe by TrackId when present, else by fallback path — a track
        that relocated (same TrackId, new path) NEVER duplicates. Keeps
        track_ids and track_paths aligned by index. Returns the number of
        members actually added; 0 → zero durable writes, zero notifies."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return 0
        playlist = self._playlists[index]
        track_ids, track_paths = self._aligned_membership(playlist)
        seen_ids = set(track_ids)
        seen_paths = set(track_paths)
        added = 0
        for ref in references:
            if ref.track_id:
                if ref.track_id in seen_ids:
                    continue
                seen_ids.add(ref.track_id)
            elif ref.fallback_path and ref.fallback_path in seen_paths:
                # Igual política que create_playlist_with_references: la
                # comparación por path solo aplica a refs sin TrackId —
                # nunca deja que el path (snapshot) sea autoridad global.
                continue
            seen_paths.add(ref.fallback_path)
            track_ids.append(ref.track_id)
            track_paths.append(ref.fallback_path)
            added += 1
        if added == 0:
            return 0
        if not self._publish_membership(playlist_id, track_ids, track_paths):
            return 0
        return added

    def add_track_reference(
        self, playlist_id: str, reference: PlaylistTrackReference
    ) -> bool:
        """Single-member convenience over add_track_references."""
        return self.add_track_references(playlist_id, (reference,)) == 1

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
        """LEGACY path-only intent → appended as a reference with no
        TrackId (""): dedupe by path; track_ids stay aligned (padded "").
        Returns True when actually added; False for unknown playlist or an
        ALREADY present member (dedupe) — callers distinguish 'Added' from
        'Already in playlist'."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        path = str(Path(file_path))
        playlist = self._playlists[index]
        if path in playlist.track_paths:
            return False  # dedupe
        track_ids, track_paths = self._aligned_membership(playlist)
        track_ids.append("")
        track_paths.append(path)
        return self._publish_membership(playlist_id, track_ids, track_paths)

    def insert_track(self, playlist_id: str, index: int, file_path) -> bool:
        """RESTORE REMOVED TRACK AT ITS EXACT ORIGINAL POSITION (P0-01).

        The caller supplies the FROZEN original playlist_id + index +
        path captured at removal time — this operation NEVER consults any
        "selected" playlist. Safe degradation: a playlist deleted before
        Undo is a no-op (False). Exact-position restore never duplicates:
        an already-present path is skipped (False). Aligned membership."""
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False  # playlist deleted before Undo: safe degradation
        playlist = self._playlists[playlist_index]
        key = str(Path(file_path))
        if key in playlist.track_paths:
            return False  # duplicate policy: exact path already present
        track_ids, track_paths = self._aligned_membership(playlist)
        count = len(track_paths)
        clamped = max(0, min(index, count))
        track_ids.insert(clamped, "")
        track_paths.insert(clamped, key)
        return self._publish_membership(playlist_id, track_ids, track_paths)

    def add_tracks(self, playlist_id: str, file_paths) -> tuple[int, int]:
        """PL-FINAL-13: BATCH add — dedupe input preserving deterministic
        first-seen order, skip already-present tracks, produce ONE new
        Playlist candidate, persist ONCE, notify ONCE.

        Legacy path-only batch: every member is a reference without
        TrackId; track_ids stay aligned (padded "").

        Returns (added_count, already_present_count). Unknown playlist
        returns (0, 0). Zero new tracks → (0, already) with ZERO durable
        writes and ZERO notifications."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return (0, 0)
        playlist = self._playlists[index]
        track_ids, track_paths = self._aligned_membership(playlist)
        existing = set(track_paths)
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
        track_ids.extend("" for _ in added)
        track_paths.extend(added)
        if not self._publish_membership(playlist_id, track_ids, track_paths):
            return (0, already)
        return (len(added), already)

    def remove_tracks(self, playlist_id: str, indices) -> bool:
        """PL-FINAL-15: BATCH remove — resolves valid indices BEFORE
        mutating, removes from HIGHEST to LOWEST so canonical positions of
        remaining rows never shift mid-operation, ONE candidate, ONE
        persist, ONE notify. Invalid indices are skipped (never corrupt
        positions). Removes from BOTH aligned collections (ids + paths)."""
        index = self._find_by_id(playlist_id)
        if index < 0:
            return False
        playlist = self._playlists[index]
        track_ids, track_paths = self._aligned_membership(playlist)
        count = len(track_paths)
        valid = sorted(
            {i for i in indices if 0 <= i < count},
            reverse=True,
        )
        if not valid:
            return False
        for i in valid:
            del track_ids[i]
            del track_paths[i]
        return self._publish_membership(playlist_id, track_ids, track_paths)

    def remove_track(self, playlist_id: str, index: int) -> bool:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False
        playlist = self._playlists[playlist_index]
        track_ids, track_paths = self._aligned_membership(playlist)
        if not (0 <= index < len(track_paths)):
            return False
        del track_ids[index]
        del track_paths[index]
        return self._publish_membership(playlist_id, track_ids, track_paths)

    def move_track(self, playlist_id: str, from_index: int, to_index: int) -> bool:
        playlist_index = self._find_by_id(playlist_id)
        if playlist_index < 0:
            return False
        playlist = self._playlists[playlist_index]
        track_ids, track_paths = self._aligned_membership(playlist)
        if not (0 <= from_index < len(track_paths)):
            return False
        to_index = max(0, min(to_index, len(track_paths) - 1))
        moved_id = track_ids.pop(from_index)
        moved_path = track_paths.pop(from_index)
        track_ids.insert(to_index, moved_id)
        track_paths.insert(to_index, moved_path)
        return self._publish_membership(playlist_id, track_ids, track_paths)

    def collect_orphan_assets(self) -> list[str]:
        """PL-FINAL-C03: production-safe orphan GC — maintenance helper
        (never automatic at load). Returns the list of REMOVED managed
        files that proved orphan status: blobs referenced by no live
        playlist, and legacy files whose owner playlist no longer exists.
        Fail closed: unknown grammar, ambiguous owners and files of live
        playlists are never touched. Rebuildable cache debt is preferred
        over any guessed deletion."""
        store = self._artwork_store
        if store is None:
            return []
        collect = getattr(store, "collect_orphan_candidates", None)
        if collect is None:
            return []
        referenced: set[str] = set()
        for playlist in self._playlists:
            if playlist.custom_cover_path:
                referenced.add(str(Path(playlist.custom_cover_path).resolve()))
            hero = playlist.appearance.hero_image_path
            if hero:
                referenced.add(str(Path(hero).resolve()))
        live_ids = {p.playlist_id for p in self._playlists}
        candidates = collect(referenced, live_ids)
        removed: list[str] = []
        for candidate in candidates:
            try:
                candidate.unlink(missing_ok=True)
                removed.append(str(candidate))
            except OSError as exc:
                logger.warning("orphan cleanup debt: %s: %s", candidate, exc)
        return removed

    def _prepare_asset(
        self, playlist_id: str, source_path, role: str
    ) -> PreparedPlaylistAsset | None:
        """PL-10-FINAL-01: llamada DIRECTA al contrato canónico. Sin
        getattr, sin fallback que invente created_by_operation — el
        constructor ya garantiza el contrato (TypeError fail-fast)."""
        store = self._artwork_store
        if store is None:
            return None
        return store.prepare_candidate(playlist_id, source_path, role)

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
