"""Folder Integrity Service — verify filesystem vs database consistency.

Diagnostic only — never modifies the database or filesystem.
"""

from __future__ import annotations

import os
import time
import hashlib
import logging
from typing import Any

from library.folder_models import (
    FolderIntegrityResult, FolderProblem,
)

logger = logging.getLogger("michi.folder_integrity")

_QUICK_HASH_SIZE = 65536  # 64KB for quick hash


class FolderIntegrityService:
    """Verify file integrity by comparing filesystem state with DB records."""

    def __init__(self, db=None):
        self._db = db

    def set_db(self, db):
        self._db = db

    def quick_check(self, path: str, recursive: bool = False) -> FolderIntegrityResult:
        """Quick integrity check: existence, permissions, size/mtime vs DB."""
        result = FolderIntegrityResult(path=path, deep=False)
        start = time.time()

        if not os.path.exists(path):
            result.errors.append(f"Path does not exist: {path}")
            result.duration_ms = (time.time() - start) * 1000
            return result

        files_to_check = self._gather_files(path, recursive)
        result.total_files = len(files_to_check)

        for fp in files_to_check:
            entry = self._quick_check_file(fp)
            if entry is None:
                result.skipped_files += 1
                continue

            fp_result, problems = entry
            result.checked_files += 1

            if problems:
                for p in problems:
                    if p.problem_type == "missing_from_db":
                        result.missing_files.append(fp)
                    elif p.problem_type == "size_mismatch" or p.problem_type == "mtime_mismatch":
                        result.changed_files.append(fp)
                    elif p.problem_type == "corrupted":
                        result.corrupted_files.append(fp)
                    result.warnings.append(p.description)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def deep_check(self, path: str, recursive: bool = False,
                   hash_full: bool = False) -> FolderIntegrityResult:
        """Deep integrity check: includes metadata extraction and optional full hash."""
        result = FolderIntegrityResult(path=path, deep=True)
        start = time.time()

        if not os.path.exists(path):
            result.errors.append(f"Path does not exist: {path}")
            result.duration_ms = (time.time() - start) * 1000
            return result

        files_to_check = self._gather_files(path, recursive)
        result.total_files = len(files_to_check)

        for fp in files_to_check:
            entry = self._deep_check_file(fp, hash_full=hash_full)
            if entry is None:
                result.skipped_files += 1
                continue

            fp_result, problems = entry
            result.checked_files += 1

            if problems:
                for p in problems:
                    if p.problem_type == "missing_from_db":
                        result.missing_files.append(fp)
                    elif p.problem_type in ("size_mismatch", "mtime_mismatch"):
                        result.changed_files.append(fp)
                    elif p.problem_type == "corrupted":
                        result.corrupted_files.append(fp)
                    result.warnings.append(p.description)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def check_file(self, path: str, deep: bool = False) -> FolderIntegrityResult:
        """Check integrity of a single file."""
        result = FolderIntegrityResult(path=path)
        start = time.time()
        result.total_files = 1

        if not os.path.exists(path):
            result.errors.append(f"File does not exist: {path}")
            result.duration_ms = (time.time() - start) * 1000
            return result

        entry = (self._deep_check_file if deep else self._quick_check_file)(path)
        if entry:
            fp_result, problems = entry
            result.checked_files = 1
            for p in problems:
                if p.problem_type == "missing_from_db":
                    result.missing_files.append(path)
                elif p.problem_type in ("size_mismatch", "mtime_mismatch"):
                    result.changed_files.append(path)
                elif p.problem_type == "corrupted":
                    result.corrupted_files.append(path)
                result.warnings.append(p.description)

        result.duration_ms = (time.time() - start) * 1000
        return result

    def compare_db_file(self, item) -> list[FolderProblem]:
        """Compare a MediaItem with actual file state. Returns problems list."""
        problems = []
        fp = item.filepath

        if not os.path.exists(fp):
            problems.append(FolderProblem(
                path=fp, problem_type="missing_from_db",
                severity="critical",
                description=f"Archivo no encontrado en disco: {fp}",
                suggested_action="cleanup_missing",
                action_label="Limpiar",
            ))
            return problems

        try:
            st = os.stat(fp)
        except OSError as e:
            problems.append(FolderProblem(
                path=fp, problem_type="permission",
                severity="critical",
                description=f"No se puede leer: {e}",
                suggested_action="open_in_file_manager",
                action_label="Abrir gestor",
            ))
            return problems

        if abs(st.st_size - (item.size or 0)) > 0:
            problems.append(FolderProblem(
                path=fp, problem_type="size_mismatch",
                severity="warning",
                description=f"Tamaño cambiado: DB={item.size} disco={st.st_size}",
            ))

        if abs(st.st_mtime - (item.mtime or 0)) > 1.0:
            problems.append(FolderProblem(
                path=fp, problem_type="mtime_mismatch",
                severity="info",
                description=f"Fecha modificación cambiada",
                suggested_action="scan_folder",
                action_label="Escanear",
            ))

        return problems

    def _gather_files(self, path: str, recursive: bool) -> list[str]:
        """Collect files to check."""
        if os.path.isfile(path):
            return [path]

        from library.folder_index import list_audio_files, walk_audio_files
        if recursive:
            return walk_audio_files(path)
        return list_audio_files(path)

    def _quick_check_file(self, path: str) -> tuple[list[str], list[FolderProblem]] | None:
        """Quick check: existence, size, mtime. Returns (result_lines, problems)."""
        problems = []
        result_info = []

        if not os.path.exists(path):
            problems.append(FolderProblem(
                path=path, problem_type="missing_from_db",
                severity="critical",
                description="Archivo no encontrado en disco",
            ))
            return result_info, problems

        if not os.access(path, os.R_OK):
            problems.append(FolderProblem(
                path=path, problem_type="permission",
                severity="critical",
                description="Sin permisos de lectura",
            ))
            return result_info, problems

        if self._db:
            sig = self._db.get_file_signature(path)
            if sig is None:
                problems.append(FolderProblem(
                    path=path, problem_type="not_indexed",
                    severity="info",
                    description="No está en la base de datos",
                    suggested_action="scan_folder",
                    action_label="Escanear",
                ))
            else:
                db_size, db_mtime, _ = sig
                try:
                    st = os.stat(path)
                    if abs(st.st_size - (db_size or 0)) > 0:
                        problems.append(FolderProblem(
                            path=path, problem_type="size_mismatch",
                            severity="warning",
                            description=f"Tamaño diferente",
                        ))
                    if abs(st.st_mtime - (db_mtime or 0)) > 1.0:
                        problems.append(FolderProblem(
                            path=path, problem_type="mtime_mismatch",
                            severity="info",
                            description="Fecha modificación cambiada",
                            suggested_action="scan_folder",
                            action_label="Escanear",
                        ))
                except OSError:
                    pass
        else:
            result_info.append(f"Exists: {path}")

        return result_info, problems

    def _deep_check_file(self, path: str, hash_full: bool = False) -> tuple[list[str], list[FolderProblem]] | None:
        """Deep check: quick check + metadata probe + optional full hash."""
        entry = self._quick_check_file(path)
        if entry is None:
            return None

        result_info, problems = entry

        if not os.path.exists(path) or not os.access(path, os.R_OK):
            return result_info, problems

        # Try metadata extraction
        try:
            from library.metadata_extractor import extract_metadata_combined
            meta = extract_metadata_combined(path)
            if not meta.get("duration"):
                problems.append(FolderProblem(
                    path=path, problem_type="corrupted",
                    severity="warning",
                    description="No se pudo extraer duración del archivo",
                ))
        except Exception as e:
            problems.append(FolderProblem(
                path=path, problem_type="corrupted",
                severity="warning",
                description=f"Error al leer metadatos: {e}",
            ))

        # Hash verification
        if hash_full:
            try:
                computed = self._full_hash(path)
                if self._db:
                    db_hash = self._db.ensure_file_hash(path)
                    if db_hash and computed != db_hash:
                        problems.append(FolderProblem(
                            path=path, problem_type="corrupted",
                            severity="warning",
                            description="Hash completo no coincide",
                        ))
            except Exception as e:
                problems.append(FolderProblem(
                    path=path, problem_type="corrupted",
                    severity="warning",
                    description=f"Error al calcular hash: {e}",
                ))

        return result_info, problems

    @staticmethod
    def _full_hash(path: str) -> str:
        """Compute full SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
