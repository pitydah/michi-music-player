from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QJSEngine, QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"

COMPONENTS = (
    ("components/MichiLibraryToolbar.qml", "michiLibraryToolbar"),
    ("pages/library/LibraryPage.qml", "libraryPage_control"),
    ("pages/library/LibraryFilterBar.qml", "libraryFilterBar"),
    ("pages/library/LibraryTrackTable.qml", "libraryTrackTable"),
    ("pages/library/LibrarySelectionBar.qml", "librarySelectionBar"),
    ("pages/library/LibraryContextMenu.qml", "LibraryContextMenu"),
    ("pages/library/AlbumDetailPage.qml", "albumDetailPage"),
    ("pages/library/ArtistDetailPage.qml", "artistDetailPage"),
    ("shell/PageStack.qml", "pageStack"),
)


@pytest.fixture
def engine(qapp):
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    yield qml_engine
    qml_engine.deleteLater()


@pytest.mark.parametrize(("relative_path", "object_name"), COMPONENTS)
def test_premium_library_component_compiles_and_instantiates(
    engine,
    relative_path,
    object_name,
):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()

    instance = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert instance is not None, component.errorString()
    assert instance.objectName() == object_name
    instance.deleteLater()


def _query_service(track_count: int = 1):
    query = MagicMock()
    query.count_tracks.return_value = track_count
    query.fetch_tracks.return_value = (
        [{"track_id": 1, "title": "Track", "artist": "Artist"}]
        if track_count else []
    )
    query.count_albums.return_value = 1 if track_count else 0
    query.fetch_albums.return_value = (
        [{"album_key": "album-1", "title": "Album", "artist": "Artist"}]
        if track_count else []
    )
    query.count_artists.return_value = 1 if track_count else 0
    query.fetch_artists.return_value = (
        [{"name": "Artist", "track_count": track_count}]
        if track_count else []
    )
    query.count_folders.return_value = 0
    query.fetch_folders.return_value = []
    return query


def test_library_bridge_initializes_models_and_reaches_ready() -> None:
    from ui_qml_bridge.library_bridge import LibraryBridge

    query = _query_service()
    sources = MagicMock()
    sources.list.return_value = [{"enabled": True, "available": True}]
    bridge = LibraryBridge(
        query_service=query,
        track_action_service=MagicMock(),
        library_sources_service=sources,
    )

    result = bridge.ensureLoaded()

    assert result["refreshed"] is True
    assert bridge.state == "READY"
    assert bridge.trackModel.initialized is True
    assert bridge.albumModel.get(0)["album_key"] == "album-1"


def test_library_bridge_does_not_requery_initialized_models() -> None:
    from ui_qml_bridge.library_bridge import LibraryBridge

    query = _query_service()
    bridge = LibraryBridge(
        query_service=query,
        track_action_service=MagicMock(),
    )
    bridge.ensureLoaded()
    initial_calls = query.count_tracks.call_count

    result = bridge.ensureLoaded()

    assert result["refreshed"] is False
    assert query.count_tracks.call_count == initial_calls


def test_empty_library_without_sources_reaches_no_sources() -> None:
    from ui_qml_bridge.library_bridge import LibraryBridge

    sources = MagicMock()
    sources.list.return_value = []
    bridge = LibraryBridge(
        query_service=_query_service(track_count=0),
        track_action_service=MagicMock(),
        library_sources_service=sources,
    )

    bridge.ensureLoaded()

    assert bridge.state == "NO_SOURCES"


def test_active_filter_with_no_matches_reaches_filtered_empty() -> None:
    from ui_qml_bridge.library_bridge import LibraryBridge

    bridge = LibraryBridge(
        query_service=_query_service(track_count=0),
        track_action_service=MagicMock(),
    )
    bridge.ensureLoaded()

    bridge.setFormatFilter("FLAC")

    assert bridge.state == "FILTERED_EMPTY"


def test_page_state_store_accepts_qml_object(qapp) -> None:
    from ui_qml_bridge.page_state_store import PageStateStore

    js_engine = QJSEngine()
    qml_state = js_engine.toScriptValue({"currentTab": 2, "searchText": "jazz"})
    store = PageStateStore()

    store.saveState("library", qml_state)

    assert store.restoreState("library") == {
        "currentTab": 2,
        "searchText": "jazz",
    }


def test_format_and_special_filters_cannot_diverge() -> None:
    from ui_qml_bridge.library_bridge import LibraryBridge

    bridge = LibraryBridge(
        query_service=_query_service(),
        track_action_service=MagicMock(),
    )
    bridge.ensureLoaded()
    bridge.setFavoritesFilter()

    bridge.setFormatFilter("flac")

    assert bridge._filter_favorites is False
    assert bridge.activeFormatFilter == "flac"
    bridge.setUnplayedFilter()
    bridge.clearSpecialFilters()
    assert bridge.activeFormatFilter == "flac"
    assert bridge._filter_unplayed is False
