"""A11 architectural schema checks; these tests do NOT validate runtime audio.

No extra runtime dependencies: standard-library structural/semantic checks.
The dedicated documentation workflow also validates Draft 2020-12 with jsonschema.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_DOCS = _ROOT / "docs/audio/phase2"
_SCHEMA = _DOCS / "F11_SIGNAL_TRUTH_FRAME_V1.schema.json"
_EXAMPLES = _DOCS / "F11_SIGNAL_TRUTH_FRAME_EXAMPLES_A11.json"
_EXPECTED_STAGES = ("SOURCE", "DECODE", "PROCESSING", "OUTPUT", "DEVICE")


def _schema() -> dict:
    return json.loads(_SCHEMA.read_text(encoding="utf-8"))


def _examples() -> dict:
    return json.loads(_EXAMPLES.read_text(encoding="utf-8"))["examples"]


def _semantic_check(frame: dict) -> None:
    """Small executable *cross-field* contract, not a JSON Schema replacement."""
    assert frame["schema"] == "michi.truth_frame.v1"
    assert frame["capture_revision"] >= 0
    assert frame["temporal"] in ("NOT_ACTIVE", "PENDING", "ACTIVE", "HISTORICAL")
    if frame["temporal"] == "NOT_ACTIVE":
        assert frame["identity"] is None
        assert frame["family"] == "UNKNOWN"
    else:
        assert frame["identity"] is not None
    if frame["family"] in ("DOP", "NATIVE_DSD"):
        assert frame["source"]["nominal_pcm"] is None
        assert frame["route"]["negotiated_pcm"] is None
    if frame["dsp"]["correlation"] == "CONFIRMED":
        assert frame["temporal"] == "ACTIVE"
        assert frame["dsp"]["state"] == "EFFECTIVE"
        assert frame["dsp"]["readback_proven"] is True
        assert frame["dsp"]["source_execution_ref"]
        assert frame["dsp"]["pipeline_generation"] is not None
        assert frame["dsp"]["host_generation"] is not None
        assert frame["dsp"]["processing_generation"] is not None
    if frame["quality"]["fidelity_proof"] in ("MATCHED_PARTIAL", "MATCHED_COMPLETE"):
        assert frame["quality"]["proof_authority"] in ("M11_5", "DAC_V35")
        assert any(x["boundary"] == "SAMPLE_COMPARE" for x in frame["provenance"])
    assert tuple(s["id"] for s in frame["stages"]) == _EXPECTED_STAGES
    ids = [op["instance_id"] for op in frame["operations"]]
    assert len(ids) == len(set(ids)), "operation instances must be unique"
    graph = {}
    for op in frame["operations"]:
        predecessors = op["predecessors"]
        if op["order_state"] == "UNKNOWN":
            assert op["order_index"] is None
            assert not predecessors
        else:
            assert op["order_index"] is not None
            assert all(p in ids for p in predecessors)
        graph[op["instance_id"]] = predecessors
    marked: set[str] = set()
    visiting: set[str] = set()

    def visit(node: str) -> None:
        assert node not in visiting, "observed operation order may not be cyclic"
        if node in marked:
            return
        visiting.add(node)
        for predecessor in graph[node]:
            visit(predecessor)
        visiting.remove(node)
        marked.add(node)

    for node in graph:
        visit(node)


def test_schema_has_draft_2020_12_and_closed_root() -> None:
    s = _schema()
    assert s["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert s["additionalProperties"] is False
    assert s["properties"]["schema"]["const"] == "michi.truth_frame.v1"


def test_required_core_contract_fields_are_closed() -> None:
    s = _schema()
    assert set(s["required"]) == set(s["properties"])
    for key in ("identity", "source", "dsp", "route", "quality"):
        subs = s["properties"][key]
        if key != "identity":
            assert subs["additionalProperties"] is False
            assert set(subs["required"]) == set(subs["properties"])


def test_three_fixtures_cover_idle_direct_and_dop_pending() -> None:
    x = _examples()
    assert set(x) == {"idle", "direct_pcm", "dop_pending"}
    for f in x.values():
        _semantic_check(f)
    assert x["direct_pcm"]["route"]["last_observed_boundary"] == "ALSA"
    assert x["dop_pending"]["quality"]["fidelity_proof"] == "NOT_ESTABLISHED"


def test_dop_carrier_separate_from_musical_pcm() -> None:
    s = _schema()["properties"]["route"]
    assert "carrier_pcm" in s["properties"]
    assert "negotiated_pcm" in s["properties"]
    assert "dac_interpretation" in s["properties"]
    f = copy.deepcopy(_examples()["dop_pending"])
    f["route"]["carrier_pcm"] = {
        "transport_format": "S24_3LE",
        "rate_hz": 176400,
        "channels": 2,
        "significant_bits": 24,
    }
    _semantic_check(f)
    f["route"]["negotiated_pcm"] = f["route"]["carrier_pcm"]
    with pytest.raises(AssertionError):
        _semantic_check(f)


def test_last_playback_cannot_be_an_aborted_candidate() -> None:
    f = copy.deepcopy(_examples()["idle"])
    f["temporal"] = "HISTORICAL"
    with pytest.raises(AssertionError):
        _semantic_check(f)


def test_dsp_confirmed_requires_owner_scope_and_readback() -> None:
    f = copy.deepcopy(_examples()["direct_pcm"])
    f["dsp"]["correlation"] = "CONFIRMED"
    with pytest.raises(AssertionError):
        _semantic_check(f)
    f["dsp"].update(
        {
            "state": "EFFECTIVE",
            "readback_proven": True,
            "processing_plan_id": "dsp:plan-b",
            "source_execution_ref": "exec:3",
            "pipeline_generation": 3,
            "host_generation": 1,
            "processing_generation": 2,
            "last_event_sequence": 8,
        }
    )
    _semantic_check(f)
    f["dsp"]["host_generation"] = None
    with pytest.raises(AssertionError):
        _semantic_check(f)


def test_matched_complete_needs_sample_authority_and_provenance() -> None:
    f = copy.deepcopy(_examples()["direct_pcm"])
    f["quality"]["fidelity_proof"] = "MATCHED_COMPLETE"
    with pytest.raises(AssertionError):
        _semantic_check(f)
    f["quality"]["proof_authority"] = "M11_5"
    f["provenance"].append(
        {
            "boundary": "SAMPLE_COMPARE",
            "owner": "M11_5",
            "evidence_ref": "comparison:fixture",
            "generation": 3,
        }
    )
    _semantic_check(f)


def test_operation_cycles_and_duplicates_fail_closed() -> None:
    f = copy.deepcopy(_examples()["direct_pcm"])
    one = {
        "instance_id": "src:a",
        "kind": "RESAMPLE",
        "observation": "OBSERVED",
        "order_state": "OBSERVED",
        "order_index": 1,
        "predecessors": ["fir:b"],
        "evidence_refs": ["host:fixture"],
    }
    two = {
        "instance_id": "fir:b",
        "kind": "FIR",
        "observation": "OBSERVED",
        "order_state": "OBSERVED",
        "order_index": 2,
        "predecessors": ["src:a"],
        "evidence_refs": ["host:fixture"],
    }
    f["operations"] = [one, two]
    with pytest.raises(AssertionError):
        _semantic_check(f)
    f["operations"] = [one, dict(one)]
    with pytest.raises(AssertionError):
        _semantic_check(f)


def test_unordered_ops_never_have_invented_edges() -> None:
    f = copy.deepcopy(_examples()["direct_pcm"])
    f["operations"] = [
        {
            "instance_id": "fir:1",
            "kind": "FIR",
            "observation": "INSTALLED",
            "order_state": "UNKNOWN",
            "order_index": None,
            "predecessors": [],
            "evidence_refs": [],
        }
    ]
    _semantic_check(f)
    f["operations"][0]["predecessors"] = ["src:1"]
    with pytest.raises(AssertionError):
        _semantic_check(f)


def test_schema_contract_prohibits_surprising_export_fields() -> None:
    s = _schema()
    assert s["additionalProperties"] is False
    forbidden = {"path", "file_path", "access_token", "remote_ip", "usb_serial"}
    assert not (forbidden & set(s["properties"]))
    assert not (forbidden & set(s["properties"]["provenance"]["items"]["properties"]))


def test_architecture_doc_labels_approval_as_pending() -> None:
    p = _DOCS / "F11_SIGNAL_TRUTH_ARCHITECTURE_CLOSURE_A11.md"
    t = p.read_text(encoding="utf-8")
    assert "CANONICAL_APPROVAL_PENDING" in t
    assert "NO_GO_F11_CLOSURE" in t
    assert "ST-ADR-028" in t
    assert "ST-ADR-027" in t
    assert "A11.11. Catálogo de pruebas" in t
