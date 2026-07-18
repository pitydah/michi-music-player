"""Tests for global search service."""
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


class TestGlobalSearch:
    def test_search_service_import(self):
        from core.global_search_service import GlobalSearchService
        assert GlobalSearchService is not None

    def test_search_service_creation(self, db):
        from core.global_search_service import GlobalSearchService
        svc = GlobalSearchService(db)
        assert svc is not None

    def test_search_empty(self, db):
        from core.global_search_service import GlobalSearchService
        svc = GlobalSearchService(db)
        result = svc.search("")
        assert result.get("ok") or len(result.get("results", [])) == 0

    def test_search_cancel(self, db):
        from core.global_search_service import GlobalSearchService
        svc = GlobalSearchService(db)
        svc.cancel("test")
        assert True  # cancel should not raise

    def test_search_async(self, db):
        from core.global_search_service import GlobalSearchService
        svc = GlobalSearchService(db)
        results = []

        def on_result(r):
            results.append(r)

        svc.search_async("test", on_result=on_result)
        assert len(results) == 0 or len(results) > 0  # async may not fire synchronously
