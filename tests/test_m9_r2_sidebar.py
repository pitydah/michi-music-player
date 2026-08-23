"""Tests for M9-R2 simplified first-level Sidebar."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _text(relative: str) -> str:
    return (QML / relative).read_text()


def test_sidebar_first_level_routes() -> None:
    sidebar_src = _text("shell/Sidebar.qml")
    assert (
        '{ id: "now_playing", label: qsTr("Now Playing"), icon: "play" }' in sidebar_src
    )
    assert '{ id: "library", label: qsTr("Library"), icon: "library" }' in sidebar_src
    assert (
        '{ id: "playlists", label: qsTr("Playlists"), icon: "playlist" }' in sidebar_src
    )
    assert (
        '{ id: "settings", label: qsTr("Settings"), icon: "settings" }' in sidebar_src
    )


def test_sidebar_has_no_deep_tree_or_nested_glass_card() -> None:
    sidebar_src = _text("shell/Sidebar.qml")
    # Tree headings and nested playlist cards removed
    assert '"PINNED"' not in sidebar_src
    assert '"RECENT"' not in sidebar_src
    assert '"New Playlist"' not in sidebar_src
    assert "playlists.pinnedPlaylists" not in sidebar_src
    assert "playlists.recentPlaylists" not in sidebar_src


def test_sidebar_compact_local_indicator() -> None:
    sidebar_src = _text("shell/Sidebar.qml")
    assert "Local · " in sidebar_src
    assert "MichiPalette.auroraGreen" in sidebar_src
