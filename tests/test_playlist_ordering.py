"""Tests for playlist ordering service."""
from __future__ import annotations

from library.playlists.playlist_ordering import (
    order_by_title, order_by_artist, order_by_quality,
    alternate_artists, order_by_bpm, random_weighted,
)
from library.playlists.playlist_models import PlaylistTrackRef


def _t(title="Song", artist="Artist", duration=200.0, quality="lossless",
        bpm=120.0, album="Album"):
    return PlaylistTrackRef(title=title, artist=artist, duration=duration,
                            quality_kind=quality, bpm=bpm, album=album)


class TestPlaylistOrdering:

    def test_order_by_title(self):
        tracks = [_t(title="Z"), _t(title="A"), _t(title="M")]
        ordered = order_by_title(tracks)
        assert ordered[0].title == "A"
        assert ordered[1].title == "M"
        assert ordered[2].title == "Z"

    def test_order_by_artist(self):
        tracks = [_t(artist="Zeta"), _t(artist="Alpha")]
        ordered = order_by_artist(tracks)
        assert ordered[0].artist == "Alpha"

    def test_order_by_quality(self):
        tracks = [
            _t(quality="lossy"),
            _t(quality="hires"),
            _t(quality="lossless"),
        ]
        ordered = order_by_quality(tracks)
        assert ordered[0].quality_kind == "hires"

    def test_order_by_bpm(self):
        tracks = [_t(bpm=140), _t(bpm=80), _t(bpm=120)]
        ordered = order_by_bpm(tracks)
        assert ordered[0].bpm == 80
        assert ordered[2].bpm == 140

    def test_alternate_artists(self):
        tracks = [
            _t(title="A1", artist="X"),
            _t(title="A2", artist="X"),
            _t(title="B1", artist="Y"),
        ]
        ordered = alternate_artists(tracks)
        # All tracks preserved
        assert len(ordered) == 3

    def test_random_weighed_preserves_all(self):
        tracks = [_t(title=f"S{i}") for i in range(10)]
        ordered = random_weighted(tracks)
        assert len(ordered) == 10
        assert set(t.title for t in ordered) == set(t.title for t in tracks)
