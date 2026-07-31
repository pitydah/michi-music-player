from __future__ import annotations

"""Fase 9 — unified Now Playing state: bridge exposure, transport show* flags,
and the shared PlaybackStatusIndicator mapping."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QSignalSpy

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

pytestmark = [pytest.mark.qml_module("playback")]

REPO_ROOT = Path(__file__).resolve().parents[3]
QML_ROOT = REPO_ROOT / "ui_qml"
COMPONENTS = QML_ROOT / "components"

_MOCK = object()


def _make_bridge(player: object = _MOCK) -> NowPlayingBridge:
    if player is _MOCK:
        player = MagicMock()
        player.state = ""
        player.current = None
        player.current_filepath = ""
        player.current_path = ""
    quality = MagicMock()
    quality.probe.return_value = {"ok": False}
    return NowPlayingBridge(
        player_service=player,
        queue_service=MagicMock(),
        audio_quality_adapter=quality,
    )


@pytest.fixture
def qml_engine(qapp) -> QQmlEngine:
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_ROOT))
    return engine


def _create_component(engine: QQmlEngine, name: str) -> tuple[QQmlComponent, QObject]:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(COMPONENTS / name)))
    assert component.isReady(), [error.toString() for error in component.errors()]
    instance = component.create()
    assert instance is not None, [error.toString() for error in component.errors()]
    return component, instance


class TestPlaybackStatusExposure:
    """The bridge exposes the raw playback status string to QML."""

    def test_playback_status_defaults_idle(self):
        bridge = _make_bridge()
        assert bridge.playbackStatus == "idle"

    def test_playback_status_unavailable_without_player(self):
        bridge = _make_bridge(player=None)
        assert bridge.playbackStatus == "unavailable"

    @pytest.mark.parametrize(
        "state",
        ["playing", "paused", "stopped", "buffering", "reconnecting", "failed"],
    )
    def test_playback_status_passthrough(self, state: str):
        bridge = _make_bridge()
        bridge._on_state(state)
        assert bridge.playbackStatus == state


class TestBackendInfoExposure:
    """The bridge exposes the effective backend id/state to QML."""

    def test_defaults_with_naive_mock(self):
        bridge = _make_bridge()
        assert bridge.backendId == ""
        assert bridge.backendState == "ready"
        assert not bridge.backendSwitching
        assert not bridge.degradedOutput

    def test_unavailable_without_player(self):
        bridge = _make_bridge(player=None)
        assert bridge.backendState == "unavailable"

    def test_backend_state_from_player(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "mpd", "state": "ready", "fallback": False,
        }
        bridge = _make_bridge(player)
        assert bridge.backendId == "mpd"
        assert bridge.backendState == "ready"

    def test_fallback_maps_to_degraded(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "gstreamer", "state": "degraded", "fallback": True,
        }
        bridge = _make_bridge(player)
        assert bridge.backendId == "gstreamer"
        assert bridge.backendState == "degraded"
        assert bridge.degradedOutput

    def test_initializing_maps_to_switching(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "mpd", "state": "initializing", "fallback": False,
        }
        bridge = _make_bridge(player)
        assert bridge.backendSwitching

    def test_failed_backend_state(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "", "state": "failed", "fallback": False,
        }
        bridge = _make_bridge(player)
        assert bridge.backendState == "failed"

    def test_backend_changed_resyncs_and_emits(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "gstreamer", "state": "ready", "fallback": False,
        }
        bridge = _make_bridge(player)
        spy = QSignalSpy(bridge.backendInfoChanged)
        player.get_backend_state.return_value = {
            "id": "mpd", "state": "ready", "fallback": False,
        }
        bridge._on_backend_changed("gstreamer", "mpd")
        assert bridge.backendId == "mpd"
        assert spy.count() == 1

    def test_backend_changed_without_delta_does_not_emit(self):
        player = MagicMock()
        player.get_backend_state.return_value = {
            "id": "gstreamer", "state": "ready", "fallback": False,
        }
        bridge = _make_bridge(player)
        spy = QSignalSpy(bridge.backendInfoChanged)
        bridge._on_backend_changed("gstreamer", "gstreamer")
        assert spy.count() == 0


class TestPlayerServiceBackendState:
    """PlayerService exposes effective backend state and reconnecting."""

    @pytest.fixture(autouse=True)
    def _patch_gst(self):
        from PySide6.QtCore import QObject, QTimer
        patches = [
            patch("audio.player.Gst", MagicMock()),
            patch("audio.player.GLib", MagicMock()),
            patch("audio.player.gi", MagicMock()),
            patch("audio.player.np", MagicMock()),
            patch("audio.player.QObject", QObject),
            patch("audio.player.QTimer", QTimer),
            patch("audio.player_service.MpdServiceManager", MagicMock(spec=object)),
            patch("audio.player_service.MpdBackend", MagicMock(spec=object)),
        ]
        for p in patches:
            p.start()
        yield
        for p in patches:
            p.stop()

    def test_get_backend_state_shape(self, qapp):
        from audio.player_service import PlayerService
        service = PlayerService(engine=None)
        info = service.get_backend_state()
        assert info["id"] == "gstreamer"
        assert info["state"] in ("uninitialized", "ready")
        assert info["fallback"] is False

    def test_reconnecting_emitted_on_stream_retry(self, qapp):
        from audio.player_service import PlayerService
        engine = MagicMock()
        engine.current = None
        service = PlayerService(engine)
        state_spy = QSignalSpy(service.state_changed)
        error_spy = QSignalSpy(service.error_occurred)
        service._retry_url = "http://stream.example/live"
        service._on_error("STREAM_NETWORK_ERROR: connection lost")
        emitted = [state_spy.at(index)[0] for index in range(state_spy.count())]
        assert "reconnecting" in emitted
        assert error_spy.count() == 0
        service._retry_timer.stop()


class TestPlaybackTransportShowFlags:
    """PlaybackTransport respects showShuffle/Previous/Next/Repeat (9.2)."""

    def test_show_flags_toggle_button_visibility(self, qml_engine: QQmlEngine):
        component, transport = _create_component(qml_engine, "PlaybackTransport.qml")
        try:
            for prop, obj_name in (
                ("showShuffle", "nowPlayingShuffleButton"),
                ("showPrevious", "nowPlayingPreviousButton"),
                ("showNext", "nowPlayingNextButton"),
                ("showRepeat", "nowPlayingRepeatButton"),
            ):
                button = transport.findChild(QObject, obj_name)
                assert button is not None, f"Missing {obj_name}"
                assert button.property("visible") is True
                transport.setProperty(prop, False)
                assert button.property("visible") is False, prop
                transport.setProperty(prop, True)
                assert button.property("visible") is True, prop
        finally:
            transport.deleteLater()
            component.deleteLater()

    def test_bar_variant_keeps_buttons_visible(self, qml_engine: QQmlEngine):
        component, transport = _create_component(qml_engine, "PlaybackTransport.qml")
        try:
            transport.setProperty("variant", "bar")
            for obj_name in (
                "nowPlayingShuffleButton",
                "nowPlayingPreviousButton",
                "nowPlayingNextButton",
                "nowPlayingRepeatButton",
            ):
                button = transport.findChild(QObject, obj_name)
                assert button.property("visible") is True, obj_name
        finally:
            transport.deleteLater()
            component.deleteLater()

    def test_play_button_always_visible(self, qml_engine: QQmlEngine):
        component, transport = _create_component(qml_engine, "PlaybackTransport.qml")
        try:
            button = transport.findChild(QObject, "nowPlayingPlayPauseButton")
            assert button is not None
            assert button.property("visible") is True
        finally:
            transport.deleteLater()
            component.deleteLater()


class TestPlaybackStatusIndicator:
    """Shared state mapping used by NowPlayingPage and NowPlayingBar (9.3)."""

    def _indicator(self, qml_engine: QQmlEngine):
        return _create_component(qml_engine, "PlaybackStatusIndicator.qml")

    def test_playing_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "playing")
            assert indicator.property("stateText") == "Reproduciendo"
            assert indicator.property("stateKind") == "success"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_playing_shows_effective_backend(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "playing")
            indicator.setProperty("backendId", "mpd")
            assert "MPD" in indicator.property("stateText")
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_live_stream_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "playing")
            indicator.setProperty("live", True)
            assert indicator.property("stateText") == "Stream en vivo"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_paused_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "paused")
            assert indicator.property("stateText") == "Pausado"
            assert indicator.property("stateKind") == "info"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_buffering_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "buffering")
            assert indicator.property("stateText") == "Cargando búfer..."
            assert indicator.property("stateKind") == "info"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_loading_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "loading")
            assert indicator.property("stateText") == "Cargando..."
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_reconnecting_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "reconnecting")
            assert indicator.property("stateText") == "Reconectando..."
            assert indicator.property("stateKind") == "reconnecting"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_failed_playback_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "failed")
            assert indicator.property("stateKind") == "error"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_stopped_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "stopped")
            assert indicator.property("stateText") == "Detenido"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_no_track_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            assert indicator.property("stateText") == "Sin reproducción"
            assert indicator.property("stateKind") == "disconnected"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_degraded_output_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("playbackStatus", "playing")
            indicator.setProperty("backendState", "degraded")
            indicator.setProperty("backendId", "gstreamer")
            assert "degradada" in indicator.property("stateText")
            assert "GStreamer" in indicator.property("stateText")
            assert indicator.property("stateKind") == "degraded"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_backend_switching_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("hasTrack", True)
            indicator.setProperty("backendState", "initializing")
            indicator.setProperty("backendId", "mpd")
            assert "MPD" in indicator.property("stateText")
            assert indicator.property("stateKind") == "info"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_backend_failed_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("backendState", "failed")
            assert indicator.property("stateKind") == "error"
        finally:
            indicator.deleteLater()
            component.deleteLater()

    def test_backend_unavailable_state(self, qml_engine: QQmlEngine):
        component, indicator = self._indicator(qml_engine)
        try:
            indicator.setProperty("backendState", "unavailable")
            assert indicator.property("stateText") == "Reproductor no disponible"
            assert indicator.property("stateKind") == "error"
        finally:
            indicator.deleteLater()
            component.deleteLater()


class TestUnifiedSurfaceWiring:
    """Static wiring checks: bar/page share the bridge model and flags (9.1/9.4)."""

    def test_page_uses_playback_status_indicator(self):
        page = (QML_ROOT / "pages" / "nowplaying" / "NowPlayingPage.qml").read_text(
            encoding="utf-8"
        )
        assert "PlaybackStatusIndicator {" in page
        assert "playbackStatus:" in page
        assert "backendState:" in page
        assert "backendId:" in page

    def test_bar_passes_real_capability_flags(self):
        bar = (COMPONENTS / "NowPlayingBar.qml").read_text(encoding="utf-8")
        for flag in ("shuffleSupported", "previousSupported", "nextSupported", "repeatSupported"):
            assert flag in bar, flag

    def test_transport_respects_show_flags(self):
        src = (COMPONENTS / "PlaybackTransport.qml").read_text(encoding="utf-8")
        for flag in ("showShuffle", "showPrevious", "showNext", "showRepeat"):
            assert f"root.{flag} &&" in src, flag

    def test_bar_and_page_use_same_bridge_and_property_names(self):
        bar = (COMPONENTS / "NowPlayingBar.qml").read_text(encoding="utf-8")
        page_dir = QML_ROOT / "pages" / "nowplaying"
        page = (page_dir / "NowPlayingPage.qml").read_text(encoding="utf-8")
        for source in (bar, page):
            assert 'typeof nowplayingBridge !== "undefined" ? nowplayingBridge : null' in source
        for prop in (
            "isPlaying", "position", "duration", "volume", "muted",
            "repeatMode", "shuffleEnabled", "playbackStatus", "backendState",
        ):
            assert f"root.ps.{prop}" in bar, prop
            assert f"root.ps.{prop}" in page, prop
        # The page delegates track metadata to subcomponents bound to the
        # same bridge object — names must match the bar's.
        metadata = (page_dir / "NowPlayingMetadata.qml").read_text(encoding="utf-8")
        for prop in ("trackTitle", "trackArtist", "trackAlbum"):
            assert f"root.ps.{prop}" in bar, prop
            assert f"root.ps.{prop}" in metadata, prop
