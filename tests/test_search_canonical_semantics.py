"""M7-CANONICAL-SEMANTICS-AND-RANKING-CORRECTION — Phase-1 RED tests.

Four corrections, all proving that M7 search semantics == M6 canonical
semantics:

P1 #1 — Track search must use M6's SINGLE canonical album-artist resolver
(resolve_album_artist): a compilation with empty album_artist resolves to
"Various Artists" for BOTH the canonical album grouping and the search
representation — no duplicate rule in search.
P1 #2 — Album entity ranking must be title-first: an exact album title
outranks an exact album-artist match on another album (title is the
identity-bearing field).
P2 #1 — Track tie-break must honor the canonical sort_title
(sort_title or title) before the canonical track id.
P2 #2 — The bridge must expose the composer entity rows as a consumable
Property (albums/artists/genres already are).
Plus: all six album modes must share the SAME filtered canonical AlbumIds
(keys, not counts).
"""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata, TrackRef, build_music_model
from michi.domain.search import (
    SearchQuery,
    build_search_corpus,
    build_search_projection,
)
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner


def _track(
    name,
    title=None,
    artist=None,
    album=None,
    album_artist=None,
    genre=None,
    composer=None,
    compilation=False,
    sort_title=None,
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
        compilation=compilation,
        sort_title=sort_title or "",
    )


def _world(*tracks):
    model = build_music_model(tracks)
    corpus = build_search_corpus(
        tracks, model.albums, model.artists, model.genres, model.composers
    )
    return tracks, model, corpus


def _project(query, tracks):
    _, _, corpus = _world(*tracks)
    return build_search_projection(SearchQuery.from_raw(query), corpus)


def _project_seq(query, tracks):
    model = build_music_model(tracks)
    corpus = build_search_corpus(
        tracks, model.albums, model.artists, model.genres, model.composers
    )
    return build_search_projection(SearchQuery.from_raw(query), corpus)


def _track_ids(projection):
    return [str(t.file_path) for t in projection.tracks]


class TestCanonicalAlbumArtist:
    def test_track_search_uses_resolved_compilation_album_artist(self):
        # a-ha / 80s Collection / compilation=True / album_artist="" — M6
        # resolves the album artist to "Various Artists".
        track = _track(
            "a.mp3",
            title="Take On Me",
            artist="a-ha",
            album="80s Collection",
            compilation=True,
        )
        projection = _project("Various Artists", [track])
        assert _track_ids(projection) == ["/m/a.mp3"]
        assert any(a.title == "80s Collection" for a in projection.albums)
        # Track + Album agree on the SAME resolved canonical artist.
        album = next(a for a in projection.albums)
        assert album.artist == "Various Artists"

    def test_compilation_tracks_searchable_as_various_artists(self):
        tracks = (
            _track(
                "a.mp3",
                title="Take On Me",
                artist="a-ha",
                album="80s Collection",
                compilation=True,
            ),
            _track(
                "b.mp3",
                title="Everybody Wants",
                artist="Tears for Fears",
                album="80s Collection",
                compilation=True,
            ),
        )
        projection = _project("various artists", tracks)
        assert set(_track_ids(projection)) == {"/m/a.mp3", "/m/b.mp3"}
        albums = [a for a in projection.albums if a.title == "80s Collection"]
        assert len(albums) == 1  # ONE canonical album for the compilation
        assert albums[0].artist == "Various Artists"

    def test_explicit_album_artist_wins_for_search(self):
        # Explicit album_artist beats the compilation fallback.
        track = _track(
            "a.mp3",
            title="T1",
            artist="Guest Artist",
            album_artist="Main Ensemble",
            compilation=True,
        )
        projection = _project("Main Ensemble", [track])
        assert _track_ids(projection) == ["/m/a.mp3"]
        assert any(a.artist == "Main Ensemble" for a in projection.albums)

    def test_artist_fallback_wins_for_search(self):
        # No album_artist, no compilation -> the track's own artist.
        track = _track("a.mp3", title="So What", artist="Miles Davis", album="K")
        projection = _project("miles", [track])
        assert _track_ids(projection) == ["/m/a.mp3"]

    def test_track_and_album_agree_on_non_compilation(self):
        track = _track("a.mp3", title="So What", artist="Miles Davis", album="K")
        projection = _project("miles davis", [track])
        assert _track_ids(projection) == ["/m/a.mp3"]
        assert any(a.artist == "Miles Davis" for a in projection.albums)


class TestAlbumTitleRanking:
    def test_album_exact_title_beats_exact_album_artist(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Blue",
                artist="Joni Mitchell",
                track_count=1,
                duration_ms=0,
            ),
            AlbumRef(
                key="a2",
                title="Something Else",
                artist="Blue",
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("blue"), corpus)
        assert [a.key for a in projection.albums] == ["a1", "a2"]

    def test_album_title_prefix_beats_album_artist_prefix(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Interstellar",
                artist="Hans Zimmer",
                track_count=1,
                duration_ms=0,
            ),
            AlbumRef(
                key="a2",
                title="Other",
                artist="Interstellar Ensemble",
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("inter"), corpus)
        assert [a.key for a in projection.albums] == ["a1", "a2"]

    def test_album_artist_match_still_returns_album(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Kind of Blue",
                artist="Miles Davis",
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("miles"), corpus)
        assert [a.key for a in projection.albums] == ["a1"]

    def test_composer_match_still_returns_album(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Interstellar",
                artist="",
                composers=("Hans Zimmer",),
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("zimmer"), corpus)
        assert [a.key for a in projection.albums] == ["a1"]

    def test_genre_match_still_returns_album(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Kind of Blue",
                artist="",
                genres=("Jazz",),
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("jazz"), corpus)
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_multi_token_cross_field(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Kind of Blue",
                artist="Miles Davis",
                track_count=1,
                duration_ms=0,
            ),
        )
        corpus = build_search_corpus((), albums, (), (), ())
        projection = build_search_projection(SearchQuery.from_raw("miles blue"), corpus)
        assert [a.key for a in projection.albums] == ["a1"]

    def test_album_title_semantic_priority_is_deterministic(self):
        from michi.domain.library import AlbumRef

        albums = (
            AlbumRef(
                key="a1",
                title="Blue",
                artist="Joni Mitchell",
                track_count=1,
                duration_ms=0,
            ),
            AlbumRef(
                key="a2",
                title="Blue Sky",
                artist="Blue Sky Band",
                track_count=1,
                duration_ms=0,
            ),
            AlbumRef(
                key="a3", title="Other", artist="Blue", track_count=1, duration_ms=0
            ),
        )
        r1 = build_search_projection(
            SearchQuery.from_raw("blue"), build_search_corpus((), albums, (), (), ())
        )
        r2 = build_search_projection(
            SearchQuery.from_raw("blue"),
            build_search_corpus((), tuple(reversed(albums)), (), (), ()),
        )
        assert [a.key for a in r1.albums] == [a.key for a in r2.albums]


class TestTrackSortTitleTieBreak:
    def test_track_tie_break_uses_sort_title(self):
        # Equal search scores (same title field match type) -> canonical
        # sort metadata decides: "Beatles, The" < "Tribe, A".
        tracks = (
            _track("a.mp3", title="The Beatles", artist="X", sort_title="Beatles, The"),
            _track("b.mp3", title="A Tribe", artist="X", sort_title="Tribe, A"),
        )
        # Give both tracks the same query field match: search by artist X
        # matches both equally -> tie -> sort_title must decide.
        projection = _project_seq("x", tracks)
        assert _track_ids(projection) == ["/m/a.mp3", "/m/b.mp3"]

    def test_track_tie_break_still_independent_of_input_order(self):
        tracks = (
            _track("a.mp3", title="The Beatles", artist="X", sort_title="Beatles, The"),
            _track("b.mp3", title="A Tribe", artist="X", sort_title="Tribe, A"),
        )
        base = _track_ids(_project("x", tracks))
        flipped = _track_ids(_project_seq("x", list(reversed(tracks))))
        assert base == flipped

    def test_title_fallback_when_sort_title_empty(self):
        tracks = (
            _track("a.mp3", title="Zebra", artist="X"),
            _track("b.mp3", title="Alpha", artist="X"),
        )
        projection = _project_seq("x", tracks)
        assert _track_ids(projection) == ["/m/b.mp3", "/m/a.mp3"]  # title order


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _service_library(tmp_path):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    paths = []
    for name in ("c.mp3", "d.mp3"):
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    audio = FakeAudioPort()
    queue = QueueService(PlaybackService(audio))
    library = LibraryService(FakeScanner(paths), queue, FakeExtractor(factory=_factory))
    library.scan(str(music))
    return library, music


def _factory(path):
    meta = {
        "c.mp3": dict(
            title="Time", artist="Hans Zimmer", album="Inception", genre="Soundtrack"
        ),
        "d.mp3": dict(
            title="Cornfield Chase",
            artist="Hans Zimmer",
            album="Interstellar",
            genre="Soundtrack",
        ),
    }[path.name]
    return TrackMetadata(
        title=meta["title"],
        artist=meta["artist"],
        album=meta["album"],
        album_artist=meta["artist"],
        genre=meta["genre"],
        composer=meta["artist"],
        duration_ms=1000,
    )


class TestBridgeComposers:
    def test_bridge_exposes_composer_rows(self, tmp_path):
        library, music = _service_library(tmp_path)
        bridge = LibraryBridge(library)
        rows = bridge.property("composers")
        assert [r["name"] for r in rows] == ["Hans Zimmer"]
        assert rows[0]["trackCount"] == 2
        bridge.dispose()

    def test_bridge_composers_follow_active_search(self, tmp_path):
        library, music = _service_library(tmp_path)
        bridge = LibraryBridge(library)
        library.search("zzz")
        assert bridge.property("composers") == []  # filtered like the others
        library.clear_search()
        assert [r["name"] for r in bridge.property("composers")] == ["Hans Zimmer"]
        bridge.dispose()

    def test_bridge_composers_clear_search_restores_canonical(self, tmp_path):
        library, music = _service_library(tmp_path)
        bridge = LibraryBridge(library)
        canonical = [r["key"] for r in bridge.property("composers")]
        library.search("zimmer")
        assert [r["key"] for r in bridge.property("composers")] == canonical
        library.clear_search()
        assert [r["key"] for r in bridge.property("composers")] == canonical
        bridge.dispose()


class TestSixViewsShareFilteredAlbumIds:
    """M7-CANONICAL-SEMANTICS hardening: every album mode must consume the
    SAME filtered canonical AlbumIds — not just the same count."""

    MODE_OBJECT_NAMES = {
        "grid": "albumGridView",
        "cover": "albumCoverView",
        "vinyl": "albumVinylView",
        "timeline": "albumTimelineView",
        "magazine": "albumMagazineView",
        "list": "albumListView",
    }

    @pytest.mark.parametrize("mode", list(MODE_OBJECT_NAMES))
    def test_mode_shares_filtered_album_ids(self, qapp, tmp_path, mode):
        from PySide6.QtCore import QCoreApplication, QObject
        from PySide6.QtQml import QQmlComponent, QQmlEngine

        qml_dir = (
            Path(__file__).parent.parent / "src" / "michi" / "presentation" / "qml"
        )
        library, music = _service_library(tmp_path)
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(qml_dir))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(qml_dir / "views/LibraryView.qml"))
        assert component.status() == QQmlComponent.Ready, "; ".join(
            e.toString() for e in component.errors()
        )
        obj = component.create()
        assert obj is not None

        library.search("zimmer")
        QCoreApplication.processEvents()
        expected_keys = {r["key"] for r in bridge.property("albums")}
        assert len(expected_keys) == 2  # Inception + Interstellar

        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        obj.setProperty("albumMode", mode)
        QCoreApplication.processEvents()

        view = obj.findChild(QObject, self.MODE_OBJECT_NAMES[mode])
        assert view is not None, f"{mode} view missing"
        model = view.property("model")
        if model is None and mode == "magazine":
            # MagazineView exposes the albums model on its inner ListView.
            inner = view.findChild(QObject, "albumMagazineList")
            model = inner.property("model") if inner is not None else []
        if hasattr(model, "toVariant"):
            model = model.toVariant()
        keys = {r["key"] for r in (model or [])}
        assert keys == expected_keys, f"{mode} consumed a different album set"

        obj.deleteLater()
        bridge.dispose()
        del component, engine
