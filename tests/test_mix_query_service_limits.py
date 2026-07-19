from __future__ import annotations

from core.mix_query_service import MixQueryService


TRACK_ROW = (1, "Track", "Artist", "Album", "album-key", 180)
QUALITY_ROW = (*TRACK_ROW, 921)


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None


class RecordingConnection:
    def __init__(self):
        self.calls: list[tuple[str, list]] = []

    def execute(self, sql, params=None):
        values = list(params or [])
        self.calls.append((sql, values))
        if "AS bucket" in sql:
            return FakeCursor([(1990,)])
        if "m.bitrate" in sql:
            return FakeCursor([QUALITY_ROW])
        return FakeCursor([TRACK_ROW])


class FakeDb:
    def __init__(self):
        self.conn = RecordingConnection()


def _service():
    db = FakeDb()
    return MixQueryService(db), db.conn


def test_by_field_binds_filter_and_limit_once():
    service, conn = _service()

    result = service.by_field("artist", "Artist", limit=25)

    assert result[0]["track_id"] == 1
    sql, params = conn.calls[-1]
    assert sql.rstrip().endswith("LIMIT ?")
    assert sql.count("LIMIT ?") == 1
    assert params == ["Artist", 25]


def test_by_field_without_value_only_binds_limit():
    service, conn = _service()

    service.by_field("genre", limit=10)

    sql, params = conn.calls[-1]
    assert "m.genre IS NOT NULL" in sql
    assert params == [10]


def test_random_decade_uses_bucket_then_bounded_query():
    service, conn = _service()

    result = service.by_decade(limit=12)

    assert result
    assert len(conn.calls) == 2
    sql, params = conn.calls[-1]
    assert "m.year >= ? AND m.year < ?" in sql
    assert params == [1990, 2000, 12]


def test_random_year_uses_bucket_then_bounded_query():
    service, conn = _service()

    service.by_year(limit=7)

    sql, params = conn.calls[-1]
    assert "m.year = ?" in sql
    assert params == [1990, 7]


def test_high_quality_returns_selected_bitrate():
    service, conn = _service()

    result = service.high_quality(min_bitrate=320, limit=15)

    assert result[0]["bitrate"] == 921
    sql, params = conn.calls[-1]
    assert sql.rstrip().endswith("LIMIT ?")
    assert params == [320, 15]


def test_limit_is_clamped_to_safe_range():
    service, conn = _service()

    service.recent(limit=100_000)

    assert conn.calls[-1][1] == [500]
