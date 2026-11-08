"""A46 P0 causal presentation regression: synthetic 5+N bridge-shaped data.

These do NOT certify actual QML loading, Qt owner, audio runtime, DAC or the
unmodified full product checkout. They are deterministic counterexample tests.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from itertools import combinations
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from michi.application.signal_truth_frame import TruthFrame, publish_truth_frame  # noqa: E402

ANCHORS = ("source", "decode", "processing", "output", "device")
DYNAMIC = ("resample", "channel-remap", "fir")


def _frame(
    dynamic=(),
    *,
    status="ACTIVE",
    canonical="RECONCILED",
    family="UNOBSERVED",
    dsp="UNOBSERVED",
):
    ids = ANCHORS[:3] + tuple(dynamic) + ANCHORS[3:]
    return {
        "status": status,
        "captureRevision": 42,
        "canonicalF03State": canonical,
        "canonicalF03Nodes": [
            {"kind": k, "state": "observed"}
            for k in ("source", "decode", "engine", "device")
        ],
        "identity": {"plan_id": "p:42", "execution_generation": 6},
        "pathProofState": "partially_verified",
        "pathVerdict": "transformed",
        "reasonCodes": ["ST_RESAMPLER_PRESENT", "ST_DSP_PRESENT"],
        "familyEvidenceState": family,
        "dspExecutionState": dsp,
        "operationsObservedUnordered": ["resampler", "remix", "fir"],
        "operationOrderVerified": True,
        "stages": [
            {
                "id": sid,
                "title": sid,
                "summary": f"fact from F11 bridge: {sid}",
                "state": "transformed"
                if sid in DYNAMIC + ("processing",)
                else "observed",
                "detail": f"producer-reported: {sid}",
                "reasonCodes": ["ST_RESAMPLER_PRESENT"],
                "detailRows": [["provenance", "bridge-reported"]],
            }
            for sid in ids
        ],
    }


@pytest.mark.parametrize(
    "extra",
    [
        ("resample",),
        ("channel-remap",),
        ("fir",),
        ("resample", "channel-remap"),
        ("resample", "channel-remap", "fir"),
    ],
)
def test_regression_a45_p0_preserves_bridge_5_plus_n(extra):
    result = publish_truth_frame(_frame(extra))
    expected = ANCHORS[:3] + extra + ANCHORS[3:]
    assert result.get("presentationWarning") != "ST_A42_INVALID_UI_TOPOLOGY"
    assert tuple(row["id"] for row in result["stages"]) == expected
    assert result["reasonCodes"] == ["ST_RESAMPLER_PRESENT", "ST_DSP_PRESENT"]
    assert result["identity"]["plan_id"] == "p:42"
    assert result["pathVerdict"] == "transformed"
    assert result["pathProofState"] == "partially_verified"
    assert result["operationOrderVerified"] is False
    assert tuple(row["index"] for row in result["stages"]) == tuple(
        range(len(expected))
    )
    assert all(row["count"] == len(expected) for row in result["stages"])
    assert sum(bool(row["first"]) for row in result["stages"]) == 1
    assert sum(bool(row["last"]) for row in result["stages"]) == 1


@pytest.mark.parametrize(
    "extra", [extra for size in range(0, 4) for extra in combinations(DYNAMIC, size)]
)
def test_all_eight_observed_dynamic_combinations_are_bounded(extra):
    out = publish_truth_frame(_frame(extra))
    assert len(out["stages"]) == 5 + len(extra)
    assert all(row["id"] != "unknown" for row in out["stages"])


def test_src_and_remix_keep_reported_transformation_but_not_pcm_bitperfect():
    out = publish_truth_frame(_frame(("resample", "channel-remap")))
    assert out["stages"][3]["state"] == "transformed"
    assert out["stages"][4]["state"] == "transformed"
    assert out["fidelityClaim"] == "UNPROVEN"
    assert out["operationOrderVerified"] is False


def test_fir_is_not_promoted_by_graph_presence_without_adoption_proof():
    out = publish_truth_frame(_frame(("fir",)))
    fir = out["stages"][3]
    assert fir["state"] == "unknown"
    assert "adopción no acreditada" in fir["summary"]
    assert fir["detailRows"] == []
    assert out["dspExecutionState"] == "UNOBSERVED"


def test_fir_stage_may_show_transform_when_owner_has_confirmed_execution():
    out = publish_truth_frame(_frame(("fir",), dsp="CURRENT_EXECUTION_CONFIRMED"))
    assert out["stages"][3]["state"] == "transformed"
    assert out["fidelityClaim"] == "UNPROVEN"


@pytest.mark.parametrize(
    "bad_ids",
    [
        ANCHORS[:3] + ("resample", "resample") + ANCHORS[3:],
        ANCHORS[:3] + ("unknown-filter",) + ANCHORS[3:],
        ("resample",) + ANCHORS,
        ANCHORS + ("fir",),
        ("source", "processing", "decode", "output", "device"),
        ("source", "decode", "processing", "device", "output"),
        ANCHORS[:3] + ("fir", "fir", "fir") + ANCHORS[3:],
    ],
)
def test_invalid_or_ambiguous_topology_still_fails_closed(bad_ids):
    payload = _frame()
    payload["stages"] = [{"id": name, "state": "transformed"} for name in bad_ids]
    out = publish_truth_frame(payload)
    assert out["presentationWarning"] == "ST_A42_INVALID_UI_TOPOLOGY"
    assert out["pathProofState"] == "no_path"
    assert out["reasonCodes"] == []
    assert all(row["state"] == "unknown" for row in out["stages"])
    assert out["operationsObservedUnordered"] == []


def test_invalid_capture_revision_revokes_all_dynamic_claims():
    data = _frame(("resample", "fir"))
    data["captureRevision"] = -1
    out = publish_truth_frame(data)
    assert out["presentationWarning"] == "ST_A42_INVALID_CAPTURE_REVISION"
    assert out["pathVerdict"] == "unknown"
    assert all(stage["state"] == "unknown" for stage in out["stages"])
    assert out["operationsObservedUnordered"] == []


def test_owner_family_without_f03_binding_cannot_inherit_pcm_dynamic_stages():
    out = publish_truth_frame(
        _frame(
            ("resample", "channel-remap", "fir"),
            canonical="OWNER_LINK_REQUIRED",
            family="RUNNING_REPORTED",
        )
    )
    assert out["pathProofState"] == "partially_verified"
    assert all(
        stage["state"] == "unknown" for stage in out["stages"] if stage["id"] in DYNAMIC
    )
    assert out["reasonCodes"] == []
    assert out["operationsObservedUnordered"] == []
    assert out["fidelityClaim"] == "UNPROVEN"


@pytest.mark.parametrize("status", ["PENDING", "NOT_ACTIVE", "HISTORICAL"])
def test_noncurrent_capture_does_not_inherit_live_transformations(status):
    out = publish_truth_frame(_frame(("resample", "fir"), status=status))
    assert all(stage["state"] != "transformed" for stage in out["stages"])
    assert out["operationsObservedUnordered"] == []
    assert out["fidelityClaim"] == "UNPROVEN"


def test_dynamic_stages_frozen_and_detached_without_mutating_source():
    data = _frame(("resample", "channel-remap", "fir"))
    pristine = deepcopy(data)
    frozen = TruthFrame.from_reconciled(data)
    with pytest.raises(TypeError):
        frozen._payload["stages"][3]["summary"] = "forged"
    detached = frozen.to_qml()
    detached["stages"][3]["summary"] = "modified"
    assert frozen.to_qml()["stages"][3]["summary"] != "modified"
    assert data == pristine


def test_unknown_props_and_risky_actions_not_emitted_from_dynamic_row():
    data = _frame(("resample",))
    data["stages"][3]["secret"] = "/home/user/private-token"
    data["stages"][3]["configAction"] = "EXECUTE_COMMAND"
    out = publish_truth_frame(data)
    assert "secret" not in out["stages"][3]
    assert out["stages"][3]["configAction"] == "NONE"


def test_dynamic_provenance_must_not_claim_unproved_order():
    out = publish_truth_frame(_frame(("resample", "channel-remap", "fir")))
    assert out["operationOrderVerified"] is False
    assert out["fidelityClaim"] == "UNPROVEN"
    assert "orderReceipt" not in out


@pytest.mark.parametrize("field", ["status", "pathProofState"])
def test_unhashable_malformed_header_fails_closed_not_exception(field):
    data = _frame(("resample",))
    data[field] = ["malformed", "non-scalar"]
    out = publish_truth_frame(data)
    assert (
        out["status"] == "NOT_ACTIVE"
        if field == "status"
        else out["pathProofState"] == "no_path"
    )
    assert out["fidelityClaim"] == "UNPROVEN"


def test_unhashable_stage_state_sanitized_without_losing_valid_topology():
    data = _frame(("resample",))
    data["stages"][3]["state"] = ["transformed"]
    out = publish_truth_frame(data)
    assert [row["id"] for row in out["stages"]] == list(
        ANCHORS[:3] + ("resample",) + ANCHORS[3:]
    )
    assert out["stages"][3]["state"] == "unknown"
    assert out["fidelityClaim"] == "UNPROVEN"
