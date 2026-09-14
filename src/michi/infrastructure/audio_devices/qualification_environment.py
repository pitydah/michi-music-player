"""Read host software/driver inputs for DAC qualification provenance."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path

from michi.infrastructure.audio_devices.alsa_ctypes import library_version


@dataclass(frozen=True, slots=True)
class QualificationHostEnvironment:
    kernel_release: str
    snd_usb_audio_identity: str
    alsa_library_version: str | None


def _read_optional(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def read_qualification_host_environment() -> QualificationHostEnvironment:
    module_version = _read_optional(Path("/sys/module/snd_usb_audio/version"))
    driver_identity = (
        f"snd-usb-audio@{module_version}" if module_version else "snd-usb-audio"
    )
    try:
        alsa_version = library_version()
    except (ImportError, OSError, RuntimeError):
        alsa_version = None
    return QualificationHostEnvironment(
        kernel_release=platform.release(),
        snd_usb_audio_identity=driver_identity,
        alsa_library_version=alsa_version,
    )
