"""Tests for Metadata Doctor module."""

import tempfile


class TestMetadataDoctor:

    def test_suggest_normalizations_none_conn(self):
        from core.audio_lab.metadata_doctor import suggest_normalizations
        s = suggest_normalizations(None)
        assert s == []

    def test_suggest_empty_title(self):
        from library.library_db import LibraryDB
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        conn = db._conn
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, artist) "
                     "VALUES ('', '', '', '/song.flac', 'song.flac', '', 'Artist')")
        conn.commit()
        from core.audio_lab.metadata_doctor import suggest_normalizations
        s = suggest_normalizations(conn)
        db.close()
        os.unlink(tmp_name)
        assert any(x["field"] == "title" for x in s)

    def test_suggest_invalid_year(self):
        from library.library_db import LibraryDB
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        conn = db._conn
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, year) "
                     "VALUES ('', '', '', '/song.flac', 'song.flac', 'Song', 9999)")
        conn.commit()
        from core.audio_lab.metadata_doctor import suggest_normalizations
        s = suggest_normalizations(conn)
        db.close()
        os.unlink(tmp_name)
        assert any(x["field"] == "year" for x in s)

    def test_suggest_empty_genre(self):
        from library.library_db import LibraryDB
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        conn = db._conn
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, genre) "
                     "VALUES ('', '', '', '/song.flac', 'song.flac', 'Song', '')")
        conn.commit()
        from core.audio_lab.metadata_doctor import suggest_normalizations
        s = suggest_normalizations(conn)
        db.close()
        os.unlink(tmp_name)
        assert any(x["field"] == "genre" for x in s)
