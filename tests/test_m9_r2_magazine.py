"""Test MagazineView unified single-scroller architecture (M9-R2.1)."""

from pathlib import Path


def test_magazine_view_is_single_scroller_listview() -> None:
    qml_path = (
        Path(__file__).parent.parent
        / "src"
        / "michi"
        / "presentation"
        / "qml"
        / "views"
        / "MagazineView.qml"
    )
    content = qml_path.read_text(encoding="utf-8")

    # Root must be a ListView (single vertical scroller)
    assert "ListView {" in content
    assert 'objectName: "albumMagazineView"' in content
    assert "ScrollBar.vertical:" in content
    assert "header: ColumnLayout" in content

    # Spotlight Hero: no fake "FEATURED ALBUM" text, square artwork layout
    assert "SPOTLIGHT" in content
    assert "FEATURED ALBUM" not in content
    assert "CATALOG ARCHIVE" in content

    # Ensure no nested scrollbars / nested scrollers
    assert content.count("ScrollBar.vertical:") == 1
