"""MpdBackend — implements the common AudioBackend API via MPD.

Translates Michi's canonical queue model into MPD's playlist commands.
Supports local and remote MPD instances.
"""

import logging
import threading

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)
from audio.backends.errors import BackendPlaybackError
from audio.mpd.mpd_client import MpdClient
from audio.mpd.mpd_errors import MpdConnectionError
from audio.mpd.mpd_path_mapper import MpdPathMapper
from audio.mpd.mpd_models import MpdStatus

logger = logging.getLogger("michi.mpd.backend")


class MpdBackend:
    """AudioBackend using MPD as the playback engine."""

    backend_id = "mpd"
    display_name = "MPD"

    def __init__(self, host: str = "127.0.0.1", port: int = 6600,
                 password: str = "", path_mapper: MpdPathMapper | None = None):
        self._client = MpdClient(host=host, port=port, password=password)
        self._mapper = path_mapper or MpdPathMapper()
        self._lock = threading.Lock()
        self._local_paths: list[str] = []
        self._queue_index: int = -1

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend_id=self.backend_id,
            display_name=self.display_name,
            supports_bitperfect=True,
            supports_dsd=True,
            supports_dop=True,
            supports_remote=True,
            supports_server_mode=True,
            supports_digital_volume=False,
        )

    @property
    def client(self) -> MpdClient:
        return self._client

    @property
    def connected(self) -> bool:
        return self._client.connected

    def connect(self):
        if not self._client.connected:
            self._client.connect()

    def disconnect(self):
        self._client.disconnect()

    # ── AudioBackend API ──

    def play(self, path_or_uri: str):
        with self._lock:
            mpd_path = self._mapper.to_mpd_path(path_or_uri)
            try:
                self._client.clear()
                self._client.add(mpd_path)
                self._client.playpos(0)
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e))

    def pause(self):
        try:
            self._client.pause(1)
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def resume(self):
        try:
            self._client.pause(0)
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def toggle(self):
        try:
            st = self._client.status()
            if st.state == "play":
                self._client.pause(1)
            elif st.state == "pause":
                self._client.pause(0)
            else:
                status = self._client.status()
                if status.playlistlength > 0:
                    self._client.playpos(0)
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def stop(self):
        try:
            self._client.stop()
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def seek(self, seconds: float):
        try:
            self._client.seekcur(seconds)
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def set_volume(self, volume: int):
        try:
            self._client.setvol(volume)
        except MpdConnectionError as e:
            raise BackendPlaybackError(str(e))

    def set_queue(self, paths: list[str], start_index: int = 0):
        with self._lock:
            self._local_paths = list(paths)
            self._queue_index = max(0, min(start_index, len(paths) - 1)) if paths else -1
            try:
                self._client.clear()
                for p in paths:
                    mpd_path = self._mapper.to_mpd_path(p)
                    self._client.add(mpd_path)
                if self._queue_index >= 0:
                    self._client.playpos(self._queue_index)
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e))

    def enqueue(self, paths: list[str], play_now: bool = True):
        with self._lock:
            self._local_paths.extend(paths)
            try:
                for p in paths:
                    mpd_path = self._mapper.to_mpd_path(p)
                    self._client.add(mpd_path)
                if play_now:
                    new_idx = len(self._local_paths) - len(paths)
                    self._queue_index = new_idx
                    self._client.playpos(new_idx)
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e))

    def enqueue_next(self, paths: list[str]):
        with self._lock:
            insert_pos = self._queue_index + 1
            self._local_paths[insert_pos:insert_pos] = paths
            try:
                for i, p in enumerate(paths):
                    mpd_path = self._mapper.to_mpd_path(p)
                    self._client.add(mpd_path)
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e))

    def clear_queue(self):
        with self._lock:
            self._local_paths = []
            self._queue_index = -1
            try:
                self._client.clear()
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e))

    def play_next(self) -> bool:
        with self._lock:
            if self._queue_index < len(self._local_paths) - 1:
                self._queue_index += 1
                try:
                    self._client.next()
                    return True
                except MpdConnectionError as e:
                    raise BackendPlaybackError(str(e))
            return False

    def play_prev(self) -> bool:
        with self._lock:
            if self._queue_index > 0:
                self._queue_index -= 1
                try:
                    self._client.previous()
                    return True
                except MpdConnectionError as e:
                    raise BackendPlaybackError(str(e))
            return False

    def get_queue(self) -> list[dict]:
        try:
            songs = self._client.playlistinfo()
            items = []
            for i, s in enumerate(songs):
                local_path = self._mapper.from_mpd_path(s.file) if s.file else ""
                items.append({
                    "filepath": local_path,
                    "title": s.title or "",
                    "artist": s.artist or "",
                    "duration": s.duration,
                    "is_current": (i == self._queue_index or
                                   i == self._client.status().song),
                })
            return items
        except MpdConnectionError:
            return []

    def get_queue_index(self) -> int:
        try:
            st = self._client.status()
            return st.song
        except MpdConnectionError:
            return self._queue_index

    def get_snapshot(self) -> PlaybackSnapshot:
        try:
            st = self._client.status()
            cs = self._client.currentsong()
        except MpdConnectionError:
            return PlaybackSnapshot(
                backend_id=self.backend_id, state="error", error="MPD connection lost")

        state_map = {
            "play": "playing",
            "pause": "paused",
            "stop": "stopped",
        }
        local_path = self._mapper.from_mpd_path(cs.file) if cs.file else ""
        return PlaybackSnapshot(
            backend_id=self.backend_id,
            state=state_map.get(st.state, "stopped"),
            current_path=local_path,
            current_uri=cs.file,
            title=cs.title or "",
            artist=cs.artist or "",
            album=cs.album or "",
            position_seconds=st.elapsed,
            duration_seconds=st.duration,
            volume=max(0, st.volume),
            queue_index=st.song,
            queue_length=st.playlistlength,
        )

    def get_diagnostics(self) -> AudioDiagnostics:
        try:
            st = self._client.status()
            cs = self._client.currentsong()
            outputs = self._client.outputs()
        except MpdConnectionError:
            return AudioDiagnostics(
                backend_id=self.backend_id, profile="mpd",
                bitperfect_status="not_connected")

        active_outputs = [o for o in outputs if o.enabled]
        device_name = active_outputs[0].name if active_outputs else ""
        audio_parts = st.audio.split(":") if st.audio else []
        out_rate = int(audio_parts[0]) if len(audio_parts) > 0 else 0

        return AudioDiagnostics(
            backend_id=self.backend_id,
            profile="mpd_hifi",
            device_name=device_name,
            input_codec=cs.file.split(".")[-1] if "." in cs.file else "",
            output_sample_rate=out_rate,
            bitperfect_requested=True,
            bitperfect_possible=True,
            bitperfect_status="requested",
            digital_volume_active=False,
        )

    def shutdown(self):
        if self._client.connected:
            self._client.stop()
        self._client.disconnect()
