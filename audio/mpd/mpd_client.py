"""MPD client — TCP socket connection with command/response protocol.

Minimal implementation. No external dependencies beyond standard library.
Uses socket with timeout for non-blocking main thread safety.
"""

import contextlib
import logging
import socket
import threading
import time

from audio.mpd.mpd_models import MpdStatus, MpdSong, MpdOutput
from audio.mpd.mpd_protocol import MpdResponse, parse_response
from audio.mpd.mpd_errors import (
    MpdAckError,
    MpdError,
    MpdConnectionError,
    MpdProtocolError,
)

logger = logging.getLogger("michi.mpd.client")

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 6600
_DEFAULT_TIMEOUT = 2.0
_RECONNECT_DELAY = 2.0
_MAX_LINE = 65536


class MpdClient:
    """Low-level MPD TCP client. Thread-safe for send/receive."""

    def __init__(self, host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT,
                 password: str = "", timeout: float = _DEFAULT_TIMEOUT):
        self._host = host
        self._port = port
        self._password = password
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._version = ""

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    def connect(self):
        """Connect to MPD server and authenticate if password is set."""
        with self._lock:
            if self._connected:
                return
            try:
                self._sock = socket.create_connection(
                    (self._host, self._port), timeout=self._timeout)
                self._sock.settimeout(self._timeout)
                self._version = self._read_greeting()
                if self._password:
                    self._send_command(f"password {self._password}")
                    self._read_ok()
                self._connected = True
                logger.info("Connected to MPD at %s:%s (version %s)",
                            self._host, self._port, self._version)
            except (socket.timeout, ConnectionRefusedError, OSError,
                    MpdProtocolError, MpdAckError) as e:
                self._connected = False
                if self._sock:
                    with contextlib.suppress(OSError):
                        self._sock.close()
                self._sock = None
                raise MpdConnectionError(
                    f"Cannot connect to MPD at {self._host}:{self._port}: {e}"
                ) from e

    def _read_greeting(self) -> str:
        """Read the initial MPD greeting: 'OK MPD <version>'."""
        line = self._read_line()
        if not line:
            raise MpdProtocolError("Empty MPD greeting")
        stripped = line.strip()
        if not stripped.startswith("OK MPD "):
            raise MpdProtocolError(f"Invalid MPD greeting: {stripped}")
        return stripped.removeprefix("OK MPD ").strip()

    def disconnect(self):
        """Close the connection."""
        with self._lock:
            self._connected = False
            if self._sock:
                with contextlib.suppress(OSError):
                    self._sock.close()
                self._sock = None

    def reconnect(self):
        """Disconnect and reconnect."""
        self.disconnect()
        time.sleep(_RECONNECT_DELAY)
        self.connect()

    def ensure_connected(self):
        """Connect if not already connected. Raises MpdConnectionError on failure."""
        if not self._connected:
            self.connect()

    def ping(self) -> bool:
        """Test if MPD is responding. Returns True if OK."""
        try:
            self.ensure_connected()
            self._send_command("ping")
            self._read_ok()
            return True
        except (MpdError, OSError):
            return False

    def status(self) -> MpdStatus:
        raw = self._command("status")
        s = MpdStatus()
        s.state = raw.pairs.get("state", "stop")
        s.volume = _int_or(raw.pairs.get("volume"), -1)
        s.repeat = raw.pairs.get("repeat", "0") == "1"
        s.random = raw.pairs.get("random", "0") == "1"
        s.single = raw.pairs.get("single", "0") == "1"
        s.consume = raw.pairs.get("consume", "0") == "1"
        s.playlist = _int_or(raw.pairs.get("playlist"), 0)
        s.playlistlength = _int_or(raw.pairs.get("playlistlength"), 0)
        s.song = _int_or(raw.pairs.get("song"), -1)
        s.songid = _int_or(raw.pairs.get("songid"), -1)
        s.elapsed = _float_or(raw.pairs.get("elapsed"), 0.0)
        s.duration = _float_or(raw.pairs.get("duration"), 0.0)
        s.bitrate = _int_or(raw.pairs.get("bitrate"), 0)
        s.audio = raw.pairs.get("audio", "")
        s.error = raw.pairs.get("error", "")
        return s

    def currentsong(self) -> MpdSong:
        """Get the current song info."""
        raw = self._command("currentsong")
        return self._parse_song(raw)

    def playlistinfo(self) -> list[MpdSong]:
        """Get all songs in the current playlist."""
        raw = self._command("playlistinfo")
        songs = []
        for entry in raw.lists.get("file", []):
            songs.append(self._parse_song_entry(entry))
        return songs

    def outputs(self) -> list[MpdOutput]:
        """List available audio outputs."""
        raw = self._command("outputs")
        outputs = []
        for entry in raw.lists.get("outputid", []):
            out = MpdOutput(
                id=_int_or(entry.get("outputid"), 0),
                name=entry.get("outputname", ""),
                enabled=entry.get("outputenabled", "0") == "1",
            )
            outputs.append(out)
        return outputs

    def play(self):
        self._command_ok("play")

    def pause(self, val: int = 1):
        self._command_ok(f"pause {val}")

    def stop(self):
        self._command_ok("stop")

    def next(self):
        self._command_ok("next")

    def previous(self):
        self._command_ok("previous")

    def seekcur(self, seconds: float):
        self._command_ok(f"seekcur {seconds:.1f}")

    def setvol(self, volume: int):
        self._command_ok(f"setvol {max(0, min(100, volume))}")

    def clear(self):
        self._command_ok("clear")

    def add(self, path: str):
        self._command_ok(f'add "{_escape(path)}"')

    def delete(self, pos: int):
        self._command_ok(f"delete {pos}")

    def playid(self, song_id: int):
        self._command_ok(f"playid {song_id}")

    def playpos(self, pos: int):
        self._command_ok(f"play {pos}")

    def addid(self, path: str) -> int:
        raw = self._command(f'addid "{_escape(path)}"')
        return _int_or(raw.pairs.get("Id"), -1)

    def moveid(self, song_id: int, to_pos: int):
        self._command_ok(f"moveid {song_id} {to_pos}")

    def move(self, from_pos: int, to_pos: int):
        self._command_ok(f"move {from_pos} {to_pos}")

    def repeat(self, val: int):
        self._command_ok(f"repeat {val}")

    def random(self, val: int):
        self._command_ok(f"random {val}")

    # ── Internal ──

    def _command(self, cmd: str) -> MpdResponse:
        """Send command and return parsed response (expects OK)."""
        self._send_command(cmd)
        return self._read_response()

    def _command_ok(self, cmd: str):
        """Send command and check OK response."""
        self._send_command(cmd)
        self._read_ok()

    def _send_command(self, cmd: str):
        with self._lock:
            if not self._sock:
                raise MpdConnectionError("Not connected")
            try:
                self._sock.sendall((cmd + "\n").encode("utf-8"))
            except OSError as e:
                self._connected = False
                raise MpdConnectionError(f"Send failed: {e}") from e

    def _read_response(self) -> MpdResponse:
        """Read full response until OK or ACK."""
        lines = []
        while True:
            try:
                line = self._read_line()
            except OSError as e:
                self._connected = False
                raise MpdConnectionError(f"Read failed: {e}") from e

            if line is None:
                break
            stripped = line.strip()
            lines.append(line)
            if stripped in ("OK",) or stripped.startswith("ACK"):
                break
        raw = "".join(lines)
        return parse_response(raw)

    def _read_ok(self):
        resp = self._read_response()
        resp.require_ok()

    def _read_line(self) -> str | None:
        if not self._sock:
            return None
        buf = bytearray()
        while len(buf) < _MAX_LINE:
            ch = self._sock.recv(1)
            if not ch:
                break
            if ch == b"\n":
                return buf.decode("utf-8")
            buf.extend(ch)
        return buf.decode("utf-8") if buf else None

    @staticmethod
    def _parse_song(raw) -> MpdSong:
        entry = {}
        for lst in raw.lists.values():
            if lst:
                entry = lst[0]
                break
        if not entry:
            entry = raw.pairs
        return MpdClient._parse_song_entry(entry)

    @staticmethod
    def _parse_song_entry(entry: dict[str, str]) -> MpdSong:
        return MpdSong(
            file=entry.get("file", ""),
            title=entry.get("Title", ""),
            artist=entry.get("Artist", ""),
            album=entry.get("Album", ""),
            albumartist=entry.get("AlbumArtist", ""),
            track=entry.get("Track", ""),
            genre=entry.get("Genre", ""),
            date=entry.get("Date", ""),
            duration=_float_or(entry.get("duration"), 0.0),
            pos=_int_or(entry.get("Pos"), -1),
            id=_int_or(entry.get("Id"), -1),
        )


def _int_or(val: str, default: int) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _float_or(val: str, default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _escape(path: str) -> str:
    """Escape quotes and backslashes for MPD command string."""
    return path.replace("\\", "\\\\").replace('"', '\\"')
