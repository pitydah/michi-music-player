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
    muted = next(
        line.split('"')[1] for line in palette.splitlines() if "textMuted:" in line
    )
    assert muted == "#8A90A0"
    for surface in ("#090B11", "#14171C", "#1F232A"):
        assert _contrast_ratio(muted, surface) >= 4.5, (
            f"textMuted {muted} on {surface} must be >= 4.5:1"
        )


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
