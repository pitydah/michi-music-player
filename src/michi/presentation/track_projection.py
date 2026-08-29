"""Shared display projection for canonical Library track facts."""

from pathlib import Path

from michi.application.audio_quality import make_track_quality_label
from michi.application.library_format import normalize_track_format
from michi.domain.library import (
    TrackRef,
    make_album_key,
    make_artist_key,
    resolve_album_artist,
)


def project_track_row(ref: TrackRef, *, artwork_path: str = "") -> dict:
    """Project one TrackRef without inferring output or quality claims.

    ``trackId`` is the STABLE library identity (legacy-path:: fallback for
    pre-catalog records only); the raw path stays visible as factual
    location (M6-EXT-R4-F)."""
    format_facts = normalize_track_format(
        ref.codec, ref.container, ref.file_path, ref.sample_rate_hz
    )
    album_title = ref.album.strip() or "Unknown Album"
    album_artist = resolve_album_artist(ref).strip() or "Unknown Artist"
    return {
        "trackId": ref.track_id or f"legacy-path::{ref.file_path}",
        "mediaFileId": ref.media_file_id,
        "librarySourceId": ref.library_source_id,
        "availability": ref.availability.value,
        "displayName": ref.display_name,
        "title": ref.title or ref.display_name,
        "artist": ref.artist,
        "artistKey": make_artist_key(ref.artist.strip() or "Unknown Artist"),
        "album": ref.album,
        "albumArtist": album_artist,
        "albumKey": make_album_key(album_title, album_artist),
        "durationMs": ref.duration_ms,
        "path": str(ref.file_path),
        "artworkPath": artwork_path,
        "qualityLabel": make_track_quality_label(ref),
        "codec": ref.codec,
        "container": ref.container,
        "formatKey": format_facts.key,
        "formatLabel": format_facts.label,
        "dsdRate": format_facts.dsd_rate,
        "sampleRateHz": ref.sample_rate_hz,
        "bitDepth": ref.bit_depth,
        "bitrateBps": ref.bitrate_bps,
        "channels": ref.channels,
        "fileSize": ref.file_size,
        "genre": ref.genre,
        "composer": ref.composer,
        "year": ref.year,
        "trackNumber": ref.track_number,
        "discNumber": ref.disc_number,
    }


def project_unavailable_track(path: str | Path) -> dict:
    """Project a persisted path whose Library metadata is unavailable.

    The projected ``trackId`` is the documented legacy-path fallback
    identity (``legacy-path::<path>``) — the same fallback the search and
    sort layers use for pre-catalog records (M6-EXT-R4-F)."""
    file_path = Path(path)
    return {
        "trackId": f"legacy-path::{file_path}",
        "displayName": file_path.stem,
        "title": file_path.stem,
        "artist": "",
        "artistKey": "",
        "album": "",
        "albumKey": "",
        "durationMs": 0,
        "path": str(file_path),
        "artworkPath": "",
        "qualityLabel": "",
        "codec": "",
        "container": "",
        "formatKey": "unknown",
        "formatLabel": "UNKNOWN",
        "dsdRate": "",
        "sampleRateHz": 0,
        "bitDepth": 0,
        "bitrateBps": 0,
        "channels": 0,
        "fileSize": 0,
        "genre": "",
        "composer": "",
        "year": 0,
        "trackNumber": 0,
        "discNumber": 0,
        "unavailable": True,
    }
