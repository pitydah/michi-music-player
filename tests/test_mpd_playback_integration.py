"""M11.3D — PlaybackService + MPDAudioPort integration (deterministic)."""

import os
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

from michi.application.playback_service import PlaybackService
from michi.application.ports import AudioLoadError
from michi.domain.playback import PlaybackStatus
from michi.infrastructure.audio_engines.mpd import (
    MPDAudioPort,
    MpdProtocolError,
    _MpdEvent,
    _MpdEventKind,
)


@pytest.fixture(scope="module")
def qapp():
    """Instancia Qt offscreen (patrón del repo — sin depender de
    pytest-qt, que no está en la CI): processEvents() entrega los eventos
    QueuedConnection del bridge observer → owner."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    yield app


class _FakeClient:
    idle_event = threading.Event()

    def __init__(self, socket_path=None, timeout=5.0):
        self.commands: list[str] = []
        self.state = "stop"
        self.songid: str | None = None
        self.elapsed = "0.000"
        self.duration = "0.000"
        self.volume = "80"
        self.error: str | None = None
        self.addid_ack: str | None = None
        self.addid_fatal: str | None = None
        self.clear_ack: str | None = None
        self.clear_fatal: str | None = None
        self.status_error: str | None = None
        self.playid_ack: str | None = None
        self.next_id = 1

    def connect(self):
        pass

    def close(self):
        pass

    def status(self):
        self.commands.append("status")
        if self.status_error:
            raise MpdProtocolError(self.status_error)
        status = {"state": self.state, "volume": self.volume}
        if self.songid is not None:
            status["songid"] = self.songid
            status["elapsed"] = self.elapsed
            status["duration"] = self.duration
        if self.error:
            status["error"] = self.error
        return status

    def clear(self):
        self.commands.append("clear")
        if self.clear_ack:
            raise MpdProtocolError(self.clear_ack, is_ack=True)
        if self.clear_fatal:
            raise MpdProtocolError(self.clear_fatal, is_ack=False)
        self.songid = None
        self.state = "stop"

    def addid(self, path):
        self.commands.append(f"addid {path}")
        if self.addid_ack:
            raise MpdProtocolError(self.addid_ack, is_ack=True)
        if self.addid_fatal:
            raise MpdProtocolError(self.addid_fatal, is_ack=False)
        self.songid = str(self.next_id)
        self.next_id += 1
        return int(self.songid)

    def playid(self, song_id):
        self.commands.append(f"playid {song_id}")
        if self.playid_ack:
            raise MpdProtocolError(self.playid_ack, is_ack=True)
        self.state = "play"

    def pause(self, enabled):
        self.commands.append(f"pause {enabled}")
        self.state = "pause" if enabled else "play"

    def stop(self):
        self.commands.append("stop")
        self.state = "stop"

    def seekid(self, song_id, seconds):
        self.commands.append(f"seekid {song_id} {seconds:.3f}")
        self.elapsed = f"{seconds:.3f}"

    def setvol(self, volume):
        self.commands.append(f"setvol {volume}")
        self.volume = str(volume)

    def currentsong(self):
        self.commands.append("currentsong")
        return {
            "file": "/m/a.flac",
            "Id": self.songid or "0",
            "duration": self.duration,
            "Time": self.duration,
        }

    def idle(self, *subsystems):
        if _FakeClient.idle_event.wait(timeout=0.1):
            _FakeClient.idle_event.clear()
            return ["player"]
        return []


class _FakeRuntime:
    def __init__(self):
        self.closed = False
        self.socket_path = "/tmp/fake-mpd.sock"
        self.alive = True

    def start(self):
        pass

    def child_alive(self):
        return self.alive

    def close(self):
        self.closed = True


@pytest.fixture
def mpd_stack(monkeypatch, qapp):
    """MPDAudioPort (protocolo fake) → PlaybackService."""
    monkeypatch.setattr(
        "michi.infrastructure.audio_engines.mpd._MpdProtocolClient", _FakeClient
    )
    _FakeClient.idle_event = threading.Event()
    port = MPDAudioPort(runtime=_FakeRuntime(), poll_interval_ms=50)
    port.open()
    svc = PlaybackService(port)
    yield port, svc, port._client
    port.close()
    _FakeClient.idle_event.set()
    for _ in range(5):
        QCoreApplication.processEvents()


def _drain():
    for _ in range(8):
        QCoreApplication.processEvents()


def _refresh(port):
    port._bridge.sig_event.emit(
        _MpdEvent(port._runtime_generation, _MpdEventKind.REFRESH_PLAYER)
    )
    _drain()


class TestFullStack:
    def test_f1_load_and_play_sync_acceptance(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        # aceptación SÍNCRONA del MPD → commit inmediato + play
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._intent is True
        assert fake.commands[-1] == "playid 1"
        fake.state = "play"
        _refresh(port)
        assert svc.state.status == PlaybackStatus.PLAYING

    def test_f2_destructive_rejection_preserves_logical_a(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        fake.addid_ack = "ACK [2@0] {addid} rejected"
        svc.load_and_play(Path("/m/b.flac"))  # rejection controlada: sin raise
        # rejection sincrónica: identidad lógica A, sin autoridad backend
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert svc._pending_path is None
        assert "rejected" in (svc.state.error_message or "")

    def test_f3_destructive_failure_audio_load_error_false(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.addid_fatal = "socket closed mid-command"
        with pytest.raises(AudioLoadError) as caught:
            svc.load_and_play(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED

    def test_f4_play_failure_no_ghost(self, mpd_stack):
        from michi.application.ports import AudioTransportCommandError

        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.playid_ack = "ACK [1@0] {playid} rejected"
        with pytest.raises(AudioTransportCommandError, match="play rejected"):
            svc.load_and_play(Path("/m/b.flac"))
        _drain()
        # sin ghost backend aceptado para B
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED

    def test_f5_recovery_after_destructive_failure(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.addid_fatal = "socket closed mid-command"
        with pytest.raises(AudioLoadError):
            svc.load_and_play(Path("/m/b.flac"))
        # play() recupera el track lógico A
        fake.addid_fatal = None
        svc.play()
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/a.flac")
        fake.state = "play"
        _refresh(port)
        assert svc.state.status == PlaybackStatus.PLAYING


class TestPrepareForResume:
    def test_pr1_sync_acceptance_seeks_no_autoplay(self, mpd_stack):
        """R2 PRODUCTION REALITY: seekid on a stopped song STARTS playback
        (verified on real MPD 0.24.14) — the prepare seek is now DEFERRED to
        the explicit play, so prepare NEVER autoplays and NEVER issues a
        seekid against a stopped daemon."""
        port, svc, fake = mpd_stack
        svc.prepare_for_resume(Path("/m/b.flac"), 42000)
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/b.flac")
        assert "seekid" not in fake.commands  # R2: deferred, no autoplay
        assert "playid" not in fake.commands  # nunca un play implícito
        assert svc._intent is False  # prepare nunca autoplay
        assert svc.state.status == PlaybackStatus.STOPPED
        # el seek diferido se aplica tras el PLAY explícito
        fake.state = "play"
        svc.play()
        assert "playid 1" in fake.commands
        assert fake.commands[-1] == "seekid 1 42.000"

    def test_pr2_sync_rejection_terminal_no_seek(self, mpd_stack):
        port, svc, fake = mpd_stack
        fake.addid_ack = "ACK [2@0] {addid} rejected"
        svc.prepare_for_resume(Path("/m/b.flac"), 42000)  # sin raise
        assert svc._accepted is False
        assert svc._pending_path is None
        assert svc.state.status == PlaybackStatus.STOPPED
        assert "rejected" in (svc.state.error_message or "")
        assert "seekid" not in fake.commands  # sin seek tras rejection

    def test_pr3_destructive_exception_disposition(self, mpd_stack):
        port, svc, fake = mpd_stack
        fake.addid_fatal = "connection reset"
        with pytest.raises(AudioLoadError) as caught:
            svc.prepare_for_resume(Path("/m/b.flac"), 42000)
        assert caught.value.previous_source_preserved is False
        assert svc._accepted is False
        assert svc._pending_resume_position_ms is None

    def test_pr4_old_exception_does_not_mutate_new_request(self, mpd_stack):
        port, svc, fake = mpd_stack
        fake.addid_fatal = "connection reset after clear"

        def on_rejected(path, reason):
            fake.addid_fatal = None
            svc.load_and_play(Path("/m/c.flac"))

        port.subscribe_media_rejected(on_rejected)
        with pytest.raises(AudioLoadError):
            svc.prepare_for_resume(Path("/m/b.flac"), 42000)
        # C sigue siendo la dueña del request (aceptada sincrónicamente:
        # pending None + accepted True + identidad C)
        assert svc._pending_path is None
        assert svc._accepted is True
        assert svc.state.file_path == Path("/m/c.flac")


class TestThreadAffinity:
    def test_public_callbacks_on_owner_thread(self, mpd_stack):
        import threading

        port, svc, fake = mpd_stack
        owner_thread = threading.get_ident()
        callback_threads = []

        def on_acc(path):
            callback_threads.append(threading.get_ident())

        port.subscribe_media_accepted(on_acc)
        port.load(Path("/m/a.flac"))
        assert callback_threads == [owner_thread]


class TestBackendLossConvergence:
    """C5 (M11.3D-R1): la pérdida del backend (crash/transporte) debe
    converger PlaybackService — accepted/intent False, sin EOM."""

    def test_c5_process_exit_converges_playback(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        assert svc._accepted is True
        assert svc.state.status == PlaybackStatus.PLAYING
        # el hijo muere
        port._bridge.sig_event.emit(
            _MpdEvent(port._runtime_generation, _MpdEventKind.PROCESS_EXIT, "died")
        )
        _drain()
        # PlaybackService convergido: identidad lógica A, sin autoridad
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert "died" in (svc.state.error_message or "")  # reason del evento
        # MPDAudioPort sin autoridad backend
        assert port._current_path is None
        assert port._song_id is None
        assert port._pending_path is None

    def test_c5_no_eom_on_process_exit(self, mpd_stack):
        port, svc, fake = mpd_stack
        eoms = []
        svc.subscribe_end_of_media(lambda: eoms.append(1))
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        port._bridge.sig_event.emit(
            _MpdEvent(port._runtime_generation, _MpdEventKind.PROCESS_EXIT, "died")
        )
        _drain()
        assert eoms == []  # crash nunca emite EOM

    def test_c5_transport_error_converges_playback(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        port._bridge.sig_event.emit(
            _MpdEvent(port._runtime_generation, _MpdEventKind.TRANSPORT_ERROR, "broken")
        )
        _drain()
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert "broken" in (svc.state.error_message or "")  # reason del evento
        assert port._current_path is None


class TestGate1CommandTransportLoss:
    """GATE 1 full-stack (M11.3D-R2): el fallo del status() con hijo vivo
    converge PlaybackService — sin inyección manual de TRANSPORT_ERROR."""

    def test_g1_status_failure_converges_playback(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        assert svc._accepted is True
        assert svc.state.status == PlaybackStatus.PLAYING
        # el socket de comandos se rompe (hijo vivo)
        fake.status_error = "command socket EOF"
        _refresh(port)
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        assert "command socket EOF" in (svc.state.error_message or "")
        assert port._current_path is None
        assert port._song_id is None


class TestGate2ClearUnknownFullStack:
    """GATE 2 full-stack (M11.3D-R2): clear con IPC desconocido → sin
    ghost A en ninguna capa."""

    def test_g2_unknown_clear_converges_playback(self, mpd_stack):
        port, svc, fake = mpd_stack
        svc.load_and_play(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        assert svc._accepted is True
        # clear con resultado desconocido durante load(B)
        fake.clear_fatal = "EOF during clear"
        with pytest.raises(AudioLoadError) as caught:
            svc.load_and_play(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False
        # PlaybackService: identidad lógica A, sin autoridad backend
        assert svc.state.file_path == Path("/m/a.flac")
        assert svc._accepted is False
        assert svc._intent is False
        assert svc.state.status == PlaybackStatus.STOPPED
        # MPDAudioPort: sin ghost A
        assert port._current_path is None
        assert port._song_id is None
