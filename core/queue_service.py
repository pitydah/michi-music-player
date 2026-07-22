"""QueueService — canonical single source of truth for queue state."""

from __future__ import annotations

import contextlib
import copy
import json
import logging
import os
import random
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable


from core.paths import app_config_dir

logger = logging.getLogger("michi.queue_service")


@dataclass
class _QueueSnapshot:
    items: list[dict]
    item_tokens: list[int]
    current_index: int
    repeat: str
    shuffle: bool
    shuffle_original_tokens: list[int] | None
    shuffle_seed: int | None
    context: str
    revision: int
    next_token: int


def _queue_state_path():
    try:
        p = app_config_dir()
        if p:
            return str(p / "queue_state.json")
    except Exception:
        pass
    return os.path.join(tempfile.gettempdir(), "michi_queue_state.json")


class QueueService:
    """Owns queue domain state and commits mutations transactionally."""

    def __init__(self, player_service=None, event_bus=None):
        self._player = player_service
        self._event_bus = event_bus
        self._lock = threading.RLock()
        self._items: list[dict] = []
        self._item_tokens: list[int] = []
        self._next_token = 1
        self._undo_stack: list[_QueueSnapshot] = []
        self._can_undo = False
        self._current_index = -1
        self._shuffle = False
        self._shuffle_original_tokens: list[int] | None = None
        self._shuffle_seed: int | None = None
        self._repeat: str = "none"
        self._context: str = ""
        self._revision = 0
        self._observers: list[Callable[[str, dict], None]] = []

    # ── Properties ──

    @property
    def items(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._items)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def current_index(self) -> int:
        with self._lock:
            return self._current_index

    @current_index.setter
    def current_index(self, value: int):
        with self._lock:
            if value < -1 or value >= len(self._items):
                raise ValueError("current_index out of range")
            self._current_index = value
        self._publish_state("compatibility_index")

    @property
    def shuffle_order(self) -> list[int] | None:
        with self._lock:
            if not self._shuffle:
                return None
            original = self._shuffle_original_tokens or []
            positions = {token: index for index, token in enumerate(original)}
            return [positions[token] for token in self._item_tokens if token in positions]

    @shuffle_order.setter
    def shuffle_order(self, value: list[int] | None):
        if value is None:
            self.set_shuffle(False)
            return
        raise ValueError("shuffle_order is managed by QueueService")

    @property
    def shuffle(self) -> bool:
        with self._lock:
            return self._shuffle

    @property
    def repeat(self) -> str:
        with self._lock:
            return self._repeat

    @repeat.setter
    def repeat(self, value: str):
        result = self.set_repeat(value)
        if not result["ok"]:
            raise ValueError(result["error"])

    @property
    def context(self) -> str:
        with self._lock:
            return self._context

    @context.setter
    def context(self, value: str):
        with self._lock:
            self._context = str(value or "")

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    @property
    def can_undo(self) -> bool:
        with self._lock:
            return self._can_undo

    # ── Core API ──

    def get_items(self) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._items)

    def get_state(self) -> dict:
        with self._lock:
            return {
                "items": copy.deepcopy(self._items),
                "current_index": self._current_index,
                "repeat": self._repeat,
                "shuffle": self._shuffle,
                "shuffle_order": self.shuffle_order,
                "context": self._context,
                "revision": self._revision,
                "can_undo": self._can_undo,
            }

    def subscribe(self, callback: Callable[[str, dict], None]) -> Callable[[], None]:
        """Observe committed canonical changes on the caller's thread."""
        with self._lock:
            if callback not in self._observers:
                self._observers.append(callback)

        def unsubscribe() -> None:
            with self._lock, contextlib.suppress(ValueError):
                self._observers.remove(callback)

        return unsubscribe

    def _notify_observers(self, event: str, state: dict) -> None:
        with self._lock:
            observers = list(self._observers)
        for callback in observers:
            try:
                callback(event, copy.deepcopy(state))
            except Exception:
                logger.exception("Queue observer failed for %s", event)

    def _result(self, operation: str, ok: bool = True, **data) -> dict:
        result = {
            "ok": ok,
            "operation": operation,
            "error": None,
            "message": "",
            "current_index": self.current_index,
            "count": self.count,
            "revision": self.revision,
        }
        result.update(data)
        return result

    def _error(self, operation: str, error: str, message: str = "") -> dict:
        return self._result(operation, False, error=error, message=message)

    def _capture_snapshot(self) -> _QueueSnapshot:
        with self._lock:
            return _QueueSnapshot(
                items=copy.deepcopy(self._items),
                item_tokens=list(self._item_tokens),
                current_index=self._current_index,
                repeat=self._repeat,
                shuffle=self._shuffle,
                shuffle_original_tokens=(
                    list(self._shuffle_original_tokens)
                    if self._shuffle_original_tokens is not None else None
                ),
                shuffle_seed=self._shuffle_seed,
                context=self._context,
                revision=self._revision,
                next_token=self._next_token,
            )

    def _restore_snapshot(self, snapshot: _QueueSnapshot) -> None:
        with self._lock:
            self._items = copy.deepcopy(snapshot.items)
            self._item_tokens = list(snapshot.item_tokens)
            self._current_index = snapshot.current_index
            self._repeat = snapshot.repeat
            self._shuffle = snapshot.shuffle
            self._shuffle_original_tokens = (
                list(snapshot.shuffle_original_tokens)
                if snapshot.shuffle_original_tokens is not None else None
            )
            self._shuffle_seed = snapshot.shuffle_seed
            self._context = snapshot.context
            self._revision = snapshot.revision
            self._next_token = snapshot.next_token

    def _new_tokens(self, count: int) -> list[int]:
        tokens = list(range(self._next_token, self._next_token + count))
        self._next_token += count
        return tokens

    def _commit_mutation(self, operation: str, mutate, *, execute=False) -> dict:
        """Synchronize a tentative mutation and roll it back on any failure."""
        before = self._capture_snapshot()
        try:
            details = mutate() or {}
        except (IndexError, TypeError, ValueError) as exc:
            self._restore_snapshot(before)
            return self._error(operation, "INVALID_ARGUMENT", str(exc))

        sync_result = self._sync_backend(revision=self.revision + 1)
        if not sync_result.get("ok"):
            self._restore_snapshot(before)
            self._sync_backend(revision=self.revision)
            result = self._error(
                operation,
                sync_result.get("error", "BACKEND_SYNC_FAILED"),
                sync_result.get("message", ""),
            )
            self._publish_failure(result)
            return result

        if execute:
            execution = self._execute_current()
            if not execution.get("ok"):
                self._restore_snapshot(before)
                self._sync_backend(revision=self.revision)
                result = self._error(
                    operation,
                    execution.get("error", "PLAYBACK_FAILED"),
                    execution.get("message", ""),
                )
                self._publish_failure(result)
                return result
            details.update({key: value for key, value in execution.items()
                            if key not in {"ok", "operation", "error", "message"}})

        with self._lock:
            self._undo_stack.append(before)
            self._can_undo = True
            self._revision += 1
        self._publish_state(operation)
        return self._result(operation, **details)

    def set_items(self, items: list[dict], current_index: int | None = None) -> dict:
        """Compatibility wrapper; use replace() or replace_and_play()."""
        return self.replace(items, start_index=current_index)

    def add(self, item: dict) -> dict:
        """Compatibility wrapper for enqueue()."""
        return self.enqueue(item, play_now=False)

    def insert(self, index: int, items: list[dict]) -> dict:
        """Compatibility insertion at an explicit effective-order index."""
        normalized = self._normalize_items(items)
        if not normalized:
            return self._error("insert", "EMPTY_QUEUE")
        if index < 0 or index > self.count:
            return self._error("insert", "INVALID_INDEX")

        def mutate():
            with self._lock:
                tokens = self._new_tokens(len(normalized))
                self._items[index:index] = copy.deepcopy(normalized)
                self._item_tokens[index:index] = tokens
                if self._shuffle_original_tokens is not None:
                    self._shuffle_original_tokens.extend(tokens)
                if self._current_index < 0:
                    self._current_index = 0
                elif index <= self._current_index:
                    self._current_index += len(normalized)
            return {"added": len(normalized)}

        return self._commit_mutation("insert", mutate)

    def append(self, items: list[dict]) -> dict:
        """Compatibility wrapper for enqueue()."""
        return self.enqueue(items, play_now=False)

    def _replace_items(self, items: list[dict], start_index: int) -> None:
        tokens = self._new_tokens(len(items))
        self._items = copy.deepcopy(items)
        self._item_tokens = tokens
        self._current_index = start_index if items else -1
        self._shuffle_original_tokens = list(tokens) if self._shuffle else None
        if self._shuffle and len(items) > 1:
            self._shuffle_seed = random.SystemRandom().randrange(2**63)
            self._shuffle_effective_order()

    def replace(self, items: list[dict], start_index: int | None = None) -> dict:
        normalized = self._normalize_items(items)
        target = 0 if normalized and start_index is None else (start_index or 0)
        if normalized and (target < 0 or target >= len(normalized)):
            return self._error("replace", "INVALID_INDEX")

        def mutate():
            with self._lock:
                self._replace_items(normalized, target)
            return {"replaced": len(normalized)}

        return self._commit_mutation("replace", mutate)

    def replace_and_play(self, items: list[dict], start_index: int = 0) -> dict:
        normalized = self._normalize_items(items)
        if not normalized:
            return self._error("replace_and_play", "EMPTY_QUEUE")
        if start_index < 0 or start_index >= len(normalized):
            return self._error("replace_and_play", "INVALID_INDEX")

        def mutate():
            with self._lock:
                self._replace_items(normalized, start_index)
            return {"replaced": len(normalized)}

        return self._commit_mutation("replace_and_play", mutate, execute=True)

    def move(self, from_index: int, to_index: int) -> dict:
        if (from_index < 0 or from_index >= self.count
                or to_index < 0 or to_index >= self.count):
            return self._error("reorder", "INVALID_INDEX")

        def mutate():
            with self._lock:
                item = self._items.pop(from_index)
                token = self._item_tokens.pop(from_index)
                self._items.insert(to_index, item)
                self._item_tokens.insert(to_index, token)
                if self._current_index == from_index:
                    self._current_index = to_index
                elif from_index < self._current_index <= to_index:
                    self._current_index -= 1
                elif to_index <= self._current_index < from_index:
                    self._current_index += 1
            return {"from_index": from_index, "to_index": to_index}

        return self._commit_mutation("reorder", mutate)

    def reorder(self, from_index: int, to_index: int) -> dict:
        return self.move(from_index, to_index)

    def remove(self, indices: list[int]) -> dict:
        unique_indices = sorted(set(indices), reverse=True)
        if not unique_indices or any(index < 0 or index >= self.count
                                     for index in unique_indices):
            return self._error("remove", "INVALID_INDEX")

        def mutate():
            removed_tokens = []
            with self._lock:
                for index in unique_indices:
                    self._items.pop(index)
                    removed_tokens.append(self._item_tokens.pop(index))
                    if self._current_index == index:
                        self._current_index = (
                            min(index, len(self._items) - 1) if self._items else -1
                        )
                    elif self._current_index > index:
                        self._current_index -= 1
                if self._shuffle_original_tokens is not None:
                    removed = set(removed_tokens)
                    self._shuffle_original_tokens = [
                        token for token in self._shuffle_original_tokens
                        if token not in removed
                    ]
            return {"removed": len(unique_indices)}

        return self._commit_mutation("remove", mutate)

    @staticmethod
    def _normalize_items(items) -> list[dict]:
        if isinstance(items, (dict, str)):
            items = [items]
        return [
            item if isinstance(item, dict) else {"filepath": str(item)}
            for item in (items or [])
        ]

    def enqueue(self, items: Any, play_now: bool = False) -> dict:
        normalized = self._normalize_items(items)
        if not normalized:
            return self._error("enqueue", "EMPTY_QUEUE")

        def mutate():
            with self._lock:
                start_index = len(self._items)
                tokens = self._new_tokens(len(normalized))
                self._items.extend(copy.deepcopy(normalized))
                self._item_tokens.extend(tokens)
                if self._shuffle_original_tokens is not None:
                    self._shuffle_original_tokens.extend(tokens)
                if play_now:
                    self._current_index = start_index
                elif self._current_index < 0:
                    self._current_index = 0
            return {"added": len(normalized), "total": self.count}

        return self._commit_mutation("enqueue", mutate, execute=play_now)

    def insert_next(self, items: Any) -> dict:
        normalized = self._normalize_items(items)
        if not normalized:
            return self._error("insert_next", "EMPTY_QUEUE")

        def mutate():
            with self._lock:
                insert_at = self._current_index + 1 if self._current_index >= 0 else 0
                tokens = self._new_tokens(len(normalized))
                self._items[insert_at:insert_at] = copy.deepcopy(normalized)
                self._item_tokens[insert_at:insert_at] = tokens
                if self._shuffle_original_tokens is not None:
                    current_token = (
                        self._item_tokens[self._current_index]
                        if self._current_index >= 0 else None
                    )
                    original_at = (
                        self._shuffle_original_tokens.index(current_token) + 1
                        if current_token in self._shuffle_original_tokens
                        else len(self._shuffle_original_tokens)
                    )
                    self._shuffle_original_tokens[original_at:original_at] = tokens
                if self._current_index < 0:
                    self._current_index = 0
            return {"added": len(normalized), "index": insert_at,
                    "total": self.count}

        return self._commit_mutation("insert_next", mutate)

    def enqueue_next(self, items: Any) -> dict:
        """Compatibility wrapper for insert_next()."""
        return self.insert_next(items)

    def save_as_playlist(self, name: str) -> dict:
        with self._lock:
            count = len(self._items)
        return {"ok": True, "message": "Queue saved to playlist", "count": count, "name": name}

    def clear(self) -> dict:
        def mutate():
            with self._lock:
                self._items = []
                self._item_tokens = []
                self._current_index = -1
                self._shuffle_original_tokens = [] if self._shuffle else None
            return {"cleared": True}

        return self._commit_mutation("clear", mutate)

    def get_current(self) -> dict | None:
        with self._lock:
            if 0 <= self._current_index < len(self._items):
                return dict(self._items[self._current_index])
        return None

    def play_from_index(self, index: int) -> dict:
        if not self.count:
            return self._error("play_from_index", "EMPTY_QUEUE")
        if index < 0 or index >= self.count:
            return self._error("play_from_index", "INVALID_INDEX")

        def mutate():
            with self._lock:
                self._current_index = index
            return {"index": index}

        return self._commit_mutation("play_from_index", mutate, execute=True)

    def next(self) -> dict:
        with self._lock:
            if not self._items:
                return self._error("next", "EMPTY_QUEUE")
            if self._repeat == "one":
                target = self._current_index
            elif self._current_index < len(self._items) - 1:
                target = self._current_index + 1
            elif self._repeat == "all":
                target = 0
            else:
                return self._error("next", "END_OF_QUEUE")
        return self._navigate("next", target)

    def previous(self) -> dict:
        with self._lock:
            if not self._items:
                return self._error("previous", "EMPTY_QUEUE")
            if self._repeat == "one":
                target = self._current_index
            elif self._current_index > 0:
                target = self._current_index - 1
            elif self._repeat == "all":
                target = len(self._items) - 1
            else:
                return self._error("previous", "START_OF_QUEUE")
        return self._navigate("previous", target)

    def _navigate(self, operation: str, target: int) -> dict:
        def mutate():
            with self._lock:
                self._current_index = target
            return {"index": target}

        return self._commit_mutation(operation, mutate, execute=True)

    def reconcile_backend_progress(
        self,
        index: int,
        filepath: str,
        reason: str,
        revision: int | None = None,
    ) -> dict:
        """Reconcile a physical backend transition without replaying it."""
        if reason not in {"manual", "eos", "gapless", "restore",
                          "backend_reconnect"}:
            return self._error("reconcile_backend_progress", "INVALID_REASON")
        with self._lock:
            if revision is not None and revision != self._revision:
                return self._error("reconcile_backend_progress", "STALE_EVENT")
            if index < 0 or index >= len(self._items):
                return self._error("reconcile_backend_progress", "INVALID_INDEX")
            expected_path = self._items[index].get("filepath", "")
            if not filepath or filepath != expected_path:
                return self._error("reconcile_backend_progress", "TRACK_MISMATCH")
            current_index = self._current_index
            current_path = (
                self._items[current_index].get("filepath", "")
                if 0 <= current_index < len(self._items) else ""
            )

        if reason == "eos":
            if index != current_index or filepath != current_path:
                return self._error("reconcile_backend_progress", "STALE_EVENT")
            result = self.next()
            if result.get("error") == "END_OF_QUEUE":
                stop = getattr(self._player, "stop", None)
                if callable(stop):
                    stop()
                self._publish("queue.finished", revision=self.revision)
                return self._result(
                    "reconcile_backend_progress", ended=True, reason="eos"
                )
            return result

        if index == current_index and filepath == current_path:
            return self._result(
                "reconcile_backend_progress", ignored=True, reason=reason
            )

        with self._lock:
            self._current_index = index
        self._publish_state("backend_progress")
        return self._result(
            "reconcile_backend_progress", reason=reason, reconciled=True
        )

    def set_repeat(self, mode: str) -> dict:
        if mode not in {"none", "all", "one"}:
            return self._error("set_repeat", "INVALID_REPEAT_MODE")
        if mode == self.repeat:
            return self._result("set_repeat", mode=mode, unchanged=True)

        def mutate():
            with self._lock:
                self._repeat = mode
            return {"mode": mode}

        return self._commit_mutation("set_repeat", mutate)

    def toggle_repeat(self) -> dict:
        modes = {"none": "all", "all": "one", "one": "none"}
        return self.set_repeat(modes[self.repeat])

    def _shuffle_effective_order(self) -> None:
        """Shuffle tokenized entries while pinning the active entry in place."""
        if len(self._items) < 2:
            return
        current_token = (
            self._item_tokens[self._current_index]
            if 0 <= self._current_index < len(self._item_tokens) else None
        )
        movable = [
            (item, token)
            for item, token in zip(self._items, self._item_tokens, strict=True)
            if token != current_token
        ]
        random.Random(self._shuffle_seed).shuffle(movable)
        iterator = iter(movable)
        pairs = []
        for index in range(len(self._items)):
            if index == self._current_index and current_token is not None:
                pairs.append((self._items[index], current_token))
            else:
                pairs.append(next(iterator))
        self._items = [item for item, _ in pairs]
        self._item_tokens = [token for _, token in pairs]

    def set_shuffle(self, enabled: bool) -> dict:
        enabled = bool(enabled)
        if enabled == self.shuffle:
            return self._result("set_shuffle", enabled=enabled, unchanged=True)

        def mutate():
            with self._lock:
                current_token = (
                    self._item_tokens[self._current_index]
                    if 0 <= self._current_index < len(self._item_tokens) else None
                )
                if enabled:
                    self._shuffle = True
                    self._shuffle_original_tokens = list(self._item_tokens)
                    self._shuffle_seed = random.SystemRandom().randrange(2**63)
                    self._shuffle_effective_order()
                else:
                    item_by_token = dict(zip(
                        self._item_tokens, self._items, strict=True
                    ))
                    original = self._shuffle_original_tokens or list(self._item_tokens)
                    ordered_tokens = [token for token in original if token in item_by_token]
                    ordered_tokens.extend(token for token in self._item_tokens
                                          if token not in set(ordered_tokens))
                    self._item_tokens = ordered_tokens
                    self._items = [item_by_token[token] for token in ordered_tokens]
                    self._current_index = (
                        ordered_tokens.index(current_token)
                        if current_token in ordered_tokens else (-1 if not ordered_tokens else 0)
                    )
                    self._shuffle = False
                    self._shuffle_original_tokens = None
                    self._shuffle_seed = None
            return {"enabled": enabled}

        return self._commit_mutation("set_shuffle", mutate)

    def toggle_shuffle(self) -> dict:
        return self.set_shuffle(not self.shuffle)

    def _execute_current(self) -> dict:
        with self._lock:
            if not self._items:
                return self._error("execute_current", "EMPTY_QUEUE")
            if self._current_index < 0 or self._current_index >= len(self._items):
                return self._error("execute_current", "INVALID_INDEX")
            item = dict(self._items[self._current_index])
            index = self._current_index
        filepath = item.get("filepath", "")
        if not filepath:
            return self._error("execute_current", "MISSING_FILEPATH")
        if not self._player or not hasattr(self._player, "play"):
            return self._error("execute_current", "NO_PLAYER")
        try:
            play_queue_index = getattr(self._player, "play_queue_index", None)
            has_explicit_queue_play = (
                callable(getattr(type(self._player), "play_queue_index", None))
                or "play_queue_index" in vars(self._player)
            )
            if callable(play_queue_index) and has_explicit_queue_play:
                if not play_queue_index(index):
                    return self._error(
                        "execute_current", "PLAYBACK_FAILED",
                        "Backend rejected queue index",
                    )
            else:
                try:
                    self._player.play(
                        filepath,
                        item.get("title", ""),
                        item.get("artist", ""),
                        item.get("album", ""),
                    )
                except TypeError as exc:
                    if "positional" not in str(exc):
                        raise
                    self._player.play(filepath)
        except Exception as exc:
            logger.exception("Queue playback execution failed")
            return self._error("execute_current", "PLAYBACK_FAILED", str(exc))
        return {"ok": True, "item": item, "index": index}

    def undo(self) -> dict:
        with self._lock:
            if not self._undo_stack:
                return self._error("undo", "NOTHING_TO_UNDO")
            target = self._undo_stack[-1]
        current = self._capture_snapshot()
        self._restore_snapshot(target)
        sync_result = self._sync_backend(revision=current.revision + 1)
        if not sync_result.get("ok"):
            self._restore_snapshot(current)
            self._sync_backend(revision=current.revision)
            result = self._error("undo", "BACKEND_SYNC_FAILED",
                                 sync_result.get("message", ""))
            self._publish_failure(result)
            return result
        with self._lock:
            self._undo_stack.pop()
            self._can_undo = bool(self._undo_stack)
            self._revision = current.revision + 1
        self._publish_state("undo")
        return self._result("undo")

    def _publish(self, event: str, **data):
        if self._event_bus:
            with contextlib.suppress(Exception):
                self._event_bus.publish(event, **data)

    def _sync_backend(self, revision: int | None = None) -> dict:
        with self._lock:
            items_snapshot = list(self._items)
            current_index = self._current_index
        if not self._player:
            return {"ok": True, "synced": False}
        paths = [item.get("filepath", "") for item in items_snapshot]
        try:
            clear_queue = getattr(self._player, "clear_queue", None)
            play_queue = getattr(self._player, "play_queue", None)
            set_queue = getattr(self._player, "set_queue", None)
            if not items_snapshot and callable(clear_queue):
                clear_queue()
            elif paths and all(paths) and callable(play_queue):
                try:
                    play_queue(paths, current_index, revision=revision)
                except TypeError as exc:
                    if "revision" not in str(exc):
                        raise
                    play_queue(paths, current_index)
            elif callable(set_queue):
                try:
                    set_queue(paths, current_index, revision=revision)
                except TypeError as exc:
                    if "revision" not in str(exc):
                        if "positional" not in str(exc):
                            raise
                        set_queue(items_snapshot)
                    else:
                        set_queue(paths, current_index)
            else:
                return {"ok": False, "error": "BACKEND_SYNC_FAILED",
                        "message": "Player does not expose a queue synchronization API"}
            set_repeat = getattr(self._player, "set_repeat", None)
            if callable(set_repeat):
                set_repeat(self._repeat)
            set_shuffle = getattr(self._player, "set_shuffle", None)
            if callable(set_shuffle):
                set_shuffle(self._shuffle)
        except Exception as exc:
            logger.exception("Queue backend synchronization failed")
            return {"ok": False, "error": "BACKEND_SYNC_FAILED",
                    "message": str(exc)}
        return {"ok": True, "synced": True}

    def _publish_state(self, operation: str = "state_changed"):
        state = self.get_state()
        self._publish("queue.changed", operation=operation, **state)
        self._publish("queue.persist_requested", revision=self.revision)
        if operation in {"set_repeat", "set_shuffle"}:
            event = "modesChanged"
        elif operation == "restore":
            event = "stateRestored"
        elif operation in {"play_from_index", "next", "previous",
                           "compatibility_index", "backend_progress"}:
            event = "currentIndexChanged"
        else:
            event = "queueChanged"
        self._notify_observers(event, {"operation": operation, **state})

    def _publish_failure(self, result: dict):
        self._publish("queue.operation_failed", **result)
        self._notify_observers("operationFailed", result)

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
                    "shuffle": self._shuffle,
                    "shuffle_order": self.shuffle_order,
                    "shuffle_original_tokens": self._shuffle_original_tokens,
                    "shuffle_seed": self._shuffle_seed,
                    "item_tokens": self._item_tokens,
                    "next_token": self._next_token,
                    "queue_revision": self._revision,
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

    def load_state(self, resolve_fn: Callable[[dict], dict | None] | None = None) -> dict:
        """Restore persisted domain state and synchronize it without autoplay."""
        path = _queue_state_path()
        if not os.path.exists(path):
            return {"ok": False, "error": "NO_SAVED_STATE"}
        try:
            with open(path) as f:
                state = json.load(f)
            items = state.get("items", [])
            if not items:
                return {"ok": False, "error": "EMPTY_QUEUE"}
            if resolve_fn:
                resolved = []
                missing_ids = []
                for item in items:
                    result = resolve_fn(item)
                    if result is not None:
                        resolved.append(result)
                    else:
                        missing_ids.append(item.get("track_id", item.get("id", "")))
                restored_items = resolved
                result = {
                    "ok": True,
                    "count": len(resolved),
                    "missing_count": len(missing_ids),
                    "partial": len(missing_ids) > 0,
                    "missing_track_ids": missing_ids,
                }
            else:
                restored_items = list(items)
                result = {"ok": True, "count": len(items)}
            with self._lock:
                self._items = copy.deepcopy(restored_items)
                saved_tokens = state.get("item_tokens", [])
                if len(saved_tokens) == len(restored_items) and not resolve_fn:
                    self._item_tokens = list(saved_tokens)
                else:
                    self._item_tokens = self._new_tokens(len(restored_items))
                saved_index = int(state.get("current_index", 0))
                self._current_index = (
                    min(max(saved_index, 0), len(restored_items) - 1)
                    if restored_items else -1
                )
                self._shuffle = bool(state.get("shuffle", False))
                self._shuffle_original_tokens = (
                    list(state.get("shuffle_original_tokens") or self._item_tokens)
                    if self._shuffle else None
                )
                self._shuffle_seed = state.get("shuffle_seed")
                self._repeat = state.get("repeat", "none")
                self._context = state.get("context", "")
                self._revision = int(state.get("queue_revision", self._revision))
                self._next_token = max(
                    int(state.get("next_token", self._next_token)),
                    max(self._item_tokens, default=0) + 1,
                )
            sync_result = self._sync_backend()
            if not sync_result.get("ok"):
                return self._error("restore", "BACKEND_SYNC_FAILED",
                                   sync_result.get("message", ""))
            self._publish_state("restore")
            return result
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def persist(self) -> dict:
        return self.save_state()

    def restore(self) -> dict:
        return self.load_state()

    def missing_tracks(self) -> list[dict]:
        return [item for item in self._items if not item.get("filepath")]

    def shutdown(self, position: float = 0.0) -> None:
        self.save_state(position=position)
        self._undo_stack.clear()
