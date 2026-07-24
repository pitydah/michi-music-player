"""Queue tools — add tracks to playback queue. REVERSIBLE, requires confirmation."""

from __future__ import annotations

from typing import Any

from integrations.ai_assistant.schemas import ToolResult


def _resolve_filepaths(db: Any, track_ids: list[int]) -> list[str]:
    filepaths: list[str] = []
    if not hasattr(db, "get_all") or not track_ids:
        return filepaths
    all_items = db.get_all() or []
    id_map = {item.id: item.filepath for item in all_items if getattr(item, "id", None)}
    for tid in track_ids:
        fp = id_map.get(tid)
        if fp:
            filepaths.append(fp)
    return filepaths


def add_tracks_to_queue(db: Any, track_ids: list[int],
                        queue_service: Any = None, play_now: bool = False) -> ToolResult:
    try:
        if not track_ids:
            return ToolResult(
                name="add_tracks_to_queue", success=False,
                error="No se especificaron canciones.",
            )
        filepaths = _resolve_filepaths(db, track_ids)
        if not filepaths:
            return ToolResult(
                name="add_tracks_to_queue", success=False,
                error="No se encontraron las canciones en la biblioteca.",
            )
        if queue_service is None:
            return ToolResult(
                name="add_tracks_to_queue", success=False,
                error="Queue service unavailable.",
            )
        queue_service.enqueue(filepaths, play_now=play_now)
        return ToolResult(
            name="add_tracks_to_queue", success=True,
            data={
                "queued_count": len(filepaths),
                "skipped_count": len(track_ids) - len(filepaths),
                "status": "enqueued",
            },
        )
    except Exception as e:
        return ToolResult(
            name="add_tracks_to_queue", success=False, error=str(e),
        )


def play_track(db: Any, track_id: int, queue_service: Any = None) -> ToolResult:
    try:
        filepaths = _resolve_filepaths(db, [track_id])
        if not filepaths:
            return ToolResult(
                name="play_track", success=False,
                error="No se encontro la cancion en la biblioteca.",
            )
        if queue_service is None:
            return ToolResult(
                name="play_track", success=False,
                error="Queue service unavailable.",
            )
        queue_service.enqueue(filepaths, play_now=True)
        return ToolResult(
            name="play_track", success=True,
            data={"status": "playing", "track_id": track_id},
        )
    except Exception as e:
        return ToolResult(
            name="play_track", success=False, error=str(e),
        )
