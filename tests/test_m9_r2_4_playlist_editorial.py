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
    background = read("playlists/PlaylistHeroBackground.qml")
    assert "PlaylistHeroBackground" in hero
    assert "autoColors" in hero
    assert "MichiSemanticColors.scrim" in background
    assert "MichiPalette.obsidian" in background


def test_hero_typography_and_compact_actions():
    hero = read("playlists/PlaylistHero.qml")
    assert 'qsTr("PLAYLIST")' in hero  # eyebrow
    assert "font.letterSpacing: 1.35" in hero
    assert 'role: "display"' in hero  # dominant title
    assert "font.weight: Font.DemiBold" in hero
    assert "maximumLineCount: 2" in hero  # description cap
    assert "iconOnly: root.width < 920" in hero
    assert "implicitHeight: MichiMetrics.controlMedium" in hero  # Play 36px
    assert "pinned" in hero  # pin toggle kept in hero


def test_hero_cover_is_square_with_faint_shadow():
    hero = read("playlists/PlaylistHero.qml")
    assert "readonly property real coverSize:" in hero
    assert "width >= 1120 ? 180" in hero
    assert "width >= 820 ? 172 : width >= 620 ? 156 : 144" in hero
    assert "Layout.preferredWidth: root.coverSize" in hero
    assert "Layout.preferredHeight: root.coverSize" in hero
    assert "radius: MichiRadius.lg" in hero
    assert "glassShadow" in hero
    assert "opacity: 0.46" in hero
    assert "glassShadowNear" in hero


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
    # M4-R1 authority: single-click row activation emits play (the
    # double-click model of the pre-M4-R1 branch was replaced).
    assert "onDoubleClicked" not in table
    assert "root.playTrackRequested(index)" in table
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
    # M4-R1 authority: the row play intent routes DIRECTLY to the
    # PlaylistsBridge (play_playlist_track) — never a bare re-emit.
    assert "onPlayTrackRequested: index => playlists.play_playlist_track(index)" in page
    assert "onShuffleRequested: root.shuffleRequested()" in page  # R2.1-07 inline
    host = read("shell/ContentHost.qml")
    assert "playlists.play_track(index)" in host
    assert "onShuffleRequested" in host
    assert "onAddMusicRequested: libraryTrackPicker.begin()" in host


def test_hero_self_sizes_and_page_never_collapses_it():
    hero = read("playlists/PlaylistHero.qml")
    # the hero computes its own editorial height from its host view; a
    # page-side `implicitHeight: root.heroHeight` binding would resolve
    # `root` to the hero (component scope wins in property bindings) and
    # collapse the ListView header to zero — regression guard.
    assert "implicitHeight: Math.max(248, Math.min(300," in hero
    assert "(parent ? parent.height : 760) * 0.36))" in hero
    page = read("playlists/PlaylistDetailView.qml")
    # the hero is instantiated inside a Component (ListView.header requires
    # QQmlComponent) with null-safe bridge bindings that re-evaluate on
    # playlists_changed — regression guard for the collapsed header
    assert "heroComponent: heroComponent" in page
    assert 'objectName: "playlistHeroHeader"' in page
    assert "width: root.width" in page
    assert "height: root.heroHeight" in page
    assert 'playlistName: playlists ? playlists.selectedPlaylistName : ""' in page


# ── M9-R2.5 spec-compliance lot (M1-M6) ───────────────────────────────────────


def test_micro_type_role_exists_for_10px_labels():
    typography = read("theme/MichiTypography.qml")
    assert "readonly property int micro: 10" in typography
    text = read("primitives/MichiText.qml")
    assert 'role === "micro" ? MichiTypography.micro' in text
    assert 'role === "micro" ? 0.35 : 0' in text  # uppercase tracking


def test_hero_type_scale_matches_spec():
    hero = read("playlists/PlaylistHero.qml")
    # eyebrow 10-11px (caption), metadata 11-12px (technical)
    assert 'role: "micro"' in hero
    assert "font.letterSpacing: 1.35" in hero
    assert 'role: "technical"' in hero
    assert "opacity: 0.78" in hero


def test_row_metadata_uses_technical_scale():
    table = read("playlists/PlaylistTrackList.qml")
    # artist/album at 12px technical (spec 11-12), title stays body 14
    assert 'role: "technical"' in table
    assert 'role: "body"' in table


def test_column_header_always_visible_backplane_fades():
    header = read("playlists/PlaylistColumnHeader.qml")
    assert 'role: "micro"' in header
    assert "opacity: 0.4" in header
    page = read("playlists/PlaylistDetailView.qml")
    # the column header lives in-flow below the hero (scrolls away) and
    # the sticky overlay fades in with its backplane while the hero leaves
    assert "PlaylistColumnHeader {" in page
    assert "opacity: root.stickyHeaderOpacity" in page
    assert "showArtist: width >= 700" in page


def test_format_column_beyond_1200():
    page = read("playlists/PlaylistDetailView.qml")
    table = read("playlists/PlaylistTrackList.qml")
    assert "readonly property bool showFormat: root.width > 1200" in page
    assert "showFormatColumn: root.width > 1200" in page
    assert "property bool showFormatColumn: false" in table
    assert "modelData.formatLabel" in table
    assert "MichiFormatBadge" in table


def test_add_tracks_action_in_hero():
    hero = read("playlists/PlaylistHero.qml")
    page = read("playlists/PlaylistDetailView.qml")
    assert 'qsTr("Add tracks")' in hero
    assert "onAddTracksRequested: root.addMusicRequested()" in page  # R2.1-07 inline


def test_row_favorite_and_pressed_state():
    table = read("playlists/PlaylistTrackList.qml")
    assert 'iconName: "heart"' in table
    assert "library.favoritePaths.indexOf(modelData.path) !== -1" in table
    assert "library.toggle_favorite(modelData.path)" in table
    assert "trackItem.pressed ? MichiSemanticColors.surfacePressed" in table
    # more hit target 32px (spec 32-36)
    assert "Layout.preferredWidth: 32" in table


def test_hero_fades_in_on_open():
    hero = read("playlists/PlaylistHero.qml")
    assert "opacity: 0" in hero
    assert "Behavior on opacity" in hero
    assert "Component.onCompleted: opacity = 1" in hero


# ── Audit pass (qt-ui-design checklist) ───────────────────────────────────────


def test_keyboard_navigation_updates_visible_selection():
    table = read("playlists/PlaylistTrackList.qml")
    # arrow-key navigation moves currentIndex invisibly unless the focused
    # row also becomes the selected row — audit fix
    assert "onActiveFocusChanged: {" in table
    assert "root.trackSelected(index)" in table
    # both keyboard paths (row keys + list keys) reproduce from the index
    assert "Keys.onReturnPressed: root.playTrackRequested(index)" in table
    assert "root.playTrackRequested(currentIndex)" in table


# ── Audit debt block (W1, W5, O2) ─────────────────────────────────────────────


def test_michi_format_is_locale_aware():
    fmt = read("theme/MichiFormat.qml")
    assert "Qt.locale().toString(n)" in fmt
    assert 'qsTr("hr")' in fmt
    assert 'qsTr("min")' in fmt
    assert 'qsTr("Unknown")' in fmt
    # R2: zero-padding is NUMERIC (_pad2) — a string fed to
    # Qt.locale().toString would raise "Could not convert argument 0 from
    # 01 to QDateTime"
    assert "_pad2(minutes)" in fmt
    assert "_pad2(seconds)" in fmt


def test_reorder_keeps_keyboard_cursor_on_moved_row():
    table = read("playlists/PlaylistTrackList.qml")
    assert "root.trackSelected(index - 1)" in table
    assert "trackList.currentIndex = index - 1" in table
    assert "trackList.currentItem.forceActiveFocus()" in table
    assert "root.trackSelected(index + 1)" in table


def test_add_tracks_becomes_icon_only_on_narrow_windows():
    hero = read("playlists/PlaylistHero.qml")
    assert 'text: root.width >= 920 ? qsTr("Add tracks") : ""' in hero
    assert "iconOnly: root.width < 920" in hero
    assert "parent.width <" not in hero


# ── Pending-feature block (drag reorder, queue undo, queue row action) ───────


def test_drag_reorder_handle_and_drop_line():
    table = read("playlists/PlaylistTrackList.qml")
    assert "Drag.active: dragHandler.active" in table
    assert '"application/x-michi-playlist-index": index' in table
    assert "DragHandler {" in table
    assert "DropArea {" in table
    assert "trackList.indexAt(drag.x, drag.y)" in table
    assert "insertLine.visible = false" in table
    assert "root.moveTrackRequested(from, to)" in table


def test_row_menu_adds_to_queue():
    table = read("playlists/PlaylistTrackList.qml")
    menu = read("media/TrackContextMenu.qml")
    assert 'qsTr("Add to Queue")' in menu
    assert "library.queue_track(modelData.trackId)" in table


def test_queue_remove_offers_undo_and_detail_menu_adds_tracks():
    # M4-R1 authority: QueueView routes navigation to the Session, not Queue.
    queue = read("views/QueueView.qml")
    assert "playbackSession.previous_track()" in queue
    assert "playbackSession.next_track()" in queue
    assert "queue.play_index" not in queue
    page = read("playlists/PlaylistDetailView.qml")
    assert 'qsTr("Add tracks…")' in page
    assert "onTriggered: root.addMusicRequested()" in page


# ── Sidebar + NowPlayingBar audit block ───────────────────────────────────────


def test_sidebar_dead_signal_removed_and_active_state_announced():
    sidebar = read("shell/Sidebar.qml")
    assert "signal createPlaylistRequested" not in sidebar
    assert "Accessible.checked: routeItem._active" in sidebar
    assert "MichiTooltip {" in sidebar  # compact mode labels
    shell = read("shell/AppShell.qml")
    # sidebar wiring removed; ContentHost's own create signal kept
    assert shell.count("onCreatePlaylistRequested") == 1


def test_now_playing_bar_repeat_has_non_chromatic_state():
    bar = read("player/NowPlayingBar.qml")
    assert 'opacity: root.repeatMode === "NONE" ? 0.45 : 1' in bar
    assert 'qsTr("Repeat: %1")' in bar  # R2: .arg() substitution
    assert "root.repeatMode.toLowerCase())" in bar
    # the album line is readable secondary text now, not caption-muted
    assert '"Unknown album")' in bar
    assert 'role: "secondary"' in bar
    assert "opacity: 0.7" in bar


def test_now_playing_bar_accessibles_are_translated():
    bar = read("player/NowPlayingBar.qml")
    for string in [
        "Playback position",
        "Previous track",
        "Next track",
        "Volume",
        "Audio settings",
        "Output selection unavailable",
    ]:
        assert f'qsTr("{string}")' in bar, string
    assert 'qsTr("%1 percent")' in bar  # R2: .arg() substitution
    assert "Math.round(value))" in bar
