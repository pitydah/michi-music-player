"""M6.7 Library Presentation Architecture — Phase-1 RED tests.

Target contract (M6.7 master plan §47-52): ``LibraryView.qml`` becomes a
PURE ORCHESTRATION component (``LibraryPage``) composing
``LibraryHeader`` + ``LibraryToolbar`` (with embedded ``LibraryTabs``) +
``LibraryContentHost``. The six album projections, the tab contents and the
album detail are NOT inline in ``LibraryView.qml`` anymore — they live in
their own component files, instantiated ON DEMAND through the host's
Loader(s). Only the ACTIVE tab content + ACTIVE album mode exist at any
moment; ``albumMode`` lives in the albums host (survives unload/reload) and
``selectedAlbumId`` (bridge) survives by construction (M6.6).

objectNames preserved: ``albumGridView``, ``albumCoverView``,
``albumVinylView``, ``albumTimelineView``, ``albumMagazineView``,
``albumListView`` (in their new files) and the tab views gain
``songsView``/``albumsView``/``artistsView``/``genresView``/``foldersView``/
``favoritesView``/``historyView``/``recentlyView`` plus
``albumDetailView``.

QML rule (M6.1/M6.6): no canonical logic in QML — the bridge adaptation
pins already exist, and ``test_qml_no_canonical_logic`` guards the views.

Baseline (expected RED): the structural tests fail because the components
do not exist yet and the monolith keeps everything inline; the smokes in
``test_library_views.py``/``test_library_album_views.py`` are adapted to the
on-demand Loader contract (activate the tab/mode first, then findChild) and
fail on baseline because there is no ``albumsView`` host to activate.
"""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QCoreApplication, QMetaObject, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"
VIEWS_DIR = QML_DIR / "views"

# Tab value on the root's currentTab -> objectName of the tab's root view.
TAB_VIEWS = [
    ("songs", "songsView"),
    ("albums", "albumsView"),
    ("artists", "artistsView"),
    ("genres", "genresView"),
    ("folders", "foldersView"),
    ("favorites", "favoritesView"),
    ("history", "historyView"),
    ("recently", "recentlyView"),
]

# Albums host albumMode value -> objectName of the projection's root view.
ALBUM_MODES = [
    ("grid", "albumGridView"),
    ("cover", "albumCoverView"),
    ("vinyl", "albumVinylView"),
    ("timeline", "albumTimelineView"),
    ("magazine", "albumMagazineView"),
    ("list", "albumListView"),
]

ALBUM_VIEW_NAMES = [name for _, name in ALBUM_MODES]
TAB_VIEW_NAMES = [name for _, name in TAB_VIEWS]

# The six album projections + the album detail must not be inline in the
# orchestration root anymore.
INLINE_FORBIDDEN_OBJECT_NAMES = ALBUM_VIEW_NAMES + TAB_VIEW_NAMES + ["albumDetailView"]

# Every M6.7 component file that must exist under views/.
COMPONENT_FILES = [
    "LibraryHeader.qml",
    "LibraryToolbar.qml",
    "LibraryTabs.qml",
    "LibraryContentHost.qml",
    "SongsView.qml",
    "AlbumsView.qml",
    "AlbumGridView.qml",
    "AlbumPathView.qml",
    "VinylWallView.qml",
    "TimelineView.qml",
    "MagazineView.qml",
    "AlbumListView.qml",
    "AlbumDetailView.qml",
    "ArtistsView.qml",
    "GenresView.qml",
    "FoldersView.qml",
    "FavoritesView.qml",
    "HistoryView.qml",
    "RecentlyAddedView.qml",
]

# Canonical-logic tokens that must never appear in QML (M6.1/M6.6 removed
# them; the bridge is the single authority).
CANONICAL_TOKENS = ("make_album_key", "timeline_decade", "casefold")


class FakeScanPipeline:
    """Duck-typed ScanPipelinePort (same shape as tests/test_library_async.py):
    records submit/cancel, NEVER runs the work — the caller drives it."""

    def __init__(self) -> None:
        self.submits: list = []
        self.cancels: list = []

    def submit(self, generation, work, on_progress, on_done) -> None:
        self.submits.append((generation, work, on_progress, on_done))

    def cancel(self, generation) -> None:
        self.cancels.append(generation)


def _make_library(scanner, extractor=None, scan_pipeline=None):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    _session = PlaybackSessionService(playback, queue)
    return LibraryService(scanner, metadata_extractor=extractor, scan_pipeline=scan_pipeline)


def _load_library_view(tmp_path, paths=(), scan_pipeline=None):
    """Real LibraryBridge over a scanned service, as QML context property
    "library"; returns (bridge, engine, component). The view is NOT created
    yet — tests drive activation before asserting on-demand content."""
    if not paths:
        paths = [tmp_path / "song.mp3"]
    for p in paths:
        p.write_bytes(b"x")
    library = _make_library(FakeScanner(list(paths)), FakeExtractor(), scan_pipeline)
    library.scan(str(tmp_path))
    bridge = LibraryBridge(library)
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", bridge)
    component = QQmlComponent(engine, str(VIEWS_DIR / "LibraryView.qml"))
    return bridge, engine, component


def _process_events():
    """Flush QML binding re-evaluation + Loader instantiation. The host
    creates content ON DEMAND: set property -> spin -> findChild."""
    QCoreApplication.processEvents()
    QCoreApplication.processEvents()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestLibraryPageOrchestration:
    def test_library_page_loads(self, qapp, tmp_path):
        """The orchestration root compiles and instantiates with the default
        Songs tab (LibraryHeader + LibraryToolbar, including its embedded
        LibraryTabs, + LibraryContentHost compose eagerly)."""
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_each_tab_loads(self, qapp, tmp_path):
        """Activating a tab instantiates its view on demand (Loader
        contract). Only the ACTIVE tab content is required to exist after
        each switch, and switching back to songs UNLOADS the albums view."""
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            for tab, object_name in TAB_VIEWS:
                obj.setProperty("currentTab", tab)
                _process_events()
                assert obj.findChild(QObject, object_name) is not None, (
                    f"{object_name} not found after activating tab {tab!r} — "
                    "the tab content is not instantiated on demand"
                )
            # Loader on-demand contract: activating the albums tab then
            # switching to songs unloads the albums view entirely.
            obj.setProperty("currentTab", "albums")
            _process_events()
            assert obj.findChild(QObject, "albumsView") is not None, (
                "albumsView not found after activating the albums tab"
            )
            obj.setProperty("currentTab", "songs")
            _process_events()
            assert obj.findChild(QObject, "albumsView") is None, (
                "albumsView still alive on the songs tab — the Loader must "
                "unload inactive tab content"
            )
            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_album_view_host_loads_six_projections(self, qapp, tmp_path):
        """The albums host (AlbumsView, objectName albumsView) exposes
        albumMode; each mode instantiates its heavy projection on demand and
        switching modes unloads the previous one."""
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            obj.setProperty("currentTab", "albums")
            _process_events()
            host = obj.findChild(QObject, "albumsView")
            assert host is not None, (
                "albumsView host not found after activating the albums tab"
            )
            for mode, object_name in ALBUM_MODES:
                host.setProperty("albumMode", mode)
                _process_events()
                assert obj.findChild(QObject, object_name) is not None, (
                    f"{object_name} not found in albumMode {mode!r} — the "
                    "projection is not instantiated on demand"
                )
                if mode != "grid":
                    previous_name = ALBUM_MODES[
                        ALBUM_MODES.index((mode, object_name)) - 1
                    ][1]
                    assert obj.findChild(QObject, previous_name) is None, (
                        f"{previous_name} still alive after switching to "
                        f"albumMode {mode!r} — the six heavy views must be "
                        "unloaded on mode switch"
                    )
            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_album_view_switcher_event_drives_the_loaded_projection(
        self, qapp, tmp_path
    ):
        """The user-facing selector is the integration contract.

        A selected-looking segment must never diverge from the projection
        owned by LibraryView/AlbumsView. Emit the public selector event rather
        than assigning albumMode directly so the full ownership chain runs.
        """
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            obj.setProperty("currentTab", "albums")
            _process_events()

            host = obj.findChild(QObject, "albumsView")
            assert host is not None
            switcher = obj.findChild(QObject, "albumViewSwitcher")
            assert switcher is not None
            previous_name = "albumGridView"
            for mode, object_name in ALBUM_MODES[1:]:
                assert QMetaObject.invokeMethod(
                    switcher,
                    "selected",
                    Qt.DirectConnection,
                    Q_ARG(str, mode),
                )
                _process_events()

                assert obj.property("albumMode") == mode
                assert host.property("albumMode") == mode
                assert switcher.property("currentValue") == mode
                assert obj.findChild(QObject, object_name) is not None
                assert obj.findChild(QObject, previous_name) is None
                previous_name = object_name

            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_album_detail_opens_and_closes(self, qapp, tmp_path):
        """select_album shows AlbumDetailView as part of the active albums
        content; clear_album_selection hides/removes it deterministically."""
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            obj.setProperty("currentTab", "albums")
            _process_events()
            assert obj.findChild(QObject, "albumsView") is not None, (
                "albumsView host not found after activating the albums tab"
            )
            album_key = bridge.property("albums")[0]["key"]
            bridge.select_album(album_key)
            _process_events()
            detail = obj.findChild(QObject, "albumDetailView")
            assert detail is not None, (
                "albumDetailView not found after select_album — the detail "
                "must be part of the active albums content"
            )
            bridge.clear_album_selection()
            _process_events()
            detail = obj.findChild(QObject, "albumDetailView")
            assert detail is None or not bool(detail.property("visible")), (
                "albumDetailView still visible after clear_album_selection — "
                "the detail must be hidden or unloaded"
            )
            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_view_switch_preserves_selection(self, qapp, tmp_path):
        """selectedAlbumKey (bridge) survives mode switches (the host owns
        albumMode; the selection lives in the bridge by construction, M6.6)
        and the detail re-opens from any mode."""
        bridge, engine, component = _load_library_view(tmp_path)
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            obj.setProperty("currentTab", "albums")
            _process_events()
            host = obj.findChild(QObject, "albumsView")
            assert host is not None, "albumsView host not found"
            album_key = bridge.property("albums")[0]["key"]
            bridge.select_album(album_key)
            _process_events()
            for mode in ("grid", "vinyl", "list"):
                host.setProperty("albumMode", mode)
                _process_events()
                assert bridge.property("selectedAlbumKey") == album_key, (
                    f"selectedAlbumKey lost after switching to albumMode {mode!r}"
                )
                assert obj.findChild(QObject, "albumDetailView") is not None, (
                    f"albumDetailView not present in albumMode {mode!r} — the "
                    "detail must re-open from any mode"
                )
            obj.deleteLater()
        finally:
            bridge.dispose()

    def test_scan_state_surfaces(self, qapp, tmp_path):
        """The toolbar/status area binds the scan-state contract: arming a
        scan (start_scan with a pipeline -> DISCOVERING) is reflected in a
        status Text (objectName scanStatusText)."""
        pipeline = FakeScanPipeline()
        library = _make_library(FakeScanner([]), FakeExtractor(), pipeline)
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(VIEWS_DIR / "LibraryView.qml"))
        try:
            errs = "; ".join(e.toString() for e in component.errors())
            assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
            obj = component.create()
            assert obj is not None, "LibraryView: null object"
            bridge.scan(str(tmp_path))  # arms DISCOVERING via the pipeline
            assert len(pipeline.submits) == 1, "scan not armed on the pipeline"
            _process_events()
            status_text = obj.findChild(QObject, "scanStatusText")
            assert status_text is not None, (
                "scanStatusText not found — the scan-state surface is missing"
            )
            assert "DISCOVERING" in str(status_text.property("text")), (
                "scanStatusText must reflect the DISCOVERING status after arming a scan"
            )
            obj.deleteLater()
        finally:
            bridge.dispose()


class TestStructuralContract:
    def test_no_monolithic_duplicate(self):
        """The monolith is gone: LibraryView.qml must NOT contain the six
        album-view objectNames nor the tab-view objectNames inline, and the
        M6.7 component files must exist."""
        content = (VIEWS_DIR / "LibraryView.qml").read_text()
        for object_name in INLINE_FORBIDDEN_OBJECT_NAMES:
            assert object_name not in content, (
                f"{object_name} still inline in LibraryView.qml — the "
                "monolith must be decomposed into components"
            )
        for filename in COMPONENT_FILES:
            assert (VIEWS_DIR / filename).exists(), (
                f"{filename} missing — the M6.7 component file does not exist"
            )

    def test_qml_no_canonical_logic(self):
        """No canonical rules in any QML view file (M6.1/M6.6 removed them;
        the bridge is the single authority)."""
        for qml_file in sorted(VIEWS_DIR.glob("*.qml")):
            text = qml_file.read_text()
            for token in CANONICAL_TOKENS:
                assert token not in text, (
                    f"{qml_file.name} contains canonical logic ({token})"
                )
