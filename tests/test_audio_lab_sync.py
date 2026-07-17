import sqlite3
from core.audio_lab.audio_lab_sync import sync_quality_to_db, _ensure_columns


class TestAudioLabSync:
    def test_ensure_columns_in_memory(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, title TEXT)")
        _ensure_columns(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(media_items)").fetchall()}
        assert "quality" in cols
        conn.close()

    def test_sync_quality_empty(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, title TEXT, quality TEXT)")
        result = sync_quality_to_db(conn, changes={})
        assert result is not None
        conn.close()
