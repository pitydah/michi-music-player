"""PlaybackHomeBuilder — builds PlaybackHomeStatus."""

from __future__ import annotations

import logging
from typing import Any

from core.home.home_status import PlaybackHomeStatus

logger = logging.getLogger("michi.home.builders.playback")


def normalize_playback_state(state: Any) -> str:
    if state is None:
        return "stopped"
    if hasattr(state, "name"):
        state = str(state.name)
    value = str(state).lower()
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    if value in ("playing",):
        return "playing"
    if value in ("paused",):
        return "paused"
    return "stopped"


def build_playback_status_from_section(section: dict) -> PlaybackHomeStatus:
    """Map the canonical ContextService playback section (S11 authority).

    The section is produced by ``PlaybackSectionProvider`` from the canonical
    ``PlaybackSnapshotService`` (S9); this adapter never re-reads the raw
    player and never invents values when the section reports unavailable.
    """
    if not isinstance(section, dict) or not section.get("available"):
        return PlaybackHomeStatus()

    state = normalize_playback_state(section.get("state"))
    np = section.get("now_playing") or {}
    queue = section.get("queue") or {}
    has_current = bool(np) and state in ("playing", "paused")
    return PlaybackHomeStatus(
        has_current_track=has_current,
        current_title=str(np.get("title", "") or ""),
        current_artist=str(np.get("artist", "") or ""),
        current_album=str(np.get("album", "") or ""),
        current_position=float(section.get("position") or 0.0),
        current_duration=float(section.get("duration") or 0.0),
        queue_active=bool(queue.get("active", False)),
        queue_count=int(queue.get("count", 0)),
        can_continue=has_current,
        source=str(section.get("source", "") or ""),
        state=state,
    )


def build_playback_status(playback: Any = None, context_svc: Any = None) -> PlaybackHomeStatus:
    if playback is None:
        return PlaybackHomeStatus()

    try:
        raw = getattr(playback, "state", "stopped") or "stopped"
    except Exception:
        raw = "unknown"
    state = normalize_playback_state(raw)

    has_current = state in ("playing", "paused")
    title = ""
    artist = ""
    album = ""
    position = 0.0
    duration = 0.0

    if has_current:
        try:
            cur = playback.current if hasattr(playback, "current") else None
            if cur:
                title = getattr(cur, "title", "") or ""
                artist = getattr(cur, "artist", "") or ""
                album = getattr(cur, "album", "") or ""
        except Exception:
            pass
        try:
            if hasattr(playback, "duration"):
                duration = playback.duration if callable(playback.duration) is False else 0.0
        except Exception:
            pass

    queue_active = False
    queue_count = 0
    try:
        if hasattr(playback, "get_queue_state"):
            qs = playback.get_queue_state()
            if isinstance(qs, tuple) and len(qs) == 2:
                paths, idx = qs
                queue_active = len(paths) > 0
                queue_count = len(paths)
            elif isinstance(qs, dict):
                queue_active = qs.get("active", False) or qs.get("count", 0) > 0
                queue_count = qs.get("count", 0)
    except Exception:
        pass

    last_title = ""
    last_artist = ""
    if context_svc is not None and not has_current:
        try:
            snap = context_svc.get_home_snapshot()
            if snap and "playback" in snap:
                pb_snap = snap["playback"]
                np = pb_snap.get("now_playing", {}) or {}
                last_title = np.get("title", "")
                last_artist = np.get("artist", "")
        except Exception:
            pass

    can_continue = has_current or bool(last_title)

    return PlaybackHomeStatus(
        has_current_track=has_current,
        current_title=title,
        current_artist=artist,
        current_album=album,
        current_position=position,
        current_duration=duration,
        queue_active=queue_active,
        queue_count=queue_count,
        last_track_title=last_title,
        last_track_artist=last_artist,
        can_continue=can_continue,
        state=state,
    )
