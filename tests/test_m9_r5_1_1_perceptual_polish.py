"""M9-R5.1.1 perceptual geometry and engine consequence contracts."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def _block(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def test_scan_and_search_share_control_medium_geometry() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    scan = _block(
        toolbar,
        'objectName: "libraryScanSplitButton"',
        "MichiMenu {",
    )

    assert "Layout.preferredHeight: MichiMetrics.controlMedium" in scan
    assert "Layout.preferredHeight: MichiMetrics.controlLarge" not in scan
    assert 'iconName: ""' in scan
    assert "iconOnly: false" in scan


def test_split_button_is_compact_and_icon_absence_has_no_ghost_gap() -> None:
    split = _qml("controls/MichiSplitButton.qml")

    assert "primaryContent.implicitWidth + MichiSpacing.md * 2" in split
    assert "primaryContent.implicitWidth + MichiSpacing.lg * 2" not in split
    assert "readonly property bool hasPrimaryIcon" in split
    assert "visible: root.hasPrimaryIcon" in split
    assert "visible: !root.iconOnly || !root.hasPrimaryIcon" in split


def test_split_disclosure_and_divider_remain_visually_subordinate() -> None:
    split = _qml("controls/MichiSplitButton.qml")
    divider = _block(
        split,
        "id: segmentDivider",
        "Button {\n                id: secondaryButton",
    )

    assert "readonly property real secondaryWidth: 26" in split
    assert "readonly property real secondaryIconSize: 10" in split
    assert "Layout.preferredWidth: root.secondaryWidth" in split
    assert "width: root.secondaryIconSize" in split
    assert "Layout.fillHeight: true" in divider
    assert "height: MichiMetrics.iconSmall" in divider
    assert "height: parent.height" not in divider


def test_toolbar_gap_separates_resize_hitbox_from_visible_affordance() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    handle = _block(
        toolbar,
        'objectName: "librarySearchResizeHandle"',
        "HoverHandler {",
    )

    assert "columnSpacing: MichiSpacing.sm" in toolbar
    assert "Layout.preferredWidth: visible ? 10 : 0" in handle
    assert "height: MichiMetrics.iconMedium - MichiSpacing.xxs" in handle
    assert "height: parent.height - MichiSpacing.sm" not in handle


def test_engine_surfaces_explain_stop_and_switch_before_selection() -> None:
    popup = _qml("player/AudioEnginePopup.qml")
    settings = _qml("views/AudioEngineSettingsSection.qml")

    for surface in (popup, settings):
        assert "modelData.requiresStop" in surface
        assert 'qsTr("Stop & switch")' in surface
    assert 'qsTr("Stops playback before switching")' in settings


def test_artist_summary_is_content_bounded_without_fixed_album_strip() -> None:
    artist = _qml("views/ArtistDetailView.qml")

    assert "readonly property real summaryHeightBudget" in artist
    assert "summaryColumn.implicitHeight, root.summaryHeightBudget" in artist
    assert "root.height - 300" not in artist
    assert "height: visible ? 244 : 0" not in artist
    assert "albumScrollBar.visible" in artist
    assert "albumScrollBar.implicitHeight" in artist


def test_split_button_preserves_canonical_interaction_material() -> None:
    split = _qml("controls/MichiSplitButton.qml")

    assert split.count("MichiSemanticColors.surfaceHover") == 2
    assert split.count("MichiSemanticColors.surfacePressed") == 2
    assert "MichiFocusRing" in split
    assert "scale:" not in split
    assert "glow" not in split.lower()
