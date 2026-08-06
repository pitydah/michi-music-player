"""Playback snapshot section — canonical playback readback (S9 authority).

Consumes ``PlaybackSnapshotService`` (registered by the container); when it is
absent it falls back to the raw player only to report presence, never to
fabricate playback values (ADR-005: no invented volume/state/position).
"""

from __future__ import annotations

from typing import Any

_PLAYBACK_SERVICE_KEY = "playback_snapshot_service"


class PlaybackSectionProvider:
    section_key = "playback"

    def build(self, context) -> dict[str, Any]:
        snapshot_service = context.services.get(_PLAYBACK_SERVICE_KEY)
        if snapshot_service is not None and hasattr(snapshot_service, "snapshot"):
            try:
                snap = snapshot_service.snapshot()
                return _from_canonical(snap)
            except Exception as exc:
                return {
                    "available": False,
                    "reason": "playback_readback_failed",
                    "error": str(exc)[:200],
                }

        playback = context.services.get("playback_service")
        if playback is None:
            return {
                "available": False,
                "reason": "playback_service_missing",
                "state": "unavailable",
            }
        return {
            "available": False,
            "reason": "snapshot_service_missing",
            "state": "unavailable",
            "raw_player_present": True,
        }


def _from_canonical(snap: dict[str, Any]) -> dict[str, Any]:
    available = bool(snap.get("available"))
    track = snap.get("track")
    queue = snap.get("queue") or {}
    return {
        "available": available,
        "status": snap.get("status", "SERVICE_UNAVAILABLE"),
        "reason": "" if available else "playback_readback_failed",
        "state": snap.get("state", "unavailable"),
        "position": snap.get("position"),
        "duration": snap.get("duration"),
        "volume": snap.get("volume"),
        "now_playing": track or None,
        "queue": {
            "active": bool(queue.get("active", False)),
            "count": int(queue.get("count", 0)),
            "index": int(queue.get("index", -1)),
        },
        "source": snap.get("source"),
    }
