"""Transactional legacy identity migration (M6-EXT-R4-D).

One owner, ONE transaction: everything that references migrated track
identity in the MAIN SQLite database moves together — catalog (sources /
media / tracks), user state (favorites / history / recently added),
playlist records (V1/V2 → V3) and the session snapshot (V1/V2 → V3).
A crash or injected failure between stages can never produce split
identity state: every stage commits or the WHOLE migration rolls back.

Rules honored:
- legacy path → TrackId map is built from EVERY path reference (index,
  favorites, history, recent, playlists, queue/session snapshot, playback
  current path) — missing files keep their important user state.
- legacy ids are deterministic (UUID5, project-fixed namespaces) — reruns
  are no-ops and never rewrite ids.
- ``settings.last_directory`` is a MIGRATION HINT: a trustworthy root
  yields one deterministic legacy LibrarySource; paths outside it become
  unresolved legacy media (source/relative NULL) — no guessed commonpath.
- The catalog schema guard (validate_or_initialize_catalog) owns
  fail-closed behavior; this module writes the same DDL inside its own
  transaction.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from michi.domain.library_catalog import (
    SourceLifecycle,
    legacy_media_id,
    legacy_source_id,
    legacy_track_id,
)
from michi.domain.session import decode_snapshot, encode_snapshot
from michi.infrastructure.library_catalog import (
    CATALOG_SCHEMA_DDL,
    CATALOG_SCHEMA_VERSION,
)
from michi.infrastructure.playlists import (
    PLAYLIST_PERSISTENCE_VERSION,
    _decode_playlist_entry,
)

logger = logging.getLogger(__name__)

_VERSION_KEY = "schema_version"


class LibraryMigrationError(RuntimeError):
    """The identity migration failed at a named stage; the database was
    rolled back and remains retry-safe."""

    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"library identity migration failed at {stage}: {detail}")
        self.stage = stage
        self.detail = detail


@dataclass(frozen=True)
class MigrationResult:
    """Truthful outcome of a migration run."""

    migrated: bool
    legacy_root: str | None = None
    sources_created: int = 0
    media_created: int = 0
    tracks_created: int = 0
    favorites_migrated: int = 0
    history_migrated: int = 0
    recently_added_migrated: int = 0
    playlists_rewritten: int = 0
    session_upgraded: bool = False


class LibraryIdentityMigration:
    """Owns the cross-state atomic legacy identity migration.

    ``inject_failures`` is a TEST-ONLY seam: naming a stage makes the
    migration raise exactly there (after the stage's writes), proving the
    whole transaction rolls back and retries cleanly.
    """

    STAGES = (
        "validate",
        "collect",
        "source_write",
        "media_write",
        "track_write",
        "favorites_write",
        "history_write",
        "recently_added_write",
        "playlist_write",
        "session_write",
        "version_write",
    )

    def __init__(
        self, db_path: Path, *, inject_failures: frozenset[str] = frozenset()
    ) -> None:
        self._db_path = db_path
        unknown = inject_failures - set(self.STAGES)
        if unknown:
            raise ValueError(f"unknown migration failpoints: {sorted(unknown)}")
        self._inject_failures = inject_failures

    def migrate(self) -> MigrationResult:
        conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._failpoint("validate")
            if self._catalog_already_initialized(conn):
                conn.execute("ROLLBACK")
                return MigrationResult(migrated=False)
            return self._migrate_locked(conn)
        except Exception as exc:
            conn.execute("ROLLBACK")
            stage = getattr(exc, "stage", "unknown")
            raise LibraryMigrationError(stage, str(exc)) from exc
        finally:
            conn.close()

    def _failpoint(self, stage: str) -> None:
        if stage in self._inject_failures:
            error = RuntimeError(f"injected migration failure at {stage}")
            error.stage = stage  # type: ignore[attr-defined]
            raise error

    # ------------------------------------------------------------ discovery

    def _catalog_already_initialized(self, conn: sqlite3.Connection) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'library_catalog_meta'"
        ).fetchone()
        return row is not None

    def _table_exists(self, conn: sqlite3.Connection, name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        return row is not None

    def _legacy_index_paths(self, conn: sqlite3.Connection) -> list[str]:
        if not self._table_exists(conn, "library_index"):
            return []
        return [row[0] for row in conn.execute("SELECT track_id FROM library_index")]

    def _legacy_prefs(self, conn: sqlite3.Connection) -> dict[str, list[str]]:
        """Read library_prefs JSON lists strictly (malformed → empty)."""
        result = {"favorites": [], "history": [], "recently_added": []}
        if not self._table_exists(conn, "library_prefs"):
            return result
        rows = conn.execute("SELECT key, value FROM library_prefs").fetchall()
        for key, value in rows:
            if key not in result:
                continue
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                continue
            if isinstance(parsed, list) and all(isinstance(p, str) for p in parsed):
                result[key] = parsed
        return result

    def _legacy_playlists(self, conn: sqlite3.Connection) -> list[dict]:
        if not self._table_exists(conn, "library_prefs"):
            return []
        row = conn.execute(
            "SELECT value FROM library_prefs WHERE key = 'playlists'"
        ).fetchone()
        if row is None:
            return []
        try:
            parsed = json.loads(row[0])
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [entry for entry in parsed if isinstance(entry, dict)]

    def _legacy_session(self, conn: sqlite3.Connection) -> tuple[str | None, object]:
        """(raw session payload or None, decoded snapshot or None)."""
        if not self._table_exists(conn, "settings"):
            return None, None
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'session_snapshot'"
        ).fetchone()
        if row is None:
            return None, None
        return row[0], decode_snapshot(row[0])

    def _last_directory(self, conn: sqlite3.Connection) -> str:
        if not self._table_exists(conn, "settings"):
            return ""
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'last_directory'"
        ).fetchone()
        return row[0] if row is not None and isinstance(row[0], str) else ""

    # ------------------------------------------------------------- migration

    def _migrate_locked(self, conn: sqlite3.Connection) -> MigrationResult:
        self._failpoint("collect")
        index_paths = self._legacy_index_paths(conn)
        prefs = self._legacy_prefs(conn)
        playlists = self._legacy_playlists(conn)
        session_raw, session = self._legacy_session(conn)

        # One deterministic path → (media_id, track_id) map from EVERY path
        # reference (missing files included — user state must survive).
        referenced_paths: dict[str, None] = {p: None for p in index_paths}
        for collection in prefs.values():
            for path in collection:
                referenced_paths.setdefault(path, None)
        for entry in playlists:
            for ref in _playlist_refs(entry):
                referenced_paths.setdefault(ref, None)
        if session is not None:
            for entry in (*session.queue_entries, *session.context.entries):
                referenced_paths.setdefault(entry.file_path, None)
            if session.playback_path:
                referenced_paths.setdefault(session.playback_path, None)

        root = self._last_directory(conn)
        legacy_root = root or None
        root_path = Path(root) if root else None

        source_id = legacy_source_id(root) if root else None
        created = _CatalogWrites()

        # 1. CREATE the catalog schema (same DDL as the repository).
        for statement in CATALOG_SCHEMA_DDL:
            conn.execute(statement)
        self._failpoint("source_write")

        # 2. LEGACY SOURCE from the last_directory hint (trustworthy root).
        if root:
            conn.execute(
                "INSERT INTO library_sources(library_source_id, display_name, "
                "root_path, enabled, lifecycle, created_at_ms, updated_at_ms) "
                "VALUES(?, ?, ?, 1, ?, 0, 0)",
                (
                    source_id,
                    _legacy_source_display_name(root),
                    root,
                    SourceLifecycle.ACTIVE.value,
                ),
            )
            created.sources = 1
        self._failpoint("media_write")

        # 3. MEDIA + TRACK records (deterministic legacy ids).
        for path in sorted(referenced_paths):
            media_id = legacy_media_id(path)
            track_id = legacy_track_id(path)
            relative = None
            attached_source = None
            if root_path is not None and _is_under(path, root_path):
                relative = Path(path).relative_to(root_path).as_posix()
                attached_source = source_id
            conn.execute(
                "INSERT INTO library_media_files(media_file_id, "
                "library_source_id, relative_path, last_known_path, "
                "availability, created_at_ms, updated_at_ms) "
                "VALUES(?, ?, ?, ?, 'unknown', 0, 0)",
                (media_id, attached_source, relative, path),
            )
            created.media += 1
            conn.execute(
                "INSERT INTO library_tracks(track_id, media_file_id, "
                "created_at_ms) VALUES(?, ?, 0)",
                (track_id, media_id),
            )
            created.tracks += 1
        self._failpoint("track_write")

        # 4. USER STATE by TrackId (favorites sorted; history/recent order).
        self._write_user_state(
            conn, "library_favorites", _resolve_ids(prefs["favorites"]), "track_id"
        )
        created.favorites = len(prefs["favorites"])
        self._failpoint("favorites_write")
        self._write_user_state(
            conn, "library_history", _resolve_ids(prefs["history"]), "position"
        )
        created.history = len(prefs["history"])
        self._failpoint("history_write")
        self._write_user_state(
            conn,
            "library_recently_added",
            _resolve_ids(prefs["recently_added"]),
            "position",
        )
        created.recently_added = len(prefs["recently_added"])
        self._failpoint("recently_added_write")

        # 5. PLAYLISTS → V3 (stable ids, fallback paths, derived projection).
        if playlists:
            upgraded = [_upgrade_playlist(entry) for entry in playlists]
            conn.execute(
                "INSERT INTO library_prefs(key, value) VALUES('playlists', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (json.dumps(upgraded),),
            )
            created.playlists = len(upgraded)
        self._failpoint("playlist_write")

        # 6. SESSION SNAPSHOT → V3 (entries gain library_track_id).
        # A fresh snapshot (malformed/absent payload) is left untouched —
        # the malformed original is preserved, never rewritten.
        from michi.domain.session import fresh_snapshot

        if (
            session is not None
            and session_raw is not None
            and session != fresh_snapshot()
        ):
            upgraded = _upgrade_session(session)
            conn.execute(
                "INSERT INTO settings(key, value) VALUES('session_snapshot', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (encode_snapshot(upgraded),),
            )
            created.session_upgraded = True
        self._failpoint("session_write")

        # 7. VERSION row — the catalog now exists at the current version.
        conn.execute(
            "INSERT INTO library_catalog_meta(key, value) VALUES(?, ?)",
            (_VERSION_KEY, str(CATALOG_SCHEMA_VERSION)),
        )
        self._failpoint("version_write")

        conn.execute("COMMIT")
        return MigrationResult(
            migrated=True,
            legacy_root=legacy_root,
            sources_created=created.sources,
            media_created=created.media,
            tracks_created=created.tracks,
            favorites_migrated=created.favorites,
            history_migrated=created.history,
            recently_added_migrated=created.recently_added,
            playlists_rewritten=created.playlists,
            session_upgraded=created.session_upgraded,
        )

    def _write_user_state(
        self, conn: sqlite3.Connection, table: str, ids: list[str], key_column: str
    ) -> None:
        if key_column == "track_id":
            for track_id in sorted(ids):
                conn.execute(f"INSERT INTO {table}(track_id) VALUES(?)", (track_id,))
        else:
            for position, track_id in enumerate(ids):
                conn.execute(
                    f"INSERT INTO {table}({key_column}, track_id) VALUES(?, ?)",
                    (position, track_id),
                )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CatalogWrites:
    def __init__(self) -> None:
        self.sources = 0
        self.media = 0
        self.tracks = 0
        self.favorites = 0
        self.history = 0
        self.recently_added = 0
        self.playlists = 0
        self.session_upgraded = False


def _legacy_source_display_name(root: str) -> str:
    name = Path(root).name.strip()
    return name or "Legacy Library"


def _is_under(path: str, root: Path) -> bool:
    try:
        return Path(path).is_relative_to(root)
    except ValueError:
        return False


def _playlist_refs(entry: dict) -> list[str]:
    """Legacy path references inside a playlist payload (V1/V2 paths;
    V3 fallback paths)."""
    playlist = _decode_playlist_entry(entry)
    if playlist is None:
        return []
    return list(playlist.track_paths)


def _resolve_ids(paths: list[str]) -> list[str]:
    """Deterministic path → TrackId resolution (UUID5 migration machinery)."""
    return [legacy_track_id(path) for path in paths]


def _upgrade_playlist(entry: dict) -> dict:
    """Rewrite a playlist payload to V3, preserving identity/visuals.

    Existing V3 track_ids are preserved (idempotent); legacy V1/V2 paths
    resolve through the deterministic map; unknown paths keep a fallback
    snapshot with an empty id (honest: never fabricated).
    """
    playlist = _decode_playlist_entry(entry)
    if playlist is None:
        return entry  # malformed entries are preserved untouched
    tracks = []
    for ref in playlist.references():
        resolved_id = ref.track_id
        if not resolved_id and ref.fallback_path:
            resolved_id = legacy_track_id(ref.fallback_path)
        tracks.append({"track_id": resolved_id, "fallback_path": ref.fallback_path})
    upgraded = {
        "version": PLAYLIST_PERSISTENCE_VERSION,
        "id": playlist.playlist_id,
        "name": playlist.name,
        "tracks": tracks,
        "track_paths": [t["fallback_path"] for t in tracks],
    }
    if playlist.custom_cover_path:
        upgraded["custom_cover_path"] = playlist.custom_cover_path
    if playlist.appearance:
        appearance = playlist.appearance
        upgraded["appearance"] = {
            "hero_mode": appearance.hero_mode.value,
            "hero_solid_color": appearance.hero_solid_color,
            "hero_gradient_colors": list(appearance.hero_gradient_colors),
            "hero_gradient_angle": appearance.hero_gradient_angle,
            "hero_image_path": appearance.hero_image_path,
        }
    return upgraded


def _upgrade_session(snapshot) -> object:
    """Rewrite a decoded snapshot to V3 with library identity.

    Entries already carrying a library_track_id keep it; legacy path-only
    entries resolve through the deterministic map; unmapped paths stay
    honest (None id, fallback path).
    """
    from michi.domain.session import (
        FORMAT_VERSION,
        PersistedQueueEntry,
        PersistedSessionContext,
        PlaybackSessionSnapshot,
    )

    def upgraded(entry) -> PersistedQueueEntry:
        track_id = entry.library_track_id
        if track_id is None and entry.file_path:
            track_id = legacy_track_id(entry.file_path)
        return PersistedQueueEntry(
            file_path=entry.file_path,
            title=entry.title,
            library_track_id=track_id,
        )

    return PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=tuple(upgraded(e) for e in snapshot.queue_entries),
        context=PersistedSessionContext(
            context_type=snapshot.context.context_type,
            source_id=snapshot.context.source_id,
            entries=tuple(upgraded(e) for e in snapshot.context.entries),
            current_index=snapshot.context.current_index,
        ),
        playback_path=snapshot.playback_path,
        position_ms=snapshot.position_ms,
        repeat_mode=snapshot.repeat_mode,
        shuffle_enabled=snapshot.shuffle_enabled,
        shuffle_seed=snapshot.shuffle_seed,
    )
