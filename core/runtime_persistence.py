"""RuntimePersistence — atomic, crash-safe storage for runtime state.

API: read(namespace), write(namespace, value), delete(namespace), transaction(namespace), migrate().
Atomic write + fsync. Namespaces: queue, page_state, jobs, notifications, etc.
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from typing import Any, Iterator

logger = logging.getLogger("michi.runtime_persistence")

CURRENT_SCHEMA_VERSION = 1

DOMAIN_FILES = {
    "queue": "queue_state.json",
    "page_state": "page_state.json",
    "jobs": "jobs.json",
    "notifications": "notifications.json",
    "connection_profiles": "connection_profiles.json",
    "device_profiles": "device_profiles.json",
    "audio_lab_profiles": "audio_lab_profiles.json",
}


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _atomic_write(path: str, data: bytes):
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(Exception):
            os.close(fd)
        with contextlib.suppress(Exception):
            os.remove(tmp)
        raise


def _load_json(path: str) -> dict | list | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("corrupted persistence file %s: %s", path, e)
        return None


_MIGRATORS: dict[int, callable] = {}
_ROLLBACKS: dict[int, callable] = {}


def _migrate(raw: dict, target_schema: int) -> dict:
    current = raw.get("schema_version", 0)
    if current == target_schema:
        return raw
    if current > target_schema:
        return _rollback(raw, target_schema)
    for v in range(current, target_schema):
        migrator = _MIGRATORS.get(v + 1)
        if migrator:
            try:
                raw = migrator(raw)
            except Exception as e:
                logger.error("migration v%d->v%d failed: %s", v, v + 1, e)
                return raw
        raw["schema_version"] = v + 1
    return raw


def _rollback(raw: dict, target_schema: int) -> dict:
    current = raw.get("schema_version", 0)
    for v in range(current, target_schema, -1):
        rollback_fn = _ROLLBACKS.get(v)
        if rollback_fn:
            try:
                raw = rollback_fn(raw)
            except Exception as e:
                logger.error("rollback v%d failed: %s", v, e)
                return raw
        raw["schema_version"] = v - 1
    return raw


class RuntimePersistence:
    """Atomic, crash-safe storage for runtime state."""
    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self._base_dir = _ensure_dir(base_dir)
        else:
            from core.paths import app_data_dir
            self._base_dir = _ensure_dir(os.path.join(app_data_dir(), "runtime"))
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}

    def _namespace_path(self, namespace: str) -> str | None:
        filename = DOMAIN_FILES.get(namespace)
        if not filename:
            return None
        return os.path.join(self._base_dir, filename)

    def read(self, namespace: str) -> Any:
        filename = DOMAIN_FILES.get(namespace)
        if not filename:
            return None
        with self._lock:
            if namespace in self._cache:
                return self._cache[namespace]
        path = os.path.join(self._base_dir, filename)
        raw = _load_json(path)
        if raw is not None:
            return raw
        return None

    def write(self, namespace: str, value: Any):
        filename = DOMAIN_FILES.get(namespace)
        if not filename:
            return
        path = os.path.join(self._base_dir, filename)
        payload = value if isinstance(value, list) else {**value, "schema_version": CURRENT_SCHEMA_VERSION}
        blob = json.dumps(payload, indent=2, default=str).encode("utf-8")
        with self._lock:
            _atomic_write(path, blob)
            self._cache[namespace] = value

    def delete(self, namespace: str):
        path = self._namespace_path(namespace)
        if path and os.path.isfile(path):
            with self._lock:
                self._cache.pop(namespace, None)
            try:
                os.remove(path)
            except OSError as e:
                logger.warning("delete %s: %s", namespace, e)

    def migrate(self):
        for namespace in DOMAIN_FILES:
            path = self._namespace_path(namespace)
            if not path or not os.path.isfile(path):
                continue
            raw = _load_json(path)
            if raw and isinstance(raw, dict):
                migrated = _migrate(raw, CURRENT_SCHEMA_VERSION)
                if migrated is not raw:
                    self.write(namespace, migrated)

    @contextmanager
    def transaction(self, namespace: str) -> Iterator[dict]:
        data = self.read(namespace) or {}
        data["schema_version"] = CURRENT_SCHEMA_VERSION
        yield data
        self.write(namespace, data)

    # Legacy domain-specific methods for backward compatibility

    def save_queue(self, data):
        self.write("queue", data)

    def load_queue(self):
        return self.read("queue")

    def save_page_state(self, data):
        self.write("page_state", data)

    def load_page_state(self):
        return self.read("page_state")

    def save_jobs(self, jobs):
        self.write("jobs", jobs)

    def load_jobs(self):
        return self.read("jobs")

    def save_notifications(self, notifications):
        self.write("notifications", notifications)

    def load_notifications(self):
        return self.read("notifications")

    def save_connection_profiles(self, profiles):
        self.write("connection_profiles", profiles)

    def load_connection_profiles(self):
        return self.read("connection_profiles")

    def save_device_profiles(self, profiles):
        self.write("device_profiles", profiles)

    def load_device_profiles(self):
        return self.read("device_profiles")

    def save_audio_lab_profiles(self, profiles):
        self.write("audio_lab_profiles", profiles)

    def load_audio_lab_profiles(self):
        return self.read("audio_lab_profiles")
