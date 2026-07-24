"""Tests for ArtistExternalInfo dataclass and Wikipedia extraction."""

from unittest.mock import patch

from integrations.artist_metadata.models import ArtistExternalInfo


class TestArtistExternalInfo:

    def test_artist_info_structure(self):
        info = ArtistExternalInfo(
            provider="musicbrainz",
            artist_id="mbid_123",
            name="Test Artist",
            mbid="mbid_123",
            biography="Full bio",
            biography_en="English bio",
            biography_es="Biografía en español",
            genre="Rock",
            style="Prog",
            mood="Energetic",
            country="UK",
            formed_year="1970",
            website="https://example.com",
            facebook="https://facebook.com/test",
            twitter="https://twitter.com/test",
            thumb_url="https://example.com/thumb.jpg",
            clearart_url="https://example.com/clearart.png",
            logo_url="https://example.com/logo.png",
            banner_url="https://example.com/banner.jpg",
            fanart_urls=["https://example.com/fanart1.jpg"],
            thumb_path="/cache/thumb.jpg",
            banner_path="/cache/banner.jpg",
            logo_path="/cache/logo.png",
            fanart_paths=["/cache/fanart1.jpg"],
            source_url="https://musicbrainz.org/artist/mbid_123",
            last_updated="2024-01-15",
        )
        assert info.provider == "musicbrainz"
        assert info.artist_id == "mbid_123"
        assert info.name == "Test Artist"
        assert info.mbid == "mbid_123"
        assert info.biography == "Full bio"
        assert info.biography_en == "English bio"
        assert info.biography_es == "Biografía en español"
        assert info.genre == "Rock"
        assert info.style == "Prog"
        assert info.mood == "Energetic"
        assert info.country == "UK"
        assert info.formed_year == "1970"
        assert info.website == "https://example.com"
        assert info.facebook == "https://facebook.com/test"
        assert info.twitter == "https://twitter.com/test"
        assert info.thumb_url == "https://example.com/thumb.jpg"
        assert info.clearart_url == "https://example.com/clearart.png"
        assert info.logo_url == "https://example.com/logo.png"
        assert info.banner_url == "https://example.com/banner.jpg"
        assert info.fanart_urls == ["https://example.com/fanart1.jpg"]
        assert info.source_url == "https://musicbrainz.org/artist/mbid_123"
        assert info.last_updated == "2024-01-15"

    def test_biography_preferred_spanish_first(self):
        info = ArtistExternalInfo(
            biography_en="English only",
            biography_es="Español primero",
        )
        assert info.biography_preferred == "Español primero"

    def test_biography_preferred_fallback_english(self):
        info = ArtistExternalInfo(biography_en="English bio")
        assert info.biography_preferred == "English bio"

    def test_biography_preferred_fallback_generic(self):
        info = ArtistExternalInfo(biography="Generic bio")
        assert info.biography_preferred == "Generic bio"

    def test_biography_preferred_empty(self):
        info = ArtistExternalInfo()
        assert info.biography_preferred == ""

    def test_has_any_data_true(self):
        info = ArtistExternalInfo(biography="Some bio")
        assert info.has_any_data

    def test_has_any_data_with_thumb(self):
        info = ArtistExternalInfo(thumb_url="http://example.com/thumb.jpg")
        assert info.has_any_data

    def test_has_any_data_false(self):
        info = ArtistExternalInfo()
        assert not info.has_any_data

    @patch("integrations.artist_metadata.artist_enrichment_service.ArtistEnrichmentService")
    def test_artist_wikipedia_extraction(self, MockEnrichment):
        service = MockEnrichment.return_value
        service.enrich_artist.return_value = ArtistExternalInfo(
            artist_id="wiki_123",
            name="Pink Floyd",
            biography_en=(
                "Pink Floyd were an English rock band formed in London in 1965. "
                "They achieved international acclaim with progressive and psychedelic music."
            ),
            biography_es=(
                "Pink Floyd fue una banda de rock inglesa formada en Londres en 1965. "
                "Alcanzaron reconocimiento internacional con su música progresiva y psicodélica."
            ),
            genre="Progressive Rock",
            country="UK",
            formed_year="1965",
            website="https://pinkfloyd.com",
            source_url="https://en.wikipedia.org/wiki/Pink_Floyd",
        )
        result = service.enrich_artist("pink_floyd")
        assert result.name == "Pink Floyd"
        assert "English rock band" in result.biography_en
        assert "banda de rock inglesa" in result.biography_es
        assert result.genre == "Progressive Rock"
        assert result.country == "UK"
        assert result.formed_year == "1965"
        assert result.website == "https://pinkfloyd.com"
