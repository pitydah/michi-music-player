"""M11.3D — managed MPD runtime tests (deterministic, fake process)."""

import signal
import subprocess
import time
from pathlib import Path

import pytest

from michi.infrastructure.audio_engines.mpd import (
    MpdProtocolError,
    _ManagedMpdRuntime,
    _pick_runtime_parent,
    _render_mpd_conf,
)


class _FakeProcess:
    """Popen fake: simula el arranque de MPD leyendo la config generada y
    creando el archivo de socket privado (el protocolo real ya está
    sellado en test_mpd_protocol.py; aquí se prueba el LIFECYCLE)."""

    instances: list["_FakeProcess"] = []

    # configuración por test
    exit_on_start = False
    create_socket = True

    def __init__(self, args, **kwargs):
        self.args = args
        self.returncode = None
        self.stderr = None
        self._killed = False
        self._term = False
        self._socket_path = None
        conf_path = args[-1]
        if _FakeProcess.create_socket:
            for line in Path(conf_path).read_text(encoding="utf-8").splitlines():
                if line.startswith("bind_to_address "):
                    self._socket_path = line.split(" ", 1)[1]
                    Path(self._socket_path).touch()
        _FakeProcess.instances.append(self)

    def poll(self):
        if _FakeProcess.exit_on_start and not self._killed:
            self.returncode = 1
            return 1
        return self.returncode

    def send_signal(self, sig):
        if sig == signal.SIGTERM:
            self._term = True
            self.returncode = 0  # el hijo "termina" limpiamente
        elif sig == signal.SIGKILL:
            self._killed = True
            self.returncode = 9

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self._killed = True
        self.returncode = 9

    def terminated(self):
        return self._term

    def killed(self):
        return self._killed


@pytest.fixture
def fake_runtime(monkeypatch, tmp_path):
    """Runtime con Popen fake y XDG_RUNTIME_DIR apuntando a tmp_path.

    El handshake usa un cliente fake: el protocolo real está sellado en
    test_mpd_protocol.py; aquí se prueba el LIFECYCLE del proceso."""
    monkeypatch.setattr(
        "michi.infrastructure.audio_engines.mpd.subprocess.Popen", _FakeProcess
    )
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def connect(self):
            pass

        def status(self):
            return {}

        def close(self):
            pass

    monkeypatch.setattr(
        "michi.infrastructure.audio_engines.mpd._MpdProtocolClient", FakeClient
    )
    _FakeProcess.instances.clear()
    _FakeProcess.exit_on_start = False
    _FakeProcess.create_socket = True
    return _FakeProcess


class TestRuntimeDirectory:
    def test_r1_unique_runtime_dir(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime()
        runtime._start_inner()
        assert runtime.runtime_dir is not None
        assert str(runtime.runtime_dir).startswith(str(tmp_path / "michi-mpd-"))
        assert (runtime.runtime_dir / "mpd.conf").exists()
        runtime.close()

    def test_r1_two_runtimes_differ(self, fake_runtime, tmp_path):
        a = _ManagedMpdRuntime()
        b = _ManagedMpdRuntime()
        a._start_inner()
        b._start_inner()
        assert a.runtime_dir != b.runtime_dir
        assert a.socket_path != b.socket_path
        a.close()
        b.close()

    def test_r2_config_uses_only_private_paths(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime()
        runtime._start_inner()
        conf = (runtime.runtime_dir / "mpd.conf").read_text(encoding="utf-8")
        assert "mpd.sock" in conf
        assert "/etc/mpd.conf" not in conf
        assert "/run/mpd" not in conf
        assert "auto_update no" in conf
        runtime.close()


class TestSpawn:
    def test_r3_spawn_uses_no_daemon(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime()
        runtime._start_inner()
        args = _FakeProcess.instances[0].args
        assert "--no-daemon" in args
        assert "--stderr" in args
        runtime.close()

    def test_r4_socket_startup_bounded(self, fake_runtime, tmp_path):
        _FakeProcess.create_socket = False  # el socket nunca aparece
        runtime = _ManagedMpdRuntime(startup_timeout=0.2)
        # timeout determinístico rápido
        start = time.monotonic()
        with pytest.raises(MpdProtocolError, match="socket"):
            runtime.start()
        assert time.monotonic() - start < 5.0
        assert runtime.runtime_dir is None  # limpieza total

    def test_r5_child_exits_during_startup_fails(self, fake_runtime, tmp_path):
        _FakeProcess.exit_on_start = True
        runtime = _ManagedMpdRuntime(startup_timeout=0.5)
        with pytest.raises(MpdProtocolError, match="exited during startup"):
            runtime.start()
        assert runtime.runtime_dir is None
        assert runtime.process is None


class TestShutdown:
    def _started(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime()
        runtime._start_inner()
        return runtime, _FakeProcess.instances[0]

    def test_r7_close_terms_and_reaps(self, fake_runtime, tmp_path):
        runtime, proc = self._started(fake_runtime, tmp_path)
        runtime_dir = runtime.runtime_dir
        runtime.close()
        assert proc.terminated() is True
        assert proc.poll() is not None  # reaped
        assert not runtime_dir.exists()  # artefactos removidos
        assert runtime.runtime_dir is None
        assert runtime.socket_path is None

    def test_r9_close_idempotent(self, fake_runtime, tmp_path):
        runtime, _ = self._started(fake_runtime, tmp_path)
        runtime.close()
        runtime.close()  # idempotente
        runtime.close()
        assert runtime.process is None

    def test_r8_kill_fallback_on_term_timeout(
        self, fake_runtime, tmp_path, monkeypatch
    ):
        runtime, proc = self._started(fake_runtime, tmp_path)

        def stuck_wait(timeout=None):
            raise subprocess.TimeoutExpired("mpd", timeout)

        monkeypatch.setattr(proc, "wait", stuck_wait)
        runtime.close()
        assert proc.killed() is True  # SIGKILL fallback
        assert proc.poll() is not None

    def test_r12_no_external_adoption(self, fake_runtime, tmp_path):
        # el runtime SIEMPRE crea paths privados únicos bajo XDG_RUNTIME_DIR
        # y nunca toca /run/mpd ni /etc/mpd.conf (verificado en r2); un
        # arranque que no produce socket propio falla cerrado
        _FakeProcess.create_socket = False
        runtime = _ManagedMpdRuntime(startup_timeout=0.2)
        with pytest.raises(MpdProtocolError):
            runtime.start()
        assert runtime.process is None
        assert runtime.runtime_dir is None


class TestConfigRender:
    def test_conf_private_paths_only(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(runtime_dir, runtime_dir / "music")
        assert f"bind_to_address {runtime_dir / 'mpd.sock'}" in conf
        assert "music_directory" in conf

    def test_c1a_production_config_has_no_null_output(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(runtime_dir, runtime_dir / "music")
        assert "null" not in conf  # producción: MPD elige su salida

    def test_c1b_test_config_supports_null_output(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(runtime_dir, runtime_dir / "music", null_output=True)
        assert "null" in conf
        assert "audio_output" in conf

    def test_c1c_production_runtime_default_no_null(self, fake_runtime, tmp_path):

        # el runtime productivo usa el default null_output=False
        runtime = _ManagedMpdRuntime()
        runtime._start_inner()
        conf = (runtime.runtime_dir / "mpd.conf").read_text(encoding="utf-8")
        assert "null" not in conf
        runtime.close()

    def test_runtime_parent_prefers_xdg(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        assert _pick_runtime_parent() == tmp_path

    def test_runtime_parent_falls_back(self, monkeypatch):
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        import tempfile

        assert _pick_runtime_parent() == Path(tempfile.gettempdir())
