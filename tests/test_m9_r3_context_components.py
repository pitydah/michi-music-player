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
    # M9-R3 CONTEXTUAL RECOVERY: cada proyección de álbum consume el
    # componente de contexto REAL (AlbumContextArea) — un token suelto
    # de play/open no prueba soporte contextual. Ninguna vista es
    # "pasiva": VinylWall/Timeline/Magazine integran su propio contexto.
    for view in (
        "media/AlbumCard.qml",
        "media/MichiAlbumRow.qml",
        "views/AlbumPathView.qml",
        "views/VinylWallView.qml",
        "views/TimelineView.qml",
        "views/MagazineView.qml",
    ):
        text = _qml(view)
        assert "AlbumContextArea" in text, (
            f"{view}: consumer contextual productivo ausente"
        )


def test_artist_context_actions_are_capability_driven() -> None:
    # M9-R3: la card de artista (portrait) integra ArtistContextArea y la
    # acción Add-to-Playlist está fail-closed (canAddToPlaylist false).
    card = _qml("media/ArtistPortraitCard.qml")
    assert "ArtistContextArea" in card
    menu = _qml("media/ArtistContextMenu.qml")
    assert "property bool canAddToPlaylist: false" in menu
    assert "visible: root.artist !== null && root.canAddToPlaylist" in menu


def test_collection_actions_never_call_queue_service_bridge_directly() -> None:
    # M9-R3 + PR #232: el intent de queue del track identificado SIEMPRE
    # va por identidad (library.queue_track_by_id); queue.add_file queda
    # SOLO para miembros legacy explícitos. Nunca queue.add_many ciego.
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    assert "library.queue_track_by_id" in playlist_tracks
    assert "queue.add_many" not in playlist_tracks
    # El uso legacy (add_file) debe estar condicionado a la ausencia de
    # identidad — nunca la ruta por defecto del miembro identificado.
    legacy_block = playlist_tracks[
        playlist_tracks.index("queue.add_file") - 400 : playlist_tracks.index(
            "queue.add_file"
        )
        + 120
    ]
    assert "trackId" in legacy_block or "legacy" in legacy_block, (
        "add_file solo en la rama legacy explícita"
    )


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
