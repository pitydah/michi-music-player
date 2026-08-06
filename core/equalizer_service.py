"""EqualizerService — EQ state with readback-first, honest semantics.

Authority per ADR-002: the audio backend (PlayerService) owns the effective EQ
state; this service is a coordinated facade that never keeps an independent
"authority" in memory. Every operation follows
validate -> apply (backend) -> readback -> update state -> persist -> event,
and the internal state is updated ONLY after the readback confirms the change
(ADR-005). When the player is absent the service is explicitly unavailable and
state mutations stay local-only (``ACCEPTED`` with ``LOCAL_ONLY``), never
fabricated as backend-applied.

Presets are persisted through :class:`EqualizerPresetRepository`, which
delegates to ``audio.eq_presets`` (built-in registry + custom user presets) —
the single preset store, no parallel copy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("michi.equalizer")

GRAPHIC_BAND_COUNT = 31
MIN_GAIN_DB = -24.0
MAX_GAIN_DB = 24.0
MIN_PREAMP_DB = -24.0
MAX_PREAMP_DB = 24.0

STATUS_COMPLETED = "COMPLETED"
STATUS_ACCEPTED = "ACCEPTED"
STATUS_FAILED = "FAILED"
STATUS_CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
STATUS_CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class EqualizerCapabilities:
    """What the EQ can do right now, with honest reasons when it cannot."""

    graphic_bands: int = GRAPHIC_BAND_COUNT
    parametric_bands: int = 6
    min_gain_db: float = MIN_GAIN_DB
    max_gain_db: float = MAX_GAIN_DB
    bitperfect_blocked: bool = False
    mpd_blocked: bool = False
    profile_forbids_eq: bool = False
    reasons: tuple[str, ...] = ()

    @property
    def available(self) -> bool:
        return not self.reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "graphic_bands": self.graphic_bands,
            "parametric_bands": self.parametric_bands,
            "min_gain_db": self.min_gain_db,
            "max_gain_db": self.max_gain_db,
            "bitperfect_blocked": self.bitperfect_blocked,
            "mpd_blocked": self.mpd_blocked,
            "profile_forbids_eq": self.profile_forbids_eq,
            "available": self.available,
            "reasons": list(self.reasons),
        }


@dataclass
class EqualizerState:
    """Readback of the effective EQ state (never invented)."""

    enabled: bool = False
    bypass: bool = True
    mode: str = "bypass"
    bands: list[float] = field(default_factory=lambda: [0.0] * GRAPHIC_BAND_COUNT)
    preamp: float = 0.0
    from_backend: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "bypass": self.bypass,
            "mode": self.mode,
            "bands": list(self.bands),
            "preamp": self.preamp,
            "from_backend": self.from_backend,
        }


class EqualizerPresetRepository:
    """Preset store delegating to ``audio.eq_presets`` — the single store.

    With ``persist=True`` user presets round-trip through the same JSON file
    the EQ bridge writes (``eq_presets.json``); with ``persist=False`` the
    repository is in-memory (test isolation).
    """

    def __init__(self, persist: bool = True):
        self._persist = persist
        self._user_presets: dict[str, dict[str, Any]] = (
            self._load_user() if persist else {}
        )

    def _load_user(self) -> dict[str, dict[str, Any]]:
        try:
            from audio.eq_presets import load_custom_presets

            return dict(load_custom_presets() or {})
        except Exception:
            logger.debug("custom preset load failed", exc_info=True)
            return {}

    def _save_user(self) -> bool:
        if not self._persist:
            return True
        try:
            from audio.eq_presets import save_custom_presets

            save_custom_presets(self._user_presets)
            return True
        except Exception:
            logger.error("custom preset save failed", exc_info=True)
            return False

    def list_builtin_names(self) -> list[str]:
        try:
            from audio.eq_presets import get_preset_names

            return list(get_preset_names())
        except Exception:
            return []

    def load_builtin(self, name: str) -> list[float] | None:
        try:
            from audio.eq_presets import GRAPHIC_PRESETS, load_graphic_preset

            if name not in GRAPHIC_PRESETS:
                return None
            bands = load_graphic_preset(name)
            return list(bands) if bands else None
        except Exception:
            return None

    def list_presets(self) -> list[str]:
        return sorted(set(self._user_presets))

    def get(self, name: str) -> dict[str, Any] | None:
        preset = self._user_presets.get(name)
        if preset is not None:
            return {
                "bands": list(preset.get("bands", [0.0] * GRAPHIC_BAND_COUNT)),
                "preamp": float(preset.get("preamp", 0.0)),
                "enabled": bool(preset.get("enabled", False)),
            }
        bands = self.load_builtin(name)
        if bands is not None:
            return {"bands": list(bands), "preamp": 0.0, "enabled": True}
        return None

    def save(self, name: str, bands: list[float], preamp: float,
             enabled: bool) -> bool:
        if not name:
            return False
        self._user_presets[name] = {
            "bands": [float(b) for b in bands],
            "preamp": float(preamp),
            "enabled": bool(enabled),
        }
        return self._save_user()

    def delete(self, name: str) -> bool:
        if name in self._user_presets:
            del self._user_presets[name]
            return self._save_user()
        return False


class EqualizerService:
    """EQ facade — validate, apply to backend, readback, then update state."""

    def __init__(self, player_service=None, preset_repository=None,
                 event_bus=None):
        self._player = player_service
        self._event_bus = event_bus
        self._repository = preset_repository or EqualizerPresetRepository(
            persist=False)
        self._enabled = False
        self._bands: list[float] = [0.0] * GRAPHIC_BAND_COUNT
        self._preamp: float = 0.0

    # ── Capability (honest) ─────────────────────────────────────────────

    def capabilities(self) -> EqualizerCapabilities:
        reasons: list[str] = []
        mpd_blocked = False
        bitperfect_blocked = False
        profile_forbids = False
        if self._player is None:
            reasons.append("player_missing")
        else:
            try:
                backend_id = self._player.get_active_backend_id()
                if backend_id and "mpd" in str(backend_id).lower():
                    mpd_blocked = True
                    reasons.append("mpd_backend_blocks_eq")
            except Exception:
                pass
            try:
                profile_id = self._player.get_active_profile_id()
                from audio.output_profiles import get_profile

                profile = get_profile(profile_id or "standard")
                if profile.bitperfect:
                    bitperfect_blocked = True
                    reasons.append("bitperfect_forbids_eq")
                elif not profile.allows_eq:
                    profile_forbids = True
                    reasons.append("profile_forbids_eq")
            except Exception:
                pass
        return EqualizerCapabilities(
            bitperfect_blocked=bitperfect_blocked,
            mpd_blocked=mpd_blocked,
            profile_forbids_eq=profile_forbids,
            reasons=tuple(reasons),
        )

    @property
    def available(self) -> bool:
        return self.capabilities().available

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── Readback ────────────────────────────────────────────────────────

    def get_eq_state(self) -> EqualizerState:
        """Readback from the backend; local state only as a last resort."""
        if self._player is not None and hasattr(self._player, "get_eq_state"):
            try:
                raw = self._player.get_eq_state()
                if isinstance(raw, dict):
                    mode = str(raw.get("mode", "bypass"))
                    bands = raw.get("bands_31")
                    if not isinstance(bands, list):
                        bands = raw.get("graphic_bands")
                    bands = [float(b) for b in bands] if isinstance(bands, list) else self._bands
                    return EqualizerState(
                        enabled=mode != "bypass",
                        bypass=mode == "bypass",
                        mode=mode,
                        bands=bands,
                        preamp=float(raw.get("preamp_db", raw.get("preamp", 0.0))),
                        from_backend=True,
                    )
                if hasattr(raw, "mode"):
                    mode = str(raw.mode)
                    bands = getattr(raw, "bands_31", None) or getattr(raw, "bands", None)
                    return EqualizerState(
                        enabled=mode != "bypass",
                        bypass=mode == "bypass",
                        mode=mode,
                        bands=[float(b) for b in bands] if bands else self._bands,
                        preamp=float(getattr(raw, "preamp_db", 0.0)),
                        from_backend=True,
                    )
            except Exception:
                logger.debug("EQ readback failed", exc_info=True)
        return EqualizerState(
            enabled=self._enabled,
            bypass=not self._enabled,
            mode="graphic" if self._enabled else "bypass",
            bands=list(self._bands),
            preamp=self._preamp,
            from_backend=False,
        )

    def get_bands(self) -> list[float]:
        return list(self.get_eq_state().bands)

    def get_preamp(self) -> float:
        return self.get_eq_state().preamp

    # ── Mutations: validate -> apply -> readback -> update state ────────

    def _validate_gain(self, value: float) -> bool:
        return MIN_GAIN_DB <= float(value) <= MAX_GAIN_DB

    def set_bands(self, bands: list[float]) -> dict:
        """Apply graphic bands to the backend, then update state on readback."""
        if not isinstance(bands, list) or not bands:
            return self._result(STATUS_FAILED, "INVALID_BANDS",
                                "Lista de bandas vacía o inválida")
        if any(not self._validate_gain(b) for b in bands):
            return self._result(STATUS_FAILED, "GAIN_OUT_OF_RANGE",
                                f"Ganancias fuera de rango ({MIN_GAIN_DB}..{MAX_GAIN_DB} dB)")
        if self._player is None:
            self._bands = [float(b) for b in bands]
            self._emit("equalizer.bands_changed", bands=list(self._bands))
            return self._result(STATUS_ACCEPTED, "LOCAL_ONLY",
                                "Sin backend: estado local actualizado",
                                data={"bands": list(self._bands)})
        if not self.available:
            return self._result(STATUS_CAPABILITY_UNAVAILABLE,
                                "EQ_CAPABILITY_UNAVAILABLE",
                                "EQ no disponible en este modo",
                                data={"reasons": list(self.capabilities().reasons)})
        if len(bands) != GRAPHIC_BAND_COUNT:
            return self._result(STATUS_FAILED, "INVALID_BAND_COUNT",
                                f"Se esperaban {GRAPHIC_BAND_COUNT} bandas, se recibieron {len(bands)}")
        try:
            self._player.set_eq_graphic([float(b) for b in bands])
        except Exception as e:
            logger.error("set_eq_graphic failed: %s", e)
            return self._result(STATUS_FAILED, "BACKEND_APPLY_FAILED", str(e))
        readback = self.get_eq_state()
        if not readback.from_backend or readback.bands != [float(b) for b in bands]:
            return self._result(STATUS_FAILED, "READBACK_MISMATCH",
                                "El readback del backend no confirma las bandas",
                                data={"expected": [float(b) for b in bands]})
        self._bands = readback.bands
        self._emit("equalizer.bands_changed", bands=list(self._bands))
        return self._result(STATUS_COMPLETED, "OK",
                            "Bandas aplicadas y verificadas",
                            data={"bands": list(self._bands)})

    def set_preamp(self, preamp: float) -> dict:
        if not self._validate_gain(float(preamp)):
            return self._result(STATUS_FAILED, "GAIN_OUT_OF_RANGE",
                                f"Preamp fuera de rango ({MIN_GAIN_DB}..{MAX_GAIN_DB} dB)")
        if self._player is None:
            self._preamp = float(preamp)
            self._emit("equalizer.preamp_changed", preamp=self._preamp)
            return self._result(STATUS_ACCEPTED, "LOCAL_ONLY",
                                "Sin backend: estado local actualizado",
                                data={"preamp": self._preamp})
        if not self.available:
            return self._result(STATUS_CAPABILITY_UNAVAILABLE,
                                "EQ_CAPABILITY_UNAVAILABLE",
                                "EQ no disponible en este modo",
                                data={"reasons": list(self.capabilities().reasons)})
        try:
            self._player.set_eq_preamp(float(preamp))
        except Exception as e:
            logger.error("set_eq_preamp failed: %s", e)
            return self._result(STATUS_FAILED, "BACKEND_APPLY_FAILED", str(e))
        readback = self.get_eq_state()
        if not readback.from_backend or abs(readback.preamp - float(preamp)) > 0.001:
            return self._result(STATUS_FAILED, "READBACK_MISMATCH",
                                "El readback del backend no confirma el preamp")
        self._preamp = readback.preamp
        self._emit("equalizer.preamp_changed", preamp=self._preamp)
        return self._result(STATUS_COMPLETED, "OK",
                            "Preamp aplicado y verificado",
                            data={"preamp": self._preamp})

    def set_enabled(self, enabled: bool) -> dict:
        """Enable/disable EQ through bypass, confirmed by backend readback."""
        if self._player is None:
            self._enabled = bool(enabled)
            self._emit("equalizer.enabled_changed", enabled=self._enabled)
            return self._result(STATUS_ACCEPTED, "LOCAL_ONLY",
                                "Sin backend: estado local actualizado",
                                data={"enabled": self._enabled})
        if not self.available and enabled:
            return self._result(STATUS_CAPABILITY_UNAVAILABLE,
                                "EQ_CAPABILITY_UNAVAILABLE",
                                "EQ no disponible en este modo",
                                data={"reasons": list(self.capabilities().reasons)})
        try:
            self._player.set_eq_bypass(not enabled)
        except Exception as e:
            logger.error("set_eq_bypass failed: %s", e)
            return self._result(STATUS_FAILED, "BACKEND_APPLY_FAILED", str(e))
        readback = self.get_eq_state()
        if not readback.from_backend or readback.enabled != bool(enabled):
            return self._result(STATUS_FAILED, "READBACK_MISMATCH",
                                "El readback del backend no confirma el estado")
        self._enabled = readback.enabled
        self._emit("equalizer.enabled_changed", enabled=self._enabled)
        return self._result(STATUS_COMPLETED, "OK",
                            "Estado aplicado y verificado",
                            data={"enabled": self._enabled})

    # ── Presets ─────────────────────────────────────────────────────────

    def save_preset(self, name: str) -> dict:
        if not name:
            return self._result(STATUS_FAILED, "EMPTY_NAME", "Nombre de preset vacío")
        state = self.get_eq_state()
        if not self._repository.save(name, state.bands, state.preamp, state.enabled):
            return self._result(STATUS_FAILED, "PRESET_PERSIST_FAILED",
                                "No se pudo persistir el preset")
        self._emit("equalizer.preset_saved", name=name)
        return self._result(STATUS_COMPLETED, "OK",
                            "Preset guardado",
                            data={"name": name, "presets": self.list_presets()})

    def load_preset(self, name: str) -> dict:
        preset = self._repository.get(name)
        if preset is None:
            return self._result(STATUS_FAILED, "NOT_FOUND",
                                f"Preset no encontrado: {name!r}")
        bands_result = self.set_bands(preset["bands"])
        if not bands_result.get("ok"):
            return bands_result
        preamp_result = self.set_preamp(preset["preamp"])
        if not preamp_result.get("ok"):
            return preamp_result
        if preset.get("enabled", True):
            enabled_result = self.set_enabled(True)
            if not enabled_result.get("ok"):
                return enabled_result
        self._emit("equalizer.preset_loaded", name=name)
        return self._result(STATUS_COMPLETED, "OK",
                            f"Preset {name!r} aplicado y verificado",
                            data={"name": name})

    def list_presets(self) -> list[str]:
        return self._repository.list_presets()

    def delete_preset(self, name: str) -> dict:
        if not self._repository.delete(name):
            return self._result(STATUS_FAILED, "NOT_FOUND",
                                f"Preset no encontrado: {name!r}")
        self._emit("equalizer.preset_deleted", name=name)
        return self._result(STATUS_COMPLETED, "OK", "Preset eliminado")

    def reset(self) -> dict:
        """Reset EQ to flat; local-only when no backend is present."""
        flat = [0.0] * GRAPHIC_BAND_COUNT
        if self._player is None:
            self._bands = flat
            self._preamp = 0.0
            self._enabled = False
            self._emit("equalizer.reset", flat=True)
            return self._result(STATUS_ACCEPTED, "LOCAL_ONLY",
                                "Sin backend: estado local reiniciado")
        try:
            self._player.set_eq_graphic(flat)
            self._player.set_eq_preamp(0.0)
            self._player.set_eq_bypass(True)
        except Exception as e:
            logger.error("EQ reset failed: %s", e)
            return self._result(STATUS_FAILED, "BACKEND_APPLY_FAILED", str(e))
        readback = self.get_eq_state()
        if not readback.from_backend:
            return self._result(STATUS_FAILED, "READBACK_MISMATCH",
                                "El readback del backend no confirma el reset")
        self._bands = readback.bands
        self._preamp = readback.preamp
        self._enabled = readback.enabled
        self._emit("equalizer.reset", flat=True)
        return self._result(STATUS_COMPLETED, "OK", "EQ reiniciado y verificado")

    # ── Helpers ─────────────────────────────────────────────────────────

    def _emit(self, event: str, **data) -> None:
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(event, **data)
        except Exception:
            logger.debug("event publish failed for %s", event, exc_info=True)

    def _result(self, status: str, code: str, message: str,
                data: dict | None = None) -> dict:
        return {
            "ok": status in (STATUS_COMPLETED, STATUS_ACCEPTED),
            "status": status,
            "code": code,
            "message": message,
            "data": data or {},
        }

    def start(self):
        pass

    def health(self) -> dict:
        caps = self.capabilities()
        state = self.get_eq_state()
        return {
            "available": caps.available,
            "enabled": state.enabled,
            "presets": len(self.list_presets()),
            "capabilities": caps.to_dict(),
        }

    def shutdown(self):
        pass
