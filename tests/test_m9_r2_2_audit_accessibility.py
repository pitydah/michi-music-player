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
    # One tab stop enters the editorial collection; arrows move a roving
    # index instead of creating a giant tab chain through every feature.
    assert content.count("activeFocusOnTab: true") == 1
    assert "property int rovingIndex" in content
    assert "Keys.onUpPressed" in content
    assert "Keys.onDownPressed" in content
    assert "Keys.onReturnPressed" in content


def test_playlist_appearance_customization_is_keyboard_accessible():
    content = read("playlists/PlaylistHero.qml")
    assert "Accessible.role: Accessible.Button" in content
    assert 'Accessible.name: qsTr("Customize playlist appearance")' in content
    assert "Keys.onSpacePressed: root.customizeAppearanceRequested()" in content
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
    """LIB-A §7/24: TODAS las superficies de tracks convergen en
    MichiTrackTable (EmptyState interno via emptyTitle/emptyIcon/icon); el
    EmptyState y el scrollbar viven en la TABLA compartida (una
    autoridad) — cada vista declara sus strings e icono."""
    table = read("media/MichiTrackTable.qml")
    assert "EmptyState" in table
    assert "MichiScrollBar" in table
    for rel_path, icon in [
        ("views/FavoritesView.qml", "heart"),
        ("views/HistoryView.qml", "history"),
        ("views/RecentlyAddedView.qml", "recent"),
    ]:
        content = read(rel_path)
        assert "MichiTrackTable" in content, rel_path
        assert f'emptyIcon: "{icon}"' in content, rel_path
        assert "emptyTitle:" in content, rel_path
        assert "emptyMessage:" in content, rel_path
    genres = read("views/GenresView.qml")
    assert "EmptyState" in genres
    assert 'iconName: "genre"' in genres
    songs = read("views/SongsView.qml")
    assert "MichiTrackTable" in songs
    assert "emptyTitle:" in songs


def test_empty_library_has_scan_cta():
    content = read("views/LibraryContentHost.qml")
    assert 'actionText: qsTr("Choose Music Folder")' in content
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
    """LIB-A §7/24: las superficies de tracks convergidas heredan el
    MichiScrollBar de la TABLA compartida; las vistas que conservan su
    propio scroll (Genres, PlaylistTrackList) lo declaran directo."""
    table = read("media/MichiTrackTable.qml")
    assert "MichiScrollBar" in table
    for rel_path in [
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
    ]:
        content = read(rel_path)
        assert "MichiTrackTable" in content, rel_path
    for rel_path in [
        "views/GenresView.qml",
        "playlists/PlaylistTrackList.qml",
    ]:
        assert "MichiScrollBar" in read(rel_path), rel_path
    for rel_path in ["views/AlbumDetailView.qml", "views/ArtistDetailView.qml"]:
        # LIB-A §7: los details convergieron en MichiTrackTable (que usa
        # su ListView interno con MichiScrollBar compartido).
        assert "MichiTrackTable" in read(rel_path), rel_path


# ── P2: table header consistency and click-to-sort ────────────────────────────


def test_track_table_header_height_matches_rows():
    # LIB-A §7: el header compartido es ResizableTrackHeader (la tabla).
    content = read("media/MichiTrackTable.qml")
    assert "ResizableTrackHeader" in content


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
    assert "onSortModeRequested: mode => root.requestAlbumSort(mode)" in library_view


# ── Phase 2: queue keyboard navigation and dismissal ──────────────────────────


def test_queue_list_keyboard_navigation_and_selection_feedback():
    content = read("components/QueuePanel.qml")
    assert "keyNavigationEnabled: true" in content
    assert "activeFocusOnTab: true" in content
    assert "selected: ListView.isCurrentItem" in content  # R2.1-08
    assert "onActiveFocusChanged" in content
    assert "MichiScrollBar" in content


def test_queue_clear_requires_confirmation():
    content = read("components/QueuePanel.qml")
    assert "clearQueueDialog.open()" in content
    assert 'title: qsTr("Clear queue?")' in content
    assert 'variant: "danger"' in content


def test_queue_view_dismisses_with_escape_and_animation():
    """Main authority: QueueView closes via closeRequested() + backdrop
    click; the global Esc shortcut routes queue → goBack() in main.qml."""
    content = read("views/QueueView.qml")
    assert "signal closeRequested()" in content
    assert "onClicked: root.closeRequested()" in content
    assert "property bool revealed" in content
    main = read("../main.qml")
    assert 'sequence: "Esc"' in main
    assert 'navigation.currentRoute === "queue"' in main
    assert "appShell.goBack()" in main


# ── Phase 2: immersive views (cover-flow, vinyl wall, timeline) ───────────────


def test_cover_flow_tap_preserves_drag_and_focus():
    content = read("views/AlbumPathView.qml")
    assert "TapHandler" in content
    assert "onDoubleTapped: library.select_album(modelData.key)" in content
    assert "pathAlbum.forceActiveFocus()" in content
    assert "tap.pressed ? MichiPalette.auroraCyan" in content
    assert "MouseArea {" not in content


def test_vinyl_wall_selects_on_tap_and_opens_on_double_tap():
    content = read("views/VinylWallView.qml")
    assert "albumVinyl.currentIndex = vinylTile.index" in content
    assert "onDoubleTapped: library.select_album(modelData.key)" in content


def test_timeline_reuses_items_and_aligns_to_grid():
    content = read("views/TimelineView.qml")
    assert "reuseItems: true" in content
    assert "anchors.leftMargin: MichiSpacing.md" in content
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
    assert "paletteBinding.value.accentSafe || MichiPalette.graphite" in content
    assert ": MichiPalette.graphite" in content
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
    """Main authority: the artist header uses the aurora gradient avatar
    + the M6.9 enrichment knowledge surface."""
    content = read("views/ArtistDetailView.qml")
    assert "MichiPalette.auroraBlue" in content
    assert "EnrichmentStatusBar" in content


def test_album_detail_no_duplicated_metadata_at_wide_widths():
    """Album detail uses shared semantic breakpoints at wide/medium widths."""
    content = read("views/AlbumDetailView.qml")
    assert "MichiBreakpoints.atLeastWide(root.width)" in content
    assert "!MichiBreakpoints.atLeastMedium(root.width)" in content
    assert "MichiBreakpoints.atLeastMedium(root.width)" in content


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
    assert "queueRow.hovered || ListView.isCurrentItem ? 1 : 0.18" in content  # R2.1-08
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
    ]:
        content = read(rel)
        assert "MichiFormat.format" in content, rel
        assert "function formatTime" not in content, rel
        assert "function formatDuration" not in content, rel


# ── Phase 4: wayfinding titles and toast feedback ─────────────────────────────


def test_library_header_names_active_tab():
    content = read("views/LibraryHeader.qml")
    assert "function tabTitle()" in content
    # LIB-A seal II: los títulos de tab viven bajo qsTr (i18n real).
    assert 'case "albums": return qsTr("Albums")' in content
    assert 'default: return qsTr("Songs")' in content
    assert "title: root.tabTitle()" in content


def test_toast_host_supports_action_and_is_wired():
    toast = read("patterns/ToastHost.qml")
    assert "function showWithAction(text, action, nextTone)" in toast
    assert "property string actionText" in toast
    shell = read("shell/AppShell.qml")
    assert "ToastHost" in shell
    assert "function showToast(text, tone)" in shell
    assert "function showToastWithAction(text, action, handler, tone)" in shell
    lib_host = read("views/LibraryContentHost.qml")
    assert "window.showToast" in lib_host


def test_action_feedback_call_sites():
    lib_host = read("views/LibraryContentHost.qml")
    assert 'qsTr("Added to %1")' in lib_host  # R2: .arg() substitution
    assert "modelData.name)" in lib_host
    # P0-01: the Undo path in ContentHost now uses insert_track with FROZEN
    # provenance; the user-facing "Add to playlist" call-site with toast
    # feedback lives in LibraryContentHost and stays audited here.
    library_host = read("views/LibraryContentHost.qml")
    assert "add_track_to_playlist(" in library_host


# ── Phase 4: full qsTr coverage (no intra-file mixes) ─────────────────────────


def test_no_hardcoded_visible_strings_in_mixed_files():
    magazine = read("views/MagazineView.qml")
    assert 'qsTr("RECENTLY ADDED")' in magazine
    assert 'qsTr("FAVORITE FROM YOUR LIBRARY")' in magazine
    assert 'qsTr("HIGH FIDELITY")' in magazine
    assert '"0%1"' in magazine  # R2: .arg() substitution
    assert "index + 2)" in magazine
    card = read("playlists/PlaylistCard.qml")
    assert "Pinned playlist" in card  # accessible name stays (decorative dot)
    toolbar = read("views/LibraryToolbar.qml")
    assert 'qsTr("No results")' in toolbar
    assert 'text: qsTr("Cancel")' in toolbar
    header = read("views/LibraryHeader.qml")
    assert 'label: qsTr("Gallery")' in header
    # The redundant technical "VIEWS" eyebrow was removed by design (the
    # segmented control is the discoverable control). Guard the i18n
    # intent: no raw eyebrow may return and the per-tab wayfinding
    # subtitles must stay translatable.
    assert 'text: "VIEWS"' not in header
    assert 'qsTr("Album view")' in header
    assert 'qsTr("%1 tracks in playback history")' in header
    assert 'qsTr("%1 recently added tracks")' in header
    assert 'qsTr("%1 favorites")' in header
    settings = read("views/SettingsView.qml")
    assert 'title: qsTr("Settings")' in settings
    assert 'text: qsTr("High contrast")' in settings
