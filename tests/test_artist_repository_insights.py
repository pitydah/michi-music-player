"""Tests for ArtistRepository insight methods."""
from legacy_widgets.ui.controllers.legacy_controllers.artist_repository import ArtistRepository
from library.library_db import MediaItem


def _make_item(**kw):
    defaults = dict(
        id=0, filepath="/tmp/track.flac", filename="track.flac",
        directory="/tmp", ext="flac", kind="audio",
        size=0, mtime=0.0, duration=200.0,
        channels=2, sample_rate=44100, bitrate=1000,
        title="Test", artist="Test Artist", album="Test Album",
        year=2020, genre="Rock",
        track_number=1, composer="",
        albumartist="", disc_number=1, disc_total=1, track_total=10,
        mb_track_id="", mb_album_id="", mb_albumartist_id="",
        bit_depth=16, bpm=120, isrc="", label="",
        conductor="", compilation=0, media_type="",
        encoder="", copyright="", originaldate="",
        remixer="", grouping="", mood="",
        replaygain_track=0.0, replaygain_album=0.0,
        replaygain_track_peak=0.0,
        play_count=5, last_played=0.0, rating=0,
        created_at=0.0, updated_at=0.0, last_scanned=0.0,
        track_uid="",
    )
    defaults.update(kw)
    return MediaItem(**defaults)


class TestArtistRepositoryInsights:
    def setup_method(self):
        self.repo = ArtistRepository()

    def test_insight_after_build(self):
        items = [_make_item()]
        self.repo.build(items)
        insight = self.repo.insight_for_artist("test artist")
        assert insight is not None
        assert insight.display_name == "Test Artist"
        assert insight.quality.total_tracks == 1

    def test_insight_for_missing_key(self):
        self.repo.build([_make_item()])
        assert self.repo.insight_for_artist("nonexistent") is None

    def test_quality_summary(self):
        self.repo.build([_make_item()])
        q = self.repo.quality_summary_for_artist("test artist")
        assert q is not None
        assert q.lossless_count == 1

    def test_metadata_health(self):
        self.repo.build([_make_item()])
        h = self.repo.metadata_health_for_artist("test artist")
        assert h is not None

    def test_collaborations_empty(self):
        self.repo.build([_make_item()])
        c = self.repo.collaborations_for_artist("test artist")
        assert c == []

    def test_artists_with_external_info(self):
        self.repo.build([_make_item()])
        assert self.repo.artists_with_external_info() == []

    def test_artists_by_quality(self):
        items = [
            _make_item(ext="flac", filepath="/tmp/a.flac"),
            _make_item(ext="mp3", filepath="/tmp/b.mp3"),
        ]
        self.repo.build(items)
        ranked = self.repo.artists_by_quality()
        assert len(ranked) > 0

    def test_invalidate_insights(self):
        self.repo.build([_make_item()])
        self.repo.invalidate_insights()
        insight = self.repo.insight_for_artist("test artist")
        assert insight is not None
