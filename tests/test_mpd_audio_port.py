"""M11.3D — MPDAudioPort transport tests (deterministic, fake protocol)."""

import os
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication

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
    """Fake del protocolo: estado mutable + historial de comandos."""

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
        self.playid_ack: str | None = None
        self.next_id = 1
        self.status_error: str | None = None
        self.close_count = 0

    def connect(self):
        pass

    def close(self):
        self.close_count += 1

    def _record(self, cmd):
        self.commands.append(cmd)

    def status(self):
        self._record("status")
        if self.status_error:
            raise MpdProtocolError(self.status_error)
        status = {
            "state": self.state,
            "volume": self.volume,
        }
        if self.songid is not None:
            status["songid"] = self.songid
            status["elapsed"] = self.elapsed
            status["duration"] = self.duration
        if self.error:
            status["error"] = self.error
        return status

    def clear(self):
        self._record("clear")
        if self.clear_ack:
            raise MpdProtocolError(self.clear_ack, is_ack=True)
        if self.clear_fatal:
            raise MpdProtocolError(self.clear_fatal, is_ack=False)
        self.songid = None
        self.state = "stop"

    def addid(self, path):
        self._record(f"addid {path}")
        if self.addid_ack:
            raise MpdProtocolError(self.addid_ack, is_ack=True)
        if self.addid_fatal:
            raise MpdProtocolError(self.addid_fatal, is_ack=False)
        self.songid = str(self.next_id)
        self.next_id += 1
        return int(self.songid)

    def playid(self, song_id):
        self._record(f"playid {song_id}")
        if self.playid_ack:
            raise MpdProtocolError(self.playid_ack)
        self.state = "play"

    def pause(self, enabled):
        self._record(f"pause {enabled}")
        self.state = "pause" if enabled else "play"

    def stop(self):
        self._record("stop")
        self.state = "stop"

    def seekid(self, song_id, seconds):
        self._record(f"seekid {song_id} {seconds}")
        self.elapsed = f"{seconds:.3f}"

    def setvol(self, volume):
        self._record(f"setvol {volume}")
        self.volume = str(volume)

    def currentsong(self):
        self._record("currentsong")
        return {
            "file": "/m/a.flac",
            "Id": self.songid or "0",
            "duration": self.duration,
            "Time": self.duration,
        }

    def idle(self, *subsystems):
        # bloquea hasta un evento (o close del observer); devuelve el
        # subsistema cuando el test lo dispara
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
def mpd_env(monkeypatch, qapp):
    """Port con protocolo y runtime fake; el qapp (instancia Qt) es
    REQUERIDO para que processEvents() entregue los eventos QueuedConnection
    del bridge observer → owner."""
    monkeypatch.setattr(
        "michi.infrastructure.audio_engines.mpd._MpdProtocolClient", _FakeClient
    )
    _FakeClient.idle_event = threading.Event()
    runtime = _FakeRuntime()
    port = MPDAudioPort(runtime=runtime, poll_interval_ms=50)
    port.open()
    yield port, port._client  # el cliente fake instanciado por el port
    port.close()
    _FakeClient.idle_event.set()  # libera el observer si sigue vivo
    for _ in range(5):
        QCoreApplication.processEvents()


def _drain():
    for _ in range(8):
        QCoreApplication.processEvents()


def _refresh(port):
    """Entrega un REFRESH_PLAYER manual (seam del observer)."""
    port._bridge.sig_event.emit(
        _MpdEvent(port._runtime_generation, _MpdEventKind.REFRESH_PLAYER)
    )
    _drain()


class TestLoad:
    def test_l1_load_accepts_synchronously(self, mpd_env):
        port, _ = mpd_env
        accepted = []
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/a.flac"))
        assert accepted == [Path("/m/a.flac")]  # aceptación SÍNCRONA
        assert port._current_path == Path("/m/a.flac")
        assert port._song_id == 1
        assert port._pending_path is None

    def test_l2_addid_stores_stable_song_id(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        assert fake.commands[-1] == "addid /m/a.flac"
        assert port._song_id == 1

    def test_l3_addid_ack_rejects(self, mpd_env):
        port, fake = mpd_env
        fake.addid_ack = "ACK [2@0] {addid} cannot decode"
        rejected = []
        accepted = []
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_media_accepted(lambda p: accepted.append(p))
        port.load(Path("/m/b.flac"))  # rejection controlada: sin excepción
        assert rejected == [(Path("/m/b.flac"), "ACK [2@0] {addid} cannot decode")]
        assert accepted == []
        assert port._current_path is None
        assert port._song_id is None

    def test_l4_clear_ack_preserves_source(self, mpd_env):
        port, fake = mpd_env
        fake.clear_ack = "ACK [5@0] {clear} db busy"
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is True  # ACK → True

    def test_c3b_clear_unknown_outcome_fails_closed(self, mpd_env):
        port, fake = mpd_env
        fake.clear_fatal = "socket closed during clear"
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        # IPC desconocido: MPD pudo ejecutar clear → FAIL CLOSED (False)
        assert caught.value.previous_source_preserved is False

    def test_l5_failure_after_clear_is_destructive(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        fake.addid_fatal = "socket closed mid-command"
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False

    def test_l7_sync_acceptance_reentrant_load_c(self, mpd_env):
        port, fake = mpd_env
        loaded = []

        def on_acc(path):
            if path == Path("/m/a.flac"):
                port.load(Path("/m/c.flac"))  # reentrancy
                loaded.append(path)

        port.subscribe_media_accepted(on_acc)
        port.load(Path("/m/a.flac"))
        # el load(C) reentrante es la transacción final
        assert loaded == [Path("/m/a.flac")]
        assert port._current_path == Path("/m/c.flac")
        assert port._song_id == 2

    def test_l8_sync_acceptance_reentrant_stop(self, mpd_env):
        port, fake = mpd_env

        def on_acc(path):
            port.stop()

        port.subscribe_media_accepted(on_acc)
        port.load(Path("/m/a.flac"))
        # el stop del callback: transport detenido, source retenido
        assert port._current_path == Path("/m/a.flac")
        assert port._song_id == 1  # sin resurrección ni pérdida

    def test_l9_rejection_callback_load_c(self, mpd_env):
        port, fake = mpd_env
        fake.addid_fatal = "connection reset after clear"

        def on_rejected(path, reason):
            fake.addid_fatal = None
            port.load(Path("/m/c.flac"))

        port.subscribe_media_rejected(on_rejected)
        with pytest.raises(AudioLoadError):
            port.load(Path("/m/b.flac"))
        # C intacta: el load(B) viejo no muta tras el callback
        assert port._current_path == Path("/m/c.flac")
        assert port._song_id == 1


class TestPlaybackState:
    def test_s1_playid_ok_but_status_stop_no_playing(self, mpd_env):
        port, fake = mpd_env
        fake.playid_ack = "ACK [1@0] {playid} problems"
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        with pytest.raises(RuntimeError, match="MPD play failed"):
            port.play()
        assert PlaybackStatus.PLAYING not in states  # sin PLAYING optimista

    def test_s2_status_play_publishes_playing(self, mpd_env):
        port, fake = mpd_env
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        assert states[-1] == PlaybackStatus.PLAYING

    def test_s3_pause_publishes_paused(self, mpd_env):
        port, fake = mpd_env
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        port.pause()
        fake.state = "pause"
        _refresh(port)
        assert states[-1] == PlaybackStatus.PAUSED

    def test_s5_stop_publishes_stopped(self, mpd_env):
        port, fake = mpd_env
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        port.stop()
        fake.state = "stop"
        _refresh(port)
        assert states[-1] == PlaybackStatus.STOPPED

    def test_s6_s7_accepted_stop_preserves_song_id_and_replays(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        port.stop()
        assert port._song_id == 1  # retenido (Michi stop != unload)
        fake.state = "stop"
        _refresh(port)
        port.play()
        assert fake.commands[-1] == "playid 1"  # mismo song id
        fake.state = "play"
        _refresh(port)
        assert port._current_state == PlaybackStatus.PLAYING

    def test_s8_play_failure_no_ghost(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        fake.playid_ack = "ACK [1@0] {playid} rejected"
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        with pytest.raises(RuntimeError, match="MPD play failed"):
            port.play()
        _drain()
        assert PlaybackStatus.PLAYING not in states
        assert port._current_state == PlaybackStatus.STOPPED


class TestEos:
    def test_e1_natural_end_emits_stopped_then_eom(self, mpd_env):
        port, fake = mpd_env
        events = []
        port.subscribe_playback_state_changed(lambda s: events.append(str(s)))
        port.subscribe_end_of_media(lambda: events.append("eom"))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        # el daemon llega al final natural: state stop y sin song actual
        fake.state = "stop"
        fake.songid = None
        _refresh(port)
        assert events == ["PlaybackStatus.PLAYING", "PlaybackStatus.STOPPED", "eom"]

    def test_e2_explicit_stop_no_eom(self, mpd_env):
        port, fake = mpd_env
        eoms = []
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        port.stop()  # stop EXPLÍCITO: sin EOM
        fake.state = "stop"
        _refresh(port)
        assert eoms == []

    def test_e5_stopped_subscriber_loads_c_suppresses_eom(self, mpd_env):
        port, fake = mpd_env
        eoms = []
        port.subscribe_end_of_media(lambda: eoms.append(1))

        def on_state(s):
            if s == PlaybackStatus.STOPPED and port._current_path == Path("/m/a.flac"):
                port.load(Path("/m/c.flac"))

        port.subscribe_playback_state_changed(on_state)
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        fake.state = "stop"
        fake.songid = None
        _refresh(port)
        assert eoms == []  # EOM suprimido por la supersesión en el callback
        assert port._current_path == Path("/m/c.flac")


class TestSeek:
    def test_t6_seek_millis_to_fractional_seconds(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        port.seek(1234)
        assert fake.commands[-1] == "seekid 1 1.234"

    def test_t7_confirmed_position(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        fake.elapsed = "1.234"
        assert port.position() == 1234

    def test_t4_t5_position_only_accepted_source(self, mpd_env):
        port, fake = mpd_env
        positions = []
        port.subscribe_position_changed(lambda ms: positions.append(ms))
        assert port.position() == 0  # sin source aceptado
        port._poll_position()  # tick: sin accepted → sin publicación
        _drain()
        assert positions == []
        port.load(Path("/m/a.flac"))
        fake.elapsed = "2.000"
        port._poll_position()
        _drain()
        assert positions == [2000]


class TestVolumeMute:
    def test_v1_clamp(self, mpd_env):
        port, fake = mpd_env
        port.set_volume(150)
        assert port._volume == 100
        port.set_volume(-5)
        assert port._volume == 0

    def test_v2_set_volume_sends_setvol(self, mpd_env):
        port, fake = mpd_env
        port.set_volume(70)
        assert fake.commands[-1] == "setvol 70"

    def test_v3_mute_sends_zero(self, mpd_env):
        port, fake = mpd_env
        port.set_volume(70)
        port.set_muted(True)
        assert fake.commands[-1] == "setvol 0"

    def test_v4_volume_while_muted_retained_logically(self, mpd_env):
        port, fake = mpd_env
        port.set_volume(70)
        port.set_muted(True)
        port.set_volume(40)
        assert port._volume == 40  # lógico retenido
        assert fake.volume == "0"  # daemon sigue en 0

    def test_v5_unmute_restores(self, mpd_env):
        port, fake = mpd_env
        port.set_volume(40)
        port.set_muted(True)
        port.set_muted(False)
        assert fake.commands[-1] == "setvol 40"


class TestCrash:
    def test_c1_child_alive_commands_work(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        assert port._song_id == 1

    def test_c3_process_exit_converges_stopped_no_eom(self, mpd_env):
        port, fake = mpd_env
        states = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        assert states[-1] == PlaybackStatus.PLAYING
        # el hijo muere
        port._bridge.sig_event.emit(
            _MpdEvent(port._runtime_generation, _MpdEventKind.PROCESS_EXIT, "died")
        )
        _drain()
        assert states[-1] == PlaybackStatus.STOPPED
        assert eoms == []  # crash nunca emite EOM
        assert port._current_path is None
        assert port._song_id is None
        assert PlaybackStatus.PLAYING not in states[1:]

    def test_c5_queued_old_runtime_event_after_close(self, mpd_env):
        port, _ = mpd_env
        port.load(Path("/m/a.flac"))
        old_generation = port._runtime_generation
        port.close()
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port._bridge.sig_event.emit(
            _MpdEvent(old_generation, _MpdEventKind.REFRESH_PLAYER)
        )
        _drain()
        assert states == []  # cero delivery tras close


class TestProcessExitTransportError:
    def test_transport_error_converges(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        port._bridge.sig_event.emit(
            _MpdEvent(port._runtime_generation, _MpdEventKind.TRANSPORT_ERROR, "x")
        )
        _drain()
        # convergencia honesta: sin source autoritativo, estado STOPPED
        assert port._current_path is None
        assert port._song_id is None
        assert port._current_state == PlaybackStatus.STOPPED


class TestOpenFailureAtomicity:
    def test_c2_connect_failure_cleans_runtime(self, monkeypatch, qapp):
        import michi.infrastructure.audio_engines.mpd as mpd_mod

        started = []
        closed = []

        class FailingConnectClient:
            def __init__(self, *a, **k):
                pass

            def connect(self):
                raise MpdProtocolError("connect refused")

            def close(self):
                pass

        class TrackingRuntime(_FakeRuntime):
            def start(self):
                started.append(1)

            def close(self):
                closed.append(1)
                self.closed = True

        monkeypatch.setattr(mpd_mod, "_MpdProtocolClient", FailingConnectClient)
        port = MPDAudioPort(runtime=TrackingRuntime())
        with pytest.raises(MpdProtocolError, match="connect refused"):
            port.open()
        # failure-atomic: runtime cerrado exactamente una vez, sin recursos
        assert started == [1]
        assert closed == [1]
        assert port._client is None
        assert port._observer is None
        assert port._poller is None
        assert port._closed is True


class TestObserverFailure:
    def _port_with_idle_error(self, monkeypatch, qapp, runtime_alive, on_event=None):
        import michi.infrastructure.audio_engines.mpd as mpd_mod

        class IdleFailingClient(_FakeClient):
            def idle(self, *subsystems):
                raise MpdProtocolError("idle connection broken")

        monkeypatch.setattr(mpd_mod, "_MpdProtocolClient", IdleFailingClient)
        runtime = _FakeRuntime()
        runtime.alive = runtime_alive
        port = MPDAudioPort(runtime=runtime, poll_interval_ms=50)
        if on_event is not None:
            # el observer emite DURANTE open() — suscribir ANTES
            port._bridge.sig_event.connect(on_event)
        port.open()
        return port

    def test_c4a_idle_eof_child_alive_transport_error(self, monkeypatch, qapp):
        errors = []
        port = self._port_with_idle_error(
            monkeypatch,
            qapp,
            runtime_alive=True,
            on_event=lambda e: errors.append(e.kind),
        )
        port._observer.join(timeout=2.0)
        for _ in range(5):
            QCoreApplication.processEvents()
        # UN evento terminal TRANSPORT_ERROR (sin loop)
        assert errors == [_MpdEventKind.TRANSPORT_ERROR]
        port.close()

    def test_c4b_idle_eof_child_dead_process_exit(self, monkeypatch, qapp):
        errors = []
        port = self._port_with_idle_error(
            monkeypatch,
            qapp,
            runtime_alive=False,
            on_event=lambda e: errors.append(e.kind),
        )
        port._observer.join(timeout=2.0)
        for _ in range(5):
            QCoreApplication.processEvents()
        assert errors == [_MpdEventKind.PROCESS_EXIT]
        port.close()

    def test_c4c_single_terminal_event_no_loop(self, monkeypatch, qapp):
        errors = []
        port = self._port_with_idle_error(
            monkeypatch,
            qapp,
            runtime_alive=True,
            on_event=lambda e: errors.append(e.kind),
        )
        port._observer.join(timeout=2.0)
        for _ in range(5):
            QCoreApplication.processEvents()
        assert errors.count(_MpdEventKind.TRANSPORT_ERROR) == 1
        port.close()

    def test_c4d_close_terminates_observer(self, mpd_env):
        port, fake = mpd_env
        observer = port._observer
        assert observer is not None and observer.is_alive()
        port.close()
        assert not observer.is_alive()
        assert port._idle_client is None


class TestStatusError:
    def test_c6a_error_converges_rejected_no_eom(self, mpd_env):
        port, fake = mpd_env
        states = []
        rejected = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        assert states[-1] == PlaybackStatus.PLAYING
        # el daemon reporta error de playback
        fake.state = "stop"
        fake.error = "decoder failed"
        _refresh(port)
        assert states[-1] == PlaybackStatus.STOPPED
        assert rejected == [(Path("/m/a.flac"), "decoder failed")]
        assert eoms == []
        assert port._current_path is None
        assert port._song_id is None

    def test_c6b_error_with_state_play_no_playing(self, mpd_env):
        port, fake = mpd_env
        states = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.load(Path("/m/a.flac"))
        fake.state = "play"
        fake.error = "output failed"
        _refresh(port)
        # el error gana sobre state=play: sin PLAYING falso
        assert PlaybackStatus.PLAYING not in states
        assert port._current_state == PlaybackStatus.STOPPED
        assert port._current_path is None


class TestPollInterval:
    def test_poll_interval_honored(self, mpd_env):
        # el fixture usa poll_interval_ms=50 → el QTimer respeta el valor
        port, fake = mpd_env
        assert port._poller is not None
        assert port._poller.interval() == 50


class TestLiveChildBrokenCommandSocket:
    """GATE 1 (M11.3D-R2): proceso vivo + socket de comandos roto → nunca
    return silencioso; convergencia de transporte honesta."""

    def test_g1_refresh_converges_transport_error(self, mpd_env):
        port, fake = mpd_env
        states = []
        rejected = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(Path("/m/a.flac"))
        port.play()
        fake.state = "play"
        _refresh(port)
        assert states[-1] == PlaybackStatus.PLAYING
        # el socket de comandos se rompe con el hijo vivo
        fake.status_error = "command socket EOF"
        _refresh(port)
        assert port._current_path is None
        assert port._song_id is None
        assert port._pending_path is None
        assert port._current_state == PlaybackStatus.STOPPED
        assert rejected == [(Path("/m/a.flac"), "command socket EOF")]
        assert eoms == []

    def test_g1_poller_converges_transport_error(self, mpd_env):
        port, fake = mpd_env
        states = []
        rejected = []
        port.subscribe_playback_state_changed(lambda s: states.append(s))
        port.subscribe_media_rejected(lambda p, r: rejected.append((p, r)))
        port.load(Path("/m/a.flac"))
        fake.state = "play"
        _refresh(port)
        fake.status_error = "socket read failed"
        port._poll_position()  # el poller del owner también converge
        _drain()
        assert port._current_path is None
        assert port._song_id is None
        assert rejected == [(Path("/m/a.flac"), "socket read failed")]
        # los ticks siguientes son no-op (sin spam de rejection)
        port._poll_position()
        _drain()
        assert rejected == [(Path("/m/a.flac"), "socket read failed")]


class TestGate2ClearUnknownOutcome:
    """GATE 2 (M11.3D-R2): clear con IPC desconocido abandona la autoridad
    backend vieja (nunca ghost song_id); clear ACK la preserva."""

    def test_g2_clear_ack_preserves_backend_authority(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        previous_id = port._song_id
        assert previous_id is not None
        fake.clear_ack = "ACK [5@0] {clear} db busy"
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is True
        # la autoridad vieja queda intacta
        assert port._current_path == Path("/m/a.flac")
        assert port._song_id == previous_id

    def test_g2_clear_unknown_invalidates_backend_authority(self, mpd_env):
        port, fake = mpd_env
        port.load(Path("/m/a.flac"))
        fake.clear_fatal = "EOF during clear"
        with pytest.raises(AudioLoadError) as caught:
            port.load(Path("/m/b.flac"))
        assert caught.value.previous_source_preserved is False
        # sin ghost A: la autoridad backend vieja se abandona
        assert port._current_path is None
        assert port._song_id is None
        assert port._pending_play is False
        assert port._pending_path is None


class TestGate3OpenFailureAfterObserver:
    """GATE 3 (M11.3D-R2): fallo tras el arranque del observer → el idle
    socket se cierra ANTES del join (sin threads vivos)."""

    def test_g3_poller_setup_failure_cleans_observer(self, monkeypatch, qapp):
        import michi.infrastructure.audio_engines.mpd as mpd_mod

        class FailingTimer:
            def __init__(self, *a, **k):
                raise RuntimeError("poller setup failed")

            def setInterval(self, *a):  # noqa: N802 — Qt API surface
                pass

            def timeout(self):
                pass

            def start(self):
                pass

            def stop(self):
                pass

        monkeypatch.setattr(mpd_mod, "QTimer", FailingTimer)
        monkeypatch.setattr(mpd_mod, "_MpdProtocolClient", _FakeClient)
        # GATE A2 (M11.3D-R3): retener el THREAD REAL del observer (el
        # cleanup pone port._observer = None — eso solo no prueba la muerte
        # del thread)
        real_thread = threading.Thread
        created_threads = []

        def tracked_thread(*args, **kwargs):
            t = real_thread(*args, **kwargs)
            created_threads.append(t)
            return t

        monkeypatch.setattr(mpd_mod.threading, "Thread", tracked_thread)
        closed = []

        class TrackingRuntime(_FakeRuntime):
            def close(self):
                closed.append(1)
                self.closed = True

        port = MPDAudioPort(runtime=TrackingRuntime(), poll_interval_ms=50)
        with pytest.raises(RuntimeError, match="poller setup failed"):
            port.open()
        # el THREAD REAL del observer está muerto (sin leak)
        assert created_threads, "el observer thread nunca se creó"
        observer_thread = created_threads[0]
        assert not observer_thread.is_alive()
        assert port._observer is None
        assert port._idle_client is None
        assert port._client is None
        assert port._poller is None
        assert closed == [1]  # runtime cerrado exactamente una vez
        assert port._closed is True
