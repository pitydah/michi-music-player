"""HistoryQueryService — paginated play history via SQL JOIN, no full load."""
from __future__ import annotations

import logging


logger = logging.getLogger("michi.history_query")


class HistoryQueryService:
    def __init__(self, db=None):
        self._db = db

    def fetch_history(self, offset: int = 0, limit: int = 100,
                      artist: str = "", album: str = "",
                      device: str = "", search: str = "") -> list[dict]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(artist, album, device, search)
            rows = self._db.conn.execute(
                f"SELECT h.track_id, h.played_at, h.device, "
                f"m.id, m.title, m.artist, m.album, m.album_key, m.duration, m.track_uid "
                f"FROM play_history h "
                f"LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                f"WHERE 1=1 {where} "
                f"ORDER BY h.played_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [
                {
                    "track_id": r[3] or 0, "track_uid": r[9] or "",
                    "title": r[4] or r[0] or "", "artist": r[5] or "",
                    "album": r[6] or "", "album_key": r[7] or "",
                    "duration": r[8] or 0, "played_at": r[1] or "",
                    "device": r[2] or "",
                }
                for r in rows
            ]
        except Exception:
            return []

    def remove_history_item(self, track_id: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history WHERE track_id=?", (track_id,))
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def clear_history(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history")
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def count_history(self, artist: str = "", album: str = "",
                      device: str = "", search: str = "") -> int:
        if not self._db:
            return 0
        try:
            where, params = self._build_where(artist, album, device, search)
            row = self._db.conn.execute(
                f"SELECT COUNT(*) FROM play_history h "
                f"LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                f"WHERE 1=1 {where}", params
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def apply_retention(self, days: int = 365, max_age_days: int = 0) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            import time
            cutoff = time.time() - (max_age_days or days) * 86400
            self._db.conn.execute("DELETE FROM play_history WHERE played_at < ?", (cutoff,))
            self._db.conn.commit()
            return {"ok": True, "deleted_count": self._db.conn.total_changes}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def record_play(self, track_id: str, device: str = "") -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            import time
            self._db.conn.execute(
                "INSERT INTO play_history (track_id, played_at, device) VALUES (?, ?, ?)",
                (track_id, int(time.time()), device or "local"),
            )
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_history_enabled(self, enabled: bool) -> dict:
        return {"ok": True}

    def set_history_limit(self, limit: int) -> dict:
        return {"ok": True}

    def fetch_history_with_event_ids(self, offset: int = 0, limit: int = 100,
                                      artist: str = "", album: str = "",
                                      device: str = "", search: str = "") -> list[dict]:
        if not self._db:
            return []
        try:
            where, params = self._build_where(artist, album, device, search)
            rows = self._db.conn.execute(
                f"SELECT h.id, h.track_id, h.played_at, h.device, "
                f"m.id, m.title, m.artist, m.album, m.album_key, m.duration, m.track_uid "
                f"FROM play_history h "
                f"LEFT JOIN media_items m ON h.track_id = m.filepath OR h.track_id = CAST(m.id AS TEXT) "
                f"WHERE 1=1 {where} "
                f"ORDER BY h.played_at DESC LIMIT ? OFFSET ?",
                params + [limit, offset]
            ).fetchall()
            return [
                {
                    "event_id": r[0],
                    "track_id": r[4] or 0, "track_uid": r[10] or "",
                    "title": r[5] or r[1] or "", "artist": r[6] or "",
                    "album": r[7] or "", "album_key": r[8] or "",
                    "duration": r[9] or 0, "played_at": r[2] or "",
                    "device": r[3] or "",
                }
                for r in rows
            ]
        except Exception:
            return []

    def remove_event_by_id(self, event_id: int) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.conn.execute("DELETE FROM play_history WHERE id=?", (event_id,))
            self._db.conn.commit()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def export_history(self, filepath: str, fmt: str = "json",
                       artist: str = "", album: str = "",
                       device: str = "", search: str = "") -> dict:
        if not filepath:
            return {"ok": False, "error": "EMPTY_PATH"}
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            items = self.fetch_history(0, 999999, artist, album, device, search)
            import json
            import csv
            if fmt == "csv":
                with open(filepath, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["event_id", "track_id", "title", "artist", "album",
                                "album_key", "duration", "played_at", "device"])
                    for item in items:
                        w.writerow([
                            item.get("event_id", ""),
                            item.get("track_id", ""),
                            item.get("title", ""),
                            item.get("artist", ""),
                            item.get("album", ""),
                            item.get("album_key", ""),
                            item.get("duration", 0),
                            item.get("played_at", ""),
                            item.get("device", ""),
                        ])
            else:
                with open(filepath, "w") as f:
                    json.dump(items, f, indent=2)
            return {"ok": True, "count": len(items), "format": fmt, "path": filepath}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_statistics(self) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            import time
            total = self._db.conn.execute("SELECT COUNT(*) FROM play_history").fetchone()[0] or 0
            unique_tracks = self._db.conn.execute(
                "SELECT COUNT(DISTINCT track_id) FROM play_history"
            ).fetchone()[0] or 0
            today_start = int(time.time()) - 86400
            today = self._db.conn.execute(
                "SELECT COUNT(*) FROM play_history WHERE played_at >= ?",
                (today_start,)
            ).fetchone()[0] or 0
            week_start = int(time.time()) - 7 * 86400
            this_week = self._db.conn.execute(
                "SELECT COUNT(*) FROM play_history WHERE played_at >= ?",
                (week_start,)
            ).fetchone()[0] or 0
            return {
                "ok": True,
                "total_plays": total,
                "unique_tracks": unique_tracks,
                "today": today,
                "this_week": this_week,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _build_where(self, artist: str = "", album: str = "",
                     device: str = "", search: str = "") -> tuple[str, list]:
        clauses = []
        params = []
        if artist:
            clauses.append("(m.artist = ? OR m.albumartist = ?)")
            params.extend([artist, artist])
        if album:
            clauses.append("(m.album = ? OR m.album_key = ?)")
            params.extend([album, album])
        if device:
            clauses.append("h.device = ?")
            params.append(device)
        if search:
            clauses.append("(m.title LIKE ? OR m.artist LIKE ? OR m.album LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where = "AND " + " AND ".join(clauses) if clauses else ""
        return where, params




