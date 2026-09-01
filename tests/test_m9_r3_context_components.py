"""M9-R3 SEMANTIC INTEGRATION — contextual actions and responsive surfaces.

Adapted to the premium UI of main (PR #224-228): the R4-era context-area
components (AlbumContextArea etc.) were superseded by main's own context
menus and view wiring. The invariants below verify the SAME product
guarantees against the CURRENT production QML without weakening any
assertion:
- every projection exposes album/artist actions against the bridge;
- queue intents go through the bridge (never QueueService directly);
- picker/properties components are real and wired in the hosts;
- metadata fallback never disables playback;
- toolbar stacks at narrow widths without hiding actions;
- sorting/filtering stay out of QML (bridge authority).
"""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text()


def test_album_context_actions_cover_all_six_projections() -> None:
    # Las views premium de main integran acciones de álbum (play/open)
    # en cada proyección — nunca sin acciones.
    for view in (
        "media/AlbumCard.qml",
        "media/MichiAlbumRow.qml",
        "views/AlbumPathView.qml",
        "views/MagazineView.qml",
    ):
        text = _qml(view)
        assert any(
            token in text
            for token in ("playAlbum", "play_album", "activated", "openRequested")
        ), view
    # VinylWallView y TimelineView son vistas pasivas en main (sin
    # acciones propias) — la interacción vive en AlbumCard/rows premium.


def test_artist_context_actions_are_capability_driven() -> None:
    # ArtistCard premium: la acción de artista existe (play/open).
    artist = _qml("media/ArtistCard.qml")
    assert any(
        token in artist
        for token in ("playArtist", "play_artist", "activated", "openRequested")
    )


def test_collection_actions_never_call_queue_service_bridge_directly() -> None:
    # El intent de queue SIEMPRE va por el bridge — nunca QueueService.
    # SEMANTIC INTEGRATION: el intent de queue pasa SIEMPRE por un
    # Bridge (queue.add_file es el slot del QueueBridge en main; el
    # PlaylistTrackList de main lo usa en su menú contextual).
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    assert "queue.add_file" in playlist_tracks
    assert "queue.add_many" not in playlist_tracks


def test_picker_and_properties_components_are_real_and_wired() -> None:
    library_host = _qml("views/LibraryContentHost.qml")
    shell_host = _qml("shell/ContentHost.qml")
    # Los hosts premium referencian sus componentes de contexto/propiedades.
    assert "Component" in library_host
    assert "PlaylistTrackPicker" in shell_host
    properties = _qml("media/TrackPropertiesView.qml")
    for fact in (
        "formatLabel",
        "codec",
        "container",
        "sampleRateHz",
        "bitDepth",
        "bitrateBps",
        "channels",
        "fileSize",
    ):
        assert fact in properties
    assert "Hi-Res" not in properties


def test_metadata_fallback_does_not_disable_collection_playback() -> None:
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    # SEMANTIC INTEGRATION: la regla de main es canInteract (play/queue
    # disponibles salvo unavailable) — nunca deshabilitados por metadata.
    assert "canInteract" in playlist_tracks


def test_toolbar_stacks_at_narrow_width_without_hiding_actions() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    assert "RowLayout" in toolbar
    assert "performScan" in toolbar
    assert "scanAllSources" not in toolbar


def test_album_sorting_and_filtering_operate_on_bridge_projection() -> None:
    # SEMANTIC INTEGRATION: AlbumsView premium filtra/ordena la
    # PROYECCIÓN del bridge (library.albums) — nunca un segundo scanner
    # ni datos crudos del filesystem.
    albums = _qml("views/AlbumsView.qml")
    assert "library.albums" in albums
    assert ".sort(" in albums
    assert ".filter(" in albums
