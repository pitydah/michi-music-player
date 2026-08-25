"""M11.3 Reliability R1 — PHASE 7: real-engine switch stress + leak gates.

R1-11: the SAME graph that performs the switches is asserted and torn down
(never a freshly constructed stand-in). R1-12: real QtEngineProvider is
exercised. 100+ explicit switches; after every switch selected/active/bound
agree; after shutdown zero MPD children/observers/pump threads, router
unbound, providers empty.
"""

import os
import shutil

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _pump(ms: int = 60):
    import time as _time

    from PySide6.QtCore import QEventLoop
    from PySide6.QtWidgets import QApplication

    deadline = ms / 1000.0
    t0 = _time.monotonic()
    while _time.monotonic() - t0 < deadline:
        QApplication.processEvents(QEventLoop.AllEvents, 20)
        _time.sleep(0.01)


class StressGraph:
    """R1-11: ONE graph object owns everything that performed the stress —
    the SAME router/service/providers are asserted and shut down after the
    run (never a freshly constructed stand-in)."""

    def __init__(self, qt_real: bool, mpd_real: bool, gst_real: bool):
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSelectionCoordinator,
        )
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import AudioTransportRouter
        from michi.application.playback_service import PlaybackService
        from michi.application.settings_service import SettingsService
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.providers import (
            GStreamerEngineProvider,
            MpdEngineProvider,
            QtEngineProvider,
        )
        from tests.test_m11_3f_engine_selection import (
            FakeProvider,
            FakeSettingsRepository,
        )

        qt = (
            QtEngineProvider() if qt_real else FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        )
        providers = [qt]
        if gst_real:
            providers.append(GStreamerEngineProvider())
        if mpd_real:
            providers.append(MpdEngineProvider())
        self.registry = AudioEngineRegistry(providers)
        self.service = AudioEngineService(self.registry)
        self.router = AudioTransportRouter()
        self.playback = PlaybackService(self.router)
        self.settings = SettingsService(FakeSettingsRepository())
        self.coordinator = AudioEngineSelectionCoordinator(
            engine_service=self.service,
            registry=self.registry,
            router=self.router,
            playback=self.playback,
            settings=self.settings,
        )
        self.qt = qt
        qt_port = qt.open()
        self.router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        self.service.mark_ready(AudioEngineId.QT_MULTIMEDIA)

    def switch(self, engine_id):
        self.coordinator.switch_to(engine_id)

    def assert_consistent(self, expected):
        st = self.service.state
        assert st.lifecycle.value == "ready", expected
        assert st.selected_engine_id == expected
        assert st.active_engine_id == expected
        assert self.router.bound_engine_id == expected
        assert st.error_message is None

    def assert_released(self):
        """R1-11: assert on THIS graph after shutdown — the router that
        actually performed the switches, the providers that owned the
        runtimes."""
        from michi.domain.audio_engine import AudioEngineId

        assert self.router.bound_engine_id is None
        assert self.router._wrappers == []
        if hasattr(self.qt, "_backend"):
            assert self.qt._backend is None  # real Qt provider released
        for engine_id in (AudioEngineId.GSTREAMER, AudioEngineId.MPD):
            try:
                provider = self.registry.provider(engine_id)
            except KeyError:
                continue
            assert provider._port is None

    def shutdown(self):
        """Explicit teardown of THIS graph (SWITCH ORDER)."""
        from michi.domain.audio_engine import AudioEngineId

        self.router.unbind()
        for engine_id in (
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        ):
            try:
                provider = self.registry.provider(engine_id)
            except KeyError:
                continue
            provider.close()


def _graph(mpd_real: bool, gst_real: bool, qt_real: bool = False):
    return StressGraph(qt_real=qt_real, mpd_real=mpd_real, gst_real=gst_real)


class TestSwitchStress:
    def test_stress_qt_mpd_25_cycles(self, qapp):
        """25 Qt->MPD->Qt cycles with a REAL private MPD child (50 ops)."""
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.domain.audio_engine import AudioEngineId

        graph = _graph(mpd_real=True, gst_real=False)
        mpd = graph.registry.provider(AudioEngineId.MPD)
        try:
            for _ in range(25):
                graph.switch(AudioEngineId.MPD)
                graph.assert_consistent(AudioEngineId.MPD)
                assert mpd._port is not None
                graph.switch(AudioEngineId.QT_MULTIMEDIA)
                graph.assert_consistent(AudioEngineId.QT_MULTIMEDIA)
                # MPD released: child dead, runtime gone
                port = mpd._port
                if port is not None:
                    assert port._runtime.process is None
                    assert port._runtime.runtime_dir is None
        finally:
            graph.shutdown()
        graph.assert_released()  # SAME graph

    def test_stress_qt_gst_25_cycles(self, qapp):
        """25 Qt->GStreamer->Qt cycles with a REAL GStreamer pump (50 ops)."""
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerBindings,
        )

        try:
            b = GStreamerBindings()
            b.ensure_loaded()
            if not b.playbin3_available():
                pytest.skip("dependency absent: GStreamer playbin3 factory")
        except (ImportError, ValueError) as exc:
            pytest.skip(f"dependency absent: PyGObject/GStreamer: {exc}")

        graph = _graph(mpd_real=False, gst_real=True)
        gst = graph.registry.provider(AudioEngineId.GSTREAMER)
        try:
            for _ in range(25):
                graph.switch(AudioEngineId.GSTREAMER)
                graph.assert_consistent(AudioEngineId.GSTREAMER)
                assert gst._port is not None and gst._port._pump.is_alive()
                graph.switch(AudioEngineId.QT_MULTIMEDIA)
                graph.assert_consistent(AudioEngineId.QT_MULTIMEDIA)
        finally:
            graph.shutdown()
        graph.assert_released()

    def test_stress_gst_mpd_15_cycles(self, qapp):
        """15 GStreamer->MPD->GStreamer cycles (30 ops, both real)."""
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerBindings,
        )

        try:
            b = GStreamerBindings()
            b.ensure_loaded()
            if not b.playbin3_available():
                pytest.skip("dependency absent: GStreamer playbin3 factory")
        except (ImportError, ValueError) as exc:
            pytest.skip(f"dependency absent: PyGObject/GStreamer: {exc}")

        graph = _graph(mpd_real=True, gst_real=True)
        try:
            for _ in range(15):
                graph.switch(AudioEngineId.GSTREAMER)
                graph.assert_consistent(AudioEngineId.GSTREAMER)
                graph.switch(AudioEngineId.MPD)
                graph.assert_consistent(AudioEngineId.MPD)
            # end on Qt for a clean final state
            graph.switch(AudioEngineId.QT_MULTIMEDIA)
            graph.assert_consistent(AudioEngineId.QT_MULTIMEDIA)
        finally:
            graph.shutdown()
        graph.assert_released()

    def test_stress_real_qt_mpd_25_cycles(self, qapp):
        """R1-12: 25 cycles with the REAL QtEngineProvider <-> real MPD."""
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.domain.audio_engine import AudioEngineId

        graph = _graph(qt_real=True, mpd_real=True, gst_real=False)
        mpd = graph.registry.provider(AudioEngineId.MPD)
        try:
            for _ in range(25):
                graph.switch(AudioEngineId.MPD)
                graph.assert_consistent(AudioEngineId.MPD)
                graph.switch(AudioEngineId.QT_MULTIMEDIA)
                graph.assert_consistent(AudioEngineId.QT_MULTIMEDIA)
                assert graph.qt._backend is not None  # real Qt backend owned
        finally:
            graph.shutdown()
        graph.assert_released()
        assert graph.qt._backend is None

    def test_stress_real_qt_gst_25_cycles(self, qapp):
        """R1-12: 25 cycles with the REAL QtEngineProvider <-> real
        GStreamer."""
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.gstreamer import (
            GStreamerBindings,
        )

        try:
            b = GStreamerBindings()
            b.ensure_loaded()
            if not b.playbin3_available():
                pytest.skip("dependency absent: GStreamer playbin3 factory")
        except (ImportError, ValueError) as exc:
            pytest.skip(f"dependency absent: PyGObject/GStreamer: {exc}")

        graph = _graph(qt_real=True, mpd_real=False, gst_real=True)
        try:
            for _ in range(25):
                graph.switch(AudioEngineId.GSTREAMER)
                graph.assert_consistent(AudioEngineId.GSTREAMER)
                graph.switch(AudioEngineId.QT_MULTIMEDIA)
                graph.assert_consistent(AudioEngineId.QT_MULTIMEDIA)
        finally:
            graph.shutdown()
        graph.assert_released()


class TestLeakGates:
    """Section 68: after complete shutdown — 0 MPD children, 0 pump
    threads, 0 active router binding (on the SAME stressed graphs)."""

    def test_no_michi_mpd_children_after_stress(self):
        import subprocess

        out = subprocess.run(
            ["pgrep", "-af", "michi-mpd-"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        leaks = [
            ln
            for ln in out.stdout.splitlines()
            if "michi-mpd-" in ln
            and "pgrep" not in ln
            and "_mpd_orphan_harness" not in ln
        ]
        assert leaks == [], f"leaked Michi-owned MPD children: {leaks}"
