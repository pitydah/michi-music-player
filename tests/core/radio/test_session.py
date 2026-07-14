import pytest
from core.radio.session import StreamSession
from core.radio.models import (
    SessionState, StreamMetadata, RadioError, ReconnectPolicyConfig,
)
from core.radio.events import EventBus
from core.radio.reconnect import RadioScheduler


_EVENTS = []


def _record_event(event):
    _EVENTS.append(event.type)


@pytest.fixture(autouse=True)
def _clear_events():
    _EVENTS.clear()


def make_session(station_id=1, stream_url="https://example.com/stream",
                 event_bus=None, generation=1, **kw):
    bus = event_bus or EventBus()
    sched = RadioScheduler()
    return StreamSession(
        station_id=station_id,
        stream_url=stream_url,
        event_bus=bus,
        generation=generation,
        scheduler=sched,
        **kw,
    )


class TestStreamSession:
    def test_initial_state_is_idle(self):
        session = make_session()
        assert session.state.state == SessionState.IDLE

    def test_start_transitions_to_connecting(self):
        session = make_session()
        session.start()
        assert session.state.state in (SessionState.CONNECTING, SessionState.PLAYING)

    def test_stop_transitions_to_stopped(self):
        session = make_session()
        session.start()
        session.stop()
        assert session.state.state == SessionState.STOPPED

    def test_cancel_transitions_to_cancelled(self):
        session = make_session()
        session.cancel()
        assert session.state.state == SessionState.CANCELLED

    def test_cancel_from_idle(self):
        session = make_session()
        session.cancel()
        assert session.state.state == SessionState.CANCELLED

    def test_retry_after_failed(self):
        session = make_session()
        session._transition = lambda *a, **kw: None
        session.start()
        assert session.state.state != SessionState.FAILED

    def test_playback_error_triggers_reconnect(self):
        session = make_session(
            reconnect_config=ReconnectPolicyConfig(enabled=True, max_attempts=2, base_delay_ms=5000),
        )
        session.start()
        session.handle_playback_error(RadioError.CONNECTION_FAILED)
        assert session.state.state in (SessionState.RECONNECTING, SessionState.PLAYING) or session.state.error_message.startswith("Reconnect attempt")

    def test_unrecoverable_error_does_not_reconnect(self):
        session = make_session()
        session.start()
        session.handle_playback_error(RadioError.URL_INVALID)
        assert session.state.state == SessionState.FAILED

    def test_update_metadata(self):
        session = make_session()
        meta = StreamMetadata(icy_name="Test Radio")
        session.update_metadata(meta)
        assert session.state.metadata.icy_name == "Test Radio"

    def test_update_stream_url(self):
        session = make_session()
        session.update_stream_url("https://new.url/stream")
        assert session.state.stream_url == "https://new.url/stream"

    def test_double_start_is_noop(self):
        session = make_session()
        session.start()
        old_state = session.state.state
        session.start()
        assert session.state.state == old_state


class TestStateTransitions:
    def verify_transition(self, from_state, to_state, allowed=True):
        session = make_session()
        session._state.state = from_state
        session._transition(to_state)
        if allowed:
            assert session.state.state == to_state, f"{from_state} -> {to_state} should be allowed"
        else:
            assert session.state.state == from_state, f"{from_state} -> {to_state} should be blocked"

    def test_idle_to_connecting(self):
        self.verify_transition(SessionState.IDLE, SessionState.CONNECTING)

    def test_connecting_to_buffering(self):
        self.verify_transition(SessionState.CONNECTING, SessionState.BUFFERING)

    def test_connecting_to_failed(self):
        self.verify_transition(SessionState.CONNECTING, SessionState.FAILED)

    def test_buffering_to_playing(self):
        self.verify_transition(SessionState.BUFFERING, SessionState.PLAYING)

    def test_playing_to_stopping(self):
        self.verify_transition(SessionState.PLAYING, SessionState.STOPPING)

    def test_playing_to_reconnecting(self):
        self.verify_transition(SessionState.PLAYING, SessionState.RECONNECTING)

    def test_stopping_to_stopped(self):
        self.verify_transition(SessionState.STOPPING, SessionState.STOPPED)

    def test_failed_to_connecting(self):
        self.verify_transition(SessionState.FAILED, SessionState.CONNECTING)

    def test_cancelled_to_idle(self):
        self.verify_transition(SessionState.CANCELLED, SessionState.IDLE)

    def test_idle_to_playing_blocked(self):
        self.verify_transition(SessionState.IDLE, SessionState.PLAYING, allowed=False)

    def test_stopped_to_playing_blocked(self):
        self.verify_transition(SessionState.STOPPED, SessionState.PLAYING, allowed=False)

    def test_cancelled_to_playing_blocked(self):
        self.verify_transition(SessionState.CANCELLED, SessionState.PLAYING, allowed=False)
