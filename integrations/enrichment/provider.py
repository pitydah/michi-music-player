"""Artist enrichment provider interface (ABC)."""
from abc import ABC, abstractmethod


class ArtistEnrichmentProvider(ABC):
    """Abstract provider for enriching artist metadata, images, and biography."""

    @abstractmethod
    def fetch_metadata(self, artist_key: str, display_name: str,
                        mbid: str = "") -> dict | None:
        """Fetch artist metadata. Returns dict or None.
        Must include: provider, name, genre, country, formed_year, mbid, thumb_url."""
        ...

    @abstractmethod
    def fetch_bio(self, artist_key: str, display_name: str,
                   lang: str = "es") -> str:
        """Fetch artist biography in the requested language."""
        ...

    @abstractmethod
    def fetch_images(self, artist_key: str, display_name: str,
                      lang: str = "es") -> dict:
        """Fetch image URLs. Returns dict with keys: thumb_url, banner_url, logo_url."""
        ...

    @abstractmethod
    def fetch_discography(self, artist_key: str, mbid: str = "") -> list[dict]:
        """Fetch album discography. Returns list of dicts with: id, title, year, type."""
        ...
