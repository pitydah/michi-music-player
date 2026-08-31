"""Render the six premium Library views at the required review frames."""

# QML context properties intentionally follow the public camelCase contract.
# ruff: noqa: N802, N815

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QEvent,
    QObject,
    QPointF,
    QtMsgType,
    QUrl,
    Signal,
    Slot,
    qInstallMessageHandler,
)
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src/michi/presentation/qml"
MODES = {
    "gallery": "grid",
    "album-flow": "cover",
    "listening-wall": "vinyl",
    "chronology": "timeline",
    "editorial": "magazine",
    "studio-list": "list",
}
ACTIVE_NAMES = {
    "grid": "albumGridView",
    "cover": "albumCoverView",
    "vinyl": "albumVinylView",
    "timeline": "albumTimelineView",
    "magazine": "albumMagazineView",
    "list": "albumListView",
}
MANIFEST = ROOT / "docs/library_views_visual_qa_manifest.json"
HARNESS_QML = b"""
import QtQuick
import "."
import "../theme"

LibraryView {
    property bool qaReducedMotion: false
    property bool qaHighContrast: false
    onQaReducedMotionChanged: MichiAccessibility.reducedMotion = qaReducedMotion
    onQaHighContrastChanged: MichiAccessibility.highContrast = qaHighContrast
    Component.onCompleted: {
        MichiAccessibility.reducedMotion = qaReducedMotion
        MichiAccessibility.highContrast = qaHighContrast
    }
}
"""


def review_frames() -> tuple[tuple[int, int, str], ...]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return tuple(
        (int(frame["width"]), int(frame["height"]), str(frame["state"]))
        for frame in manifest["requiredReviewFrames"]
    )


def album_rows(count: int = 72) -> list[dict]:
    palettes = (
        ("#1D4561", "#163548", "#09141E", "#62B5D7"),
        ("#67402E", "#462A25", "#170D0D", "#D78B62"),
        ("#3D315C", "#29213E", "#0E0A16", "#A88BD5"),
    )
    rows = []
    for index in range(count):
        dominant, secondary, backplane, accent = palettes[index % len(palettes)]
        year = 1958 + index % 68
        rows.append(
            {
                "key": f"qa::{index}",
                "title": f"Nocturne Archive {index + 1:02d}",
                "artist": f"Michi Ensemble {index % 11 + 1}",
                "year": year,
                "decade": f"{year // 10 * 10}s",
                "trackCount": 7 + index % 8,
                "durationMs": 2_100_000 + index * 1_300,
                "discCount": 2 if index % 9 == 0 else 1,
                "genres": ["Electronic", "Ambient"] if index % 3 == 0 else ["Jazz"],
                "composers": [],
                "hasArtwork": False,
                "artworkPath": "",
                "technicalState": "mixed" if index % 5 == 0 else "homogeneous",
                "technicalSummary": "FLAC · 24-bit · 96 kHz",
                "codecs": ["FLAC"],
                "maxSampleRateHz": 96_000,
                "maxBitDepth": 24,
                "maxChannels": 2,
                "containsDsd": False,
                "containsHighResolution": index % 4 == 0,
                "isFavorite": index % 8 == 0,
                "isRecentlyAdded": index < 6,
                "artworkPalette": {
                    "colors": [dominant, secondary, backplane],
                    "dominant": dominant,
                    "secondary": secondary,
                    "backplane": backplane,
                    "accentSafe": accent,
                    "luminance": 0.18,
                    "warmth": 0.0,
                },
            }
        )
    return rows


def visual_descendants(item):
    """Walk QQuickItem ownership, including view-managed delegate wrappers."""
    pending = list(item.childItems())
    while pending:
        child = pending.pop()
        yield child
        pending.extend(child.childItems())


class QaLibrary(QObject):
    library_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._albums = album_rows()

    @Property(list, notify=library_changed)
    def albums(self):
        return self._albums

    @Property(list, notify=library_changed)
    def timelineAlbums(self):
        return sorted(self._albums, key=lambda row: (-row["year"], row["title"]))

    fileCount = Property(int, lambda self: 864, notify=library_changed)
    albumCount = Property(int, lambda self: len(self._albums), notify=library_changed)
    artistCount = Property(int, lambda self: 11, notify=library_changed)
    currentDir = Property(str, lambda self: "/qa/music", notify=library_changed)
    selectedAlbumKey = Property(str, lambda self: "", notify=library_changed)
    selectedArtistKey = Property(str, lambda self: "", notify=library_changed)
    searchActive = Property(bool, lambda self: False, notify=library_changed)
    searchQuery = Property(str, lambda self: "", notify=library_changed)
    searchAlbumCount = Property(
        int, lambda self: len(self._albums), notify=library_changed
    )
    searchTotalCount = Property(
        int, lambda self: len(self._albums), notify=library_changed
    )
    scanStatus = Property(str, lambda self: "", notify=library_changed)
    scanProcessed = Property(int, lambda self: 0, notify=library_changed)
    scanTotal = Property(int, lambda self: 0, notify=library_changed)
    scanProgress = Property(float, lambda self: 0.0, notify=library_changed)
    favoritePaths = Property(list, lambda self: [], notify=library_changed)
    hasDiagnostic = Property(bool, lambda self: False, notify=library_changed)
    diagnosticMessage = Property(str, lambda self: "", notify=library_changed)
    albumTitle = Property(str, lambda self: "", notify=library_changed)
    albumArtist = Property(str, lambda self: "", notify=library_changed)
    albumYear = Property(int, lambda self: 0, notify=library_changed)
    albumGenres = Property(str, lambda self: "", notify=library_changed)
    albumDurationMs = Property(int, lambda self: 0, notify=library_changed)
    albumTechnicalSummary = Property(str, lambda self: "", notify=library_changed)
    albumArtwork = Property(str, lambda self: "", notify=library_changed)
    albumTracks = Property(list, lambda self: [], notify=library_changed)
    albumPresentation = Property(
        "QVariantMap", lambda self: self._albums[0], notify=library_changed
    )
    albumArtworkPalette = Property(
        "QVariantMap",
        lambda self: self._albums[0]["artworkPalette"],
        notify=library_changed,
    )

    @Slot(str)
    def search(self, _query):
        return None

    @Slot()
    def clear_search(self):
        return None

    @Slot(str)
    def scan(self, _path):
        return None

    @Slot(str)
    def select_album(self, _key):
        return None

    @Slot(str)
    def play_album(self, _key):
        return None

    @Slot(str)
    def request_album_palette(self, _key):
        return None

    @Slot()
    def clear_album_selection(self):
        return None


class QaEnrichment(QObject):
    changed = Signal()
    revision = Property(int, lambda self: 0, notify=changed)
    onlineEnabled = Property(bool, lambda self: False, notify=changed)
    activeKind = Property(str, lambda self: "", notify=changed)
    state = Property(str, lambda self: "idle", notify=changed)
    stateMessage = Property(str, lambda self: "", notify=changed)
    busy = Property(bool, lambda self: False, notify=changed)
    albumArtworkPath = Property(str, lambda self: "", notify=changed)
    albumKnowledge = Property(
        "QVariantMap", lambda self: knowledge_row(), notify=changed
    )
    albumHasKnowledge = Property(bool, lambda self: False, notify=changed)
    albumAttributions = Property(list, lambda self: [], notify=changed)
    reviewOpen = Property(bool, lambda self: False, notify=changed)
    reviewKind = Property(str, lambda self: "", notify=changed)
    reviewLoading = Property(bool, lambda self: False, notify=changed)
    reviewError = Property(str, lambda self: "", notify=changed)
    albumCandidates = Property(list, lambda self: [], notify=changed)

    @Slot(str, int, result="QVariantMap")
    def album(self, key, _revision):
        return {
            "albumKey": key,
            "hasCachedKnowledge": True,
            "knowledge": knowledge_row(),
        }

    @Slot(str)
    def open_album_cached(self, _key):
        return None

    @Slot(str)
    def activate_album(self, _key):
        return None


class QaPlaylists(QObject):
    changed = Signal()
    playlists = Property(list, lambda self: [], notify=changed)


def knowledge_row() -> dict:
    return {
        "biography": "",
        "country": "",
        "area": "",
        "beginYear": 0,
        "endYear": 0,
        "artistType": "",
        "website": "",
        "label": "Michi Editions",
        "releaseYear": 2024,
        "genres": [],
    }


def render(output: Path) -> list[dict]:
    app = QGuiApplication.instance() or QGuiApplication([])
    library = QaLibrary()
    enrichment = QaEnrichment()
    playlists = QaPlaylists()
    results = []
    messages: list[str] = []

    def message_handler(kind, _context, message):
        failure_kinds = (
            QtMsgType.QtWarningMsg,
            QtMsgType.QtCriticalMsg,
            QtMsgType.QtFatalMsg,
        )
        if kind in failure_kinds:
            messages.append(str(message))

    previous_handler = qInstallMessageHandler(message_handler)
    try:
        for view_name, mode in MODES.items():
            for width, height, state in review_frames():
                _render_frame(
                    app,
                    library,
                    enrichment,
                    playlists,
                    output,
                    results,
                    view_name,
                    mode,
                    width,
                    height,
                    state,
                )
    finally:
        qInstallMessageHandler(previous_handler)
    if messages:
        unique = sorted(set(messages))
        preview = "\n".join(f"- {message}" for message in unique[:40])
        raise RuntimeError(
            f"visual QA emitted {len(messages)} Qt warning(s)/error(s):\n{preview}"
        )
    return results


def _render_frame(
    app,
    library,
    enrichment,
    playlists,
    output,
    results,
    view_name,
    mode,
    width,
    height,
    state,
) -> None:
    engine = None
    component = None
    root = None
    window = None
    try:
        engine = QQmlEngine()
        engine.addImportPath(str(QML))
        engine.rootContext().setContextProperty("library", library)
        engine.rootContext().setContextProperty("libraryEnrichment", enrichment)
        engine.rootContext().setContextProperty("enrichment", enrichment)
        engine.rootContext().setContextProperty("playlists", playlists)
        component = QQmlComponent(engine)
        component.setData(
            HARNESS_QML, QUrl.fromLocalFile(str(QML / "views/QaLibraryView.qml"))
        )
        errors = "; ".join(error.toString() for error in component.errors())
        if component.status() != QQmlComponent.Ready:
            raise RuntimeError(errors)
        root = component.createWithInitialProperties(
            {
                "currentTab": "albums",
                "albumMode": mode,
                "width": width,
                "height": height,
                "qaReducedMotion": state == "reduced-motion",
                "qaHighContrast": state == "high-contrast",
            }
        )
        if root is None:
            raise RuntimeError(errors or "LibraryView could not instantiate")
        window = QQuickWindow()
        window.setGeometry(0, 0, width, height)
        window.setColor(QColor("#0A0D14"))
        root.setParentItem(window.contentItem())
        window.show()
        QTest.qWait(160)

        active = root.findChild(QObject, ACTIVE_NAMES[mode])
        if active is None:
            raise RuntimeError(f"{view_name} did not instantiate {ACTIVE_NAMES[mode]}")
        active_width = float(active.property("width"))
        if active_width < width * 0.5:
            raise RuntimeError(
                f"{view_name} collapsed to {active_width}px at {width}px"
            )
        if mode == "grid" and width >= 1440:
            columns = int(active.property("columnCount"))
            if columns < 3:
                raise RuntimeError(
                    f"Gallery rendered only {columns} column(s) at {width}px"
                )
            cells = [
                item
                for item in visual_descendants(active)
                if item.objectName() == "albumGridCell"
            ]
            cell_records = []
            for cell in cells:
                position = cell.mapToItem(active, QPointF())
                cell_records.append(
                    {
                        "index": int(cell.property("index")),
                        "x": round(float(position.x()), 1),
                        "y": round(float(position.y()), 1),
                        "width": round(float(cell.property("width")), 1),
                        "height": round(float(cell.property("height")), 1),
                    }
                )
            on_screen = [
                cell
                for cell in cell_records
                if cell["x"] < active_width
                and cell["x"] + cell["width"] > 0
                and cell["y"] < float(active.property("height"))
                and cell["y"] + cell["height"] > 0
            ]
            cell_x_positions = {cell["x"] for cell in on_screen}
            if len(cell_x_positions) < 3:
                raise RuntimeError(
                    "Gallery delegates did not occupy three distinct columns: "
                    f"columns={columns}, rowsFlow="
                    f"{active.property('rowsFlowActive')}, "
                    f"cellWidth={active.property('cellWidth')}, "
                    f"content={active.property('contentWidth')}x"
                    f"{active.property('contentHeight')}, cells={cell_records[:12]}"
                )

        if state == "selected-and-focus":
            active.setFocus(True)
        elif state == "view-options-open":
            popup = root.findChild(QObject, "libraryViewOptionsPopup")
            if popup is None:
                raise RuntimeError("View Options popup not found")
            popup.setProperty("visible", True)
        QTest.qWait(260 if state == "view-options-open" else 80)

        target = output / f"{view_name}--{width}x{height}--{state}.png"
        image = window.grabWindow()
        if image.isNull() or not image.save(str(target)):
            raise RuntimeError(f"could not save {target}")
        results.append(
            {
                "view": view_name,
                "width": width,
                "height": height,
                "state": state,
                "file": target.name,
            }
        )
    finally:
        if root is not None:
            root.setParentItem(None)
            root.deleteLater()
        if window is not None:
            window.close()
            window.deleteLater()
        if component is not None:
            component.deleteLater()
        if engine is not None:
            engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    args.output.mkdir(parents=True, exist_ok=True)
    frames = render(args.output)
    (args.output / "index.json").write_text(
        json.dumps({"schemaVersion": 1, "frames": frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    if len(frames) != len(MODES) * len(review_frames()):
        raise RuntimeError("incomplete visual QA matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
