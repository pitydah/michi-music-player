"""Shared typed playback-action failure projection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaybackActionFailure:
    code: str
    title: str
    explanation: str

    @property
    def message(self) -> str:
        return f"{self.title}: {self.explanation}"


#: Recovery intents a refusal may offer. NONE of them is executed
#: automatically: the user always decides explicitly.
RECOVERY_TRY_COMPATIBLE_DIRECT = "try_compatible_direct"
RECOVERY_USE_SHARED = "use_shared"
RECOVERY_CANCEL = "cancel"

#: The compatible Direct policy resolves a wider lossless carrier; offering it
#: only makes sense while the exact carrier is the one that failed.
_STRICT_INCOMPATIBLE_CODES = frozenset(
    {
        "EXACT_TUPLE_UNSUPPORTED",
        "EXACT_TUPLE_UNKNOWN",
        "SIGNIFICANT_BITS_UNPROVEN",
    }
)
_SHARED_FALLBACK_CODES = frozenset(
    {
        "NO_COMPATIBLE_CARRIER",
        "ALSA_DEVICE_BUSY",
        "OUTPUT_DEVICE_LOST",
        "DEVICE_UNAVAILABLE",
        "DEVICE_LOST",
        "NO_ALSA_HW_BINDING",
        "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE",
        "MULTIPLE_ALSA_PLAYBACK_ENDPOINTS",
        "ENGINE_UNSUPPORTED_FOR_DIRECT",
        "ENGINE_NOT_GSTREAMER",
        "SELECTED_DEVICE_MISSING",
        "EXACT_QUALIFICATION_TIMEOUT",
        "EXACT_QUALIFICATION_INCONCLUSIVE",
        "EXACT_QUALIFICATION_STALE",
    }
)


def output_recovery_actions(code: str | None) -> tuple[str, ...]:
    """Explicit recovery intents for one typed output refusal."""
    normalized = (code or "").upper()
    if normalized in _STRICT_INCOMPATIBLE_CODES:
        return (
            RECOVERY_TRY_COMPATIBLE_DIRECT,
            RECOVERY_USE_SHARED,
            RECOVERY_CANCEL,
        )
    if normalized in _SHARED_FALLBACK_CODES:
        return (RECOVERY_USE_SHARED, RECOVERY_CANCEL)
    return ()


def playback_action_failure(code: str | None) -> PlaybackActionFailure:
    """Map one typed refusal to stable normal-mode copy."""
    normalized = (code or "").upper()
    if "BUSY" in normalized:
        title, detail = "Device busy", "Another application is using this DAC."
    elif normalized in {"DEVICE_LOST", "OUTPUT_DEVICE_LOST", "DEVICE_UNAVAILABLE"}:
        title, detail = "Device disconnected", "The selected DAC is unavailable."
    elif normalized in {"ENGINE_UNSUPPORTED_FOR_DIRECT", "ENGINE_NOT_GSTREAMER"}:
        title, detail = (
            "Direct requires GStreamer",
            "Select GStreamer explicitly to use Direct output.",
        )
    elif normalized in {"EXACT_TUPLE_UNKNOWN", "SIGNIFICANT_BITS_UNPROVEN"}:
        title, detail = (
            "Format not verified",
            "Michi could not confirm this format for the current DAC connection.",
        )
    elif normalized == "EXACT_TUPLE_UNSUPPORTED":
        title, detail = (
            "Format unsupported",
            "The selected DAC rejected this exact format in Direct mode.",
        )
    elif normalized == "NO_COMPATIBLE_CARRIER":
        title, detail = (
            "No compatible Direct format",
            "This DAC rejected every lossless carrier Michi can send for this track.",
        )
    elif normalized == "EXACT_QUALIFICATION_TIMEOUT":
        title, detail = (
            "Format check timed out",
            "The DAC did not answer the exact format check in time.",
        )
    elif normalized == "EXACT_QUALIFICATION_INCONCLUSIVE":
        title, detail = (
            "Format check inconclusive",
            "Michi could not prove a supported carrier for this track.",
        )
    elif normalized == "EXACT_QUALIFICATION_STALE":
        title, detail = (
            "DAC connection changed",
            "The DAC connection changed while Michi was checking the format.",
        )
    elif normalized in {
        "OUTPUT_BINDING_STALE",
        "OUTPUT_BINDING_VALIDATION_FAILED",
        "BINDING_GENERATION_CHANGED",
    }:
        title, detail = (
            "DAC connection changed",
            "The Direct endpoint changed before playback could start.",
        )
    elif normalized == "MULTIPLE_ALSA_PLAYBACK_ENDPOINTS":
        title, detail = (
            "Choose a Direct endpoint",
            "This DAC exposes multiple playback endpoints and Michi will not guess.",
        )
    elif normalized == "NO_ALSA_HW_BINDING":
        title, detail = (
            "Direct endpoint unavailable",
            "No current hardware playback endpoint is available for this DAC.",
        )
    elif normalized == "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE":
        title, detail = (
            "Not an audio output",
            "This hardware does not expose a current playback endpoint.",
        )
    elif normalized.startswith("SOURCE_CHARACTERIZATION_"):
        title, detail = (
            "Track format unavailable",
            "Michi could not inspect the decoded audio format safely.",
        )
    elif "FIXED" in normalized or "LOCKED" in normalized:
        title, detail = (
            "Output locked at fixed level",
            "Digital attenuation is disabled for this output.",
        )
    elif "CONTRADICT" in normalized or normalized == "OUTPUT_MISMATCH":
        title, detail = (
            "Output mismatch",
            "The runtime output does not match the expected Direct plan.",
        )
    elif normalized in {"OUTPUT_DEVICE_UNKNOWN", "OUTPUT_PROFILE_UNKNOWN"}:
        title, detail = (
            "Output unavailable",
            "The requested output is no longer known to Michi.",
        )
    elif normalized in {"SELECTED_DEVICE_MISSING", "DIRECT_PROFILE_REQUIRED"}:
        title, detail = "Select a DAC", "Choose an available physical DAC first."
    elif normalized == "OUTPUT_PROFILE_DEVICE_MISMATCH":
        title, detail = "Profile mismatch", "This profile belongs to another DAC."
    elif normalized in {"VOLUME_MODE_UNAVAILABLE", "RESYNC_DELAY_INVALID"}:
        title, detail = (
            "Setting unavailable",
            "This setting is not qualified for the selected output.",
        )
    elif normalized == "OUTPUT_PATH_MODE_UNKNOWN":
        title, detail = "Output path unavailable", "Choose Shared or Direct output."
    elif not normalized:
        title, detail = "", ""
    else:
        title, detail = (
            "Output unavailable",
            "Michi could not activate the selected output.",
        )
    return PlaybackActionFailure(normalized, title, detail)
