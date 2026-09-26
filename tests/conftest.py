"""Test fixtures — single canonical FakeAudioPort, never copied from Legacy."""

import os
import sys
from functools import wraps
from pathlib import Path

import pytest

from michi.application.ports import AudioLoadError

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# The platform plugin is chosen when the FIRST QApplication is constructed and
# cannot be changed afterwards. Several DAC test modules build their own
# QApplication in an autouse fixture, so setting this only inside the qapp
# fixture let a real platform (wayland/xcb) win whenever a DAC module ran first;
# QML interaction/geometry gates then failed purely from test ordering.
# CI already exports QT_QPA_PLATFORM=offscreen, so binding it at import time
# makes local runs deterministic and identical to CI.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """Provide Qt without depending on the optional pytest-qt plugin."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


class _SharedOutputTruth:
    mode = "shared"
    volume_policy = None


@pytest.fixture(autouse=True)
def _install_explicit_test_volume_policy(monkeypatch):
    """Legacy tests get an explicit Shared policy without weakening product API.

    Production composition always injects its one real VolumePolicyService;
    PlaybackService itself retains a required ``volume_port`` argument.
    """
    from michi.application.playback_service import PlaybackService
    from michi.application.volume_policy_service import VolumePolicyService

    original = PlaybackService.__init__

    @wraps(original)
    def test_init(self, audio_port, *, volume_port=None, **kwargs):
        if volume_port is None:
            output_tx = kwargs.get("output_tx")
            output = (
                output_tx
                if output_tx is not None
                and hasattr(output_tx, "mode")
                and hasattr(output_tx, "volume_policy")
                else _SharedOutputTruth()
            )
            volume_port = VolumePolicyService(audio_port, output)
        original(self, audio_port, volume_port=volume_port, **kwargs)

    monkeypatch.setattr(PlaybackService, "__init__", test_init)


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
        if getattr(self, "fail_load", False):
            raise AudioLoadError(p, "load failed", previous_source_preserved=False)
        self.loaded = p

    def emit_position_changed(self, ms):
        for cb in list(self._pos):
            cb(ms)

    def backend_state(self):
        return self.state

    def play(self):
        self.state = "playing"

    def pause(self):
        self.state = "paused"

    def resume(self):
        self.state = "playing"

    def stop(self):
        if getattr(self, "fail_stop", False):
            raise RuntimeError("stop failed")
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
