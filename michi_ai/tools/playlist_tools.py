"""Michi AI Playlist Tools — playlist operations."""

from __future__ import annotations

from michi_ai.tools.tool_result import ToolResult


def create_playlist_from_selection(db=None, name: str = "Nueva playlist", track_ids: list[int] | None = None, **kwargs) -> ToolResult:
    if db is None:
        return ToolResult(ok=False, code="NO_DB", message="Biblioteca no disponible.")
    if not track_ids:
        return ToolResult(ok=False, code="NO_TRACKS", message="No hay pistas seleccionadas.")
    try:
        pid = db.create_playlist(name) if hasattr(db, "create_playlist") else None
        if pid is None:
            return ToolResult(ok=False, code="CREATE_FAILED", message="No se pudo crear la playlist.")
        for tid in track_ids[:200]:
            if hasattr(db, "add_to_playlist"):
                db.add_to_playlist(pid, track_id=tid)
        return ToolResult(ok=True, data={"playlist_id": pid, "track_count": len(track_ids[:200])})
    except Exception as e:
        return ToolResult(ok=False, code="ERROR", message=str(e))


def queue_selection(db=None, track_ids: list[int] | None = None, playback=None, **kwargs) -> ToolResult:
    if not track_ids:
        return ToolResult(ok=False, code="NO_TRACKS", message="No hay pistas seleccionadas.")
    if playback is not None and hasattr(playback, "enqueue_many"):
        try:
            playback.enqueue_many(track_ids)
            return ToolResult(ok=True, data={"queued": len(track_ids)})
        except Exception as e:
            return ToolResult(ok=False, code="ERROR", message=str(e))
    return ToolResult(ok=False, code="NO_PLAYBACK", message="Reproductor no disponible.")
