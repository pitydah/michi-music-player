"""F11 Signal Truth bridge contract: projection only, never a proof upgrade."""

# ruff: noqa: N815 - the fake mirrors Qt Property camelCase names.

from __future__ import annotations

import threading
import time
from dataclasses import replace

from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QApplication

from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
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
    recorder._last_committed = snapshot
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

    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.EFFECTIVE,
            processing_generation=7,
            plan_id="plan:f11",
            pipeline_generation=1,
            readback_proven=True,
        )
    )
    bridge = SignalPathBridge(recorder, _Output(), _Matched())

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
        processing_verified=True,
    )
    assert contradicted == "contradicted"
    assert _path_proof_label(contradicted) == "Output mismatch"


def test_unverified_dsp_never_verifies_the_whole_path() -> None:
    class _UnverifiedDspProcessing(_Processing):
        truth = {
            "effective_state": "effective",
            "effective_revision": 3,
            "effective_plan_id": "dsp:other-execution",
        }

    snapshot = _snapshot()
    pcm = PcmTuple(44_100, "S16LE", 2, 16)
    dsp_snapshot = replace(
        snapshot,
        verdict=SignalTruthVerdict.DSP,
        device_negotiated=AlsaRuntimeEvidence(
            snapshot.identity, pcm, None, None, None, None, ""
        ),
    )
    bridge = SignalPathBridge(
        _recorder_with_active(dsp_snapshot),
        _Output(),
        _UnverifiedDspProcessing(),
    )

    assert bridge.pathProofState == "partially_verified"
    assert bridge.pathProofState != "verified"
    assert bridge.headline == "DSP detected · identity unverified"
    assert bridge.stages[2]["state"] == "unknown"


def test_source_discloses_the_track_name_and_decode_explains_the_engine_input() -> None:
    snapshot = _snapshot()
    bridge = SignalPathBridge(
        _recorder_with_active(snapshot),
        _Output(),
        _Processing(),
        playback_path_provider=lambda: "/music/Album/track_01.flac",
    )

    source = bridge.stages[0]
    assert ["File", "track_01.flac"] in source["detailRows"]
    assert "engine input" in bridge.stages[1]["detail"]


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
    recorder._last_committed = snapshot
    return recorder


def test_configuration_action_is_an_intent_only() -> None:
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    seen: list[str] = []
    bridge.configuration_action_requested.connect(seen.append)

    bridge.request_configuration("OPEN_PROCESSING")
    bridge.request_configuration("INVALID")

    assert seen == ["OPEN_PROCESSING"]


# A11 Qt-thread negative tests. The legacy module import above is untouched;
# new public identifiers are deliberately Michi-owned for the future rename.
class _TruthOwnerWitness(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.delivery_threads: list[int] = []

    @Slot()
    def on_update(self) -> None:
        self.delivery_threads.append(threading.get_ident())


def _pump_truth_owner(app: QApplication, predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.002)
    return predicate()


def _emit_truth_updates(recorder: SignalTruthRecorder, count: int = 1) -> None:
    for index in range(count):
        recorder.record_processing_event(
            ProcessingTruthEvent(
                state=ProcessingTruthState.REQUESTED,
                processing_generation=index + 1,
            )
        )


def test_truth_worker_event_only_projects_on_qt_owner() -> None:
    app = QApplication.instance() or QApplication([])
    owner = threading.get_ident()
    recorder = SignalTruthRecorder()
    projection_threads: list[int] = []
    bridge = SignalPathBridge(
        recorder,
        _Output(),
        _Processing(),
        playback_path_provider=lambda: (
            projection_threads.append(threading.get_ident()) or ""
        ),
    )
    witness = _TruthOwnerWitness()
    bridge.state_changed.connect(witness.on_update)
    projection_threads.clear()

    worker = threading.Thread(target=_emit_truth_updates, args=(recorder,))
    worker.start()
    worker.join(timeout=5.0)
    assert not worker.is_alive(), "worker blocked by UI"

    # No worker is permitted to reconstruct presentation QObject state.
    assert projection_threads == []
    assert witness.delivery_threads == []
    assert _pump_truth_owner(app, lambda: len(witness.delivery_threads) == 1)
    assert projection_threads == [owner]
    assert witness.delivery_threads == [owner]
    bridge.dispose()


def test_truth_worker_burst_uses_single_owner_refresh() -> None:
    app = QApplication.instance() or QApplication([])
    owner = threading.get_ident()
    recorder = SignalTruthRecorder()
    rebuild_threads: list[int] = []
    bridge = SignalPathBridge(
        recorder,
        _Output(),
        _Processing(),
        playback_path_provider=lambda: (
            rebuild_threads.append(threading.get_ident()) or ""
        ),
    )
    witness = _TruthOwnerWitness()
    bridge.state_changed.connect(witness.on_update)
    rebuild_threads.clear()

    worker = threading.Thread(target=_emit_truth_updates, args=(recorder, 250))
    worker.start()
    worker.join(timeout=5.0)
    assert not worker.is_alive()
    assert rebuild_threads == []
    assert witness.delivery_threads == []
    assert _pump_truth_owner(app, lambda: len(witness.delivery_threads) >= 1)
    app.processEvents()

    assert rebuild_threads == [owner], rebuild_threads
    assert witness.delivery_threads == [owner]
    assert bridge.generation == 1
    bridge.dispose()


def test_truth_dispose_discards_queued_owner_refresh() -> None:
    app = QApplication.instance() or QApplication([])
    recorder = SignalTruthRecorder()
    projection_threads: list[int] = []
    bridge = SignalPathBridge(
        recorder,
        _Output(),
        _Processing(),
        playback_path_provider=lambda: (
            projection_threads.append(threading.get_ident()) or ""
        ),
    )
    witness = _TruthOwnerWitness()
    bridge.state_changed.connect(witness.on_update)
    projection_threads.clear()

    worker = threading.Thread(target=_emit_truth_updates, args=(recorder,))
    worker.start()
    worker.join(timeout=5.0)
    assert not worker.is_alive()
    bridge.dispose()
    app.processEvents()
    assert projection_threads == []
    assert witness.delivery_threads == []


def test_truth_owner_updates_remain_synchronous_without_worker() -> None:
    app = QApplication.instance() or QApplication([])
    owner = threading.get_ident()
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    witness = _TruthOwnerWitness()
    bridge.state_changed.connect(witness.on_update)

    _emit_truth_updates(recorder)
    assert witness.delivery_threads == [owner]
    assert bridge.generation == 1
    bridge.dispose()
    app.processEvents()


def test_truth_reentrant_owner_notification_preserves_next_refresh() -> None:
    app = QApplication.instance() or QApplication([])
    owner = threading.get_ident()
    recorder = SignalTruthRecorder()
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    witnessed: list[int] = []

    def on_updated() -> None:
        witnessed.append(threading.get_ident())
        if len(witnessed) == 1:
            _emit_truth_updates(recorder)

    bridge.state_changed.connect(on_updated)
    _emit_truth_updates(recorder)
    assert _pump_truth_owner(app, lambda: len(witnessed) == 2)
    assert witnessed == [owner, owner]
    assert bridge.generation == 2
    bridge.dispose()


# A13 DSP regressions: output plan ID is NOT DSP plan ID, and the newest
# causal event must revoke an earlier effective receipt.
def _truth_dsp_event(
    state: ProcessingTruthState,
    *,
    revision: int,
    plan: str | None = "dsp:owner",
    pipeline: int | None = 1,
    readback: bool = False,
) -> ProcessingTruthEvent:
    return ProcessingTruthEvent(
        state=state,
        processing_generation=revision,
        plan_id=plan,
        host_generation=1,
        pipeline_generation=pipeline,
        readback_proven=readback,
    )


def _truth_effective_processing(revision: int = 3, plan: str = "dsp:owner"):
    processing = _Processing()
    processing.truth = {
        "effective_state": "effective",
        "effective_revision": revision,
        "effective_plan_id": plan,
    }
    return processing


def _truth_dsp_stage(recorder: SignalTruthRecorder, processing) -> dict:
    bridge = SignalPathBridge(recorder, _Output(), processing)
    return next(row for row in bridge.stages if row["id"] == "processing")


def test_truth_equal_output_and_dsp_plan_without_receipt_is_unverified() -> None:
    recorder = _recorder_with_active(_snapshot())
    stage = _truth_dsp_stage(recorder, _truth_effective_processing(3, plan="plan:f11"))
    assert stage["state"] == "unknown"
    assert "identity unverified" in stage["summary"]


def test_truth_latest_bypass_revokes_earlier_effective_receipt() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.BYPASSED, revision=4, plan=None)
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] != "transformed"


def test_truth_latest_unavailable_revokes_earlier_effective_receipt() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.UNAVAILABLE, revision=4, plan=None)
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] != "transformed"


def test_truth_newer_wrong_plan_revokes_older_matching_receipt() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(
            ProcessingTruthState.EFFECTIVE,
            revision=4,
            plan="dsp:other",
            readback=True,
        )
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] == "unknown"


def test_truth_dsp_effective_revision_must_match_current_owner() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=2, readback=True)
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing(revision=3))
    assert stage["state"] == "unknown"


def test_truth_new_request_does_not_resurrect_effective_on_same_pipeline() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.REQUESTED, revision=4)
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] != "transformed"


def test_truth_unscoped_terminal_blocks_unproven_effective_join() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(
            ProcessingTruthState.UNAVAILABLE,
            revision=4,
            plan=None,
            pipeline=None,
        )
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] == "unknown"


def test_truth_other_pipeline_terminal_does_not_revoke_current_proof() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(
            ProcessingTruthState.UNAVAILABLE,
            revision=4,
            pipeline=2,
            plan=None,
        )
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing())
    assert stage["state"] == "transformed"


def test_truth_new_valid_effective_reactivates_after_bypass() -> None:
    recorder = _recorder_with_active(_snapshot())
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.BYPASSED, revision=4, plan=None)
    )
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=5, readback=True)
    )
    stage = _truth_dsp_stage(recorder, _truth_effective_processing(revision=5))
    assert stage["state"] == "transformed"


def test_truth_aborted_preparation_is_not_historical_playback() -> None:
    recorder = SignalTruthRecorder()
    snapshot = _snapshot()
    recorder.begin_candidate(snapshot.plan)
    assert recorder.discard_candidate(snapshot.identity)
    assert recorder.last_snapshot is not None
    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    assert bridge.status == "NOT_ACTIVE"
    assert bridge.historical is False


def test_truth_last_committed_survives_failed_handover() -> None:
    recorder = SignalTruthRecorder()
    source = _snapshot()
    recorder.begin_candidate(source.plan)
    assert recorder.commit_candidate(source.identity)
    assert recorder.retire_active(source.identity)
    replacement_identity = replace(
        source.identity, execution_generation=2, port_generation=2
    )
    recorder.begin_candidate(replace(source.plan, identity=replacement_identity))
    assert recorder.discard_candidate(replacement_identity)

    bridge = SignalPathBridge(recorder, _Output(), _Processing())
    assert bridge.status == "HISTORICAL"
    assert bridge.identity["execution_generation"] == 1


# A15: One recorder capture must be the source of BOTH lifecycle and DSP
# receipts. Reading the event property separately would mix two revisions.
def test_truth_projection_consumes_only_one_capture() -> None:
    class _CaptureOnlyRecorder(SignalTruthRecorder):
        def __init__(self) -> None:
            super().__init__()
            self.capture_reads = 0

        def read_capture_state(self):
            self.capture_reads += 1
            return super().read_capture_state()

        @property
        def processing_events(self):
            raise AssertionError("a projection cannot read a second recorder epoch")

    recorder = _CaptureOnlyRecorder()
    recorder._active = _snapshot()
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    bridge = SignalPathBridge(recorder, _Output(), _truth_effective_processing())
    assert recorder.capture_reads == 1
    stage = next(row for row in bridge.stages if row["id"] == "processing")
    assert stage["state"] == "transformed"
    bridge.dispose()


def test_truth_concurrent_terminal_only_affects_subsequent_capture() -> None:
    class _InterleavingRecorder(SignalTruthRecorder):
        inject_terminal = False

        def read_capture_state(self):
            captured = super().read_capture_state()
            if self.inject_terminal:
                self.inject_terminal = False
                # Deterministic interleaving AFTER capture, BEFORE DSP projection.
                # Avoid a callback so the first frame is tested independently.
                with self._lock:
                    self._processing_events.append(
                        _truth_dsp_event(
                            ProcessingTruthState.BYPASSED, revision=4, plan=None
                        )
                    )
                    self._capture_revision += 1
            return captured

    recorder = _InterleavingRecorder()
    recorder._active = _snapshot()
    recorder.record_processing_event(
        _truth_dsp_event(ProcessingTruthState.EFFECTIVE, revision=3, readback=True)
    )
    recorder.inject_terminal = True
    bridge = SignalPathBridge(recorder, _Output(), _truth_effective_processing())
    stage = next(row for row in bridge.stages if row["id"] == "processing")
    assert stage["state"] == "transformed", "frame mixed two recorder epochs"

    bridge._on_source_changed()
    stage = next(row for row in bridge.stages if row["id"] == "processing")
    assert stage["state"] != "transformed", "terminal must revoke DSP on refresh"
    bridge.dispose()
