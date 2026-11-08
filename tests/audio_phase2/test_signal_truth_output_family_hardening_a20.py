"""A20 ST-02 exact PR245 source: immutable evidence, serialization and copies.

Software-level proof only, not an audio/DAC/Qt integration certificate.
"""

from __future__ import annotations

import copy
import json
import pickle
from collections.abc import Mapping
from dataclasses import asdict, replace
from enum import StrEnum

import pytest

from michi.domain.signal_truth import (
    OutputFamilyEvent,
    OutputFamilyState,
    SignalTruthRecorder,
)


class ConversionNode(StrEnum):
    SOURCE_DSD = "SOURCE_DSD"
    DSD_TO_PCM_DECODER = "DSD_TO_PCM_DECODER"


def receipt(runtime=None):
    if runtime is None:
        runtime = {
            "host_generation": 7,
            "negotiated": {"rate_hz": 96000},
            "conversion": {"nodes": [ConversionNode.SOURCE_DSD]},
        }
    return OutputFamilyEvent(
        family="dsd_pcm",
        state=OutputFamilyState.RUNNING,
        execution_id="exec:a20",
        runtime_identity=runtime,
    )


def test_mapping_contract_and_original_detached():
    original = {"negotiated": {"rate_hz": 96000}}
    ev = receipt(original)
    assert isinstance(ev.runtime_identity, Mapping)
    assert not isinstance(ev.runtime_identity, dict)
    original["negotiated"]["rate_hz"] = 8000
    assert ev.runtime_identity["negotiated"]["rate_hz"] == 96000
    assert dict(ev.runtime_identity)["negotiated"]["rate_hz"] == 96000


def test_runtime_mutation_attacks_are_refused():
    ev = receipt()
    data = ev.runtime_identity
    with pytest.raises(TypeError):
        dict.__setitem__(data, "host_generation", -1)
    with pytest.raises(TypeError):
        data["negotiated"]["rate_hz"] = 8000
    with pytest.raises(TypeError):
        data.update({"host_generation": -1})
    with pytest.raises(TypeError):
        data |= {"host_generation": -1}
    assert ev.runtime_identity["host_generation"] == 7
    assert ev.runtime_identity["negotiated"]["rate_hz"] == 96000


def test_deepcopy_receipt_remains_immutable():
    ev = copy.deepcopy(receipt())
    with pytest.raises(TypeError):
        ev.runtime_identity["negotiated"]["rate_hz"] = 1
    assert ev.runtime_identity["conversion"]["nodes"][0] == "SOURCE_DSD"


def test_pickle_receipt_roundtrip_remains_immutable():
    ev = pickle.loads(pickle.dumps(receipt()))
    with pytest.raises(TypeError):
        ev.runtime_identity["negotiated"]["rate_hz"] = 1


def test_replace_receipt_remains_immutable():
    ev = replace(receipt(), detail="updated")
    with pytest.raises(TypeError):
        ev.runtime_identity["host_generation"] = 1
    assert ev.detail == "updated"


def test_json_boundary_is_explicit_and_detached():
    ev = receipt()
    # A20 migration: a truly immutable Mapping is not a built-in dict;
    # callers must serialize through asdict or an explicit JSON boundary.
    with pytest.raises(TypeError):
        json.dumps(ev.runtime_identity)
    payload = asdict(ev)
    wire = json.dumps(payload, allow_nan=False)
    assert json.loads(wire)["runtime_identity"]["conversion"]["nodes"] == ["SOURCE_DSD"]
    payload["runtime_identity"]["negotiated"]["rate_hz"] = 100
    assert ev.runtime_identity["negotiated"]["rate_hz"] == 96000


def test_actual_output_bridge_mapping_access_protocol():
    ev = receipt({"negotiated": {"format": "S32LE", "rate_hz": 96000, "channels": 2}})
    # src/michi/presentation/audio_output_bridge.py:1047-1051 uses this exact API.
    runtime = dict(ev.runtime_identity or {})
    negotiated = dict(runtime.get("negotiated") or {})
    assert (int(negotiated.get("rate_hz") or 0), negotiated.get("format")) == (
        96000,
        "S32LE",
    )


def test_strenum_family_conversion_evidence_accepted_as_json_strings():
    ev = receipt(
        {
            "conversion": {
                "nodes": (ConversionNode.SOURCE_DSD, ConversionNode.DSD_TO_PCM_DECODER),
                "observed_nodes": [
                    {"node": ConversionNode.DSD_TO_PCM_DECODER, "level": "OBSERVED"}
                ],
            }
        }
    )
    data = asdict(ev)
    nodes = json.loads(json.dumps(data, allow_nan=False))["runtime_identity"][
        "conversion"
    ]["nodes"]
    assert nodes == ["SOURCE_DSD", "DSD_TO_PCM_DECODER"]


def test_runtime_none_and_empty_have_same_meaning_as_existing_contract():
    assert receipt({}).runtime_identity == {}
    ev = OutputFamilyEvent("shared", OutputFamilyState.RELEASED, runtime_identity=None)
    assert ev.runtime_identity is None
    assert asdict(ev)["runtime_identity"] is None


def test_recorder_revision_unchanged_on_rejected_wrong_type():
    rec = SignalTruthRecorder()
    before = rec.read_capture_state().revision
    with pytest.raises(TypeError):
        rec.record_output_family_event(receipt({"bad": b"bytes"}))
    assert rec.read_capture_state().revision == before
    assert rec.output_family_events == ()


@pytest.mark.parametrize(
    "bad",
    [
        {"x": float("nan")},
        {"x": float("inf")},
        {1: "not string"},
        {"set": {1, 2}},
        {"x": object()},
        {"x": "a" * 5000},
    ],
)
def test_refuses_noncanonical_or_oversized_facts(bad):
    with pytest.raises((ValueError, TypeError)):
        receipt(bad)


def test_oversized_breadth_refused():
    with pytest.raises(ValueError, match="limit"):
        receipt({f"key{i}": i for i in range(3000)})


def test_nested_list_cycle_refused():
    seq = []
    seq.append(seq)
    with pytest.raises(ValueError, match="cyclic"):
        receipt({"cycle": seq})


def test_repr_does_not_expose_identity_secrets():
    ev = receipt({"local_private_path": "/private/music/library.flac"})
    text = repr(ev)
    assert "/private/music/library.flac" not in text
    assert "_FrozenRuntimeFact" in text


def test_event_copy_does_not_modify_capture_history():
    rec = SignalTruthRecorder()
    ev = receipt()
    rec.record_output_family_event(ev)
    first = rec.read_capture_state()
    copied = copy.deepcopy(first.output_family_events[0])
    thawed = asdict(copied)["runtime_identity"]
    thawed["host_generation"] = -100
    assert first.output_family_events[0].runtime_identity["host_generation"] == 7
    current = rec.read_capture_state().output_family_events[0]
    assert current.runtime_identity["host_generation"] == 7
