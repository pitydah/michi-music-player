"""Tests for MetadataResolver — local scoring, merging, and lookups."""
import pytest

from ui.audio_lab.models import DiscMetadata, TrackMetadata
from ui.audio_lab.services.metadata_resolver import MetadataResolver


class TestMetadataResolver:
    @pytest.fixture
    def resolver(self):
        return MetadataResolver()

    # ── Confidence ──

    def test_confidence_full_match(self, resolver):
        candidate = DiscMetadata(
            artist="Test Artist",
            album="Test Album",
            year=2024,
            genre="Rock",
            tracks=[
                TrackMetadata(track_number=1, title="Track One", duration=200.0),
                TrackMetadata(track_number=2, title="Track Two", duration=180.0),
                TrackMetadata(track_number=3, title="Track Three", duration=220.0),
            ],
        )
        disc_info = {
            "track_count": 3,
            "total_duration": 600.0,
        }
        conf = resolver.calculate_confidence(candidate, disc_info)
        assert conf >= 0.70

    def test_confidence_empty_candidate(self, resolver):
        conf = resolver.calculate_confidence(DiscMetadata(), {})
        assert conf == 0.0

    def test_confidence_no_tracks_low(self, resolver):
        candidate = DiscMetadata(artist="A", album="B")
        disc_info = {"track_count": 10, "total_duration": 3000}
        conf = resolver.calculate_confidence(candidate, disc_info)
        assert conf == 0.30  # artist + album only

    def test_confidence_track_count_mismatch(self, resolver):
        candidate = DiscMetadata(
            artist="A", album="B",
            tracks=[TrackMetadata(track_number=1, title="T1", duration=100)],
        )
        disc_info = {"track_count": 10, "total_duration": 3000}
        conf = resolver.calculate_confidence(candidate, disc_info)
        # Artist(0.15) + album(0.15) + track ratio(0.1*0.25) + title(1.0*0.20) + duration ratio(0.033*0.15)
        assert conf < 0.55

    def test_confidence_duration_match(self, resolver):
        candidate = DiscMetadata(
            artist="A", album="B",
            tracks=[
                TrackMetadata(track_number=1, title="T1", duration=500),
                TrackMetadata(track_number=2, title="T2", duration=500),
            ],
        )
        disc_info = {"track_count": 2, "total_duration": 1000}
        conf = resolver.calculate_confidence(candidate, disc_info)
        assert conf >= 0.70

    # ── Merge ──

    def test_merge_best_wins(self, resolver):
        c1 = DiscMetadata(artist="Artist1", album="Album1", confidence=0.8, source="src1")
        c2 = DiscMetadata(artist="Artist2", album="Album2", confidence=0.3, source="src2")
        result = resolver.merge_metadata_candidates([c1, c2])
        assert result.artist == "Artist1"
        assert result.album == "Album1"
        assert result.confidence == 0.8

    def test_merge_fills_gaps(self, resolver):
        c1 = DiscMetadata(artist="Artist1", album="", confidence=0.8, source="src1")
        c2 = DiscMetadata(artist="", album="Album2", year=2024, confidence=0.5, source="src2")
        result = resolver.merge_metadata_candidates([c1, c2])
        assert result.artist == "Artist1"
        assert result.album == "Album2"
        assert result.year == 2024

    def test_merge_does_not_overwrite(self, resolver):
        c1 = DiscMetadata(artist="Good", album="Good", confidence=0.8, source="src1")
        c2 = DiscMetadata(artist="", album="Bad", year=0, confidence=0.3, source="src2")
        result = resolver.merge_metadata_candidates([c1, c2])
        assert result.artist == "Good"
        assert result.album == "Good"

    def test_merge_empty_list(self, resolver):
        result = resolver.merge_metadata_candidates([])
        assert result.artist == ""

    def test_merge_track_titles_filled(self, resolver):
        c1 = DiscMetadata(
            confidence=0.8,
            tracks=[
                TrackMetadata(track_number=1, title="Title1", duration=100),
                TrackMetadata(track_number=2, title="", duration=200),
            ],
        )
        c2 = DiscMetadata(
            confidence=0.5,
            tracks=[
                TrackMetadata(track_number=1, title="Other", duration=100),
                TrackMetadata(track_number=2, title="Title2", duration=200),
            ],
        )
        result = resolver.merge_metadata_candidates([c1, c2])
        assert result.tracks[0].title == "Title1"  # not overwritten
        assert result.tracks[1].title == "Title2"  # filled from c2

    # ── Artist/Album ──

    def test_find_artist_album_returns_metadata(self, resolver):
        result = resolver.find_album_by_artist_album("The Artist", "Great Album")
        assert result is not None
        assert result.artist == "The Artist"
        assert result.album == "Great Album"
        assert result.confidence == 0.55
        assert result.source == "artist_album"

    def test_find_artist_album_empty_artist(self, resolver):
        result = resolver.find_album_by_artist_album("", "Album")
        assert result is None

    def test_find_artist_album_empty_album(self, resolver):
        result = resolver.find_album_by_artist_album("Artist", "")
        assert result is None

    def test_find_artist_album_strips_whitespace(self, resolver):
        result = resolver.find_album_by_artist_album("  Artist  ", "  Album  ")
        assert result.artist == "Artist"
        assert result.album == "Album"

    # ── TOC ──

    def test_toc_with_tracks(self, resolver):
        toc = {
            "track_count": 3,
            "tracks": [
                {"length_sectors": 15000},
                {"length_sectors": 18000},
                {"length_sectors": 12000},
            ],
        }
        result = resolver.find_album_by_disc_toc(toc)
        assert result is not None
        assert len(result.tracks) == 3
        assert result.tracks[0].duration == 200.0  # 15000/75
        assert result.source == "toc_local"
        assert result.confidence > 0.15

    def test_toc_empty(self, resolver):
        result = resolver.find_album_by_disc_toc({})
        assert result is None

    def test_toc_no_tracks(self, resolver):
        result = resolver.find_album_by_disc_toc({"track_count": 0})
        assert result is None

    def test_toc_confidence_increases_with_tracks(self, resolver):
        toc1 = {"track_count": 2, "tracks": [{}, {}]}
        toc2 = {"track_count": 12, "tracks": [{}] * 12}
        r1 = resolver.find_album_by_disc_toc(toc1)
        r2 = resolver.find_album_by_disc_toc(toc2)
        assert r2.confidence > r1.confidence
