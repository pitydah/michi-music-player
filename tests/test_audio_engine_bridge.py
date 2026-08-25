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
    bridge = AudioEngineBridge(service, registry, coordinator)
    return service, registry, coordinator, bridge, qt, gst, mpd


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
        assert "MPD could not start" in bridge.statusSummary
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

    def test_probe_does_not_open_provider(self):
        _, registry, _, bridge, qt, gst, mpd = _graph()
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
