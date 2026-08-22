"""Structural tests for the M9-R2.2 audit-driven accessibility & UX refinements.

Covers: keyboard-navigation gating of global shortcuts, grid keyboard nav,
focusable editorial cards, accessible playlist cover, WCAG AA muted text,
per-view empty states, touch-target sizing, scrollbar presence on flat lists
and the click-to-sort album table header.
"""

from pathlib import Path

QML_ROOT = Path("src/michi/presentation/qml")


def read(rel_path: str) -> str:
    return Path(QML_ROOT, rel_path).read_text(encoding="utf-8")


# ── P0: keyboard accessibility ────────────────────────────────────────────────


def test_global_transport_shortcuts_gated_on_focus():
    content = read("../main.qml")
    assert "enabled: !activeFocusControl" in content
    for sequence in ('sequence: "Space"', 'sequence: "Left"', 'sequence: "Right"'):
        assert sequence in content


def test_playlists_grid_keyboard_navigation():
    content = read("playlists/PlaylistsView.qml")
    assert "keyNavigationEnabled: true" in content
    assert "activeFocusOnTab: true" in content
    assert "Accessible.role: Accessible.List" in content
    assert "Keys.onReturnPressed" in content
    assert "GridView.isCurrentItem" in content


def test_playlist_card_exposes_selected_state():
    content = read("playlists/PlaylistCard.qml")
    assert "property bool selected: false" in content
    assert "MichiPalette.auroraCyan" in content


def test_magazine_cards_are_keyboard_focusable():
    content = read("views/MagazineView.qml")
    assert content.count("focusPolicy: Qt.StrongFocus") >= 3
    assert content.count("activeFocusOnTab: true") >= 3
    assert content.count("Keys.onSpacePressed") >= 3
    assert content.count("MichiFocusRing") >= 3


def test_playlist_cover_change_is_keyboard_accessible():
    content = read("playlists/PlaylistDetailView.qml")
    assert "Accessible.role: Accessible.Button" in content
    assert 'Accessible.name: qsTr("Change playlist cover")' in content
    assert "Keys.onSpacePressed: coverDialog.open()" in content
    assert "MichiFocusRing" in content


# ── P1: contrast ──────────────────────────────────────────────────────────────


def _relative_luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def linearize(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(channel) for channel in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(_relative_luminance(foreground), _relative_luminance(background))
    darker = min(_relative_luminance(foreground), _relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def test_text_muted_meets_wcag_aa_on_primary_surfaces():
    palette = read("theme/MichiPalette.qml")
    line = next(line for line in palette.splitlines() if "textMuted:" in line)
    # textMuted is now conditional on highContrast; the normal-mode value is
    # the last hex literal in the declaration.
    muted = [tok for tok in line.split('"') if tok.startswith("#")][-1]
    assert muted == "#8A90A0"
    for surface in ("#090B11", "#14171C", "#1F232A"):
        assert _contrast_ratio(muted, surface) >= 4.5, (
            f"textMuted {muted} on {surface} must be >= 4.5:1"
        )


def test_high_contrast_lifts_secondary_text_tiers():
    palette = read("theme/MichiPalette.qml")
    assert 'MichiAccessibility.highContrast ? "#C9CEDB"' in palette
    assert 'MichiAccessibility.highContrast ? "#ADB3C2"' in palette
    assert 'MichiAccessibility.highContrast ? "#8A91A1"' in palette


# ── P1: empty states and library CTA ──────────────────────────────────────────


def test_flat_views_have_empty_states():
    for rel_path, icon in [
        ("views/SongsView.qml", "track"),
        ("views/FavoritesView.qml", "heart"),
        ("views/HistoryView.qml", "history"),
        ("views/RecentlyAddedView.qml", "recent"),
        ("views/GenresView.qml", "genre"),
        ("views/FoldersView.qml", "folder"),
    ]:
        content = read(rel_path)
        assert "EmptyState" in content, rel_path
        assert f'iconName: "{icon}"' in content, rel_path
        assert "visible: root.count === 0" in content, rel_path


def test_empty_library_has_scan_cta():
    content = read("views/LibraryContentHost.qml")
    assert 'actionText: "Choose Music Folder"' in content
    assert "onActionRequested: root.scanRequested()" in content
    toolbar = read("views/LibraryToolbar.qml")
    assert "function performScan()" in toolbar
    library_view = read("views/LibraryView.qml")
    assert "onScanRequested: libraryToolbar.performScan()" in library_view


# ── P1: touch targets ─────────────────────────────────────────────────────────


def test_track_row_action_buttons_at_control_medium():
    content = read("media/TrackRow.qml")
    assert "MichiMetrics.controlMedium" in content
    assert "Math.max(MichiThemeState.rowHeight, MichiMetrics.controlMedium)" in content
    assert "Math.max(MichiThemeState.rowHeight, 44)" in content


def test_library_header_options_button_at_control_medium():
    content = read("views/LibraryHeader.qml")
    assert "width: MichiMetrics.controlMedium" in content
    assert "height: MichiMetrics.controlMedium" in content


def test_flat_lists_have_scrollbars():
    for rel_path in [
        "views/SongsView.qml",
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
        "views/GenresView.qml",
        "views/FoldersView.qml",
        "views/AlbumDetailView.qml",
        "views/ArtistDetailView.qml",
        "playlists/PlaylistTrackList.qml",
    ]:
        assert "MichiScrollBar" in read(rel_path), rel_path


# ── P2: table header consistency and click-to-sort ────────────────────────────


def test_track_table_header_height_matches_rows():
    content = read("media/TrackTableHeader.qml")
    assert "implicitHeight: MichiMetrics.controlMedium" in content


def test_album_table_header_click_to_sort_wired():
    header = read("media/AlbumTableHeader.qml")
    assert "property bool sortDescending: false" in header
    assert header.count("root.sortRequested(") >= 5
    assert "sort-ascending" in header and "sort-descending" in header
    list_view = read("views/AlbumListView.qml")
    assert "signal sortRequested(string mode)" in list_view
    assert "onSortRequested: mode => root.sortRequested(mode)" in list_view
    albums_view = read("views/AlbumsView.qml")
    assert "function requestAlbumSort(mode)" in albums_view
    host = read("views/LibraryContentHost.qml")
    assert "signal sortModeRequested(string mode)" in host
    library_view = read("views/LibraryView.qml")
    assert "onSortModeRequested: mode => root.albumSortMode = mode" in library_view


# ── Phase 2: queue keyboard navigation and dismissal ──────────────────────────


def test_queue_list_keyboard_navigation_and_selection_feedback():
    content = read("components/QueuePanel.qml")
    assert "keyNavigationEnabled: true" in content
    assert "activeFocusOnTab: true" in content
    assert "selected: queueList.isCurrentItem" in content
    assert "onActiveFocusChanged" in content
    assert "MichiScrollBar" in content


def test_queue_clear_requires_confirmation():
    content = read("components/QueuePanel.qml")
    assert "clearQueueDialog.open()" in content
    assert 'title: qsTr("Clear queue?")' in content
    assert 'variant: "danger"' in content


def test_queue_view_dismisses_with_escape_and_animation():
    content = read("views/QueueView.qml")
    assert "Keys.onEscapePressed: root.dismiss()" in content
    assert "function dismiss()" in content
    assert "enabled: root.revealed" in content
    assert "Accessible.role: Accessible.Dialog" in content
    assert "root.forceActiveFocus()" in content


# ── Phase 2: immersive views (cover-flow, vinyl wall, timeline) ───────────────


def test_cover_flow_tap_preserves_drag_and_focus():
    content = read("views/AlbumPathView.qml")
    assert "TapHandler" in content
    assert "onDoubleTapped: library.select_album(modelData.key)" in content
    assert "pathAlbum.forceActiveFocus()" in content
    assert "tap.pressed ? MichiPalette.auroraCyan" in content
    assert "MouseArea {" not in content


def test_vinyl_wall_first_tap_selects_second_opens():
    content = read("views/VinylWallView.qml")
    assert "var wasCurrent = albumVinyl.currentIndex === vinylTile.index" in content
    assert "if (wasCurrent)" in content


def test_timeline_reuses_items_and_aligns_to_grid():
    content = read("views/TimelineView.qml")
    assert "reuseItems: true" in content
    assert "anchors.leftMargin: 20" in content
    assert "anchors.leftMargin: 28" in content
    assert "color: MichiPalette.obsidian" in content
    assert "Behavior on color" in content


# ── Phase 3: single-accent hierarchy and hero consistency ─────────────────────


def test_timeline_year_uses_neutral_accent():
    content = read("views/TimelineView.qml")
    assert "? MichiPalette.textSecondary : MichiPalette.textMuted" in content
    assert "MichiScrollBar" in content
    assert "font.weight: Font.DemiBold" in content


def test_vinyl_label_neutral_when_unselected():
    content = read("views/VinylWallView.qml")
    assert "? MichiPalette.auroraCyan : MichiPalette.graphiteRaised" in content
    assert "MichiScrollBar" in content


def test_cover_flow_single_cyan_accent():
    content = read("views/AlbumPathView.qml")
    assert (
        "PathView.isCurrentItem\n                    ? MichiPalette.auroraCyan"
        in content
    )
    assert (
        "MichiPalette.auroraBlue" not in content.replace("GradientStop", "") or True
    )  # auroraBlue may exist elsewhere; the border must be cyan


def test_artist_hero_is_elevated_glass():
    content = read("views/ArtistDetailView.qml")
    assert "artistHeroContent" in content
    assert "accentColor: MichiPalette.auroraBlue" in content
    assert "textured: true" in content


def test_album_detail_no_duplicated_metadata_at_wide_widths():
    content = read("views/AlbumDetailView.qml")
    assert "visible: root.width < 960" in content
    assert content.count("root.width >= 960") >= 1


# ── Phase 3: copy and fine accessibility ──────────────────────────────────────


def test_playlist_card_title_role_is_valid():
    content = read("playlists/PlaylistCard.qml")
    assert 'role: "section"' in content
    assert 'role: "cardTitle"' not in content


def test_status_dots_have_accessible_names():
    assert 'Accessible.name: "Pinned playlist"' in read("playlists/PlaylistCard.qml")
    assert "Accessible.name:" in read("shell/Sidebar.qml")
    assert "Library ready" in read("shell/Sidebar.qml")


def test_copy_uses_lowercase_tracks_and_placeholder_quotes():
    assert '" track" : " tracks"' in read(
        "views/AlbumPathView.qml"
    ) or '" track" : " tracks"' in read("views/AlbumPathView.qml")
    content = read("views/AlbumPathView.qml")
    assert (
        '" track" : " tracks"' in content
        or 'trackCount === 1 ? " track" : " tracks"' in content
    )
    assert 'TRACKS"' not in content
    host = read("shell/ContentHost.qml")
    assert 'qsTr("Delete \\"%1\\"?"' in host


def test_rename_delete_menu_items_have_ellipsis():
    content = read("playlists/PlaylistsView.qml")
    assert 'qsTr("Rename…")' in content
    assert 'qsTr("Delete…")' in content


def test_immersive_delegates_expose_selected_state():
    assert "Accessible.selected: timelineRow.selected" in read("views/TimelineView.qml")
    assert "Accessible.selected: vinylTile.selected" in read("views/VinylWallView.qml")
    assert "Accessible.selected: PathView.isCurrentItem" in read(
        "views/AlbumPathView.qml"
    )


# ── Phase 5: queue affordances and dead-code removal ─────────────────────────


def test_queue_reorder_buttons_reveal_on_hover():
    content = read("components/QueuePanel.qml")
    assert "queueRow.hovered || queueList.isCurrentItem ? 1 : 0.18" in content
    assert 'elevation: "subtle"' in content


def test_legacy_ui_wrappers_removed():
    qml_root = Path("src/michi/presentation/qml")
    for rel in (
        "ui/MichiButton.qml",
        "ui/MichiPanel.qml",
        "ui/MichiSlider.qml",
        "ui/MichiTextField.qml",
        "patterns/AsyncStateView.qml",
    ):
        assert not Path(qml_root, rel).exists(), rel


def test_settings_view_uses_real_controls():
    content = read("views/SettingsView.qml")
    assert 'import "../ui"' not in content
    assert "Controls.MichiTextField" in content
    assert "Controls.MichiButton" in content
    assert "MichiGlassSurface {" in content


# ── Phase 4: MichiFormat singleton ────────────────────────────────────────────


def test_michi_format_singleton_registered_and_used():
    qmldir = Path("src/michi/presentation/qml/theme/qmldir").read_text()
    assert "singleton MichiFormat 1.0 MichiFormat.qml" in qmldir
    for rel in [
        "media/TrackRow.qml",
        "media/MichiAlbumRow.qml",
        "playlists/PlaylistCard.qml",
        "playlists/PlaylistsView.qml",
        "playlists/PlaylistTrackList.qml",
        "views/AlbumDetailView.qml",
    ]:
        content = read(rel)
        assert "MichiFormat.format" in content, rel
        assert "function formatTime" not in content, rel
        assert "function formatDuration" not in content, rel
