"""Michi AI Library Tools — read-only operations on library state."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def get_library_health(db=None, **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    try:
        stats = db.get_dashboard_stats() if hasattr(db, "get_dashboard_stats") else {}
        return ToolResult(ok=True, data={"track_count": stats.get("total_songs", 0), "album_count": stats.get("total_albums", 0), "artist_count": stats.get("total_artists", 0)})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def list_missing_metadata(db=None, **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    try:
        stats = db.get_dashboard_stats() if hasattr(db, "get_dashboard_stats") else {}
        mm = stats.get("missing_metadata", 0)
        return ToolResult(ok=True, data={"missing_metadata_count": mm})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def search_library(db=None, query: str = "", **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    if not query:
        return ToolResult(ok=False, code="NO_QUERY", message="Consulta vacia.")
    try:
        results = db.search_advanced(query, limit=20) if hasattr(db, "search_advanced") else []
        safe = [{"title": getattr(r, "title", ""), "artist": getattr(r, "artist", ""), "album": getattr(r, "album", "")} for r in (results or [])]
        return ToolResult(ok=True, data={"results": safe, "count": len(safe)})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def summarize_current_selection(db=None, selection: dict | None = None, **kwargs) -> ToolResult:
    sel = selection or {}
    scope = sel.get("scope", "none")
    track = sel.get("track", "")
    artist = sel.get("artist", "")
    album = sel.get("album", "")
    return ToolResult(ok=True, data={"scope": scope, "track": track, "artist": artist, "album": album})
