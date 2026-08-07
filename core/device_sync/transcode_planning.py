"""TranscodePlanner — transcode decisions per device capabilities.

Decides WHETHER a track must be transcoded and to WHICH target format,
based on the device's declared supported formats. Execution of the
conversion belongs to the TransferAdapter (controlled subprocess port);
this module never runs external tools.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from core.device_sync.models import DeviceCapabilities
from core.device_sync.profile_resolver import DeviceProfile

# Priority-ordered transcode targets: (target_ext, profile_id)
DEVICE_TRANSCODE_TARGETS = (
    (".flac", "flac_mobile"),
    (".opus", "opus_balanced"),
    (".mp3", "mp3_320"),
)


@dataclass
class TranscodeDecision:
    needs_transcode: bool = False
    possible: bool = True
    profile_id: str = ""
    target_ext: str = ""
    reason: str = ""


def build_ffmpeg_command(source: str, profile_id: str, dest: str) -> list[str] | None:
    """Build the ffmpeg argv for a transcode target (no execution here)."""
    base = ["-y", "-i", source, "-map_metadata", "0"]
    if profile_id == "flac_mobile":
        return base + ["-c:a", "flac", "-compression_level", "5",
                       "-sample_fmt", "s16"]
    if profile_id == "opus_balanced":
        return base + ["-c:a", "libopus", "-b:a", "160k", "-vbr", "on",
                       "-compression_level", "10"]
    if profile_id == "mp3_320":
        return base + ["-c:a", "libmp3lame", "-b:a", "320k"]
    return None


class TranscodePlanner:
    """Real transcode decision: source format vs device supported formats."""

    def __init__(self, transcode_service=None):
        self._transcode = transcode_service

    def decide(self, source_path: str, caps: DeviceCapabilities) -> TranscodeDecision:
        ext = os.path.splitext(source_path)[1].lower()
        if not ext:
            return TranscodeDecision(
                needs_transcode=False, possible=False,
                reason="FORMAT_UNSUPPORTED")
        if ext in caps.supported_formats:
            return TranscodeDecision(
                needs_transcode=False, possible=True,
                reason="Format compatible — copy")

        supported = {
            target for target, _profile in DEVICE_TRANSCODE_TARGETS
            if target in caps.supported_formats
        }
        if not supported:
            return TranscodeDecision(
                needs_transcode=True, possible=False,
                reason="FORMAT_UNSUPPORTED")

        for target, profile in DEVICE_TRANSCODE_TARGETS:
            if target in supported:
                return TranscodeDecision(
                    needs_transcode=True, possible=True,
                    profile_id=profile, target_ext=target,
                    reason=f"Transcode to {target}")

        return TranscodeDecision(
            needs_transcode=True, possible=False,
            reason="FORMAT_UNSUPPORTED")

    def profile_for(self, profile: DeviceProfile) -> str:
        """Preferred transcode profile for a device profile (target first)."""
        for target, transcode_profile in DEVICE_TRANSCODE_TARGETS:
            if target in profile.supported_formats:
                return transcode_profile
        return ""
