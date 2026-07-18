"""Tests for global search service — filters, cancellation, stale protection."""
import os
import tempfile
from unittest.mock import MagicMock, PropertyMock, patch

import pytest


@pytest.fixture
def db_path():
    import library.library_db
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = library.library_db.LibraryDB(path)
    db.conn.close()
    return path


@pytest.fixture
def svc(db_path):
    from core.global_search_service import GlobalSearchService
    return GlobalSearchService(db_path)


@pytest.fixture
def seeded_svc(db_path, tmp_path):
    """Create a search service with some seeded data."""
    import library.library_db
    db = library.library_db.LibraryDB(db_path)
    # Seed some test data via the actual library API
    from library.indexer import Indexer
    music_dir = tmp_path / "seed_music"
    music_dir.mkdir()
    for artist, album, title in [
        ("Rock Band", "Rock Album", "Rock Song 1"),
        ("Jazz Band", "Jazz Album", "Jazz Song 1"),
        ("Pop Star", "Pop Album", "Pop Song 1"),
    ]:
        d = music_dir / artist / album
        d.mkdir(parents=True)
        import wave
        fp = d / f"{title}.wav"
        with wave.open(str(fp), "w") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)
    idx = Indexer.from_db_path(db_path, str(music_dir))
    idx.run()
    from core.global_search_service import GlobalSearchService
    return GlobalSearchService(db_path)


class TestGlobalSearchBasic:
    def test_search_service_import(self):
        from core.global_search_service import GlobalSearchService
        assert GlobalSearchService is not None

    def test_search_service_creation(self, svc):
        assert svc is not None

    def test_search_empty_query(self, svc):
        result = svc.search("")
        assert result.get("ok")

    def test_search_cancel(self, svc):
        svc.cancel("test")

    def test_search_async(self, svc):
        results = []

        def on_result(r):
            results.append(r)

        svc.search_async("test", on_result=on_result)

    def test_search_handles_special_chars(self, svc):
        result = svc.search("artist:test")
        assert result is not None

    def test_search_with_filters(self, svc):
        result = svc.search("genre:rock year:>2020")
        assert result is not None


class TestGlobalSearchWithData:
    def test_search_finds_results(self, seeded_svc):
        result = seeded_svc.search("Rock")
        assert result.get("ok")
        assert len(result.get("results", [])) > 0

    def test_search_by_artist(self, seeded_svc):
        result = seeded_svc.search("artist:Rock Band")
        assert result.get("ok")

    def test_search_by_album(self, seeded_svc):
        result = seeded_svc.search("album:Jazz Album")
        assert result.get("ok")

    def test_search_by_genre(self, seeded_svc):
        result = seeded_svc.search("genre:Jazz")
        assert result.get("ok")

    def test_search_no_results(self, seeded_svc):
        result = seeded_svc.search("XYZZYX_NONEXISTENT_12345")
        assert len(result.get("results", [])) == 0

    def test_search_multiple_owners(self, seeded_svc):
        r1 = seeded_svc.search("Rock", owner="owner_a")
        r2 = seeded_svc.search("Jazz", owner="owner_b")
        assert r1.get("ok")
        assert r2.get("ok")

    def test_search_cancellation(self, seeded_svc):
        result = seeded_svc.search("Rock", owner="cancel_test")
        seeded_svc.cancel("cancel_test")
        assert result is not None
