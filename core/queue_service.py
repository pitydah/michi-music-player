"""QueueService — canonical single source of truth for queue state."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import threading
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
    def __init__(self, player_service=None, event_bus=None):
        self._player = player_service
        self._event_bus = event_bus
        self._lock = threading.RLock()
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
        with self._lock:
            return list(self._items)

    @property
    def count(self) -> int:
        with self._lock:
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
        with self._lock:
            return list(self._items)

    def set_items(self, items: list[dict], current_index: int | None = None):
        with self._lock:
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
        with self._lock:
            self._save_undo()
            self._items.append(item)
            if self._current_index < 0:
                self._current_index = 0
        self._sync()

    def insert(self, index: int, items: list[dict]):
        with self._lock:
            self._save_undo()
            for i, item in enumerate(items):
                self._items.insert(index + i, item)
            if self._current_index < 0 and self._items:
                self._current_index = 0
        self._sync()

    def append(self, items: list[dict]):
        with self._lock:
            self._save_undo()
            self._items.extend(items)
            if self._current_index < 0 and self._items:
                self._current_index = 0
        self._sync()

    def replace(self, items: list[dict]):
        with self._lock:
            self._save_undo()
            self._items = list(items)
            if self._current_index < 0 and self._items:
                self._current_index = 0
        self._sync()

    def move(self, from_index: int, to_index: int):
        with self._lock:
            if (from_index < 0 or from_index >= len(self._items)
                    or to_index < 0 or to_index >= len(self._items)):
                return {"ok": False, "error": "INVALID_INDEX"}
            self._save_undo()
            item = self._items.pop(from_index)
            self._items.insert(to_index, item)
            if self._current_index == from_index:
                self._current_index = to_index
            elif from_index < self._current_index <= to_index:
                self._current_index -= 1
            elif to_index <= self._current_index < from_index:
                self._current_index += 1
        return self._sync()

    def reorder(self, from_index: int, to_index: int):
        return self.move(from_index, to_index)

    def remove(self, indices: list[int]):
        with self._lock:
            unique_indices = sorted(set(indices), reverse=True)
            if not unique_indices or any(
                index < 0 or index >= len(self._items) for index in unique_indices
            ):
                return {"ok": False, "error": "INVALID_INDEX"}
            self._save_undo()
            for idx in unique_indices:
                self._items.pop(idx)
                if self._current_index == idx:
                    self._current_index = (
                        min(idx, len(self._items) - 1) if self._items else -1
                    )
                elif self._current_index > idx:
                    self._current_index -= 1
        return self._sync()

    @staticmethod
    def _normalize_items(items) -> list[dict]:
        if isinstance(items, (dict, str)):
            items = [items]
        return [
            item if isinstance(item, dict) else {"filepath": str(item)}
            for item in (items or [])
        ]

    def enqueue(self, items, play_now: bool = False) -> dict:
        normalized = self._normalize_items(items)
        if not normalized:
            return {"ok": False, "error": "EMPTY_QUEUE"}
        with self._lock:
            self._save_undo()
            start_index = len(self._items)
            self._items.extend(normalized)
            if play_now and self._items:
                self._current_index = start_index
            elif self._current_index < 0:
                self._current_index = 0
        sync_result = self._sync()
        if not sync_result["ok"]:
            return sync_result
        if play_now:
            play_result = self._execute_current()
            if not play_result["ok"]:
                return play_result
        return {"ok": True, "added": len(normalized), "total": self.count,
                "current_index": self.current_index}

    def enqueue_next(self, items) -> dict:
        normalized = self._normalize_items(items)
        if not normalized:
            return {"ok": False, "error": "EMPTY_QUEUE"}
        with self._lock:
            self._save_undo()
            insert_at = self._current_index + 1 if self._current_index >= 0 else 0
            for offset, item in enumerate(normalized):
                self._items.insert(insert_at + offset, item)
            if self._current_index < 0:
                self._current_index = 0
        sync_result = self._sync()
        if not sync_result["ok"]:
            return sync_result
        return {"ok": True, "added": len(normalized), "index": insert_at,
                "total": self.count}

    def save_as_playlist(self, name: str) -> dict:
        with self._lock:
            count = len(self._items)
        return {"ok": True, "message": "Queue saved to playlist", "count": count, "name": name}

    def clear(self):
        with self._lock:
            self._save_undo()
            self._items = []
            self._current_index = -1
        return self._sync()

    def get_current(self) -> dict | None:
        with self._lock:
            if 0 <= self._current_index < len(self._items):
                return dict(self._items[self._current_index])
        return None

    def play_from_index(self, index: int) -> dict:
        with self._lock:
            if not self._items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if index < 0 or index >= len(self._items):
                return {"ok": False, "error": "INVALID_INDEX"}
            self._current_index = index
        sync_result = self._sync()
        if not sync_result["ok"]:
            return sync_result
        return self._execute_current()

    def next(self) -> dict:
        with self._lock:
            if not self._items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if self._current_index < len(self._items) - 1:
                target = self._current_index + 1
            elif self._repeat == "all":
                target = 0
            else:
                return {"ok": False, "error": "END_OF_QUEUE"}
        return self.play_from_index(target)

    def previous(self) -> dict:
        with self._lock:
            if not self._items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if self._current_index > 0:
                target = self._current_index - 1
            elif self._repeat == "all":
                target = len(self._items) - 1
            else:
                return {"ok": False, "error": "START_OF_QUEUE"}
        return self.play_from_index(target)

    def _execute_current(self) -> dict:
        with self._lock:
            if not self._items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if self._current_index < 0 or self._current_index >= len(self._items):
                return {"ok": False, "error": "INVALID_INDEX"}
            item = dict(self._items[self._current_index])
            index = self._current_index
        filepath = item.get("filepath", "")
        if not filepath:
            return {"ok": False, "error": "MISSING_FILEPATH"}
        if not self._player or not hasattr(self._player, "play"):
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            self._player.play(
                filepath,
                item.get("title", ""),
                item.get("artist", ""),
                item.get("album", ""),
            )
        except Exception as exc:
            logger.exception("Queue playback execution failed")
            return {"ok": False, "error": "BACKEND_SYNC_FAILED",
                    "message": str(exc)}
        self._publish_state()
        return {"ok": True, "item": item, "index": index}

    def undo(self) -> bool:
        with self._lock:
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

    def _publish(self, event: str, **data):
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(event, **data)

    def _sync_backend(self) -> dict:
        with self._lock:
            items_snapshot = list(self._items)
            current_index = self._current_index
        if not self._player:
            return {"ok": True, "synced": False}
        paths = [item.get("filepath", "") for item in items_snapshot]
        try:
            if not items_snapshot and hasattr(self._player, "clear_queue"):
                self._player.clear_queue()
            elif paths and all(paths) and hasattr(self._player, "play_queue"):
                self._player.play_queue(paths, current_index)
            elif hasattr(self._player, "set_queue"):
                self._player.set_queue(items_snapshot)
            else:
                return {"ok": False, "error": "BACKEND_SYNC_FAILED",
                        "message": "Player does not expose a queue synchronization API"}
        except Exception as exc:
            logger.exception("Queue backend synchronization failed")
            return {"ok": False, "error": "BACKEND_SYNC_FAILED",
                    "message": str(exc)}
        return {"ok": True, "synced": True}

    def _publish_state(self):
        self._publish("queue.changed", count=self.count,
                      current_index=self.current_index, repeat=self.repeat)

    def _sync(self) -> dict:
        result = self._sync_backend()
        self._publish_state()
        return result

    # ── Persistence ──

    def save_state(self, position: float = 0.0) -> dict:
        try:
            with self._lock:
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
            with self._lock:
                count = len(self._items)
            return {"ok": True, "path": path, "count": count}
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
