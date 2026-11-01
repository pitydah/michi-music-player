"""F11 Signal Truth bridge contract: projection only, never a proof upgrade."""

# ruff: noqa: N815 - the fake mirrors Qt Property camelCase names.

from __future__ import annotations

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    DecodedRuntimeEvidence,
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthRecorder,
    SignalTruthSnapshot,
    SignalTruthVerdict,
    SourceFileFactsEvidence,
)
from michi.presentation.signal_path_bridge import SignalPathBridge

_FORBIDDEN = (
    "Bit-perfect playback",
    "Exclusive verified",
    "Native DSD preserved",
    "DoP verified end-to-end",
)


class _Signal:
    def connect(self, _callback) -> None:
        return None


class _Output:
    state_changed = _Signal()
    signalTruthLabel = "Not verified"
    signalTruthSummary = ""
    signalTruthReasonCodes = []
    activeDeviceId = ""
    currentFormat = ""

    def property(self, name: str, fallback=None):
        return getattr(self, name, fallback)


class _Processing:
    state_changed = _Signal()
    truth = {
        "effective_state": "bypassed",
        "effective_revision": 0,
    }
    bands = []
    preampDb = 0.0


def test_without_truth_the_bridge_never_claims_verification() -> None:
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())

    assert bridge.headline == "Not verified"
    assert bridge.proofLevel == "Not verified"
    assert len(bridge.stages) == 5
    assert [stage["id"] for stage in bridge.stages] == [
        "source",
        "decode",
        "processing",
        "output",
        "device",
    ]
    assert all(forbidden not in bridge.headline for forbidden in _FORBIDDEN)


def test_observed_snapshot_projects_canonical_facts_and_no_future_claims() -> None:
    recorder = SignalTruthRecorder()
    identity = SignalTruthIdentity(
        plan_id="plan:f11",
        execution_generation=1,
        port_generation=1,
        binding_generation=1,
        stable_device_id="usb:f11",
        stable_endpoint_signature=None,
    )
    pcm = PcmTuple(44_100, "S16LE", 2, 16)
    snapshot = SignalTruthSnapshot(
        identity=identity,
        plan=OutputPlanEvidence(identity, pcm, "alsasink", "hw:0,0", False),
        source_file_facts=SourceFileFactsEvidence(
            identity, container="FLAC", codec="flac", nominal_pcm=pcm
        ),
        decoded_runtime=DecodedRuntimeEvidence(identity, pcm),
        engine_effective=None,
        device_negotiated=None,
        anomalies=(),
        verdict=SignalTruthVerdict.DIRECT,
        reasons=(),
    )
    recorder._active = snapshot
    bridge = SignalPathBridge(recorder, _Output(), _Processing())

    assert bridge.headline == "Direct path"
    assert bridge.proofLevel == "Source · host · transport"
    assert bridge.stages[0]["summary"] == "flac · FLAC"
    assert bridge.stages[2]["summary"] == "Bypassed"
    serialized = str(bridge.stages) + bridge.headline + bridge.proofLevel
    for forbidden in _FORBIDDEN:
        assert forbidden not in serialized


def test_configuration_action_is_an_intent_only() -> None:
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    seen: list[str] = []
    bridge.configuration_action_requested.connect(seen.append)

    bridge.request_configuration("OPEN_PROCESSING")
    bridge.request_configuration("INVALID")

    assert seen == ["OPEN_PROCESSING"]
