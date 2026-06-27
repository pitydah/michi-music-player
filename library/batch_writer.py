"""Batch writer — write extracted metadata records to SQLite in batches.

Uses dynamic batch sizing with exponential backoff on failure:
  - Starts at batch_size (default 100)
  - On failure: halves the batch and retries, down to a minimum of 1
  - After a successful smaller batch: gradually grows back up
"""
import sqlite3
import time
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

_MIN_BATCH = 1
_MAX_BATCH = 500


class BatchWriter:
    """Writes metadata records to the media_items table in batches.

    On SQLite errors, uses exponential backoff: halves batch size
    and retries. After a successful smaller batch, gradually grows
    back toward the target batch_size.
    """

    def __init__(self, conn: sqlite3.Connection, batch_size: int = 100):
        self._conn = conn
        self._target_batch = max(_MIN_BATCH, min(batch_size, _MAX_BATCH))
        self._current_batch = self._target_batch
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

    @property
    def current_batch_size(self) -> int:
        return self._current_batch

    def reset_batch_size(self):
        self._current_batch = self._target_batch

    def add(self, record: dict):
        """Add a record to the buffer; flushes automatically when full."""
        self._buffer.append(record)
        if len(self._buffer) >= self._current_batch:
            self.flush()

    def flush(self) -> int:
        """Write all buffered records, using dynamic batch sizing.

        Returns count of records successfully written.
        """
        if not self._buffer:
            return 0
        return self._flush_batch(self._buffer)

    def _flush_batch(self, records: list[dict]) -> int:
        if not records:
            return 0
        params = [self._record_to_row(r) for r in records]
        count = len(records)
        try:
            self._conn.execute("BEGIN")
            self._conn.executemany(self._sql, params)
            self._conn.commit()
            self._written += count
            self._buffer = self._buffer[len(records):]
            self._grow_batch_size()
            return count
        except sqlite3.Error as e:
            self._conn.rollback()
            logger.warning(
                "Batch write failed (%d records): %s — backing off", count, e)
            return self._backoff_and_retry(records, e)

    def _backoff_and_retry(self, records: list[dict], last_error: Exception) -> int:
        if len(records) <= _MIN_BATCH:
            return self._flush_single(records)

        mid = len(records) // 2
        if mid < _MIN_BATCH:
            mid = _MIN_BATCH

        self._shrink_batch_size()
        logger.info("Backoff: splitting batch of %d into %d + %d",
                     len(records), mid, len(records) - mid)

        saved = 0
        saved += self._flush_batch(records[:mid])
        saved += self._flush_batch(records[mid:])
        return saved

    def _flush_single(self, records: list[dict]) -> int:
        saved = 0
        for r in records:
            try:
                row = self._record_to_row(r)
                self._conn.execute(self._sql, row)
                self._conn.commit()
                saved += 1
                self._written += 1
                self._buffer.remove(r)
            except sqlite3.Error as e:
                fp = r.get("filepath", "unknown")
                logger.warning("Failed to write record %s: %s", fp, e)
                try:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO index_errors"
                        " (filepath, error, stage, updated_at) VALUES (?,?,?,?)",
                        (fp, str(e)[:256], "batch_writer", time.time()))
                    self._conn.commit()
                except Exception:
                    pass
                self._buffer.remove(r)
        if saved < len(records):
            logger.warning("Single flush: %d saved, %d failed",
                           saved, len(records) - saved)
        return saved

    def _shrink_batch_size(self):
        new = max(_MIN_BATCH, self._current_batch // 2)
        if new != self._current_batch:
            logger.debug("Batch size shrunk: %d → %d", self._current_batch, new)
            self._current_batch = new

    def _grow_batch_size(self):
        if self._current_batch < self._target_batch:
            new = min(self._target_batch, int(self._current_batch * 1.5))
            if new != self._current_batch:
                logger.debug("Batch size grown: %d → %d", self._current_batch, new)
                self._current_batch = new

    def _record_to_row(self, r: dict) -> tuple:
        return tuple(
            self._default_for(r, c) for c in BATCH_COLUMNS)

    @staticmethod
    def _default_for(r: dict, col: str):
        if col in NUMERIC_DEFAULTS:
            return r.get(col, 0.0 if col in FLOAT_DEFAULTS else 0)
        return r.get(col, "")
