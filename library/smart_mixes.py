"""Smart Mixes — dynamic playlists based on play history and library data.

Uses the real schema:
  - media_items: play_count, last_played, deleted_at, genre
  - play_history: track_id (= filepath), played_at
  - favorites:  track_id (= filepath), added_at
"""

import logging
import sqlite3

from library.library_db import DB_PATH

logger = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def _has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def _deleted_filter(conn: sqlite3.Connection, alias: str = "") -> str:
    """Return 'AND deleted_at IS NULL' (optionally qualified) if the column exists."""
    if not _has_column(conn, "media_items", "deleted_at"):
        return ""
    prefix = f"{alias}." if alias else ""
    return f"AND {prefix}deleted_at IS NULL"


def get_popular(limit: int = 30) -> list[str]:
    """Most played tracks overall (by media_items.play_count)."""
    try:
        conn = _connect()
        deleted = _deleted_filter(conn)
        rows = conn.execute(
            f"SELECT filepath FROM media_items "
            f"WHERE play_count > 0 {deleted} "
            f"ORDER BY play_count DESC, last_played DESC LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.warning("get_popular failed: %s", e)
        return []


def get_daily_mix(limit: int = 30) -> list[str]:
    """Tracks played in the last 7 days.

    Uses media_items.last_played (preferred) or falls back to
    play_history.played_at grouped by track_id.
    """
    try:
        conn = _connect()
        deleted = _deleted_filter(conn)
        if _has_table(conn, "play_history"):
            # Use media_items joined with play_history for recency
            rows = conn.execute(
                f"SELECT m.filepath, MAX(h.played_at) as latest "
                f"FROM media_items m "
                f"JOIN play_history h ON h.track_id = m.filepath "
                f"WHERE h.played_at > strftime('%s','now') - 604800 {deleted} "
                f"GROUP BY m.filepath "
                f"ORDER BY m.play_count DESC, latest DESC LIMIT ?",
                (limit,)).fetchall()
            conn.close()
            if rows:
                return [r[0] for r in rows]
        # Fallback: use media_items.last_played
        conn2 = _connect()
        deleted2 = _deleted_filter(conn2)
        rows = conn2.execute(
            f"SELECT filepath FROM media_items "
            f"WHERE last_played IS NOT NULL "
            f"AND last_played > strftime('%s','now') - 604800 {deleted2} "
            f"ORDER BY play_count DESC, last_played DESC LIMIT ?",
            (limit,)).fetchall()
        conn2.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.warning("get_daily_mix failed: %s", e)
        return []


def get_unplayed(limit: int = 20) -> list[str]:
    """Tracks with play_count = 0 or never played."""
    try:
        conn = _connect()
        deleted = _deleted_filter(conn)
        rows = conn.execute(
            f"SELECT filepath FROM media_items "
            f"WHERE (play_count = 0 OR play_count IS NULL) "
            f"AND (last_played IS NULL) {deleted} "
            f"ORDER BY RANDOM() LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.warning("get_unplayed failed: %s", e)
        return []


def get_favorites_recent(limit: int = 20) -> list[str]:
    """Recently favorited tracks, ordered by favorites.added_at."""
    try:
        conn = _connect()
        if not _has_table(conn, "favorites"):
            conn.close()
            return []
        deleted = _deleted_filter(conn)
        rows = conn.execute(
            f"SELECT m.filepath FROM media_items m "
            f"JOIN favorites f ON f.track_id = m.filepath "
            f"WHERE 1=1 {deleted} "
            f"ORDER BY f.added_at DESC LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.warning("get_favorites_recent failed: %s", e)
        return []


def get_by_genre(genre: str, limit: int = 30) -> list[str]:
    """Tracks of a specific genre."""
    if not genre or not genre.strip():
        return []
    try:
        conn = _connect()
        deleted = _deleted_filter(conn)
        rows = conn.execute(
            f"SELECT filepath FROM media_items WHERE genre LIKE ? "
            f"{deleted} "
            f"ORDER BY RANDOM() LIMIT ?",
            (f"%{genre}%", limit)).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logger.warning("get_by_genre failed: %s", e)
        return []
