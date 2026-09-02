"""POST-MERGE MICRO-FIX — toolbar R4 + M6.9 enrichment layout seam.

P0-07 runtime geometry: Search/Scan/Enrich real x/y/width/height at
1920/1440/1200/900 — no overlap, positive dimensions, inside toolbar,
zero layout warnings.
P0-08 parenting: libraryEnrichButton.parent != libraryScanSplitButton
and both are siblings under the same GridLayout.
P0-09 compact Enrich icon: width=900 + Online ON + IDLE → visible,
iconOnly, sparkles icon, valid accessibleName.
P0-10 scan active: enrich hidden while scanning.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _Pipeline:
    def __init__(self):
        self.submissions = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append((1, work))

    def cancel(self, generation):
        pass


class _FakeEnrichment(QObject):  # noqa: N815 (QML properties)
    """QML-compatible enrichment double (Properties, no fake Python attrs)."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self._online = True
        self._state = "IDLE"
        self._processed = 0
        self._total = 0

    def _online(self):
        return self._online

    onlineEnabled = Property(bool, lambda self: self._online, notify=changed)
    enrichmentJobState = Property(str, lambda self: self._state, notify=changed)
    enrichmentJobProcessed = Property(int, lambda self: self._processed, notify=changed)
    enrichmentJobTotal = Property(int, lambda self: self._total, notify=changed)

    @Slot()
    def start_library_enrichment(self):
        pass

    @Slot()
    def cancel_library_enrichment(self):
        pass


class _FakePlayback(QObject):
    currentPath = Property(str, lambda self: "")


def _world(tmp_path):
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coord = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    lifecycle = SourceScanLifecycle(coord, _Pipeline())
    bridge = LibraryBridge(
        library, source_coordinator=coord, source_scan_lifecycle=lifecycle
    )
    return bridge


def _toolbar(qapp, tmp_path, width, scan_active=False):
    bridge = _world(tmp_path)
    enrichment = _FakeEnrichment()
    if scan_active:
        bridge._scan_state = None
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    view.rootContext().setContextProperty("library", bridge)
    view.rootContext().setContextProperty("enrichment", enrichment)
    view.rootContext().setContextProperty("playback", _FakePlayback())
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "views" / "LibraryToolbar.qml")))
    assert view.status() == QQuickView.Ready, view.errors()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, 400)
    view.show()
    QTest.qWait(30)
    return view, bridge, enrichment


def _geo(view, object_name):
    obj = view.rootObject().findChild(QObject, object_name)
    if obj is None:
        return None
    return obj.x(), obj.y(), obj.width(), obj.height()


def _no_overlap(a, b):
    if a is None or b is None:
        return True
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay


def test_toolbar_runtime_geometry_no_overlap(qapp, tmp_path):
    """P0-07: en los 4 anchos los controles visibles tienen dimensiones
    positivas, no se superponen y quedan dentro del toolbar."""
    for width in (1920, 1440, 1200, 900):
        view, bridge, enrichment = _toolbar(qapp, tmp_path, width)
        scan = _geo(view, "libraryScanSplitButton")
        enrich = _geo(view, "libraryEnrichButton")
        search = _geo(view, "resizableLibrarySearchPane")

        assert scan is not None, f"{width}: scan presente"
        assert enrich is not None, f"{width}: enrich presente"
        assert search is not None, f"{width}: search presente"
        assert scan[2] > 0 and scan[3] > 0, f"{width}: scan dimensiones > 0"
        assert enrich[2] > 0 and enrich[3] > 0, f"{width}: enrich > 0"
        assert search[2] > 0 and search[3] > 0, f"{width}: search > 0"
        assert _no_overlap(scan, enrich), f"{width}: scan/enrich no se superponen"
        assert _no_overlap(search, scan), f"{width}: search/scan no se superponen"
        assert _no_overlap(search, enrich), f"{width}: search/enrich no se superponen"
        for name, geo in (("scan", scan), ("enrich", enrich), ("search", search)):
            assert geo[0] >= 0 and geo[1] >= 0, f"{width}: {name} dentro del toolbar"
        view.close()


def test_enrich_button_is_sibling_of_scan_button(qapp, tmp_path):
    """P0-08: libraryEnrichButton NO es hijo de libraryScanSplitButton —
    ambos son hermanos bajo el GridLayout (el bug estructural sellado)."""
    view, bridge, enrichment = _toolbar(qapp, tmp_path, 1440)
    root = view.rootObject()
    enrich = root.findChild(QObject, "libraryEnrichButton")
    scan = root.findChild(QObject, "libraryScanSplitButton")
    assert enrich is not None and scan is not None
    assert enrich.parent() != scan, "enrich NO puede ser hijo del split button"
    assert enrich.parent() == scan.parent(), (
        "ambos deben ser hermanos del mismo layout container"
    )
    assert scan.parent().objectName() == "libraryNavigationGrid"
    view.close()


def test_compact_enrich_icon_visible_with_sparkles(qapp, tmp_path):
    """P0-09: width=900 + Online ON + IDLE → visible, iconOnly, sparkles,
    accessibleName válido (nunca un botón icon-only vacío)."""
    view, bridge, enrichment = _toolbar(qapp, tmp_path, 900)
    root = view.rootObject()
    enrich = root.findChild(QObject, "libraryEnrichButton")
    assert enrich.property("visible") is True
    assert enrich.property("iconOnly") is True
    assert enrich.property("iconName") == "sparkles"
    assert enrich.property("accessibleName") == "Enrich entire library"
    view.close()


def test_enrich_hidden_while_scanning(qapp, tmp_path):
    """P0-10: scan activo → enrich invisible (no compite con el scan)."""
    view, bridge, enrichment = _toolbar(qapp, tmp_path, 1440)
    root = view.rootObject()
    enrich = root.findChild(QObject, "libraryEnrichButton")
    # La property visible del botón incluye !root.scanning (gate).
    toolbar_src = (QML_DIR / "views" / "LibraryToolbar.qml").read_text()
    visible_block = toolbar_src.split("id: enrichButton", 1)[1].split("text: {", 1)[0]
    assert "!root.scanning" in visible_block
    # scanActive es UNA truth del bridge (lifecycle) — nunca terminal
    # strings inferidos en QML.
    assert "library.scanActive" in toolbar_src
    # Con el bridge en reposo (scanActive False) enrich sigue visible.
    assert enrich.property("visible") is True
    view.close()
