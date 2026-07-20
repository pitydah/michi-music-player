"""Batch writer — resilient, normalized writes to the SQLite catalogue.

Every record crosses the metadata normalization boundary exactly once before it
enters the buffer. This guarantees that display fields, normalized SQL keys,
metadata hashes and catalogue-health diagnostics cannot drift between scanners.
"""
from __future__ import annotations

import logging
import sqlite3
import time

from library.metadata_normalizer import enrich_index_record

logger = logging.getLogger("michi.indexer.batch_writer")

BATCH_COLUMNS = [
    "filepath", "filename", "directory", "ext", "kind", "size", "mtime",
    "duration", "channels", "sample_rate", "bitrate",
    "title", "artist", "album", "albumartist", "album_key",
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
    "normalized_title", "normalized_artist", "normalized_album",
    "normalized_albumartist", "metadata_source", "metadata_confidence",
    "metadata_completeness", "metadata_issues", "metadata_hash",
    "rating", "play_count", "last_played",
]

# User-owned playback/rating state must survive ordinary metadata rescans. A
# force reindex can restore it separately, but an upsert never overwrites it.
_PRESERVED_ON_CONFLICT = {
    "filepath", "created_at", "rating", "play_count", "last_played",
}
_CONFLICT_UPDATE_COLS = [
    column for column in BATCH_COLUMNS if column not in _PRESERVED_ON_CONFLICT
]

NUMERIC_DEFAULTS = frozenset({
    "size", "mtime", "duration", "channels", "sample_rate", "bitrate", "year",
    "track_number", "track_total", "disc_number", "disc_total", "bit_depth",
    "bpm", "replaygain_track", "replaygain_album", "replaygain_track_peak",
    "replaygain_album_peak", "r128_track_gain", "r128_album_gain", "compilation",
    "created_at", "updated_at", "last_scanned", "metadata_confidence",
    "metadata_completeness", "rating", "play_count", "last_played",
})

FLOAT_DEFAULTS = frozenset({
    "mtime", "duration", "replaygain_track", "replaygain_album",
    "replaygain_track_peak", "replaygain_album_peak", "r128_track_gain",
    "r128_album_gain", "created_at", "updated_at", "last_scanned",
    "metadata_confidence", "last_played",
})

_MIN_BATCH = 1
_MAX_BATCH = 500


class BatchWriter:
    """Write normalized metadata records with adaptive batch backoff."""

    def __init__(self, conn: sqlite3.Connection, batch_size: int = 100):
        self._conn = conn
        self._target_batch = max(_MIN_BATCH, min(int(batch_size), _MAX_BATCH))
        self._current_batch = self._target_batch
        self._buffer: list[dict] = []
        self._written = 0

        set_clause = ", ".join(
            f"{column}=excluded.{column}" for column in _CONFLICT_UPDATE_COLS
        )
        set_clause += ", deleted_at=NULL, scan_status='ok', scan_error=''"
        placeholders = ", ".join("?" for _ in BATCH_COLUMNS)
        self._sql = (
            f"INSERT INTO media_items ({', '.join(BATCH_COLUMNS)}) "
            f"VALUES ({placeholders}) "
            f"ON CONFLICT(filepath) DO UPDATE SET {set_clause}"
        )

    @property
    def buffered(self) -> int:
        return len(self._buffer)

    @property
    def total_written(self) -> int:
        return self._written

    @property
    def current_batch_size(self) -> int:
        return self._current_batch

    def reset_batch_size(self) -> None:
        self._current_batch = self._target_batch

    def add(self, record: dict) -> None:
        """Normalize and buffer a record; flush automatically at the threshold."""
        enriched = enrich_index_record(record)
        if not enriched.get("album_key") and enriched.get("album"):
            from library.album_key import make_album_key

            enriched["album_key"] = make_album_key(
                enriched.get("albumartist") or enriched.get("artist") or "",
                enriched.get("artist") or "",
                enriched.get("album") or "",
            )
        self._buffer.append(enriched)
        if len(self._buffer) >= self._current_batch:
            self.flush()

    def flush(self) -> int:
        """Write all buffered records, reducing batch size after SQLite errors."""
        if not self._buffer:
            return 0
        return self._flush_batch(list(self._buffer))

    def _flush_batch(self, records: list[dict]) -> int:
        if not records:
            return 0
        params = [self._record_to_row(record) for record in records]
        count = len(records)
        try:
            self._conn.execute("BEGIN")
            self._conn.executemany(self._sql, params)
            self._conn.commit()
            self._written += count
            del self._buffer[:count]
            self._grow_batch_size()
            return count
        except sqlite3.Error as error:
            self._conn.rollback()
            logger.warning(
                "Batch write failed (%d records): %s — backing off", count, error
            )
            return self._backoff_and_retry(records, error)

    def _backoff_and_retry(self, records: list[dict], last_error: Exception) -> int:
        if len(records) <= _MIN_BATCH:
            return self._flush_single(records)

        midpoint = max(_MIN_BATCH, len(records) // 2)
        self._shrink_batch_size()
        logger.info(
            "Backoff after %s: splitting batch of %d into %d + %d",
            last_error,
            len(records),
            midpoint,
            len(records) - midpoint,
        )
        return (
            self._flush_batch(records[:midpoint])
            + self._flush_batch(records[midpoint:])
        )

    def _flush_single(self, records: list[dict]) -> int:
        saved = 0
        for record in records:
            try:
                self._conn.execute(self._sql, self._record_to_row(record))
                self._conn.commit()
                saved += 1
                self._written += 1
                if self._buffer:
                    self._buffer.pop(0)
            except sqlite3.Error as error:
                self._conn.rollback()
                filepath = record.get("filepath", "unknown")
                logger.warning("Failed to write record %s: %s", filepath, error)
                self._log_write_error(filepath, error)
                if self._buffer:
                    self._buffer.pop(0)
        if saved < len(records):
            logger.warning(
                "Single flush: %d saved, %d failed", saved, len(records) - saved
            )
        return saved

    def _log_write_error(self, filepath: str, error: Exception) -> None:
        try:
            self._conn.execute(
                "INSERT INTO index_errors (filepath, error, stage, updated_at) "
                "VALUES (?,?,?,?)",
                (filepath, str(error)[:256], "batch_writer", time.time()),
            )
            self._conn.commit()
        except Exception as log_error:
            logger.warning(
                "Failed to log index_error for %s: %s", filepath, log_error
            )

    def _shrink_batch_size(self) -> None:
        new_size = max(_MIN_BATCH, self._current_batch // 2)
        if new_size != self._current_batch:
            logger.debug(
                "Batch size shrunk: %d → %d", self._current_batch, new_size
            )
            self._current_batch = new_size

    def _grow_batch_size(self) -> None:
        if self._current_batch < self._target_batch:
            new_size = min(
                self._target_batch,
                max(self._current_batch + 1, int(self._current_batch * 1.5)),
            )
            if new_size != self._current_batch:
                logger.debug(
                    "Batch size grown: %d → %d", self._current_batch, new_size
                )
                self._current_batch = new_size

    def _record_to_row(self, record: dict) -> tuple:
        return tuple(self._default_for(record, column) for column in BATCH_COLUMNS)

    @staticmethod
    def _default_for(record: dict, column: str):
        if column in NUMERIC_DEFAULTS:
            return record.get(column, 0.0 if column in FLOAT_DEFAULTS else 0)
        return record.get(column, "")
