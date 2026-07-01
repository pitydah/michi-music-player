"""Dependency Center — detecta herramientas externas requeridas por Audio Lab.

Uso:
    check = check_dependencies()
    check["ffmpeg"]["available"]  # True/False
    check["ffmpeg"]["path"]       # /usr/bin/ffmpeg o None
"""

from __future__ import annotations

import shutil
from typing import Any

_DEPENDENCIES: list[dict[str, Any]] = [
    {
        "name": "ffmpeg",
        "cmd": "ffmpeg",
        "label": "FFmpeg",
        "required_for": ["FLAC spectral", "conversión a ALAC", "exportación vinilo"],
        "optional": True,
    },
    {
        "name": "flac",
        "cmd": "flac",
        "label": "FLAC CLI",
        "required_for": ["conversión a FLAC"],
        "optional": True,
    },
    {
        "name": "lame",
        "cmd": "lame",
        "label": "LAME MP3",
        "required_for": ["conversión a MP3"],
        "optional": True,
    },
    {
        "name": "opusenc",
        "cmd": "opusenc",
        "label": "Opus encoder",
        "required_for": ["conversión a Opus"],
        "optional": True,
    },
    {
        "name": "cdparanoia",
        "cmd": "cdparanoia",
        "label": "cdparanoia",
        "required_for": ["ripeo de CD"],
        "optional": True,
    },
    {
        "name": "abcde",
        "cmd": "abcde",
        "label": "ABCDE",
        "required_for": ["ripeo de CD automático"],
        "optional": True,
    },
    {
        "name": "fpcalc",
        "cmd": "fpcalc",
        "label": "fpcalc (Chromaprint)",
        "required_for": ["fingerprinting acústico"],
        "optional": True,
    },
]


def check_dependencies() -> dict[str, dict]:
    """Check all known dependencies and return availability."""
    result: dict[str, dict] = {}
    for dep in _DEPENDENCIES:
        path = shutil.which(dep["cmd"])
        result[dep["name"]] = {
            "name": dep["name"],
            "label": dep["label"],
            "available": path is not None,
            "path": path,
            "required_for": dep["required_for"],
            "optional": dep["optional"],
        }
    return result


def check_tools(*names: str) -> dict[str, bool]:
    """Quick check for specific tools. Returns {name: available}."""
    return {n: shutil.which(n) is not None for n in names}


def missing_for(format_name: str) -> list[str]:
    """Return list of missing tools required for a given format."""
    tool_map = {
        "flac": "flac",
        "mp3": "lame",
        "opus": "opusenc",
        "alac": "ffmpeg",
    }
    tool = tool_map.get(format_name)
    if tool and not shutil.which(tool):
        return [tool]
    return []


def format_needs_tool(format_name: str) -> str | None:
    """Return the tool name needed for a format, or None if WAV (no tool)."""
    if format_name == "wav":
        return None
    return {"flac": "flac", "mp3": "lame", "opus": "opusenc", "alac": "ffmpeg"}.get(format_name)
