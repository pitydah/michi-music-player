import pytest
import tempfile
import os

from core.radio.models import (
    StationCreateRequest, StationUpdateRequest,
)
from infrastructure.radio.station_repository import SqliteStationRepository


@pytest.fixture
def repo():
    _, path = tempfile.mkstemp(suffix=".db")
    repo = SqliteStationRepository(path, clock=lambda: "2024-01-01T00:00:00")
    repo.initialize()
    yield repo
    os.unlink(path)


class TestSqliteStationRepository:
    def test_add_and_get(self, repo):
        req = StationCreateRequest(name="Test Radio", stream_url="https://example.com/stream")
        station = repo.add(req)
        assert station.id > 0
        assert station.name == "Test Radio"

        got = repo.get(station.id)
        assert got is not None
        assert got.name == "Test Radio"

    def test_get_nonexistent(self, repo):
        assert repo.get(999) is None

    def test_update(self, repo):
        req = StationCreateRequest(name="Old", stream_url="https://example.com/stream")
        station = repo.add(req)
        updated = repo.update(station.id, StationUpdateRequest(name="New"))
        assert updated is not None
        assert updated.name == "New"

    def test_update_nonexistent(self, repo):
        assert repo.update(999, StationUpdateRequest(name="X")) is None

    def test_delete(self, repo):
        req = StationCreateRequest(name="Test", stream_url="https://example.com/stream")
        station = repo.add(req)
        assert repo.delete(station.id) is True
        assert repo.get(station.id) is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete(999) is False

    def test_count(self, repo):
        assert repo.count() == 0
        repo.add(StationCreateRequest(name="A", stream_url="https://a.com/stream"))
        repo.add(StationCreateRequest(name="B", stream_url="https://b.com/stream"))
        assert repo.count() == 2

    def test_list_all_pagination(self, repo):
        for i in range(10):
            repo.add(StationCreateRequest(name=f"S{i}", stream_url=f"https://s{i}.com/stream"))
        page1 = repo.list_all(page=1, page_size=3)
        assert len(page1.items) == 3
        assert page1.total == 10
        assert page1.pages == 4

    def test_search(self, repo):
        repo.add(StationCreateRequest(name="Rock FM", stream_url="https://rock.fm/stream"))
        repo.add(StationCreateRequest(name="Jazz FM", stream_url="https://jazz.fm/stream"))
        repo.add(StationCreateRequest(name="Classical", stream_url="https://classical.fm/stream"))
        result = repo.search("Rock")
        assert len(result.items) == 1
        assert result.items[0].name == "Rock FM"

    def test_search_by_country(self, repo):
        repo.add(StationCreateRequest(name="RNE", stream_url="https://rne.es/stream", country="Spain"))
        result = repo.search("Spain")
        assert len(result.items) == 1

    def test_find_by_url(self, repo):
        req = StationCreateRequest(name="Test", stream_url="https://example.com/stream")
        repo.add(req)
        found = repo.find_by_url("https://example.com/stream")
        assert found is not None
        assert found.name == "Test"

    def test_find_by_url_normalized(self, repo):
        req = StationCreateRequest(name="Test", stream_url="https://Example.COM/Stream")
        repo.add(req)
        found = repo.find_by_url("https://example.com/Stream")
        assert found is not None

    def test_set_favorite(self, repo):
        req = StationCreateRequest(name="Test", stream_url="https://example.com/stream")
        station = repo.add(req)
        assert repo.set_favorite(station.id, True) is True
        got = repo.get(station.id)
        assert got.favorite == 1  # SQLite stores bool as INTEGER

    def test_list_favorites(self, repo):
        a = repo.add(StationCreateRequest(name="A", stream_url="https://a.com/stream"))
        repo.add(StationCreateRequest(name="B", stream_url="https://b.com/stream"))
        repo.set_favorite(a.id, True)
        result = repo.list_favorites()
        assert len(result.items) == 1
        assert result.items[0].id == a.id

    def test_mark_played(self, repo):
        station = repo.add(StationCreateRequest(name="Test", stream_url="https://example.com/stream"))
        repo.mark_played(station.id)
        got = repo.get(station.id)
        assert got.play_count == 1
        assert got.last_played_at != ""

    def test_list_recent(self, repo):
        a = repo.add(StationCreateRequest(name="A", stream_url="https://a.com/stream"))
        repo.add(StationCreateRequest(name="B", stream_url="https://b.com/stream"))
        repo.mark_played(a.id)
        recent = repo.list_recent()
        assert len(recent) == 1
        assert recent[0].id == a.id

    def test_bulk_add(self, repo):
        stations = [
            StationCreateRequest(name=f"S{i}", stream_url=f"https://s{i}.com/stream")
            for i in range(5)
        ]
        count = repo.bulk_add(stations, mode="best_effort")
        assert count == 5
        assert repo.count() == 5

    def test_bulk_add_deduplicates(self, repo):
        repo.add(StationCreateRequest(name="Existing", stream_url="https://example.com/stream"))
        stations = [
            StationCreateRequest(name="New", stream_url="https://example.com/stream"),
            StationCreateRequest(name="Other", stream_url="https://other.com/stream"),
        ]
        count = repo.bulk_add(stations, mode="best_effort")
        assert count == 1

    def test_get_all_for_export(self, repo):
        for i in range(3):
            repo.add(StationCreateRequest(name=f"S{i}", stream_url=f"https://s{i}.com/stream"))
        exported = repo.get_all_for_export()
        assert len(exported) == 3

    def test_soft_delete_not_in_lists(self, repo):
        station = repo.add(StationCreateRequest(name="Test", stream_url="https://example.com/stream"))
        repo.delete(station.id)
        assert repo.count() == 0
        assert len(repo.list_all().items) == 0

    def test_duplicate_url_returns_same(self, repo):
        req = StationCreateRequest(name="First", stream_url="https://example.com/stream")
        a = repo.add(req)
        req2 = StationCreateRequest(name="Second", stream_url="https://example.com/stream")
        b = repo.add(req2)
        assert a.id == b.id

    def test_update_probe(self, repo):
        station = repo.add(StationCreateRequest(name="Test", stream_url="https://example.com/stream"))
        repo.update_probe(station.id, "valid", "2024-01-01T00:00:00")
        got = repo.get(station.id)
        assert got.last_probe_status == "valid"

    def test_sort_by_bitrate(self, repo):
        for i in [128, 320, 192]:
            repo.add(StationCreateRequest(
                name=f"Radio {i}", stream_url=f"https://r{i}.com/stream", bitrate=i,
            ))
        result = repo.list_all(sort_by="bitrate", sort_dir="desc")
        assert result.items[0].bitrate == 320
        assert result.items[-1].bitrate == 128
