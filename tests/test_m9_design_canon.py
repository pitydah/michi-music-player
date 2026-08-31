"""Static acceptance gates for the Michi UI Design Canon 2.0."""

import re
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
        "primitives/MichiMaterialTexture.qml",
        "primitives/MichiStatusChip.qml",
        "controls/MichiButton.qml",
        "controls/MichiSearchField.qml",
        "controls/MichiSegmentedControl.qml",
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


def test_material_texture_is_lightweight_packaged_and_quality_aware() -> None:
    texture = _text("primitives/MichiMaterialTexture.qml")
    glass = _text("primitives/MichiGlassSurface.qml")
    surface = _text("primitives/MichiSurface.qml")
    package = Path("pyproject.toml").read_text()
    # Library Views 2.0: static catalog assets are decoded once by Qt and
    # shared across surfaces; no Canvas/data URL is generated per instance.
    assert "Canvas {" not in texture
    assert "toDataURL" not in texture
    assert 'return "../assets/" + resolved + ".svg"' in texture
    assert (QML / "assets/grain-graphite-01.svg").is_file()
    assert (QML / "assets/grain-glass-01.svg").is_file()
    assert (QML / "assets/paper-editorial-01.svg").is_file()
    assert "property int tileSeed: 0" in texture
    assert 'MichiThemeState.glassQuality === "low" ? 0' in texture
    assert "property bool shadowed" in glass
    assert "MichiElevation.shadowFarSpread" in glass
    assert "MichiMaterialTexture" in glass
    assert "MichiMaterialTexture" in surface
    assert "presentation/qml/theme/*.qml" in package


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
    for directory in (
        "controls",
        "dev",
        "media",
        "patterns",
        "player",
        "primitives",
    ):
        assert f'"presentation/qml/{directory}/*.qml"' in pyproject


def test_canonical_now_playing_bar_is_shell_bound() -> None:
    bar = _text("player/NowPlayingBar.qml")
    shell = _text("shell/AppShell.qml")
    assert "implicitWidth: 800" in bar
    assert "implicitHeight: 154" in bar
    assert "readonly property bool compact" in bar
    assert 'objectName: "playbackZone"' in bar
    assert 'objectName: "outputZone"' in bar
    assert "NowPlayingBar" in shell
    for projection in (
        "playback.position",
        "playback.duration",
        "playback.volume",
        "playbackSession.shuffleEnabled",
        "playbackSession.repeatMode",
    ):
        assert projection in shell


def test_premium_detail_pass_is_shared_and_capability_honest() -> None:
    glass = _text("primitives/MichiGlassSurface.qml")
    button = _text("controls/MichiButton.qml")
    toolbar = _text("views/LibraryToolbar.qml")
    content = _text("views/LibraryContentHost.qml")
    queue = _text("views/QueueView.qml")
    now_playing = _text("player/NowPlayingBar.qml")
    assert "property bool accented" in glass
    assert "Behavior on scale" in button
    assert 'objectName: "stableLibrarySearchPane"' in toolbar
    assert "Layout.preferredWidth: 82" in toolbar
    assert 'import "../controls"' in content
    assert 'text: qsTr("ADD TRACK TO")' in content
    assert "MichiIconButton" in content
    assert "property bool revealed" in queue
    assert "Gradient.Horizontal" in now_playing
    assert 'objectName: "qualityBadge"' in now_playing
    assert now_playing.count('objectName: "outputDeviceButton"') == 1
    assert 'accessibleName: qsTr("Output selection unavailable")' in now_playing
    # M11.3-UI: the placeholder indicator is replaced by a real interactive
    # quick-selector button. The popup is the quick surface; no configuration
    # controls (DAC/DSD/sample-rate/buffers) live here.
    assert now_playing.count('objectName: "audioEngineButton"') == 1
    assert 'objectName: "audioEngineIndicator"' not in now_playing
    assert "AudioEnginePopup" in now_playing
    assert 'objectName: "outputStatusButton"' not in now_playing


def test_audio_engine_quick_selector_bound_in_shell() -> None:
    """M11.3-UI: the NowPlayingBar quick selector is wired in AppShell."""
    now_playing = _text("player/NowPlayingBar.qml")
    app_shell = _text("shell/AppShell.qml")
    assert now_playing.count('objectName: "audioEngineButton"') == 1
    assert 'objectName: "audioEngineIndicator"' not in now_playing
    assert "AudioEnginePopup" in now_playing
    assert "onAudioEngineSwitchRequested" in app_shell
    assert "audioEngine.switch_engine" in app_shell


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
    assert "ArtistCard {" in _text("views/ArtistsView.qml")
    assert 'objectName: "artistGridView"' in _text("views/ArtistsView.qml")
    for view in ("views/GenresView.qml", "views/FoldersView.qml"):
        assert "delegate: MichiEntityRow" in _text(view)
    assert "delegate: MichiAlbumRow" in _text("views/AlbumListView.qml")


def test_density_precision_and_inspector_are_real_surfaces() -> None:
    header = _text("views/LibraryHeader.qml")
    popup = _text("views/LibraryViewOptionsPopup.qml")
    toolbar = _text("views/LibraryToolbar.qml")
    album_detail = _text("views/AlbumDetailView.qml")
    assert "View options" in header
    assert "viewPreferenceRequested" in popup
    assert "galleryOptions" in popup
    assert "studioOptions" in popup
    assert "precisionMetadata" in popup
    assert "MichiThemeState.density" not in toolbar
    assert "MichiThemeState.precisionMode" not in toolbar
    assert "InspectorPanel" in album_detail
    assert "library.albumTechnicalSummary" in album_detail
    assert 'text: "Add to queue"' not in album_detail


def test_library_navigation_and_path_selection_follow_the_canon() -> None:
    tabs = _text("views/LibraryTabs.qml")
    toolbar = _text("views/LibraryToolbar.qml")
    library = _text("views/LibraryView.qml")
    path_view = _text("views/AlbumPathView.qml")
    assert 'objectName: "libraryNavigationRail"' in tabs
    assert "signal tabRequested(string tab)" in tabs
    assert "root.tabRequested(modelData.value)" in tabs
    assert "ensureCurrentTabVisible" in tabs
    assert "LibraryTabs {" in toolbar
    assert "onCurrentTabRequested" in library
    assert "LibraryTabs {" not in library
    for icon in ("track", "album", "artist", "genre", "heart", "history", "recent"):
        assert f'icon: "{icon}"' in tabs
    # M9-R2: Folders removed from visual tabs per product decision
    assert 'icon: "folder"' not in tabs
    # M9-R1 hierarchy: Playlists is a first-class Shell feature — it is NOT
    # a Library tab (canonical playlist navigation resolves through
    # AppRoute.PLAYLISTS, per PLAYLIST-HIERARCHY-01/03).
    assert 'icon: "playlist"' not in tabs
    assert 'objectName: "pathViewSelectionCard"' in path_view
    assert "width: Math.min(720" in path_view
    assert "anchors.leftMargin: MichiSpacing.xl" not in path_view
    assert "anchors.bottom: parent.bottom" in path_view
    assert 'text: qsTr("Open album")' in path_view


def test_album_artwork_zoom_is_real_and_persistent() -> None:
    library = _text("views/LibraryView.qml")
    popup = _text("views/LibraryViewOptionsPopup.qml")
    content = _text("views/LibraryContentHost.qml")
    albums = _text("views/AlbumsView.qml")
    grid = _text("views/AlbumGridView.qml")
    vinyl = _text("views/VinylWallView.qml")
    path = _text("views/AlbumPathView.qml")
    icons = _text("primitives/MichiIcon.qml")
    assert "property real albumZoom: 1.0" in library
    assert "libraryViews" in library
    assert "set_library_views" in library
    assert "artworkSize" in popup
    assert "coverSize" in popup
    assert "sleeveSize" in popup
    assert "albumZoom: root.albumZoom" in content
    assert albums.count("albumZoom: root.albumZoom") == 3
    for source in (grid, vinyl, path):
        assert "property real albumZoom: 1.0" in source
        assert "albumZoom" in source
    assert 'root.name === "view-options"' in icons


def test_album_grid_and_detail_have_premium_information_hierarchy() -> None:
    grid = _text("views/AlbumGridView.qml")
    card = _text("media/AlbumCard.qml")
    detail = _text("views/AlbumDetailView.qml")
    artwork = _text("media/Artwork.qml")
    assert "minimumCardWidth" in grid
    assert "maximumCardWidth" in grid
    assert "resolvedCardWidth" in grid
    assert "technicalText" in card
    assert "album.technicalSummary" in card
    assert "root.album.trackCount" in card
    assert 'objectName: "albumHeroSurface"' in detail
    assert 'objectName: "albumTrackTableSurface"' in detail
    assert "library.albumDurationMs" in detail
    assert "asynchronous: true" in artwork
    assert "cache: true" in artwork
    assert "sourceSize.width" in artwork


def test_transport_microdetails_are_coherent_surfaces() -> None:
    bar = _text("player/NowPlayingBar.qml")
    icons = _text("primitives/MichiIcon.qml")
    assert 'objectName: "volumeControlRow"' in bar
    assert 'objectName: "volumeControlSurface"' not in bar
    assert bar.count("height: root.sliderTrackHeight") == 2
    assert "playPauseButton.hovered ? 1.025" in bar
    assert bar.count("x: volumeSlider.leftPadding") == 2
    assert bar.count("y: volumeSlider.topPadding") == 2
    repeat_branch = icons.split(
        '} else if (root.name === "repeat" || root.name === "repeat-one") {'
    )[1].split('} else if (root.name === "view-options") {')[0]
    assert "ctx.arc" not in repeat_branch


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
    assert (
        "playlists.searchPlaylists" in overlay
    )  # M9-R1: playlist projection via PlaylistsBridge
    assert "playlists.open_playlist" in overlay  # M9-R1: validated open intent


def test_artist_detail_focus_mode_and_contextual_queue_are_real() -> None:
    artists = _text("views/ArtistsView.qml")
    artist_detail = _text("views/ArtistDetailView.qml")
    now_playing = _text("views/NowPlayingView.qml")
    shell = _text("shell/AppShell.qml")
    track_row = _text("media/TrackRow.qml")
    assert "library.select_artist" in artists
    assert "library.artistTracks" in artist_detail
    assert "ArtworkFocusMode" in now_playing
    assert 'active: root.currentRoute === "queue"' in shell
    assert "Qt.RightButton" in track_row
    assert "MichiContextMenu" in track_row


def test_now_playing_page_never_duplicates_the_persistent_transport() -> None:
    page = _text("views/NowPlayingView.qml")
    focus = _text("media/ArtworkFocusMode.qml")
    assert "ArtworkFocusMode" in page
    assert (
        'message: "Choose a track from your library. Playback controls remain '
        'in the persistent bar below."' in page
    )
    for duplicate in (
        "NowPlayingPanel",
        "PlaybackControls",
        "PlaybackProgress",
        "VolumeControl",
    ):
        assert duplicate not in page
        assert duplicate not in focus


def test_playing_indicator_is_bound_on_library_track_surfaces() -> None:
    for view in (
        "views/SongsView.qml",
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
        "views/AlbumDetailView.qml",
        "views/ArtistDetailView.qml",
    ):
        assert "playback.currentPath" in _text(view)


def test_premium_library_workspace_is_contextual_and_single_source() -> None:
    header = _text("views/LibraryHeader.qml")
    toolbar = _text("views/LibraryToolbar.qml")
    albums = _text("views/AlbumsView.qml")
    library = _text("views/LibraryView.qml")
    segmented = _text("controls/MichiSegmentedControl.qml")
    assert 'objectName: "albumViewSwitcher"' in header
    assert "albumViewsVisible" in header
    assert 'currentTab === "albums"' in header
    assert 'objectName: "albumViewSwitcher"' not in toolbar
    assert 'objectName: "stableLibrarySearchPane"' in toolbar
    assert "SplitView" not in toolbar
    assert "Layout.preferredWidth: 82" in toolbar
    assert toolbar.index("LibraryTabs {") < toolbar.index("MichiSearchField {")
    assert "compact: true" in header
    for icon in (
        "view-grid",
        "view-path",
        "view-vinyl",
        "view-timeline",
        "view-magazine",
        "view-list",
    ):
        assert f'icon: "{icon}"' in header
    assert "albumModeRequested" in header
    assert "MichiSegmentedControl {" not in albums
    assert "onAlbumModeRequested" in library
    assert "sourceComponent: root.componentForMode(root.loadedMode)" in albums
    assert "MichiMotion.viewExit" in albums
    assert "MichiMotion.viewEnter" in albums
    assert "root.currentValue = modelData.value" not in segmented


def test_precision_pass_uses_resizable_smoked_surfaces_without_accent_rules() -> None:
    shell = _text("shell/AppShell.qml")
    sidebar = _text("shell/Sidebar.qml")
    tabs = _text("views/LibraryTabs.qml")
    popup = _text("views/LibraryViewOptionsPopup.qml")
    bar = _text("player/NowPlayingBar.qml")
    glass = _text("primitives/MichiGlassSurface.qml")
    button = _text("controls/MichiButton.qml")
    icon_button = _text("controls/MichiIconButton.qml")
    assert 'objectName: "workspaceSplitView"' in shell
    assert 'objectName: "resizableSidebar"' in shell
    assert "SplitView.minimumWidth: MichiMetrics.sidebarCompact" in shell
    assert 'elevation: "elevated"' in sidebar
    # single grain: the glass surfaces texture (textured: true); the
    # sidebar must NOT stack its own MichiMaterialTexture on top
    assert "textured: true" in sidebar
    assert "MichiMaterialTexture" not in sidebar
    # true smoke glass: always-on blur, translucent smoked material,
    # single cyan accent (no purple chromatic noise)
    assert "forceBlur: true" in sidebar
    # sidebar texture follows the library toolbar treatment:
    # standard glass material (no translucency override, no ambient tint)
    assert "materialOpacityOverride" not in sidebar
    assert "contentAmbientBlue" not in sidebar
    assert "accentColor: MichiPalette.auroraCyan" in sidebar
    assert "contentAmbientPurple" not in sidebar
    assert "property bool accentLineVisible: false" in glass
    assert "root.accented && root.accentLineVisible" in glass
    assert "root.enabled && root.primary" in button
    assert "anchors.bottom: parent.bottom" not in tabs
    assert "visible: root.selected" not in icon_button
    assert "artworkSize" in popup
    assert "coverSize" in popup
    assert "sleeveSize" in popup
    quality = bar.split('objectName: "qualityBadge"', 1)[1].split(
        'objectName: "queueButton"', 1
    )[0]
    assert "width: 7" in quality
    assert "height: 7" in quality
    assert "GradientStop" not in quality


def test_audio_surfaces_share_a_semantic_table_header() -> None:
    assert (QML / "media" / "TrackTableHeader.qml").is_file()
    for view in (
        "views/SongsView.qml",
        "views/FavoritesView.qml",
        "views/HistoryView.qml",
        "views/RecentlyAddedView.qml",
        "views/AlbumDetailView.qml",
        "views/ArtistDetailView.qml",
    ):
        assert "TrackTableHeader" in _text(view)
    row = _text("media/TrackRow.qml")
    assert "showArtistColumn" in row
    assert "showAlbumColumn" in row
    assert "MichiSemanticColors.surfaceSelected" in row


def test_album_table_header_and_rows_share_responsive_columns() -> None:
    header = _text("media/AlbumTableHeader.qml")
    row = _text("media/MichiAlbumRow.qml")
    for source in (header, row):
        assert "titleColumnRatio" in source
        assert "titleColumnWidth" in source
        assert "artistColumnWidth" in source
        assert "Layout.minimumWidth: 150" in source


def test_queue_respects_the_player_and_quality_status_is_not_duplicated() -> None:
    shell = _text("shell/AppShell.qml")
    bar = _text("player/NowPlayingBar.qml")
    assert shell.count("anchors.bottom: nowPlayingBar.top") >= 2
    assert "Qt.rgba" not in bar
    assert "#" not in bar
    assert bar.count('objectName: "qualityBadge"') == 1
    assert "album: playback.album" in shell
    assert "root.qualityText()" in bar
    assert '"LOCAL · "' not in bar
    assert 'objectName: "outputStatusButton"' not in bar
    assert 'objectName: "deviceButton"' not in bar


def test_presentation_colors_are_owned_by_the_theme_layer() -> None:
    offenders = []
    for path in QML.rglob("*.qml"):
        if path.parent.name == "theme":
            continue
        source = path.read_text()
        if "Qt.rgba" in source or re.search(r'"#[0-9A-Fa-f]{6,8}"', source):
            offenders.append(str(path.relative_to(QML)))
    assert offenders == []
