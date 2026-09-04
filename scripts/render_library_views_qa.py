"""Render the six premium Library views at the required review frames."""

# QML context properties intentionally follow the public camelCase contract.
# ruff: noqa: N802, N815

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QEvent,
    QMetaObject,
    QObject,
    QPoint,
    QPointF,
    Qt,
    QtMsgType,
    QUrl,
    Signal,
    Slot,
    qInstallMessageHandler,
)
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
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
    property bool qaPrecisionMode: false
    onQaReducedMotionChanged: MichiAccessibility.reducedMotion = qaReducedMotion
    onQaHighContrastChanged: MichiAccessibility.highContrast = qaHighContrast
    onQaPrecisionModeChanged: MichiThemeState.precisionMode = qaPrecisionMode
    function qaEnableKeyboardMode() { MichiAccessibility.noteKeyboard() }
    Component.onCompleted: {
        MichiAccessibility.reducedMotion = qaReducedMotion
        MichiAccessibility.highContrast = qaHighContrast
        MichiThemeState.precisionMode = qaPrecisionMode
    }
}
"""


def review_frames() -> tuple[tuple[int, int, str], ...]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return tuple(
        (int(frame["width"]), int(frame["height"]), str(frame["state"]))
        for frame in manifest["requiredReviewFrames"]
    )


def create_artwork_fixtures(directory: Path) -> tuple[str, ...]:
    """Create asymmetric covers so crop/stretch defects are visible."""
    colors = (
        ("#163548", "#62B5D7"),
        ("#462A25", "#D78B62"),
        ("#29213E", "#A88BD5"),
    )
    paths = []
    for index, (background, accent) in enumerate(colors):
        image = QImage(420, 280, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(background))
        painter = QPainter(image)
        painter.fillRect(0, 0, 105, 280, QColor(accent))
        painter.fillRect(315, 0, 105, 280, QColor("#09141E"))
        painter.setBrush(QColor("#F4EEE8"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(156, 86, 108, 108)
        painter.end()
        path = directory / f"qa-cover-{index}.png"
        if not image.save(str(path)):
            raise RuntimeError(f"could not create QA artwork fixture {path}")
        paths.append(str(path))
    return tuple(paths)


def album_rows(
    count: int = 72,
    *,
    state: str = "idle",
    artwork_paths: tuple[str, ...] = (),
) -> list[dict]:
    palettes = (
        ("#1D4561", "#163548", "#09141E", "#62B5D7"),
        ("#67402E", "#462A25", "#170D0D", "#D78B62"),
        ("#3D315C", "#29213E", "#0E0A16", "#A88BD5"),
    )
    if state == "empty":
        return []
    rows = []
    for index in range(count):
        dominant, secondary, backplane, accent = palettes[index % len(palettes)]
        year = 1958 + index % 68
        artwork_path = ""
        if state != "missing-artwork" and artwork_paths and index % 5 != 4:
            artwork_path = artwork_paths[index % len(artwork_paths)]
        title = f"Nocturne Archive {index + 1:02d}"
        artist = f"Michi Ensemble {index % 11 + 1}"
        if state == "long-metadata":
            title += " — The Complete Restored Sessions and Alternate Takes"
            artist += " with the Transpacific Chamber Orchestra Collective"
        rows.append(
            {
                "key": f"qa::{index}",
                "title": title,
                "artist": artist,
                "year": year,
                "decade": f"{year // 10 * 10}s",
                "trackCount": 7 + index % 8,
                "durationMs": 2_100_000 + index * 1_300,
                "discCount": 2 if index % 9 == 0 else 1,
                "genres": ["Electronic", "Ambient"] if index % 3 == 0 else ["Jazz"],
                "composers": [],
                "hasArtwork": bool(artwork_path),
                "artworkPath": artwork_path,
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


def _visual_items(item):
    """Traversal visual (childItems) — los delegates de Repeater/ListView
    no son alcanzables con findChildren."""
    out = []

    def visit(current):
        for child in current.childItems():
            out.append(child)
            visit(child)

    visit(item)
    return out


def visual_descendants(item):
    """Walk QQuickItem ownership, including view-managed delegate wrappers."""
    pending = list(item.childItems())
    while pending:
        child = pending.pop()
        yield child
        pending.extend(child.childItems())


class QaLibrary(QObject):
    library_changed = Signal()
    albumPaletteChanged = Signal(str, "QVariantMap")

    def __init__(self, state: str, artwork_paths: tuple[str, ...]) -> None:
        super().__init__()
        self._state = state
        self._albums = album_rows(state=state, artwork_paths=artwork_paths)

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
    # P1.1/R4 recovered toolbar contract: the productive LibraryToolbar
    # reads these Bridge properties (real LibraryBridge exposes them);
    # the QA harness must model them to render warning-free.
    configuredSourceCount = Property(
        int, lambda self: 0 if self._state == "empty" else 1, notify=library_changed
    )
    sourceOperationError = Property(str, lambda self: "", notify=library_changed)
    # M9-R3 context menus contract: capability surfaces del Bridge.
    canQueueTracks = Property(bool, lambda self: True, notify=library_changed)
    canAddTracksToPlaylists = Property(bool, lambda self: True, notify=library_changed)
    scanCurrentPath = Property(str, lambda self: "", notify=library_changed)
    selectedAlbumKey = Property(str, lambda self: "", notify=library_changed)
    selectedArtistKey = Property(str, lambda self: "", notify=library_changed)
    searchActive = Property(
        bool, lambda self: self._state == "search-active", notify=library_changed
    )
    searchQuery = Property(
        str,
        lambda self: "nocturne" if self._state == "search-active" else "",
        notify=library_changed,
    )
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
        "QVariantMap",
        lambda self: self._albums[0] if self._albums else {},
        notify=library_changed,
    )
    albumArtworkPalette = Property(
        "QVariantMap",
        lambda self: self._albums[0]["artworkPalette"] if self._albums else {},
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


_KEEP: list = []


def render(output: Path) -> list[dict]:
    app = QGuiApplication.instance() or QGuiApplication([])
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
        with tempfile.TemporaryDirectory(prefix="michi-library-qa-") as temp_dir:
            artwork_paths = create_artwork_fixtures(Path(temp_dir))
            for view_name, mode in MODES.items():
                for width, height, state in review_frames():
                    if state == "album-context-menu" and view_name != "editorial":
                        continue  # frame del menú de álbum (editorial)
                    library = QaLibrary(state, artwork_paths)
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
            # M9-R3: menús contextuales aislados reales (genre/track) —
            # los popups de los delegates de GridView/Repeaters no abren
            # en offscreen; el componente del menú se renderiza abierto.
            _render_standalone_menu(
                app,
                output,
                results,
                "genre-context-menu",
                "media/GenreContextMenu.qml",
                {
                    "genre": {
                        "key": "genre:jazz",
                        "name": "Jazz",
                        "albumCount": 24,
                        "trackCount": 312,
                    }
                },
            )
            _render_standalone_menu(
                app,
                output,
                results,
                "track-context-menu",
                "media/TrackContextMenu.qml",
                {
                    "titleText": "Nocturne",
                    "artistText": "Artist",
                    "albumText": "Album",
                    "canAddToPlaylist": True,
                    "canAddToNewPlaylist": True,
                    "canShowProperties": True,
                },
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


def _render_standalone_menu(
    app,
    output,
    results,
    state: str,
    component_path: str,
    properties: dict,
) -> None:
    """M9-R3 CONVERGENCE SEAL: render del menú contextual REAL abierto
    (componente productivo + datos) para inspección perceptual de
    geometría/header/separadores/capacidades ocultas. FALLA si el menú
    no abre. El Popup se ancla vía un Item anfitrión (los Popup no son
    visual children por sí mismos)."""
    from PySide6.QtCore import QObject, QUrl, Signal, Slot
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
    from PySide6.QtTest import QTest

    class _Library(QObject):  # noqa: N815 (QML-facing)
        changed = Signal()
        canQueueTracks = Property(bool, lambda self: True, notify=changed)
        canAddTracksToPlaylists = Property(bool, lambda self: True, notify=changed)

        @Slot(str)
        def select_album(self, key):
            del key

        @Slot(str)
        def play_album(self, key):
            del key

        @Slot(str)
        def queue_album(self, key):
            del key

        @Slot(str)
        def select_artist(self, key):
            del key

        @Slot(str)
        def select_genre(self, key):
            del key

        @Slot(str)
        def request_album_playlist_target(self, key):
            del key

        @Slot(str)
        def request_new_playlist_for_album(self, key):
            del key

        @Slot(str)
        def request_album_properties(self, key):
            del key

    library = _Library()
    _KEEP.append(library)
    engine = QQmlEngine()
    engine.addImportPath(str(QML))
    engine.rootContext().setContextProperty("library", library)
    component = QQmlComponent(engine)
    component.setData(
        (
            "import QtQuick\n"
            f'import "{QML.as_uri()}/media"\n'
            "Item {\n"
            "    id: host\n"
            '    objectName: "menuHost"\n'
            f"    {Path(component_path).stem} {{ id: theMenu }}\n"
            "}\n"
        ).encode(),
        QUrl("menu_host.qml"),
    )
    if component.status() != QQmlComponent.Ready:
        raise RuntimeError(
            f"{state}: " + "; ".join(e.toString() for e in component.errors())
        )
    host = component.create()
    _KEEP.extend([engine, component, host])
    menu = None
    for child in host.findChildren(QObject):
        if Path(component_path).stem in child.metaObject().className():
            menu = child
            break
    if menu is None:
        raise RuntimeError(f"{state}: menú del host no encontrado")
    for key, value in properties.items():
        menu.setProperty(key, value)
    window = QQuickWindow()
    window.resize(1200, 900)
    host.setParentItem(window.contentItem())
    window.show()
    QTest.qWait(100)
    meta = menu.metaObject()
    popup_index = meta.indexOfMethod("popup()")
    if popup_index < 0 or not meta.method(popup_index).invoke(menu):
        raise RuntimeError(f"{state}: popup() no invocable")
    QTest.qWait(120)
    if not menu.property("visible"):
        raise RuntimeError(f"{state}: el menú no abrió para el QA")
    image = window.grabWindow()
    name = f"1200-{state}.png"
    if image.isNull() or not image.save(str(output / name)):
        raise RuntimeError(f"could not save {name}")
    results.append({"frame": name, "w": 1200, "h": 900, "state": state})
    window.close()


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
                "qaPrecisionMode": state == "precision-on",
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

        albums_host = root.findChild(QObject, "albumsView")
        if state == "filter-active" and albums_host is not None:
            albums_host.setProperty("albumFilterMode", "hires")
            QCoreApplication.processEvents()

        active = root.findChild(QObject, ACTIVE_NAMES[mode])
        if active is None and state == "empty":
            active = albums_host
        if active is None:
            raise RuntimeError(f"{view_name} did not instantiate {ACTIVE_NAMES[mode]}")
        active_width = float(active.property("width"))
        if active_width < width * 0.5:
            raise RuntimeError(
                f"{view_name} collapsed to {active_width}px at {width}px"
            )
        if mode == "grid" and width >= 1440 and state != "empty":
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

        if state in {"selected", "keyboard-focus"}:
            if mode == "magazine":
                active.setProperty("rovingIndex", 1)
                magazine_list = root.findChild(QObject, "albumMagazineList")
                if magazine_list is not None:
                    magazine_list.setProperty("currentIndex", 1)
            elif active.property("currentIndex") is not None:
                active.setProperty("currentIndex", 1)

        if state == "keyboard-focus":
            QMetaObject.invokeMethod(root, "qaEnableKeyboardMode", Qt.DirectConnection)
            focus_target = (
                root.findChild(QObject, "albumMagazineList")
                if mode == "magazine"
                else active
            )
            if focus_target is None:
                raise RuntimeError(f"{view_name} has no keyboard focus target")
            focus_target.setFocus(True, Qt.FocusReason.TabFocusReason)
            QCoreApplication.processEvents()
            if window.activeFocusItem() is None:
                raise RuntimeError(
                    f"{view_name} did not establish active keyboard focus"
                )
        elif state == "hover":
            hover_target = (
                active.property("currentItem")
                if mode != "magazine" and active.property("currentItem") is not None
                else active
            )
            target_width = float(hover_target.property("width"))
            target_height = float(hover_target.property("height"))
            point = hover_target.mapToItem(
                window.contentItem(),
                QPointF(
                    min(target_width * 0.5, 220),
                    min(target_height * 0.5, 110),
                ),
            )
            QTest.mouseMove(window, QPoint(round(point.x()), round(point.y())))
        elif state == "view-options-open":
            popup = root.findChild(QObject, "libraryViewOptionsPopup")
            if popup is None:
                raise RuntimeError("View Options popup not found")
            popup.setProperty("visible", True)
        elif state == "album-context-menu":
            # M9-R3: abre el menú contextual REAL del álbum hero del
            # magazine para el render de revisión perceptual.
            if view_name != "editorial":
                raise RuntimeError(
                    "album-context-menu QA frame requires the editorial mode"
                )
            hero = root.findChild(QObject, "magazineHeroContext")
            if hero is None:
                raise RuntimeError("magazineHeroContext not found")
            meta = hero.metaObject()
            index = meta.indexOfMethod("openMenu()")
            if index < 0 or not meta.method(index).invoke(hero):
                raise RuntimeError("album context openMenu() failed")
        QTest.qWait(260 if state in {"view-options-open", "hover"} else 80)
        if state == "album-context-menu":
            visible_menus = [
                item
                for item in root.findChildren(QObject)
                if item.property("visible") is True
                and "Menu" in item.metaObject().className()
            ]
            if not visible_menus:
                raise RuntimeError("album context menu did not open for QA")

        if state == "empty" and library.albumCount != 0:
            raise RuntimeError("empty QA state still contains albums")
        if (
            state == "filter-active"
            and active.property("count") is not None
            and int(active.property("count")) >= library.albumCount
        ):
            raise RuntimeError("active filter did not reduce the album collection")

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
    expected = len(MODES) * len(review_frames())
    editorial_only = sum(
        1 for frame in review_frames() if frame[2] == "album-context-menu"
    )
    expected -= editorial_only * (len(MODES) - 1)
    expected += 2  # menús aislados genre/track del convergence seal
    if len(frames) != expected:
        raise RuntimeError("incomplete visual QA matrix")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
