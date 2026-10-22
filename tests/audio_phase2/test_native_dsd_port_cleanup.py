"""AP2-F08 — transactional Native DSD transport cleanup and exclusivity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from michi.application.ports import AudioTransportCommandError
from michi.infrastructure.audio_engines.gstreamer_host_client import (
    OutputHostCommandError,
)
from michi.infrastructure.audio_engines.gstreamer_host_port import (
    GStreamerHostedAudioPort,
)


class _Supervisor:
    host_generation = 1


def _identity(path: Path) -> dict[str, Any]:
    return {
        "plan_id": "native-dsd:plan",
        "execution_id": "exec:1",
        "stable_device_id": "usb:152a:85dd",
        "device": "hw:3,0",
        "binding_generation": 1,
        "format": "DSDU32BE",
        "rate": 352_800,
        "channels": 2,
        "source_bits": 2_822_400,
        "sink_factory": "alsasink",
        "lab_sink": False,
        "prerolled": True,
        "path": str(path),
        "observations": [],
    }


def _expected() -> dict[str, Any]:
    return {
        "plan_id": "native-dsd:plan",
        "execution_id": "exec:1",
        "stable_device_id": "usb:152a:85dd",
        "device": "hw:3,0",
        "binding_generation": 1,
    }


class _Submit:
    def __init__(self, path: Path, responses: dict[str, dict[str, Any]] | None = None):
        self.path = path
        self.responses = dict(responses or {})
        self.calls: list[str] = []

    def __call__(self, operation, payload, **kwargs):
        name = str(operation)
        self.calls.append(name)
        if name in self.responses:
            return self.responses[name]
        if name == "prepare_native_dsd":
            return _identity(self.path)
        if name == "commit_native_dsd":
            return {"committed": True}
        if name == "start_native_dsd":
            return {"state": "PLAYING", "confirmed": True}
        if name == "abort_native_dsd":
            return {"aborted": True, "stale": False}
        if name == "stop_native_dsd":
            return {"stopped": True, "stale": False}
        if name == "load":
            return {"accepted": True}
        if name == "stop":
            return {"stopped": True}
        return {}


def _port(tmp_path: Path, responses=None):
    path = tmp_path / "source.dsf"
    path.write_bytes(b"DSD ")
    port = GStreamerHostedAudioPort(_Supervisor())
    submit = _Submit(path, responses)
    port._submit = submit  # type: ignore[method-assign]
    port.prepare_native_dsd({"path": str(path)})
    return port, submit, _identity(path)


def test_abort_requires_identity_and_explicit_confirmation(tmp_path) -> None:
    port, submit, _ = _port(tmp_path)
    with pytest.raises(AudioTransportCommandError):
        port.abort_native_dsd({})
    assert port._native_dsd_active is True

    submit.responses["abort_native_dsd"] = {"aborted": True}
    with pytest.raises(OutputHostCommandError):
        port.abort_native_dsd(_expected())
    assert port._native_dsd_active is True

    submit.responses["abort_native_dsd"] = {"aborted": True, "stale": False}
    port.abort_native_dsd(_expected())
    assert port._native_dsd_active is False


def test_stop_requires_identity_and_explicit_confirmation(tmp_path) -> None:
    port, submit, _ = _port(tmp_path)
    with pytest.raises(AudioTransportCommandError):
        port.stop_native_dsd({})
    assert port._native_dsd_active is True

    submit.responses["stop_native_dsd"] = {"stopped": True}
    with pytest.raises(OutputHostCommandError):
        port.stop_native_dsd(_expected())
    assert port._native_dsd_active is True

    submit.responses["stop_native_dsd"] = {"stopped": True, "stale": False}
    port.stop_native_dsd(_expected())
    assert port._native_dsd_active is False


def test_stale_identity_cannot_destroy_the_current_execution(tmp_path) -> None:
    port, submit, _ = _port(tmp_path)
    stale = dict(_expected(), execution_id="exec:old")
    with pytest.raises(AudioTransportCommandError):
        port.stop_native_dsd(stale)
    assert port._native_dsd_active is True
    assert "stop_native_dsd" not in submit.calls
    with pytest.raises(AudioTransportCommandError):
        port.abort_native_dsd(stale)
    assert port._native_dsd_active is True


def test_prepare_is_refused_while_pcm_owns_the_output(tmp_path) -> None:
    path = tmp_path / "source.dsf"
    path.write_bytes(b"DSD ")
    port = GStreamerHostedAudioPort(_Supervisor())
    port._submit = _Submit(path)  # type: ignore[method-assign]
    port._pcm_active = True
    with pytest.raises(AudioTransportCommandError) as info:
        port.prepare_native_dsd({"path": str(path)})
    assert "NATIVE_DSD_PCM_CONFLICT" in str(info.value)


def test_abort_recovery_allows_pcm_load_again(tmp_path) -> None:
    port, submit, _ = _port(tmp_path)
    port.abort_native_dsd(_expected())
    assert port._native_dsd_active is False
    assert port._pcm_active is False

    port.load(tmp_path / "source.dsf")
    assert port._pcm_active is True
    port.stop()
    assert port._pcm_active is False


def test_unconfirmed_playing_is_not_published(tmp_path) -> None:
    port, submit, _ = _port(tmp_path)
    port.commit_native_dsd(_expected())
    submit.responses["start_native_dsd"] = {"state": "PLAYING"}
    with pytest.raises(OutputHostCommandError):
        port.start_native_dsd()
    assert port._native_dsd_active is True
    assert port._native_dsd_state == "COMMITTED"
