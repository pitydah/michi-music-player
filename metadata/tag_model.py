"""Track tags data model — in-memory representation for the metadata editor."""
from dataclasses import dataclass, field


@dataclass
class TrackTags:
    filepath: str
    title: str = ""
    artist: str = ""
    album: str = ""
    albumartist: str = ""
    tracknumber: str = ""
    tracktotal: str = ""
    discnumber: str = ""
    disctotal: str = ""
    date: str = ""
    genre: str = ""
    composer: str = ""
    comment: str = ""
    lyrics: str = ""
    bpm: str = ""
    isrc: str = ""
    musicbrainz_trackid: str = ""
    musicbrainz_albumid: str = ""

    # Technical info (read-only)
    kind: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 0
    duration: float = 0.0
    filesize: int = 0
    file_mtime: float = 0.0

    has_artwork: bool = False
    artwork_mime: str = ""
    artwork_data: bytes | None = None

    # State
    dirty: bool = False
    dirty_fields: set[str] = field(default_factory=set)
    artwork_dirty: bool = False
    error: str = ""
    original: "TrackTags | None" = None

    TEXT_FIELDS = [
        "title", "artist", "album", "albumartist",
        "tracknumber", "tracktotal", "discnumber", "disctotal",
        "date", "genre", "composer", "comment", "lyrics",
        "bpm", "isrc", "musicbrainz_trackid", "musicbrainz_albumid",
    ]

    def set_field(self, field: str, value) -> bool:
        """Set a field value, tracking dirty state. Returns True if changed."""
        old = getattr(self, field, "")
        if str(old) != str(value):
            setattr(self, field, value)
            self.dirty = True
            self.dirty_fields.add(field)
            return True
        return False

    def mark_dirty(self, field: str | None = None):
        self.dirty = True
        if field:
            self.dirty_fields.add(field)

    def mark_artwork_dirty(self):
        self.artwork_dirty = True
        self.dirty = True
        self.dirty_fields.add("artwork")

    def revert(self):
        if self.original:
            for f in self.TEXT_FIELDS:
                setattr(self, f, getattr(self.original, f))
            self.has_artwork = self.original.has_artwork
            self.artwork_mime = self.original.artwork_mime
            self.artwork_data = self.original.artwork_data
        self.dirty = False
        self.dirty_fields.clear()
        self.artwork_dirty = False

    def clone(self) -> "TrackTags":
        """Clone without circular reference — original is set to None on the clone."""
        return TrackTags(
            filepath=self.filepath,
            title=self.title, artist=self.artist, album=self.album,
            albumartist=self.albumartist, tracknumber=self.tracknumber,
            tracktotal=self.tracktotal, discnumber=self.discnumber,
            disctotal=self.disctotal, date=self.date, genre=self.genre,
            composer=self.composer, comment=self.comment, lyrics=self.lyrics,
            bpm=self.bpm, isrc=self.isrc,
            musicbrainz_trackid=self.musicbrainz_trackid,
            musicbrainz_albumid=self.musicbrainz_albumid,
            kind=self.kind, bitrate=self.bitrate, sample_rate=self.sample_rate,
            channels=self.channels, duration=self.duration, filesize=self.filesize,
            file_mtime=self.file_mtime,
            has_artwork=self.has_artwork, artwork_mime=self.artwork_mime,
            artwork_data=self.artwork_data,
            dirty=False, dirty_fields=set(), artwork_dirty=False,
            error=self.error, original=None,
        )

    def is_field_dirty(self, field: str) -> bool:
        return field in self.dirty_fields or field == "artwork" and self.artwork_dirty

    @property
    def changed_fields(self) -> list[str]:
        return sorted(self.dirty_fields)
