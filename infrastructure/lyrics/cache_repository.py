from __future__ import annotations

import datetime
import json
import sqlite3
from typing import Callable

from core.lyrics.models import (
    LyricsDocument, TrackIdentity, MatchConfidence, LyricsSource,
    LyricsMetadata, LyricsAttribution, LyricsLine, LyricsWord,
)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS lyrics_cache (
    cache_key TEXT PRIMARY KEY,
    track_identity_json TEXT NOT NULL,
    plain_text TEXT DEFAULT '',
    synced_text TEXT DEFAULT '',
    lines_json TEXT DEFAULT '[]',
    metadata_json TEXT DEFAULT '{}',
    source TEXT DEFAULT '',
    provider_id TEXT DEFAULT '',
    provider_item_id TEXT DEFAULT '',
    language TEXT DEFAULT '',
    instrumental INTEGER DEFAULT 0,
    match_confidence TEXT DEFAULT '',
    duration_ms INTEGER DEFAULT 0,
    offset_ms INTEGER DEFAULT 0,
    attribution_json TEXT DEFAULT '{}',
    fetched_at TEXT DEFAULT '',
    expires_at TEXT DEFAULT '',
    content_hash TEXT DEFAULT '',
    negative INTEGER DEFAULT 0,
    created_at TEXT DEFAULT '',
    last_accessed_at TEXT DEFAULT ''
)
"""

_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_lyrics_cache_expires ON lyrics_cache(expires_at)
"""


class SqliteLyricsCacheRepository:
    def __init__(self, db_path: str,
                 clock: Callable[[], str] | None = None,
                 positive_ttl_s: int = 86400,
                 negative_ttl_s: int = 3600):
        self._db_path = db_path
        self._clock = clock or (lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
        self._positive_ttl_s = positive_ttl_s
        self._negative_ttl_s = negative_ttl_s

    def initialize(self):
        conn = self._conn()
        try:
            conn.execute(_SCHEMA_SQL)
            conn.execute(_INDEX_SQL)
            conn.execute("PRAGMA user_version = 1")
            conn.commit()
        finally:
            conn.close()

    def get(self, cache_key: str) -> LyricsDocument | None:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM lyrics_cache WHERE cache_key = ? AND negative = 0 AND expires_at > ?",
                (cache_key, self._clock()),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE lyrics_cache SET last_accessed_at = ? WHERE cache_key = ?",
                (self._clock(), cache_key),
            )
            conn.commit()
            return self._row_to_doc(row)
        finally:
            conn.close()

    def put(self, cache_key: str, doc: LyricsDocument, ttl_s: int | None = None):
        ttl = ttl_s or self._positive_ttl_s
        now = self._clock()
        expires = self._future(ttl)
        conn = self._conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO lyrics_cache
                (cache_key, track_identity_json, plain_text, synced_text, lines_json,
                 metadata_json, source, provider_id, provider_item_id, language,
                 instrumental, match_confidence, duration_ms, offset_ms,
                 attribution_json, fetched_at, expires_at, content_hash, negative, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                cache_key,
                json.dumps(self._identity_to_dict(doc.identity)),
                doc.plain_text,
                doc.synced_text,
                json.dumps(self._lines_to_list(doc.lines)),
                json.dumps(self._metadata_to_dict(doc.metadata)),
                doc.source.value if doc.source else "",
                doc.provider_id,
                doc.provider_item_id,
                doc.language,
                1 if doc.instrumental else 0,
                doc.match_confidence.value if doc.match_confidence else "",
                doc.duration_ms,
                doc.offset_ms,
                json.dumps(self._attribution_to_dict(doc.attribution)),
                doc.fetched_at,
                expires,
                doc.content_hash,
                now,
            ))
            conn.commit()
        finally:
            conn.close()

    def get_negative(self, cache_key: str) -> bool:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM lyrics_cache WHERE cache_key = ? AND negative = 1 AND expires_at > ?",
                (cache_key, self._clock()),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def put_negative(self, cache_key: str, ttl_s: int | None = None):
        ttl = ttl_s or self._negative_ttl_s
        now = self._clock()
        expires = self._future(ttl)
        conn = self._conn()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO lyrics_cache
                (cache_key, track_identity_json, negative, expires_at, created_at)
                VALUES (?, '{}', 1, ?, ?)
            """, (cache_key, expires, now))
            conn.commit()
        finally:
            conn.close()

    def invalidate(self, cache_key: str):
        conn = self._conn()
        try:
            conn.execute("DELETE FROM lyrics_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
        finally:
            conn.close()

    def invalidate_all(self):
        conn = self._conn()
        try:
            conn.execute("DELETE FROM lyrics_cache")
            conn.commit()
        finally:
            conn.close()

    def close(self):
        pass

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _future(self, ttl_s: int) -> str:
        try:
            dt = datetime.datetime.fromisoformat(self._clock())
        except (ValueError, TypeError):
            dt = datetime.datetime.now(datetime.timezone.utc)
        return (dt + datetime.timedelta(seconds=ttl_s)).isoformat()

    def _row_to_doc(self, row: sqlite3.Row) -> LyricsDocument:
        cache_key = row["cache_key"]
        return LyricsDocument(
            document_id=cache_key,
            identity=TrackIdentity(**json.loads(row["track_identity_json"] or "{}")),
            plain_text=row["plain_text"] or "",
            synced_text=row["synced_text"] or "",
            lines=self._list_to_lines(json.loads(row["lines_json"] or "[]")),
            metadata=LyricsMetadata(**json.loads(row["metadata_json"] or "{}")),
            source=LyricsSource(row["source"]) if row["source"] else LyricsSource.CACHE,
            provider_id=row["provider_id"] or "",
            provider_item_id=row["provider_item_id"] or "",
            language=row["language"] or "",
            instrumental=bool(row["instrumental"]),
            match_confidence=MatchConfidence(row["match_confidence"]) if row["match_confidence"] else MatchConfidence.UNKNOWN,
            duration_ms=row["duration_ms"] or 0,
            offset_ms=row["offset_ms"] or 0,
            attribution=LyricsAttribution(**json.loads(row["attribution_json"] or "{}")),
            fetched_at=row["fetched_at"] or "",
            content_hash=row["content_hash"] or "",
        )

    @staticmethod
    def _identity_to_dict(identity: TrackIdentity) -> dict:
        return {
            "track_id": identity.track_id,
            "filepath": identity.filepath,
            "title": identity.title,
            "artist": identity.artist,
            "album": identity.album,
            "album_artist": identity.album_artist,
            "duration_ms": identity.duration_ms,
            "musicbrainz_track_id": identity.musicbrainz_track_id,
            "isrc": identity.isrc,
        }

    @staticmethod
    def _lines_to_list(lines: list[LyricsLine]) -> list[dict]:
        return [
            {
                "line_id": ln.line_id,
                "start_ms": ln.start_ms,
                "end_ms": ln.end_ms,
                "text": ln.text,
                "translation": ln.translation,
                "speaker": ln.speaker,
                "words": [{"start_ms": w.start_ms, "end_ms": w.end_ms, "text": w.text} for w in ln.words],
            }
            for ln in lines
        ]

    @staticmethod
    def _list_to_lines(data: list[dict]) -> list[LyricsLine]:
        return [
            LyricsLine(
                line_id=item.get("line_id", ""),
                start_ms=item.get("start_ms", 0.0),
                end_ms=item.get("end_ms", 0.0),
                text=item.get("text", ""),
                translation=item.get("translation", ""),
                speaker=item.get("speaker", ""),
                words=[LyricsWord(**w) for w in item.get("words", [])],
            )
            for item in data
        ]

    @staticmethod
    def _metadata_to_dict(meta: LyricsMetadata) -> dict:
        return {
            "artist": meta.artist,
            "album": meta.album,
            "title": meta.title,
            "author": meta.author,
            "editor": meta.editor,
            "version": meta.version,
            "language": meta.language,
            "offset_ms": meta.offset_ms,
        }

    @staticmethod
    def _attribution_to_dict(attr: LyricsAttribution) -> dict:
        return {
            "source_label": attr.source_label,
            "provider_url": attr.provider_url,
            "provider_id": attr.provider_id,
            "license_hint": attr.license_hint,
            "terms_reference": attr.terms_reference,
        }
