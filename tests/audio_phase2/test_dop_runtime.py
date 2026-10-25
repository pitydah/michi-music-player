"""AP2-F09 — productive DoP executor identity/caps validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.infrastructure.audio_output.dop_runtime import (
    DopExecutionError,
    DopOutputExecutor,
)
from tests.dop.test_dop_planner import _plan


class _Port:
    def __init__(self, plan):
        self.plan = plan
        self.identity = {
            "dop": True,
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "host_generation": plan.host_generation,
            "binding_generation": plan.binding_generation,
            "stable_device_id": plan.stable_device_id,
            "device": plan.binding_locator,
            "carrier_rate_hz": plan.carrier_rate.frames_per_second,
            "carrier_format": plan.memory_contract.alsa_format,
            "channels": plan.source.channels,
            "plugin_revision": "michidop-rust-0.1.0",
            "prerolled": True,
            "path": "",
            "observations": [
                {
                    "factory": "michidop",
                    "media_type": "audio/x-raw",
                    "caps_state": "NEGOTIATED_CURRENT",
                    "fields": [
                        ["format", plan.memory_contract.alsa_format],
                        ["rate", str(plan.carrier_rate.frames_per_second)],
                        ["channels", str(plan.source.channels)],
                    ],
                }
            ],
        }

    def prepare_dop(self, payload):
        self.identity["path"] = payload["path"]
        return dict(self.identity)

    def commit_dop(self, expected):
        return {"committed": True}

    def start_dop(self):
        return {"state": "PLAYING", "confirmed": True}

    def pause_dop(self):
        return {"confirmed": True}

    def resume_dop(self):
        return {"confirmed": True}

    def stop_dop(self, expected):
        return {"stopped": True, "stale": False}

    def abort_dop(self, expected):
        return {"aborted": True, "stale": False}

    def query_dop_identity(self):
        return dict(self.identity)


def test_executor_prepares_and_confirms_exact_identity(tmp_path: Path) -> None:
    source = tmp_path / "track.dsf"
    source.write_bytes(b"DSD ")
    plan = _plan()
    port = _Port(plan)
    prepared = DopOutputExecutor(port).prepare(plan, source)
    assert prepared.execution_id == plan.execution_id
    assert port.identity["carrier_format"] == plan.memory_contract.alsa_format


@pytest.mark.parametrize(
    "field,value", [("carrier_format", "S32LE"), ("channels", "6")]
)
def test_executor_rejects_carrier_mismatch(
    tmp_path: Path, field: str, value: str
) -> None:
    source = tmp_path / "track.dsf"
    source.write_bytes(b"DSD ")
    plan = _plan()
    port = _Port(plan)
    port.identity[field] = value
    with pytest.raises(DopExecutionError) as info:
        DopOutputExecutor(port).prepare(plan, source)
    assert (
        info.value.code == "DOP_CARRIER_MISMATCH"
        or info.value.code == "DOP_HOST_IDENTITY_MISMATCH"
    )


def test_executor_rejects_host_generation_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "track.dsf"
    source.write_bytes(b"DSD ")
    plan = _plan()
    port = _Port(plan)
    port.identity["host_generation"] = 99
    with pytest.raises(DopExecutionError) as info:
        DopOutputExecutor(port).prepare(plan, source)
    assert info.value.code == "DOP_HOST_IDENTITY_MISMATCH"


def test_executor_threads_plan_identity_into_start_pause_resume(tmp_path: Path) -> None:
    source = tmp_path / "track.dsf"
    source.write_bytes(b"DSD ")
    plan = _plan()
    port = _Port(plan)
    expected: list[dict] = []

    def start(value):
        expected.append(value)
        return {"state": "PLAYING", "confirmed": True}

    def pause(value):
        expected.append(value)
        return {"confirmed": True}

    def resume(value):
        expected.append(value)
        return {"confirmed": True}

    port.start_dop = start
    port.pause_dop = pause
    port.resume_dop = resume
    executor = DopOutputExecutor(port)
    prepared = executor.prepare(plan, source)
    executor.start(prepared)
    executor.pause(prepared)
    executor.resume(prepared)
    assert len(expected) == 3
    assert all(item["execution_id"] == plan.execution_id for item in expected)
    assert all(item["host_generation"] == plan.host_generation for item in expected)


def test_child_runtime_rejects_stale_start_identity() -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_dop import (
        DopHostError,
        DopHostRuntime,
    )

    runtime = DopHostRuntime()
    runtime._identity = {
        "plan_id": "plan:new",
        "execution_id": "exec:new",
        "stable_device_id": "dev:dac",
        "device": "hw:3,0",
        "binding_generation": 7,
        "host_generation": 2,
    }
    with pytest.raises(DopHostError) as info:
        runtime.start(
            {
                "plan_id": "plan:old",
                "execution_id": "exec:old",
                "stable_device_id": "dev:dac",
                "device": "hw:3,0",
                "binding_generation": 7,
                "host_generation": 2,
            }
        )
    assert info.value.code == "DOP_HOST_IDENTITY_MISMATCH"
