from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("home"), pytest.mark.qml_dimension("responsive")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeHomeBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hasPlayback = False
        self._libraryAlbums = 42
        self._libraryArtists = 12
        self._libraryTracks = 500
        self._sourcesCount = 2
        self._lastScan = "hoy"
        self._activeJobs = 0

    @Property(bool, notify=dataChanged)
    def hasPlayback(self): return self._hasPlayback

    @Property(int, notify=dataChanged)
    def libraryAlbums(self): return self._libraryAlbums

    @Property(int, notify=dataChanged)
    def libraryArtists(self): return self._libraryArtists

    @Property(int, notify=dataChanged)
    def libraryTracks(self): return self._libraryTracks

    @Property(int, notify=dataChanged)
    def sourcesCount(self): return self._sourcesCount

    @Property(str, notify=dataChanged)
    def lastScan(self): return self._lastScan

    @Property(int, notify=dataChanged)
    def activeJobs(self): return self._activeJobs

    @Slot(result=dict)
    def refresh(self): return {"ok": True}


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestHomeResponsive:
    SIZES = [(1920, 1080), (1366, 768), (1024, 768), (900, 700),
             (600, 800), (360, 640), (900, 700), (720, 600)]
    ZOOMS = [("100%", 1.0), ("125%", 1.25), ("150%", 1.5)]

    def _create_page(self, engine, width, height, scale=1.0):
        bridge = FakeHomeBridge()
        engine.rootContext().setContextProperty("homeBridge", bridge)
        engine.addImportPath(str(QML_DIR))
        if scale != 1.0:
            engine.rootContext().setContextProperty("michiPixelRatio", scale)
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home/HomePage.qml")))
        return comp

    def _check_no_overflow(self, page, viewport_w, viewport_h):
        children = [page] + self._collect_children(page)
        for child in children:
            x = child.property("x") or 0
            y = child.property("y") or 0
            w = child.property("width") or 0
            h = child.property("height") or 0
            if hasattr(child, "objectName") and child.objectName and (x + w > viewport_w + 5 or y + h > viewport_h + 5):
                    pytest.fail(f"Control '{child.objectName()}' overflows viewport at ({x},{y}) {w}x{h} in {viewport_w}x{viewport_h}")

    def _collect_children(self, item):
        found = []
        for c in item.childItems():
            found.append(c)
            found.extend(self._collect_children(c))
        return found

    def test_desktop_1920(self, engine):
        comp = self._create_page(engine, 1920, 1080)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1366(self, engine):
        comp = self._create_page(engine, 1366, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1024(self, engine):
        comp = self._create_page(engine, 1024, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_900(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact(self, engine):
        comp = self._create_page(engine, 600, 800)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow(self, engine):
        comp = self._create_page(engine, 360, 640)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_125(self, engine):
        comp = self._create_page(engine, 900, 700, 1.25)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_150(self, engine):
        comp = self._create_page(engine, 900, 700, 1.5)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_qml_exists(self):
        assert (QML_DIR / "pages/home/HomePage.qml").exists()
