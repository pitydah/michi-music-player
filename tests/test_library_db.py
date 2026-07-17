import tempfile
import os
from library.library_db import LibraryDB


class TestLibraryDB:
    def test_create_in_memory(self):
        db = LibraryDB(":memory:")
        assert db is not None

    def test_create_temp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            db = LibraryDB(path)
            assert db.conn is not None
        finally:
            os.unlink(path)
