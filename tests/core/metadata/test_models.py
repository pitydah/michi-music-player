from core.metadata.models import (
    TrackMetadata, TechnicalMetadata, MetadataOperationResult, TrackIdentity,
    compute_file_signature,
)
from core.metadata.enums import (
    MetadataErrorCode, FieldOperation, BackupPolicy, ReviewStatus,
)


class TestTrackMetadata:
    def test_defaults(self):
        t = TrackMetadata()
        assert t.title == ""
        assert t.artists == []
        assert t.track_number is None

    def test_with_values(self):
        t = TrackMetadata(title="Song", artists=["Artist"],
                          track_number=1, isrc="USABC1234567")
        assert t.title == "Song"
        assert t.artists == ["Artist"]
        assert t.track_number == 1


class TestTechnicalMetadata:
    def test_defaults(self):
        t = TechnicalMetadata()
        assert t.container == ""
        assert t.lossless is False

    def test_immutable_like(self):
        t = TechnicalMetadata(duration_ms=240000, bitrate=320000)
        assert t.duration_ms == 240000
        assert t.bitrate == 320000


class TestMetadataOperationResult:
    def test_ok_default(self):
        r = MetadataOperationResult()
        assert r.ok is True
        assert r.code == "ok"

    def test_error(self):
        r = MetadataOperationResult(
            ok=False, code=MetadataErrorCode.FILE_NOT_FOUND.value,
        )
        assert r.ok is False
        assert r.retryable is False


class TestBackupPolicy:
    def test_values(self):
        assert BackupPolicy.NONE.value == "none"
        assert BackupPolicy.FULL_FILE_BACKUP.value == "full_file_backup"


class TestFieldOperation:
    def test_values(self):
        assert FieldOperation.SET.value == "set"
        assert FieldOperation.APPEND.value == "append"
        assert FieldOperation.CLEAR.value == "clear"


class TestReviewStatus:
    def test_values(self):
        assert ReviewStatus.DRAFT.value == "draft"
        assert ReviewStatus.APPLIED.value == "applied"
        assert ReviewStatus.ROLLED_BACK.value == "rolled_back"


class TestTrackIdentity:
    def test_defaults(self):
        i = TrackIdentity()
        assert i.library_track_id == ""
        assert i.filepath == ""

    def test_with_values(self):
        i = TrackIdentity(
            library_track_id="lib-1",
            filepath="/music/song.flac",
            title="Song",
            artists=["Artist"],
        )
        assert i.library_track_id == "lib-1"
        assert len(i.artists) == 1


class TestComputeFileSignature:
    def test_nonexistent_file(self):
        sig = compute_file_signature("/nonexistent/file.flac")
        assert sig == ""
