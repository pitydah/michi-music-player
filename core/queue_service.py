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
        self._current_index = -1
        self._shuffle_order: list[int] | None = None
        self._repeat: str = "none"
        self._context: str = ""

    # ── Properties ──

    @property
    def items(self) -> list[dict]:
        return list(self._items)

    @property
    def count(self) -> int:
        return len(self._items)

    @property
    def current_index(self) -> int:
        return self._current_index

    @current_index.setter
    def current_index(self, value: int):
        self._current_index = value

    @property
    def shuffle_order(self) -> list[int] | None:
        return self._shuffle_order

    @shuffle_order.setter
    def shuffle_order(self, value: list[int] | None):
        self._shuffle_order = value

    @property
    def repeat(self) -> str:
        return self._repeat

    @repeat.setter
    def repeat(self, value: str):
        self._repeat = value

    @property
    def context(self) -> str:
        return self._context

    @context.setter
    def context(self, value: str):
        self._context = value

    # ── Core API ──

    def get_items(self) -> list[dict]:
        return list(self._items)

    def set_items(self, items: list[dict], current_index: int | None = None):
        self._save_undo()
        self._items = list(items)
        if current_index is not None:
            self._current_index = current_index
        elif self._items and self._current_index < 0:
            self._current_index = 0
        elif not self._items:
            self._current_index = -1
        self._sync()

    def add(self, item: dict):
        self._save_undo()
        self._items.append(item)
        if self._current_index < 0:
            self._current_index = 0
        self._sync()

    def insert(self, index: int, items: list[dict]):
        self._save_undo()
        for i, item in enumerate(items):
            self._items.insert(index + i, item)
        if self._current_index < 0 and self._items:
            self._current_index = 0
        self._sync()

    def append(self, items: list[dict]):
        self._save_undo()
        self._items.extend(items)
        if self._current_index < 0 and self._items:
            self._current_index = 0
        self._sync()

    def replace(self, items: list[dict]):
        self._save_undo()
        self._items = list(items)
        if self._current_index < 0 and self._items:
            self._current_index = 0
        self._sync()

    def move(self, from_index: int, to_index: int):
        self._save_undo()
        if 0 <= from_index < len(self._items) and 0 <= to_index < len(self._items):
            item = self._items.pop(from_index)
            self._items.insert(to_index, item)
            if self._current_index == from_index:
                self._current_index = to_index
            self._sync()

    def reorder(self, from_index: int, to_index: int):
        self.move(from_index, to_index)

    def remove(self, indices: list[int]):
        self._save_undo()
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self._items):
                removed = self._items.pop(idx)
                if self._current_index == idx:
                    self._current_index = min(idx, len(self._items) - 1) if self._items else -1
                elif self._current_index > idx:
                    self._current_index -= 1
        self._sync()

    def clear(self):
        self._save_undo()
        self._items = []
        self._current_index = -1
        self._sync()

    def get_current(self) -> dict | None:
        if 0 <= self._current_index < len(self._items):
            return dict(self._items[self._current_index])
        return None

    def undo(self) -> bool:
        if self._undo_stack:
            self._items = self._undo_stack.pop()
            self._can_undo = len(self._undo_stack) > 0
            if self._current_index >= len(self._items):
                self._current_index = len(self._items) - 1 if self._items else -1
            self._sync()
            return True
        return False

    def _save_undo(self):
        self._undo_stack.append(list(self._items))
        self._can_undo = True

    def _sync(self):
        if self._player and hasattr(self._player, 'set_queue'):
            with contextlib.suppress(Exception):
                self._player.set_queue(self._items)

    # ── Persistence ──

    def save_state(self, position: float = 0.0) -> dict:
        try:
            state = {
                "version": 2,
                "timestamp": time.time(),
                "current_index": self._current_index if self._current_index >= 0 else 0,
                "position": position,
                "source": "queue_service",
                "shuffle_order": self._shuffle_order,
                "repeat": self._repeat,
                "context": self._context,
                "items": self._items,
            }
            path = _queue_state_path()
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(state, f)
            os.replace(tmp, path)
            return {"ok": True, "path": path, "count": len(self._items)}
        except Exception as e:
            logger.exception("save_state failed")
            return {"ok": False, "error": str(e)}

    def load_state(self, resolve_fn=None) -> dict:
        path = _queue_state_path()
        if not os.path.exists(path):
            return {"ok": False, "error": "NO_SAVED_STATE"}
        try:
            with open(path) as f:
                state = json.load(f)
            items = state.get("items", [])
            if not items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            self._current_index = state.get("current_index", 0)
            self._shuffle_order = state.get("shuffle_order")
            self._repeat = state.get("repeat", "none")
            self._context = state.get("context", "")
            if resolve_fn:
                resolved = []
                missing_ids = []
                for item in items:
                    result = resolve_fn(item)
                    if result is not None:
                        resolved.append(result)
                    else:
                        missing_ids.append(item.get("track_id", item.get("id", "")))
                self._items = resolved
                result = {
                    "ok": True,
                    "count": len(resolved),
                    "missing_count": len(missing_ids),
                    "partial": len(missing_ids) > 0,
                    "missing_track_ids": missing_ids,
                }
            else:
                self._items = list(items)
                result = {"ok": True, "count": len(items)}
            self._sync()
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def persist(self) -> dict:
        return self.save_state()

    def restore(self) -> dict:
        return self.load_state()

    def missing_tracks(self) -> list[dict]:
        return [item for item in self._items if not item.get("filepath")]

    def shutdown(self, position: float = 0.0):
        self.save_state(position=position)
        self._undo_stack.clear()
