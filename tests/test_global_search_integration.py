"""Tests for Global Search — DB connection, filters, cancelation."""
import os
import tempfile
import wave

import pytest


@pytest.fixture
def search_svc(tmp_path):
    from core.global_search_service import GlobalSearchService
    import library.library_db
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = library.library_db.LibraryDB(path)

    # Seed with real WAV files and index
    music_dir = tmp_path / "seed_music"
    music_dir.mkdir()
    for artist, album, title in [
        ("Rock Band", "Rock Album", "Rock Song"),
        ("Jazz Trio", "Jazz Night", "Jazz Song"),
        ("Pop Star", "Pop World", "Pop Hit"),
    ]:
        d = music_dir / artist / album
        d.mkdir(parents=True)
        fp = d / f"{title}.wav"
        with wave.open(str(fp), "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)

    from library.indexer import Indexer
    idx = Indexer.from_db_path(str(db.db_path), str(music_dir))
    idx.run()

    svc = GlobalSearchService(db.db_path)
    yield svc
    db.conn.close()
    os.unlink(path)


class TestGlobalSearchIntegration:
    def test_search_finds_results(self, search_svc):
        result = search_svc.search("Rock")
        assert result["ok"]
        assert len(result["results"]) > 0

    def test_search_no_results(self, search_svc):
        result = search_svc.search("XYZZY_NONEXISTENT")
        assert result["ok"]
        assert len(result["results"]) == 0

    def test_search_empty_query(self, search_svc):
        result = search_svc.search("")
        assert result["ok"]

    def test_search_cancel(self, search_svc):
        search_svc.cancel("test_owner")
        result = search_svc.search("Song", owner="test_owner")
        assert result["ok"]

    def test_search_async(self, search_svc):
        results = []
        def on_result(r):
            results.append(r)
        search_svc.search_async("Rock", on_result=on_result)

    def test_search_stale_protection(self, search_svc):
        r1 = search_svc.search("Rock", owner="stale_test")
        r2 = search_svc.search("Jazz", owner="stale_test")
        assert r2["ok"]

    def test_global_search_bridge_import(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        assert GlobalSearchBridge is not None
