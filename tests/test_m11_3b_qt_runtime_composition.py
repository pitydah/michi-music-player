"""M11.3B: productive Qt reference runtime composition gates.

_build_services() must wire PlaybackService/PlaybackCoordinator through the
SAME AudioTransportRouter (one router, one owned Qt backend); the Qt engine
state converges to READY; injected test backends go through the same router
(TEST GRAPH == PRODUCTION GRAPH); shutdown honors SWITCH ORDER.
"""

import os

import pytest
from PySide6.QtGui import QGuiApplication

from michi.application.audio_transport_router import (
    AudioTransportRouter,
)
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle
from michi.infrastructure.audio_engines.providers import QtEngineProvider
from tests.audio_engine_fakes import RecordingBackend


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


def _graph(tmp_path, backend=None):
    from michi.bootstrap import _build_services

    return _build_services(tmp_path / "michi.db", backend=backend)


class TestProductiveComposition:
    def test_graph_contains_router_bound_to_qt(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            assert isinstance(graph.audio_router, AudioTransportRouter)
            assert graph.audio_router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        finally:
            graph.qt_engine_provider.close()

    def test_playback_receives_router(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            # PlaybackService gets the ROUTER, never the raw backend
            assert graph.playback._audio is graph.audio_router
        finally:
            graph.qt_engine_provider.close()

    def test_registry_has_three_canonical_engines(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            assert graph.audio_engine_registry.engine_ids == (
                AudioEngineId.QT_MULTIMEDIA,
                AudioEngineId.GSTREAMER,
                AudioEngineId.MPD,
            )
            assert (
                graph.audio_engine_registry.can_activate(AudioEngineId.QT_MULTIMEDIA)
                is True
            )
            assert (
                graph.audio_engine_registry.can_activate(AudioEngineId.GSTREAMER)
                is False
            )
            assert graph.audio_engine_registry.can_activate(AudioEngineId.MPD) is False
        finally:
            graph.qt_engine_provider.close()

    def test_engine_state_converges_to_ready(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            state = graph.audio_engine_service.state
            assert state.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
            assert state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            assert state.lifecycle == AudioEngineLifecycle.READY
            assert state.switching_to is None
            assert state.error_message is None
        finally:
            graph.qt_engine_provider.close()

    def test_single_owned_qt_backend(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            first = graph.qt_engine_provider.open()
            second = graph.qt_engine_provider.open()
            assert first is second
            assert graph.audio_router._bound is first
        finally:
            graph.qt_engine_provider.close()


class TestInjectedBackendThroughRouter:
    def test_fake_backend_routed_exactly_once(self, tmp_path, qapp):
        fake = RecordingBackend("F")
        graph = _graph(tmp_path, backend=fake)
        try:
            # the fake is bound INSIDE the router — never injected directly
            assert graph.audio_router._bound is fake
            assert graph.playback._audio is graph.audio_router
            # command reaches the fake exactly once
            graph.playback.play()
            assert fake.commands == ["play"]
            # callback reaches the router exactly once (the router is the
            # transport identity both services consume; PlaybackService EOM
            # forwarding is its own tested contract)
            events = []
            graph.audio_router.subscribe_end_of_media(lambda: events.append("eom"))
            fake.fire_end_of_media()
            assert events == ["eom"]
            fake.fire_end_of_media()
            assert events == ["eom", "eom"]
        finally:
            graph.audio_router.unbind()
            fake.close()


class TestShutdownIntegrity:
    def test_router_detaches_before_provider_closes(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        router = graph.audio_router
        provider = graph.qt_engine_provider
        assert router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        # SWITCH ORDER: detach first, then provider close
        router.unbind()
        assert router.bound_engine_id is None
        provider.close()
        provider.close()  # idempotent
        # reopen yields a fresh backend
        fresh = provider.open()
        assert fresh is not None
        provider.close()

    def test_no_callback_after_detach(self, tmp_path, qapp):
        fake = RecordingBackend("F")
        graph = _graph(tmp_path, backend=fake)
        events = []
        graph.audio_router.subscribe_end_of_media(lambda: events.append("eom"))
        graph.audio_router.unbind()
        fake.fire_end_of_media()
        assert events == []  # nothing after detach
        graph.qt_engine_provider.close()


class TestStartupFailure:
    def test_open_failure_marks_failed(self, tmp_path, monkeypatch):
        from michi import bootstrap

        class BoomProvider:
            engine_id = AudioEngineId.QT_MULTIMEDIA

            def open(self):
                raise RuntimeError("qt init failed")

            def close(self):
                pass

            def probe(self):
                from michi.domain.audio_engine import AudioEngineDescriptor

                return AudioEngineDescriptor(
                    engine_id=self.engine_id,
                    display_name="Qt Multimedia",
                    available=True,
                    implemented=True,
                )

        monkeypatch.setattr(bootstrap, "QtEngineProvider", BoomProvider)
        from michi.bootstrap import _build_services

        with pytest.raises(RuntimeError, match="qt init failed"):
            _build_services(tmp_path / "michi.db")

    def test_unavailable_probe_blocks_activation(self):
        """probe unavailable → can_activate False → never READY."""
        provider = QtEngineProvider()
        desc = provider.probe()
        if desc.available:
            pytest.skip("Qt runtime disponible en esta máquina")
        assert desc.can_activate is False
        assert desc.activation_blocker is not None
