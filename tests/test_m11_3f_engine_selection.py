"""M11.3F — Engine Selection + Persistence (quiescent transactional switching).

Deterministic gates F01-F42 using fake providers / fake repository / real
router / real PlaybackService / real coordinator. No arbitrary sleeps.
"""

import sqlite3

import pytest

from michi.application.audio_engine_registry import (
    AudioEngineProviderPort,
    AudioEngineRegistry,
)
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
    AudioEngineSwitchError,
    AudioEngineSwitchInProgressError,
    AudioEngineSwitchNotQuiescentError,
    AudioEngineSwitchUnavailableError,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.persistence import SettingsRepository
from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import (
    AudioEngineId,
    AudioEngineLifecycle,
)
from michi.domain.playback import PlaybackStatus
from michi.domain.settings import SettingsState
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

# ---------------------------------------------------------------------------
# Deterministic fakes
# ---------------------------------------------------------------------------


class FakePort:
    """Deterministic AudioPort double recording every transport call."""

    def __init__(self, engine_id: AudioEngineId, owner: "FakeProvider") -> None:
        self.engine_id = engine_id
        self.owner = owner
        self.events: list[str] = []
        self._listeners = {
            "media_accepted": [],
            "media_rejected": [],
            "playback_state_changed": [],
            "end_of_media": [],
            "position_changed": [],
            "duration_changed": [],
        }

    # AudioPort commands
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

    # AudioPort subscriptions
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

    # Test emitters (post-detach callbacks for F29)
    def emit_media_accepted(self, path):
        for cb in list(self._listeners["media_accepted"]):
            cb(path)

    def emit_playback_state(self, status):
        for cb in list(self._listeners["playback_state_changed"]):
            cb(status)

    def emit_end_of_media(self):
        for cb in list(self._listeners["end_of_media"]):
            cb()

    def emit_position(self, ms):
        for cb in list(self._listeners["position_changed"]):
            cb(ms)

    def emit_duration(self, ms):
        for cb in list(self._listeners["duration_changed"]):
            cb(ms)


class FakeProvider(AudioEngineProviderPort):
    """Deterministic provider with global simultaneity tracking."""

    _open_count = 0  # global: engines currently open

    def __init__(
        self,
        engine_id: AudioEngineId,
        *,
        available: bool = True,
        implemented: bool = True,
        unavailable_reason: str | None = None,
        open_error: Exception | None = None,
        close_error: Exception | None = None,
        volume_error: Exception | None = None,
    ):
        self._engine_id = engine_id
        self._available = available
        self._implemented = implemented
        self._unavailable_reason = unavailable_reason
        self._open_error = open_error
        self._close_error = close_error
        self._volume_error = volume_error
        self.events: list[str] = []
        self.port: FakePort | None = None
        self.port_loads: list[tuple[AudioEngineId, str]] = []
        self.port_plays: list[AudioEngineId] = []
        self.volume_received: int | None = None
        self.muted_received: bool | None = None
        self.probe_count = 0
        self.open_count = 0
        self.close_count = 0

    @property
    def engine_id(self) -> AudioEngineId:
        return self._engine_id

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
            unavailable_reason=self._unavailable_reason,
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
        self.events.append("open")
        self.open_count += 1
        if self._open_error is not None:
            raise self._open_error
        FakeProvider._open_count += 1
        self.port = FakePort(self._engine_id, self)
        return self.port

    def close(self):
        self.events.append("close")
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error
        if self.port is not None:
            FakeProvider._open_count -= 1
            self.port = None

    # Test seam: fail volume restore on the NEXT set_volume call
    def fail_next_volume(self):
        self._volume_error = RuntimeError("volume restore failed")

    def check_volume_error(self):
        err = self._volume_error
        self._volume_error = None
        return err


class FakeSettingsRepository(SettingsRepository):
    """In-memory settings repository with injectable save failure."""

    def __init__(self, initial: SettingsState | None = None):
        self._state = initial if initial is not None else SettingsState()
        self.save_fail: Exception | None = None
        self.saved: list[SettingsState] = []

    def load(self) -> SettingsState:
        return SettingsState(
            volume=self._state.volume,
            muted=self._state.muted,
            last_directory=self._state.last_directory,
            recent_files=list(self._state.recent_files),
            theme=self._state.theme,
            window_geometry=self._state.window_geometry,
            online_enrichment=self._state.online_enrichment,
            audio_engine_id=self._state.audio_engine_id,
        )

    def save(self, state: SettingsState) -> None:
        if self.save_fail is not None:
            raise self.save_fail
        self.saved.append(state)
        self._state = SettingsState(
            volume=state.volume,
            muted=state.muted,
            last_directory=state.last_directory,
            recent_files=list(state.recent_files),
            theme=state.theme,
            window_geometry=state.window_geometry,
            online_enrichment=state.online_enrichment,
            audio_engine_id=state.audio_engine_id,
        )


class FakeRouter(AudioTransportRouter):
    """Router with injectable unbind failure.

    ``unbind_error``: every unbind raises (pre-detach). ``unbind_script``:
    per-call list of exceptions — each unbind consumes the next entry (None
    = succeed); a script entry raises BEFORE detaching.
    """

    def __init__(
        self,
        *,
        unbind_error: Exception | None = None,
        unbind_script: list[Exception | None] | None = None,
    ):
        super().__init__()
        self._unbind_error = unbind_error
        self._unbind_script = list(unbind_script) if unbind_script else None
        self.unbind_calls = 0

    def unbind(self) -> None:
        self.unbind_calls += 1
        if self._unbind_script is not None:
            if self.unbind_calls <= len(self._unbind_script):
                failure = self._unbind_script[self.unbind_calls - 1]
                if failure is not None:
                    raise failure
            super().unbind()
            return
        if self._unbind_error is not None:
            raise self._unbind_error
        super().unbind()


class EngineHarness:
    """Composed deterministic graph: registry + service + router + playback +
    settings + coordinator, with an event log."""

    def __init__(
        self,
        *providers: FakeProvider,
        unbind_error: Exception | None = None,
        unbind_script: list[Exception | None] | None = None,
        settings_initial: SettingsState | None = None,
        start_active: AudioEngineId = AudioEngineId.QT_MULTIMEDIA,
    ):
        self.providers = {p.engine_id: p for p in providers}
        self.registry = AudioEngineRegistry(list(providers))
        self.service = AudioEngineService(self.registry)
        self.router = FakeRouter(unbind_error=unbind_error, unbind_script=unbind_script)
        self.playback = PlaybackService(self.router)
        self.settings_repo = FakeSettingsRepository(initial=settings_initial)
        self.settings = SettingsService(self.settings_repo)
        self.coordinator = AudioEngineSelectionCoordinator(
            engine_service=self.service,
            registry=self.registry,
            router=self.router,
            playback=self.playback,
            settings=self.settings,
        )
        self.events: list[str] = []
        # start the reference engine (like bootstrap)
        self.activate(start_active)

    def activate(self, engine_id: AudioEngineId) -> None:
        provider = self.providers[engine_id]
        port = provider.open()
        self.router.bind(engine_id, port)
        self.service.mark_ready(engine_id)

    def track_state(self):
        """Subscribe to state transitions recording human-readable events."""

        def on_change():
            st = self.service.state
            self.events.append(
                f"state:{st.lifecycle.value}:selected={st.selected_engine_id.value}"
                ":active="
                f"{st.active_engine_id.value if st.active_engine_id else 'None'}"
                f":switching_to={st.switching_to.value if st.switching_to else 'None'}"
            )

        self.service.subscribe_changed(on_change)

    def snapshot(self):
        st = self.service.state
        return (
            st.selected_engine_id,
            st.active_engine_id,
            st.lifecycle,
            st.switching_to,
        )


def make_harness(
    *ids: AudioEngineId,
    available: dict[AudioEngineId, bool] | None = None,
    unbind_error: Exception | None = None,
    unbind_script: list[Exception | None] | None = None,
    start_active: AudioEngineId = AudioEngineId.QT_MULTIMEDIA,
    open_errors: dict[AudioEngineId, Exception] | None = None,
    close_errors: dict[AudioEngineId, Exception] | None = None,
) -> EngineHarness:
    available = available or {}
    providers = [
        FakeProvider(
            eid,
            available=available.get(eid, True),
            unavailable_reason=(
                "runtime missing" if available.get(eid, True) is False else None
            ),
            open_error=(open_errors or {}).get(eid),
            close_error=(close_errors or {}).get(eid),
        )
        for eid in ids
    ]
    return EngineHarness(
        *providers,
        unbind_error=unbind_error,
        unbind_script=unbind_script,
        start_active=start_active,
    )


# ---------------------------------------------------------------------------
# F1 — PERSISTENCE
# ---------------------------------------------------------------------------


class TestF1Persistence:
    def test_f01_default_selected_qt(self):
        service = AudioEngineService()
        assert service.state.selected_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f02_valid_persisted_qt_roundtrip(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "qt.db")
        repo.save(SettingsState(audio_engine_id=AudioEngineId.QT_MULTIMEDIA))
        assert repo.load().audio_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f03_valid_persisted_gstreamer_roundtrip(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "gst.db")
        repo.save(SettingsState(audio_engine_id=AudioEngineId.GSTREAMER))
        assert repo.load().audio_engine_id == AudioEngineId.GSTREAMER

    def test_f04_valid_persisted_mpd_roundtrip(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "mpd.db")
        repo.save(SettingsState(audio_engine_id=AudioEngineId.MPD))
        assert repo.load().audio_engine_id == AudioEngineId.MPD

    def test_f05_malformed_persisted_id_falls_back_to_qt(self, tmp_path, caplog):
        import logging

        db_path = tmp_path / "malformed.db"
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings VALUES ('audio_engine_id', 'foobar')"
            )
        caplog.set_level(logging.WARNING, logger="michi.infrastructure.sqlite_settings")
        repo = SQLiteSettingsRepository(db_path)
        state = repo.load()
        assert state.audio_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert any("audio_engine_id" in r.getMessage() for r in caplog.records)
        # NO database recovery / quarantine for a bad preference: HEALTHY
        from michi.domain.persistence_health import PersistenceHealth

        diag = SQLiteSettingsRepository.inspect_path(db_path)
        assert diag.health is PersistenceHealth.HEALTHY

    @pytest.mark.parametrize(
        "raw",
        ["", "MPD", "foobar", "qt_multimedia_", "GSTREAMER"],
    )
    def test_f05b_malformed_variants_fallback_qt(self, tmp_path, raw):
        db_path = tmp_path / "m.db"
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings VALUES ('audio_engine_id', ?)",
                (raw,),
            )
        repo = SQLiteSettingsRepository(db_path)
        assert repo.load().audio_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f05c_blob_value_falls_back_qt(self, tmp_path):
        db_path = tmp_path / "blob.db"
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings VALUES ('audio_engine_id', ?)",
                (b"\x00\x01\x02",),
            )
        repo = SQLiteSettingsRepository(db_path)
        assert repo.load().audio_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f06_persistence_failure_is_predestructive(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        h.settings_repo.save_fail = RuntimeError("disk full")
        with pytest.raises(RuntimeError, match="disk full"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # old runtime untouched
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 0
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        # in-memory preference restored
        assert h.settings.state.audio_engine_id == AudioEngineId.QT_MULTIMEDIA


# ---------------------------------------------------------------------------
# F2 — QUIESCENCE
# ---------------------------------------------------------------------------


class TestF2Quiescence:
    def _harness(self):
        return make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)

    def test_f07_playing_switch_rejected(self):
        h = self._harness()
        # canonical PLAYING: accepted track + armed intent + backend PLAYING
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PLAYING)
        assert h.playback.state.status == PlaybackStatus.PLAYING
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f08_paused_switch_rejected(self):
        h = self._harness()
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.play()
        h.router._bound.emit_playback_state(PlaybackStatus.PAUSED)
        assert h.playback.state.status == PlaybackStatus.PAUSED
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f09_pending_load_switch_rejected(self):
        h = self._harness()
        # arm a pending load (async acceptance pending)
        h.playback.load_and_play("/music/x.flac")
        assert h.playback.state.status == PlaybackStatus.STOPPED
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)

    def test_f10_pending_play_intent_switch_rejected(self):
        h = self._harness()
        # intent armed but backend not yet PLAYING
        h.playback._intent = True
        assert h.playback.is_engine_switch_quiescent() is False
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        h.playback._intent = False

    def test_f11_resume_preparation_switch_rejected(self):
        h = self._harness()
        h.playback.prepare_for_resume("/music/x.flac", 1000)
        assert h.playback.is_engine_switch_quiescent() is False
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)

    def test_f12_accepted_stopped_is_quiescent(self):
        h = self._harness()
        # accepted track explicitly stopped
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        assert h.playback.state.file_path == "/music/a.flac"
        assert h.playback._accepted is True
        h.playback.stop()
        assert h.playback.state.status == PlaybackStatus.STOPPED
        assert h.playback.is_engine_switch_quiescent() is True


# ---------------------------------------------------------------------------
# F3 — SWITCH ORDER + F4 — SELECTION TRUTH
# ---------------------------------------------------------------------------


class TestF3F4SwitchOrder:
    def _harness(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
        )
        h.track_state()
        return h

    def test_f13_same_engine_switch_idempotent(self):
        h = self._harness()
        before = (
            h.providers[AudioEngineId.QT_MULTIMEDIA].open_count,
            h.providers[AudioEngineId.QT_MULTIMEDIA].close_count,
        )
        h.coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
        after = (
            h.providers[AudioEngineId.QT_MULTIMEDIA].open_count,
            h.providers[AudioEngineId.QT_MULTIMEDIA].close_count,
        )
        assert before == after  # no churn
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.READY

    def test_f14_exact_successful_switch_order(self):
        h = self._harness()
        qt, gst, _mpd = (
            h.providers[AudioEngineId.QT_MULTIMEDIA],
            h.providers[AudioEngineId.GSTREAMER],
            h.providers[AudioEngineId.MPD],
        )
        # prepare pre-switch events from fakes
        order: list[str] = []
        original_close = qt.close
        original_unbind = h.router.unbind

        def spy_close():
            order.append("source-close")
            return original_close()

        def spy_unbind():
            order.append("router-unbind")
            return original_unbind()

        qt.close = spy_close  # type: ignore[method-assign]
        h.router.unbind = spy_unbind  # type: ignore[method-assign]
        gst.open = gst.open  # keep identity
        original_gst_open = gst.open

        def spy_gst_open():
            order.append("target-open")
            return original_gst_open()

        gst.open = spy_gst_open  # type: ignore[method-assign]

        h.coordinator.switch_to(AudioEngineId.GSTREAMER)

        unbind_idx = order.index("router-unbind")
        close_idx = order.index("source-close")
        open_idx = order.index("target-open")
        assert (
            unbind_idx < close_idx < open_idx
        )  # F15 + source-close before target-open
        # persistence happened before the destructive boundary
        assert len(h.settings_repo.saved) >= 1
        assert h.settings.state.audio_engine_id == AudioEngineId.GSTREAMER
        # final state
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.GSTREAMER
        assert st.active_engine_id == AudioEngineId.GSTREAMER
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert st.switching_to is None

    def test_f15_router_unbound_before_source_close(self):
        h = self._harness()
        order: list[str] = []
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        original_close = qt.close
        original_unbind = h.router.unbind

        def spy_close():
            order.append("close")
            return original_close()

        def spy_unbind():
            order.append("unbind")
            return original_unbind()

        qt.close = spy_close  # type: ignore[method-assign]
        h.router.unbind = spy_unbind  # type: ignore[method-assign]
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert order.index("unbind") < order.index("close")

    def test_f16_max_one_provider_open_simultaneously(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
        )
        # Track simultaneously-open engines as a live SET: the coordinator
        # must close the source BEFORE opening the target, so the set never
        # exceeds one element.
        FakeProvider._open_set: set = set()
        peak = 0
        original_open = FakeProvider.open
        original_close = FakeProvider.close

        def spy_open(self):
            nonlocal peak
            FakeProvider._open_set.add(self.engine_id)
            peak = max(peak, len(FakeProvider._open_set))
            self.port = FakePort(self.engine_id, self)
            return self.port

        def spy_close(self):
            FakeProvider._open_set.discard(self.engine_id)
            return original_close(self)

        FakeProvider.open = spy_open  # type: ignore[method-assign]
        FakeProvider.close = spy_close  # type: ignore[method-assign]
        try:
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
            h.coordinator.switch_to(AudioEngineId.MPD)
            assert peak == 1  # never two engines open at the same time
        finally:
            FakeProvider.open = original_open  # type: ignore[method-assign]
            FakeProvider.close = original_close  # type: ignore[method-assign]
            FakeProvider._open_set = set()

    def test_f37_target_not_fabricated_active_early(self):
        h = self._harness()
        states_seen = []
        original_mark_ready = h.service.mark_ready

        def spy_mark_ready(engine_id):
            st = h.service.state
            states_seen.append((st.selected_engine_id, st.active_engine_id))
            return original_mark_ready(engine_id)

        h.service.mark_ready = spy_mark_ready  # type: ignore[method-assign]
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # before the final READY, active must NEVER be GSTREAMER while
        # switching_to is set and validation hasn't completed
        for _selected, active in states_seen:
            assert active != AudioEngineId.GSTREAMER

    def test_f38_fallback_from_remains_none(self):
        h = self._harness()
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.service.state.fallback_from is None
        st = h.service.state
        # state transitions never set fallback_from
        assert st.fallback_from is None


# ---------------------------------------------------------------------------
# F5 — BACKEND ACCEPTANCE + F6 — VOLUME/MUTE + F7 — QUEUE
# ---------------------------------------------------------------------------


class TestF5F6F7:
    def test_f54_playback_acceptance_switch(self):
        """The MANDATORY acceptance gate: old acceptance invalidated, next
        play reloads the logical track on the NEW backend."""
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        gst = h.providers[AudioEngineId.GSTREAMER]
        # source backend accepts /music/a.flac
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        assert h.playback.state.file_path == "/music/a.flac"
        assert h.playback.state.status == PlaybackStatus.STOPPED
        assert h.playback._accepted is True
        h.playback.stop()  # accepted + explicit STOP = quiescent (canonical)
        assert h.playback.is_engine_switch_quiescent() is True
        qt.port_loads.clear()
        qt.port_plays.clear()
        gst.port_loads.clear()
        gst.port_plays.clear()
        # switch Qt -> GStreamer
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.playback.state.file_path == "/music/a.flac"
        assert h.playback.state.status == PlaybackStatus.STOPPED
        assert h.playback._accepted is False  # old backend acceptance invalidated
        # next play() reloads on the NEW backend
        h.playback.play()
        assert [t for _, t in gst.port_loads] == ["/music/a.flac"]  # exactly once
        assert gst.port_plays.count(AudioEngineId.GSTREAMER) == 1
        assert qt.port_loads == []  # no load on old backend after detach
        assert qt.port_plays == []

    def test_f25_logical_file_path_preserved_stopped(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.stop()
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.playback.state
        assert st.file_path == "/music/a.flac"
        assert st.status == PlaybackStatus.STOPPED
        assert h.playback.is_engine_switch_quiescent() is True

    def test_f26_old_backend_acceptance_invalidated(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        assert h.playback._accepted is True
        h.playback.stop()
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.playback._accepted is False
        assert h.playback._intent is False
        assert h.playback.state.file_path == "/music/a.flac"

    def test_f27_next_play_reloads_logical_track_on_target(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        gst = h.providers[AudioEngineId.GSTREAMER]
        h.playback.load_and_play("/music/a.flac")
        h.router._bound.emit_media_accepted("/music/a.flac")
        h.playback.stop()
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        qt.port_loads.clear()  # solo importa lo que ocurre DESPUÉS del detach
        qt.port_plays.clear()
        h.playback.play()
        assert [t for _, t in gst.port_loads] == ["/music/a.flac"]
        assert gst.port_plays == [AudioEngineId.GSTREAMER]
        assert qt.port_loads == []
        assert qt.port_plays == []

    def test_f23_volume_continuity(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        h.playback.restore_volume(37, False)
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        gst = h.providers[AudioEngineId.GSTREAMER]
        assert gst.volume_received == 37
        assert h.playback.state.volume == 37

    def test_f24_mute_continuity(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        h.playback.restore_volume(37, True)
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        gst = h.providers[AudioEngineId.GSTREAMER]
        assert gst.muted_received is True
        assert h.playback.state.muted is True

    def test_f28_queue_state_unchanged(self):
        from pathlib import Path

        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.queue_service import QueueService
        from michi.domain.playback_session import RepeatMode

        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        queue = QueueService()
        session = PlaybackSessionService(h.playback, queue)
        # nontrivial queue: A B C + repeat + current identity
        session.set_repeat_mode(RepeatMode.ALL)
        queue.add(Path("/music/A.flac"))
        queue.add(Path("/music/B.flac"))
        queue.add(Path("/music/C.flac"))
        session.play_queue_index(1)  # current identity = B
        h.playback.stop()  # canonical: switches require quiescent playback
        assert h.playback.is_engine_switch_quiescent() is True
        before = queue.state
        before_index = session.state.current_index
        before_repeat = session.state.repeat_mode
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        after = queue.state
        # exact same state: tracks / session navigation untouched
        assert tuple((t.file_path, t.title) for t in after.tracks) == tuple(
            (t.file_path, t.title) for t in before.tracks
        )
        assert session.state.current_index == before_index
        assert session.state.repeat_mode == before_repeat
        assert after.count == 3

    def test_f29_old_detached_callbacks_ignored(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        old_port = h.router._bound
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # the detached old backend emits events — the router no longer forwards
        before = h.playback.state
        old_port.emit_media_accepted("/music/stale.flac")
        old_port.emit_playback_state(PlaybackStatus.PLAYING)
        old_port.emit_end_of_media()
        old_port.emit_position(5000)
        old_port.emit_duration(99999)
        after = h.playback.state
        assert after.file_path == before.file_path
        assert after.status == before.status
        assert after.position_ms == before.position_ms
        assert after.duration_ms == before.duration_ms


# ---------------------------------------------------------------------------
# F8 — FAILURE ATOMICITY
# ---------------------------------------------------------------------------


class TestF8FailureAtomicity:
    def test_f17_target_unavailable_preserves_old_runtime(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            available={AudioEngineId.GSTREAMER: False},
        )
        with pytest.raises(AudioEngineSwitchUnavailableError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        assert h.settings.state.audio_engine_id == AudioEngineId.QT_MULTIMEDIA

    def test_f32_target_open_failure_no_fallback(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            open_errors={AudioEngineId.GSTREAMER: RuntimeError("gst init failed")},
        )
        with pytest.raises(RuntimeError, match="gst init failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.active_engine_id is None
        assert st.selected_engine_id == AudioEngineId.GSTREAMER  # persisted intent
        assert h.router.bound_engine_id is None
        # no fallback: Qt NOT reopened
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].open_count == 1

    def test_f31_source_close_failure_does_not_open_target(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            close_errors={AudioEngineId.QT_MULTIMEDIA: RuntimeError("close blew up")},
        )
        with pytest.raises(RuntimeError, match="close blew up"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # router unbound; target NEVER opened
        assert h.router.bound_engine_id is None
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        st = h.service.state
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        # old-backend acceptance invalidated (old ownership is gone)
        assert h.playback._accepted is False

    def test_f30_router_unbind_failure_does_not_close_source(self):
        """F-FINAL-P2-01: source unbind failure preserves ACTIVE IDENTITY,
        conservatively FAILED.

        AudioTransportRouter._detach() is NOT failure-atomic: an exception
        may occur after SOME callbacks were detached while bound_engine_id
        still equals the source. Physical ownership (active=source) is
        preserved — READY is NOT guaranteed, so the projection is
        conservatively FAILED. Source NOT closed, target NOT opened, no
        fallback."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            unbind_error=RuntimeError("unbind failed"),
        )
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        with pytest.raises(RuntimeError, match="unbind failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # source untouched: still bound + open, target never opened
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert qt.close_count == 0
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        st = h.service.state
        # SELECTED = target (durably persisted user intent), ACTIVE = source
        assert st.selected_engine_id == AudioEngineId.GSTREAMER
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.FAILED  # conservative
        assert st.switching_to is None
        assert "unbind failed" in st.error_message
        # persisted preference = target
        assert h.settings.state.audio_engine_id == AudioEngineId.GSTREAMER
        # router physical truth == state active truth (mandatory F seal)
        assert h.router.bound_engine_id == st.active_engine_id

    def test_f33_target_bind_failure_cleanup_no_fallback(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        gst = h.providers[AudioEngineId.GSTREAMER]

        def broken_bind(engine_id, port):
            raise RuntimeError("bind rejected")

        h.router.bind = broken_bind  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="bind rejected"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.active_engine_id is None
        assert gst.close_count == 1  # cleanup best effort
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].open_count == 1  # no reopen

    def test_f34_validation_failure_cleanup_no_fallback(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        gst = h.providers[AudioEngineId.GSTREAMER]

        def broken_bind(engine_id, port):
            # bind succeeds but validation must fail: bind wrong identity
            h.router._bound = port
            h.router._bound_engine_id = AudioEngineId.MPD  # wrong!
            h.router._attach()

        h.router.bind = broken_bind  # type: ignore[method-assign]
        with pytest.raises(AudioEngineSwitchError, match="bind validation failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.active_engine_id is None
        assert gst.close_count == 1

    def test_f35_volume_mute_restore_failure_cleanup_no_fallback(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        gst = h.providers[AudioEngineId.GSTREAMER]
        gst.fail_next_volume()

        class VolumeFailPort(FakePort):
            def set_volume(self, value):
                raise RuntimeError("volume restore failed")

        gst.port = None

        def failing_open():
            gst.events.append("open")
            gst.open_count += 1
            FakeProvider._open_count += 1
            gst.port = VolumeFailPort(gst.engine_id, gst)
            return gst.port

        gst.open = failing_open  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="volume restore failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.active_engine_id is None
        assert gst.close_count == 1  # cleanup
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].open_count == 1  # no reopen

    def test_f36_first_error_wins_cleanup(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            close_errors={
                AudioEngineId.QT_MULTIMEDIA: RuntimeError("primary close err")
            },
        )
        with pytest.raises(RuntimeError, match="primary close err") as excinfo:
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert "primary close err" in str(excinfo.value)


# ---------------------------------------------------------------------------
# F9 — RESTART CONTRACT
# ---------------------------------------------------------------------------


class TestF9RestartContract:
    def test_f39_persisted_selected_restored_on_restart(self):
        from michi import bootstrap

        # persist MPD preference
        repo = FakeSettingsRepository()
        repo._state.audio_engine_id = AudioEngineId.MPD
        settings = SettingsService(repo)

        # reference runtime through the canonical bootstrap transaction,
        # with the deterministic fake port injected (topology parity)
        qt_provider = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        mpd_provider = FakeProvider(AudioEngineId.MPD)
        registry = AudioEngineRegistry([qt_provider, mpd_provider])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        fake_port = FakePort(AudioEngineId.QT_MULTIMEDIA, qt_provider)
        bootstrap._initialize_reference_audio_runtime(
            qt_provider, registry, service, router, injected_backend=fake_port
        )
        service.restore_selected(settings.state.audio_engine_id)
        st = service.state
        assert st.selected_engine_id == AudioEngineId.MPD
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.READY

    def test_f40_restart_does_not_auto_switch(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        # simulate restart restore: persisted GSTREAMER, active stays Qt
        h.service.restore_selected(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.GSTREAMER
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.lifecycle == AudioEngineLifecycle.READY
        # nothing switched: gst provider never opened
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0

    def test_f18_stop_reentrancy_revalidated_before_unbind(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        # a subscriber that, on the FIRST STOPPED notification of the
        # switch's stop(), re-requests playback (DIRECT/reentrant mutation
        # of the request state during the notification)
        fired = False

        def reentrant():
            nonlocal fired
            if not fired and h.playback.state.status == PlaybackStatus.STOPPED:
                fired = True
                h.playback.load_and_play("/music/reentrant.flac")

        h.playback.subscribe_changed(reentrant)
        with pytest.raises(AudioEngineSwitchNotQuiescentError):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # the destructive boundary was NOT crossed
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 0
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0

    def test_f19_selection_persisted_before_destructive_boundary(self):
        h = make_harness(AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER)
        order: list[str] = []
        original_save = h.settings_repo.save

        def spy_save(state):
            order.append("persist")
            return original_save(state)

        h.settings_repo.save = spy_save  # type: ignore[method-assign]
        original_unbind = h.router.unbind

        def spy_unbind():
            order.append("unbind")
            return original_unbind()

        h.router.unbind = spy_unbind  # type: ignore[method-assign]
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert order.index("persist") < order.index("unbind")


# ---------------------------------------------------------------------------
# CROSS-ENGINE FAKE MATRIX (F20-F22) + REGRESSION
# ---------------------------------------------------------------------------


class TestCrossEngineMatrix:
    @pytest.mark.parametrize(
        "start,target",
        [
            (AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER),
            (AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD),
            (AudioEngineId.GSTREAMER, AudioEngineId.QT_MULTIMEDIA),
            (AudioEngineId.GSTREAMER, AudioEngineId.MPD),
            (AudioEngineId.MPD, AudioEngineId.QT_MULTIMEDIA),
            (AudioEngineId.MPD, AudioEngineId.GSTREAMER),
        ],
    )
    def test_f20_f21_f22_all_directed_transitions(self, start, target):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
            start_active=start,
        )
        h.coordinator.switch_to(target)
        st = h.service.state
        assert st.selected_engine_id == target
        assert st.active_engine_id == target
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert h.router.bound_engine_id == target
        assert h.settings.state.audio_engine_id == target
        assert st.switching_to is None


class TestF41RecoveryLKG:
    def test_f41_recovery_lkg_retains_audio_engine_id(self, tmp_path):
        db_path = tmp_path / "recover.db"
        repo = SQLiteSettingsRepository(db_path)
        repo.save(SettingsState(audio_engine_id=AudioEngineId.MPD))
        # canonical LKG refresh (as performed at every healthy startup)
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db_path).health.name
            == "HEALTHY"
        )
        diag = SQLiteSettingsRepository.inspect_path(db_path)
        assert diag.health.name == "HEALTHY"
        # corrupt the primary and re-open through startup preflight:
        # recovery from LKG must retain the engine preference
        with db_path.open("wb") as fh:
            fh.write(b"\x00\x01\x02\x03corrupt")
        repo2 = SQLiteSettingsRepository.open_for_startup(db_path)
        loaded = repo2.load()
        assert loaded.audio_engine_id == AudioEngineId.MPD

    def test_f56_settings_matrix(self, tmp_path):
        """Canonical persisted values + malformed variants."""
        cases_ok = {
            None: AudioEngineId.QT_MULTIMEDIA,  # missing row
            "qt_multimedia": AudioEngineId.QT_MULTIMEDIA,
            "gstreamer": AudioEngineId.GSTREAMER,
            "mpd": AudioEngineId.MPD,
        }
        for raw, expected in cases_ok.items():
            db_path = tmp_path / f"ok_{raw}.db"
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS settings ("
                    "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                if raw is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO settings VALUES ('audio_engine_id', ?)",
                        (raw,),
                    )
            state = SQLiteSettingsRepository(db_path).load()
            assert state.audio_engine_id == expected
        for bad in ["", "MPD", "foobar"]:
            db_path = tmp_path / f"bad_{bad}.db"
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS settings ("
                    "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO settings VALUES ('audio_engine_id', ?)",
                    (bad,),
                )
            state = SQLiteSettingsRepository(db_path).load()
            assert state.audio_engine_id == AudioEngineId.QT_MULTIMEDIA


class TestF42AdapterContract:
    # Content hashes of the FROZEN adapter files at the M11.3F baseline
    # (be663c6299ef54ec911d0e8dd0e1ec05edd55bda). Content-anchored (no git
    # history needed) so the gate also runs in shallow CI checkouts.
    # M11.3G AUTHORIZED EXCEPTION: mpd.py gained the minimal fatal-runtime
    # notification seam (runtime_failure_callback — PROCESS_EXIT / fatal
    # TRANSPORT_ERROR publication only; transport semantics unchanged), so
    # its hash moved to the M11.3G value.
    # M11.3-UI-R2 AUTHORIZED REOPENING (approved concrete defect): mpd.py
    # gained the explicit default-system-output compatibility policy —
    # output-plugin discovery (`mpd --version`, pipewire > pulse > alsa) and
    # a single explicit audio_output with mixer_type "software", replacing
    # the implicit MPD output autodetection that failed on the local runtime
    # (ACK [5@0] {setvol} no such mixer control: PCM). Transport semantics
    # unchanged; volume/mute guaranteed by the software mixer.
    # M4-R1 GOVERNANCE CORRECTION: QueueService was REMOVED from the frozen
    # adapter hash ownership — M11.3 freezes engine/runtime transport
    # semantics, it does NOT own Queue implementation (queue_service.py is
    # legitimately refactored by M4-R1).
    _BASELINE_HASHES = {
        "src/michi/infrastructure/audio_engines/gstreamer.py": "1ee9e1d5fc493797",
        "src/michi/infrastructure/audio_engines/mpd.py": "ceaa2ec4c6d283ce",
        "src/michi/infrastructure/qt_backend.py": "88614638da12acd8",
        # M4-R1/M9-R2.1 authorized additive change: ports.py gained the
        # PlaylistArtworkStorePort boundary (never touches AudioPort).
        "src/michi/application/ports.py": "141926bd096ec714",
        "src/michi/application/audio_transport_router.py": "d27e9dca6304722c",
    }

    def test_f42_no_adapter_source_changes(self):
        """Frozen adapters must be byte-identical to the M11.3F baseline."""
        import hashlib
        from pathlib import Path

        for rel, expected in self._BASELINE_HASHES.items():
            data = Path(rel).read_bytes()
            actual = hashlib.sha256(data).hexdigest()[:16]
            assert actual == expected, f"adapter changed vs baseline: {rel}"


# ---------------------------------------------------------------------------
# F11 — FINAL LIFECYCLE SEAL (P1-01 shutdown, P1-02 truth, P1-03 reentrancy,
#       P1-04 bound-target cleanup)
# ---------------------------------------------------------------------------


class TestF11LifecycleSeal:
    def _shutdown(self, h):
        from michi import bootstrap

        return bootstrap._shutdown_audio_runtime(h.router, h.service, h.registry)

    def test_f43_shutdown_active_qt(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
        )
        self._shutdown(h)
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 1
        assert h.providers[AudioEngineId.GSTREAMER].close_count == 0
        assert h.providers[AudioEngineId.MPD].close_count == 0
        assert h.router.bound_engine_id is None

    def test_f44_shutdown_after_switch_to_gstreamer(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
        )
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.router.bound_engine_id == AudioEngineId.GSTREAMER
        assert h.service.state.active_engine_id == AudioEngineId.GSTREAMER
        self._shutdown(h)
        # the ACTUAL active provider is closed — never hard-coded Qt
        assert h.providers[AudioEngineId.GSTREAMER].close_count == 1
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 1
        assert h.providers[AudioEngineId.MPD].close_count == 0

    def test_f45_shutdown_after_switch_to_mpd(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
        )
        h.coordinator.switch_to(AudioEngineId.MPD)
        assert h.router.bound_engine_id == AudioEngineId.MPD
        assert h.service.state.active_engine_id == AudioEngineId.MPD
        self._shutdown(h)
        # managed/private MPD ownership: the MPD provider is the shutdown owner
        assert h.providers[AudioEngineId.MPD].close_count == 1
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 1

    def test_f46_shutdown_unbind_failure_does_not_close_still_bound(self):
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
            unbind_error=RuntimeError("shutdown unbind failed"),
        )
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        with pytest.raises(RuntimeError, match="shutdown unbind failed"):
            self._shutdown(h)
        # never close a provider the router still references
        assert qt.close_count == 0
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        # no alternate provider opened
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        assert h.providers[AudioEngineId.MPD].open_count == 0

    def test_f47_nested_switch_rejected(self):
        """P1-03: a synchronous subscriber attempting a nested switch during
        the outer transaction is rejected with AudioEngineSwitchInProgressError."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.GSTREAMER, AudioEngineId.MPD
        )
        nested_error = []
        seen_states = []

        def subscriber():
            st = h.service.state
            seen_states.append((st.selected_engine_id, st.active_engine_id))
            # after the outer mark_selected(GSTREAMER): try nested switch to MPD
            if (
                st.selected_engine_id == AudioEngineId.GSTREAMER
                and st.switching_to == AudioEngineId.GSTREAMER
                and not nested_error
            ):
                try:
                    h.coordinator.switch_to(AudioEngineId.MPD)
                except AudioEngineSwitchInProgressError as exc:
                    nested_error.append(exc)
                except Exception as exc:  # pragma: no cover - guard failure
                    nested_error.append(exc)

        h.service.subscribe_changed(subscriber)
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # nested switch rejected deterministically
        assert len(nested_error) == 1
        assert isinstance(nested_error[0], AudioEngineSwitchInProgressError)
        # MPD never probed/opened/persisted by the nested attempt
        mpd = h.providers[AudioEngineId.MPD]
        assert mpd.open_count == 0
        assert mpd.probe_count == 0  # nested switch rejected before probing
        assert h.settings.state.audio_engine_id == AudioEngineId.GSTREAMER
        # outer switch completed normally
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.GSTREAMER
        assert st.active_engine_id == AudioEngineId.GSTREAMER
        assert st.lifecycle == AudioEngineLifecycle.READY
        assert h.router.bound_engine_id == AudioEngineId.GSTREAMER
        # guard reset (finally) — a subsequent switch is accepted
        h.coordinator.switch_to(AudioEngineId.MPD)
        assert h.service.state.active_engine_id == AudioEngineId.MPD

    def test_f48_guard_resets_after_failure(self):
        """P1-03: after a failed switch the guard must reset — a second
        explicit switch is accepted (no permanently wedged coordinator)."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            open_errors={AudioEngineId.GSTREAMER: RuntimeError("gst init failed")},
        )
        with pytest.raises(RuntimeError, match="gst init failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        assert h.coordinator._switch_in_progress is False
        # second transaction accepted
        h.providers[AudioEngineId.GSTREAMER]._open_error = None
        h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        st = h.service.state
        assert st.active_engine_id == AudioEngineId.GSTREAMER
        assert st.lifecycle == AudioEngineLifecycle.READY

    def test_f49_target_cleanup_unbind_failure_preserves_bound_target(self):
        """P1-04: target activation fails late (volume restore) AND the
        cleanup unbind also fails — the target stays PHYSICALLY bound, is
        NOT closed, state reflects active=target FAILED, primary error wins."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            unbind_script=[None, RuntimeError("cleanup unbind failed")],
        )
        gst = h.providers[AudioEngineId.GSTREAMER]
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        gst.fail_next_volume()

        class VolumeFailPort(FakePort):
            def set_volume(self, value):
                raise RuntimeError("volume restore failed")

        gst.port = None

        def failing_open():
            gst.events.append("open")
            gst.open_count += 1
            FakeProvider._open_count += 1
            gst.port = VolumeFailPort(gst.engine_id, gst)
            return gst.port

        gst.open = failing_open  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="volume restore failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # first unbind (source detach) succeeded: Qt closed; target opened
        assert qt.close_count == 1
        assert gst.open_count == 1
        # cleanup unbind FAILED: target remains physically bound, NOT closed
        assert h.router.bound_engine_id == AudioEngineId.GSTREAMER
        assert gst.close_count == 0
        st = h.service.state
        assert st.selected_engine_id == AudioEngineId.GSTREAMER
        assert st.active_engine_id == AudioEngineId.GSTREAMER
        assert st.lifecycle == AudioEngineLifecycle.FAILED
        assert st.switching_to is None
        assert "volume restore failed" in st.error_message
        # router physical truth == state active truth
        assert h.router.bound_engine_id == st.active_engine_id

    def test_f50_shutdown_owns_failed_but_bound_target(self):
        """Shutdown ownership resolves the ACTUAL active provider even when
        lifecycle == FAILED (activation failed late, cleanup detach failed,
        target still physically bound) — never hard-coded Qt."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            unbind_script=[None, RuntimeError("cleanup unbind failed")],
        )
        gst = h.providers[AudioEngineId.GSTREAMER]
        gst.fail_next_volume()

        class VolumeFailPort(FakePort):
            def set_volume(self, value):
                raise RuntimeError("volume restore failed")

        gst.port = None

        def failing_open():
            gst.events.append("open")
            gst.open_count += 1
            FakeProvider._open_count += 1
            gst.port = VolumeFailPort(gst.engine_id, gst)
            return gst.port

        gst.open = failing_open  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="volume restore failed"):
            h.coordinator.switch_to(AudioEngineId.GSTREAMER)
        # pre-shutdown truth: FAILED but physically bound to GStreamer
        assert h.service.state.lifecycle == AudioEngineLifecycle.FAILED
        assert h.router.bound_engine_id == AudioEngineId.GSTREAMER
        # the shutdown unbind now SUCCEEDS (script consumed) → GST released
        self._shutdown(h)
        assert h.router.bound_engine_id is None
        assert gst.close_count == 1


# ---------------------------------------------------------------------------
# F12 — FINAL CONTAINER OWNERSHIP SEAL (F-FINAL-P1-01)
# ---------------------------------------------------------------------------


class TestF12ContainerOwnership:
    def _container_with_graph(self, h):
        """Minimal ApplicationContainer owning the canonical audio graph
        (same construction style as the resilience container tests)."""
        from michi.bootstrap import ApplicationContainer

        container = ApplicationContainer()
        container._audio_router = h.router
        container._audio_engine_registry = h.registry
        container._audio_engine_service = h.service
        container._qt_engine_provider = h.providers[AudioEngineId.QT_MULTIMEDIA]
        return container

    def test_f51_container_retains_audio_ownership_after_failed_shutdown(self):
        """F-FINAL-P1-01: a failed audio teardown must NOT erase the container
        audio ownership references (explicit path to the still-bound runtime)."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
            unbind_error=RuntimeError("unbind failed"),
        )
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        container = self._container_with_graph(h)
        with pytest.raises(RuntimeError, match="unbind failed"):
            container.shutdown()
        # provider NOT closed, router still bound
        assert qt.close_count == 0
        assert h.router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        # ownership retained — the owner keeps an explicit path to the runtime
        assert container._audio_router is h.router
        assert container._audio_engine_registry is h.registry
        assert container._audio_engine_service is h.service

    def test_f52_container_retry_shutdown_releases_retained_audio_runtime(self):
        """Retry semantics: after a failed audio teardown (ownership retained),
        a second shutdown with a working unbind releases the ACTUAL provider
        exactly once and then clears the audio ownership references."""
        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            AudioEngineId.MPD,
            unbind_error=RuntimeError("unbind failed"),
        )
        qt = h.providers[AudioEngineId.QT_MULTIMEDIA]
        container = self._container_with_graph(h)
        # FIRST shutdown fails: ownership retained
        with pytest.raises(RuntimeError, match="unbind failed"):
            container.shutdown()
        assert container._audio_router is h.router
        assert qt.close_count == 0
        # make the next unbind succeed, SECOND shutdown releases
        h.router._unbind_error = None
        container.shutdown()
        assert h.router.bound_engine_id is None
        assert qt.close_count == 1  # exactly once
        assert container._audio_router is None
        assert container._audio_engine_registry is None
        assert container._audio_engine_service is None
        assert container._qt_engine_provider is None
        # no alternate engine opened
        assert h.providers[AudioEngineId.GSTREAMER].open_count == 0
        assert h.providers[AudioEngineId.MPD].open_count == 0


class TestF13FirstErrorRetention:
    def test_f53_first_error_retained_with_audio_ownership(self):
        """F53 (optional): an earlier shutdown subsystem error stays the
        final propagated error, while the failed audio teardown STILL retains
        ownership (first-error-wins + ownership retention both hold)."""
        from michi.bootstrap import ApplicationContainer

        h = make_harness(
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.GSTREAMER,
            unbind_error=RuntimeError("audio unbind failed"),
        )
        container = ApplicationContainer()
        container._audio_router = h.router
        container._audio_engine_registry = h.registry
        container._audio_engine_service = h.service
        container._qt_engine_provider = h.providers[AudioEngineId.QT_MULTIMEDIA]

        class BoomCoordinator:
            def stop(self):
                raise RuntimeError("coordinator stop failed")

        container._coordinator = BoomCoordinator()
        with pytest.raises(RuntimeError, match="coordinator stop failed"):
            container.shutdown()
        # first-error-wins: the EARLIER error is the final propagated error
        # audio ownership retained even though its own teardown also failed
        assert container._audio_router is h.router
        assert container._audio_engine_registry is h.registry
        assert container._audio_engine_service is h.service
        assert h.providers[AudioEngineId.QT_MULTIMEDIA].close_count == 0
