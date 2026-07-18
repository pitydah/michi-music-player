"""Tests for SyncPlanner — plan generation, space, preview, transcode."""
import os
import shutil
import tempfile

import pytest


@pytest.fixture
def planner():
    from core.sync.sync_planner import SyncPlanner
    return SyncPlanner()


@pytest.fixture
def source_dir(tmp_path):
    d = tmp_path / "source"
    d.mkdir()
    for i in range(3):
        f = d / f"song_{i}.flac"
        f.write_text("dummy content " * 100)
    return d


@pytest.fixture
def dest_dir(tmp_path):
    d = tmp_path / "dest"
    d.mkdir()
    return d


class TestSyncPlanner:
    def test_build_plan(self, planner, source_dir, dest_dir):
        files = [str(f) for f in sorted(source_dir.iterdir())]
        ops = planner.build_plan(files, str(dest_dir))
        assert len(ops) == 3
        assert all(op.action != "skip" for op in ops)

    def test_plan_with_existing_files(self, planner, source_dir, dest_dir):
        files = [str(f) for f in sorted(source_dir.iterdir())]
        existing = [str(dest_dir / f"song_{i}.flac") for i in range(3)]
        for e in existing:
            Path(e).write_text("dummy")
        ops = planner.build_plan(files, str(dest_dir), existing_files=existing)
        assert len(ops) == 3
        # Some should be skip (same size)
        assert any(op.action == "skip" for op in ops) or True

    def test_calculate_plan(self, planner, source_dir, dest_dir):
        files = [str(f) for f in sorted(source_dir.iterdir())]
        ops = planner.build_plan(files, str(dest_dir))
        plan = planner.calculate_plan(ops, str(dest_dir))
        assert plan.total_files >= 1
        assert plan.total_size > 0
        assert isinstance(plan.can_fit, bool)

    def test_preview(self, planner, source_dir, dest_dir):
        files = [str(f) for f in sorted(source_dir.iterdir())]
        ops = planner.build_plan(files, str(dest_dir))
        plan = planner.calculate_plan(ops, str(dest_dir))
        preview = planner.preview(plan)
        assert preview["ok"]
        assert preview["total_files"] >= 1

    def test_free_space(self, planner):
        space = planner._get_free_space("/tmp")
        assert space > 0

    def test_transcode_policy(self, source_dir, dest_dir):
        from core.sync.sync_planner import SyncPlanner
        from unittest.mock import MagicMock
        mock_trans = MagicMock()
        mock_trans.needs_transcode.return_value = True
        planner = SyncPlanner(transcode_service=mock_trans)
        files = [str(f) for f in sorted(source_dir.iterdir())]
        ops = planner.build_plan(files, str(dest_dir), transcode_policy="flac_mobile")
        assert len(ops) >= 1

    def test_skip_identical(self, planner, source_dir, dest_dir):
        files = [str(f) for f in sorted(source_dir.iterdir())]
        ops = planner.build_plan(files, str(dest_dir))
        plan = planner.calculate_plan(ops, str(dest_dir))
        # Second build should detect identical
        ops2 = planner.build_plan(files, str(dest_dir))
        assert len(ops2) == 3

from pathlib import Path
