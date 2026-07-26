"""Static contracts for the compact library chrome."""

from pathlib import Path


QML_ROOT = Path(__file__).resolve().parents[3] / "ui_qml"


def test_library_uses_filter_popover_without_layout_height() -> None:
    source = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()
    popover = (QML_ROOT / "pages/library/LibraryFilterPopover.qml").read_text()

    assert "LibraryFilterPopover {" in source
    assert "implicitHeight: 0" in popover
    assert "onFiltersRequested: filterBar.open()" in source


def test_album_view_selector_lives_in_context_toolbar() -> None:
    page = (QML_ROOT / "pages/library/LibraryPage.qml").read_text()

    assert "viewModes: root._currentLibrarySection === 1" in page
    assert "onViewModeChanged:" in page
    assert "albumViewHost.selectView(index)" in page


def test_formats_are_compact_combo_box_options() -> None:
    source = (QML_ROOT / "pages/library/LibraryFilterPopover.qml").read_text()

    assert "ComboBox {" in source
    assert 'qsTr("Todos los formatos")' in source
    assert "Flickable" not in source
