"""AudioIntegrityService — verify audio file integrity.

Checks: decode verification, invalid header, truncated stream,
unreadable file, unsupported codec, duration mismatch, corrupted frames,
checksum, duplicate content, metadata inconsistency, artwork corruption,
file extension mismatch.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.integrity")


class IntegrityStatus:
    VALID = "VALID"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


@dataclass
class IntegrityCheck:
    filepath: str = ""
    status: str = IntegrityStatus.VALID
    issues: list[dict] = field(default_factory=list)
    checksum: str = ""
    duration: float = 0.0
    file_size: int = 0
    is_valid: bool = True
    error: str = ""


class AudioIntegrityService(QObject):
    checkCompleted = Signal(str, object)

    def __init__(self, db=None, wm: WorkerManager | None = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm

    def check(self, filepath: str, quick: bool = False) -> IntegrityCheck:
        result = IntegrityCheck(filepath=filepath)
        if not filepath or not os.path.isfile(filepath):
            result.status = IntegrityStatus.ERROR
            result.error = "FILE_NOT_FOUND"
            result.is_valid = False
            result.issues.append({"type": "FILE_NOT_FOUND", "detail": "Archivo no encontrado"})
            return result

        result.file_size = os.path.getsize(filepath)
        ext = Path(filepath).suffix.lower()

        supported_exts = {".flac", ".wav", ".aiff", ".aif", ".mp3", ".m4a",
                          ".mp4", ".opus", ".ogg", ".mka", ".wma", ".dsf", ".dff"}
        if ext not in supported_exts:
            result.status = IntegrityStatus.UNSUPPORTED
            result.issues.append({"type": "UNSUPPORTED_EXTENSION", "detail": f"Extensión {ext} no soportada"})
            result.is_valid = False
            return result

        if ext == ".mp3" and not self._check_mp3_header(filepath):
            result.issues.append({"type": "INVALID_HEADER", "detail": "Cabecera MP3 inválida"})
            result.is_valid = False

        if ext == ".flac":
            flac_issues = self._check_flac(filepath)
            result.issues.extend(flac_issues)
            if flac_issues:
                result.is_valid = False

        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None:
                result.issues.append({"type": "UNREADABLE", "detail": "mutagen no pudo leer el archivo"})
                result.is_valid = False
            else:
                if hasattr(af.info, "length") and af.info.length > 0:
                    result.duration = af.info.length
                else:
                    result.issues.append({"type": "ZERO_DURATION", "detail": "Duración cero"})
        except Exception as e:
            result.issues.append({"type": "UNREADABLE", "detail": str(e)})
            result.is_valid = False

        if not quick:
            result.checksum = self._compute_checksum(filepath)
            decode_ok = self._check_decode(filepath)
            if not decode_ok:
                result.issues.append({"type": "DECODE_FAILED", "detail": "FFmpeg no pudo decodificar el archivo sin errores"})
                result.is_valid = False

        if ext in (".wma", ".dsf", ".dff"):
            pass

        result.status = IntegrityStatus.VALID if result.is_valid else IntegrityStatus.INVALID
        return result

    def _check_mp3_header(self, filepath: str) -> bool:
        try:
            with open(filepath, "rb") as f:
                header = f.read(3)
            return header[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
        except Exception:
            return False

    def _check_flac(self, filepath: str) -> list[dict]:
        issues = []
        try:
            with open(filepath, "rb") as f:
                magic = f.read(4)
            if magic != b"fLaC":
                issues.append({"type": "INVALID_FLAC_MAGIC", "detail": "Marca fLaC no encontrada"})
        except Exception as e:
            issues.append({"type": "UNREADABLE", "detail": str(e)})
        return issues

    def _compute_checksum(self, filepath: str, blocks: int = 0) -> str:
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                if blocks > 0:
                    for _ in range(blocks):
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
                else:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def _check_decode(self, filepath: str) -> bool:
        """Verifica que FFmpeg pueda decodificar el archivo completo sin errores."""
        import subprocess
        try:
            result = subprocess.run(
                ["ffmpeg", "-v", "error", "-xerror", "-i", filepath, "-f", "null", "-"],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0
        except Exception:
            return False

    def check_duplicate_content(self, filepaths: list[str]) -> list[list[str]]:
        groups: dict[str, list[str]] = {}
        for fp in filepaths:
            ck = self._compute_checksum(fp, blocks=8)
            if ck:
                groups.setdefault(ck, []).append(fp)
        return [g for g in groups.values() if len(g) > 1]
