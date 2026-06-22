"""Tag writer — saves modified tags back to audio files using Mutagen."""
import os

from metadata.tag_model import TrackTags
import contextlib

try:
    import mutagen  # noqa: F401
    import mutagen.flac  # noqa: F401 — registers FLAC handler
    import mutagen.id3  # noqa: F401 — registers ID3 handler
    import mutagen.mp4  # noqa: F401 — registers MP4 handler
    from mutagen.flac import Picture
    from mutagen.id3 import APIC, TIT2, TPE1, TALB, TPE2, TRCK, TPOS, TDRC, TCON, TCOM, COMM, USLT, TBPM, TSRC, TXXX
    from mutagen.mp4 import MP4Cover
    _mutagen_available = True
except ImportError:
    _mutagen_available = False

_FRAME_ID_MAP = {
    "title": "TIT2",
    "artist": "TPE1",
    "album": "TALB",
    "albumartist": "TPE2",
    "tracknumber": "TRCK",
    "discnumber": "TPOS",
    "date": "TDRC",
    "genre": "TCON",
    "composer": "TCOM",
    "comment": "COMM",
    "lyrics": "USLT",
    "bpm": "TBPM",
    "isrc": "TSRC",
}

_MP4_KEY_MAP = {
    "title": "\xa9nam",
    "artist": "\xa9ART",
    "album": "\xa9alb",
    "albumartist": "aART",
    "tracknumber": "trkn",
    "discnumber": "disk",
    "date": "\xa9day",
    "genre": "\xa9gen",
    "composer": "\xa9wrt",
    "comment": "\xa9cmt",
    "lyrics": "\xa9lyr",
    "bpm": "tmpo",
}


def write_tags(tags: TrackTags) -> bool:
    if not os.path.isfile(tags.filepath):
        return False
    if not _mutagen_available:
        return False

    try:
        f = mutagen.File(tags.filepath)
        if f is None:
            return False

        ext = os.path.splitext(tags.filepath)[1].lower()
        kind = "mp3" if ext == ".mp3" else "flac" if ext == ".flac" else ext.lstrip(".")

        dirty = tags.dirty_fields or set()
        use_all = not dirty  # if no fields tracked, write everything (backward compat)

        # Write text fields
        for attr in TrackTags.TEXT_FIELDS:
            val = getattr(tags, attr, "")
            if use_all or attr in dirty:
                if kind == "mp3":
                    _set_mp3_field(f, attr, val)
                elif kind in ("flac", "ogg", "opus"):
                    _set_vorbis_field(f, attr, val)
                elif kind in ("mp4", "m4a"):
                    _set_mp4_field(f, attr, val)

        # Artwork
        if use_all or tags.artwork_dirty or "artwork" in dirty:
            _write_artwork(f, kind, tags)

        f.save()
        tags.dirty = False
        tags.dirty_fields.clear()
        tags.artwork_dirty = False
        tags.error = ""
        return True

    except Exception as e:
        tags.error = str(e)
        return False


# ── MP3 ──

def _celiminar_mp3_frame(f, frame_id: str):
    """Delete existing frames of a given type to avoid duplicates."""
    try:
        f.tags.delall(frame_id)
    except Exception:
        import logging
        logging.getLogger("michi").debug("Non-critical operation failed")


def _set_mp3_field(f, attr: str, value: str):
    if f.tags is None:
        f.add_tags()

    frame_id = _FRAME_ID_MAP.get(attr)
    if frame_id:
        _celiminar_mp3_frame(f, frame_id)  # always delete old frame first
        if value.strip():
            _add_mp3_frame(f, frame_id, value)
    elif attr in ("musicbrainz_trackid", "musicbrainz_albumid", "tracktotal", "disctotal"):
        _celiminar_mp3_frame(f, "TXXX:" + attr)
        if value.strip():
            f.tags.add(TXXX(encoding=3, desc=attr, text=[value]))


def _add_mp3_frame(f, frame_id: str, value: str):
    frame_cls = {
        "TIT2": TIT2, "TPE1": TPE1, "TALB": TALB, "TPE2": TPE2,
        "TRCK": TRCK, "TPOS": TPOS, "TDRC": TDRC, "TCON": TCON,
        "TCOM": TCOM, "TBPM": TBPM, "TSRC": TSRC,
    }.get(frame_id)

    if frame_cls in (TCOM, TBPM, TSRC) or frame_cls:
        f.tags.add(frame_cls(encoding=3, text=[value]))
    elif frame_id == "COMM":
        f.tags.add(COMM(encoding=3, lang="spa", desc="", text=[value]))
    elif frame_id == "USLT":
        f.tags.add(USLT(encoding=3, lang="spa", desc="", text=value))


# ── Vorbis ──

def _set_vorbis_field(f, attr: str, value: str):
    if not hasattr(f, 'tags'):
        return
    if value.strip():
        f.tags[attr] = value
    else:
        with contextlib.suppress(KeyError, Exception):
            del f.tags[attr]


# ── MP4 ──

def _set_mp4_field(f, attr: str, value: str):
    if not hasattr(f, 'tags'):
        return
    mp4_key = _MP4_KEY_MAP.get(attr)
    if not mp4_key:
        return

    if value.strip():
        if mp4_key in ("trkn", "disk"):
            parts = value.split("/")
            nums = [(int(p) if p.isdigit() else 0) for p in parts[:2]]
            f.tags[mp4_key] = [tuple(nums)]
        else:
            f.tags[mp4_key] = [value]
    else:
        with contextlib.suppress(KeyError, Exception):
            del f.tags[mp4_key]

    # Handle tracktotal/disctotal via trkn/disk
    if attr == "tracknumber" and value.strip() and "/" not in value:
        pass  # keep as-is
    if attr == "discnumber" and value.strip() and "/" not in value:
        pass


# ── Artwork ──

def _write_artwork(f, kind: str, tags: TrackTags):
    if kind == "mp3":
        if f.tags is None:
            f.add_tags()
        _celiminar_mp3_frame(f, "APIC")
        if tags.has_artwork and tags.artwork_data:
            f.tags.add(APIC(encoding=3, mime=tags.artwork_mime or "image/jpeg",
                           type=3, desc="Cover", data=tags.artwork_data))

    elif kind == "flac":
        if hasattr(f, 'pictures'):
            f.clear_pictures()
        if tags.has_artwork and tags.artwork_data:
            pic = Picture()
            pic.type = 3
            pic.mime = tags.artwork_mime or "image/jpeg"
            pic.desc = "Cover"
            pic.data = tags.artwork_data
            f.add_picture(pic)

    elif kind in ("mp4", "m4a"):
        if tags.has_artwork and tags.artwork_data:
            fmt = MP4Cover.FORMAT_JPEG if "jpeg" in (tags.artwork_mime or "jpeg") else MP4Cover.FORMAT_PNG
            f.tags["covr"] = [MP4Cover(tags.artwork_data, imageformat=fmt)]
        else:
            with contextlib.suppress(KeyError, Exception):
                del f.tags["covr"]
