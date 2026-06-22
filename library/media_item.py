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
    isrc: str = ""
    label: str = ""
    conductor: str = ""
    compilation: int = 0
    media_type: str = ""
    encoder: str = ""
    copyright: str = ""
    originaldate: str = ""
    remixer: str = ""
    grouping: str = ""
    mood: str = ""
    replaygain_track: float = 0.0
    replaygain_album: float = 0.0
    replaygain_track_peak: float = 0.0
    play_count: int = 0
    last_played: float = 0.0
    rating: int = 0

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
        def _s(idx, default=""):
            v = row[idx] if len(row) > idx else None
            return str(v) if v is not None else default
        def _i(idx, default=0):
            v = row[idx] if len(row) > idx else None
            if v is None or v == "":
                return default
            try:
                return int(float(v)) if isinstance(v, str) else int(v)
            except (ValueError, TypeError):
                return default
        def _f(idx, default=0.0):
            v = row[idx] if len(row) > idx else None
            if v is None or v == "":
                return default
            try:
                return float(v)
            except (ValueError, TypeError):
                return default

        return cls(
            id=_i(0), filepath=_s(1), filename=_s(2), directory=_s(3),
            ext=_s(4), kind=_s(5), size=_i(6),
            mtime=_f(7), duration=_f(8),
            channels=_i(9), sample_rate=_i(10),
            bitrate=_i(11), title=_s(12),
            artist=_s(13), album=_s(14),
            year=_i(15), genre=_s(16),
            track_number=_i(17), composer=_s(18),
            albumartist=_s(19), disc_number=_i(20),
            disc_total=_i(21), track_total=_i(22),
            mb_track_id=_s(23), mb_album_id=_s(24),
            mb_albumartist_id=_s(25), bit_depth=_i(26),
            bpm=_i(27), isrc=_s(28), label=_s(29),
            conductor=_s(30), compilation=_i(31),
            media_type=_s(32), encoder=_s(33),
            copyright=_s(34), originaldate=_s(35),
            remixer=_s(36), grouping=_s(37),
            mood=_s(38), replaygain_track=_f(39),
            replaygain_album=_f(40), replaygain_track_peak=_f(41),
            play_count=_i(42), last_played=_f(43),
            rating=_i(44),
        )

    @classmethod
    def from_dict(cls, d: dict) -> "MediaItem":
        return cls(
            id=d.get("id", 0),
            filepath=d.get("filepath", ""),
            filename=d.get("filename", ""),
            directory=d.get("directory", ""),
            ext=d.get("ext", ""),
            kind=d.get("kind", ""),
            size=d.get("size", 0),
            mtime=d.get("mtime", 0.0),
            duration=d.get("duration", 0.0),
            channels=d.get("channels", 0),
            sample_rate=d.get("sample_rate", 0),
            bitrate=d.get("bitrate", 0),
            title=d.get("title", ""),
            artist=str(d.get("artist") or ""),
            album=str(d.get("album") or ""),
            year=d.get("year", 0),
            genre=d.get("genre", ""),
            track_number=d.get("track_number", 0),
            composer=d.get("composer", ""),
            albumartist=str(d.get("albumartist") or ""),
            disc_number=d.get("disc_number", 0),
            disc_total=d.get("disc_total", 0),
            track_total=d.get("track_total", 0),
            mb_track_id=str(d.get("mb_track_id") or ""),
            mb_album_id=str(d.get("mb_album_id") or ""),
            mb_albumartist_id=str(d.get("mb_albumartist_id") or ""),
            bit_depth=d.get("bit_depth", 0),
            bpm=d.get("bpm", 0),
            isrc=str(d.get("isrc") or ""),
            label=str(d.get("label") or ""),
            conductor=str(d.get("conductor") or ""),
            compilation=d.get("compilation", 0),
            media_type=str(d.get("media_type") or ""),
            encoder=str(d.get("encoder") or ""),
            copyright=str(d.get("copyright") or ""),
            originaldate=str(d.get("originaldate") or ""),
            remixer=str(d.get("remixer") or ""),
            grouping=str(d.get("grouping") or ""),
            mood=str(d.get("mood") or ""),
            replaygain_track=d.get("replaygain_track", 0.0),
            replaygain_album=d.get("replaygain_album", 0.0),
            replaygain_track_peak=d.get("replaygain_track_peak", 0.0),
            play_count=d.get("play_count", 0),
            last_played=d.get("last_played", 0.0),
            rating=d.get("rating", 0),
        )
