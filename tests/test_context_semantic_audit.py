"""Semantic audit: events, payloads, context_repository isolation."""

import os
from pathlib import Path

_EXCLUDED_DIRS = {
    "__pycache__", "audio_lab", "vinyl",
}


def _check_file(p: Path, pattern: str) -> bool:
    if any(excl in str(p) for excl in _EXCLUDED_DIRS):
        return False
    text = p.read_text(encoding="utf-8", errors="ignore")
    return pattern in text


class TestContextSemanticAudit:

    def teardown_method(self):
        from core.context import context_repository as repo
        repo.close()
        repo.override_db_path(None)

    def _path(self, tmp_path):
        return os.path.join(str(tmp_path), "ctx.sqlite")

    def test_context_repository_not_imported_by_ui(self):
        src = Path(__file__).resolve().parent.parent
        for p in (src / "ui").rglob("*.py"):
            if _check_file(p, "context_repository"):
                assert False, f"{p} imports context_repository"

    def test_context_repository_not_imported_by_controllers(self):
        src = Path(__file__).resolve().parent.parent
        for p in (src / "ui" / "controllers").rglob("*.py"):
            if _check_file(p, "context_repository"):
                assert False, f"{p} imports context_repository"
        for p in (src / "ui" / "routers").rglob("*.py"):
            if _check_file(p, "context_repository"):
                assert False, f"{p} imports context_repository"

    def test_playback_controller_no_context_repository(self):
        src = Path(__file__).resolve().parent.parent
        text = (src / "core" / "playback_controller.py").read_text(
            encoding="utf-8", errors="ignore")
        assert "context_repository" not in text

    def test_no_absolute_paths_in_event_payloads(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(self._path(tmp_path))
        svc = ContextService()

        for fp in ("/home/user/file.flac", "/tmp/private/song.flac", "C:\\Users\\me\\file.flac"):
            svc.record_event("test_event", {"filepath": fp})
        events = repo.recent_events(limit=10)
        raw = str(events)
        assert "filepath" not in raw, "filepath leaked into event payload"
        assert "/home/" not in raw
        assert "/tmp/" not in raw
        assert "C:\\" not in raw

    def test_record_event_sanitizes_payload(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(self._path(tmp_path))
        svc = ContextService()

        svc.record_event("x", {"filepath": "/home/user/a.flac", "safe": "ok"})
        events = repo.recent_events(limit=5)
        payload = events[0]["payload"]
        assert "filepath" not in payload
        assert payload.get("safe") == "ok"

    def test_update_selection_includes_scope(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(self._path(tmp_path))
        svc = ContextService()

        svc.update_selection(album="TestAlbum")
        state = svc.get_selection_state()
        assert state.get("selection_scope") == "album"

    def test_update_selection_sanitizes_folder_path(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(self._path(tmp_path))
        svc = ContextService()

        svc.update_selection(scope="folder", folder_name="/home/user/Music/Rock")
        state = svc.get_selection_state()
        assert state.get("folder_name") == "Rock"
        assert "/home/" not in str(state)

    def test_selection_state_no_absolute_paths(self, tmp_path):
        from core.context import context_repository as repo
        from core.context.context_service import ContextService

        repo.override_db_path(self._path(tmp_path))
        svc = ContextService()

        svc.update_selection(scope="folder", folder_name="/home/user/Music")
        snap = svc.get_assistant_snapshot()
        raw = str(snap)
        assert "/home/" not in raw

    def test_controllers_use_semantic_methods(self):
        src = Path(__file__).resolve().parent.parent
        violations = []
        for p in (src / "ui" / "controllers").rglob("*.py"):
            if _check_file(p, "context_repository"):
                violations.append(f"{p}: context_repository")
            if _check_file(p, "ctx.record_event("):
                violations.append(f"{p}: ctx.record_event(")

        for p in (src / "ui" / "routers").rglob("*.py"):
            if _check_file(p, "context_repository"):
                violations.append(f"{p}: context_repository")
            if _check_file(p, "ctx.record_event("):
                violations.append(f"{p}: ctx.record_event(")

        assert not violations, "\n".join(violations)
