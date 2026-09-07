"""Regression gates for the real-app Library visible recovery pass."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "src" / "michi" / "presentation" / "qml"


def _read(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_genres_never_hide_rows_behind_full_height_header() -> None:
    source = _read("views/GenresView.qml")
    assert 'Item {\n    id: root\n    objectName: "genresView"' in source
    assert "header: EmptyState" not in source
    assert "visible: genreList.count === 0" in source
    assert "visible: count > 0" in source
    assert "library.select_genre(modelData.key)" in source


def test_historical_per_tab_wayfinding_is_restored_without_views_eyebrow() -> None:
    source = _read("views/LibraryHeader.qml")
    assert 'qsTr("%1 favorites")' in source
    assert 'qsTr("%1 tracks in playback history")' in source
    assert 'qsTr("%1 recently added tracks")' in source
    assert 'qsTr("%1 artists")' in source
    assert 'qsTr("%1 genres")' in source
    assert 'text: qsTr("VIEWS")' not in source


def test_library_tabs_expose_overflow_instead_of_silent_clipping() -> None:
    source = _read("views/LibraryTabs.qml")
    assert "readonly property bool overflowed" in source
    assert 'objectName: "libraryTabsScrollLeft"' in source
    assert 'objectName: "libraryTabsScrollRight"' in source
    assert 'qsTr("Show previous library tabs")' in source
    assert 'qsTr("Show more library tabs")' in source


def test_track_table_customization_has_visible_affordance() -> None:
    source = _read("media/ResizableTrackHeader.qml")
    assert 'objectName: "trackTableOptionsButton"' in source
    assert 'accessibleName: qsTr("Table options")' in source
    assert "onClicked: root.openGlobalContext()" in source
    assert "acceptedButtons: Qt.RightButton" in source


def test_column_resize_feedback_is_local_and_truthful() -> None:
    source = _read("media/ResizableHeaderCell.qml")
    assert "ToolTip.visible: pressed" in source
    assert 'qsTr("%1 · %2 px")' in source
    assert "height: 14" in source
    assert (
        "opacity: resizeArea.containsMouse || resizeArea.pressed ? 1 : 0.34" in source
    )


def test_track_actions_are_discoverable_without_becoming_visual_noise() -> None:
    source = _read("media/TrackRow.qml")
    assert "readonly property real idleActionOpacity: 0.34" in source
    assert "? 1 : 0.18" not in source
    assert source.count("root.idleActionOpacity") >= 7


def test_r11_shell_layout_frozen() -> None:
    """R11-SHELL-01 (§21.5): LibraryHeader sobre LibraryToolbar sobre
    LibraryContentHost — las posiciones son intencionales y se congelan."""
    library = _read("views/LibraryView.qml")
    assert library.index("LibraryHeader {") < library.index("LibraryToolbar {")
    assert library.index("LibraryToolbar {") < library.index("LibraryContentHost {")
    # Sin zonas de navegación/estado nuevas que reorganicen el shell.
    assert "LibraryStateStrip" not in library
    assert "LibraryAlbumViewTools" not in library


def test_r11_scrollbar_navigation_matrix() -> None:
    """R11 NAV-11: surfaces continuas con MichiScrollBar; Artists sin raw
    ScrollBar; tabla con barras nombradas + Home/End; AlbumFlow discreto
    con indicador de posición."""
    artists = _read("views/ArtistsView.qml")
    assert "MichiScrollBar" in artists
    assert "artistsNavigationScrollBar" in artists
    assert "ScrollBar: ScrollBar" not in artists
    detail = _read("views/ArtistDetailView.qml")
    assert "artistAlbumsNavigationScrollBar" in detail
    table = _read("media/MichiTrackTable.qml")
    assert "trackTableVerticalScrollBar" in table
    assert "trackTableHorizontalScrollBar" in table
    assert "Qt.Key_Home" in table and "Qt.Key_End" in table
    path = _read("views/AlbumPathView.qml")
    assert "ScrollBar" not in path, "AlbumFlow discreto: sin scrollbar"
    assert 'qsTr("%1 / %2")' in path
    scrollbar = _read("controls/MichiScrollBar.qml")
    assert "minimumSize: 0.04" in scrollbar
    assert "implicitWidth: root.vertical ? 12 : 48" in scrollbar


def test_r11_track_hierarchy_visual_contract() -> None:
    """HIER-04..08: tres estados visuales; título Medium; badge quiet;
    numéricas a la derecha; sin doble separación."""
    row = _read("media/TrackRow.qml")
    assert "auroraCyanSurface" in row, "playing con superficie propia"
    assert "Font.DemiBold : Font.Medium" in row, "título Medium default"
    assert "compactQuiet: true" in row
    assert "horizontalAlignment: Text.AlignRight" in row
    badge = _read("media/MichiFormatBadge.qml")
    assert "property bool compactQuiet: false" in badge
    table = _read("media/MichiTrackTable.qml")
    assert "spacing: 0" in table


def test_artist_detail_never_uses_album_sleeve_as_portrait() -> None:
    """R12 (§33): ArtistDetail converged — enriched portrait wins; the
    fallback is the deliberate monogram, never an album sleeve cropped
    into a circular portrait."""
    source = _read("views/ArtistDetailView.qml")
    assert "artistAlbums[0].artworkPath" not in source, (
        "la portada de un álbum no puede ser el retrato del artista"
    )
    assert "enrichment.artistArtworkPath.length > 0" in source
    assert "fallbackText: library.artistName" in source


def test_collections_share_one_table_with_semantic_configuration() -> None:
    """R13 (§45): las colecciones usan la ÚNICA MichiTrackTable con
    configuración semántica por vista (sin duplicar la tabla)."""
    for view in ("FavoritesView", "HistoryView", "RecentlyAddedView"):
        source = _read(f"views/{view}.qml")
        assert "MichiTrackTable {" in source, view
        assert "rows: library." in source, view
        # empty states semánticos por colección (no un genérico de Songs).
        assert (
            "No matching" in source
            or "No favorites yet" in source
            or "Nothing added recently" in source
            or "history" in source
        ), view
    # Ninguna vista de colección construye un ListView propio para tracks.
    for view in ("FavoritesView", "HistoryView", "RecentlyAddedView"):
        source = _read(f"views/{view}.qml")
        assert "ListView {" not in source, f"{view} duplica la tabla"


def test_r10_menu_primitives_have_geometry_authority() -> None:
    """R10 (V4 §9/§16): primitivos con geometría determinista; el wrapper
    con subMenu escribible (MichiSubMenuItem) está AUSENTE."""
    qml = Path("src/michi/presentation/qml")
    assert not (qml / "controls" / "MichiSubMenuItem.qml").exists(), (
        "el wrapper con writable subMenu fue eliminado (V4 §9.5)"
    )
    menu = (qml / "controls" / "MichiMenu.qml").read_text(
        encoding="utf-8", errors="ignore"
    )
    item = (qml / "controls" / "MichiMenuItem.qml").read_text(
        encoding="utf-8", errors="ignore"
    )
    header = (qml / "controls" / "MichiMenuHeader.qml").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "minimumMenuWidth" in menu
    assert "implicitWidth:" in item
    assert "implicitHeight:" in header
    assert 'property: "y"' not in menu, (
        "la animación no puede mutar el posicionamiento del popup"
    )
    assert "minimumMenuWidth" in menu and "maximumMenuWidth" in menu
    # MichiMenuInfoHeader: la cabecera de información menu-aware.
    assert (qml / "media" / "MichiMenuInfoHeader.qml").exists()


def test_r10_productive_menus_use_michi_primitives() -> None:
    """R10 (§11/§13): los menús productivos usan los primitivos Michi;
    sin raw MenuItem fuera de los primitivos; género con MichiMenuItem."""
    qml = Path("src/michi/presentation/qml")

    for rel in (
        "media/TrackContextMenu.qml",
        "media/AlbumContextMenu.qml",
        "media/ArtistContextMenu.qml",
    ):
        src = (qml / rel).read_text(encoding="utf-8", errors="ignore")
        assert "MichiMenuInfoHeader {" in src, rel
        assert "MichiMenuHeader {" in src, rel
    genre = (qml / "media" / "GenreContextMenu.qml").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "MichiMenuItem {" in genre
    assert "MenuItem {" not in genre.replace("MichiMenuItem {", "")
    # El header de la tabla usa headers de sección reales.
    menu = (qml / "media" / "TrackTableHeaderContextMenu.qml").read_text(
        encoding="utf-8", errors="ignore"
    )
    for section in (
        "TRACK TABLE",
        "IDENTITY",
        "MUSICAL CONTEXT",
        "AUDIO",
        "METADATA",
        "TIME",
        "UTILITY",
    ):
        assert f'qsTr("{section}")' in menu, section
    assert "MichiMenuHeader {" in menu
    # R10.2: submenús nativos reales (Qt crea el proxy con subMenu
    # read-only); el customizePopup hermano desapareció.
    assert 'title: qsTr("Preset")' in menu
    assert 'title: qsTr("Columns")' in menu
    assert "openCustomize" not in menu


def test_temporal_model_stays_truthful_no_fabricated_timestamps() -> None:
    """R14 (§46-47): History/Recently NO inventan datos temporales —
    last_played_at/play_count/first_seen_at son NEW_DESIGN si llegan; el
    QML nunca simula timestamps (ni mtime como 'added')."""
    for view in ("HistoryView", "RecentlyAddedView"):
        source = _read(f"views/{view}.qml")
        assert "mtime" not in source, view
        assert "lastPlayed" not in source and "last_played" not in source, view
        assert "playCount" not in source and "play_count" not in source, view
        assert "firstSeen" not in source and "addedAt" not in source, view
    # El modelo expone SOLO los datos reales (secuencia), nunca pseudo-datos.

    bridge = Path("src/michi/presentation/library_bridge.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "historyTrackRows = Property(" in bridge


def test_artist_gallery_does_not_crop_album_sleeves_as_portraits() -> None:
    source = _read("views/ArtistsView.qml")
    assert "|| artistCell.modelData.artworkPath" not in source
    assert "enrichment.artistPortraits[artistCell.modelData.key]" in source
    assert '|| ""' in source
    assert 'qsTr("%n artist(s)", "", library.artists.length)' in source


def test_library_error_copy_remains_translatable() -> None:
    source = _read("views/LibraryContentHost.qml")
    assert 'qsTr("Library unavailable")' in source
    assert 'qsTr("Scan failed")' in source
    message = (
        'qsTr("The library could not be scanned. '
        'Check your music folder and try again.")'
    )
    assert message in source


def test_visible_recovery_does_not_resurrect_file_browser() -> None:
    tabs = _read("views/LibraryTabs.qml")
    host = _read("views/LibraryContentHost.qml")
    assert 'value: "folders"' not in tabs
    assert 'case "folders"' not in host
    assert "FoldersView" not in host
