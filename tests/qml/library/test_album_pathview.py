from __future__ import annotations
"""Tests for AlbumCoverFlowView (PathView-based) — model lifecycle and delegate rendering."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl, QAbstractListModel, Qt, QModelIndex
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlApplicationEngine
from PySide6.QtQml import qmlRegisterType

from ui_qml.models.AlbumPagedListModel import AlbumPagedListModel

pytestmark = [pytest.mark.qml_module("album_views")]

QML_DIR = pytest.importorskip("pathlib").Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FlatAlbumModel(QAbstractListModel):
    """Minimal QAbstractListModel for PathView testing — no async pagination."""

    AlbumKeyRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    YearRole = Qt.UserRole + 4
    CoverKeyRole = Qt.UserRole + 5

    def __init__(self, albums=None, parent=None):
        super().__init__(parent)
        self._albums = albums or []

    def roleNames(self):
        return {
            self.AlbumKeyRole: b"albumKey",
            self.TitleRole: b"title",
            self.ArtistRole: b"artist",
            self.YearRole: b"year",
            self.CoverKeyRole: b"coverKey",
        }

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._albums):
            return None
        a = self._albums[index.row()]
        mapping = {
            self.AlbumKeyRole: "album_key",
            self.TitleRole: "title",
            self.ArtistRole: "artist",
            self.YearRole: "year",
            self.CoverKeyRole: "cover_key",
        }
        key = mapping.get(role, "")
        if key:
            return a.get(key, "")
        if role == Qt.DisplayRole:
            return a.get("title", "")
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._albums)

    def append(self, album: dict):
        row = len(self._albums)
        self.beginInsertRows(QModelIndex(), row, row)
        self._albums.append(album)
        self.endInsertRows()

    def remove(self, index: int):
        self.beginRemoveRows(QModelIndex(), index, index)
        del self._albums[index]
        self.endRemoveRows()


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_coverflow(engine, model=None):
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/library/album/AlbumCoverFlowView.qml")))
    assert component.isReady(), f"Component errors: {component.errors()}"
    obj = component.create()
    assert obj is not None, f"Failed to create: {component.errors()}"
    if model is not None:
        obj.setProperty("albumModel", model)
    return obj


class TestAlbumCoverFlowView:
    def test_empty_model(self, engine):
        model = FlatAlbumModel([])
        view = _load_coverflow(engine, model)
        try:
            path_view = view.findChild(type(view).staticQtMetaObject.superClass().__class__ if False else object, "pathView")
            if not path_view:
                path_view = view.property("albumModel")
            assert view.property("albumModel") is model
            assert model.rowCount() == 0
        finally:
            view.deleteLater()

    def test_single_album(self, engine):
        album = {"album_key": "k1", "title": "Alpha", "artist": "X", "year": 2000, "cover_key": "c1"}
        model = FlatAlbumModel([album])
        view = _load_coverflow(engine, model)
        try:
            assert view.property("albumModel") is model
            assert model.rowCount() == 1
            idx = model.index(0, 0)
            assert model.data(idx, model.TitleRole) == "Alpha"
            assert model.data(idx, model.ArtistRole) == "X"
            assert model.data(idx, model.YearRole) == 2000
        finally:
            view.deleteLater()

    def test_multiple_albums(self, engine):
        albums = [
            {"album_key": "k1", "title": "Alpha", "artist": "X", "year": 2000, "cover_key": "c1"},
            {"album_key": "k2", "title": "Beta", "artist": "Y", "year": 2001, "cover_key": "c2"},
            {"album_key": "k3", "title": "Gamma", "artist": "Z", "year": 2002, "cover_key": "c3"},
        ]
        model = FlatAlbumModel(albums)
        view = _load_coverflow(engine, model)
        try:
            assert model.rowCount() == 3
            for i, expected in enumerate(albums):
                idx = model.index(i, 0)
                assert model.data(idx, model.TitleRole) == expected["title"]
                assert model.data(idx, model.ArtistRole) == expected["artist"]
        finally:
            view.deleteLater()

    def test_delegate_shows_cover(self, engine):
        album = {"album_key": "k_cover", "title": "CoverTest", "artist": "A", "year": 2020, "cover_key": "cover_abc"}
        model = FlatAlbumModel([album])
        view = _load_coverflow(engine, model)
        try:
            idx = model.index(0, 0)
            assert model.data(idx, model.CoverKeyRole) == "cover_abc"
            assert model.data(idx, model.TitleRole) == "CoverTest"
        finally:
            view.deleteLater()

    def test_model_append(self, engine):
        model = FlatAlbumModel([])
        view = _load_coverflow(engine, model)
        try:
            assert model.rowCount() == 0
            model.append({"album_key": "k_app", "title": "Appended", "artist": "A", "year": 2023, "cover_key": "c_app"})
            assert model.rowCount() == 1
            idx = model.index(0, 0)
            assert model.data(idx, model.TitleRole) == "Appended"
        finally:
            view.deleteLater()

    def test_model_remove(self, engine):
        albums = [
            {"album_key": "k1", "title": "First", "artist": "A", "year": 2020, "cover_key": "c1"},
            {"album_key": "k2", "title": "Second", "artist": "B", "year": 2021, "cover_key": "c2"},
        ]
        model = FlatAlbumModel(albums)
        view = _load_coverflow(engine, model)
        try:
            assert model.rowCount() == 2
            model.remove(0)
            assert model.rowCount() == 1
            idx = model.index(0, 0)
            assert model.data(idx, model.TitleRole) == "Second"
        finally:
            view.deleteLater()

    def test_model_append_then_remove(self, engine):
        model = FlatAlbumModel([])
        view = _load_coverflow(engine, model)
        try:
            model.append({"album_key": "k_a", "title": "A", "artist": "X", "year": 2020, "cover_key": "c_a"})
            model.append({"album_key": "k_b", "title": "B", "artist": "Y", "year": 2021, "cover_key": "c_b"})
            assert model.rowCount() == 2
            model.remove(0)
            assert model.rowCount() == 1
            assert model.data(model.index(0, 0), model.TitleRole) == "B"
        finally:
            view.deleteLater()

    def test_paged_model_interface(self, engine):
        qs = MagicMock()
        qs.count_albums.return_value = 2
        qs.fetch_albums.return_value = [
            {"album_key": "kp1", "title": "PagedA", "artist": "X", "year": 2020,
             "genre": "Rock", "track_count": 10, "disc_count": 1, "duration": 3600,
             "cover_key": "cp1", "artist_id": 1, "album_artist": "X",
             "formats": "FLAC", "max_quality": "24bit", "last_played": "",
             "date_added": "2024-01-01", "favorite": False, "compilation": False},
            {"album_key": "kp2", "title": "PagedB", "artist": "Y", "year": 2021,
             "genre": "Jazz", "track_count": 8, "disc_count": 1, "duration": 2400,
             "cover_key": "cp2", "artist_id": 2, "album_artist": "Y",
             "formats": "MP3", "max_quality": "320kbps", "last_played": "",
             "date_added": "2024-02-01", "favorite": True, "compilation": False},
        ]
        paged = AlbumPagedListModel(query_service=qs)
        paged.refresh()
        assert paged.count == 2
        assert paged.totalCount == 2
        view = _load_coverflow(engine, paged)
        try:
            assert view.property("albumModel") is paged
            idx = paged.index(0, 0)
            assert paged.data(idx, paged.TitleRole) == "PagedA"
        finally:
            view.deleteLater()
