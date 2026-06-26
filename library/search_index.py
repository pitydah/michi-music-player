"""Search index — FTS5 full-text index on media_items, with LIKE fallback."""
import sqlite3
import logging

logger = logging.getLogger("michi.search_index")

# Columns to include in the FTS5 index
FTS_COLUMNS = ["title", "artist", "album", "albumartist",
                "genre", "composer", "filepath", "filename",
                "isrc", "label", "conductor", "grouping", "mood"]

FTS_TABLE = "media_fts"


class SearchIndex:
    """Manages the FTS5 full-text search index on media_items."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ── FTS5 ──

    @property
    def fts_available(self) -> bool:
        """Check if FTS5 extension is available."""
        try:
            self._conn.execute("SELECT fts5('test')")
            return True
        except sqlite3.OperationalError:
            return False

    @property
    def fts_exists(self) -> bool:
        """Check if the media_fts table exists."""
        try:
            row = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (FTS_TABLE,)).fetchone()
            return row is not None
        except sqlite3.Error:
            return False

    def build_fts(self):
        """Create the FTS5 content table linked to media_items."""
        if not self.fts_available:
            logger.info("FTS5 not available — using LIKE fallback")
            return False

        cols = ", ".join(FTS_COLUMNS)
        try:
            self._conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE}
                USING fts5({cols}, content='media_items', content_rowid='id')
            """)
            self._conn.commit()
            logger.info("FTS5 index created")
            return True
        except sqlite3.Error as e:
            logger.warning(f"FTS5 creation failed: {e}")
            return False

    def rebuild_fts(self):
        """Drop and recreate the FTS5 index, then fully repopulate."""
        self.drop_fts()
        if not self.build_fts():
            return False

        # Rebuild triggers insert on existing content table rows
        try:
            self._conn.execute(f"""
                INSERT INTO {FTS_TABLE}({FTS_TABLE}) VALUES('rebuild')
            """)
            self._conn.commit()
            logger.info("FTS5 index rebuilt")
            return True
        except sqlite3.Error as e:
            logger.warning(f"FTS5 rebuild failed: {e}")
            return False

    def drop_fts(self):
        """Drop the FTS5 virtual table if it exists."""
        try:
            self._conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
            self._conn.commit()
        except sqlite3.Error:
            pass

    def search_fts(self, query: str, limit: int = 200) -> list[int]:
        """Search FTS5 and return matching media_items IDs."""
        if not self.fts_available or not self.fts_exists:
            return []

        try:
            # Escape FTS5 special chars in query but keep meaningful text
            safe = _escape_fts(query)
            if not safe:
                return []

            rows = self._conn.execute(f"""
                SELECT rowid FROM {FTS_TABLE}
                WHERE {FTS_TABLE} MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (safe, limit)).fetchall()
            return [r[0] for r in rows]
        except sqlite3.Error:
            return []

    def search_like(self, query: str, limit: int = 200) -> list[int]:
        """Fallback: LIKE search across text columns."""
        if not query.strip():
            return []

        q = f"%{query}%"
        columns = ["title", "artist", "album", "albumartist",
                   "genre", "composer", "filepath"]
        conditions = " OR ".join(f"{c} LIKE ?" for c in columns)
        params = [q] * len(columns)

        try:
            rows = self._conn.execute(f"""
                SELECT id FROM media_items
                WHERE ({conditions})
                AND deleted_at IS NULL
                ORDER BY title ASC
                LIMIT ?
            """, (*params, limit)).fetchall()
            return [r[0] for r in rows]
        except sqlite3.Error:
            return []


def _escape_fts(query: str) -> str:
    """Escape FTS5 special characters and add prefix-matching."""
    clean = query.strip().replace("'", "''")
    if not clean:
        return ""
    # Split into tokens, add * suffix for prefix matching
    tokens = clean.split()
    escaped = [f"{t}*" if len(t) > 1 and not t.startswith('"') else t
               for t in tokens]
    return " ".join(escaped)
