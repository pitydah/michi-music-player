from __future__ import annotations

import os
import shutil

from core.metadata.models import MetadataOperationResult, compute_file_signature
from core.metadata.enums import MetadataErrorCode, BackupPolicy


class MetadataBackupService:
    def __init__(self, backup_dir: str | None = None):
        self._backup_dir = backup_dir

    def create_backup(self, path: str,
                      policy: BackupPolicy = BackupPolicy.FULL_FILE_BACKUP) -> MetadataOperationResult:
        if not os.path.exists(path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.FILE_NOT_FOUND.value,
            )
        if policy == BackupPolicy.NONE:
            return MetadataOperationResult(ok=True, data={"backup_path": ""})

        if policy == BackupPolicy.FULL_FILE_BACKUP:
            backup_dir = self._backup_dir or os.path.join(os.path.dirname(path), ".michi_backups")
            os.makedirs(backup_dir, exist_ok=True)
            base = os.path.basename(path)
            backup_path = os.path.join(backup_dir, f"{base}.bak")
            try:
                shutil.copy2(path, backup_path)
                return MetadataOperationResult(
                    ok=True, data={"backup_path": backup_path},
                )
            except (OSError, IOError) as e:
                return MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.BACKUP_FAILED.value,
                    message=str(e),
                )

        return MetadataOperationResult(
            ok=False, code=MetadataErrorCode.UNSUPPORTED_OPERATION.value,
            message=f"Backup policy {policy.value} not implemented",
        )

    def restore_backup(self, original_path: str,
                       backup_path: str) -> MetadataOperationResult:
        if not os.path.exists(backup_path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.BACKUP_FAILED.value,
                message="Backup file not found",
            )
        try:
            shutil.copy2(backup_path, original_path)
            return MetadataOperationResult(ok=True)
        except (OSError, IOError) as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.ROLLBACK_FAILED.value,
                message=str(e),
            )

    def cleanup_backup(self, backup_path: str):
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
        except OSError:
            pass


class MetadataRollbackService:
    def __init__(self, backup_service: MetadataBackupService):
        self._backup = backup_service

    def rollback(self, original_path: str, backup_path: str,
                 before_signature: str) -> MetadataOperationResult:
        if not backup_path:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.ROLLBACK_FAILED.value,
                message="No backup reference",
            )
        current_sig = compute_file_signature(original_path)
        if current_sig == before_signature:
            return MetadataOperationResult(
                ok=True, message="File unchanged, no rollback needed",
            )

        result = self._backup.restore_backup(original_path, backup_path)
        if not result.ok:
            return result

        return MetadataOperationResult(ok=True, message="Rollback successful")
