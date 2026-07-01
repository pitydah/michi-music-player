"""Playlist ordering service — manual and smart reordering."""
from __future__ import annotations

import random
from collections import defaultdict

from library.playlists.playlist_models import PlaylistTrackRef

_KEY_CHROMATIC = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_KEY_TO_INDEX = {k: i for i, k in enumerate(_KEY_CHROMATIC)}
_KEY_CAMELOT = {f"{n}{l}": i for i, (n, l) in enumerate([(n, l) for n in range(1, 13) for l in ("A", "B")])}


def order_by_title(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.title or "").lower())


def order_by_artist(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.artist or "").lower() + (t.title or "").lower())


def order_by_album(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.album or "").lower() + str(t.position or 0))


def order_by_year(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.year or 9999))


def order_by_duration(tracks: list[PlaylistTrackRef], reverse: bool = False) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: t.duration, reverse=reverse)


def order_by_quality(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    quality_order = {"dsd": 0, "hires": 1, "lossless": 2, "lossy": 3, "unknown": 4}
    return sorted(tracks, key=lambda t: (quality_order.get(t.quality_kind, 4), -(t.sample_rate or 0), -(t.bit_depth or 0)))


def order_by_bpm(tracks: list[PlaylistTrackRef], reverse: bool = False) -> list[PlaylistTrackRef]:
    return sorted(tracks, key=lambda t: (t.bpm or 0), reverse=reverse)


def order_by_key(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    def _key_index(t):
        if t.key in _KEY_TO_INDEX: return _KEY_TO_INDEX[t.key]
        if t.key in _KEY_CAMELOT: return _KEY_CAMELOT[t.key]
        return 999
    return sorted(tracks, key=_key_index)


def alternate_artists(tracks: list[PlaylistTrackRef]) -> list[PlaylistTrackRef]:
    if not tracks: return tracks
    buckets = defaultdict(list)
    for t in tracks:
        buckets[(t.artist or t.albumartist or "").lower()].append(t)
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
    if not tracks: return tracks
    albums = defaultdict(list)
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
    result = list(tracks)
    random.shuffle(result)
    return result
