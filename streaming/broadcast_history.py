"""Broadcast history — track radio and podcast listening history."""

from __future__ import annotations

import dataclasses
import json
import os

from streaming.podcast_models import BroadcastHistoryEntry


class BroadcastHistory:
    """Persistent history of radio and podcast listening."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from core.paths import app_data_dir
            db_path = os.path.join(app_data_dir(), "broadcast_history.json")
        self._path = db_path
        self._entries: list[BroadcastHistoryEntry] = []
        self._load()

    def _load(self):
        if os.path.isfile(self._path):
            try:
                with open(self._path) as f:
                    data = json.load(f)
                self._entries = [BroadcastHistoryEntry(**e) for e in data]
            except Exception:
                self._entries = []

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(
                [dataclasses.asdict(e) for e in self._entries],
                f, indent=2, default=str,
            )

    def add(self, entry: BroadcastHistoryEntry):
        self._entries.insert(0, entry)
        if len(self._entries) > 500:
            self._entries = self._entries[:500]
        self._save()

    def get_all(self, limit: int = 100) -> list[BroadcastHistoryEntry]:
        return self._entries[:limit]

    def get_by_type(self, entry_type: str, limit: int = 50) -> list[BroadcastHistoryEntry]:
        return [e for e in self._entries if e.entry_type == entry_type][:limit]

    def clear(self):
        self._entries.clear()
        self._save()
