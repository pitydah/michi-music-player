"""Tests for FolderIntegrityService."""

import os
import tempfile
from unittest.mock import MagicMock

from library.folder_integrity import FolderIntegrityService


class TestQuickCheck:
    def service(self, db=None):
        return FolderIntegrityService(db=db)

    def test_nonexistent_path(self):
        result = self.service().quick_check("/nonexistent_path")
        assert not result.passed
        assert result.errors

    def test_single_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            result = self.service().check_file(tmp)
            assert result.passed
            assert result.checked_files == 1
        finally:
            os.unlink(tmp)

    def test_single_file_missing(self):
        result = self.service().check_file("/nonexistent.mp3")
        assert not result.passed
        assert result.errors

    def test_folder_quick(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "a.flac"), "w").close()
            open(os.path.join(tmpdir, "b.mp3"), "w").close()
            result = self.service().quick_check(tmpdir)
            assert result.total_files == 2
            assert result.checked_files == 2
            assert result.passed

    def test_folder_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            open(os.path.join(tmpdir, "a.flac"), "w").close()
            open(os.path.join(tmpdir, "sub", "b.mp3"), "w").close()
            result = self.service().quick_check(tmpdir, recursive=True)
            assert result.total_files == 2

    def test_size_mismatch(self):
        db = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"small")
            tmp = f.name
        st = os.stat(tmp)
        db.get_file_signature.return_value = (999999, st.st_mtime, "hash123")
        try:
            result = self.service(db).check_file(tmp)
            assert result.changed_files
            assert len(result.warnings) > 0
        finally:
            os.unlink(tmp)

    def test_not_indexed(self):
        db = MagicMock()
        db.get_file_signature.return_value = None
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            result = self.service(db).check_file(tmp)
            assert result.checked_files == 1
            # not_indexed is info, not an error
            assert result.passed
        finally:
            os.unlink(tmp)

    def test_compare_db_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 100)
            tmp = f.name
        st = os.stat(tmp)
        item = MagicMock()
        item.filepath = tmp
        item.size = st.st_size
        item.mtime = st.st_mtime
        try:
            problems = FolderIntegrityService().compare_db_file(item)
            assert len(problems) == 0
        finally:
            os.unlink(tmp)

    def test_compare_db_file_missing(self):
        item = MagicMock()
        item.filepath = "/nonexistent.mp3"
        problems = self.service().compare_db_file(item)
        assert len(problems) == 1
        assert problems[0].problem_type == "missing_from_db"

    def test_compare_db_file_size_mismatch(self):
        item = MagicMock()
        item.filepath = "/tmp/test.mp3"
        item.size = 99999
        item.mtime = 100.0
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"small")
            tmp = f.name
        try:
            item.filepath = tmp
            problems = FolderIntegrityService().compare_db_file(item)
            assert any(p.problem_type == "size_mismatch" for p in problems)
        finally:
            os.unlink(tmp)


class TestDeepCheck:
    def test_deep_check_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"x" * 1000)
            tmp = f.name
        try:
            result = FolderIntegrityService().check_file(tmp, deep=True)
            assert result.checked_files == 1
        finally:
            os.unlink(tmp)

    def test_deep_check_full_hash(self):
        db = MagicMock()
        db.get_file_signature.return_value = None
        db.ensure_file_hash.return_value = ""
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"x" * 1000)
            tmp = f.name
        try:
            result = FolderIntegrityService(db).deep_check(tmp, hash_full=True)
            assert result.checked_files >= 1
        finally:
            os.unlink(tmp)
