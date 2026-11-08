"""A49 focused pure tests; not a Qt/KWin or DAC product certification."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from michi.application.signal_truth_p1_owner_metrics import OwnerProjectionMeter
from scripts.benchmark_michi_truth_p1_a49 import (
    percentile,
    read_process,
)
from scripts.benchmark_michi_truth_p1_a49 import (
    run as bench_run,
)
from scripts.execute_michi_truth_r15c_a49 import (
    checkout_status,
    validate_nodes,
)
from scripts.execute_michi_truth_r15c_a49 import (
    run as matrix_run,
)


def f03(*, status="ACTIVE", plan="route-1", generation=11, port=21, binding=3):
    return {
        "status": status,
        "identity": {
            "plan_id": plan,
            "execution_generation": generation,
            "port_generation": port,
            "binding_generation": binding,
        },
    }


def test_real_duration_becomes_only_local_qt_projection_metric():
    meter = OwnerProjectionMeter()
    assert meter.observe(frame=f03(), elapsed_ns=1_250_000)
    item = meter.items(temporal_status="ACTIVE")[0]
    assert (item["name"], item["state"], item["value"], item["unit"]) == (
        "projection_build_ms",
        "OBSERVED",
        1.25,
        "ms",
    )
    assert item["producer"] == "ui_observer"
    assert item["count"] == 1
    assert item["p99"] == 1.25


@pytest.mark.parametrize("status", ("NONE", "NOT_ACTIVE", "HISTORICAL", "PENDING", ""))
def test_nonactive_f03_drops_metric(status):
    meter = OwnerProjectionMeter()
    meter.observe(frame=f03(), elapsed_ns=4_000_000)
    assert not meter.observe(frame=f03(status=status), elapsed_ns=1_000_000)
    assert meter.items(temporal_status="ACTIVE") == []


@pytest.mark.parametrize(
    "changed", ({"plan": "route-2"}, {"generation": 12}, {"port": 22}, {"binding": 4})
)
def test_new_f03_identity_invalidates_older_percentiles(changed):
    meter = OwnerProjectionMeter()
    meter.observe(frame=f03(), elapsed_ns=42_000_000)
    meter.observe(frame=f03(**changed), elapsed_ns=2_000_000)
    row = meter.items(temporal_status="ACTIVE")[0]
    assert row["count"] == 1 and row["p99"] == 2.0


@pytest.mark.parametrize(
    "changed",
    (
        {"plan": ""},
        {"generation": 0},
        {"port": 0},
        {"binding": 0},
        {"generation": True},
        {"port": True},
        {"binding": True},
    ),
)
def test_incomplete_f03_never_creates_fake_owner_scope(changed):
    meter = OwnerProjectionMeter()
    assert not meter.observe(frame=f03(**changed), elapsed_ns=1_000_000)
    assert not meter.items(temporal_status="ACTIVE")


def test_missed_input_identity_is_silent():
    meter = OwnerProjectionMeter()
    assert not meter.observe(frame={"status": "ACTIVE"}, elapsed_ns=1200)


def test_no_value_after_retire_even_if_requested_live():
    meter = OwnerProjectionMeter()
    meter.observe(frame=f03(), elapsed_ns=1200)
    meter.retire()
    assert meter.items(temporal_status="ACTIVE") == []


def test_bounded_cpu_readout_and_ranked_p99():
    meter = OwnerProjectionMeter(samples=16)
    for value in range(1, 41):
        assert meter.observe(frame=f03(), elapsed_ns=value * 1_000_000)
    row = meter.items(temporal_status="ACTIVE")[0]
    assert row["count"] == 16 and row["p99"] == 40.0 and row["p95"] == 40.0
    assert row["missing"] == 0


def test_negative_or_invalid_elapsed_rejected():
    meter = OwnerProjectionMeter()
    for elapsed in (-1, 1.0, True):
        with pytest.raises(ValueError):
            meter.observe(frame=f03(), elapsed_ns=elapsed)


def test_local_metric_does_not_generate_audio_dac_xrun_claims():
    meter = OwnerProjectionMeter()
    meter.observe(frame=f03(), elapsed_ns=8_000_000)
    row = meter.items(temporal_status="ACTIVE")[0]
    assert set(row) == {
        "name",
        "state",
        "value",
        "unit",
        "producer",
        "count",
        "missing",
        "p95",
        "p99",
    }
    for prohibited in (
        "xrun_events",
        "bit_perfect",
        "true_peak_dbtp",
        "audio_callback_p99_ms",
    ):
        assert prohibited not in json.dumps(row)


def test_popup_is_surgical_and_does_not_add_a_second_renderer():
    root = Path(__file__).resolve().parents[2]
    popup = (
        root / "src/michi/presentation/qml/player/SignalTruthPopup.qml"
    ).read_text()
    stage = (
        root / "src/michi/presentation/qml/components/MichiSignalPathView.qml"
    ).read_text()
    bridge = (root / "src/michi/presentation/signal_path_bridge.py").read_text()
    assert "metricItems: root.metricItems" in popup
    assert "temporalStatus: root.temporalStatus" in popup
    assert popup.count("MichiSignalTruthMetrics {") == 1
    assert "metricItems && metricItems.length > 0 ? 32 : 0" in popup
    assert stage.count("MichiSignalTruthMetrics {") == 0
    assert 'visible: root.temporalStatus === "ACTIVE"' in popup
    assert "def metricItems(self)" in bridge
    assert "perf_counter_ns() - started_ns" in bridge
    assert bridge.index("started_ns = perf_counter_ns()") < bridge.index(
        "self.state_changed.emit()"
    )
    assert "self._ui_projection_meter.observe(" in bridge
    assert not any(s in stage for s in ("Timer {", "Popup {", "AudioProcessingService"))


def test_metric_qml_title_identifies_real_scope():
    root = Path(__file__).resolve().parents[2]
    qml = (
        root / "src/michi/presentation/qml/components/MichiSignalTruthMetrics.qml"
    ).read_text()
    assert "Signal Truth projection time" in qml
    assert "projection_build_ms" in qml
    assert 'root.temporalStatus === "ACTIVE"' in qml


def test_benchmark_probe_reads_actual_linux_process_not_fake_xruns():
    ticks, rss = read_process(os.getpid())
    assert ticks >= 0 and rss > 0
    assert percentile([1, 2, 3, 4, 5], 0.99) == 5
    assert percentile([], 0.99) is None


def test_benchmark_without_pid_reports_not_run(tmp_path):
    target = tmp_path / "process.json"
    d = bench_run(["--scenario", "managed_dsp_ai", "--out", str(target)])
    assert d["overall"] == "NOT_RUN"
    assert d["xrun_count"]["state"] == "NOT_RUN"
    assert d["audio_callback_p99_ms"]["state"] == "NOT_RUN"
    assert d["qt_frame_p99_ms"]["state"] == "NOT_RUN"
    assert json.loads(target.read_text())["overall"] == "NOT_RUN"


def test_r15c_rejects_synthetic_checkout(tmp_path):
    out = tmp_path / "matrix.json"
    d = matrix_run(
        [
            "--product-root",
            str(Path(__file__).resolve().parents[2]),
            "--require-head",
            "d32228fbcc49c4f107e4295b1a70e31fde4d9b07",
            "--out",
            str(out),
        ]
    )
    assert len(d["cases"]) == 50
    assert (d["pass"], d["not_run"], d["fail_or_skip"]) == (0, 50, 0)
    assert d["overall"] == "NO_GO"
    assert not d["checkout_verified"]


def test_r15c_node_validation_fails_closed(tmp_path):
    assert validate_nodes(["../../secrets.py"], tmp_path) == ()
    assert (
        validate_nodes(["src/michi/application/audio_processing_service.py"], tmp_path)
        == ()
    )
    assert validate_nodes(["tests/fake.py"], tmp_path) == ()


def test_r15c_missing_checkout_gives_stop(tmp_path):
    okay, code = checkout_status(tmp_path, "abcd")
    assert not okay and code == "INCOMPLETE_PRODUCT_CHECKOUT"


from michi.application.signal_truth_p1_f05_adapter import project_f05_capabilities  # noqa: E402


def test_f05_quick_eq_action_requires_real_backend_and_applicability():
    f05 = {
        "capability_state": "queried",
        "strategies": ["BIQUAD_CASCADE", "GAIN"],
        "effective_state": "effective",
        "readback_proven": True,
    }
    items = project_f05_capabilities(f05, quick_eq_can_apply=True)
    eq = next(item for item in items if item["id"] == "parametric_eq")
    assert eq["state"] == "AVAILABLE" and eq["configAction"] == "OPEN_PROCESSING"
    assert not eq["effective"]  # F05 readback != OutputSession execution adoption


@pytest.mark.parametrize(
    "truth,apply",
    [
        (
            {"capability_state": "unknown", "strategies": ["BIQUAD_CASCADE", "GAIN"]},
            True,
        ),
        ({"capability_state": "queried", "strategies": ["BIQUAD_CASCADE"]}, True),
        (
            {"capability_state": "queried", "strategies": ["BIQUAD_CASCADE", "GAIN"]},
            False,
        ),
        ({"capability_state": "queried", "strategies": "BIQUAD_CASCADE, GAIN"}, True),
    ],
)
def test_no_quick_eq_enablement_without_all_owner_conditions(truth, apply):
    eq = next(
        v
        for v in project_f05_capabilities(truth, quick_eq_can_apply=apply)
        if v["id"] == "parametric_eq"
    )
    assert eq["configAction"] == "NONE" and not eq["effective"]


def test_no_future_dsp_advanced_feature_enabled_from_host_capability_alone():
    f05 = {
        "capability_state": "queried",
        "strategies": [
            "BIQUAD_CASCADE",
            "GAIN",
            "CONVOLUTION_FIR",
            "GRAPHIC_EQ_NBANDS",
        ],
    }
    items = project_f05_capabilities(f05, quick_eq_can_apply=True)
    for id in ("advanced_peq", "fir_convolution", "graphic_eq", "profile_library"):
        x = next(c for c in items if c["id"] == id)
        assert x["configAction"] == "NONE" and not x["effective"]


def test_settings_crud_needs_readback_not_selected_preset():
    base = {"capability_state": "queried", "strategies": []}
    fake = {"owner": "SETTINGS", "profile_crud_wired": True, "readback_proven": False}
    x = next(
        v
        for v in project_f05_capabilities(base, settings_receipt=fake)
        if v["id"] == "profile_library"
    )
    assert x["state"] != "AVAILABLE"
    proof = dict(fake, readback_proven=True)
    x = next(
        v
        for v in project_f05_capabilities(base, settings_receipt=proof)
        if v["id"] == "profile_library"
    )
    assert x["state"] == "AVAILABLE" and not x["effective"]


from scripts.inspect_michi_truth_dac_a49 import inspect_receipts  # noqa: E402
from scripts.verify_michi_truth_product_a49 import run as product_run  # noqa: E402
from scripts.verify_michi_truth_product_a49 import validate_source  # noqa: E402


def test_dac_qualification_is_not_inferred_from_seemingly_positive_receipt():
    source = {
        "family": "dop",
        "device_id": "dac:a",
        "base_commit_sha": "a" * 40,
        "capture_sha256": "f" * 64,
        "observed_at": "2026-11-08",
        "source_family": "dsd",
        "output_owner_receipt": "RUNNING",
        "execution_id": "exec-1",
        "dsd_executor_readback": "DOP_CARRIER_OBSERVED",
        "bit_perfect": True,
        "receiver_verified": True,
    }
    result = inspect_receipts([source])
    row = next(x for x in result["coverage"] if x["family"] == "dop")
    assert row["state"] == "UNVERIFIED_RECEIPTS_PRESENT"
    assert row["physical_certification"] == "NOT_RUN"
    assert row["receiver_interpretation"] == "NOT_RUN"
    assert result["qualification"] == "NO_GO"


def test_all_six_dac_families_require_observed_capability_receipts():
    results = inspect_receipts([])
    assert {v["family"] for v in results["coverage"]} == {
        "direct",
        "managed",
        "shared",
        "native_dsd",
        "dop",
        "dsd_pcm",
    }
    assert all(v["state"] == "NOT_RUN" for v in results["coverage"])


def test_product_gate_rejects_incomplete_fixture_without_mutating_it(tmp_path):
    # The fixture must be incomplete by construction: the real integration
    # checkout is a complete repository at the baseline, not a negative case.
    root = tmp_path / "incomplete"
    root.mkdir()
    assert (
        validate_source(root, "d32228fbcc49c4f107e4295b1a70e31fde4d9b07")
        == "INCOMPLETE_REPOSITORY"
    )
    source = tmp_path / "candidate.patch"
    source.write_text("")
    out = tmp_path / "product.json"
    result = product_run(
        [
            "--repo",
            str(root),
            "--patch",
            str(source),
            "--baseline-sha",
            "d32228fbcc49c4f107e4295b1a70e31fde4d9b07",
            "--out",
            str(out),
        ]
    )
    assert result["overall"] == "NO_GO" and result["blocker"] == "INCOMPLETE_REPOSITORY"
    assert result["github_mutated"] is False
    assert result["original_checkout_mutated"] is False
    assert not any(v["status"] == "PASS" for v in result["checks"].values())
