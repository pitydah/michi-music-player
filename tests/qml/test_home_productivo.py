"""PK — Tests for Home productivo.

Home: estado del sistema, reproduccion, Queue, fuente activa, jobs,
servidor, errores, continuidad, acciones utiles de Michi AI.
No usar vitrinas redundantes. Cada card con accion real.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, PropertyMock

from ui_qml_bridge.action_registry import ActionRegistry
from ui_qml_bridge.home_bridge import HomeBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.route_registry import ROUTES

pytestmark = [pytest.mark.qml_module("home_productivo")]


class TestHomeBridgeEstadoSistema:
    def test_home_bridge_initial_state(self):
        hb = HomeBridge()
        assert hb.libraryAlbums == 0
        assert hb.libraryArtists == 0
        assert hb.libraryTracks == 0
        assert hb.sourcesCount == 0
        assert not hb.hasPlayback
        assert hb.activeJobs == 0

    def test_home_bridge_refresh_loads_stats(self):
        lib = MagicMock()
        lib.songCount = 500
        lib.albumCount = 50
        lib.artistCount = 25
        hb = HomeBridge(library_bridge=lib)
        hb.refresh()
        assert hb.libraryTracks == 500
        assert hb.libraryAlbums == 50
        assert hb.libraryArtists == 25

    def test_home_bridge_refresh_snapshot_signal(self):
        signals = []
        hb = HomeBridge()
        hb.snapshotChanged.connect(lambda: signals.append(True))
        hb.refresh()
        assert len(signals) >= 1

    def test_home_bridge_playback_with_player(self):
        player = MagicMock()
        cur = MagicMock()
        cur.title = "Current Song"
        cur.artist = "Current Artist"
        player.current = cur
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert hb.hasPlayback
        assert hb.currentTrackTitle == "Current Song"
        assert hb.currentArtist == "Current Artist"

    def test_home_bridge_no_playback_without_player(self):
        hb = HomeBridge()
        hb.refresh()
        assert not hb.hasPlayback
        assert hb.currentTrackTitle == "—"

    def test_home_bridge_playback_with_get_current_track(self):
        player = MagicMock(spec=["get_current_track"])
        player.get_current_track = MagicMock(return_value={"title": "Track", "artist": "Artist"})
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert hb.hasPlayback
        assert hb.currentTrackTitle == "Track"

    def test_home_bridge_audio_backend(self):
        player = MagicMock()
        player.get_active_backend_id.return_value = "gstreamer"
        player.get_output_device_id.return_value = "default"
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert hb.backend == "gstreamer"
        assert hb.output == "default"

    def test_home_bridge_jobs_from_job_bridge(self):
        jb = MagicMock()
        jb.activeCount = 3
        hb = HomeBridge(job_bridge=jb)
        hb.refresh()
        assert hb.activeJobs == 3


class TestHomeBridgeReproduccion:
    def test_home_bridge_playback_changed_signal(self):
        player = MagicMock()
        player.track_changed = MagicMock()
        player.state_changed = MagicMock()
        HomeBridge(player_service=player)
        assert player.track_changed.connect.called
        assert player.state_changed.connect.called

    def test_home_bridge_playback_track_properties(self):
        player = MagicMock()
        cur = MagicMock()
        cur.title = "Test"
        cur.artist = "Artist"
        player.current = cur
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert hb.currentTrackTitle == "Test"
        assert hb.currentArtist == "Artist"

    def test_home_bridge_playback_no_track(self):
        player = MagicMock()
        player.current = None
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert not hb.hasPlayback

    def test_home_bridge_playback_exception_safe(self):
        player = MagicMock()
        type(player).current = PropertyMock(side_effect=RuntimeError("fail"))
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert not hb.hasPlayback

    def test_home_bridge_backend_tolerates_missing_attrs(self):
        player = MagicMock(spec=[])
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert hb.backend == ""

    def test_home_bridge_set_library_stats(self):
        hb = HomeBridge()
        hb.set_library_stats(100, 50, 2000)
        assert hb.libraryAlbums == 100
        assert hb.libraryArtists == 50
        assert hb.libraryTracks == 2000


class TestHomeBridgeQueueFuenteActiva:
    def test_home_bridge_sources_count(self):
        src_svc = MagicMock()
        src_svc.list.return_value = [{"path": "/music", "enabled": True}]
        hb = HomeBridge(library_sources_service=src_svc)
        hb.refresh()
        assert hb.sourcesCount == 1

    def test_home_bridge_sources_exception_safe(self):
        src_svc = MagicMock()
        src_svc.list.side_effect = RuntimeError("fail")
        hb = HomeBridge(library_sources_service=src_svc)
        hb.refresh()
        assert hb.sourcesCount == 0

    def test_home_bridge_last_scan(self):
        hb = HomeBridge()
        assert hb.lastScan == ""

    def test_home_bridge_jobs_tied_to_job_bridge(self):
        jb = MagicMock()
        type(jb).activeCount = PropertyMock(return_value=5)
        hb = HomeBridge(job_bridge=jb)
        hb.refresh()
        assert hb.activeJobs == 5


class TestHomeBridgeScore:
    def test_home_score_zero_without_services(self):
        hb = HomeBridge()
        score = hb.homeScore()
        assert score["score"] == 15

    def test_home_score_with_db(self):
        hb = HomeBridge(db=MagicMock())
        score = hb.homeScore()
        assert score["has_db"]
        assert score["score"] > 0

    def test_home_score_with_player(self):
        player = MagicMock()
        player.state = "playing"
        hb = HomeBridge(player_service=player)
        score = hb.homeScore()
        assert score["has_player"]
        assert score["score"] >= 35

    def test_home_score_with_tracks(self):
        hb = HomeBridge(library_bridge=MagicMock(songCount=100))
        hb.set_library_stats(10, 5, 100)
        score = hb.homeScore()
        assert score["tracks"] == 100
        assert score["score"] > 30


class TestHomeBridgeNavigation:
    def test_navigate_to_library(self):
        nav = NavigationBridge()
        nav.navigate("library")
        assert nav.currentRoute == "library"

    def test_navigate_to_playback(self):
        nav = NavigationBridge()
        nav.navigate("playback")
        assert nav.currentRoute == "playback"

    def test_navigate_to_assistant(self):
        nav = NavigationBridge()
        nav.navigate("assistant")
        assert nav.currentRoute == "assistant"

    def test_navigate_to_connections(self):
        nav = NavigationBridge()
        nav.set_capabilities({"connections"})
        nav.navigate("connections")
        assert nav.currentRoute == "connections"

    def test_navigate_to_home_audio(self):
        nav = NavigationBridge()
        nav.set_capabilities({"home_audio"})
        nav.navigate("home_audio")
        assert nav.currentRoute == "home_audio"

    def test_navigate_to_jobs(self):
        nav = NavigationBridge()
        nav.set_capabilities({"audio_lab"})
        nav.navigate("audio_lab.jobs")
        assert nav.currentRoute == "audio_lab.jobs"

    def test_navigate_to_queue(self):
        nav = NavigationBridge()
        nav.navigate("queue")
        assert nav.currentRoute == "queue"

    def test_navigate_to_history(self):
        nav = NavigationBridge()
        nav.navigate("history")
        assert nav.currentRoute == "history"

    def test_navigate_to_settings(self):
        nav = NavigationBridge()
        nav.set_capabilities({"settings"})
        nav.navigate("settings")
        assert nav.currentRoute == "settings"

    def test_navigate_to_radio(self):
        nav = NavigationBridge()
        nav.navigate("radio")
        assert nav.currentRoute == "radio"

    def test_navigate_to_mix(self):
        nav = NavigationBridge()
        nav.navigate("mix")
        assert nav.currentRoute == "mix"

    def test_navigate_to_lyrics(self):
        nav = NavigationBridge()
        nav.navigate("lyrics")
        assert nav.currentRoute == "lyrics"

    def test_navigate_home_then_back(self):
        nav = NavigationBridge()
        nav.navigate("library")
        nav.navigate("playback")
        nav.back()
        assert nav.currentRoute == "library"
        nav.back()
        assert nav.currentRoute == "home"


class TestHomeBridgeErrores:
    def test_home_bridge_safe_without_db(self):
        hb = HomeBridge()
        hb.refresh()
        assert hb.libraryAlbums == 0

    def test_home_bridge_safe_without_player(self):
        hb = HomeBridge()
        hb.refresh()
        assert not hb.hasPlayback

    def test_home_bridge_tolerates_missing_player_attrs(self):
        player = MagicMock()
        del player.current
        hb = HomeBridge(player_service=player)
        hb.refresh()
        assert not hb.hasPlayback


class TestHomeBridgeMichiAIActions:
    def test_action_registry_has_assistant_actions(self):
        ar = ActionRegistry()
        action = ar.get("navigate_lyrics")
        assert action is not None

    def test_action_registry_playback_actions(self):
        ar = ActionRegistry()
        for action_id in ["playback_playpause", "playback_next", "playback_prev"]:
            assert ar.get(action_id) is not None, f"Missing action: {action_id}"

    def test_action_registry_navigation_actions(self):
        ar = ActionRegistry()
        for route in ["home", "library", "playlists", "radio", "settings", "queue"]:
            action_id = f"navigate_{route}"
            assert ar.get(action_id) is not None, f"Missing action: {action_id}"

    def test_action_registry_album_actions(self):
        ar = ActionRegistry()
        for action_id in ["album_play", "album_shuffle", "album_queue", "album_favorite"]:
            assert ar.get(action_id) is not None, f"Missing action: {action_id}"

    def test_action_registry_track_actions(self):
        ar = ActionRegistry()
        for action_id in ["track_play_now", "track_play_next", "track_add_to_queue",
                          "track_favorite", "track_open_album", "track_open_artist"]:
            assert ar.get(action_id) is not None, f"Missing action: {action_id}"

    def test_action_registry_library_actions(self):
        ar = ActionRegistry()
        for action_id in ["library_refresh", "library_scan", "library_add_folder"]:
            assert ar.get(action_id) is not None, f"Missing action: {action_id}"

    def test_action_registry_playlist_actions(self):
        ar = ActionRegistry()
        assert ar.get("playlist_create") is not None

    def test_action_registry_system_actions(self):
        ar = ActionRegistry()
        assert ar.get("app_quit") is not None


class TestRouteRegistryIntegrity:
    def test_home_route_exists(self):
        assert "home" in ROUTES
        assert ROUTES["home"]["title"] == "Inicio"

    def test_core_routes_exist(self):
        core_routes = ["home", "library", "queue", "playback", "playlists",
                       "history", "mix", "connections", "home_audio",
                       "ai", "assistant", "radio"]
        for route in core_routes:
            assert route in ROUTES, f"Missing core route: {route}"

    def test_tools_routes_exist(self):
        tools = ["audio_lab", "equalizer", "library_doctor", "tagging",
                 "lyrics", "diagnostics"]
        for route in tools:
            assert route in ROUTES, f"Missing tools route: {route}"

    def test_settings_routes_exist(self):
        settings = ["settings", "settings.general", "settings.appearance",
                    "settings.playback", "settings.library",
                    "settings.accessibility", "settings.audio", "settings.about"]
        for route in settings:
            assert route in ROUTES, f"Missing settings route: {route}"

    def test_detail_routes_exist(self):
        details = ["library.album_detail", "library.artist_detail",
                   "library.folder_detail", "playlist_detail",
                   "mix_detail", "mix_generator", "connections.detail",
                   "devices.detail", "devices.pairing"]
        for route in details:
            assert route in ROUTES, f"Missing detail route: {route}"
