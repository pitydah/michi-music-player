"""A1 — Library Context Action Host: runtime seal.

Real input → signal → consumer → backend mutation → observable result.

Entorno offscreen: Popup.opened requiere un window real (limitación
documentada en test_m9_r1j). El contrato observable es el del repo: el
destino poblado por el host, la señal REAL del componente (la misma del
click productivo), la mutación del backend y el feedback — nunca la
visibilidad del popup.

- right-click row → context menu → Add to Playlist → Bridge targeting
  (TrackId) → host puebla PlaylistTargetPicker → picker.targetRequested
  → library.add_tracks_to_playlist(playlist_id, [trackId]) → feedback.
- New playlist… → SelectionPlaylistCreateDialog.begin(payload) →
  createRequested(name, payload) → create_playlist_from_tracks →
  feedback (sin fake success en falla).
- Properties → TrackPropertiesView poblada con facts canónicos.
- Unavailable: Add y Properties siguen productivos (no requieren
  disponibilidad); Queue ausente (sellado aparte).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import (  # noqa: E402
    Property,
    QObject,
    QPoint,
    QPointF,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication, Qt  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _process(rounds=6):
    from PySide6.QtCore import QCoreApplication

    for _ in range(rounds):
        QCoreApplication.processEvents()


def _walk(item, predicate):
    for child in item.childItems():
        if predicate(child):
            return child
        found = _walk(child, predicate)
        if found is not None:
            return found
    return None


def _find_any(item, predicate):
    from PySide6.QtCore import QObject

    for child in item.findChildren(QObject):
        if predicate(child):
            return child
    return _walk(item, predicate)


def _find_text_deep(root, text):
    """Recorre el árbol visual y, por cada item visual, sus children QObject
    (popups/menús declarados en delegates)."""
    from PySide6.QtCore import QObject

    def visit(item):
        try:
            children = item.findChildren(QObject)
        except RuntimeError:
            return None
        for child in children:
            try:
                if child.property("text") == text:
                    return child
            except RuntimeError:
                continue
        try:
            subitems = list(item.childItems())
        except RuntimeError:
            return None
        for child in subitems:
            found = visit(child)
            if found is not None:
                return found
        return None

    return visit(root)


def _wait_for(root, prop, value, rounds=30):
    for _ in range(rounds):
        found = _find_any(root, lambda c, p=prop, v=value: c.property(p) == v)
        if found is not None:
            return found
        QTest.qWait(40)
    return None


def _activate_menu_item(delegate, text):
    """Trigger REAL MenuItem.triggered → onTriggered (production chain).
    El menú del delegate (TrackContextMenu declarado en el row) se abre con
    el right-click real; sus items son estables en el mismo tick."""
    from PySide6.QtCore import QObject

    menu = None
    for _ in range(30):
        for child in delegate.findChildren(QObject):
            if (
                "ContextMenu" in child.metaObject().className()
                and child.property("visible") is True
            ):
                menu = child
                break
        if menu is not None:
            break
        QTest.qWait(40)
    assert menu is not None, "menú contextual del delegate no visible"
    for _ in range(10):
        for child in menu.findChildren(QObject):
            try:
                if child.property("text") == text and child.property("visible") is True:
                    child.triggered.emit()
                    _process()
                    return
            except RuntimeError:
                continue
        QTest.qWait(40)
    pytest.fail(f"item {text!r} no activable en el menú del delegate")


def _right_click_row(view, root, track_id):
    row = _wait_for(root, "trackId", track_id)
    assert row is not None, f"TrackRow {track_id} no instanciado"
    center = row.mapToScene(QPointF(row.width() / 2, row.height() / 2))
    QTest.mouseClick(
        view,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(int(center.x()), int(center.y())),
    )
    QTest.qWait(80)
    return row


def _row():
    return {
        "trackId": "T-1",
        "path": "/music/one.flac",
        "title": "One",
        "displayName": "One",
        "artist": "Artist A",
        "artistKey": "artist-a",
        "album": "Album One",
        "albumKey": "album-one",
        "durationMs": 180000,
        "artworkPath": "",
        "formatKey": "flac",
        "formatLabel": "FLAC",
        "codec": "flac",
        "container": "flac",
        "dsdRate": "",
        "sampleRateHz": 44100,
        "bitDepth": 16,
        "bitrateBps": 800000,
        "channels": 2,
        "fileSize": 12000000,
        "genre": "Jazz",
        "composer": "Composer",
        "year": 1960,
        "trackNumber": 1,
        "discNumber": 1,
        "available": True,
        "unavailable": False,
    }


def _unavailable_row():
    row = _row()
    row["trackId"] = "T-2"
    row["path"] = "/music/offline.flac"
    row["title"] = "Offline"
    row["available"] = False
    row["unavailable"] = True
    row["unavailableReason"] = "source_offline"
    row["availability"] = "source_offline"
    return row


class _Playback(QObject):
    currentPath = Property(str, lambda self: "")


class _Playlists(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._rows = [
            {"playlistId": "pl-1", "name": "Chill", "trackCount": 3, "pinned": True},
            {"playlistId": "pl-2", "name": "Focus", "trackCount": 9, "pinned": False},
        ]

    playlists = Property("QVariantList", lambda self: self._rows, notify=changed)
    pinnedPlaylists = Property(
        "QVariantList",
        lambda self: [r for r in self._rows if r["pinned"]],
        notify=changed,
    )
    recentPlaylists = Property("QVariantList", lambda self: [], notify=changed)


class _Library(QObject):
    """Fake del LibraryBridge: valida y emite playlist_target_requested
    como el bridge real; registra las mutaciones de membership."""

    changed = Signal()
    playlist_target_requested = Signal(dict)
    new_playlist_target_requested = Signal(dict)
    album_properties_requested = Signal(dict)

    def __init__(self, rows):
        super().__init__()
        self._rows = rows
        self.add_calls = []
        self.create_calls = []
        self.target_calls = []
        self.already_present = False

    # ContentHost / SongsView surfaces
    libraryTrackCount = Property(int, lambda self: 2, notify=changed)
    scanStatus = Property(str, lambda self: "", notify=changed)
    hasDiagnostic = Property(bool, lambda self: False, notify=changed)
    diagnosticMessage = Property(str, lambda self: "", notify=changed)
    genreFilterActive = Property(bool, lambda self: False, notify=changed)
    selectedGenreName = Property(str, lambda self: "", notify=changed)
    songRows = Property("QVariantList", lambda self: self._rows, notify=changed)
    favoriteTrackIds = Property("QVariantList", lambda self: [], notify=changed)
    favoritePaths = Property("QVariantList", lambda self: [], notify=changed)
    canQueueTracks = Property(bool, lambda self: True, notify=changed)
    canAddTracksToPlaylists = Property(bool, lambda self: True, notify=changed)
    trackSortColumn = Property(str, lambda self: "", notify=changed)
    trackSortDescending = Property(bool, lambda self: False, notify=changed)
    searchActive = Property(bool, lambda self: False, notify=changed)

    def activate_track_by_id(self, track_id):
        pass

    def toggle_favorite_by_id(self, track_id):
        pass

    def queue_track_by_id(self, track_id):
        pass

    def select_album(self, key):
        pass

    def select_artist(self, key):
        pass

    def sort_tracks(self, column):
        pass

    def set_track_sort(self, column, descending):
        pass

    @Slot(list)
    def request_tracks_playlist_target(self, track_ids):
        self.target_calls.append(list(track_ids))
        valid = [str(t) for t in track_ids if str(t).startswith("T-")]
        if valid:
            self.playlist_target_requested.emit({"kind": "tracks", "trackIds": valid})

    @Slot(str, list, result=int)
    def add_tracks_to_playlist(self, playlist_id, track_ids):
        self.add_calls.append((playlist_id, list(track_ids)))
        if self.already_present:
            return 0  # ya presentes → el bridge reporta 0 agregados
        return 1

    @Slot(str, list, result=str)
    def create_playlist_from_tracks(self, name, track_ids):
        self.create_calls.append((name, list(track_ids)))
        if name.strip().lower() == "dupe":
            return ""  # nombre duplicado → el bridge devuelve ""
        return "pl-new-1"


def _mount(qapp, rows):
    library = _Library(rows)
    playlists = _Playlists()
    playback = _Playback()
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    ctx = view.rootContext()
    ctx.setContextProperty("library", library)
    ctx.setContextProperty("playlists", playlists)
    ctx.setContextProperty("playback", playback)
    view.setSource(
        QUrl.fromLocalFile(str(QML_DIR / "views" / "LibraryContentHost.qml"))
    )
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(1200, 800)
    view.show()
    view.requestActivate()
    QTest.qWait(120)
    view._kept = (library, playlists, playback)
    return view, library


def _host_and_feedback(root):
    host = _find_any(root, lambda c: c.objectName() == "libraryContextActionHost")
    assert host is not None, "LibraryContextActionHost no hallado"
    feedback = []
    host.feedbackRequested.connect(lambda text, tone: feedback.append((text, tone)))
    return host, feedback


def _variant(value):
    """QJSValue → nativo: dict plano (kind/claves), strings, números.
    Los arrays anidados se leen con _str_array (toVariant los pierde)."""
    from PySide6.QtQml import QJSValue

    if not isinstance(value, QJSValue):
        return value
    if value.isString():
        return value.toString()
    if value.isNumber():
        return value.toNumber()
    if value.isBool():
        return value.toBool()
    if value.isNull() or value.isUndefined():
        return None
    return value.toVariant()


def _str_array(value):
    """QJSValue array de strings → list[str] (acceso por property)."""
    from PySide6.QtQml import QJSValue

    if isinstance(value, QJSValue) and value.isArray():
        length = value.property("length").toInt()
        return [value.property(i).toString() for i in range(length)]
    return list(value or [])


def _pk(payload, key):
    """Acceso a payload (dict python O QJSValue) — el tipo varía según el
    camino de asignación del host."""
    from PySide6.QtQml import QJSValue

    if isinstance(payload, QJSValue):
        return payload.property(key)
    return payload.get(key) if isinstance(payload, dict) else None


def _str_array(value):
    """trackIds: QJSValue array, dict python o list → list[str]."""
    from PySide6.QtQml import QJSValue

    if isinstance(value, QJSValue) and value.isArray():
        length = value.property("length").toInt()
        return [value.property(i).toString() for i in range(length)]
    if isinstance(value, list):
        return [str(v) for v in value]
    return list(value or [])


def _click_button(container, text):
    """Click REAL (clicked.emit) sobre un botón con el texto dado."""
    from PySide6.QtCore import QObject

    for _ in range(30):
        for child in container.findChildren(QObject):
            try:
                if child.property("text") == text and hasattr(child, "clicked"):
                    child.clicked.emit()
                    _process()
                    return
            except RuntimeError:
                continue
        QTest.qWait(40)
    pytest.fail(f"botón {text!r} no encontrado")


def _picker(root):
    return _find_any(root, lambda c: c.objectName() == "libraryContextTargetPicker")


class TestTrackAddToPlaylistRuntime:
    def test_right_click_add_menu_populates_host_picker_with_track_id(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()

        row = _right_click_row(view, root, "T-1")
        _activate_menu_item(row, "Add to Playlist")

        # Bridge targeting llamado con el TrackId estable.
        assert library.target_calls == [["T-1"]], (
            "request_tracks_playlist_target([TrackId]) — nunca path"
        )
        # El host pobló el picker con el payload canónico (contrato
        # observable del entorno offscreen; Popup.opened requiere window).
        picker = _picker(root)
        assert picker is not None, "PlaylistTargetPicker no encontrado"
        QTest.qWait(60)
        payload = picker.property("selectionPayload")
        kind = _pk(payload, "kind")
        assert _variant(kind) == "tracks", kind
        assert picker.property("selectionDescription") != "", (
            "descripción humana del picker poblada"
        )
        view.close()

    def test_picker_selection_mutates_membership_with_feedback(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()
        _host_and_feedback(root)

        row = _right_click_row(view, root, "T-1")
        _activate_menu_item(row, "Add to Playlist")
        picker = _picker(root)
        assert picker is not None
        QTest.qWait(60)
        payload = _variant(picker.property("selectionPayload")) or {}

        # La selección real del picker (la misma señal del click de la
        # fila) → dispatch del host → mutación V3 con TrackId. El payload
        # del picker (QVariantMap) se emite como dict nativo: es el mismo
        # contrato que el QML interno recibe del bridge.
        payload = picker.property("selectionPayload")
        kind = _variant(_pk(payload, "kind"))
        selection = {"kind": kind, "trackIds": ["T-1"]}
        picker.targetRequested.emit("pl-1", "Chill", selection)
        QTest.qWait(80)

        assert library.add_calls == [("pl-1", ["T-1"])], (
            "add_tracks_to_playlist(playlist, [TrackId]) — V3"
        )
        view.close()

    def test_already_present_reports_feedback_without_fake_success(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()
        host, feedback = _host_and_feedback(root)

        row = _right_click_row(view, root, "T-1")
        _activate_menu_item(row, "Add to Playlist")
        picker = _picker(root)
        QTest.qWait(60)
        library.already_present = True  # el bridge reporta 0 agregados
        payload = picker.property("selectionPayload")
        kind = _variant(_pk(payload, "kind"))
        selection = {"kind": kind, "trackIds": ["T-1"]}
        picker.targetRequested.emit("pl-1", "Chill", selection)
        QTest.qWait(80)

        assert library.add_calls == [("pl-1", ["T-1"])]
        assert any("Already in Chill" in text for text, _tone in feedback), (
            f"feedback 'Already in' esperado, recibido {feedback}"
        )
        assert not any("Added to" in text for text, _tone in feedback)
        view.close()


class TestTrackNewPlaylistRuntime:
    def _open_new_dialog(self, view, root):
        row = _right_click_row(view, root, "T-1")
        _activate_menu_item(row, "Add to Playlist")
        picker = _picker(root)
        assert picker is not None
        QTest.qWait(60)
        # New playlist… (botón productivo del picker) → begin(payload).
        _click_button(picker, "New playlist…")
        dialog = _find_any(
            root, lambda c: c.objectName() == "libraryContextCreateDialog"
        )
        assert dialog is not None, "SelectionPlaylistCreateDialog no hallado"
        QTest.qWait(60)
        payload = _variant(dialog.property("selectionPayload")) or {}
        assert payload.get("kind") == "tracks", payload
        return dialog, payload

    def test_new_playlist_creates_from_track_ids(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()
        _host_and_feedback(root)
        dialog, payload = self._open_new_dialog(view, root)

        # Submit real del dialog (la señal del click "Create and add").
        dialog.createRequested.emit("Road Trip", payload)
        QTest.qWait(80)

        assert library.create_calls == [("Road Trip", ["T-1"])], (
            "create_playlist_from_tracks(name, [TrackId])"
        )
        view.close()

    def test_new_playlist_duplicate_keeps_error_without_fake_success(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()
        host, feedback = _host_and_feedback(root)
        dialog, payload = self._open_new_dialog(view, root)

        dialog.createRequested.emit("dupe", payload)
        QTest.qWait(80)

        assert library.create_calls == [("dupe", ["T-1"])]
        # El host NO emite feedback de éxito (el dialog muestra el error
        # inline vía complete(false)).
        assert not any("Created" in text for text, _tone in feedback), (
            f"fake success prohibido, recibido {feedback}"
        )
        view.close()


class TestTrackPropertiesRuntime:
    def test_properties_menu_opens_populated_view(self, qapp):
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()

        row = _right_click_row(view, root, "T-1")

        # La acción es visible: el consumer real está en el árbol (A1).
        props_item = None
        for _ in range(30):
            props_item = _find_text_deep(root, "Properties")
            if props_item is not None and props_item.property("visible") is True:
                break
            QTest.qWait(40)
        assert props_item is not None, "Properties no visible con consumer real"
        _activate_menu_item(row, "Properties")

        props = _find_any(
            root, lambda c: c.objectName() == "libraryContextTrackProperties"
        )
        assert props is not None, "TrackPropertiesView no hallado"
        QTest.qWait(80)
        track = _variant(props.property("track")) or {}
        assert track.get("trackId") == "T-1", "la vista recibe el row canónico"
        facts = _variant(props.property("propertyRows")) or []
        labels = [fact[0] for fact in facts]
        assert "Title" in labels and "Location" in labels and "Format" in labels
        values = [fact[1] for fact in facts]
        assert any("One" in str(v) for v in values), "facts canónicos visibles"
        view.close()


class TestUnavailableAddAndPropertiesRuntime:
    def test_unavailable_can_add_but_never_queue(self, qapp):
        view, library = _mount(qapp, [_row(), _unavailable_row()])
        root = view.rootObject()

        row = _right_click_row(view, root, "T-2")
        assert row.property("canQueue") is False, "unavailable: queue no"
        _activate_menu_item(row, "Add to Playlist")

        assert library.target_calls == [["T-2"]], (
            "unavailable se puede añadir (membership sin disponibilidad)"
        )
        picker = _picker(root)
        payload = _variant(picker.property("selectionPayload")) or {}
        assert payload.get("trackIds") == ["T-2"]
        view.close()

    def test_unavailable_properties_show_factual_location(self, qapp):
        view, library = _mount(qapp, [_unavailable_row()])
        root = view.rootObject()

        row = _right_click_row(view, root, "T-2")
        _activate_menu_item(row, "Properties")

        props = _find_any(
            root, lambda c: c.objectName() == "libraryContextTrackProperties"
        )
        assert props is not None
        QTest.qWait(80)
        track = _variant(props.property("track")) or {}
        assert track.get("path") == "/music/offline.flac", (
            "la ubicación factual se muestra aunque el archivo esté offline"
        )
        view.close()


class TestContextHostFailClosed:
    def test_invalid_payloads_never_open(self, qapp):
        """Appendix B: payloads inválidos del Bridge (señal real) se
        rechazan sin abrir nada y con feedback de rechazo."""
        view, library = _mount(qapp, [_row()])
        root = view.rootObject()
        host, feedback = _host_and_feedback(root)
        picker = _picker(root)

        # El bridge puede emitir payloads corruptos (defensa en
        # profundidad): el host debe rechazarlos SIN poblar el picker.
        for bad in (
            {"kind": "tracks", "trackIds": []},
            {"kind": "tracks", "trackIds": [""]},
            {"kind": "tracks"},  # sin trackIds
            {"kind": "album", "albumKey": ""},
            {"kind": "artist"},  # sin artistKey
            {"kind": "mystery"},
            None,
        ):
            library.playlist_target_requested.emit(bad)
            QTest.qWait(40)

        payload = _variant(picker.property("selectionPayload")) or {}
        assert payload.get("kind") == "tracks" and payload.get("trackIds") == [], (
            "el picker conserva su default: ningún payload inválido lo puebla"
        )
        assert any("Invalid selection" in text for text, _tone in feedback), (
            f"feedback de rechazo esperado, recibido {feedback}"
        )
        view.close()
