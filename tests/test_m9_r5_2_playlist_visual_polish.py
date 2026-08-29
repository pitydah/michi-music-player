"""Structural guards for the screenshot-led playlist visual polish."""

from pathlib import Path


QML_ROOT = Path("src/michi/presentation/qml")


def read(relative_path: str) -> str:
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def test_overview_header_and_grid_share_a_left_axis() -> None:
    overview = read("playlists/PlaylistsView.qml")
    assert 'role: "display"' in overview
    assert "cellWidth: Math.min(width, targetCellWidth)" in overview
    assert "anchors.left: parent.left" in overview
    assert "anchors.leftMargin: MichiSpacing.sm" in overview
    assert "cellWidth: width / columnCount" not in overview


def test_detail_navigation_is_integrated_into_the_hero() -> None:
    detail = read("playlists/PlaylistDetailView.qml")
    hero = read("playlists/PlaylistHero.qml")
    assert 'objectName: "playlistBackButton"' in detail
    assert "navigationInset: MichiMetrics.controlMedium" in detail
    assert "property real navigationInset: 0" in hero
    assert "root.navigationInset + MichiSpacing.sm" in hero
    assert "Top bar (fixed)" not in detail


def test_hero_keeps_only_primary_actions_visible() -> None:
    hero = read("playlists/PlaylistHero.qml")
    detail = read("playlists/PlaylistDetailView.qml")
    assert 'qsTr("Play")' in hero
    assert 'qsTr("Shuffle")' in hero
    assert 'qsTr("Add tracks")' in hero
    assert 'qsTr("Customize appearance")' not in hero
    assert 'qsTr("Customize appearance…")' in detail
    assert "Keys.onSpacePressed: root.customizeAppearanceRequested()" in hero


def test_track_table_prioritizes_artwork_and_readable_metadata() -> None:
    table = read("playlists/PlaylistTrackList.qml")
    header = read("playlists/PlaylistColumnHeader.qml")
    assert 'objectName: "playlistTrackArtwork_" + index' in table
    assert "Layout.preferredWidth: 40" in table
    assert 'sourcePath: modelData.artworkPath || ""' in table
    assert "trackList.width * 0.34" in table
    assert table.count("trackList.width * 0.21") == 2
    assert "root.width * 0.34" in header
    assert header.count("root.width * 0.21") == 2
    assert "LibraryTrackColumnState.formatWidth" in header
    assert "Layout.preferredWidth: 76" in header
    assert header.count("opacity: 0.58") == 5


def test_now_playing_track_card_is_compact_without_moving_bar_zones() -> None:
    bar = read("player/NowPlayingBar.qml")
    assert "implicitHeight: 154" in bar
    assert "Layout.preferredHeight: 82" in bar
    assert "Layout.preferredWidth: 62" in bar
    assert 'objectName: "playbackZone"' in bar
    assert 'objectName: "outputZone"' in bar
    assert "Layout.preferredHeight: 94" not in bar
