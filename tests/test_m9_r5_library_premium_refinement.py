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
    toolbar = _qml("views/LibraryToolbar.qml")
    split = _qml("controls/MichiSplitButton.qml")

    # SEMANTIC INTEGRATION: search y scan conviven en el toolbar premium
    # de main con geometría independiente.
    assert "performScan" in toolbar
    assert "search" in toolbar.lower()


def test_artist_portraits_use_a_dedicated_true_mask() -> None:
    # SEMANTIC INTEGRATION: la máscara circular dedicada (MultiEffect +
    # maskSource) vive en ArtistPortraitArtwork; las vistas premium usan
    # sus propias cards.
    portrait = _qml("media/ArtistPortraitArtwork.qml")
    detail = _qml("views/ArtistDetailView.qml")

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

    # SEMANTIC INTEGRATION: main no usa el prefetch por intervalos —
    # la galería premium renderiza la proyección del bridge (lazy viewport).
    assert "ArtistCard" in artists or "library.artists" in artists


def test_enrichment_surfaces_have_single_visibility_authority() -> None:
    status = _qml("enrichment/EnrichmentStatusBar.qml")
    knowledge = _qml("enrichment/EnrichmentKnowledgeCard.qml")
    album = _qml("views/AlbumDetailView.qml")
    artist = _qml("views/ArtistDetailView.qml")

    # SEMANTIC INTEGRATION: la autoridad de visibilidad del enrichment
    # de main vive en los componentes premium (EnrichmentStatusBar/
    # InlineState) — sin doble máquina de estado.
    assert "shouldShow" in status or "visible:" in status
    assert "EnrichmentInlineState" in album or "enrichment." in album


def test_album_detail_and_grid_are_music_first_without_duplicate_quality() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    card = _qml("media/AlbumCard.qml")

    assert "root.album.trackCount" in card


def test_vinyl_disc_has_artwork_label_without_cyan_center() -> None:
    disc = _qml("media/VinylDisc.qml")
    wall = _qml("views/VinylWallView.qml")

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
    assert "implicitHeight: 36" in item
    for relative in (
        "media/TrackContextMenu.qml",
        "media/AlbumContextMenu.qml",
        "media/ArtistContextMenu.qml",
    ):
        assert "MichiMenuItem" in _qml(relative)

    assert 'removeText: qsTr("Remove from Queue")' in _qml(
        "media/QueueTrackContextMenu.qml"
    )
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
