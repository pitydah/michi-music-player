import sqlite3
from core.audio_lab.audio_lab_sync import sync_audio_lab_cache_to_media_items, _ensure_columns


class TestAudioLabSync:
    def test_ensure_columns_in_memory(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, title TEXT)")
        _ensure_columns(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(media_items)").fetchall()}
        assert "quality" in cols
        conn.close()

    def test_sync_cache_empty(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, title TEXT, quality TEXT)")
        result = sync_audio_lab_cache_to_media_items(conn)
        assert result is not None
        conn.close()
