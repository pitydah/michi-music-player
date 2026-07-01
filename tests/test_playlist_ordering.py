"""Tests for playlist ordering service."""
from __future__ import annotations

from library.playlists.playlist_ordering import order_by_title, order_by_artist, order_by_quality, order_by_bpm, alternate_artists, random_weighted
from library.playlists.playlist_models import PlaylistTrackRef


def _t(title="S", artist="A", duration=200.0, quality="lossless", bpm=120.0, album="Al"):
    return PlaylistTrackRef(title=title, artist=artist, duration=duration, quality_kind=quality, bpm=bpm, album=album)


class TestPlaylistOrdering:
    def test_title(self):
        o = order_by_title([_t(title="Z"), _t(title="A")])
        assert o[0].title == "A"

    def test_artist(self):
        o = order_by_artist([_t(artist="Z"), _t(artist="A")])
        assert o[0].artist == "A"

    def test_quality(self):
        o = order_by_quality([_t(quality="lossy"), _t(quality="hires")])
        assert o[0].quality_kind == "hires"

    def test_bpm(self):
        o = order_by_bpm([_t(bpm=140), _t(bpm=80)])
        assert o[0].bpm == 80

    def test_alternate(self):
        o = alternate_artists([_t(title="A1", artist="X"), _t(title="A2", artist="X"), _t(title="B1", artist="Y")])
        assert len(o) == 3

    def test_random_preserves(self):
        t = [_t(title=f"S{i}") for i in range(10)]
        assert len(random_weighted(t)) == 10
