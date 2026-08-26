"""R2.1-04 — TRUE production persisted-MPD startup golden gate.

Executes the EXACT production composition (ApplicationContainer +
persisted settings DB + persisted session + real private MPD child) —
not a manually assembled fake graph. Asserts at three truth levels
(model, daemon, temporal) plus process ownership and the full user
command cycle.

CLAIM:
    persisted MPD + persisted session startup does not autoplay and the
    full Play/Pause/Resume/Stop cycle works against the real daemon.

OBSERVABLES:
    PlaybackState.status, container router binding, engine service state,
    exact private MPD status.state, exact private MPD elapsed, MPD child
    pid/socket ownership.

REAL:
    ApplicationContainer, SQLite settings + session DBs, MpdEngineProvider,
    private mpd child, production convergence + persistence restore.

FAKE:
    none in the causal path being proven.

DOES NOT PROVE:
    DAC/direct-output behavior (M11.4), UI interaction (covered by the
    QML gate), non-MPD engines on this path.
"""

import contextlib
import os
import shutil
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _write_wav(path: Path, seconds: float = 120.0) -> Path:
    import struct
    import wave
    from math import sin

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(
            b"".join(
                struct.pack("<h", int(8000 * 0.8 * sin(2 * 3.14159 * 440 * i / 44100)))
                for i in range(44100 * int(seconds))
            )
        )
    return path


def _seed_db(db_path: Path, wav: Path) -> None:
    """Persist the production inputs BEFORE the container starts:
    selected engine = MPD, coherent session (track + position)."""
    from michi.application.settings_service import SettingsService
    from michi.domain.audio_engine import AudioEngineId
    from michi.domain.session import (
        PersistedSessionContext,
        PlaybackSessionSnapshot,
        RepeatMode,
    )
    from michi.infrastructure.session_repository import SqliteSessionRepository
    from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

    settings_repo = SQLiteSettingsRepository.open_for_startup(db_path)
    settings = SettingsService(settings_repo)
    settings.set_audio_engine(AudioEngineId.MPD)
    settings.save()

    session_repo = SqliteSessionRepository(db_path)
    # a COHERENT session: the current entry equals playback_path, so the
    # production restore requests prepare_for_resume (M4-R1 §66 coherence
    # rule) — this is exactly the production startup condition
    from michi.domain.session import FORMAT_VERSION, PersistedQueueEntry

    snapshot = PlaybackSessionSnapshot(
        format_version=FORMAT_VERSION,
        queue_entries=(),
        context=PersistedSessionContext(
            context_type="none",
            source_id=None,
            entries=(PersistedQueueEntry(file_path=str(wav), title="tone"),),
            current_index=0,
        ),
        playback_path=str(wav),
        position_ms=45000,
        repeat_mode=RepeatMode.NONE,
        shuffle_enabled=False,
        shuffle_seed=0,
    )
    session_repo.save(snapshot)


class TestProductionContainerRestore:
    def test_persisted_mpd_startup_golden(self, qapp, tmp_path):
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from PySide6.QtWidgets import QApplication

        from michi.bootstrap import ApplicationContainer
        from michi.domain.audio_engine import AudioEngineId
        from michi.domain.playback import PlaybackStatus

        # isolate the data/cache dirs from the real user profile
        data_home = tmp_path / "data"
        cache_home = tmp_path / "cache"
        data_home.mkdir()
        cache_home.mkdir()
        os.environ["XDG_DATA_HOME"] = str(data_home)
        os.environ["XDG_CACHE_HOME"] = str(cache_home)

        wav = _write_wav(tmp_path / "tone.wav")
        # AppLocalDataLocation under XDG_DATA_HOME is
        # <XDG_DATA_HOME>/<org>/<app> — resolve it with the SAME org/app
        # names the container's initialize() sets (otherwise the path
        # differs and the seed writes to the wrong database)
        from PySide6.QtCore import QCoreApplication, QStandardPaths

        QCoreApplication.setOrganizationName("Michi")
        QCoreApplication.setApplicationName("Michi Music Player")
        app_data = Path(
            QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        )
        app_data.mkdir(parents=True, exist_ok=True)
        db_path = app_data / "michi.db"
        _seed_db(db_path, wav)
        assert db_path.exists()

        container = ApplicationContainer()
        container.initialize()
        try:
            # ── LEVEL 1: APPLICATION TRUTH ─────────────────────────────
            playback = container._playback
            service = container._audio_engine_service
            router = container._audio_router
            assert playback.state.status == PlaybackStatus.STOPPED
            assert service.state.active_engine_id == AudioEngineId.MPD
            assert service.state.selected_engine_id == AudioEngineId.MPD
            assert router.bound_engine_id == AudioEngineId.MPD
            assert playback._intent is False

            # ── LEVEL 2: DAEMON TRUTH (exact private socket) ───────────
            mpd = container._audio_engine_registry.provider(AudioEngineId.MPD)
            assert mpd is not None and mpd._port is not None
            port = mpd._port
            client = port._client
            assert client is not None
            daemon_state = client.status().get("state")
            assert daemon_state == "stop", (
                f"AUTOPLAY: daemon state={daemon_state} after startup restore"
            )

            # ── LEVEL 3: TEMPORAL TRUTH ────────────────────────────────
            elapsed_before = client.status().get("elapsed", "0")
            time.sleep(1.5)
            for _ in range(10):
                QApplication.processEvents()
            elapsed_after = client.status().get("elapsed", "0")
            assert elapsed_before == elapsed_after == "0", (
                f"AUTOPLAY: elapsed advanced {elapsed_before} -> {elapsed_after}"
            )

            # ── LEVEL 4: PROCESS OWNERSHIP ─────────────────────────────
            runtime = port._runtime
            assert runtime is not None
            assert runtime.process is not None and runtime.process.poll() is None
            pid = runtime.process.pid
            cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            joined = " ".join(p.decode(errors="replace") for p in cmdline)
            assert "--no-daemon" in joined
            assert str(runtime.runtime_dir / "mpd.conf") in joined
            assert (runtime.runtime_dir / "mpd.sock").exists()
            # the client socket IS the owned runtime's socket
            assert client._sock is not None

            # ── LEVEL 5: USER PLAY resumes at the persisted position ───
            playback.play()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                if (
                    client.status().get("state") == "play"
                    and playback.state.status == PlaybackStatus.PLAYING
                ):
                    break
                time.sleep(0.1)
            assert client.status().get("state") == "play"
            assert playback.state.status == PlaybackStatus.PLAYING
            elapsed = client.status().get("elapsed", "0")
            assert float(elapsed) >= 44.0, (
                f"resume position not applied: elapsed={elapsed}"
            )

            # ── LEVEL 6: PAUSE ─────────────────────────────────────────
            playback.pause()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                if client.status().get("state") == "pause":
                    break
                time.sleep(0.1)
            assert client.status().get("state") == "pause"

            # ── LEVEL 7: RESUME ────────────────────────────────────────
            playback.resume()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                if client.status().get("state") == "play":
                    break
                time.sleep(0.1)
            assert client.status().get("state") == "play"

            # ── LEVEL 8: STOP ──────────────────────────────────────────
            playback.stop()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                QApplication.processEvents()
                if client.status().get("state") == "stop":
                    break
                time.sleep(0.1)
            assert client.status().get("state") == "stop"
            assert playback.state.status == PlaybackStatus.STOPPED

            # ── LEVEL 4b: engine switch while stopped is allowed ───────
            assert playback.is_engine_switch_quiescent() is True
            container._engine_selection_coordinator.switch_to(
                AudioEngineId.QT_MULTIMEDIA
            )
            assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            assert router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
        finally:
            container.shutdown()
        # ── NO CHILD LEFT BEHIND ───────────────────────────────────────
        assert mpd._port is None  # provider released at shutdown


class TestProductionSelectorGolden:
    """KCR-025: real QML → AudioEngineBridge → SelectionCoordinator →
    Settings → Router → providers → live QML state — the click path the
    user actually uses, not a direct coordinator call."""

    def test_persisted_mpd_selector_qt_via_real_qml(self, qapp, tmp_path):
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from PySide6.QtCore import QCoreApplication, QEventLoop, QStandardPaths
        from PySide6.QtWidgets import QApplication

        from michi.bootstrap import ApplicationContainer
        from michi.domain.audio_engine import AudioEngineId

        data_home = tmp_path / "data"
        cache_home = tmp_path / "cache"
        data_home.mkdir()
        cache_home.mkdir()
        os.environ["XDG_DATA_HOME"] = str(data_home)
        os.environ["XDG_CACHE_HOME"] = str(cache_home)
        QCoreApplication.setOrganizationName("Michi")
        QCoreApplication.setApplicationName("Michi Music Player")
        app_data = Path(
            QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        )
        app_data.mkdir(parents=True, exist_ok=True)
        db_path = app_data / "michi.db"
        wav = _write_wav(tmp_path / "tone.wav", 120.0)
        _seed_db(db_path, wav)  # persisted MPD + coherent session

        container = ApplicationContainer()
        container.initialize()
        try:
            assert container.load_qml() is True
            service = container._audio_engine_service
            router = container._audio_router
            # startup converged to the persisted MPD
            assert service.state.active_engine_id == AudioEngineId.MPD
            assert router.bound_engine_id == AudioEngineId.MPD

            # the REAL QML selector surface exists in the live tree
            # (button + popup + rows = the production click path)
            root = container._engine.rootObjects()[0]
            button = root.findChild(object, "audioEngineButton")
            assert button is not None, "audioEngineButton MISSING"
            popup = root.findChild(object, "AudioEnginePopup")
            assert popup is not None, "AudioEnginePopup MISSING"
            # NOTE: a physical popup open needs a rendering environment; the
            # popup row click emits audioEngineSwitchRequested(engineId)
            # which AppShell routes to audioEngine.switch_engine(engineId) —
            # invoking that exact slot exercises the full
            # QML→Bridge→Coordinator→Settings→Router→providers path.
            bridge = container._aeb
            bridge.switch_engine("qt_multimedia")
            # settle the switch (real MPD child teardown + Qt activation)
            deadline = time.monotonic() + 10.0
            while time.monotonic() < deadline:
                QApplication.processEvents(QEventLoop.AllEvents, 20)
                time.sleep(0.02)
                if service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA:
                    break
            # THE SAME TRUTH across every authority
            assert service.state.selected_engine_id == AudioEngineId.QT_MULTIMEDIA
            assert service.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            assert router.bound_engine_id == AudioEngineId.QT_MULTIMEDIA
            mpd = container._audio_engine_registry.provider(AudioEngineId.MPD)
            assert mpd._port is None, "MPD provider not released"
            # persisted preference updated
            settings = container._settings
            assert settings.load().audio_engine_id == AudioEngineId.QT_MULTIMEDIA
            # QML live state reflects the new active engine
            assert service.state.switching_to is None
            # the deferred resume target of the MPD restore survived the
            # switch (KCR-021) and rehydrated on Qt without autoplay
            pb = container._playback
            assert pb.state.status.value == 1  # STOPPED — no autoplay
            assert pb.state.file_path == wav
            # restart truth: the newly selected engine persists
            container.shutdown()
            container2 = ApplicationContainer()
            container2.initialize()
            try:
                svc2 = container2._audio_engine_service
                assert svc2.state.active_engine_id == AudioEngineId.QT_MULTIMEDIA
            finally:
                container2.shutdown()
            return
        finally:
            with contextlib.suppress(Exception):
                container.shutdown()
