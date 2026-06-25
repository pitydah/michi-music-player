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


def _mutagen_basic(filepath: str) -> dict:
    """Extract basic metadata (title, artist, album, duration, etc.) via mutagen."""
    info = {"title": "", "artist": "", "album": "", "albumartist": "",
            "date": "", "tracknumber": 0, "trackcount": 0,
            "duration": 0.0, "sample_rate": 0, "channels": 0, "bitrate": 0}
    try:
        from mutagen import File as MutagenFile
        mf = MutagenFile(filepath)
        if mf is None:
            return info
        if mf.tags and hasattr(mf.tags, 'get'):
            def _get(*keys):
                for k in keys:
                    v = mf.tags.get(k)
                    if v:
                        return str(v[0]) if isinstance(v, list) else str(v)
                return ""
            info["title"] = _get("title", "TIT2", "\xa9nam")
            info["artist"] = _get("artist", "TPE1", "\xa9ART")
            info["album"] = _get("album", "TALB", "\xa9alb")
            info["albumartist"] = _get(
                "albumartist", "ALBUMARTIST", "TPE2", "aART", "\u00a9ART")
            date_val = _get("date", "TDRC", "TYER", "\u00a9day")
            if date_val:
                info["date"] = date_val[:4] if len(date_val) >= 4 else date_val
            tn = _get("tracknumber", "TRCK")
            if tn:
                info["tracknumber"] = int(tn.split("/")[0]) if tn.split("/")[0].isdigit() else 0
                if "/" in tn:
                    parts = tn.split("/")
                    info["trackcount"] = int(parts[1]) if parts[1].isdigit() else 0
        if hasattr(mf, 'info') and mf.info:
            if getattr(mf.info, 'length', 0):
                info["duration"] = float(mf.info.length)
            info["sample_rate"] = getattr(mf.info, 'sample_rate', 0) or 0
            info["channels"] = getattr(mf.info, 'channels', 0) or 0
            info["bitrate"] = getattr(mf.info, 'bitrate', 0) or 0
    except Exception as e:
        log.debug("Mutagen basic extraction failed for %s: %s", filepath, e)
    return info


def _merge_into(target: dict, source: dict, fields: list[str]):
    """Copy non-empty/zero values from source into target for given fields."""
    for f in fields:
        sv = source.get(f)
        if sv is None:
            continue
        tv = target.get(f)
        if f in ("duration", "sample_rate", "channels", "bitrate",
                 "tracknumber", "trackcount"):
            if (tv or 0) <= 0 and (sv or 0) > 0:
                target[f] = sv
        elif f in ("date",):
            if not tv and sv:
                target[f] = sv
        else:
            if not tv and sv:
                target[f] = sv


def extract_metadata(filepath: str) -> dict:
    """Extract duration, sample_rate, channels, bitrate, tags via GStreamer + Mutagen.

    Falls back to mutagen for basic fields GStreamer misses, then to
    filename inference for artist/title.
    """
    info = {"duration": 0.0, "channels": 0, "sample_rate": 0,
            "bitrate": 0, "title": "", "artist": "", "album": "",
            "albumartist": "", "date": "", "tracknumber": 0,
            "trackcount": 0}

    gst_failed = False
    try:
        uri = _safe_uri(filepath)
        discoverer = _get_discoverer()
        disc = discoverer.discover_uri(uri)
        if disc is None:
            gst_failed = True
        else:
            dur = disc.get_duration()
            if dur > 0:
                info["duration"] = dur / 1e9

            tags = disc.get_tags()
            if tags:
                ok, v = tags.get_string(Gst.TAG_TITLE)
                if ok:
                    info["title"] = v
                ok, v = tags.get_string(Gst.TAG_ARTIST)
                if ok:
                    info["artist"] = v
                ok, v = tags.get_string(Gst.TAG_ALBUM)
                if ok:
                    info["album"] = v
                ok, v = tags.get_string(Gst.TAG_ALBUM_ARTIST)
                if ok:
                    info["albumartist"] = v
                ok, v = tags.get_string(Gst.TAG_DATE)
                if ok:
                    info["date"] = v
                ok, v = tags.get_uint(Gst.TAG_TRACK_NUMBER)
                if ok:
                    info["tracknumber"] = v
                ok, v = tags.get_uint(Gst.TAG_TRACK_COUNT)
                if ok:
                    info["trackcount"] = v

            streams = disc.get_audio_streams()
            if streams:
                s = streams[0]
                info["sample_rate"] = s.get_sample_rate() or 0
                info["channels"] = s.get_channels() or 0
                info["bitrate"] = s.get_bitrate() or 0
    except Exception as e:
        gst_failed = True
        log.debug("GStreamer metadata failed for %s: %s", filepath, e)

    # Mutagen fallback for fields GStreamer missed
    if gst_failed or not info["title"] or not info["artist"] or info["duration"] <= 0:
        mg = _mutagen_basic(filepath)
        _merge_into(info, mg, ["title", "artist", "album", "albumartist",
                                "date", "tracknumber", "trackcount",
                                "duration", "sample_rate", "channels", "bitrate"])

    # Filename inference as last resort
    if not info["title"] or not info["artist"]:
        inferred = _infer_from_filename(filepath)
        if not info["title"] and inferred.get("title"):
            info["title"] = inferred["title"]
        if not info["artist"] and inferred.get("artist"):
            info["artist"] = inferred["artist"]

    return info


def extract_metadata_full(filepath: str) -> dict:
    """Extract full metadata: year, genre, composer, ISRC, etc. via mutagen."""
    info = {"year": 0, "genre": "", "track_number": 0, "composer": "",
            "cover_mime": "", "cover_data": b"", "albumartist": "",
            "disc_number": 0, "disc_total": 0, "track_total": 0,
            "originaldate": "", "mb_albumartist_id": "",
            "mb_album_id": "", "mb_track_id": "",
            "replaygain_track": 0.0, "replaygain_track_peak": 0.0,
            "replaygain_album": 0.0, "bit_depth": 0, "bpm": 0,
            "isrc": "", "label": "", "conductor": "",
            "compilation": 0, "media_type": "", "encoder": "",
            "copyright": "", "remixer": "", "grouping": "", "mood": ""}
    try:
        from mutagen import File as MutagenFile
        mf = MutagenFile(filepath)
        if mf is None:
            return info
        if mf.tags and hasattr(mf.tags, 'get'):
            def get_tag(tags, *names):
                for n in names:
                    val = tags.get(n)
                    if val:
                        if isinstance(val, list):
                            return str(val[0])
                        return str(val)
                return ""
            info["composer"] = get_tag(mf.tags, "composer", "TPE1", "\u00a9wrt", "TCOM")
            info["albumartist"] = get_tag(mf.tags,
                "albumartist", "ALBUMARTIST", "album artist",
                "TPE2", "aART", "\u00a9ART")
            genre_val = get_tag(mf.tags, "genre", "TCON", "\u00a9gen")
            try:
                if genre_val and genre_val.startswith("(") and ")" in genre_val:
                    genre_val = genre_val.split(")", 1)[-1].strip()
            except Exception:
                pass
            info["genre"] = genre_val
            year_val = get_tag(mf.tags, "date", "year", "TYER", "\u00a9day", "TDRC")
            try:
                info["year"] = int(year_val[:4]) if year_val else 0
            except Exception:
                info["year"] = 0
            track_val = get_tag(mf.tags, "tracknumber", "TRCK", "track", "trkn")
            try:
                info["track_number"] = int(track_val.split("/")[0]) if track_val else 0
                info["track_total"] = int(track_val.split("/")[1]) if track_val and "/" in track_val else 0
            except Exception:
                info["track_number"] = 0
            disc_val = get_tag(mf.tags, "discnumber", "TPOS", "disc")
            try:
                info["disc_number"] = int(disc_val.split("/")[0]) if disc_val else 0
                info["disc_total"] = int(disc_val.split("/")[1]) if disc_val and "/" in disc_val else 0
            except Exception:
                pass
            info["originaldate"] = get_tag(mf.tags, "originaldate", "ORIGINALYEAR",
                                            "TDOR", "TORY", "\u00a9day")
            info["mb_albumartist_id"] = get_tag(mf.tags,
                "MUSICBRAINZ_ALBUMARTISTID", "MusicBrainz Album Artist Id",
                "MUSICBRAINZ_ALBUMARTISTID:")
            info["mb_album_id"] = get_tag(mf.tags,
                "MUSICBRAINZ_ALBUMID", "MusicBrainz Album Id",
                "MUSICBRAINZ_ALBUMID:")
            info["mb_track_id"] = get_tag(mf.tags,
                "MUSICBRAINZ_TRACKID", "MusicBrainz Track Id",
                "MUSICBRAINZ_TRACKID:")
            bpm_val = get_tag(mf.tags, "bpm", "TBPM", "BPM")
            with contextlib.suppress(ValueError, Exception):
                info["bpm"] = int(float(bpm_val)) if bpm_val else 0
            rg_track = get_tag(mf.tags, "REPLAYGAIN_TRACK_GAIN",
                                "replaygain_track_gain")
            with contextlib.suppress(ValueError, Exception):
                info["replaygain_track"] = float(rg_track.split(" ")[0]) if rg_track else 0.0
            rg_track_peak = get_tag(mf.tags, "REPLAYGAIN_TRACK_PEAK",
                                     "replaygain_track_peak")
            with contextlib.suppress(ValueError, Exception):
                info["replaygain_track_peak"] = float(rg_track_peak) if rg_track_peak else 0.0
            rg_album = get_tag(mf.tags, "REPLAYGAIN_ALBUM_GAIN",
                                "replaygain_album_gain")
            with contextlib.suppress(ValueError, Exception):
                info["replaygain_album"] = float(rg_album.split(" ")[0]) if rg_album else 0.0
            info["isrc"] = get_tag(mf.tags, "TSRC", "ISRC", "isrc")
            info["label"] = get_tag(mf.tags, "TPUB", "label", "LABEL", "\u00a9pub")
            info["conductor"] = get_tag(mf.tags, "TPE3", "conductor", "TCONDUCTOR")
            cp_val = get_tag(mf.tags, "TCMP", "cpil")
            if cp_val:
                info["compilation"] = 1 if cp_val in ("1", "true", "True") else 0
            info["media_type"] = get_tag(mf.tags, "TMED", "MEDIA", "sourcemedia")
            info["encoder"] = get_tag(mf.tags, "TENC", "TSSE")
            info["copyright"] = get_tag(mf.tags, "TCOP", "copyright")
            info["remixer"] = get_tag(mf.tags, "TPE4", "REMIXER")
            info["grouping"] = get_tag(mf.tags, "TIT1", "GRP1", "GROUPING")
            info["mood"] = get_tag(mf.tags, "TMOO", "MOOD")
            if hasattr(mf, 'info') and hasattr(mf.info, 'bits_per_sample'):
                info["bit_depth"] = mf.info.bits_per_sample
            elif hasattr(mf, 'info') and mf.info is not None:
                bps = getattr(mf.info, 'bits_per_sample', 0)
                if bps:
                    info["bit_depth"] = bps
            # Mutagen basic fallback for title/artist/album if missing
            _merge_into(info, _mutagen_basic(filepath),
                        ["title", "artist", "album", "albumartist", "date",
                         "duration", "sample_rate", "channels", "bitrate"])
        for tag_type in mf or []:
            if tag_type and (b'APIC' in str(tag_type).encode() or 'APIC' in str(tag_type)):
                try:
                    cover = mf.tags.get(tag_type)
                    if cover:
                        info["cover_mime"] = cover.mime if hasattr(cover, 'mime') else "image/jpeg"
                        info["cover_data"] = cover.data if hasattr(cover, 'data') else b""
                except Exception:
                    pass
                break
        if not info["cover_data"]:
            for key in (b'APIC:', 'APIC:'):
                try:
                    val = mf.tags.get(key)
                    if val:
                        info["cover_mime"] = getattr(val, 'mime', 'image/jpeg')
                        info["cover_data"] = getattr(val, 'data', b'')
                        break
                except Exception:
                    pass
        if not info["cover_data"] and hasattr(mf, 'pictures'):
            pics = getattr(mf, 'pictures', [])
            if pics:
                try:
                    p = pics[0]
                    info["cover_mime"] = getattr(p, 'mime', 'image/jpeg')
                    info["cover_data"] = getattr(p, 'data', b'')
                except Exception:
                    pass
    except Exception as e:
        log.debug("Full metadata extraction failed for %s: %s", filepath, e)
    return info
