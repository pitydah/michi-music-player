"""GenreRepository — persistent SQLite-backed repository for genre operations.

Follows the existing repository patterns in the codebase (AlbumRepository,
FeatureRepository) but operates directly on the LibraryDB connection.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Any

from metadata.genre_normalizer import (
    canonicalize_genre,
)

_log = logging.getLogger("michi.genre_repo")

_GENRE_ALIAS_FIELDS = (
    "id", "alias", "canonical_genre", "confidence",
    "source", "is_builtin", "is_user_defined", "created_at", "updated_at",
)

_TRACK_GENRE_FIELDS = (
    "id", "track_id", "genre", "canonical_genre",
    "original_value", "confidence", "source", "is_manual",
    "created_at", "updated_at",
)


class GenreRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ── Track-genre operations ──

    def ensure_track_genre(
        self, track_id: int, raw_genre: str,
        canonical: str | None = None,
        source: str = "tag",
    ) -> bool:
        norm = canonical or canonicalize_genre(raw_genre)
        if not norm or not raw_genre.strip():
            return False
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO track_genres "
                "(track_id, genre, canonical_genre, original_value, source, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (track_id, norm, norm, raw_genre.strip(), source, time.time()),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("ensure_track_genre failed: %s", e)
            return False

    def set_track_genre(self, track_id: int, genre: str, canonical: str | None = None) -> bool:
        norm = canonical or canonicalize_genre(genre)
        if not norm:
            return False
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO track_genres "
                "(track_id, genre, canonical_genre, original_value, "
                "confidence, source, is_manual, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (track_id, norm, norm, genre, 1.0, "manual", 1, time.time()),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("set_track_genre failed: %s", e)
            return False

    def remove_track_genre(self, track_id: int, genre: str) -> bool:
        try:
            self._conn.execute(
                "DELETE FROM track_genres WHERE track_id=? AND genre=?",
                (track_id, genre),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("remove_track_genre failed: %s", e)
            return False

    def get_track_genres(self, track_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, track_id, genre, canonical_genre, original_value, "
            "confidence, source, is_manual, created_at, updated_at "
            "FROM track_genres WHERE track_id=? ORDER BY genre",
            (track_id,),
        ).fetchall()
        return [dict(zip(_TRACK_GENRE_FIELDS, r, strict=False)) for r in rows]

    def get_tracks_for_genre(self, canonical_genre: str) -> list[int]:
        rows = self._conn.execute(
            "SELECT DISTINCT track_id FROM track_genres "
            "WHERE canonical_genre=? ORDER BY track_id",
            (canonical_genre,),
        ).fetchall()
        return [r[0] for r in rows]

    def get_all_canonical_genres(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT canonical_genre FROM track_genres "
            "WHERE canonical_genre != '' ORDER BY canonical_genre",
        ).fetchall()
        return [r[0] for r in rows]

    # ── Alias operations ──

    def add_alias(self, alias: str, canonical: str, confidence: float = 1.0,
                  source: str = "user", is_user_defined: bool = True) -> bool:
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO genre_aliases "
                "(alias, canonical_genre, confidence, source, "
                "is_builtin, is_user_defined, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (alias.lower().strip(), canonical, confidence, source,
                 0, int(is_user_defined), time.time()),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("add_alias failed: %s", e)
            return False

    def remove_alias(self, alias: str) -> bool:
        try:
            self._conn.execute(
                "DELETE FROM genre_aliases WHERE alias=?",
                (alias.lower().strip(),),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("remove_alias failed: %s", e)
            return False

    def get_all_aliases(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, alias, canonical_genre, confidence, source, "
            "is_builtin, is_user_defined, created_at, updated_at "
            "FROM genre_aliases ORDER BY canonical_genre, alias",
        ).fetchall()
        return [dict(zip(_GENRE_ALIAS_FIELDS, r, strict=False)) for r in rows]

    def get_aliases_for_canonical(self, canonical: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, alias, canonical_genre, confidence, source, "
            "is_builtin, is_user_defined, created_at, updated_at "
            "FROM genre_aliases WHERE canonical_genre=? ORDER BY alias",
            (canonical,),
        ).fetchall()
        return [dict(zip(_GENRE_ALIAS_FIELDS, r, strict=False)) for r in rows]

    def resolve_alias(self, raw: str) -> str | None:
        key = raw.lower().strip()
        row = self._conn.execute(
            "SELECT canonical_genre FROM genre_aliases WHERE alias=?",
            (key,),
        ).fetchone()
        if row:
            return row[0]
        return None

    # ── Cleanup suggestions ──

    def add_suggestion(self, sug_type: str, source_genre: str,
                       target_genre: str = "", affected_count: int = 0,
                       confidence: float = 0.0, reason: str = "",
                       extra: dict | None = None) -> int | None:
        try:
            cur = self._conn.execute(
                "INSERT INTO genre_cleanup_suggestions "
                "(suggestion_type, source_genre, target_genre, "
                "affected_track_count, confidence, reason, extra_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (sug_type, source_genre, target_genre,
                 affected_count, confidence, reason,
                 json.dumps(extra or {})),
            )
            self._conn.commit()
            return cur.lastrowid
        except sqlite3.Error as e:
            _log.warning("add_suggestion failed: %s", e)
            return None

    def get_pending_suggestions(self, sug_type: str | None = None) -> list[dict]:
        if sug_type:
            rows = self._conn.execute(
                "SELECT * FROM genre_cleanup_suggestions "
                "WHERE status='pending' AND suggestion_type=? "
                "ORDER BY confidence DESC, created_at DESC",
                (sug_type,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM genre_cleanup_suggestions "
                "WHERE status='pending' "
                "ORDER BY confidence DESC, created_at DESC",
            ).fetchall()
        cols = [r[1] for r in self._conn.execute(
            "PRAGMA table_info(genre_cleanup_suggestions)").fetchall()]
        return [dict(zip(cols, r, strict=False)) for r in rows]

    def resolve_suggestion(self, sug_id: int, status: str) -> bool:
        try:
            self._conn.execute(
                "UPDATE genre_cleanup_suggestions SET status=?, resolved_at=? WHERE id=?",
                (status, time.time(), sug_id),
            )
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            _log.warning("resolve_suggestion failed: %s", e)
            return False

    def clear_suggestions(self, status: str = "resolved"):
        try:
            self._conn.execute(
                "DELETE FROM genre_cleanup_suggestions WHERE status=?",
                (status,),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            _log.warning("clear_suggestions failed: %s", e)

    # ── Genre operations (merge, rename, apply) ──

    def merge_genres(self, source_genres: list[str], target: str) -> dict:
        affected = 0
        track_ids = []
        target = canonicalize_genre(target)
        for src in source_genres:
            src = canonicalize_genre(src)
            ids = self.get_tracks_for_genre(src)
            track_ids.extend(ids)
            try:
                self._conn.execute(
                    "UPDATE track_genres SET canonical_genre=?, genre=?, "
                    "updated_at=? WHERE canonical_genre=?",
                    (target, target, time.time(), src),
                )
                affected += len(ids)
            except sqlite3.Error as e:
                _log.warning("merge_genres(%s -> %s) failed: %s", src, target, e)
        self._conn.commit()
        self._log_operation("merge", ",".join(source_genres), target,
                            list(set(track_ids)), affected)
        return {"affected": affected, "track_ids": list(set(track_ids))}

    def rename_genre(self, old_name: str, new_name: str) -> int:
        try:
            cur = self._conn.execute(
                "UPDATE track_genres SET canonical_genre=?, genre=?, "
                "updated_at=? WHERE canonical_genre=?",
                (new_name, new_name, time.time(), old_name),
            )
            self._conn.commit()
            affected = cur.rowcount
            if affected:
                ids = self.get_tracks_for_genre(new_name)
                self._log_operation("rename", old_name, new_name, ids, affected)
            return affected
        except sqlite3.Error as e:
            _log.warning("rename_genre failed: %s", e)
            return 0

    def apply_genre_to_tracks(self, track_ids: list[int], genre: str,
                              write_tags: bool = False) -> int:
        count = 0
        norm = canonicalize_genre(genre)
        now = time.time()
        for tid in track_ids:
            try:
                self._conn.execute(
                    "INSERT OR REPLACE INTO track_genres "
                    "(track_id, genre, canonical_genre, original_value, "
                    "confidence, source, is_manual, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (tid, norm, norm, genre, 1.0, "manual", 1, now),
                )
                self._conn.execute(
                    "UPDATE media_items SET genre=? WHERE id=?",
                    (genre, tid),
                )
                count += 1
            except sqlite3.Error as e:
                _log.warning("apply_genre_to_tracks track %d failed: %s", tid, e)
        self._conn.commit()
        if count:
            self._log_operation("apply", "", genre, track_ids[:count], count)
        return count

    # ── Stats cache ──

    def compute_stats(self, force: bool = False) -> dict[str, Any]:
        try:
            self._conn.execute("DELETE FROM genre_stats_cache")
            rows = self._conn.execute(
                "SELECT tg.canonical_genre, "
                "COUNT(DISTINCT tg.track_id) as track_count, "
                "COUNT(DISTINCT COALESCE(m.album,'')) as album_count, "
                "COUNT(DISTINCT COALESCE(m.artist,'')) as artist_count, "
                "COALESCE(SUM(m.duration),0) as duration_total, "
                "SUM(CASE WHEN m.ext IN ('.mp3','.aac','.wma','.ogg','.opus') THEN 1 ELSE 0 END) as lossy_count, "
                "SUM(CASE WHEN m.ext NOT IN ('.mp3','.aac','.wma','.ogg','.opus') "
                "    AND (m.sample_rate >= 88200 OR m.bit_depth >= 24) THEN 1 ELSE 0 END) as hires_count, "
                "SUM(CASE WHEN m.ext NOT IN ('.mp3','.aac','.wma','.ogg','.opus') "
                "    AND (m.sample_rate < 88200 OR m.bit_depth IS NULL OR m.bit_depth < 24) THEN 1 ELSE 0 END) as lossless_count, "
                "SUM(CASE WHEN COALESCE(m.title,'')='' OR COALESCE(m.artist,'')='' "
                "    OR COALESCE(m.album,'')='' THEN 1 ELSE 0 END) as missing_meta, "
                "COALESCE(SUM(m.play_count),0) as play_count "
                "FROM track_genres tg "
                "JOIN media_items m ON m.id = tg.track_id AND m.deleted_at IS NULL "
                "GROUP BY tg.canonical_genre"
            ).fetchall()
            now = time.time()
            stats = {}
            for r in rows:
                (genre, track_count, album_count, artist_count,
                 duration, lossy, hires, lossless, missing_meta, plays) = r
                total_coded = lossy + hires + lossless
                if total_coded == 0:
                    total_coded = lossy + hires + lossless + 1
                dominant_format = "Lossy" if lossy > total_coded / 2 else (
                    "Hi-Res" if hires > total_coded / 3 else "Lossless"
                )
                health = "ok"
                if missing_meta > 0:
                    health = "warning"
                self._conn.execute(
                    "INSERT OR REPLACE INTO genre_stats_cache "
                    "(genre, canonical_genre, track_count, album_count, artist_count, "
                    "duration_total, dominant_format, dominant_quality, "
                    "lossless_count, lossy_count, hires_count, "
                    "missing_metadata_count, play_count, "
                    "health_status, last_computed_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (genre, genre, track_count, album_count, artist_count,
                     duration, dominant_format, dominant_format,
                     lossless, lossy, hires,
                     missing_meta, plays,
                     health, now),
                )
                stats[genre] = {
                    "track_count": track_count,
                    "album_count": album_count,
                    "artist_count": artist_count,
                    "duration_total": duration,
                    "dominant_format": dominant_format,
                    "dominant_quality": dominant_format,
                    "lossless_count": lossless,
                    "lossy_count": lossy,
                    "hires_count": hires,
                    "missing_metadata_count": missing_meta,
                    "play_count": plays,
                    "health": health,
                }
            self._conn.commit()
            return stats
        except sqlite3.Error as e:
            _log.warning("compute_stats failed: %s", e)
            return {}

    def get_cached_stats(self) -> dict[str, Any]:
        rows = self._conn.execute(
            "SELECT * FROM genre_stats_cache ORDER BY track_count DESC",
        ).fetchall()
        cols = [r[1] for r in self._conn.execute(
            "PRAGMA table_info(genre_stats_cache)").fetchall()]
        stats = {}
        for r in rows:
            d = dict(zip(cols, r, strict=False))
            stats[d.get("genre", "")] = d
        return stats

    def get_genre_health(self, genre: str) -> dict:
        row = self._conn.execute(
            "SELECT * FROM genre_stats_cache WHERE genre=?",
            (genre,),
        ).fetchone()
        if not row:
            return {
                "genre": genre, "health": "unknown",
                "track_count": 0, "missing_metadata_count": 0,
            }
        cols = [r[1] for r in self._conn.execute(
            "PRAGMA table_info(genre_stats_cache)").fetchall()]
        return dict(zip(cols, row, strict=False))

    def invalidate_stats(self):
        try:
            self._conn.execute("DELETE FROM genre_stats_cache")
            self._conn.commit()
        except sqlite3.Error:
            pass

    # ── Operation log ──

    def _log_operation(self, op_type: str, source: str, target: str,
                       track_ids: list[int], count: int, wrote_tags: bool = False):
        try:
            self._conn.execute(
                "INSERT INTO genre_operation_log "
                "(operation_type, source_genre, target_genre, track_ids, "
                "affected_count, wrote_tags) "
                "VALUES (?,?,?,?,?,?)",
                (op_type, source, target,
                 json.dumps(track_ids[:100]), count, int(wrote_tags)),
            )
            self._conn.commit()
        except sqlite3.Error as e:
            _log.warning("_log_operation failed: %s", e)

    def get_recent_operations(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM genre_operation_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        cols = [r[1] for r in self._conn.execute(
            "PRAGMA table_info(genre_operation_log)").fetchall()]
        return [dict(zip(cols, r, strict=False)) for r in rows]
