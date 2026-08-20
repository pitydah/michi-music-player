"""Static acceptance gates for the Michi UI Design Canon 2.0."""

from pathlib import Path

QML = Path("src/michi/presentation/qml")


def _text(relative: str) -> str:
    return (QML / relative).read_text()


def test_aurora_palette_replaces_legacy_pink() -> None:
    palette = _text("theme/MichiPalette.qml")
    assert "#4CA6FF" in palette
    assert "#21D6E6" in palette
    assert "#9A7CFF" in palette
    assert "#5DE3A2" in palette
    assert "#C06C9A" not in "\n".join(path.read_text() for path in QML.rglob("*.qml"))


def test_design_system_has_canonical_layers() -> None:
    required = {
        "theme/MichiAccessibility.qml",
        "theme/MichiBreakpoints.qml",
        "theme/MichiMotion.qml",
        "theme/MichiThemeState.qml",
        "primitives/MichiGlassSurface.qml",
        "primitives/MichiFocusRing.qml",
        "primitives/MichiIcon.qml",
        "controls/MichiButton.qml",
        "controls/MichiSearchField.qml",
        "controls/MichiSegmentedControl.qml",
        "patterns/AsyncStateView.qml",
        "patterns/SearchOverlay.qml",
        "media/Artwork.qml",
        "media/MichiPlayingIndicator.qml",
        "dev/MichiUIGallery.qml",
    }
    assert not [relative for relative in required if not (QML / relative).is_file()]


def test_glass_is_reserved_for_control_surfaces() -> None:
    shell = _text("shell/AppShell.qml")
    library = _text("views/LibraryView.qml")
    toolbar = _text("views/LibraryToolbar.qml")
    assert "MichiSemanticColors.backplane" in shell
    assert "MichiPanel" not in library
    assert "MichiGlassSurface" in toolbar


def test_artwork_access_is_centralized() -> None:
    direct_images = []
    for path in QML.rglob("*.qml"):
        if path.name == "Artwork.qml":
            continue
        if 'source: "file://"' in path.read_text():
            direct_images.append(str(path.relative_to(QML)))
    assert direct_images == []


def test_vinyl_wall_has_no_permanent_rotation() -> None:
    vinyl = _text("views/VinylWallView.qml")
    assert "RotationAnimation" not in vinyl
    assert "loops: Animation.Infinite" not in vinyl


def test_six_canonical_album_views_remain_available() -> None:
    albums = _text("views/AlbumsView.qml")
    expected = {
        "grid": "AlbumGridView.qml",
        "cover": "AlbumPathView.qml",
        "vinyl": "VinylWallView.qml",
        "timeline": "TimelineView.qml",
        "magazine": "MagazineView.qml",
        "list": "AlbumListView.qml",
    }
    for mode, filename in expected.items():
        assert f'onClicked: albumMode = "{mode}"' in albums
        assert (QML / "views" / filename).is_file()
    assert "CoverFlow" not in albums


def test_motion_loops_are_reduced_motion_aware() -> None:
    loading = _text("patterns/LoadingState.qml")
    playing = _text("media/MichiPlayingIndicator.qml")
    assert "!MichiAccessibility.reducedMotion" in loading
    assert "!MichiAccessibility.reducedMotion" in playing


def test_deferred_capabilities_have_no_qml_shells() -> None:
    filenames = {path.name.casefold() for path in QML.rglob("*.qml")}
    forbidden_fragments = (
        "audiolab",
        "michiai",
        "streaming",
        "ecosystem",
        "michisync",
        "homeaudio",
    )
    assert not [
        name
        for name in filenames
        if any(fragment in name for fragment in forbidden_fragments)
    ]


def test_package_contains_new_qml_layers() -> None:
    pyproject = Path("pyproject.toml").read_text()
    for directory in ("controls", "dev", "media", "patterns", "primitives"):
        assert f'"presentation/qml/{directory}/*.qml"' in pyproject


def test_search_and_playback_errors_are_actionable_surfaces() -> None:
    main = Path("src/michi/presentation/main.qml").read_text()
    now_playing = _text("views/NowPlayingView.qml")
    overlay = _text("patterns/SearchOverlay.qml")
    assert 'sequence: "Ctrl+F"' in main
    assert "playback.errorMessage" in now_playing
    assert "library.searchTrackCount" in overlay
    assert "Keys.onEscapePressed" in overlay


def test_library_delegates_use_shared_media_rows() -> None:
    track_views = (
        "views/SongsView.qml",
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
    )
    for view in track_views:
        assert "delegate: TrackRow" in _text(view)
    for view in (
        "views/ArtistsView.qml",
        "views/GenresView.qml",
        "views/FoldersView.qml",
    ):
        assert "delegate: MichiEntityRow" in _text(view)
    assert "delegate: MichiAlbumRow" in _text("views/AlbumListView.qml")


def test_density_precision_and_inspector_are_real_surfaces() -> None:
    toolbar = _text("views/LibraryToolbar.qml")
    album_detail = _text("views/AlbumDetailView.qml")
    assert "MichiThemeState.density" in toolbar
    assert "MichiThemeState.precisionMode" in toolbar
    assert "InspectorPanel" in album_detail
    assert "library.albumTechnicalSummary" in album_detail
    assert 'text: "Add to queue"' not in album_detail


def test_queue_panel_exposes_existing_m4_intents() -> None:
    queue_view = _text("views/QueueView.qml")
    queue_panel = _text("components/QueuePanel.qml")
    bridge = Path("src/michi/presentation/queue_bridge.py").read_text()
    assert "MichiGlassSurface" in queue_panel
    assert "queue.move_track" in queue_view
    assert "queue.remove_track" in queue_view
    assert "queue.clear_queue" in queue_view
    assert "def remove_track" in bridge


def test_search_overlay_supports_keyboard_result_navigation() -> None:
    field = _text("controls/MichiSearchField.qml")
    overlay = _text("patterns/SearchOverlay.qml")
    assert "nextResultRequested" in field
    assert "previousResultRequested" in field
    assert "activateResultRequested" in field
    assert "function moveResult" in overlay
    assert "function activateResult" in overlay
    assert "playlists" not in overlay.casefold()
