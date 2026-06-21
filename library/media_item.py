"""MediaItem — dataclass representing a single track in the library."""
from dataclasses import dataclass

from library.metadata_extractor import AUDIO_EXTS


def media_kind(ext: str) -> str:
    return "audio" if ext.lower() in AUDIO_EXTS else "unknown"


@dataclass
class MediaItem:
    id: int = 0
    filepath: str = ""
    filename: str = ""
    directory: str = ""
    ext: str = ""
    kind: str = ""
    size: int = 0
    mtime: float = 0.0
    duration: float = 0.0
    channels: int = 0
    sample_rate: int = 0
    bitrate: int = 0
    title: str = ""
    artist: str = ""
    album: str = ""
    year: int = 0
    genre: str = ""
    track_number: int = 0
    composer: str = ""
    albumartist: str = ""
    disc_number: int = 0
    disc_total: int = 0
    track_total: int = 0
    mb_track_id: str = ""
    mb_album_id: str = ""
    mb_albumartist_id: str = ""
    bit_depth: int = 0
    bpm: int = 0

    @property
    def display_title(self) -> str:
        if self.artist and self.title:
            return f"{self.artist} — {self.title}"
        return self.title or self.filename

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return ""
        m = int(self.duration // 60)
        s = int(self.duration % 60)
        if self.duration >= 3600:
            h = int(self.duration // 3600)
            m = int((self.duration % 3600) // 60)
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @classmethod
    def from_row(cls, row: tuple) -> "MediaItem":
        return cls(
            id=row[0], filepath=row[1], filename=row[2], directory=row[3],
            ext=row[4] or "", kind=row[5] or "", size=row[6] or 0,
            mtime=row[7] or 0.0, duration=row[8] or 0.0,
            channels=row[9] or 0, sample_rate=row[10] or 0,
            bitrate=row[11] or 0, title=row[12] or "",
            artist=str(row[13]) if row[13] else "",
            album=str(row[14]) if row[14] else "",
            year=row[15] if len(row) > 15 and row[15] else 0,
            genre=row[16] if len(row) > 16 and row[16] else "",
            track_number=row[17] if len(row) > 17 and row[17] else 0,
            composer=row[18] if len(row) > 18 and row[18] else "",
            albumartist=str(row[19]) if len(row) > 19 and row[19] else "",
            disc_number=row[20] if len(row) > 20 and row[20] else 0,
            disc_total=row[21] if len(row) > 21 and row[21] else 0,
            track_total=row[22] if len(row) > 22 and row[22] else 0,
            mb_track_id=str(row[23]) if len(row) > 23 and row[23] else "",
            mb_album_id=str(row[24]) if len(row) > 24 and row[24] else "",
            mb_albumartist_id=str(row[25]) if len(row) > 25 and row[25] else "",
            bit_depth=row[26] if len(row) > 26 and row[26] else 0,
            bpm=row[27] if len(row) > 27 and row[27] else 0,
        )
