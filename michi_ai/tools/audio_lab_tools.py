"""Michi AI Audio Lab Tools — audio analysis and intelligence."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def get_audio_analysis_status(db=None, **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    try:
        conn = db.conn if hasattr(db, "conn") else None
        if conn is None:
            return ToolResult(ok=True, data={"analyzed": 0, "pending": 0})
        total = conn.execute("SELECT COUNT(*) FROM media_items WHERE kind='audio' AND deleted_at IS NULL").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM media_items WHERE analysis_status IS NULL AND kind='audio' AND deleted_at IS NULL").fetchone()[0]
        return ToolResult(ok=True, data={"total": total, "pending": pending, "analyzed": total - pending})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def list_tracks_missing_features(db=None, **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    try:
        conn = db.conn if hasattr(db, "conn") else None
        if conn is None:
            return ToolResult(ok=True, data={"count": 0})
        count = conn.execute("SELECT COUNT(*) FROM media_items WHERE analysis_status IS NULL AND kind='audio' AND deleted_at IS NULL").fetchone()[0]
        return ToolResult(ok=True, data={"count": count})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))
