"""ProcessController — centralizes external process management.

API: spawn, stdout, stderr, progress, PID, timeout, terminate, kill, cleanup.
Thread-safe, never blocks UI thread. No subprocess.run() in Qt slots.

Sync path (``spawn_sync``/``terminate_sync``/``is_alive``/``cleanup_sync``):
for daemon-style processes driven from synchronous call sites (e.g.
``MpdServiceManager``), a tracked :class:`SyncManagedProcess` is registered in
a separate registry with its own threading lock — the sync and async paths
never share bookkeeping.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Any

logger = logging.getLogger("michi.process_controller")


class ManagedProcess:
    def __init__(
        self,
        pid: int,
        cmd: str,
        args: list[str],
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ):
        self.pid = pid
        self.cmd = cmd
        self.args = list(args)
        self.cwd = cwd
        self.env = dict(env or {})
        self.started_at = time.monotonic()
        self._exit_status: int | None = None
        self._stdout_lines: list[str] = []
        self._stderr_lines: list[str] = []
        self._cancelled = False
        self._process: asyncio.subprocess.Process | None = None

    def exit_status(self) -> int | None:
        return self._exit_status

    def stdout(self) -> list[str]:
        return list(self._stdout_lines)

    def stderr(self) -> list[str]:
        return list(self._stderr_lines)

    def is_alive(self) -> bool:
        if not self._process:
            return False
        return self._process.returncode is None

    def cleanup(self):
        self._cancelled = True
        if self._process and self._process.returncode is None:
            import contextlib
            with contextlib.suppress(Exception):
                self._process.kill()
        self._exit_status = -1


class SyncManagedProcess:
    """A daemon-style subprocess tracked by the controller (sync API).

    Spawned with :meth:`ProcessController.spawn_sync`; terminated with
    :meth:`ProcessController.terminate_sync` (SIGTERM with a bounded wait,
    SIGKILL fallback) — callers must never terminate a PID that this instance
    did not spawn.
    """

    def __init__(self, pid: int, cmd: str, args: list[str],
                 cwd: str | None = None, env: dict[str, str] | None = None,
                 stdout=None, stderr=None):
        self.pid = pid
        self.cmd = cmd
        self.args = list(args)
        self.cwd = cwd
        self.env = dict(env or {})
        self.started_at = time.monotonic()
        self._proc: subprocess.Popen | None = None
        self._stdout = stdout
        self._stderr = stderr

    def attach(self, proc: subprocess.Popen) -> None:
        self._proc = proc

    def poll(self) -> int | None:
        if self._proc is None:
            return -1
        return self._proc.poll()

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def terminate(self, timeout: float = 5.0) -> bool:
        """SIGTERM with bounded wait; SIGKILL fallback. Own processes only."""
        if self._proc is None or self._proc.poll() is not None:
            return False
        try:
            self._proc.send_signal(signal.SIGTERM)
            self._proc.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            self._proc.kill()
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                return False
            return True
        except Exception:
            return False

    def kill(self) -> bool:
        if self._proc is None or self._proc.poll() is not None:
            return False
        try:
            self._proc.kill()
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        if self.is_alive():
            with contextlib.suppress(Exception):
                self._proc.kill()
        self._proc = None

    def summary(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "cmd": self.cmd,
            "args": list(self.args),
            "alive": self.is_alive(),
            "returncode": self.poll(),
            "started_at": self.started_at,
        }


class ProcessController:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._processes: dict[int, ManagedProcess] = {}
        self._counter = 0
        self._sync_lock = threading.Lock()
        self._sync_processes: dict[int, SyncManagedProcess] = {}

    async def spawn(
        self,
        cmd: str = "",
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        capture_stdout: bool = False,
    ) -> ManagedProcess:
        if not cmd:
            return ManagedProcess(pid=0, cmd="", args=[])
        all_args = [cmd] + (args or [])
        full_env = {**os.environ, **(env or {})}
        stdout_dest = asyncio.subprocess.PIPE if capture_stdout else asyncio.subprocess.DEVNULL
        proc = await asyncio.create_subprocess_exec(
            *all_args,
            cwd=cwd,
            env=full_env,
            stdout=stdout_dest,
            stderr=asyncio.subprocess.PIPE,
        )
        mp = ManagedProcess(
            pid=proc.pid,
            cmd=cmd,
            args=args or [],
            cwd=cwd,
            env=env,
        )
        mp._process = proc
        async with self._lock:
            self._counter += 1
            self._processes[proc.pid] = mp
        loop = asyncio.get_event_loop()
        if capture_stdout:
            loop.create_task(self._collect_stdout(proc, mp))
        loop.create_task(self._collect_stderr(proc, mp))
        loop.create_task(self._wait_exit(proc, mp))
        return mp

    async def _collect_stdout(self, proc: asyncio.subprocess.Process, mp: ManagedProcess):
        try:
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=300)
                if not line:
                    break
                mp._stdout_lines.append(line.decode("utf-8", errors="replace").rstrip())
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug("stdout collector: %s", e)

    async def _collect_stderr(self, proc: asyncio.subprocess.Process, mp: ManagedProcess):
        try:
            while True:
                line = await asyncio.wait_for(proc.stderr.readline(), timeout=300)
                if not line:
                    break
                mp._stderr_lines.append(line.decode("utf-8", errors="replace").rstrip())
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.debug("stderr collector: %s", e)

    async def _wait_exit(self, proc: asyncio.subprocess.Process, mp: ManagedProcess):
        try:
            returncode = await proc.wait()
            mp._exit_status = returncode
        except AttributeError:
            mp._exit_status = -1
        except Exception as e:
            logger.debug("wait exit: %s", e)
            mp._exit_status = -1

    async def stdout(self, pid: int) -> list[str]:
        mp = await self._get(pid)
        if not mp:
            return []
        return mp.stdout()

    async def stderr(self, pid: int) -> list[str]:
        mp = await self._get(pid)
        if not mp:
            return []
        return mp.stderr()

    async def terminate(self, pid: int) -> bool:
        mp = await self._get(pid)
        if not mp or not mp._process:
            return False
        try:
            mp._process.terminate()
            return True
        except Exception:
            return False

    async def kill(self, pid: int) -> bool:
        mp = await self._get(pid)
        if not mp or not mp._process:
            return False
        try:
            mp._process.kill()
            return True
        except Exception:
            return False

    async def timeout(self, pid: int, seconds: float) -> bool:
        mp = await self._get(pid)
        if not mp or not mp._process:
            return False
        try:
            await asyncio.wait_for(mp._process.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            await self.kill(pid)
            return True
        return False

    async def cleanup(self, pid: int) -> bool:
        mp = await self._get(pid)
        if not mp:
            return False
        mp.cleanup()
        async with self._lock:
            if pid in self._processes:
                del self._processes[pid]
        return True

    async def exit_status(self, pid: int) -> int | None:
        mp = await self._get(pid)
        if not mp:
            return None
        return mp.exit_status()

    async def progress(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "active": len(self._processes),
                "pids": sorted(self._processes.keys()),
            }

    async def _get(self, pid: int) -> ManagedProcess | None:
        async with self._lock:
            return self._processes.get(pid)

    # ── Sync API (daemon processes driven from synchronous call sites) ──

    def spawn_sync(
        self,
        cmd: str = "",
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        stdout=None,
        stderr=None,
    ) -> SyncManagedProcess | None:
        """Spawn and track a daemon subprocess. Returns None on failure.

        The caller must terminate it via :meth:`terminate_sync` — never by
        PID from external sources.
        """
        if not cmd:
            return None
        try:
            proc = subprocess.Popen(
                [cmd] + (args or []),
                cwd=cwd,
                env={**os.environ, **(env or {})},
                stdout=stdout if stdout is not None else subprocess.DEVNULL,
                stderr=stderr if stderr is not None else subprocess.DEVNULL,
            )
        except (OSError, ValueError) as e:
            logger.error("spawn_sync(%s) failed: %s", cmd, e)
            return None
        managed = SyncManagedProcess(
            pid=proc.pid,
            cmd=cmd,
            args=args or [],
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
        managed.attach(proc)
        with self._sync_lock:
            self._sync_processes[proc.pid] = managed
        logger.info("spawn_sync: %s (pid %d)", cmd, proc.pid)
        return managed

    def get_sync_process(self, pid: int) -> SyncManagedProcess | None:
        with self._sync_lock:
            return self._sync_processes.get(pid)

    def is_alive(self, pid: int) -> bool:
        with self._sync_lock:
            managed = self._sync_processes.get(pid)
        return bool(managed and managed.is_alive())

    def poll(self, pid: int) -> int | None:
        with self._sync_lock:
            managed = self._sync_processes.get(pid)
        if managed is None:
            return None
        return managed.poll()

    def terminate_sync(self, pid: int, timeout: float = 5.0) -> bool:
        """SIGTERM the tracked process (bounded wait, kill fallback)."""
        with self._sync_lock:
            managed = self._sync_processes.get(pid)
        if managed is None:
            return False
        return managed.terminate(timeout=timeout)

    def cleanup_sync(self, pid: int) -> bool:
        """Kill if alive and drop the tracking entry (own processes only)."""
        with self._sync_lock:
            managed = self._sync_processes.get(pid)
        if managed is None:
            return False
        managed.cleanup()
        with self._sync_lock:
            self._sync_processes.pop(pid, None)
        return True

    def sync_progress(self) -> dict[str, Any]:
        with self._sync_lock:
            return {
                "active": len(self._sync_processes),
                "pids": sorted(self._sync_processes.keys()),
            }
