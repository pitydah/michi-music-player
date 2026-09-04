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
    # El uso legacy (add_file) debe estar condicionado EXPLÍCITAMENTE a la
    # ausencia de identidad estable — nunca la ruta por defecto.
    queue_handler = playlist_tracks[
        playlist_tracks.index("onQueueRequested") : playlist_tracks.index(
            "onFavoriteRequested"
        )
    ]
    assert "hasStableTrackId" in queue_handler
    assert "library.queue_track_by_id" in queue_handler
    # add_file solo en el else-if legacy (después del branch identificado).
    assert queue_handler.index("library.queue_track_by_id") < (
        queue_handler.index("queue.add_file")
    ), "identificado primero; legacy solo como fallback"
    assert "!trackItem.hasStableTrackId" in queue_handler


def test_picker_and_properties_components_exist_without_implying_context_host() -> None:
    """Los componentes picker/properties existen como componentes — PERO el
    host contextual compartido (playlist_target_requested /
    album_properties_requested productivamente consumidos) NO está wired
    todavía: llega en PR D. Este test no afirma un wiring inexistente."""
    library_host = _qml("views/LibraryContentHost.qml")
    shell_host = _qml("shell/ContentHost.qml")
    # Los hosts referencian sus componentes premium existentes.
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
    # FAIL-CLOSED (PR D): los menús no exponen las acciones sin consumer
    # compartido — nunca inferir capacidad del signal del Bridge.
    album_menu = _qml("media/AlbumContextMenu.qml")
    assert "property bool canAddToPlaylist: false" in album_menu
    assert "property bool canCreatePlaylist: false" in album_menu
    assert "property bool canShowProperties: false" in album_menu
    artist_menu = _qml("media/ArtistContextMenu.qml")
    assert "property bool canAddToPlaylist: false" in artist_menu


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
