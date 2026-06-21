"""Tests for Indexer / ScanState / BatchWriter."""


class TestScanState:
    def test_initial_state(self):
        from library.index_state import ScanState, ScanPhase
        state = ScanState()
        assert state.phase == ScanPhase.IDLE
        assert state.file_count == 0
        assert state.added_count == 0

    def test_start_resets(self):
        from library.index_state import ScanState, ScanPhase
        state = ScanState()
        state.phase = ScanPhase.WRITING
        state.added_count = 100
        state.start("/test")
        assert state.phase == ScanPhase.WALKING
        assert state.added_count == 0
        assert state.root_path == "/test"

    def test_finish(self):
        from library.index_state import ScanState, ScanPhase
        state = ScanState()
        state.finish()
        assert state.phase == ScanPhase.DONE
        assert state.progress_pct == 100.0

    def test_cancel(self):
        from library.index_state import ScanState, ScanPhase
        state = ScanState()
        state.cancel()
        assert state.phase == ScanPhase.CANCELLED
        assert state.cancelled is True

    def test_to_dict(self):
        from library.index_state import ScanState
        state = ScanState()
        state.start("/test", file_count=50)
        d = state.to_dict()
        assert d["phase"] == "walking"
        assert d["root_path"] == "/test"
        assert d["file_count"] == 50


class TestBatchWriter:
    def test_init_empty(self, mock_window):
        db = mock_window._db
        from library.batch_writer import BatchWriter
        writer = BatchWriter(db._conn)
        assert writer.buffered == 0
        assert writer.total_written == 0

    def test_add_buffers(self, mock_window):
        db = mock_window._db
        from library.batch_writer import BatchWriter
        writer = BatchWriter(db._conn, batch_size=5)
        rec = {"filepath": "/test.mp3", "filename": "test.mp3",
               "directory": "/", "ext": ".mp3", "kind": "audio",
               "size": 0, "mtime": 0.0, "duration": 0.0,
               "channels": 0, "sample_rate": 0, "bitrate": 0,
               "title": "test", "artist": "", "album": "",
               "albumartist": "", "year": 0, "genre": "",
               "track_number": 0, "track_total": 0,
               "disc_number": 0, "disc_total": 0, "composer": "",
               "mb_track_id": "", "mb_album_id": "",
               "mb_albumartist_id": "", "bit_depth": 0, "bpm": 0,
               "replaygain_track": 0.0, "replaygain_album": 0.0}
        writer.add(rec)
        assert writer.buffered == 1

    def test_default_for_string(self, mock_window):
        from library.batch_writer import BatchWriter
        assert BatchWriter._default_for({}, "title") == ""

    def test_default_for_numeric(self, mock_window):
        from library.batch_writer import BatchWriter
        assert BatchWriter._default_for({}, "year") == 0

    def test_default_for_float(self, mock_window):
        from library.batch_writer import BatchWriter
        assert BatchWriter._default_for({}, "replaygain_track") == 0.0
