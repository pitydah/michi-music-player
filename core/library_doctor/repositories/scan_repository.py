from __future__ import annotations

import time
import hashlib
import logging

logger = logging.getLogger("michi.library_doctor.repository")


class LibraryDoctorScanRepository:
    def __init__(self, db):
        self._db = db

    def _conn(self):
        return getattr(self._db, 'conn', None) if self._db else None

    def fetch_all_tracks(self):
        conn = self._conn()
        if conn is None:
            return []
        try:
            return conn.execute(
                "SELECT id, filepath, title, artist, album, album_key, track_uid "
                "FROM media_items WHERE deleted_at IS NULL"
            ).fetchall()
        except Exception:
            return []

    def find_orphan_playlist_items(self):
        conn = self._conn()
        if conn is None:
            return []
        try:
            return conn.execute(
                "SELECT pi.rowid, pi.filepath, pi.playlist_id FROM playlist_items pi "
                "LEFT JOIN media_items m ON pi.filepath = m.filepath "
                "WHERE m.id IS NULL"
            ).fetchall()
        except Exception:
            return []

    def find_orphan_history(self):
        conn = self._conn()
        if conn is None:
            return []
        try:
            return conn.execute(
                "SELECT h.id, h.filepath FROM play_history h "
                "LEFT JOIN media_items m ON h.filepath = m.filepath "
                "WHERE m.id IS NULL AND h.filepath != ''"
            ).fetchall()
        except Exception:
            return []

    def update_title(self, track_id: int, title: str):
        conn = self._conn()
        if conn:
            conn.execute(
                "UPDATE media_items SET title=? WHERE id=? AND (title IS NULL OR title='')",
                (title, track_id),
            )

    def delete_playlist_item(self, rowid: int):
        conn = self._conn()
        if conn:
            conn.execute("DELETE FROM playlist_items WHERE rowid=?", (rowid,))

    def delete_history(self, history_id: int):
        conn = self._conn()
        if conn:
            conn.execute("DELETE FROM play_history WHERE id=?", (history_id,))

    def mark_deleted(self, track_id: int):
        conn = self._conn()
        if conn:
            conn.execute(
                "UPDATE media_items SET deleted_at=? WHERE id=?",
                (time.time(), track_id),
            )

    def update_uid(self, track_id: int, filepath: str):
        conn = self._conn()
        if conn:
            new_uid = f"fp:{hashlib.sha256(filepath.encode()).hexdigest()[:16]}"
            conn.execute(
                "UPDATE media_items SET track_uid=? WHERE id=?",
                (new_uid, track_id),
            )

    def get_track_uid(self, track_id: int) -> str:
        """Public read port: current ``track_uid`` for readback verification."""
        conn = self._conn()
        if conn is None:
            return ""
        try:
            row = conn.execute(
                "SELECT track_uid FROM media_items WHERE id=?", (track_id,),
            ).fetchone()
            return str(row[0]) if row and row[0] else ""
        except Exception:  # noqa: BLE001
            return ""

    def restore_track_uid(self, track_id: int, uid: str) -> bool:
        """Public port: restore a previous ``track_uid`` (undo compensation)."""
        conn = self._conn()
        if conn is None or not uid:
            return False
        try:
            conn.execute(
                "UPDATE media_items SET track_uid=? WHERE id=?",
                (uid, track_id),
            )
            conn.commit()
            return True
        except Exception:  # noqa: BLE001
            return False

    def begin(self):
        conn = self._conn()
        if conn:
            conn.execute("BEGIN IMMEDIATE")

    def commit(self):
        conn = self._conn()
        if conn:
            conn.commit()

    def rollback(self):
        conn = self._conn()
        if conn:
            conn.execute("ROLLBACK")
