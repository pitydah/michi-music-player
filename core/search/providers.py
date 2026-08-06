"""Search providers — one provider per domain.

Repositories (tracks, albums, artists, playlists, radio, genres, folders) own
their SQL and open fresh read-only connections per query, so they are safe to
run from any worker thread. In-memory providers (devices, connections,
actions, settings) query their backing registry/service.

A provider returns ``(items, status_code)``; status codes are the typed
contract of the search response (see core.search.models). A provider must
never swallow a failure — it reports a typed status instead.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Callable

from core.search.models import (
    DATABASE_BUSY,
    DATABASE_CORRUPT,
    DATABASE_LOCKED,
    FTS_AVAILABLE,
    FTS_FAILED,
    FTS_SCHEMA_MISMATCH,
    FTS_UNAVAILABLE,
    LIKE_FALLBACK_USED,
    SEARCH_FAILED,
    SERVICE_UNAVAILABLE,
    STATUS_OK,
    SearchDomain,
    SearchRequest,
    SearchResultItem,
)

logger = logging.getLogger("michi.search.providers")

SearchProvider = Callable[[SearchRequest, int], tuple[list[SearchResultItem], str]]

_DEFAULT_QUERY_TIMEOUT_S = 5.0


def _resolve_db_path(conn_source: Any) -> str:
    if isinstance(conn_source, str):
        return conn_source
    return str(getattr(conn_source, "db_path", "") or "")


def _open_readonly(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=_DEFAULT_QUERY_TIMEOUT_S)
    conn.execute("PRAGMA query_only = 1")
    conn.row_factory = sqlite3.Row
    return conn


def _sql_status(exc: Exception) -> str:
    """Map a sqlite error to a typed search status code."""
    if not isinstance(exc, sqlite3.DatabaseError):
        return SEARCH_FAILED
    msg = str(exc).lower()
    if "busy" in msg:
        return DATABASE_BUSY
    if "locked" in msg:
        return DATABASE_LOCKED
    if "corrupt" in msg:
        return DATABASE_CORRUPT
    return SEARCH_FAILED


def _fts_failure_status(exc: Exception) -> str:
    """Classify an FTS-phase failure without swallowing it."""
    code = _sql_status(exc)
    if code != SEARCH_FAILED:
        return code
    msg = str(exc).lower()
    if "no such table" in msg:
        return FTS_UNAVAILABLE
    if "no such column" in msg or "schema" in msg:
        return FTS_SCHEMA_MISMATCH
    return FTS_FAILED


def _fts_query(query: str) -> str:
    """Prefix-token FTS query, same shape as the canonical query authority."""
    tokens = [w for w in query.split() if w]
    return " OR ".join(f"{w}*" for w in tokens) if tokens else query


class _SqlRepositoryBase:
    """Base for SQL-backed search repositories."""

    def __init__(self, conn_source: Any) -> None:
        self._db_path = _resolve_db_path(conn_source)

    def _conn(self) -> sqlite3.Connection:
        if not self._db_path:
            raise RuntimeError("no database path")
        return _open_readonly(self._db_path)


class TrackSearchRepository(_SqlRepositoryBase):
    """FTS5 (media_fts) with LIKE fallback over media_items."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        try:
            fts_code, rows = self._try_fts(conn, query, limit)
            if rows:
                return [self._item(r) for r in rows], FTS_AVAILABLE
            if fts_code in (DATABASE_BUSY, DATABASE_LOCKED, DATABASE_CORRUPT):
                return [], fts_code
            try:
                rows = self._try_like(conn, query, limit)
            except sqlite3.DatabaseError as exc:
                return [], _sql_status(exc)
            return [self._item(r) for r in rows], LIKE_FALLBACK_USED
        finally:
            conn.close()

    def _try_fts(
        self, conn: sqlite3.Connection, query: str, limit: int
    ) -> tuple[str, list]:
        """Return ``(failure_code, rows)``; failure_code is FTS_AVAILABLE on hit."""
        try:
            rows = conn.execute(
                "SELECT m.id, m.title, m.artist, m.album, m.album_key, "
                "m.duration, m.track_uid "
                "FROM media_fts f JOIN media_items m ON m.id = f.rowid "
                "WHERE media_fts MATCH ? AND m.deleted_at IS NULL "
                "ORDER BY rank LIMIT ?",
                (_fts_query(query), limit),
            ).fetchall()
            return FTS_AVAILABLE, rows
        except sqlite3.DatabaseError as exc:
            # Typed failure — never swallowed globally.
            return _fts_failure_status(exc), []

    def _try_like(self, conn: sqlite3.Connection, query: str, limit: int) -> list:
        p = f"%{query}%"
        return conn.execute(
            "SELECT id, title, artist, album, album_key, duration, track_uid "
            "FROM media_items WHERE deleted_at IS NULL AND "
            "(title LIKE ? OR artist LIKE ? OR album LIKE ?) LIMIT ?",
            (p, p, p, limit),
        ).fetchall()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=str(r["id"]),
            result_type="track",
            public_ref=f"track_{r['id']}",
            title=r["title"] or "",
            subtitle=f"{r['artist'] or ''} · {r['album'] or ''}",
            extra={
                "score": 1.0,
                "artist": r["artist"] or "",
                "album": r["album"] or "",
                "album_key": r["album_key"] or "",
                "duration": r["duration"] or 0,
                "track_uid": r["track_uid"] or "",
            },
        )


class AlbumSearchRepository(_SqlRepositoryBase):
    """Distinct albums; FTS5 join with LIKE fallback."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        try:
            fts_code, rows = self._try_fts(conn, query, limit)
            if rows:
                return [self._item(r) for r in rows], FTS_AVAILABLE
            if fts_code in (DATABASE_BUSY, DATABASE_LOCKED, DATABASE_CORRUPT):
                return [], fts_code
            try:
                rows = self._try_like(conn, query, limit)
            except sqlite3.DatabaseError:
                return [], fts_code
            return [self._item(r) for r in rows], LIKE_FALLBACK_USED
        finally:
            conn.close()

    def _try_fts(
        self, conn: sqlite3.Connection, query: str, limit: int
    ) -> tuple[str, list]:
        try:
            return FTS_AVAILABLE, conn.execute(
                "SELECT COALESCE(NULLIF(m.album_key, ''), m.album, '') AS album_key, "
                "m.album AS album_title, "
                "COALESCE(NULLIF(m.albumartist, ''), m.artist, '') AS album_artist, "
                "MIN(m.year) AS year "
                "FROM media_fts f JOIN media_items m ON m.id = f.rowid "
                "WHERE media_fts MATCH ? AND m.deleted_at IS NULL "
                "AND COALESCE(m.album, '') != '' "
                "GROUP BY album_key ORDER BY MIN(m.year) DESC LIMIT ?",
                (_fts_query(query), limit),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            return _fts_failure_status(exc), []

    def _try_like(self, conn: sqlite3.Connection, query: str, limit: int) -> list:
        p = f"%{query}%"
        return conn.execute(
            "SELECT COALESCE(NULLIF(album_key, ''), album, '') AS album_key, "
            "album AS album_title, "
            "COALESCE(NULLIF(albumartist, ''), artist, '') AS album_artist, "
            "MIN(year) AS year "
            "FROM media_items WHERE deleted_at IS NULL AND album LIKE ? "
            "AND COALESCE(album, '') != '' "
            "GROUP BY album_key LIMIT ?",
            (p, limit),
        ).fetchall()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=r["album_key"] or "",
            result_type="album",
            public_ref=f"album_{r['album_key'] or ''}",
            title=r["album_title"] or "",
            subtitle=r["album_artist"] or "",
            extra={"score": 0.9, "year": r["year"] or 0},
        )


class ArtistSearchRepository(_SqlRepositoryBase):
    """Distinct artists; FTS5 join with LIKE fallback."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        try:
            fts_code, rows = self._try_fts(conn, query, limit)
            if rows:
                return [self._item(r) for r in rows], FTS_AVAILABLE
            if fts_code in (DATABASE_BUSY, DATABASE_LOCKED, DATABASE_CORRUPT):
                return [], fts_code
            try:
                rows = self._try_like(conn, query, limit)
            except sqlite3.DatabaseError:
                return [], fts_code
            return [self._item(r) for r in rows], LIKE_FALLBACK_USED
        finally:
            conn.close()

    def _try_fts(
        self, conn: sqlite3.Connection, query: str, limit: int
    ) -> tuple[str, list]:
        try:
            return FTS_AVAILABLE, conn.execute(
                "SELECT COALESCE(NULLIF(m.albumartist, ''), m.artist, '') AS artist_name, "
                "COUNT(*) AS track_count "
                "FROM media_fts f JOIN media_items m ON m.id = f.rowid "
                "WHERE media_fts MATCH ? AND m.deleted_at IS NULL "
                "AND COALESCE(m.artist, '') != '' "
                "GROUP BY artist_name ORDER BY COUNT(*) DESC LIMIT ?",
                (_fts_query(query), limit),
            ).fetchall()
        except sqlite3.DatabaseError as exc:
            return _fts_failure_status(exc), []

    def _try_like(self, conn: sqlite3.Connection, query: str, limit: int) -> list:
        p = f"%{query}%"
        return conn.execute(
            "SELECT COALESCE(NULLIF(albumartist, ''), artist, '') AS artist_name, "
            "COUNT(*) AS track_count "
            "FROM media_items WHERE deleted_at IS NULL AND "
            "COALESCE(NULLIF(albumartist, ''), artist, '') LIKE ? "
            "AND COALESCE(artist, '') != '' "
            "GROUP BY artist_name ORDER BY COUNT(*) DESC LIMIT ?",
            (p, limit),
        ).fetchall()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=r["artist_name"] or "",
            result_type="artist",
            public_ref=f"artist_{r['artist_name'] or ''}",
            title=r["artist_name"] or "",
            subtitle="Artista",
            extra={"score": 0.8, "track_count": r["track_count"] or 0},
        )


class PlaylistSearchRepository(_SqlRepositoryBase):
    """Playlists by name (LIKE). Tolerates both production and legacy schemas."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        p = f"%{query}%"
        try:
            try:
                rows = conn.execute(
                    "SELECT p.id, p.name, COUNT(pi.track_id) AS track_count "
                    "FROM playlists p LEFT JOIN playlist_items pi "
                    "ON pi.playlist_id = p.id "
                    "WHERE p.name LIKE ? GROUP BY p.id "
                    "ORDER BY track_count DESC LIMIT ?",
                    (p, limit),
                ).fetchall()
            except sqlite3.DatabaseError:
                rows = self._schema_fallback(conn, p, limit)
            return [self._item(r) for r in rows], STATUS_OK
        except sqlite3.DatabaseError as exc:
            return [], _sql_status(exc)
        finally:
            conn.close()

    def _schema_fallback(
        self, conn: sqlite3.Connection, like: str, limit: int
    ) -> list:
        try:
            return conn.execute(
                "SELECT id, name, COALESCE(track_count, 0) AS track_count "
                "FROM playlists WHERE name LIKE ? "
                "ORDER BY track_count DESC LIMIT ?",
                (like, limit),
            ).fetchall()
        except sqlite3.DatabaseError:
            return conn.execute(
                "SELECT id, name, 0 AS track_count "
                "FROM playlists WHERE name LIKE ? LIMIT ?",
                (like, limit),
            ).fetchall()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=str(r["id"]),
            result_type="playlist",
            public_ref=f"playlist_{r['id']}",
            title=r["name"] or "",
            subtitle=f"{r['track_count'] or 0} canciones",
            extra={"score": 0.7, "track_count": r["track_count"] or 0},
        )


class RadioSearchRepository(_SqlRepositoryBase):
    """Radio stations by name/url/country (LIKE).

    The production library database has no ``radio_stations`` table (radio
    persists in its own database); the typed failure is reported instead of
    being swallowed, matching the old silent-empty behavior only through the
    response's domain status.
    """

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        p = f"%{query}%"
        try:
            rows = conn.execute(
                "SELECT id, name, url, codec, country FROM radio_stations "
                "WHERE name LIKE ? OR url LIKE ? OR country LIKE ? LIMIT ?",
                (p, p, p, limit),
            ).fetchall()
            return [self._item(r) for r in rows], STATUS_OK
        except sqlite3.DatabaseError as exc:
            if "no such table" in str(exc).lower():
                return [], SEARCH_FAILED
            return [], _sql_status(exc)
        finally:
            conn.close()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=str(r["id"]),
            result_type="radio",
            public_ref=f"radio_{r['id']}",
            title=r["name"] or "",
            subtitle=f"{r['country'] or ''} · {r['codec'] or ''}",
            extra={"score": 0.6, "url": r["url"] or ""},
        )


class GenreSearchRepository(_SqlRepositoryBase):
    """Distinct genres by name (LIKE)."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        try:
            rows = conn.execute(
                "SELECT DISTINCT genre FROM media_items "
                "WHERE deleted_at IS NULL AND genre LIKE ? "
                "AND COALESCE(genre, '') != '' "
                "ORDER BY genre LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [self._item(r) for r in rows], STATUS_OK
        except sqlite3.DatabaseError as exc:
            return [], _sql_status(exc)
        finally:
            conn.close()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        return SearchResultItem(
            result_id=r["genre"] or "",
            result_type="genre",
            public_ref=f"genre_{r['genre'] or ''}",
            title=r["genre"] or "",
            subtitle="Género",
            extra={"score": 0.55},
        )


class FolderSearchRepository(_SqlRepositoryBase):
    """Distinct library folders by path (LIKE)."""

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        query = (request.query or "").strip()
        if not query:
            return [], STATUS_OK
        try:
            conn = self._conn()
        except RuntimeError:
            return [], SERVICE_UNAVAILABLE
        try:
            rows = conn.execute(
                "SELECT DISTINCT directory FROM media_items "
                "WHERE deleted_at IS NULL AND directory LIKE ? "
                "AND COALESCE(directory, '') != '' "
                "ORDER BY directory LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [self._item(r) for r in rows], STATUS_OK
        except sqlite3.DatabaseError as exc:
            return [], _sql_status(exc)
        finally:
            conn.close()

    @staticmethod
    def _item(r: sqlite3.Row) -> SearchResultItem:
        path = r["directory"] or ""
        name = path.rsplit("/", 1)[-1] if "/" in path else path
        return SearchResultItem(
            result_id=path,
            result_type="folder",
            public_ref=f"folder_{path}",
            title=name,
            subtitle=path,
            extra={"score": 0.5, "path": path},
        )


class DeviceSearchProvider:
    """In-memory registry search over paired devices."""

    def __init__(self, device_registry: Any) -> None:
        self._registry = device_registry

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        if self._registry is None:
            return [], SERVICE_UNAVAILABLE
        query = (request.query or "").strip().lower()
        if not query:
            return [], STATUS_OK
        try:
            devices = self._registry.list_all() or []
        except Exception as exc:
            logger.warning("Device search failed: %s", exc)
            return [], SEARCH_FAILED
        items: list[SearchResultItem] = []
        for dev in devices:
            device_id = str(getattr(dev, "device_id", "") or "")
            name = str(getattr(dev, "name", "") or "")
            host = str(getattr(dev, "host", "") or "")
            if query not in (device_id + " " + name + " " + host).lower():
                continue
            items.append(SearchResultItem(
                result_id=device_id,
                result_type="device",
                public_ref=f"device_{device_id}",
                title=name or device_id,
                subtitle=host,
                extra={"score": 0.45, "host": host,
                       "status": getattr(dev, "status", "") or ""},
            ))
            if len(items) >= limit:
                break
        return items, STATUS_OK


class ConnectionSearchProvider:
    """In-memory search over known connections (Michi Link servers)."""

    def __init__(self, connection_service: Any) -> None:
        self._service = connection_service

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        if self._service is None:
            return [], SERVICE_UNAVAILABLE
        query = (request.query or "").strip().lower()
        if not query:
            return [], STATUS_OK
        try:
            connections = self._service.get_connections() or []
        except Exception as exc:
            logger.warning("Connection search failed: %s", exc)
            return [], SEARCH_FAILED
        items: list[SearchResultItem] = []
        for conn in connections:
            if not isinstance(conn, dict):
                continue
            conn_id = str(conn.get("id") or conn.get("server_id") or "")
            name = str(conn.get("name") or "")
            host = str(conn.get("host") or conn.get("url") or "")
            if query not in (conn_id + " " + name + " " + host).lower():
                continue
            items.append(SearchResultItem(
                result_id=conn_id,
                result_type="server",
                public_ref=f"server_{conn_id}",
                title=name or conn_id,
                subtitle=host,
                extra={"score": 0.4, "host": host},
            ))
            if len(items) >= limit:
                break
        return items, STATUS_OK


class ActionSearchProvider:
    """In-memory search over the ActionRegistry."""

    def __init__(self, action_registry: Any) -> None:
        self._registry = action_registry

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        if self._registry is None:
            return [], SERVICE_UNAVAILABLE
        query = (request.query or "").strip().lower()
        if not query:
            return [], STATUS_OK
        try:
            actions = self._registry.actions
        except Exception as exc:
            logger.warning("Action search failed: %s", exc)
            return [], SEARCH_FAILED
        items: list[SearchResultItem] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_id = str(action.get("id") or "")
            title = str(action.get("title") or "")
            category = str(action.get("category") or "")
            if query not in (action_id + " " + title + " " + category).lower():
                continue
            items.append(SearchResultItem(
                result_id=action_id,
                result_type="action",
                public_ref=f"action_{action_id}",
                title=title or action_id,
                subtitle=category,
                extra={"score": 0.35, "action_id": action_id},
            ))
            if len(items) >= limit:
                break
        return items, STATUS_OK


class SettingsSearchProvider:
    """In-memory search over the settings schema (categories/entries)."""

    def __init__(self, settings_service: Any) -> None:
        self._service = settings_service

    def __call__(
        self, request: SearchRequest, limit: int
    ) -> tuple[list[SearchResultItem], str]:
        if self._service is None:
            return [], SERVICE_UNAVAILABLE
        query = (request.query or "").strip().lower()
        if not query:
            return [], STATUS_OK
        try:
            categories = self._service.categories() or []
        except Exception as exc:
            logger.warning("Settings search failed: %s", exc)
            return [], SEARCH_FAILED
        items: list[SearchResultItem] = []
        for category in categories:
            if not isinstance(category, dict):
                continue
            for section in category.get("sections") or []:
                if not isinstance(section, dict):
                    continue
                for entry in section.get("entries") or []:
                    if not isinstance(entry, dict):
                        continue
                    key = str(entry.get("key") or "")
                    label = str(entry.get("label") or "")
                    if query not in (key + " " + label).lower():
                        continue
                    items.append(SearchResultItem(
                        result_id=key,
                        result_type="setting",
                        public_ref=f"setting_{key}",
                        title=label or key,
                        subtitle=key,
                        extra={"score": 0.3, "key": key},
                    ))
                    if len(items) >= limit:
                        return items, STATUS_OK
        return items, STATUS_OK


class SearchProviderRegistry:
    """Maps SearchDomain -> provider callable(request, limit)."""

    def __init__(self) -> None:
        self._providers: dict[SearchDomain, SearchProvider] = {}

    def register(self, domain: SearchDomain, provider: SearchProvider) -> None:
        if not isinstance(domain, SearchDomain):
            raise TypeError(f"domain must be a SearchDomain, got {domain!r}")
        if provider is None:
            raise ValueError(f"provider for {domain} must not be None")
        self._providers[domain] = provider

    def provider(self, domain: SearchDomain) -> SearchProvider | None:
        return self._providers.get(domain)

    def domains(self) -> frozenset[SearchDomain]:
        return frozenset(self._providers)

    def count(self) -> int:
        return len(self._providers)

    def is_empty(self) -> bool:
        return not self._providers


def build_default_registry(
    conn_source: Any,
    device_registry: Any = None,
    connection_service: Any = None,
    action_registry: Any = None,
    settings_service: Any = None,
) -> SearchProviderRegistry:
    """Legacy-compatible registry for callers that only provide a DB source."""
    registry = SearchProviderRegistry()
    registry.register(SearchDomain.TRACK, TrackSearchRepository(conn_source))
    registry.register(SearchDomain.ALBUM, AlbumSearchRepository(conn_source))
    registry.register(SearchDomain.ARTIST, ArtistSearchRepository(conn_source))
    registry.register(SearchDomain.PLAYLIST, PlaylistSearchRepository(conn_source))
    registry.register(SearchDomain.RADIO, RadioSearchRepository(conn_source))
    registry.register(SearchDomain.GENRE, GenreSearchRepository(conn_source))
    registry.register(SearchDomain.FOLDER, FolderSearchRepository(conn_source))
    if device_registry is not None:
        registry.register(SearchDomain.DEVICE, DeviceSearchProvider(device_registry))
    if connection_service is not None:
        registry.register(
            SearchDomain.CONNECTION, ConnectionSearchProvider(connection_service)
        )
    if action_registry is not None:
        registry.register(SearchDomain.ACTION, ActionSearchProvider(action_registry))
    if settings_service is not None:
        registry.register(
            SearchDomain.SETTINGS, SettingsSearchProvider(settings_service)
        )
    return registry


__all__ = [
    "SearchProvider",
    "SearchProviderRegistry",
    "build_default_registry",
    "TrackSearchRepository",
    "AlbumSearchRepository",
    "ArtistSearchRepository",
    "PlaylistSearchRepository",
    "RadioSearchRepository",
    "GenreSearchRepository",
    "FolderSearchRepository",
    "DeviceSearchProvider",
    "ConnectionSearchProvider",
    "ActionSearchProvider",
    "SettingsSearchProvider",
]
