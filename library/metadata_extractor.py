"""Metadata extraction — GStreamer discoverer + Mutagen full tags."""
import os
import logging

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


def extract_metadata(filepath: str) -> dict:
    """Extract duration, sample_rate, channels, bitrate, tags via GStreamer."""
    info = {"duration": 0.0, "channels": 0, "sample_rate": 0,
            "bitrate": 0, "title": "", "artist": "", "album": ""}
    try:
        uri = "file://" + os.path.abspath(filepath)
        discoverer = GstPbutils.Discoverer.new(5 * Gst.SECOND)
        disc = discoverer.discover_uri(uri)
        if disc is None:
            return info

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

        streams = disc.get_audio_streams()
        if streams:
            s = streams[0]
            info["sample_rate"] = s.get_sample_rate() or 0
            info["channels"] = s.get_channels() or 0
            info["bitrate"] = s.get_bitrate() or 0
    except Exception as e:
        logging.getLogger("astra").debug(f"Metadata extraction failed for {filepath}: {e}")
    return info


def extract_metadata_full(filepath: str) -> dict:
    """Extract full metadata including year, genre, track, composer, cover art via mutagen."""
    info = {"year": 0, "genre": "", "track_number": 0, "composer": "",
            "cover_mime": "", "cover_data": b""}
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
            info["composer"] = get_tag(mf.tags, "composer", "TPE1", "©wrt", "TCOM")
            genre_val = get_tag(mf.tags, "genre", "TCON", "©gen")
            try:
                if genre_val and genre_val.startswith("(") and ")" in genre_val:
                    genre_val = genre_val.split(")", 1)[-1].strip()
            except Exception:
                logging.getLogger("astra").debug("Genre parsing failed, using raw value")
            info["genre"] = genre_val
            year_val = get_tag(mf.tags, "date", "year", "TYER", "©day", "TDRC")
            try:
                info["year"] = int(year_val[:4]) if year_val else 0
            except Exception:
                info["year"] = 0
            track_val = get_tag(mf.tags, "tracknumber", "TRCK", "track", "trkn")
            try:
                info["track_number"] = int(track_val.split("/")[0]) if track_val else 0
            except Exception:
                info["track_number"] = 0
        for tag_type in mf or []:
            if tag_type and (b'APIC' in str(tag_type).encode() or 'APIC' in str(tag_type)):
                try:
                    cover = mf.tags.get(tag_type)
                    if cover:
                        info["cover_mime"] = cover.mime if hasattr(cover, 'mime') else "image/jpeg"
                        info["cover_data"] = cover.data if hasattr(cover, 'data') else b""
                except Exception:
                    logging.getLogger("astra").debug("Cover art APIC extraction failed")
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
                    logging.getLogger("astra").debug("Cover art key extraction failed")
        if not info["cover_data"] and hasattr(mf, 'pictures'):
            pics = getattr(mf, 'pictures', [])
            if pics:
                try:
                    p = pics[0]
                    info["cover_mime"] = getattr(p, 'mime', 'image/jpeg')
                    info["cover_data"] = getattr(p, 'data', b'')
                except Exception:
                    logging.getLogger("astra").debug("Cover art picture extraction failed")
    except Exception as e:
        logging.getLogger("astra").debug(f"Full metadata extraction failed for {filepath}: {e}")
    return info
