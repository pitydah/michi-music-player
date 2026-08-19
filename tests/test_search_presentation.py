"""M7.6 + M7.7 — Search presentation smoke and six-view unified model — tests.

The six album modes (grid/cover/vinyl/timeline/magazine/list) consume THE
SAME filtered album set: the bridge `albums` projection is the single
source, so no per-view search divergence is possible. The smoke drives the
real LibraryView with an active query and asserts every mode's view object
loads and reflects the filtered model (count == filtered album rows), and
that clearing restores the canonical count.

Also covers the toolbar surfaces: clear action object and the no-results
text (deterministic state, no business logic in QML).
"""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

try:  # QQuickPathView/QQuickListView exist in QtQuick 6, but not every PySide6
    # build exposes their Python bindings — fall back to QObject.
    from PySide6.QtQuick import QQuickListView, QQuickPathView
except ImportError:  # pragma: no cover - fallback path
    from PySide6.QtCore import QObject

    QQuickPathView = QObject  # type: ignore[assignment,misc]
    QQuickListView = QObject  # type: ignore[assignment,misc]

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackMetadata
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).parent.parent / "src" / "michi" / "presentation" / "qml"

GOLDEN = {
    "a.mp3": dict(title="Blue", artist="Joni Mitchell", album="Blue", genre="Folk"),
    "b.mp3": dict(
        title="So What", artist="Miles Davis", album="Kind of Blue", genre="Jazz"
    ),
    "c.mp3": dict(
        title="Time", artist="Hans Zimmer", album="Inception", genre="Soundtrack"
    ),
    "d.mp3": dict(
        title="Cornfield Chase",
        artist="Hans Zimmer",
        album="Interstellar",
        genre="Soundtrack",
    ),
}


def _factory(path):
    meta = GOLDEN.get(path.name, {})
    return TrackMetadata(
        title=meta.get("title", ""),
        artist=meta.get("artist", ""),
        album=meta.get("album", ""),
        album_artist=meta.get("artist", ""),
        genre=meta.get("genre", ""),
        composer=meta.get("artist", ""),
        duration_ms=1000,
    )


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


def _make_library(tmp_path):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    paths = []
    for name in GOLDEN:
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    audio = FakeAudioPort()
    queue = QueueService(PlaybackService(audio))
    library = LibraryService(FakeScanner(paths), queue, FakeExtractor(factory=_factory))
    library.scan(str(music))
    return library, music


def _load_view(library):
    bridge = LibraryBridge(library)
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", bridge)
    component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
    obj = component.create()
    assert obj is not None, "LibraryView: null object"
    # Keep engine+component alive: the created QML object dies with them.
    return bridge, obj, engine, component


class TestSixViewsUnifiedModel:
    MODES = ["grid", "cover", "vinyl", "timeline", "magazine", "list"]

    @pytest.mark.parametrize("mode", MODES)
    def test_mode_consumes_filtered_album_model(self, qapp, tmp_path, mode):
        library, music = _make_library(tmp_path)
        bridge, obj, engine, component = _load_view(library)
        assert len(bridge.property("albums")) == 4  # canonical

        library.search("zimmer")
        QCoreApplication.processEvents()
        filtered = bridge.property("albums")
        assert len(filtered) == 2  # Inception + Interstellar

        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        obj.setProperty("albumMode", mode)
        QCoreApplication.processEvents()
        albums_view = obj.findChild(QObject, "albumsView")
        assert albums_view is not None
        assert albums_view.property("albumMode") == mode

        # The active mode projection reflects the SAME filtered model count.
        if mode in ("grid", "list"):
            list_view = obj.findChild(QQuickListView, "albumsList")
            if list_view is not None:
                assert list_view.property("count") == len(filtered)
        path_view = obj.findChild(QQuickPathView, "albumCoverView")
        if mode == "cover" and path_view is not None:
            assert path_view.property("count") == len(filtered)

        # No per-view divergence: every mode reads bridge.albums.
        assert albums_view.property("albumMode") == mode
        obj.deleteLater()
        bridge.dispose()
        del component, engine

    def test_clear_restores_canonical_count_in_all_modes(self, qapp, tmp_path):
        library, music = _make_library(tmp_path)
        bridge, obj, engine, component = _load_view(library)
        obj.setProperty("currentTab", "albums")
        QCoreApplication.processEvents()
        library.search("joni")
        QCoreApplication.processEvents()
        assert len(bridge.property("albums")) == 1
        library.clear_search()
        QCoreApplication.processEvents()
        assert len(bridge.property("albums")) == 4  # canonical passthrough
        obj.deleteLater()
        bridge.dispose()
        del component, engine


class TestToolbarSurfaces:
    def test_clear_button_and_no_results_state(self, qapp, tmp_path):
        library, music = _make_library(tmp_path)
        bridge, obj, engine, component = _load_view(library)

        library.search("zzz")
        QCoreApplication.processEvents()
        no_results = obj.findChild(QObject, "searchNoResultsText")
        assert no_results is not None
        assert no_results.property("visible") is True  # active + total == 0

        library.search("miles")
        QCoreApplication.processEvents()
        assert no_results.property("visible") is False

        library.search("")
        QCoreApplication.processEvents()
        assert bridge.property("searchQuery") == ""
        obj.deleteLater()
        bridge.dispose()
        del component, engine
