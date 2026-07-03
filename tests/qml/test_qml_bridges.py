"""Smoke tests for QML bridges (Python side only, no QML rendering)."""

from pathlib import Path
from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.command_bus import CommandBus
from ui_qml_bridge.theme_bridge import ThemeBridge
from ui_qml_bridge.home_bridge import HomeBridge
from ui_qml_bridge.connections_bridge import ConnectionsBridge
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge
from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
from ui_qml_bridge.metadata_bridge import MetadataBridge
from ui_qml_bridge.radio_bridge import RadioBridge
from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from ui_qml_bridge.settings_bridge import SettingsBridge


QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"


def test_qml_main_exists():
    assert (QML_DIR / "Main.qml").exists()


def test_michi_app_exists():
    assert (QML_DIR / "MichiApp.qml").exists()


def test_qmldir_exists():
    assert (QML_DIR / "qmldir").exists()


def test_theme_qmldir_exists():
    assert (QML_DIR / "theme" / "qmldir").exists()


def test_theme_files():
    for name in ("MichiColors", "MichiTypography", "MichiSpacing", "MichiMotion", "MichiTheme"):
        assert (QML_DIR / "theme" / f"{name}.qml").exists(), f"Missing theme file: {name}.qml"


def test_materials_files():
    for name in ("GlassMaterial", "HeroMaterial", "PopupMaterial", "SidebarMaterial", "InputMaterial", "AcrylicBackdrop"):
        assert (QML_DIR / "materials" / f"{name}.qml").exists(), f"Missing material: {name}.qml"


def test_components_files():
    for name in ("GlassPanel", "GlassCard", "HeroPanel", "MichiButton", "StatusBadge",
                 "EmptyState", "SearchField", "SidebarItem", "SectionHeader", "IconSlot",
                 "InspectorPanel", "DiscoveryResultCard"):
        assert (QML_DIR / "components" / f"{name}.qml").exists(), f"Missing component: {name}.qml"


def test_shell_files():
    for name in ("AppShell", "Sidebar", "HeaderBar", "PageStack", "RouteTransition"):
        assert (QML_DIR / "shell" / f"{name}.qml").exists(), f"Missing shell: {name}.qml"


def test_page_stack_contains_new_routes():
    import re
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    assert "RadioPage" in page_stack, "radio should resolve to RadioPage"
    assert "PlaylistsPage" in page_stack, "playlists should resolve to PlaylistsPage"

    cases = {
        "assistant": "../pages/assistant/AssistantPage.qml",
        "home": "../pages/home/HomePage.qml",
    }
    for route, expected in cases.items():
        assert re.search(rf'case "{route}":\s*return "{expected}"', page_stack), \
            f"PageStack missing {route} -> {expected}"


def test_page_stack_references_exist():
    import re
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    refs = re.findall(r'"([^"]+\.qml)"', page_stack)
    shell_dir = QML_DIR / "shell"
    for ref in refs:
        p = Path(ref)
        p = (shell_dir / ref).resolve() if not p.is_absolute() else p.resolve()
        if p.exists():
            continue
        rel = QML_DIR / ref.replace("../", "")
        assert rel.exists(), (
            f"PageStack references non-existent file: {ref}\n"
            f"  Tried: {p}\n  Tried: {rel}"
        )


def test_qml_files_have_no_emoji_icons():
    import unicodedata
    emoji_codepoints = set()
    for cp in range(0x1F300, 0x1FAFF):
        try:
            cat = unicodedata.category(chr(cp))
        except ValueError:
            continue
        if cat in ("So", "Cn"):
            emoji_codepoints.add(cp)
    for cp in range(0x2600, 0x27BF):
        try:
            cat = unicodedata.category(chr(cp))
        except ValueError:
            continue
        if cat == "So":
            emoji_codepoints.add(cp)
    known_non_emoji = {0x2609, 0x2605, 0x2606, 0x2610, 0x2611, 0x2660,
                       0x2663, 0x2665, 0x2666, 0x2702, 0x2708, 0x2713,
                       0x2714, 0x2716, 0x2728, 0x2744}
    emoji_codepoints -= known_non_emoji

    for qml_file in sorted(QML_DIR.rglob("*.qml")):
        content = qml_file.read_text(encoding="utf-8", errors="ignore")
        for ch in content:
            cp = ord(ch)
            if cp in emoji_codepoints:
                assert False, (
                    f"Emoji U+{cp:04X} ({ch}) found in "
                    f"{qml_file.relative_to(QML_DIR)}"
                )


def test_app_shell_titles_match_sidebar_routes():
    import re
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    appshell = (QML_DIR / "shell" / "AppShell.qml").read_text()

    sidebar_routes = set(re.findall(r'route: "(\w+)"', sidebar))
    appshell_routes = set(re.findall(r'"(\w+)":\s*"', appshell))

    internal_routes = {"nowplaying", "metadata_inspector", "mix_detail", "settings", "devices", "playlist_detail", "eq", "library_doctor", "disc_lab", "output_profiles", "smart_tagging"}
    sidebar_only = sidebar_routes - appshell_routes
    appshell_only = (appshell_routes - sidebar_routes) - internal_routes

    assert not sidebar_only, (
        f"Sidebar routes missing from AppShell titles: {sidebar_only}"
    )
    assert not appshell_only, (
        f"AppShell titles without sidebar route: {appshell_only}"
    )


def test_sidebar_has_no_forbidden_routes():
    import re
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    forbidden = {"genres", "ecosystem"}
    routes = set(re.findall(r'route: "(\w+)"', sidebar))
    found = routes & forbidden
    assert not found, f"Forbidden sidebar routes found: {found}"


def test_sidebar_contains_radio_and_playlists():
    import re
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    routes = set(re.findall(r'route: "(\w+)"', sidebar))
    assert "radio" in routes, "Sidebar missing 'radio' route"
    assert "playlists" in routes, "Sidebar missing 'playlists' route"


def test_sidebar_uses_michi_ai_label():
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    assert "Michi AI" in sidebar, "Sidebar missing 'Michi AI' label"
    assert "Asistente" not in sidebar, "Sidebar contains 'Asistente' label (use 'Michi AI')"


def test_sidebar_contains_reproduccion_label():
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    assert "Reproducción" in sidebar, "Sidebar missing 'Reproducción' label (with tilde)"
    assert "Reproduccion" not in sidebar, "Sidebar contains 'Reproduccion' without tilde"


def test_sidebar_has_no_ajustes():
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    assert "Ajustes" not in sidebar, "Sidebar still contains 'Ajustes' label"
    assert "settings" not in sidebar, "Sidebar still contains 'settings' route"


def test_page_stack_has_explicit_radio_playlists():
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    assert 'case "radio":' in page_stack, "PageStack missing explicit case for radio"
    assert 'case "playlists":' in page_stack, "PageStack missing explicit case for playlists"
    assert 'case "assistant":' in page_stack, "PageStack missing assistant case"
    assert 'AssistantPage.qml' in page_stack, "PageStack missing AssistantPage reference"


def test_sidebar_no_settings_ajustes():
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    assert "settings" not in sidebar, "Sidebar still contains 'settings' route"
    assert "Ajustes" not in sidebar, "Sidebar still contains 'Ajustes' label"


def test_sidebar_has_no_emoji_glyphs():
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    emoji_ranges = set(range(0x1F300, 0x1FAFF)) | set(range(0x2600, 0x27BF))
    safe = {0x2609, 0x2605, 0x2606, 0x2610, 0x2611, 0x2660, 0x2663, 0x2665, 0x2666}
    emoji_ranges -= safe
    for ch in sidebar:
        if ord(ch) in emoji_ranges:
            assert False, f"Emoji U+{ord(ch):04X} found in Sidebar.qml"


def test_context_menu_has_no_emojis():
    import re
    window_path = Path(__file__).resolve().parent.parent.parent / "ui" / "window.py"
    content = window_path.read_text()
    menu_items = re.findall(r'menu\.addAction\("([^"]+)"\)', content)
    for item in menu_items:
        for ch in item:
            if ord(ch) > 127 and ord(ch) not in range(0x00C0, 0x02FF):
                assert False, f"Non-ASCII/emoji in menu action: '{item}' (char U+{ord(ch):04X})"


def test_qml_main_importable():
    import importlib
    mod = importlib.import_module("ui_qml_bridge.qml_main")
    assert hasattr(mod, "main")


class TestAppBridge:
    def test_instantiate(self):
        bridge = AppBridge()
        assert bridge.appName == "Michi Music Player"
        # Version comes from importlib.metadata, fallback to 0.2.0-alpha.1
        assert bridge.version
        assert bridge.experimentalQml is True

    def test_quit_slot(self):
        bridge = AppBridge()
        assert hasattr(bridge, 'quit')


class TestNavigationBridge:
    def test_default_route(self):
        bridge = NavigationBridge()
        assert bridge.currentRoute == "home"

    def test_navigate_changes_route(self):
        bridge = NavigationBridge()
        bridge.navigate("connections")
        assert bridge.currentRoute == "connections"

    def test_same_route_no_change(self):
        bridge = NavigationBridge()
        bridge.navigate("home")
        assert bridge.currentRoute == "home"

    def test_empty_route_falls_back(self):
        bridge = NavigationBridge()
        bridge.navigate("")
        assert bridge.currentRoute == "home"

    def test_invalid_route_falls_back(self):
        bridge = NavigationBridge()
        bridge.navigate("nonexistent_route")
        assert bridge.currentRoute == "placeholder"

    def test_navigate_slot(self):
        bridge = NavigationBridge()
        assert hasattr(bridge, 'navigate')

    def test_navigate_radio_works(self):
        bridge = NavigationBridge()
        bridge.navigate("radio")
        assert bridge.currentRoute == "radio"

    def test_navigate_playlists_works(self):
        bridge = NavigationBridge()
        bridge.navigate("playlists")
        assert bridge.currentRoute == "playlists"

    def test_navigate_assistant_works(self):
        bridge = NavigationBridge()
        bridge.navigate("assistant")
        assert bridge.currentRoute == "assistant"

    def test_navigate_settings_falls_to_placeholder(self):
        bridge = NavigationBridge()
        bridge.navigate("settings")
        assert bridge.currentRoute == "settings", "settings should be a valid route now"

    def test_navigate_michi_ai_falls_to_placeholder(self):
        bridge = NavigationBridge()
        bridge.navigate("michi_ai")
        assert bridge.currentRoute == "placeholder", "michi_ai is not a valid route"


class TestCommandBus:
    def test_instantiate(self):
        bus = CommandBus()
        assert bus is not None

    def test_execute_does_not_crash(self):
        bus = CommandBus()
        bus.execute("navigate", {"route": "home"})


class TestThemeBridge:
    def test_default_dark(self):
        bridge = ThemeBridge()
        assert bridge.darkMode is True

    def test_set_light(self):
        bridge = ThemeBridge()
        bridge.darkMode = False
        assert bridge.darkMode is False

    def test_set_dark(self):
        bridge = ThemeBridge()
        bridge.darkMode = True
        assert bridge.darkMode is True


class TestHomeBridge:
    def test_default_stats(self):
        bridge = HomeBridge()
        assert bridge.libraryAlbums == 0
        assert bridge.libraryArtists == 0
        assert bridge.libraryTracks == 0
        assert bridge.microServerState == "not_configured"

    def test_set_library_stats(self):
        bridge = HomeBridge()
        bridge.set_library_stats(10, 5, 100)
        assert bridge.libraryAlbums == 10
        assert bridge.libraryArtists == 5
        assert bridge.libraryTracks == 100

    def test_refresh_does_not_crash(self):
        bridge = HomeBridge()
        bridge.refresh()

    def test_set_library_stats_slot(self):
        bridge = HomeBridge()
        assert hasattr(bridge, 'set_library_stats')


class TestConnectionsBridge:
    def test_default_state(self):
        bridge = ConnectionsBridge()
        assert bridge.microServerState == "not_configured"

    def test_scan_for_servers(self):
        bridge = ConnectionsBridge()
        bridge.scanForServers()
        assert bridge.microServerState == "not_configured"

    def test_add_manual_server(self):
        bridge = ConnectionsBridge()
        bridge.addManualServer()

    def test_scan_slot(self):
        bridge = ConnectionsBridge()
        assert hasattr(bridge, 'scanForServers')


class TestHomeAudioBridge:
    def test_default_state(self):
        bridge = HomeAudioBridge()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.streamState == "concept"
        assert len(bridge.devices) == 0

    def test_configure_home_assistant(self):
        bridge = HomeAudioBridge()
        bridge.configureHomeAssistant()

    def test_open_diagnostics(self):
        bridge = HomeAudioBridge()
        bridge.openDiagnostics()

    def test_open_stream_concept(self):
        bridge = HomeAudioBridge()
        bridge.openStreamConcept()

    def test_slots_exist(self):
        bridge = HomeAudioBridge()
        assert hasattr(bridge, 'configureHomeAssistant')
        assert hasattr(bridge, 'openDiagnostics')
        assert hasattr(bridge, 'openStreamConcept')


class TestLibraryBridge:
    def test_instantiate(self):
        bridge = LibraryBridge()
        assert bridge is not None

    def test_default_counts(self):
        bridge = LibraryBridge()
        assert bridge.songCount == 0
        assert bridge.albumCount == 0

    def test_refresh_does_not_crash(self):
        bridge = LibraryBridge()
        bridge.refresh()


class TestMichiAIBridge:
    def test_instantiate(self):
        bridge = MichiAIBridge()
        assert bridge is not None

    def test_refresh_does_not_crash(self):
        bridge = MichiAIBridge()
        bridge.refresh()

    def test_send_message_returns_response(self):
        bridge = MichiAIBridge()
        bridge.sendMessage("hola")
        history = bridge.getChatHistory()
        assert "hola" in history
        assert "assistant" in history

    def test_suggestions_after_refresh(self):
        bridge = MichiAIBridge()
        bridge.refresh()
        assert len(bridge.suggestions) > 0


class TestLibraryBridgeContract:
    def test_importable_without_db(self):
        bridge = LibraryBridge()
        assert bridge is not None
        assert bridge.songCount == 0
        assert bridge.albumCount == 0

    def test_songs_property_returns_list(self):
        bridge = LibraryBridge()
        songs = bridge.songs
        assert isinstance(songs, list)

    def test_albums_property_returns_list(self):
        bridge = LibraryBridge()
        albums = bridge.albums
        assert isinstance(albums, list)

    def test_refresh_does_not_crash_without_db(self):
        bridge = LibraryBridge()
        bridge.refresh()

    def test_play_song_delegates_to_player_service_with_metadata(self):
        from types import SimpleNamespace

        class FakePlayback:
            def __init__(self):
                self.calls = []

            def play(self, filepath, title="", artist="", album=""):
                self.calls.append((filepath, title, artist, album))

        playback = FakePlayback()
        bridge = LibraryBridge(playback_ctrl=playback)
        bridge._songs = [
            SimpleNamespace(
                filepath="/music/song.flac",
                title="Song Title",
                artist="Song Artist",
                album="Song Album",
            )
        ]

        bridge.play_song("/music/song.flac")

        assert playback.calls == [
            ("/music/song.flac", "Song Title", "Song Artist", "Song Album")
        ]


class TestAlbumGrid:
    def test_album_grid_qml_exists(self):
        assert (QML_DIR / "pages" / "library" / "AlbumGrid.qml").exists()

    def test_album_grid_uses_cover_bridge(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "CoverImage" in content, "AlbumCard does not use CoverImage"
        proxy = (QML_DIR / "components" / "CoverBridgeProxy.qml").read_text()
        assert "CoverBridge" in proxy, "CoverBridgeProxy does not wrap CoverBridge"

    def test_album_grid_no_emoji(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        for ch in content:
            if ord(ch) in set(range(0x1F300, 0x1FAFF)):
                assert False, f"Emoji found in AlbumCard.qml: U+{ord(ch):04X}"


class TestSongTable:
    def test_song_table_qml_exists(self):
        assert (QML_DIR / "pages" / "library" / "SongTable.qml").exists()

    def test_song_table_structure(self):
        content = (QML_DIR / "pages" / "library" / "SongTable.qml").read_text()
        assert "songPlayRequested" in content
        assert "SongRow" in content


class TestCoverBridge:
    def test_cover_bridge_importable(self):
        from ui_qml_bridge.cover_bridge import CoverBridge
        assert CoverBridge is not None

    def test_cover_bridge_has_paint(self):
        from ui_qml_bridge.cover_bridge import CoverBridge
        assert hasattr(CoverBridge, 'paint')

    def test_cover_bridge_cover_key_property(self):
        from ui_qml_bridge.cover_bridge import CoverBridge
        assert hasattr(CoverBridge, 'coverKey')

    def test_album_card_uses_cover_bridge(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "CoverImage" in content, "AlbumCard does not use CoverImage"
        proxy = (QML_DIR / "components" / "CoverBridgeProxy.qml").read_text()
        assert "CoverBridge" in proxy, "CoverBridgeProxy does not wrap CoverBridge"

    def test_album_card_no_image_provider(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "michi-cover" not in content, "AlbumCard still uses old image provider"

    def test_album_card_no_parent_source(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "parent.source" not in content, "AlbumCard uses parent.source (deprecated)"
        assert "parent.status" not in content, "AlbumCard uses parent.status (deprecated)"

    def test_cover_bridge_no_bare_except_pass(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "cover_bridge.py").read_text()
        assert "except Exception:\n        pass" not in content, (
            "cover_bridge.py has bare except:pass"
        )

    def test_cover_bridge_uses_qt_enums(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "cover_bridge.py").read_text()
        assert "Qt.AspectRatioMode" in content or "Qt.KeepAspectRatio" in content, (
            "cover_bridge.py missing Qt aspect ratio enum"
        )
        assert "Qt.SmoothTransformation" in content or "Qt.FastTransformation" in content, (
            "cover_bridge.py missing Qt transformation enum"
        )

    def test_cover_bridge_has_cache_limit(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "cover_bridge.py").read_text()
        assert "_MAX_CACHE" in content, "cover_bridge.py missing _MAX_CACHE constant"
        assert "_trim_cache" in content, "cover_bridge.py missing _trim_cache function"

    def test_qml_main_registers_cover_bridge(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "qml_main.py").read_text()
        assert "qmlRegisterType(CoverBridge" in content, (
            "qml_main.py does not register CoverBridge"
        )
        assert "MichiCover" in content, (
            "qml_main.py missing MichiCover import in qmlRegisterType"
        )
        assert "register_image_provider" not in content, (
            "qml_main.py still calls register_image_provider (dead code)"
        )

    def test_cover_bridge_paint_no_db_load(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "cover_bridge.py").read_text()
        paint_body = content[content.find("def paint"):]
        paint_body = paint_body[:paint_body.find("\n    def ") if "\n    def " in paint_body else len(paint_body)]
        assert "_load_cover_image" not in paint_body, (
            "paint() still calls _load_cover_image (should be in setter)"
        )

    def test_cover_bridge_docstring_honest(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "cover_bridge.py").read_text()
        docstring = content.split('"""')[1] if '"""' in content else ""
        assert "paint()" in docstring, "docstring missing paint() contract"
        assert "NO heavy work" in docstring, (
            "docstring should state paint() does no heavy work"
        )

    def test_no_broadcast_files_in_this_branch(self):
        import subprocess
        result = subprocess.run(
            ["git", "ls-tree", "-r", "HEAD", "--name-only"],
            capture_output=True, text=True, check=True,
        )
        files = result.stdout.split("\n")
        forbidden = [f for f in files if "broadcast" in f or "podcast" in f]
        assert not forbidden, f"Broadcast/podcast files found in branch: {forbidden}"

    def test_sidebar_no_genres(self):
        content = (QML_DIR / "shell" / "Sidebar.qml").read_text()
        assert "genres" not in content, "Sidebar contains 'genres' route"
        assert "Géneros" not in content, "Sidebar contains 'Géneros' label"

    def test_navigation_bridge_rejects_genres(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("genres")
        assert bridge.currentRoute == "placeholder", "genres should fall to placeholder"

    def test_page_stack_no_genres(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "genres" not in content, "PageStack contains 'genres' case"

    def test_app_shell_no_genres_title(self):
        content = (QML_DIR / "shell" / "AppShell.qml").read_text()
        assert "genres" not in content, "AppShell contains 'genres' title"
        assert "Géneros" not in content, "AppShell contains 'Géneros' title"


class TestMetadataBridge:
    def test_metadata_bridge_exists(self):
        assert MetadataBridge is not None

    def test_metadata_bridge_properties(self):
        bridge = MetadataBridge()
        assert bridge.hasSelection is False
        assert bridge.isLoading is False
        assert bridge.canApply is False
        assert bridge.errorMessage == ""

    def test_metadata_bridge_inspect(self):
        bridge = MetadataBridge()
        bridge.inspectTrack("/test/song.flac")
        assert bridge.hasSelection is True

    def test_metadata_bridge_clear(self):
        bridge = MetadataBridge()
        bridge.inspectTrack("/test/song.flac")
        bridge.clear()
        assert bridge.hasSelection is False

    def test_metadata_bridge_preview_no_write(self):
        bridge = MetadataBridge()
        bridge.previewSuggestedFixes()
        # should not crash, should not write

    def test_metadata_inspector_page_exists(self):
        assert (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").exists()

    def test_metadata_field_row_exists(self):
        assert (QML_DIR / "pages" / "metadata" / "MetadataFieldRow.qml").exists()

    def test_metadata_artwork_preview_exists(self):
        assert (QML_DIR / "pages" / "metadata" / "MetadataArtworkPreview.qml").exists()

    def test_navigation_bridge_accepts_metadata_inspector(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("metadata_inspector")
        assert bridge.currentRoute == "metadata_inspector"

    def test_navigation_bridge_rejects_nowplaying(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("nowplaying")
        assert bridge.currentRoute == "placeholder", "nowplaying should fall to placeholder"

    def test_no_nowplaying_page_in_qml_clean(self):
        assert not (QML_DIR / "pages" / "NowPlayingPage.qml").exists(), (
            "NowPlayingPage.qml should not exist in qml-migration-foundation-clean"
        )

    def test_metadata_bridge_can_apply_false_without_selection(self):
        bridge = MetadataBridge()
        assert bridge.canApply is False

    def test_metadata_bridge_can_apply_true_with_selection(self):
        bridge = MetadataBridge()
        bridge.inspectTrack("/tmp/test_fake.flac")
        assert bridge.canApply is True

    def test_metadata_bridge_apply_changes_has_slot(self):
        bridge = MetadataBridge()
        assert hasattr(bridge, 'applyChanges')

    def test_metadata_inspector_apply_button_disabled(self):
        content = (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").read_text()
        assert "enabled:" in content, "Apply button missing enabled state"
        assert "canApply" in content, "Apply button must use canApply property"


class TestLibraryComponents:
    def test_artist_card_exists(self):
        assert (QML_DIR / "pages" / "library" / "ArtistCard.qml").exists()

    def test_artist_list_exists(self):
        assert (QML_DIR / "pages" / "library" / "ArtistList.qml").exists()

    def test_artist_detail_page_exists(self):
        assert (QML_DIR / "pages" / "library" / "ArtistDetailPage.qml").exists()

    def test_album_detail_page_exists(self):
        assert (QML_DIR / "pages" / "library" / "AlbumDetailPage.qml").exists()

    def test_folder_browser_exists(self):
        assert (QML_DIR / "pages" / "library" / "FolderBrowser.qml").exists()

    def test_library_page_has_artists_tab(self):
        content = (QML_DIR / "pages" / "library" / "LibraryPage.qml").read_text()
        assert "Artistas" in content, "LibraryPage missing Artists tab"

    def test_library_page_has_folders_tab(self):
        content = (QML_DIR / "pages" / "library" / "LibraryPage.qml").read_text()
        assert "Carpetas" in content, "LibraryPage missing Folders tab"

    def test_library_bridge_has_artists_property(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        assert hasattr(bridge, 'artists'), "LibraryBridge missing artists property"

    def test_library_bridge_has_folders_property(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        assert hasattr(bridge, 'folders'), "LibraryBridge missing folders property"

    def test_library_bridge_has_filter_methods(self):
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        assert hasattr(bridge, 'filterByArtist'), "LibraryBridge missing filterByArtist"
        assert hasattr(bridge, 'filterByAlbum'), "LibraryBridge missing filterByAlbum"
        assert hasattr(bridge, 'clearFilters'), "LibraryBridge missing clearFilters"
        assert hasattr(bridge, 'sortBy'), "LibraryBridge missing sortBy"

    def test_folder_browser_no_emojis(self):
        content = (QML_DIR / "pages" / "library" / "FolderBrowser.qml").read_text()
        assert "📁" not in content, "FolderBrowser contains emoji"

    def test_album_grid_has_album_clicked_signal(self):
        content = (QML_DIR / "pages" / "library" / "AlbumGrid.qml").read_text()
        assert "albumClicked" in content, "AlbumGrid missing albumClicked signal"


class TestMixComponents:
    def test_mix_bridge_importable(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        assert MixBridge is not None

    def test_mix_bridge_has_categories(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge()
        cats = bridge.categories
        assert len(cats) > 0, "MixBridge has no categories"
        assert any(c["id"] == "daily_mix" for c in cats), "Missing daily_mix"

    def test_mix_bridge_load_mix(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge()
        bridge.loadMix("favorites")
        assert bridge.currentMixTitle == "Favoritos"

    def test_mix_hub_page_exists(self):
        assert (QML_DIR / "pages" / "MixHubPage.qml").exists()

    def test_mix_detail_page_exists(self):
        assert (QML_DIR / "pages" / "MixDetailPage.qml").exists()

    def test_mix_detail_route_in_navigation(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("mix_detail")
        assert bridge.currentRoute == "mix_detail", "mix_detail route should be valid"

    def test_mix_detail_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "mix_detail" in content, "PageStack missing mix_detail case"

    def test_qml_main_registers_mix_bridge(self):
        content = (QML_DIR.parent / "ui_qml_bridge" / "qml_main.py").read_text()
        assert "MixBridge" in content, "qml_main missing MixBridge import"
        assert "mixBridge" in content, "qml_main missing mixBridge context property"


class TestPlaybackComponents:
    def test_playback_bridge_importable(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        assert PlaybackBridge is not None

    def test_playback_page_exists(self):
        assert (QML_DIR / "pages" / "PlaybackPage.qml").exists()

    def test_playback_bridge_has_properties(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        bridge = PlaybackBridge()
        assert bridge.isPlaying is False
        assert bridge.volume == 80


class TestRadioComponents:
    def test_radio_page_exists(self):
        assert (QML_DIR / "pages" / "RadioPage.qml").exists()

    def test_radio_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "RadioPage" in content, "PageStack missing RadioPage"


class TestSettingsComponents:
    def test_settings_page_exists(self):
        assert (QML_DIR / "pages" / "SettingsPage.qml").exists()

    def test_settings_route_in_navigation(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("settings")
        assert bridge.currentRoute == "settings", "settings should be valid route"

    def test_settings_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "SettingsPage" in content, "PageStack missing SettingsPage"


class TestNowPlayingBar:
    def test_nowplaying_bar_exists(self):
        assert (QML_DIR / "components" / "NowPlayingBar.qml").exists()

    def test_nowplaying_cover_exists(self):
        assert (QML_DIR / "components" / "NowPlayingCover.qml").exists()

    def test_nowplaying_info_exists(self):
        assert (QML_DIR / "components" / "NowPlayingInfo.qml").exists()

    def test_nowplaying_controls_exists(self):
        assert (QML_DIR / "components" / "NowPlayingControls.qml").exists()

    def test_nowplaying_seekbar_exists(self):
        assert (QML_DIR / "components" / "NowPlayingSeekBar.qml").exists()

    def test_nowplaying_volume_exists(self):
        assert (QML_DIR / "components" / "NowPlayingVolume.qml").exists()

    def test_appshell_has_nowplaying(self):
        content = (QML_DIR / "shell" / "AppShell.qml").read_text()
        assert "NowPlayingBar" in content, "AppShell missing NowPlayingBar"

    def test_nowplaying_bridge_importable(self):
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
        assert NowPlayingBridge is not None

    def test_nowplaying_bridge_mirrors_player_signals(self):
        from PySide6.QtCore import QObject, Signal
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

        class FakePlayer(QObject):
            track_changed = Signal(str, str)
            state_changed = Signal(str)
            position_changed = Signal(float)
            duration_changed = Signal(float)
            volume_changed = Signal(int)
            queue_changed = Signal(list)

            @property
            def current(self):
                return "/music/track.flac"

            @property
            def state(self):
                return "stopped"

            @property
            def duration(self):
                return 0

            def get_queue(self):
                return []

        player = FakePlayer()
        bridge = NowPlayingBridge(player_service=player)

        player.track_changed.emit("A Song", "An Artist")
        player.state_changed.emit("playing")
        player.position_changed.emit(42.0)
        player.duration_changed.emit(180.0)
        player.volume_changed.emit(55)
        player.queue_changed.emit([{"title": "A Song", "artist": "An Artist"}])

        assert bridge.trackTitle == "A Song"
        assert bridge.trackArtist == "An Artist"
        assert bridge.isPlaying is True
        assert bridge.position == 42
        assert bridge.duration == 180
        assert bridge.volume == 55
        assert bridge.coverPath.startswith("track_")
        assert bridge.queue[0]["title"] == "A Song"

    def test_nowplaying_bridge_reads_current_track_object(self):
        from types import SimpleNamespace
        from PySide6.QtCore import QObject, Signal
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

        class FakePlayer(QObject):
            track_changed = Signal(str, str)
            state_changed = Signal(str)
            position_changed = Signal(float)
            duration_changed = Signal(float)
            volume_changed = Signal(int)
            queue_changed = Signal(list)

            @property
            def current(self):
                return SimpleNamespace(
                    filepath="/music/object-track.flac",
                    title="Object Song",
                    artist="Object Artist",
                    album="Object Album",
                )

            @property
            def state(self):
                return "playing"

            @property
            def duration(self):
                return 240

            def get_queue(self):
                return []

        bridge = NowPlayingBridge(player_service=FakePlayer())

        assert bridge.trackTitle == "Object Song"
        assert bridge.trackArtist == "Object Artist"
        assert bridge.trackAlbum == "Object Album"
        assert bridge.coverPath == "track_c79b4c2b8e46"
        assert bridge.hasTrack is True

    def test_nowplaying_bridge_commands_call_player_service(self):
        from PySide6.QtCore import QObject, Signal
        from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

        class FakePlayer(QObject):
            track_changed = Signal(str, str)
            state_changed = Signal(str)
            position_changed = Signal(float)
            duration_changed = Signal(float)
            volume_changed = Signal(int)
            queue_changed = Signal(list)

            def __init__(self):
                super().__init__()
                self.calls = []

            @property
            def current(self):
                return ""

            @property
            def state(self):
                return "stopped"

            @property
            def duration(self):
                return 0

            def get_queue(self):
                return []

            def play_or_resume(self):
                self.calls.append(("play_or_resume",))

            def pause(self):
                self.calls.append(("pause",))

            def play_next(self):
                self.calls.append(("play_next",))

            def play_prev(self):
                self.calls.append(("play_prev",))

            def seek(self, position):
                self.calls.append(("seek", position))

            def set_volume(self, volume):
                self.calls.append(("set_volume", volume))

            def toggle_shuffle(self):
                self.calls.append(("toggle_shuffle",))
                return True

            def toggle_repeat(self):
                self.calls.append(("toggle_repeat",))
                return "all"

        player = FakePlayer()
        bridge = NowPlayingBridge(player_service=player)

        bridge.togglePlay()
        bridge.next()
        bridge.previous()
        bridge.seek(30)
        bridge.setVolume(65)
        bridge.toggleShuffle()
        bridge.toggleRepeat()
        bridge._on_state("playing")
        bridge.togglePlay()

        assert ("play_or_resume",) in player.calls
        assert ("play_next",) in player.calls
        assert ("play_prev",) in player.calls
        assert ("seek", 30) in player.calls
        assert ("set_volume", 65) in player.calls
        assert ("toggle_shuffle",) in player.calls
        assert ("toggle_repeat",) in player.calls
        assert ("pause",) in player.calls
        assert bridge.shuffleEnabled is True
        assert bridge.repeatMode == "all"

    def test_playback_bridge_has_nowplaying_props(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        bridge = PlaybackBridge()
        assert hasattr(bridge, 'coverPath')
        assert hasattr(bridge, 'sourceType')
        assert hasattr(bridge, 'qualityLabel')
        assert hasattr(bridge, 'repeatMode')
        assert hasattr(bridge, 'shuffleEnabled')

    def test_playback_bridge_advanced_slots(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        bridge = PlaybackBridge()
        assert hasattr(bridge, 'toggleShuffle')
        assert hasattr(bridge, 'toggleRepeat')
        assert hasattr(bridge, 'seekRelative')

    def test_nowplaying_bar_uses_nowplaying_bridge_first(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "nowplayingBridge" in content
        assert "playbackState" in content
        assert "? nowplayingBridge" in content

    def test_nowplaying_bar_no_emojis(self):
        for name in ("NowPlayingBar", "NowPlayingCover", "NowPlayingInfo",
                     "NowPlayingControls", "NowPlayingSeekBar", "NowPlayingVolume"):
            content = (QML_DIR / "components" / f"{name}.qml").read_text()
            for ch in content:
                if ord(ch) in set(range(0x1F300, 0x1FAFF)):
                    assert False, f"Emoji U+{ord(ch):04X} found in {name}.qml"


class TestDevicesComponents:
    def test_devices_page_exists(self):
        assert (QML_DIR / "pages" / "DevicesPage.qml").exists()
    def test_device_card_exists(self):
        assert (QML_DIR / "pages" / "devices" / "DeviceCard.qml").exists()
    def test_sync_status_panel_exists(self):
        assert (QML_DIR / "pages" / "devices" / "SyncStatusPanel.qml").exists()
    def test_devices_bridge_importable(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        assert DevicesBridge is not None
    def test_devices_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "DevicesPage" in content

class TestPlaylistsComponents:
    def test_playlists_page_real_exists(self):
        assert (QML_DIR / "pages" / "playlists" / "PlaylistsPage.qml").exists()
    def test_playlist_card_exists(self):
        assert (QML_DIR / "pages" / "playlists" / "PlaylistCard.qml").exists()
    def test_playlist_detail_page_exists(self):
        assert (QML_DIR / "pages" / "playlists" / "PlaylistDetailPage.qml").exists()
    def test_playlists_bridge_importable(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        assert PlaylistsBridge is not None
    def test_playlists_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "PlaylistsPage" in content
    def test_playlist_detail_route_in_pagestack(self):
        content = (QML_DIR / "shell" / "PageStack.qml").read_text()
        assert "PlaylistDetailPage" in content

class TestContextMenu:
    def test_song_context_menu_exists(self):
        assert (QML_DIR / "components" / "SongContextMenu.qml").exists()


class TestRadioBridgeIntegration:
    def test_radio_bridge_importable(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert RadioBridge is not None

    def test_radio_bridge_refresh(self):
        bridge = RadioBridge()
        bridge.refresh()
        # Without a real RadioManager, stations should be empty
        assert len(bridge.stations) == 0

    def test_radio_bridge_has_slots(self):
        bridge = RadioBridge()
        assert hasattr(bridge, 'addStation')
        assert hasattr(bridge, 'playStation')
        assert hasattr(bridge, 'deleteStation')


class TestAudioLabIntegration:
    def test_audio_lab_bridge_importable(self):
        from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
        assert AudioLabBridge is not None

    def test_audio_lab_bridge_modules(self):
        bridge = AudioLabBridge()
        mods = bridge.modules
        assert len(mods) > 0
        assert any(m["id"] == "diagnostics" for m in mods)

    def test_audio_lab_bridge_refresh(self):
        bridge = AudioLabBridge()
        bridge.refresh()


class TestSettingsBridgeIntegration:
    def test_settings_bridge_importable(self):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        assert SettingsBridge is not None

    def test_settings_bridge_sections(self):
        bridge = SettingsBridge()
        secs = bridge.sections
        assert len(secs) > 0
        assert any(s["id"] == "general" for s in secs)


class TestConnectionsV2Bridge:
    def test_connections_bridge_refresh(self):
        bridge = ConnectionsBridge()
        bridge.refresh()
        assert bridge.microServerState == "not_configured"

    def test_connections_bridge_scan(self):
        bridge = ConnectionsBridge()
        bridge.scanForServers()
        # Without demo data and without a real controller, should return empty
        assert len(bridge.discoveredServers) == 0

    def test_connections_bridge_demo_flag(self):
        import os
        os.environ["MICHI_QML_DEMO"] = "1"
        try:
            bridge = ConnectionsBridge()
            bridge.scanForServers()
            servers = bridge.discoveredServers
            assert len(servers) > 0
            for s in servers:
                assert s.get("is_demo") is True
        finally:
            os.environ.pop("MICHI_QML_DEMO", None)


class TestHomeAudioV2Bridge:
    def test_home_audio_bridge_refresh(self):
        bridge = HomeAudioBridge()
        bridge.refresh()
        assert bridge.homeAssistantState == "not_configured"

    def test_home_audio_bridge_devices(self):
        bridge = HomeAudioBridge()
        assert len(bridge.devices) == 0
