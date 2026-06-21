"""Album Summary — lightweight dataclass for album info banner."""
from dataclasses import dataclass


@dataclass
class AlbumSummary:
    album_key: str = ""
    title: str = ""
    artist: str = ""
    year: str = ""
    genre: str = ""
    style: str = ""
    mood: str = ""
    description: str = ""
    track_count: int = 0
    duration: float = 0.0
    cover_path: str = ""
    thumb_path: str = ""
    fanart_path: str = ""
    source: str = "local"
    match_confidence: float = 0.0
    updated_at: str = ""
    dominant_color: str = ""
    track_list: list = None

    def __post_init__(self):
        if self.track_list is None:
            self.track_list = []
