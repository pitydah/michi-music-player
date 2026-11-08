"""A47 P0 contract falsifiers. Pure isolated model, not full product/hardware QA."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "verify_michi_truth_p0_contract.py"
)
spec = importlib.util.spec_from_file_location("signal_truth_p0_contract", SCRIPT)
assert spec and spec.loader
import sys  # noqa: E402

mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def frame():
    return {
        "schema": mod.SCHEMA,
        "status": "ACTIVE",
        "identity": {
            "output_plan_id": "output.123",
            "execution_generation": 11,
            "port_generation": 8,
            "binding_generation": 3,
            "media_epoch": 9,
            "route_epoch": 17,
            "branch_id": "main",
            "endpoint_stable_id": "dac.local.01",
        },
        "family": {
            "source_family": "PCM",
            "sink_family": "PCM",
            "transport": "managed_pcm",
            "state": "RUNNING_REPORTED",
            "owner_receipt_id": "out.11",
            "receiver_evidence": "ALSA_NEGOTIATED",
            "carrier": None,
            "decoded_pcm": {"family": "PCM", "rate_hz": 44100},
        },
        "operations": [],
        "fidelity": {"claim": "UNPROVEN", "dac_analog_verified": False},
    }


def op(oid="op.1", kind="resample", predecessors=None, order_ref=None):
    return {
        "operation_instance_id": oid,
        "kind": kind,
        "branch_id": "main",
        "execution_generation": 11,
        "producer_id": "host.gst.02",
        "state": "RUNTIME_OBSERVED",
        "evidence_ref": "gst.pad.1",
        "evidence_class": "RUNTIME_NEGOTIATED",
        "input_format": {
            "family": "PCM",
            "rate_hz": 44100,
            "channels": 2,
            "significant_bits": 24,
        },
        "output_format": {"family": "PCM", "rate_hz": 96000, "channels": 2},
        "predecessors": predecessors or [],
        "order_evidence_ref": order_ref,
    }


def coverage():
    return {
        "family": "PCM",
        "boundary": "HOST_PCM_WRITER",
        "execution_id": "exec.11",
        "tap_id": "alsa.writer",
        "method": "SAMPLE_EXACT",
        "source_trace_id": "src.trace.01",
        "frame_start": 100,
        "frame_end": 110,
        "channels": ["L", "R"],
        "dropped_frames": 0,
        "segments": [
            {"channel": c, "start": 100, "end": 110, "exact_equal": True}
            for c in ("L", "R")
        ],
    }


def check_change(mutator, code):
    x = frame()
    mutator(x)
    assert code in mod.validate_envelope(x)


def test_valid_canonical_candidate():
    assert mod.validate_envelope(frame()) == ()


def test_schema_not_certification():
    x = frame()
    assert mod.validate_envelope(x) == ()
    assert x["fidelity"]["claim"] == "UNPROVEN"


@pytest.mark.parametrize(
    "field",
    [
        "execution_generation",
        "port_generation",
        "binding_generation",
        "media_epoch",
        "route_epoch",
    ],
)
def test_generation_nonpositive_rejected(field):
    check_change(lambda x: x["identity"].__setitem__(field, 0), "P0_IDENTITY_FENCE")


def test_boolean_generation_rejected():
    check_change(
        lambda x: x["identity"].__setitem__("route_epoch", True), "P0_IDENTITY_FENCE"
    )


def test_empty_device_rejected():
    check_change(
        lambda x: x["identity"].__setitem__("endpoint_stable_id", ""),
        "P0_IDENTITY_FENCE",
    )


def test_stale_operation_generation():
    check_change(
        lambda x: x["operations"].append({**op(), "execution_generation": 10}),
        "P0_OP_0_EPOCH_MISMATCH",
    )


def test_repeat_same_kind_with_distinct_ids_and_unknown_order_allowed():
    x = frame()
    x["operations"] = [op("src.1"), op("src.2")]
    assert mod.validate_envelope(x) == ()


def test_duplicate_instance_id_refused():
    x = frame()
    x["operations"] = [op("same"), op("same")]
    assert "P0_OP_1_IDENTITY_OR_DUPLICATE" in mod.validate_envelope(x)


def test_edge_without_owner_order_receipt_refused():
    x = frame()
    x["operations"] = [op("a"), op("b", predecessors=["a"])]
    assert "P0_OP_1_UNPROVEN_ORDER" in mod.validate_envelope(x)


def test_edge_with_order_receipt_is_structurally_valid_not_certified():
    x = frame()
    x["operations"] = [op("a"), op("b", predecessors=["a"], order_ref="topology.1")]
    assert mod.validate_envelope(x) == ()


def test_cycle_rejected():
    x = frame()
    x["operations"] = [
        op("a", predecessors=["b"], order_ref="topo.1"),
        op("b", predecessors=["a"], order_ref="topo.1"),
    ]
    assert "P0_OPERATION_DAG_INVALID" in mod.validate_envelope(x)


def test_outside_branch_predecessor_rejected():
    x = frame()
    x["operations"] = [op("a", predecessors=["foreign"], order_ref="topo.1")]
    assert "P0_OPERATION_DAG_INVALID" in mod.validate_envelope(x)


@pytest.mark.parametrize(
    "kind",
    [
        "peq",
        "fir",
        "gain",
        "headroom",
        "dither",
        "requantize",
        "mix",
        "resample",
        "channel-remap",
        "dsd-to-pcm",
        "dop-pack",
    ],
)
def test_known_kind_validated_without_claiming_runtime(kind):
    x = frame()
    x["operations"] = [op("a", kind)]
    assert mod.validate_envelope(x) == ()


def test_adopted_without_receipt_rejected():
    x = frame()
    x["operations"] = [{**op(), "state": "ADOPTED"}]
    assert "P0_OP_0_ADOPTION_UNPROVEN" in mod.validate_envelope(x)


def test_adopted_with_receipt_is_shape_only():
    x = frame()
    x["operations"] = [
        {**op(), "state": "ADOPTED", "adoption_receipt_id": "host.adopt.9"}
    ]
    assert mod.validate_envelope(x) == ()
    assert x["fidelity"]["claim"] == "UNPROVEN"


def test_zero_rate_rejected():
    x = frame()
    x["operations"] = [op()]
    x["operations"][0]["input_format"]["rate_hz"] = 0
    assert "P0_OP_0_INPUT_FORMAT" in mod.validate_envelope(x)


@pytest.mark.parametrize(
    "transport,src,sink",
    [
        ("direct_pcm", "PCM", "PCM"),
        ("managed_pcm", "PCM", "PCM"),
        ("shared_pcm", "PCM", "PCM"),
        ("dsd_to_pcm", "DSD", "PCM"),
        ("native_dsd", "DSD", "DSD"),
        ("dop", "DSD", "DSD"),
    ],
)
def test_six_family_modes_have_contract(transport, src, sink):
    x = frame()
    f = x["family"]
    f.update(transport=transport, source_family=src, sink_family=sink)
    f["carrier"] = (
        {"family": "PCM_CARRIER", "rate_hz": 176400} if transport == "dop" else None
    )
    if transport == "dsd_to_pcm":
        f["pcm_host_receipt"] = "gst.dsdpcm.1"
    if transport in ("native_dsd", "dop"):
        f["decoded_pcm"] = None
    assert mod.validate_envelope(x) == ()


def test_native_pcm_fabrication_refused():
    x = frame()
    x["family"].update(
        transport="native_dsd",
        source_family="DSD",
        sink_family="DSD",
        decoded_pcm={"family": "PCM"},
    )
    assert "P0_NATIVE_DSD_FAKE_PCM" in mod.validate_envelope(x)


def test_dop_pcm_fabrication_refused():
    x = frame()
    x["family"].update(
        transport="dop",
        source_family="DSD",
        sink_family="DSD",
        carrier={"family": "PCM_CARRIER", "rate_hz": 176400},
        decoded_pcm={"family": "PCM"},
    )
    assert "P0_DOP_FAKE_PCM" in mod.validate_envelope(x)


def test_dop_missing_carrier_rejected():
    x = frame()
    x["family"].update(transport="dop", source_family="DSD", sink_family="DSD")
    assert "P0_DOP_CARRIER_UNOBSERVED" in mod.validate_envelope(x)


def test_dsd_pcm_requires_effective_host_receipt():
    x = frame()
    x["family"].update(transport="dsd_to_pcm", source_family="DSD", sink_family="PCM")
    assert "P0_DSD_PCM_HOST_RECEIPT_REQUIRED" in mod.validate_envelope(x)


def test_shared_hwparams_without_source_receipt_rejected():
    x = frame()
    x["family"].update(transport="shared_pcm", alsa_negotiated={"rate_hz": 44100})
    assert "P0_SHARED_ALSA_PROOF_UNSCOPED" in mod.validate_envelope(x)


def test_ack_without_owner_running_not_eligible():
    x = frame()
    x["family"]["owner_receipt_id"] = None
    assert "P0_OUTPUT_OWNER_RECEIPT_MISSING" in mod.validate_envelope(x)


def test_external_measurement_must_have_id():
    x = frame()
    x["family"]["receiver_evidence"] = "EXTERNALLY_MEASURED"
    assert "P0_EXTERNAL_MEASUREMENT_ID" in mod.validate_envelope(x)


def test_positive_fidelity_claim_rejected_without_m115():
    x = frame()
    x["fidelity"]["claim"] = "MATCHED_COMPLETE"
    assert "P0_FIDELITY_M11_5_OWNER_REQUIRED" in mod.validate_envelope(x)


def test_analog_claim_rejected():
    x = frame()
    x["fidelity"]["dac_analog_verified"] = True
    assert "P0_ANALOG_CERTIFICATION_FORBIDDEN" in mod.validate_envelope(x)


def test_complete_coverage_digital_scope_only():
    r = mod.evaluate_pcm_coverage(coverage())
    assert r.verdict == mod.Coverage.MATCHED_COMPLETE
    assert r.to_dict()["physical_dac_verified"] is False
    assert r.compared_channel_frames == r.expected_channel_frames == 20


def test_partial_missing_lfe_channel():
    x = coverage()
    x["channels"].append("LFE")
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.MATCHED_PARTIAL


def test_mismatch_third_channel_detected():
    x = coverage()
    x["channels"].append("C")
    x["segments"].append(
        {"channel": "C", "start": 100, "end": 110, "exact_equal": False}
    )
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.MISMATCH


def test_partial_single_frame_not_complete():
    x = coverage()
    x["segments"] = [{"channel": "L", "start": 100, "end": 101, "exact_equal": True}]
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.MATCHED_PARTIAL


def test_discontinuity_not_complete():
    x = coverage()
    x["segments"][0]["end"] = 109
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.MATCHED_PARTIAL


def test_declared_drops_not_complete():
    x = coverage()
    x["dropped_frames"] = 1
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.MATCHED_PARTIAL


def test_overlapping_spans_contradicted():
    x = coverage()
    x["segments"].append(
        {"channel": "L", "start": 100, "end": 104, "exact_equal": True}
    )
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.CONTRADICTED


def test_non_pcm_unsupported():
    x = coverage()
    x["family"] = "DSD"
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.UNSUPPORTED


def test_hash_only_not_exact_evidence():
    x = coverage()
    x["method"] = "HASH64"
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.INCONCLUSIVE


def test_missing_provenance_inconclusive():
    x = coverage()
    x["source_trace_id"] = None
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.INCONCLUSIVE


def test_negative_malformed_empty_scope_inconclusive():
    x = coverage()
    x["frame_end"] = 99
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.INCONCLUSIVE


def test_input_data_not_mutated():
    x = frame()
    x["operations"] = [op()]
    original = deepcopy(x)
    assert not mod.validate_envelope(x)
    assert x == original


def test_matrix_ids_and_gates_are_complete():
    p = (
        Path(__file__).resolve().parents[2]
        / "docs/audio/phase2/F11_SIGNAL_TRUTH_A47_P0_ACCEPTANCE.json"
    )
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["schema"] == "michi.signal_truth.p0.acceptance.v1"
    assert len(data["gates"]) == 7
    assert {row["id"] for row in data["gates"]} == {
        "P0-ARCH",
        "P0-SCHEMA",
        "P0-OPS",
        "P0-FAMILIES",
        "P0-FIDELITY",
        "P0-CERT",
        "P0-DELIVERY",
    }
    assert len(data["r15c"]) == 50
    assert {r["id"] for r in data["r15c"]} == {f"R15C-{i:02d}" for i in range(1, 51)}
    assert all(row["product_status"] == "NOT_RUN" for row in data["r15c"])
    assert all(row["gate_status"] != "PASS" for row in data["gates"])


# A47 candidate read-model: repeatable operations without upgrading DSP/DAC claims.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from michi.application.signal_truth_frame import publish_truth_frame  # noqa: E402


def view_frame():
    ids = ["source", "decode", "processing", "output", "device"]
    return {
        "status": "ACTIVE",
        "captureRevision": 9,
        "canonicalF03State": "RECONCILED",
        "canonicalF03Nodes": [
            {"kind": k, "state": "observed"}
            for k in ("source", "decode", "engine", "device")
        ],
        "reasonCodes": ["ST_RESAMPLER_PRESENT"],
        "pathVerdict": "resampled",
        "identity": {"plan_id": "output.1", "execution_generation": 11},
        "stages": [
            {"id": k, "title": k, "summary": "reported", "state": "observed"}
            for k in ids
        ],
    }


def test_frame_repeatable_src_are_separate_instances():
    x = view_frame()
    x["operationInstances"] = [op("src.1"), op("src.2")]
    result = publish_truth_frame(x)
    assert len(result["operationInstances"]) == 2
    assert [o["operationInstanceId"] for o in result["operationInstances"]] == [
        "src.1",
        "src.2",
    ]
    assert all(o["orderVerified"] is False for o in result["operationInstances"])
    assert all(o["adoptionState"] == "UNVERIFIED" for o in result["operationInstances"])
    assert result["reasonCodes"] == ["ST_RESAMPLER_PRESENT"]
    assert result["fidelityClaim"] == "UNPROVEN"


def test_frame_separate_peq_fir_same_time():
    x = view_frame()
    x["operationInstances"] = [
        op("peq.1", "peq"),
        op("fir.1", "fir"),
        op("fir.2", "fir"),
    ]
    result = publish_truth_frame(x)
    assert [v["kind"] for v in result["operationInstances"]] == ["peq", "fir", "fir"]
    assert len(result["stages"]) == 5  # no forged extra F03 stages


def test_frame_adoption_input_not_promoted_without_authority():
    x = view_frame()
    x["operationInstances"] = [
        {**op(), "state": "ADOPTED", "adoption_receipt_id": "fake.1"}
    ]
    out = publish_truth_frame(x)
    assert out["operationInstances"][0]["adoptionState"] == "UNVERIFIED"
    assert "adoption_receipt_id" not in out["operationInstances"][0]


def test_frame_graph_edges_not_forged_from_input_order():
    x = view_frame()
    x["operationInstances"] = [
        op("a"),
        op("b", predecessors=["a"], order_ref="topology.1"),
    ]
    out = publish_truth_frame(x)
    assert all(o["predecessors"] == [] for o in out["operationInstances"])
    assert out["operationOrderVerified"] is False


def test_frame_duplicate_operation_ids_rejected_without_wiping_f03():
    x = view_frame()
    x["operationInstances"] = [op("a"), op("a")]
    out = publish_truth_frame(x)
    assert out["operationInstances"] == []
    assert out["operationPresentationWarning"] == "ST_A47_OPERATION_ID_DUPLICATE"
    assert out["reasonCodes"] == ["ST_RESAMPLER_PRESENT"]


def test_frame_foreign_generation_not_exposed():
    x = view_frame()
    x["operationInstances"] = [{**op(), "execution_generation": 99}]
    out = publish_truth_frame(x)
    assert out["operationInstances"] == []
    assert (
        out["operationPresentationWarning"] == "ST_A47_OPERATION_IDENTITY_OR_PROVENANCE"
    )


def test_frame_historical_has_no_current_operations():
    x = view_frame()
    x["status"] = "HISTORICAL"
    x["operationInstances"] = [op()]
    out = publish_truth_frame(x)
    assert out["operationInstances"] == []
    assert out["operationPresentationWarning"] == "ST_A47_OPERATION_SCOPE_NOT_ACTIVE"


def test_frame_legacy_f03_without_operations_unchanged():
    x = view_frame()
    out = publish_truth_frame(x)
    assert out["operationInstances"] == []
    assert out["operationPresentationWarning"] == ""
    assert out["reasonCodes"] == ["ST_RESAMPLER_PRESENT"]


def test_frame_sensitive_operation_payload_stripped():
    x = view_frame()
    x["operationInstances"] = [
        {
            **op(),
            "title": "secret album",
            "token": "sk-private",
            "url": "https://private-host/track",
            "source_path": "/home/user/song.flac",
        }
    ]
    out = publish_truth_frame(x)
    text = json.dumps(out["operationInstances"])
    assert "private-host" not in text and "/home/" not in text
    assert "secret album" not in text and "sk-private" not in text


def test_frame_operation_unbounded_list_refused():
    x = view_frame()
    x["operationInstances"] = [op(f"item.{i}") for i in range(25)]
    out = publish_truth_frame(x)
    assert out["operationInstances"] == []
    assert out["operationPresentationWarning"] == "ST_A47_OPERATION_COUNT_REFUSED"


def test_frame_operations_are_detached_from_original():
    x = view_frame()
    x["operationInstances"] = [op()]
    original = deepcopy(x)
    out = publish_truth_frame(x)
    out["operationInstances"][0]["kind"] = "gain"
    assert x == original
    assert publish_truth_frame(x)["operationInstances"][0]["kind"] == "resample"


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("status", [], "P0_TEMPORAL"),
        ("transport", [], "P0_TRANSPORT_UNSUPPORTED"),
        ("receiver_evidence", [], "P0_RECEIVER_EVIDENCE"),
        ("state", [], "P0_FAMILY_STATE"),
    ],
)
def test_malformed_unhashable_fields_are_refused_not_crashes(field, value, expected):
    x = frame()
    if field == "status":
        x[field] = value
    else:
        x["family"][field] = value
    assert expected in mod.validate_envelope(x)


def test_unhashable_operation_kind_refused():
    x = frame()
    x["operations"] = [{**op(), "kind": []}]
    assert "P0_OP_0_KIND_OR_STATE" in mod.validate_envelope(x)


def test_unhashable_channel_identifier_safe():
    x = coverage()
    x["segments"][0]["channel"] = []
    assert mod.evaluate_pcm_coverage(x).verdict == mod.Coverage.CONTRADICTED
