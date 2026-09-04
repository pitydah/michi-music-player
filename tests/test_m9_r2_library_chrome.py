"""Tests for M9-R2 Library Chrome, View Options popup, and single-strip toolbar."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _text(relative: str) -> str:
    return (QML / relative).read_text()


def test_six_view_icons_remain_in_library_header() -> None:
    header_src = _text("views/LibraryHeader.qml")
    for view_mode in (
        "view-grid",
        "view-path",
        "view-vinyl",
        "view-timeline",
        "view-magazine",
        "view-list",
    ):
        assert f'icon: "{view_mode}"' in header_src


def test_view_options_popup_consolidates_density_precision_zoom_sort() -> None:
    header_src = _text("views/LibraryHeader.qml")
    popup_src = _text("views/LibraryViewOptionsPopup.qml")
    assert "View options" in header_src
    assert "LibraryViewOptionsPopup" in header_src
    assert "viewPreferenceRequested" in popup_src
    for view_id in (
        "galleryOptions",
        "flowOptions",
        "vinylOptions",
        "chronologyOptions",
        "editorialOptions",
        "studioOptions",
    ):
        assert f"id: {view_id}" in popup_src
    assert "artworkSize" in popup_src
    assert "SORT & FILTER" in popup_src
    assert "CHRONOLOGY" in popup_src


def test_toolbar_is_single_strip_with_source_popover() -> None:
    """POST-MERGE SEMANTIC RECOVERY: el toolbar premium R4 usa el
    FolderDialog DIRECTO (mismo seam P1.1: selectedFolder →
    add_and_scan_music_source_url) en lugar del popover premium; el
    gate verifica el seam contractual exacto y el MusicSourcesDialog."""
    toolbar_src = _text("views/LibraryToolbar.qml")
    assert "LibraryTabs" in toolbar_src
    assert "MichiSearchField" in toolbar_src
    # P1.1 seam: FolderDialog.selectedFolder → add_and_scan_music_source_url
    assert "FolderDialog" in toolbar_src
    assert 'objectName: "libraryFolderDialog"' in toolbar_src
    assert (
        "library.add_and_scan_music_source_url(folderDialog.selectedFolder)"
        in toolbar_src
    )
    assert "MusicSourcesDialog" in toolbar_src
    assert "QUrl.fromLocalFile" not in toolbar_src
    assert "library.scan(" not in toolbar_src
    # Permanent second albums row is removed from toolbar
    assert 'objectName: "albumOrganizationControl"' not in toolbar_src
    assert 'objectName: "albumSizeControl"' not in toolbar_src


def test_library_tabs_has_7_tabs_and_no_folders() -> None:
    tabs_src = _text("views/LibraryTabs.qml")
    expected_tabs = [
        '{ value: "songs", label: qsTr("Songs")',
        '{ value: "albums", label: qsTr("Albums")',
        '{ value: "artists", label: qsTr("Artists")',
        '{ value: "genres", label: qsTr("Genres")',
        '{ value: "favorites", label: qsTr("Favorites")',
        '{ value: "history", label: qsTr("History")',
        '{ value: "recently", label: qsTr("Recently Added")',
    ]
    for tab in expected_tabs:
        assert tab in tabs_src
    assert 'label: "Folders"' not in tabs_src
    assert 'value: "folders"' not in tabs_src
