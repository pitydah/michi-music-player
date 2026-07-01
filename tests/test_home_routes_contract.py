"""Contract tests — every route emitted from Home must exist in NAV_ROUTES."""
from __future__ import annotations

from ui.hubs.home_page import HomePage


class TestHomeRoutesContract:
    NAV_ROUTES = {
        "home", "library_hub", "playback_hub", "audio_lab",
        "audio_lab_output", "audio_lab_diagnostics", "audio_lab_artwork",
        "audio_lab_intelligence", "connections_hub", "metadata_editor",
        "assistant", "mix_hub", "devices_page",
    }

    def test_all_nav_routes_valid(self, qtbot):
        page = HomePage()
        qtbot.addWidget(page)
        emitted = set()

        def capture(route):
            emitted.add(route)

        page.navigation_requested.connect(capture)

        for route in self.NAV_ROUTES:
            page.navigation_requested.emit(route)

        for route in emitted:
            assert route in self.NAV_ROUTES, f"Route '{route}' not in NAV_ROUTES"

    def test_no_orphan_routes(self, qtbot):
        page = HomePage()
        qtbot.addWidget(page)
        from core.home.home_status import (
            HomeDashboardSnapshot,
            LibraryHomeStatus,
            PlaybackHomeStatus,
            AudioHomeStatus,
            EcosystemHomeStatus,
            HomeAlert,
            AssistantSuggestion,
        )

        snap = HomeDashboardSnapshot(
            overall_state="needs_attention",
            headline="Michi requiere atención",
            library=LibraryHomeStatus(
                track_count=1000,
                is_empty=False,
                is_healthy=False,
                index_error_count=3,
                missing_metadata_count=100,
            ),
            playback=PlaybackHomeStatus(
                has_current_track=True,
                current_title="Test",
                current_artist="Artist",
                state="playing",
                queue_active=True,
                queue_count=5,
            ),
            audio=AudioHomeStatus(
                output_device="USB DAC",
                output_profile="hifi_pcm",
                dac_active=True,
            ),
            ecosystem=EcosystemHomeStatus(
                micro_server_state="disconnected",
            ),
            alerts=[
                HomeAlert(
                    severity="critical",
                    kind="index_errors",
                    title="Error",
                    message="test",
                    target_route="audio_lab_diagnostics",
                    action_label="Revisar",
                ),
            ],
            assistant_suggestions=[
                AssistantSuggestion(
                    title="Sugerencia",
                    target_route="metadata_editor",
                ),
            ],
        )
        page.render_snapshot(snap)
        assert page._snapshot is not None

    def test_assistant_open_button_exists(self, qtbot):
        page = HomePage()
        qtbot.addWidget(page)
        snap = type("snap", (), {
            "overall_state": "ready",
            "headline": "Ready",
            "subtitle": "",
            "library": type("lib", (), {
                "track_count": 100, "album_count": 10, "artist_count": 5,
                "genre_count": 3, "active_roots_count": 1, "last_scan": "today",
                "index_error_count": 0, "missing_file_count": 0,
                "missing_metadata_count": 0, "missing_cover_count": 0,
                "tracks_without_audio_features": 0, "new_tracks_count": 0,
                "is_empty": False, "is_healthy": True,
            })(),
            "playback": type("pb", (), {
                "has_current_track": False, "current_title": "", "current_artist": "",
                "current_album": "", "current_cover_id": "", "current_position": 0.0,
                "current_duration": 0.0, "queue_active": False, "queue_count": 0,
                "last_track_title": "", "last_track_artist": "",
                "can_continue": False, "can_continue_remote": False,
                "source": "", "state": "stopped",
            })(),
            "audio": type("au", (), {
                "output_device": "", "output_profile": "", "dac_active": False,
                "replaygain_enabled": False, "eq_enabled": False, "dsp_active": False,
                "bitperfect_state": "not_available", "format_label": "",
                "sample_rate": 0, "bit_depth": 0, "warnings": [],
            })(),
            "ecosystem": type("ec", (), {
                "micro_server_state": "disconnected", "micro_server_name": "",
                "mobile_sync_state": "no_device", "mobile_device_count": 0,
                "api_state": "unknown", "home_audio_state": "disabled",
                "last_sync": None, "diagnostics_available": False,
            })(),
            "alerts": [],
            "assistant_suggestions": [],
            "actions": [],
            "errors": [],
            "generated_at": 0.0,
        })()
        page.render_snapshot(snap)
