"""Transcode service — audio format conversion via ffmpeg for device sync."""

from __future__ import annotations

import logging
import os
import contextlib
import shutil
import subprocess

logger = logging.getLogger("michi.sync.transcode")

TRANSCODE_PROFILES = {
    "original": {"name": "Original", "description": "Sin conversión — archivos tal cual"},
    "flac_mobile": {"name": "FLAC móvil", "description": "FLAC nivel 5 para dispositivos"},
    "opus_balanced": {"name": "OPUS 160", "description": "Equilibrado calidad/espacio"},
    "opus_efficient": {"name": "OPUS 64", "description": "Máximo ahorro de espacio"},
}

_TIMEOUT_SECONDS = 300


class TranscodeService:
    """Audio format conversion using ffmpeg subprocess."""

    def __init__(self):
        self._profiles = TRANSCODE_PROFILES

    @property
    def available(self) -> bool:
        """Whether ffmpeg is available for transcoding."""
        return shutil.which("ffmpeg") is not None

    @property
    def available_encoders(self) -> dict[str, bool]:
        return {
            "flac": shutil.which("flac") is not None,
            "opus": shutil.which("opusenc") is not None,
            "ffmpeg": self.available,
        }

    def get_profile(self, profile_id: str) -> dict:
        return self._profiles.get(profile_id, self._profiles["original"])

    def needs_transcode(self, source_path: str, profile_id: str) -> bool:
        return profile_id != "original"

    # ── Transcode ──

    def transcode(self, source_path: str, dest_path: str,
                  profile_id: str = "original") -> dict:
        """Convert audio from source to destination using the given profile.

        Returns {"ok": bool, "source": str, "destination": str,
                 "profile": str, "error": str}.
        """
        result = {
            "ok": False,
            "source": source_path,
            "destination": dest_path,
            "profile": profile_id,
            "error": "",
        }

        if not os.path.isfile(source_path):
            result["error"] = f"Source file not found: {source_path}"
            return result

        profile = self.get_profile(profile_id)
        if profile is None:
            result["error"] = f"Unknown profile: {profile_id}"
            return result

        if profile_id == "original":
            return self._copy_original(source_path, dest_path, result)

        if profile_id not in self._profiles:
            result["error"] = f"Unknown profile: {profile_id}"
            return result

        return self._transcode_file(source_path, dest_path, profile_id, result)

    # ── Internal ──

    def _copy_original(self, source: str, dest: str,
                       result: dict) -> dict:
        """Copy file without transcoding."""
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            result["ok"] = True
            result["destination"] = dest
            logger.debug("Copied (no transcode): %s → %s", source, dest)
        except OSError as e:
            result["error"] = str(e)
        return result

    def _transcode_file(self, source: str, dest: str,
                        profile_id: str, result: dict) -> dict:
        """Build and run ffmpeg command for a given profile."""
        cmd = self._build_command(source, profile_id)

        if cmd is None:
            result["error"] = f"No ffmpeg command for profile: {profile_id}"
            return result

        # Write to temp file first, then rename atomically
        dest_dir = os.path.dirname(dest)
        os.makedirs(dest_dir, exist_ok=True)
        tmp_path = dest + ".tmp"

        try:
            proc = subprocess.run(
                cmd + [tmp_path],
                capture_output=True,
                timeout=_TIMEOUT_SECONDS,
                text=True,
            )
            if proc.returncode == 0 and os.path.isfile(tmp_path):
                os.replace(tmp_path, dest)
                result["ok"] = True
                result["destination"] = dest
                logger.debug("Transcoded: %s → %s [%s]", source, dest, profile_id)
            else:
                result["error"] = proc.stderr.strip() or f"ffmpeg exit code {proc.returncode}"
                self._cleanup_tmp(tmp_path)
        except subprocess.TimeoutExpired:
            result["error"] = f"Transcode timed out after {_TIMEOUT_SECONDS}s"
            self._cleanup_tmp(tmp_path)
        except FileNotFoundError:
            result["error"] = "ffmpeg not found — is it installed?"
            self._cleanup_tmp(tmp_path)
        except Exception as e:
            result["error"] = str(e)
            self._cleanup_tmp(tmp_path)
        return result

    @staticmethod
    def _cleanup_tmp(tmp_path: str):
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)

    def _build_command(self, source: str, profile_id: str) -> list[str] | None:
        """Build the ffmpeg command array (no shell=True)."""
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return None

        base = [ffmpeg, "-y", "-i", source, "-map_metadata", "0"]

        if profile_id == "flac_mobile":
            return base + [
                "-c:a", "flac",
                "-compression_level", "5",
                "-sample_fmt", "s16",
            ]
        elif profile_id == "opus_balanced":
            return base + [
                "-c:a", "libopus",
                "-b:a", "160k",
                "-vbr", "on",
                "-compression_level", "10",
            ]
        elif profile_id == "opus_efficient":
            return base + [
                "-c:a", "libopus",
                "-b:a", "64k",
                "-vbr", "on",
                "-compression_level", "10",
            ]
        return None
