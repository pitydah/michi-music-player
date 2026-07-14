"""QueueService — canonical single source of truth for queue state."""

from __future__ import annotations

import contextlib
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
        self._items: list[dict] = []
        self._undo_stack: list[dict] = []
        self._can_undo = False

    def get_items(self) -> list[dict]:
        return list(self._items)

    def set_items(self, items: list[dict]):
        self._save_undo()
        self._items = list(items)
        if self._player and hasattr(self._player, 'set_queue'):
            with contextlib.suppress(Exception):
                self._player.set_queue(items)

    def insert(self, index: int, items: list[dict]):
        self._save_undo()
        for i, item in enumerate(items):
            self._items.insert(index + i, item)
        self._sync()

    def append(self, items: list[dict]):
        self._save_undo()
        self._items.extend(items)
        self._sync()

    def replace(self, items: list[dict]):
        self._save_undo()
        self._items = list(items)
        self._sync()

    def reorder(self, from_index: int, to_index: int):
        self._save_undo()
        if 0 <= from_index < len(self._items) and 0 <= to_index < len(self._items):
            item = self._items.pop(from_index)
            self._items.insert(to_index, item)
            self._sync()

    def remove(self, indices: list[int]):
        self._save_undo()
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self._items):
                self._items.pop(idx)
        self._sync()

    def clear(self):
        self._save_undo()
        self._items = []
        self._sync()

    def undo(self):
        if self._undo_stack:
            self._items = self._undo_stack.pop()
            self._can_undo = len(self._undo_stack) > 0
            self._sync()

    def _save_undo(self):
        self._undo_stack.append(list(self._items))
        self._can_undo = True

    def _sync(self):
        if self._player and hasattr(self._player, 'set_queue'):
            with contextlib.suppress(Exception):
                self._player.set_queue(self._items)

    def save_state(self) -> dict:
        try:
            state = {
                "version": 1,
                "timestamp": time.time(),
                "current_index": 0,
                "position": 0,
                "source": "queue_service",
                "items": self._items,
            }
            path = _queue_state_path()
            with open(path, "w") as f:
                json.dump(state, f)
            return {"ok": True, "path": path, "count": len(self._items)}
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
            self._items = list(items)
            self._sync()
            return {"ok": True, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def persist(self) -> dict:
        return self.save_state()

    def restore(self) -> dict:
        return self.load_state()

    def missing_tracks(self) -> list[dict]:
        return [item for item in self._items if not item.get("filepath")]

    def shutdown(self):
        self.save_state()
        self._undo_stack.clear()
