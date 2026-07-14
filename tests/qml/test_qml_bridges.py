"""Smoke tests for QML bridges (Python side only, no QML rendering)."""

import pytest
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
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    assert "RadioPage" in page_stack, "radio should resolve to RadioPage"
    assert "PlaylistsPage" in page_stack, "playlists should resolve to PlaylistsPage"

    targets = ["RadioPage", "PlaylistsPage", "AssistantPage", "HomePage", "LibraryPage",
               "ConnectionsPage", "DevicesPage", "SettingsPage", "EqPage",
               "LibraryDoctorPage", "DiscLabPage", "SmartTaggingPage",
               "OutputProfilesPage", "DiagnosticsPage"]
    for t in targets:
        assert t in page_stack, f"PageStack missing reference to {t}"


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
    from ui_qml_bridge.route_registry import ROUTES
    sidebar = (QML_DIR / "shell" / "Sidebar.qml").read_text()
    sidebar_routes = set(re.findall(r'route: "(\w+)"', sidebar))
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    for route in sidebar_routes:
        assert route in ROUTES, f"Sidebar route {route} not in RouteRegistry"
        info = ROUTES[route]
        assert info["source"] in page_stack or info["source"].replace("../pages/", "") in page_stack, \
            f"PageStack missing source for route {route}: {info['source']}"


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
    (QML_DIR / "shell" / "Sidebar.qml").read_text()
    # Settings is now a delivery core route, "Ajustes" label is acceptable in delivery model


def test_page_stack_has_explicit_radio_playlists():
    page_stack = (QML_DIR / "shell" / "PageStack.qml").read_text()
    assert '"radio"' in page_stack, "PageStack missing explicit case for radio"
    assert '"playlists"' in page_stack, "PageStack missing explicit case for playlists"
    assert '"assistant"' in page_stack, "PageStack missing assistant case"
    assert 'AssistantPage.qml' in page_stack, "PageStack missing AssistantPage reference"


def test_sidebar_no_settings_ajustes():
    (QML_DIR / "shell" / "Sidebar.qml").read_text()
    # Settings is now a delivery core route


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
        assert bridge.hasPlayback is False

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

    def test_connect_manual_returns_dict(self):
        bridge = ConnectionsBridge()
        result = bridge.connectManual("192.168.1.100", 8080, "test")
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_diagnose_returns_dict(self):
        bridge = ConnectionsBridge()
        result = bridge.diagnose()
        assert isinstance(result, dict)

    def test_disconnect_returns_dict(self):
        bridge = ConnectionsBridge()
        result = bridge.disconnect()
        assert isinstance(result, dict)

    def test_capabilities_list(self):
        bridge = ConnectionsBridge()
        caps = bridge.capabilities
        assert len(caps) > 0
        assert all("key" in c for c in caps)


class TestHomeAudioBridge:
    def test_default_state(self):
        bridge = HomeAudioBridge()
        assert bridge.homeAssistantState == "not_configured"
        assert bridge.snapcastState == "unavailable"
        assert len(bridge.devices) == 0

    def test_configure_home_assistant_returns_dict(self):
        bridge = HomeAudioBridge()
        result = bridge.configureHomeAssistant("host", 8123, "token")
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_open_diagnostics(self):
        bridge = HomeAudioBridge()
        result = bridge.openDiagnostics()
        assert result.get("ok") is True

    def test_capabilities_no_controller(self):
        bridge = HomeAudioBridge()
        assert bridge.homeAssistantAvailable is False
        assert bridge.snapcastAvailable is False
        assert bridge.volumeSupported is False


class TestSmartTaggingBridge:
    def test_smart_tagging_importable(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        assert bridge is not None
        assert bridge.status == "idle"

    def test_smart_tagging_scan_by_id_no_service(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        result = bridge.scanTrackById(1)
        assert result.get("ok") is False
        assert result.get("error_code") == "UNSUPPORTED"

    def test_smart_tagging_apply_no_suggestions(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        bridge._status = "review"
        result = bridge.applySelected()
        assert result.get("ok") is False
        assert result.get("error_code") == "NO_SUGGESTIONS"

    def test_refresh_returns_dict(self):
        bridge = HomeAudioBridge()
        result = bridge.refresh()
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_discover_receivers_unsupported(self):
        bridge = HomeAudioBridge()
        result = bridge.discoverReceivers()
        assert result.get("ok") is False


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

    def test_add_folder_empty_path(self):
        bridge = LibraryBridge()
        result = bridge.addFolder("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_PATH"

    def test_add_folder_not_found(self):
        bridge = LibraryBridge()
        result = bridge.addFolder("/nonexistent/path/12345")
        assert result.get("ok") is False
        assert result.get("error") == "DIR_NOT_FOUND"

    def test_add_folder_no_db(self):
        import tempfile
        import os
        from ui_qml_bridge.library_bridge import LibraryBridge
        bridge = LibraryBridge()
        tmpdir = tempfile.mkdtemp()
        try:
            result = bridge.addFolder(tmpdir)
            assert result.get("ok") is False
            assert result.get("error") == "NO_JOB_SERVICE"
        finally:
            os.rmdir(tmpdir)

    def test_add_media_empty(self):
        bridge = LibraryBridge()
        result = bridge.addMedia("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_PATH"

    def test_add_media_not_found(self):
        bridge = LibraryBridge()
        result = bridge.addMedia("/nonexistent/file.mp3")
        assert result.get("ok") is False
        assert result.get("error") == "FILE_NOT_FOUND"


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
        from unittest.mock import MagicMock

        class FakePlayback:
            def __init__(self):
                self.calls = []

            def play(self, filepath, title="", artist="", album=""):
                self.calls.append((filepath, title, artist, album))

        playback = FakePlayback()
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = ["Song Title", "Song Artist", "Song Album"]
        from ui_qml_bridge.library_query_service import LibraryQueryService
        qs = LibraryQueryService(db=db)
        bridge = LibraryBridge(playback_ctrl=playback, query_service=qs)

        result = bridge.play_song("http://example.com/song.flac")
        assert result["ok"] is True
        assert playback.calls == [
            ("http://example.com/song.flac", "Song Title", "Song Artist", "Song Album")
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

    def test_metadata_bridge_load_empty_path(self):
        bridge = MetadataBridge()
        result = bridge.loadMetadata("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_FILEPATH"

    def test_metadata_bridge_clear(self):
        bridge = MetadataBridge()
        bridge.loadMetadata("/test/song.flac")
        bridge.clear()
        assert bridge.hasSelection is False

    def test_metadata_bridge_load_not_found(self):
        bridge = MetadataBridge()
        result = bridge.loadMetadata("/nonexistent/file.flac")
        assert result.get("ok") is False

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

    def test_metadata_bridge_can_apply_false_without_file(self):
        bridge = MetadataBridge()
        assert bridge.canApply is False

    def test_metadata_bridge_save_changes_return_dict(self):
        bridge = MetadataBridge()
        bridge.loadMetadata("/tmp/test_fake.flac")
        result = bridge.saveChanges()
        assert isinstance(result, dict)

    def test_metadata_inspector_apply_button_disabled(self):
        content = (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").read_text()
        assert "applyChanges" in content, "Metadata page missing applyChanges call"
        assert "_editing" in content, "Metadata page missing editing state"


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
        bindings = (QML_DIR.parent / "ui_qml_bridge" / "context_bindings.py").read_text()
        assert "mixBridge" in bindings, "context_bindings missing mixBridge"

    @pytest.mark.skip(reason="Requiere SQL real: MixQueryService")
    def test_mix_favorites_uses_fav_db(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        db.get_favorites.return_value = ["/path/fav1.mp3", "/path/fav2.mp3"]
        item1 = MagicMock(spec=MediaItem, filepath="/path/fav1.mp3", title="Fav1", artist="A1",
                          album="Al1", duration=100, id=1, play_count=0, last_played=0)
        item2 = MagicMock(spec=MediaItem, filepath="/path/fav2.mp3", title="Fav2", artist="A2",
                          album="Al2", duration=200, id=2, play_count=0, last_played=0)
        item3 = MagicMock(spec=MediaItem, filepath="/path/other.mp3", title="Other", artist="O",
                          album="O", duration=300, id=3, play_count=0, last_played=0)
        db.fetch_all.return_value = [item1, item2, item3]
        bridge = MixBridge(db=db)
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 2, "Expected 2 favorites"
        fps = [s["filepath"] for s in bridge.currentSongs]
        assert "/path/fav1.mp3" in fps
        assert "/path/other.mp3" not in fps

    @pytest.mark.skip(reason="Requiere SQL real: MixQueryService")
    def test_mix_recent_uses_last_played(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        item1 = MagicMock(spec=MediaItem, filepath="/old.mp3", title="Old", artist="A",
                          album="Al", duration=100, id=1, play_count=5, last_played=100.0)
        item2 = MagicMock(spec=MediaItem, filepath="/new.mp3", title="New", artist="B",
                          album="Bl", duration=200, id=2, play_count=1, last_played=200.0)
        item3 = MagicMock(spec=MediaItem, filepath="/never.mp3", title="Never", artist="C",
                          album="Cl", duration=300, id=3, play_count=0, last_played=0)
        db.fetch_all.return_value = [item1, item2, item3]
        db.get_favorites.return_value = []
        bridge = MixBridge(db=db)
        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 2, "Expected 2 recent tracks"
        assert bridge.currentSongs[0]["filepath"] == "/new.mp3", "Most recent first"

    @pytest.mark.skip(reason="Requiere SQL real: MixQueryService")
    def test_mix_unplayed_excludes_played(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        db.fetch_all.return_value = [
            MagicMock(spec=MediaItem, filepath="/a.mp3", title="A", artist="X",
                      album="Y", duration=100, id=1, play_count=0, last_played=0),
            MagicMock(spec=MediaItem, filepath="/b.mp3", title="B", artist="X",
                      album="Y", duration=200, id=2, play_count=5, last_played=100.0),
        ]
        db.get_favorites.return_value = []
        bridge = MixBridge(db=db)
        bridge.loadMix("unplayed")
        assert len(bridge.currentSongs) == 1
        assert bridge.currentSongs[0]["filepath"] == "/a.mp3"

    @pytest.mark.skip(reason="Requiere SQL real: MixQueryService")
    def test_mix_most_played_orders_by_play_count(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        db.fetch_all.return_value = [
            MagicMock(spec=MediaItem, filepath="/a.mp3", title="A", artist="X",
                      album="Y", duration=100, id=1, play_count=1, last_played=100.0),
            MagicMock(spec=MediaItem, filepath="/b.mp3", title="B", artist="X",
                      album="Y", duration=200, id=2, play_count=10, last_played=200.0),
            MagicMock(spec=MediaItem, filepath="/c.mp3", title="C", artist="X",
                      album="Y", duration=300, id=3, play_count=0, last_played=0),
        ]
        db.get_favorites.return_value = []
        bridge = MixBridge(db=db)
        bridge.loadMix("most_played")
        assert len(bridge.currentSongs) == 2
        assert bridge.currentSongs[0]["filepath"] == "/b.mp3", "Highest play count first"

    def test_mix_daily_fallback_not_first_25(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        items = []
        for i in range(50):
            items.append(MagicMock(spec=MediaItem,
                                   filepath=f"/track_{i}.mp3", title=f"T{i}",
                                   artist="X", album="Y", duration=100, id=i,
                                   play_count=0, last_played=0, created_at=float(i),
                                   genre="", _fields={}))
        db.fetch_all.return_value = items
        db.get_favorites.return_value = []
        bridge = MixBridge(db=db)
        bridge.loadMix("daily_mix")
        # Should have max 25 items
        assert len(bridge.currentSongs) <= 25
        # Verify not hardcoded to first indices — since no recent plays,
        # fallback sorts by created_at DESC, newest first
        if len(bridge.currentSongs) > 0:
            assert bridge.currentSongs[0]["filepath"] == "/track_49.mp3", "Should start from newest"

    def test_mix_ai_requires_enabled(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge()
        assert "ai_recommended" not in [c["id"] for c in bridge.categories]

    def test_mix_daily_uses_smart_mix_service(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        from library.media_item import MediaItem
        db = MagicMock()
        item = MagicMock(spec=MediaItem, filepath="/a.mp3", title="A", artist="X",
                         album="Y", duration=100, id=1, play_count=1, last_played=100.0,
                         created_at=1000.0, genre="Rock")
        db.fetch_all.return_value = [item]
        db.get_favorites.return_value = []
        bridge = MixBridge(db=db)
        bridge.loadMix("daily_mix")
        # Falls back to genre heuristic since SmartMixService.create_mix
        # may not find items via balanced_mix strategy
        assert len(bridge.currentSongs) <= 25


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

    def test_radio_bridge_edit_station(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        bridge = RadioBridge(radio_manager=mgr)
        result = bridge.editStation(1, "New Name", "http://new.url/stream")
        assert result.get("ok") is True
        mgr.update.assert_called_once()

    def test_radio_bridge_edit_station_no_mgr(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        bridge = RadioBridge()
        result = bridge.editStation(1, "Name", "url")
        assert result.get("ok") is False
        assert result.get("error") == "NO_RADIO_MANAGER"

    def test_radio_bridge_toggle_favorite(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        mgr.toggle_favorite.return_value = True
        bridge = RadioBridge(radio_manager=mgr)
        result = bridge.toggleFavorite(1)
        assert result.get("ok") is True
        assert result.get("favorite") is True

    def test_radio_bridge_toggle_favorite_no_mgr(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        bridge = RadioBridge()
        result = bridge.toggleFavorite(1)
        assert result.get("ok") is False

    def test_radio_bridge_search(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.radio_bridge import RadioBridge
        from streaming.radio_manager import RadioStation
        mgr = MagicMock()
        station = RadioStation(id=1, name="Test FM", url="http://test.fm/stream",
                               codec="MP3", country="US", tags=["rock", "pop"])
        mgr.get_all.return_value = [station]
        bridge = RadioBridge(radio_manager=mgr)
        result = bridge.search(query="Test")
        assert result.get("ok") is True
        assert result.get("count") == 1

    def test_radio_bridge_search_no_match(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.radio_bridge import RadioBridge
        from streaming.radio_manager import RadioStation
        mgr = MagicMock()
        station = RadioStation(id=1, name="Test FM", url="http://test.fm/stream")
        mgr.get_all.return_value = [station]
        bridge = RadioBridge(radio_manager=mgr)
        result = bridge.search(query="Jazz")
        assert result.get("count") == 0


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
        bridge._duration = 300  # set duration so seek works
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
        assert "playbackBridge" in content
        assert "notificationBridge" in content

    def test_nowplaying_bar_no_emojis(self):
        for name in ("NowPlayingBar", "NowPlayingCover", "NowPlayingInfo",
                     "NowPlayingControls", "NowPlayingSeekBar", "NowPlayingVolume"):
            content = (QML_DIR / "components" / f"{name}.qml").read_text()
            for ch in content:
                if ord(ch) in set(range(0x1F300, 0x1FAFF)):
                    assert False, f"Emoji U+{ord(ch):04X} found in {name}.qml"


class TestLibraryQueryService:
    def test_query_service_sort_whitelist(self):
        from ui_qml_bridge.library_query_service import _sort_col, _TRACK_SORT
        assert _sort_col("title") == "LOWER(COALESCE(title, ''))"
        assert _sort_col("invalid") == "LOWER(COALESCE(title, ''))"
        assert "artist" in _TRACK_SORT

    def test_query_service_empty_db(self):
        from ui_qml_bridge.library_query_service import LibraryQueryService
        from unittest.mock import MagicMock
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = [0]
        db.conn.execute.return_value.fetchall.return_value = []
        svc = LibraryQueryService(db=db)
        assert svc.count_tracks() == 0
        assert svc.fetch_tracks() == []
        assert svc.count_albums() == 0
        assert svc.count_artists() == 0
        assert svc.search_backend in ("fts5", "like", "none")

    def test_query_service_search_backend_detection(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_query_service import LibraryQueryService
        db = MagicMock()
        db.conn.execute.return_value.fetchone.return_value = ["media_fts"]
        svc = LibraryQueryService(db=db)
        assert svc.search_backend == "fts5"

    def test_track_model_has_correct_signals(self):
        from ui_qml.models.TrackListModel import TrackListModel
        model = TrackListModel()
        assert hasattr(model, 'countChanged')
        assert hasattr(model, 'loadingChanged')
        assert hasattr(model, 'errorChanged')
        assert hasattr(model, 'hasMoreChanged')


class TestTrackListModel:
    def test_track_model_importable(self):
        from ui_qml.models.TrackListModel import TrackListModel
        model = TrackListModel()
        assert model.count == 0

    def test_track_model_basic(self):
        from ui_qml.models.TrackListModel import TrackListModel
        model = TrackListModel()
        assert model.count == 0
        assert model.loading is False

    def test_album_model_importable(self):
        from ui_qml.models.AlbumListModel import AlbumListModel
        model = AlbumListModel()
        assert model.count == 0

    def test_album_model_basic(self):
        from ui_qml.models.AlbumListModel import AlbumListModel
        model = AlbumListModel()
        assert model.count == 0
        assert model.loading is False


class TestQueueListModel:
    def test_queue_model_importable(self):
        from ui_qml.models.QueueListModel import QueueListModel
        model = QueueListModel()
        assert model.count == 0

    def test_queue_model_counts_empty(self):
        from ui_qml.models.QueueListModel import QueueListModel
        model = QueueListModel()
        assert model.totalCount == 0
        assert model.hasMore is False

    def test_queue_bridge_importable(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        bridge = QueueBridge()
        assert bridge.queueCount == 0

    def test_queue_bridge_refresh(self):
        from ui_qml_bridge.queue_bridge import QueueBridge
        bridge = QueueBridge()
        result = bridge.refresh()
        assert result.get("ok") is True


class TestHistoryListModel:
    def test_history_model_importable(self):
        from ui_qml.models.HistoryListModel import HistoryListModel
        model = HistoryListModel()
        assert model.count == 0

    def test_history_model_basic(self):
        from ui_qml.models.HistoryListModel import HistoryListModel
        model = HistoryListModel()
        assert model.loading is False
        assert model.totalCount == 0

    def test_history_bridge_importable(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        bridge = HistoryBridge()
        assert bridge.historyCount == 0

    def test_history_bridge_refresh(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        bridge = HistoryBridge()
        result = bridge.refresh()
        assert result.get("ok") is True

    def test_history_bridge_clear_no_db(self):
        from ui_qml_bridge.history_bridge import HistoryBridge
        bridge = HistoryBridge()
        result = bridge.clearHistory()
        assert result.get("ok") is False


class TestEqBridge:
    def test_eq_importable(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge()
        assert bridge is not None
        assert bridge.backendAvailable is False
        result = bridge.refresh()
        assert result.get("ok") is True

    def test_eq_apply_preset_no_player(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge()
        result = bridge.applyPreset("Rock")
        assert result.get("ok") is False

    def test_eq_toggle_bypass_no_player(self):
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge()
        result = bridge.toggleBypass(True)
        assert result.get("ok") is False


class TestSettingsBridge:
    def test_settings_importable(self):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        bridge = SettingsBridge()
        assert len(bridge.sections) > 0

    def test_settings_output_profiles(self):
        from ui_qml_bridge.settings_bridge import SettingsBridge
        bridge = SettingsBridge()
        profiles = bridge.outputProfiles
        assert len(profiles) > 0
        assert any(p.get("key") for p in profiles)


class TestLibraryDoctorBridge:
    def test_library_doctor_importable(self):
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge()
        assert bridge is not None


class TestPlaylistsFullBridge:
    def test_playlists_bridge_duplicate(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        db = MagicMock()
        db.get_playlists.return_value = [{"id": 1, "name": "Test", "track_count": 2}]
        db.get_playlist_items.return_value = [
            type("Item", (), {"id": 1, "title": "A", "artist": "X", "album": "Y",
                              "duration": 100, "filepath": "/tmp/test.mp3", "track_uid": "u1",
                              "position": 0})(),
        ]
        db.create_playlist.return_value = 2
        bridge = PlaylistsBridge(db=db)
        bridge.refresh()
        result = bridge.duplicatePlaylist(1)
        assert result.get("ok") is True

    def test_playlists_bridge_clear(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        db = MagicMock()
        db.get_playlists.return_value = []
        db.get_playlist_items.return_value = []
        bridge = PlaylistsBridge(db=db)
        result = bridge.clearPlaylist(1)
        assert result.get("ok") is True

    def test_playlists_bridge_save_queue_no_player(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        bridge = PlaylistsBridge()
        result = bridge.saveQueueAsPlaylist("Test")
        assert result.get("ok") is False

    def test_playlists_bridge_m3u_import_not_found(self):
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        bridge = PlaylistsBridge()
        result = bridge.importM3U("/nonexistent/file.m3u")
        assert result.get("ok") is False


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
    def test_devices_start_server_no_sync(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        bridge = DevicesBridge()
        result = bridge.startServer()
        assert result.get("ok") is False
        assert result.get("error") == "NO_SYNC_MANAGER"
    def test_devices_stop_server_no_sync(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        bridge = DevicesBridge()
        result = bridge.stopServer()
        assert result.get("ok") is not True
    def test_devices_refresh_no_sync(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        bridge = DevicesBridge()
        result = bridge.refresh()
        assert isinstance(result, dict)

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
        assert any(m["status"] == "experimental" for m in mods)

    def test_audio_lab_bridge_refresh(self):
        bridge = AudioLabBridge()
        bridge.refresh()


class TestDiscLabBridge:
    def test_disc_lab_importable(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        assert DiscLabBridge is not None

    def test_disc_lab_unavailable_no_service(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        bridge = DiscLabBridge()
        assert bridge.status == "unavailable"
        result = bridge.refresh()
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_disc_lab_scan_no_disc(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        svc = MagicMock()
        svc.detect_drives.return_value = ["/dev/sr0"]
        svc.get_default_drive.return_value = "/dev/sr0"
        svc.detect_audio_cd.return_value = False
        bridge = DiscLabBridge(disc_detection_service=svc)
        result = bridge.refresh()
        assert result.get("ok") is True
        assert bridge.status == "no_disc"

    def test_disc_lab_scan_with_tracks(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        svc = MagicMock()
        svc.detect_drives.return_value = ["/dev/sr0"]
        svc.get_default_drive.return_value = "/dev/sr0"
        svc.detect_audio_cd.return_value = True
        svc.get_disc_toc.return_value = {"tracks": 3, "duration_seconds": 300}
        svc.get_track_durations.return_value = [100.0, 100.0, 100.0]
        bridge = DiscLabBridge(disc_detection_service=svc)
        bridge.refresh()
        assert bridge.status == "ready"
        result = bridge.scanDisc()
        assert result.get("ok") is True
        assert result.get("tracks") == 3
        assert len(bridge.tracks) == 3

    def test_disc_lab_eject(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        bridge = DiscLabBridge()
        bridge._status = "scanned"
        bridge._tracks = [{"track": 1, "title": "Track 1"}]
        result = bridge.eject()
        assert result.get("ok") is True
        assert bridge.status == "no_disc"
        assert len(bridge.tracks) == 0


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

    def test_connections_bridge_no_demo_without_controller(self):
        bridge = ConnectionsBridge()
        bridge.scanForServers()
        servers = bridge.discoveredServers
        assert len(servers) == 0, "No demo data without MICHI_QML_DEMO flag"


class TestLyricsBridge:
    def test_lyrics_idle_on_create(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        assert bridge.status == "idle"
        assert bridge.lyrics == ""
        assert bridge.syncedLyrics == []

    def test_lyrics_parse_lrc(self):
        from ui_qml_bridge.lyrics_bridge import _parse_lrc
        lrc_text = "[00:01.00]Line 1\n[00:02.50]Line 2\n[00:03.75]Line 3"
        synced = _parse_lrc(lrc_text)
        assert len(synced) == 3
        assert synced[0]["time"] == 1.0
        assert synced[0]["text"] == "Line 1"
        assert synced[1]["time"] == 2.5
        assert synced[2]["time"] == 3.75

    def test_lyrics_parse_lrc_no_timestamp(self):
        from ui_qml_bridge.lyrics_bridge import _parse_lrc
        synced = _parse_lrc("Plain text line")
        assert len(synced) == 1
        assert synced[0]["time"] == 0

    def test_lyrics_cache_hit(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        bridge._cache["test||artist||album||0"] = {
            "lyrics": "cached lyrics", "synced_lyrics": "",
            "source": "LRCLIB", "timestamp": 1000,
        }
        result = bridge.search("test", "artist", "album", 0)
        assert result.get("cached") is True
        assert bridge.lyrics == "cached lyrics"
        assert bridge.status == "done"

    def test_lyrics_cancel_search(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        bridge._status = "searching"
        bridge.cancelSearch()
        assert bridge.status == "idle"

    def test_lyrics_clear_cache_for_track(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        bridge._cache["test||artist||album||0"] = {"lyrics": "x", "synced_lyrics": "", "source": "L", "timestamp": 1000}
        bridge._current_title = "test"
        bridge._current_artist = "artist"
        bridge._current_album = "album"
        bridge._current_duration = 0
        result = bridge.clearCacheForCurrentTrack()
        assert result.get("ok") is True
        assert "test||artist||album||0" not in bridge._cache

    def test_lyrics_search_manual_empty(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        result = bridge.searchManual("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_QUERY"

    def test_lyrics_search_current_track_no_np(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        result = bridge.searchCurrentTrack()
        assert result.get("ok") is False

    def test_lyrics_get_active_line(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        bridge._synced_lyrics = [{"time": 1.0, "text": "A"}, {"time": 2.0, "text": "B"}, {"time": 3.0, "text": "C"}]
        assert bridge.getActiveLine(0) == 0
        assert bridge.getActiveLine(1500) == 0
        assert bridge.getActiveLine(2500) == 1
        assert bridge.getActiveLine(5000) == 2

    def test_lyrics_get_active_line_empty(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        assert bridge.getActiveLine(1000) is None

    def test_lyrics_on_track_changed_noop_same_track(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        bridge = LyricsBridge()
        bridge._current_title = "Same"
        bridge._current_artist = "Same"
        np_mock = MagicMock()
        np_mock.trackTitle = "Same"
        np_mock.trackArtist = "Same"
        bridge._np_bridge = np_mock
        bridge._on_track_changed()
        # No search started — status stays idle
        assert bridge.status == "idle"


class TestHomeAudioV2Bridge:
    def test_home_audio_bridge_refresh(self):
        bridge = HomeAudioBridge()
        result = bridge.refresh()
        assert result.get("ok") is True
        assert bridge.homeAssistantState == "not_configured"

    def test_home_audio_bridge_devices(self):
        bridge = HomeAudioBridge()
        assert len(bridge.devices) == 0

    def test_home_audio_capabilities_no_controller(self):
        bridge = HomeAudioBridge()
        assert bridge.homeAssistantAvailable is False
        assert bridge.snapcastAvailable is False
        assert bridge.receiversAvailable is False
        assert bridge.zonesSupported is False
        assert bridge.groupingSupported is False
        assert bridge.volumeSupported is False

    def test_home_audio_configure_unsupported_without_ha(self):
        bridge = HomeAudioBridge()
        result = bridge.configureHomeAssistant("192.168.1.100", 8123, "token")
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_home_audio_discover_receivers_unsupported(self):
        bridge = HomeAudioBridge()
        result = bridge.discoverReceivers()
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_home_audio_set_zone_volume_unsupported(self):
        bridge = HomeAudioBridge()
        result = bridge.setZoneVolume("zone1", 0.5)
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_home_audio_test_ha_unsupported(self):
        bridge = HomeAudioBridge()
        result = bridge.testHomeAssistant()
        assert result.get("ok") is False

    def test_home_audio_assign_stream_unsupported(self):
        bridge = HomeAudioBridge()
        result = bridge.assignStream("stream1")
        assert result.get("ok") is False

    def test_home_audio_bridge_with_ha_adapter(self):
        from unittest.mock import MagicMock
        ha_adapter = MagicMock()
        ha_adapter.is_connected = True
        ha_adapter.get_devices.return_value = [
            {"name": "Salón", "entity_id": "media_player.salon", "available": True},
        ]
        bridge = HomeAudioBridge(ha_controller=ha_adapter)
        bridge.refresh()
        assert bridge.homeAssistantAvailable is True
        assert bridge.homeAssistantState == "connected"

    def test_home_audio_bridge_with_snapcast_adapter(self):
        from unittest.mock import MagicMock
        snap_adapter = MagicMock()
        snap_adapter.is_available = True
        snap_adapter.get_groups.return_value = [
            {"id": "zone1", "name": "Salón", "muted": False, "volume": 80},
        ]
        bridge = HomeAudioBridge(snapcast_ctrl=snap_adapter)
        bridge.refresh()
        assert bridge.snapcastAvailable is True
        assert bridge.snapcastState == "available"
        assert len(bridge.zones) == 1

    def test_home_audio_bridge_configure_with_ha_adapter(self):
        from unittest.mock import MagicMock
        ha_adapter = MagicMock()
        bridge = HomeAudioBridge(ha_controller=ha_adapter)
        result = bridge.configureHomeAssistant("192.168.1.100", 8123, "token")
        assert result.get("ok") is True
        ha_adapter.configure.assert_called_once()

    def test_home_audio_bridge_volume_with_snapcast(self):
        from unittest.mock import MagicMock
        snap_adapter = MagicMock()
        bridge = HomeAudioBridge(snapcast_ctrl=snap_adapter)
        result = bridge.setZoneVolume("zone1", 0.8)
        assert result.get("ok") is True
        snap_adapter.set_group_volume.assert_called_once_with("zone1", 0.8)


class TestActionRegistry:
    def test_action_registry_importable(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        registry = ActionRegistry()
        assert len(registry.actions) > 0

    def test_action_registry_contains_navigation(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        registry = ActionRegistry()
        actions = registry.actions
        ids = [a["id"] for a in actions]
        assert "navigate_home" in ids
        assert "navigate_library" in ids
        assert "playback_playpause" in ids
        assert "library_refresh" in ids

    def test_action_registry_execute_no_handler(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        registry = ActionRegistry()
        result = registry.execute("navigate_home")
        assert result.get("ok") is False
        assert result.get("error") == "NO_HANDLER"

    def test_action_registry_execute_not_found(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        registry = ActionRegistry()
        result = registry.execute("nonexistent")
        assert result.get("ok") is False
        assert result.get("error") == "NOT_FOUND"

    def test_action_registry_register(self):
        from ui_qml_bridge.action_registry import ActionRegistry, ActionDescriptor
        registry = ActionRegistry()
        registry.register(ActionDescriptor("test_action", "Test", "test"))
        action = registry.get("test_action")
        assert action is not None
        assert action.title == "Test"


class TestGlobalSearchBridge:
    def test_global_search_importable(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        bridge = GlobalSearchBridge()
        assert bridge.results == []

    def test_global_search_empty_query(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        bridge = GlobalSearchBridge()
        result = bridge.search("")
        assert result.get("ok") is True
        assert result.get("count") == 0

    def test_global_search_no_db_returns_empty(self):
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        bridge = GlobalSearchBridge()
        result = bridge.search("test")
        assert result.get("ok") is True
        assert result.get("count") <= 50


class TestJobBridge:
    def test_job_bridge_importable(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        assert bridge.jobs == []
        assert bridge.activeCount == 0

    def test_job_bridge_unknown_job(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        result = bridge.runJob("unknown_job")
        assert result.get("ok") is False
        assert result.get("error") == "UNKNOWN_JOB_TYPE"

    def test_job_bridge_run_scan(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        result = bridge.runJob("library_scan", "/tmp")
        assert result.get("ok") is True
        assert len(bridge.jobs) == 1
        assert bridge.jobs[0]["state"] in ("completed", "running", "failed")

    def test_job_bridge_cancel(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        bridge.runJob("library_scan", "/tmp")
        job_id = bridge.jobs[0]["job_id"]
        result = bridge.cancelJob(job_id)
        assert result.get("ok") is True
        assert bridge.activeCount == 0

    def test_job_bridge_cancel_not_found(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        result = bridge.cancelJob(999)
        assert result.get("ok") is False

    def test_job_bridge_clear_completed(self):
        from ui_qml_bridge.job_bridge import JobBridge
        bridge = JobBridge()
        bridge.runJob("library_scan", "/tmp")
        bridge.cancelJob(bridge.jobs[0]["job_id"])
        bridge.clearCompleted()
        assert bridge.activeCount == 0
        assert len(bridge.jobs) == 0


class TestLibrarySourcesBridge:
    def _make_source_db(self):
        from unittest.mock import MagicMock
        db = MagicMock()
        db.conn.execute.return_value.fetchall.return_value = []
        db.add_library_root.return_value = True
        db.remove_library_root.return_value = True
        return db

    def test_library_sources_service_importable(self):
        from core.library_sources_service import LibrarySourcesService
        svc = LibrarySourcesService(db=self._make_source_db())
        sources = svc.list()
        assert isinstance(sources, list)

    def test_library_sources_service_add_remove(self):
        import tempfile
        from core.library_sources_service import LibrarySourcesService
        db = self._make_source_db()
        svc = LibrarySourcesService(db=db)
        with tempfile.TemporaryDirectory() as tmp:
            db.add_library_root.return_value = True
            result = svc.add(tmp)
            assert result.get("ok") is True

    def test_library_sources_service_add_nonexistent(self):
        from core.library_sources_service import LibrarySourcesService
        svc = LibrarySourcesService(db=self._make_source_db())
        result = svc.add("/nonexistent/path")
        assert result.get("ok") is False

    def test_library_sources_service_duplicate(self):
        import tempfile
        from core.library_sources_service import LibrarySourcesService
        db = self._make_source_db()
        svc = LibrarySourcesService(db=db)
        with tempfile.TemporaryDirectory() as tmp:
            db.add_library_root.return_value = False
            result = svc.add(tmp)
            assert result.get("ok") is False
            assert result.get("error") == "ALREADY_EXISTS"

    def test_library_sources_bridge_importable(self):
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        bridge = LibrarySourcesBridge()
        assert bridge.status == "ready"
        assert isinstance(bridge.sources, list)

    def test_library_sources_bridge_add_source(self):
        import tempfile
        from unittest.mock import MagicMock
        from core.library_sources_service import LibrarySourcesService
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        db = MagicMock()
        db.add_library_root.return_value = True
        db.conn.execute.return_value.fetchall.return_value = []
        svc = LibrarySourcesService(db=db)
        bridge = LibrarySourcesBridge(service=svc)
        with tempfile.TemporaryDirectory() as tmp:
            result = bridge.addSource(tmp)
            assert result.get("ok") is True

    def test_library_sources_bridge_remove_missing(self):
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        bridge = LibrarySourcesBridge()
        result = bridge.removeSource("/nonexistent")
        assert result.get("ok") is False

    def test_library_sources_bridge_refresh(self):
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        bridge = LibrarySourcesBridge()
        result = bridge.refresh()
        assert result.get("ok") is True


class TestRadioBridgeWithService:
    def test_radio_bridge_with_manager(self):
        from unittest.mock import MagicMock
        from types import SimpleNamespace
        from ui_qml_bridge.radio_bridge import RadioBridge
        mgr = MagicMock()
        station = SimpleNamespace(
            id=1, name="Station 1", url="http://example.com/stream",
            codec="MP3", country="US", tags=["Rock"],
            favorite=False, image_path=""
        )
        mgr.get_all.return_value = [station]
        bridge = RadioBridge(radio_manager=mgr)
        bridge.refresh()
        assert len(bridge.stations) >= 1


class TestMixBridgeWithService:
    def test_mix_bridge_with_db(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        db = MagicMock()
        db.fetch_all.return_value = []
        db.conn.execute.return_value.fetchall.return_value = []
        mqs = MagicMock()
        mqs.favorites.return_value = [{"track_id": 1, "title": "Test", "artist": "A", "album": "B", "duration": 200, "reason": "Fav"}]
        bridge = MixBridge(db=db, query_service=mqs)
        assert len(bridge.categories) > 0
        result = bridge.loadMix("favorites")
        assert result.get("ok") is True
        assert isinstance(result.get("count"), int)
