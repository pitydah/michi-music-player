"""AP2-F08 — parent executor over the supervised Native DSD host."""

from __future__ import annotations

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
    NativeDsdExecutionError,
    NativeDsdOutputExecutor,
)

DEVICE = "hw:3,0"
EXEC = "exec:executor"


def _plan():
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
        stable_device_id="usb:152a:85dd",
        binding_locator=DEVICE,
        binding_generation=3,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id="usb:152a:85dd",
                binding_generation=3,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:test",
            ),
        ),
        execution_id=EXEC,
        source_proven=True,
        active_engine_id="gstreamer",
    )


def _observation(role: str, factory: str, pad: str, direction: str, **fields):
    base = {
        "format": "DSDU32BE",
        "rate": "352800",
        "channels": "2",
        "layout": "interleaved",
        "reversed-bytes": "false",
    }
    base.update(fields)
    return {
        "element_name": f"{role}-element",
        "factory": factory,
        "pad_name": pad,
        "direction": direction,
        "role": role,
        "media_type": "audio/x-dsd",
        "fields": [[k, str(v)] for k, v in base.items()],
        "caps_state": "NEGOTIATED_CURRENT",
        "linked": True,
        "selected_device": DEVICE,
        "execution_id": EXEC,
        "binding_generation": 3,
    }


def _identity(**overrides):
    identity = {
        "plan_id": _plan().plan_id,
        "execution_id": EXEC,
        "binding_generation": 3,
        "stable_device_id": "usb:152a:85dd",
        "device": DEVICE,
        "format": "DSDU32BE",
        "rate": 352_800,
        "channels": 2,
        "source_bits": 2_822_400,
        "sink_factory": "alsasink",
        "lab_sink": False,
        "factories": ["avdemux_dsf", "dsdconvert", "capsfilter", "alsasink"],
        "observations": [
            _observation(
                "source",
                "avdemux_dsf",
                "audio_0",
                "src",
                format="DSDU8",
                layout="non-interleaved",
            ),
            _observation("sink", "alsasink", "sink", "sink"),
        ],
        "prerolled": True,
        "path": "/tmp/source.dsf",
    }
    identity.update(overrides)
    return identity


class _FakePort:
    def __init__(self, identity=None, error=None) -> None:
        self.identity = _identity() if identity is None else identity
        self.error = error
        self.calls: list[tuple[str, object]] = []

    def prepare_native_dsd(self, payload):
        self.calls.append(("prepare", payload))
        if self.error is not None:
            raise self.error
        return self.identity

    def commit_native_dsd(self, expected):
        self.calls.append(("commit", expected))
        return {"committed": True}

    def start_native_dsd(self):
        self.calls.append(("start", None))
        return {"state": "PLAYING"}

    def pause_native_dsd(self):
        self.calls.append(("pause", None))
        return {"state": "PAUSED"}

    def resume_native_dsd(self):
        self.calls.append(("resume", None))
        return {"state": "PLAYING"}

    def stop_native_dsd(self, expected):
        self.calls.append(("stop", expected))
        return {"stopped": True, "stale": False}

    def abort_native_dsd(self, expected):
        self.calls.append(("abort", expected))
        return {"aborted": True, "stale": False}


def _file(tmp_path):
    path = tmp_path / "source.dsf"
    path.write_bytes(b"DSD ")
    return path


def test_prepare_proves_identity_and_evidence(tmp_path) -> None:
    port = _FakePort()
    prepared = NativeDsdOutputExecutor(port).prepare(_plan(), _file(tmp_path))
    assert prepared.execution_id == EXEC
    assert prepared.recipe.sink_factory == "alsasink"
    payload = port.calls[0][1]
    assert payload["source_family"] == "dsf"
    assert payload["sink_factory"] == "alsasink"
    assert payload["requires_dsdconvert"] is True


def test_commit_start_pause_resume_stop(tmp_path) -> None:
    port = _FakePort()
    executor = NativeDsdOutputExecutor(port)
    prepared = executor.prepare(_plan(), _file(tmp_path))
    executor.commit(prepared)
    executor.start(prepared)
    executor.pause()
    executor.resume()
    executor.stop(prepared)
    assert [name for name, _ in port.calls] == [
        "prepare",
        "commit",
        "start",
        "pause",
        "resume",
        "stop",
    ]


def test_identity_mismatch_aborts_and_never_commits(tmp_path) -> None:
    port = _FakePort(identity=_identity(device="hw:9,0"))
    with pytest.raises(NativeDsdExecutionError) as info:
        NativeDsdOutputExecutor(port).prepare(_plan(), _file(tmp_path))
    assert info.value.code == "NATIVE_DSD_HOST_IDENTITY_MISMATCH"
    assert port.calls[-1][0] == "abort"
    assert all(name != "commit" for name, _ in port.calls)


def test_raw_pad_in_host_evidence_aborts(tmp_path) -> None:
    identity = _identity()
    identity["observations"][0]["media_type"] = "audio/x-raw"
    port = _FakePort(identity=identity)
    with pytest.raises(NativeDsdExecutionError) as info:
        NativeDsdOutputExecutor(port).prepare(_plan(), _file(tmp_path))
    assert info.value.code == "NATIVE_DSD_PCM_CONVERSION_DETECTED"
    assert port.calls[-1][0] == "abort"


def test_lab_sink_identity_is_never_productive(tmp_path) -> None:
    port = _FakePort(identity=_identity(lab_sink=True))
    with pytest.raises(NativeDsdExecutionError) as info:
        NativeDsdOutputExecutor(port).prepare(_plan(), _file(tmp_path))
    assert info.value.code == "NATIVE_DSD_HOST_IDENTITY_MISMATCH"
    assert port.calls[-1][0] == "abort"


def test_unknown_source_family_is_refused(tmp_path) -> None:
    path = tmp_path / "source.wav"
    path.write_bytes(b"RIFF")
    with pytest.raises(NativeDsdExecutionError) as info:
        NativeDsdOutputExecutor(_FakePort()).prepare(_plan(), path)
    assert info.value.code == "NATIVE_DSD_SOURCE_FAMILY_UNKNOWN"


def test_host_prepare_error_is_typed_and_not_committed(tmp_path) -> None:
    class _HostError(RuntimeError):
        code = "NATIVE_DSD_HOST_PREROLL_FAILED"

    port = _FakePort(error=_HostError("preroll failed"))
    with pytest.raises(NativeDsdExecutionError) as info:
        NativeDsdOutputExecutor(port).prepare(_plan(), _file(tmp_path))
    assert info.value.code == "NATIVE_DSD_HOST_PREROLL_FAILED"
    assert all(name != "commit" for name, _ in port.calls)
