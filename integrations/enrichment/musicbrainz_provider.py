"""MusicBrainz enrichment provider — combines MusicBrainz + Wikipedia + Cover Art."""
from integrations.enrichment.provider import ArtistEnrichmentProvider
from integrations.musicbrainz.client import MusicBrainzClient
from integrations.wikipedia.client import WikipediaClient
from integrations.coverart.client import CoverArtClient


class MusicBrainzProvider(ArtistEnrichmentProvider):
    """Unified provider using MusicBrainz for metadata, Wikipedia for bios+images,
    and Cover Art Archive for album covers."""

    def __init__(self, parent=None):
        self._mb = MusicBrainzClient(parent)
        self._wiki = WikipediaClient(parent)
        self._cover = CoverArtClient(parent)
        self._pending_bios: dict = {}   # artist_key → callback
        self._pending_images: dict = {}  # artist_key → callback
        self._pending_covers: dict = {}  # album_key → callback

        self._wiki.bio_loaded.connect(self._on_bio_loaded)
        self._wiki.image_url_found.connect(self._on_image_found)
        self._cover.cover_found.connect(self._on_cover_found)

    # ── Metadata ──

    def fetch_metadata(self, artist_key: str, display_name: str,
                        mbid: str = "") -> dict | None:
        """Asynchronous — result via signal. Returns None synchronously."""
        if mbid:
            self._mb.get_artist_by_mbid(mbid)
        else:
            self._mb.search_artist(display_name)

        # We store results via signal — return the cached dict once available
        return None  # Async — real result comes via signal

    # ── Bio ──

    def fetch_bio(self, artist_key: str, display_name: str,
                   lang: str = "es") -> str:
        self._wiki.fetch_bio(artist_key, display_name, lang)
        return ""  # Async — result via signal

    # ── Images ──

    def fetch_images(self, artist_key: str, display_name: str,
                      lang: str = "es") -> dict:
        self._wiki.fetch_image(artist_key, display_name, lang)
        return {}  # Async — result via signal

    # ── Discography ──

    def fetch_discography(self, artist_key: str, mbid: str = "") -> list[dict]:
        if mbid:
            self._mb.get_release_groups(mbid)
        return []  # Async — result via signal

    # ── Callbacks ──

    def _on_bio_loaded(self, artist_key: str, bio: str):
        cb = self._pending_bios.pop(artist_key, None)
        if cb:
            cb(bio)

    def _on_image_found(self, artist_key: str, image_url: str):
        cb = self._pending_images.pop(artist_key, None)
        if cb:
            cb(image_url)

    def _on_cover_found(self, album_key: str, image_url: str):
        cb = self._pending_covers.pop(album_key, None)
        if cb:
            cb(image_url)
