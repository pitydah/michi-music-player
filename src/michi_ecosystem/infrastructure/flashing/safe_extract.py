"""Secure archive extraction (R6).

Rejects path traversal, absolute paths, backslashes, symlink entries,
duplicate names, oversized entries and oversized totals. Extracts only into a
controlled staging directory.
"""

from __future__ import annotations

import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath

_MAX_ENTRIES = 256
_MAX_ENTRY_BYTES = 16 * 1024 * 1024
_MAX_TOTAL_BYTES = 64 * 1024 * 1024


class ExtractionError(RuntimeError):
    code = "EXTRACTION_REJECTED"


def safe_extract_zip(
    archive: Path,
    destination: Path,
    *,
    max_entries: int = _MAX_ENTRIES,
    max_entry_bytes: int = _MAX_ENTRY_BYTES,
    max_total_bytes: int = _MAX_TOTAL_BYTES,
) -> tuple[str, ...]:
    if not zipfile.is_zipfile(archive):
        raise ExtractionError("archivo no es un ZIP válido")
    destination.mkdir(parents=True, exist_ok=True)
    names: set[str] = set()
    total = 0
    extracted: list[str] = []
    try:
        with zipfile.ZipFile(archive) as bundle:
            infos = bundle.infolist()
            if len(infos) > max_entries:
                raise ExtractionError("demasiadas entradas en el archivo")
            for info in infos:
                name = info.filename
                if name.endswith("/"):
                    continue
                if name.startswith("/") or name.startswith("\\") or "\\" in name:
                    raise ExtractionError(f"ruta no permitida: {name}")
                parts = Path(name).parts
                if Path(name).is_absolute() or any(
                    part in ("..", "") for part in parts
                ):
                    raise ExtractionError(f"path traversal bloqueado: {name}")
                normalized = str(PurePosixPath(name))
                if normalized in names:
                    raise ExtractionError(f"entrada duplicada: {name}")
                names.add(normalized)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ExtractionError(f"symlink bloqueado: {name}")
                if info.file_size > max_entry_bytes:
                    raise ExtractionError(f"entrada demasiado grande: {name}")
                total += info.file_size
                if total > max_total_bytes:
                    raise ExtractionError("extracción total demasiado grande")
                target = destination / str(PurePosixPath(name))
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(info) as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink, 64 * 1024)
                extracted.append(name)
    except ExtractionError:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    except zipfile.BadZipFile as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise ExtractionError(f"ZIP dañado: {exc}") from exc
    return tuple(extracted)
