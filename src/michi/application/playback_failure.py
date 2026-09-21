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
