"""M7.4 — Canonical entity search (albums/artists/genres/composers) — RED tests.

Entity results consume the canonical M6 model directly (AlbumRef, ArtistRef,
GenreRef, ComposerRef). Albums are searchable by title, album artist, genres
and composers; artists by name; genres by name; composers by name. Ranking
is deterministic per entity; tie-break by canonical order.
"""

from michi.domain.library import AlbumRef, ArtistRef, ComposerRef, GenreRef
from michi.domain.search import (
    SearchQuery,
    build_search_corpus,
    build_search_projection,
)


def _album(key, title, artist="", genres=(), composers=()):
    return AlbumRef(
        key=key,
        title=title,
        artist=artist,
        track_count=1,
        duration_ms=0,
        genres=tuple(genres),
        composers=tuple(composers),
    )


def _album_tracks(key, title, artist="", genre="", composer=""):
    from pathlib import Path

    from michi.domain.library import TrackRef

    return TrackRef(
        file_path=Path(f"/m/{key}.mp3"),
        display_name=f"{key}.mp3",
        title=title,
        artist=artist or title,
        album=title,
        album_artist=artist,
        genre=genre,
        composer=composer,
    )


def _project(query, tracks, albums, artists, genres, composers):
    corpus = build_search_corpus(tracks, albums, artists, genres, composers)
    return build_search_projection(SearchQuery.from_raw(query), corpus)


class TestAlbumSearch:
    def test_returns_album_results(self):
        albums = (_album("a1", "Kind of Blue", artist="Miles Davis"),)
        projection = _project("blue", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_search_uses_album_artist(self):
        albums = (
            _album("a1", "Blue", artist="Joni Mitchell"),
            _album("a2", "Blue", artist="Miles Davis"),
        )
        projection = _project("joni", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_search_matches_genre(self):
        albums = (_album("a1", "Inception", genres=("Soundtrack",)),)
        projection = _project("soundtrack", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_search_matches_composer(self):
        albums = (_album("a1", "Interstellar", composers=("Hans Zimmer",)),)
        projection = _project("zimmer", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1"]

    def test_compilation_album_searchable_as_various_artists(self):
        albums = (_album("a1", "Hits", artist="Various Artists"),)
        projection = _project("various artists", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_ranking_exact_title_first(self):
        albums = (
            _album("a1", "Blue"),
            _album("a2", "Blue Moon"),
            _album("a3", "True Blue"),
        )
        projection = _project("blue", (), albums, (), (), ())
        assert [a.key for a in projection.albums] == ["a1", "a2", "a3"]

    def test_album_results_from_canonical_tracks(self):
        # The canonical pipeline: TrackRefs -> build_music_model albums.
        from michi.domain.library import build_music_model

        tracks = (
            _album_tracks("t1", "Kind of Blue", artist="Miles Davis", genre="Jazz"),
            _album_tracks("t2", "Inception", artist="Hans Zimmer"),
        )
        model = build_music_model(tracks)
        projection = _project(
            "jazz", tracks, model.albums, model.artists, model.genres, model.composers
        )
        assert [a.key for a in projection.albums] == [model.albums[0].key]
        assert [g.key for g in projection.genres] == [model.genres[0].key]


class TestArtistSearch:
    def test_returns_artist_results(self):
        artists = (
            ArtistRef(key="a1", name="Miles Davis", track_count=1, album_count=1),
        )
        projection = _project("miles", (), (), artists, (), ())
        assert [a.key for a in projection.artists] == ["a1"]

    def test_artist_prefix_match(self):
        artists = (
            ArtistRef(key="a1", name="Miles Davis", track_count=1, album_count=1),
            ArtistRef(key="a2", name="Joni Mitchell", track_count=1, album_count=1),
        )
        projection = _project("dav", (), (), artists, (), ())
        assert [a.key for a in projection.artists] == ["a1"]

    def test_artist_exact_beats_prefix(self):
        artists = (
            ArtistRef(key="a1", name="Blue", track_count=1, album_count=1),
            ArtistRef(key="a2", name="Blue Man Group", track_count=1, album_count=1),
        )
        projection = _project("blue", (), (), artists, (), ())
        assert [a.key for a in projection.artists] == ["a1", "a2"]


class TestGenreSearch:
    def test_returns_genre_results(self):
        genres = (GenreRef(key="g1", name="Jazz", track_count=1),)
        projection = _project("jazz", (), (), (), genres, ())
        assert [g.key for g in projection.genres] == ["g1"]

    def test_genre_prefix(self):
        genres = (
            GenreRef(key="g1", name="Soundtrack", track_count=1),
            GenreRef(key="g2", name="Folk", track_count=1),
        )
        projection = _project("sound", (), (), (), genres, ())
        assert [g.key for g in projection.genres] == ["g1"]


class TestComposerSearch:
    def test_returns_composer_results(self):
        composers = (ComposerRef(key="c1", name="Hans Zimmer", track_count=1),)
        projection = _project("zimmer", (), (), (), (), composers)
        assert [c.key for c in projection.composers] == ["c1"]

    def test_composer_prefix(self):
        composers = (
            ComposerRef(key="c1", name="Hans Zimmer", track_count=1),
            ComposerRef(key="c2", name="Joni Mitchell", track_count=1),
        )
        projection = _project("zimm", (), (), (), (), composers)
        assert [c.key for c in projection.composers] == ["c1"]


class TestEntityCounts:
    def test_counts_reflect_results(self):
        albums = (_album("a1", "Kind of Blue"),)
        artists = (ArtistRef(key="a1", name="Blue Note", track_count=1, album_count=1),)
        projection = _project("blue", (), albums, artists, (), ())
        assert projection.album_count == 1
        assert projection.artist_count == 1
        assert projection.total_count == 2

    def test_no_results_empty_projection(self):
        albums = (_album("a1", "Inception"),)
        projection = _project("zzz", (), albums, (), (), ())
        assert projection.album_count == 0
        assert projection.total_count == 0
