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


def test_real_mixer_software_guarantees_volume(qapp):
    """M11.3-UI-R2 gate (section 12): REAL MPD + explicit output policy +
    software mixer must guarantee setvol — no 'no such mixer control: PCM'.

    The pre-fix implicit output autodetection selected a hardware ALSA
    mixer ("PCM") that the default device does not expose (ACK [5@0]
    {setvol}). The explicit compatibility output with software mixer
    must succeed on the real private runtime."""
    _require_mpd()

    from michi.infrastructure.audio_engines.mpd import (
        _ManagedMpdRuntime,
        _MpdProtocolClient,
    )

    runtime = _ManagedMpdRuntime(startup_timeout=10.0)
    runtime.start()
    try:
        # production output policy selected deterministically
        assert runtime._output_plugin in ("pipewire", "pulse", "alsa")
        conf = (runtime.runtime_dir / "mpd.conf").read_text(encoding="utf-8")
        assert 'mixer_type\t"software"' in conf
        assert "mixer_control" not in conf

        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        try:
            st = client.status()
            assert "volume" in st  # a mixer actually exists
            client.setvol(73)
            assert client.status()["volume"] == "73"
            client.setvol(0)
            assert client.status()["volume"] == "0"
            client.setvol(100)
            assert client.status()["volume"] == "100"
        finally:
            client.close()
    finally:
        runtime.close()
    assert runtime.process is None or runtime.process.poll() is not None


def test_real_production_output_policy_selected(qapp):
    """The local physical gate: private child starts, output policy is
    selected from the compiled plugin list, protocol connects and the
    software mixer answers setvol without any ACK."""
    _require_mpd()

    from michi.infrastructure.audio_engines.mpd import (
        _discover_mpd_output_plugins,
        _ManagedMpdRuntime,
        _MpdProtocolClient,
        _select_default_mpd_output_plugin,
    )

    compiled = _discover_mpd_output_plugins()
    assert compiled  # real evidence from the installed binary
    selected = _select_default_mpd_output_plugin(compiled)
    assert selected in ("pipewire", "pulse", "alsa")

    runtime = _ManagedMpdRuntime(startup_timeout=10.0)
    runtime.start()
    try:
        assert runtime._output_plugin == selected
        client = _MpdProtocolClient(runtime.socket_path, timeout=5.0)
        client.connect()
        try:
            client.setvol(42)
            assert client.status()["volume"] == "42"
            client.setvol(100)
        finally:
            client.close()
    finally:
        runtime.close()


class TestRealEngineSwitch:
    """M11.3-UI-R2 gate (section 13): the FULL explicit switch transaction
    responsible for the reported defect, against the REAL MPD runtime.

    Qt (fake provider) active → explicit switch to REAL MPD → restore
    volume/mute succeeds → READY → switch back to Qt → no child leaks.
    """

    def _graph(self):
        from michi.application.audio_engine_registry import (
            AudioEngineRegistry,
        )
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSelectionCoordinator,
        )
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import AudioTransportRouter
        from michi.application.playback_service import PlaybackService
        from michi.application.settings_service import SettingsService
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.providers import (
            MpdEngineProvider,
        )
        from tests.test_m11_3f_engine_selection import (
            FakeProvider,
            FakeSettingsRepository,
        )

        qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        mpd = MpdEngineProvider()
        registry = AudioEngineRegistry([qt, mpd])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        playback = PlaybackService(router)
        settings = SettingsService(FakeSettingsRepository())
        coordinator = AudioEngineSelectionCoordinator(
            engine_service=service,
            registry=registry,
            router=router,
            playback=playback,
            settings=settings,
        )
        return qt, mpd, service, router, playback, coordinator

    def test_real_switch_qt_to_mpd_and_back(self, qapp):
        _require_mpd()
        from michi.domain.audio_engine import AudioEngineId

        qt, mpd, service, router, playback, coordinator = self._graph()
        # arm: Qt active (like bootstrap)
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        playback.set_volume(63)
        playback.set_muted(False)

        # ── Qt → MPD ───────────────────────────────────────────────────
        coordinator.switch_to(AudioEngineId.MPD)
        st = service.state
        assert st.lifecycle.value == "ready"
        assert st.selected_engine_id == AudioEngineId.MPD
        assert st.active_engine_id == AudioEngineId.MPD
        assert router.bound_engine_id == AudioEngineId.MPD
        assert st.error_message is None
        # volume restored on the REAL MPD mixer (provider → port → runtime)
        port = mpd._port
        assert port is not None and port._client is not None
        assert port._client.status()["volume"] == "63"
        assert port._runtime is not None and port._runtime.child_alive()

        # ── MPD → Qt ───────────────────────────────────────────────────
        coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
        st = service.state
        assert st.lifecycle.value == "ready"
        assert st.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.active_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        assert st.error_message is None
        # MPD child reaped and artifacts removed — no leak
        assert port._runtime.process is None
        assert port._runtime.runtime_dir is None

    def test_real_switch_multiple_cycles_no_leak(self, qapp):
        _require_mpd()
        from michi.domain.audio_engine import AudioEngineId

        qt, mpd, service, router, playback, coordinator = self._graph()
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        playback.set_volume(55)
        playback.set_muted(False)

        last_mpd_runtime = None
        for target in (
            AudioEngineId.MPD,
            AudioEngineId.QT_MULTIMEDIA,
            AudioEngineId.MPD,
            AudioEngineId.QT_MULTIMEDIA,
        ):
            coordinator.switch_to(target)
            st = service.state
            assert st.lifecycle.value == "ready", target
            assert st.selected_engine_id == target
            assert st.active_engine_id == target
            assert router.bound_engine_id == target
            assert st.error_message is None
            # every cycle must restore the canonical volume; keep the last
            # MPD runtime reference for the leak check after it is closed
            if target == AudioEngineId.MPD:
                assert mpd._port._client.status()["volume"] == "55"
                last_mpd_runtime = mpd._port._runtime

        # final state on Qt (last cycle); MPD fully released
        assert last_mpd_runtime is not None
        assert last_mpd_runtime.process is None
        assert last_mpd_runtime.runtime_dir is None


def test_real_mixer_failure_still_fatal(qapp, monkeypatch):
    """M11.3-UI-R2 gate (section 14): a genuine mixer failure must remain
    fatal — restore_volume raises, the coordinator never marks READY.

    This proves the fix configures the mixer correctly instead of
    suppressing mixer failures."""
    _require_mpd()

    from michi.application.audio_engine_registry import AudioEngineRegistry
    from michi.application.audio_engine_selection_coordinator import (
        AudioEngineSelectionCoordinator,
    )
    from michi.application.audio_engine_service import AudioEngineService
    from michi.application.audio_transport_router import AudioTransportRouter
    from michi.application.playback_service import PlaybackService
    from michi.application.settings_service import SettingsService
    from michi.domain.audio_engine import AudioEngineId
    from michi.infrastructure.audio_engines.providers import (
        MpdEngineProvider,
    )
    from tests.test_m11_3f_engine_selection import (
        FakeProvider,
        FakeSettingsRepository,
    )

    qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
    mpd = MpdEngineProvider()
    registry = AudioEngineRegistry([qt, mpd])
    service = AudioEngineService(registry)
    router = AudioTransportRouter()
    playback = PlaybackService(router)
    settings = SettingsService(FakeSettingsRepository())
    coordinator = AudioEngineSelectionCoordinator(
        engine_service=service,
        registry=registry,
        router=router,
        playback=playback,
        settings=settings,
    )
    qt_port = qt.open()
    router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
    service.mark_ready(AudioEngineId.QT_MULTIMEDIA)

    # inject a REAL mixer failure at the port boundary (the provider opens
    # its port inside the switch transaction; a genuine setvol failure must
    # remain fatal)
    from michi.infrastructure.audio_engines.mpd import MPDAudioPort

    def broken_set_volume(self, value):
        raise RuntimeError("MPD setvol failed: mixer exploded")

    monkeypatch.setattr(MPDAudioPort, "set_volume", broken_set_volume)

    with pytest.raises(RuntimeError, match="MPD setvol failed"):
        coordinator.switch_to(AudioEngineId.MPD)
    st = service.state
    # first-error-wins: target NOT ready, honest lifecycle
    assert st.lifecycle.value == "failed"
    assert st.active_engine_id != AudioEngineId.MPD
    # cleanup: no leaked child
    port = mpd._port
    if port is not None and port._runtime is not None:
        runtime = port._runtime
        assert runtime.process is None or runtime.process.poll() is not None
        if runtime.process is not None:
            runtime.process.kill()


class TestProductionRestoreGolden:
    """R2 PRODUCTION REALITY golden gate: the exact production restore
    sequence (persisted MPD selected -> activate -> prepare_for_resume)
    against the REAL private MPD must NEVER autoplay — verified at THREE
    levels: PlaybackState, daemon status, elapsed progress."""

    def _graph(self):
        from michi.application.audio_engine_registry import AudioEngineRegistry
        from michi.application.audio_engine_selection_coordinator import (
            AudioEngineSelectionCoordinator,
        )
        from michi.application.audio_engine_service import AudioEngineService
        from michi.application.audio_transport_router import AudioTransportRouter
        from michi.application.playback_service import PlaybackService
        from michi.application.settings_service import SettingsService
        from michi.domain.audio_engine import AudioEngineId
        from michi.infrastructure.audio_engines.providers import MpdEngineProvider
        from tests.test_m11_3f_engine_selection import (
            FakeProvider,
            FakeSettingsRepository,
        )

        qt = FakeProvider(AudioEngineId.QT_MULTIMEDIA)
        mpd = MpdEngineProvider()
        registry = AudioEngineRegistry([qt, mpd])
        service = AudioEngineService(registry)
        router = AudioTransportRouter()
        playback = PlaybackService(router)
        settings = SettingsService(FakeSettingsRepository())
        coordinator = AudioEngineSelectionCoordinator(
            engine_service=service,
            registry=registry,
            router=router,
            playback=playback,
            settings=settings,
        )
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        return qt, mpd, service, router, playback, coordinator

    def test_real_restore_prepare_never_autoplays(self, qapp, tmp_path):
        import time

        from PySide6.QtTest import QTest

        def _drain():
            from PySide6.QtWidgets import QApplication

            for _ in range(20):
                QApplication.processEvents()

        def _pump(ms):
            QTest.qWait(ms)

        _require_mpd()
        from michi.domain.audio_engine import AudioEngineId
        from michi.domain.playback import PlaybackStatus
        from tests.test_audio_engine_conformance import _write_wav

        wav = _write_wav(tmp_path / "tone.wav")
        qt, mpd, service, router, playback, coordinator = self._graph()
        qt_port = qt.open()
        router.bind(AudioEngineId.QT_MULTIMEDIA, qt_port)
        service.mark_ready(AudioEngineId.QT_MULTIMEDIA)
        try:
            # PRODUCTION SEQUENCE: persisted preferred engine = MPD
            coordinator.switch_to(AudioEngineId.MPD)
            assert service.state.active_engine_id == AudioEngineId.MPD
            # persisted session restore → prepare_for_resume
            playback.prepare_for_resume(wav, 1000)
            _drain()
            # LEVEL 1: model state
            assert playback.state.status == PlaybackStatus.STOPPED
            assert playback._intent is False
            # LEVEL 2: DAEMON truth — must be stop, NOT play
            port = mpd._port
            daemon_state = port._client.status().get("state")
            assert daemon_state == "stop", (
                f"AUTOPLAY: daemon state={daemon_state} after prepare_for_resume"
            )
            # LEVEL 3: elapsed must NOT advance (no playback progress)
            elapsed_before = port._client.status().get("elapsed", "0")
            time.sleep(1.2)
            elapsed_after = port._client.status().get("elapsed", "0")
            assert elapsed_before == elapsed_after == "0", (
                f"AUTOPLAY: elapsed advanced {elapsed_before} -> {elapsed_after}"
            )
            # EXPLICIT user play starts playback with the deferred position
            playback.play()
            _pump(600)
            assert playback.state.status == PlaybackStatus.PLAYING
            daemon_state = port._client.status().get("state")
            assert daemon_state == "play"
            elapsed = port._client.status().get("elapsed", "0")
            assert float(elapsed) >= 1.0  # resumed near the persisted position
            playback.stop()
            coordinator.switch_to(AudioEngineId.QT_MULTIMEDIA)
        finally:
            try:
                router.unbind()
                qt.close()
                mpd.close()
            except Exception:  # noqa: BLE001 — teardown must not mask
                pass
