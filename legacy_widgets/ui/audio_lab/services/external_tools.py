"""External tool diagnostics — checks if system tools are installed."""

from __future__ import annotations

import shutil
from ui.audio_lab.models import ExternalToolStatus

_TOOLS_TO_CHECK = [
    ("whipper", False, "Modo Preciso", "sudo pacman -S whipper"),
    ("cdparanoia", False, "Modo Seguro", "sudo pacman -S cdparanoia"),
    ("udisksctl", False, "Montaje de ISO", "sudo pacman -S udisks2"),
    ("7z", False, "Extracción de ISO (alternativo)", "sudo pacman -S p7zip"),
    ("ffmpeg", False, "Conversión de formatos", "sudo pacman -S ffmpeg"),
    ("flac", False, "Codificacion FLAC", "sudo pacman -S flac"),
    ("lame", False, "Codificacion MP3", "sudo pacman -S lame"),
    ("opusenc", False, "Codificacion Opus", "sudo pacman -S opus-tools"),
    ("metaflac", False, "Etiquetas FLAC", "sudo pacman -S flac"),
    ("fpcalc", False, "Identificacion acustica", "sudo pacman -S chromaprint"),
]


def check_all_tools() -> dict[str, ExternalToolStatus]:
    result = {}
    for name, _required, recommended_for, install_hint in _TOOLS_TO_CHECK:
        path = shutil.which(name)
        result[name] = ExternalToolStatus(
            name=name,
            available=path is not None,
            path=path or "",
            required=False,
            recommended_for=recommended_for,
            install_hint=install_hint,
        )
    return result


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def get_tool_diagnostics() -> dict:
    tools = check_all_tools()
    available_count = sum(1 for t in tools.values() if t.available)
    return {
        "tools": {name: {"available": t.available, "path": t.path}
                  for name, t in tools.items()},
        "available_count": available_count,
        "total_checked": len(tools),
        "all_critical_available": all(
            t.available for t in tools.values() if t.required
        ),
    }
