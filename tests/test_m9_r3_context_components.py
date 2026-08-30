"""M9-R3 structural gates for contextual actions and responsive surfaces."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _qml(relative: str) -> str:
    return (QML / relative).read_text()


def test_album_context_actions_cover_all_six_projections() -> None:
    assert "AlbumContextArea" in _qml("media/AlbumCard.qml")
    assert "AlbumContextArea" in _qml("media/MichiAlbumRow.qml")
    for view in (
        "views/AlbumPathView.qml",
        "views/VinylWallView.qml",
        "views/TimelineView.qml",
        "views/MagazineView.qml",
    ):
        assert "AlbumContextArea" in _qml(view), view
    menu = _qml("media/AlbumContextMenu.qml")
    assert "library.play_album" in menu
    assert "library.queue_album" in menu
    assert "library.request_album_playlist_target" in menu
    assert "library.canQueueTracks" in menu
    assert "library.canAddTracksToPlaylists" in menu


def test_artist_context_actions_are_capability_driven() -> None:
    assert "ArtistContextArea" in _qml("media/ArtistCard.qml")
    menu = _qml("media/ArtistContextMenu.qml")
    assert "library.select_artist" in menu
    assert "library.queue_artist" in menu
    assert "library.request_artist_playlist_target" in menu
    assert "library.canQueueTracks" in menu


def test_collection_actions_never_call_queue_service_bridge_directly() -> None:
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    assert "queue.add_file" not in playlist_tracks
    assert "library.queue_track" in playlist_tracks
    for view in (
        "views/SongsView.qml",
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
    ):
        source = _qml(view)
        assert "canQueue: library.canQueueTracks" in source
        # CORRECTIVE SEAL §11: queue intent is TrackId-first.
        assert (
            "onQueueRequested: trackId => library.queue_track_by_id(trackId)" in source
        )
    queue_panel = _qml("components/QueuePanel.qml")
    assert "canMoveUp: index > 0" in queue_panel
    assert "onMoveUpRequested: root.moveRequested" in queue_panel


def test_picker_and_properties_components_are_real_and_wired() -> None:
    library_host = _qml("views/LibraryContentHost.qml")
    shell_host = _qml("shell/ContentHost.qml")
    assert "PlaylistTargetPicker" in shell_host
    assert "TrackPropertiesView" in library_host
    assert "LibraryTrackPicker" in shell_host
    assert "library.add_tracks_to_playlist" in shell_host
    assert "library.add_album_to_playlist" in shell_host
    assert "library.add_artist_to_playlist" in shell_host
    assert "library.add_tracks_to_playlist" in shell_host
    properties = _qml("media/TrackPropertiesView.qml")
    for fact in (
        "formatLabel",
        "codec",
        "container",
        "sampleRateHz",
        "bitDepth",
        "dsdRate",
        "bitrateBps",
        "channels",
        "fileSize",
        "path",
    ):
        assert fact in properties
    assert "Hi-Res" not in properties


def test_metadata_fallback_does_not_disable_collection_playback() -> None:
    queue_panel = _qml("components/QueuePanel.qml")
    playlist_tracks = _qml("playlists/PlaylistTrackList.qml")
    assert "unavailable: false" in queue_panel
    assert "canPlayNow: true" in playlist_tracks
    assert "onGoToAlbumRequested:" in _qml("shell/ContentHost.qml")
    assert 'navigation.navigate("library")' in _qml("shell/ContentHost.qml")


def test_toolbar_stacks_at_narrow_width_without_hiding_actions() -> None:
    toolbar = _qml("views/LibraryToolbar.qml")
    assert "columns: root.width < 1100 ? 2 : 4" in toolbar
    assert "GridLayout" in toolbar
    assert 'secondaryIconName: "chevron-down"' in toolbar
    # R5.1.1: the scan split button is icon-less by default (compact).
    assert 'iconName: ""' in toolbar
    # M6-EXT-R4 freeze gate §13 + PRODUCT CONVERGENCE SEAL (P1-LIB-01):
    # the primary scan action drives the multi-source workflow through the
    # ONE canonical snake_case action (the camelCase alias never existed).
    assert "performScan" in toolbar
    assert "scan_all_sources()" in toolbar
    assert "scanAllSources" not in toolbar
    assert "MichiSplitButton" in toolbar
    assert "Math.min(root.width" in toolbar


def test_album_sorting_and_filtering_are_not_implemented_in_qml() -> None:
    albums = _qml("views/AlbumsView.qml")
    assert ".sort(" not in albums
    assert ".filter(" not in albums
    assert "Hi-Res" not in _qml("views/LibraryViewOptionsPopup.qml")
