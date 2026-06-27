"""Library database — high-level API for the music player's SQLite backend.

Features:
    - SQLite with WAL mode (thread-safe, check_same_thread=False)
    - Playlist CRUD, scan management, search, favorites
    - Schema management delegated to library/schema.py
"""
import os
import time
import sqlite3
import logging
import contextlib

from library.schema import Schema

logger = logging.getLogger("michi.library")


# ── Re-exports from split modules ──
from library.metadata_extractor import AUDIO_EXTS, ALL_EXTS, extract_metadata, extract_metadata_full, extract_metadata_combined  # noqa: E402, F401
from library.media_item import MediaItem, media_kind  # noqa: E402
from library.devices import get_mounted_devices, scan_device_music  # noqa: E402, F401

def _default_db_path() -> str:
    from core.paths import database_path
    return database_path()

DB_PATH = _default_db_path()


# ── Database ──

class LibraryDB:
    def __init__(self, db_path: str = DB_PATH):
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        Schema.initialize(self._conn)
        self._init_fts()

    # ── Migration / schema delegates (kept for compat) ──

    def _run_migrations(self):
        Schema.run_migrations(self._conn)

    def _migrate_scan_roots_to_library_roots(self):
        Schema._migrate_scan_roots_to_library_roots(self._conn)

    def _populate_track_uids(self):
        Schema._populate_track_uids(self._conn)

    @staticmethod
    def _compute_track_uid(filepath, artist, album, title, duration, mb_track_id):
        return Schema._compute_track_uid(filepath, artist, album, title, duration, mb_track_id)

    def _populate_track_uids(self):
        """Populate track_uid for existing rows where it was not computed."""
        cursor = self._conn.execute(
            "SELECT id, filepath, artist, album, title, duration, "
            "mb_track_id, mb_album_id "
            "FROM media_items WHERE track_uid = '' OR track_uid IS NULL")
        rows = cursor.fetchall()
        if not rows:
            return
        updates = []
        for rid, fp, artist, album, title, duration, mb_track, _mb_album in rows:
            uid = self._compute_track_uid(
                fp, artist, album, title, duration, mb_track)
            updates.append((uid, rid))
        self._conn.executemany(
            "UPDATE media_items SET track_uid=? WHERE id=?", updates)
        self._conn.commit()
        logger.info("Populated track_uid for %d records", len(updates))

    @staticmethod
    def _compute_track_uid(filepath: str, artist: str | None,
                           album: str | None, title: str | None,
                           duration: float, mb_track_id: str | None) -> str:
        """Compute a stable track UID with fallback priority:
        1. MusicBrainz Track ID (mb:<uuid>)
        2. File path hash (fp:<sha256_hex16>)
        """
        import hashlib
        if mb_track_id and mb_track_id.strip():
            return f"mb:{mb_track_id.strip()}"
        fp_hash = hashlib.sha256(filepath.encode()).hexdigest()[:16]
        return f"fp:{fp_hash}"

    def _migrate_scan_roots_to_library_roots(self):
        """Copy data from legacy scan_roots to library_roots (idempotent)."""
        try:
            existing = {r[0] for r in self._conn.execute(
                "SELECT path FROM library_roots").fetchall()}
        except sqlite3.OperationalError:
            return
        rows = self._conn.execute(
            "SELECT path, enabled, last_scan_started, last_scan_finished, "
            "file_count, added_count, updated_count, skipped_count, missing_count "
            "FROM scan_roots").fetchall()
        for (path, enabled, _started, finished,
             file_count, added, updated, skipped, missing) in rows:
            if path in existing:
                continue
            self._conn.execute(
                "INSERT OR IGNORE INTO library_roots "
                "(path, enabled, last_scan, file_count, added_count, "
                "updated_count, skipped_count, missing_count, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (path, enabled, finished, file_count, added,
                 updated, skipped, missing, finished))
        self._conn.commit()

    def _init_fts(self):
        """Create FTS5 full-text search index on media_items (if available)."""
        try:
            self._conn.execute("SELECT fts5('test')")
        except sqlite3.OperationalError:
            return  # FTS5 not available — LIKE fallback will be used
        try:
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS media_fts
                USING fts5(title, artist, album, albumartist, genre, composer,
                            filepath, filename, isrc, label, conductor, grouping, mood,
                            content='media_items', content_rowid='id')
            """)
            # Populate FTS5 with existing data (content= sync is for new rows only)
            self._conn.execute(
                "INSERT INTO media_fts(media_fts) VALUES('rebuild')")
            self._conn.commit()
        except sqlite3.Error:
            pass

    def close(self):
        self._conn.close()

    def add_file(self, filepath: str) -> int | None:
        """Add a single file to the library using BatchWriter for consistency.

        Extracts metadata (Mutagen > GStreamer > filename inference),
        computes track_uid, stores cover art, and upserts via BatchWriter.
        This ensures the same column set and ON CONFLICT logic as Indexer.
        """
        if not os.path.exists(filepath):
            return None
        ext = os.path.splitext(filepath)[1].lower()
        kind = media_kind(ext)
        if kind == "unknown":
            return None

        from library.change_detector import compute_quick_hash
        from library.batch_writer import BatchWriter
        from library.album_key import make_album_key
        from library.metadata_normalizer import (
            normalize_text, normalize_artist_name, normalize_genre,
            normalize_year, normalize_bpm, normalize_mb_id,
        )

        meta = extract_metadata_combined(filepath)
        fname = os.path.basename(filepath)
        dname = os.path.dirname(filepath)
        stat = os.stat(filepath)
        now = time.time()

        record = {
            "filepath": filepath,
            "filename": fname,
            "directory": dname,
            "ext": ext,
            "kind": kind,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "duration": meta.get("duration", 0.0) or 0.0,
            "channels": meta.get("channels", 0) or 0,
            "sample_rate": meta.get("sample_rate", 0) or 0,
            "bitrate": meta.get("bitrate", 0) or 0,
            "title": normalize_text(meta.get("title", "") or fname, 256),
            "artist": normalize_artist_name(meta.get("artist", "") or ""),
            "album": normalize_text(meta.get("album", "") or "", 256),
            "albumartist": normalize_artist_name(meta.get("albumartist", "") or ""),
            "year": normalize_year(meta.get("year")),
            "genre": normalize_genre(meta.get("genre", "") or ""),
            "track_number": int(meta.get("track_number", 0) or 0),
            "track_total": int(meta.get("track_total", 0) or 0),
            "disc_number": int(meta.get("disc_number", 0) or 0),
            "disc_total": int(meta.get("disc_total", 0) or 0),
            "composer": normalize_text(meta.get("composer", "") or "", 256),
            "mb_track_id": normalize_mb_id(meta.get("mb_track_id", "") or ""),
            "mb_album_id": normalize_mb_id(meta.get("mb_album_id", "") or ""),
            "mb_albumartist_id": normalize_mb_id(meta.get("mb_albumartist_id", "") or ""),
            "bit_depth": int(meta.get("bit_depth", 0) or 0),
            "bpm": normalize_bpm(meta.get("bpm")),
            "replaygain_track": float(meta.get("replaygain_track", 0.0) or 0.0),
            "replaygain_album": float(meta.get("replaygain_album", 0.0) or 0.0),
            "replaygain_track_peak": float(meta.get("replaygain_track_peak", 0.0) or 0.0),
            "isrc": normalize_text(meta.get("isrc", "") or "", 128),
            "label": normalize_text(meta.get("label", "") or "", 256),
            "conductor": normalize_text(meta.get("conductor", "") or "", 256),
            "compilation": int(meta.get("compilation", 0) or 0),
            "media_type": normalize_text(meta.get("media_type", "") or "", 128),
            "encoder": normalize_text(meta.get("encoder", "") or "", 256),
            "copyright": normalize_text(meta.get("copyright", "") or "", 512),
            "originaldate": normalize_text(meta.get("originaldate", "") or "", 32),
            "remixer": normalize_text(meta.get("remixer", "") or "", 256),
            "grouping": normalize_text(meta.get("grouping", "") or "", 256),
            "mood": normalize_text(meta.get("mood", "") or "", 128),
            "comment": normalize_text(meta.get("comment", "") or "", 512),
            "lyricist": normalize_text(meta.get("lyricist", "") or "", 256),
            "replaygain_album_peak": float(meta.get("replaygain_album_peak", 0.0) or 0.0),
            "r128_track_gain": float(meta.get("r128_track_gain", 0.0) or 0.0),
            "r128_album_gain": float(meta.get("r128_album_gain", 0.0) or 0.0),
            "mb_artist_id": normalize_mb_id(meta.get("mb_artist_id", "") or ""),
            "mb_releasegroup_id": normalize_mb_id(meta.get("mb_releasegroup_id", "") or ""),
            "acoustid_id": normalize_text(meta.get("acoustid_id", "") or "", 128),
            "acoustid_fingerprint": normalize_text(meta.get("acoustid_fingerprint", "") or "", 512),
            "content_hash": compute_quick_hash(filepath),
            "track_uid": self._compute_track_uid(
                filepath, meta.get("artist"), meta.get("album"),
                meta.get("title"), meta.get("duration", 0.0),
                meta.get("mb_track_id")),
            "created_at": now,
            "updated_at": stat.st_mtime,
            "last_scanned": now,
            "scan_status": "ok",
        }

        cover_data = meta.get("cover_data", b"")
        album = record["album"]
        albumartist = record["albumartist"] or record["artist"]
        if cover_data and album:
            try:
                ak = make_album_key(albumartist or "", record.get("artist", ""), album)
                cover_mime = meta.get("cover_mime", "image/jpeg")
                self._conn.execute(
                    "INSERT OR REPLACE INTO album_art_cache "
                    "(album_hash, mime, data) VALUES (?,?,?)",
                    (ak, cover_mime, cover_data))
            except Exception:
                pass

        try:
            writer = BatchWriter(self._conn, batch_size=1)
            writer.add(record)
            writer.flush()
            self._conn.commit()
            return self._conn.execute(
                "SELECT id FROM media_items WHERE filepath=?",
                (filepath,)).fetchone()[0]
        except Exception as e:
            logger.debug("add_file failed for %s: %s", filepath, e)
            return None

    def backfill_missing_metadata(self, progress_cb=None) -> int:
        """Repair records with missing metadata by re-extracting from files.

        Finds rows where title is empty/NULL or equals filename, and
        re-extracts metadata using the existing extractors, updating the DB.
        Returns the number of rows repaired.
        """
        rows = self._conn.execute(
            "SELECT id, filepath, filename FROM media_items "
            "WHERE deleted_at IS NULL "
            "AND (COALESCE(title,'') = '' OR COALESCE(artist,'') = ''"
            "     OR COALESCE(album,'') = '' OR COALESCE(duration,0) <= 0)"
            "ORDER BY id").fetchall()
        if not rows:
            return 0

        repaired = 0
        for idx, (row_id, fp, _) in enumerate(rows, 1):
            if not os.path.exists(fp):
                continue
            try:
                meta = extract_metadata_combined(fp)
                title = meta.get("title") or ""
                artist = meta.get("artist") or ""
                album = meta.get("album") or ""
                year = meta.get("year") or 0
                self._conn.execute(
                    "UPDATE media_items SET title=?, artist=?, album=?,"
                    "year=?, genre=?, duration=?, albumartist=?,"
                    "track_number=?, track_total=?, disc_number=?, disc_total=?,"
                    "composer=?, bitrate=?, sample_rate=?, channels=?,"
                    "bit_depth=?, bpm=?,"
                    "mb_track_id=?, mb_album_id=?, mb_albumartist_id=?"
                    " WHERE id=?",
                    (title, artist, album,
                     year,
                     str(meta.get("genre", "") or ""),
                     meta.get("duration", 0.0) or 0.0,
                     str(meta.get("albumartist", "") or ""),
                     int(meta.get("track_number", 0) or 0),
                     int(meta.get("track_total", 0) or 0),
                     int(meta.get("disc_number", 0) or 0),
                     int(meta.get("disc_total", 0) or 0),
                     str(meta.get("composer", "") or ""),
                     int(meta.get("bitrate", 0) or 0),
                     int(meta.get("sample_rate", 0) or 0),
                     int(meta.get("channels", 0) or 0),
                     int(meta.get("bit_depth", 0) or 0),
                     int(meta.get("bpm", 0) or 0),
                     str(meta.get("mb_track_id", "") or ""),
                     str(meta.get("mb_album_id", "") or ""),
                     str(meta.get("mb_albumartist_id", "") or ""),
                     row_id))
                repaired += 1
                if progress_cb and idx % 10 == 0:
                    progress_cb(idx, len(rows))
            except Exception as e:
                logger.debug("Backfill failed for %s: %s", fp, e)
        self._conn.commit()
        logger.info("Backfilled metadata for %d/%d records", repaired, len(rows))
        return repaired

    def backfill_missing_album_art(self, progress_cb=None) -> int:
        """Repair album_art_cache for tracks with albums but missing cached covers."""
        rows = self._conn.execute(
            "SELECT DISTINCT COALESCE(albumartist,''), COALESCE(artist,''), album "
            "FROM media_items WHERE deleted_at IS NULL "
            "AND album IS NOT NULL AND album != '' "
            "ORDER BY album").fetchall()
        if not rows:
            return 0
        repaired = 0
        for idx, (albumartist, artist, album) in enumerate(rows, 1):
            from library.album_key import make_album_key
            ak = make_album_key(albumartist or "", artist or "", album)
            exists = self._conn.execute(
                "SELECT 1 FROM album_art_cache WHERE album_hash=?",
                (ak,)).fetchone()
            if exists:
                continue
            fp_row = self._conn.execute(
                "SELECT filepath FROM media_items WHERE deleted_at IS NULL "
                "AND album=? LIMIT 1", (album,)).fetchone()
            if not fp_row:
                continue
            try:
                meta = extract_metadata_combined(fp_row[0])
                cd = meta.get("cover_data", b"")
                if cd:
                    cm = meta.get("cover_mime", "image/jpeg")
                    self._conn.execute(
                        "INSERT OR REPLACE INTO album_art_cache "
                        "(album_hash, mime, data) VALUES (?,?,?)",
                        (ak, cm, cd))
                    repaired += 1
                    self._conn.commit()
                    if progress_cb and idx % 10 == 0:
                        progress_cb(idx, len(rows))
            except Exception as e:
                logger.debug("Art backfill failed for %s: %s", album, e)
        logger.info("Backfilled album art for %d/%d albums", repaired, len(rows))
        return repaired

    def get_file_signature(self, filepath: str) -> tuple | None:
        """Return (size, mtime, content_hash) for a filepath, or None if not in DB."""
        row = self._conn.execute(
            "SELECT size, mtime, COALESCE(content_hash,'') FROM media_items "
            "WHERE filepath=? AND deleted_at IS NULL",
            (filepath,)).fetchone()
        return (row[0], row[1], row[2]) if row else None

    def ensure_file_hash(self, filepath: str) -> str:
        """Return a full SHA-256 file hash, computed once then cached in DB.

        Used by the sync manifest builder — avoids re-reading the entire file
        on every manifest build. Only recomputes if the file's mtime changed.
        """
        row = self._conn.execute(
            "SELECT COALESCE(file_hash,''), mtime FROM media_items "
            "WHERE filepath=? AND deleted_at IS NULL",
            (filepath,)).fetchone()
        db_hash, db_mtime = (row[0], row[1]) if row else ("", 0)
        try:
            current_mtime = os.path.getmtime(filepath)
        except OSError:
            return ""
        if db_hash and abs(current_mtime - (db_mtime or 0)) < 1.0:
            return db_hash
        import hashlib
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            full_hash = h.hexdigest()
            self._conn.execute(
                "UPDATE media_items SET file_hash=? WHERE filepath=?",
                (full_hash, filepath))
            self._conn.commit()
            return full_hash
        except OSError:
            return db_hash or ""

    def log_index_error(self, filepath: str, error: str, stage: str = ""):
        with contextlib.suppress(sqlite3.Error):
            self._conn.execute(
                "INSERT INTO index_errors (filepath, error, stage) VALUES (?,?,?)",
                (filepath, error, stage))
            self._conn.commit()

    def upsert_media_items_batch(self, records: list[dict]) -> int:
        """Batch insert/update media items. Returns count of affected rows."""
        if not records:
            return 0
        columns = [
            "filepath", "filename", "directory", "ext", "kind", "size", "mtime",
            "duration", "channels", "sample_rate", "bitrate",
            "title", "artist", "album", "albumartist",
            "year", "genre", "track_number", "track_total",
            "disc_number", "disc_total", "composer",
            "mb_track_id", "mb_album_id", "mb_albumartist_id",
            "bit_depth", "bpm", "replaygain_track", "replaygain_album",
            "replaygain_track_peak", "isrc", "label", "conductor",
            "compilation", "media_type", "encoder", "copyright",
            "originaldate", "remixer", "grouping", "mood", "content_hash",
        ]
        update_cols = [c for c in columns if c != "filepath"]
        set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
        sql = (
            f"INSERT INTO media_items ({', '.join(columns)}) "
            f"VALUES ({', '.join(['?'] * len(columns))}) "
            f"ON CONFLICT(filepath) DO UPDATE SET {set_clause}")
        params = []
        for r in records:
            params.append(tuple(
                r.get(c, "" if c not in ("size", "mtime", "duration", "year",
                                          "track_number", "track_total",
                                          "disc_number", "disc_total",
                                          "bit_depth", "bpm", "compilation",
                                          "replaygain_track", "replaygain_album",
                                          "replaygain_track_peak")
                    else 0 if c not in ("mtime", "duration",
                                         "replaygain_track", "replaygain_album",
                                         "replaygain_track_peak")
                    else 0.0)
                for c in columns))
        try:
            self._conn.execute("BEGIN")
            self._conn.executemany(sql, params)
            self._conn.commit()
            return len(records)
        except sqlite3.Error as e:
            self._conn.rollback()
            raise e

    def update_scan_root(self, path: str, **kwargs):
        """Update scan root statistics (legacy scan_roots + canonical library_roots)."""
        cols = ["path", "enabled", "last_scan_started", "last_scan_finished",
                "file_count", "added_count", "updated_count",
                "skipped_count", "missing_count"]
        vals = [path]
        for c in cols[1:]:
            vals.append(kwargs.get(c, 1 if c == "enabled" else 0))
        self._conn.execute(
            f"INSERT OR REPLACE INTO scan_roots ({','.join(cols)}) "
            f"VALUES ({','.join(['?']*len(cols))})", vals)
        # Mirror to library_roots
        lcols = ["path", "enabled", "last_scan", "file_count",
                 "added_count", "updated_count", "skipped_count",
                 "missing_count", "updated_at"]
        lvals = [path, kwargs.get("enabled", 1),
                 kwargs.get("last_scan_finished", 0),
                 kwargs.get("file_count", 0),
                 kwargs.get("added_count", 0),
                 kwargs.get("updated_count", 0),
                 kwargs.get("skipped_count", 0),
                 kwargs.get("missing_count", 0),
                 kwargs.get("last_scan_finished", 0)]
        self._conn.execute(
            f"INSERT OR REPLACE INTO library_roots ({','.join(lcols)}) "
            f"VALUES ({','.join(['?']*len(lcols))})", lvals)
        self._conn.commit()

    def remove_file(self, filepath: str):
        self._conn.execute("DELETE FROM media_items WHERE filepath=?", (filepath,))
        self._conn.commit()
    def remove_missing(self) -> int:
        """Soft-delete: mark files that disappeared from disk as deleted.

        Only checks files under active scan roots — not the entire library.
        Rows with deleted_at set are excluded from get_all(), search, etc.
        """
        roots = {r[0] for r in self._conn.execute(
            "SELECT path FROM scan_roots WHERE enabled=1").fetchall()}
        if not roots:
            return 0
        rows = self._conn.execute(
            "SELECT id, filepath FROM media_items "
            "WHERE deleted_at IS NULL").fetchall()
        missing = [rid for rid, fp in rows
                   if not os.path.exists(fp)
                   and any(fp.startswith(r) for r in roots)]
        now = time.time()
        for rid in missing:
            self._conn.execute(
                "UPDATE media_items SET deleted_at=?, scan_status='missing' WHERE id=?",
                (now, rid))
        self._conn.commit()
        return len(missing)


    def cleanup_missing(self) -> int:
        """Soft-delete missing files, scoped to known directories."""
        dirs = self.get_directories()
        if not dirs:
            return 0
        all_rows = self._conn.execute(
            "SELECT id, filepath FROM media_items WHERE deleted_at IS NULL").fetchall()
        missing_ids = []
        for rid, fp in all_rows:
            if not os.path.isfile(fp):
                missing_ids.append(rid)
        if not missing_ids:
            return 0
        now = time.time()
        for rid in missing_ids:
            self._conn.execute(
                "UPDATE media_items SET deleted_at=?, scan_status='missing' WHERE id=?",
                (now, rid))
        self._conn.commit()

        # Rebuild FTS5 after soft-deletes
        from library.search_index import SearchIndex
        idx = SearchIndex(self._conn)
        if idx.fts_exists:
            with contextlib.suppress(Exception):
                idx.rebuild_fts()
        return len(missing_ids)

    def cleanup_missing_under_root(self, root_path: str) -> int:
        """Soft-delete missing files ONLY under the given directory root.

        Uses normalized path prefix comparison instead of SQL LIKE to avoid
        accidental matches (e.g. root '/music' matching '/music_backup').
        """
        import os
        root = os.path.normpath(os.path.abspath(root_path)) + os.sep
        rows = self._conn.execute(
            "SELECT id, filepath FROM media_items WHERE deleted_at IS NULL"
            " AND directory >= ? AND directory < ?",
            (root, root + "\uffff")).fetchall()
        if not rows:
            return 0
        missing_ids = []
        for rid, fp in rows:
            if not os.path.isfile(fp):
                missing_ids.append(rid)
        if not missing_ids:
            return 0
        now = time.time()
        for rid in missing_ids:
            self._conn.execute(
                "UPDATE media_items SET deleted_at=?, scan_status='missing' WHERE id=?",
                (now, rid))
        self._conn.commit()
        return len(missing_ids)

    def purge_deleted(self) -> int:
        """Permanently remove soft-deleted tracks (user-requested cleanup)."""
        rows = self._conn.execute(
            "SELECT id FROM media_items WHERE deleted_at IS NOT NULL").fetchall()
        rids = [r[0] for r in rows]
        if not rids:
            return 0
        for rid in rids:
            self._conn.execute("DELETE FROM media_items WHERE id=?", (rid,))
        self._conn.execute(
            "DELETE FROM playlist_items WHERE track_id NOT IN "
            "(SELECT id FROM media_items) "
            "AND (filepath IS NULL OR filepath NOT IN "
            "(SELECT filepath FROM media_items))")
        self._conn.execute(
            "DELETE FROM favorites WHERE track_id NOT IN "
            "(SELECT filepath FROM media_items)")
        self._conn.execute(
            "DELETE FROM play_history WHERE track_id NOT IN "
            "(SELECT filepath FROM media_items)")
        self._conn.commit()
        # Rebuild FTS5 after purge
        from library.search_index import SearchIndex
        idx = SearchIndex(self._conn)
        if idx.fts_exists:
            with contextlib.suppress(Exception):
                idx.rebuild_fts()
        return len(rids)

    def _touch_last_scanned(self, filepath: str):
        """Update last_scanned for a file that was verified unchanged."""
        self._conn.execute(
            "UPDATE media_items SET last_scanned=?, scan_status='ok' WHERE filepath=?",
            (time.time(), filepath))
        self._conn.commit()

    def get_all(self, kind: str | None = None, search: str | None = None,
                 group_by: str = "") -> list[MediaItem]:
        query = (
            "SELECT id, filepath, filename, directory, ext, kind, "
            "size, mtime, duration, channels, sample_rate, bitrate, "
            "title, artist, album, year, genre, track_number, composer, "
            "albumartist, disc_number, disc_total, track_total, "
            "mb_track_id, mb_album_id, mb_albumartist_id, "
            "bit_depth, bpm, isrc, label, conductor, compilation, "
            "media_type, encoder, copyright, originaldate, remixer, "
            "grouping, mood, replaygain_track, replaygain_album, "
            "replaygain_track_peak, play_count, last_played, rating, "
            "created_at, updated_at, last_scanned, track_uid "
            "FROM media_items")
        params = []
        conditions = ["deleted_at IS NULL"]
        if kind:
            conditions.append("kind = ?")
            params.append(kind)
        if search:
            conditions.append(
                "(title LIKE ? OR artist LIKE ? OR album LIKE ? OR filepath LIKE ?)")
            q = f"%{search}%"
            params.extend([q, q, q, q])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        if group_by and group_by in ("artist", "album", "genre"):
            query += f" ORDER BY {group_by} ASC, title ASC"
        else:
            query += " ORDER BY title ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def search_advanced(self, query: str, limit: int = 200) -> list[MediaItem]:
        """Search using SearchEngine 2.0 (FTS5 + field filters)."""
        from library.search_engine import SearchEngine
        engine = SearchEngine(self._conn)
        results = engine.search(query, limit=limit)
        items = []
        for r in results:
            with contextlib.suppress(Exception):
                items.append(MediaItem.from_dict(r))
        return items

    def get_directories(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT directory FROM media_items"
            " WHERE deleted_at IS NULL ORDER BY directory").fetchall()
        return [r[0] for r in rows]

    def get_all_by_directory(self, directory: str, exact: bool = True) -> list[MediaItem]:
        """Return MediaItems for a specific directory (exact match or prefix)."""
        query = (
            "SELECT id, filepath, filename, directory, ext, kind, "
            "size, mtime, duration, channels, sample_rate, bitrate, "
            "title, artist, album, year, genre, track_number, composer, "
            "albumartist, disc_number, disc_total, track_total, "
            "mb_track_id, mb_album_id, mb_albumartist_id, "
            "bit_depth, bpm, isrc, label, conductor, compilation, "
            "media_type, encoder, copyright, originaldate, remixer, "
            "grouping, mood, replaygain_track, replaygain_album, "
            "replaygain_track_peak, play_count, last_played, rating, "
            "created_at, updated_at, last_scanned, track_uid "
            "FROM media_items WHERE deleted_at IS NULL")
        if exact:
            rows = self._conn.execute(
                query + " AND directory = ? ORDER BY track_number, title",
                (directory,)).fetchall()
        else:
            prefix = directory + ("/" if not directory.endswith("/") else "")
            rows = self._conn.execute(
                query + " AND (directory = ? OR directory LIKE ?) ORDER BY track_number, title",
                (directory, prefix + "%")).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def get_library_roots(self) -> list[str]:
        """Return active indexed root directories."""
        try:
            rows = self._conn.execute(
                "SELECT path FROM library_roots WHERE enabled=1 ORDER BY path"
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    # ── Partial metadata updates (for AI-assisted metadata review) ──

    _EDITABLE_FIELDS = frozenset({
        "title", "artist", "album", "albumartist", "year", "date", "genre",
        "track_number", "track_total", "disc_number", "disc_total",
        "composer", "bpm", "isrc", "label", "conductor",
        "mb_track_id", "mb_album_id", "mb_albumartist_id",
        "grouping", "mood", "copyright", "originaldate", "remixer", "media_type",
    })

    def update_media_item_field(self, media_id: int, field: str, value: str) -> bool:
        if field not in self._EDITABLE_FIELDS:
            return False
        if not media_id:
            return False
        try:
            self._conn.execute(
                f"UPDATE media_items SET {field}=? WHERE id=?",
                (value, media_id),
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def get_media_item_by_id(self, media_id: int):
        row = self._conn.execute(
            "SELECT * FROM media_items WHERE id=?", (media_id,)
        ).fetchone()
        if row:
            from library.media_item import MediaItem
            return MediaItem.from_row(row)
        return None

    def get_stats(self) -> dict:
        total = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL").fetchone()[0]
        audio = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='audio' AND deleted_at IS NULL").fetchone()[0]
        video = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE kind='video' AND deleted_at IS NULL").fetchone()[0]
        dur = self._conn.execute(
            "SELECT COALESCE(SUM(duration),0) FROM media_items WHERE deleted_at IS NULL").fetchone()[0] or 0
        return {"total": total, "audio": audio, "video": video, "duration": dur}

    def get_dashboard_stats(self) -> dict:
        """Aggregated stats for the Home dashboard — no full table scan."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL").fetchone()[0]
        artists = self._conn.execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(artist,''),"
            " NULLIF(albumartist,''))) FROM media_items WHERE deleted_at IS NULL").fetchone()[0]
        albums = self._conn.execute(
            "SELECT COUNT(DISTINCT COALESCE(NULLIF(album,''),NULLIF(albumartist,'')))"
            " FROM media_items WHERE deleted_at IS NULL").fetchone()[0]
        dur = self._conn.execute(
            "SELECT COALESCE(SUM(duration),0) FROM media_items WHERE deleted_at IS NULL").fetchone()[0] or 0
        missing_meta = self._conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
            " AND (COALESCE(title,'')='' OR COALESCE(artist,'')='' OR COALESCE(album,'')='')").fetchone()[0]
        return {"total_songs": total, "total_artists": artists,
                "total_albums": albums, "total_duration": dur,
                "missing_metadata": missing_meta}

    def find_duplicates(self) -> list[dict]:
        """Find duplicate tracks in the library.

        A duplicate is defined as having the same track_uid or the same
        content_hash (quick hash). Returns a list of dicts with:
          - key: the duplicate key (track_uid or content_hash)
          - type: "uid" or "hash"
          - tracks: list of dicts with id, filepath, title, artist, album
        """
        duplicates = []
        # By track_uid (most reliable — catches renamed/moved files)
        rows = self._conn.execute(
            "SELECT track_uid, GROUP_CONCAT(id) as ids, "
            "GROUP_CONCAT(filepath, '||') as paths, COUNT(*) as cnt "
            "FROM media_items WHERE deleted_at IS NULL "
            "AND track_uid != '' AND track_uid IS NOT NULL "
            "GROUP BY track_uid HAVING cnt > 1"
        ).fetchall()
        for row in rows:
            track_uid, ids_str, paths_str, cnt = row
            ids = [int(x) for x in ids_str.split(",")]
            paths = paths_str.split("||")
            duplicates.append({
                "key": track_uid, "type": "uid", "count": cnt,
                "ids": ids, "filepaths": paths,
            })

        # By content_hash (files with identical first+last 64KB)
        rows = self._conn.execute(
            "SELECT content_hash, GROUP_CONCAT(id) as ids, "
            "GROUP_CONCAT(filepath, '||') as paths, COUNT(*) as cnt "
            "FROM media_items WHERE deleted_at IS NULL "
            "AND content_hash != '' AND content_hash IS NOT NULL "
            "AND content_hash NOT IN ("
            "  SELECT DISTINCT content_hash FROM media_items "
            "  WHERE track_uid != '' AND track_uid IS NOT NULL"
            ") "
            "GROUP BY content_hash HAVING cnt > 1"
        ).fetchall()
        for row in rows:
            ch, ids_str, paths_str, cnt = row
            ids = [int(x) for x in ids_str.split(",")]
            paths = paths_str.split("||")
            duplicates.append({
                "key": ch[:16], "type": "hash", "count": cnt,
                "ids": ids, "filepaths": paths,
            })

        return duplicates

    def get_directory_stats(self, directory: str) -> dict:
        """Return aggregated stats for a directory."""
        row = self._conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(duration), 0) FROM media_items "
            "WHERE directory = ? AND deleted_at IS NULL",
            (directory,)).fetchone()
        return {
            "file_count": row[0] if row else 0,
            "total_duration": float(row[1]) if row else 0.0,
        }

    # ── Playlists ──

    # Extracted to library/playlist_store.py — CRUD playlists
    def create_playlist(self, name: str) -> int:
        cur = self._conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,))
        self._conn.commit()
        return cur.lastrowid

    def delete_playlist(self, pid: int):
        self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
        self._conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
        self._conn.commit()

    def get_playlists(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, name, cover_path, cover_type, description, created_at "
            "FROM playlists ORDER BY name").fetchall()
        return [{"id": r[0], "name": r[1], "cover_path": r[2] or "",
                 "cover_type": r[3] or "mosaic", "description": r[4] or "",
                 "created_at": r[5] if len(r) > 5 else 0}
                for r in rows]

    def update_playlist(self, pid: int, name: str = "", description: str = "",
                        cover_path: str = "", cover_type: str = ""):
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if cover_path is not None:
            updates.append("cover_path = ?")
            params.append(cover_path)
        if cover_type is not None:
            updates.append("cover_type = ?")
            params.append(cover_type)
        if updates:
            params.append(pid)
            self._conn.execute(
                f"UPDATE playlists SET {', '.join(updates)} WHERE id = ?", params)
            self._conn.commit()

    def add_to_playlist(self, pid: int, filepath: str = "", track_id: int | None = None):
        """Add a track to a playlist. Accepts filepath (legacy) and/or track_id.

        Auto-calculates position = MAX(position) + 1 within the playlist.
        Deduplicates by track_id when available, then by filepath.
        """
        tid = track_id
        if tid is None and filepath:
            row = self._conn.execute(
                "SELECT id FROM media_items WHERE filepath=?", (filepath,)).fetchone()
            tid = row[0] if row else None
        # Check duplicate
        if tid is not None:
            dup = self._conn.execute(
                "SELECT 1 FROM playlist_items WHERE playlist_id=? AND track_id=?",
                (pid, tid)).fetchone()
        else:
            dup = self._conn.execute(
                "SELECT 1 FROM playlist_items WHERE playlist_id=? AND filepath=?",
                (pid, filepath)).fetchone()
        if dup:
            return  # already exists, skip silently
        # Calculate next position
        pos_row = self._conn.execute(
            "SELECT MAX(position) FROM playlist_items WHERE playlist_id=?",
            (pid,)).fetchone()
        next_pos = (pos_row[0] + 1) if pos_row[0] is not None else 0
        self._conn.execute(
            "INSERT INTO playlist_items (playlist_id, filepath, track_id, position) "
            "VALUES (?,?,?,?)",
            (pid, filepath or "", tid, next_pos))
        self._conn.commit()

    def get_playlist_items(self, pid: int) -> list[MediaItem]:
        rows = self._conn.execute(
            "SELECT m.* FROM media_items m "
            "JOIN playlist_items p ON (p.track_id = m.id OR p.filepath = m.filepath) "
            "WHERE p.playlist_id = ? ORDER BY p.position, m.title",
            (pid,)).fetchall()
        return [MediaItem.from_row(r) for r in rows]

    def get_playlist_track_ids(self, pid: int) -> list[int]:
        """Return canonical track IDs for a playlist (uses track_id when available)."""
        rows = self._conn.execute(
            "SELECT COALESCE(p.track_id, m.id) FROM playlist_items p "
            "LEFT JOIN media_items m ON m.filepath = p.filepath "
            "WHERE p.playlist_id = ? ORDER BY p.position, m.title",
            (pid,)).fetchall()
        return [r[0] for r in rows if r[0] is not None]

    # Extracted to library/history_store.py — favorites, play history, detected tracks
    def save_queue(self, filepaths: list[str], current_index: int):
        self._conn.execute("DELETE FROM queue_state")
        self._conn.execute("INSERT INTO queue_state (id, filepath) VALUES (?,?)", (-1, str(current_index)))
        for i, fp in enumerate(filepaths):
            self._conn.execute("INSERT INTO queue_state (id, filepath) VALUES (?,?)", (i, fp))
        self._conn.commit()

    def load_queue(self) -> tuple[list[str], int]:
        rows = self._conn.execute(
            "SELECT id, filepath FROM queue_state ORDER BY id").fetchall()
        index = 0
        filepaths = []
        for r in rows:
            if r[0] == -1:
                index = int(r[1]) if r[1].isdigit() else 0
            else:
                filepaths.append(r[1])
        return filepaths, index

    def clear_queue_state(self):
        self._conn.execute("DELETE FROM queue_state")
        self._conn.commit()

    def update_play_history(self, track_id: str, device: str = "desktop"):
        self._conn.execute(
            "INSERT INTO play_history (track_id, device) VALUES (?,?)", (track_id, device))
        self._conn.commit()

    def increment_play_count(self, filepath: str):
        self._conn.execute(
            "UPDATE media_items SET play_count = play_count + 1, "
            "last_played = ? WHERE filepath = ?",
            (__import__("time").time(), filepath),
        )
        self._conn.commit()

    def toggle_favorite(self, track_id: str, device: str = "desktop") -> bool:
        cur = self._conn.execute(
            "SELECT track_id FROM favorites WHERE track_id = ?", (track_id,))
        if cur.fetchone():
            self._conn.execute("DELETE FROM favorites WHERE track_id = ?", (track_id,))
            self._conn.commit()
            return False
        self._conn.execute(
            "INSERT INTO favorites (track_id, device) VALUES (?,?)", (track_id, device))
        self._conn.commit()
        return True

    def get_by_id(self, item_id: int) -> MediaItem | None:
        """Fetch a single MediaItem by primary key id."""
        row = self._conn.execute(
            "SELECT id, filepath, filename, directory, ext, kind, "
            "size, mtime, duration, channels, sample_rate, bitrate, "
            "title, artist, album, year, genre, track_number, composer, "
            "albumartist, disc_number, disc_total, track_total, "
            "mb_track_id, mb_album_id, mb_albumartist_id, "
            "bit_depth, bpm, isrc, label, conductor, compilation, "
            "media_type, encoder, copyright, originaldate, remixer, "
            "lyrics, track_uid, replaygain_track_gain, replaygain_track_peak, "
            "replaygain_album_gain, replaygain_album_peak, "
            "deleted_at, created_at, updated_at "
            "FROM media_items WHERE id = ? AND deleted_at IS NULL", (item_id,)
        ).fetchone()
        if not row:
            return None
        return MediaItem.from_row(row)

    def get_favorites(self, device: str = "desktop") -> list[str]:
        rows = self._conn.execute(
            "SELECT track_id FROM favorites ORDER BY added_at DESC").fetchall()
        return [r[0] for r in rows]

    def get_deleted_since(self, since: float = 0.0) -> list[dict]:
        """Return soft-deleted tracks newer than a Unix timestamp."""
        rows = self._conn.execute(
            "SELECT id, filepath, title, artist, album, duration, ext,"
            " size, year, genre, track_uid"
            " FROM media_items WHERE deleted_at IS NOT NULL"
            " AND deleted_at >= ?", (since,)).fetchall()
        return [{"id": r[0], "filepath": r[1], "title": r[2] or "",
                 "artist": r[3] or "", "album": r[4] or "",
                 "duration": r[5] or 0, "ext": r[6] or "",
                 "size": r[7] or 0, "year": r[8] or 0,
                 "genre": r[9] or "", "track_uid": r[11] or ""}
                for r in rows]

    def get_play_history(self, device: str = "desktop") -> list[dict]:
        rows = self._conn.execute(
            "SELECT track_id, played_at FROM play_history ORDER BY played_at DESC LIMIT 100"
        ).fetchall()
        return [{"track_id": r[0], "played_at": r[1]} for r in rows]

    # ── Detected Tracks ──

    def add_detected_track(
        self, title: str, artist: str, album: str = "", year: int = 0,
        genre: str = "", duration: float = 0.0, source: str = "",
        provider: str = "", confidence: float = 0.0, isrc: str = "",
        artwork_url: str = "", external_url: str = "", filepath: str = "",
        matched_library_id: int = 0, raw_json: str = ""
    ):
        self._conn.execute(
            "INSERT INTO detected_tracks (title,artist,album,year,genre,duration,"
            "source,provider,confidence,isrc,artwork_url,external_url,filepath,"
            "matched_library_id,raw_json,detected_at) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%s','now'))",
            (title, artist, album, year, genre, duration, source, provider,
             confidence, isrc, artwork_url, external_url, filepath,
             matched_library_id, raw_json))
        self._conn.commit()

    def get_detected_tracks(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM detected_tracks ORDER BY detected_at DESC LIMIT ?",
            (limit,)).fetchall()
        cols = [desc[1] for desc in self._conn.execute(  # desc[1]=name, desc[0]=cid
            "PRAGMA table_info(detected_tracks)").fetchall()]
        return [dict(zip(cols, r, strict=False)) for r in rows]

    def clear_detected_tracks(self):
        self._conn.execute("DELETE FROM detected_tracks")
        self._conn.commit()

    def delete_detected_track(self, track_id: int):
        self._conn.execute("DELETE FROM detected_tracks WHERE id = ?", (track_id,))
        self._conn.commit()

    def find_detected_track_recent(
        self, title: str, artist: str, max_age_hours: int = 24
    ) -> dict | None:
        rows = self._conn.execute(
            "SELECT * FROM detected_tracks WHERE title=? AND artist=? "
            "AND detected_at > strftime('%s','now') - ? ORDER BY detected_at DESC LIMIT 1",
            (title, artist, max_age_hours * 3600)).fetchall()
        if not rows:
            return None
        cols = [desc[1] for desc in self._conn.execute(  # desc[1]=name
            "PRAGMA table_info(detected_tracks)").fetchall()]
        return dict(zip(cols, rows[0], strict=False))
