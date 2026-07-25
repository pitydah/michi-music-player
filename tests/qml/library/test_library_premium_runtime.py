from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QJSEngine, QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library")]

QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"

SECTION_PAGES = (
    ("pages/library/GenresPage.qml", "genresPage", 3),
    ("pages/library/ComposersPage.qml", "composersPage", 4),
    ("pages/library/FolderBrowserPage.qml", "folderBrowserPage", 5),
    ("pages/library/CollectionsPage.qml", "libraryCollectionsPage", 6),
    ("pages/library/FavoritesPage.qml", "favoritesPage", 6),
    ("pages/library/RecentPage.qml", "recentPage", 6),
    ("pages/library/MostPlayedPage.qml", "mostPlayedPage", 6),
    ("pages/library/UnplayedPage.qml", "unplayedPage", 6),
    ("pages/library/YearsPage.qml", "yearsPage", 6),
    ("pages/library/MissingPage.qml", "missingPage", 6),
)

COMPONENTS = (
    ("components/ContextToolbar.qml", "contextToolbar"),
    ("components/layout/MichiPage.qml", "michiPage"),
    ("components/layout/MichiPageHeader.qml", "michiPageHeader"),
    ("components/MichiLibraryToolbar.qml", "michiLibraryToolbar"),
    ("pages/library/LibraryPage.qml", "libraryPage_control"),
    ("pages/library/LibraryNavigationBar.qml", "libraryNavigationBar"),
    ("pages/library/LibraryFilterBar.qml", "libraryFilterBar"),
    ("pages/library/LibraryTrackTable.qml", "libraryTrackTable"),
    ("pages/library/LibrarySelectionBar.qml", "librarySelectionBar"),
    ("pages/library/LibraryContextMenu.qml", "LibraryContextMenu"),
    ("pages/library/AlbumDetailPage.qml", "albumDetailPage"),
    ("pages/library/ArtistDetailPage.qml", "artistDetailPage"),
    ("shell/PageStack.qml", "pageStack"),
) + tuple((path, name) for path, name, _index in SECTION_PAGES)


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


@pytest.mark.parametrize("width", (800, 1200))
def test_library_uses_canonical_page_surface_at_supported_widths(engine, width):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "pages/library/LibraryPage.qml")))
    assert component.isReady(), component.errorString()

    instance = component.createWithInitialProperties({"width": width, "height": 700})
    assert instance is not None, component.errorString()

    header = instance.findChild(QObject, "michiPageHeader")
    body = instance.findChild(QObject, "michiPageBody")
    toolbar = instance.findChild(QObject, "michiLibraryToolbar")
    visible_headers = [
        item for item in instance.findChildren(QObject, "michiPageHeader")
        if item.property("visible")
    ]
    assert header is not None
    assert header.property("title") == "Biblioteca"
    assert body is not None
    assert body.property("height") > 0
    assert toolbar is not None
    assert toolbar.property("title") == "Canciones"
    assert len(visible_headers) == 1

    instance.deleteLater()


def test_library_uses_shared_page_states() -> None:
    source = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()

    assert "MichiLoadingState {" in source
    assert source.count("MichiEmptyState {") == 5
    assert source.count("MichiErrorState {") == 2
    assert "LibraryEmptyState {" not in source
    assert "LibraryErrorState {" not in source


def test_library_secondary_navigation_exposes_target_information_architecture() -> None:
    source = (QML_ROOT / "pages/library/LibraryNavigationBar.qml").read_text()

    for route in (
        "library.songs",
        "library.albums",
        "library.artists",
        "library.genres",
        "library.composers",
        "library.folders",
        "library.collections",
    ):
        assert route in source


@pytest.mark.parametrize(("relative_path", "object_name", "expected_index"), SECTION_PAGES)
def test_library_section_pages_share_secondary_navigation(
    engine,
    relative_path,
    object_name,
    expected_index,
):
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    assert component.isReady(), component.errorString()
    instance = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert instance is not None, component.errorString()

    navigation = instance.findChild(QObject, "libraryNavigationBar")
    header = instance.findChild(QObject, "michiPageHeader")
    assert navigation is not None
    assert navigation.property("currentIndex") == expected_index
    assert header is not None
    assert header.property("visible") is True
    assert header.property("title") != ""

    instance.deleteLater()


def test_library_section_actions_use_canonical_routes_and_model_api() -> None:
    genres = (QML_ROOT / "pages/library/GenresPage.qml").read_text()
    composers = (QML_ROOT / "pages/library/ComposersPage.qml").read_text()
    years = (QML_ROOT / "pages/library/YearsPage.qml").read_text()
    folders = (QML_ROOT / "pages/library/FolderBrowserPage.qml").read_text()

    assert 'navigateWithParams("library.genre_detail"' in genres
    assert 'navigateWithParams("library.composer_detail"' in composers
    assert "root.lib.setYearFilter(String(year))" in years
    assert "root.folderModel.refresh(root._currentPath)" in folders
    assert 'refresh("parent_path"' not in folders
    assert "Keys.onReturnPressed" in genres
    assert "Keys.onReturnPressed" in composers
    assert "Keys.onReturnPressed" in years


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


def test_album_refresh_is_chronological_without_view_switch_queries() -> None:
    from ui_qml_bridge.library_refresh_coordinator import LibraryRefreshCoordinator

    album_model = MagicMock()
    coordinator = LibraryRefreshCoordinator(
        album_model=album_model,
        library_bridge=SimpleNamespace(_search_query="query"),
    )

    coordinator.refresh_albums()

    kwargs = album_model.refresh.call_args.kwargs
    assert kwargs["search"] == "query"
    assert kwargs["sort"] == "year"
    assert kwargs["asc"] is False
    assert kwargs["favorites"] is False


def test_filter_bar_exposes_composer_contract() -> None:
    source = (QML_ROOT / "pages/library/LibraryFilterBar.qml").read_text()

    assert "property string composerText" in source
    assert "signal composerFilterChanged" in source
    assert 'placeholderText: qsTr("Compositor")' in source


def test_catalog_models_forward_complete_filter_state() -> None:
    from ui_qml.models.AlbumListModel import AlbumListModel
    from ui_qml.models.ArtistListModel import ArtistListModel

    query = MagicMock()
    query.count_albums.return_value = 0
    query.fetch_albums.return_value = []
    query.count_artists.return_value = 0
    query.fetch_artists.return_value = []
    filters = {"fmt": "flac", "composer": "Composer", "favorites": True}

    AlbumListModel(query_service=query)._fetch_count(**filters)
    ArtistListModel(query_service=query)._fetch_page(0, 100, **filters)

    query.count_albums.assert_called_once_with(**filters)
    query.fetch_artists.assert_called_once_with(offset=0, limit=100, **filters)
