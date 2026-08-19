"""M7.2 + M7.3 — Canonical track search and deterministic ranking — RED tests.

The projector consumes the CANONICAL M6 model (TrackRef) and produces
deterministic search results: rich searchable fields (title/artist/album/
album_artist/genre/composer/display_name), AND semantics across tokens
(each token may match ANY field; cross-field matching allowed), stable
match types (EXACT > PREFIX > TOKEN_PREFIX > SUBSTRING) and deterministic
relevance (score desc -> canonical display sort -> canonical ID; never
input order).
"""

from pathlib import Path

from michi.domain.library import TrackRef
from michi.domain.search import (
    SearchCorpus,
    SearchQuery,
    build_search_projection,
)


def _track(
    name,
    title=None,
    artist=None,
    album=None,
    album_artist=None,
    genre=None,
    composer=None,
):
    return TrackRef(
        file_path=Path(f"/m/{name}"),
        display_name=name,
        title=title or "",
        artist=artist or "",
        album=album or "",
        album_artist=album_artist or "",
        genre=genre or "",
        composer=composer or "",
    )


def _project(query, *tracks):
    corpus = SearchCorpus.from_tracks(tracks)
    return build_search_projection(SearchQuery.from_raw(query), corpus)


def _ids(projection):
    return [t.file_path for t in projection.tracks]


class TestTrackFields:
    def test_matches_title(self):
        tracks = (_track("a.mp3", title="Blue"), _track("b.mp3", title="Red"))
        assert _ids(_project("blue", *tracks)) == [tracks[0].file_path]

    def test_matches_artist(self):
        tracks = (_track("a.mp3", artist="Miles Davis"), _track("b.mp3", artist="Toto"))
        assert _ids(_project("miles", *tracks)) == [tracks[0].file_path]

    def test_matches_album(self):
        tracks = (
            _track("a.mp3", album="Kind of Blue"),
            _track("b.mp3", album="Inception"),
        )
        assert _ids(_project("blue", *tracks)) == [tracks[0].file_path]

    def test_matches_album_artist(self):
        tracks = (
            _track("a.mp3", album_artist="Various Artists"),
            _track("b.mp3", album_artist="Joni Mitchell"),
        )
        assert _ids(_project("various", *tracks)) == [tracks[0].file_path]

    def test_matches_genre(self):
        tracks = (_track("a.mp3", genre="Jazz"), _track("b.mp3", genre="Folk"))
        assert _ids(_project("jazz", *tracks)) == [tracks[0].file_path]

    def test_matches_composer(self):
        tracks = (
            _track("a.mp3", composer="Hans Zimmer"),
            _track("b.mp3", composer="Joni Mitchell"),
        )
        assert _ids(_project("zimmer", *tracks)) == [tracks[0].file_path]

    def test_matches_display_name_fallback(self):
        # Empty title: the filename-derived display_name keeps the track
        # findable (preserves the bootstrap behavior).
        tracks = (_track("rare_live_take.mp3"), _track("other.mp3"))
        assert _ids(_project("rare", *tracks)) == [tracks[0].file_path]


class TestMultiToken:
    def test_tokens_can_match_across_fields(self):
        # miles -> artist; blue -> album. AND semantics across FIELDS.
        tracks = (
            _track("a.mp3", artist="Miles Davis", album="Kind of Blue"),
            _track("b.mp3", artist="Miles Davis", album="Inception"),
            _track("c.mp3", artist="Joni Mitchell", album="Blue"),
        )
        assert _ids(_project("miles blue", *tracks)) == [tracks[0].file_path]

    def test_requires_all_tokens(self):
        tracks = (
            _track("a.mp3", artist="Miles Davis", album="Kind of Blue"),
            _track("b.mp3", artist="Metallica", album="Blue"),
        )
        assert _ids(_project("miles metallica", *tracks)) == []  # no track has both

    def test_multiple_whitespace_no_empty_tokens(self):
        tracks = (_track("a.mp3", artist="Miles Davis"),)
        assert _ids(_project("miles    davis", *tracks)) == [tracks[0].file_path]

    def test_single_token_matches_one_field_is_enough(self):
        tracks = (
            _track("a.mp3", artist="Miles Davis", album="Kind of Blue"),
            _track("b.mp3", artist="Miles Davis", album="Bitches Brew"),
        )
        assert _ids(_project("blue", *tracks)) == [tracks[0].file_path]


class TestRanking:
    def test_exact_title_beats_title_prefix(self):
        tracks = (
            _track("a.mp3", title="Blue"),
            _track("b.mp3", title="Blue Moon"),
        )
        assert _ids(_project("blue", *tracks)) == [
            tracks[0].file_path,
            tracks[1].file_path,
        ]

    def test_title_prefix_beats_title_substring(self):
        tracks = (
            _track("a.mp3", title="Blue Moon"),
            _track("b.mp3", title="True Blue"),
        )
        assert _ids(_project("blue", *tracks)) == [
            tracks[0].file_path,
            tracks[1].file_path,
        ]

    def test_title_match_beats_display_name_fallback(self):
        tracks = (
            _track("blue.mp3", title="Blue"),
            _track("blue_otherwise.mp3"),  # display_name only
        )
        assert _ids(_project("blue", *tracks)) == [
            tracks[0].file_path,
            tracks[1].file_path,
        ]

    def test_field_priority_artist_beats_album(self):
        tracks = (
            _track("a.mp3", artist="Blue", album="X"),
            _track("b.mp3", artist="Y", album="Blue"),
        )
        assert _ids(_project("blue", *tracks)) == [
            tracks[0].file_path,  # exact artist beats exact album
            tracks[1].file_path,
        ]

    def test_ranking_is_deterministic(self):
        tracks = tuple(
            _track(f"t{i:02}.mp3", title="Blue", artist=f"Artist {i % 3}")
            for i in range(9)
        )
        r1 = _ids(_project("blue", *tracks))
        r2 = _ids(_project("blue", *tracks))
        assert r1 == r2  # same query, same corpus -> identical order

    def test_ranking_independent_of_input_order(self):
        tracks = tuple(
            _track(f"t{i:02}.mp3", title="Blue", artist=f"Artist {i % 3}")
            for i in range(9)
        )
        base = _ids(_project("blue", *tracks))
        shuffled = tuple(reversed(tracks))
        assert _ids(_project("blue", *shuffled)) == base  # canonical tie-breaks

    def test_substring_is_lowest_match_type(self):
        tracks = (
            _track("a.mp3", title="Blue"),
            _track("b.mp3", title="The Blue Album"),
            _track("c.mp3", title="Truest Blue Sky"),
        )
        ids = _ids(_project("blue", *tracks))
        assert ids == [tracks[0].file_path, tracks[1].file_path, tracks[2].file_path]
