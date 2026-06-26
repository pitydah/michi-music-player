"""Search engine — unified search with FTS5, field filters, and LIKE fallback."""
import sqlite3
import logging

from library.query_parser import FieldOp, FieldTerm, parse_query
from library.search_index import SearchIndex

logger = logging.getLogger("michi.search_engine")

# Numeric columns that support range operators
NUMERIC_COLS = frozenset({
    "year", "bitrate", "rating", "play_count", "sample_rate",
    "channels", "bit_depth", "bpm",
})


class SearchEngine:
    """Unified search across the media_items table.

    Composes:
        - FTS5 full-text search (primary)
        - LIKE fallback (no FTS5)
        - Field-based filters (artist:Genesis, year:>2000, etc.)
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._index = SearchIndex(conn)

    @property
    def index(self) -> SearchIndex:
        return self._index

    def search(self, query: str, *, limit: int = 200,
               source_type: str = "") -> list[dict]:
        """Execute a search query. Returns list of media_items dicts."""
        if not query.strip() and not source_type:
            return self._list_all(limit)

        parsed = parse_query(query)

        # Build WHERE clauses
        conditions: list[str] = []
        params: list = []

        # FTS5 full-text filter
        if parsed.freetext:
            ids = self._index.search_fts(parsed.freetext, limit=500)
            if ids:
                placeholders = ", ".join(["?"] * len(ids))
                conditions.append(f"id IN ({placeholders})")
                params.extend(ids)
            else:
                # FTS5 returned nothing — try LIKE fallback
                ids = self._index.search_like(parsed.freetext, limit=500)
                if not ids:
                    return []  # No matches at all
                placeholders = ", ".join(["?"] * len(ids))
                conditions.append(f"id IN ({placeholders})")
                params.extend(ids)

        # Source type filter
        if source_type:
            conditions.append("kind = ?")
            params.append(source_type)

        # Field-based filters
        for term in parsed.terms:
            clause, clause_params = _build_field_clause(term)
            if clause:
                conditions.append(clause)
                params.extend(clause_params)

        # Build and execute SQL
        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM media_items WHERE ({where}) AND deleted_at IS NULL ORDER BY title ASC LIMIT ?"
        params.append(limit)

        try:
            rows = self._conn.execute(sql, params).fetchall()
            return _rows_to_dicts(rows, self._conn)
        except sqlite3.Error as e:
            logger.warning(f"Search failed: {e}")
            return []

    def count(self, query: str = "", source_type: str = "") -> int:
        """Return count of matching tracks."""
        results = self.search(query, limit=10000, source_type=source_type)
        return len(results)

    def _list_all(self, limit: int) -> list[dict]:
        try:
            rows = self._conn.execute(
                "SELECT * FROM media_items WHERE deleted_at IS NULL"
                " ORDER BY title ASC LIMIT ?",
                (limit,)).fetchall()
            return _rows_to_dicts(rows, self._conn)
        except sqlite3.Error:
            return []


def _build_field_clause(term: FieldTerm) -> tuple[str, list]:
    """Build a SQL WHERE clause fragment for a field filter term."""
    col = term.field

    if col in NUMERIC_COLS and term.op is not FieldOp.EQ:
        try:
            val = float(term.value)
        except ValueError:
            val = term.value
        op_sql = {FieldOp.GT: ">", FieldOp.GTE: ">=",
                   FieldOp.LT: "<", FieldOp.LTE: "<="}.get(term.op, "=")
        return f"{col} {op_sql} ?", [val]

    if term.op is FieldOp.EQ:
        if col == "ext":
            return "ext = ?", [f".{term.value.lstrip('.')}".lower()]
        if col == "source_type":
            return "kind = ?", [term.value.lower()]
        if col == "filepath":
            if term.value.startswith("/"):
                return "filepath LIKE ?", [f"%{term.value}%"]
            return "filepath LIKE ?", [f"%{term.value}%"]
        if col == "directory":
            return "directory LIKE ?", [f"%{term.value}%"]
        if col == "filename":
            return "filename LIKE ?", [f"%{term.value}%"]
        # Default: LIKE match for text columns
        return f"{col} LIKE ?", [f"%{term.value}%"]

    return "", []


def _rows_to_dicts(rows: list, conn: sqlite3.Connection) -> list[dict]:
    """Convert DB rows to dicts using column names from PRAGMA table_info."""
    cols = [desc[1] for desc in  # desc[1] = name, desc[0] = cid
            conn.execute("PRAGMA table_info(media_items)").fetchall()]
    return [dict(zip(cols, r, strict=False)) for r in rows]
