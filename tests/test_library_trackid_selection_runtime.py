"""POST-R4 P3 — MichiTrackTable simple-selection TrackId authority.

La selección simple de la tabla PRODUCTIVA se ata al TrackId del row, no
al índice visual:

- seleccionar B (índice 1) y reordenar: B sigue seleccionado aunque su
  índice cambie;
- si B desaparece del modelo (filtro), la política explícita de la vista
  es CLEAR (selectedTrackId == "") — nunca transferencia accidental a
  otro TrackId; al restaurar B, la selección sigue vacía y ningún otro
  row queda marcado;
- el índice NUNCA cambia la identidad seleccionada.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _row(track_id, title):
    return {
        "trackId": track_id,
        "path": f"/music/{track_id}.flac",
        "title": title,
        "artist": "Artist",
        "album": "Album",
        "durationMs": 1000,
        "artworkPath": "",
        "artistKey": "artist",
        "albumKey": "album",
        "trackNumber": 0,
        "discNumber": 1,
        "genre": "",
        "composer": "",
        "year": 2000,
        "sampleRateHz": 0,
        "bitDepth": 0,
        "channels": 0,
        "bitrateBps": 0,
        "fileSize": 0,
        "codec": "",
        "container": "",
        "formatKey": "unknown",
        "formatLabel": "UNKNOWN",
        "dsdRate": "",
        "unavailable": False,
    }


def _mount_table(rows):
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    view.setSource(QUrl.fromLocalFile(str(QML / "media" / "MichiTrackTable.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(900, 500)
    view.show()
    QTest.qWait(120)
    root = view.rootObject()
    root.setProperty("rows", rows)
    QTest.qWait(250)
    return view, root


def _rows_in_order(root):
    """Delegates vivos con su (trackId, title, y)."""

    def visit(item, out):
        try:
            md = item.property("modelData")
            if isinstance(md, dict) and md.get("trackId"):
                out.append((md["trackId"], md.get("title"), item.y()))
        except RuntimeError:
            pass
        for child in item.childItems():
            visit(child, out)

    out = []
    visit(root, out)
    return out


def _row_items(root):
    def visit(item, out):
        try:
            md = item.property("modelData")
            if isinstance(md, dict) and md.get("trackId"):
                out.append(item)
        except RuntimeError:
            pass
        for child in item.childItems():
            visit(child, out)

    out = []
    visit(root, out)
    return out


def _select_row(view, item):
    """Selección productiva del row: el TrackRow emite selectedRequested
    por el camino contextual (click derecho / menú) — la tabla la ata al
    TrackId (POST-R4 P3). Las coordenadas se mapean al contentItem del
    view (el header Overlay no desplaza el content del ListView)."""
    from PySide6.QtCore import QPoint, Qt

    content = view.contentItem()
    mapped = item.mapToItem(content, 0, 0)
    x = mapped.x() + item.width() / 2
    y = mapped.y() + item.height() / 2
    QTest.mouseClick(view, Qt.RightButton, Qt.NoModifier, QPoint(int(x), int(y)))
    QTest.qWait(150)


class TestTrackIdSelection:
    def _dataset(self):
        return [
            _row("A", "Zulu"),
            _row("B", "Alpha"),
            _row("C", "Mike"),
        ]

    def test_selection_follows_track_id_through_reorder(self, qapp):
        """B seleccionado por click en el índice 1; el reorder lo mueve al
        índice 0 y B SIGUE seleccionado (misma identidad, nuevo índice)."""
        view, root = _mount_table(self._dataset())
        try:
            rows = self._dataset()
            # seleccionar B (segunda fila: título Alpha)
            items = _row_items(root)
            b_item = next(i for i in items if i.property("modelData")["trackId"] == "B")
            _select_row(view, b_item)
            assert root.property("selectedTrackId") == "B"
            assert root.property("selectedIndex") == 1
            # reorder: B al frente (títulos: Alpha primero)
            reordered = [rows[1], rows[0], rows[2]]
            root.setProperty("rows", reordered)
            QTest.qWait(250)
            assert root.property("selectedTrackId") == "B", (
                "el reorder no cambia la identidad seleccionada"
            )
            b_items = [
                i for i in _row_items(root) if i.property("modelData")["trackId"] == "B"
            ]
            assert b_items and b_items[0].property("selected") is True, (
                "B sigue visualmente seleccionado en su nueva posición"
            )
            selected = [i for i in _row_items(root) if i.property("selected") is True]
            assert len(selected) == 1, "exactamente un row seleccionado"
        finally:
            view.close()

    def test_removed_track_id_clears_without_transfer(self, qapp):
        """B desaparece (filtro): la política explícita es clear — ningún
        otro TrackId hereda la selección; al restaurar B no hay selección
        fantasma ni transferencia."""
        view, root = _mount_table(self._dataset())
        try:
            items = _row_items(root)
            b_item = next(i for i in items if i.property("modelData")["trackId"] == "B")
            _select_row(view, b_item)
            assert root.property("selectedTrackId") == "B"
            # filtro: B fuera del modelo
            filtered = [self._dataset()[0], self._dataset()[2]]
            root.setProperty("rows", filtered)
            QTest.qWait(250)
            assert root.property("selectedTrackId") == "", (
                "política: al desaparecer el TrackId la selección se limpia"
            )
            selected = [i for i in _row_items(root) if i.property("selected") is True]
            assert selected == [], "sin transferencia accidental a A/C"
            # restaurar B
            root.setProperty("rows", self._dataset())
            QTest.qWait(250)
            b_items = [
                i for i in _row_items(root) if i.property("modelData")["trackId"] == "B"
            ]
            assert b_items, "B vuelve a existir"
            assert all(i.property("selected") is not True for i in b_items), (
                "B restaurado NO queda seleccionado (política clear explícita)"
            )
            selected = [i for i in _row_items(root) if i.property("selected") is True]
            assert selected == []
        finally:
            view.close()

    def test_clicking_another_row_transfers_selection_by_id(self, qapp):
        """Click en C transfiere la selección a C (por identidad) — nunca
        por posición heredada."""
        view, root = _mount_table(self._dataset())
        try:
            items = _row_items(root)
            b_item = next(i for i in items if i.property("modelData")["trackId"] == "B")
            _select_row(view, b_item)
            assert root.property("selectedTrackId") == "B"
            # reordenar A<->C mientras B sigue seleccionado
            rows = self._dataset()
            root.setProperty("rows", [rows[2], rows[1], rows[0]])
            QTest.qWait(200)
            # click en C (ahora índice 0)
            c_item = next(
                i for i in _row_items(root) if i.property("modelData")["trackId"] == "C"
            )
            _select_row(view, c_item)
            assert root.property("selectedTrackId") == "C"
            assert root.property("selectedIndex") == 0
            selected = [i for i in _row_items(root) if i.property("selected") is True]
            assert len(selected) == 1
            assert selected[0].property("modelData")["trackId"] == "C"
        finally:
            view.close()
