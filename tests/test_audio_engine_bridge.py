"""M11.3-UI — AudioEngineBridge unit tests.

The bridge is a THIN QML adapter: it must project canonical engine state
truthfully, expose the engine set in deterministic registry order, and
delegate the ONLY switch path to the selection coordinator. It never
opens/closes providers, never binds the router, never mutates state.
"""

from michi.application.audio_engine_registry import AudioEngineRegistry
from michi.application.audio_engine_selection_coordinator import (
    AudioEngineSelectionCoordinator,
    AudioEngineSwitchNotQuiescentError,
)
from michi.application.audio_engine_service import AudioEngineService
from michi.application.audio_transport_router import AudioTransportRouter
from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.audio_engine import AudioEngineId
from michi.domain.playback import PlaybackStatus
from michi.presentation.audio_engine_bridge import AudioEngineBridge
from tests.test_m11_3f_engine_selection import FakeProvider, FakeSettingsRepository


def _graph():
    """Deterministic engine graph + bridge (registry order Qt/Gst/MPD)."""
    qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
    gst = FakeProvider(AudioEngineId.GSTREAMER)
    mpd = FakeProvider(AudioEngineId.MPD)
    registry = AudioEngineRegistry([qt, gst, mpd])
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
    bridge = AudioEngineBridge(
        service,
        registry,
        coordinator,
        playback_quiescent=playback.is_engine_switch_quiescent,
        playback_subscribe=playback.subscribe_changed,
        playback_unsubscribe=playback.unsubscribe_changed,
    )
    return service, registry, coordinator, bridge, qt, gst, mpd, router, playback


class TestBridgeProjections:
    def test_engine_order_canonical(self):
        _, _, _, bridge, *_ = _graph()
        ids = [e["id"] for e in bridge.engines]
        assert ids == ["qt_multimedia", "gstreamer", "mpd"]

    def test_display_names_and_identities(self):
        _, _, _, bridge, *_ = _graph()
        names = {e["id"]: e["displayName"] for e in bridge.engines}
        assert names == {
            "qt_multimedia": "Qt Multimedia",
            "gstreamer": "GStreamer",
            "mpd": "MPD",
        }
        identities = {e["id"]: e["shortIdentity"] for e in bridge.engines}
        assert identities == {
            "qt_multimedia": "Compatibility",
            "gstreamer": "Precision",
            "mpd": "Dedicated",
        }

    def test_selected_equals_active_projection(self):
        service, _, _, bridge, qt, *_ = _graph()
        service.mark_initializing(AudioEngineId.QT_MULTIMEDIA)
        qt.open()
        service._router = None  # placeholder never used
        assert service.state.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert bridge.selectedEngineId == "qt_multimedia"
        assert bridge.activeEngineId == ""

    def test_selected_active_different_after_ready(self):
        service, _, _, bridge, qt, *_ = _graph()
        qt.open()
        # simulate production activation state without the router binding
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        service.restore_selected(AudioEngineId.GSTREAMER)
        assert bridge.selectedEngineId == "gstreamer"
        assert bridge.activeEngineId == "qt_multimedia"
        assert bridge.selectedEngineName == "GStreamer"
        assert bridge.activeEngineName == "Qt Multimedia"

    def test_fallback_projection(self):
        service, _, _, bridge, qt, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        service.restore_selected(AudioEngineId.MPD)
        service.mark_fallback_ready(
            AudioEngineId.QT_MULTIMEDIA, AudioEngineId.MPD, "mpd failed"
        )
        assert bridge.hasFallback is True
        assert bridge.fallbackFrom == "mpd"
        # P2-03: runtime-general wording (failure may be at startup OR after)
        assert "MPD encountered a problem" in bridge.statusSummary
        assert "Qt Multimedia" in bridge.statusSummary

    def test_lifecycle_labels(self):
        service, _, _, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        assert bridge.lifecycleLabel == "Ready"
        service.mark_unavailable(AudioEngineId.QT_MULTIMEDIA, "missing")
        assert bridge.lifecycleLabel == "Not available"

    def test_unavailable_descriptor_projection(self):
        service, registry, _, bridge, *_ = _graph()
        mpd = registry.provider(AudioEngineId.MPD)
        mpd._available = False
        mpd._unavailable_reason = "mpd executable no encontrado en PATH"
        bridge.refresh_engines()
        mpd_row = [e for e in bridge.engines if e["id"] == "mpd"][0]
        assert mpd_row["available"] is False
        assert mpd_row["canActivate"] is False
        assert mpd_row["activationBlocker"] == ("mpd executable no encontrado en PATH")

    def test_capabilities_projected(self):
        _, _, _, bridge, *_ = _graph()
        qt_row = [e for e in bridge.engines if e["id"] == "qt_multimedia"][0]
        caps = qt_row["capabilities"]
        assert set(caps.keys()) == {
            "localFilePlayback",
            "seek",
            "pause",
            "volume",
            "mute",
        }
        assert "bitPerfect" not in caps
        assert "dsd" not in caps


class TestLiveEngineModel:
    """M11.3-UI-R1: dynamic overlays compose from CURRENT service state.

    AVAILABILITY may be cached (explicit refresh only); RUNTIME STATE
    (selected/active/switching) must update immediately without re-probe.
    """

    def _graph(self):
        return _graph()

    def test_overlays_follow_state_without_refresh(self):
        """Section 10 mandatory test: state change → engines rows current,
        provider probe count unchanged."""
        service, registry, _, bridge, qt, gst, mpd, *_ = _graph()
        bridge.refresh_engines()
        probes_before = sum(p.probe_count for p in (qt, gst, mpd))
        assert [e["selected"] for e in bridge.engines] == [True, False, False]

        # Canonical state changes to GStreamer selected+active (no refresh!)
        service.mark_ready(AudioEngineId.GSTREAMER)
        service.restore_selected(AudioEngineId.GSTREAMER)

        rows = {e["id"]: e for e in bridge.engines}
        assert rows["gstreamer"]["selected"] is True
        assert rows["gstreamer"]["active"] is True
        assert rows["qt_multimedia"]["active"] is False
        probes_after = sum(p.probe_count for p in (qt, gst, mpd))
        assert probes_after == probes_before  # NO provider re-probe

    def test_selected_overlay_live(self):
        _, _, _, bridge, *_ = _graph()
        service = bridge._service
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        service.restore_selected(AudioEngineId.MPD)
        rows = {e["id"]: e for e in bridge.engines}
        assert rows["mpd"]["selected"] is True
        assert rows["qt_multimedia"]["selected"] is False

    def test_active_overlay_live(self):
        _, _, _, bridge, *_ = _graph()
        service = bridge._service
        service.mark_ready(AudioEngineId.GSTREAMER)
        rows = {e["id"]: e for e in bridge.engines}
        assert rows["gstreamer"]["active"] is True
        assert rows["qt_multimedia"]["active"] is False

    def test_switching_overlay_live(self):
        _, _, _, bridge, *_ = _graph()
        service = bridge._service
        service.mark_initializing(AudioEngineId.MPD)
        rows = {e["id"]: e for e in bridge.engines}
        assert rows["mpd"]["switching"] is True
        assert rows["qt_multimedia"]["switching"] is False

    def test_engines_changed_fires_on_state_change(self):
        """Notify contract: engines projection re-evaluates on state change."""
        _, _, _, bridge, *_ = _graph()
        service = bridge._service
        notified = []
        bridge.engines_changed.connect(lambda: notified.append(1))
        service.mark_ready(AudioEngineId.GSTREAMER)
        service.restore_selected(AudioEngineId.GSTREAMER)
        assert len(notified) >= 2  # one per state notification

    def test_facts_unchanged_by_state_change(self):
        """Availability facts are NOT re-probed on state change; the cached
        snapshot stays authoritative until an explicit refresh."""
        _, registry, _, bridge, *_ = _graph()
        mpd = registry.provider(AudioEngineId.MPD)
        mpd._available = False
        bridge.refresh_engines()
        service = bridge._service
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        rows = {e["id"]: e for e in bridge.engines}
        assert rows["mpd"]["available"] is False  # snapshot untouched
        assert rows["mpd"]["canActivate"] is False


class TestSwitchDiagnostics:
    """P1-07: technical failure evidence never disappears."""

    def test_last_switch_technical_error_records_rejection(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchNotQuiescentError,
        )

        service, registry, coordinator, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        bridge.switch_failed.connect(lambda *_: None)

        def rejecting(target):
            raise AudioEngineSwitchNotQuiescentError(
                "engine switch requires quiescent playback"
            )

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert "quiescent playback" in bridge.lastSwitchTechnicalError

    def test_last_switch_technical_error_invalid_id(self):
        _, _, _, bridge, *_ = _graph()
        bridge.switch_failed.connect(lambda *_: None)
        bridge.switch_engine("not-an-engine")
        assert "not-an-engine" in bridge.lastSwitchTechnicalError

    def test_unexpected_exception_logged_and_surfaces_friendly(self, caplog):
        service, registry, coordinator, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        failures = []
        bridge.switch_failed.connect(lambda eid, msg: failures.append((eid, msg)))

        def exploding(target):
            raise RuntimeError("boom in transport")

        coordinator.switch_to = exploding  # type: ignore[method-assign]
        with caplog.at_level("ERROR"):
            bridge.switch_engine("gstreamer")
        assert failures == [("gstreamer", "Michi could not change the audio engine.")]
        assert "boom in transport" in caplog.text
        assert "boom in transport" in bridge.lastSwitchTechnicalError


class TestTransientDiagnosticLifecycle:
    """P2-03: lastSwitchTechnicalError must never look current after a
    later successful attempt; clear-on-attempt; notify only on change."""

    def _coordinator_rejecting(self, service, coordinator, exc):
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)

        def rejecting(target):
            raise exc

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        return service

    def test_failure_populates_diagnostic(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchNotQuiescentError,
        )

        service, registry, coordinator, bridge, *_ = _graph()
        self._coordinator_rejecting(
            service, coordinator, AudioEngineSwitchNotQuiescentError("not quiescent")
        )
        bridge.switch_failed.connect(lambda *_: None)
        bridge.switch_engine("gstreamer")
        assert "not quiescent" in bridge.lastSwitchTechnicalError

    def test_failure_then_success_clears_diagnostic(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchNotQuiescentError,
        )

        service, registry, coordinator, bridge, qt, _, _, router, _ = _graph()
        # arm Qt active (graph router) so a real switch can succeed after
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        bridge.switch_failed.connect(lambda *_: None)

        original_switch = coordinator.switch_to

        def rejecting(target):
            raise AudioEngineSwitchNotQuiescentError("not quiescent")

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert bridge.lastSwitchTechnicalError != ""

        # next attempt succeeds with the real transaction
        coordinator.switch_to = original_switch  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert bridge.lastSwitchTechnicalError == ""

    def test_invalid_id_notifies(self):
        _, _, _, bridge, *_ = _graph()
        notified = []
        bridge.technical_error_changed.connect(lambda: notified.append(1))
        bridge.switch_failed.connect(lambda *_: None)
        bridge.switch_engine("not-an-engine")
        # attempt start: clear is a no-op (already empty) → exactly ONE
        # notification for storing the invalid-id diagnostic
        assert len(notified) == 1
        assert "not-an-engine" in bridge.lastSwitchTechnicalError

    def test_two_failures_second_replaces_first(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchNotQuiescentError,
            AudioEngineSwitchUnavailableError,
        )

        service, registry, coordinator, bridge, *_ = _graph()
        bridge.switch_failed.connect(lambda *_: None)

        def rejecting(exc):
            def inner(target):
                raise exc

            coordinator.switch_to = inner  # type: ignore[method-assign]

        rejecting(AudioEngineSwitchNotQuiescentError("first failure"))
        bridge.switch_engine("gstreamer")
        rejecting(AudioEngineSwitchUnavailableError("second failure"))
        bridge.switch_engine("gstreamer")
        assert "second failure" in bridge.lastSwitchTechnicalError
        assert "first failure" not in bridge.lastSwitchTechnicalError

    def test_notify_only_on_value_change(self):
        service, registry, coordinator, bridge, *_ = _graph()
        bridge.switch_failed.connect(lambda *_: None)
        notified = []
        bridge.technical_error_changed.connect(lambda: notified.append(1))
        # success path with empty diagnostic: cleared (no-op) → no notify
        bridge.switch_engine("gstreamer")  # real switch → success
        assert bridge.lastSwitchTechnicalError == ""
        # the clear at attempt start was a no-op (already empty) — zero
        # notifications for the whole success path
        assert notified == []


class TestBridgeSwitch:
    def test_switch_delegates_exactly_once(self):
        service, registry, coordinator, bridge, qt, gst, *_ = _graph()
        # arm the graph: Qt active, quiescent
        qt.open()
        # direct activation via the service + router

        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        bridge.refresh_engines()
        calls = []
        original = coordinator.switch_to

        def spy(target):
            calls.append(target)
            original(target)

        coordinator.switch_to = spy  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert len(calls) == 1
        assert calls[0] == AudioEngineId.GSTREAMER

    def test_invalid_engine_id_deterministic_failure(self):
        service, registry, coordinator, bridge, *_ = _graph()
        failures = []
        bridge.switch_failed.connect(lambda eid, msg: failures.append((eid, msg)))
        bridge.switch_engine("not-an-engine")
        assert len(failures) == 1
        assert failures[0][0] == "not-an-engine"
        assert failures[0][1] == "Michi could not change the audio engine."

    def test_not_quiescent_friendly_message(self):
        service, registry, coordinator, bridge, qt, gst, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        failures = []

        def fail(eid, msg):
            failures.append((eid, msg))

        bridge.switch_failed.connect(fail)
        # make playback non-quiescent via pending intent
        bridge._service = service

        # simulate: coordinator rejects because a pending request exists
        def rejecting(target):
            raise AudioEngineSwitchNotQuiescentError("not quiescent")

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert len(failures) == 1
        assert failures[0][1] == ("Stop playback before changing the audio engine.")

    def test_unavailable_friendly_message(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchUnavailableError,
        )

        service, registry, coordinator, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        failures = []

        def fail(eid, msg):
            failures.append((eid, msg))

        bridge.switch_failed.connect(fail)

        def rejecting(target):
            raise AudioEngineSwitchUnavailableError("unavailable")

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert failures[0][1] == ("This audio engine is not available on this system.")

    def test_switch_in_progress_friendly_message(self):
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSwitchInProgressError,
        )

        service, registry, coordinator, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        failures = []

        def fail(eid, msg):
            failures.append((eid, msg))

        bridge.switch_failed.connect(fail)

        def rejecting(target):
            raise AudioEngineSwitchInProgressError("in progress")

        coordinator.switch_to = rejecting  # type: ignore[method-assign]
        bridge.switch_engine("gstreamer")
        assert failures[0][1] == ("Michi is already changing the audio engine.")

    def test_technical_message_preserved_separately(self):
        """The technical error stays in canonical state; the UI gets a
        friendly message only (diagnostic truth never destroyed)."""
        service, registry, coordinator, bridge, *_ = _graph()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        # a generic switch failure leaves canonical error state intact
        assert bridge.errorMessage == ""
        service.mark_failed(AudioEngineId.GSTREAMER, "technical failure detail")
        assert bridge.errorMessage == "technical failure detail"


class TestBridgeLifecycle:
    def test_state_notification_reaches_bridge(self):
        service, registry, coordinator, *_ = _graph()
        notified = []
        bridge = AudioEngineBridge(service, registry, coordinator)
        bridge.state_changed.connect(lambda: notified.append(1))
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        assert len(notified) == 1

    def test_dispose_unsubscribes(self):
        service, registry, coordinator, bridge, *_ = _graph()
        notified = []
        bridge.state_changed.connect(lambda: notified.append(1))
        bridge.dispose()
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        assert notified == []  # no callback after dispose
        bridge.dispose()  # idempotent

    def test_playback_notifications_refresh_readiness_and_unsubscribe(self):
        _, _, _, bridge, _, _, _, _, playback = _graph()
        notified = []
        bridge.state_changed.connect(lambda: notified.append(bridge.engineSwitchReady))

        assert bridge.engineSwitchReady is True
        playback._intent = True
        playback._accepted = True
        playback._on_playback_state_changed(PlaybackStatus.PLAYING)
        assert bridge.engineSwitchReady is False
        assert notified == [False]

        playback._intent = False
        playback._on_playback_state_changed(PlaybackStatus.STOPPED)
        assert bridge.engineSwitchReady is True
        assert notified == [False, True]

        bridge.dispose()
        playback._intent = True
        playback._on_playback_state_changed(PlaybackStatus.PLAYING)
        assert notified == [False, True]

    def test_probe_does_not_open_provider(self):
        _, registry, _, bridge, qt, gst, mpd, *_ = _graph()
        bridge.refresh_engines()
        assert qt.open_count == 0
        assert gst.open_count == 0
        assert mpd.open_count == 0

    def test_refresh_updates_availability_snapshot(self):
        service, registry, _, bridge, *_ = _graph()
        mpd = registry.provider(AudioEngineId.MPD)
        mpd._available = False
        bridge.refresh_engines()
        mpd_row = [e for e in bridge.engines if e["id"] == "mpd"][0]
        assert mpd_row["available"] is False
        # state change does NOT re-probe all engines (controlled snapshot)
        state_notify = []
        bridge.state_changed.connect(lambda: state_notify.append(1))
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        assert len(state_notify) == 1
        assert bridge.engines[0]["available"] is True  # snapshot unchanged
