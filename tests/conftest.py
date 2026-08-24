"""Test fixtures — single canonical FakeAudioPort, never copied from Legacy."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class FakeAudioPort:
    """Minimal fake for testing. Not copied from Legacy."""

    def __init__(self) -> None:
        self.loaded: Path | None = None
        self.state: str = "stopped"
        self.volume: int = 80
        self.muted: bool = False
        self._position: int = 0
        self._duration: int = 0
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pstate: list = []
        self.seek_calls: list[int] = []

    def load(self, p):
        self.loaded = p

    def play(self):
        self.state = "playing"

    def pause(self):
        self.state = "paused"

    def resume(self):
        self.state = "playing"

    def stop(self):
        self.state = "stopped"

    def set_volume(self, v):
        self.volume = max(0, min(100, v))

    def set_muted(self, m):
        self.muted = m

    def seek(self, ms):
        self._position = ms
        self.seek_calls.append(ms)

    def position(self):
        return self._position

    def duration(self):
        return self._duration

    def set_duration(self, ms):
        self._duration = ms

    def subscribe_end_of_media(self, cb):
        if cb not in self._eom:
            self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb):
        if cb in self._eom:
            self._eom.remove(cb)

    def subscribe_position_changed(self, cb):
        if cb not in self._pos:
            self._pos.append(cb)

    def unsubscribe_position_changed(self, cb):
        if cb in self._pos:
            self._pos.remove(cb)

    def subscribe_duration_changed(self, cb):
        if cb not in self._dur:
            self._dur.append(cb)

    def unsubscribe_duration_changed(self, cb):
        if cb in self._dur:
            self._dur.remove(cb)

    def subscribe_media_accepted(self, cb):
        if cb not in self._acc:
            self._acc.append(cb)

    def unsubscribe_media_accepted(self, cb):
        if cb in self._acc:
            self._acc.remove(cb)

    def subscribe_media_rejected(self, cb):
        if cb not in self._rej:
            self._rej.append(cb)

    def unsubscribe_media_rejected(self, cb):
        if cb in self._rej:
            self._rej.remove(cb)

    def subscribe_playback_state_changed(self, cb):
        if cb not in self._pstate:
            self._pstate.append(cb)

    def unsubscribe_playback_state_changed(self, cb):
        if cb in self._pstate:
            self._pstate.remove(cb)

    def trigger_end_of_media(self):
        for cb in list(self._eom):
            cb()

    def trigger_position(self, pos_ms):
        for cb in list(self._pos):
            cb(pos_ms)

    def trigger_duration(self, dur_ms):
        for cb in list(self._dur):
            cb(dur_ms)

    def trigger_media_accepted(self, path):
        # Acceptance only: never implies playing state (play() is a separate
        # command observation; playback state is a separate event channel).
        for cb in list(self._acc):
            cb(path)

    def trigger_media_rejected(self, path, msg):
        for cb in list(self._rej):
            cb(path, msg)

    def trigger_playback_state(self, status):
        for cb in list(self._pstate):
            cb(status)


@pytest.fixture
def fake_audio() -> FakeAudioPort:
    return FakeAudioPort()


@pytest.fixture
def playback_service(fake_audio: FakeAudioPort):
    from michi.application.playback_service import PlaybackService

    return PlaybackService(fake_audio)


@pytest.fixture
def queue_service(playback_service):
    from michi.application.queue_service import QueueService

    # M4-R1: QueueService has NO playback dependency (the legacy positional
    # arg is absorbed and ignored during the migration window).
    return QueueService()


@pytest.fixture
def playback_session(playback_service, queue_service):
    from michi.application.playback_session_service import (
        PlaybackSessionService,
    )

    return PlaybackSessionService(playback_service, queue_service)


class FakeSettingsRepo:
    """Minimal fake — not copied from Legacy."""

    def __init__(self) -> None:
        self._state = None
        from michi.domain.settings import SettingsState

        self._state = SettingsState()

    def load(self):
        from michi.domain.settings import SettingsState

        return SettingsState(
            volume=self._state.volume,
            muted=self._state.muted,
            last_directory=self._state.last_directory,
            recent_files=list(self._state.recent_files),
        )

    def save(self, state):
        from michi.domain.settings import SettingsState

        self._state = SettingsState(
            volume=state.volume,
            muted=state.muted,
            last_directory=state.last_directory,
            recent_files=list(state.recent_files),
        )


@pytest.fixture
def fake_settings_repo():
    return FakeSettingsRepo()
