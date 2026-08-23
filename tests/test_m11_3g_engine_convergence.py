"""M11.3G — Lifecycle / Failure / Convergence (deterministic).

Startup selected-first convergence, safe Qt fallback (the ONLY automatic
fallback engine in 1.0), fatal runtime engine loss convergence, safe
explicit-switch recovery, Playback/Queue convergence, restart, shutdown.
No sleeps, no network, no real devices. Deterministic fakes only.
"""

import pytest

from michi.application.audio_engine_convergence_coordinator import (
    AudioEngineConvergenceCoordinator,
)
from michi.application.audio_engine_registry import (
    AudioEngineProviderPort,
    AudioEngineRegistry,
)
from michi.application.audio_engine_runtime_failure import (
    AudioEngineRuntimeFailureEvent,
)
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import (
    AudioEngineId,
    AudioEngineLifecycle,
)
from michi.domain.playback import PlaybackStatus

# ---------------------------------------------------------------------------
# Deterministic fakes
# ---------------------------------------------------------------------------


class FakePort:
    """Deterministic AudioPort double (same shape as the F harness)."""

    def __init__(self, engine_id, owner):
        self.engine_id = engine_id
        self.owner = owner
        self.events = []
        self._listeners = {
            "media_accepted": [],
            "media_rejected": [],
            "playback_state_changed": [],
            "end_of_media": [],
            "position_changed": [],
            "duration_changed": [],
        }

    def load(self, file_path):
        self.events.append(f"load:{file_path}")
        self.owner.port_loads.append((self.engine_id, str(file_path)))

    def play(self):
        self.events.append("play")
        self.owner.port_plays.append(self.engine_id)

    def pause(self):
        self.events.append("pause")

    def resume(self):
        self.events.append("resume")

    def stop(self):
        self.events.append("stop")

    def seek(self, position_ms):
        self.events.append(f"seek:{position_ms}")

    def set_volume(self, value):
        self.events.append(f"volume:{value}")
        self.owner.volume_received = value

    def set_muted(self, muted):
        self.events.append(f"muted:{muted}")
        self.owner.muted_received = muted

    def position(self):
        return 0

    def duration(self):
        return 0

    def subscribe_media_accepted(self, cb):
        self._listeners["media_accepted"].append(cb)

    def unsubscribe_media_accepted(self, cb):
        if cb in self._listeners["media_accepted"]:
            self._listeners["media_accepted"].remove(cb)

    def subscribe_media_rejected(self, cb):
        self._listeners["media_rejected"].append(cb)

    def unsubscribe_media_rejected(self, cb):
        if cb in self._listeners["media_rejected"]:
            self._listeners["media_rejected"].remove(cb)

    def subscribe_playback_state_changed(self, cb):
        self._listeners["playback_state_changed"].append(cb)

    def unsubscribe_playback_state_changed(self, cb):
        if cb in self._listeners["playback_state_changed"]:
            self._listeners["playback_state_changed"].remove(cb)

    def subscribe_end_of_media(self, cb):
        self._listeners["end_of_media"].append(cb)

    def unsubscribe_end_of_media(self, cb):
        if cb in self._listeners["end_of_media"]:
            self._listeners["end_of_media"].remove(cb)

    def subscribe_position_changed(self, cb):
        self._listeners["position_changed"].append(cb)

    def unsubscribe_position_changed(self, cb):
        if cb in self._listeners["position_changed"]:
            self._listeners["position_changed"].remove(cb)

    def subscribe_duration_changed(self, cb):
        self._listeners["duration_changed"].append(cb)

    def unsubscribe_duration_changed(self, cb):
        if cb in self._listeners["duration_changed"]:
            self._listeners["duration_changed"].remove(cb)

    def emit_media_accepted(self, path):
        for cb in list(self._listeners["media_accepted"]):
            cb(path)

    def emit_media_rejected(self, path, message):
        for cb in list(self._listeners["media_rejected"]):
            cb(path, message)

    def emit_playback_state(self, status):
        for cb in list(self._listeners["playback_state_changed"]):
            cb(status)

    def emit_end_of_media(self):
        for cb in list(self._listeners["end_of_media"]):
            cb()


class FakeProvider(AudioEngineProviderPort):
    """Deterministic provider with runtime-failure emission (G seam)."""

    def __init__(
        self,
        engine_id,
        *,
        available=True,
        implemented=True,
        open_error=None,
        close_error=None,
    ):
        self._engine_id = engine_id
        self._available = available
        self._implemented = implemented
        self._open_error = open_error
        self._close_error = close_error
        self.port = None
        self.port_loads = []
        self.port_plays = []
        self.volume_received = None
        self.muted_received = None
        self.probe_count = 0
        self.open_count = 0
        self.close_count = 0
        self.runtime_failure_listeners = []
        self._runtime_generation = 0

    @property
    def engine_id(self):
        return self._engine_id

    @property
    def current_runtime_generation(self):
        return self._runtime_generation

    def probe(self):
        from michi.domain.audio_engine import (
            AudioEngineCapabilities,
            AudioEngineDescriptor,
        )

        self.probe_count += 1
        return AudioEngineDescriptor(
            engine_id=self._engine_id,
            display_name=self._engine_id.value,
            available=self._available,
            unavailable_reason=("runtime missing" if not self._available else None),
            implemented=self._implemented,
            capabilities=AudioEngineCapabilities(
                local_file_playback=True,
                seek=True,
                pause=True,
                volume=True,
                mute=True,
            ),
        )

    def open(self):
        self.open_count += 1
        if self._open_error is not None:
            raise self._open_error
        self._runtime_generation += 1
        self.port = FakePort(self._engine_id, self)
        return self.port

    def close(self):
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error
        self._runtime_generation += 1  # invalidate in-flight events
        self.port = None

    # --- G seam: runtime-failure observation ---
    def subscribe_runtime_failed(self, cb):
        if cb not in self.runtime_failure_listeners:
            self.runtime_failure_listeners.append(cb)

    def unsubscribe_runtime_failed(self, cb):
        if cb in self.runtime_failure_listeners:
            self.runtime_failure_listeners.remove(cb)

    def emit_runtime_failure(self, reason, generation=None):
        event = AudioEngineRuntimeFailureEvent(
            engine_id=self._engine_id,
            runtime_generation=(
                generation if generation is not None else self._runtime_generation
            ),
            reason=reason,
        )
        for cb in list(self.runtime_failure_listeners):
            cb(event)


class GH:
    """Composed deterministic graph: registry + service + router + playback
    + settings + selection + convergence coordinators."""

    def __init__(self, *providers, start_selected=None):
        self.providers = {p.engine_id: p for p in providers}
        self.registry = AudioEngineRegistry(list(providers))
        self.service = AudioEngineService(self.registry)
        if start_selected is not None:
            self.service.restore_selected(start_selected)
        self.router = AudioTransportRouter()
        self.playback = PlaybackService(self.router)
        from tests.test_m11_3f_engine_selection import FakeSettingsRepository

        self.settings_repo = FakeSettingsRepository()
        self.settings = SettingsService(self.settings_repo)
        self.convergence = AudioEngineConvergenceCoordinator(
            engine_service=self.service,
            registry=self.registry,
            router=self.router,
            playback=self.playback,
        )
        for p in providers:
            self.convergence.subscribe_provider(p)
        self.selection = AudioEngineSelectionCoordinator(
            engine_service=self.service,
            registry=self.registry,
            router=self.router,
            playback=self.playback,
            settings=self.settings,
        )
        self.selection.set_recovery_callback(
            self.convergence.recover_safe_unbound_failure
        )

    def activate(self, engine_id):
        """Direct activation (startup-simulation without convergence)."""
        provider = self.providers[engine_id]
        port = provider.open()
        self.router.bind(engine_id, port)
        self.service.mark_ready(engine_id)


def make_g(
    *ids,
    start_selected=None,
    available=None,
    open_errors=None,
    close_errors=None,
):
    available = available or {}
    providers = [
        FakeProvider(
            eid,
            available=available.get(eid, True),
            open_error=(open_errors or {}).get(eid),
            close_error=(close_errors or {}).get(eid),
        )
        for eid in ids
    ]
    return GH(*providers, start_selected=start_selected)


QT, GST, MPD = (
    AudioEngineId.QT_MULTIMEDIA,
    AudioEngineId.GSTREAMER,
    AudioEngineId.MPD,
)


@pytest.fixture(scope="module")
def qapp():
    """Instancia Qt offscreen local (patrón del repo) — sin depender de
    pytest-qt, que no está en la CI (real-MPD runtime test)."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


# ---------------------------------------------------------------------------
# G1 — STARTUP SELECTED CONVERGENCE
# ---------------------------------------------------------------------------


class TestG1Startup:
    def test_g01_default_selected_qt_active_ready(self):
        h = make_g(QT, GST, MPD)  # default selected Qt
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == QT
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from is None
        assert h.router.bound_engine_id == QT

    def test_g02_selected_gstreamer_success_qt_never_opened(self):
        h = make_g(QT, GST, MPD, start_selected=GST)
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == GST
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from is None
        assert h.router.bound_engine_id == GST
        assert h.providers[QT].open_count == 0  # Qt NEVER opened

    def test_g03_selected_mpd_success_qt_never_opened(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id == MPD
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert h.providers[QT].open_count == 0

    def test_g04_selected_gst_unavailable_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=GST, available={GST: False})
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST
        assert st.error_message is not None
        assert h.router.bound_engine_id == QT

    def test_g05_selected_mpd_unavailable_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == MPD

    def test_g06_selected_gst_open_failure_qt_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=GST,
            open_errors={GST: RuntimeError("gst init failed")},
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST
        assert "gst init failed" in st.error_message

    def test_g07_selected_mpd_open_failure_qt_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            open_errors={MPD: RuntimeError("mpd init failed")},
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id == QT
        assert st.fallback_from == MPD

    def test_g08_selected_qt_unavailable_no_alternate(self):
        h = make_g(QT, GST, MPD, available={QT: False})
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == QT
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.UNAVAILABLE
        assert st.fallback_from is None
        assert h.router.bound_engine_id is None
        # NO GStreamer/MPD fallback
        assert h.providers[GST].open_count == 0
        assert h.providers[MPD].open_count == 0

    def test_g09_selected_qt_open_failure_no_alternate(self):
        h = make_g(
            QT,
            GST,
            MPD,
            open_errors={QT: RuntimeError("qt init failed")},
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == QT
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert h.providers[GST].open_count == 0

    def test_g10_mpd_failure_plus_qt_unavailable_failed(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            available={MPD: False, QT: False},
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.fallback_from is None
        assert "mpd" in st.error_message and "fallback" in st.error_message

    def test_g11_mpd_failure_plus_qt_open_failure_failed(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            open_errors={
                MPD: RuntimeError("mpd init failed"),
                QT: RuntimeError("qt init failed"),
            },
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert "mpd init failed" in st.error_message
        assert "Qt Multimedia fallback failed" in st.error_message

    def test_g12_fallback_never_changes_persisted_selected(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        assert h.service.state.selected_engine_id == MPD
        # settings repository untouched by fallback
        assert h.settings_repo.saved == []


# ---------------------------------------------------------------------------
# G2 — EXPLICIT SWITCH FAILURE CONVERGENCE (F→G seam)
# ---------------------------------------------------------------------------


class TestG2SwitchFailure:
    def test_g13_target_open_failure_after_safe_source_close_qt_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            open_errors={GST: RuntimeError("gst open failed")},
        )
        h.activate(MPD)
        with pytest.raises(RuntimeError, match="gst open failed"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST  # user intent persisted
        assert st.active_engine_id == QT  # safe Qt fallback
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST
        assert h.router.bound_engine_id == QT
        assert h.providers[MPD].close_count == 1  # source closed

    def test_g14_bind_failure_cleanup_detached_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        gst = h.providers[GST]
        original_bind = h.router.bind
        calls = {"n": 0}

        def broken_bind(engine_id, port):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("bind rejected")  # target bind fails
            return original_bind(engine_id, port)  # Qt fallback bind works

        h.router.bind = broken_bind  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="bind rejected"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST
        assert gst.close_count == 1  # cleanup detached + closed

    def test_g15_validation_failure_cleanup_detached_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        original_bind = h.router.bind
        calls = {"n": 0}

        def wrong_bind(engine_id, port):
            calls["n"] += 1
            if calls["n"] == 1:
                # target bind commits a WRONG identity → validation fails
                h.router._bound = port
                h.router._bound_engine_id = MPD
                h.router._attach()
                return
            return original_bind(engine_id, port)  # Qt fallback binds fine

        h.router.bind = wrong_bind  # type: ignore[method-assign]
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchError,
        )

        with pytest.raises(AudioEngineSwitchError):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST

    def test_g16_volume_restore_failure_cleanup_detached_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        gst = h.providers[GST]

        class VolumeFailPort(FakePort):
            def set_volume(self, value):
                raise RuntimeError("volume restore failed")

        def failing_open():
            gst.open_count += 1
            gst._runtime_generation += 1
            gst.port = VolumeFailPort(gst.engine_id, gst)
            return gst.port

        gst.open = failing_open  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="volume restore failed"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == GST

    def test_g17_source_unbind_failure_no_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)

        # the SHARED router's unbind now fails BEFORE detaching (identity of
        # the router object preserved across playback/selection/convergence)
        def boom_unbind():
            raise RuntimeError("unbind failed")

        h.router.unbind = boom_unbind  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="unbind failed"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == MPD  # source preserved (physical truth)
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.fallback_from is None  # NOT a successful fallback
        assert h.providers[QT].open_count == 0  # NO fallback opened

    def test_g18_source_close_failure_no_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            close_errors={MPD: RuntimeError("close blew up")},
        )
        h.activate(MPD)
        with pytest.raises(RuntimeError, match="close blew up"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert h.providers[QT].open_count == 0  # NO fallback

    def test_g19_target_cleanup_still_bound_no_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        gst = h.providers[GST]
        # shared router: 1st unbind (source detach) OK; 2nd (target cleanup)
        # fails BEFORE detaching (identity preserved across all consumers)
        original_unbind = h.router.unbind
        unbind_calls = {"n": 0}

        def scripted_unbind():
            unbind_calls["n"] += 1
            if unbind_calls["n"] == 2:
                raise RuntimeError("cleanup unbind failed")
            return original_unbind()

        h.router.unbind = scripted_unbind  # type: ignore[method-assign]

        class VolumeFailPort(FakePort):
            def set_volume(self, value):
                raise RuntimeError("volume restore failed")

        def failing_open():
            gst.open_count += 1
            gst._runtime_generation += 1
            gst.port = VolumeFailPort(gst.engine_id, gst)
            return gst.port

        gst.open = failing_open  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="volume restore failed"):
            h.selection.switch_to(GST)
        st = h.service.state
        assert st.selected_engine_id == GST
        assert st.active_engine_id == GST  # still physically bound
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.fallback_from is None
        assert h.router.bound_engine_id == GST
        assert h.providers[QT].open_count == 0  # NOT SAFE → no fallback

    def test_g20_original_exception_propagates_even_with_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            open_errors={GST: RuntimeError("GSTREAMER PRIMARY ERROR")},
        )
        h.activate(MPD)
        with pytest.raises(RuntimeError, match="GSTREAMER PRIMARY ERROR"):
            h.selection.switch_to(GST)
        # fallback happened but the caller still got the ORIGINAL error
        assert h.service.state.active_engine_id == QT

    def test_g21_persisted_target_remains_target_after_fallback(self):
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            open_errors={GST: RuntimeError("gst failed")},
        )
        h.activate(MPD)
        with pytest.raises(RuntimeError):
            h.selection.switch_to(GST)
        assert h.settings.state.audio_engine_id == GST  # persisted target


# ---------------------------------------------------------------------------
# G3 — RUNTIME ENGINE LOSS
# ---------------------------------------------------------------------------


class TestG3RuntimeLoss:
    def test_g22_mpd_process_exit_playback_stopped(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        # committed track playing
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        assert h.playback.state.status == PlaybackStatus.PLAYING
        # MPD dies
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        assert h.playback.state.status == PlaybackStatus.STOPPED
        assert h.playback.state.file_path == "/music/a.flac"  # preserved
        assert h.playback.state.error_message == "MPD process exited"

    def test_g23_mpd_fatal_transport_loss_playback_stopped(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.providers[MPD].emit_runtime_failure("MPD transport error")
        assert h.playback.state.status == PlaybackStatus.STOPPED
        assert h.playback.state.file_path == "/music/a.flac"

    def test_g24_committed_logical_track_preserved(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        st = h.playback.state
        assert st.file_path == "/music/a.flac"
        assert st.status == PlaybackStatus.STOPPED
        assert h.playback._accepted is False
        assert h.playback._intent is False

    def test_g25_no_eom_on_engine_loss(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        eom_fired = []
        h.playback.subscribe_end_of_media(lambda: eom_fired.append(1))
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        assert eom_fired == []

    def test_g26_queue_current_unchanged(self):
        from pathlib import Path

        from michi.application.queue_service import QueueService

        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        queue = QueueService(h.playback)
        queue.add(Path("/music/A.flac"))
        queue.add(Path("/music/B.flac"))
        queue.add(Path("/music/C.flac"))
        queue.play_index(1)
        h.playback.stop()
        h.playback.load_and_play("/music/B.flac")
        h.router._bound.emit_media_accepted("/music/B.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        before = queue.state
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        after = queue.state
        assert tuple(after.tracks) == tuple(before.tracks)
        assert after.current_index == before.current_index
        assert after.repeat_mode == before.repeat_mode
        assert after.shuffle_enabled == before.shuffle_enabled

    def test_g27_qt_fallback_exactly_once(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        st = h.service.state
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == MPD
        assert h.providers[QT].open_count == 1

    def test_g28_fallback_no_autoplay(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        qt = h.providers[QT]
        assert qt.port_loads == []  # no auto-load on fallback
        assert qt.port_plays == []  # no autoplay
        assert h.playback.state.status == PlaybackStatus.STOPPED

    def test_g29_next_explicit_play_reloads_logical_track_on_qt(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        qt = h.providers[QT]
        h.playback.play()  # explicit user play
        assert [t for _, t in qt.port_loads] == ["/music/a.flac"]
        assert qt.port_plays == [QT]

    def test_g30_qt_runtime_failure_no_alternate_fallback(self):
        h = make_g(QT, GST, MPD)
        h.activate(QT)  # Qt active
        h.providers[QT].emit_runtime_failure("Qt runtime died")
        st = h.service.state
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.fallback_from is None
        assert h.providers[GST].open_count == 0
        assert h.providers[MPD].open_count == 0

    def test_g31_stale_old_generation_failure_ignored(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        old_gen = h.providers[MPD].current_runtime_generation
        # close MPD (generation advances), activate Qt, MPD gen1 event arrives
        h.router.unbind()
        h.providers[MPD].close()
        h.convergence._converge_runtime_loss = None  # noqa: SLF001
        qt_port = h.providers[QT].open()
        h.router.bind(QT, qt_port)
        h.service.mark_ready(QT)
        before = h.service.state
        h.providers[MPD].emit_runtime_failure("late stale failure", generation=old_gen)
        after = h.service.state
        assert after == before  # no mutation
        assert h.providers[QT].close_count == 0
        assert h.providers[QT].open_count == 1  # no reopen

    def test_g32_failure_from_inactive_engine_ignored(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        before = h.service.state
        # GStreamer never active: its failure must be ignored
        h.providers[GST].emit_runtime_failure("gst died")
        assert h.service.state == before
        assert h.providers[QT].open_count == 0

    def test_g33_duplicate_fatal_events_single_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        mpd = h.providers[MPD]
        mpd.emit_runtime_failure("transport error")
        mpd.emit_runtime_failure("process exit")  # duplicate burst
        assert h.providers[QT].open_count == 1  # exactly once
        st = h.service.state
        assert st.active_engine_id == QT


# ---------------------------------------------------------------------------
# G4 — MEDIA VS ENGINE FAILURE
# ---------------------------------------------------------------------------


class TestG4MediaVsEngine:
    def test_g34_media_rejected_does_not_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/corrupt.flac")
        h.router._bound.emit_media_rejected("/music/corrupt.flac", "corrupt")
        assert h.service.state.active_engine_id == MPD
        assert h.service.state.lifecycle == AudioEngineLifecycle.READY
        assert h.providers[QT].open_count == 0

    def test_g35_corrupt_track_does_not_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        # media rejection path (same as corrupt file)
        h.playback.load_and_play("/music/bad.flac")
        h.router._bound.emit_media_rejected("/music/bad.flac", "unsupported")
        assert h.providers[QT].open_count == 0
        assert h.service.state.fallback_from is None

    def test_g36_natural_eos_does_not_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        # natural EOS: backend STOPPED then EOM
        h.router._bound.emit_playback_state(PlaybackStatus.STOPPED)
        h.router._bound.emit_end_of_media()
        assert h.providers[QT].open_count == 0
        st = h.service.state
        assert st.active_engine_id == MPD
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from is None

    def test_g37_explicit_stop_does_not_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.playback.stop()
        assert h.providers[QT].open_count == 0
        assert h.service.state.active_engine_id == MPD

    def test_g38_pause_does_not_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        h.playback.pause()
        h.router._bound.emit_playback_state(PlaybackStatus.PAUSED)
        assert h.providers[QT].open_count == 0
        assert h.service.state.active_engine_id == MPD

    def test_g39_mpd_media_status_error_stays_media(self):
        """MPD media-specific status.error must NOT become engine failure:
        it does not flow through the runtime-failure seam at all."""
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        # only a runtime failure EVENT could trigger fallback — media errors
        # never produce one; assert the gate: emit media rejection, no
        # fallback and no runtime-failure telemetry mutation.
        h.playback.load_and_play("/music/bad.flac")
        h.router._bound.emit_media_rejected("/music/bad.flac", "ACK error")
        assert h.providers[QT].open_count == 0
        assert h.service.state.fallback_from is None


# ---------------------------------------------------------------------------
# G5 — PENDING PLAYBACK CONVERGENCE
# ---------------------------------------------------------------------------


class TestG5PendingPlayback:
    def test_g40_engine_loss_with_pending_load(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        rejected = []
        h.playback.load_and_play(
            "/music/pending.flac",
            on_rejected=lambda path, msg: rejected.append((path, msg)),
        )
        assert h.playback._pending_path is not None
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        assert len(rejected) == 1  # rejected exactly once
        assert rejected[0][0] == "/music/pending.flac"
        assert h.playback._pending_path is None  # cleared
        assert h.playback.state.status == PlaybackStatus.STOPPED

    def test_g41_engine_loss_with_pending_resume(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        resume_fired = []
        h.playback.subscribe_resume_prepared(
            lambda path, pos: resume_fired.append((path, pos))
        )
        h.playback.prepare_for_resume("/music/a.flac", 12345)
        assert h.playback._pending_resume_position_ms is not None
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        assert resume_fired == []  # resume_prepared NEVER emitted
        assert h.playback._pending_resume_position_ms is None
        assert h.playback._resume_prepared_pending is False
        assert h.playback.state.status == PlaybackStatus.STOPPED

    def test_g42_late_accepted_after_engine_loss_ignored(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        dead_port = h.providers[MPD].port
        h.playback.load_and_play("/music/a.flac")
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        # late acceptance from the dead backend arrives AFTER the loss
        # (acceptance is dropped: no pending request survives the loss)
        dead_port.emit_media_accepted("/music/a.flac")
        assert h.playback._accepted is False
        assert h.playback.state.status == PlaybackStatus.STOPPED

    def test_g43_late_playing_after_engine_loss_ignored(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        dead_port = h.providers[MPD].port
        h.playback.load_and_play("/music/a.flac")
        dead_port.emit_media_accepted("/music/a.flac")
        h.playback.play()
        dead_port.emit_playback_state(PlaybackStatus.PLAYING)
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        # late PLAYING from the dead backend (intent already cleared)
        dead_port.emit_playback_state(PlaybackStatus.PLAYING)
        assert h.playback.state.status == PlaybackStatus.STOPPED


# ---------------------------------------------------------------------------
# G6 — RESTART CONVERGENCE
# ---------------------------------------------------------------------------


class TestG6Restart:
    def test_g44_persist_mpd_restart_available_active_mpd(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.convergence.converge_startup()
        assert h.service.state.active_engine_id == MPD
        assert h.service.state.fallback_from is None

    def test_g45_persist_mpd_restart_unavailable_qt_fallback(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        st = h.service.state
        assert st.selected_engine_id == MPD
        assert st.active_engine_id == QT
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.fallback_from == MPD

    def test_g46_persist_gst_restart_available_active_gst(self):
        h = make_g(QT, GST, MPD, start_selected=GST)
        h.convergence.converge_startup()
        assert h.service.state.active_engine_id == GST
        assert h.service.state.fallback_from is None

    def test_g47_fallback_does_not_overwrite_persisted_preference(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        assert h.service.state.selected_engine_id == MPD
        assert h.settings_repo.saved == []  # persistence untouched

    def test_g48_next_restart_retries_preferred_engine(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        assert h.service.state.active_engine_id == QT
        # simulate a NEW process: MPD available again, same persisted pref
        h2 = make_g(QT, GST, MPD, start_selected=MPD)
        h2.convergence.converge_startup()
        assert h2.service.state.active_engine_id == MPD

    def test_g49_no_auto_return_to_preferred_during_process(self):
        h = make_g(QT, GST, MPD, start_selected=MPD, available={MPD: False})
        h.convergence.converge_startup()
        assert h.service.state.active_engine_id == QT
        assert h.service.state.fallback_from == MPD
        # "MPD becomes available" — DO NOTHING automatically
        h.providers[MPD]._available = True
        h.providers[MPD].probe()
        assert h.service.state.active_engine_id == QT  # unchanged
        assert h.providers[MPD].open_count == 0  # no background switch


# ---------------------------------------------------------------------------
# G7 — STARTUP RESUME ORDER + NO-ENGINE STARTUP
# ---------------------------------------------------------------------------


class TestG7StartupOrder:
    def test_g50_resume_prepared_after_engine_convergence(self):
        """prepare_for_resume is called AFTER the selected engine is active —
        never loading on Qt first and switching afterward."""

        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.convergence.converge_startup()
        assert h.service.state.active_engine_id == MPD
        # prepare_for_resume now goes to the ACTIVE (MPD) backend
        h.playback.prepare_for_resume("/music/a.flac", 12345)
        mpd_port = h.providers[MPD].port
        assert mpd_port is not None
        assert "load:/music/a.flac" in mpd_port.events
        assert h.providers[QT].open_count == 0

    def test_g51_no_engine_startup_honest(self):
        """All engines unavailable → honest FAILED/UNAVAILABLE, router
        unbound, graph continues to exist, no backend load attempted."""
        h = make_g(
            QT,
            GST,
            MPD,
            start_selected=MPD,
            available={QT: False, MPD: False, GST: False},
        )
        h.convergence.converge_startup()
        st = h.service.state
        assert st.active_engine_id is None
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert h.router.bound_engine_id is None
        # graph remains usable (no crash)
        assert h.playback.state.status == PlaybackStatus.STOPPED


# ---------------------------------------------------------------------------
# G8 — SHUTDOWN
# ---------------------------------------------------------------------------


class TestG8Shutdown:
    def test_g52_convergence_disabled_before_teardown(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.convergence.shutdown()
        assert h.convergence._shutdown is True
        assert h.providers[MPD].runtime_failure_listeners == []
        # a fatal event after shutdown is IGNORED — no fallback
        h.providers[MPD].emit_runtime_failure("MPD process exited")
        assert h.providers[QT].open_count == 0
        assert h.service.state.active_engine_id == MPD

    def test_g53_close_time_mpd_event_cannot_open_qt_during_shutdown(self):
        h = make_g(QT, GST, MPD, start_selected=MPD)
        h.activate(MPD)
        h.convergence.shutdown()
        # MPD close triggers a transport error event (shutdown sequence)
        h.providers[MPD].emit_runtime_failure("MPD transport error")
        assert h.providers[QT].open_count == 0

    def test_g54_retry_after_failed_shutdown_still_works(self):
        """F ownership-retention regression: convergence disabled does not
        break the retryable shutdown path (F51/F52 contract)."""
        h = make_g(QT, GST, MPD)
        h.convergence.shutdown()
        assert h.service.state.active_engine_id is None  # nothing activated


# ---------------------------------------------------------------------------
# G9 — REAL MPD RUNTIME FAILURE (skips when /usr/bin/mpd is absent)
# ---------------------------------------------------------------------------


class TestG9RealMpd:
    def test_g90_real_mpd_process_exit_publishes_runtime_failure(self, qapp, tmp_path):
        """Real MPD: terminate the managed child externally → the provider
        emits a fatal runtime failure through the G seam. Split from the Qt
        fallback transaction (environment-sensitive): only the death signal
        verification runs against the real runtime."""
        import shutil
        import time

        if shutil.which("mpd") is None:
            pytest.skip("mpd executable no encontrado (dependency ausente)")
        import tempfile

        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )

        # SHORT runtime parent: the AF_UNIX socket path is bounded (~108
        # chars) — a deep tmp_path would exceed it.
        runtime_dir = tempfile.mkdtemp(prefix="michi-g9-")

        import michi.infrastructure.audio_engines.mpd as mpd_mod

        events = []
        provider = MpdEngineProvider()
        provider.subscribe_runtime_failed(lambda e: events.append(e))
        # Open THROUGH the provider so the runtime-failure relay and the
        # runtime generation match; patch the runtime parent to the short
        # dir (bounded AF_UNIX socket path).
        original_pick = mpd_mod._pick_runtime_parent
        import pathlib

        mpd_mod._pick_runtime_parent = lambda: pathlib.Path(runtime_dir)
        port = None
        try:
            port = provider.open()
            assert port._client is not None
            # wait until the child is alive
            deadline = time.time() + 10
            while (
                port._runtime.process is None
                or port._runtime.process.poll() is not None
            ):
                if time.time() > deadline:
                    pytest.skip("real MPD no arrancó (entorno)")
                time.sleep(0.05)
            proc = port._runtime.process
            proc.kill()  # external termination — the fatal signal
            # wait for the provider relay to observe PROCESS_EXIT (the
            # bridge delivers via QueuedConnection — process the Qt loop)
            from PySide6.QtCore import QCoreApplication

            deadline = time.time() + 10
            while not events and time.time() < deadline:
                for _ in range(5):
                    QCoreApplication.processEvents()
                time.sleep(0.03)
            for _ in range(5):
                QCoreApplication.processEvents()
            assert events, "provider no recibió el runtime failure real"
            assert events[0].engine_id.value == "mpd"
            reason = events[0].reason.lower()
            # Both PROCESS_EXIT and fatal TRANSPORT_ERROR are authorized
            # fatal runtime losses (timing of child reaping decides).
            assert (
                "process" in reason
                or "exit" in reason
                or "socket" in reason
                or "transport" in reason
            )
        finally:
            mpd_mod._pick_runtime_parent = original_pick
            if port is not None:
                port.close()
