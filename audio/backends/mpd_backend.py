"""MpdBackend — implements the common AudioBackend API via MPD.

Translates Michi's canonical queue model into MPD's playlist commands.
Supports local and remote MPD instances.
"""

import logging
import threading

from PySide6.QtCore import QObject, QTimer, Signal

from audio.backends.types import (
    BackendCapabilities,
    PlaybackSnapshot,
    AudioDiagnostics,
)
from audio.backends.errors import BackendPlaybackError, BackendCapabilityError
from audio.mpd.mpd_client import MpdClient
from audio.mpd.mpd_errors import MpdAckError, MpdConnectionError, MpdProtocolError
from audio.mpd.mpd_path_mapper import MpdPathMapper


logger = logging.getLogger("michi.mpd.backend")


class MpdBackend(QObject):
    """AudioBackend using MPD as the playback engine."""

    position_changed = Signal(float)
    state_changed = Signal(str)
    duration_changed = Signal(float)
    queue_progressed = Signal(int, str, str, object)

    backend_id = "mpd"
    display_name = "MPD"

    def __init__(self, host: str = "127.0.0.1", port: int = 6600,
                 password: str = "", path_mapper: MpdPathMapper | None = None,
                 parent=None):
        super().__init__(parent)
        self._client = MpdClient(host=host, port=port, password=password)
        self._mapper = path_mapper or MpdPathMapper()
        self._lock = threading.Lock()
        self._local_paths: list[str] = []
        self._queue_index: int = -1
        self._dsd_mode: str = "pcm"
        self._dop_enabled: bool = False
        self._last_snapshot: PlaybackSnapshot | None = None
        self._queue_revision: int | None = None
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_snapshot)

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

    def connect(self) -> None:
        if not self._client.connected:
            self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    def _ensure(self):
        self._client.ensure_connected()

    def _start_poll(self):
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def _stop_poll(self):
        self._poll_timer.stop()
        self._last_snapshot = None

    def _poll_snapshot(self):
        try:
            snap = self.get_snapshot()
        except Exception:
            return
        if self._last_snapshot:
            if snap.state != self._last_snapshot.state:
                self.state_changed.emit(snap.state)
            if snap.position_seconds != self._last_snapshot.position_seconds:
                self.position_changed.emit(snap.position_seconds)
            if snap.duration_seconds != self._last_snapshot.duration_seconds:
                self.duration_changed.emit(snap.duration_seconds)
            if snap.current_path != self._last_snapshot.current_path:
                if snap.queue_index >= 0 and snap.current_path:
                    self._queue_index = snap.queue_index
                    self.queue_progressed.emit(
                        snap.queue_index,
                        snap.current_path,
                        "gapless",
                        self._queue_revision,
                    )
                self.state_changed.emit(snap.state)
        else:
            self.state_changed.emit(snap.state)
            self.position_changed.emit(snap.position_seconds)
            self.duration_changed.emit(snap.duration_seconds)
        self._last_snapshot = snap

    def set_profile(self, profile_key: str) -> None:
        self._profile_key = profile_key

    def configure_dsd(self, mode: str, dop: bool = False) -> None:
        """Configure MPD for DSD playback.

        Args:
            mode: "pcm", "dop", or "native"
            dop: enable DoP (DSD over PCM)
        """
        self._dsd_mode = mode
        self._dop_enabled = dop
        logger.info("MPD DSD mode set to: %s (dop=%s)", mode, dop)

    # ── AudioBackend API ──

    def play(self, path_or_uri: str) -> None:
        with self._lock:
            mpd_path = self._mapper.to_mpd_path(path_or_uri)
            try:
                self._client.ensure_connected()
                self._client.clear()
                self._client.add(mpd_path)
                self._client.playpos(0)
                self._start_poll()
            except MpdConnectionError as e:
                raise BackendPlaybackError(str(e)) from e

    def pause(self) -> None:
        try:
            self._ensure()
            self._client.pause(1)
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
            raise BackendPlaybackError(str(e)) from e

    def resume(self) -> None:
        try:
            self._ensure()
            self._client.pause(0)
            self._start_poll()
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
            raise BackendPlaybackError(str(e)) from e

    def toggle(self) -> None:
        try:
            self._ensure()
            st = self._client.status()
            if st.state == "play":
                self._client.pause(1)
            elif st.state == "pause":
                self._client.pause(0)
            else:
                status = self._client.status()
                if status.playlistlength > 0:
                    self._client.playpos(0)
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
            raise BackendPlaybackError(str(e)) from e

    def stop(self) -> None:
        try:
            self._ensure()
            self._client.stop()
            self._stop_poll()
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
            raise BackendPlaybackError(str(e)) from e

    def seek(self, seconds: float) -> None:
        try:
            self._ensure()
            self._client.seekcur(seconds)
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
            raise BackendPlaybackError(str(e)) from e

    def set_volume(self, volume: int) -> None:
        raise BackendCapabilityError("Volumen digital bloqueado en MPD bit-perfect")

    def set_repeat(self, mode: str) -> str:
        if mode not in {"none", "all", "one"}:
            raise ValueError("Invalid repeat mode")
        self._ensure()
        self._client.repeat(1 if mode in {"all", "one"} else 0)
        self._repeat = mode
        return mode

    def set_shuffle(self, enabled: bool) -> bool:
        self._ensure()
        # QueueService already supplies the effective order; MPD must not randomize it.
        self._client.random(0)
        self._shuffle = bool(enabled)
        return self._shuffle

    def set_queue(self, paths: list[str], start_index: int = 0,
                  revision: int | None = None) -> None:
        with self._lock:
            self._local_paths = list(paths)
            self._queue_index = max(0, min(start_index, len(paths) - 1)) if paths else -1
            self._queue_revision = revision
            try:
                self._ensure()
                self._client.clear()
                for p in paths:
                    mpd_path = self._mapper.to_mpd_path(p)
                    self._client.add(mpd_path)
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def play_queue_index(self, index: int) -> bool:
        if index < 0 or index >= len(self._local_paths):
            return False
        try:
            self._ensure()
            self._client.playpos(index)
            self._queue_index = index
            self._start_poll()
            return True
        except (MpdConnectionError, MpdAckError, MpdProtocolError) as exc:
            raise BackendPlaybackError(str(exc)) from exc

    def enqueue(self, paths: list[str], play_now: bool = True) -> None:
        with self._lock:
            self._local_paths.extend(paths)
            try:
                self._ensure()
                for p in paths:
                    mpd_path = self._mapper.to_mpd_path(p)
                    self._client.add(mpd_path)
                if play_now:
                    new_idx = len(self._local_paths) - len(paths)
                    self._queue_index = new_idx
                    self._client.playpos(new_idx)
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def enqueue_next(self, paths: list[str]) -> None:
        with self._lock:
            try:
                self._ensure()
                st = self._client.status()
                insert_pos = max(0, st.song + 1)
                for offset, p in enumerate(paths):
                    mpd_path = self._mapper.to_mpd_path(p)
                    sid = self._client.addid(mpd_path)
                    if sid >= 0:
                        self._client.moveid(sid, insert_pos + offset)
                self._local_paths[insert_pos:insert_pos] = paths
                self._queue_index = st.song
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def clear_queue(self) -> None:
        with self._lock:
            self._local_paths = []
            self._queue_index = -1
            try:
                self._ensure()
                self._client.clear()
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def play_next(self) -> bool:
        with self._lock:
            try:
                self._ensure()
                st = self._client.status()
                if st.song < st.playlistlength - 1:
                    self._client.next()
                    return True
                return False
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def play_prev(self) -> bool:
        with self._lock:
            try:
                self._ensure()
                st = self._client.status()
                if st.song > 0:
                    self._client.previous()
                    return True
                return False
            except (MpdConnectionError, MpdAckError, MpdProtocolError) as e:
                raise BackendPlaybackError(str(e)) from e

    def get_queue(self) -> list[dict]:
        try:
            self._ensure()
            st = self._client.status()
            songs = self._client.playlistinfo()
            current_song = st.song
            items = []
            for i, s in enumerate(songs):
                local_path = self._mapper.from_mpd_path(s.file) if s.file else ""
                items.append({
                    "filepath": local_path,
                    "title": s.title or "",
                    "artist": s.artist or "",
                    "duration": s.duration,
                    "is_current": (i == current_song),
                })
            return items
        except (MpdConnectionError, MpdAckError, MpdProtocolError):
            return []

    def get_queue_index(self) -> int:
        try:
            st = self._client.status()
            return st.song
        except (MpdConnectionError, MpdAckError, MpdProtocolError):
            return self._queue_index

    def get_snapshot(self) -> PlaybackSnapshot:
        try:
            self._ensure()
            st = self._client.status()
            cs = self._client.currentsong()
        except (MpdConnectionError, MpdAckError, MpdProtocolError):
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
            self._ensure()
            st = self._client.status()
            cs = self._client.currentsong()
            outputs = self._client.outputs()
        except (MpdConnectionError, MpdAckError, MpdProtocolError):
            return AudioDiagnostics(
                backend_id=self.backend_id, profile="mpd",
                bitperfect_status="not_connected")

        active_outputs = [o for o in outputs if o.enabled]
        device_name = active_outputs[0].name if active_outputs else ""
        audio_parts = st.audio.split(":") if st.audio else []
        out_rate = int(audio_parts[0]) if len(audio_parts) > 0 else 0

        profile_key = getattr(self, '_profile_key', 'mpd_hifi')

        return AudioDiagnostics(
            backend_id=self.backend_id,
            profile=profile_key,
            device_name=device_name,
            input_codec=cs.file.split(".")[-1] if "." in cs.file else "",
            output_sample_rate=out_rate,
            bitperfect_requested=True,
            bitperfect_possible=True,
            bitperfect_status="requested",
            digital_volume_active=False,
            eq_active=False,
            replaygain_active=False,
            spectrum_active=False,
            resampling_active=False,
            input_sample_rate=out_rate,
        )

    def shutdown(self) -> None:
        self._stop_poll()
        if self._client.connected:
            self._client.stop()
        self._client.disconnect()
