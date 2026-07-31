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
    stateChanged = Signal()

    def __init__(self, player_service=None, parent=None):
        super().__init__(parent)
        logger.debug("OutputProfilesBridge.__init__ called")
        self._player = player_service
        self._profiles: list[dict] = []
        self._active_id = ""
        self._applied_state = "idle"
        # Real runtime state — never fabricated, only captured from the service.
        self._requested_id = ""
        self._effective_id = ""
        self._active_backend = ""
        self._output_device = ""
        self._output_api = ""
        self._verification_level = ""
        self._bitperfect_state = ""
        self._invalidators: list[str] = []
        self._fallback_active = False
        self._requires_restart = False
        self._last_message = ""

    @Property("QVariantList", notify=dataChanged)
    def profiles(self):
        return list(self._profiles)

    @Property(str, notify=dataChanged)
    def activeProfileId(self):
        return self._active_id

    @Property(str, notify=appliedStateChanged)
    def appliedState(self):
        return self._applied_state

    @Property(str, notify=stateChanged)
    def requestedProfileId(self):
        return self._requested_id

    @Property(str, notify=stateChanged)
    def effectiveProfileId(self):
        return self._effective_id

    @Property(str, notify=stateChanged)
    def activeBackend(self):
        return self._active_backend

    @Property(str, notify=stateChanged)
    def outputDevice(self):
        return self._output_device

    @Property(str, notify=stateChanged)
    def outputApi(self):
        return self._output_api

    @Property(str, notify=stateChanged)
    def verificationLevel(self):
        return self._verification_level

    @Property(str, notify=stateChanged)
    def bitperfectState(self):
        return self._bitperfect_state

    @Property("QVariantList", notify=stateChanged)
    def invalidators(self):
        return list(self._invalidators)

    @Property(bool, notify=stateChanged)
    def fallbackActive(self):
        return self._fallback_active

    @Property(bool, notify=stateChanged)
    def requiresRestart(self):
        return self._requires_restart

    @Property(str, notify=stateChanged)
    def lastMessage(self):
        return self._last_message

    @staticmethod
    def _safe_str(value) -> str:
        return value if isinstance(value, str) else ""

    def _resolve_output_api(self, device_id: str) -> str:
        """Resolve the real output API (alsa/pipewire/pulseaudio) for ``device_id``.

        Returns "" when the device cannot be resolved — never guesses an API.
        """
        if self._active_backend == "mpd":
            return "mpd"
        try:
            from audio.output_device_manager import get_device
            device = get_device(device_id or "auto")
            if device is not None:
                return self._safe_str(getattr(device, "backend", ""))
        except Exception:
            logger.debug("output api resolution failed", exc_info=True)
        return ""

    def _capture_runtime_state(self) -> None:
        """Read effective profile/backend/device from the service (best-effort)."""
        try:
            if hasattr(self._player, "get_active_profile_id"):
                self._effective_id = self._safe_str(self._player.get_active_profile_id())
        except Exception:
            logger.debug("get_active_profile_id failed", exc_info=True)
        try:
            if hasattr(self._player, "get_active_backend_id"):
                self._active_backend = self._safe_str(self._player.get_active_backend_id())
        except Exception:
            logger.debug("get_active_backend_id failed", exc_info=True)
        try:
            if hasattr(self._player, "get_output_device_id"):
                self._output_device = self._safe_str(self._player.get_output_device_id())
        except Exception:
            logger.debug("get_output_device_id failed", exc_info=True)
        self._output_api = self._resolve_output_api(self._output_device)

    def _capture_apply_result(self, profile_id: str, result: dict) -> None:
        """Capture verification/fallback/invalidators from a real apply result."""
        self._requested_id = profile_id
        self._effective_id = self._safe_str(result.get("active_profile")) or self._effective_id
        self._active_backend = self._safe_str(result.get("active_backend")) or self._active_backend
        self._fallback_active = bool(result.get("fallback", False))
        self._requires_restart = bool(result.get("requires_restart", False))
        self._verification_level = self._safe_str(result.get("verification_level"))
        self._bitperfect_state = self._safe_str(result.get("bitperfect_state"))
        self._last_message = self._safe_str(result.get("message"))
        effective_format = result.get("effective_format")
        if isinstance(effective_format, dict):
            device = self._safe_str(effective_format.get("device"))
            if device:
                self._output_device = device
            invalidators = effective_format.get("invalidators") or ()
            self._invalidators = [str(i) for i in invalidators]
            bitperfect = effective_format.get("bitperfect")
            if isinstance(bitperfect, str) and bitperfect:
                self._bitperfect_state = bitperfect
        elif not result.get("ok"):
            self._invalidators = []
        self._output_api = self._resolve_output_api(self._output_device)

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
        self._capture_runtime_state()
        self.dataChanged.emit()
        self.stateChanged.emit()
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
            self._capture_apply_result(profile_id, err if isinstance(err, dict) else {})
            self.stateChanged.emit()
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
        self._capture_apply_result(profile_id, player_result)
        self.dataChanged.emit()
        self.stateChanged.emit()
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

    @Slot(str, result=dict)
    def testProfile(self, profile_id: str):
        """Probe the output device of ``profile_id`` against the real backend.

        Delegates to ``PlayerService.test_output_device`` which performs a real
        existence/permissions/open-close check — the result is never fabricated.
        """
        if not self._player or not hasattr(self._player, 'test_output_device'):
            return {"ok": False, "error": "UNSUPPORTED", "message": "Prueba no soportada"}
        device_id = ""
        try:
            from audio.output_profiles import PROFILES
            profile = PROFILES.get(profile_id)
            if profile is not None:
                if isinstance(profile, dict):
                    device_id = self._safe_str(profile.get("device"))
                else:
                    device_id = self._safe_str(getattr(profile, "device", ""))
        except Exception:
            logger.debug("profile device lookup failed", exc_info=True)
        if not device_id:
            try:
                device_id = self._safe_str(self._player.get_output_device_id())
            except Exception:
                device_id = ""
        if not device_id:
            return {"ok": False, "error": "NO_DEVICE",
                    "message": "Sin dispositivo de salida para probar"}
        try:
            probe = self._player.test_output_device(device_id)
            if not isinstance(probe, tuple) or len(probe) != 2:
                return {"ok": False, "error": "INVALID_RESULT",
                        "message": "Resultado de prueba inválido", "device": device_id}
            ok, message = probe
            return {"ok": bool(ok), "message": str(message), "device": device_id,
                    "details": str(message)}
        except Exception as e:
            return {"ok": False, "error": str(e), "device": device_id}
