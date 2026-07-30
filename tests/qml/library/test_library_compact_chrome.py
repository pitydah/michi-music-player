"""Static contracts for the compact library chrome."""
from __future__ import annotations

from pathlib import Path


QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"


def test_library_uses_filter_popover_without_layout_height() -> None:
    source = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    popover = (QML_ROOT / "pages/library/LibraryFilterPopover.qml").read_text()

    assert "LibraryFilterPopover {" in source
    assert "implicitHeight: 0" in popover
    assert "function openHeaderFilters()" in source
    assert "filterBar.open()" in source


def test_album_controls_share_one_local_toolbar() -> None:
    page = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    header = (QML_ROOT / "shell/HeaderBar.qml").read_text()

    assert "readonly property var headerViewModes:" in page
    assert "function applyHeaderView(index)" in page
    assert "HeaderViewSwitcher {" in header
    host = (QML_ROOT / "pages/library/album/AlbumViewHost.qml").read_text()
    assert 'objectName: "albumLibraryToolbar"' in host
    assert 'objectName: "albumViewSelector"' in host
    assert 'objectName: "albumSortSelector"' in host
    assert 'objectName: "albumDensitySelector"' in host
    assert "modeSelector" not in host
    assert 'qsTr("Ctrl+1…5 · Ctrl+Tab")' not in host

def test_library_has_no_second_search_field_or_context_toolbar() -> None:
    source = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    assert "MichiSearchField {" not in source
    assert "MichiLibraryToolbar {" not in source


def test_formats_are_compact_combo_box_options() -> None:
    source = (QML_ROOT / "pages/library/LibraryFilterPopover.qml").read_text()

    assert "ComboBox {" in source
    assert 'qsTr("Todos los formatos")' in source
    assert "Flickable" not in source
