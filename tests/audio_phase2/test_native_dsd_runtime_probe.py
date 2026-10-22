"""AP2-F08 — isolated runtime probe evidence (real GStreamer, lab sink)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
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
from michi.infrastructure.audio_output.dsd_runtime_inspector import (
    ObservedPad,
    inspect_native_dsd_branch,
)
from michi.infrastructure.audio_output.strict_dsd_sink import recipe_from_native_plan
from tests.audio_phase2.test_dsd_source_truth import build_dsf

PROBE = Path(__file__).resolve().parents[2] / "scripts" / "probe_native_dsd_runtime.py"


def _require_gst():
    gi = pytest.importorskip("gi")
    gi.require_version("Gst", "1.0")
    from gi.repository import Gst

    Gst.init(None)
    if Gst.ElementFactory.find("avdemux_dsf") is None:
        pytest.skip("GStreamer avdemux_dsf is unavailable")
    return Gst


def _run_probe(tmp_path: Path, dsf: Path, *extra: str) -> dict:
    out = tmp_path / "probe.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--path",
            str(dsf),
            "--json-out",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    return json.loads(out.read_text(encoding="utf-8"))


def test_isolated_probe_observes_real_dsd_source_caps(tmp_path) -> None:
    _require_gst()
    dsf = tmp_path / "source.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    data = _run_probe(tmp_path, dsf)
    assert data["errors"] == []
    media_types = {cap["media_type"] for cap in data["observed_caps"]}
    assert "audio/x-dsd" in media_types
    assert "audio/x-raw" not in media_types
    cap = next(
        cap for cap in data["observed_caps"] if cap["media_type"] == "audio/x-dsd"
    )
    fields = dict(cap["fields"])
    assert fields["format"] == "DSDU8"
    assert fields["rate"] == "352800"
    assert fields["channels"] == "2"
    assert fields["reversed-bytes"] == "False"


@pytest.mark.skipif(
    os.environ.get("MICHI_RUN_DSD_HARDWARE") != "1",
    reason="physical DSD sink negotiation requires the explicit operator gate",
)
def test_isolated_probe_negotiates_strict_dsd_sink_if_selected(tmp_path) -> None:
    _require_gst()
    dsf = tmp_path / "source.dsf"
    dsf.write_bytes(build_dsf(sample_count=2_822_400))
    device = os.environ.get("MICHI_DSD_DEVICE", "hw:3,0")
    data = _run_probe(
        tmp_path,
        dsf,
        "--sink",
        "alsasink",
        "--device",
        device,
        "--convert",
        "--execution-id",
        "exec:probe",
        "--binding-generation",
        "1",
    )
    assert data["errors"] == []
    assert data["prerolled"] is True
    media_types = {cap["media_type"] for cap in data["observed_caps"]}
    assert "audio/x-raw" not in media_types

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
    plan = NativeDsdPlanner().plan(
        stable_device_id="hardware:selected",
        binding_locator=device,
        binding_generation=1,
        source=source,
        qualifications=(
            NativeDsdQualification(
                stable_device_id="hardware:selected",
                binding_generation=1,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:hardware",
            ),
        ),
        execution_id="exec:probe",
        source_proven=True,
        active_engine_id="gstreamer",
    )
    observed = tuple(
        ObservedPad(
            element_name=str(cap["element_name"]),
            factory=str(cap["factory"]),
            pad_name=str(cap["pad_name"]),
            direction=str(cap["direction"]),
            role=str(cap["role"]),
            media_type=str(cap["media_type"]),
            fields=tuple((str(k), str(v)) for k, v in cap["fields"]),
            caps_state=str(cap["caps_state"]),
            linked=bool(cap["linked"]),
            selected_device=str(cap["selected_device"]),
            execution_id=str(cap["execution_id"]),
            binding_generation=int(cap["binding_generation"]),
        )
        for cap in data["observed_caps"]
    )
    evidence = inspect_native_dsd_branch(
        observed,
        recipe_from_native_plan(plan),
        expected_execution_id="exec:probe",
        expected_binding_generation=1,
        expected_device=device,
    )
    assert evidence.sink_format == "DSDU32BE"
    assert evidence.sink_rate_bytes_per_second_per_channel == 352_800
