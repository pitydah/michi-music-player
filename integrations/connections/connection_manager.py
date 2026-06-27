"""Connection manager — CRUD for server connection profiles."""

from __future__ import annotations

import json
import logging
import os

from integrations.connections.connection_profile import ConnectionProfile
from core.paths import connection_profiles_path

logger = logging.getLogger("michi.connections.manager")

_STORE_PATH = connection_profiles_path()


class ConnectionManager:
    def __init__(self, store_path: str = _STORE_PATH):
        self._path = store_path
        self._profiles: dict[str, ConnectionProfile] = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path) as f:
                    data = json.load(f)
                for item in data:
                    p = ConnectionProfile(**item)
                    self._profiles[p.id] = p
            except Exception as e:
                logger.warning("Failed to load connections: %s", e)

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = [p.__dict__ for p in self._profiles.values()]
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add(self, profile: ConnectionProfile) -> bool:
        if profile.id in self._profiles:
            return False
        self._profiles[profile.id] = profile
        self._save()
        return True

    def update(self, profile: ConnectionProfile) -> bool:
        if profile.id not in self._profiles:
            return False
        self._profiles[profile.id] = profile
        self._save()
        return True

    def remove(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        del self._profiles[profile_id]
        self._save()
        return True

    def get(self, profile_id: str) -> ConnectionProfile | None:
        return self._profiles.get(profile_id)

    def list_all(self) -> list[ConnectionProfile]:
        return list(self._profiles.values())

    def list_by_type(self, server_type: str) -> list[ConnectionProfile]:
        return [p for p in self._profiles.values() if p.server_type == server_type]
