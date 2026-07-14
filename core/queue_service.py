"""QueueService — canonical queue management for PlayerService.

This is the single source of truth for queue state.
PlayerService delegates queue operations here.
QueueBridge and NowPlayingBridge both read from PlayerService.
"""
from __future__ import annotations

import json
import logging
import os
import time


from core.paths import app_config_dir

logger = logging.getLogger("michi.queue_service")


def _queue_state_path():
    try:
        p = app_config_dir()
        if p:
            return str(p / "queue_state.json")
    except Exception:
        pass
    import tempfile
    return os.path.join(tempfile.gettempdir(), "michi_queue_state.json")


class QueueService:
    def __init__(self, player_service=None):
        self._player = player_service
        self._undo_stack: list[dict] = []
        self._can_undo = False

    def save_state(self) -> dict:
        if not self._player or not hasattr(self._player, 'get_queue'):
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            q = self._player.get_queue()
            items = []
            for i in (q or []):
                if isinstance(i, dict):
                    items.append({
                        "id": i.get("id", i.get("track_id", "")),
                        "track_uid": i.get("track_uid", ""),
                        "title": i.get("title", ""),
                        "artist": i.get("artist", ""),
                        "album": i.get("album", ""),
                        "duration": i.get("duration", 0),
                        "source": i.get("source_type", "local_file"),
                    })
            state = {
                "version": 1,
                "timestamp": time.time(),
                "current_index": 0,
                "position": 0,
                "source": "queue_service",
                "items": items,
            }
            path = _queue_state_path()
            with open(path, "w") as f:
                json.dump(state, f)
            return {"ok": True, "path": path, "count": len(items)}
        except Exception as e:
            logger.exception("save_state failed")
            return {"ok": False, "error": str(e)}

    def load_state(self) -> dict:
        path = _queue_state_path()
        if not os.path.exists(path):
            return {"ok": False, "error": "NO_SAVED_STATE"}
        try:
            with open(path) as f:
                state = json.load(f)
            items = state.get("items", [])
            if not items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if not self._player or not hasattr(self._player, 'set_queue'):
                return {"ok": False, "error": "UNSUPPORTED"}
            resolved = []
            for item in items:
                track = self._resolve_track(item)
                if track:
                    resolved.append(track)
            self._player.set_queue(resolved)
            return {"ok": True, "count": len(resolved)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _resolve_track(self, item: dict) -> dict | None:
        tid = item.get("id", item.get("track_id", ""))
        if not self._player or not hasattr(self._player, 'get_track_by_id'):
            return item
        try:
            track = self._player.get_track_by_id(tid)
            if track:
                return track
        except Exception:
            pass
        return item

    def shutdown(self):
        self.save_state()
        self._undo_stack.clear()
