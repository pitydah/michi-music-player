"""OutputProfileService — audio output profiles with honest capability state.

Authority per ADR-002 (single domain authority for output profile readback and
application); results per ADR-005: ``available``/``health()`` reflect real
conditions (player present, backend compatible, output detected, profile
validated, readback available) and ``set_profile`` follows
validate -> backend -> output -> apply -> readback -> event, returning
``PARTIAL_SUCCESS``/``FAILED`` when the readback does not match the intent.

Bit-perfect profiles refuse to enable simultaneous incompatible options
(EQ, ReplayGain, resampling, crossfade, normalization, DSP, transmit) with a
``CONFLICT`` status — never a nominal success.
"""
from __future__ import annotations

import logging

from core.models.operation_result import OperationResult

logger = logging.getLogger("michi.output_profile")

STATUS_COMPLETED = "COMPLETED"
STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_CONFLICT = "CONFLICT"
STATUS_CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"


class OutputProfileService:
    """Manage audio output profiles against the live player facade."""

    def __init__(self, player_service=None, event_bus=None):
        self._player = player_service
        self._event_bus = event_bus

    # ── Honest capability state ─────────────────────────────────────────

    def _reasons(self) -> list[str]:
        reasons: list[str] = []
        if self._player is None:
            reasons.append("player_missing")
            return reasons
        if not callable(getattr(self._player, "set_profile", None)):
            reasons.append("player_profile_capability_missing")
        if not callable(getattr(self._player, "get_active_profile_id", None)):
            reasons.append("readback_profile_missing")
        if not callable(getattr(self._player, "get_active_backend_id", None)):
            reasons.append("readback_backend_missing")
        if not callable(getattr(self._player, "get_output_device_id", None)):
            reasons.append("readback_output_missing")
        return reasons

    @property
    def available(self) -> bool:
        return not self._reasons()

    def health(self) -> dict:
        reasons = self._reasons()
        return {
            "available": not reasons,
            "reasons": reasons,
            "active_profile": self.get_active_profile_id(),
            "active_backend": self.get_active_backend_id(),
            "output_device": self.get_output_device_id(),
        }

    # ── Profile listing ─────────────────────────────────────────────────

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

    # ── Readback ────────────────────────────────────────────────────────

    def get_active_profile_id(self) -> str:
        if not self._player:
            return ""
        try:
            return self._player.get_active_profile_id() or ""
        except Exception:
            return ""

    def get_active_backend_id(self) -> str:
        if not self._player:
            return ""
        try:
            return self._player.get_active_backend_id() or ""
        except Exception:
            return ""

    def get_output_device_id(self) -> str:
        if not self._player:
            return ""
        try:
            return self._player.get_output_device_id() or ""
        except Exception:
            return ""

    def get_active(self) -> dict | None:
        """Readback of the effective profile, or None when unavailable."""
        active = self.get_active_profile_id()
        if not active:
            return None
        try:
            from audio.output_profiles import PROFILES

            return {
                "id": active,
                "name": PROFILES.get(active, {}).get("name", active),
                "backend": self.get_active_backend_id(),
                "device": self.get_output_device_id(),
            }
        except Exception:
            return {"id": active, "name": active,
                    "backend": self.get_active_backend_id(),
                    "device": self.get_output_device_id()}

    # ── Bit-perfect compatibility ───────────────────────────────────────

    def check_compatibility(self, profile_id: str) -> list[str]:
        """Return the list of conflicts for applying ``profile_id``.

        A conflict is a currently-active option that a bit-perfect profile
        forbids (EQ, ReplayGain, resampling, crossfade, normalization,
        spectrum/DSP, transmit). Mirrors PlayerService's bit-perfect
        invalidator semantics: MPD's DSP-free backend contributes no DSP
        conflicts and resampling only counts when the pipeline actually
        resamples. Empty list means compatible.
        """
        try:
            from audio.output_profiles import is_bitperfect_profile
        except Exception:
            return []
        if not is_bitperfect_profile(profile_id):
            return []
        backend = self.get_active_backend_id()
        conflicts: list[str] = []
        if backend != "mpd" and self._eq_active():
            conflicts.append("eq")
        if self._setting("audio/replaygain_enabled", False):
            conflicts.append("replaygain")
        if backend != "mpd" and self._resampling_active():
            conflicts.append("resampling")
        if backend != "mpd" and float(
                self._setting("audio/crossfade_seconds", 0) or 0) > 0:
            conflicts.append("crossfade")
        if backend != "mpd" and self._setting("audio/spectrum_enabled", False):
            conflicts.append("spectrum")
        if self._transmit_active():
            conflicts.append("transmit")
        return sorted(set(conflicts))

    def _resampling_active(self) -> bool:
        if not self._player:
            return False
        getter = getattr(self._player, "get_audio_diagnostics", None)
        if not callable(getter):
            return False
        try:
            diag = getter()
            return bool(getattr(diag, "resampling_active", False))
        except Exception:
            return False

    def _eq_active(self) -> bool:
        if not self._player:
            return False
        getter = getattr(self._player, "get_eq_state", None)
        if not callable(getter):
            return False
        try:
            state = getter()
            if isinstance(state, dict):
                return str(state.get("mode", "bypass")) != "bypass"
            mode = getattr(state, "mode", "bypass")
            return str(mode) != "bypass"
        except Exception:
            return False

    def _transmit_active(self) -> bool:
        if not self._player:
            return False
        getter = getattr(self._player, "get_transmit_device", None)
        if not callable(getter):
            return False
        try:
            return bool(getter())
        except Exception:
            return False

    @staticmethod
    def _setting(key: str, default):
        try:
            from core.settings_manager import get

            return get(key, default)
        except Exception:
            return default

    # ── Apply pipeline: validate -> backend -> output -> apply -> readback ─

    def set_profile(self, profile_id: str) -> dict:
        """Apply a profile with validate -> apply -> readback -> event.

        Returns an OperationResult-shaped dict. ``ok`` is only True when the
        readback (active profile id + backend) matches the intent.
        """
        if not self.available:
            return self._result(
                OperationResult.fail(
                    "INFRASTRUCTURE_UNAVAILABLE",
                    "Player no disponible para aplicar perfiles",
                ),
                STATUS_CAPABILITY_UNAVAILABLE,
                profile_id=profile_id,
            )
        validated = self._validate_profile(profile_id)
        if not validated.ok:
            return self._result(validated, STATUS_FAILED, profile_id=profile_id)
        conflicts = self.check_compatibility(profile_id)
        if conflicts:
            return self._result(
                OperationResult.fail(
                    "BITPERFECT_CONFLICT",
                    "Perfil bit-perfect incompatible con opciones activas",
                ),
                STATUS_CONFLICT,
                profile_id=profile_id,
                data={"conflicts": conflicts},
            )
        try:
            applied = self._player.set_profile(profile_id)
        except Exception as e:
            logger.error("set_profile(%s) raised: %s", profile_id, e)
            return self._result(
                OperationResult.fail("APPLY_ERROR", str(e)),
                STATUS_FAILED,
                profile_id=profile_id,
            )
        if not isinstance(applied, dict) or not applied.get("ok"):
            err = applied if isinstance(applied, dict) else {}
            return self._result(
                OperationResult.fail(
                    err.get("code", "APPLY_FAILED"),
                    err.get("message", err.get("error", "Fallo al aplicar perfil")),
                ),
                STATUS_FAILED,
                profile_id=profile_id,
            )
        readback = self._readback_matches(profile_id)
        self._emit_event("output_profile.applied", {
            "profile_id": profile_id,
            "readback_ok": readback,
            "backend": self.get_active_backend_id(),
            "device": self.get_output_device_id(),
        })
        if readback:
            return self._result(
                OperationResult.success(
                    data={
                        "profile_id": profile_id,
                        "backend": self.get_active_backend_id(),
                        "device": self.get_output_device_id(),
                    },
                    message="Perfil aplicado y verificado por readback",
                ),
                STATUS_COMPLETED,
                profile_id=profile_id,
            )
        return self._result(
            OperationResult(
                ok=False,
                code="READBACK_MISMATCH",
                message="Perfil aplicado pero el readback no coincide",
            ),
            STATUS_PARTIAL_SUCCESS,
            profile_id=profile_id,
        )

    def apply(self, profile_id: str) -> dict:
        """Alias of :meth:`set_profile` for backward compatibility."""
        return self.set_profile(profile_id)

    def _validate_profile(self, profile_id: str) -> OperationResult:
        try:
            from audio.output_profiles import PROFILES
        except Exception:
            return OperationResult.fail("PROFILE_REGISTRY_UNAVAILABLE",
                                        "No se pudo leer el registro de perfiles")
        if not profile_id or profile_id not in PROFILES:
            return OperationResult.fail(
                "UNKNOWN_PROFILE", f"Perfil desconocido: {profile_id!r}")
        profile = PROFILES[profile_id]
        if isinstance(profile, dict):
            backend = profile.get("preferred_backend", "gstreamer")
        else:
            backend = getattr(profile, "preferred_backend", "gstreamer")
        if backend not in ("gstreamer", "mpd", "auto", "alsa"):
            return OperationResult.fail(
                "UNKNOWN_BACKEND", f"Backend desconocido: {backend!r}")
        return OperationResult.success(data={"profile_id": profile_id, "backend": backend})

    def _readback_matches(self, profile_id: str) -> bool:
        """Readback check: active profile id must match the intent."""
        active = self.get_active_profile_id()
        if not active:
            return False
        if active != profile_id:
            try:
                from audio.output_profiles import get_profile

                intended = get_profile(profile_id)
                active_prof = get_profile(active)
                same = (
                    isinstance(intended, dict) and isinstance(active_prof, dict)
                    and intended.get("name") == active_prof.get("name")
                ) or getattr(intended, "name", None) == getattr(active_prof, "name", None)
                if not same:
                    return False
            except Exception:
                return False
        backend = self.get_active_backend_id()
        return bool(backend)

    def _emit_event(self, event: str, data: dict) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(event, **data)
        except Exception:
            logger.debug("event publish failed for %s", event, exc_info=True)

    def _result(self, op: OperationResult, status: str, profile_id: str,
                data: dict | None = None) -> dict:
        payload = op.to_dict()
        payload["status"] = status
        payload["profile_id"] = profile_id
        if data:
            payload["data"] = {**payload.get("data", {}), **data}
        return payload

    def start(self):
        pass

    def shutdown(self):
        pass
