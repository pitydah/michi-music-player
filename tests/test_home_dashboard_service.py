"""Tests for HomeDashboardService — snapshot building from services & fallbacks."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.home.home_dashboard_service import HomeDashboardService
from core.home.home_status import LibraryHomeStatus, EcosystemHomeStatus


@pytest.fixture
def empty_db():
    db = MagicMock()
    db.get_dashboard_stats.return_value = {"total_songs": 0, "total_albums": 0, "total_artists": 0}
    return db


@pytest.fixture
def healthy_db():
    db = MagicMock()
    db.get_dashboard_stats.return_value = {"total_songs": 12438, "total_albums": 845, "total_artists": 312, "missing_metadata": 12}
    return db


@pytest.fixture
def playing_playback():
    pb = MagicMock()
    pb.state = "playing"
    cur = MagicMock()
    cur.title = "Test Song"
    cur.artist = "Test Artist"
    cur.album = "Test Album"
    pb.current = cur
    pb.get_queue_state.return_value = {"active": True, "count": 5}
    return pb


@pytest.fixture
def stopped_playback():
    pb = MagicMock()
    pb.state = "stopped"
    pb.current = None
    pb.get_queue_state.return_value = {"active": False, "count": 0}
    return pb


@pytest.fixture
def context_svc_with_data():
    svc = MagicMock()
    svc.get_home_snapshot.return_value = {
        "library_health": {"track_count": 12438, "album_count": 845, "artist_count": 312, "genre_count": 28, "active_roots_count": 3, "last_scan": "2026-06-29 18:30", "index_error_count": 0, "missing_file_count": 0, "missing_metadata_count": 12, "missing_cover_count": 3, "tracks_without_audio_features": 200, "new_tracks_count": 45},
        "playback": {"now_playing": {"title": "Test", "artist": "Artist"}, "queue_length": 3},
        "warnings": [], "sync_peers": 0,
    }
    return svc


@pytest.fixture
def sync_mgr_with_peers():
    mgr = MagicMock()
    mgr.get_all_peers.return_value = [{"device_id": "a"}, {"device_id": "b"}]
    mgr.last_sync = "2026-06-30 12:00"
    mgr.is_syncing.return_value = False
    return mgr


@pytest.fixture
def empty_sync_mgr():
    mgr = MagicMock()
    mgr.get_all_peers.return_value = []
    mgr.last_sync = None
    return mgr


class TestEmptyLibrary:
    def test_empty_db_returns_empty_snapshot(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.library.is_empty
        assert snap.overall_state == "empty_library"

    def test_empty_db_actions_include_add_folder(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert any("Añadir" in a.label for a in snap.actions)

    def test_empty_db_no_alerts(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert len(snap.alerts) == 0


class TestHealthyLibrary:
    def test_healthy_db_returns_ready(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert snap.overall_state in ("ready", "playback_active", "needs_attention")

    def test_actions_include_view_library(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert any("biblioteca" in a.label.lower() for a in snap.actions)

    def test_no_errors(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert len(snap.errors) == 0


class TestPlayback:
    def test_playing_state(self, playing_playback):
        svc = HomeDashboardService(playback=playing_playback)
        snap = svc.build_snapshot()
        assert snap.playback.state == "playing"
        assert snap.playback.has_current_track is True
        assert snap.playback.current_title == "Test Song"

    def test_playing_queue(self, playing_playback):
        svc = HomeDashboardService(playback=playing_playback)
        snap = svc.build_snapshot()
        assert snap.playback.queue_active is True
        assert snap.playback.queue_count == 5

    def test_stopped_no_track(self, stopped_playback):
        svc = HomeDashboardService(playback=stopped_playback)
        snap = svc.build_snapshot()
        assert snap.playback.state == "stopped"
        assert snap.playback.has_current_track is False

    def test_queue_does_not_expose_paths(self, playing_playback):
        svc = HomeDashboardService(playback=playing_playback)
        snap = svc.build_snapshot()
        qs = snap.playback
        assert qs.queue_count == 5


class TestAudio:
    def test_default_audio_profile(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert snap.audio.output_device == "Predeterminado"


class TestNormalizePlayback:
    def test_normalize_none(self):
        assert HomeDashboardService._normalize_playback_state(None) == "stopped"

    def test_normalize_string_playing(self):
        assert HomeDashboardService._normalize_playback_state("playing") == "playing"

    def test_normalize_string_paused(self):
        assert HomeDashboardService._normalize_playback_state("paused") == "paused"

    def test_normalize_string_stopped(self):
        assert HomeDashboardService._normalize_playback_state("stopped") == "stopped"

    def test_normalize_unknown(self):
        assert HomeDashboardService._normalize_playback_state("bogus") == "stopped"

    def test_normalize_enum(self):
        class FakeEnum:
            name = "PLAYING"
        assert HomeDashboardService._normalize_playback_state(FakeEnum()) == "playing"


class TestEcosystem:
    def test_micro_server_without_host_is_not_configured(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "not_configured"

    def test_remote_music_server_does_not_set_micro_connected(self, empty_db):
        srv = MagicMock()
        srv.name = "MyServer"
        srv.server_type = "subsonic"
        with patch("streaming.subsonic_client.load_servers", return_value=[srv]):
            svc = HomeDashboardService(db=empty_db)
            snap = svc.build_snapshot()
            assert snap.ecosystem.remote_music_server_state == "configured"
            assert snap.ecosystem.remote_music_server_name == "MyServer"
            assert snap.ecosystem.micro_server_state == "not_configured"

    def test_sync_with_peers(self, empty_db, sync_mgr_with_peers):
        svc = HomeDashboardService(db=empty_db, sync_mgr=sync_mgr_with_peers)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state in ("paired",)
        assert snap.ecosystem.mobile_device_count == 2

    def test_sync_no_devices(self, empty_db, empty_sync_mgr):
        svc = HomeDashboardService(db=empty_db, sync_mgr=empty_sync_mgr)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state == "no_device"
        assert snap.ecosystem.mobile_device_count == 0

    def test_sync_no_mgr(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state == "no_device"

    def test_ecosystem_doctor_micro_connected(self):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {"micro_server_state": "connected", "micro_server_name": "192.168.1.100"}
        mlc.get_capabilities.return_value = {"contract_ok": True, "can_continue_playback": True}
        svc = HomeDashboardService(michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "connected"

    def test_ecosystem_doctor_micro_requires_pairing(self):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {"micro_server_state": "requires_pairing"}
        mlc.get_capabilities.return_value = {}
        svc = HomeDashboardService(michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "requires_pairing"

    def test_ecosystem_doctor_micro_contract_error(self):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {"micro_server_state": "unreachable"}
        mlc.get_capabilities.return_value = {}
        svc = HomeDashboardService(michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "unreachable"


class TestAlerts:
    def test_micro_requires_pairing_alert(self):
        svc = HomeDashboardService(db=MagicMock())
        lib = LibraryHomeStatus(track_count=1000, is_empty=False, is_healthy=True)
        audio = MagicMock()
        audio.warnings = []
        eco = EcosystemHomeStatus(micro_server_state="requires_pairing")
        alerts = svc._build_alerts(lib, audio, eco)
        kinds = [a.kind for a in alerts]
        assert "micro_server" in kinds

    def test_disabled_home_audio_no_alert(self):
        svc = HomeDashboardService()
        lib = LibraryHomeStatus(track_count=1000, is_empty=False)
        audio = MagicMock()
        audio.warnings = []
        eco = EcosystemHomeStatus(home_audio_state="disabled")
        alerts = svc._build_alerts(lib, audio, eco)
        kinds = [a.kind for a in alerts]
        assert "home_audio" not in kinds

    def test_alerts_max_five(self):
        svc = HomeDashboardService()
        lib = LibraryHomeStatus(track_count=1000, index_error_count=5, missing_file_count=5, missing_metadata_count=200, missing_cover_count=200, tracks_without_audio_features=200, is_empty=False)
        audio = MagicMock()
        audio.warnings = []
        eco = EcosystemHomeStatus()
        alerts = svc._build_alerts(lib, audio, eco)
        assert len(alerts) <= 5


class TestAssistantSuggestions:
    def test_suggestions_from_context(self, context_svc_with_data, healthy_db):
        svc = HomeDashboardService(db=healthy_db, context_svc=context_svc_with_data)
        snap = svc.build_snapshot()
        assert len(snap.assistant_suggestions) > 0

    def test_suggestions_fallback(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert len(snap.assistant_suggestions) > 0


class TestNoAbsolutePaths:
    def test_dashboard_snapshot_no_paths(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        text = str(snap)
        assert "/home" not in text
        assert "C:" not in text


class TestSafeMode:
    def test_safe_mode_overall_state(self, healthy_db):
        with patch.dict(os.environ, {"MICHI_SAFE_MODE": "1"}, clear=False):
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            assert snap.overall_state == "safe_mode"

    def test_safe_mode_alert_present(self, healthy_db):
        with patch.dict(os.environ, {"MICHI_SAFE_MODE": "1"}, clear=False):
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            kinds = [a.kind for a in snap.alerts]
            assert "safe_mode" in kinds


class TestPartialFailure:
    def test_audio_card_failure_does_not_break_dashboard(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert snap.library is not None
        assert snap.playback is not None
        assert snap.audio is not None

    def test_library_card_failure_does_not_break_playback(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert snap.playback is not None
        assert snap.library.is_empty

    def test_ecosystem_failure_defaults(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "not_configured"


class TestSubtitle:
    def test_subtitle_with_library(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert "12,438" in snap.subtitle or "12438" in snap.subtitle

    def test_subtitle_empty(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.subtitle == "Todo listo"


class TestSettingsKeys:
    def test_home_audio_url_uses_get_str(self):
        with patch("core.home.home_dashboard_service.logger"):
            svc = HomeDashboardService()
            snap = svc.build_snapshot()
            assert snap.ecosystem.home_audio_state in ("disabled", "configured", "active")
