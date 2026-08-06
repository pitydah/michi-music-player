"""Radio playback vertical (FASE 5 P0 stabilization).

Real canonical services (SqliteStationRepository + SqliteRadioHistoryRepository
+ RadioService) with the REAL RadioPlaybackAdapter over a controllable fake
player, driven by a fake scheduler + fake monotonic clock so every transition
is deterministic.

Contract under test:

- Playback is never reported as completed while the session is only
  CONNECTING/BUFFERING: ``start_station`` returns accepted=True + status, and
  effective success (PLAYING + history kind=play) requires the adapter
  (PlayerService) readback to confirm PLAYING.
- There is no ``return True`` fallback: an absent player or a rejected stream
  is an explicit failure.
- History kinds are distinct: attempt / play / failure / reconnect / stopped.
"""
from __future__ import annotations

import pytest

from core.radio.models import (
    SessionState, StationCreateRequest, StreamMetadata, RadioError,
    ReconnectPolicyConfig,
)
from core.radio.playback_adapter import RadioPlaybackAdapter
from core.radio.service import RadioService


class FakePlayer:
    """Controllable PlayerService stand-in (state/play_url/stop/resume)."""

    def __init__(self, initial: str = "stopped"):
        self._state = initial
        self.loaded: list[str] = []
        self.fail_urls: set[str] = set()
        self.raise_on_load: Exception | None = None
        self.reject_readback = False
        self.stop_calls = 0

    @property
    def state(self) -> str:
        if self.reject_readback:
            raise RuntimeError("readback rejected")
        return self._state

    def play_url(self, url: str):
        if self.raise_on_load is not None:
            raise self.raise_on_load
        if url in self.fail_urls:
            raise ConnectionError(f"rejected: {url}")
        self.loaded.append(url)

    def stop(self):
        self.stop_calls += 1
        self._state = "stopped"

    def resume(self):
        pass

    def set_state(self, state: str):
        self._state = state


class FakeScheduler:
    """Deterministic scheduler: callbacks only run when the test fires them."""

    def __init__(self):
        self._pending: dict[int, callable] = {}
        self._next = 0

    def schedule(self, delay_ms: int, callback):
        self._next += 1
        self._pending[self._next] = callback
        return self._next

    def cancel(self, token):
        self._pending.pop(token, None)

    def close(self):
        self._pending.clear()

    def fire_all(self):
        pending = list(self._pending.values())
        self._pending.clear()
        for cb in pending:
            cb()

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class FakeClock:
    """Advanceable monotonic clock."""

    def __init__(self, start: float = 0.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float):
        self._now += seconds


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "radio.db")


def _repos(db_path: str):
    from infrastructure.radio.history_repository import SqliteRadioHistoryRepository
    from infrastructure.radio.station_repository import SqliteStationRepository

    station_repo = SqliteStationRepository(db_path)
    station_repo.initialize()
    history_repo = SqliteRadioHistoryRepository(db_path)
    history_repo.initialize()
    return station_repo, history_repo


def _build(db_path: str, player: FakePlayer | None,
           clock: FakeClock | None = None,
           connect_timeout_s: int = 10,
           reconnect: ReconnectPolicyConfig | None = None,
           adapter=None) -> RadioService:
    station_repo, history_repo = _repos(db_path)
    scheduler = FakeScheduler()
    if adapter is None:
        adapter = RadioPlaybackAdapter(player_service=player)
    return RadioService(
        station_repo=station_repo,
        history_repo=history_repo,
        playback_adapter=adapter,
        scheduler=scheduler,
        confirm_interval_ms=50,
        connect_timeout_s=connect_timeout_s,
        monotonic_clock=clock or FakeClock(),
        reconnect_config=reconnect or ReconnectPolicyConfig(
            enabled=True, max_attempts=5, base_delay_ms=0, jitter_ms=0,
        ),
    )


def _add_station(svc: RadioService, name: str = "FM", url: str = "http://fm/stream") -> int:
    result = svc.create_station(StationCreateRequest(name=name, stream_url=url))
    assert result.ok
    return result.station.id


def _kinds(svc: RadioService) -> list[str]:
    return [h.get("result") or "" for h in svc.history()]


def _reach_playing(svc: RadioService, player: FakePlayer, title: str = ""):
    if title:
        svc._session.update_metadata(StreamMetadata(stream_title=title))
    player.set_state("playing")
    svc.poll_playback()


class TestPlaybackVertical:
    def test_backend_absent(self, db_path):
        """Adapter with no player: explicit failure, never ok=True."""
        adapter = RadioPlaybackAdapter(player_service=None)
        assert adapter.load_stream("http://x/stream") is False
        error, _message = adapter.get_error()
        assert error == RadioError.BACKEND_UNAVAILABLE

        svc = _build(db_path, player=None, adapter=adapter)
        station_id = _add_station(svc)
        result = svc.start_station(station_id)
        assert result.ok is False
        assert result.accepted is False
        assert result.status == "failed"
        assert result.error == RadioError.BACKEND_UNAVAILABLE
        # The attempt is recorded and the failure is explicit — no play.
        kinds = _kinds(svc)
        assert "attempt" in kinds
        assert "failure" in kinds
        assert "play" not in kinds

    def test_invalid_url(self, db_path):
        """load_stream fails → FAILED + history failure + error code."""
        player = FakePlayer()
        player.raise_on_load = ValueError("malformed url")
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        result = svc.start_station(station_id)
        assert result.ok is False  # explicit failure, never ok=True
        assert result.status == "failed"
        assert svc.session.state == SessionState.FAILED
        assert svc.session.error == RadioError.CONNECTION_FAILED

        kinds = _kinds(svc)
        assert "attempt" in kinds
        assert "failure" in kinds
        assert "play" not in kinds
        failure = svc.history()[0]
        assert failure["error_code"] == "connection_failed"

    def test_connection_rejected(self, db_path):
        """Player rejects after load → FAILED, no play history entry."""
        player = FakePlayer()
        player.reject_readback = True
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        result = svc.start_station(station_id)
        assert result.ok and result.accepted
        assert svc.session.state == SessionState.BUFFERING
        svc.poll_playback()

        assert svc.session.state == SessionState.FAILED
        kinds = _kinds(svc)
        assert "attempt" in kinds
        assert "failure" in kinds
        assert "play" not in kinds

    def test_timeout(self, db_path):
        """No PLAYING within timeout → FAILED + history failure."""
        clock = FakeClock()
        player = FakePlayer()
        svc = _build(db_path, player=player, clock=clock, connect_timeout_s=1)
        station_id = _add_station(svc)

        result = svc.start_station(station_id)
        assert result.ok and result.accepted
        assert svc.session.state == SessionState.BUFFERING

        clock.advance(2.0)
        svc.poll_playback()

        assert svc.session.state == SessionState.FAILED
        assert svc.session.error == RadioError.CONNECTION_TIMEOUT
        kinds = _kinds(svc)
        assert "failure" in kinds
        assert "play" not in kinds
        assert kinds[0] == "failure"  # latest entry is the failure

    def test_no_play_history_on_connecting(self, db_path):
        """While CONNECTING/BUFFERING: attempt exists, play does not."""
        player = FakePlayer()
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        result = svc.start_station(station_id)
        assert result.ok and result.accepted
        assert result.status in ("connecting", "buffering")

        kinds = _kinds(svc)
        assert "attempt" in kinds
        assert "play" not in kinds

    def test_reaches_playing(self, db_path):
        """Fake player confirms PLAYING → play entry with stream metadata."""
        player = FakePlayer()
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        result = svc.start_station(station_id)
        assert result.ok and result.accepted
        assert result.status in ("connecting", "buffering")
        assert svc.session.state == SessionState.BUFFERING

        _reach_playing(svc, player, title="Test Song")
        assert svc.session.state == SessionState.PLAYING

        kinds = _kinds(svc)
        assert "attempt" in kinds
        assert "play" in kinds
        assert "failure" not in kinds
        play = next(h for h in svc.history() if h["result"] == "play")
        assert play["metadata_title"] == "Test Song"

    def test_reconnect(self, db_path):
        """Player drops then recovers: RECONNECTING → PLAYING."""
        player = FakePlayer()
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        svc.start_station(station_id)
        _reach_playing(svc, player)
        assert svc.session.state == SessionState.PLAYING

        # Player drops → readback says reconnecting → reconnect flow.
        player.set_state("reconnecting")
        svc.poll_playback()
        assert svc.session.state == SessionState.RECONNECTING
        kinds = _kinds(svc)
        assert "reconnect" in kinds

        # Reconnect fires: load again, buffer, then player recovers → PLAYING.
        svc._session._scheduler.fire_all()
        assert svc.session.state == SessionState.BUFFERING
        player.set_state("playing")
        svc.poll_playback()
        assert svc.session.state == SessionState.PLAYING
        assert player.loaded.count("http://fm/stream") >= 2

    def test_stop(self, db_path):
        """stop → STOPPED + history stopped entry + player stopped."""
        player = FakePlayer()
        svc = _build(db_path, player=player)
        station_id = _add_station(svc)

        svc.start_station(station_id)
        _reach_playing(svc, player)
        result = svc.stop()
        assert result.ok
        assert svc.session is None
        assert player.stop_calls == 1
        kinds = _kinds(svc)
        assert "stopped" in kinds

    def test_station_change(self, db_path):
        """Switching stations stops old + starts new (no stale PLAYING)."""
        player = FakePlayer()
        svc = _build(db_path, player=player)
        a_id = _add_station(svc, name="A FM", url="http://a.fm/stream")
        _add_station(svc, name="B FM", url="http://b.fm/stream")

        svc.start_station(a_id)
        _reach_playing(svc, player)
        assert svc.session.state == SessionState.PLAYING

        player.set_state("stopped")
        result = svc.play_station("http://b.fm/stream")
        assert result.ok and result.accepted
        assert svc.session.station_id != a_id
        assert svc.session.state == SessionState.BUFFERING

        kinds = _kinds(svc)
        assert kinds.count("attempt") == 2
        assert kinds.count("stopped") == 1
        assert kinds.count("play") == 1
        assert svc.session.state != SessionState.PLAYING  # no stale PLAYING

        player.set_state("playing")
        svc.poll_playback()
        assert svc.session.state == SessionState.PLAYING

    def test_readback_player_service(self, db_path):
        """service.get_state reflects adapter.get_state (PlayerService truth)."""
        player = FakePlayer()
        adapter = RadioPlaybackAdapter(player_service=player)
        svc = _build(db_path, player=player, adapter=adapter)

        assert svc.get_state() == SessionState.STOPPED
        player.set_state("playing")
        assert svc.get_state() == adapter.get_state() == SessionState.PLAYING
        player.set_state("paused")
        assert svc.get_state() == adapter.get_state() == SessionState.BUFFERING
        player.set_state("reconnecting")
        assert svc.get_state() == adapter.get_state() == SessionState.RECONNECTING


class TestAdapterMapping:
    def test_player_states_map(self):
        player = FakePlayer("playing")
        adapter = RadioPlaybackAdapter(player_service=player)
        assert adapter.get_state() == SessionState.PLAYING

        player.set_state("paused")
        assert adapter.get_state() == SessionState.BUFFERING

        player.set_state("stopped")
        assert adapter.get_state() == SessionState.STOPPED

        player.set_state("reconnecting")
        assert adapter.get_state() == SessionState.RECONNECTING

    def test_load_stream_success_clears_error(self):
        player = FakePlayer()
        adapter = RadioPlaybackAdapter(player_service=player)
        assert adapter.load_stream("http://ok/stream") is True
        assert adapter.get_error() == (RadioError.NONE, "")
        assert player.loaded == ["http://ok/stream"]

    def test_load_stream_exception_is_explicit_failure(self):
        player = FakePlayer()
        player.raise_on_load = ConnectionError("refused")
        adapter = RadioPlaybackAdapter(player_service=player)
        assert adapter.load_stream("http://bad/stream") is False
        error, message = adapter.get_error()
        assert error == RadioError.CONNECTION_FAILED
        assert "refused" in message
