"""M11.3D — managed MPD runtime tests (deterministic, fake process)."""

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from michi.infrastructure.audio_engines.mpd import (
    MpdOutputPluginDiscoveryError,
    MpdProtocolError,
    _discover_mpd_output_plugins,
    _ManagedMpdRuntime,
    _parse_mpd_output_plugins,
    _pick_runtime_parent,
    _render_mpd_conf,
    _select_default_mpd_output_plugin,
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
                if line.startswith('bind_to_address "'):
                    self._socket_path = line.split('"')[1]
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
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        runtime._start_inner()
        assert runtime.runtime_dir is not None
        assert str(runtime.runtime_dir).startswith(str(tmp_path / "michi-mpd-"))
        assert (runtime.runtime_dir / "mpd.conf").exists()
        runtime.close()

    def test_r1_two_runtimes_differ(self, fake_runtime, tmp_path):
        a = _ManagedMpdRuntime(output_plugin="alsa")
        b = _ManagedMpdRuntime(output_plugin="alsa")
        a._start_inner()
        b._start_inner()
        assert a.runtime_dir != b.runtime_dir
        assert a.socket_path != b.socket_path
        a.close()
        b.close()

    def test_r2_config_uses_only_private_paths(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        runtime._start_inner()
        conf = (runtime.runtime_dir / "mpd.conf").read_text(encoding="utf-8")
        assert "mpd.sock" in conf
        assert "/etc/mpd.conf" not in conf
        assert "/run/mpd" not in conf
        assert 'auto_update "no"' in conf
        runtime.close()


class TestSpawn:
    def test_r3_spawn_uses_no_daemon(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        runtime._start_inner()
        args = _FakeProcess.instances[0].args
        assert "--no-daemon" in args
        assert "--stderr" in args
        runtime.close()

    def test_r4_socket_startup_bounded(self, fake_runtime, tmp_path):
        _FakeProcess.create_socket = False  # el socket nunca aparece
        runtime = _ManagedMpdRuntime(startup_timeout=0.2, output_plugin="alsa")
        # timeout determinístico rápido
        start = time.monotonic()
        with pytest.raises(MpdProtocolError, match="socket"):
            runtime.start()
        assert time.monotonic() - start < 5.0
        assert runtime.runtime_dir is None  # limpieza total

    def test_r5_child_exits_during_startup_fails(self, fake_runtime, tmp_path):
        _FakeProcess.exit_on_start = True
        runtime = _ManagedMpdRuntime(startup_timeout=0.5, output_plugin="alsa")
        with pytest.raises(MpdProtocolError, match="exited during startup"):
            runtime.start()
        assert runtime.runtime_dir is None
        assert runtime.process is None


class TestShutdown:
    def _started(self, fake_runtime, tmp_path):
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
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
        """AR-06: TERM timeout → KILL fallback → proven death → release."""
        runtime, proc = self._started(fake_runtime, tmp_path)

        real_wait = proc.wait
        calls = {"n": 0}

        def wait_with_timeout(timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise subprocess.TimeoutExpired("mpd", timeout)
            return real_wait(timeout)

        monkeypatch.setattr(proc, "wait", wait_with_timeout)
        runtime_dir = runtime.runtime_dir
        runtime.close()
        assert proc.killed() is True  # SIGKILL fallback
        assert proc.poll() is not None  # death proven → released
        assert runtime.process is None
        assert not runtime_dir.exists()  # artifacts removed after death

    def test_r8b_close_retains_handle_when_child_wont_die(
        self, fake_runtime, tmp_path, monkeypatch
    ):
        """AR-06: if the child refuses termination (TERM+KILL timeouts) the
        handle, runtime dir and socket are RETAINED and close raises an
        explicit ownership error — never a fabricated clean release."""
        from michi.infrastructure.audio_engines.mpd import (
            MpdOwnershipTeardownError,
        )

        runtime, proc = self._started(fake_runtime, tmp_path)

        def stuck_wait(timeout=None):
            raise subprocess.TimeoutExpired("mpd", timeout)

        monkeypatch.setattr(proc, "wait", stuck_wait)
        runtime_dir = runtime.runtime_dir
        socket_path = runtime.socket_path
        with pytest.raises(
            MpdOwnershipTeardownError, match="ownership handle retained"
        ):
            runtime.close()
        # ownership RETAINED: handle, runtime dir, socket, diagnostics
        assert runtime.process is proc
        assert runtime.runtime_dir == runtime_dir
        assert runtime.socket_path == socket_path
        assert runtime_dir.exists()
        # a retry can still be attempted (close is not permanently stuck)
        assert runtime.closed is False

    def test_r12_no_external_adoption(self, fake_runtime, tmp_path):
        # el runtime SIEMPRE crea paths privados únicos bajo XDG_RUNTIME_DIR
        # y nunca toca /run/mpd ni /etc/mpd.conf (verificado en r2); un
        # arranque que no produce socket propio falla cerrado
        _FakeProcess.create_socket = False
        runtime = _ManagedMpdRuntime(startup_timeout=0.2, output_plugin="alsa")
        with pytest.raises(MpdProtocolError):
            runtime.start()
        assert runtime.process is None
        assert runtime.runtime_dir is None


class TestConfigRender:
    def test_conf_private_paths_only(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="alsa"
        )
        assert f'bind_to_address "{runtime_dir / "mpd.sock"}"' in conf
        assert "music_directory" in conf

    def test_c1a_production_config_has_no_null_output(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="alsa"
        )
        assert "null" not in conf  # producción: salida explícita, nunca null

    def test_c1b_test_config_supports_null_output(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(runtime_dir, runtime_dir / "music", null_output=True)
        assert "null" in conf
        assert "audio_output" in conf

    def test_c1c_production_runtime_default_no_null(self, fake_runtime, tmp_path):

        # el runtime productivo usa plugin explícito (nunca implícito)
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
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


class TestOutputPluginDiscovery:
    """M11.3-UI-R2 — deterministic output-plugin discovery + selection.

    The implicit MPD output autodetection (which selected an ALSA hardware
    mixer "PCM" missing on the default device) is REPLACED by an explicit
    compatibility output policy: pipewire > pulse > alsa, software mixer.
    """

    VERSION_ALL = (
        "Output plugins:\n"
        " shout null fifo pipe alsa ao oss openal solaris pipewire pulse "
        "jack httpd snapcast recorder\n"
    )
    VERSION_PULSE_ALSA = "Output plugins:\n shout null fifo alsa pulse\n"
    VERSION_ALSA_ONLY = "Output plugins:\n shout null fifo alsa\n"
    VERSION_NONE = "Output plugins:\n shout null fifo jack httpd\n"

    def test_parser_full_fixture(self):
        plugins = _parse_mpd_output_plugins(self.VERSION_ALL)
        assert "pipewire" in plugins
        assert "pulse" in plugins
        assert "alsa" in plugins

    def test_parser_ignores_other_sections(self):
        plugins = _parse_mpd_output_plugins(
            "Decoder plugins:\n [mad] mp3\n\n" + self.VERSION_ALL
        )
        assert "mad" not in plugins
        assert "mp3" not in plugins

    def test_parser_no_output_section(self):
        assert _parse_mpd_output_plugins("nothing here") == set()

    def test_selection_preference_pipewire_first(self):
        assert (
            _select_default_mpd_output_plugin({"alsa", "pipewire", "pulse"})
            == "pipewire"
        )

    def test_selection_pulse_over_alsa(self):
        assert _select_default_mpd_output_plugin({"alsa", "pulse"}) == "pulse"

    def test_selection_alsa_fallback(self):
        assert _select_default_mpd_output_plugin({"alsa"}) == "alsa"

    def test_selection_no_supported_plugin_raises(self):
        with pytest.raises(
            MpdOutputPluginDiscoveryError, match="no supported default audio output"
        ):
            _select_default_mpd_output_plugin({"null", "fifo", "jack"})

    def test_discovery_uses_argv_not_shell(self, monkeypatch):
        """E: never shell=True; bounded; deterministic parse."""
        captured = {}

        def fake_run(args, **kwargs):
            captured["args"] = args
            captured["shell"] = kwargs.get("shell", False)
            assert args == ["mpd", "--version"]
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=("Music Player Daemon 0.24.14\n\n" + self.VERSION_ALL).encode(),
                stderr=b"",
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        plugins = _discover_mpd_output_plugins("mpd")
        assert captured["shell"] is False
        assert plugins == {
            "shout",
            "null",
            "fifo",
            "pipe",
            "alsa",
            "ao",
            "oss",
            "openal",
            "solaris",
            "pipewire",
            "pulse",
            "jack",
            "httpd",
            "snapcast",
            "recorder",
        }

    def test_discovery_timeout_deterministic(self, monkeypatch):
        def fake_run(args, **kwargs):
            raise subprocess.TimeoutExpired(args[0], kwargs.get("timeout", 5.0))

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MpdOutputPluginDiscoveryError, match="timed out"):
            _discover_mpd_output_plugins("mpd", timeout=0.5)

    def test_discovery_missing_executable_truthful(self, monkeypatch):
        def fake_run(args, **kwargs):
            raise FileNotFoundError("mpd")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MpdOutputPluginDiscoveryError, match="not found"):
            _discover_mpd_output_plugins("mpd")

    def test_discovery_nonzero_exit_truthful(self, monkeypatch):
        def fake_run(args, **kwargs):
            return subprocess.CompletedProcess(args, 3, stdout=b"", stderr=b"oops")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(MpdOutputPluginDiscoveryError, match="exit code 3"):
            _discover_mpd_output_plugins("mpd")


class TestProductionOutputPolicy:
    """M11.3-UI-R2 — generated production config contract (section 11.B)."""

    def test_production_config_explicit_single_output(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="pipewire"
        )
        assert conf.count("audio_output {") == 1
        assert 'type\t\t"pipewire"' in conf
        assert 'name\t\t"Michi MPD Default"' in conf

    def test_production_config_software_mixer(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="alsa"
        )
        assert 'mixer_type\t"software"' in conf

    def test_production_config_no_hardcoded_pcm(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="alsa"
        )
        assert "mixer_control" not in conf
        assert "PCM" not in conf

    def test_production_config_no_device_ids(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="alsa"
        )
        for forbidden in ("hw:", "device", "card", "mixer_control"):
            assert forbidden not in conf

    def test_production_config_no_audiophile_settings(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(
            runtime_dir, runtime_dir / "music", output_plugin="pipewire"
        )
        for forbidden in (
            "dsd",
            "DoP",
            "sample_rate",
            "format",
            "replaygain",
            "resampler",
            "dop",
            "exclusive",
        ):
            assert forbidden not in conf

    def test_production_config_forbids_implicit_output(self, tmp_path):
        """The pre-fix implicit behavior must be impossible now."""
        runtime_dir = tmp_path / "rt"
        with pytest.raises(ValueError, match="explicit output_plugin"):
            _render_mpd_conf(runtime_dir, runtime_dir / "music")

    def test_null_output_config_independent(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        conf = _render_mpd_conf(runtime_dir, runtime_dir / "music", null_output=True)
        assert "null" in conf
        assert "mixer_type" not in conf  # null output owns no mixer
        assert 'type\t\t"null"' in conf

    def test_null_and_plugin_mutually_exclusive(self, tmp_path):
        runtime_dir = tmp_path / "rt"
        with pytest.raises(ValueError, match="mutually exclusive"):
            _render_mpd_conf(
                runtime_dir,
                runtime_dir / "music",
                null_output=True,
                output_plugin="alsa",
            )


class TestPartialStartupCleanup:
    """R1-08: if subprocess.Popen raises before self._process is assigned,
    the partial runtime artifacts must still be cleaned (no leak)."""

    def test_popen_failure_cleans_partial_runtime(self, monkeypatch, tmp_path):
        import os

        from michi.infrastructure.audio_engines.mpd import (
            _ManagedMpdRuntime,
            _pick_runtime_parent,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        real_popen = subprocess.Popen

        def exploding_popen(*args, **kwargs):
            raise OSError("spawn failed")

        monkeypatch.setattr(subprocess, "Popen", exploding_popen)
        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        with pytest.raises(OSError, match="spawn failed"):
            runtime.start()
        # first-error-wins: the ORIGINAL error propagates
        # no process, no runtime dir, no socket, stderr log closed
        assert runtime.process is None
        assert runtime.runtime_dir is None
        assert runtime.socket_path is None
        leftovers = list(tmp_path.glob("michi-mpd-*"))
        assert leftovers == [], f"partial runtime leaked: {leftovers}"

    def test_close_case_b_cleans_artifacts_without_process(self, tmp_path):
        from michi.infrastructure.audio_engines.mpd import (
            _ManagedMpdRuntime,
            _render_mpd_conf,
        )

        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        base = tmp_path / "michi-mpd-1234-abc"
        base.mkdir()
        (base / "music").mkdir()
        (base / "playlists").mkdir()
        (base / "mpd.conf").write_text(
            _render_mpd_conf(base, base / "music", output_plugin="alsa")
        )
        (base / "mpd.sock").touch()
        runtime.runtime_dir = base
        runtime.socket_path = str(base / "mpd.sock")
        runtime._stderr_log = (base / "mpd.stderr.log").open("wb")
        # NO process ever assigned (partial startup)
        runtime.close()
        assert runtime.process is None
        assert runtime.runtime_dir is None
        assert not base.exists()


class TestOrphanRecoveryContract:
    """R1-09: conservative orphan recovery — multi-fact validation; never
    touches anything that cannot be PROVEN Michi-owned."""

    def _make_stale_dir(self, tmp_path, name="michi-mpd-9999-dead", conf_ok=True):
        from michi.infrastructure.audio_engines.mpd import _render_mpd_conf

        base = tmp_path / name
        base.mkdir()
        (base / "music").mkdir()
        (base / "playlists").mkdir()
        if conf_ok:
            (base / "mpd.conf").write_text(
                _render_mpd_conf(base, base / "music", output_plugin="alsa")
            )
        else:
            (base / "mpd.conf").write_text("not a michi config at all")
        return base

    def test_f_stale_dir_no_process_artifacts_removed(self, tmp_path, monkeypatch):
        import os

        from michi.infrastructure.audio_engines.mpd import (
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path)
        results = recover_stale_michi_mpd_runtimes()
        assert len(results) == 1
        assert results[0]["action"] == "stale artifacts removed (no live process)"
        assert not base.exists()

    def test_d_malformed_config_not_touched(self, tmp_path, monkeypatch):
        from michi.infrastructure.audio_engines.mpd import (
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path, conf_ok=False)
        results = recover_stale_michi_mpd_runtimes()
        assert results[0]["action"].startswith("skipped")
        assert base.exists()  # NOT touched

    def test_c_foreign_uid_dir_not_touched(self, tmp_path, monkeypatch):
        import os

        from michi.infrastructure.audio_engines.mpd import (
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path)
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd.os.stat",
            lambda path, **kwargs: type(
                "S", (), {"st_uid": os.getuid() + 1, "st_mode": 0o40700}
            )(),
        )
        results = recover_stale_michi_mpd_runtimes()
        assert results[0]["action"] == "skipped: foreign UID"
        assert base.exists()

    def test_e_current_live_runtime_not_touched(self, tmp_path, monkeypatch):
        """A live Michi-owned runtime (parent alive + michi owner) is never
        recovered."""
        import threading

        from michi.infrastructure.audio_engines.mpd import (
            _read_proc_cmdline,
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path)
        # a FAKE live process claiming to own this conf, with a live
        # michi-owner parent → must be skipped
        fake_pid = 424242
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._mpd_process_for_conf",
            lambda conf: fake_pid,
        )
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._read_proc_uid",
            lambda pid: 1000,
        )
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._read_proc_ppid",
            lambda pid: 1,
        )
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._pid_alive",
            lambda pid: pid == 1,
        )
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._looks_like_michi_owner",
            lambda pid: True,
        )
        results = recover_stale_michi_mpd_runtimes()
        assert results[0]["action"] == "skipped: live Michi owner"
        assert base.exists()

    def _spoof_mpd_process(self, tmp_path) -> subprocess.Popen:
        """A REAL long-lived process standing in for a live orphan PID
        (termination is exercised against the REAL pid)."""
        helper = tmp_path / "michi_mpd_fake.py"
        helper.write_text(
            "#!/usr/bin/env python3" + chr(10)
            + "import time" + chr(10) + "time.sleep(600)" + chr(10),
            encoding="utf-8",
        )
        helper.chmod(0o700)
        return subprocess.Popen(
            [str(helper)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def test_a_valid_stale_orphan_terminated(self, tmp_path, monkeypatch):
        """Validated stale orphan: exact PID terminated, exact dir removed.
        The /proc cmdline matcher is injected (real MPD shape); the
        TERM/KILL/proof/removal lifecycle runs against the REAL pid."""
        import os

        from michi.infrastructure.audio_engines.mpd import (
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path)
        conf = base / "mpd.conf"
        proc = self._spoof_mpd_process(tmp_path)
        try:
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._mpd_process_for_conf",
                lambda conf_path: proc.pid,
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._read_proc_uid",
                lambda pid: os.getuid(),
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._read_proc_ppid",
                lambda pid: None,  # parent gone/unknown → stale
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._pid_alive",
                lambda pid: pid == proc.pid,
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._looks_like_michi_owner",
                lambda pid: False,
            )
            results = recover_stale_michi_mpd_runtimes()
            assert results[0]["action"] == "orphan terminated"
            assert results[0]["pid"] == proc.pid
            assert not base.exists()
            proc.wait(timeout=5)
            assert proc.poll() is not None  # REALLY terminated
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def test_b_system_mpd_like_process_not_touched(self, tmp_path, monkeypatch):
        """A process resembling system MPD (cmdline references a DIFFERENT
        conf) is never terminated — the dir is only artifact-cleaned."""
        import os

        from michi.infrastructure.audio_engines.mpd import (
            recover_stale_michi_mpd_runtimes,
        )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        base = self._make_stale_dir(tmp_path)
        proc = self._spoof_mpd_process(tmp_path)
        try:
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._mpd_process_for_conf",
                lambda conf_path: None,  # no process references THIS conf
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._read_proc_uid",
                lambda pid: os.getuid(),
            )
            monkeypatch.setattr(
                "michi.infrastructure.audio_engines.mpd._pid_alive",
                lambda pid: pid == proc.pid,
            )
            results = recover_stale_michi_mpd_runtimes()
            # no process matches THIS dir's conf → artifact-only cleanup of
            # the validated dir; the unrelated process is untouched
            assert results[0]["action"] == "stale artifacts removed (no live process)"
            assert proc.poll() is None  # system-like process SURVIVES
        finally:
            proc.kill()
            proc.wait(timeout=5)

    def test_cmdline_matcher_requires_michi_shape(self, tmp_path, monkeypatch):
        """The /proc cmdline matcher only accepts the exact MPD no-daemon
        shape referencing the conf (injected cmdlines)."""
        from michi.infrastructure.audio_engines.mpd import (
            _mpd_process_for_conf,
        )

        conf = tmp_path / "mpd.conf"
        fake_pid = os.getpid()  # a REAL /proc entry (the test process)
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._read_proc_cmdline",
            lambda pid: ["mpd", "--no-daemon", "--stderr", str(conf)]
            if pid == fake_pid
            else None,
        )
        assert _mpd_process_for_conf(str(conf)) == fake_pid
        # different conf → no match
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._read_proc_cmdline",
            lambda pid: ["mpd", "--no-daemon", "--stderr", "/etc/mpd.conf"]
            if pid == fake_pid
            else None,
        )
        assert _mpd_process_for_conf(str(conf)) is None
        # no --no-daemon (daemonized/system MPD) → no match
        monkeypatch.setattr(
            "michi.infrastructure.audio_engines.mpd._read_proc_cmdline",
            lambda pid: ["mpd", "--stderr", str(conf)]
            if pid == fake_pid
            else None,
        )
        assert _mpd_process_for_conf(str(conf)) is None
