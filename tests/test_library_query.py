from core.library.library_query_service import LibraryQueryService, LibraryQueryError


class TestLibraryQuery:
    def test_create(self):
        svc = LibraryQueryService(db=None)
        assert svc._db is None
