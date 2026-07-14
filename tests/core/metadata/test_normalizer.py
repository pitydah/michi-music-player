from core.metadata.normalizer import MetadataNormalizer
from core.metadata.models import TrackMetadata, MetadataDocument


class TestMetadataNormalizer:
    def test_normalize_title_trim(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(title="  Hello World  "))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.title == "Hello World"

    def test_normalize_collapse_spaces(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(title="Hello   World"))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.title == "Hello World"

    def test_normalize_artist_list(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(artists=["  Artist One  ", "Artist Two"]))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.artists[0] == "Artist One"

    def test_isrc_uppercased(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(isrc="usabc1234567"))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.isrc == "USABC1234567"

    def test_mbid_lowercased(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(musicbrainz_recording_id="MBID-1234"))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.musicbrainz_recording_id == "mbid-1234"

    def test_release_year_from_date(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(date="2024"))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.release_year == 2024

    def test_release_year_kept_if_set(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(date="2024", release_year=2023))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.release_year == 2023

    def test_genre_normalization(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(genres=["  Rock  ", "Pop  "]))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.genres == ["Rock", "Pop"]

    def test_unicode_nfc(self):
        normalizer = MetadataNormalizer()
        doc = MetadataDocument(track=TrackMetadata(title="Caf\u00e9"))
        normalized = normalizer.normalize_document(doc)
        assert normalized.track.title == "Caf\u00e9"
