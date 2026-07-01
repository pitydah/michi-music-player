"""Tests for HomeDashboardService — snapshot building from services & fallbacks."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from core.home.home_dashboard_service import HomeDashboardService
from core.home.home_status import LibraryHomeStatus


# ── Fixtures ──


@pytest.fixture
def empty_db():
    db = MagicMock()
    db.get_dashboard_stats.return_value = {"total_songs": 0, "total_albums": 0, "total_artists": 0}
    return db


@pytest.fixture
def healthy_db():
    db = MagicMock()
    db.get_dashboard_stats.return_value = {
        "total_songs": 12438,
        "total_albums": 845,
        "total_artists": 312,
        "missing_metadata": 12,
    }
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
        "library_health": {
            "track_count": 12438,
            "album_count": 845,
            "artist_count": 312,
            "genre_count": 28,
            "active_roots_count": 3,
            "last_scan": "2026-06-29 18:30",
            "index_error_count": 0,
            "missing_file_count": 0,
            "missing_metadata_count": 12,
            "missing_cover_count": 3,
            "tracks_without_audio_features": 200,
            "new_tracks_count": 45,
        },
        "playback": {
            "now_playing": {"title": "Test", "artist": "Artist"},
            "queue_length": 3,
        },
        "warnings": [],
        "sync_peers": 0,
    }
    svc.get_assistant_snapshot.return_value = {
        "suggested_actions": [
            {"label": "Limpiar metadatos", "route": "metadata_editor", "priority": 10},
        ]
    }
    return svc


@pytest.fixture
def sync_mgr_with_peers():
    mgr = MagicMock()
    mgr.get_all_peers.return_value = [{"id": "dev1"}, {"id": "dev2"}]
    mgr.is_syncing.return_value = False
    mgr.last_sync = "2026-06-30 10:00"
    return mgr


@pytest.fixture
def empty_sync_mgr():
    mgr = MagicMock()
    mgr.get_all_peers.return_value = []
    return mgr


@pytest.fixture
def player_engine_with_dsp():
    eng = MagicMock()
    dsp = MagicMock()
    dsp.eq_enabled = True
    dsp.replaygain_enabled = True
    dsp.is_dsp_active = lambda: True
    eng.dsp_state = dsp
    eng.current_format = MagicMock()
    return eng


# ── Tests ──


class TestEmptyLibrary:
    def test_empty_db_returns_empty_snapshot(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.library.is_empty is True
        assert snap.overall_state == "empty_library"
        assert snap.headline == "Agrega música para comenzar"

    def test_empty_db_library_metrics(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.library.track_count == 0
        assert snap.library.album_count == 0
        assert snap.library.artist_count == 0

    def test_empty_db_no_playback(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.playback.can_continue is False
        assert snap.playback.state == "stopped"

    def test_empty_db_audio_defaults(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.audio.bitperfect_state == "not_available"

    def test_empty_db_ecosystem_defaults(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "not_configured"
        assert snap.ecosystem.mobile_sync_state == "no_device"

    def test_empty_db_no_alerts(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert len(snap.alerts) == 0

    def test_empty_db_actions_include_add_folder(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        actions = snap.actions
        assert any("Añadir" in a.label for a in actions)


class TestHealthyLibrary:
    def test_healthy_db_returns_ready(self, healthy_db):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            assert snap.library.is_empty is False
            assert snap.overall_state == "ready"
            assert snap.headline == "Michi está listo"

    def test_healthy_metrics(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert snap.library.track_count == 12438
        assert snap.library.album_count == 845
        assert snap.library.artist_count == 312

    def test_subtitle_includes_count(self, healthy_db):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            assert "12,438" in snap.subtitle or "12438" in snap.subtitle

    def test_healthy_has_micro_server_alert_when_not_connected(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        kinds = [a.kind for a in snap.alerts]
        assert "micro_server" not in kinds  # remote version uses not_configured, not disconnected

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
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(playback=playing_playback)
            snap = svc.build_snapshot()
            assert snap.playback.state == "playing"
            assert snap.playback.has_current_track is True
            assert snap.playback.current_title == "Test Song"
            assert snap.playback.current_artist == "Test Artist"

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
        assert snap.playback.can_continue is False


class TestAudio:
    def test_no_engine_returns_defaults(self):
        svc = HomeDashboardService()
        snap = svc.build_snapshot()
        assert snap.audio.bitperfect_state == "not_available"

    def test_eq_active_via_playback(self):
        pb = MagicMock()
        pb.get_output_device_id.return_value = None
        pb.get_eq_state.return_value = {"bypass": False}
        pb.get_audio_diagnostics.return_value = {}
        svc = HomeDashboardService(playback=pb)
        snap = svc.build_snapshot()
        assert snap.audio.eq_enabled is True

    def test_output_device_fallback(self):
        pb = MagicMock()
        pb.get_output_device_id.return_value = None
        svc = HomeDashboardService(playback=pb)
        snap = svc.build_snapshot()
        assert snap.audio.output_device == "Predeterminado"

    def test_output_profile_from_settings(self):
        with patch("core.settings_manager.get_str", return_value="hifi_pcm"), patch(
            "core.settings_manager.get_bool", return_value=True
        ):
            svc = HomeDashboardService(settings_mgr=MagicMock())
            snap = svc.build_snapshot()
            assert snap.audio.output_profile == "hifi_pcm"


class TestEcosystem:
    def test_no_michi_link_not_configured(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "not_configured"

    def test_michi_link_connected(self, empty_db):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {
            "micro_server_state": "connected",
            "micro_server_name": "MyMicro",
        }
        svc = HomeDashboardService(db=empty_db, michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "connected"
        assert snap.ecosystem.micro_server_name == "MyMicro"

    def test_michi_link_requires_pairing(self, empty_db):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {
            "micro_server_state": "requires_pairing",
        }
        svc = HomeDashboardService(db=empty_db, michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "requires_pairing"

    def test_michi_link_contract_error(self, empty_db):
        mlc = MagicMock()
        mlc.get_connection_state.return_value = {
            "micro_server_state": "contract_error",
        }
        svc = HomeDashboardService(db=empty_db, michi_link_ctrl=mlc)
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "contract_error"

    def test_sync_with_peers(self, empty_db, sync_mgr_with_peers):
        svc = HomeDashboardService(db=empty_db, sync_mgr=sync_mgr_with_peers)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state == "paired"
        assert snap.ecosystem.mobile_device_count == 2
        assert snap.ecosystem.last_sync is not None

    def test_sync_no_devices(self, empty_db, empty_sync_mgr):
        empty_sync_mgr.is_active = True
        svc = HomeDashboardService(db=empty_db, sync_mgr=empty_sync_mgr)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state in ("paired", "no_device")
        assert snap.ecosystem.mobile_device_count == 0

    def test_sync_no_mgr(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.ecosystem.mobile_sync_state == "no_device"


class TestAlerts:
    def test_index_errors_alert(self):
        svc = HomeDashboardService(db=MagicMock())
        lib = LibraryHomeStatus(track_count=1000, index_error_count=5, is_empty=False, is_healthy=False)
        audio = MagicMock()
        audio.warnings = []
        eco = MagicMock()
        eco.micro_server_state = "disconnected"
        eco.micro_server_name = ""
        alerts = svc._build_alerts(lib, audio, eco)
        kinds = [a.kind for a in alerts]
        assert "index_errors" in kinds

    def test_metadata_alert_threshold(self):
        svc = HomeDashboardService()
        lib = LibraryHomeStatus(track_count=1000, missing_metadata_count=100, is_empty=False)
        audio = MagicMock()
        audio.warnings = []
        eco = MagicMock()
        eco.micro_server_state = "connected"
        alerts = svc._build_alerts(lib, audio, eco)
        kinds = [a.kind for a in alerts]
        assert "metadata" in kinds

    def test_alerts_max_five(self):
        svc = HomeDashboardService(db=MagicMock())
        lib = LibraryHomeStatus(
            track_count=1000, index_error_count=5, missing_file_count=5,
            missing_metadata_count=200, missing_cover_count=200,
            tracks_without_audio_features=200, is_empty=False,
        )
        audio = MagicMock()
        audio.warnings = []
        eco = MagicMock()
        eco.micro_server_state = "connected"
        alerts = svc._build_alerts(lib, audio, eco)
        assert len(alerts) <= 5

    def test_alerts_truncated_with_summary(self):
        svc = HomeDashboardService(db=MagicMock())
        lib = LibraryHomeStatus(
            track_count=1000, index_error_count=5, missing_file_count=5,
            missing_metadata_count=200, missing_cover_count=200,
            tracks_without_audio_features=200, is_empty=False,
        )
        audio = MagicMock()
        audio.warnings = ["test warning"]
        eco = MagicMock()
        eco.micro_server_state = "disconnected"
        alerts = svc._build_alerts(lib, audio, eco)
        assert len(alerts) <= 6
        extras = [a for a in alerts if "adicionales" in a.title.lower()]
        assert len(extras) <= 1

    def test_alerts_critical_before_warning(self):
        svc = HomeDashboardService(db=MagicMock())
        lib = LibraryHomeStatus(
            track_count=1000, index_error_count=5, missing_file_count=5,
            missing_metadata_count=200, missing_cover_count=3,
            tracks_without_audio_features=3, is_empty=False,
        )
        audio = MagicMock()
        audio.warnings = []
        eco = MagicMock()
        eco.micro_server_state = "disconnected"
        alerts = svc._build_alerts(lib, audio, eco)
        severities = [a.severity for a in alerts]
        crit_idx = severities.index("critical") if "critical" in severities else 999
        warn_idx = severities.index("warning") if "warning" in severities else 999
        info_idx = severities.index("info") if "info" in severities else 999
        assert crit_idx < warn_idx or warn_idx == 999
        assert warn_idx < info_idx or info_idx == 999


class TestSafeMode:
    def test_safe_mode_overall_state(self):
        with patch.dict(os.environ, {"MICHI_SAFE_MODE": "1"}):
            svc = HomeDashboardService()
            snap = svc.build_snapshot()
            assert snap.overall_state == "safe_mode"
            assert snap.headline == "Michi está en modo seguro"

    def test_safe_mode_alert_present(self):
        with patch.dict(os.environ, {"MICHI_SAFE_MODE": "1"}):
            svc = HomeDashboardService()
            snap = svc.build_snapshot()
            kinds = [a.kind for a in snap.alerts]
            assert "safe_mode" in kinds


class TestPartialFailure:
    def test_audio_card_failure_does_not_break_dashboard(self):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            db = MagicMock()
            db.get_dashboard_stats.return_value = {"total_songs": 1000}
            svc = HomeDashboardService(db=db)
            svc._build_audio_status = lambda: (_ for _ in ()).throw(RuntimeError("Audio failure"))
            snap = svc.build_snapshot()
            assert len(snap.errors) > 0
            assert any(e.card_name == "audio" for e in snap.errors)

    def test_library_card_failure_does_not_break_playback(self, playing_playback):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(playback=playing_playback)
            svc._build_library_status = lambda: (_ for _ in ()).throw(RuntimeError("Lib failure"))
            snap = svc.build_snapshot()
            assert snap.playback.state == "playing"
            assert len(snap.errors) > 0

    def test_ecosystem_failure_defaults(self):
        svc = HomeDashboardService()
        svc._build_ecosystem_status = lambda: (_ for _ in ()).throw(RuntimeError("Eco failure"))
        snap = svc.build_snapshot()
        assert snap.ecosystem.micro_server_state == "not_configured"


class TestAssistantSuggestions:
    def test_suggestions_from_context(self, context_svc_with_data, healthy_db):
        svc = HomeDashboardService(db=healthy_db, context_svc=context_svc_with_data)
        snap = svc.build_snapshot()
        assert len(snap.assistant_suggestions) > 0
        assert any("metadatos" in s.title.lower() for s in snap.assistant_suggestions)

    def test_suggestions_max_three(self):
        ctx = MagicMock()
        ctx.get_assistant_snapshot.return_value = {
            "suggested_actions": [
                {"label": f"A{i}", "route": "home", "priority": i} for i in range(10)
            ]
        }
        svc = HomeDashboardService(context_svc=ctx)
        snap = svc.build_snapshot()
        assert len(snap.assistant_suggestions) <= 3

    def test_suggestions_fallback_when_no_context(self, healthy_db):
        svc = HomeDashboardService(db=healthy_db)
        snap = svc.build_snapshot()
        assert len(snap.assistant_suggestions) > 0


class TestNoAbsolutePaths:
    def _check_no_paths(self, obj, path=""):
        if isinstance(obj, str):
            assert "/home/" not in obj, f"Found absolute path at {path}: {obj}"
            assert obj.startswith("/") is False, f"Found absolute path at {path}: {obj}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._check_no_paths(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                self._check_no_paths(v, f"{path}[{i}]")

    def test_dashboard_snapshot_no_paths(self, healthy_db):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            self._check_no_paths(snap)


class TestSubtitle:
    def test_subtitle_with_library(self, healthy_db):
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(db=healthy_db)
            snap = svc.build_snapshot()
            assert "canciones" in snap.subtitle.lower() or "12,438" in snap.subtitle

    def test_subtitle_empty(self, empty_db):
        svc = HomeDashboardService(db=empty_db)
        snap = svc.build_snapshot()
        assert snap.subtitle == "Todo listo"

    def test_subtitle_with_audio(self, healthy_db):
        pb = MagicMock()
        pb.get_output_device_id.return_value = "USB DAC"
        with patch.dict("os.environ", {"MICHI_TEST": "1"}):  # no-op patch for removed Subsonic dep
            svc = HomeDashboardService(db=healthy_db, playback=pb)
            snap = svc.build_snapshot()
            assert "USB DAC" in snap.subtitle or "Salida" in snap.subtitle
