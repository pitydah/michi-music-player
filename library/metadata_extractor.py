"""Metadata extraction — unified Mutagen-first reader with per-format priority.

Format coverage: ID3v2, ID3v1, APEv2, VorbisComment, MP4/iTunes, ASF/WMA,
RIFF INFO (WAV), AIFF, DSF/DFF.

Priority per field: Mutagen real tags > GStreamer > filename inference.
For MP3: ID3v2 > APEv2 > ID3v1 > GStreamer > filename.
"""
import os
import logging
import contextlib
import threading
from pathlib import Path

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstPbutils", "1.0")
from gi.repository import Gst, GstPbutils  # noqa: E402

Gst.init(None)

AUDIO_EXTS = frozenset({
    ".ogg", ".oga", ".opus", ".flac", ".wav", ".wv", ".spx",
    ".mp3", ".dsf", ".dff", ".aiff", ".aif", ".ape", ".tta",
    ".m4a", ".aac", ".ac3", ".shn", ".wma",
})
ALL_EXTS = AUDIO_EXTS

log = logging.getLogger("michi.extractor")
_thread_local = threading.local()

# ── ID3v1 genre table ──
_ID3V1_GENRES = [
    "Blues", "Classic Rock", "Country", "Dance", "Disco", "Funk",
    "Grunge", "Hip-Hop", "Jazz", "Metal", "New Age", "Oldies",
    "Other", "Pop", "R&B", "Rap", "Reggae", "Rock", "Techno",
    "Industrial", "Alternative", "Ska", "Death Metal", "Pranks",
    "Soundtrack", "Euro-Techno", "Ambient", "Trip-Hop", "Vocal",
    "Jazz+Funk", "Fusion", "Trance", "Classical", "Instrumental",
    "Acid", "House", "Game", "Sound Clip", "Gospel", "Noise",
    "AlternRock", "Bass", "Soul", "Punk", "Space", "Meditative",
    "Instrumental Pop", "Instrumental Rock", "Ethnic", "Gothic",
    "Darkwave", "Techno-Industrial", "Electronic", "Pop-Folk",
    "Eurodance", "Dream", "Southern Rock", "Comedy", "Cult",
    "Gangsta", "Top 40", "Christian Rap", "Pop/Funk", "Jungle",
    "Native American", "Cabaret", "New Wave", "Psychedelic", "Rave",
    "Showtunes", "Trailer", "Lo-Fi", "Tribal", "Acid Punk",
    "Acid Jazz", "Polka", "Retro", "Musical", "Rock & Roll",
    "Hard Rock",
]


def _get_discoverer():
    d = getattr(_thread_local, "discoverer", None)
    if d is None:
        d = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        _thread_local.discoverer = d
    return d


def _safe_uri(filepath: str) -> str:
    try:
        from gi.repository import GLib
        return GLib.filename_to_uri(os.path.abspath(filepath), None)
    except (ImportError, Exception):
        return Path(filepath).resolve().as_uri()


def _infer_from_filename(filepath: str) -> dict:
    from library.metadata_normalizer import infer_metadata_from_filename
    return infer_metadata_from_filename(filepath)


# ── Parsing helpers ──

def parse_track_number(value) -> tuple[int, int]:
    """Parse '3/12', '3', or MP4 tuple '(3, 12)' into (number, total)."""
    if not value:
        return 0, 0
    s = str(value).strip()
    if s.startswith("(") and s.endswith(")") and "," in s:
        s = s[1:-1]
    with contextlib.suppress(ValueError, TypeError):
        parts = s.split("/")
        num = int(float(parts[0]))
        total = int(float(parts[1])) if len(parts) > 1 else 0
        return num, total
    return 0, 0


def parse_disc_number(value) -> tuple[int, int]:
    """Parse disc number — delegates to parse_track_number."""
    return parse_track_number(value)


def parse_year(value) -> int:
    """Normalize year from string, int, or date string like '2024-01-15'."""
    if not value:
        return 0
    if isinstance(value, int):
        return value
    with contextlib.suppress(ValueError, TypeError, IndexError):
        s = str(value).strip()
        return int(s[:4])
    return 0


# ── ID3v1 fallback ──

def extract_id3v1(filepath: str) -> dict:
    """Read ID3v1 from last 128 bytes of MP3 as fallback only."""
    info = {"title": "", "artist": "", "album": "", "year": 0,
            "comment": "", "track_number": 0, "genre": ""}
    try:
        with open(filepath, "rb") as fh:
            fh.seek(-128, os.SEEK_END)
            data = fh.read(128)
        if data[:3] != b"TAG":
            return info
        def _d(start, length):
            raw = data[start:start + length]
            text = raw.split(b"\x00", 1)[0]
            try:
                text = text.decode("utf-8")
            except UnicodeDecodeError:
                text = text.decode("latin-1", errors="replace")
            return text.strip().rstrip("\x00").rstrip()
        info["title"] = _d(3, 30)
        info["artist"] = _d(33, 30)
        info["album"] = _d(63, 30)
        yr = _d(93, 4)
        info["year"] = parse_year(yr)
        info["comment"] = _d(97, 30)
        if data[125] == 0 and data[126] != 0:
            info["track_number"] = data[126]
        genre_byte = data[127]
        if 0 <= genre_byte < len(_ID3V1_GENRES):
            info["genre"] = _ID3V1_GENRES[genre_byte]
    except Exception:
        pass
    return info


# ── Tag search helper ──

def _tag_get(tags, *keys) -> str:
    """Search mutagen tags dict for first matching key."""
    for k in keys:
        v = tags.get(k)
        if v:
            if isinstance(v, list):
                return str(v[0]) if len(v) > 0 else ""
            return str(v)
    return ""


# ── merge_metadata_by_priority ──

def merge_metadata_by_priority(*dicts: dict) -> dict:
    """Merge dicts left to right; first non-empty/non-zero value wins per field."""
    merged: dict = {}
    for d in reversed(dicts):
        for k, v in d.items():
            if v not in (None, "", 0, 0.0, b""):
                merged[k] = v
    return merged


# ── Core mutagen tags ──

def extract_mutagen_tags(filepath: str) -> dict:
    """Read all metadata tags from any Mutagen-supported format.

    Returns flat dict with all standard fields. Handles:
    ID3v2, APEv2, ID3v1, VorbisComment, MP4/iTunes atoms, ASF/WMA, RIFF INFO.
    """
    from mutagen import File as MutagenFile

    info: dict = {
        "title": "", "artist": "", "album": "", "albumartist": "",
        "date": "", "year": 0, "originaldate": "",
        "genre": "", "track_number": 0, "track_total": 0,
        "disc_number": 0, "disc_total": 0,
        "composer": "", "lyricist": "", "bpm": 0,
        "comment": "", "copyright": "", "isrc": "",
        "label": "", "conductor": "", "compilation": 0,
        "media_type": "", "encoder": "",
        "remixer": "", "grouping": "", "mood": "",
        "mb_track_id": "", "mb_album_id": "", "mb_albumartist_id": "",
        "mb_artist_id": "", "mb_releasegroup_id": "",
        "acoustid_id": "", "acoustid_fingerprint": "",
        "replaygain_track": 0.0, "replaygain_album": 0.0,
        "replaygain_track_peak": 0.0, "replaygain_album_peak": 0.0,
        "r128_track_gain": 0.0, "r128_album_gain": 0.0,
        "bit_depth": 0, "duration": 0.0,
        "sample_rate": 0, "channels": 0, "bitrate": 0,
        "cover_mime": "", "cover_data": b"",
    }

    try:
        mf = MutagenFile(filepath)
        if mf is None:
            return info

        # ── Audio properties ──
        if hasattr(mf, 'info') and mf.info:
            info["duration"] = float(getattr(mf.info, 'length', 0) or 0)
            info["sample_rate"] = int(getattr(mf.info, 'sample_rate', 0) or 0)
            info["channels"] = int(getattr(mf.info, 'channels', 0) or 0)
            info["bitrate"] = int(getattr(mf.info, 'bitrate', 0) or 0)
            info["bit_depth"] = int(getattr(mf.info, 'bits_per_sample', 0) or 0)

        if not mf.tags or not hasattr(mf.tags, 'get'):
            # Try ID3v1 fallback for MP3
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".mp3":
                id3v1 = extract_id3v1(filepath)
                for k in ("title", "artist", "album", "year", "genre",
                          "track_number", "comment"):
                    if not info.get(k):
                        info[k] = id3v1.get(k, info.get(k))
            return info

        tags = mf.tags

        def _G(*keys):
            return _tag_get(tags, *keys)

        # ── Core tags ──
        info["title"] = _G("title", "TIT2", "\xa9nam", "Title", "WM/Title",
                           "INAM")
        info["artist"] = _G("artist", "TPE1", "\xa9ART", "Author", "WM/Author",
                            "AUTH", "IART")
        info["album"] = _G("album", "TALB", "\xa9alb", "WM/AlbumTitle",
                           "Album", "IPRD")
        info["albumartist"] = _G("albumartist", "ALBUMARTIST", "album artist",
                                 "TPE2", "aART", "WM/AlbumArtist", "\xa9ART")

        # ── Date / year / originaldate ──
        date_val = _G("date", "originaldate", "TDRC", "TYER", "TDOR",
                      "TORY", "\xa9day", "WM/Year", "ICRD")
        info["date"] = date_val[:4] if len(date_val) >= 4 else date_val
        info["originaldate"] = _G("originaldate", "TDOR", "TORY",
                                  "ORIGINALYEAR")
        with contextlib.suppress(ValueError, TypeError):
            yd = info["date"] or info["originaldate"] or "0"
            info["year"] = int(yd[:4])

        # ── Genre (strip ID3 parenthetical) ──
        genre = _G("genre", "TCON", "\xa9gen", "WM/Genre", "GENRE", "IGNR")
        if genre.startswith("(") and ")" in genre:
            genre = genre.split(")", 1)[-1].strip()
        info["genre"] = genre

        # ── Track / disc ──
        info["track_number"], info["track_total"] = parse_track_number(
            _G("tracknumber", "TRCK", "trkn", "TRACKNUMBER",
               "WM/TrackNumber", "Track", "ITRK"))
        info["disc_number"], info["disc_total"] = parse_disc_number(
            _G("discnumber", "TPOS", "disk", "DISCNUMBER",
               "WM/PartOfSet", "Disc"))

        # ── Composer / lyricist / BPM / ISRC ──
        info["composer"] = _G("composer", "TCOM", "\xa9wrt",
                              "WM/Composer", "Composer")
        info["lyricist"] = _G("lyricist", "TEXT", "LYRICIST", "LYRICS",
                              "WM/Writer")
        bpm_val = _G("bpm", "TBPM", "tmpo", "BPM", "WM/BeatsPerMinute")
        with contextlib.suppress(ValueError, TypeError):
            info["bpm"] = int(float(bpm_val)) if bpm_val else 0
        info["isrc"] = _G("isrc", "TSRC", "ISRC", "WM/ISRC")

        # ── Comment / copyright / label ──
        info["comment"] = _G("comment", "COMM", "\xa9cmt", "COMMENT",
                             "Description", "ICMT")
        info["copyright"] = _G("TCOP", "copyright", "COPYRIGHT",
                               "WM/Copyright", "\xa9cpy", "cprt", "ICOP")
        info["label"] = _G("label", "TPUB", "\xa9pub", "LABEL",
                           "organization", "WM/Publisher")

        # ── Conductor / compilation / media / encoder ──
        info["conductor"] = _G("conductor", "TPE3", "TCONDUCTOR", "Conductor")
        cp_val = _G("TCMP", "cpil", "COMPILATION", "compilation")
        info["compilation"] = 1 if cp_val.lower() in ("1", "true", "yes") else 0
        info["media_type"] = _G("TMED", "MEDIA", "sourcemedia", "WM/Media")
        info["encoder"] = _G("TENC", "TSSE", "ENCODER", "encoder",
                             "WM/EncodedBy", "ISFT")

        # ── Remixer / grouping / mood ──
        info["remixer"] = _G("TPE4", "REMIXER", "remixer",
                             "WM/ModifiedBy")
        info["grouping"] = _G("TIT1", "GRP1", "GROUPING", "grouping",
                              "WM/ContentGroupDescription")
        info["mood"] = _G("TMOO", "MOOD", "mood", "WM/Mood")

        # ── MusicBrainz IDs ──
        info["mb_track_id"] = _G(
            "MUSICBRAINZ_TRACKID", "MusicBrainz Track Id",
            "musicbrainz_trackid",
            "----:com.apple.iTunes:MusicBrainz Track Id",
            "MusicBrainz/Track Id")
        info["mb_album_id"] = _G(
            "MUSICBRAINZ_ALBUMID", "MusicBrainz Album Id",
            "musicbrainz_albumid",
            "----:com.apple.iTunes:MusicBrainz Album Id",
            "MusicBrainz/Album Id")
        info["mb_albumartist_id"] = _G(
            "MUSICBRAINZ_ALBUMARTISTID", "MusicBrainz Album Artist Id",
            "musicbrainz_albumartistid",
            "----:com.apple.iTunes:MusicBrainz Album Artist Id",
            "MusicBrainz/Album Artist Id")
        info["mb_artist_id"] = _G(
            "MUSICBRAINZ_ARTISTID", "MusicBrainz Artist Id",
            "musicbrainz_artistid",
            "----:com.apple.iTunes:MusicBrainz Artist Id",
            "MusicBrainz/Artist Id")
        info["mb_releasegroup_id"] = _G(
            "MUSICBRAINZ_RELEASEGROUPID", "MusicBrainz Release Group Id",
            "musicbrainz_releasegroupid",
            "----:com.apple.iTunes:MusicBrainz Release Group Id",
            "MusicBrainz/Release Group Id")

        # ── AcoustID ──
        info["acoustid_id"] = _G(
            "ACOUSTID_ID", "Acoustid Id", "acoustid_id",
            "----:com.apple.iTunes:Acoustid Id")
        info["acoustid_fingerprint"] = _G(
            "ACOUSTID_FINGERPRINT", "Acoustid Fingerprint",
            "acoustid_fingerprint")

        # ── ReplayGain ──
        for key, field in [
            ("REPLAYGAIN_TRACK_GAIN", "replaygain_track"),
            ("replaygain_track_gain", "replaygain_track"),
            ("REPLAYGAIN_ALBUM_GAIN", "replaygain_album"),
            ("replaygain_album_gain", "replaygain_album"),
            ("REPLAYGAIN_TRACK_PEAK", "replaygain_track_peak"),
            ("replaygain_track_peak", "replaygain_track_peak"),
            ("REPLAYGAIN_ALBUM_PEAK", "replaygain_album_peak"),
            ("replaygain_album_peak", "replaygain_album_peak"),
        ]:
            val = _G(key)
            if val:
                with contextlib.suppress(ValueError, TypeError):
                    if not info.get(field):
                        info[field] = float(val.split(" ")[0])

        # ── R128 (EBU loudness) ──
        for key, field in [
            ("R128_TRACK_GAIN", "r128_track_gain"),
            ("r128_track_gain", "r128_track_gain"),
            ("R128_ALBUM_GAIN", "r128_album_gain"),
            ("r128_album_gain", "r128_album_gain"),
        ]:
            val = _G(key)
            if val:
                with contextlib.suppress(ValueError, TypeError):
                    if not info.get(field):
                        info[field] = float(val.split(" ")[0])

        # ── Cover art ──
        info.update(_extract_cover_art(mf, tags))

        # ── ID3v1 fallback for MP3 (fills gaps only) ──
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".mp3":
            id3v1 = extract_id3v1(filepath)
            for k in ("title", "artist", "album", "year", "genre",
                      "track_number", "comment"):
                if not info.get(k):
                    info[k] = id3v1.get(k, "")

    except Exception as e:
        log.debug("Mutagen tags extraction failed for %s: %s", filepath, e)
    return info


# ── Cover art ──

def _extract_cover_art(mf, tags) -> dict:
    result: dict = {"cover_mime": "", "cover_data": b""}
    try:
        # VorbisComment/FLAC — pictures list
        if hasattr(mf, 'pictures') and mf.pictures:
            p = mf.pictures[0]
            result["cover_mime"] = getattr(p, 'mime', 'image/jpeg')
            result["cover_data"] = getattr(p, 'data', b'')
            return result
        # METADATA_BLOCK_PICTURE (FLAC)
        pic_key = "METADATA_BLOCK_PICTURE"
        if pic_key in tags:
            try:
                import base64
                raw = tags[pic_key]
                if isinstance(raw, list) and raw:
                    raw = raw[0]
                data = base64.b64decode(str(raw))
                result["cover_mime"] = "image/jpeg"
                result["cover_data"] = data
                return result
            except Exception:
                pass
        # MP3 APIC frame — iterate all keys for startswith("APIC")
        for key in tags:
            skey = str(key)
            if skey.startswith("APIC"):
                try:
                    v = tags.get(key)
                    if v and getattr(v, "data", None):
                        result["cover_mime"] = getattr(v, "mime", "image/jpeg")
                        result["cover_data"] = v.data
                        return result
                except Exception:
                    pass
        # Fallback: also try exact keys
        for key in ("\xa9cov",):
            try:
                v = tags.get(key)
                if v:
                    result["cover_mime"] = getattr(v, "mime", "image/jpeg")
                    result["cover_data"] = getattr(v, "data", b"")
                    return result
            except Exception:
                pass
        # MP4 covr atom
        for key in ("covr", "COVER"):
            try:
                v = tags.get(key)
                if v and isinstance(v, list) and len(v) > 0:
                    result["cover_mime"] = "image/jpeg"
                    result["cover_data"] = (
                        bytes(v[0]) if not isinstance(v[0], bytes) else v[0])
                    return result
            except Exception:
                pass
        # ASF/WMA picture
        for key in ("WM/Picture", "Cover Art (Front)"):
            try:
                v = tags.get(key)
                if v:
                    result["cover_mime"] = getattr(v, 'mime', 'image/jpeg')
                    result["cover_data"] = getattr(v, 'data', b'')
                    return result
            except Exception:
                pass
    except Exception:
        pass
    return result


# ── Sidecar cover art ──

_COVER_NAMES = ("cover.jpg", "cover.png", "folder.jpg", "folder.png",
                "front.jpg", "front.png", "Cover.jpg", "Cover.png",
                "Folder.jpg", "Folder.png")


def extract_sidecar_cover(filepath: str) -> dict:
    """Look for cover image files in the same directory as the audio file."""
    result: dict = {"cover_mime": "", "cover_data": b""}
    try:
        directory = os.path.dirname(os.path.abspath(filepath))
        for name in _COVER_NAMES:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate):
                ext = os.path.splitext(name)[1].lower()
                mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                            ".png": "image/png"}
                result["cover_mime"] = mime_map.get(ext, "image/jpeg")
                with open(candidate, "rb") as fh:
                    result["cover_data"] = fh.read()
                return result
    except Exception:
        pass
    return result


# ── Combined extraction ──

def extract_metadata_combined(filepath: str) -> dict:
    """Unified extraction: Mutagen > GStreamer > filename inference.

    Priority (per field):
      title:   Mutagen real > GStreamer > filename inference > filename clean
      artist:  Mutagen real > GStreamer > filename inference > ""
      album:   Mutagen real > GStreamer > ""
      year:    Mutagen date/year/originaldate > GStreamer date > 0
      genre:   Mutagen real > ""
      duration: GStreamer > Mutagen info.length > 0
      track_number: Mutagen real > GStreamer > filename inference > 0
    """
    from library.metadata_normalizer import infer_metadata_from_filename

    mg = extract_mutagen_tags(filepath)
    inferred = infer_metadata_from_filename(filepath)

    gst = {}
    try:
        uri = _safe_uri(filepath)
        d = _get_discoverer()
        disc = d.discover_uri(uri)
        if disc is not None:
            dur = disc.get_duration()
            if dur > 0:
                gst["duration"] = dur / 1e9
            tags = disc.get_tags()
            if tags:
                ok, v = tags.get_string(Gst.TAG_TITLE)
                if ok:
                    gst["title"] = v
                ok, v = tags.get_string(Gst.TAG_ARTIST)
                if ok:
                    gst["artist"] = v
                ok, v = tags.get_string(Gst.TAG_ALBUM)
                if ok:
                    gst["album"] = v
                ok, v = tags.get_string(Gst.TAG_ALBUM_ARTIST)
                if ok:
                    gst["albumartist"] = v
                ok, v = tags.get_string(Gst.TAG_DATE)
                if ok:
                    gst["date"] = v
                ok, v = tags.get_uint(Gst.TAG_TRACK_NUMBER)
                if ok:
                    gst["track_number"] = v
                ok, v = tags.get_uint(Gst.TAG_TRACK_COUNT)
                if ok:
                    gst["track_total"] = v
            streams = disc.get_audio_streams()
            if streams:
                s = streams[0]
                gst["sample_rate"] = s.get_sample_rate() or 0
                gst["channels"] = s.get_channels() or 0
                gst["bitrate"] = s.get_bitrate() or 0
    except Exception:
        pass

    def _p(mg_key, gst_key, default=None):
        v = mg.get(mg_key)
        if v not in (None, "", 0, 0.0):
            return v
        v = gst.get(gst_key)
        if v not in (None, "", 0, 0.0):
            return v
        return default

    r: dict = {}
    r["title"] = _p("title", "title") or str(inferred.get("title") or "") or ""
    r["artist"] = _p("artist", "artist") or str(inferred.get("artist") or "") or ""
    r["album"] = _p("album", "album") or ""
    r["albumartist"] = _p("albumartist", "albumartist") or r["artist"]
    r["date"] = _p("date", "date") or ""
    r["originaldate"] = mg.get("originaldate") or ""
    r["year"] = mg.get("year") or 0
    r["genre"] = mg.get("genre") or ""
    r["track_number"] = _p("track_number", "track_number") or inferred.get("track_number", 0) or 0
    r["track_total"] = _p("track_total", "track_total") or 0
    r["disc_number"] = mg.get("disc_number") or 0
    r["disc_total"] = mg.get("disc_total") or 0
    r["composer"] = mg.get("composer") or ""
    r["lyricist"] = mg.get("lyricist") or ""
    r["bpm"] = mg.get("bpm") or 0
    r["comment"] = mg.get("comment") or ""
    r["isrc"] = mg.get("isrc") or ""
    r["label"] = mg.get("label") or ""
    r["conductor"] = mg.get("conductor") or ""
    r["compilation"] = mg.get("compilation") or 0
    r["media_type"] = mg.get("media_type") or ""
    r["encoder"] = mg.get("encoder") or ""
    r["copyright"] = mg.get("copyright") or ""
    r["remixer"] = mg.get("remixer") or ""
    r["grouping"] = mg.get("grouping") or ""
    r["mood"] = mg.get("mood") or ""
    r["mb_track_id"] = mg.get("mb_track_id") or ""
    r["mb_album_id"] = mg.get("mb_album_id") or ""
    r["mb_albumartist_id"] = mg.get("mb_albumartist_id") or ""
    r["mb_artist_id"] = mg.get("mb_artist_id") or ""
    r["mb_releasegroup_id"] = mg.get("mb_releasegroup_id") or ""
    r["acoustid_id"] = mg.get("acoustid_id") or ""
    r["acoustid_fingerprint"] = mg.get("acoustid_fingerprint") or ""
    r["replaygain_track"] = mg.get("replaygain_track") or 0.0
    r["replaygain_album"] = mg.get("replaygain_album") or 0.0
    r["replaygain_track_peak"] = mg.get("replaygain_track_peak") or 0.0
    r["replaygain_album_peak"] = mg.get("replaygain_album_peak") or 0.0
    r["r128_track_gain"] = mg.get("r128_track_gain") or 0.0
    r["r128_album_gain"] = mg.get("r128_album_gain") or 0.0
    r["bit_depth"] = mg.get("bit_depth") or 0
    r["duration"] = _p("duration", "duration") or 0.0
    r["sample_rate"] = _p("sample_rate", "sample_rate") or 0
    r["channels"] = _p("channels", "channels") or 0
    r["bitrate"] = _p("bitrate", "bitrate") or 0
    r["cover_mime"] = mg.get("cover_mime") or ""
    r["cover_data"] = mg.get("cover_data") or b""
    # Fallback to sidecar cover if no embedded cover
    if not r["cover_data"]:
        sidecar = extract_sidecar_cover(filepath)
        if sidecar["cover_data"]:
            r["cover_mime"] = sidecar["cover_mime"]
            r["cover_data"] = sidecar["cover_data"]
    return r


# ── Backward-compat wrappers ──

def extract_metadata(filepath: str) -> dict:
    """Backward-compat: returns combined metadata dict."""
    return extract_metadata_combined(filepath)


def extract_metadata_full(filepath: str) -> dict:
    """Backward-compat: full Mutagen tags for legacy callers."""
    return extract_mutagen_tags(filepath)
