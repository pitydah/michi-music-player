"""FeatureManager — tracks optional feature availability and status."""
from dataclasses import dataclass


@dataclass
class FeatureStatus:
    name: str
    enabled: bool = False
    available: bool = False
    error: str = ""


class FeatureManager:
    """Central registry for optional features: availability, errors, status."""

    def __init__(self):
        self._features: dict[str, FeatureStatus] = {}

    def register(self, name: str, enabled: bool = True):
        self._features[name] = FeatureStatus(name=name, enabled=enabled)

    def mark_available(self, name: str):
        f = self._features.get(name)
        if f:
            f.available = True
            f.error = ""

    def mark_error(self, name: str, error: str):
        f = self._features.get(name)
        if f:
            f.error = error
            f.available = False

    def is_available(self, name: str) -> bool:
        f = self._features.get(name)
        return f.available if f else False

    def is_enabled(self, name: str) -> bool:
        f = self._features.get(name)
        return f.enabled if f else False

    def status_report(self) -> list[dict]:
        return [
            {"name": f.name, "enabled": f.enabled,
             "available": f.available, "error": f.error}
            for f in self._features.values()
        ]
