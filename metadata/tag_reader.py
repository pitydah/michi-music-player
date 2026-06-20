"""Tag reader — reads audio metadata using Mutagen."""
import os

from metadata.tag_model import TrackTags

_mutagen_available = False
try:
    import mutagen
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import ID3, APIC
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.easyid3 import EasyID3
    from mutagen.aiff import AIFF
    from mutagen.wave import WAVE
    _mutagen_available = True
except ImportError:
    pass

AUDIO_EXTS = {
    ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".mp4",
    ".wav", ".aiff", ".aif", ".ape", ".wma", ".dsf",
}

# MP3 ID3 frame → TrackTags attr mapping (for non-EasyID3 path)
_ID3_FRAME_MAP = {
    "TIT2": "title",
    "TPE1": "artist",
    "TALB": "album",
    "TPE2": "albumartist",
    "TRCK": "tracknumber",
    "TPOS": "discnumber",
    "TDRC": "date",
    "TYER": "date",
    "TCOM": "composer",
    "TCON": "genre",
    "TBPM": "bpm",
    "TSRC": "isrc",
}

# MP4 atom → TrackTags attr mapping (reverse of writer)
_MP4_READ_MAP = {
    "\xa9nam": "title",
    "\xa9ART": "artist",
    "\xa9alb": "album",
    "aART": "albumartist",
    "trkn": "tracknumber",
    "disk": "discnumber",
    "\xa9day": "date",
    "\xa9gen": "genre",
    "\xa9wrt": "composer",
    "\xa9cmt": "comment",
    "tmpo": "bpm",
}

_MP4_READ_MAP_ALT = {
    "©nam": "title",
    "©ART": "artist",
    "©alb": "album",
    "©day": "date",
    "©gen": "genre",
    "©wrt": "composer",
    "©cmt": "comment",
}


def _read_artwork(f, kind: str) -> tuple[bool, str, bytes | None]:
    try:
        if kind == "mp3" and hasattr(f, "tags"):
            for k in f.tags or {}:
                if k.startswith("APIC:"):
                    return True, f.tags[k].mime, f.tags[k].data
        elif kind == "flac" and hasattr(f, "pictures"):
            pics = f.pictures or []
            if pics:
                return True, pics[0].mime, pics[0].data
        elif kind in ("mp4", "m4a"):
            covr = f.tags.get("covr", []) if hasattr(f, "tags") else []
            if covr:
                fmt = "image/jpeg" if covr[0].imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                return True, fmt, bytes(covr[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")
    return False, "", None


def _read_id3_tags(f, desc: TrackTags):
    """Read ID3 tags using frame-level access (works without EasyID3)."""
    tags = f.tags
    if not tags:
        return

    for frame_id, attr in _ID3_FRAME_MAP.items():
        try:
            frame = tags.get(frame_id)
            if frame:
                val = str(frame)
                if val and not getattr(desc, attr):
                    setattr(desc, attr, val)
        except Exception:
            continue

    # COMM → comment
    try:
        comms = tags.getall("COMM")
        if comms:
            desc.comment = str(comms[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")

    # USLT → lyrics
    try:
        uslts = tags.getall("USLT")
        if uslts:
            desc.lyrics = str(uslts[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")

    # TXXX frames
    _txxx_map = {
        "MusicBrainz Track Id": "musicbrainz_trackid",
        "MusicBrainz Album Id": "musicbrainz_albumid",
        "TRACKTOTAL": "tracktotal",
        "tracktotal": "tracktotal",
        "DISCTOTAL": "disctotal",
        "disctotal": "disctotal",
    }
    try:
        for key in tags:
            if key.startswith("TXXX:"):
                desc_key = key[5:]
                mapped = _txxx_map.get(desc_key) or _txxx_map.get(desc_key.lower())
                if mapped:
                    setattr(desc, mapped, str(tags[key]))
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")

    # Track number — may contain "/N"
    if desc.tracknumber and "/" in desc.tracknumber:
        parts = desc.tracknumber.split("/")
        desc.tracknumber = parts[0]
        if len(parts) > 1 and not desc.tracktotal:
            desc.tracktotal = parts[1]

    # Disc number — may contain "/N"
    if desc.discnumber and "/" in desc.discnumber:
        parts = desc.discnumber.split("/")
        desc.discnumber = parts[0]
        if len(parts) > 1 and not desc.disctotal:
            desc.disctotal = parts[1]


def _read_mp4_tags(f, desc: TrackTags):
    """Read MP4/M4A tags using atom-level access."""
    tags = f.tags
    if not tags:
        return

    for mp4_key, attr in _MP4_READ_MAP.items():
        try:
            val = tags.get(mp4_key)
            if val is None:
                continue
            if mp4_key in ("trkn", "disk"):
                if isinstance(val, list) and val:
                    item = val[0]
                    if isinstance(item, tuple):
                        desc_val = str(item[0]) if item[0] else ""
                        if len(item) > 1 and item[1] and not getattr(desc, mp4_key + "total", ""):
                            if mp4_key == "trkn":
                                desc.tracktotal = str(item[1])
                            else:
                                desc.disctotal = str(item[1])
                        setattr(desc, attr, desc_val)
                    else:
                        setattr(desc, attr, str(item))
            else:
                v = val[0] if isinstance(val, list) else val
                setattr(desc, attr, str(v))
        except Exception:
            continue

    # Also check alt encoding
    for mp4_key, attr in _MP4_READ_MAP_ALT.items():
        try:
            val = tags.get(mp4_key)
            if val and not getattr(desc, attr):
                v = val[0] if isinstance(val, list) else val
                setattr(desc, attr, str(v))
        except Exception:
            continue

    # ISRC
    try:
        isrc = tags.get("----:com.apple.iTunes:ISRC")
        if isrc:
            desc.isrc = str(isrc[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")

    # MusicBrainz via Xtra
    try:
        mb_track = tags.get("----:com.apple.iTunes:MusicBrainz Track Id")
        if mb_track:
            desc.musicbrainz_trackid = str(mb_track[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")
    try:
        mb_album = tags.get("----:com.apple.iTunes:MusicBrainz Album Id")
        if mb_album:
            desc.musicbrainz_albumid = str(mb_album[0])
    except Exception:
        import logging
        logging.getLogger("astra").debug("Non-critical operation failed")


def read_tags(filepath: str) -> TrackTags:
    if not os.path.isfile(filepath):
        return TrackTags(filepath=filepath, error="Archivo no encontrado")

    if not _mutagen_available:
        return TrackTags(filepath=filepath, error="Instala mutagen: pip install mutagen")

    try:
        f = mutagen.File(filepath)
    except Exception as e:
        return TrackTags(filepath=filepath, error=f"Error al abrir: {e}")

    if f is None:
        return TrackTags(filepath=filepath, error="Formato no soportado")

    ext = os.path.splitext(filepath)[1].lower()
    kind = "mp3" if ext == ".mp3" else "flac" if ext == ".flac" else ext.lstrip(".")

    desc = TrackTags(filepath=filepath, filesize=os.path.getsize(filepath),
                     file_mtime=os.path.getmtime(filepath))

    if hasattr(f, 'info') and f.info:
        desc.duration = getattr(f.info, 'length', 0.0)
        desc.bitrate = getattr(f.info, 'bitrate', 0) or 0
        desc.sample_rate = getattr(f.info, 'sample_rate', 0) or 0
        desc.channels = getattr(f.info, 'channels', 0) or 0

    desc.kind = kind.upper()

    # ── Read tags per format ──
    if kind == "mp3":
        _read_id3_tags(f, desc)
    elif kind in ("mp4", "m4a"):
        _read_mp4_tags(f, desc)
    elif hasattr(f, 'tags') and f.tags:
        # FLAC / OGG / Opus — Vorbis comments, simple key-value
        t = f.tags
        for attr in TrackTags.TEXT_FIELDS:
            try:
                val = t.get(attr)
                if val:
                    v = val[0] if isinstance(val, list) else str(val)
                    setattr(desc, attr, str(v))
            except Exception:
                continue

    # Artwork
    has_art, art_mime, art_data = _read_artwork(f, kind)
    desc.has_artwork = has_art
    desc.artwork_mime = art_mime
    desc.artwork_data = art_data

    desc.original = desc.clone()
    desc.dirty = False

    return desc
