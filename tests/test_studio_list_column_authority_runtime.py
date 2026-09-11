"""POST-R4 P5 — Studio List: packing continue + shared column authority.

AlbumListView productivo (MichiAlbumRow + AlbumTableHeader reales):

- el packing recorre TODAS las columnas (continue): si Artist no cabe,
  Year/Tracks/Duration/Format siguen siendo elegibles;
- header y row consumen AlbumListColumnMetrics: x del título alineada
  ±1px en widths estrecho/medio/amplio × artwork none/small/standard;
- precisionMetadata on/off mantiene la alineación;
- metadataLevel huérfano eliminado del schema studioList.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QUrl  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


class _AlbumLibrary(QObject):
    albums = Property(
        "QVariantList",
        lambda self: [
            {
                "key": "album-1",
                "title": "Kind of Blue",
                "artist": "Miles Davis",
                "artworkPath": "",
                "hasArtwork": False,
                "trackCount": 9,
                "durationMs": 2700000,
                "year": 1959,
                "technicalSummary": "FLAC · 24/96",
                "codecs": ["FLAC"],
            }
        ],
    )

    def select_album(self, key):  # pragma: no cover — QML intent spy
        pass

    def play_album(self, key):  # pragma: no cover
        pass


def _mount_list(qapp, width, preferences, height=600):
    library = _AlbumLibrary()
    view = QQuickView()
    view.engine().addImportPath(str(QML))
    view.rootContext().setContextProperty("library", library)
    view.setSource(QUrl.fromLocalFile(str(QML / "views" / "AlbumListView.qml")))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, height)
    view.show()
    QTest.qWait(120)
    root = view.rootObject()
    root.setProperty("viewPreferences", preferences)
    QTest.qWait(200)
    return view, root


def _walk(obj, predicate):
    if predicate(obj):
        return obj
    for child in obj.childItems():
        found = _walk(child, predicate)
        if found is not None:
            return found
    return None


def _title_x(root, of_header):
    scope = _walk(
        root,
        lambda c: (
            ("AlbumTableHeader" if of_header else "MichiAlbumRow")
            in c.metaObject().className()
            and c.property("visible") is True
        ),
    )
    assert scope is not None, "scope " + ("header" if of_header else "row")
    text = _walk(scope, lambda c: c.property("text") == "Kind of Blue")
    if text is None and of_header:
        text = _walk(scope, lambda c: c.property("text") == "ALBUM")
    assert text is not None, "columna título del " + ("header" if of_header else "row")
    from PySide6.QtCore import QPointF

    return float(text.mapToScene(QPointF(0, 0)).x())


class TestStudioListPacking:
    def test_artist_not_fitting_does_not_block_year(self, qapp):
        """Ancho estrecho: Artist (210px) no cabe pero Year sí — el
        packing usa continue: year/tracks siguen siendo elegibles."""
        prefs = {
            "artistColumn": True,
            "yearColumn": True,
            "tracksColumn": True,
            "durationColumn": True,
            "formatColumn": True,
        }
        view, root = _mount_list(qapp, 500, prefs)
        try:
            assert root.property("showArtistColumn") is False, "Artist no cabe a 500px"
            assert root.property("showYearColumn") is True, (
                "Year cabe aunque Artist no (continue semantics)"
            )
            assert root.property("showTrackCountColumn") is True
        finally:
            view.close()

    def test_wide_viewport_packs_all_columns(self, qapp):
        prefs = {
            "artistColumn": True,
            "yearColumn": True,
            "tracksColumn": True,
            "durationColumn": True,
            "formatColumn": True,
        }
        view, root = _mount_list(qapp, 1500, prefs)
        try:
            for prop in (
                "showArtistColumn",
                "showYearColumn",
                "showTrackCountColumn",
                "showDurationColumn",
                "showTechnicalColumn",
            ):
                assert root.property(prop) is True, prop
        finally:
            view.close()


class TestStudioListSharedGeometry:
    @pytest.mark.parametrize("artwork", ["none", "small", "standard"])
    @pytest.mark.parametrize("width", [800, 1200, 1500])
    def test_header_row_title_aligned(self, qapp, artwork, width):
        """x del título del header == x del título del row (±1px) para
        cada estado de artwork — nunca header 34 con row 0."""
        prefs = {
            "artworkSize": artwork,
            "artistColumn": True,
            "yearColumn": True,
            "tracksColumn": True,
            "durationColumn": True,
            "formatColumn": True,
            "precisionMetadata": True,
        }
        view, root = _mount_list(qapp, width, prefs)
        try:
            header_x = _title_x(root, of_header=True)
            row_x = _title_x(root, of_header=False)
            assert abs(header_x - row_x) <= 1.0, (
                f"artwork={artwork} width={width}: "
                f"header {header_x:.1f} vs row {row_x:.1f}"
            )
        finally:
            view.close()

    @pytest.mark.parametrize("precision", [True, False])
    def test_precision_toggle_keeps_alignment(self, qapp, precision):
        prefs = {
            "artworkSize": "small",
            "artistColumn": True,
            "yearColumn": True,
            "tracksColumn": True,
            "durationColumn": True,
            "formatColumn": True,
            "precisionMetadata": precision,
        }
        view, root = _mount_list(qapp, 1200, prefs)
        try:
            header_x = _title_x(root, of_header=True)
            row_x = _title_x(root, of_header=False)
            assert abs(header_x - row_x) <= 1.0, (
                f"precision={precision}: header {header_x:.1f} vs row {row_x:.1f}"
            )
        finally:
            view.close()


class TestMetadataLevelRemoved:
    def test_studio_list_defaults_have_no_orphan_metadata_level(self):
        src = (QML / "views" / "LibraryView.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        seg = src[src.index("studioList: {") :]
        seg = seg[: seg.index("}") + 1]
        assert "metadataLevel" not in seg, (
            "el schema studioList ya no declara metadataLevel (setting ficticio)"
        )

    def test_album_list_view_does_not_consume_metadata_level(self):
        src = (QML / "views" / "AlbumListView.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        assert "metadataLevel" not in src
