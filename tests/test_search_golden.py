"""M7.7 — Golden dataset and 10k scale gates — tests.

The golden dataset exercises the full canonical pipeline: TrackRefs ->
build_music_model -> SearchCorpus -> SearchProjection, covering
case/accent insensitivity, exact-title precedence, artist/album/
album-artist/genre/composer queries, multi-token AND semantics,
unknown metadata, display-name fallback, compilation/Various Artists,
input-permutation determinism and the 10k correctness/determinism scale
baseline (no filesystem, no extraction — pure domain; M12 owns
performance).

The canonical library is the source of truth; search is a deterministic
derived projection.
"""

from pathlib import Path

from michi.domain.library import TrackRef, build_music_model
from michi.domain.search import (
    SearchQuery,
    build_search_corpus,
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
    year=0,
    disc_number=0,
    track_number=0,
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
        year=year,
        disc_number=disc_number,
        track_number=track_number,
    )


GOLDEN = (
    # TRACK A
    _track(
        "a.mp3",
        title="Blue",
        artist="Joni Mitchell",
        album="Blue",
        album_artist="Joni Mitchell",
        genre="Folk",
        composer="Joni Mitchell",
    ),
    # TRACK B
    _track(
        "b.mp3",
        title="So What",
        artist="Miles Davis",
        album="Kind of Blue",
        album_artist="Miles Davis",
        genre="Jazz",
        composer="Miles Davis",
    ),
    # TRACK C
    _track(
        "c.mp3",
        title="Time",
        artist="Hans Zimmer",
        album="Inception",
        album_artist="Hans Zimmer",
        genre="Soundtrack",
        composer="Hans Zimmer",
    ),
    # TRACK D
    _track(
        "d.mp3",
        title="Cornfield Chase",
        artist="Hans Zimmer",
        album="Interstellar",
        album_artist="Hans Zimmer",
        genre="Soundtrack",
        composer="Hans Zimmer",
    ),
    # Accented artist/title (accent-insensitive matching).
    _track(
        "e.mp3",
        title="Halo",
        artist="Beyoncé",
        album="Halo",
        album_artist="Beyoncé",
        genre="Pop",
        composer="Beyoncé",
    ),
    # Compilation / Various Artists.
    _track(
        "f.mp3",
        title="Stand",
        artist="Various Artists",
        album="Hits",
        album_artist="Various Artists",
        genre="Rock",
        composer="A Composer",
    ),
    # Same album title under two album artists (canonical identity).
    _track(
        "g.mp3",
        title="Blue",
        artist="Blue Notes",
        album="Blue",
        album_artist="Blue Notes",
        genre="Jazz",
        composer="Blue Notes",
    ),
    # Unknown metadata (canonical "Unknown Artist" placeholders).
    _track("h.mp3", title="", album=""),  # display_name fallback "h.mp3"
    # Multidisc album.
    _track(
        "i1.mp3",
        title="Overture",
        artist="Symphony",
        album="Symphony",
        album_artist="Symphony",
        genre="Classical",
        composer="Symphony",
        disc_number=1,
        track_number=1,
    ),
    _track(
        "i2.mp3",
        title="Finale",
        artist="Symphony",
        album="Symphony",
        album_artist="Symphony",
        genre="Classical",
        composer="Symphony",
        disc_number=2,
        track_number=1,
    ),
)


def _golden_world(input_order=None):
    tracks = tuple(input_order) if input_order is not None else GOLDEN
    model = build_music_model(tracks)
    corpus = build_search_corpus(
        tracks, model.albums, model.artists, model.genres, model.composers
    )
    return tracks, model, corpus


def _project(query, input_order=None):
    tracks, model, corpus = _golden_world(input_order)
    return build_search_projection(SearchQuery.from_raw(query), corpus), tracks, model


def _track_ids(projection):
    return [str(t.file_path) for t in projection.tracks]


class TestCaseAndAccentInsensitivity:
    def test_case_insensitive_equivalent(self):
        for form in ("miles", "MILES", "Miles"):
            p, *_ = _project(form)
            assert _track_ids(p) == ["/m/b.mp3"]

    def test_accent_insensitive(self):
        p, *_ = _project("beyonce")
        assert _track_ids(p) == ["/m/e.mp3"]
        p2, *_ = _project("Beyoncé")
        assert _track_ids(p2) == _track_ids(p)


class TestGoldenQueries:
    def test_exact_title_outranks_album_substring(self):
        # "blue": Joni's track titled Blue (exact title) must outrank the
        # Kind of Blue track (album substring) and Blue Notes (artist/title).
        p, *_ = _project("blue")
        ids = _track_ids(p)
        assert ids[0] == "/m/a.mp3"  # exact title first
        assert "/m/b.mp3" in ids  # album substring still matched

    def test_artist_query(self):
        p, *_ = _project("miles davis")
        assert _track_ids(p) == ["/m/b.mp3"]
        assert [a.name for a in p.artists] == ["Miles Davis"]

    def test_album_query(self):
        p, *_ = _project("kind blue")
        assert "/m/b.mp3" in _track_ids(p)
        assert any(a.title == "Kind of Blue" for a in p.albums)

    def test_album_artist_various_artists(self):
        p, *_ = _project("various artists")
        assert any(a.title == "Hits" for a in p.albums)

    def test_genre_query(self):
        p, *_ = _project("jazz")
        assert [g.name for g in p.genres] == ["Jazz"]
        assert {str(t.file_path) for t in p.tracks} >= {"/m/b.mp3", "/m/g.mp3"}

    def test_composer_query(self):
        p, *_ = _project("zimmer")
        assert [c.name for c in p.composers] == ["Hans Zimmer"]
        assert {str(t.file_path) for t in p.tracks} == {"/m/c.mp3", "/m/d.mp3"}


class TestMultiTokenGoldens:
    def test_miles_blue_across_entities(self):
        p, *_ = _project("miles blue")
        assert "/m/b.mp3" in _track_ids(p)  # miles:artist + blue:album

    def test_hans_interstellar(self):
        p, *_ = _project("hans interstellar")
        assert _track_ids(p) == ["/m/d.mp3"]
        assert any(a.title == "Interstellar" for a in p.albums)

    def test_jazz_zimmer_requires_both(self):
        p, *_ = _project("jazz zimmer")
        # No entity genuinely satisfies both tokens.
        assert _track_ids(p) == []
        assert p.albums == () and p.artists == () and p.genres == ()

    def test_multiple_whitespace_no_empty_tokens(self):
        p, *_ = _project("miles    davis")
        assert _track_ids(p) == ["/m/b.mp3"]


class TestUnknownAndFallback:
    def test_display_name_fallback(self):
        # Track h has no title: the filename-derived display_name keeps it
        # findable.
        p, *_ = _project("h.mp3")
        assert _track_ids(p) == ["/m/h.mp3"]

    def test_unknown_artist_placeholder_searchable(self):
        # Empty artist -> canonical "Unknown Artist" display value; searching
        # the placeholder finds the canonical entity (no fabrication).
        p, *_ = _project("unknown artist")
        assert any(a.name == "Unknown Artist" for a in p.artists)


class TestDeterminism:
    def test_input_permutation_same_results(self):
        p_base, *_ = _project("blue")
        shuffled = tuple(reversed(GOLDEN))
        p_shuffled, *_ = _project("blue", shuffled)
        assert _track_ids(p_shuffled) == _track_ids(p_base)
        assert [a.key for a in p_shuffled.albums] == [a.key for a in p_base.albums]

    def test_repeated_query_consistent(self):
        p1, *_ = _project("blue")
        p2, *_ = _project("blue")
        assert _track_ids(p1) == _track_ids(p2)

    def test_clear_restores_canonical(self):
        p, tracks, model = _project("blue")
        assert len(p.tracks) < len(tracks)
        cleared, *_ = _project("")
        assert cleared.tracks == ()
        assert cleared.query.active is False


class TestScale10k:
    def _synthetic(self, n):
        tracks = []
        for i in range(n):
            tracks.append(
                _track(
                    f"t{i:05}.mp3",
                    title=f"Blue Track {i % 97}",
                    artist=f"Artist {i % 131}",
                    album=f"Album {i % 23}",
                    genre=f"Genre {i % 7}",
                )
            )
        return tracks

    def test_10k_correctness_and_determinism(self):
        tracks = self._synthetic(10_000)
        model = build_music_model(tracks)
        corpus = build_search_corpus(
            tracks, model.albums, model.artists, model.genres, model.composers
        )

        def brute_force(query):
            """Independent naive implementation: every token must appear in
            at least one searchable field (casefolded substring)."""
            tokens = tuple(t for t in query.casefold().split() if t)
            matched = []
            for t in tracks:
                fields = (
                    t.title,
                    t.artist,
                    t.album,
                    t.album_artist,
                    t.genre,
                    t.composer,
                    t.display_name,
                )
                if all(any(token in f.casefold() for f in fields) for token in tokens):
                    matched.append(t)
            return matched

        # Correctness against an INDEPENDENT naive implementation (the
        # projection ranks deterministically; the SET must match exactly).
        for query in ("Artist 5", "artist 5 album 3", "blue", "zzzz"):
            expected = brute_force(query)
            p = build_search_projection(SearchQuery.from_raw(query), corpus)
            assert {t.file_path for t in p.tracks} == {t.file_path for t in expected}, (
                query
            )

        # Entity correctness against the same independent naive matching.
        def brute_force_entities(entities, query):
            tokens = tuple(t for t in query.casefold().split() if t)
            matched = []
            for entity in entities:
                fields = (entity.name,)
                if all(any(token in f.casefold() for f in fields) for token in tokens):
                    matched.append(entity)
            return matched

        p = build_search_projection(SearchQuery.from_raw("Artist 5"), corpus)
        assert {a.key for a in p.artists} == {
            a.key for a in brute_force_entities(model.artists, "Artist 5")
        }
        assert p.artist_count == len(brute_force_entities(model.artists, "Artist 5"))
        p2 = build_search_projection(SearchQuery.from_raw("Artist 5"), corpus)
        assert [t.file_path for t in p2.tracks] == [t.file_path for t in p.tracks]
        p4 = build_search_projection(SearchQuery.from_raw("zzzz"), corpus)
        assert p4.total_count == 0
