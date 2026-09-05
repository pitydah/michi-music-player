"""Regression gates for the real-app Library visible recovery pass."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src" / "michi" / "presentation" / "qml"


def _read(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_genres_never_hide_rows_behind_full_height_header() -> None:
    source = _read("views/GenresView.qml")
    assert 'Item {\n    id: root\n    objectName: "genresView"' in source
    assert "header: EmptyState" not in source
    assert "visible: genreList.count === 0" in source
    assert "visible: count > 0" in source
    assert "library.select_genre(modelData.key)" in source


def test_historical_per_tab_wayfinding_is_restored_without_views_eyebrow() -> None:
    source = _read("views/LibraryHeader.qml")
    assert 'qsTr("%1 favorites")' in source
    assert 'qsTr("%1 tracks in playback history")' in source
    assert 'qsTr("%1 recently added tracks")' in source
    assert 'qsTr("%1 artists")' in source
    assert 'qsTr("%1 genres")' in source
    assert 'text: qsTr("VIEWS")' not in source


def test_library_tabs_expose_overflow_instead_of_silent_clipping() -> None:
    source = _read("views/LibraryTabs.qml")
    assert "readonly property bool overflowed" in source
    assert 'objectName: "libraryTabsScrollLeft"' in source
    assert 'objectName: "libraryTabsScrollRight"' in source
    assert 'qsTr("Show previous library tabs")' in source
    assert 'qsTr("Show more library tabs")' in source


def test_track_table_customization_has_visible_affordance() -> None:
    source = _read("media/ResizableTrackHeader.qml")
    assert 'objectName: "trackTableOptionsButton"' in source
    assert 'accessibleName: qsTr("Table options")' in source
    assert "onClicked: root.openGlobalContext()" in source
    assert "acceptedButtons: Qt.RightButton" in source


def test_column_resize_feedback_is_local_and_truthful() -> None:
    source = _read("media/ResizableHeaderCell.qml")
    assert "ToolTip.visible: pressed" in source
    assert 'qsTr("%1 · %2 px")' in source
    assert "height: 14" in source
    assert (
        "opacity: resizeArea.containsMouse || resizeArea.pressed ? 1 : 0.34" in source
    )


def test_track_actions_are_discoverable_without_becoming_visual_noise() -> None:
    source = _read("media/TrackRow.qml")
    assert "readonly property real idleActionOpacity: 0.34" in source
    assert "? 1 : 0.18" not in source
    assert source.count("root.idleActionOpacity") >= 7


def test_artist_gallery_does_not_crop_album_sleeves_as_portraits() -> None:
    source = _read("views/ArtistsView.qml")
    assert "|| artistCell.modelData.artworkPath" not in source
    assert "enrichment.artistPortraits[artistCell.modelData.key]" in source
    assert '|| ""' in source
    assert 'qsTr("%n artist(s)", "", library.artists.length)' in source


def test_library_error_copy_remains_translatable() -> None:
    source = _read("views/LibraryContentHost.qml")
    assert 'qsTr("Library unavailable")' in source
    assert 'qsTr("Scan failed")' in source
    message = (
        'qsTr("The library could not be scanned. '
        'Check your music folder and try again.")'
    )
    assert message in source


def test_visible_recovery_does_not_resurrect_file_browser() -> None:
    tabs = _read("views/LibraryTabs.qml")
    host = _read("views/LibraryContentHost.qml")
    assert 'value: "folders"' not in tabs
    assert 'case "folders"' not in host
    assert "FoldersView" not in host
