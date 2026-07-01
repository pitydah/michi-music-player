"""Tests for SafeFileOperations — move/rename with preflight and DB update."""

import os
import shutil
import tempfile
from unittest.mock import MagicMock

from library.folder_models import FolderMovePlan
from core.safe_file_ops import SafeFileOperations


class TestPlanMove:
    def ops(self, db=None):
        return SafeFileOperations(db=db)

    def test_move_file_plan(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        try:
            dst_dir = tempfile.mkdtemp()
            dst = os.path.join(dst_dir, "moved.mp3")
            plan = self.ops().plan_move(tmp, dst)
            assert plan.can_proceed is True
            assert plan.files_to_move == 1
            assert plan.is_rename is False
        finally:
            os.unlink(tmp)
            if os.path.exists(dst):
                os.unlink(dst)
            if 'dst_dir' in dir() and os.path.exists(dst_dir):
                os.rmdir(dst_dir)

    def test_rename_file_plan(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        base = os.path.basename(tmp)
        dst = os.path.join(os.path.dirname(tmp), "renamed_" + base)
        try:
            plan = self.ops().plan_move(tmp, dst)
            assert plan.can_proceed is True
            assert plan.is_rename is True
        finally:
            os.unlink(tmp)
            if os.path.exists(dst):
                os.unlink(dst)

    def test_move_nonexistent(self):
        plan = self.ops().plan_move("/nonexistent", "/other")
        assert plan.can_proceed is False
        assert plan.warnings

    def test_move_to_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp1 = f.name
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp2 = f.name
        try:
            plan = self.ops().plan_move(tmp1, tmp2)
            assert plan.can_proceed is False
            assert plan.conflicts
        finally:
            os.unlink(tmp1)
            os.unlink(tmp2)

    def test_move_folder_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "song.flac"), "w").close()
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            open(os.path.join(tmpdir, "sub", "track.mp3"), "w").close()
            dst = tmpdir + "_moved"
            try:
                plan = self.ops().plan_move(tmpdir, dst)
                assert plan.can_proceed is True
                assert plan.files_to_move == 2
                assert plan.folders_to_move >= 1
            finally:
                if os.path.exists(dst):
                    shutil.rmtree(dst)

    def test_move_db_impacts(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [5]
        db.conn.execute.return_value.fetchall.return_value = [("My Playlist",)]
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = tmpdir + "_moved"
            db.get_library_roots.return_value = [os.path.dirname(tmpdir)]
            plan = self.ops(db).plan_move(tmpdir, dst)
            assert plan.affected_media_items == 5
            assert "My Playlist" in plan.affected_playlists


class TestExecuteMove:
    def test_move_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        dst = tmp + ".moved"
        try:
            plan = SafeFileOperations().plan_move(tmp, dst)
            result = SafeFileOperations().execute_move(plan)
            assert result.success is True
            assert result.files_moved >= 1
            assert os.path.exists(dst)
            assert not os.path.exists(tmp)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
            if os.path.exists(dst):
                os.unlink(dst)

    def test_move_file_with_db(self):
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = None
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        dst = tmp + ".moved"
        try:
            plan = SafeFileOperations(db).plan_move(tmp, dst)
            result = SafeFileOperations(db).execute_move(plan)
            assert result.success is True
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
            if os.path.exists(dst):
                os.unlink(dst)

    def test_move_nonexistent_plan(self):
        plan = FolderMovePlan(source="/x", destination="/y", can_proceed=True)
        result = SafeFileOperations().execute_move(plan)
        assert result.success is False

    def test_rollback_on_db_failure(self):
        db = MagicMock()
        db.conn.execute.side_effect = Exception("DB error")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(b"data")
            tmp = f.name
        dst = tmp + ".moved"
        try:
            plan = SafeFileOperations(db).plan_move(tmp, dst)
            result = SafeFileOperations(db).execute_move(plan)
            # Move may have succeeded, DB fails, rollback attempted
            assert result.files_moved >= 1
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
            if os.path.exists(dst):
                os.unlink(dst)


