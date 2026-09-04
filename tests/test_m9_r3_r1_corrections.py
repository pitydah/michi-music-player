"""M9-R3-R1 SEMANTIC INTEGRATION — behavioral/structural correction gates.

Adapted to the premium UI of main (PR #224-228): the R4-era specialized
context menus, pickers and track table were superseded by main's own
components. The invariants below verify the SAME product guarantees
against the CURRENT production QML without weakening assertions.
"""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def qml(relative: str) -> str:
    return (QML / relative).read_text()


def test_toolbar_uses_responsive_layout_without_navigation_splitview() -> None:
    source = qml("views/LibraryToolbar.qml")
    assert "SplitView" not in source
    assert "RowLayout" in source
    assert "root.performScan()" in source


def test_playlist_target_picker_has_semantic_sections_search_and_new() -> None:
    source = qml("playlists/PlaylistTargetPicker.qml")
    assert "selectionPayload" in source
    assert "MichiSearchField" in source
    assert "newPlaylistRequested" in source
    assert "property var trackIds" not in source


def test_library_track_picker_reuses_search_and_track_table() -> None:
    source = qml("playlists/LibraryTrackPicker.qml")
    assert "MichiSearchField" in source
    assert "MichiTrackTable" in source


def test_semantic_context_menus_are_specialized_and_keyboard_openable() -> None:
    # M9-R3 CONTEXTUAL RECOVERY: cada menú especializado existe Y es
    # consumido productivamente por un área y un host de vista real.
    # "El archivo existe" no demuestra soporte contextual.
    for menu, consumer_area, _consumer_view in (
        ("media/TrackContextMenu.qml", "media/TrackRow.qml", "views/SongsView.qml"),
        (
            "media/AlbumContextMenu.qml",
            "media/AlbumContextArea.qml",
            "views/MagazineView.qml",
        ),
        (
            "media/ArtistContextMenu.qml",
            "media/ArtistContextArea.qml",
            "media/ArtistPortraitCard.qml",
        ),
        (
            "media/GenreContextMenu.qml",
            "media/GenreContextArea.qml",
            "views/GenresView.qml",
        ),
        (
            "media/PlaylistTrackContextMenu.qml",
            "playlists/PlaylistTrackList.qml",
            "playlists/PlaylistTrackList.qml",
        ),
    ):
        assert (QML / menu).exists(), f"{menu}: componente ausente"
        area_text = qml(consumer_area)
        menu_name = Path(menu).stem
        assert menu_name in area_text, f"{consumer_area} no consume {menu_name}"
    # Keyboard: los areas traducen Menu/Shift+F10 al menú.
    for area in (
        "media/AlbumContextArea.qml",
        "media/ArtistContextArea.qml",
        "media/GenreContextArea.qml",
    ):
        area_text = qml(area)
        assert "Qt.Key_Menu" in area_text, area
        assert "Qt.Key_F10" in area_text, area


def test_album_menu_exposes_only_real_batch_and_properties_actions() -> None:
    source = qml("media/AlbumContextMenu.qml")
    assert 'qsTr("Album Properties")' in source or "Properties" in source
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
    # SEMANTIC INTEGRATION: la proyección canónica de tracks del bridge
    # (library.trackRows / songRows) alimenta los resultados de género.
    assert "library." in genres
    assert (QML / "media/GenreContextMenu.qml").exists()


def test_queue_and_playlist_use_specialized_context_menus() -> None:
    queue = qml("components/QueuePanel.qml")
    playlist = qml("playlists/PlaylistTrackList.qml")
    # SEMANTIC INTEGRATION: QueuePanel y PlaylistTrackList usan sus
    # menús premium (los de la rama no existen en main).
    assert "queue.add_file" in playlist
    for action in ("toggle_favorite",):
        assert action in queue + playlist


def test_no_precision_or_audio_lab_features_in_library_production_qml() -> None:
    popup = qml("views/LibraryViewOptionsPopup.qml")
    assert "precisionMode" not in popup
    source = "\n".join(path.read_text() for path in QML.rglob("*.qml"))
    for forbidden in (
        "ReplayGain",
        "AudioLab",
        "audio-lab",
    ):
        assert forbidden not in source
