from __future__ import annotations

import datetime
import time
from typing import Callable

from core.radio.models import (
    SessionState, StreamSessionState, StreamMetadata, StationId,
    RadioError, ReconnectPolicyConfig,
)
from core.radio.reconnect import ReconnectPolicy, RadioScheduler
from core.radio.icy_parser import IcyMetadataTracker
from core.radio.events import EventBus

_ALLOWED_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.REQUESTED, SessionState.CONNECTING},
    SessionState.REQUESTED: {SessionState.CONNECTING, SessionState.FAILED, SessionState.CANCELLED, SessionState.STOPPED},
    SessionState.CONNECTING: {SessionState.BUFFERING, SessionState.PLAYING, SessionState.FAILED, SessionState.CANCELLED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.BUFFERING: {SessionState.PLAYING, SessionState.FAILED, SessionState.CANCELLED, SessionState.STOPPED, SessionState.RECONNECTING},
    SessionState.PLAYING: {SessionState.RECONNECTING, SessionState.STOPPING, SessionState.STOPPED, SessionState.FAILED, SessionState.CANCELLED},
    SessionState.RECONNECTING: {SessionState.CONNECTING, SessionState.PLAYING, SessionState.CANCELLED, SessionState.FAILED, SessionState.STOPPED},
    SessionState.STOPPING: {SessionState.STOPPED, SessionState.FAILED},
    SessionState.STOPPED: {SessionState.REQUESTED, SessionState.CONNECTING},
    SessionState.FAILED: {SessionState.REQUESTED, SessionState.CONNECTING, SessionState.IDLE},
    SessionState.CANCELLED: {SessionState.REQUESTED, SessionState.IDLE},
}

# States that produce a visible transition (event + on_state_change).
_NOTIFY_STATES = frozenset({
    SessionState.REQUESTED,
    SessionState.CONNECTING,
    SessionState.BUFFERING,
    SessionState.PLAYING,
    SessionState.RECONNECTING,
    SessionState.STOPPED,
    SessionState.FAILED,
    SessionState.CANCELLED,
})


class StreamSession:
    def __init__(
        self,
        station_id: StationId,
        stream_url: str,
        event_bus: EventBus,
        generation: int,
        reconnect_config: ReconnectPolicyConfig | None = None,
        on_state_change: Callable[[StreamSessionState], None] | None = None,
        playback_backend: Callable[[str], bool] | None = None,
        playback_adapter=None,
        confirm_interval_ms: int = 300,
        connect_timeout_ms: int = 10000,
        monotonic: Callable[[], float] | None = None,
        scheduler: RadioScheduler | None = None,
    ):
        self._station_id = station_id
        self._stream_url = stream_url
        self._event_bus = event_bus
        self._generation = generation
        self._state = StreamSessionState(
            station_id=station_id, state=SessionState.IDLE,
            stream_url=stream_url, generation=generation,
        )
        self._reconnect = ReconnectPolicy(ReconnectPolicyConfig() if reconnect_config is None else reconnect_config)
        self._scheduler = scheduler or RadioScheduler()
        self._on_state_change = on_state_change
        self._playback_backend = playback_backend
        self._playback_adapter = playback_adapter
        self._confirm_interval_ms = max(50, int(confirm_interval_ms or 300))
        self._connect_timeout_ms = max(100, int(connect_timeout_ms or 10000))
        self._monotonic = monotonic or time.monotonic
        self._confirm_token: object | None = None
        self._connect_deadline: float | None = None
        self._metadata_tracker = IcyMetadataTracker(self._on_metadata_change)
        self._cancelled = False

    @property
    def state(self) -> StreamSessionState:
        return self._state

    def start(self):
        if self._state.state not in (SessionState.IDLE, SessionState.STOPPED, SessionState.FAILED, SessionState.CANCELLED):
            return
        self._cancelled = False
        self._transition(SessionState.REQUESTED)
        self._reconnect.reset()
        self._do_connect()

    def stop(self):
        self._cancelled = True
        self._reconnect.cancel()
        self._cancel_confirm()
        if self._state.state in (SessionState.PLAYING, SessionState.RECONNECTING, SessionState.BUFFERING, SessionState.CONNECTING):
            self._transition(SessionState.STOPPING)
            self._do_stop()
        self._transition(SessionState.STOPPED)

    def cancel(self):
        self._cancelled = True
        self._reconnect.cancel()
        self._cancel_confirm()
        self._scheduler.close()
        if self._state.state in (SessionState.IDLE, SessionState.STOPPED, SessionState.CANCELLED):
            self._state.state = SessionState.CANCELLED
            self._state.error = RadioError.CANCELLED
        else:
            self._do_stop()
            self._transition(SessionState.CANCELLED)

    def retry(self):
        if self._state.state in (SessionState.FAILED, SessionState.STOPPED):
            self.start()

    def update_stream_url(self, url: str):
        self._stream_url = url
        self._state.stream_url = url

    def _do_connect(self):
        if self._cancelled:
            self._transition(SessionState.CANCELLED)
            return
        if self._state.state == SessionState.PLAYING:
            return

        self._transition(SessionState.CONNECTING, error=RadioError.NONE)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self._state.started_at = now

        if self._playback_adapter is not None:
            if not self._playback_adapter.load_stream(self._stream_url):
                error, message = self._playback_adapter.get_error()
                self._transition(SessionState.FAILED, error=error or RadioError.CONNECTION_FAILED,
                                 error_message=message or "Playback failed to start")
                return
            if not self._playback_adapter.play():
                error, message = self._playback_adapter.get_error()
                self._transition(SessionState.FAILED, error=error or RadioError.CONNECTION_FAILED,
                                 error_message=message or "Playback failed to resume")
                return
            self._connect_deadline = self._monotonic() + self._connect_timeout_ms / 1000.0
            self._transition(SessionState.BUFFERING)
            self._schedule_confirm()
            return

        if self._playback_backend:
            ok = self._playback_backend(self._stream_url)
            if not ok:
                self._transition(SessionState.FAILED, error=RadioError.CONNECTION_FAILED, error_message="Playback failed to start")
                return
        self._transition(SessionState.PLAYING)

    def poll_playback(self):
        """One confirmation step against the adapter (PlayerService truth).

        Public so tests can drive confirmation deterministically; production
        drives it through the scheduler via :meth:`_schedule_confirm`. While
        PLAYING the poll keeps monitoring the player so a drop (player state
        ``reconnecting``/``stopped``) transitions the session to RECONNECTING.
        """
        if self._cancelled or self._playback_adapter is None:
            return
        current = self._state.state
        if current not in (SessionState.CONNECTING, SessionState.BUFFERING,
                           SessionState.PLAYING, SessionState.RECONNECTING):
            return

        mapped = self._playback_adapter.get_state()
        if mapped == SessionState.PLAYING:
            if current == SessionState.PLAYING:
                self._schedule_confirm()
            else:
                self._transition(SessionState.PLAYING)
            return
        if mapped == SessionState.FAILED:
            error, message = self._playback_adapter.get_error()
            self._transition(SessionState.FAILED, error=error or RadioError.CONNECTION_FAILED,
                             error_message=message or "Playback failed")
            return
        if mapped == SessionState.RECONNECTING:
            if current == SessionState.RECONNECTING:
                return  # reconnect already scheduled
            self.handle_playback_error(RadioError.CONNECTION_FAILED, "Player is reconnecting")
            return
        if current == SessionState.RECONNECTING:
            return
        if current == SessionState.PLAYING and mapped == SessionState.STOPPED:
            # Player stopped unexpectedly while playing: treat as a drop.
            self.handle_playback_error(RadioError.CONNECTION_FAILED, "Player stopped unexpectedly")
            return
        if self._connect_deadline is not None and self._monotonic() > self._connect_deadline:
            self._transition(SessionState.FAILED, error=RadioError.CONNECTION_TIMEOUT,
                             error_message="Connect timeout waiting for PLAYING")
            return
        self._schedule_confirm()

    def _schedule_confirm(self):
        if self._playback_adapter is None:
            return
        if self._state.state not in (SessionState.CONNECTING, SessionState.BUFFERING,
                                     SessionState.PLAYING):
            return
        self._cancel_confirm()
        self._confirm_token = self._scheduler.schedule(
            self._confirm_interval_ms, self.poll_playback,
        )

    def _cancel_confirm(self):
        if self._confirm_token is not None:
            self._scheduler.cancel(self._confirm_token)
            self._confirm_token = None

    def _do_stop(self):
        if self._playback_adapter is not None:
            self._playback_adapter.stop()
        elif self._playback_backend:
            pass

    def _reconnect_flow(self, error: RadioError):
        if not self._cancelled and self._reconnect.is_error_recoverable(error) and self._reconnect.should_retry():
            delay = self._reconnect.next_delay_ms()
            self._transition(SessionState.RECONNECTING, error=error, error_message=f"Reconnect attempt {self._reconnect.attempt} in {delay}ms")
            self._scheduler.schedule(delay, self._do_connect)
        else:
            if not self._reconnect.is_error_recoverable(error):
                self._transition(SessionState.FAILED, error=error, error_message="Unrecoverable error")
            else:
                self._transition(SessionState.FAILED, error=error, error_message=f"Max retries reached ({self._reconnect.attempt})")

    def handle_playback_error(self, error: RadioError, message: str = ""):
        self._state.error = error
        self._state.error_message = message
        if self._state.state == SessionState.CONNECTING:
            self._state.state = SessionState.RECONNECTING
        self._reconnect_flow(error)

    def update_metadata(self, metadata: StreamMetadata):
        self._metadata_tracker._last_metadata = metadata
        self._state.metadata = metadata

    def _transition(self, new_state: SessionState, error: RadioError = RadioError.NONE, error_message: str = ""):
        current = self._state.state
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if new_state not in allowed:
            return

        if new_state == SessionState.PLAYING:
            self._reconnect.reset()
            self._cancel_confirm()

        self._state.state = new_state
        if error != RadioError.NONE:
            self._state.error = error
            self._state.error_message = error_message

        if new_state in _NOTIFY_STATES:
            self._emit_event(f"session_{new_state.value}", self._state)
            if self._on_state_change:
                self._on_state_change(self._state)

    def _on_metadata_change(self, metadata: StreamMetadata):
        self._state.metadata = metadata
        self._emit_event("metadata_changed", self._state)

    def _emit_event(self, event_type: str, state: StreamSessionState):
        self._event_bus.emit(event_type, {
            "station_id": state.station_id,
            "state": state.state.value,
            "metadata": state.metadata,
            "error": state.error.value,
            "generation": self._generation,
        }, generation=self._generation)
