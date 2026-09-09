"""Regression seals for the Album Detail UI/UX refinement.

These gates protect both sides of the patch: visual hierarchy and the
productive seams that must not regress while presentation changes.
"""

from pathlib import Path

ROOT = Path(__file__).parents[1]
QML = ROOT / "src" / "michi" / "presentation" / "qml"


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_album_detail_compacts_duplicate_metadata_into_one_hero() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    metric_source = detail.split("readonly property var heroMetricRows:", 1)[1].split(
        "AlbumPaletteBinding", 1
    )[0]

    assert 'objectName: "albumHeroSurface"' in detail
    assert "heroMetricRows" in detail
    assert "technicalSummaryText" in detail
    assert "albumTechnicalSummary" in detail
    assert "LIBRARY QUALITY" not in detail
    assert "albumTechnicalFacts" not in detail
    assert "Album facts" not in detail
    assert "AudioQualityBadge" not in detail
    assert "MichiStatusChip" not in detail
    assert "compactTechnicalSummary" not in detail
    assert 'qsTr("Stereo")' in detail
    assert 'qsTr("N/A")' in detail

    # The canonical technical summary owns codec/rate/depth or bitrate. The
    # metric rail must not repeat sample rate. Channels are derived from all
    # album members and may say Mixed only when that is factually observed.
    assert "SAMPLE RATE" not in metric_source
    assert "albumChannelsText()" in detail
    assert 'return qsTr("Mixed")' in detail


def test_album_detail_uses_shared_formatting_authority() -> None:
    detail = _qml("views/AlbumDetailView.qml")

    assert "MichiFormat.formatDuration(" in detail
    assert "MichiFormat.formatFileSize(" in detail
    assert "function formatDuration" not in detail
    assert "function formatFileSize" not in detail


def test_album_detail_bounds_context_and_preserves_track_viewport() -> None:
    detail = _qml("views/AlbumDetailView.qml")

    assert "MichiScrollView" in detail
    assert 'objectName: "albumContextScroll"' in detail
    assert "albumContextColumn.implicitHeight" in detail
    assert "contextFraction: root.height < 560 ? 0.42 : 0.54" in detail
    assert "Math.min(440" in detail
    assert 'objectName: "albumTrackTableSurface"' in detail
    assert 'objectName: "albumTracksTable"' in detail
    assert "MichiTrackTable" in detail
    assert "Layout.minimumHeight: Math.min(132" in detail
    assert 'columnProfile: "album"' in detail
    assert 'numberingMode: "disc-track"' in detail
    assert "showArtwork: false" in detail

    # Canonical TrackId-first behavior and productive context seams survive
    # the redesign unchanged.
    for seam in (
        "activate_album_track_by_id(trackId)",
        "toggle_favorite_by_id(trackId)",
        "queue_track_by_id(trackId)",
        "request_tracks_playlist_target([trackId])",
        "select_artist(artistKey)",
    ):
        assert seam in detail


def test_album_detail_hero_does_not_create_an_inset_card_inside_glass() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    hero = detail.split('objectName: "albumHeroSurface"', 1)[1].split(
        "// ── Factual knowledge", 1
    )[0]

    assert "accentLineVisible: true" in hero
    assert "gradient: Gradient" not in hero


def test_album_information_matches_the_actual_enrichment_contract() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    card = _qml("enrichment/EnrichmentKnowledgeCard.qml")

    assert 'qsTr("Album information")' in detail
    assert "firstReleaseYear" in card
    assert "root.knowledge.releaseYear || root.knowledge.firstReleaseYear" in card
    assert 'qsTr("Release year")' in card
    assert 'qsTr("Show more")' in card
    assert 'qsTr("Show less")' in card


def test_album_detail_enrichment_stays_cache_only_but_fetch_is_reachable() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    inline = _qml("enrichment/EnrichmentInlineState.qml")
    status = _qml("enrichment/EnrichmentStatusBar.qml")

    assert "enrichment.open_album_cached(root.selectedAlbumKey)" in detail
    assert "enrichment.refresh_album()" in detail
    assert "EnrichmentInlineState" in detail
    assert "EnrichmentActions" not in detail
    assert "EnrichmentStatusBar" not in detail
    assert "showTitle: false" in detail
    assert 'state === "IDLE" || state === "READY"' in inline
    assert 'qsTr("Fetch information")' in inline
    assert 'hasKnowledge: enrichment.activeKind === "album"' in detail
    assert "&& enrichment.albumHasKnowledge" in detail

    # A freshly-created IDLE status bar must be hidden declaratively; relying
    # on change handlers leaves a stray IDLE chip when no signal fires.
    assert 'readonly property bool shouldShow: state !== "IDLE"' in status
    assert "visible: root.shouldShow" in status
    assert "onStateChanged: root.visible" not in status


def test_album_detail_more_menu_reuses_productive_album_context_ia() -> None:
    detail = _qml("views/AlbumDetailView.qml")
    menu = _qml("media/AlbumContextMenu.qml")

    assert "AlbumContextMenu" in detail
    assert "showOpenAction: false" in detail
    assert "property bool showOpenAction: true" in menu
    assert "root.showOpenAction" in menu
    for action in (
        "library.play_album(root.album.key)",
        "library.queue_album(root.album.key)",
        "library.request_album_playlist_target(root.album.key)",
        "library.request_new_playlist_for_album(root.album.key)",
        "library.request_album_properties(root.album.key)",
    ):
        assert action in menu


def test_library_chrome_is_detail_aware_without_losing_global_actions() -> None:
    header = _qml("views/LibraryHeader.qml")
    toolbar = _qml("views/LibraryToolbar.qml")

    assert 'library.selectedAlbumKey !== ""' in header
    assert 'qsTr("Album details")' in header
    assert 'qsTr("Search library…")' in toolbar
    assert 'qsTr("Search albums or album artists…")' in toolbar
    assert 'objectName: "libraryScanSplitButton"' in toolbar


def test_decorative_material_texture_never_renders_broken_image_placeholder() -> None:
    texture = _qml("primitives/MichiMaterialTexture.qml")
    surface = _qml("primitives/MichiSurface.qml")
    glass = _qml("primitives/MichiGlassSurface.qml")

    # The component root stays present while its internal asynchronous Image
    # loads. Loading/Error never paints the platform placeholder, while the
    # root preserves the historic opacity contract consumed by surfaces.
    assert "Item {\n    id: root" in texture
    assert "Image {" in texture
    assert "texture.status === Image.Ready" in texture
    assert "readonly property bool textureReady" in texture
    assert "opacity: root.textureOpacity" in texture
    assert "visible: opacity > 0" in texture
    assert "implicitWidth: 128" in texture
    assert "implicitHeight: 128" in texture
    assert "opacity: root.textureReady ? 1 : 0" in texture
    assert "visible: root.textureReady" in texture
    assert "visible: root.level === \"content\" && opacity > 0" in surface
    assert "visible: root.textured && opacity > 0" in glass
