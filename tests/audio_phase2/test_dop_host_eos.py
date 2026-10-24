"""AP2-F09 — DoP EOS identity and supersession fences at the host port."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)


class _Supervisor:
    host_generation = 1


def _identity(path: Path, execution: str = "exec:dop") -> dict[str, Any]:
    return {
        "dop": True,
        "plan_id": "dop:plan",
        "execution_id": execution,
        "host_generation": 1,
        "binding_generation": 3,
        "stable_device_id": "usb:test",
        "device": "hw:3,0",
        "carrier_rate_hz": 176_400,
        "carrier_format": "S32LE",
        "prerolled": True,
        "path": str(path),
    }


class _Submit:
    def __init__(self, path: Path):
        self.path = path
        self.execution = "exec:dop"

    def __call__(self, operation, payload, **kwargs):
        name = str(operation)
        if name == "prepare_dop":
            return _identity(self.path, self.execution)
        if name == "commit_dop":
            return {"committed": True}
        if name == "start_dop":
            return {"state": "PLAYING", "confirmed": True}
        if name == "stop_dop":
            return {"stopped": True, "stale": False}
        return {}


def _port(tmp_path: Path) -> tuple[GStreamerHostedAudioPort, _Submit]:
    path = tmp_path / "dop.dsf"
    path.write_bytes(b"DSD ")
    port = GStreamerHostedAudioPort(_Supervisor())
    submit = _Submit(path)
    port._submit = submit  # type: ignore[method-assign]
    port.prepare_dop({"path": str(path)})
    return port, submit


def _eos(execution: str = "exec:dop", plan: str = "dop:plan", gen: int = 1) -> dict:
    return {
        "command_generation": 1,
        "payload": {
            "event": "eos",
            "dop": True,
            "execution_id": execution,
            "plan_id": plan,
            "host_generation": gen,
        },
    }


def _eom(port: GStreamerHostedAudioPort) -> list[bool]:
    events: list[bool] = []
    port.subscribe_end_of_media(lambda: events.append(True))
    return events


def test_dop_eos_is_committed_once_with_captured_identity(tmp_path) -> None:
    port, _ = _port(tmp_path)
    eom = _eom(port)
    port._on_host_event(_eos())
    port.dispatch_pending()
    port._on_host_event(_eos())
    port.dispatch_pending()
    assert eom == [True]


def test_dop_eos_cannot_terminate_a_superseding_execution(tmp_path) -> None:
    port, submit = _port(tmp_path)
    eom = _eom(port)
    submit.execution = "exec:new"
    port.prepare_dop({"path": str(tmp_path / "dop.dsf")})
    port._on_host_event(_eos("exec:dop"))
    port.dispatch_pending()
    assert eom == []
    port._on_host_event(_eos("exec:new"))
    port.dispatch_pending()
    assert eom == [True]


def test_dop_eos_after_stop_is_stale(tmp_path) -> None:
    port, _ = _port(tmp_path)
    eom = _eom(port)
    port.stop_dop(
        {
            "plan_id": "dop:plan",
            "execution_id": "exec:dop",
            "stable_device_id": "usb:test",
            "device": "hw:3,0",
            "binding_generation": 3,
            "host_generation": 1,
        }
    )
    port._on_host_event(_eos())
    port.dispatch_pending()
    assert eom == []


def test_dop_eos_rejects_missing_or_old_identity(tmp_path) -> None:
    port, _ = _port(tmp_path)
    eom = _eom(port)
    frame = _eos()
    frame["payload"].pop("plan_id")
    port._on_host_event(frame)
    port._on_host_event(_eos(gen=0))
    port.dispatch_pending()
    assert eom == []


def test_native_and_dop_cleanup_are_independent() -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_session import (
        HostEngineSession,
    )

    session = HostEngineSession(
        port_factory=lambda _coordinator: None,
        emit=lambda *_args: None,
        request_callback=lambda *_args: (True, {}),
    )
    session._dop_active = True
    session._native_dsd_active = True
    session._clear_native_eos_timer()
    assert session._dop_active is True
    session._clear_dop_eos_timer()
    assert session._native_dsd_active is True
