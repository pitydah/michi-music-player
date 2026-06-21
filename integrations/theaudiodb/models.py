"""TheAudioDB data models."""
from dataclasses import dataclass, field


@dataclass
class ArtistExternalInfo:
    provider: str = "theaudiodb"
    artist_id: str = ""
    name: str = ""
    mbid: str = ""
    biography: str = ""
    biography_en: str = ""
    biography_es: str = ""
    genre: str = ""
    style: str = ""
    mood: str = ""
    country: str = ""
    formed_year: str = ""
    website: str = ""
    facebook: str = ""
    twitter: str = ""
    thumb_url: str = ""
    clearart_url: str = ""
    logo_url: str = ""
    banner_url: str = ""
    fanart_urls: list[str] = field(default_factory=list)
    thumb_path: str = ""
    banner_path: str = ""
    logo_path: str = ""
    fanart_paths: list[str] = field(default_factory=list)
    source_url: str = ""
    last_updated: str = ""

    @property
    def biography_preferred(self) -> str:
        """Return best biography: Spanish first, then English."""
        return self.biography_es or self.biography_en or self.biography or ""

    @property
    def has_any_data(self) -> bool:
        return bool(self.name or self.biography or self.thumb_url or self.genre)
