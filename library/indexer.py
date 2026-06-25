"""Indexer 2.0 — orchestrates full indexing pipeline.

Flow:
    FileWalker → ChangeDetector → MetadataExtractor → AlbumKeyBuilder
    → BatchWriter → Cleanup → Rebuild UI indexes → Schedule enrichment
"""
import os
import time
import logging

from PySide6.QtCore import Signal, QObject

from library.index_state import ScanState, ScanPhase
from library.batch_writer import BatchWriter
from library.metadata_normalizer import (
    normalize_text, normalize_artist_name, normalize_genre, normalize_year,
    normalize_disc_track, normalize_bpm, normalize_mb_id,
)
from library.metadata_extractor import ALL_EXTS, extract_metadata_combined
from library.media_item import media_kind
from library.album_key import make_album_key, make_artist_key

logger = logging.getLogger("michi.indexer")


class Indexer(QObject):
    """Main indexer — walks files, detects changes, extracts metadata,
    writes in batches, cleans up missing files, and schedules enrichment."""

    # Signals
    progress = Signal(int, int, str)           # current, total, filepath
    detail = Signal(dict)                     # full ScanState as dict
    batch_complete = Signal(int)              # records written
    cleanup_complete = Signal(int)            # records removed
    finished = Signal(int)                    # total added
    enrichment_requested = Signal(str, str)   # artist_key, artist_name

    @classmethod
    def from_db_path(cls, db_path: str, root_path: str, parent=None):
        """Create an Indexer with its own LibraryDB connection from a path."""
        from library.library_db import LibraryDB
        db = LibraryDB(db_path)
        return cls(db, root_path, parent)

    def __init__(self, db, root_path: str, parent=None):
        super().__init__(parent)
        self._db = db
        self._root_path = root_path
        self._state = ScanState()
        self._cancelled = False

    # ── Public API ──

    @property
    def state(self) -> ScanState:
        return self._state

    def cancel(self):
        self._cancelled = True
        self._state.cancel()

    def run(self):
        """Execute the full indexing pipeline."""
        self._state.start(self._root_path)
        self._db.update_scan_root(self._root_path, last_scan_started=time.time())

        try:
            # Phase 1: Walk files
            self._state.set_phase(ScanPhase.WALKING)
            files = list(self._walk_files())
            self._state.file_count = len(files)

            if self._cancelled:
                return self._finish()

            # Process files: detect changes, extract metadata, build album keys
            self._state.set_phase(ScanPhase.EXTRACTING)
            batch_writer = BatchWriter(self._db._conn)

            for i, fp in enumerate(files):
                if self._cancelled:
                    break

                self._state.current_file = fp
                pct = ((i + 1) / max(self._state.file_count, 1)) * 100
                self._state.progress_pct = pct

                # Change detection
                if self._is_unchanged(fp):
                    self._state.skipped_count += 1
                    self._db._touch_last_scanned(fp)
                    self._emit_progress(i)
                    continue

                # Is this a new file or an update?
                sig = self._db.get_file_signature(fp)
                is_new = sig is None

                # Extract metadata + build record
                try:
                    record = self._build_record(fp)
                    if record is not None:
                        stat = os.stat(fp)
                        record["updated_at"] = stat.st_mtime
                        record["last_scanned"] = time.time()
                        record["scan_status"] = "ok" if is_new else "updated"
                        now = time.time()
                        if is_new:
                            record["created_at"] = now

                        # Compute track_uid for new/updated records
                        tuid = self._db._compute_track_uid(
                            fp, record.get("artist"), record.get("album"),
                            record.get("title"), record.get("duration", 0),
                            record.get("mb_track_id"))
                        record["track_uid"] = tuid

                        batch_writer.add(record)
                        if is_new:
                            self._state.added_count += 1
                        else:
                            self._state.updated_count += 1
                    else:
                        self._state.skipped_count += 1
                except Exception as e:
                    self._state.error_count += 1
                    self._db.log_index_error(fp, str(e), "extract")

                # Flush every 100 records inline
                if batch_writer.buffered >= 100:
                    self._state.set_phase(ScanPhase.WRITING)
                    batch_writer.flush()

                self._emit_progress(i)

            # Phase 5: Flush remaining
            self._state.set_phase(ScanPhase.WRITING)
            batch_writer.flush()

            # Phase 6: Cleanup missing files
            self._state.set_phase(ScanPhase.CLEANING)
            missing = self._db.remove_missing()
            self._state.missing_count = missing

            # Phase 7: Rebuild UI indexes
            self._state.set_phase(ScanPhase.REBUILDING)
            self._rebuild_indexes()

            # Phase 8: Schedule enrichment
            self._state.set_phase(ScanPhase.ENRICHING)
            self._schedule_enrichment()

            self._db.update_scan_root(self._root_path,
                last_scan_finished=time.time(),
                file_count=self._state.file_count,
                added_count=self._state.added_count,
                updated_count=self._state.updated_count,
                skipped_count=self._state.skipped_count,
                missing_count=self._state.missing_count)

        except Exception as e:
            logger.error(f"Indexer failed: {e}")
            self._state.error_count += 1

        self._finish()

    # ── Pipeline phases ──

    def _walk_files(self):
        """FileWalker — recursive directory walk, yield audio files."""
        for root, dirs, fnames in os.walk(self._root_path):
            if self._cancelled:
                return
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in sorted(fnames):
                if self._cancelled:
                    return
                if os.path.splitext(fn)[1].lower() in ALL_EXTS:
                    yield os.path.join(root, fn)

    def _is_unchanged(self, filepath: str) -> bool:
        """ChangeDetector — skip files that haven't changed since last scan.
        Delegates to library/change_detector.py for the logic."""
        try:
            stat = os.stat(filepath)
        except OSError:
            self._state.error_count += 1
            self._db.log_index_error(filepath, "stat failed", "detect")
            return True
        from library.change_detector import is_file_unchanged
        return is_file_unchanged(self._db, filepath, stat)

    @staticmethod
    def _compute_quick_hash(filepath: str) -> str:
        from library.change_detector import compute_quick_hash
        return compute_quick_hash(filepath)

    def _build_record(self, filepath: str) -> dict | None:
        """MetadataExtractor + AlbumKeyBuilder — extract and normalize metadata."""
        if not os.path.exists(filepath):
            return None

        ext = os.path.splitext(filepath)[1].lower()
        kind = media_kind(ext)
        if kind == "unknown":
            return None

        stat = os.stat(filepath)
        meta = extract_metadata_combined(filepath)

        fname = os.path.basename(filepath)
        dname = os.path.dirname(filepath)
        title = normalize_text(meta.get("title") or "", 256)
        artist = normalize_artist_name(meta.get("artist", ""))
        album = normalize_text(meta.get("album", ""), 256)
        genre = normalize_genre(meta.get("genre", ""))
        year = normalize_year(meta.get("year"))
        albumartist = normalize_artist_name(meta.get("albumartist", ""))
        composer = normalize_text(meta.get("composer", ""), 256)

        disc_number, disc_total = normalize_disc_track(
            f"{meta.get('disc_number', 0)}/{meta.get('disc_total', 0)}")
        track_number = meta.get("track_number", 0)
        track_total = meta.get("track_total", 0)

        mb_track_id = normalize_mb_id(meta.get("mb_track_id", ""))
        mb_album_id = normalize_mb_id(meta.get("mb_album_id", ""))
        mb_albumartist_id = normalize_mb_id(meta.get("mb_albumartist_id", ""))
        bit_depth = meta.get("bit_depth", 0) or 0
        bpm = normalize_bpm(meta.get("bpm"))
        replaygain_track = meta.get("replaygain_track", 0.0)
        replaygain_album = meta.get("replaygain_album", 0.0)
        replaygain_track_peak = meta.get("replaygain_track_peak", 0.0)
        isrc = normalize_text(meta.get("isrc", ""), 128)
        label = normalize_text(meta.get("label", ""), 256)
        conductor = normalize_text(meta.get("conductor", ""), 256)
        compilation = meta.get("compilation", 0)
        media_type = normalize_text(meta.get("media_type", ""), 128)
        encoder = normalize_text(meta.get("encoder", ""), 256)
        copyright = normalize_text(meta.get("copyright", ""), 512)
        originaldate = normalize_text(meta.get("originaldate", ""), 32)
        remixer = normalize_text(meta.get("remixer", ""), 256)
        grouping = normalize_text(meta.get("grouping", ""), 256)
        mood = normalize_text(meta.get("mood", ""), 128)

        # AlbumKeyBuilder — cache embedded cover art with stable key
        cover_data = meta.get("cover_data", b"")
        if cover_data and album:
            try:
                ak = make_album_key(albumartist or artist, artist, album)
                cover_mime = meta.get("cover_mime", "image/jpeg")
                self._db._conn.execute(
                    "INSERT OR REPLACE INTO album_art_cache "
                    "(album_hash, mime, data) VALUES (?,?,?)",
                    (ak, cover_mime, cover_data))
                self._db._conn.commit()
            except Exception:
                pass

        return {
            "filepath": filepath,
            "filename": fname,
            "directory": dname,
            "ext": ext,
            "kind": kind,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "duration": meta.get("duration", 0.0),
            "channels": meta.get("channels", 0),
            "sample_rate": meta.get("sample_rate", 0),
            "bitrate": meta.get("bitrate", 0),
            "title": title,
            "artist": artist,
            "album": album,
            "albumartist": albumartist,
            "year": year,
            "genre": genre,
            "track_number": track_number,
            "track_total": track_total,
            "disc_number": disc_number,
            "disc_total": disc_total,
            "composer": composer,
            "mb_track_id": mb_track_id,
            "mb_album_id": mb_album_id,
            "mb_albumartist_id": mb_albumartist_id,
            "bit_depth": bit_depth,
            "bpm": bpm,
            "replaygain_track": replaygain_track,
            "replaygain_album": replaygain_album,
            "replaygain_track_peak": replaygain_track_peak,
            "isrc": isrc, "label": label, "conductor": conductor,
            "compilation": compilation, "media_type": media_type,
            "encoder": encoder, "copyright": copyright,
            "originaldate": originaldate, "remixer": remixer,
            "grouping": grouping, "mood": mood,
            "content_hash": self._compute_quick_hash(filepath),
        }

    def _rebuild_indexes(self):
        """Rebuild SQLite indexes and FTS5 index for fast queries."""
        try:
            self._db._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_artist ON media_items(artist)")
            self._db._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_album ON media_items(album)")
            self._db._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_albumartist ON media_items(albumartist)")
            self._db._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_genre ON media_items(genre)")
            self._db._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_year ON media_items(year)")
            self._db._conn.commit()
            # Rebuild FTS5 to sync new/changed rows
            from library.search_index import SearchIndex
            idx = SearchIndex(self._db._conn)
            if idx.fts_exists:
                idx.rebuild_fts()
        except Exception as e:
            logger.warning(f"Index rebuild failed: {e}")

    def _schedule_enrichment(self):
        """Request MusicBrainz enrichment for newly indexed artists."""
        try:
            rows = self._db._conn.execute(
                "SELECT DISTINCT albumartist, artist FROM media_items "
                "WHERE albumartist != '' OR artist != ''").fetchall()
            seen = set()
            for row in rows:
                name = normalize_artist_name(row[0] or row[1] or "")
                if name and name not in seen and name.lower() not in seen:
                    seen.add(name)
                    artist_key = make_artist_key(name)
                    self.enrichment_requested.emit(artist_key, name)
        except Exception as e:
            logger.warning(f"Enrichment scheduling failed: {e}")

    def _emit_progress(self, idx: int):
        total = max(self._state.file_count, 1)
        self.progress.emit(idx + 1, total, self._state.current_file)
        self.detail.emit(self._state.to_dict())

    def _finish(self):
        state = self._state
        if not state.cancelled:
            state.finish(ScanPhase.DONE)
        self.finished.emit(state.added_count + state.updated_count)
