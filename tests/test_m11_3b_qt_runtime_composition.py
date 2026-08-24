"""M11.3B: productive Qt reference runtime composition gates.

_build_services() must wire PlaybackService/PlaybackCoordinator through the
SAME AudioTransportRouter (one router, one owned Qt backend); the Qt engine
state converges to READY; injected test backends go through the same router
(TEST GRAPH == PRODUCTION GRAPH); shutdown honors SWITCH ORDER.
"""

import os
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication

from michi.application.audio_transport_router import (
    AudioTransportRouter,
)
from michi.domain.audio_engine import AudioEngineId, AudioEngineLifecycle
from michi.domain.playback import PlaybackStatus
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


class _UnavailableProvider:
    engine_id = AudioEngineId.QT_MULTIMEDIA

    def probe(self):
        from michi.domain.audio_engine import AudioEngineDescriptor

        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name="Qt Multimedia",
            available=False,
            unavailable_reason="qt runtime missing",
        )

    def open(self):
        raise AssertionError("open no debe llamarse")

    def close(self):
        pass


class _OpenBoomProvider:
    engine_id = AudioEngineId.QT_MULTIMEDIA

    def __init__(self):
        self.opened = False
        self.closed = False

    def probe(self):
        from michi.domain.audio_engine import AudioEngineDescriptor

        return AudioEngineDescriptor(
            engine_id=self.engine_id,
            display_name="Qt Multimedia",
            available=True,
            implemented=True,
        )

    def open(self):
        self.opened = True
        raise RuntimeError("qt init failed")

    def close(self):
        self.closed = True


class TestStartupTransaction:
    """P1-02: canonical lifecycle — UNINITIALIZED → INITIALIZING → READY."""

    def test_success_progression(self, tmp_path, qapp):
        """La transacción completa se observa con un subscriber registrado
        ANTES de _build_services (reproduce el flujo productivo)."""
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )

        qt_provider = QtEngineProvider()
        registry = AudioEngineRegistry(
            [qt_provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        states = []
        service.subscribe_changed(lambda: states.append(service.state))
        router = AudioTransportRouter()
        try:
            bootstrap._initialize_reference_audio_runtime(
                qt_provider, registry, service, router
            )
            assert service.state.lifecycle == AudioEngineLifecycle.READY
            assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            # la progresión observable: INITIALIZING seguido de READY
            lifecycle_values = [s.lifecycle for s in states]
            assert AudioEngineLifecycle.INITIALIZING in lifecycle_values
            assert lifecycle_values[-1] == AudioEngineLifecycle.READY
        finally:
            qt_provider.close()

    def test_initial_state_uninitialized(self):
        from michi.application.audio_engine_service import AudioEngineService

        service = AudioEngineService()
        assert service.state.lifecycle == AudioEngineLifecycle.UNINITIALIZED

    def test_unavailable_convergence(self, tmp_path, monkeypatch):
        """probe can_activate=False → UNAVAILABLE, open nunca llamado."""
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
        )

        provider = _UnavailableProvider()
        registry = AudioEngineRegistry(
            [provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        with pytest.raises(RuntimeError, match="no activable"):
            bootstrap._initialize_reference_audio_runtime(
                provider, registry, service, router
            )
        state = service.state
        assert state.lifecycle == AudioEngineLifecycle.UNAVAILABLE
        assert state.active_engine_id is None
        assert state.error_message is not None
        assert router.bound_engine_id is None

    def test_open_failure_convergence(self, tmp_path, monkeypatch):
        """open raise → FAILED, active None, router unbound."""
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
        )

        provider = _OpenBoomProvider()
        registry = AudioEngineRegistry(
            [provider, GStreamerEngineProvider(), MpdEngineProvider()]
        )
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        with pytest.raises(RuntimeError, match="qt init failed"):
            bootstrap._initialize_reference_audio_runtime(
                provider, registry, service, router
            )
        state = service.state
        assert provider.opened is True
        assert state.lifecycle == AudioEngineLifecycle.FAILED
        assert state.active_engine_id is None
        assert "qt init failed" in state.error_message
        assert router.bound_engine_id is None

    def test_bind_failure_cleans_up_provider(self, tmp_path, monkeypatch):
        """bind raise → provider.close called, FAILED, sin half-runtime."""
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from tests.audio_engine_fakes import RecordingBackend

        class BindBoomRouter(AudioTransportRouter):
            def bind(self, engine_id, audio_port):
                raise RuntimeError("bind failed")

        provider = _OpenBoomProvider()

        # open raise en este provider — para bind failure usamos open OK
        class _BindBoomProvider(_OpenBoomProvider):
            def open(self):
                self.opened = True
                return RecordingBackend("B")

        provider = _BindBoomProvider()
        registry = AudioEngineRegistry([provider])
        service = AudioEngineService(registry)
        router = BindBoomRouter()
        with pytest.raises(RuntimeError, match="bind failed"):
            bootstrap._initialize_reference_audio_runtime(
                provider, registry, service, router
            )
        state = service.state
        assert provider.opened is True
        assert provider.closed is True  # cleanup del provider
        assert state.lifecycle == AudioEngineLifecycle.FAILED
        assert state.active_engine_id is None


class TestProviderAuthority:
    """P1-01: exactamente UN provider canónico de Qt."""

    def test_registry_provider_is_productive_provider(self, tmp_path, qapp):
        graph = _graph(tmp_path)
        try:
            assert (
                graph.audio_engine_registry.provider(AudioEngineId.QT_MULTIMEDIA)
                is graph.qt_engine_provider
            )
            # un solo backend owned
            first = graph.qt_engine_provider.open()
            assert first is graph.qt_engine_provider.open()
            assert graph.audio_router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        finally:
            graph.qt_engine_provider.close()

    def test_playback_and_coordinator_share_router(self, tmp_path, qapp):
        """PlaybackService y PlaybackCoordinator (instancia REAL) consumen el
        MISMO objeto router — identidad de objeto, no texto de fuente."""
        from michi.application.coordinator import PlaybackCoordinator

        graph = _graph(tmp_path)
        try:
            assert graph.playback._audio is graph.audio_router
            # instancia REAL del coordinator con el wiring productivo
            coordinator = PlaybackCoordinator(graph.audio_router, graph.playback)
            assert coordinator._audio is graph.audio_router
            assert coordinator._audio is graph.playback._audio
            coordinator.stop()
        finally:
            graph.qt_engine_provider.close()


class TestFirstErrorWinsCleanup:
    """P1-01: un fallo de cleanup secundario (router.unbind raise) NUNCA
    reemplaza el error primario del startup."""

    def test_cleanup_unbind_failure_preserves_primary_error(self, tmp_path):
        from michi import bootstrap
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )
        from tests.audio_engine_fakes import RecordingBackend

        class UnbindBoomRouter(AudioTransportRouter):
            def bind(self, engine_id, audio_port):
                raise RuntimeError("primary bind failure")

            def unbind(self):
                raise RuntimeError("secondary unbind failure")

        class OkOpenProvider:
            engine_id = AudioEngineId.QT_MULTIMEDIA

            def __init__(self):
                self.closed = False

            def probe(self):
                from michi.domain.audio_engine import AudioEngineDescriptor

                return AudioEngineDescriptor(
                    engine_id=self.engine_id,
                    display_name="Qt Multimedia",
                    available=True,
                    implemented=True,
                )

            def open(self):
                return RecordingBackend("B")

            def close(self):
                self.closed = True

        provider = OkOpenProvider()
        registry = AudioEngineRegistry([provider])
        service = AudioEngineService(registry)
        router = UnbindBoomRouter()
        with pytest.raises(RuntimeError, match="primary bind failure"):
            bootstrap._initialize_reference_audio_runtime(
                provider, registry, service, router
            )
        state = service.state
        assert state.lifecycle == AudioEngineLifecycle.FAILED
        assert state.active_engine_id is None
        assert "primary bind failure" in state.error_message
        assert provider.closed is True  # cleanup del provider intentado


class TestCallbackParity:
    """Cada evento del backend llega exactamente una vez; tras unbind, cero."""

    def test_all_event_types_forwarded_exactly_once(self, tmp_path, qapp):
        fake = RecordingBackend("F")
        graph = _graph(tmp_path, backend=fake)
        try:
            events = []
            router = graph.audio_router
            router.subscribe_end_of_media(lambda: events.append("eom"))
            router.subscribe_position_changed(lambda ms: events.append(f"pos:{ms}"))
            router.subscribe_duration_changed(lambda ms: events.append(f"dur:{ms}"))
            router.subscribe_media_accepted(lambda p: events.append(f"acc:{p.name}"))
            router.subscribe_media_rejected(
                lambda p, r: events.append(f"rej:{p.name}:{r}")
            )
            router.subscribe_playback_state_changed(
                lambda s: events.append(f"st:{s.name}")
            )
            fake.fire_end_of_media()
            fake.fire_position(1)
            fake.fire_duration(1234)
            fake.fire_media_accepted(Path("/m/a.mp3"))
            fake.fire_media_rejected(Path("/m/b.mp3"), "no")
            fake.fire_state(PlaybackStatus.PLAYING)
            assert events == [
                "eom",
                "pos:1",
                "dur:1234",
                "acc:a.mp3",
                "rej:b.mp3:no",
                "st:PLAYING",
            ]
        finally:
            graph.audio_router.unbind()

    def test_zero_delivery_after_unbind(self, tmp_path, qapp):
        fake = RecordingBackend("F")
        graph = _graph(tmp_path, backend=fake)
        events = []
        graph.audio_router.subscribe_end_of_media(lambda: events.append("eom"))
        graph.audio_router.unbind()
        fake.fire_end_of_media()
        assert events == []
        graph.qt_engine_provider.close()


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
            # M11.3C: GStreamer implemented=True — can_activate es
            # runtime-dependent (GI presente)
            assert graph.audio_engine_registry.can_activate(
                AudioEngineId.GSTREAMER
            ) == graph.audio_engine_registry.is_available(AudioEngineId.GSTREAMER)
            # runtime-dependent: MPD can_activate == executable instalado
            import shutil

            assert graph.audio_engine_registry.can_activate(AudioEngineId.MPD) == (
                shutil.which("mpd") is not None
            )
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
        """M11.3G selected-first startup: an activation failure does NOT
        crash the graph — the state converges honestly to FAILED (active
        None, router unbound) and the rest of Michi can keep existing
        without playback. (Pre-G the forced-Qt startup re-raised; G §15
        requires honest degradation instead. The original-error raise is
        still exercised by the injected-backend test seam path.)"""
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
        from michi.domain.audio_engine import AudioEngineLifecycle

        graph = _build_services(tmp_path / "michi.db")
        state = graph.audio_engine_service.state
        assert state.lifecycle == AudioEngineLifecycle.FAILED
        assert state.active_engine_id is None
        assert "qt init failed" in state.error_message
        assert graph.audio_router.bound_engine_id is None

    def test_unavailable_probe_blocks_activation(self):
        """probe unavailable → can_activate False → never READY."""
        provider = QtEngineProvider()
        desc = provider.probe()
        if desc.available:
            pytest.skip("Qt runtime disponible en esta máquina")
        assert desc.can_activate is False
        assert desc.activation_blocker is not None
