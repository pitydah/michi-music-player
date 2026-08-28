"""M9-R3-R1 behavioral/structural correction gates."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def qml(relative: str) -> str:
    return (QML / relative).read_text()


def test_toolbar_uses_responsive_layout_without_navigation_splitview() -> None:
    source = qml("views/LibraryToolbar.qml")
    assert "SplitView" not in source
    assert "GridLayout" in source
    assert "root.width < 900 ? 1 : 2" in source
    assert "root.performScan()" in source


def test_playlist_target_picker_has_semantic_sections_search_and_new() -> None:
    source = qml("playlists/PlaylistTargetPicker.qml")
    assert "selectionPayload" in source
    assert "pinnedRows" in source
    assert "recentRows" in source
    assert "MichiSearchField" in source
    assert 'qsTr("Pinned")' in source
    assert 'qsTr("Recent")' in source
    assert 'qsTr("New playlist…")' in source
    assert "newPlaylistRequested" in source
    assert "property var trackIds" not in source


def test_library_track_picker_reuses_search_and_track_table() -> None:
    source = qml("playlists/LibraryTrackPicker.qml")
    assert "MichiSearchField" in source
    assert "MichiTrackTable" in source
    assert "selectedTrackIds" in source
    assert "selectionEnabled: true" in source


def test_semantic_context_menus_are_specialized_and_keyboard_openable() -> None:
    for menu in (
        "media/TrackContextMenu.qml",
        "media/AlbumContextMenu.qml",
        "media/ArtistContextMenu.qml",
        "media/GenreContextMenu.qml",
        "media/PlaylistTrackContextMenu.qml",
        "media/QueueTrackContextMenu.qml",
    ):
        assert (QML / menu).exists(), menu
    track_row = qml("media/TrackRow.qml")
    assert "Qt.Key_Menu" in track_row
    assert "Qt.Key_F10" in track_row
    album_area = qml("media/AlbumContextArea.qml")
    assert "Qt.Key_Menu" in album_area
    assert "Qt.Key_F10" in album_area


def test_album_menu_exposes_only_real_batch_and_properties_actions() -> None:
    source = qml("media/AlbumContextMenu.qml")
    assert "MichiFormatBadge" not in source
    assert 'qsTr("Create Playlist from Album…")' in source
    assert 'qsTr("Album Properties")' in source
    assert "request_new_playlist_for_album" in source
    assert "request_album_properties" in source
    assert "library.queue_album" in source
    assert "library.play_album" in source
    assert "for (" not in source


def test_track_properties_cover_identity_audio_and_file_facts() -> None:
    source = qml("media/TrackPropertiesView.qml")
    for fact in (
        "albumArtist",
        "trackNumber",
        "discNumber",
        "durationMs",
        "formatLabel",
        "codec",
        "container",
        "sampleRateHz",
        "bitDepth",
        "bitrateBps",
        "channels",
        "fileSize",
        "path",
    ):
        assert fact in source
    assert (QML / "media/AlbumPropertiesView.qml").exists()


def test_album_views_have_open_play_context_and_no_fake_play_all() -> None:
    all_album_sources = "\n".join(
        qml(path)
        for path in (
            "views/AlbumGridView.qml",
            "views/AlbumPathView.qml",
            "views/VinylWallView.qml",
            "views/TimelineView.qml",
            "views/MagazineView.qml",
            "views/AlbumListView.qml",
            "media/AlbumCard.qml",
            "media/MichiAlbumRow.qml",
        )
    )
    assert "library.play_all()" not in all_album_sources
    assert all_album_sources.count("library.play_album") >= 6
    assert 'qsTr("SPOTLIGHT")' not in qml("views/MagazineView.qml")


def test_genre_results_open_canonical_track_projection() -> None:
    genres = qml("views/GenresView.qml")
    search = qml("patterns/SearchOverlay.qml")
    assert "library.select_genre(modelData.key)" in genres
    assert "library.select_genre(library.genres[index].key)" in search
    assert "interactive: false" not in search
    assert (QML / "media/GenreContextMenu.qml").exists()


def test_queue_and_playlist_use_specialized_context_menus() -> None:
    queue = qml("components/QueuePanel.qml")
    queue_navigation = qml("views/QueueView.qml")
    playlist = qml("playlists/PlaylistTrackList.qml")
    assert "QueueTrackContextMenu" in queue
    assert "PlaylistTrackContextMenu" in playlist
    for action in (
        "request_tracks_playlist_target",
        "toggle_favorite",
        "select_album",
        "select_artist",
        "TrackPropertiesView",
    ):
        assert action in queue + queue_navigation


def test_no_precision_or_audio_lab_features_in_library_production_qml() -> None:
    source = "\n".join(path.read_text() for path in QML.rglob("*.qml"))
    assert "precisionMode" not in source
    for forbidden in (
        "ReplayGain",
        "LUFS",
        "True Peak",
        "Spectrogram",
        "Waveform Analysis",
    ):
        assert forbidden not in source
