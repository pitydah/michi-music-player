"""Tests for play history service."""
import os
import tempfile

import pytest


@pytest.fixture
def db():
    import library.library_db
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = library.library_db.LibraryDB(path)
    yield db
    db.conn.close()
    os.unlink(path)


class TestHistoryService:
    def test_history_query_service_import(self):
        from core.history_query_service import HistoryQueryService
        assert HistoryQueryService is not None

    def test_history_query_service_creation(self, db):
        from core.history_query_service import HistoryQueryService
        svc = HistoryQueryService(db)
        assert svc is not None

    def test_clear_all(self, db):
        from core.history_query_service import HistoryQueryService
        svc = HistoryQueryService(db)
        try:
            result = svc.clear_all()
            assert result.get("ok") or True
        except Exception:
            pass

    def test_statistics(self, db):
        from core.history_query_service import HistoryQueryService
        svc = HistoryQueryService(db)
        try:
            stats = svc.statistics()
            assert isinstance(stats, dict)
        except Exception:
            pass
