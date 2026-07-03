"""Tests for Backup Manifest module."""

import tempfile


class TestBackupManifest:

    def test_generate_manifest_none_conn(self):
        from core.audio_lab.backup_manifest import generate_manifest
        m = generate_manifest(None)
        assert m == []

    def test_generate_manifest_with_real_db(self):
        from library.library_db import LibraryDB
        import os
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_name = tmp.name
        db = LibraryDB(tmp_name)
        conn = db._conn
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, artist) "
                     "VALUES ('', '', '', '/a.flac', 'a.flac', 'A', 'X')")
        conn.execute("INSERT INTO media_items (directory, ext, kind, filepath, filename, title, artist) "
                     "VALUES ('', '', '', '/b.flac', 'b.flac', 'B', 'Y')")
        conn.commit()
        from core.audio_lab.backup_manifest import generate_manifest
        m = generate_manifest(conn)
        db.close()
        os.unlink(tmp_name)
        assert len(m) == 2
        assert m[0]["filepath"] == "/a.flac"
        assert m[1]["filepath"] == "/b.flac"
        assert "sha256" in m[0]
        assert "format" in m[0]

    def test_manifest_to_json(self):
        from core.audio_lab.backup_manifest import manifest_to_json
        m = [{"filepath": "/a.flac", "title": "A"}]
        j = manifest_to_json(m)
        assert '"filepath"' in j
        assert '"title"' in j

    def test_manifest_to_csv(self):
        from core.audio_lab.backup_manifest import manifest_to_csv
        m = [{"filepath": "/a.flac", "title": "A"}]
        c = manifest_to_csv(m)
        assert "filepath" in c
        assert "title" in c

    def test_manifest_to_csv_empty(self):
        from core.audio_lab.backup_manifest import manifest_to_csv
        assert manifest_to_csv([]) == ""
