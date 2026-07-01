"""Playlist ordering service — manual and smart reordering."""
from __future__ import annotations

import random

from library.playlists.playlist_models import PlaylistTrackRef

# Key ordering helpers
_KEY_CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_KEY_TO_INDEX = {k: i for i, k in enumerate(_KEY_CHROMATIC)}
_KEY_CAMELOT = {
    "1A": 0, "2A": 1, "3A": 2, "4A": 3, "5A": 4, "6A": 5,
    "7A": 6, "8A": 7, "9A": 8, "10A": 9, "11A": 10, "12A": 11,
    "1B": 12, "2B": 13, "3B": 14, "4B": 15, "5B": 16, "6B": 17,
    "7B": 18, "8B": 19, "9B": 20, "10B": 21, "11B": 22, "12B": 23,
}


def order_by_title(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.title or "").lower())


def order_by_artist(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.artist or "").lower() + (t.title or "").lower())


def order_by_album(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.album or "").lower() + (t.position or 0))


def order_by_year(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.year or 9999))


def order_by_duration(tracks: list[PlaylistTrackRef], reverse: bool = False) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: t.duration, reverse=reverse)


def order_by_quality(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    quality_order = {"dsd": 0, "hires": 1, "lossless": 2, "lossy": 3, "unknown": 4}
    return sorted(tracks, key=lambda t: (
        quality_order.get(t.quality_kind, 4),
        -(t.sample_rate or 0),
        -(t.bit_depth or 0),
    ))


def order_by_bpm(tracks: list[PlaylistTrackRef], reverse: bool = False) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.bpm or 0), reverse=reverse)


def order_by_key(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    def _key_index(t):
        if t.key in _KEY_TO_INDEX:
            return _KEY_TO_INDEX[t.key]
        if t.key in _KEY_CAMELOT:
            return _KEY_CAMELOT[t.key]
        return 999
    return sorted(tracks, key=_key_index)


def alternate_artists(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    """Alternate between different artists to avoid consecutive same-artist."""
    if not tracks:
        return tracks
    buckets: dict[str, list[PlaylistTrackRef]] = {}
    for t in tracks:
        key = (t.artist or t.albumartist or "").lower()
        buckets.setdefault(key, []).append(t)
    artists = list(buckets.keys())
    random.shuffle(artists)
    result = []
    while any(buckets.values()):
        for a in list(buckets.keys()):
            if buckets[a]:
                result.append(buckets[a].pop(0))
            if not buckets[a]:
                del buckets[a]
    return result


def avoid_same_album(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    """Reorder so that songs from the same album are spread out."""
    if not tracks:
        return tracks
    from collections import defaultdict
    albums: dict[str, list[PlaylistTrackRef]] = defaultdict(list)
    for t in tracks:
        albums[(t.album or "").lower()].append(t)
    result = []
    sorted_albums = list(albums.keys())
    random.shuffle(sorted_albums)
    while any(albums.values()):
        for a in sorted_albums:
            if albums[a]:
                result.append(albums[a].pop(0))
    return result


def random_weighted(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    """Fisher-Yates shuffle."""
    result = list(tracks)
    random.shuffle(result)
    return result
