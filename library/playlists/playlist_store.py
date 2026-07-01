"""PlaylistStore — CRUD."""
from __future__ import annotations
import json, logging, sqlite3, time
from library.playlists.playlist_models import PlaylistHealthReport, PlaylistSummary, PlaylistTrackRef
logger = logging.getLogger("michi.playlist_store")
class PlaylistStore:
    def __init__(self, conn: sqlite3.Connection): self._conn = conn
    def create_playlist(self, name: str, description: str = "", is_smart: bool = False, rules_json: str = "") -> int:
        now = time.time()
        cur = self._conn.execute("INSERT INTO playlists (name, description, created_at, updated_at, is_smart, rules_json, source) VALUES (?,?,?,?,?,?,?)", (name, description, now, now, 1 if is_smart else 0, rules_json, "local"))
        self._conn.commit(); return cur.lastrowid
    def delete_playlist(self, pid: int):
        self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,))
        self._conn.execute("DELETE FROM playlists WHERE id=?", (pid,)); self._conn.commit()
    def duplicate_playlist(self, pid: int, new_name: str | None = None) -> int:
        orig = self.get_playlist(pid)
        if not orig: raise ValueError(f"Playlist {pid} not found")
        name = new_name or f"{orig['name']} (copia)"
        nid = self.create_playlist(name, orig.get("description", "") or "")
        for item in self.get_playlist_items_raw(pid):
            self._conn.execute("INSERT INTO playlist_items (playlist_id, filepath, track_id, position, source) VALUES (?,?,?,?,?)", (nid, item["filepath"], item.get("track_id"), item.get("position", 0), "duplicate"))
        self._conn.commit(); return nid
    def rename_playlist(self, pid: int, name: str):
        self._conn.execute("UPDATE playlists SET name=?, updated_at=? WHERE id=?", (name, time.time(), pid)); self._conn.commit()
    def update_playlist_metadata(self, pid: int, **kw):
        updates = []; params = []
        for k in ("description", "cover_path", "cover_type"):
            if k in kw: updates.append(f"{k}=?"); params.append(kw[k])
        if updates: updates.append("updated_at=?"); params.append(time.time()); params.append(pid); self._conn.execute(f"UPDATE playlists SET {', '.join(updates)} WHERE id=?", params); self._conn.commit()
    def touch_playlist(self, pid: int):
        self._conn.execute("UPDATE playlists SET updated_at=? WHERE id=?", (time.time(), pid)); self._conn.commit()
    def get_playlist(self, pid: int) -> dict | None:
        r = self._conn.execute("SELECT * FROM playlists WHERE id=?", (pid,)).fetchone(); return dict(r) if r else None
    def get_all_playlists(self, include_stats: bool = True) -> list[PlaylistSummary]:
        result = []
        for r in self._conn.execute("SELECT * FROM playlists ORDER BY name COLLATE NOCASE").fetchall():
            d = dict(r)
            s = PlaylistSummary(id=d["id"], name=d["name"], description=d.get("description","") or "", cover_path=d.get("cover_path","") or "", cover_type=d.get("cover_type","none") or "none", is_smart=bool(d.get("is_smart",0)), is_locked=bool(d.get("locked",0)), created_at=d.get("created_at",0.0) or 0.0, updated_at=d.get("updated_at",0.0) or 0.0, last_played=d.get("last_played",0.0) or 0.0, health_score=d.get("health_score",100) or 100, source=d.get("source","local") or "local", sync_status=d.get("sync_status","") or "", sync_version=d.get("sync_version",1) or 1)
            if include_stats:
                st = self.get_summary(d["id"]); s.track_count = st.track_count; s.total_duration = st.total_duration
            result.append(s)
        return result
    def get_playlist_items(self, pid: int) -> list[PlaylistTrackRef]:
        rows = self._conn.execute("""SELECT pi.position, pi.track_id, pi.filepath, pi.added_at, pi.source, m.title, m.artist, m.album, m.albumartist, m.year, m.genre, m.duration, m.ext, m.bitrate, m.sample_rate, m.bit_depth, m.track_uid, m.content_hash, m.bpm, m.key, m.replaygain_track, m.replaygain_album, m.filepath AS m_path FROM playlist_items pi LEFT JOIN media_items m ON pi.track_id = m.id WHERE pi.playlist_id = ? ORDER BY pi.position""", (pid,)).fetchall()
        result = []
        for r in rows:
            d = dict(r); fp = d.get("filepath") or d.get("m_path") or ""
            result.append(PlaylistTrackRef(position=d.get("position",0) or 0, track_id=d.get("track_id",0) or 0, filepath=fp, title=d.get("title") or "", artist=d.get("artist") or "", album=d.get("album") or "", albumartist=d.get("albumartist") or "", year=d.get("year",0) or 0, genre=d.get("genre") or "", duration=d.get("duration",0.0) or 0.0, ext=d.get("ext") or "", bitrate=d.get("bitrate",0) or 0, sample_rate=d.get("sample_rate",0) or 0, bit_depth=d.get("bit_depth",0) or 0, track_uid=d.get("track_uid") or "", content_hash=d.get("content_hash") or "", bpm=d.get("bpm",0.0) or 0.0, key=d.get("key") or "", replaygain_track=d.get("replaygain_track",0.0) or 0.0, replaygain_album=d.get("replaygain_album",0.0) or 0.0, added_at=d.get("added_at",0.0) or 0.0, source=d.get("source","manual") or "manual", exists=bool(fp and self._file_exists(fp))))
        return result
    def get_playlist_items_raw(self, pid: int) -> list[dict]:
        return [dict(r) for r in self._conn.execute("SELECT rowid, * FROM playlist_items WHERE playlist_id=? ORDER BY position", (pid,)).fetchall()]
    def add_track(self, pid: int, filepath: str = "", track_id: int | None = None, source: str = "manual"):
        pos = self._next_position(pid); tid = track_id
        if tid is None and filepath:
            r = self._conn.execute("SELECT id FROM media_items WHERE filepath=?", (filepath,)).fetchone()
            if r: tid = r["id"]
        self._conn.execute("INSERT INTO playlist_items (playlist_id, filepath, track_id, position, source, added_at) VALUES (?,?,?,?,?,?)", (pid, filepath, tid, pos, source, time.time()))
        self.touch_playlist(pid)
    def add_tracks(self, pid: int, tracks: list[tuple[str, int | None, str]]):
        for fp, tid, source in tracks: self.add_track(pid, filepath=fp, track_id=tid, source=source)
    def remove_track(self, pid: int, track_id: int | None = None, filepath: str | None = None):
        if track_id: self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=? AND track_id=?", (pid, track_id))
        elif filepath: self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=? AND filepath=?", (pid, filepath))
        self._renumber_positions(pid); self.touch_playlist(pid)
    def clear_playlist(self, pid: int):
        self._conn.execute("DELETE FROM playlist_items WHERE playlist_id=?", (pid,)); self.touch_playlist(pid)
    def set_playlist_order(self, pid: int, ordered_track_ids: list[int] | None = None, ordered_filepaths: list[str] | None = None):
        if ordered_track_ids:
            for pos, tid in enumerate(ordered_track_ids): self._conn.execute("UPDATE playlist_items SET position=? WHERE playlist_id=? AND track_id=?", (pos, pid, tid))
        elif ordered_filepaths:
            for pos, fp in enumerate(ordered_filepaths): self._conn.execute("UPDATE playlist_items SET position=? WHERE playlist_id=? AND filepath=?", (pos, pid, fp))
        self._conn.commit(); self.touch_playlist(pid)
    def move_item(self, pid: int, from_index: int, to_index: int):
        items = self.get_playlist_items_raw(pid)
        if from_index < 0 or from_index >= len(items) or to_index < 0 or to_index >= len(items): return
        item = items.pop(from_index); items.insert(to_index, item)
        for pos, it in enumerate(items): self._conn.execute("UPDATE playlist_items SET position=? WHERE rowid=?", (pos, it["rowid"]))
        self._conn.commit(); self.touch_playlist(pid)
    def find_empty_playlists(self) -> list[int]:
        return [r["id"] for r in self._conn.execute("SELECT p.id FROM playlists p LEFT JOIN playlist_items i ON p.id = i.playlist_id WHERE i.playlist_id IS NULL").fetchall()]
    def find_duplicate_playlist_names(self) -> list[tuple[str, int]]:
        return [(r["name"], r["cnt"]) for r in self._conn.execute("SELECT name, COUNT(*) as cnt FROM playlists GROUP BY name HAVING cnt > 1").fetchall()]
    def get_summary(self, pid: int) -> PlaylistSummary:
        row = self._conn.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(m.duration),0) AS dur FROM playlist_items pi LEFT JOIN media_items m ON pi.track_id=m.id WHERE pi.playlist_id=?", (pid,)).fetchone()
        pl = self.get_playlist(pid); return PlaylistSummary(id=pid, name=pl["name"] if pl else "", track_count=row["cnt"] if row else 0, total_duration=row["dur"] if row else 0.0)
    def get_all_summaries(self) -> list[PlaylistSummary]: return self.get_all_playlists(include_stats=True)
    def update_health(self, pid: int, report: PlaylistHealthReport):
        self._conn.execute("UPDATE playlists SET health_score=?, health_json=?, updated_at=? WHERE id=?", (report.score, json.dumps(report, default=str), time.time(), pid)); self._conn.commit()
    def _next_position(self, pid: int) -> int:
        r = self._conn.execute("SELECT COALESCE(MAX(position), -1) + 1 AS nxt FROM playlist_items WHERE playlist_id=?", (pid,)).fetchone(); return r["nxt"] if r else 0
    def _renumber_positions(self, pid: int):
        for pos, r in enumerate(self._conn.execute("SELECT rowid FROM playlist_items WHERE playlist_id=? ORDER BY position", (pid,)).fetchall()): self._conn.execute("UPDATE playlist_items SET position=? WHERE rowid=?", (pos, r["rowid"]))
        self._conn.commit()
    @staticmethod
    def _file_exists(fp: str) -> bool:
        import os; return os.path.isfile(fp)
