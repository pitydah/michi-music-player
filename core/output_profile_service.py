"""OutputProfileService — manages audio output profiles and their capabilities."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.output_profile")


class OutputProfileService:
    def __init__(self, player_service=None):
        self._player = player_service

    @property
    def available(self) -> bool:
        return True

    def list_profiles(self) -> list[dict]:
        try:
            from audio.output_profiles import PROFILES
            return [
                {
                    "id": k,
                    "name": v.get("name", k),
                    "allows_eq": v.get("allows_eq", False),
                    "allows_replaygain": v.get("allows_replaygain", False),
                    "bitperfect": v.get("bitperfect", False),
                    "dsd_mode": v.get("dsd_mode", None),
                    "preferred_backend": v.get("preferred_backend", "gstreamer"),
                    "allows_transmit": v.get("allows_transmit", False),
                }
                for k, v in PROFILES.items()
            ]
        except Exception as e:
            logger.error("Error listing profiles: %s", e)
            return []

    def get_active(self) -> dict | None:
        if self._player and hasattr(self._player, 'get_profile'):
            try:
                return self._player.get_profile()
            except Exception:
                pass
        return None

    def apply(self, profile_id: str) -> dict:
        if self._player and hasattr(self._player, 'set_profile'):
            try:
                self._player.set_profile(profile_id)
                return {"ok": True, "profile_id": profile_id}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
