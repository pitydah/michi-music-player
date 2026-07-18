from __future__ import annotations

import re
from typing import Any

_SANITIZED_FIELDS: set[str] = {
    "title", "artist", "album", "genre", "year",
    "duration_seconds", "track_number", "play_count",
    "last_played", "quality", "format", "sample_rate",
    "bitrate", "channels", "has_artwork", "album_artist",
    "composer", "track_total", "disc_number", "disc_total",
    "bpm", "key", "mood", "energy", "acousticness",
    "danceability", "loudness", "speechiness",
    "instrumentalness", "liveness", "valence",
}

_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(filepath|file_path|abs_path|full_path)"),
    re.compile(r"/home/\w+/"),
    re.compile(r"/mnt/"),
    re.compile(r"/media/\w+/"),
    re.compile(r"/run/media/\w+/"),
    re.compile(r"[A-Za-z]:\\\\"),
    re.compile(r"(?i)(token|secret|password|credential|api_key|apikey)"),
    re.compile(r"(?i)(session_id|sessiontoken|bearer)"),
    re.compile(r"(?i)(device_id|udid|uuid|mac_address|ip_address)"),
]


class SanitizedSnapshot:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class PrivacyGuard:
    def sanitize_input(self, text: str) -> str:
        result = text
        for pattern in _BLOCKED_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result

    def build_snapshot(self, context: dict[str, Any] | None) -> SanitizedSnapshot:
        if not context:
            return SanitizedSnapshot({})
        safe: dict[str, Any] = {}
        for key, value in context.items():
            if key in _SANITIZED_FIELDS:
                safe[key] = value
            elif isinstance(value, dict):
                nested = {}
                for k, v in value.items():
                    if k in _SANITIZED_FIELDS:
                        nested[k] = v
                if nested:
                    safe[key] = nested
            elif isinstance(value, list):
                items = []
                for item in value[:20]:
                    if isinstance(item, dict):
                        filtered = {k: v for k, v in item.items() if k in _SANITIZED_FIELDS}
                        if filtered:
                            items.append(filtered)
                if items:
                    safe[key] = items
        return SanitizedSnapshot(safe)

    def validate_output(self, text: str) -> str:
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(text):
                return "[Respuesta bloqueada por seguridad]"
        return text
