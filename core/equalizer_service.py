"""EqualizerService — manages graphic and parametric EQ state and presets."""
from __future__ import annotations

import contextlib
import logging

logger = logging.getLogger("michi.equalizer")


class EqualizerService:
    def __init__(self, player_service=None):
        self._player = player_service
        self._presets: dict[str, dict] = {}
        self._enabled = False
        self._bands: list[float] = [0.0] * 10
        self._preamp: float = 0.0

    @property
    def available(self) -> bool:
        return self._player is not None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if self._player and hasattr(self._player, 'set_eq_bypass'):
            with contextlib.suppress(Exception):
                self._player.set_eq_bypass(not enabled)

    def set_bands(self, bands: list[float]):
        self._bands = list(bands)
        if self._player and hasattr(self._player, 'set_eq_graphic'):
            with contextlib.suppress(Exception):
                self._player.set_eq_graphic(bands)

    def get_bands(self) -> list[float]:
        return list(self._bands)

    def set_preamp(self, preamp: float):
        self._preamp = preamp
        if self._player and hasattr(self._player, 'set_eq_preamp'):
            with contextlib.suppress(Exception):
                self._player.set_eq_preamp(preamp)

    def get_preamp(self) -> float:
        return self._preamp

    def save_preset(self, name: str) -> dict:
        self._presets[name] = {
            "bands": list(self._bands),
            "preamp": self._preamp,
            "enabled": self._enabled,
        }
        return {"ok": True}

    def load_preset(self, name: str) -> dict:
        preset = self._presets.get(name)
        if not preset:
            return {"ok": False, "error": "NOT_FOUND"}
        self._bands = list(preset.get("bands", [0.0] * 10))
        self._preamp = preset.get("preamp", 0.0)
        self._enabled = preset.get("enabled", False)
        self.set_bands(self._bands)
        self.set_preamp(self._preamp)
        self.set_enabled(self._enabled)
        return {"ok": True}

    def list_presets(self) -> list[str]:
        return list(self._presets.keys())

    def delete_preset(self, name: str) -> dict:
        if name in self._presets:
            del self._presets[name]
            return {"ok": True}
        return {"ok": False, "error": "NOT_FOUND"}

    def reset(self):
        self._bands = [0.0] * 10
        self._preamp = 0.0
        self._enabled = False
        if self._player and hasattr(self._player, 'set_eq_bypass'):
            with contextlib.suppress(Exception):
                self._player.set_eq_bypass(True)

    def start(self):
        pass

    def health(self) -> dict:
        return {"available": self.available, "enabled": self._enabled, "presets": len(self._presets)}

    def shutdown(self):
        pass
