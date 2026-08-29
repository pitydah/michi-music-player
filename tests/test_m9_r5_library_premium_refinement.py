"""M9-R5 Library premium UI/UX refinement contracts."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_library_header_is_contextual_without_duplicate_views_label() -> None:
    header = _qml("views/LibraryHeader.qml")

    assert "function contextualSubtitle()" in header
    assert 'case "artists"' in header
    assert "library.artistCount" in header
    assert 'text: qsTr("VIEWS")' not in header


def test_search_and_scan_have_independent_toolbar_geometry() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    split = _qml("controls/MichiSplitButton.qml")

    search_start = toolbar.index('objectName: "resizableLibrarySearchPane"')
    scan_start = toolbar.index('objectName: "libraryScanSplitButton"')
    assert search_start < scan_start
    assert 'secondaryIconName: "chevron-down"' in toolbar
    assert "Layout.preferredWidth: 28" in split
    assert "TapHandler" in toolbar and "onDoubleTapped" in toolbar
    assert "visible: root.width >= 1100" in toolbar


def test_artist_portraits_use_a_dedicated_true_mask() -> None:
    portrait = _qml("media/ArtistPortraitArtwork.qml")
    card = _qml("media/ArtistPortraitCard.qml")
    detail = _qml("views/ArtistDetailView.qml")

    assert "import QtQuick.Effects" in portrait
    assert "MultiEffect" in portrait
    assert "maskEnabled: true" in portrait
    assert "maskSource:" in portrait
    assert "Artwork {" not in portrait
    assert "ArtistPortraitArtwork" in card
    assert "ArtistPortraitArtwork" in detail


def test_artist_gallery_prefetch_is_viewport_batched_and_debounced() -> None:
    artists = _qml("views/ArtistsView.qml")
    bridge = Path("src/michi/presentation/enrichment_bridge.py").read_text(
        encoding="utf-8"
    )

    assert "Component.onCompleted: enrichment.prefetch_artist_portrait" not in artists
    assert "prefetch_artist_portraits" in artists
    assert "interval: 180" in artists
    assert "firstVisibleRow" in artists
    assert "lastVisibleRow" in artists
    assert "def prefetch_artist_portraits" in bridge


def test_enrichment_surfaces_have_single_visibility_authority() -> None:
    status = _qml("enrichment/EnrichmentStatusBar.qml")
    knowledge = _qml("enrichment/EnrichmentKnowledgeCard.qml")
    album = _qml("views/AlbumDetailView.qml")
    artist = _qml("views/ArtistDetailView.qml")

    assert "onStateChanged:" not in status
    assert "onMessageChanged:" not in status
    assert "readonly property bool shouldShow" in status
    assert "visible: root.hasKnowledge" in knowledge
    assert 'activeKind === "album" && enrichment.albumHasKnowledge' in album
    assert 'activeKind === "artist" && enrichment.artistHasKnowledge' in artist
    assert "EnrichmentInlineState" in album
    assert "EnrichmentInlineState" in artist


def test_album_detail_and_grid_are_music_first_without_duplicate_quality() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    card = _qml("media/AlbumCard.qml")

    assert "LIBRARY QUALITY" not in detail
    assert 'objectName: "albumFactRail"' not in detail
    assert detail.count("library.albumDurationMs") <= 2
    assert "root.album.technicalSummary" not in card
    assert "root.album.trackCount" in card


def test_vinyl_disc_has_artwork_label_without_cyan_center() -> None:
    disc = _qml("media/VinylDisc.qml")
    wall = _qml("views/VinylWallView.qml")

    assert "property string labelArtworkPath" in disc
    assert "sourcePath: root.labelArtworkPath" in disc
    assert "MichiPalette.auroraCyan" not in disc
    assert "Repeater" not in disc
    assert "labelArtworkPath: modelData.artworkPath" in wall


def test_track_table_uses_safe_fixed_columns_and_context_profiles() -> None:
    state = _qml("theme/LibraryTrackColumnState.qml")
    table = _qml("media/MichiTrackTable.qml")

    assert "readonly property real artworkMaxWidth: 52" in state
    assert "property real durationWidth: 80" in state
    assert "readonly property real durationMinWidth: 76" in state
    assert "readonly property real actionsWidth" in state
    assert 'property string columnProfile: "songs"' in table
    assert "cacheBuffer: Math.max(0, height)" in table
    assert 'columnProfile: "album"' in _qml("views/AlbumDetailView.qml")
    assert 'columnProfile: "artist"' in _qml("views/ArtistDetailView.qml")


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
