"""End-to-end tests for Audio Lab search filters via SearchEngine."""

from __future__ import annotations

import sqlite3


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            title TEXT,
            artist TEXT,
            album TEXT,
            ext TEXT,
            quality TEXT DEFAULT '',
            analysis_status TEXT DEFAULT '',
            spectral_verdict TEXT DEFAULT '',
            deleted_at REAL
        )
    """)
    rows = [
        ("/music/a.flac", "Song A", "Artist X", "Album 1", "flac", "hires", "done", ""),
        ("/music/b.flac", "Song B", "Artist Y", "Album 1", "flac", "lossless", "done", ""),
        ("/music/c.mp3", "Song C", "Artist Z", "Album 2", "mp3", "lossy", "done", ""),
        ("/music/d.dsf", "Song D", "Artist X", "Album 2", "dsf", "dsd", "done", ""),
        ("/music/e.flac", "Song E", "Artist Y", "Album 3", "flac", "", "pending", ""),
        ("/music/f.wav", "Song F", "Artist Z", "Album 3", "wav", "", "error", ""),
        ("/music/g.wav", "Song G", "Artist X", "Album 4", "wav", "lossless", "done", "SUSPICIOUS_UPSAMPLING"),
        ("/music/h.flac", "Song H", "Artist Y", "Album 4", "flac", "hires", "done", "INCONCLUSIVE"),
        ("/music/i.wav", "Song I", "Artist Z", "Album 5", "wav", "lossless", "done", "POSSIBLE_LOSSY_SOURCE"),
    ]
    for fp, title, artist, album, ext, quality, status, spec in rows:
        conn.execute(
            "INSERT INTO media_items (filepath, title, artist, album, ext, quality, analysis_status, spectral_verdict) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (fp, title, artist, album, ext, quality, status, spec),
        )
    conn.commit()
    return conn


class TestAudioLabSearchFilters:

    def _search(self, query: str) -> list[str]:
        """Run SearchEngine.search() and return list of titles found."""
        from library.search_engine import SearchEngine
        conn = _make_db()
        engine = SearchEngine(conn)
        results = engine.search(query)
        conn.close()
        return [r.get("title", "") for r in results]

    def test_quality_hires(self):
        titles = self._search("quality:hires")
        assert "Song A" in titles
        assert "Song H" in titles
        assert "Song B" not in titles

    def test_quality_lossless(self):
        titles = self._search("quality:lossless")
        assert "Song B" in titles
        assert "Song G" in titles
        assert "Song A" not in titles

    def test_quality_lossy(self):
        titles = self._search("quality:lossy")
        assert "Song C" in titles

    def test_quality_dsd(self):
        titles = self._search("quality:dsd")
        assert "Song D" in titles

    def test_analysis_pending(self):
        titles = self._search("analysis:pending")
        assert "Song E" in titles

    def test_analysis_error(self):
        titles = self._search("analysis:error")
        assert "Song F" in titles

    def test_spectral_suspicious(self):
        titles = self._search("spectral:suspicious")
        assert "Song G" in titles
        assert "Song I" in titles
        assert "Song H" not in titles

    def test_spectral_inconclusive(self):
        titles = self._search("spectral:inconclusive")
        assert "Song H" in titles

    def test_combined_artist_quality(self):
        titles = self._search("artist:Artist quality:hires")
        assert "Song A" in titles
        assert "Song H" in titles
        assert "Song B" not in titles
