"""Audio snapshot section — output device, profile and DSP state.

Derives from PlayerService readback + persisted audio settings. The DAC/bit-
perfect heuristics follow the Home Dashboard rules (AGENTS.md): bit-perfect is
never reported as ``verified`` (at most ``intended``) and ``dac_active`` is
derived from the device NAME keywords, never from the profile name alone.
"""

from __future__ import annotations

from typing import Any

_DAC_KEYWORDS = (
    "dac", "usb audio", "hi-fi", "hifi", "audioquest", "ifi",
    "topping", "schiit", "smsl", "rme", "focusrite",
    "scarlett", "motu", "benchmark", "apogee",
    "minidsp", "cmedia", "xmos",
)


class AudioSectionProvider:
    section_key = "audio"

    def build(self, context) -> dict[str, Any]:
        output_device = ""
        output_profile = ""
        replaygain_enabled = False
        eq_enabled = False
        dsp_active = False
        warnings_list: list[str] = []
        backend_id = ""
        sample_rate = 0
        bit_depth = 0
        format_label = ""

        try:
            from core.settings_manager import get_str, get_bool
            output_profile = get_str("audio/profile") or ""
            replaygain_enabled = get_bool("audio/replaygain_enabled")
        except Exception:
            pass

        playback = context.services.get("playback_service")
        if playback is not None:
            try:
                if hasattr(playback, "get_output_device_id"):
                    oid = playback.get_output_device_id()
                    if oid:
                        output_device = str(oid)
                if hasattr(playback, "get_audio_diagnostics"):
                    diag = playback.get_audio_diagnostics()
                    if isinstance(diag, dict):
                        warnings_list = diag.get("warnings", [])
                if hasattr(playback, "get_eq_state"):
                    eq_state = playback.get_eq_state()
                    if isinstance(eq_state, dict):
                        eq_enabled = not eq_state.get("bypass", True)
                        dsp_active = dsp_active or eq_enabled
                if hasattr(playback, "get_active_backend_id"):
                    backend_id = playback.get_active_backend_id() or ""
                if hasattr(playback, "get_playback_snapshot"):
                    snap = playback.get_playback_snapshot()
                    if isinstance(snap, dict):
                        sample_rate = int(snap.get("sample_rate", 0) or 0)
                        bit_depth = int(snap.get("bit_depth", 0) or 0)
                        format_label = str(snap.get("format_label", "") or "")
            except Exception:
                pass

        if playback is None and not output_device and not output_profile:
            return {
                "available": False,
                "reason": "playback_service_missing",
                "output_device": "",
                "output_profile": output_profile,
            }

        if not output_device:
            output_device = "Predeterminado"

        dac_active = False
        dev_lower = output_device.lower()
        if output_device != "Predeterminado":
            for kw in _DAC_KEYWORDS:
                if kw in dev_lower:
                    dac_active = True
                    break

        # Honest bit-perfect semantics (AGENTS.md: never "verified").
        is_bitperfect_profile = "bitperfect" in output_profile.lower()
        bitperfect_state = "not_available"
        bitperfect_intended = False
        if is_bitperfect_profile:
            bitperfect_intended = True
            if eq_enabled or dsp_active or replaygain_enabled:
                bitperfect_state = "disabled"
            elif dac_active:
                bitperfect_state = "intended"
            else:
                bitperfect_state = "not_verified"
        elif output_device != "Predeterminado":
            bitperfect_state = "disabled" if (eq_enabled or dsp_active) else "not_verified"

        return {
            "available": True,
            "reason": "",
            "output_device": output_device,
            "output_profile": output_profile,
            "backend_id": backend_id,
            "dac_active": dac_active,
            "replaygain_enabled": replaygain_enabled,
            "eq_enabled": eq_enabled,
            "dsp_active": dsp_active,
            "bitperfect_state": bitperfect_state,
            "bitperfect_intended": bitperfect_intended,
            "format_label": format_label,
            "sample_rate": sample_rate,
            "bit_depth": bit_depth,
            "warnings": warnings_list[:5],
        }
