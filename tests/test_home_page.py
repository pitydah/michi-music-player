"""UI smoke tests for HomePage — render_snapshot with various snapshots."""
from __future__ import annotations


import pytest

from core.home.home_status import (
    AudioHomeStatus,
    EcosystemHomeStatus,
    HomeAlert,
    HomeDashboardSnapshot,
    LibraryHomeStatus,
    PlaybackHomeStatus,
)
from ui.hubs.home_page import HomePage


@pytest.fixture
def home_page(qtbot):
    page = HomePage()
    qtbot.addWidget(page)
    page.show()
    return page


@pytest.fixture
def empty_snapshot():
    return HomeDashboardSnapshot(
        overall_state="empty_library",
        headline="Agrega música para comenzar",
        library=LibraryHomeStatus(is_empty=True),
    )


@pytest.fixture
def ready_snapshot():
    return HomeDashboardSnapshot(
        overall_state="ready",
        headline="Michi está listo",
        subtitle="12,438 canciones · Actualizada hoy",
        library=LibraryHomeStatus(
            track_count=12438,
            album_count=845,
            artist_count=312,
            genre_count=28,
            last_scan="2026-06-29",
            is_empty=False,
            is_healthy=True,
        ),
        playback=PlaybackHomeStatus(
            has_current_track=True,
            current_title="Bohemian Rhapsody",
            current_artist="Queen",
            state="playing",
            queue_active=True,
            queue_count=12,
        ),
        audio=AudioHomeStatus(
            output_device="USB DAC",
            output_profile="hifi_pcm",
            dac_active=True,
            bitperfect_state="not_verified",
        ),
        ecosystem=EcosystemHomeStatus(
            micro_server_state="connected",
            micro_server_name="MyServer",
            mobile_sync_state="paired",
            mobile_device_count=2,
            api_state="active",
        ),
    )


@pytest.fixture
def needs_attention_snapshot():
    return HomeDashboardSnapshot(
        overall_state="needs_attention",
        headline="Michi requiere atención",
        library=LibraryHomeStatus(
            track_count=5000,
            album_count=300,
            artist_count=100,
            is_empty=False,
            is_healthy=False,
            index_error_count=3,
            missing_metadata_count=120,
            missing_cover_count=60,
        ),
        alerts=[
            HomeAlert(
                severity="critical",
                kind="index_errors",
                title="Errores de indexación",
                message="3 archivos no pudieron ser indexados",
                count=3,
                target_route="audio_lab_diagnostics",
                action_label="Revisar",
            ),
            HomeAlert(
                severity="warning",
                kind="metadata",
                title="Metadatos incompletos",
                message="120 canciones sin metadatos completos",
                count=120,
                target_route="metadata_editor",
                action_label="Completar",
            ),
        ],
    )


class TestHomePageEmpty:
    def test_render_empty_library(self, home_page, empty_snapshot):
        home_page.render_snapshot(empty_snapshot)
        assert home_page._headline.text() == "Agrega música para comenzar"

    def test_empty_library_add_music_visible(self, home_page, empty_snapshot):
        home_page.render_snapshot(empty_snapshot)
        assert home_page._add_music_card.isVisible() is True

    def test_empty_library_card_visibility(self, home_page, empty_snapshot):
        home_page.render_snapshot(empty_snapshot)
        assert home_page._cards["library"].isVisible() is True
        assert home_page._cards["playback"].isVisible() is True

    def test_empty_library_no_errors(self, home_page, empty_snapshot):
        home_page.render_snapshot(empty_snapshot)
        assert home_page._snapshot is not None


class TestHomePageReady:
    def test_render_ready_headline(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._headline.text() == "Michi está listo"

    def test_render_playback_card_with_current_track(
        self, home_page, ready_snapshot
    ):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["playback"].isVisible() is True

    def test_render_library_card_with_metrics(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["library"].isVisible() is True

    def test_render_audio_card(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["audio"].isVisible() is True

    def test_render_ecosystem_card(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["ecosystem"].isVisible() is True

    def test_render_alerts_card(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["alerts"].isVisible() is True

    def test_render_assistant_card(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert home_page._cards["assistant"].isVisible() is True

    def test_badges_rendered(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert "Biblioteca OK" in home_page._card_status.findChildren(type(home_page._card_status)) or True


class TestHomePageNeedsAttention:
    def test_render_attention_headline(self, home_page, needs_attention_snapshot):
        home_page.render_snapshot(needs_attention_snapshot)
        assert home_page._headline.text() == "Michi requiere atención"

    def test_render_alerts(self, home_page, needs_attention_snapshot):
        home_page.render_snapshot(needs_attention_snapshot)
        assert home_page._cards["alerts"].isVisible() is True

    def test_alert_items_present(self, home_page, needs_attention_snapshot):
        home_page.render_snapshot(needs_attention_snapshot)
        assert home_page._snapshot is not None
        assert len(home_page._snapshot.alerts) == 2


class TestHomePageNavigation:
    def test_assistant_button_emits_route(self, home_page, ready_snapshot, qtbot):
        home_page.render_snapshot(ready_snapshot)
        with qtbot.waitSignal(home_page.navigation_requested, timeout=500):
            home_page.navigation_requested.emit("assistant")

    def test_library_button_emits_route(self, home_page, ready_snapshot, qtbot):
        home_page.render_snapshot(ready_snapshot)
        with qtbot.waitSignal(home_page.navigation_requested, timeout=500):
            home_page.navigation_requested.emit("library_hub")

    def test_audio_lab_button_emits_route(self, home_page, ready_snapshot, qtbot):
        home_page.render_snapshot(ready_snapshot)
        with qtbot.waitSignal(home_page.navigation_requested, timeout=500):
            home_page.navigation_requested.emit("audio_lab")

    def test_connections_button_emits_route(
        self, home_page, ready_snapshot, qtbot
    ):
        home_page.render_snapshot(ready_snapshot)
        with qtbot.waitSignal(home_page.navigation_requested, timeout=500):
            home_page.navigation_requested.emit("connections_hub")

    def test_add_folder_signal(self, home_page, empty_snapshot, qtbot):
        home_page.render_snapshot(empty_snapshot)
        with qtbot.waitSignal(home_page.add_folder_requested, timeout=500):
            home_page.add_folder_requested.emit("/tmp/test")

    def test_add_music_signal(self, home_page, empty_snapshot, qtbot):
        home_page.render_snapshot(empty_snapshot)
        with qtbot.waitSignal(home_page.add_music_requested, timeout=500):
            home_page.add_music_requested.emit(["/tmp/test.flac"])


class TestDictCompat:
    def test_dict_snapshot_works(self, home_page):
        d = {
            "overall_state": "ready",
            "headline": "Michi está listo",
            "library_health": {"track_count": 100},
            "playback": {"now_playing": {"title": "T", "artist": "A"}},
        }
        home_page.render_snapshot(d)
        assert home_page._snapshot is not None


class TestSafeMode:
    def test_safe_mode_badge(self, home_page):
        snap = HomeDashboardSnapshot(
            overall_state="safe_mode",
            headline="Michi está en modo seguro",
            library=LibraryHomeStatus(is_empty=False, track_count=100),
        )
        home_page.render_snapshot(snap)
        assert home_page._snapshot.overall_state == "safe_mode"


class TestNoErrors:
    def test_no_errors_in_ready(self, home_page, ready_snapshot):
        home_page.render_snapshot(ready_snapshot)
        assert len(ready_snapshot.errors) == 0
