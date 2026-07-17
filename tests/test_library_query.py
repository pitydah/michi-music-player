from core.library.library_query_service import LibraryQueryService, LibraryQueryError


class TestLibraryQuery:
    def test_create(self):
        svc = LibraryQueryService(db=None)
        assert svc._db is None

    def test_query_tracks_empty_db(self):
        svc = LibraryQueryService(db=None)
        result = svc.query_tracks(limit=10)
        assert result == []
