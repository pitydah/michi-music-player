"""M9-R4 Library hierarchy, interaction, and visual hardening gates."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_album_and_artist_cards_never_use_boolean_as_a_color() -> None:
    for relative in ("media/AlbumCard.qml", "media/ArtistCard.qml"):
        source = _qml(relative)
        assert ": root.selected\n        border.width" not in source
        assert "MichiSemanticColors.surfaceSelected" in source
        assert "MichiSemanticColors.contentSurface" in source


def test_album_and_artist_cards_do_not_scale_on_hover() -> None:
    for relative in ("media/AlbumCard.qml", "media/ArtistCard.qml"):
        source = _qml(relative)
        assert "scale: hover.hovered" not in source
        assert "Behavior on scale" not in source


def test_library_toolbar_has_resizable_search_and_one_split_scan_control() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    split_button = _qml("controls/MichiSplitButton.qml")

    assert "property real searchPanePreferredWidth" in toolbar
    assert 'objectName: "librarySearchResizeHandle"' in toolbar
    assert "DragHandler" in toolbar
    assert "Layout.fillWidth: root.width < 1100" in toolbar
    assert "MichiSplitButton" in toolbar
    assert "onPrimaryClicked: root.performScan()" in toolbar
    assert "onSecondaryClicked: sourceMenu.popup()" in toolbar
    assert "id: sourceBtn" not in toolbar
    assert "signal primaryClicked()" in split_button
    assert "signal secondaryClicked()" in split_button


def test_vinyl_wall_uses_a_reusable_non_spinning_disc_and_opens_on_tap() -> None:
    wall = _qml("views/VinylWallView.qml")
    disc = _qml("media/VinylDisc.qml")

    assert "VinylDisc {" in wall
    assert "library.select_album(modelData.key)" in wall
    assert "var wasCurrent" not in wall
    assert "RotationAnimator" not in disc
    assert "Animation.Infinite" not in disc
    assert "Repeater" not in disc
    assert "MichiPalette.graphiteRaised" not in disc


def test_artists_gallery_uses_circular_portrait_cards_without_copy() -> None:
    view = _qml("views/ArtistsView.qml")
    portrait = _qml("media/ArtistPortraitCard.qml")

    assert "ArtistPortraitCard {" in view
    assert "Select an artist to explore albums and tracks" not in view
    assert "cellWidth - cardGap" in view
    assert "ArtistPortraitArtwork" in portrait
    assert "ArtistContextArea" in portrait
    assert "scale: hover.hovered" not in portrait


def test_artist_portrait_prefetch_is_bounded_and_separate() -> None:
    view = _qml("views/ArtistsView.qml")
    bridge = Path("src/michi/presentation/enrichment_bridge.py").read_text(
        encoding="utf-8"
    )

    assert "Component.onCompleted: schedulePortraitPrefetch()" in view
    assert "prefetch_artist_portraits" in view
    assert "interval: 180" in view
    assert "enrichment.artistPortraits" in view
    assert "_MAX_PORTRAIT_PREFETCH_INFLIGHT = 2" in bridge
    assert "artistPortraits = Property" in bridge
    assert (
        "self._active_kind ="
        not in bridge.split("def _apply_portrait_event", 1)[1].split(
            "def _invalidate_review_session", 1
        )[0]
    )


def test_artist_context_menu_has_identity_header_and_only_real_actions() -> None:
    menu = _qml("media/ArtistContextMenu.qml")

    assert "RowLayout" in menu
    assert "root.artist.name" in menu
    assert "root.artist.albumCount" in menu
    assert "library.select_artist(root.artist.key)" in menu
    assert "library.queue_artist(root.artist.key)" in menu
    assert "library.request_artist_playlist_target(root.artist.key)" in menu
    assert "library.play_artist" not in menu
    assert "request_artist_properties" not in menu
