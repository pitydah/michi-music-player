"""AP2-F09 — Gate A DoP vertical through the supervised GStreamer host.

The Rust element lives in an isolated plugin prefix. The test is skipped when
that Gate A artifact is not installed; it never falls back to the checkout.
"""

from __future__ import annotations

import contextlib
import importlib.util
import time
from pathlib import Path

import pytest

from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None


def _resolved_prefix():
    from michi.infrastructure.audio_output.dop_plugin import resolve_dop_prefix

    try:
        return resolve_dop_prefix()
    except RuntimeError:
        return None


_PREFIX = _resolved_prefix()
_PLUGIN = (
    _PREFIX / "libmichidop.so"
    if _PREFIX is not None
    else Path("/nonexistent/libmichidop.so")
)

pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _PLUGIN.exists(),
    reason="Gate A michidop artifact is not installed in its private prefix",
)


def _payload(
    path: Path,
    *,
    plan_id: str = "dop:host-test",
    execution_id: str = "exec:dop-host",
) -> dict:
    return {
        "path": str(path),
        "plan_id": plan_id,
        "execution_id": execution_id,
        "host_generation": 1,
        "binding_generation": 1,
        "stable_device_id": "usb:test",
        "locator": "hw:3,0",
        "source_family": "dsf",
        "source_rate_hz": 352_800,
        "carrier_rate_hz": 176_400,
        "carrier_format": "S32LE",
        "channels": 2,
        "reverse_payload_bits": False,
        "sink_factory": "fakesink",
    }


def _supervisor_and_port():
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        GStreamerHostSupervisor,
    )
    from michi.infrastructure.audio_engines.gstreamer_host_port import (
        GStreamerHostedAudioPort,
    )

    supervisor = GStreamerHostSupervisor(
        start_timeout_s=45.0,
        command_timeout_s=30.0,
        terminate_grace_s=8.0,
        term_grace_s=5.0,
        kill_grace_s=5.0,
    )
    port = GStreamerHostedAudioPort(
        supervisor, command_deadline_s=30.0, load_deadline_s=30.0
    )
    return supervisor, port


def _expected(identity: dict) -> dict:
    return {
        "plan_id": identity["plan_id"],
        "execution_id": identity["execution_id"],
        "stable_device_id": identity["stable_device_id"],
        "device": identity["device"],
        "binding_generation": identity["binding_generation"],
        "host_generation": identity["host_generation"],
    }


def test_gate_a_dop_host_vertical_is_explicit_and_confirmed(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        assert identity["dop"] is True
        assert identity["prerolled"] is True
        assert identity["plugin_filename"].startswith(str(_PREFIX))
        assert identity["carrier_rate_hz"] == 176_400
        assert identity["carrier_format"] == "S32LE"
        observations = {item["role"]: item for item in identity["observations"]}
        assert observations["michidop"]["media_type"] == "audio/x-raw"
        assert observations["sink"]["media_type"] == "audio/x-raw"
        assert "audio/x-dsd" in observations["dsd_caps"]["media_type"]
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        assert port.commit_dop(expected)["committed"] is True
        eom: list[bool] = []
        port.subscribe_end_of_media(lambda: eom.append(True))
        assert port.start_dop()["state"] == "PLAYING"
        deadline = time.monotonic() + 8.0
        while not eom and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)
        port.dispatch_pending()
        assert eom, "DoP EOS never reached the parent"
        evidence = port.query_dop_evidence()
        assert evidence["dop"] is True
        assert evidence["execution_id"] == "exec:dop-host"
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()


def test_abort_after_a_confirmed_stop_is_exact_not_identity_failure(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        expected = {
            "plan_id": identity["plan_id"],
            "execution_id": identity["execution_id"],
            "stable_device_id": identity["stable_device_id"],
            "device": identity["device"],
            "binding_generation": identity["binding_generation"],
            "host_generation": identity["host_generation"],
        }
        assert port.commit_dop(expected)["committed"] is True
        stopped = port.stop_dop(expected)
        assert stopped["stopped"] is True and stopped["stale"] is False
        aborted = port.abort_dop(expected)
        assert aborted["aborted"] is True
        assert aborted["already"] is True
        assert aborted["stale"] is False
        assert aborted["execution_id"] == expected["execution_id"]
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()


def test_stop_response_loss_is_recovered_from_child_receipt(
    tmp_path, monkeypatch
) -> None:
    from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
        HostOperation,
    )

    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    original_submit = port._submit
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        expected = _expected(identity)
        assert port.commit_dop(expected)["committed"] is True
        assert port.start_dop()["state"] == "PLAYING"

        dropped = {"done": False}

        def drop_stop_response(operation, payload, **kwargs):
            result = original_submit(operation, payload, **kwargs)
            if operation is HostOperation.STOP_DOP and not dropped["done"]:
                dropped["done"] = True
                raise TimeoutError("response lost after child released A")
            return result

        monkeypatch.setattr(port, "_submit", drop_stop_response)
        with pytest.raises(TimeoutError, match="response lost"):
            port.stop_dop(expected)
        assert dropped["done"] is True
        # The parent did not receive the response: it cannot claim release.
        assert port.dop_active is True
        assert port._dop_release_receipt is None

        # The child retained the proof; the retry is exact and idempotent.
        monkeypatch.setattr(port, "_submit", original_submit)
        retry = port.stop_dop(expected)
        assert retry["stopped"] is True
        assert retry["already"] is True
        assert retry["release"]["execution_id"] == expected["execution_id"]
        assert retry["release"]["confirmed"] is True
        assert retry["release"]["provenance"] == "SUPERVISED_HOST"
        assert port.dop_active is False
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()


def test_abort_with_an_invented_execution_id_is_not_a_release(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        expected = _expected(identity)
        assert port.commit_dop(expected)["committed"] is True
        stopped = port.stop_dop(expected)
        assert stopped["release"]["execution_id"] == expected["execution_id"]

        invented = dict(expected, execution_id="exec:invented")
        with pytest.raises(Exception, match="DOP_RELEASE_UNCONFIRMED"):
            port.abort_dop(invented)
        # The proof for A is still available for the exact execution.
        proof = port.abort_dop(expected)
        assert proof["already"] is True
        assert proof["release"]["execution_id"] == expected["execution_id"]
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()


def test_release_receipt_for_a_never_certifies_active_b(tmp_path, monkeypatch) -> None:
    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    expected_b: dict = {}
    try:
        port.activate()
        identity_a = port.prepare_dop(
            _payload(dsf, plan_id="dop:host-a", execution_id="exec:dop-a")
        )
        expected_a = _expected(identity_a)
        port.commit_dop(expected_a)
        port.stop_dop(expected_a)

        identity_b = port.prepare_dop(
            _payload(dsf, plan_id="dop:host-b", execution_id="exec:dop-b")
        )
        expected_b = _expected(identity_b)
        assert port.dop_active is True

        with pytest.raises(Exception, match="DOP_HOST_IDENTITY_MISMATCH"):
            port.abort_dop(expected_a)

        released_b = port.abort_dop(expected_b)
        assert released_b["release"]["execution_id"] == "exec:dop-b"
        assert released_b["release"]["plan_id"] == "dop:host-b"
        # A's proof must not certify B.
        assert released_b["release"]["execution_id"] != expected_a["execution_id"]
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected_b)
        supervisor.close()


def test_host_loss_invalidates_release_receipt(tmp_path, monkeypatch) -> None:
    """A release proof cannot survive the host generation that produced it."""
    from michi.application.ports import AudioTransportCommandError

    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        expected = _expected(identity)
        assert port.commit_dop(expected)["committed"] is True
        stopped = port.stop_dop(expected)
        assert stopped["release"]["confirmed"] is True
        assert port._dop_release_receipt is not None

        port._on_host_lost(
            identity["host_generation"], "host_lost", "supervisor restart"
        )
        assert port._dop_release_receipt is None
        with pytest.raises(AudioTransportCommandError, match="DOP_RELEASE_UNCONFIRMED"):
            port.abort_dop(expected)
    finally:
        supervisor.close()


def test_host_restart_never_reuses_a_release_receipt(tmp_path, monkeypatch) -> None:
    """A new supervisor generation cannot inherit A's physical ownership."""
    from michi.infrastructure.audio_engines.gstreamer_host_client import (
        OutputHostError,
    )

    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    first_supervisor, first_port = _supervisor_and_port()
    second_supervisor = None
    try:
        first_port.activate()
        identity_a = first_port.prepare_dop(
            _payload(dsf, plan_id="dop:host-restart-a", execution_id="exec:a")
        )
        expected_a = _expected(identity_a)
        first_port.commit_dop(expected_a)
        assert first_port.start_dop()["state"] == "PLAYING"

        # The process exits without a confirmed DoP release. The next host
        # generation must not inherit A's receipt.
        first_supervisor.close()
        with pytest.raises(OutputHostError):
            first_port.abort_dop(expected_a)
        assert first_port._dop_release_receipt is None

        second_supervisor, second_port = _supervisor_and_port()
        second_port.activate()
        expected_b: dict = {}
        try:
            with pytest.raises(Exception, match="DOP_RELEASE_UNCONFIRMED"):
                second_port.abort_dop(expected_a)
            identity_b = second_port.prepare_dop(
                _payload(dsf, plan_id="dop:host-restart-b", execution_id="exec:b")
            )
            expected_b = _expected(identity_b)
            second_port.commit_dop(expected_b)
            assert second_port.start_dop()["state"] == "PLAYING"
            released_b = second_port.stop_dop(expected_b)
            assert released_b["release"]["execution_id"] == "exec:b"
            assert second_port._dop_release_receipt is not None
        finally:
            with contextlib.suppress(Exception):
                if expected_b:
                    second_port.abort_dop(expected_b)
    finally:
        with contextlib.suppress(Exception):
            first_port.close()
        first_supervisor.close()
        if second_supervisor is not None:
            second_supervisor.close()


def test_stop_without_host_release_keeps_a_then_abort_retries(
    tmp_path, monkeypatch
) -> None:
    """A failed STOP must not publish or forget the still-owned execution A."""
    from michi.infrastructure.audio_engines.gstreamer_host_protocol import (
        HostOperation,
    )

    dsf = tmp_path / "dop.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("GST_PLUGIN_PATH", str(_PREFIX))
    monkeypatch.setenv("MICHI_DOP_PLUGIN_PREFIX", str(_PREFIX))
    supervisor, port = _supervisor_and_port()
    original_submit = port._submit

    def fail_before_stop(operation, payload, **kwargs):
        if operation is HostOperation.STOP_DOP:
            raise TimeoutError("STOP deadline before host execution")
        return original_submit(operation, payload, **kwargs)

    try:
        port.activate()
        identity = port.prepare_dop(_payload(dsf))
        expected = _expected(identity)
        assert port.commit_dop(expected)["committed"] is True
        monkeypatch.setattr(port, "_submit", fail_before_stop)
        with pytest.raises(TimeoutError, match="STOP deadline"):
            port.stop_dop(expected)
        assert port.dop_active is True
        assert port._dop_release_receipt is None

        monkeypatch.setattr(port, "_submit", original_submit)
        retried = port.abort_dop(expected)
        assert retried["aborted"] is True
        assert retried["release"]["execution_id"] == expected["execution_id"]
        assert retried["release"]["confirmed"] is True
        assert port.dop_active is False
    finally:
        with contextlib.suppress(Exception):
            port.abort_dop(expected)
        supervisor.close()
