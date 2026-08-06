"""PlaybackSnapshotService — canonical readback authority for playback state.

Single source of truth for *reading* playback state (state, position, volume,
current track, queue) from PlayerService + QueueService (ADR-002). Never
fabricates values: when the player is absent or the readback fails, the
snapshot is explicit ``available=False`` with ``status=SERVICE_UNAVAILABLE``
instead of invented defaults (ADR-005, criterion 49).

PlayerBarService, ContextService and other consumers derive from this service;
they must never re-implement readback or fall back to fabricated defaults.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.playback_snapshot")

SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
AVAILABLE = "AVAILABLE"


class PlaybackSnapshotService:
    """Canonical, honest playback readback derived from the live player."""

    def __init__(self, player_service=None, queue_service=None):
        self._player = player_service
        self._queue = queue_service

    @property
    def available(self) -> bool:
        return self._player is not None

    def _read_snapshot(self) -> Any | None:
        """Best-effort read of the backend snapshot; None on failure."""
        if not self._player:
            return None
        getter = getattr(self._player, "get_playback_snapshot", None)
        if callable(getter):
            try:
                snap = getter()
                if snap is not None:
                    return snap
            except Exception:
                logger.debug("get_playback_snapshot failed", exc_info=True)
                return None
        return None

    @staticmethod
    def _field(snap: Any, name: str, default):
        if snap is None:
            return default
        try:
            if isinstance(snap, dict):
                value = snap.get(name, default)
            else:
                value = getattr(snap, name, default)
        except Exception:
            return default
        return default if value is None else value

    def snapshot(self) -> dict[str, Any]:
        """Canonical playback snapshot.

        Returns:
            dict with ``available`` and ``status`` always present; when the
            player is missing, ``status`` is ``SERVICE_UNAVAILABLE`` and no
            fabricated playback values are returned.
        """
        if not self.available:
            return {
                "available": False,
                "status": SERVICE_UNAVAILABLE,
                "state": "unavailable",
                "position": None,
                "volume": None,
                "track": None,
                "queue": {"active": False, "count": 0, "index": -1},
                "source": None,
            }
        snap = self._read_snapshot()
        if snap is None:
            return {
                "available": False,
                "status": SERVICE_UNAVAILABLE,
                "state": "unavailable",
                "position": None,
                "volume": None,
                "track": None,
                "queue": {"active": False, "count": 0, "index": -1},
                "source": None,
            }
        state = str(self._field(snap, "state", "stopped"))
        position = self._field(snap, "position_seconds", 0.0)
        duration = self._field(snap, "duration_seconds", 0.0)
        volume = self._field(snap, "volume", None)
        queue_length = self._field(snap, "queue_length", 0)
        queue_index = self._field(snap, "queue_index", -1)
        track = {
            "title": self._field(snap, "title", ""),
            "artist": self._field(snap, "artist", ""),
            "album": self._field(snap, "album", ""),
            "filepath": self._field(snap, "current_path", "")
            or self._field(snap, "current_uri", ""),
        }
        if not any(track.values()):
            track = None
        source = self._source_label(snap)
        return {
            "available": True,
            "status": AVAILABLE,
            "state": state,
            "position": position,
            "duration": duration,
            "volume": volume,
            "track": track,
            "queue": {
                "active": int(queue_length or 0) > 0,
                "count": int(queue_length or 0),
                "index": int(queue_index or -1),
            },
            "source": source,
        }

    def _source_label(self, snap: Any) -> str:
        backend = self._field(snap, "backend_id", "")
        if not backend:
            return None
        if backend == "mpd":
            return "mpd"
        if self._field(snap, "current_uri", ""):
            return "radio"
        if self._field(snap, "current_path", ""):
            return "local"
        return str(backend)

    def get_state(self) -> str:
        """Playback state, or ``unavailable`` when the player is missing."""
        snap = self.snapshot()
        if not snap["available"]:
            return "unavailable"
        return snap["state"]

    def get_position(self):
        """Current position in seconds, or None when the player is missing."""
        return self.snapshot()["position"]

    def get_volume(self):
        """Current volume, or None when the player is missing."""
        return self.snapshot()["volume"]

    def get_track(self) -> dict | None:
        """Current track info, or None when nothing is playing."""
        return self.snapshot()["track"]

    def get_queue_state(self) -> dict:
        """Queue readback; the queue is canonical in QueueService."""
        snap = self.snapshot()
        return dict(snap["queue"])

    def health(self) -> dict:
        """Honest health: available reflects player presence + readback."""
        snap = self.snapshot()
        return {
            "available": snap["available"],
            "status": snap["status"],
            "state": snap["state"],
            "reasons": [] if snap["available"] else ["player_missing"],
        }

    def start(self):
        pass

    def shutdown(self):
        pass
