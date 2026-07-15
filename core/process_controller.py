"""ProcessController — centralizes external process management.

API: start, stdout, stderr, progress, PID, timeout, terminate, kill, cleanup.
Thread-safe, never blocks UI thread. No subprocess.run() in Qt slots.
"""
from __future__ import annotations

import asyncio
import logging
import os
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


class ProcessController:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._processes: dict[int, ManagedProcess] = {}
        self._counter = 0

    async def start(
        self,
        cmd: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        capture_stdout: bool = False,
    ) -> ManagedProcess:
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

    async     def _wait_exit(self, proc: asyncio.subprocess.Process, mp: ManagedProcess):
        try:
            returncode = await proc.wait()
            mp._exit_status = returncode
        except Exception as e:
            logger.debug("wait exit: %s", e)
            mp._exit_status = -1
        proc._transport = None  # noqa: SIM105

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
