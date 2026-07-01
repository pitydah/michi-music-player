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
    for name in ("GlassPanel", "GlassCard", "HeroPanel", "ActionButton", "StatusBadge",
                 "EmptyState", "SearchField", "SidebarItem", "SectionHeader", "IconSlot",
                 "InspectorPanel", "DiscoveryResultCard"):
        assert (QML_DIR / "components" / f"{name}.qml").exists(), f"Missing component: {name}.qml"


def test_shell_files():
    for name in ("AppShell", "Sidebar", "HeaderBar", "PageStack", "RouteTransition"):
        assert (QML_DIR / "shell" / f"{name}.qml").exists(), f"Missing shell: {name}.qml"


def test_page_stack_contains_new_routes():
    import re
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    assert "radio" not in page_stack or "PlaceholderPage" in page_stack, \
        "radio routes should resolve to PlaceholderPage"
    assert "playlists" not in page_stack or "PlaceholderPage" in page_stack, \
        "playlists routes should resolve to PlaceholderPage"

    cases = {
        "assistant": "../pages/assistant/AssistantPage.qml",
        "home": "../pages/home/HomePage.qml",
    }
    for route, expected in cases.items():
        assert re.search(rf'case "{route}":\s*return "{expected}"', page_stack), \
            f"PageStack missing {route} -> {expected}"

    assert "settings" not in page_stack, "PageStack still references 'settings'"


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

    sidebar_only = sidebar_routes - appshell_routes
    appshell_only = appshell_routes - sidebar_routes

    assert not sidebar_only, (
        f"Sidebar routes missing from AppShell titles: {sidebar_only}"
    )
    assert not appshell_only, (
        f"AppShell titles without sidebar route: {appshell_only}"
    )


def test_sidebar_has_no_forbidden_routes():
    import re
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    forbidden = {"genres", "ecosystem", "settings"}
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
    assert 'case "settings":' not in page_stack, "PageStack still has settings case"
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
        assert bridge.version == "0.1.0-qml"
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
        assert bridge.currentRoute == "placeholder", "settings should fall to placeholder"

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
        assert bridge.receiverCount == 0

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


class TestImageProvider:
    def test_register_function_exists(self):
        from ui_qml_bridge.image_provider import register_image_provider
        assert callable(register_image_provider)


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


class TestAlbumGrid:
    def test_album_grid_qml_exists(self):
        assert (QML_DIR / "pages" / "library" / "AlbumGrid.qml").exists()

    def test_album_grid_uses_cover_bridge(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "CoverBridge" in content, "AlbumCard does not use CoverBridge"

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
        assert "CoverBridge" in content, "AlbumCard does not use CoverBridge"

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



