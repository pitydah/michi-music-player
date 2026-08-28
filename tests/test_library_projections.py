"""M6.6 canonical library projections — Phase-1 RED tests.

Selection is bridge-level: ``selectedAlbumId`` (the bridge's
``selectedAlbumKey``) is the ONLY selection identity — never a visual
index. The QML ``albumMode`` is purely local presentation state, so a
view switch must not move or reset the selection. Album deletion clears
the selection SAFELY: when the selected album's key disappears from
``state.albums`` on any library change, the bridge clears
``selectedAlbumKey`` + ``albumTracks`` (no stale detail).

This batch pins the M6.6 audit contract:

- The six album views consume ONE shared model: ``library.albums``
  (grid/cover/vinyl/list + the magazine hero) and
  ``library.timelineAlbums`` (timeline — the canonical domain
  projection). No view-specific album models exist anywhere.
- The bridge adapts ``build_timeline_projection`` EXACTLY (only
  ``hasArtwork``/``artworkPath`` are bridge additions).
- albumTracks rows gain ``trackNumber``/``discNumber`` from the resolved
  TrackRef and follow the canonical (M6.1) per-album ordering exactly
  (the rows correspond to the album model, not the scan order).

Phase-1 RED evidence on baseline: tests 3 and 7 FAIL — the stale
selection survives a rescan that removes the album (no safe clear), and
the albumTracks rows have no trackNumber/discNumber keys. The structural
pins (1/2/4/5/6/8) pass on baseline.
"""

from pathlib import Path

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    TrackMetadata,
    build_timeline_projection,
    make_album_key,
)
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

_LIBRARY_BRIDGE_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "michi"
    / "presentation"
    / "library_bridge.py"
)

# M6.7 ADAPTATION (documented): LibraryView.qml is now PURE ORCHESTRATION —
# the six album projections, the tab contents and the album detail moved
# into their own components under views/. The structural greps that pinned
# the shared album model must therefore AGGREGATE over every views/*.qml
# file: the "model: library.albums" bindings, the objectNames and the
# heroAlbum property now live in the projection components, not in the
# root file.
_VIEWS_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "michi"
    / "presentation"
    / "qml"
    / "views"
)


def _aggregated_views_qml() -> str:
    """Concatenated text of every QML file under views/ (sorted for
    determinism). M6.7: the projections/tab contents are components now."""
    return "\n".join(p.read_text() for p in sorted(_VIEWS_DIR.glob("*.qml")))


def _make_library(scanner, extractor=None, artwork_provider=None, artwork_cache=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    return (
        LibraryService(
            scanner,
            metadata_extractor=extractor,
            artwork_provider=artwork_provider,
            artwork_cache=artwork_cache,
        ),
        queue,
        playback,
        audio,
    )


def _album_genre_factory():
    """a* -> album Alpha / artist Artist One; anything else -> Beta."""

    def factory(path):
        alpha = path.stem.startswith("a")
        return TrackMetadata(
            title=path.stem,
            artist="Artist One",
            album="Alpha" if alpha else "Beta",
            duration_ms=1000,
        )

    return factory


def _numbered_factory():
    """One album; per-file canonical numbers from the name 'd<disc>t<track>'.

    Scan order stays as given (shuffled vs canonical) so the tests can
    distinguish scan order from the M6.1 canonical album order."""

    def factory(path):
        disc, track = path.stem.split("t")
        return TrackMetadata(
            title=path.stem,
            artist="Artist One",
            album="Alpha",
            duration_ms=1000,
            track_number=int(track),
            disc_number=int(disc[1:]),
        )

    return factory


def _numbered_paths(tmp_path):
    """Four tracks of one album, scan order deliberately NOT canonical."""
    names = ["d1t3.mp3", "d1t1.mp3", "d2t1.mp3", "d1t2.mp3"]
    paths = [tmp_path / name for name in names]
    for p in paths:
        p.write_bytes(b"x")
    return paths


class TestSharedAlbumModel:
    def test_six_views_share_one_album_model(self):
        # M6.7 ADAPTATION: aggregated views/*.qml text — the six
        # projections are components now (AlbumGridView/AlbumPathView/
        # VinylWallView/TimelineView/MagazineView/AlbumListView), each
        # carrying its own objectName and shared-model binding.
        qml = _aggregated_views_qml()
        # The six album views exist by objectName.
        for name in (
            "albumGridView",
            "albumCoverView",
            "albumVinylView",
            "albumTimelineView",
            "albumMagazineView",
            "albumListView",
        ):
            assert f'objectName: "{name}"' in qml, f"{name} missing"
        # Each projection exposes one injectable model. AlbumsView owns the
        # single filtered/sorted presentation projection and passes it to the
        # five free-order views; timeline receives the canonical chronological
        # projection after the same filter has been applied.
        assert qml.count("property var albumModel: library.albums") == 5
        assert qml.count("property var albumModel: library.timelineAlbums") == 1
        assert qml.count("albumModel: root.presentationAlbums") == 5
        assert qml.count("albumModel: root.presentationTimelineAlbums") == 1
        # The magazine hero is derived from its injected model rather than
        # owning a separate album collection.
        assert "readonly property var heroAlbum: albumModel.length" in qml
        # No view-specific album model surfaces anywhere.
        for ident in (
            "gridAlbums",
            "vinylAlbums",
            "magazineAlbums",
            "pathAlbums",
            "listAlbums",
        ):
            assert ident not in qml, (
                f"view-specific album model {ident!r} must not exist"
            )

    def test_view_switch_preserves_selected_album(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        b1 = tmp_path / "b1.mp3"
        for p in (a1, b1):
            p.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner([a1, b1]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        album_a = next(al for al in library.state.albums if al.title == "Alpha")
        bridge.select_album(album_a.key)
        assert bridge.property("selectedAlbumKey") == album_a.key
        # A view switch is NOTHING at the bridge — the QML albumMode is a
        # purely local presentation property. The selection must not move
        # or reset (selection identity is the key, never a visual index).
        assert bridge.property("selectedAlbumKey") == album_a.key
        bridge.dispose()

        # Structural: albumMode is a local view property and the switcher
        # buttons only ASSIGN albumMode (no library. calls inside the block).
        # M6.7 ADAPTATION: albumMode + the switcher moved into
        # AlbumsView.qml (the albums host), so the greps target that file.
        albums_view_qml = (_VIEWS_DIR / "AlbumsView.qml").read_text()
        assert "property string albumMode" in albums_view_qml
        start = albums_view_qml.index('onClicked: albumMode = "grid"')
        list_marker = 'onClicked: albumMode = "list"'
        end = albums_view_qml.index(list_marker) + len(list_marker)
        switcher = albums_view_qml[start:end]
        assert "library." not in switcher, (
            "the mode switcher must not touch the bridge — albumMode is local"
        )
        for mode in ("grid", "cover", "vinyl", "timeline", "magazine", "list"):
            assert f'onClicked: albumMode = "{mode}"' in switcher


class TestSelectionLifecycle:
    def test_album_deletion_clears_selection_safely(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        a2 = tmp_path / "a2.mp3"
        b1 = tmp_path / "b1.mp3"
        for p in (a1, a2, b1):
            p.write_bytes(b"x")
        scanner = FakeScanner([a1, a2, b1])
        library, *_ = _make_library(
            scanner, FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        album_a = next(al for al in library.state.albums if al.title == "Alpha")
        bridge.select_album(album_a.key)
        assert bridge.property("selectedAlbumKey") == album_a.key
        assert len(bridge.property("albumTracks")) == 2
        # Rescan removes A's files: the selected key disappears from
        # state.albums -> the bridge must clear the selection SAFELY.
        scanner.paths = [b1]
        library.scan(str(tmp_path))
        assert [al.title for al in library.state.albums] == ["Beta"]
        assert bridge.property("selectedAlbumKey") == "", (
            "stale selectedAlbumKey survives the album deletion"
        )
        assert bridge.property("albumTracks") == [], (
            "stale album detail must not survive the album deletion"
        )
        bridge.dispose()

    def test_selection_survives_unrelated_rescan(self, tmp_path):
        a1 = tmp_path / "a1.mp3"
        b1 = tmp_path / "b1.mp3"
        c1 = tmp_path / "c1.mp3"
        for p in (a1, b1, c1):
            p.write_bytes(b"x")
        scanner = FakeScanner([a1, b1])

        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album={"a1": "Alpha", "b1": "Beta", "c1": "Gamma"}[path.stem],
                duration_ms=1000,
            )

        library, *_ = _make_library(scanner, FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        album_a = next(al for al in library.state.albums if al.title == "Alpha")
        bridge.select_album(album_a.key)
        assert bridge.property("selectedAlbumKey") == album_a.key
        # Rescan keeps A present and adds C: the selection must survive.
        scanner.paths = [a1, c1]
        library.scan(str(tmp_path))
        assert [al.title for al in library.state.albums] == ["Alpha", "Gamma"]
        assert bridge.property("selectedAlbumKey") == album_a.key, (
            "an unrelated rescan must not clear the selection"
        )
        rows = bridge.property("albumTracks")
        assert [r["path"] for r in rows] == [str(a1)]
        bridge.dispose()


class TestCanonicalProjections:
    def test_timeline_uses_canonical_projection(self, tmp_path):
        paths = [tmp_path / "a1.mp3", tmp_path / "b1.mp3", tmp_path / "c1.mp3"]
        for p in paths:
            p.write_bytes(b"x")
        years = {"a1.mp3": 2005, "b1.mp3": 2021, "c1.mp3": 0}

        def factory(path):
            return TrackMetadata(
                title=path.stem,
                artist="Artist One",
                album=path.stem,
                duration_ms=1000,
                year=years.get(path.name, 0),
            )

        library, *_ = _make_library(FakeScanner(paths), FakeExtractor(factory=factory))
        library.scan(str(tmp_path))
        assert {a.year for a in library.state.albums} == {0, 2005, 2021}
        bridge = LibraryBridge(library)
        rows = bridge.property("timelineAlbums")
        expected = build_timeline_projection(library.state.albums)
        # The bridge adapts the canonical projection EXACTLY.
        assert [
            (r["key"], r["title"], r["artist"], r["year"], r["decade"]) for r in rows
        ] == [(p.album_key, p.title, p.artist, p.year, p.decade) for p in expected]
        # Only hasArtwork/artworkPath are bridge additions.
        for row in rows:
            assert {
                "key",
                "title",
                "artist",
                "year",
                "decade",
                "hasArtwork",
                "artworkPath",
            }.issubset(row)
            assert row["artistKey"]
        bridge.dispose()

    def test_no_duplicated_album_identity_logic(self, tmp_path):
        src = _LIBRARY_BRIDGE_SRC.read_text()
        for ident in (
            "gridAlbums",
            "vinylAlbums",
            "magazineAlbums",
            "pathAlbums",
            "listAlbums",
        ):
            assert ident not in src, (
                f"view-specific album model {ident!r} must not exist"
            )
        a1 = tmp_path / "a1.mp3"
        b1 = tmp_path / "b1.mp3"
        for p in (a1, b1):
            p.write_bytes(b"x")
        library, *_ = _make_library(
            FakeScanner([a1, b1]), FakeExtractor(factory=_album_genre_factory())
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        rows = bridge.property("albums")
        assert len(rows) == 2
        # The rows carry the CANONICAL identity: make_album_key of their own
        # title/artist — no bridge-side identity generation.
        for row in rows:
            assert row["key"] == make_album_key(row["title"], row["artist"])
        bridge.dispose()

    def test_album_tracks_rows_include_canonical_numbers(self, tmp_path):
        paths = _numbered_paths(tmp_path)
        library, *_ = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_numbered_factory())
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        assert album.track_count == 4
        assert [p.name for p in album.track_paths] == [
            "d1t1.mp3",
            "d1t2.mp3",
            "d1t3.mp3",
            "d2t1.mp3",
        ]
        bridge = LibraryBridge(library)
        bridge.select_album(album.key)
        rows = bridge.property("albumTracks")
        assert len(rows) == 4
        # trackNumber/discNumber come from the resolved TrackRef.
        for row, path in zip(rows, album.track_paths, strict=True):
            ref = next(t for t in library.state.tracks if t.file_path == path)
            assert row["trackNumber"] == ref.track_number
            assert row["discNumber"] == ref.disc_number
        # ... in the M6.1 canonical order.
        assert [r["trackNumber"] for r in rows] == [1, 2, 3, 1]
        assert [r["discNumber"] for r in rows] == [1, 1, 1, 2]
        bridge.dispose()

    def test_bridge_rows_correspond_to_canonical_model(self, tmp_path):
        paths = _numbered_paths(tmp_path)
        library, *_ = _make_library(
            FakeScanner(paths), FakeExtractor(factory=_numbered_factory())
        )
        library.scan(str(tmp_path))
        album = library.state.albums[0]
        bridge = LibraryBridge(library)
        bridge.select_album(album.key)
        rows = bridge.property("albumTracks")
        # The rows follow the ALBUM MODEL (M6.1 canonical ordering), not the
        # scan order; the row count equals the canonical track count.
        assert len(rows) == album.track_count
        assert [r["path"] for r in rows] == [str(p) for p in album.track_paths]
        assert [r["path"] for r in rows] != [str(p) for p in paths], (
            "rows must not follow the scan order for a shuffled scan"
        )
        bridge.dispose()
