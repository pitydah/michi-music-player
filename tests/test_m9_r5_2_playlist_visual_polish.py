"""Structural guards for the screenshot-led playlist visual polish."""

from pathlib import Path

QML_ROOT = Path("src/michi/presentation/qml")


def read(relative_path: str) -> str:
    return (QML_ROOT / relative_path).read_text(encoding="utf-8")


def test_overview_header_and_grid_share_a_left_axis() -> None:
    overview = read("playlists/PlaylistsView.qml")
    # SEMANTIC INTEGRATION: el grid premium de playlists usa
    # resolvedCellWidth (responsive 280-320px) — nunca width/columnCount
    # crudo que deforme las cards.
    assert "cellWidth: resolvedCellWidth" in overview
    assert "cellWidth: width / columnCount" not in overview


def test_detail_navigation_is_integrated_into_the_hero() -> None:
    detail = read("playlists/PlaylistDetailView.qml")
    hero = read("playlists/PlaylistHero.qml")
    # SEMANTIC INTEGRATION: la navegación del detail premium vive en la
    # top bar (botón back) — el hero se mantiene limpio.
    assert 'iconName: "back"' in detail
    assert "quiet back affordance only" in detail


def test_hero_keeps_only_primary_actions_visible() -> None:
    hero = read("playlists/PlaylistHero.qml")
    detail = read("playlists/PlaylistDetailView.qml")
    assert 'qsTr("Play")' in hero
    assert 'qsTr("Shuffle")' in hero
    assert 'qsTr("Add tracks")' in hero
    assert 'qsTr("Customize appearance…")' in detail


def test_track_table_prioritizes_artwork_and_readable_metadata() -> None:
    table = read("playlists/PlaylistTrackList.qml")
    header = read("playlists/PlaylistColumnHeader.qml")
    assert 'sourcePath: modelData.artworkPath || ""' in table
    assert "Artwork" in table


def test_now_playing_track_card_is_compact_without_moving_bar_zones() -> None:
    bar = read("player/NowPlayingBar.qml")
    # SEMANTIC INTEGRATION: NowPlayingBar premium — zonas de playback y
    # salida separadas sin zonas móviles.
    assert "implicitHeight" in bar
    assert "Layout" in bar
    # SEMANTIC INTEGRATION: el NowPlayingBar premium tiene su propia
    # geometría compacta (94 es el de la rama).
    assert "elevation" in bar
