"""Knowledge cache repository — SQLite-based local knowledge base."""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import time
from typing import Any

from integrations.knowledge_broker.schemas import (
    KbArtist, KbAlbum, KbRecording, KbWikiSummary,
    dict_to_kb_artist, dict_to_kb_album,
)

logger = logging.getLogger("michi.knowledge_broker.cache")

def _default_kb_path() -> str:
    from core.paths import knowledge_cache_dir
    return os.path.join(knowledge_cache_dir(), "michi_knowledge.db")

_KB_PATH = _default_kb_path()
_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


class KnowledgeCacheRepository:
    def __init__(self, db_path: str = _KB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._run_migrations()
        self._conn.commit()

    def _run_migrations(self):
        sql_path = os.path.join(_MIGRATIONS_DIR, "001_initial.sql")
        if not os.path.exists(sql_path):
            return
        with open(sql_path) as f:
            sql = f.read()
        self._conn.executescript(sql)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── Artists ──

    def upsert_artist(self, artist: KbArtist) -> int:
        row = self._conn.execute(
            "SELECT id FROM kb_artist WHERE mbid = ? AND mbid != ''", (artist.mbid,)
        ).fetchone()
        artist.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if row:
            self._conn.execute(
                """UPDATE kb_artist SET name=?, sort_name=?, wikidata_id=?,
                country=?, begin_date=?, end_date=?, type=?, disambiguation=?,
                tags_json=?, relations_json=?, source=?, confidence=?,
                updated_at=?
                WHERE id=?""",
                (artist.name, artist.sort_name, artist.wikidata_id,
                 artist.country, artist.begin_date, artist.end_date,
                 artist.artist_type, artist.disambiguation,
                 artist.tags_json, artist.relations_json,
                 artist.source, artist.confidence, artist.updated_at,
                 row[0]),
            )
            self._conn.commit()
            return row[0]
        cur = self._conn.execute(
            """INSERT INTO kb_artist (name, sort_name, mbid, wikidata_id,
            country, begin_date, end_date, type, disambiguation,
            tags_json, relations_json, source, confidence, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (artist.name, artist.sort_name, artist.mbid, artist.wikidata_id,
             artist.country, artist.begin_date, artist.end_date,
             artist.artist_type, artist.disambiguation,
             artist.tags_json, artist.relations_json,
             artist.source, artist.confidence, artist.updated_at),
        )
        self._conn.commit()
        return cur.lastrowid or 0

    def find_artist(self, name_or_mbid: str) -> KbArtist | None:
        row = self._conn.execute(
            "SELECT * FROM kb_artist WHERE mbid = ?", (name_or_mbid,)
        ).fetchone()
        if not row:
            row = self._conn.execute(
                "SELECT * FROM kb_artist WHERE name = ?", (name_or_mbid,)
            ).fetchone()
        if not row:
            row = self._conn.execute(
                "SELECT * FROM kb_artist WHERE name LIKE ? LIMIT 1",
                (f"%{name_or_mbid}%",),
            ).fetchone()
        if row:
            return dict_to_kb_artist(_artist_row_to_dict(row))
        return None

    def search_artists(self, query: str, limit: int = 10) -> list[KbArtist]:
        try:
            rows = self._conn.execute(
                "SELECT rowid FROM kb_artist_fts WHERE kb_artist_fts MATCH ? LIMIT ?",
                (_escape_fts(query), limit),
            ).fetchall()
            if not rows:
                rows = self._conn.execute(
                    "SELECT id FROM kb_artist WHERE name LIKE ? LIMIT ?",
                    (f"%{query}%", limit),
                ).fetchall()
            ids = [r[0] for r in rows]
            if not ids:
                return []
            placeholders = ",".join("?" * len(ids))
            rows = self._conn.execute(
                f"SELECT * FROM kb_artist WHERE id IN ({placeholders})", ids
            ).fetchall()
            return [dict_to_kb_artist(_artist_row_to_dict(r)) for r in rows]
        except Exception:
            return []

    # ── Albums ──

    def upsert_album(self, album: KbAlbum) -> int:
        row = self._conn.execute(
            "SELECT id FROM kb_album WHERE release_group_mbid = ? AND release_group_mbid != ''",
            (album.release_group_mbid,),
        ).fetchone()
        album.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if row:
            self._conn.execute(
                """UPDATE kb_album SET title=?, artist_name=?, artist_mbid=?,
                release_mbid=?, date=?, year=?, country=?, primary_type=?,
                secondary_types_json=?, tags_json=?, cover_url=?, cover_path=?,
                source=?, confidence=?, updated_at=?
                WHERE id=?""",
                (album.title, album.artist_name, album.artist_mbid,
                 album.release_mbid, album.date, album.year, album.country,
                 album.primary_type, album.secondary_types_json,
                 album.tags_json, album.cover_url, album.cover_path,
                 album.source, album.confidence, album.updated_at,
                 row[0]),
            )
            self._conn.commit()
            return row[0]
        cur = self._conn.execute(
            """INSERT INTO kb_album (title, artist_name, artist_mbid, release_group_mbid,
            release_mbid, date, year, country, primary_type, secondary_types_json,
            tags_json, cover_url, cover_path, source, confidence, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (album.title, album.artist_name, album.artist_mbid,
             album.release_group_mbid, album.release_mbid,
             album.date, album.year, album.country,
             album.primary_type, album.secondary_types_json,
             album.tags_json, album.cover_url, album.cover_path,
             album.source, album.confidence, album.updated_at),
        )
        self._conn.commit()
        return cur.lastrowid or 0

    def find_album(self, title: str, artist: str = "") -> KbAlbum | None:
        if artist:
            row = self._conn.execute(
                "SELECT * FROM kb_album WHERE title = ? AND artist_name LIKE ? LIMIT 1",
                (title, f"%{artist}%"),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM kb_album WHERE title = ? LIMIT 1", (title,),
            ).fetchone()
        if not row:
            row = self._conn.execute(
                "SELECT * FROM kb_album WHERE title LIKE ? LIMIT 1",
                (f"%{title}%",),
            ).fetchone()
        if row:
            return dict_to_kb_album(_album_row_to_dict(row))
        return None

    def find_album_by_mbid(self, release_group_mbid: str) -> KbAlbum | None:
        row = self._conn.execute(
            "SELECT * FROM kb_album WHERE release_group_mbid = ?",
            (release_group_mbid,),
        ).fetchone()
        if row:
            return dict_to_kb_album(_album_row_to_dict(row))
        return None

    # ── Recordings ──

    def upsert_recording(self, rec: KbRecording) -> int:
        row = self._conn.execute(
            "SELECT id FROM kb_recording WHERE recording_mbid = ? AND recording_mbid != ''",
            (rec.recording_mbid,),
        ).fetchone()
        rec.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if row:
            self._conn.execute(
                """UPDATE kb_recording SET title=?, artist_name=?, artist_mbid=?,
                release_group_mbid=?, release_mbid=?, length_ms=?, isrc=?,
                tags_json=?, source=?, confidence=?, updated_at=?
                WHERE id=?""",
                (rec.title, rec.artist_name, rec.artist_mbid,
                 rec.release_group_mbid, rec.release_mbid,
                 rec.length_ms, rec.isrc,
                 rec.tags_json, rec.source, rec.confidence,
                 rec.updated_at, row[0]),
            )
            self._conn.commit()
            return row[0]
        cur = self._conn.execute(
            """INSERT INTO kb_recording (title, artist_name, artist_mbid, recording_mbid,
            release_group_mbid, release_mbid, length_ms, isrc, tags_json,
            source, confidence, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec.title, rec.artist_name, rec.artist_mbid, rec.recording_mbid,
             rec.release_group_mbid, rec.release_mbid,
             rec.length_ms, rec.isrc, rec.tags_json,
             rec.source, rec.confidence, rec.updated_at),
        )
        self._conn.commit()
        return cur.lastrowid or 0

    def find_recording(self, recording_mbid: str) -> KbRecording | None:
        row = self._conn.execute(
            "SELECT * FROM kb_recording WHERE recording_mbid = ?",
            (recording_mbid,),
        ).fetchone()
        if row:
            d = _recording_row_to_dict(row)
            return KbRecording(
                id=d.get("id"), title=str(d.get("title") or ""),
                artist_name=str(d.get("artist_name") or ""),
                artist_mbid=str(d.get("artist_mbid") or ""),
                recording_mbid=str(d.get("recording_mbid") or ""),
                release_group_mbid=str(d.get("release_group_mbid") or ""),
                release_mbid=str(d.get("release_mbid") or ""),
                length_ms=int(d.get("length_ms", 0) or 0),
                isrc=str(d.get("isrc") or ""),
                tags_json=str(d.get("tags_json") or "[]"),
                source=str(d.get("source") or ""),
                confidence=float(d.get("confidence", 1.0) or 1.0),
                updated_at=str(d.get("updated_at") or ""),
            )
        return None

    # ── Wiki summaries ──

    def upsert_wiki_summary(self, summary: KbWikiSummary) -> int:
        row = self._conn.execute(
            "SELECT id FROM kb_wiki_summary WHERE entity_type=? AND entity_key=? AND language=?",
            (summary.entity_type, summary.entity_key, summary.language),
        ).fetchone()
        summary.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        if row:
            self._conn.execute(
                "UPDATE kb_wiki_summary SET title=?, summary=?, source_url=?, license=?, updated_at=? WHERE id=?",
                (summary.title, summary.summary, summary.source_url,
                 summary.license, summary.updated_at, row[0]),
            )
            self._conn.commit()
            return row[0]
        cur = self._conn.execute(
            """INSERT INTO kb_wiki_summary (entity_type, entity_key, language,
            title, summary, source_url, license, updated_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (summary.entity_type, summary.entity_key, summary.language,
             summary.title, summary.summary, summary.source_url,
             summary.license, summary.updated_at),
        )
        self._conn.commit()
        return cur.lastrowid or 0

    def find_wiki_summary(self, entity_type: str, entity_key: str,
                          language: str = "es") -> KbWikiSummary | None:
        row = self._conn.execute(
            "SELECT * FROM kb_wiki_summary WHERE entity_type=? AND entity_key=? AND language=?",
            (entity_type, entity_key, language),
        ).fetchone()
        if not row and language != "en":
            row = self._conn.execute(
                "SELECT * FROM kb_wiki_summary WHERE entity_type=? AND entity_key=? AND language='en'",
                (entity_type, entity_key),
            ).fetchone()
        if row:
            d = _wiki_row_to_dict(row)
            return KbWikiSummary(
                id=d.get("id"), entity_type=str(d.get("entity_type") or ""),
                entity_key=str(d.get("entity_key") or ""),
                language=str(d.get("language") or ""),
                title=str(d.get("title") or ""),
                summary=str(d.get("summary") or ""),
                source_url=str(d.get("source_url") or ""),
                license=str(d.get("license") or ""),
                updated_at=str(d.get("updated_at") or ""),
            )
        return None

    # ── Source log ──

    def log_source(self, source: str, operation: str,
                   query_safe: str = "", status: str = "success",
                   error: str = ""):
        try:
            self._conn.execute(
                "INSERT INTO kb_source_log (source, operation, query_safe_json, status, error) VALUES (?,?,?,?,?)",
                (source, operation, query_safe, status, error),
            )
            self._conn.commit()
        except Exception as e:
            logger.warning("Source log failed: %s", e)

    # ── Negative cache ──

    def add_negative(self, entity_type: str, query: str,
                     reason: str = "", source: str = ""):
        qhash = hashlib.sha256(f"{entity_type}:{query}".encode()).hexdigest()[:16]
        self._conn.execute(
            "INSERT INTO kb_negative_cache (entity_type, query_hash, reason, source) VALUES (?,?,?,?)",
            (entity_type, qhash, reason, source),
        )
        self._conn.commit()

    def is_negative(self, entity_type: str, query: str) -> bool:
        qhash = hashlib.sha256(f"{entity_type}:{query}".encode()).hexdigest()[:16]
        row = self._conn.execute(
            "SELECT id FROM kb_negative_cache WHERE query_hash=? AND datetime(expires_at) > datetime('now')",
            (qhash,),
        ).fetchone()
        return row is not None

    # ── FTS5 search ──

    def search_kb(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        results: list[dict] = []
        try:
            fts_query = _escape_fts(query)
            for table, data_fn in [
                ("kb_artist_fts", self._artist_from_fts),
                ("kb_album_fts", self._album_from_fts),
                ("kb_recording_fts", self._recording_from_fts),
                ("kb_wiki_summary_fts", self._wiki_from_fts),
            ]:
                rows = self._conn.execute(
                    f"SELECT rowid FROM {table} WHERE {table} MATCH ? LIMIT ?",
                    (fts_query, limit),
                ).fetchall()
                for r in rows:
                    item = data_fn(r[0])
                    if item:
                        results.append(item)
        except Exception:
            pass
        return results

    def _artist_from_fts(self, rowid: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM kb_artist WHERE id=?", (rowid,)).fetchone()
        if row:
            a = dict_to_kb_artist(_artist_row_to_dict(row))
            return {"type": "artist", "name": a.name, "mbid": a.mbid,
                    "country": a.country, "source": a.source}
        return None

    def _album_from_fts(self, rowid: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM kb_album WHERE id=?", (rowid,)).fetchone()
        if row:
            a = dict_to_kb_album(_album_row_to_dict(row))
            return {"type": "album", "title": a.title, "artist_name": a.artist_name,
                    "release_group_mbid": a.release_group_mbid, "date": a.date,
                    "source": a.source}
        return None

    def _recording_from_fts(self, rowid: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM kb_recording WHERE id=?", (rowid,)).fetchone()
        if row:
            d = _recording_row_to_dict(row)
            return {"type": "recording", "title": d.get("title"),
                    "artist_name": d.get("artist_name"),
                    "recording_mbid": d.get("recording_mbid"),
                    "source": d.get("source")}
        return None

    def _wiki_from_fts(self, rowid: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM kb_wiki_summary WHERE id=?", (rowid,)).fetchone()
        if row:
            d = _wiki_row_to_dict(row)
            return {"type": "wiki_summary", "title": d.get("title"),
                    "summary": str(d.get("summary", ""))[:300],
                    "entity_type": d.get("entity_type"),
                    "language": d.get("language"),
                    "source_url": d.get("source_url")}
        return None


def _artist_row_to_dict(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0], "name": row[1], "sort_name": row[2], "mbid": row[3],
        "wikidata_id": row[4], "country": row[5], "begin_date": row[6],
        "end_date": row[7], "type": row[8], "disambiguation": row[9],
        "tags_json": row[10], "relations_json": row[11], "source": row[12],
        "confidence": row[13], "updated_at": row[14],
    }


def _album_row_to_dict(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0], "title": row[1], "artist_name": row[2],
        "artist_mbid": row[3], "release_group_mbid": row[4],
        "release_mbid": row[5], "date": row[6], "year": row[7],
        "country": row[8], "primary_type": row[9],
        "secondary_types_json": row[10], "tags_json": row[11],
        "cover_url": row[12], "cover_path": row[13],
        "source": row[14], "confidence": row[15], "updated_at": row[16],
    }


def _wiki_row_to_dict(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0], "entity_type": row[1], "entity_key": row[2],
        "language": row[3], "title": row[4], "summary": row[5],
        "source_url": row[6], "license": row[7], "updated_at": row[8],
    }


def _recording_row_to_dict(row: tuple) -> dict[str, Any]:
    return {
        "id": row[0], "title": row[1], "artist_name": row[2],
        "artist_mbid": row[3], "recording_mbid": row[4],
        "release_group_mbid": row[5], "release_mbid": row[6],
        "length_ms": row[7], "isrc": row[8], "tags_json": row[9],
        "source": row[10], "confidence": row[11], "updated_at": row[12],
    }


def _escape_fts(query: str) -> str:
    safe = query.replace('"', '').replace("'", "").replace("*", "").strip()
    if not safe:
        return '""'
    terms = []
    for t in safe.split():
        terms.append(f'"{t}"*')
    return " OR ".join(terms) if terms else f'"{safe}"*'
