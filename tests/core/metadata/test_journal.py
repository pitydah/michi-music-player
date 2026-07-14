import pytest
import tempfile
import os

from core.metadata.journal import MetadataJournalRepository
from core.metadata.models import JournalEntry
from core.metadata.enums import JournalStatus


@pytest.fixture
def repo():
    _, path = tempfile.mkstemp(suffix=".db")
    os.unlink(path)
    repo = MetadataJournalRepository(path, clock=lambda: "2024-01-01T00:00:00")
    repo.initialize()
    yield repo
    os.unlink(path)


class TestMetadataJournalRepository:
    def test_create_entry(self, repo):
        entry = JournalEntry(
            operation_id="op-1",
            target="/music/song.flac",
            status=JournalStatus.PLANNED,
            started_at="2024-01-01T00:00:00",
        )
        result = repo.create(entry)
        assert result.ok is True

    def test_get_entry(self, repo):
        entry = JournalEntry(
            operation_id="op-2",
            target="/music/song.flac",
            status=JournalStatus.PLANNED,
            started_at="2024-01-01T00:00:00",
        )
        repo.create(entry)
        loaded = repo.get("op-2")
        assert loaded is not None
        assert loaded.operation_id == "op-2"
        assert loaded.status == JournalStatus.PLANNED

    def test_get_nonexistent(self, repo):
        assert repo.get("nonexistent") is None

    def test_update_status(self, repo):
        repo.create(JournalEntry(
            operation_id="op-3", target="/music/song.flac",
            status=JournalStatus.PLANNED, started_at="2024-01-01T00:00:00",
        ))
        repo.update_status("op-3", JournalStatus.COMPLETED, after_signature="sig-abc")
        loaded = repo.get("op-3")
        assert loaded.status == JournalStatus.COMPLETED
        assert loaded.after_signature == "sig-abc"

    def test_update_rollback(self, repo):
        repo.create(JournalEntry(
            operation_id="op-4", target="/music/song.flac",
            status=JournalStatus.FAILED, started_at="2024-01-01T00:00:00",
        ))
        repo.update_rollback("op-4", "rolled_back")
        loaded = repo.get("op-4")
        assert loaded.rollback_status == "rolled_back"

    def test_list_by_batch(self, repo):
        for i in range(3):
            repo.create(JournalEntry(
                operation_id=f"op-b{i}", batch_id="batch-1",
                target=f"/music/song{i}.flac",
                status=JournalStatus.PLANNED, started_at="2024-01-01T00:00:00",
            ))
        entries = repo.list_by_batch("batch-1")
        assert len(entries) == 3

    def test_list_recent(self, repo):
        for i in range(5):
            repo.create(JournalEntry(
                operation_id=f"op-r{i}", target="/music/song.flac",
                status=JournalStatus.PLANNED, started_at="2024-01-01T00:00:00",
            ))
        entries = repo.list_recent(limit=3)
        assert len(entries) == 3

    def test_count_by_status(self, repo):
        repo.create(JournalEntry(
            operation_id="op-c1", target="/music/song.flac",
            status=JournalStatus.COMPLETED, started_at="2024-01-01T00:00:00",
        ))
        repo.create(JournalEntry(
            operation_id="op-c2", target="/music/song2.flac",
            status=JournalStatus.COMPLETED, started_at="2024-01-01T00:00:00",
        ))
        repo.create(JournalEntry(
            operation_id="op-c3", target="/music/song3.flac",
            status=JournalStatus.FAILED, started_at="2024-01-01T00:00:00",
        ))
        assert repo.count_by_status(JournalStatus.COMPLETED) == 2
        assert repo.count_by_status(JournalStatus.FAILED) == 1
