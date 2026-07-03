"""Tests for Library Health module."""

import tempfile


class TestLibraryHealth:

    def test_compute_health_none_conn_returns_defaults(self):
        from core.audio_lab.library_health import compute_health
        h = compute_health(None)
        assert h["total_tracks"] == 0

    def test_compute_health_with_real_db(self):
        from library.library_db import LibraryDB
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        conn = db._conn
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title) VALUES ('', '', '', '/a.flac', 'a.flac', 'A')")
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, analysis_status, quality) "
                     "VALUES ('', '', '', '/b.flac', 'b.flac', 'B', 'done', 'hires')")
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, analysis_status, spectral_verdict) "
                     "VALUES ('', '', '', '/c.flac', 'c.flac', 'C', 'done', 'SUSPICIOUS_UPSAMPLING')")
        conn.commit()
        from core.audio_lab.library_health import compute_health
        h = compute_health(conn)
        db.close()
        import os
        os.unlink(tmp_name)
        assert h["total_tracks"] >= 3
        assert h["analysed_tracks"] >= 2
        assert h["hires_count"] >= 1
        assert h["spectral_warnings"] >= 1

    def test_compute_health_handles_empty_db(self):
        from library.library_db import LibraryDB
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        from core.audio_lab.library_health import compute_health
        h = compute_health(db._conn)
        db.close()
        os.unlink(tmp_name)
        assert h["total_tracks"] == 0
        assert h["total_size_mb"] == 0.0
        assert h["total_duration_str"] != ""
