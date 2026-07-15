"""RuntimePersistence — atomic, crash-safe storage for runtime state.

Persistence domains:
- Queue (track ID, UID, current index, position, shuffle, repeat, source, schema version)
- Page state (current route, scroll position, filters)
- Jobs (id, type, state, progress, payload)
- Notifications persistentes (id, type, message, timestamp)
- Settings (delegated to settings_service)
- Connection profiles
- Device profiles
- Audio Lab profiles

Writes: temp → fsync → atomic rename → schema version → migration → rollback.
Never writes partially.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from contextlib import suppress
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger("michi.runtime_persistence")

CURRENT_SCHEMA_VERSION = 1


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class PersistedQueue:
    track_id: str = ""
    uid: str = ""
    current_index: int = -1
    position: float = 0.0
    shuffle: bool = False
    repeat: str = "none"
    source: str = "unknown"
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class PersistedPageState:
    current_route: str = ""
    scroll_position: float = 0.0
    filters: dict[str, Any] = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class PersistedJob:
    id: str = ""
    type: str = ""
    state: str = "queued"
    progress: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class PersistedNotification:
    id: str = ""
    type: str = "info"
    message: str = ""
    timestamp: float = 0.0
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class ConnectionProfileData:
    id: str = ""
    name: str = ""
    server_type: str = ""
    url: str = ""
    enabled: bool = True
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class DeviceProfileData:
    id: str = ""
    name: str = ""
    backend: str = ""
    output_device: str = ""
    schema_version: int = CURRENT_SCHEMA_VERSION


@dataclass
class AudioLabProfileData:
    id: str = ""
    name: str = ""
    format: str = ""
    codec: str = ""
    bitrate: int = 320
    schema_version: int = CURRENT_SCHEMA_VERSION


DOMAIN_SERIALIZERS = {
    "queue": (PersistedQueue, "queue_state.json"),
    "page_state": (PersistedPageState, "page_state.json"),
    "jobs": (PersistedJob, "jobs.json"),
    "notifications": (PersistedNotification, "notifications.json"),
    "connection_profiles": (ConnectionProfileData, "connection_profiles.json"),
    "device_profiles": (DeviceProfileData, "device_profiles.json"),
    "audio_lab_profiles": (AudioLabProfileData, "audio_lab_profiles.json"),
}


def _atomic_write(path: str, data: bytes):
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, prefix=".tmp_", suffix=".json")
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp, path)
    except BaseException:
        with suppress(Exception):
            os.close(fd)
        with suppress(Exception):
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


def _migrate(raw: dict, target_schema: int) -> dict:
    current = raw.get("schema_version", 0)
    if current == target_schema:
        return raw
    if current > target_schema:
        logger.warning("schema version %d > target %d, rollback attempt", current, target_schema)
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


_MIGRATORS: dict[int, callable] = {}

_ROLLBACKS: dict[int, callable] = {}


class RuntimePersistence:
    def __init__(self, base_dir: str | None = None):
        if base_dir:
            self._base_dir = _ensure_dir(base_dir)
        else:
            from core.paths import app_data_dir
            self._base_dir = _ensure_dir(os.path.join(app_data_dir(), "runtime"))
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}

    def _domain_path(self, domain: str) -> str | None:
        entry = DOMAIN_SERIALIZERS.get(domain)
        if not entry:
            return None
        return os.path.join(self._base_dir, entry[1])

    def save_queue(self, data: PersistedQueue):
        self._save_domain("queue", asdict(data))

    def load_queue(self) -> PersistedQueue | None:
        raw = self._load_domain("queue")
        if raw:
            raw = _migrate(raw, CURRENT_SCHEMA_VERSION)
            cls = DOMAIN_SERIALIZERS["queue"][0]
            return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})
        return None

    def save_page_state(self, data: PersistedPageState):
        self._save_domain("page_state", asdict(data))

    def load_page_state(self) -> PersistedPageState | None:
        raw = self._load_domain("page_state")
        if raw:
            raw = _migrate(raw, CURRENT_SCHEMA_VERSION)
            cls = DOMAIN_SERIALIZERS["page_state"][0]
            return cls(**{k: v for k, v in raw.items() if k in cls.__dataclass_fields__})
        return None

    def save_jobs(self, jobs: list[PersistedJob]):
        self._save_domain("jobs", [asdict(j) for j in jobs])

    def load_jobs(self) -> list[PersistedJob]:
        raw = self._load_domain("jobs")
        if not raw:
            return []
        cls = DOMAIN_SERIALIZERS["jobs"][0]
        return [cls(**{k: v for k, v in j.items() if k in cls.__dataclass_fields__}) for j in raw]

    def save_notifications(self, notifications: list[PersistedNotification]):
        self._save_domain("notifications", [asdict(n) for n in notifications])

    def load_notifications(self) -> list[PersistedNotification]:
        raw = self._load_domain("notifications")
        if not raw:
            return []
        cls = DOMAIN_SERIALIZERS["notifications"][0]
        return [cls(**{k: v for k, v in n.items() if k in cls.__dataclass_fields__}) for n in raw]

    def save_connection_profiles(self, profiles: list[ConnectionProfileData]):
        self._save_domain("connection_profiles", [asdict(p) for p in profiles])

    def load_connection_profiles(self) -> list[ConnectionProfileData]:
        raw = self._load_domain("connection_profiles")
        if not raw:
            return []
        cls = DOMAIN_SERIALIZERS["connection_profiles"][0]
        return [cls(**{k: v for k, v in p.items() if k in cls.__dataclass_fields__}) for p in raw]

    def save_device_profiles(self, profiles: list[DeviceProfileData]):
        self._save_domain("device_profiles", [asdict(p) for p in profiles])

    def load_device_profiles(self) -> list[DeviceProfileData]:
        raw = self._load_domain("device_profiles")
        if not raw:
            return []
        cls = DOMAIN_SERIALIZERS["device_profiles"][0]
        return [cls(**{k: v for k, v in p.items() if k in cls.__dataclass_fields__}) for p in raw]

    def save_audio_lab_profiles(self, profiles: list[AudioLabProfileData]):
        self._save_domain("audio_lab_profiles", [asdict(p) for p in profiles])

    def load_audio_lab_profiles(self) -> list[AudioLabProfileData]:
        raw = self._load_domain("audio_lab_profiles")
        if not raw:
            return []
        cls = DOMAIN_SERIALIZERS["audio_lab_profiles"][0]
        return [cls(**{k: v for k, v in p.items() if k in cls.__dataclass_fields__}) for p in raw]

    def _save_domain(self, domain: str, data: Any):
        entry = DOMAIN_SERIALIZERS.get(domain)
        if not entry:
            return
        path = os.path.join(self._base_dir, entry[1])
        payload = data if isinstance(data, list) else {**data, "schema_version": CURRENT_SCHEMA_VERSION}
        blob = json.dumps(payload, indent=2, default=str).encode("utf-8")
        with self._lock:
            _atomic_write(path, blob)
            self._cache[domain] = data

    def _load_domain(self, domain: str) -> Any:
        entry = DOMAIN_SERIALIZERS.get(domain)
        if not entry:
            return None
        with self._lock:
            if domain in self._cache:
                return self._cache[domain]
        path = os.path.join(self._base_dir, entry[1])
        raw = _load_json(path)
        return raw
