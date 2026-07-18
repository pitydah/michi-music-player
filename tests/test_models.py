"""Tests for canonical models — TrackRef, OperationResult."""
import pytest


class TestTrackRef:
    def test_frozen(self):
        from core.models import TrackRef
        t = TrackRef(track_id=1, filepath="/test/song.flac")
        with pytest.raises(Exception):
            t.filepath = "/other/path.flac"

    def test_defaults(self):
        from core.models import TrackRef
        t = TrackRef()
        assert t.track_id is None
        assert t.filepath == ""
        assert t.title == ""
        assert t.source_type == "local_file"

    def test_to_dict(self):
        from core.models import TrackRef
        t = TrackRef(track_id=42, filepath="/music/song.flac", title="Test", artist="Me")
        d = t.to_dict()
        assert d["track_id"] == 42
        assert d["filepath"] == "/music/song.flac"
        assert d["title"] == "Test"
        assert d["artist"] == "Me"

    def test_from_dict_roundtrip(self):
        from core.models import TrackRef
        t = TrackRef(track_id=1, filepath="/a.flac", title="A", artist="B",
                     album="C", duration=180.0, bitrate=320, sample_rate=44100,
                     format="flac", genre="Rock", year=2020, track_number=1,
                     favorite=True)
        d = t.to_dict()
        t2 = TrackRef(**d)
        assert t2.track_id == t.track_id
        assert t2.filepath == t.filepath
        assert t2.favorite == t.favorite


class TestOperationResult:
    def test_success(self):
        from core.models import OperationResult
        r = OperationResult.success(data={"key": "val"}, message="OK")
        assert r.ok
        assert r.code == "OK"
        assert r.data["key"] == "val"

    def test_fail(self):
        from core.models import OperationResult
        r = OperationResult.fail("ERR", "Something broke", recoverable=True)
        assert not r.ok
        assert r.code == "ERR"
        assert r.recoverable

    def test_to_dict(self):
        from core.models import OperationResult
        r = OperationResult.success(data={"count": 5}, message="Done")
        d = r.to_dict()
        assert d["ok"]
        assert d["code"] == "OK"
        assert d["data"]["count"] == 5

    def test_from_dict_legacy(self):
        from core.models import OperationResult
        legacy = {"ok": True, "result": "played", "error_code": "OK"}
        r = OperationResult.from_dict(legacy)
        assert r.ok
        assert r.code == "OK"

    def test_frozen(self):
        from core.models import OperationResult
        r = OperationResult.success()
        with pytest.raises(Exception):
            r.ok = False
