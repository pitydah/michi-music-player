"""Shared audio fakes for M11.3 tests (router/production composition)."""

from pathlib import Path

from michi.application.ports import AudioPort
from michi.domain.playback import PlaybackStatus


class RecordingBackend(AudioPort):
    """Fake AudioPort: records commands; can fire events on demand."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.commands: list[str] = []
        self.closed = False
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._st: list = []

    def load(self, file_path: Path) -> None:
        self.commands.append(f"load:{file_path.name}")

    def play(self) -> None:
        self.commands.append("play")

    def pause(self) -> None:
        self.commands.append("pause")

    def resume(self) -> None:
        self.commands.append("resume")

    def stop(self) -> None:
        self.commands.append("stop")
        self.closed = True

    def set_volume(self, value: int) -> None:
        self.commands.append(f"volume:{value}")

    def set_muted(self, muted: bool) -> None:
        self.commands.append(f"muted:{muted}")

    def seek(self, position_ms: int) -> None:
        self.commands.append(f"seek:{position_ms}")

    def position(self) -> int:
        self.commands.append("position")
        return 100

    def duration(self) -> int:
        self.commands.append("duration")
        return 200

    def subscribe_end_of_media(self, cb) -> None:
        self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb) -> None:
        if cb in self._eom:
            self._eom.remove(cb)

    def subscribe_position_changed(self, cb) -> None:
        self._pos.append(cb)

    def unsubscribe_position_changed(self, cb) -> None:
        if cb in self._pos:
            self._pos.remove(cb)

    def subscribe_duration_changed(self, cb) -> None:
        self._dur.append(cb)

    def unsubscribe_duration_changed(self, cb) -> None:
        if cb in self._dur:
            self._dur.remove(cb)

    def subscribe_media_accepted(self, cb) -> None:
        self._acc.append(cb)

    def unsubscribe_media_accepted(self, cb) -> None:
        if cb in self._acc:
            self._acc.remove(cb)

    def subscribe_media_rejected(self, cb) -> None:
        self._rej.append(cb)

    def unsubscribe_media_rejected(self, cb) -> None:
        if cb in self._rej:
            self._rej.remove(cb)

    def subscribe_playback_state_changed(self, cb) -> None:
        self._st.append(cb)

    def unsubscribe_playback_state_changed(self, cb) -> None:
        if cb in self._st:
            self._st.remove(cb)

    def close(self) -> None:
        self.closed = True

    # event faking
    def fire_duration(self, ms: int) -> None:
        for cb in list(self._dur):
            cb(ms)

    def fire_end_of_media(self) -> None:
        for cb in list(self._eom):
            cb()

    def fire_position(self, ms: int) -> None:
        for cb in list(self._pos):
            cb(ms)

    def fire_media_accepted(self, path: Path) -> None:
        for cb in list(self._acc):
            cb(path)

    def fire_media_rejected(self, path: Path, reason: str) -> None:
        for cb in list(self._rej):
            cb(path, reason)

    def fire_state(self, status: PlaybackStatus) -> None:
        for cb in list(self._st):
            cb(status)
