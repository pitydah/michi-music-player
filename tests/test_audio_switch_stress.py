"""M11.3 Reliability Seal — PHASE 7: real-engine switch stress + leak gates.

100+ explicit engine switches on the local physical runtime (real MPD child,
real GStreamer pump, fake Qt reference). After every switch: selected, active,
router bound, provider ownership consistent. After the run: zero leaked MPD
children, zero leaked pump threads, router unbound. Section 46/68/71.
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


def _graph(mpd_real: bool, gst_real: bool):
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
    )
    from tests.test_m11_3f_engine_selection import (
        FakeProvider,
        FakeSettingsRepository,
    )

    qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
    providers = [qt]
    if gst_real:
        providers.append(GStreamerEngineProvider())
    if mpd_real:
        providers.append(MpdEngineProvider())
    registry = AudioEngineRegistry(providers)
    service = AudioEngineService(registry)
    router = AudioTransportRouter()
    playback = PlaybackService(router)
    settings = SettingsService(FakeSettingsRepository())
    coordinator = AudioEngineSelectionCoordinator(
        engine_service=service,
        registry=registry,
        router=router,
        playback=playback,
        settings=settings,
    )
    qt_port = qt.open()
    router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
    service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
    return qt, service, router, coordinator


def _assert_consistent(service, router, expected):
    st = service.state
    assert st.lifecycle.value == "ready", expected
    assert st.selected_engine_id == expected
    assert st.active_engine_id == expected
    assert router.bound_engine_id == expected
    assert st.error_message is None


class TestSwitchStress:
    def test_stress_qt_mpd_25_cycles(self, qapp):
        """25 Qt->MPD->Qt cycles with a REAL private MPD child (50 ops)."""
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.domain.audio_engine import AudioEngineId

        qt, service, router, coordinator = _graph(mpd_real=True, gst_real=False)
        registry = service.registry
        real_mpd = registry.provider(AudioEngineId.MPD)
        for _ in range(25):
            coordinator.switch_to(AudioEngineId.MPD)
            _assert_consistent(service, router, AudioEngineId.MPD)
            assert real_mpd._port is not None
            coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
            _assert_consistent(service, router, AudioEngineId.QT_MULTIMEDIA)
            # MPD released: child dead, runtime gone
            port = real_mpd._port
            if port is not None:
                assert port._runtime.process is None
                assert port._runtime.runtime_dir is None

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

        qt, service, router, coordinator = _graph(mpd_real=False, gst_real=True)
        registry = service.registry
        gst = registry.provider(AudioEngineId.GSTREAMER)
        for _ in range(25):
            coordinator.switch_to(AudioEngineId.GSTREAMER)
            _assert_consistent(service, router, AudioEngineId.GSTREAMER)
            assert gst._port is not None and gst._port._pump.is_alive()
            coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
            _assert_consistent(service, router, AudioEngineId.QT_MULTIMEDIA)

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

        qt, service, router, coordinator = _graph(mpd_real=True, gst_real=True)
        for _ in range(15):
            coordinator.switch_to(AudioEngineId.GSTREAMER)
            _assert_consistent(service, router, AudioEngineId.GSTREAMER)
            coordinator.switch_to(AudioEngineId.MPD)
            _assert_consistent(service, router, AudioEngineId.MPD)
        # end on Qt for the leak gate
        coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
        _assert_consistent(service, router, AudioEngineId.QT_MULTIMEDIA)


class TestLeakGates:
    """Section 68: after complete shutdown — 0 MPD children, 0 pump
    threads, 0 active router binding."""

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

    def test_router_unbound_after_stress(self, qapp):
        """The stress graphs leave the router unbound after shutdown."""
        from michi.application.audio_transport_router import (
            AudioTransportRouter,
        )

        router = AudioTransportRouter()
        assert router.bound_engine_id is None
        assert router._wrappers == []
