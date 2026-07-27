"""Contracts for the contextual, single-chrome Library header."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[3]
QML_ROOT = REPO_ROOT / "ui_qml"
VIEW_ICON_ROOT = REPO_ROOT / "icons" / "view"


def _read(relative_path: str) -> str:
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def test_shell_exposes_active_page_context_to_header() -> None:
    page_stack = _read("shell/PageStack.qml")
    app_shell = _read("shell/AppShell.qml")
    header = _read("shell/HeaderBar.qml")
    switcher = _read("components/HeaderViewSwitcher.qml")

    assert "readonly property var currentPage:" in page_stack
    assert "contextPage: pageStack.currentPage" in app_shell
    assert "contextPage.applyHeaderSearch(query, submitted)" in app_shell
    assert "contextPage.applyHeaderView(index)" in app_shell
    assert "contextPage.openHeaderFilters()" in app_shell
    assert "contextPage.refreshHeaderContext()" in app_shell
    assert "HeaderViewSwitcher {" in header
    assert "effectiveSearchPlaceholder" in header
    assert "contextFilterCount" in header
    assert "width: MichiTheme.minimumInteractiveSize" in switcher
    assert "height: MichiTheme.minimumInteractiveSize" in switcher


def test_library_root_declares_real_view_matrix() -> None:
    source = _read("pages/library/LibraryPage.qml")

    for mode_group in (
        "_songViewModes",
        "_albumViewModes",
        "_artistViewModes",
        "_folderViewModes",
    ):
        assert mode_group in source

    for mode_id in (
        '"detailed"',
        '"compact"',
        '"coverflow"',
        '"vinyl"',
        '"timeline"',
        '"editorial"',
        '"split"',
        '"tree"',
    ):
        assert mode_id in source

    assert "compactMode: root._songView === 1" in source
    assert "currentView: root._artistView" in source
    assert "currentView: root._folderView" in source


def test_primary_library_routes_implement_context_contract() -> None:
    routes = (
        "pages/library/tracks/TracksPage.qml",
        "pages/library/AlbumGridPage.qml",
        "pages/library/ArtistGridPage.qml",
        "pages/library/GenresPage.qml",
        "pages/library/ComposersPage.qml",
        "pages/library/FolderBrowserPage.qml",
        "pages/library/CollectionsPage.qml",
    )

    for route in routes:
        source = _read(route)
        assert "headerSearchPlaceholder:" in source, route
        assert "function applyHeaderSearch(" in source, route


def test_redundant_route_headers_are_removed() -> None:
    artist = _read("pages/library/ArtistGridPage.qml")
    genres = _read("pages/library/GenresPage.qml")
    composers = _read("pages/library/ComposersPage.qml")
    folder_content = _read("pages/library/FolderContentView.qml")
    collections = (
        "pages/library/FavoritesPage.qml",
        "pages/library/RecentPage.qml",
        "pages/library/MostPlayedPage.qml",
        "pages/library/UnplayedPage.qml",
        "pages/library/MissingPage.qml",
    )

    assert "Layout.preferredHeight: 44" not in artist
    assert "Layout.preferredHeight: 40" not in genres
    assert "Layout.preferredHeight: 40" not in composers
    assert "Layout.preferredHeight: 52" not in folder_content
    for route in collections:
        assert "LibraryTrackCollectionPage {" in _read(route)


def test_folder_actions_share_one_compact_navigation_strip() -> None:
    browser = _read("pages/library/FolderBrowserPage.qml")
    content = _read("pages/library/FolderContentView.qml")

    assert "embedded: true" in browser
    assert "folder-up.svg" in browser
    assert "folder-root.svg" in browser
    assert "folder-play.svg" in browser
    assert "folder-queue.svg" in browser
    assert "folder-source-add.svg" in browser
    assert "visibleTracks: root.filterTracks" in content
    assert "model: root.visibleTracks" in content


def test_monochrome_view_icons_are_valid_and_consistent() -> None:
    icon_names = (
        "library-table.svg",
        "library-compact.svg",
        "library-grid.svg",
        "library-coverflow.svg",
        "library-vinyl.svg",
        "library-timeline.svg",
        "library-editorial.svg",
        "library-artist-grid.svg",
        "library-artist-list.svg",
        "library-list.svg",
        "library-genre-grid.svg",
        "library-folder-split.svg",
        "library-folder-tree.svg",
    )

    for icon_name in icon_names:
        icon_path = VIEW_ICON_ROOT / icon_name
        root = ElementTree.parse(icon_path).getroot()
        assert root.attrib["viewBox"] == "0 0 24 24", icon_name
        source = icon_path.read_text(encoding="utf-8")
        assert "white" in source, icon_name
        assert "#FF" not in source.upper(), icon_name
