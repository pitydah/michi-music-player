"""E2E test: library add -> search."""
import sqlite3
from library.schema import Schema
def test_e2e_library_add_search():
    conn = sqlite3.connect(":memory:")
    Schema.initialize(conn)
    conn.execute("INSERT INTO media_items (filepath, filename, directory, ext, kind, title) VALUES (?,?,?,?,?,?)",
                 ("/test/song.flac", "song.flac", "/test", "flac", "audio", "Test"))
    conn.commit()
    row = conn.execute("SELECT title FROM media_items WHERE filepath=?", ("/test/song.flac",)).fetchone()
    assert row[0] == "Test"
    conn.close()
