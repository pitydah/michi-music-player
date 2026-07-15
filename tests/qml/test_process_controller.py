"""Tests for core/process_controller.py — ProcessController."""
import asyncio
import sys
import tempfile

import pytest

from core.process_controller import ProcessController


@pytest.fixture
def controller():
    return ProcessController()


@pytest.mark.asyncio
async def test_start_and_exit_status(controller):
    mp = await controller.start(sys.executable, ["-c", "exit(0)"])
    await asyncio.sleep(0.3)
    assert mp.exit_status() == 0


@pytest.mark.asyncio
async def test_start_failure_exit(controller):
    mp = await controller.start(sys.executable, ["-c", "exit(42)"])
    await asyncio.sleep(0.3)
    assert mp.exit_status() == 42


@pytest.mark.asyncio
async def test_progress_empty(controller):
    prog = await controller.progress()
    assert prog["active"] == 0


@pytest.mark.asyncio
async def test_progress_after_start(controller):
    await controller.start(sys.executable, ["-c", "import time; time.sleep(5)"])
    prog = await controller.progress()
    assert prog["active"] == 1


@pytest.mark.asyncio
async def test_terminate(controller):
    mp = await controller.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    assert mp.is_alive()
    ok = await controller.terminate(mp.pid)
    await asyncio.sleep(0.3)
    assert ok


@pytest.mark.asyncio
async def test_kill(controller):
    mp = await controller.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    assert mp.is_alive()
    ok = await controller.kill(mp.pid)
    await asyncio.sleep(0.3)
    assert ok


@pytest.mark.asyncio
async def test_timeout_kills(controller):
    mp = await controller.start(sys.executable, ["-c", "import time; time.sleep(30)"])
    timed_out = await controller.timeout(mp.pid, 0.001)
    assert timed_out
    await asyncio.sleep(0.3)
    assert mp.exit_status() is not None


@pytest.mark.asyncio
async def test_cleanup_removes(controller):
    mp = await controller.start(sys.executable, ["-c", "exit(0)"])
    await asyncio.sleep(0.3)
    await controller.cleanup(mp.pid)
    prog = await controller.progress()
    assert mp.pid not in prog["pids"]


@pytest.mark.asyncio
async def test_stderr_collection(controller):
    mp = await controller.start(sys.executable, ["-c", "import sys; print('err line', file=sys.stderr)"])
    await asyncio.sleep(0.5)
    lines = await controller.stderr(mp.pid)
    assert any("err line" in line for line in lines)


@pytest.mark.asyncio
async def test_exit_status_api(controller):
    mp = await controller.start(sys.executable, ["-c", "exit(0)"])
    await asyncio.sleep(0.3)
    status = await controller.exit_status(mp.pid)
    assert status == 0


@pytest.mark.asyncio
async def test_unknown_pid_returns_false(controller):
    assert await controller.terminate(99999) is False
    assert await controller.kill(99999) is False
    assert await controller.cleanup(99999) is False
    assert await controller.stderr(99999) == []
    assert await controller.exit_status(99999) is None


@pytest.mark.asyncio
async def test_start_with_custom_cwd(controller):
    with tempfile.TemporaryDirectory() as td:
        mp = await controller.start(sys.executable, ["-c", "import os; print(os.getcwd())"], cwd=td)
        await asyncio.sleep(0.3)
        assert mp.cwd == td


@pytest.mark.asyncio
async def test_start_with_custom_env(controller):
    mp = await controller.start(sys.executable, ["-c", "exit(0)"], env={"MICHI_TEST": "1"})
    await asyncio.sleep(0.3)
    assert mp.env.get("MICHI_TEST") == "1"
