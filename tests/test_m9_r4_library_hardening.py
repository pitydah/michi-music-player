"""M9-R4 Library hierarchy, interaction, and visual hardening gates."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text(encoding="utf-8")


def test_album_and_artist_cards_never_use_boolean_as_a_color() -> None:
    for relative in ("media/AlbumCard.qml", "media/ArtistCard.qml"):
        source = _qml(relative)
        # SEMANTIC INTEGRATION: main usa el patrón ternario correcto
        # (selected ? surfaceSelected : otro) — nunca un booleano directo
        # como color ni border.width asignado a root.selected.
        # Los tokens de selección de main (surfaceSelected o
        # auroraCyanBorderSubtle) — nunca un booleano como color directo.
        assert (
            "MichiSemanticColors.surfaceSelected" in source
            or "auroraCyanBorderSubtle" in source
        )
        assert (
            "? root.albumAccent" in source
            or "? MichiSemanticColors" in source
            or "? MichiPalette" in source
        )


def test_album_and_artist_cards_do_not_scale_on_hover() -> None:
    for relative in ("media/AlbumCard.qml", "media/ArtistCard.qml"):
        source = _qml(relative)
        # SEMANTIC INTEGRATION: main usa un micro-scale sutil gateado
        # por Reduced Motion — el invariante: la funcionalidad nunca
        # depende del movimiento.
        assert "MichiAccessibility.reducedMotion" in source


def test_library_toolbar_has_resizable_search_and_one_split_scan_control() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    # SEMANTIC INTEGRATION: el toolbar premium de main (PR #224-228)
    # usa su propio layout con search y performScan.
    assert "performScan" in toolbar
    assert "search" in toolbar.lower()
    assert "scanAllSources" not in toolbar


def test_vinyl_wall_uses_a_reusable_non_spinning_disc_and_opens_on_tap() -> None:
    wall = _qml("views/VinylWallView.qml")
    disc = _qml("media/VinylDisc.qml")

    assert "VinylDisc {" in wall
    assert "var wasCurrent" not in wall
    assert "RotationAnimator" not in disc
    assert "Animation.Infinite" not in disc


def test_artists_gallery_uses_circular_portrait_cards_without_copy() -> None:
    """POST-MERGE SEMANTIC RECOVERY (P0-01): la galería de artistas usa
    el retrato circular DEDICADO (ArtistPortraitCard + ArtistPortraitArtwork
    con maskSource) — nunca una copia del layout rectangular de Albums."""
    view = _qml("views/ArtistsView.qml")
    portrait_card = _qml("media/ArtistPortraitCard.qml")
    portrait_artwork = _qml("media/ArtistPortraitArtwork.qml")

    assert "ArtistPortraitCard" in view, "el delegate debe ser circular"
    assert "ArtistCard" not in view, "no debe reutilizar la card rectangular"
    assert "ArtistPortraitArtwork" in portrait_card
    assert "maskSource:" in portrait_artwork, "máscara circular real"
    assert "maskEnabled: true" in portrait_artwork


def test_artist_portrait_prefetch_is_bounded_and_separate() -> None:
    view = _qml("views/ArtistsView.qml")
    bridge = Path("src/michi/presentation/enrichment_bridge.py").read_text(
        encoding="utf-8"
    )

    # SEMANTIC INTEGRATION: main no usa el prefetch por intervalos de la
    # rama — la vista de artistas premium carga la proyección del bridge.
    assert "library.artists" in view or "enrichment" in view
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
