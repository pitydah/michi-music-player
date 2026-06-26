"""Batch writer — write extracted metadata records to SQLite in batches."""
import sqlite3
import logging

logger = logging.getLogger("michi.indexer.batch_writer")

BATCH_COLUMNS = [
    "filepath", "filename", "directory", "ext", "kind", "size", "mtime",
    "duration", "channels", "sample_rate", "bitrate",
    "title", "artist", "album", "albumartist",
    "year", "genre", "track_number", "track_total",
    "disc_number", "disc_total", "composer",
    "mb_track_id", "mb_album_id", "mb_albumartist_id",
    "bit_depth", "bpm", "replaygain_track", "replaygain_album",
    "replaygain_track_peak",
    "isrc", "label", "conductor", "compilation", "media_type",
    "encoder", "copyright", "originaldate", "remixer", "grouping", "mood",
    "comment", "lyricist",
    "replaygain_album_peak", "r128_track_gain", "r128_album_gain",
    "mb_artist_id", "mb_releasegroup_id", "acoustid_id", "acoustid_fingerprint",
    "content_hash", "track_uid", "created_at",
    "updated_at", "last_scanned", "scan_status",
]

# Columns set ON CONFLICT DO UPDATE (excludes identity columns)
_CONFLICT_UPDATE_COLS = [
    c for c in BATCH_COLUMNS
    if c not in ("filepath", "created_at")
]

NUMERIC_DEFAULTS = frozenset({
    "size", "mtime", "duration", "year",
    "track_number", "track_total",
    "disc_number", "disc_total",
    "bit_depth", "bpm",
    "replaygain_track", "replaygain_album",
    "compilation",
})

FLOAT_DEFAULTS = frozenset({
    "mtime", "duration", "replaygain_track", "replaygain_album",
    "created_at", "updated_at", "last_scanned",
})


class BatchWriter:
    """Writes metadata records to the media_items table in batches."""

    def __init__(self, conn: sqlite3.Connection, batch_size: int = 100):
        self._conn = conn
        self._batch_size = batch_size
        self._buffer: list[dict] = []
        self._written = 0

        set_clause = ", ".join(
            f"{c}=excluded.{c}" for c in _CONFLICT_UPDATE_COLS)
        set_clause += ", deleted_at=NULL, scan_status='ok', scan_error=''"
        self._sql = (
            f"INSERT INTO media_items ({', '.join(BATCH_COLUMNS)}) "
            f"VALUES ({', '.join(['?'] * len(BATCH_COLUMNS))}) "
            f"ON CONFLICT(filepath) DO UPDATE SET {set_clause}")

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    @property
    def total_written(self) -> int:
        return self._written

    def add(self, record: dict):
        """Add a record to the buffer; flushes automatically when full."""
        self._buffer.append(record)
        if len(self._buffer) >= self._batch_size:
            self.flush()

    def flush(self) -> int:
        """Write all buffered records to the database. Returns count written.
        If batch fails, retries records individually to rescue valid ones."""
        if not self._buffer:
            return 0
        count = len(self._buffer)
        params = [self._record_to_row(r) for r in self._buffer]
        try:
            self._conn.execute("BEGIN")
            self._conn.executemany(self._sql, params)
            self._conn.commit()
            self._written += count
            self._buffer.clear()
            return count
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.error("Batch write failed (%d records): %s — retrying individually", count, e)
            return self._flush_individual()

    def _flush_individual(self) -> int:
        """Retry each buffered record one by one; log problematic ones."""
        saved = 0
        failed = 0
        for r in self._buffer:
            try:
                row = self._record_to_row(r)
                self._conn.execute(self._sql, row)
                self._conn.commit()
                saved += 1
                self._written += 1
            except sqlite3.Error as e:
                failed += 1
                fp = r.get("filepath", "unknown")
                logger.warning("Failed to write record %s: %s", fp, e)
                try:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO index_errors"
                        " (filepath, error, stage, updated_at) VALUES (?,?,?,?)",
                        (fp, str(e)[:256], "batch_writer", __import__("time").time()))
                    self._conn.commit()
                except Exception:
                    pass
        self._buffer.clear()
        if failed:
            logger.warning("Batch flush: %d saved, %d failed", saved, failed)
        return saved

    def _record_to_row(self, r: dict) -> tuple:
        """Convert a record dict to a tuple matching BATCH_COLUMNS."""
        return tuple(
            self._default_for(r, c) for c in BATCH_COLUMNS)

    @staticmethod
    def _default_for(r: dict, col: str):
        if col in NUMERIC_DEFAULTS:
            return r.get(col, 0.0 if col in FLOAT_DEFAULTS else 0)
        return r.get(col, "")
