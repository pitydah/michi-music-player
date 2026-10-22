"""AP2-F08 — real supervised-host Native DSD pipeline tests.

The lab test uses fakesink under the explicit lab switch; it still exercises
the real child process and the explicit DSD pipeline. The hardware test is
opt-in and uses the selected ALSA endpoint, never a mock.
"""

from __future__ import annotations

import importlib.util
import os
import signal
import time
from pathlib import Path

import pytest

from michi.application.dsd_output_planner import (
    AlsaDsdTuple,
    NativeDsdPlanner,
    NativeDsdQualification,
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from michi.infrastructure.audio_output.native_dsd_executor import (
    NativeDsdOutputExecutor,
)
from tests.audio_phase2.test_dsd_source_truth import build_dsf

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer is not available"
)


def _require_dsd_factories() -> None:
    """Skip only when the runtime genuinely lacks the DSD demux/converter."""
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    missing = [
        name
        for name in ("avdemux_dsf", "dsdconvert")
        if Gst.ElementFactory.find(name) is None
    ]
    if missing:
        pytest.skip(f"GStreamer DSD factories unavailable: {missing}")


def _plan(device: str, execution_id: str = "exec:host-test") -> object:
    source = DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=("FL", "FR"),
    )
    requested = AlsaDsdTuple(
        format_name=AlsaDsdGrouping.DSD_U32_BE.alsa_format_name,
        frame_rate_hz=88_200,
        channels=2,
        sample_width_bits=32,
        source_bits_per_second_per_channel=2_822_400,
    )
    return NativeDsdPlanner().plan(
        stable_device_id="host:selected",
        binding_locator=device,
        binding_generation=1,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id="host:selected",
                binding_generation=1,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:host",
            ),
        ),
        execution_id=execution_id,
        source_proven=True,
        active_engine_id="gstreamer",
    )


def _payload(plan, path: Path, sink_factory: str) -> dict:
    return {
        "path": str(path),
        "plan_id": plan.plan_id,
        "execution_id": plan.execution_id,
        "binding_generation": plan.binding_generation,
        "stable_device_id": plan.stable_device_id,
        "locator": plan.binding_locator,
        "gst_format": plan.gst_format,
        "gst_rate_bytes_per_second_per_channel": (
            plan.gst_rate_bytes_per_second_per_channel
        ),
        "channels": plan.alsa_tuple.channels,
        "source_bits_per_second_per_channel": plan.source.bit_rate_hz,
        "normalize_reversed_bytes": plan.normalize_reversed_bytes,
        "requires_dsdconvert": True,
        "source_family": "dsf",
        "sink_factory": sink_factory,
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


def test_real_host_native_dsd_lab_pipeline_is_explicit_and_clean(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "native.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    plan = _plan("hw:3,0")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        identity = port.prepare_native_dsd(_payload(plan, dsf, "fakesink"))
        assert identity["prerolled"] is True
        assert identity["sink_factory"] == "fakesink"
        from michi.application.ports import AudioTransportCommandError

        with pytest.raises(AudioTransportCommandError):
            port.load(dsf)
        with pytest.raises(AudioTransportCommandError):
            port.seek(0)
        with pytest.raises(AudioTransportCommandError):
            port.set_volume(0)
        observations = identity["observations"]
        media_types = {item["media_type"] for item in observations}
        assert "audio/x-dsd" in media_types
        assert "audio/x-raw" not in media_types
        expected = {
            "plan_id": plan.plan_id,
            "execution_id": plan.execution_id,
            "stable_device_id": plan.stable_device_id,
            "device": plan.binding_locator,
            "binding_generation": 1,
        }
        assert port.commit_native_dsd(expected)["committed"] is True
        assert port.start_native_dsd()["state"] == "PLAYING"
        port.stop()
        assert port.query_native_dsd_identity() == {"native_dsd": False}
    finally:
        port.close()
    assert port.termination_kind == "GRACEFUL"
    assert not supervisor.pid_alive()


@pytest.mark.skipif(
    os.environ.get("MICHI_RUN_DSD_HARDWARE") != "1",
    reason="physical DSD host playback requires the explicit operator gate",
)
def test_real_host_native_dsd_alsasink_executor(tmp_path) -> None:
    _require_dsd_factories()
    device = os.environ.get("MICHI_DSD_DEVICE", "hw:3,0")
    dsf = tmp_path / "native-hw.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    plan = _plan(device)
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        executor = NativeDsdOutputExecutor(port)
        prepared = executor.prepare(plan, dsf)
        assert prepared.identity["sink_factory"] == "alsasink"
        assert prepared.identity["lab_sink"] is False
        executor.commit(prepared)
        executor.start(prepared)
        time.sleep(0.2)
        identity = port.query_native_dsd_identity()
        assert identity["native_dsd"] is True
        assert identity["errors"] == []
        executor.stop(prepared)
    finally:
        port.close()
    assert not supervisor.pid_alive()


def test_new_preparation_supersedes_the_previous_execution(
    tmp_path, monkeypatch
) -> None:
    dsf = tmp_path / "native.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    first = _plan("hw:3,0", "exec:A")
    second = _plan("hw:3,0", "exec:B")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    supervisor, port = _supervisor_and_port()
    try:
        port.activate()
        port.prepare_native_dsd(_payload(first, dsf, "fakesink"))
        port.prepare_native_dsd(_payload(second, dsf, "fakesink"))
        from michi.application.ports import AudioTransportCommandError

        with pytest.raises(AudioTransportCommandError) as info:
            port.commit_native_dsd(
                {
                    "plan_id": first.plan_id,
                    "execution_id": first.execution_id,
                    "device": first.binding_locator,
                    "binding_generation": 1,
                }
            )
        assert "NATIVE_DSD_IDENTITY_STALE" in str(info.value)
        assert (
            port.commit_native_dsd(
                {
                    "plan_id": second.plan_id,
                    "execution_id": second.execution_id,
                    "stable_device_id": second.stable_device_id,
                    "device": second.binding_locator,
                    "binding_generation": 1,
                }
            )["committed"]
            is True
        )
        port.stop_native_dsd(
            {
                "plan_id": second.plan_id,
                "execution_id": second.execution_id,
                "stable_device_id": second.stable_device_id,
                "device": second.binding_locator,
                "binding_generation": 1,
            }
        )
    finally:
        port.close()
    assert not supervisor.pid_alive()


def test_native_dsd_host_loss_retires_the_execution(tmp_path, monkeypatch) -> None:
    _require_dsd_factories()
    dsf = tmp_path / "native.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    plan = _plan("hw:3,0")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    supervisor, port = _supervisor_and_port()
    lost: list[str] = []
    port.add_host_lost_listener(lost.append)
    expected = {
        "plan_id": plan.plan_id,
        "execution_id": plan.execution_id,
        "stable_device_id": plan.stable_device_id,
        "device": plan.binding_locator,
        "binding_generation": 1,
    }
    try:
        port.activate()
        port.prepare_native_dsd(_payload(plan, dsf, "fakesink"))
        port.commit_native_dsd(expected)
        port.start_native_dsd()
        pid = supervisor.pid
        assert pid is not None
        os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            port.dispatch_pending()
            if lost:
                break
            time.sleep(0.02)
        assert lost, "host loss must be reported"
        from michi.application.ports import AudioTransportUnavailableError

        with pytest.raises(AudioTransportUnavailableError):
            port.query_native_dsd_identity()
        with pytest.raises(AudioTransportUnavailableError):
            port.stop_native_dsd(expected)
    finally:
        port.close()
    assert not supervisor.pid_alive()
