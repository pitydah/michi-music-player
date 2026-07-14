import pytest
import tempfile
import os

from core.metadata.backup_rollback import MetadataBackupService, MetadataRollbackService
from core.metadata.enums import BackupPolicy


@pytest.fixture
def test_file():
    fd, path = tempfile.mkstemp(suffix=".flac")
    os.write(fd, b"test audio data")
    os.close(fd)
    yield path
    os.unlink(path)


class TestMetadataBackupService:
    def test_create_backup(self, test_file):
        svc = MetadataBackupService()
        result = svc.create_backup(test_file, BackupPolicy.FULL_FILE_BACKUP)
        assert result.ok is True
        assert "backup_path" in result.data
        backup_path = result.data["backup_path"]
        assert os.path.exists(backup_path)
        os.unlink(backup_path)

    def test_none_policy(self, test_file):
        svc = MetadataBackupService()
        result = svc.create_backup(test_file, BackupPolicy.NONE)
        assert result.ok is True
        assert result.data["backup_path"] == ""

    def test_nonexistent_file(self):
        svc = MetadataBackupService()
        result = svc.create_backup("/nonexistent/file.flac", BackupPolicy.FULL_FILE_BACKUP)
        assert result.ok is False

    def test_restore_backup(self, test_file):
        svc = MetadataBackupService()
        backup = svc.create_backup(test_file, BackupPolicy.FULL_FILE_BACKUP)
        backup_path = backup.data["backup_path"]

        with open(test_file, "w") as f:
            f.write("modified content")

        result = svc.restore_backup(test_file, backup_path)
        assert result.ok is True
        with open(test_file) as f:
            content = f.read()
        assert content == "test audio data"
        os.unlink(backup_path)

    def test_restore_missing_backup(self, test_file):
        svc = MetadataBackupService()
        result = svc.restore_backup(test_file, "/nonexistent/backup.bak")
        assert result.ok is False


class TestMetadataRollbackService:
    def test_rollback_restores_file(self, test_file):
        backup = MetadataBackupService()
        rollback = MetadataRollbackService(backup)

        bk = backup.create_backup(test_file, BackupPolicy.FULL_FILE_BACKUP)
        backup_path = bk.data["backup_path"]

        before_sig = bk.data.get("before_signature", "")

        with open(test_file, "w") as f:
            f.write("modified")

        result = rollback.rollback(test_file, backup_path, before_sig)
        assert result.ok is True
        os.unlink(backup_path)

    def test_rollback_no_backup(self, test_file):
        backup = MetadataBackupService()
        rollback = MetadataRollbackService(backup)
        result = rollback.rollback(test_file, "", "")
        assert result.ok is False
