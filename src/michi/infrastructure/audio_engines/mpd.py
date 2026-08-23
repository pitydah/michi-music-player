"""MPD managed private AudioPort transport (M11.3D).

Michi owns ONE private MPD child process per provider instance (never a
system daemon): an in-repository minimal MPD protocol client over a
private AF_UNIX socket, a generated private mpd.conf, a bounded fail-atomic
startup, deterministic TERM→KILL shutdown and full runtime cleanup.

Architecture (lessons from M11.3C applied proactively):

    MPD daemon truth
        ↓
    observer thread (OBSERVES ONLY)
        ↓
    immutable _MpdEvent + runtime generation
        ↓
    ONE Qt.QueuedConnection
        ↓
    Qt owner thread
        ↓
    validate / re-query daemon truth
        ↓
    semantic commit
        ↓
    DIRECT AudioPort callbacks

MPD is TRANSPORT ONLY. The private MPD queue holds at most ONE Michi-owned
song (a transport slot); Michi Queue/Repeat/Shuffle authority stays in
QueueService. Song IDs are engine-local transport identity and never leave
this module. No GStreamer/Qt code is touched; no external daemon adoption;
no auto-restart (M11.3G owns fallback); no output/DAC claims (M11.4/M11.5).
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Qt, Signal

from michi.application.ports import AudioLoadError, AudioPort
from michi.domain.playback import PlaybackStatus

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# D1 — minimal MPD protocol client (in-repository, stdlib only)
# ---------------------------------------------------------------------------


class MpdProtocolError(RuntimeError):
    """Fallo del protocolo MPD: ACK del daemon, greeting inválido, EOF o
    malformación. Nunca se filtra el ACK crudo como arquitectura."""


def _quote_mpd_arg(arg: str) -> str:
    """Cita UN argumento para el protocolo de línea de MPD.

    Escapa backslash y double quote; RECHAZA \n y \r (un path local nunca
    puede inyectar un segundo comando). Esto NO es shell quoting."""
    if "\n" in arg or "\r" in arg:
        raise MpdProtocolError("MPD argument contains CR/LF injection")
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _parse_key_value_response(lines: list[str]) -> dict[str, str]:
    """Convierte líneas 'key: value' de una respuesta MPD en un dict
    (la última línea 'OK' ya fue removida por el parser)."""
    result: dict[str, str] = {}
    for line in lines:
        if ": " in line:
            key, _, value = line.partition(": ")
            result[key] = value
    return result


class _MpdProtocolClient:
    """Cliente síncrono minimalista del protocolo MPD (AF_UNIX).

    Superficie de comandos limitada a lo que M11.3D necesita — NO es un
    cliente MPD genérico y no expone execute() arbitrario."""

    def __init__(self, socket_path: str | Path, timeout: float = 5.0) -> None:
        self._socket_path = str(socket_path)
        self._timeout = timeout
        self._sock: socket.socket | None = None
        self._buffer = b""

    # -- connection ---------------------------------------------------------

    def connect(self) -> None:
        """Abre el socket AF_UNIX y valida el greeting 'OK MPD <version>'."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        try:
            sock.connect(self._socket_path)
        except OSError:
            sock.close()
            raise
        self._sock = sock
        greeting = self._read_line()
        if not greeting.startswith("OK MPD "):
            self.close()
            raise MpdProtocolError(
                f"greeting MPD inválido: {greeting!r}"
            )

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # -- low-level framing ---------------------------------------------------

    def _read_line(self) -> str:
        while b"\n" not in self._buffer:
            if self._sock is None:
                raise MpdProtocolError("MPD socket cerrado")
            try:
                chunk = self._sock.recv(4096)
            except OSError as exc:
                raise MpdProtocolError(f"MPD socket read failed: {exc}") from exc
            if not chunk:
                raise MpdProtocolError("MPD connection closed (EOF)")
            self._buffer += chunk
        line, _, self._buffer = self._buffer.partition(b"\n")
        return line.decode("utf-8", errors="replace").rstrip("\r")

    def _command(self, *args: str) -> dict[str, str]:
        """Envía un comando y devuelve la respuesta parseada (sin 'OK')."""
        if self._sock is None:
            raise MpdProtocolError("MPD not connected")
        line = " ".join(args) + "\n"
        try:
            self._sock.sendall(line.encode("utf-8"))
        except OSError as exc:
            raise MpdProtocolError(f"MPD socket write failed: {exc}") from exc
        lines: list[str] = []
        while True:
            response_line = self._read_line()
            if response_line == "OK":
                return _parse_key_value_response(lines)
            if response_line.startswith("ACK"):
                raise MpdProtocolError(f"MPD command rejected: {response_line}")
            lines.append(response_line)

    # -- typed command surface (M11.3D only) --------------------------------

    def status(self) -> dict[str, str]:
        return self._command("status")

    def clear(self) -> None:
        self._command("clear")

    def addid(self, path: str) -> int:
        """addid <path> → Id: N (song ID engine-local)."""
        response = self._command("addid", _quote_mpd_arg(path))
        try:
            return int(response["Id"])
        except (KeyError, ValueError) as exc:
            raise MpdProtocolError(f"addid response malformed: {response}") from exc

    def playid(self, song_id: int) -> None:
        self._command("playid", str(song_id))

    def pause(self, enabled: bool) -> None:
        self._command("pause", "1" if enabled else "0")

    def stop(self) -> None:
        self._command("stop")

    def seekid(self, song_id: int, seconds: float) -> None:
        self._command("seekid", str(song_id), f"{seconds:.3f}")

    def setvol(self, volume: int) -> None:
        self._command("setvol", str(max(0, min(100, volume))))

    def currentsong(self) -> dict[str, str]:
        return self._command("currentsong")

    def idle(self, *subsystems: str) -> list[str]:
        """Bloquea la conexión hasta que un subsistema cambie (observer).

        El daemon responde con las líneas de subsistema + OK cuando ocurre
        el cambio; devuelve la lista de subsistemas cambiados."""
        if self._sock is None:
            raise MpdProtocolError("MPD not connected")
        line = "idle " + " ".join(subsystems) + "\n"
        try:
            self._sock.sendall(line.encode("utf-8"))
        except OSError as exc:
            raise MpdProtocolError(f"MPD socket write failed: {exc}") from exc
        lines: list[str] = []
        while True:
            response_line = self._read_line()
            if response_line == "OK":
                return lines
            if response_line.startswith("ACK"):
                raise MpdProtocolError(f"MPD idle rejected: {response_line}")
            lines.append(response_line)


# ---------------------------------------------------------------------------
# deterministic conversions (MPD seconds ↔ AudioPort milliseconds)
# ---------------------------------------------------------------------------


def _mpd_seconds_to_millis(seconds: str | float) -> int:
    """MPD reporta segundos (posiblemente fraccionarios) → ms int."""
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 0
    if value < 0:
        return 0
    return int(round(value * 1000))
