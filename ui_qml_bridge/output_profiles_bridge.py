"""OutputProfilesBridge — QML bridge for audio output profiles.
Create, edit, duplicate, delete, backend, device, sample rate, bit depth,
channels, exclusive, bit-perfect, DSP, fallback, applied state.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger(__name__)


class OutputProfilesBridge(QObject):
    dataChanged = Signal()
    appliedStateChanged = Signal(str)

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        logger.debug("OutputProfilesBridge.__init__ called")
        self._player = player_service
        self._profiles: list[dict] = []
        self._active_id = ""
        self._applied_state = "idle"

    @Property("QVariantList", notify=dataChanged)
    def profiles(self):
        return list(self._profiles)

    @Property(str, notify=dataChanged)
    def activeProfileId(self):
        return self._active_id

    @Property(str, notify=appliedStateChanged)
    def appliedState(self):
        return self._applied_state

    @Slot(result=dict)
    def refresh(self):
        if not self._player:
            return {"ok": False, "error": "NO_PLAYER"}
        try:
            from audio.output_profiles import PROFILES
            self._profiles = []
            for k, v in PROFILES.items():
                if isinstance(v, dict):
                    self._profiles.append({
                        "id": k, "name": v.get("name", k),
                        "backend": v.get("preferred_backend", "gstreamer"),
                        "allows_eq": v.get("allows_eq", False),
                        "bitperfect": v.get("bitperfect", False),
                        "dsd_mode": v.get("dsd_mode", "pcm"),
                        "exclusive": v.get("exclusive", False),
                        "sample_rate": v.get("sample_rate", 0),
                        "bit_depth": v.get("bit_depth", 0),
                        "channels": v.get("channels", 0),
                        "device": v.get("device", ""),
                        "dsp": v.get("allows_eq", False),
                        "fallback": v.get("fallback", False),
                    })
                else:
                    self._profiles.append({
                        "id": k, "name": getattr(v, 'name', k),
                        "backend": getattr(v, 'preferred_backend', 'gstreamer'),
                        "allows_eq": getattr(v, 'allows_eq', False),
                        "bitperfect": getattr(v, 'bitperfect', False),
                        "dsd_mode": getattr(v, 'dsd_mode', 'pcm'),
                        "exclusive": getattr(v, 'exclusive', False),
                        "sample_rate": getattr(v, 'sample_rate', 0),
                        "bit_depth": getattr(v, 'bit_depth', 0),
                        "channels": getattr(v, 'channels', 0),
                        "device": getattr(v, 'device', ""),
                        "dsp": getattr(v, 'allows_eq', False),
                        "fallback": getattr(v, 'fallback', False),
                    })
        except Exception as e:
            return {"ok": False, "error": str(e)}
        # The active-profile-id lookup is best-effort: a failure to read it must
        # not fail the whole refresh (the profile list is still valid).
        try:
            if hasattr(self._player, 'get_active_profile_id'):
                self._active_id = self._player.get_active_profile_id() or ""
        except Exception:
            logger.debug("get_active_profile_id failed during refresh", exc_info=True)
        self.dataChanged.emit()
        return {"ok": True, "count": len(self._profiles)}

    def _resolve_backend(self, profile_id: str) -> str:
        """Resolve the real backend for ``profile_id`` from the profiles registry.

        Handles both ``AudioOutputProfile`` dataclasses (production) and plain
        dicts (tests). Never fabricates a backend: falls back to ``gstreamer``
        only when the profile is unknown or cannot be read.
        """
        try:
            from audio.output_profiles import PROFILES
            p = PROFILES.get(profile_id)
            if p is None:
                return "gstreamer"
            if isinstance(p, dict):
                return p.get("preferred_backend", "gstreamer") or "gstreamer"
            return getattr(p, "preferred_backend", "gstreamer") or "gstreamer"
        except Exception:
            return "gstreamer"

    def _safe_active_profile(self) -> str:
        """Best-effort read of the active profile id from the service."""
        try:
            if self._player and hasattr(self._player, 'get_active_profile_id'):
                return self._player.get_active_profile_id() or ""
        except Exception:
            pass
        return ""

    @Slot(str, result=dict)
    def setActiveProfile(self, profile_id: str):
        if not self._player:
            return {"ok": False, "error": "UNSUPPORTED", "error_code": "UNSUPPORTED", "message": "Reproductor no disponible"}
        if not hasattr(self._player, 'set_profile'):
            return {"ok": False, "error": "UNSUPPORTED", "error_code": "UNSUPPORTED", "message": "Perfiles no soportados"}
        requested_backend = self._resolve_backend(profile_id)
        try:
            from audio.output_profiles import PROFILES
            if profile_id not in PROFILES:
                return {"ok": False, "error": "UNKNOWN_PROFILE", "error_code": "UNKNOWN_PROFILE",
                        "message": "Perfil desconocido", "requested_profile": profile_id,
                        "active_profile": self._active_id, "fallback": False, "requires_restart": False}
        except Exception:
            # If the registry cannot be read, defer validation to the service.
            pass
        try:
            self._applied_state = "applying"
            self.appliedStateChanged.emit(self._applied_state)
            player_result = self._player.set_profile(profile_id)
        except Exception as e:
            self._applied_state = "rejected"
            self.appliedStateChanged.emit(self._applied_state)
            return {"ok": False, "error_code": "PROFILE_FAILED", "message": str(e),
                    "error": str(e), "requested_profile": profile_id,
                    "active_profile": self._active_id, "requested_backend": requested_backend,
                    "active_backend": self._resolve_backend(self._active_id or "standard"),
                    "fallback": False, "requires_restart": False}
        # Require an explicit dict result with ok=True — never fabricate success.
        if not isinstance(player_result, dict) or not player_result.get("ok"):
            self._applied_state = "rejected"
            self.appliedStateChanged.emit(self._applied_state)
            err = player_result if isinstance(player_result, dict) else {}
            err_msg = err.get("message", err.get("error", "Error al cambiar perfil"))
            active_profile = err.get("active_profile", self._active_id or self._safe_active_profile())
            return {
                "ok": False,
                "error": err_msg,
                "error_code": err.get("error_code", err.get("code", "PROFILE_FAILED")),
                "message": err_msg,
                "requested_profile": profile_id,
                "active_profile": active_profile,
                "requested_backend": requested_backend,
                "active_backend": err.get("active_backend",
                                          self._resolve_backend(active_profile or "standard")),
                "fallback": err.get("fallback", False),
                "requires_restart": err.get("requires_restart", False),
                "rollback": err.get("rollback", False),
            }
        # Success — propagate the real fields returned by the service.
        self._active_id = player_result.get("active_profile", profile_id)
        self._applied_state = "applied"
        self.appliedStateChanged.emit(self._applied_state)
        self.dataChanged.emit()
        return {
            "ok": True,
            "requested_profile": profile_id,
            "active_profile": self._active_id,
            "requested_backend": requested_backend,
            "active_backend": player_result.get("active_backend", requested_backend),
            "fallback": player_result.get("fallback", False),
            "requires_restart": player_result.get("requires_restart", False),
            "verified": player_result.get("verified", False),
            "state": player_result.get("state", "applied"),
        }

    @Slot(result=dict)
    def duplicateProfile(self, profile_id: str):
        if not self._player or not hasattr(self._player, 'duplicate_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.duplicate_profile(profile_id)
            self.refresh()
            if isinstance(result, dict):
                return result
            return {"ok": False, "error": "DUPLICATE_FAILED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteProfile(self, profile_id: str):
        if not self._player or not hasattr(self._player, 'delete_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.delete_profile(profile_id)
            if self._active_id == profile_id:
                self._active_id = "standard"
            self.refresh()
            return result if isinstance(result, dict) else {"ok": bool(result)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(dict, result=dict)
    def createProfile(self, data: dict):
        if not self._player or not hasattr(self._player, 'create_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.create_profile(data)
            self.refresh()
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(dict, result=dict)
    def updateProfile(self, data: dict):
        if not self._player or not hasattr(self._player, 'update_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.update_profile(data)
            self.refresh()
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def rollbackProfile(self):
        if not self._player or not hasattr(self._player, 'rollback_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.rollback_profile()
            self.refresh()
            self._applied_state = "idle"
            self.appliedStateChanged.emit(self._applied_state)
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
