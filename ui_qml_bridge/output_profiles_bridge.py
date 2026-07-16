"""OutputProfilesBridge — QML bridge for audio output profiles.
Create, edit, duplicate, delete, backend, device, sample rate, bit depth,
channels, exclusive, bit-perfect, DSP, fallback, applied state.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class OutputProfilesBridge(QObject):
    dataChanged = Signal()
    appliedStateChanged = Signal(str)

    def __init__(self, player_service=None, parent=None):
        assert player_service is not None, "OutputProfilesBridge: player_service is REQUIRED"
        super().__init__(parent)
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
            if hasattr(self._player, 'get_active_profile_id'):
                self._active_id = self._player.get_active_profile_id() or ""
            self.dataChanged.emit()
            return {"ok": True, "count": len(self._profiles)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _resolve_backend(self, profile_id: str) -> str:
        try:
            from audio.output_profiles import PROFILES
            p = PROFILES.get(profile_id)
            if p:
                return p.get("preferred_backend", "gstreamer")
        except Exception:
            pass
        return "gstreamer"

    @Slot(str, result=dict)
    def setActiveProfile(self, profile_id: str):
        if not self._player:
            return {"ok": False, "error": "UNSUPPORTED", "error_code": "UNSUPPORTED", "message": "Reproductor no disponible"}
        if not hasattr(self._player, 'set_profile'):
            return {"ok": False, "error": "UNSUPPORTED", "error_code": "UNSUPPORTED", "message": "Perfiles no soportados"}
        try:
            backend = self._resolve_backend(profile_id)
            try:
                from audio.output_profiles import PROFILES
                if profile_id not in PROFILES:
                    return {"ok": False, "error": "UNKNOWN_PROFILE", "error_code": "UNKNOWN_PROFILE",
                            "message": "Perfil desconocido", "requested_profile": profile_id,
                            "active_profile": self._active_id, "fallback": False, "requires_restart": False}
            except Exception:
                pass
            self._applied_state = "applying"
            self.appliedStateChanged.emit(self._applied_state)
            player_result = self._player.set_profile(profile_id)
            if isinstance(player_result, dict):
                ok = player_result.get("ok", False)
                fallback = player_result.get("fallback", False)
                err_msg = player_result.get("message", player_result.get("error", ""))
                if not ok:
                    self._applied_state = "rejected"
                    self.appliedStateChanged.emit(self._applied_state)
                    self.dataChanged.emit()
                    return {
                        "ok": False,
                        "error": err_msg or "Error al cambiar perfil",
                        "error_code": player_result.get("error_code", "PROFILE_FAILED"),
                        "message": err_msg or "Error al cambiar perfil",
                        "requested_profile": profile_id,
                        "active_profile": self._active_id,
                        "requested_backend": self._resolve_backend(profile_id),
                        "active_backend": self._resolve_backend(self._active_id if self._active_id else "standard"),
                        "fallback": fallback,
                        "requires_restart": player_result.get("requires_restart", False),
                    }
            self._active_id = profile_id
            self._applied_state = "applied"
            self.appliedStateChanged.emit(self._applied_state)
            self.dataChanged.emit()
            return {
                "ok": True,
                "requested_profile": profile_id,
                "active_profile": profile_id,
                "requested_backend": backend,
                "active_backend": backend,
                "fallback": False,
                "requires_restart": False,
            }
        except Exception as e:
            self._applied_state = "rejected"
            self.appliedStateChanged.emit(self._applied_state)
            return {"ok": False, "error_code": "PROFILE_FAILED", "message": str(e),
                    "requested_profile": profile_id, "active_profile": self._active_id,
                    "requested_backend": backend, "active_backend": self._resolve_backend(self._active_id),
                    "fallback": False, "requires_restart": False}

    @Slot(result=dict)
    def duplicateProfile(self, profile_id: str):
        if not self._player or not hasattr(self._player, 'duplicate_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            result = self._player.duplicate_profile(profile_id)
            self.refresh()
            if isinstance(result, dict) and result.get("ok"):
                return result
            if isinstance(result, dict) and result.get("ok"):
                return result
            return {"ok": False, "error": "DUPLICATE_FAILED"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def deleteProfile(self, profile_id: str):
        if not self._player or not hasattr(self._player, 'delete_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.delete_profile(profile_id)
            if self._active_id == profile_id:
                self._active_id = "standard"
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(dict, result=dict)
    def createProfile(self, data: dict):
        if not self._player or not hasattr(self._player, 'create_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.create_profile(data)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(dict, result=dict)
    def updateProfile(self, data: dict):
        if not self._player or not hasattr(self._player, 'update_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.update_profile(data)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def rollbackProfile(self):
        if not self._player or not hasattr(self._player, 'rollback_profile'):
            return {"ok": False, "error": "UNSUPPORTED"}
        try:
            self._player.rollback_profile()
            self.refresh()
            self._applied_state = "idle"
            self.appliedStateChanged.emit(self._applied_state)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
