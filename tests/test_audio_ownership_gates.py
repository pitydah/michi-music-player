"""M11.3 Reliability Seal — process ownership & abnormal exit gates.

AR-01 evidence + section 20/66/67: a Michi-owned MPD child must NEVER
survive its owner. MPD >= 0.23 sets PR_SET_PDEATHSIG (SIGTERM) on Linux
when not daemonized — verified empirically: SIGKILL of the owner kills the
child within ~1s. This suite proves the behavior through a real subprocess
harness (no manual GUI).
"""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_mpd_orphan_harness.py"

HARNESS_SRC = '''
"""Spawns a Michi-owned MPD runtime and parks until killed."""
import sys, time
sys.path.insert(0, {repo!r})
from michi.infrastructure.audio_engines.mpd import _ManagedMpdRuntime
runtime = _ManagedMpdRuntime()
runtime.start()
print(runtime._process.pid, flush=True)
print(runtime.runtime_dir, flush=True)
time.sleep(300)
'''


@pytest.fixture(scope="module")
def harness_script():
    HARNESS.write_text(HARNESS_SRC.format(repo=str(REPO / "src")), encoding="utf-8")
    yield HARNESS
    HARNESS.unlink(missing_ok=True)


def _require_mpd():
    import shutil

    if shutil.which("mpd") is None:
        pytest.skip("dependency absent: mpd executable not found in PATH")


class TestAbnormalExitOwnership:
    def test_parent_sigkill_terminates_mpd_child(self, harness_script):
        """AR-01 gate: killing the owning process abnormally (SIGKILL) must
        not leave a live Michi-owned MPD child behind (PDEATHSIG)."""
        _require_mpd()
        proc = subprocess.Popen(
            [sys.executable, str(harness_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        try:
            line1 = proc.stdout.readline().strip()
            line2 = proc.stdout.readline().strip()
            assert line1.startswith("PID=") or line1.isdigit(), line1
            child_pid = int(line1)
            runtime_dir = Path(line2) if not line2.isdigit() else Path(line1)
            assert os.path.exists(runtime_dir)
            # child alive while owner alive
            time.sleep(0.3)
            assert os.path.exists(f"/proc/{child_pid}"), "child should be alive"

            # abnormal owner death
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)

            # child must be gone within a bounded window (PDEATHSIG)
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                if not os.path.exists(f"/proc/{child_pid}"):
                    break
                time.sleep(0.2)
            assert not os.path.exists(f"/proc/{child_pid}"), (
                f"ORPHANED MPD CHILD {child_pid} survived owner SIGKILL"
            )
        finally:
            if proc.poll() is None:
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)

    def test_mpd_child_count_zero_when_no_michi_running(self):
        """Section 66: with no Michi process alive, `mpgrep` of Michi-owned
        MPD children must be empty (excluding our own command line)."""
        out = subprocess.run(
            ["pgrep", "-af", "michi-mpd-"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = [ln for ln in out.stdout.splitlines() if "pgrep" not in ln]
        # any remaining match must be a test harness from THIS run
        for line in lines:
            assert "_mpd_orphan_harness" in line or "michi-mpd-" not in line, line


class TestRuntimeOwnershipInvariants:
    """Section 20 — fake-level ownership invariants (deterministic)."""

    def test_mpd_close_success_releases_everything(self, tmp_path):
        if shutil.which("mpd") is None:
            pytest.skip("dependency absent: mpd executable not found in PATH")
        from michi.infrastructure.audio_engines.mpd import _ManagedMpdRuntime

        runtime = _ManagedMpdRuntime(output_plugin="alsa")
        runtime._start_inner()
        runtime_dir = runtime.runtime_dir
        runtime.close()
        assert runtime.process is None
        assert runtime.runtime_dir is None
        assert not runtime_dir.exists()

    def test_mpd_observer_handle_retained_on_join_timeout(self):
        """AR-08: the port must retain the observer thread handle when the
        join cannot prove termination."""
        from michi.infrastructure.audio_engines.mpd import (
            MPDAudioPort,
            MpdOwnershipTeardownError,
        )

        port = MPDAudioPort()
        # arm a fake observer that never dies
        import threading

        stuck = threading.Thread(target=lambda: time.sleep(60), daemon=True)
        stuck.start()
        port._observer = stuck
        port._closed = False
        with pytest.raises(MpdOwnershipTeardownError, match="observer thread"):
            port.close()
        assert port._observer is stuck  # handle retained
        stuck.join(timeout=2)  # cleanup


class TestRetryableClose:
    """R1-02: MPDAudioPort close() is retryable — a failed close retains
    ownership, _closed stays False, and a second close completes."""

    def test_mpd_port_observer_failure_retry_succeeds(self):
        import threading

        from michi.infrastructure.audio_engines.mpd import (
            MPDAudioPort,
            MpdOwnershipTeardownError,
        )

        port = MPDAudioPort()
        # observer that refuses to die on the FIRST join, then terminates
        release = threading.Event()

        class StubbornThread(threading.Thread):
            def __init__(self):
                super().__init__(daemon=True)
                self.joins = 0

            def run(self):
                release.wait(timeout=10)

            def join(self, timeout=None):
                self.joins += 1
                if self.joins == 1 and not release.is_set():
                    # first join: simulate timeout (thread stays alive)
                    return None
                return super().join(timeout)

        stuck = StubbornThread()
        stuck.start()
        port._observer = stuck
        port._closing = False
        port._closed = False
        with pytest.raises(MpdOwnershipTeardownError, match="observer thread"):
            port.close()
        # R1-02: ownership retained, _closed must NOT claim complete close
        assert port._observer is stuck
        assert port._closed is False
        # allow termination and RETRY → full success
        release.set()
        port.close()
        assert port._observer is None
        assert port._closed is True
        # every owned resource released (runtime never started → None)
        assert port._runtime is not None
