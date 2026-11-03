"""F11 Signal Truth bridge contract: projection only, never a proof upgrade."""

# ruff: noqa: N815 - the fake mirrors Qt Property camelCase names.

from __future__ import annotations

from dataclasses import replace

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    DecodedRuntimeEvidence,
    EngineRuntimeEvidence,
    OutputPlanEvidence,
    ProcessingTruthEvent,
    ProcessingTruthState,
    SignalTruthIdentity,
    SignalTruthRecorder,
    SignalTruthSnapshot,
    SignalTruthVerdict,
    SourceFileFactsEvidence,
)
from michi.presentation.signal_path_bridge import (
    SignalPathBridge,
    _path_proof_label,
    _path_proof_state,
)

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

    assert bridge.headline == "No active path"
    assert bridge.proofLevel == "Not verified"
    assert bridge.status == "NOT_ACTIVE"
    assert bridge.indicatorState == "none"
    assert len(bridge.stages) == 5
    assert [stage["id"] for stage in bridge.stages] == [
        "source",
        "decode",
        "processing",
        "output",
        "device",
    ]
    assert bridge.stages[0]["state"] == "unknown"
    assert bridge.stages[0]["first"] is True
    assert bridge.stages[-1]["last"] is True
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
    assert bridge.proofLevel == "Source · host · device"
    assert bridge.status == "ACTIVE"
    assert bridge.active is True
    assert bridge.historical is False
    assert bridge.indicatorState == "observed"
    assert bridge.stages[0]["summary"] == "FLAC"
    assert bridge.stages[0]["detail"] == "16-bit · 44.1 kHz"
    assert bridge.stages[0]["first"] is True
    assert bridge.stages[-1]["last"] is True
    assert bridge.stages[2]["summary"] == "Bypassed"
    serialized = str(bridge.stages) + bridge.headline + bridge.proofLevel
    for forbidden in _FORBIDDEN:
        assert forbidden not in serialized


def test_historical_snapshot_is_never_presented_as_active() -> None:
    recorder = SignalTruthRecorder()
    snapshot = _snapshot()
    recorder._last = snapshot
    bridge = SignalPathBridge(recorder, _Output(), _Processing())

    assert bridge.status == "HISTORICAL"
    assert bridge.active is False
    assert bridge.historical is True
    assert bridge.headline == "Last playback · historical"
    assert bridge.indicatorState == "historical"
    assert all(stage.get("historical") is True for stage in bridge.stages)
    assert all(stage["state"] != "historical" for stage in bridge.stages)
    assert bridge.statusLabel == "Last playback · historical"


def test_stopped_transport_demotes_the_active_snapshot_to_historical() -> None:
    bridge = SignalPathBridge(
        _recorder_with_active(_snapshot()),
        _Output(),
        _Processing(),
        playback_status_provider=lambda: "stopped",
    )

    assert bridge.status == "HISTORICAL"
    assert bridge.active is False
    assert bridge.historical is True
    assert bridge.indicatorState == "historical"
    assert bridge.headline == "Last playback · historical"


def test_candidate_snapshot_is_pending_not_effective() -> None:
    recorder = SignalTruthRecorder()
    recorder._candidate = _snapshot()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())

    assert bridge.status == "PENDING"
    assert bridge.active is False
    assert bridge.historical is False
    assert bridge.indicatorState == "pending"
    assert "Preparation" in bridge.headline or "Preparing" in bridge.headline


def test_standard_converters_do_not_claim_dsp_processing() -> None:
    snapshot = _snapshot()
    engine = EngineRuntimeEvidence(
        identity=snapshot.identity,
        effective_pcm=PcmTuple(44_100, "S16LE", 2, 16),
        sink_factory="alsasink",
        sink_device="hw:0,0",
        graph_factories=("audioconvert", "audioresample", "alsasink"),
        graph_inspection_complete=True,
        software_gain=None,
        muted=None,
        sink_provides_clock=None,
        sink_clock_is_pipeline_clock=None,
        slave_method=None,
    )
    bridge = SignalPathBridge(
        _recorder_with_active(replace(snapshot, engine_effective=engine)),
        _Output(),
        _Processing(),
    )

    processing = next(stage for stage in bridge.stages if stage["id"] == "processing")
    assert processing["state"] == "observed"
    assert processing["summary"] == "Bypassed"
    assert "DSP observed" not in processing["summary"]


def test_mismatched_processing_runtime_never_claims_effective_dsp() -> None:
    class _Mismatched(_Processing):
        truth = {
            "effective_state": "effective",
            "effective_revision": 7,
            "effective_plan_id": "plan:other",
        }

    bridge = SignalPathBridge(
        _recorder_with_active(_snapshot()),
        _Output(),
        _Mismatched(),
    )

    processing = next(stage for stage in bridge.stages if stage["id"] == "processing")
    assert processing["state"] == "unknown"
    assert "identity unverified" in processing["summary"]
    assert processing["detail"]


def test_matching_processing_receipt_is_the_only_dsp_claim() -> None:
    class _Matched(_Processing):
        truth = {
            "effective_state": "effective",
            "effective_revision": 7,
            "effective_plan_id": "plan:f11",
        }
        bands = [{"gainDb": 6.0}, {"gainDb": 0.0}]

    bridge = SignalPathBridge(
        _recorder_with_active(_snapshot()),
        _Output(),
        _Matched(),
    )

    processing = next(stage for stage in bridge.stages if stage["id"] == "processing")
    assert processing["state"] == "transformed"
    assert processing["summary"] == "DSP active"
    assert "bands" not in processing["summary"]
    assert bridge.indicatorState == "transformed"


def test_processing_receipt_binds_to_the_output_pipeline_not_the_plan_id() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.EFFECTIVE,
            processing_generation=3,
            plan_id="dsp:quick-eq",
            bit_perfect=False,
            host_generation=1,
            pipeline_generation=1,
            readback_proven=True,
        )
    )

    class _MatchingPipeline(_Processing):
        truth = {
            "effective_state": "effective",
            "effective_revision": 3,
            "effective_plan_id": "dsp:quick-eq",
        }

    bridge = SignalPathBridge(recorder, _Output(), _MatchingPipeline())

    processing = next(stage for stage in bridge.stages if stage["id"] == "processing")
    assert processing["state"] == "transformed"
    assert processing["summary"] == "DSP active"
    assert ["Pipeline generation", "1"] in processing["detailRows"]
    assert bridge.headline == "Processing active"
    assert bridge.indicatorState == "transformed"


def test_processing_receipt_from_another_pipeline_never_claims_effect() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.EFFECTIVE,
            processing_generation=3,
            plan_id="dsp:quick-eq",
            bit_perfect=False,
            host_generation=1,
            pipeline_generation=2,
            readback_proven=True,
        )
    )

    class _MatchingPlan(_Processing):
        truth = {
            "effective_state": "effective",
            "effective_revision": 3,
            "effective_plan_id": "dsp:quick-eq",
        }

    bridge = SignalPathBridge(recorder, _Output(), _MatchingPlan())

    processing = next(stage for stage in bridge.stages if stage["id"] == "processing")
    assert processing["state"] == "unknown"
    assert "identity unverified" in processing["summary"]


def _snapshot() -> SignalTruthSnapshot:
    identity = SignalTruthIdentity(
        plan_id="plan:f11",
        execution_generation=1,
        port_generation=1,
        binding_generation=1,
        stable_device_id="usb:f11",
        stable_endpoint_signature=None,
    )
    pcm = PcmTuple(44_100, "S16LE", 2, 16)
    return SignalTruthSnapshot(
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


def _recorder_with_active(snapshot: SignalTruthSnapshot) -> SignalTruthRecorder:
    recorder = SignalTruthRecorder()
    recorder._active = snapshot
    return recorder


def test_quality_badge_fields_are_typed_and_never_parsed_from_labels() -> None:
    snapshot = _snapshot()
    bridge = SignalPathBridge(
        _recorder_with_active(snapshot),
        _Output(),
        _Processing(),
    )

    assert bridge.sourceQualityClass == "pcm_standard"
    assert bridge.sourceFormatLabel == "FLAC"
    assert bridge.sourceRateDepthLabel == "16-bit · 44.1 kHz"
    assert bridge.pathProofState == "partially_verified"
    assert bridge.pathProofLabel == "Partially verified"
    assert "Nominal quality: FLAC 16-bit" in bridge.qualityAccessibleText
    assert "No active path" not in bridge.qualityAccessibleText


def test_wav_container_wins_over_the_raw_codec_name() -> None:
    snapshot = _snapshot()
    facts = SourceFileFactsEvidence(
        snapshot.identity,
        container="WAVE",
        codec="pcm_s16le",
        nominal_pcm=PcmTuple(44_100, "S16LE", 2, 16),
    )
    bridge = SignalPathBridge(
        _recorder_with_active(replace(snapshot, source_file_facts=facts)),
        _Output(),
        _Processing(),
    )

    assert bridge.sourceFormatLabel == "WAVE"
    assert bridge.sourceQualityClass == "pcm_standard"


def test_hires_quality_requires_more_than_sixteen_bits_or_48_khz() -> None:
    snapshot = _snapshot()
    pcm = PcmTuple(96_000, "S24LE", 2, 24)
    facts = SourceFileFactsEvidence(
        snapshot.identity, container="FLAC", codec="flac", nominal_pcm=pcm
    )
    bridge = SignalPathBridge(
        _recorder_with_active(replace(snapshot, source_file_facts=facts)),
        _Output(),
        _Processing(),
    )

    assert bridge.sourceQualityClass == "pcm_hires"
    assert bridge.sourceRateDepthLabel == "24-bit · 96 kHz"


def test_dsd_and_lossy_are_distinct_quality_classes() -> None:
    snapshot = _snapshot()
    dsd_facts = SourceFileFactsEvidence(
        snapshot.identity, container="DSF", codec="dsd64", nominal_pcm=None
    )
    dsd_bridge = SignalPathBridge(
        _recorder_with_active(replace(snapshot, source_file_facts=dsd_facts)),
        _Output(),
        _Processing(),
    )
    assert dsd_bridge.sourceQualityClass == "dsd"
    assert dsd_bridge.sourceFormatLabel == "DSD64"
    assert dsd_bridge.sourceRateDepthLabel == "1-bit"

    lossy_facts = SourceFileFactsEvidence(
        snapshot.identity, container="MP3", codec="mp3", nominal_pcm=None
    )
    lossy_bridge = SignalPathBridge(
        _recorder_with_active(replace(snapshot, source_file_facts=lossy_facts)),
        _Output(),
        _Processing(),
    )
    assert lossy_bridge.sourceQualityClass == "lossy"
    assert lossy_bridge.sourceFormatLabel == "MP3"


def test_historical_and_contradicted_paths_never_publish_verified_proof() -> None:
    snapshot = _snapshot()
    historical = SignalPathBridge(
        _recorder_with_last(snapshot),
        _Output(),
        _Processing(),
    )
    assert historical.pathProofState == "historical"
    assert historical.pathProofLabel == "Last playback"
    assert "Verified path" not in historical.qualityAccessibleText

    contradicted = _path_proof_state(
        temporal_status="ACTIVE",
        verdict_state="contradicted",
        tone="error",
        proof_parts=["Source", "host", "transport", "device"],
    )
    assert contradicted == "contradicted"
    assert _path_proof_label(contradicted) == "Output mismatch"


def test_device_stage_prefers_route_name_over_raw_usb_identity() -> None:
    class _NamedOutput(_Output):
        devices = [
            {
                "stableDeviceId": "usb:f11",
                "displayName": "Studio DAC",
            }
        ]

    bridge = SignalPathBridge(
        _recorder_with_active(_snapshot()),
        _NamedOutput(),
        _Processing(),
    )

    device = next(stage for stage in bridge.stages if stage["id"] == "device")
    assert device["summary"] == "Studio DAC"
    assert ["Stable ID", "usb:f11"] in device["detailRows"]


def _recorder_with_last(snapshot: SignalTruthSnapshot) -> SignalTruthRecorder:
    recorder = SignalTruthRecorder()
    recorder._last = snapshot
    return recorder


def test_configuration_action_is_an_intent_only() -> None:
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    seen: list[str] = []
    bridge.configuration_action_requested.connect(seen.append)

    bridge.request_configuration("OPEN_PROCESSING")
    bridge.request_configuration("INVALID")

    assert seen == ["OPEN_PROCESSING"]
