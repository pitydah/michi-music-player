"""Metadata extraction — GStreamer discoverer + Mutagen fallback + filename inference."""
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


def _get_discoverer():
    d = getattr(_thread_local, "discoverer", None)
    if d is None:
        d = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        _thread_local.discoverer = d
    return d


def _safe_uri(filepath: str) -> str:
    """Build a file:// URI that works with spaces, accents, and special chars."""
    try:
        from gi.repository import GLib
        abspath = os.path.abspath(filepath)
        return GLib.filename_to_uri(abspath, None)
    except (ImportError, Exception):
        return Path(filepath).resolve().as_uri()


def _infer_from_filename(filepath: str) -> dict:
    """Infer artist and title from filename patterns like 'Artist - Title.ext'."""
    from library.metadata_normalizer import infer_metadata_from_filename
    return infer_metadata_from_filename(filepath)


def extract_mutagen_tags(filepath: str) -> dict:
    """Read all common metadata tags from any Mutagen-supported format.

    Returns flat dict with title, artist, album, albumartist, date, year,
    genre, track_number, track_total, disc_number, disc_total, composer,
    bpm, isrc, label, conductor, compilation, media_type, encoder, copyright,
    remixer, grouping, mood, originaldate, mb_*, replaygain, bit_depth,
    duration, sample_rate, channels, bitrate, cover_mime, cover_data.

    Covers: ID3 (MP3), VorbisComment (FLAC/OGG/Opus), MP4/M4A, ASF/WMA, APEv2.
    """
    from mutagen import File as MutagenFile
    info: dict = {
        "title": "", "artist": "", "album": "", "albumartist": "",
        "date": "", "year": 0, "genre": "",
        "track_number": 0, "track_total": 0,
        "disc_number": 0, "disc_total": 0,
        "composer": "", "bpm": 0, "isrc": "",
        "label": "", "conductor": "", "compilation": 0,
        "media_type": "", "encoder": "", "copyright": "",
        "remixer": "", "grouping": "", "mood": "",
        "originaldate": "",
        "mb_track_id": "", "mb_album_id": "", "mb_albumartist_id": "",
        "replaygain_track": 0.0, "replaygain_album": 0.0,
        "replaygain_track_peak": 0.0,
        "bit_depth": 0, "duration": 0.0,
        "sample_rate": 0, "channels": 0, "bitrate": 0,
        "cover_mime": "", "cover_data": b"",
    }
    try:
        mf = MutagenFile(filepath)
        if mf is None:
            return info

        if hasattr(mf, 'info') and mf.info:
            info["duration"] = float(getattr(mf.info, 'length', 0) or 0)
            info["sample_rate"] = int(getattr(mf.info, 'sample_rate', 0) or 0)
            info["channels"] = int(getattr(mf.info, 'channels', 0) or 0)
            info["bitrate"] = int(getattr(mf.info, 'bitrate', 0) or 0)
            info["bit_depth"] = int(getattr(mf.info, 'bits_per_sample', 0) or 0)

        if not mf.tags or not hasattr(mf.tags, 'get'):
            return info
        tags = mf.tags

        def _get(*keys):
            for k in keys:
                v = tags.get(k)
                if v:
                    if isinstance(v, list):
                        return str(v[0]) if len(v) > 0 else ""
                    return str(v)
            return ""

        info["title"] = _get("title", "TIT2", "\xa9nam", "Title", "WM/Title")
        info["artist"] = _get("artist", "TPE1", "\xa9ART", "Author", "WM/Author")
        info["album"] = _get("album", "TALB", "\xa9alb", "WM/AlbumTitle", "Album")
        info["albumartist"] = _get("albumartist", "ALBUMARTIST", "album artist",
                                   "TPE2", "aART", "WM/AlbumArtist", "\xa9ART")

        date_val = _get("date", "originaldate", "TDRC", "TYER", "TDOR",
                        "TORY", "\xa9day", "WM/Year")
        info["date"] = date_val[:4] if len(date_val) >= 4 else date_val
        info["originaldate"] = _get("originaldate", "TDOR", "TORY", "ORIGINALYEAR")
        with contextlib.suppress(ValueError, TypeError):
            yd = info["date"] or info["originaldate"] or "0"
            info["year"] = int(yd[:4])

        genre = _get("genre", "TCON", "\xa9gen", "WM/Genre", "GENRE")
        if genre.startswith("(") and ")" in genre:
            genre = genre.split(")", 1)[-1].strip()
        info["genre"] = genre

        raw_track = _get("tracknumber", "TRCK", "trkn", "TRACKNUMBER",
                         "WM/TrackNumber", "Track")
        info["track_number"], info["track_total"] = _parse_track_disc(raw_track)
        raw_disc = _get("discnumber", "TPOS", "disk", "DISCNUMBER", "Disc")
        info["disc_number"], info["disc_total"] = _parse_track_disc(raw_disc)

        info["composer"] = _get("composer", "TCOM", "\xa9wrt", "WM/Composer", "Composer")
        bpm_val = _get("bpm", "TBPM", "tmpo", "BPM", "WM/BeatsPerMinute")
        with contextlib.suppress(ValueError, TypeError):
            info["bpm"] = int(float(bpm_val)) if bpm_val else 0
        info["isrc"] = _get("isrc", "TSRC", "ISRC", "WM/ISRC")
        info["label"] = _get("label", "TPUB", "\xa9pub", "LABEL",
                             "organization", "WM/Publisher")
        info["conductor"] = _get("conductor", "TPE3", "TCONDUCTOR", "Conductor")
        cp_val = _get("TCMP", "cpil", "COMPILATION", "compilation")
        info["compilation"] = 1 if cp_val.lower() in ("1", "true", "yes") else 0
        info["media_type"] = _get("TMED", "MEDIA", "sourcemedia", "WM/Media")
        info["encoder"] = _get("TENC", "TSSE", "ENCODER", "encoder", "WM/EncodedBy")
        info["copyright"] = _get("TCOP", "copyright", "COPYRIGHT", "WM/Copyright")
        info["remixer"] = _get("TPE4", "REMIXER", "remixer", "WM/ModifiedBy")
        info["grouping"] = _get("TIT1", "GRP1", "GROUPING", "grouping",
                                "WM/ContentGroupDescription")
        info["mood"] = _get("TMOO", "MOOD", "mood", "WM/Mood")

        info["mb_track_id"] = _get("MUSICBRAINZ_TRACKID", "MusicBrainz Track Id",
                                   "musicbrainz_trackid")
        info["mb_album_id"] = _get("MUSICBRAINZ_ALBUMID", "MusicBrainz Album Id",
                                   "musicbrainz_albumid")
        info["mb_albumartist_id"] = _get("MUSICBRAINZ_ALBUMARTISTID",
                                         "MusicBrainz Album Artist Id",
                                         "musicbrainz_albumartistid")

        rg = _get("REPLAYGAIN_TRACK_GAIN", "replaygain_track_gain")
        with contextlib.suppress(ValueError, TypeError):
            info["replaygain_track"] = float(rg.split(" ")[0]) if rg else 0.0
        rgp = _get("REPLAYGAIN_TRACK_PEAK", "replaygain_track_peak")
        with contextlib.suppress(ValueError, TypeError):
            info["replaygain_track_peak"] = float(rgp) if rgp else 0.0
        rga = _get("REPLAYGAIN_ALBUM_GAIN", "replaygain_album_gain")
        with contextlib.suppress(ValueError, TypeError):
            info["replaygain_album"] = float(rga.split(" ")[0]) if rga else 0.0

        info.update(_extract_cover_art(mf, tags))

    except Exception as e:
        log.debug("Mutagen tags extraction failed for %s: %s", filepath, e)
    return info


def _parse_track_disc(raw: str) -> tuple[int, int]:
    if not raw:
        return 0, 0
    s = str(raw).strip()
    if s.startswith("(") and s.endswith(")") and "," in s:
        s = s[1:-1]
    with contextlib.suppress(ValueError, TypeError):
        parts = s.split("/")
        num = int(float(parts[0]))
        total = int(float(parts[1])) if len(parts) > 1 else 0
        return num, total
    return 0, 0


def _extract_cover_art(mf, tags) -> dict:
    result: dict = {"cover_mime": "", "cover_data": b""}
    try:
        if hasattr(mf, 'pictures') and mf.pictures:
            p = mf.pictures[0]
            result["cover_mime"] = getattr(p, 'mime', 'image/jpeg')
            result["cover_data"] = getattr(p, 'data', b'')
            return result
        for key in ("APIC:", "APIC"):
            try:
                v = tags.get(key)
                if v:
                    result["cover_mime"] = getattr(v, 'mime', 'image/jpeg')
                    result["cover_data"] = getattr(v, 'data', b'')
                    return result
            except Exception:
                pass
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
    except Exception:
        pass
    return result


def extract_metadata_combined(filepath: str) -> dict:
    """Unified extraction: Mutagen > GStreamer > filename inference."""
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
    r["year"] = mg.get("year") or 0
    r["genre"] = mg.get("genre") or ""
    r["track_number"] = _p("track_number", "track_number") or inferred.get("track_number", 0) or 0
    r["track_total"] = _p("track_total", "track_total") or 0
    r["disc_number"] = mg.get("disc_number") or 0
    r["disc_total"] = mg.get("disc_total") or 0
    r["composer"] = mg.get("composer") or ""
    r["bpm"] = mg.get("bpm") or 0
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
    r["originaldate"] = mg.get("originaldate") or ""
    r["mb_track_id"] = mg.get("mb_track_id") or ""
    r["mb_album_id"] = mg.get("mb_album_id") or ""
    r["mb_albumartist_id"] = mg.get("mb_albumartist_id") or ""
    r["replaygain_track"] = mg.get("replaygain_track") or 0.0
    r["replaygain_album"] = mg.get("replaygain_album") or 0.0
    r["replaygain_track_peak"] = mg.get("replaygain_track_peak") or 0.0
    r["bit_depth"] = mg.get("bit_depth") or gst.get("bit_depth", 0) or 0
    r["duration"] = _p("duration", "duration") or 0.0
    r["sample_rate"] = _p("sample_rate", "sample_rate") or 0
    r["channels"] = _p("channels", "channels") or 0
    r["bitrate"] = _p("bitrate", "bitrate") or 0
    r["cover_mime"] = mg.get("cover_mime") or ""
    r["cover_data"] = mg.get("cover_data") or b""
    return r


def extract_metadata(filepath: str) -> dict:
    """Backward-compat: returns GStreamer-prioritized dict for legacy callers."""
    return extract_metadata_combined(filepath)


def extract_metadata_full(filepath: str) -> dict:
    """Backward-compat: full Mutagen tags for legacy callers."""
    return extract_mutagen_tags(filepath)
