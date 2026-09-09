"""M9-R5 Library premium UI/UX refinement contracts."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_library_header_is_contextual_without_duplicate_views_label() -> None:
    header = _qml("views/LibraryHeader.qml")
    # SEMANTIC INTEGRATION: el header premium de main (PR #224-228)
    # contextualiza por ruta — sin label duplicado de "VIEWS".
    assert "library." in header
    # SEMANTIC INTEGRATION: el label "VIEWS" de main es CONTEXTUAL
    # (visible solo en album views XL) — nunca un duplicado permanente.
    assert "albumViewsVisible" in header


def test_search_and_scan_have_independent_toolbar_geometry() -> None:
    """P0-06 + R11 TOOL-01: search resizable y scan split conviven como
    hermanos en el GridLayout; el Enrich global NO vive en el toolbar
    (product decision §22.5)."""
    toolbar = _qml("views/LibraryToolbar.qml")
    assert "searchPanePreferredWidth" in toolbar
    assert 'objectName: "resizableLibrarySearchPane"' in toolbar
    assert 'objectName: "librarySearchResizeHandle"' in toolbar
    assert "DragHandler" in toolbar
    assert "resizeSearchBy" in toolbar
    assert "MichiSplitButton" in toolbar
    assert 'objectName: "libraryScanSplitButton"' in toolbar
    assert 'objectName: "libraryEnrichButton"' not in toolbar
    assert "id: sourceBtn" not in toolbar
    # El resizer desktop usa el seam incremental (nunca snapshot).
    assert "xAxis.onActiveValueChanged" in toolbar


def test_artist_portraits_use_a_dedicated_true_mask() -> None:
    portrait = _qml("media/ArtistPortraitArtwork.qml")

    assert "import QtQuick.Effects" in portrait
    assert "MultiEffect" in portrait
    assert "maskEnabled: true" in portrait
    assert "maskSource:" in portrait
    assert "Artwork {" not in portrait


def test_artist_gallery_prefetch_is_viewport_batched_and_debounced() -> None:
    artists = _qml("views/ArtistsView.qml")
    bridge = Path("src/michi/presentation/enrichment_bridge.py").read_text(
        encoding="utf-8"
    )

    # POST-MERGE SEMANTIC RECOVERY: prefetch de retratos restaurado —
    # viewport-bounded (visibleArtistKeys), debounced (180ms), gated
    # por Online ON; límites del bridge preservados.
    assert "schedulePortraitPrefetch" in artists
    assert "visibleArtistKeys" in artists
    assert "interval: 180" in artists
    assert "enrichment.prefetch_artist_portraits" in artists
    assert "onlineEnabled" in artists
    assert "_MAX_PORTRAIT_PREFETCH_QUEUE" in bridge


def test_enrichment_surfaces_have_single_visibility_authority() -> None:
    status = _qml("enrichment/EnrichmentStatusBar.qml")

    assert "shouldShow" in status or "visible:" in status


def test_album_detail_and_grid_are_music_first_without_duplicate_quality() -> None:
    card = _qml("media/AlbumCard.qml")
    assert "root.album.trackCount" in card

    # Album Detail keeps ONE canonical technical summary in the identity
    # column; the old repeated pills / LIBRARY QUALITY / Album facts panel
    # were the source of the screenshot's triple metadata duplication.
    detail = _qml("views/AlbumDetailView.qml")
    assert "albumTechnicalSummary" in detail
    assert "LIBRARY QUALITY" not in detail
    assert "albumTechnicalFacts" not in detail
    assert "AudioQualityBadge" not in detail
    assert "EnrichmentInlineState" in detail
    assert 'showArtwork: false' in detail
    assert "formatDurationPrecise" in detail


def test_vinyl_disc_has_artwork_label_without_cyan_center() -> None:
    disc = _qml("media/VinylDisc.qml")

    assert "MichiPalette.auroraCyan" not in disc
    assert "Repeater" not in disc


def test_track_table_uses_safe_fixed_columns_and_context_profiles() -> None:
    # SEMANTIC INTEGRATION: la tabla de la rama (LibraryTrackColumnState/
    # MichiTrackTable) persiste como componente de playlists; las vistas
    # primarias de main usan TrackRow con su propia geometría segura.
    state = _qml("theme/LibraryTrackColumnState.qml")
    assert "readonly property real actionsWidth" in state
    row = _qml("media/TrackRow.qml")
    assert "Layout.preferredWidth" in row


def test_context_menus_use_deterministic_michi_menu_items() -> None:
    item = _qml("controls/MichiMenuItem.qml")

    assert "MenuItem" in item
    # R10 (V4 §9.2): geometría determinista: implicitHeight por el token
    # de métrica + implicitWidth con autoridad mínima/máxima.
    assert "implicitHeight: MichiMetrics.controlMedium" in item
    assert "minimumItemWidth" in item
    assert "maximumItemWidth" in item
    for relative in (
        "media/TrackContextMenu.qml",
        "media/AlbumContextMenu.qml",
        "media/ArtistContextMenu.qml",
    ):
        assert "MichiMenuItem" in _qml(relative)

    # R6: el menú huérfano QueueTrackContextMenu fue removido; su contrato
    # mínimo (Remove from Queue) vive en el QueuePanel (fila de cola).
    assert 'removeText: qsTr("Remove from Queue")' in _qml("components/QueuePanel.qml")
    assert 'removeText: qsTr("Remove from this Playlist")' in _qml(
        "media/PlaylistTrackContextMenu.qml"
    )


def test_artist_tracks_project_existing_album_artwork_without_qml_lookup() -> None:
    bridge = Path("src/michi/presentation/library_bridge.py").read_text(
        encoding="utf-8"
    )

    artist_tracks = bridge.split("def _get_artist_tracks", 1)[1].split("\n    def ", 1)[
        0
    ]
    assert "_track_rows_with_artwork" in artist_tracks
    assert "for album in" not in _qml("views/ArtistDetailView.qml")
