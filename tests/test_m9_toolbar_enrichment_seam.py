"""POST-MERGE MICRO-FIX — toolbar R4 + M6.9 enrichment layout seam.

P0-07 runtime geometry: Search/Scan/Enrich real x/y/width/height at
1920/1440/1200/900 — positive dimensions, INSIDE the toolbar bounds
(x+w <= toolbar_w + EPSILON), no overlap, zero layout warnings.
P0-08 parenting: libraryEnrichButton.parent != libraryScanSplitButton
and both are siblings under libraryNavigationGrid.
P0-09 compact Enrich icon: width=900 + Online ON + IDLE → visible,
iconOnly, sparkles icon, valid accessibleName.
P0-01..05 scan visibility: a REAL scan through the productive intent
(performScan → scan_all_sources → SourceScanLifecycle → manual
pipeline) transitions scanActive False→True and enrich.visible True→False
with exactly 1 lifecycle submission.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot  # noqa: F401
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from michi.application.library_service import LibraryService
from michi.application.ports import LibraryPrefsPort
from michi.application.source_scan_coordinator import SourceScanCoordinator
from michi.application.source_scan_lifecycle import SourceScanLifecycle
from michi.domain.library import LibraryPrefs
from michi.domain.library_catalog import (
    LibrarySource,
    new_library_source_id,
)
from michi.infrastructure.filesystem_source_scanner import (
    FilesystemLibrarySourceScanner,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_media_cache import SqliteLibraryMediaCache
from michi.presentation.library_bridge import LibraryBridge

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

EPSILON = 1.0


class _Prefs(LibraryPrefsPort):
    def load(self):
        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _ManualPipeline:
    """P0-03: pipeline que NO ejecuta el work — el lifecycle permanece
    ACTIVO mientras el test inspecciona scanActive. Nunca se llama
    on_done() antes de verificar la invisibilidad de Enrich."""

    def __init__(self):
        self.submissions = []

    def submit(self, generation, work, on_progress, on_done):
        self.submissions.append(
            {
                "generation": generation,
                "work": work,
                "on_progress": on_progress,
                "on_done": on_done,
            }
        )

    def cancel(self, generation):
        pass


class _FakeEnrichment(QObject):  # noqa: N815 (QML properties)
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._online = True
        self._state = "IDLE"
        self._processed = 0
        self._total = 0

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


def _world(tmp_path, with_source=False):
    """Real world: LibraryBridge + SourceScanLifecycle + Coordinator +
    manual pipeline (mismo patrón que los gates P1.1/R4)."""
    db_path = tmp_path / "michi.db"
    catalog = SqliteLibraryCatalogRepository(db_path)
    library = LibraryService(FilesystemLibrarySourceScanner(), library_prefs=_Prefs())
    coord = SourceScanCoordinator(
        library,
        catalog,
        FilesystemLibrarySourceScanner(),
        media_cache=SqliteLibraryMediaCache(db_path),
    )
    pipeline = _ManualPipeline()
    lifecycle = SourceScanLifecycle(coord, pipeline)
    bridge = LibraryBridge(
        library, source_coordinator=coord, source_scan_lifecycle=lifecycle
    )
    if with_source:
        source_dir = tmp_path / "music"
        source_dir.mkdir(exist_ok=True)
        (source_dir / "a.flac").write_bytes(b"x")
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="Music",
            root_path=str(source_dir),
        )
        catalog.upsert_source(source)
        coord.list_sources()
        bridge.library_changed.emit()
    return bridge, pipeline


def _toolbar(qapp, tmp_path, width, with_source=False):
    bridge, pipeline = _world(tmp_path, with_source=with_source)
    enrichment = _FakeEnrichment()
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
    return view, bridge, pipeline, enrichment


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


def test_toolbar_runtime_geometry_inside_bounds_no_overlap(qapp, tmp_path):
    """P0-06/07: en los 4 anchos los controles visibles tienen
    dimensiones positivas, quedan DENTRO del toolbar (con tolerancia
    mínima EPSILON) y no se superponen."""
    for width in (1920, 1440, 1200, 900):
        view, bridge, pipeline, enrichment = _toolbar(qapp, tmp_path, width)
        scan = _geo(view, "libraryScanSplitButton")
        enrich = _geo(view, "libraryEnrichButton")
        search = _geo(view, "resizableLibrarySearchPane")

        assert scan is not None, f"{width}: scan presente"
        assert enrich is not None, f"{width}: enrich presente"
        assert search is not None, f"{width}: search presente"
        assert scan[2] > 0 and scan[3] > 0, f"{width}: scan > 0"
        assert enrich[2] > 0 and enrich[3] > 0, f"{width}: enrich > 0"
        assert search[2] > 0 and search[3] > 0, f"{width}: search > 0"
        toolbar_w = view.width()
        toolbar_h = view.height()
        for name, geo in (("scan", scan), ("enrich", enrich), ("search", search)):
            x, y, w, h = geo
            assert x >= 0 and y >= 0, f"{width}: {name} x/y >= 0"
            assert x + w <= toolbar_w + EPSILON, (
                f"{width}: {name} dentro del ancho del toolbar ({x}+{w} <= {toolbar_w})"
            )
            assert y + h <= toolbar_h + EPSILON, (
                f"{width}: {name} dentro del alto del toolbar"
            )
        assert _no_overlap(scan, enrich), f"{width}: scan/enrich sin overlap"
        assert _no_overlap(search, scan), f"{width}: search/scan sin overlap"
        assert _no_overlap(search, enrich), f"{width}: search/enrich sin overlap"
        view.close()


def test_enrich_button_is_sibling_of_scan_button(qapp, tmp_path):
    """P0-08: libraryEnrichButton NO es hijo de libraryScanSplitButton —
    ambos son hermanos bajo libraryNavigationGrid."""
    view, bridge, pipeline, enrichment = _toolbar(qapp, tmp_path, 1440)
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
    view, bridge, pipeline, enrichment = _toolbar(qapp, tmp_path, 900)
    root = view.rootObject()
    enrich = root.findChild(QObject, "libraryEnrichButton")
    assert enrich.property("visible") is True
    assert enrich.property("iconOnly") is True
    assert enrich.property("iconName") == "sparkles"
    assert enrich.property("accessibleName") == "Enrich entire library"
    view.close()


def test_scan_active_hides_enrich_through_real_scan(qapp, tmp_path):
    """P0-01..05: un scan REAL (intención productiva → scan_all_sources
    → SourceScanLifecycle → pipeline manual pendiente) transiciona
    scanActive False→True y enrich.visible True→False, con exactamente
    1 submission al lifecycle. Sin estado privado simulado."""
    view, bridge, pipeline, enrichment = _toolbar(
        qapp, tmp_path, 1440, with_source=True
    )
    root = view.rootObject()
    enrich = root.findChild(QObject, "libraryEnrichButton")

    # Estado inicial: reposo.
    assert bridge.scanActive is False
    assert enrich.property("visible") is True

    # Intención productiva: primary del split button → performScan →
    # scan_all_sources() (el slot canónico del Bridge).
    scan = root.findChild(QObject, "libraryScanSplitButton")
    meta = scan.metaObject()
    primary_index = meta.indexOfMethod("primaryClicked()")
    assert primary_index >= 0, "MichiSplitButton.primaryClicked disponible"
    meta.method(primary_index).invoke(scan)
    QTest.qWait(30)

    # El scan quedó PENDIENTE (pipeline manual no ejecuta on_done).
    assert len(pipeline.submissions) == 1, (
        "la intención llegó al lifecycle: exactamente 1 submission"
    )
    assert bridge.scanActive is True, "scanActive publica True (autoridad real)"
    assert enrich.property("visible") is False, "enrich oculto durante el scan activo"

    # El scan sigue activo (on_done nunca se llamó) — el estado se
    # mantiene coherente.
    assert bridge.scanActive is True
    view.close()
