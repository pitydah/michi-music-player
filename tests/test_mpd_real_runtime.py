"""M11.3D — real MPD runtime smoke (private instance only).

SKIP truthful solo si el ejecutable mpd está genuinamente ausente; con el
ejecutable presente, los fallos de arranque/config/socket son FAIL."""

import os
import shutil

import pytest

pytestmark = pytest.mark.mpd_runtime

REQUIRED = [
    "mpd",
]


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


def _require_mpd():
    if shutil.which("mpd") is None:
        pytest.skip("dependency absent: mpd executable not found in PATH")
    return True


def test_real_private_runtime_smoke(qapp, tmp_path):
    """Arranca UNA instancia MPD privada (runtime + socket propios),
    handshake, status, addid/clear, y teardown completo."""
    _require_mpd()

    from michi.infrastructure.audio_engines.mpd import (
        _ManagedMpdRuntime,
        _MpdProtocolClient,
    )

    runtime = _ManagedMpdRuntime(startup_timeout=10.0)
    runtime.start()
    try:
        assert runtime.socket_path is not None
        assert os.path.exists(runtime.socket_path)
        assert runtime.child_alive()
        # handshake + status reales
        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        status = client.status()
        assert "state" in status
        # addid/clear sobre un archivo inexistente → ACK determinista o error
        # (no exigimos reproducción; solo que el protocolo responda)
        try:
            client.clear()
            client.addid(str(tmp_path / "nope.flac"))
        except Exception as exc:  # noqa: BLE001 — runtime truth
            # un ACK o error del daemon es una respuesta VÁLIDA del
            # protocolo; un EOF/socket roto sería un fallo real
            assert "EOF" not in str(exc), f"protocol broken: {exc}"
        client.close()
    finally:
        runtime.close()
    # teardown completo: sin proceso, sin socket, sin runtime
    assert runtime.process is None or runtime.process.poll() is not None
    assert runtime.socket_path is None
    assert runtime.runtime_dir is None


def test_real_natural_eos_observation(qapp, tmp_path):
    """GATE B (M11.3D-R3): observación REAL del fin natural de MPD.

    WAV diminuto (0.25s, PCM 16-bit mono 44.1kHz) → clear → addid →
    playid → esperar state=play → esperar el fin natural SIN stop() →
    registrar los campos reales del daemon."""
    _require_mpd()

    import struct
    import time
    import wave
    from math import sin

    from michi.infrastructure.audio_engines.mpd import (
        _ManagedMpdRuntime,
        _MpdProtocolClient,
    )

    # WAV determinista de 0.25 s
    wav = tmp_path / "tone.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * 0.8 * sin(2 * 3.14159 * 440 * i / 44100)))
                for i in range(11025)
            )
        )
    runtime = _ManagedMpdRuntime(startup_timeout=10.0, null_output=True)
    runtime.start()
    try:
        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        client.clear()
        song_id = client.addid(str(wav))
        client.playid(song_id)
        # esperar PLAYING real (bounded)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            status = client.status()
            if status.get("state") == "play":
                break
            time.sleep(0.05)
        assert status.get("state") == "play", f"no PLAYING: {status}"
        while_playing = dict(status)
        # esperar el fin natural SIN stop() (bounded 10s)
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            status = client.status()
            if status.get("state") == "stop":
                break
            time.sleep(0.05)
        assert status.get("state") == "stop", f"no natural end: {status}"
        after_end = dict(status)
        song_after = client.currentsong()
        # EVIDENCIA OBSERVADA (se reporta tal cual)
        print(
            "WHILE PLAYING: state={} songid={} elapsed={} duration={}".format(
                while_playing.get("state"),
                while_playing.get("songid"),
                while_playing.get("elapsed"),
                while_playing.get("duration"),
            )
        )
        print(
            "AFTER NATURAL END: state={} songid={} elapsed={} duration={}".format(
                after_end.get("state"),
                after_end.get("songid"),
                after_end.get("elapsed"),
                after_end.get("duration"),
            )
        )
        print("currentsong after end:", song_after)
        # la heurística actual (songid ausente tras fin natural) se evalúa
        # con la evidencia real: si MPD conserva songid, la heurística es
        # incorrecta — el test falla y exige revisarla
        assert after_end.get("songid") is None, (
            "real MPD conserva songid tras el fin natural — heurística EOS "
            f"incorrecta (observado: {after_end})"
        )
        client.close()
    finally:
        runtime.close()


def test_real_explicit_stop_observation(qapp, tmp_path):
    """GATE B (M11.3D-RUNTIME-VERIFY): observación REAL del stop
    EXPLÍCITO — compara con el fin natural (songid presente vs ausente)."""
    _require_mpd()

    import struct
    import time
    import wave
    from math import sin

    from michi.infrastructure.audio_engines.mpd import (
        _ManagedMpdRuntime,
        _MpdProtocolClient,
    )

    wav = tmp_path / "tone.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * 0.8 * sin(2 * 3.14159 * 440 * i / 44100)))
                for i in range(11025)
            )
        )

    runtime = _ManagedMpdRuntime(startup_timeout=10.0, null_output=True)
    runtime.start()
    try:
        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        client.clear()
        song_id = client.addid(str(wav))
        client.playid(song_id)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            status = client.status()
            if status.get("state") == "play":
                break
            time.sleep(0.05)
        assert status.get("state") == "play", f"no PLAYING: {status}"
        while_playing = dict(status)
        # STOP EXPLÍCITO (diferente del fin natural)
        client.stop()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            status = client.status()
            if status.get("state") == "stop":
                break
            time.sleep(0.05)
        after_stop = dict(status)
        song_after = client.currentsong()
        print(
            "WHILE PLAYING: state={} songid={} elapsed={} duration={}".format(
                while_playing.get("state"),
                while_playing.get("songid"),
                while_playing.get("elapsed"),
                while_playing.get("duration"),
            )
        )
        print(
            "AFTER EXPLICIT STOP: state={} songid={} elapsed={} duration={}".format(
                after_stop.get("state"),
                after_stop.get("songid"),
                after_stop.get("elapsed"),
                after_stop.get("duration"),
            )
        )
        print("currentsong after explicit stop:", song_after)
        # distinción real observada: el stop EXPLÍCITO conserva la canción
        # (songid presente); el fin natural la elimina (songid ausente)
        assert after_stop.get("songid") is not None, (
            "stop explícito no conserva songid — distinción natural/stop "
            f"no observable (observado: {after_stop})"
        )
        client.close()
    finally:
        runtime.close()


def _real_port_and_wav(tmp_path):
    """Port MPD real + WAV diminuto (0.25s) con null output de test."""
    import struct
    import wave
    from math import sin

    from michi.infrastructure.audio_engines.mpd import (
        MPDAudioPort,
        _ManagedMpdRuntime,
    )

    wav = tmp_path / "tone.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * 0.8 * sin(2 * 3.14159 * 440 * i / 44100)))
                for i in range(11025)
            )
        )
    port = MPDAudioPort(
        runtime=_ManagedMpdRuntime(startup_timeout=10.0, null_output=True),
        poll_interval_ms=50,
    )
    port.open()
    return port, wav


def _wait_real(port, predicate, timeout=8.0):
    import time

    from PySide6.QtCore import QCoreApplication

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for _ in range(5):
            QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.03)
    for _ in range(5):
        QCoreApplication.processEvents()
    return predicate()


def test_real_mpd_audio_port_natural_eos(qapp, tmp_path):
    """MPDAudioPort real: fin natural → callbacks [PLAYING, STOPPED, EOM]."""
    _require_mpd()

    from michi.domain.playback import PlaybackStatus

    port, wav = _real_port_and_wav(tmp_path)
    try:
        events = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: events.append(s))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(wav)
        assert port._song_id is not None  # aceptación sincrónica real
        port.play()
        assert _wait_real(port, lambda: PlaybackStatus.PLAYING in events), (
            f"no PLAYING real (events={events})"
        )
        # fin natural (0.25s) → STOPPED → EOM exactamente una vez
        assert _wait_real(port, lambda: eoms == [1]), (
            f"no EOM real (events={events}, eoms={eoms})"
        )
        assert eoms == [1]
        playing = [i for i, s in enumerate(events) if s == PlaybackStatus.PLAYING]
        stopped = [i for i, s in enumerate(events) if s == PlaybackStatus.STOPPED]
        assert playing and stopped and playing[0] < stopped[0]
        assert eoms == [1]
    finally:
        port.close()


def test_real_mpd_audio_port_explicit_stop_no_eom(qapp, tmp_path):
    """MPDAudioPort real: stop EXPLÍCITO → STOPPED sin EOM."""
    _require_mpd()

    from michi.domain.playback import PlaybackStatus

    port, wav = _real_port_and_wav(tmp_path)
    try:
        events = []
        eoms = []
        port.subscribe_playback_state_changed(lambda s: events.append(s))
        port.subscribe_end_of_media(lambda: eoms.append(1))
        port.load(wav)
        port.play()
        assert _wait_real(port, lambda: PlaybackStatus.PLAYING in events), (
            f"no PLAYING real (events={events})"
        )
        port.stop()  # stop explícito ANTES del fin natural (0.25s)
        assert _wait_real(port, lambda: PlaybackStatus.STOPPED in events), (
            f"no STOPPED real (events={events})"
        )
        # margen: esperar un poco más por si un EOM espurio llegara
        _wait_real(port, lambda: bool(eoms), timeout=1.5)
        assert eoms == []
    finally:
        port.close()
