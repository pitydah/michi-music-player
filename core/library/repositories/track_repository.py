from __future__ import annotations

import logging
import sqlite3
from typing import Any

logger = logging.getLogger("michi.track_repo")

_TRACK_FIELDS = (
    "id", "filepath", "filename", "directory", "ext", "kind",
    "size", "mtime", "duration", "channels", "sample_rate", "bitrate",
    "title", "artist", "album", "year", "genre", "track_number",
    "composer", "albumartist", "disc_number", "disc_total", "track_total",
    "mb_track_id", "mb_album_id", "mb_albumartist_id",
    "bit_depth", "bpm", "isrc", "label", "conductor",
    "compilation", "media_type", "encoder", "copyright",
    "originaldate", "remixer", "grouping", "mood",
    "replaygain_track", "replaygain_album", "replaygain_track_peak",
    "play_count", "last_played", "rating",
    "created_at", "updated_at", "last_scanned", "track_uid",
    "deleted_at", "scan_status", "scan_error",
)

_SORT_WHITELIST = {
    "title": "LOWER(COALESCE(title, ''))",
    "artist": "LOWER(COALESCE(NULLIF(albumartist,''), artist, ''))",
    "album": "LOWER(COALESCE(album, ''))",
    "year": "COALESCE(year, 0)",
    "duration": "COALESCE(duration, 0)",
    "format": "LOWER(COALESCE(ext, ''))",
    "added": "COALESCE(created_at, 0)",
    "play_count": "COALESCE(play_count, 0)",
    "bitrate": "COALESCE(bitrate, 0)",
    "track_number": "COALESCE(track_number, 0)",
}

_TRACK_SELECT_COLS = (
    "m.id", "m.filepath", "m.filename", "m.directory", "m.ext", "m.kind",
    "m.size", "m.mtime", "m.duration", "m.channels", "m.sample_rate", "m.bitrate",
    "m.title", "m.artist", "m.album", "m.year", "m.genre", "m.track_number",
    "m.composer", "m.albumartist", "m.disc_number", "m.disc_total", "m.track_total",
    "m.mb_track_id", "m.mb_album_id", "m.mb_albumartist_id",
    "m.bit_depth", "m.bpm", "m.isrc", "m.label", "m.conductor",
    "m.compilation", "m.media_type", "m.encoder", "m.copyright",
    "m.originaldate", "m.remixer", "m.grouping", "m.mood",
    "m.replaygain_track", "m.replaygain_album", "m.replaygain_track_peak",
    "COALESCE(m.play_count, 0) as play_count",
    "m.last_played", "m.rating",
    "m.created_at", "m.updated_at", "m.last_scanned", "m.track_uid",
    "m.deleted_at", "m.scan_status", "m.scan_error",
)

_TRACK_SELECT = ", ".join(_TRACK_SELECT_COLS)


class TrackRepository:
    def __init__(self, conn_factory):
        self._conn_factory = conn_factory

    def _conn(self) -> sqlite3.Connection:
        if callable(self._conn_factory):
            return self._conn_factory()
        return self._conn_factory

    def _row_to_dict(self, row) -> dict[str, Any]:
        keys = list(_TRACK_FIELDS)
        return dict(zip(keys, row, strict=False))

    def get_by_id(self, track_id: int) -> dict[str, Any] | None:
        row = self._conn().execute(
            f"SELECT {_TRACK_SELECT} FROM media_items m WHERE m.id=? AND m.deleted_at IS NULL",
            (track_id,),
        ).fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    def get_by_ids(self, track_ids: list[int]) -> list[dict[str, Any]]:
        if not track_ids:
            return []
        placeholders = ",".join("?" for _ in track_ids)
        rows = self._conn().execute(
            f"SELECT {_TRACK_SELECT} FROM media_items m "
            f"WHERE m.id IN ({placeholders}) AND m.deleted_at IS NULL",
            track_ids,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_page(self, offset: int = 0, limit: int = 100,
                 sort: str = "title", asc: bool = True) -> list[dict[str, Any]]:
        sort_col = _SORT_WHITELIST.get(sort, _SORT_WHITELIST["title"])
        order = "ASC" if asc else "DESC"
        rows = self._conn().execute(
            f"SELECT {_TRACK_SELECT} FROM media_items m "
            f"WHERE m.deleted_at IS NULL "
            f"ORDER BY {sort_col} {order} LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count(self) -> int:
        row = self._conn().execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL",
        ).fetchone()
        return row[0] if row else 0

    def search_fts(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        fts_query = " OR ".join(f"{w}*" for w in query.split() if w)
        rows = self._conn().execute(
            f"SELECT {_TRACK_SELECT} FROM media_items m "
            "JOIN media_fts fts ON m.id = fts.rowid "
            "WHERE media_fts MATCH ? AND m.deleted_at IS NULL "
            "ORDER BY rank LIMIT ?",
            (fts_query, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def filter(self, **filters) -> list[dict[str, Any]]:
        clauses = ["m.deleted_at IS NULL"]
        params = []
        for key, value in filters.items():
            if key in ("artist", "album", "genre", "ext") and value:
                clauses.append(f"m.{key}=?")
                params.append(value)
            elif key == "folder" and value:
                clauses.append("m.directory LIKE ?")
                params.append(f"{value}%")
            elif key == "year" and value:
                clauses.append("m.year=?")
                params.append(int(value))
            elif key == "search" and value:
                p = f"%{value}%"
                clauses.append(
                    "(m.title LIKE ? OR m.artist LIKE ? OR m.album LIKE ? COLLATE NOCASE)")
                params.extend([p, p, p])
        where = " AND ".join(clauses)
        rows = self._conn().execute(
            f"SELECT {_TRACK_SELECT} FROM media_items m WHERE {where}",
            params,
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def sort(self, sort: str = "title", asc: bool = True,
             offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        return self.get_page(offset=offset, limit=limit, sort=sort, asc=asc)

    def insert(self, **kwargs) -> int:
        conn = self._conn()
        cols = [k for k in kwargs if k in _TRACK_FIELDS]
        vals = [kwargs[k] for k in cols]
        placeholders = ",".join("?" for _ in cols)
        cur = conn.execute(
            f"INSERT INTO media_items ({','.join(cols)}) "
            f"VALUES ({placeholders})",
            vals,
        )
        conn.commit()
        return cur.lastrowid

    def update(self, track_id: int, **kwargs) -> bool:
        conn = self._conn()
        cols = [k for k in kwargs if k in _TRACK_FIELDS]
        if not cols:
            return False
        vals = [kwargs[k] for k in cols]
        vals.append(track_id)
        conn.execute(
            f"UPDATE media_items SET {','.join(f'{c}=?' for c in cols)} "
            f"WHERE id=? AND deleted_at IS NULL",
            vals,
        )
        conn.commit()
        return True

    def delete(self, track_id: int) -> bool:
        conn = self._conn()
        cur = conn.execute(
            "UPDATE media_items SET deleted_at=strftime('%s','now') "
            "WHERE id=? AND deleted_at IS NULL",
            (track_id,),
        )
        conn.commit()
        return cur.rowcount > 0
