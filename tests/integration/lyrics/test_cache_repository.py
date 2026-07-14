import pytest
import tempfile
import os

from core.lyrics.models import (
    LyricsDocument, TrackIdentity, LyricsLine, MatchConfidence,
    LyricsSource, LyricsAttribution,
)
from infrastructure.lyrics.cache_repository import SqliteLyricsCacheRepository


@pytest.fixture
def repo():
    _, path = tempfile.mkstemp(suffix=".db")
    os.unlink(path)
    repo = SqliteLyricsCacheRepository(path, clock=lambda: "2024-01-01T00:00:00")
    repo.initialize()
    yield repo
    os.unlink(path)


class TestSqliteLyricsCacheRepository:
    def test_positive_hit(self, repo):
        doc = LyricsDocument(
            plain_text="Hello World",
            identity=TrackIdentity(title="Song"),
        )
        repo.put("test:key", doc)
        cached = repo.get("test:key")
        assert cached is not None
        assert cached.plain_text == "Hello World"

    def test_negative_hit(self, repo):
        repo.put_negative("test:missing")
        assert repo.get_negative("test:missing") is True

    def test_negative_miss(self, repo):
        assert repo.get_negative("test:nonexistent") is False

    def test_miss_on_wrong_key(self, repo):
        doc = LyricsDocument(plain_text="Test")
        repo.put("key:a", doc)
        assert repo.get("key:b") is None

    def test_expiration(self, repo):
        repo_pos = SqliteLyricsCacheRepository(
            repo._db_path, clock=lambda: "2024-01-01T00:00:00",
            positive_ttl_s=1,
        )
        repo_pos.initialize()
        doc = LyricsDocument(plain_text="Test")
        repo_pos.put("exp:key", doc)

        repo_exp = SqliteLyricsCacheRepository(
            repo._db_path, clock=lambda: "2024-01-02T00:00:00",
        )
        repo_exp.initialize()
        assert repo_exp.get("exp:key") is None

    def test_invalidate(self, repo):
        doc = LyricsDocument(plain_text="Test")
        repo.put("inv:key", doc)
        assert repo.get("inv:key") is not None
        repo.invalidate("inv:key")
        assert repo.get("inv:key") is None

    def test_invalidate_all(self, repo):
        repo.put("k1", LyricsDocument(plain_text="A"))
        repo.put("k2", LyricsDocument(plain_text="B"))
        repo.invalidate_all()
        assert repo.get("k1") is None
        assert repo.get("k2") is None

    def test_round_trip_preserves_data(self, repo):
        doc = LyricsDocument(
            plain_text="Line one\nLine two",
            synced_text="[01:00.00]Line one\n[02:00.00]Line two",
            lines=[
                LyricsLine(line_id="0", start_ms=60000, end_ms=120000, text="Line one"),
                LyricsLine(line_id="1", start_ms=120000, text="Line two"),
            ],
            identity=TrackIdentity(title="Test Song", artist="Test Artist"),
            source=LyricsSource.REMOTE_PROVIDER,
            provider_id="lrclib",
            provider_item_id="123",
            language="en",
            match_confidence=MatchConfidence.EXACT,
            duration_ms=240000,
            offset_ms=0,
            attribution=LyricsAttribution(source_label="lrclib.net", provider_url="https://lrclib.net"),
        )
        repo.put("full:doc", doc)
        cached = repo.get("full:doc")
        assert cached is not None
        assert cached.plain_text == "Line one\nLine two"
        assert len(cached.lines) == 2
        assert cached.identity.title == "Test Song"
        assert cached.provider_id == "lrclib"
        assert cached.match_confidence == MatchConfidence.EXACT

    def test_concurrent_readers_dont_crash(self, repo):
        import threading
        errors = []

        def worker():
            try:
                for i in range(10):
                    repo.put(f"c:{i}", LyricsDocument(plain_text=f"Test {i}"))
                    repo.get(f"c:{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_persistence_across_instances(self, repo):
        doc = LyricsDocument(plain_text="Persist me")
        repo.put("persist:key", doc)

        repo2 = SqliteLyricsCacheRepository(repo._db_path, clock=lambda: "2024-01-01T00:00:00")
        repo2.initialize()
        cached = repo2.get("persist:key")
        assert cached is not None
        assert cached.plain_text == "Persist me"
