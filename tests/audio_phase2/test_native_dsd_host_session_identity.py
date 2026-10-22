"""AP2-F08 — child host session identity and ownership guards."""

from __future__ import annotations

from typing import Any

from michi.infrastructure.audio_engines.gstreamer_host_session import (
    HostEngineSession,
)


class _FakePort:
    def __init__(self) -> None:
        self.has_source = False
        self.closed = False
        self.loads: list[str] = []

    def has_active_source(self) -> bool:
        return self.has_source

    def load(self, path) -> None:
        self.loads.append(str(path))

    def close(self) -> None:
        self.closed = True

    def set_runtime_failure_callback(self, callback) -> None:
        return None


class _FakeNative:
    def __init__(self) -> None:
        self.closed = False
        self.prepared = False
        self.aborted: list[dict] = []
        self.stopped: list[dict] = []

    def prepare(self, payload) -> dict[str, Any]:
        self.prepared = True
        return {
            "plan_id": "p",
            "execution_id": "e",
            "stable_device_id": "s",
            "device": "hw:3,0",
            "binding_generation": 1,
        }

    def abort(self, expected):
        self.aborted.append(expected)
        return {"aborted": True, "stale": False}

    def stop(self, expected):
        self.stopped.append(expected)
        return {"stopped": True, "stale": False}

    def close(self) -> None:
        self.closed = True


def _session():
    port = _FakePort()
    native = _FakeNative()
    session = HostEngineSession(
        port_factory=lambda _coordinator: port,
        emit=lambda *_args, **_kwargs: None,
        request_callback=lambda *_args, **_kwargs: (True, {}),
    )
    session._port = port
    session._opened = True
    session._native_dsd = native
    return session, port, native


def test_prepare_refuses_while_pcm_owns_output() -> None:
    session, port, native = _session()
    port.has_source = True
    ok, result = session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})
    assert ok is False
    assert result["code"] == "NATIVE_DSD_PCM_CONFLICT"
    assert native.prepared is False
    assert session._native_dsd_active is False


def test_load_and_close_pipeline_are_refused_while_native_owns_output() -> None:
    session, _port, _native = _session()
    ok, _ = session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})
    assert ok is True and session._native_dsd_active is True

    ok, result = session._op_load({"path": "/tmp/pcm.wav"})
    assert ok is False and result["code"] == "NATIVE_DSD_LOAD_CONFLICT"

    ok, result = session._op_close_pipeline({})
    assert ok is False and result["code"] == "NATIVE_DSD_PIPELINE_ACTIVE"


def test_destructive_operations_require_identity() -> None:
    session, _port, native = _session()
    session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})

    for handler in (session._op_abort_native_dsd, session._op_stop_native_dsd):
        ok, result = handler({"expected": {}})
        assert ok is False
        assert result["code"] == "NATIVE_DSD_HOST_IDENTITY_REQUIRED"
        ok, result = handler({})
        assert ok is False
        assert result["code"] == "NATIVE_DSD_HOST_IDENTITY_REQUIRED"
    assert native.aborted == [] and native.stopped == []
    assert session._native_dsd_active is True


def test_abort_and_stop_with_identity_release_ownership() -> None:
    session, _port, native = _session()
    session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})
    expected = {
        "plan_id": "p",
        "execution_id": "e",
        "stable_device_id": "s",
        "device": "hw:3,0",
        "binding_generation": 1,
    }
    ok, result = session._op_abort_native_dsd({"expected": expected})
    assert ok is True and result["aborted"] is True
    assert session._native_dsd_active is False
    assert native.aborted == [expected]

    session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})
    ok, result = session._op_stop_native_dsd({"expected": expected})
    assert ok is True and result["stopped"] is True
    assert session._native_dsd_active is False
    assert native.stopped == [expected]


def test_full_close_releases_native_runtime() -> None:
    session, port, native = _session()
    session._op_prepare_native_dsd({"path": "/tmp/a.dsf"})
    session.close()
    assert native.closed is True
    assert port.closed is True
    assert session._native_dsd_active is False
