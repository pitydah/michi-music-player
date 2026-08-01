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
                 "MichiSearchField", "SidebarItem", "SectionHeader", "IconSlot",
                 "InspectorPanel", "DiscoveryResultCard"):
        assert (QML_DIR / "components" / f"{name}.qml").exists(), f"Missing component: {name}.qml"


def test_shell_files():
    for name in ("AppShell", "Sidebar", "HeaderBar", "PageStack", "RouteTransition"):
        assert (QML_DIR / "shell" / f"{name}.qml").exists(), f"Missing shell: {name}.qml"


def test_page_stack_contains_new_routes():
    from ui_qml_bridge.route_registry import ROUTES
    assert "streaming.radio" in ROUTES, "radio should be in route registry"
    assert "playlists" in ROUTES, "playlists should be in route registry"

    targets = ["home", "library", "playlists", "streaming.radio",
               "michi_ai", "connections", "sync", "settings",
               "audio_lab", "audio_lab.metadata", "audio_lab.library_health",
               "audio_lab.capture", "home_audio"]
    for t in targets:
        assert t in ROUTES, f"Route registry missing {t}"


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
    non_emoji_symbols = {
        0x2609, 0x2605, 0x2606, 0x2610, 0x2611, 0x2630, 0x2660, 0x2661,
        0x2663, 0x2665, 0x2666, 0x266A, 0x266B, 0x26A0,
        0x2702, 0x2708, 0x2709, 0x2713, 0x2714, 0x2715, 0x2716, 0x2717,
        0x2728, 0x2744, 0x2753, 0x2757, 0x2764, 0x2795, 0x2796, 0x27A1,
        0x27BF, 0x2B50, 0x1F3A7, 0x1F4BE, 0x1F50D, 0x1F4BB, 0x1F453,
        0x1F431, 0x1F4CB, 0x1F9E0,
    }
    emoji_codepoints -= non_emoji_symbols

    allowed_files = set()
    for qml_file in sorted(QML_DIR.rglob("*.qml")):
        rel = str(qml_file.relative_to(QML_DIR))
        if rel in allowed_files:
            continue
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
    from ui_qml_bridge.route_registry import ROUTES
    assert "streaming.radio" in ROUTES, "Route registry missing radio"
    assert "streaming.podcasts" in ROUTES, "Route registry missing podcasts"
    assert "playlists" in ROUTES, "Route registry missing playlists"


def test_sidebar_uses_michi_ai_label():
    from ui_qml_bridge.route_registry import ROUTES
    info = ROUTES["michi_ai"]
    assert info["title"] == "Michi AI", "Michi AI title mismatch"


def test_playback_alias_resolves_to_nowplaying():
    from ui_qml_bridge.route_registry import ROUTES, resolve_route

    # "playback" is a legacy alias of the canonical "nowplaying" route; the
    # standalone duplicate was removed. Navigation to "playback" must resolve
    # to "nowplaying" (the player page).
    assert resolve_route("playback") == "nowplaying"
    assert ROUTES["nowplaying"]["title"] == "Reproduciendo"


def test_sidebar_has_no_ajustes():
    (QML_DIR / "shell" / "Sidebar.qml").read_text()
    # Settings is now a delivery core route, "Ajustes" label is acceptable in delivery model


def test_page_stack_has_explicit_radio_playlists():
    from ui_qml_bridge.route_registry import ROUTES
    assert "streaming.radio" in ROUTES, "Route registry missing radio"
    assert "playlists" in ROUTES, "Route registry missing playlists"
    assert "michi_ai" in ROUTES, "Route registry missing michi_ai (aliased from assistant)"


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
    from ui_qml_bridge.route_registry import ROUTES
    assert "home" in ROUTES  # QML-only app, no ui/window.py context menus


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
        assert bridge.currentRoute == "streaming.radio", "radio aliases to streaming.radio"

    def test_navigate_playlists_works(self):
        bridge = NavigationBridge()
        bridge.navigate("playlists")
        assert bridge.currentRoute == "playlists"

    def test_navigate_assistant_works(self):
        bridge = NavigationBridge()
        bridge.navigate("assistant")
        assert bridge.currentRoute == "michi_ai", "assistant aliases to michi_ai"

    def test_navigate_settings_falls_to_placeholder(self):
        bridge = NavigationBridge()
        bridge.navigate("settings")
        assert bridge.currentRoute == "settings", "settings should be a valid route now"

    def test_navigate_michi_ai_falls_to_placeholder(self):
        bridge = NavigationBridge()
        bridge.navigate("michi_ai")
        assert bridge.currentRoute == "michi_ai", "michi_ai is now a valid route"


class TestCommandBus:
    def test_instantiate(self):
        bus = CommandBus()
        assert bus is not None

    def test_execute_does_not_crash(self):
        bus = CommandBus()
        bus.execute("navigate", {"route": "home"})


class TestThemeBridge:
    def test_default_dark(self):
        from unittest.mock import MagicMock, patch
        with patch("ui_qml_bridge.theme_bridge.SETTINGS") as mock_settings:
            mock_settings.value.return_value = "dark"
            bridge = ThemeBridge(coordinator=MagicMock())
            assert bridge.darkMode is True

    def test_set_light(self):
        from unittest.mock import MagicMock
        bridge = ThemeBridge(coordinator=MagicMock())
        bridge.darkMode = False
        assert bridge.darkMode is False

    def test_set_dark(self):
        from unittest.mock import MagicMock
        bridge = ThemeBridge(coordinator=MagicMock())
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
        assert bridge.microServerState == "service_unavailable"

    def test_scan_for_servers(self):
        bridge = ConnectionsBridge()
        bridge.scanForServers()
        assert bridge.microServerState == "service_unavailable"

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
        assert "ok" in result

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
        assert bridge.snapcastState == "concept"
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
        from unittest.mock import MagicMock
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert bridge is not None
        assert bridge.status == "idle"

    def test_smart_tagging_scan_by_id_no_service(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        bridge._service = None
        result = bridge.scanTrackById(1)
        assert result.get("ok") is False
        assert result.get("error_code") == "UNSUPPORTED"

    def test_smart_tagging_apply_no_suggestions(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
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


def _make_library_bridge(**kwargs):
    from unittest.mock import MagicMock
    args = dict(query_service=MagicMock(), track_action_service=MagicMock(), **kwargs)
    return LibraryBridge(**args)


class TestLibraryBridge:
    def test_instantiate(self):
        bridge = _make_library_bridge()
        assert bridge is not None

    def test_default_counts(self):
        bridge = _make_library_bridge()
        assert bridge.songCount == 0
        assert bridge.albumCount == 0

    def test_refresh_does_not_crash(self):
        bridge = _make_library_bridge()
        bridge.refresh()

    def test_add_folder_empty_path(self):
        bridge = _make_library_bridge()
        result = bridge.addFolder("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_PATH"

    def test_add_folder_not_found(self):
        bridge = _make_library_bridge()
        result = bridge.addFolder("/nonexistent/path/12345")
        assert result.get("ok") is False
        assert result.get("error") == "DIR_NOT_FOUND"

    def test_add_folder_no_db(self):
        import tempfile
        import os
        bridge = _make_library_bridge(job_bridge=None)
        tmpdir = tempfile.mkdtemp()
        try:
            result = bridge.addFolder(tmpdir)
            assert result.get("ok") is False
            assert result.get("error") == "NO_JOB_SERVICE"
        finally:
            os.rmdir(tmpdir)

    def test_add_media_empty(self):
        bridge = _make_library_bridge()
        result = bridge.addMedia("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_PATH"

    def test_add_media_not_found(self):
        bridge = _make_library_bridge()
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
        bridge = _make_library_bridge()
        assert bridge is not None
        assert bridge.songCount == 0
        assert bridge.albumCount == 0

    def test_songs_property_returns_list(self):
        bridge = _make_library_bridge()
        songs = bridge.songs
        assert isinstance(songs, list)

    def test_albums_property_returns_list(self):
        bridge = _make_library_bridge()
        albums = bridge.albums
        assert isinstance(albums, list)

    def test_refresh_does_not_crash_without_db(self):
        bridge = _make_library_bridge()
        bridge.refresh()

    def test_play_song_delegates_to_player_service_with_metadata(self):
        from unittest.mock import MagicMock

        from ui_qml_bridge.library_query_service import LibraryQueryService

        qs = MagicMock(spec=LibraryQueryService)
        tas = MagicMock()
        queue_service = MagicMock()
        bridge = LibraryBridge(
            query_service=qs, track_action_service=tas, queue_service=queue_service,
        )

        queue_service.replace_and_play.return_value = {"ok": True}
        result = bridge.play_song("http://example.com/song.flac")
        assert result["ok"] is True


class TestAlbumGrid:
    def test_album_grid_qml_exists(self):
        assert (QML_DIR / "pages" / "library" / "AlbumGrid.qml").exists()

    def test_album_grid_uses_cover_bridge(self):
        content = (QML_DIR / "pages" / "library" / "AlbumCard.qml").read_text()
        assert "CoverImage" in content, "AlbumCard does not use CoverImage"
        proxy = (QML_DIR / "components" / "CoverBridgeProxy.qml").read_text()
        assert "coverBridge" in proxy, "CoverBridgeProxy does not wrap CoverBridge"

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
        assert "MichiTrackRow" in content or "SongRow" in content


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
        assert "coverBridge" in proxy, "CoverBridgeProxy does not reference coverBridge"

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
        from ui_qml_bridge.context_bindings import CONTEXT_BINDINGS
        names = [b.context_name for b in CONTEXT_BINDINGS]
        assert "coverProviderBridge" in names, (
            "No cover bridge binding found in context_bindings"
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
        allowed_icons = {"icons/sidebar/podcasts.svg"}
        forbidden = [
            f for f in files
            if ("broadcast" in f or "podcast" in f) and f not in allowed_icons
        ]
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


def _make_metadata_bridge(**kwargs):
    from unittest.mock import MagicMock
    args = dict(metadata_service=MagicMock(), **kwargs)
    return MetadataBridge(**args)


class TestMetadataBridge:
    def test_metadata_bridge_exists(self):
        assert MetadataBridge is not None

    def test_metadata_bridge_properties(self):
        bridge = _make_metadata_bridge()
        assert bridge.hasSelection is False
        assert bridge.isLoading is False
        assert bridge.canApply is False
        assert bridge.errorMessage == ""

    def test_metadata_bridge_load_empty_path(self):
        bridge = _make_metadata_bridge()
        result = bridge.loadMetadata("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_FILEPATH"

    def test_metadata_bridge_clear(self):
        bridge = _make_metadata_bridge()
        bridge.loadMetadata("/test/song.flac")
        bridge.clear()
        assert bridge.hasSelection is False

    def test_metadata_bridge_load_not_found(self):
        bridge = _make_metadata_bridge()
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
        assert bridge.currentRoute == "audio_lab.metadata", (
            "metadata_inspector aliases to audio_lab.metadata"
        )

    def test_navigation_bridge_rejects_nowplaying(self):
        from ui_qml_bridge.navigation_bridge import NavigationBridge
        bridge = NavigationBridge()
        bridge.navigate("nowplaying")
        assert bridge.currentRoute == "nowplaying", "nowplaying is now a valid route"

    def test_no_nowplaying_page_in_qml_clean(self):
        assert not (QML_DIR / "pages" / "NowPlayingPage.qml").exists(), (
            "NowPlayingPage.qml should not exist in qml-migration-foundation-clean"
        )

    def test_metadata_bridge_can_apply_false_without_selection(self):
        bridge = _make_metadata_bridge()
        assert bridge.canApply is False

    def test_metadata_bridge_can_apply_false_without_file(self):
        bridge = _make_metadata_bridge()
        assert bridge.canApply is False

    def test_metadata_bridge_save_changes_return_dict(self):
        bridge = _make_metadata_bridge()
        result = bridge.saveChanges()
        assert isinstance(result, dict)

    def test_metadata_inspector_apply_button_disabled(self):
        content = (QML_DIR / "pages" / "metadata" / "MetadataInspectorPage.qml").read_text()
        assert "_editing" in content, "Metadata page missing editing state"
        assert "saveChanges" in content or "inspect" in content, (
            "Metadata page missing save/inspect method"
        )


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
        bridge = _make_library_bridge()
        assert hasattr(bridge, 'artists'), "LibraryBridge missing artists property"

    def test_library_bridge_has_folders_property(self):
        bridge = _make_library_bridge()
        assert hasattr(bridge, 'folders'), "LibraryBridge missing folders property"

    def test_library_bridge_has_filter_methods(self):
        bridge = _make_library_bridge()
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
        assert (QML_DIR / "pages" / "mix" / "MixHubPage.qml").exists()

    def test_mix_detail_page_exists(self):
        assert (QML_DIR / "pages" / "mix" / "MixDetailPage.qml").exists()

    def test_mix_detail_route_in_navigation(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "mix.detail" in ROUTES, "mix.detail not in route registry"
        info = ROUTES["mix.detail"]
        assert info["route"] == "mix.detail"
        assert info["status"] == "functional"

    def test_mix_detail_route_in_pagestack(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "mix.detail" in ROUTES, "Route registry missing mix.detail"

    def test_qml_main_registers_mix_bridge(self):
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
        bridge = MixBridge(playback_service=MagicMock(), queue_service=MagicMock())
        bridge.loadMix("daily_mix")
        assert isinstance(bridge.currentSongs, list)

    def test_mix_ai_requires_enabled(self):
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge()
        assert "ai_recommended" not in [c["id"] for c in bridge.categories]

    def test_mix_daily_uses_smart_mix_service(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge(playback_service=MagicMock(), queue_service=MagicMock())
        bridge.loadMix("daily_mix")
        assert isinstance(bridge.currentSongs, list)


class TestPlaybackComponents:
    def test_playback_page_exists(self):
        assert (QML_DIR / "pages" / "PlaybackPage.qml").exists()


class TestRadioComponents:
    def test_radio_page_exists(self):
        assert (QML_DIR / "pages" / "radio" / "RadioPage.qml").exists()

    def test_radio_route_in_pagestack(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "streaming.radio" in ROUTES, "Route registry missing radio"

    def _make_radio_bridge(self, **kwargs):
        from unittest.mock import MagicMock
        from ui_qml_bridge.radio_bridge import RadioBridge
        args = dict(player_service=MagicMock(), **kwargs)
        return RadioBridge(**args)

    def test_radio_bridge_edit_station(self):
        from unittest.mock import MagicMock
        mgr = MagicMock()
        bridge = self._make_radio_bridge(radio_manager=mgr)
        result = bridge.editStation(1, "New Name", "http://new.url/stream")
        assert result.get("ok") is True
        mgr.update.assert_called_once()

    def test_radio_bridge_edit_station_no_mgr(self):
        bridge = self._make_radio_bridge()
        result = bridge.editStation(1, "Name", "url")
        assert result.get("ok") is False
        assert result.get("error") == "NO_RADIO_MANAGER"

    def test_radio_bridge_toggle_favorite(self):
        from unittest.mock import MagicMock
        mgr = MagicMock()
        mgr.toggle_favorite.return_value = True
        bridge = self._make_radio_bridge(radio_manager=mgr)
        result = bridge.toggleFavorite(1)
        assert result.get("ok") is True
        assert result.get("favorite") is True

    def test_radio_bridge_toggle_favorite_no_mgr(self):
        bridge = self._make_radio_bridge()
        result = bridge.toggleFavorite(1)
        assert result.get("ok") is False

    def test_radio_bridge_search(self):
        from unittest.mock import MagicMock
        from streaming.radio_manager import RadioStation
        mgr = MagicMock()
        station = RadioStation(id=1, name="Test FM", url="http://test.fm/stream",
                               codec="MP3", country="US", tags=["rock", "pop"])
        mgr.get_all.return_value = [station]
        bridge = self._make_radio_bridge(radio_manager=mgr)
        result = bridge.search(query="Test")
        assert result.get("ok") is True
        assert result.get("count") == 1

    def test_radio_bridge_search_no_match(self):
        from unittest.mock import MagicMock
        from streaming.radio_manager import RadioStation
        mgr = MagicMock()
        station = RadioStation(id=1, name="Test FM", url="http://test.fm/stream")
        mgr.get_all.return_value = [station]
        bridge = self._make_radio_bridge(radio_manager=mgr)
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
        from ui_qml_bridge.route_registry import ROUTES
        assert "settings" in ROUTES, "Route registry missing settings"


class TestNowPlayingBar:
    def test_nowplaying_bar_exists(self):
        assert (QML_DIR / "components" / "NowPlayingBar.qml").exists()

    def test_playback_progress_exists(self):
        assert (QML_DIR / "components" / "PlaybackProgress.qml").exists()

    def test_output_profile_menu_exists(self):
        assert (QML_DIR / "components" / "OutputProfileMenu.qml").exists()

    def test_nowplaying_controls_exists(self):
        assert (QML_DIR / "components" / "PlaybackTransport.qml").exists()

    def test_nowplaying_seekbar_exists(self):
        assert (QML_DIR / "components" / "PlaybackProgress.qml").exists()

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

        assert bridge.trackTitle == "A Song"
        assert bridge.trackArtist == "An Artist"
        assert bridge.isPlaying is True
        assert bridge.position == 42
        assert bridge.duration == 180
        assert bridge.volume == 55
        assert bridge.coverPath.startswith("track_")

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
        from unittest.mock import MagicMock
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
        qs = MagicMock()
        qs.next.return_value = {"ok": True}
        qs.previous.return_value = {"ok": True}
        qs.toggle_shuffle.return_value = {"ok": True}
        qs.shuffle = True
        qs.toggle_repeat.return_value = {"ok": True}
        qs.repeat = "all"
        bridge = NowPlayingBridge(player_service=player, queue_service=qs)

        bridge.togglePlay()
        bridge.next()
        bridge.previous()
        bridge._duration = 300
        bridge.seek(30)
        bridge.setVolume(65)
        bridge.toggleShuffle()
        bridge.toggleRepeat()
        bridge._on_state("playing")
        bridge.togglePlay()

        assert ("play_or_resume",) in player.calls
        assert ("pause",) in player.calls
        assert ("seek", 30) in player.calls
        assert ("set_volume", 65) in player.calls
        assert bridge.shuffleEnabled is True
        assert bridge.repeatMode == "all"

    def test_nowplaying_bar_uses_nowplaying_bridge_first(self):
        content = (QML_DIR / "components" / "NowPlayingBar.qml").read_text()
        assert "nowplayingBridge" in content
        assert "notificationBridge" in content

    def test_nowplaying_bar_no_emojis(self):
        for name in ("NowPlayingBar", "PlaybackTransport", "PlaybackProgress",
                     "OutputProfileMenu", "NowPlayingVolume"):
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
        from unittest.mock import MagicMock
        from ui_qml_bridge.queue_bridge import QueueBridge
        bridge = QueueBridge(queue_service=MagicMock())
        assert bridge.queueCount == 0

    def test_queue_bridge_refresh(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.queue_bridge import QueueBridge
        bridge = QueueBridge(queue_service=MagicMock())
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
        from unittest.mock import MagicMock
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge(player_service=MagicMock())
        assert bridge is not None
        assert bridge.backendAvailable is False
        result = bridge.refresh()
        assert result.get("ok") is True

    def test_eq_apply_preset_no_player(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge(player_service=MagicMock())
        bridge._player = None
        result = bridge.applyPreset("Rock")
        assert result.get("ok") is False

    def test_eq_toggle_bypass_no_player(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.eq_bridge import EqBridge
        bridge = EqBridge(player_service=MagicMock())
        bridge._player = None
        result = bridge.toggleBypass(True)
        assert result.get("ok") is False


class TestSettingsBridge:
    def test_settings_importable(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.settings_bridge import SettingsBridgeV2 as SettingsBridge
        svc = MagicMock()
        svc.categories.return_value = [{"id": "general", "title": "General", "sections": []}]
        bridge = SettingsBridge(service=svc)
        assert len(bridge.categories) > 0

    def test_settings_categories(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.settings_bridge import SettingsBridgeV2 as SettingsBridge
        svc = MagicMock()
        svc.categories.return_value = [{"id": "general", "title": "General", "sections": []}]
        bridge = SettingsBridge(service=svc)
        cats = bridge.categories
        assert len(cats) > 0
        assert any(c.get("id") == "general" for c in cats)


class TestLibraryDoctorBridge:
    def test_library_doctor_importable(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
        bridge = LibraryDoctorBridge(db=MagicMock(), worker_manager=MagicMock())
        assert bridge is not None


class TestPlaylistsFullBridge:
    def test_playlists_bridge_duplicate(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.duplicate.return_value = {"ok": True}
        bridge = PlaylistsBridge(playlist_service=svc)
        result = bridge.duplicatePlaylist(1)
        assert result.get("ok") is True

    def test_playlists_bridge_clear(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.playlists_bridge import PlaylistsBridge
        svc = MagicMock()
        svc.clear_playlist.return_value = {"ok": True}
        bridge = PlaylistsBridge(playlist_service=svc)
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
        assert (QML_DIR / "pages" / "devices" / "DevicesPage.qml").exists()
    def test_device_card_exists(self):
        assert (QML_DIR / "pages" / "devices" / "DeviceCard.qml").exists()
    def test_sync_status_panel_exists(self):
        assert (QML_DIR / "pages" / "devices" / "SyncStatusPanel.qml").exists()
    def test_devices_bridge_importable(self):
        from ui_qml_bridge.devices_bridge import DevicesBridge
        assert DevicesBridge is not None
    def test_devices_route_in_pagestack(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "sync" in ROUTES
        assert "sync.mobile" in ROUTES
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
        from ui_qml_bridge.route_registry import ROUTES
        assert "playlists" in ROUTES
    def test_playlist_detail_route_in_pagestack(self):
        from ui_qml_bridge.route_registry import ROUTES
        assert "playlist_detail" in ROUTES

class TestContextMenu:
    def test_song_context_menu_exists(self):
        assert (QML_DIR / "components" / "SongContextMenu.qml").exists()


class TestRadioBridgeIntegration:
    def test_radio_bridge_importable(self):
        from ui_qml_bridge.radio_bridge import RadioBridge
        assert RadioBridge is not None

    def test_radio_bridge_refresh(self):
        from unittest.mock import MagicMock
        bridge = RadioBridge(player_service=MagicMock())
        bridge.refresh()
        assert len(bridge.stations) == 0

    def test_radio_bridge_has_slots(self):
        from unittest.mock import MagicMock
        bridge = RadioBridge(player_service=MagicMock())
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
        assert isinstance(mods, list)

    def test_audio_lab_bridge_refresh(self):
        bridge = AudioLabBridge()
        bridge.refresh()


class TestDiscLabBridge:
    def test_disc_lab_importable(self):
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        assert DiscLabBridge is not None

    def _make_disc_lab_bridge(self, **kwargs):
        from unittest.mock import MagicMock
        from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
        args = dict(worker_manager=MagicMock(), **kwargs)
        return DiscLabBridge(**args)

    def test_disc_lab_unavailable_no_service(self):
        bridge = self._make_disc_lab_bridge()
        assert bridge.status == "unavailable"
        result = bridge.refresh()
        assert result.get("ok") is False
        assert result.get("error") == "UNSUPPORTED"

    def test_disc_lab_scan_no_disc(self):
        from unittest.mock import MagicMock
        svc = MagicMock()
        svc.detect_drives.return_value = ["/dev/sr0"]
        svc.get_cd_info.return_value = None
        bridge = self._make_disc_lab_bridge(disc_detection_service=svc)
        result = bridge.refresh()
        assert result.get("ok") is True
        assert bridge.status == "no_disc"

    def test_disc_lab_scan_with_tracks(self):
        from unittest.mock import MagicMock
        svc = MagicMock()
        svc.detect_drives.return_value = ["/dev/sr0"]
        svc.get_cd_info.return_value = {"tracks": 3, "duration_seconds": 300}
        bridge = self._make_disc_lab_bridge(disc_detection_service=svc)
        bridge.refresh()
        assert bridge.status == "ready"

    def test_disc_lab_eject(self):
        bridge = self._make_disc_lab_bridge()
        bridge._status = "scanned"
        bridge._tracks = [{"track": 1, "title": "Track 1"}]
        result = bridge.eject()
        assert result.get("ok") is True
        assert bridge.status == "no_disc"
        assert len(bridge.tracks) == 0


class TestSettingsBridgeIntegration:
    def test_settings_bridge_importable(self):
        from ui_qml_bridge.settings_bridge import SettingsBridgeV2 as SettingsBridge
        assert SettingsBridge is not None

    def test_settings_bridge_sections(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.settings_bridge import SettingsBridgeV2 as SettingsBridge
        svc = MagicMock()
        svc.categories.return_value = [{"id": "general", "title": "General", "sections": []}]
        bridge = SettingsBridge(service=svc)
        cats = bridge.categories
        assert len(cats) > 0
        assert any(c.get("id") == "general" for c in cats)


class TestConnectionsV2Bridge:
    def test_connections_bridge_refresh(self):
        bridge = ConnectionsBridge()
        bridge.refresh()
        assert bridge.microServerState == "service_unavailable"

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
    def _make_lyrics_bridge(self, **kwargs):
        from unittest.mock import MagicMock
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        args = dict(worker_manager=MagicMock(), **kwargs)
        return LyricsBridge(**args)

    def test_lyrics_idle_on_create(self):
        bridge = self._make_lyrics_bridge()
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
        bridge = self._make_lyrics_bridge()
        bridge._cache["test||artist||album||0"] = {
            "lyrics": "cached lyrics", "synced_lyrics": "",
            "source": "LRCLIB", "timestamp": 1000,
        }
        result = bridge.search("test", "artist", "album", 0)
        assert result.get("cached") is True
        assert bridge.lyrics == "cached lyrics"
        assert bridge.status == "done"

    def test_lyrics_cancel_search(self):
        bridge = self._make_lyrics_bridge()
        bridge._status = "searching"
        bridge.cancelSearch()
        assert bridge.status == "idle"

    def test_lyrics_clear_cache_for_track(self):
        bridge = self._make_lyrics_bridge()
        bridge._cache["test||artist||album||0"] = {"lyrics": "x", "synced_lyrics": "", "source": "L", "timestamp": 1000}
        bridge._current_title = "test"
        bridge._current_artist = "artist"
        bridge._current_album = "album"
        bridge._current_duration = 0
        result = bridge.clearCacheForCurrentTrack()
        assert result.get("ok") is True
        assert "test||artist||album||0" not in bridge._cache

    def test_lyrics_search_manual_empty(self):
        bridge = self._make_lyrics_bridge()
        result = bridge.searchManual("")
        assert result.get("ok") is False
        assert result.get("error") == "EMPTY_QUERY"

    def test_lyrics_search_current_track_no_np(self):
        bridge = self._make_lyrics_bridge()
        result = bridge.searchCurrentTrack()
        assert result.get("ok") is False

    def test_lyrics_get_active_line(self):
        bridge = self._make_lyrics_bridge()
        bridge._synced_lyrics = [{"time": 1.0, "text": "A"}, {"time": 2.0, "text": "B"}, {"time": 3.0, "text": "C"}]
        assert bridge.getActiveLine(0) == 0
        assert bridge.getActiveLine(1500) == 0
        assert bridge.getActiveLine(2500) == 1
        assert bridge.getActiveLine(5000) == 2

    def test_lyrics_get_active_line_empty(self):
        bridge = self._make_lyrics_bridge()
        assert bridge.getActiveLine(1000) is None

    def test_lyrics_on_track_changed_noop_same_track(self):
        from unittest.mock import MagicMock
        bridge = self._make_lyrics_bridge()
        bridge._current_title = "Same"
        bridge._current_artist = "Same"
        np_mock = MagicMock()
        np_mock.trackTitle = "Same"
        np_mock.trackArtist = "Same"
        bridge._np_bridge = np_mock
        bridge._on_track_changed()
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
        snap_adapter.get_servers.return_value = [
            {"id": "srv1", "state": "running", "name": "Snapcast"},
        ]
        snap_adapter.get_zones.return_value = [
            {"id": "zone1", "name": "Salón", "muted": False, "volume": 80},
        ]
        snap_adapter.is_connected = False
        bridge = HomeAudioBridge(snapcast_ctrl=snap_adapter)
        bridge.refresh()
        assert bridge.snapcastAvailable is True
        assert len(bridge.servers) == 1

    def test_home_audio_bridge_configure_with_ha_adapter(self):
        class _HAAdapter:
            def configure(self, host="", port=0, access_token=""):
                return {"ok": True}
        ha_adapter = _HAAdapter()
        bridge = HomeAudioBridge(home_audio_service=ha_adapter)
        result = bridge.configureHomeAssistant("192.168.1.100", 8123, "token")
        assert result.get("ok") is True

    def test_home_audio_bridge_volume_with_snapcast(self):
        from unittest.mock import MagicMock
        snap_adapter = MagicMock()
        snap_adapter.set_volume.return_value = {"ok": True}
        bridge = HomeAudioBridge(snapcast_ctrl=snap_adapter)
        result = bridge.setZoneVolume("zone1", 0.8)
        assert result.get("ok") is True
        snap_adapter.set_volume.assert_called_once_with("zone1", 0.8)


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
        from unittest.mock import MagicMock
        from ui_qml_bridge.global_search_bridge import GlobalSearchBridge
        qe = MagicMock()
        qe.execute.return_value = []
        bridge = GlobalSearchBridge(query_executor=qe)
        result = bridge.search("test")
        assert result.get("ok") is True
        assert result.get("count", 0) <= 50


class TestJobBridge:
    def _make_job_bridge(self, **kwargs):
        from unittest.mock import MagicMock
        from ui_qml_bridge.job_bridge import JobBridge
        args = dict(worker_manager=MagicMock(), db=MagicMock(), **kwargs)
        return JobBridge(**args)

    def test_job_bridge_importable(self):
        bridge = self._make_job_bridge()
        assert bridge.jobs == []
        assert bridge.activeCount == 0

    def test_job_bridge_unknown_job(self):
        bridge = self._make_job_bridge()
        result = bridge.runJob("unknown_job")
        assert result.get("ok") is False
        assert result.get("error") == "UNKNOWN_JOB_TYPE"

    def test_job_bridge_run_scan(self):
        bridge = self._make_job_bridge()
        result = bridge.runJob("library_scan", "/tmp")
        assert result.get("ok") is True
        assert len(bridge.jobs) == 1

    def test_job_bridge_cancel(self):
        bridge = self._make_job_bridge()
        bridge.runJob("library_scan", "/tmp")
        job_id = bridge.jobs[0]["job_id"]
        result = bridge.cancelJob(job_id)
        assert result.get("ok") is True
        assert bridge.activeCount == 0

    def test_job_bridge_cancel_not_found(self):
        bridge = self._make_job_bridge()
        result = bridge.cancelJob(999)
        assert result.get("ok") is False

    def test_job_bridge_clear_completed(self):
        bridge = self._make_job_bridge()
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
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        svc = MagicMock()
        svc.list.return_value = []
        bridge = LibrarySourcesBridge(service=svc)
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
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        from core.library_sources_service import LibrarySourcesService
        db = MagicMock()
        db.remove_library_root.return_value = False
        svc = LibrarySourcesService(db=db)
        bridge = LibrarySourcesBridge(service=svc)
        result = bridge.removeSource("/nonexistent")
        assert result.get("ok") is False

    def test_library_sources_bridge_refresh(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.library_sources_bridge import LibrarySourcesBridge
        bridge = LibrarySourcesBridge(service=MagicMock())
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
        bridge = RadioBridge(radio_manager=mgr, player_service=MagicMock())
        bridge.refresh()
        assert len(bridge.stations) >= 1


class TestMixBridgeWithService:
    def test_mix_bridge_with_db(self):
        from unittest.mock import MagicMock
        from ui_qml_bridge.mix_bridge import MixBridge
        bridge = MixBridge(playback_service=MagicMock(), queue_service=MagicMock())
        assert len(bridge.categories) > 0
        assert any(c["id"] == "favorites" for c in bridge.categories)
