"""Structural tests for the M9-R2.4 editorial playlist page redesign.

Covers: atmospheric hero (gradient tokens, eyebrow, compact actions),
dense track table (row states, keyboard nav, reuse, playing indicator),
sticky column header, responsive columns, empty state and the
play-from-track bridge contract (no queue coupling in the UI).
"""

from pathlib import Path

QML_ROOT = Path("src/michi/presentation/qml")


def read(rel_path: str) -> str:
    return Path(QML_ROOT, rel_path).read_text(encoding="utf-8")


# ── PlaylistHero ──────────────────────────────────────────────────────────────


def test_hero_uses_low_saturation_atmosphere_tokens():
    palette = read("theme/MichiPalette.qml")
    assert 'playlistHeroTop: "#152A45"' in palette
    assert 'playlistHeroMid: "#13243D"' in palette
    assert 'playlistHeroBottom: "#0A0D14"' in palette
    hero = read("playlists/PlaylistHero.qml")
    assert "MichiPalette.playlistHeroTop" in hero
    assert "MichiPalette.playlistHeroBottom" in hero


def test_hero_typography_and_compact_actions():
    hero = read("playlists/PlaylistHero.qml")
    assert 'qsTr("PLAYLIST")' in hero  # eyebrow
    assert "font.letterSpacing: 1.4" in hero
    assert 'role: "display"' in hero  # dominant title
    assert "font.weight: Font.DemiBold" in hero
    assert "maximumLineCount: 2" in hero  # description cap
    assert "implicitWidth: 28" in hero  # compact secondary actions
    assert "implicitHeight: MichiMetrics.controlMedium" in hero  # Play 36px
    assert "pinned" in hero  # pin toggle kept in hero


def test_hero_cover_is_square_with_faint_shadow():
    hero = read("playlists/PlaylistHero.qml")
    assert "Layout.preferredWidth: 136" in hero
    assert "Layout.preferredHeight: 136" in hero
    assert "radius: 10" in hero
    assert "glassShadowFar" in hero
    assert "opacity: 0.55" in hero


# ── PlaylistTrackList (dense table) ───────────────────────────────────────────


def test_track_rows_are_quiet_and_stateful():
    table = read("playlists/PlaylistTrackList.qml")
    colors = read("theme/MichiSemanticColors.qml")
    assert "rowHover: Qt.rgba(1, 1, 1, 0.035)" in colors
    assert "rowSelected: Qt.rgba(1, 1, 1, 0.06)" in colors
    assert "rowDivider: Qt.rgba(1, 1, 1, 0.05)" in colors
    assert "MichiSemanticColors.rowSelected" in table
    assert "MichiSemanticColors.rowHover" in table
    assert "MichiSemanticColors.rowDivider" in table
    assert "height: 50" in table  # compact 48-52px rows
    assert "radius: 5" in table  # discrete hover radius
    assert "reuseItems: true" in table
    assert "keyNavigationEnabled: true" in table


def test_playing_state_is_distinct_from_selected():
    table = read("playlists/PlaylistTrackList.qml")
    assert "playback.currentPath === modelData.path" in table
    assert "MichiPlayingIndicator" in table
    assert "MichiPalette.auroraCyan" in table  # accent on the title
    assert "root.selectedIndex === index" in table


def test_rows_activate_play_and_hide_actions_until_hover():
    table = read("playlists/PlaylistTrackList.qml")
    assert "onDoubleClicked: root.playTrackRequested(index)" in table
    assert "Keys.onReturnPressed: root.playTrackRequested(index)" in table
    assert "opacity: trackItem.hovered || trackItem.visualFocus ? 1 : 0" in table
    assert "enabled: !MichiAccessibility.reducedMotion" in table  # gated fade


# ── PlaylistDetailView (page composition) ─────────────────────────────────────


def test_page_has_sticky_column_header_and_responsive_columns():
    page = read("playlists/PlaylistDetailView.qml")
    assert "stickyHeaderOpacity" in page
    assert "trackList.contentY" in page
    assert "readonly property bool showArtist: root.width >= 700" in page
    assert "readonly property bool showAlbum: root.width >= 900" in page
    assert "showArtistColumn: root.width >= 700" in page
    assert "showAlbumColumn: root.width >= 900" in page
    assert "narrow: root.width < 700" in page


def test_page_keeps_hero_and_integrates_empty_state():
    page = read("playlists/PlaylistDetailView.qml")
    assert "PlaylistHero" in page
    assert "visible: playlists.playlistTrackRows.length === 0" in page
    assert 'qsTr("This playlist is empty")' in page
    assert 'qsTr("Add Music")' in page
    assert "root.addMusicRequested()" in page
    # the old glass-card hero is gone
    assert "MichiGlassSurface" not in page
    # legacy flat header title gone
    assert 'text: qsTr("PLAYLIST")' not in page


def test_page_connects_play_track_and_shuffle():
    page = read("playlists/PlaylistDetailView.qml")
    assert "onPlayTrackRequested: index => root.playTrackRequested(index)" in page
    assert "onShuffleRequested: root.shuffleRequested()" in page
    host = read("shell/ContentHost.qml")
    assert "playlists.play_track(index)" in host
    assert "onShuffleRequested" in host
    assert 'navigation.navigate("library")' in host


def test_hero_self_sizes_and_page_never_collapses_it():
    hero = read("playlists/PlaylistHero.qml")
    # the hero computes its own editorial height from its host view; a
    # page-side `implicitHeight: root.heroHeight` binding would resolve
    # `root` to the hero (component scope wins in property bindings) and
    # collapse the ListView header to zero — regression guard.
    assert "implicitHeight: Math.max(240, Math.min(300," in hero
    assert "(parent ? parent.height : 600) * 0.36)" in hero
    page = read("playlists/PlaylistDetailView.qml")
    assert "implicitHeight: root.heroHeight" not in page
    assert (
        "implicitHeight:"
        not in page.split("heroHeader: PlaylistHero {")[1].split("playlistName:")[0]
    )
