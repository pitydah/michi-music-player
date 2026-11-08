"""A42 pure projection tests; no Qt, no audio and no hardware implied."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from michi.application.signal_truth_frame import TruthFrame, publish_truth_frame  # noqa: E402

STAGES = ("source", "decode", "processing", "output", "device")


def base(*, canonical="RECONCILED", family="RUNNING_REPORTED", status="ACTIVE"):
    return {
        "status": status,
        "captureRevision": 12,
        "canonicalF03State": canonical,
        "canonicalF03Nodes": [
            {"kind": k, "state": "observed"}
            for k in ("source", "decode", "engine", "device")
        ],
        "pathProofState": "partially_verified",
        "pathProofLabel": "Ruta observada hasta ALSA",
        "pathVerdict": "observed",
        "reasonCodes": ["ST_CANONICAL_OBSERVED"],
        "identity": {
            "plan_id": "P",
            "execution_generation": 3,
            "stable_device_id": "Device",
            "extra_secret": "never",
        },
        "stages": [
            {
                "id": k,
                "title": k,
                "state": "observed",
                "summary": "observed",
                "detailRows": [["Fact", "Observed"]],
                "reasonCodes": ["ST_F03"],
            }
            for k in STAGES
        ],
        "familyEvidenceState": family,
        "dspExecutionState": "UNOBSERVED",
        "headline": "Ruta observada",
        "sourceIdentity": "test",
        "untrustedSecret": "must-not-publish",
        "fidelityClaim": "BIT_PERFECT",
        "operationOrderVerified": True,
    }


def test_active_canonical_preserves_bounded_f03_only():
    out = publish_truth_frame(base())
    assert out["status"] == "ACTIVE" and out["captureRevision"] == 12
    assert out["pathProofState"] == "partially_verified"
    assert [r["id"] for r in out["stages"]] == list(STAGES)
    assert out["fidelityClaim"] == "UNPROVEN"
    assert out["operationOrderVerified"] is False
    assert out["identity"] == {
        "plan_id": "P",
        "execution_generation": 3,
        "stable_device_id": "Device",
    }
    assert "untrustedSecret" not in out


def test_not_dsp_confirmed_from_old_processing_state():
    data = base()
    data["stages"][2]["state"] = "transformed"
    out = publish_truth_frame(data)
    assert out["stages"][2]["state"] == "unknown"
    assert out["stages"][2]["detailRows"] == []


def test_current_dsp_claim_only_passed_through_from_c6():
    data = base()
    data["stages"][2]["state"] = "transformed"
    data["dspExecutionState"] = "CURRENT_EXECUTION_CONFIRMED"
    assert publish_truth_frame(data)["stages"][2]["state"] == "transformed"


@pytest.mark.parametrize("status", ("PENDING", "NOT_ACTIVE", "HISTORICAL"))
def test_no_current_owner_fact_when_not_active(status):
    data = base(status=status)
    data["stages"][2]["state"] = "transformed"
    data["dspExecutionState"] = "CURRENT_EXECUTION_CONFIRMED"
    result = publish_truth_frame(data)
    assert result["dspExecutionState"] == "UNOBSERVED"
    assert result["familyEvidenceState"] == "UNOBSERVED"
    assert result["pathProofState"] != "partially_verified"
    assert result["stages"][2]["state"] != "transformed"


def test_owner_receipt_must_not_resurrect_foreign_f03():
    data = base(canonical="OWNER_LINK_REQUIRED")
    out = publish_truth_frame(data)
    assert out["stages"][0]["state"] == "unknown"
    assert out["stages"][1]["detailRows"] == []
    assert out["stages"][4]["state"] == "unknown"
    assert out["pathProofState"] == "partially_verified"
    assert out["identity"] == {}
    assert out["reasonCodes"] == []


def test_ready_is_not_running():
    data = base(canonical="OWNER_LINK_REQUIRED", family="READY_REPORTED")
    assert publish_truth_frame(data)["pathProofState"] == "pending"


@pytest.mark.parametrize("reason", ("REFUSED", "NO_CAPTURE", "OWNER_LINK_REQUIRED", ""))
def test_no_owner_or_f03_refuses_all_positive_labels(reason):
    data = base(canonical=reason, family="UNOBSERVED")
    data["stages"][2]["state"] = "transformed"
    out = publish_truth_frame(data)
    assert all(x["state"] == "unknown" for x in out["stages"])
    assert out["pathProofState"] == "no_path"
    assert out["dspExecutionState"] == "UNOBSERVED"
    assert out["presentationWarning"] == "ST_A42_NO_CANONICAL_F03_OR_OWNER_LINK"


def test_changed_revision_fails_closed():
    data = base()
    data["captureRevision"] = -1
    out = publish_truth_frame(data)
    assert out["presentationWarning"] == "ST_A42_INVALID_CAPTURE_REVISION"
    assert out["pathProofState"] == "no_path"


def test_wrong_f03_node_topology_fails_closed():
    data = base()
    data["canonicalF03Nodes"][1]["kind"] = "output"
    out = publish_truth_frame(data)
    assert out["presentationWarning"] == "ST_A42_INVALID_F03_NODE_TOPOLOGY"


def test_wrong_ui_topology_is_downgraded():
    data = base()
    data["stages"][1]["id"] = "output"
    out = publish_truth_frame(data)
    assert all(row["state"] == "unknown" for row in out["stages"])
    assert out["presentationWarning"] == "ST_A42_INVALID_UI_TOPOLOGY"
    assert out["pathProofState"] == "no_path"


def test_snapshot_is_deeply_frozen_and_serialization_detached():
    data = base()
    snap = TruthFrame.from_reconciled(data)
    with pytest.raises(TypeError):
        snap._payload["identity"]["plan_id"] = "mutation"
    with pytest.raises(TypeError):
        snap._payload["stages"][0]["state"] = "error"
    out = snap.to_qml()
    out["stages"][0]["detailRows"][0][0] = "modified"
    out["identity"]["plan_id"] = "modified"
    assert snap.to_qml()["identity"]["plan_id"] == "P"
    assert snap.to_qml()["stages"][0]["detailRows"][0][0] == "Fact"
    assert data["identity"]["plan_id"] == "P"


def test_no_raw_binary_or_unknown_properties_pass():
    data = base()
    data["alsaLocator"] = "/dev/private/path"
    data["key"] = b"secrets"
    assert "alsaLocator" not in publish_truth_frame(data)
    assert "key" not in publish_truth_frame(data)


def test_repeat_projection_is_deterministic_and_does_not_mutate_input():
    data = base()
    original = deepcopy(data)
    one = publish_truth_frame(data)
    two = publish_truth_frame(data)
    assert one == two and data == original


def test_unknown_ui_actions_and_source_path_not_exported():
    data = base()
    data["sourceIdentity"] = "/home/me/private/song.flac"
    data["configurationActions"] = ["OPEN_ENGINE", "EXECUTE_SHELL"]
    data["stages"][0]["configAction"] = "EXECUTE_SHELL"
    out = publish_truth_frame(data)
    assert out["sourceIdentity"] == ""
    assert out["configurationActions"] == ["OPEN_ENGINE"]
    assert out["stages"][0]["configAction"] == "NONE"


@pytest.mark.parametrize("family", ("managed", "native_dsd", "dop", "dsd_pcm"))
def test_four_owner_families_do_not_inherit_pcm_graph(family):
    data = base(canonical="OWNER_LINK_REQUIRED")
    data["audioFamily"] = family
    data["familyEvidenceState"] = "RUNNING_REPORTED"
    data["stages"][3]["summary"] = "Recibo del propietario OutputSession"
    result = publish_truth_frame(data)
    assert result["audioFamily"] == family
    assert result["pathProofState"] == "partially_verified"
    assert result["stages"][0]["state"] == "unknown"
    assert result["stages"][4]["state"] == "unknown"
    assert (
        result["pathProofLabel"] == "Recibo de salida; ruta completa no correlacionada"
    )
    assert result["fidelityClaim"] == "UNPROVEN"


@pytest.mark.parametrize("family", ("managed", "native_dsd", "dop", "dsd_pcm"))
def test_four_owner_families_no_receipt_cannot_claim_current_path(family):
    data = base(canonical="OWNER_LINK_REQUIRED", family="UNOBSERVED")
    data["audioFamily"] = family
    data["stages"][3]["state"] = "observed"
    result = publish_truth_frame(data)
    assert result["pathProofState"] == "no_path"
    assert result["stages"][3]["state"] == "unknown"
    assert result["familyEvidenceState"] == "UNOBSERVED"
