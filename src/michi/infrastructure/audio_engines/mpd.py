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

import contextlib
import logging
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from michi.application.ports import AudioLoadError, AudioPort
from michi.domain.playback import PlaybackStatus

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# D1 — minimal MPD protocol client (in-repository, stdlib only)
# ---------------------------------------------------------------------------


class MpdProtocolError(RuntimeError):
    """Fallo del protocolo MPD: ACK del daemon, greeting inválido, EOF o
    malformación. Nunca se filtra el ACK crudo como arquitectura.

    is_ack=True marca una REJECTION DETERMINISTA del daemon (ACK): el
    adapter la trata como media_rejected controlada; los demás fallos
    (socket/EOF) son errores de transporte con disposición destructiva."""

    def __init__(self, message: str, *, is_ack: bool = False) -> None:
        super().__init__(message)
        self.is_ack = is_ack


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
            raise MpdProtocolError(f"greeting MPD inválido: {greeting!r}")

    def close(self) -> None:
        """Cierre determinista: shutdown(SHUT_RDWR) ANTES de close().

        GATE A1 (M11.3D-R3): close() solo NO despierta un recv() bloqueado
        en otro thread (observado con socket AF_UNIX real) — shutdown()
        libera el recv pendiente de forma determinista (EOF/error)."""
        sock = self._sock
        self._sock = None  # nadie más lo considera conectado
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                sock.close()

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
                raise MpdProtocolError(
                    f"MPD command rejected: {response_line}", is_ack=True
                )
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


# ---------------------------------------------------------------------------
# D2 — managed private MPD process/runtime (Michi-owned, never adopted)
# ---------------------------------------------------------------------------


def _pick_runtime_parent() -> Path:
    """XDG_RUNTIME_DIR válido y escribible, o un tempdir seguro (0700)."""
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        candidate = Path(xdg)
        if candidate.is_dir() and os.access(candidate, os.W_OK):
            return candidate
    return Path(tempfile.gettempdir())


def _render_mpd_conf(
    runtime_dir: Path, music_dir: Path, *, null_output: bool = False
) -> str:
    """Config mínima privada — SOLO paths de este runtime; nada del sistema.

    PRODUCCIÓN (null_output=False): NO se emite un bloque audio_output —
    MPD usa su selección de salida por defecto hasta que M11.4 posea la
    configuración DAC/output explícita. La salida null SOLO se usa en
    tests/smoke deterministas (null_output=True)."""
    lines = [
        'bind_to_address "' + str(runtime_dir / "mpd.sock") + '"',
        'pid_file "' + str(runtime_dir / "mpd.pid") + '"',
        'log_file "' + str(runtime_dir / "mpd.log") + '"',
        'db_file "' + str(runtime_dir / "database") + '"',
        'state_file "' + str(runtime_dir / "state") + '"',
        'sticker_file "' + str(runtime_dir / "stickers.sqlite") + '"',
        'playlist_directory "' + str(runtime_dir / "playlists") + '"',
        'music_directory "' + str(music_dir) + '"',
        'auto_update "no"',
    ]
    if null_output:
        lines.append('audio_output {\n\ttype\t\t"null"\n\tname\t\t"Michi MPD Test"\n}')
    lines.append("")
    return "\n".join(lines)


class _ManagedMpdRuntime:
    """Posee UN proceso MPD privado con su árbol de runtime único.

    Startup bounded y failure-atomic (primer error primario; limpieza
    best-effort); shutdown TERM → KILL → reap → remoción de artefactos;
    close() idempotente. NUNCA adopta un daemon externo."""

    def __init__(
        self,
        executable: str = "mpd",
        startup_timeout: float = 5.0,
        null_output: bool = False,
    ):
        self._executable = executable
        self._startup_timeout = startup_timeout
        self._null_output = null_output  # SOLO para tests/smoke reales
        self.runtime_dir: Path | None = None
        self.socket_path: str | None = None
        self._process: subprocess.Popen | None = None
        self._closed = True

    # -- startup -------------------------------------------------------------

    def start(self) -> None:
        """Crea el runtime, genera la config, spawna MPD y valida el
        handshake. Failure-atomic: cualquier fallo limpia TODO y re-lanza
        el error ORIGINAL."""
        try:
            self._start_inner()
        except Exception:
            self.close()
            raise

    def _start_inner(self) -> None:
        parent = _pick_runtime_parent()
        base = parent / f"michi-mpd-{os.getpid()}-{time.time_ns():x}"
        base.mkdir(mode=0o700)
        music_dir = base / "music"
        music_dir.mkdir(mode=0o700)
        (base / "playlists").mkdir(mode=0o700)
        self.runtime_dir = base
        self.socket_path = str(base / "mpd.sock")
        conf_path = base / "mpd.conf"
        conf_path.write_text(
            _render_mpd_conf(base, music_dir, null_output=self._null_output),
            encoding="utf-8",
        )
        # spawn --no-daemon (nunca shell=True, nunca daemonizar)
        self._process = subprocess.Popen(
            [self._executable, "--no-daemon", "--stderr", str(conf_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        # bounded wait por el socket + liveness del hijo
        deadline = time.monotonic() + self._startup_timeout
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise MpdProtocolError(
                    "MPD child exited during startup: "
                    f"rc={self._process.returncode} "
                    f"stderr={self._read_stderr()}"
                )
            if os.path.exists(self.socket_path):
                break
            time.sleep(0.05)
        if not os.path.exists(self.socket_path):
            raise MpdProtocolError("MPD socket no apareció dentro del timeout")
        # handshake real
        probe = _MpdProtocolClient(self.socket_path, timeout=2.0)
        probe.connect()
        probe.status()
        probe.close()
        self._closed = False

    def _read_stderr(self) -> str:
        if self._process is None or self._process.stderr is None:
            return ""
        try:
            return self._process.stderr.read()[:2000]
        except (OSError, ValueError):
            return ""

    # -- liveness / ownership ------------------------------------------------

    @property
    def process(self) -> subprocess.Popen | None:
        return self._process

    @property
    def closed(self) -> bool:
        return self._closed

    def child_alive(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    # -- shutdown ------------------------------------------------------------

    def close(self) -> None:
        """TERM → bounded wait → KILL → reap → remover artefactos.
        Idempotente; NUNCA deja un proceso huérfano."""
        if self._closed and self._process is None:
            return
        self._closed = True
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            with contextlib.suppress(OSError, ProcessLookupError):
                process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(OSError, ProcessLookupError):
                    process.kill()
                try:
                    process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    _logger.warning("mpd: child no reaped; releasing handle")
        runtime_dir = self.runtime_dir
        self.runtime_dir = None
        self.socket_path = None
        if runtime_dir is not None:
            shutil.rmtree(runtime_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# D3/D4 — MPDAudioPort: transport semantics + owner-thread event convergence
# ---------------------------------------------------------------------------


class _MpdEventKind(Enum):
    REFRESH_PLAYER = auto()
    PROCESS_EXIT = auto()
    TRANSPORT_ERROR = auto()


@dataclass(frozen=True, slots=True)
class _MpdEvent:
    """Observación inmutable del observer thread (M11.3C lesson)."""

    runtime_generation: int
    kind: _MpdEventKind
    reason: str | None = None


class _MpdEventBridge(QObject):
    """ÚNICA frontera asíncrona: observer thread → owner thread."""

    sig_event = Signal(object)


class MPDAudioPort(AudioPort):
    """Transport MPD gestionado detrás del contrato canónico AudioPort.

    El observer thread SOLO observa (idle/EOF) y encola _MpdEvent; el
    owner thread re-valida y re-consulta la verdad del daemon antes del
    commit semántico y publica callbacks DIRECTOS. La cola privada de MPD
    es UN slot de transporte (cero o una canción de Michi); el song ID es
    identidad engine-local. Nunca adopta daemons externos, nunca
    auto-reinicia (M11.3G), nunca emite EOM por stop/reemplazo/crash."""

    def __init__(
        self,
        runtime: _ManagedMpdRuntime | None = None,
        poll_interval_ms: int = 500,
        runtime_failure_callback: Callable[[int, str], None] | None = None,
    ) -> None:
        super().__init__()
        self._bridge = _MpdEventBridge()
        self._poll_interval_ms = poll_interval_ms
        self._runtime = runtime if runtime is not None else _ManagedMpdRuntime()
        self._client: _MpdProtocolClient | None = None
        self._runtime_generation = 0
        self._closed = True  # se abre con open()
        # M11.3G seam (minimal, OPTIONAL): publica PROVEN fatal runtime loss
        # (PROCESS_EXIT / fatal TRANSPORT_ERROR) hacia el provider lifecycle
        # seam — recibe (runtime_generation, reason). NUNCA media errors.
        self._runtime_failure_callback = runtime_failure_callback
        # identity engine-local
        self._pending_path: Path | None = None
        self._current_path: Path | None = None
        self._song_id: int | None = None
        # semántica
        self._pending_play = False
        self._current_state = PlaybackStatus.STOPPED
        self._eos_emitted = False
        self._volume = 80
        self._muted = False
        # command ownership (M11.3C lesson): tokens privados
        self._load_epoch = 0
        # observer
        self._observer: threading.Thread | None = None
        self._observer_stop = threading.Event()
        self._idle_client: _MpdProtocolClient | None = None
        # poller owner-thread (posición) — QTimer en el thread owner
        self._poller: QTimer | None = None
        # subscribers
        self._eom: list = []
        self._pos: list = []
        self._dur: list = []
        self._acc: list = []
        self._rej: list = []
        self._pst: list = []
        self._bridge.sig_event.connect(self._on_backend_event, Qt.QueuedConnection)

    def set_runtime_failure_callback(
        self, callback: Callable[[int, str], None] | None
    ) -> None:
        """M11.3G: re-asocia el callback del seam tras open().

        El provider captura su PROPIA generación en el momento del open y la
        cierra en el callback (dominio del provider); la generación interna
        del port (primer argumento) es un dominio SEPARADO que el provider
        no compara directamente."""
        self._runtime_failure_callback = callback

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Abre el runtime gestionado — TRANSACCIONAL (M11.3D-R1 C2):
        cualquier fallo tras runtime.start() limpia TODO lo creado (cliente,
        observer, poller), cierra el runtime y re-lanza el error ORIGINAL.
        Nunca queda un hijo huérfano ni un port a medio abrir."""
        if not self._closed:
            return
        try:
            self._runtime.start()
            self._runtime_generation += 1
            generation = self._runtime_generation
            self._client = _MpdProtocolClient(self._runtime.socket_path, timeout=5.0)
            self._client.connect()
            # observer thread con conexión idle propia (nunca bloquea comandos)
            self._observer_stop.clear()
            self._observer = threading.Thread(
                target=self._observer_main,
                args=(generation,),
                name="michi-mpd-observer",
                daemon=True,
            )
            self._observer.start()
            # poller de posición (owner-thread, solo mientras runtime abierto)
            self._poller = QTimer()
            self._poller.setInterval(self._poll_interval_ms)
            self._poller.timeout.connect(self._poll_position)
            self._poller.start()
            self._closed = False
        except Exception:
            # FIRST ERROR WINS: limpieza best-effort de cada recurso creado
            if self._poller is not None:
                self._poller.stop()
                self._poller = None
            observer = self._observer
            self._observer = None
            if observer is not None:
                self._observer_stop.set()
                # GATE 3 (M11.3D-R2): liberar el recv bloqueante del idle
                # ANTES del join — si el observer está bloqueado en idle(),
                # el join expiraría y el thread quedaría vivo
                idle_client = self._idle_client
                if idle_client is not None:
                    with contextlib.suppress(Exception):
                        idle_client.close()
                self._idle_client = None
                observer.join(timeout=2.0)
            if self._client is not None:
                self._client.close()
                self._client = None
            self._runtime_generation += 1
            self._runtime.close()
            self._closed = True
            raise

    def close(self) -> None:
        """Idempotente: detiene observer y poller, cierra sockets, termina
        el hijo, remueve artefactos."""
        if self._closed:
            return
        self._closed = True
        self._runtime_generation += 1  # invalida eventos en vuelo
        self._observer_stop.set()
        # libera el recv bloqueante del observer idle (C4-D)
        idle_client = self._idle_client
        if idle_client is not None:
            with contextlib.suppress(Exception):
                idle_client.close()
        observer = self._observer
        self._observer = None
        if observer is not None:
            observer.join(timeout=2.0)
        if self._poller is not None:
            self._poller.stop()
            self._poller = None
        if self._client is not None:
            self._client.close()
            self._client = None
        self._pending_path = None
        self._current_path = None
        self._song_id = None
        self._pending_play = False
        self._eos_emitted = False
        self._eom = []
        self._pos = []
        self._dur = []
        self._acc = []
        self._rej = []
        self._pst = []
        self._runtime.close()

    # ------------------------------------------------------------------
    # observer (OBSERVES ONLY — nunca muta semántica)
    # ------------------------------------------------------------------

    def _observer_main(self, generation: int) -> None:
        """OBSERVA SOLO. Un fallo del transporte idle produce EXACTAMENTE
        UN evento terminal (TRANSPORT_ERROR con hijo vivo, PROCESS_EXIT con
        hijo muerto) y el observer sale — sin loops error/refresh (C4)."""
        idle_client = None
        try:
            idle_client = _MpdProtocolClient(
                self._runtime.socket_path,
                timeout=None,  # idle bloqueante
            )
            idle_client.connect()
            self._idle_client = idle_client  # close() del port lo libera
            while not self._observer_stop.is_set():
                changed = idle_client.idle("player")
                if changed:
                    self._bridge.sig_event.emit(
                        _MpdEvent(generation, _MpdEventKind.REFRESH_PLAYER)
                    )
        except MpdProtocolError as exc:
            if self._observer_stop.is_set():
                pass  # cierre normal: close() cerró el socket idle
            elif self._runtime.child_alive():
                # transporte del observer roto con hijo vivo: UN evento
                self._bridge.sig_event.emit(
                    _MpdEvent(generation, _MpdEventKind.TRANSPORT_ERROR, str(exc))
                )
            else:
                self._bridge.sig_event.emit(
                    _MpdEvent(generation, _MpdEventKind.PROCESS_EXIT, str(exc))
                )
        finally:
            self._idle_client = None
            with contextlib.suppress(Exception):  # noqa: BLE001
                if idle_client is not None:
                    idle_client.close()

    # ------------------------------------------------------------------
    # owner commit (única autoridad semántica)
    # ------------------------------------------------------------------

    def _on_backend_event(self, event) -> None:
        if self._closed:
            return
        if event.runtime_generation != self._runtime_generation:
            return  # evento stale de un runtime anterior
        if event.kind == _MpdEventKind.PROCESS_EXIT:
            self._converge_process_exit(event.reason)
            return
        if event.kind == _MpdEventKind.TRANSPORT_ERROR:
            self._converge_transport_error(event.reason)
            return
        if event.kind == _MpdEventKind.REFRESH_PLAYER:
            self._refresh_status()

    def _refresh_status(self) -> None:
        """Re-consulta la verdad del daemon y commitea el estado (solo si
        el daemon confirma; nunca PLAYING optimista)."""
        if self._closed or self._client is None:
            return
        try:
            status = self._client.status()
        except MpdProtocolError as exc:
            # GATE 1 (M11.3D-R2): proceso vivo ≠ transporte sano. Con el
            # socket de comandos roto no se puede consultar la verdad del
            # daemon → convergencia honesta (nunca return silencioso).
            if self._runtime.child_alive():
                self._converge_transport_error(str(exc))
            else:
                self._converge_process_exit(str(exc))
            return
        error = status.get("error")
        if error:
            # C6 (M11.3D-R1): un error del daemon para el media actual NO es
            # verdad de reproducción normal → convergencia terminal honesta
            self._converge_media_error(error)
            return
        state = status.get("state", "stop")
        if state == "play":
            self._deliver_state_if(PlaybackStatus.PLAYING)
        elif state == "pause":
            self._deliver_state_if(PlaybackStatus.PAUSED)
        elif state == "stop":
            self._commit_stopped(status)

    def _commit_stopped(self, status: dict[str, str]) -> None:
        """STOPPED convergente. EOS natural SOLO si veníamos de PLAYING
        con intención y el daemon ya no reporta la canción actual."""
        if self._current_state == PlaybackStatus.STOPPED:
            return
        was_playing = self._current_state == PlaybackStatus.PLAYING
        current = self._current_path
        self._pending_play = False
        self._deliver_state_if(PlaybackStatus.STOPPED)
        # REVALIDACIÓN post-callback (M11.3C lesson): el subscriber del
        # STOPPED pudo cargar C/cerrar → EOM de la fuente vieja suprimido.
        # El fin natural requiere: veníamos de PLAYING, la fuente sigue
        # siendo la misma, el daemon ya no reporta la canción (el stop
        # explícito de MPD retiene songid).
        if (
            was_playing
            and current is not None
            and self._current_path == current
            and not self._eos_emitted
            and status.get("songid") is None
        ):
            self._emit_natural_eos()
        self._eos_emitted = False

    def _emit_natural_eos(self) -> None:
        """STOPPED ya publicado; revalida y emite EOM como ÚLTIMA acción
        (un subscriber del STOPPED pudo cargar C/cerrar → EOM suprimido)."""
        if self._closed:
            return
        self._eos_emitted = True
        self._deliver_eom()

    def _converge_media_loss(self, reason: str | None) -> None:
        """C5/C6: pérdida de autoridad del source aceptado — captura el
        path perdido, limpia autoridad backend, STOPPED, y media_rejected
        (PlaybackService terminaliza accepted/intent). NUNCA EOM."""
        lost = self._current_path or self._pending_path
        self._pending_path = None
        self._current_path = None
        self._song_id = None
        self._pending_play = False
        self._eos_emitted = True  # la pérdida nunca es fin natural
        self._deliver_state_if(PlaybackStatus.STOPPED)
        if lost is not None:
            self._deliver_rej(lost, reason or "MPD transport lost")

    def _converge_process_exit(self, reason: str | None) -> None:
        """El hijo murió: sin PLAYING futuro, sin EOM, convergencia
        honesta, sin auto-restart (M11.3G)."""
        # M11.3G seam: PROCESS_EXIT es PROVEN fatal runtime loss.
        if self._runtime_failure_callback is not None:
            self._runtime_failure_callback(
                self._runtime_generation, reason or "MPD process exited"
            )
        if self._current_path is not None or self._pending_path is not None:
            self._converge_media_loss(reason or "MPD process exited")

    def _converge_transport_error(self, reason: str | None) -> None:
        # M11.3G seam: fatal TRANSPORT_ERROR (runtime no confiable) — solo
        # el transport terminal; el status.error del media NO pasa por aquí.
        if self._runtime_failure_callback is not None:
            self._runtime_failure_callback(
                self._runtime_generation, reason or "MPD transport error"
            )
        if self._current_path is not None:
            self._converge_media_loss(reason or "MPD transport error")

    def _converge_media_error(self, reason: str | None) -> None:
        """C6: status.error del daemon para el media actual."""
        if self._current_path is not None:
            self._converge_media_loss(reason or "MPD playback error")

    # ------------------------------------------------------------------
    # position / duration (owner thread, solo source aceptado)
    # ------------------------------------------------------------------

    def _poll_position(self) -> None:
        if self._closed or self._client is None:
            return
        if self._current_path is None:
            return
        try:
            status = self._client.status()
        except MpdProtocolError as exc:
            # GATE 1: pérdida del transporte de comandos con source
            # autoritativo → convergencia honesta (una vez; el cleanup de
            # current_path hace no-op los ticks siguientes)
            if self._current_path is not None:
                self._converge_transport_error(str(exc))
            return
        elapsed = status.get("elapsed")
        if elapsed is not None:
            self._deliver_pos(_mpd_seconds_to_millis(elapsed))

    # ------------------------------------------------------------------
    # transport commands (owner thread)
    # ------------------------------------------------------------------

    def load(self, file_path: Path) -> None:
        if self._closed or self._client is None:
            raise RuntimeError("MPD port cerrado")
        self._load_epoch += 1
        my_load_epoch = self._load_epoch
        # COMMIT POINT DESTRUCTIVO: clear() — tras confirmarse, la fuente
        # previa ya no está garantizada (AudioLoadError=False)
        try:
            self._client.clear()
        except MpdProtocolError as exc:
            if exc.is_ack:
                # ACK DETERMINISTA: clear rechazado → la fuente previa sigue
                # (current_path/song_id intactos)
                raise AudioLoadError(
                    file_path, str(exc), previous_source_preserved=True
                ) from exc
            # GATE 2 (M11.3D-R2): resultado de IPC DESCONOCIDO — MPD pudo
            # ejecutar clear → FAIL CLOSED: la fuente previa NO está
            # garantizada Y la autoridad backend vieja se abandona (nunca
            # un ghost song_id tras un clear incierto)
            self._pending_path = None
            self._current_path = None
            self._song_id = None
            self._pending_play = False
            raise AudioLoadError(
                file_path, str(exc), previous_source_preserved=False
            ) from exc
        try:
            song_id = self._client.addid(str(file_path.resolve()))
        except MpdProtocolError as exc:
            # post-commit: la fuente previa se perdió
            self._pending_path = None
            self._current_path = None
            self._song_id = None
            if exc.is_ack:
                # REJECTION CONTROLADA del daemon (ACK determinista):
                # media_rejected SIN excepción — el PlaybackService la
                # trata como disposición terminal sincrónica
                self._deliver_rej(file_path, str(exc))
                return
            # fallo no determinista (socket/EOF): disposición destructiva
            self._deliver_rej(file_path, str(exc))
            raise AudioLoadError(
                file_path, str(exc), previous_source_preserved=False
            ) from exc
        # aceptación SÍNCRONA (MPD la confirma al instante)
        if my_load_epoch != self._load_epoch:
            return  # un callback reentrante supersedió este load
        self._pending_path = None
        self._current_path = file_path
        self._song_id = song_id
        self._eos_emitted = False
        self._deliver_acc(file_path)

    def play(self) -> None:
        if self._closed or self._client is None:
            return
        if self._song_id is None:
            return
        try:
            self._client.playid(self._song_id)
        except MpdProtocolError as exc:
            # sin ghost accepted: converger honesto
            self._converge_transport_error(str(exc))
            raise RuntimeError(f"MPD play failed: {exc}") from exc
        self._pending_play = True
        # PLAYING NUNCA es optimista: espera la verdad del daemon

    def pause(self) -> None:
        if self._closed or self._client is None:
            return
        try:
            self._client.pause(True)
        except MpdProtocolError as exc:
            raise RuntimeError(f"MPD pause failed: {exc}") from exc
        self._pending_play = False

    def resume(self) -> None:
        if self._closed or self._client is None:
            return
        try:
            self._client.pause(False)
        except MpdProtocolError as exc:
            raise RuntimeError(f"MPD resume failed: {exc}") from exc
        self._pending_play = True

    def stop(self) -> None:
        if self._closed or self._client is None:
            return
        self._pending_play = False
        try:
            self._client.stop()
        except MpdProtocolError as exc:
            raise RuntimeError(f"MPD stop failed: {exc}") from exc
        # STOPPED solo cuando el daemon confirma state=stop (refresh)
        self._refresh_status()

    def seek(self, position_ms: int) -> None:
        if self._closed or self._client is None:
            return
        if self._song_id is None:
            return
        try:
            self._client.seekid(self._song_id, position_ms / 1000.0)
        except MpdProtocolError as exc:
            raise RuntimeError(f"MPD seek failed: {exc}") from exc

    def position(self) -> int:
        if self._closed or self._client is None or self._current_path is None:
            return 0
        try:
            status = self._client.status()
        except MpdProtocolError:
            return 0
        return _mpd_seconds_to_millis(status.get("elapsed", "0"))

    def duration(self) -> int:
        if self._closed or self._client is None or self._current_path is None:
            return 0
        try:
            song = self._client.currentsong()
        except MpdProtocolError:
            return 0
        return _mpd_seconds_to_millis(song.get("duration", song.get("Time", "0")))

    def set_volume(self, value: int) -> None:
        if self._closed or self._client is None:
            return
        self._volume = max(0, min(100, value))
        if not self._muted:
            try:
                self._client.setvol(self._volume)
            except MpdProtocolError as exc:
                raise RuntimeError(f"MPD setvol failed: {exc}") from exc

    def set_muted(self, muted: bool) -> None:
        if self._closed or self._client is None:
            return
        self._muted = muted
        effective = 0 if muted else self._volume
        try:
            self._client.setvol(effective)
        except MpdProtocolError as exc:
            raise RuntimeError(f"MPD setvol failed: {exc}") from exc

    # ------------------------------------------------------------------
    # publication (owner thread, DIRECT)
    # ------------------------------------------------------------------

    def _deliver_state_if(self, status: PlaybackStatus) -> None:
        if self._current_state is status:
            return
        self._current_state = status
        self._deliver_state(status)

    def _deliver_eom(self) -> None:
        for cb in list(self._eom):
            cb()

    def _deliver_pos(self, ms: int) -> None:
        for cb in list(self._pos):
            cb(ms)

    def _deliver_dur(self, ms: int) -> None:
        for cb in list(self._dur):
            cb(ms)

    def _deliver_acc(self, path) -> None:
        for cb in list(self._acc):
            cb(path)

    def _deliver_rej(self, path, reason: str) -> None:
        for cb in list(self._rej):
            cb(path, reason)

    def _deliver_state(self, status) -> None:
        for cb in list(self._pst):
            cb(status)

    # ------------------------------------------------------------------
    # subscriptions (idempotentes)
    # ------------------------------------------------------------------

    def subscribe_end_of_media(self, cb) -> None:
        if cb not in self._eom:
            self._eom.append(cb)

    def unsubscribe_end_of_media(self, cb) -> None:
        if cb in self._eom:
            self._eom.remove(cb)

    def subscribe_position_changed(self, cb) -> None:
        if cb not in self._pos:
            self._pos.append(cb)

    def unsubscribe_position_changed(self, cb) -> None:
        if cb in self._pos:
            self._pos.remove(cb)

    def subscribe_duration_changed(self, cb) -> None:
        if cb not in self._dur:
            self._dur.append(cb)

    def unsubscribe_duration_changed(self, cb) -> None:
        if cb in self._dur:
            self._dur.remove(cb)

    def subscribe_media_accepted(self, cb) -> None:
        if cb not in self._acc:
            self._acc.append(cb)

    def unsubscribe_media_accepted(self, cb) -> None:
        if cb in self._acc:
            self._acc.remove(cb)

    def subscribe_media_rejected(self, cb) -> None:
        if cb not in self._rej:
            self._rej.append(cb)

    def unsubscribe_media_rejected(self, cb) -> None:
        if cb in self._rej:
            self._rej.remove(cb)

    def subscribe_playback_state_changed(self, cb) -> None:
        if cb not in self._pst:
            self._pst.append(cb)

    def unsubscribe_playback_state_changed(self, cb) -> None:
        if cb in self._pst:
            self._pst.remove(cb)
