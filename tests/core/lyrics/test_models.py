from core.lyrics.models import (
    LyricsDocument, TrackIdentity, LyricsLine, LyricsSource, LyricsStatus, MatchConfidence, LyricsErrorCode,
    compute_track_hash, compute_content_hash,
)


class TestLyricsDocument:
    def test_has_synced_true_with_synced_text(self):
        doc = LyricsDocument(synced_text="[01:00.00]Test")
        assert doc.has_synced is True

    def test_has_synced_true_with_line_timestamps(self):
        doc = LyricsDocument(lines=[LyricsLine(start_ms=1000, text="Test")])
        assert doc.has_synced is True

    def test_has_synced_false(self):
        doc = LyricsDocument(plain_text="Test")
        assert doc.has_synced is False

    def test_has_plain_true(self):
        doc = LyricsDocument(plain_text="Test")
        assert doc.has_plain is True

    def test_has_plain_true_with_lines(self):
        doc = LyricsDocument(lines=[LyricsLine(text="Test")])
        assert doc.has_plain is True

    def test_has_plain_false(self):
        doc = LyricsDocument()
        assert doc.has_plain is False


class TestComputeHash:
    def test_track_hash_deterministic(self):
        id1 = TrackIdentity(title="Song", artist="Artist")
        id2 = TrackIdentity(title="Song", artist="Artist")
        assert compute_track_hash(id1) == compute_track_hash(id2)

    def test_track_hash_different(self):
        id1 = TrackIdentity(title="Song A", artist="Artist")
        id2 = TrackIdentity(title="Song B", artist="Artist")
        assert compute_track_hash(id1) != compute_track_hash(id2)

    def test_content_hash(self):
        h1 = compute_content_hash("Hello World")
        h2 = compute_content_hash("Hello World")
        assert h1 == h2

    def test_content_hash_whitespace(self):
        h1 = compute_content_hash("Hello World  ")
        h2 = compute_content_hash("Hello World")
        assert h1 == h2


class TestLyricsSource:
    def test_values(self):
        assert LyricsSource.EMBEDDED.value == "embedded"
        assert LyricsSource.SIDECAR_LRC.value == "sidecar_lrc"
        assert LyricsSource.REMOTE_PROVIDER.value == "remote_provider"
        assert LyricsSource.MANUAL.value == "manual"


class TestLyricsStatus:
    def test_values(self):
        assert LyricsStatus.IDLE.value == "idle"
        assert LyricsStatus.RESOLVING.value == "resolving"
        assert LyricsStatus.FOUND.value == "found"
        assert LyricsStatus.NOT_FOUND.value == "not_found"


class TestMatchConfidence:
    def test_order(self):
        assert MatchConfidence.EXACT.value == "exact"
        assert MatchConfidence.REJECTED.value == "rejected"


class TestLyricsErrorCode:
    def test_ok(self):
        assert LyricsErrorCode.OK.value == "ok"

    def test_not_found(self):
        assert LyricsErrorCode.NOT_FOUND.value == "not_found"

    def test_cancelled(self):
        assert LyricsErrorCode.CANCELLED.value == "cancelled"
