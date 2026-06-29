"""Semantic audit: events, payloads, context_repository isolation."""

import subprocess
from pathlib import Path


class TestContextSemanticAudit:

    def test_context_repository_not_imported_by_ui(self):
        src = Path(__file__).resolve().parent.parent
        ui_dir = src / "ui"
        result = subprocess.run(
            ["rg", "-l", "context_repository", str(ui_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode in (0, 1), "ripgrep failed"
        files = result.stdout.strip().splitlines()
        files = [f for f in files if f and "__pycache__" not in f]
        assert len(files) == 0, (
            f"context_repository imported in UI files: {files}"
        )

    def test_context_repository_not_imported_by_controllers(self):
        src = Path(__file__).resolve().parent.parent
        ctrl_dir = src / "core"
        result = subprocess.run(
            ["rg", "-l", "context_repository", str(ctrl_dir / "playback_controller.py")],
            capture_output=True, text=True, timeout=30,
        )
        files = result.stdout.strip().splitlines()
        files = [f for f in files if f and "__pycache__" not in f]
        assert len(files) == 0

    def test_no_absolute_paths_in_event_payloads(self):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(":memory:")
        svc = ContextService()

        for fp in ("/home/user/file.flac", "/tmp/private/song.flac", "C:\\Users\\me\\file.flac"):
            svc.record_event("test_event", {"filepath": fp})
        events = repo.recent_events(limit=10)
        raw = str(events)
        assert "filepath" not in raw, "filepath leaked into event payload"
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "C:\\" not in raw

    def test_update_selection_includes_scope(self):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(":memory:")
        repo.close()
        svc = ContextService()

        svc.update_selection(album="TestAlbum")
        state = svc.get_selection_state()
        assert state.get("selection_scope") == "album"
