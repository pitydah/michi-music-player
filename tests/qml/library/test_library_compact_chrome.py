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


def test_album_view_selector_lives_in_shell_header() -> None:
    page = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    header = (QML_ROOT / "shell/HeaderBar.qml").read_text()

    assert "readonly property var headerViewModes:" in page
    assert "function applyHeaderView(index)" in page
    assert "HeaderViewSwitcher {" in header


def test_library_has_no_second_search_field_or_context_toolbar() -> None:
    source = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    assert "MichiSearchField {" not in source
    assert "MichiLibraryToolbar {" not in source


def test_formats_are_compact_combo_box_options() -> None:
    source = (QML_ROOT / "pages/library/LibraryFilterPopover.qml").read_text()

    assert "ComboBox {" in source
    assert 'qsTr("Todos los formatos")' in source
    assert "Flickable" not in source
