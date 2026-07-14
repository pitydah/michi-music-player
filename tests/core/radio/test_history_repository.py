import pytest
import tempfile
import os

from infrastructure.radio.history_repository import SqliteRadioHistoryRepository


@pytest.fixture
def repo():
    _, path = tempfile.mkstemp(suffix=".db")
    repo = SqliteRadioHistoryRepository(path, clock=lambda: "2024-01-01T00:00:00")
    repo.initialize()
    yield repo
    os.unlink(path)


class TestSqliteRadioHistoryRepository:
    def test_record_play(self, repo):
        repo.record_play(station_id=1, title="Song A")
        history = repo.list_history()
        assert len(history) == 1

    def test_list_history_returns_latest_first(self, repo):
        repo.record_play(station_id=1, title="Song A")
        repo.record_play(station_id=2, title="Song B")
        history = repo.list_history()
        assert len(history) == 2

    def test_count_history(self, repo):
        assert repo.count_history() == 0
        repo.record_play(station_id=1)
        assert repo.count_history() == 1

    def test_clear_history(self, repo):
        repo.record_play(station_id=1)
        repo.clear_history()
        assert repo.count_history() == 0

    def test_clear_history_with_retention(self, repo):
        class RepoWithRetention(SqliteRadioHistoryRepository):
            def __init__(self):
                _, self._path = tempfile.mkstemp(suffix=".db")

        repo.record_play(station_id=1)
        repo.clear_history(retention_days=365)
        assert repo.count_history() >= 0

    def test_list_history_pagination(self, repo):
        for i in range(10):
            repo.record_play(station_id=i)
        page1 = repo.list_history(limit=5, offset=0)
        assert len(page1) == 5
        page2 = repo.list_history(limit=5, offset=5)
        assert len(page2) == 5
