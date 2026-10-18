"""AP2-F05 — ADDITIVE DSP evidence through the ONE SignalTruthRecorder.

The DAC verdict stream is untouched: processing state convergence is a
separate, passive event stream on the canonical recorder (no second
recorder, no Direct fabrication, tri-state bit_perfect preserved).
"""

from __future__ import annotations

import pytest

from michi.application.audio_processing_service import AudioProcessingService
from michi.domain.signal_truth import (
    ProcessingTruthEvent,
    ProcessingTruthState,
    SignalTruthRecorder,
)
from michi.infrastructure.audio_processing.native_mapping import (
    NativeProcessingMapping,
)
from tests.audio_phase2.test_processing_capabilities import (
    _FakeProcessingTransport,
    _transaction_plan,
)


class _BypassTransport(_FakeProcessingTransport):
    def bypass_processing(self) -> dict:
        return {"bypassed": True}


def test_processing_convergence_events_are_additive_and_tristate() -> None:
    recorder = SignalTruthRecorder()
    service = AudioProcessingService(
        native_mapping=NativeProcessingMapping(), truth_recorder=recorder
    )
    plan = _transaction_plan()[1]
    transport = _BypassTransport()

    revision = service.note_requested()
    candidate = service.begin_candidate(
        plan,
        host_generation=1,
        transport=transport,
        processing_generation=revision,
    )
    receipt = service.commit_candidate(candidate, transport=transport)
    service.publish_effective(receipt)
    latency = service.processing_truth()["latency"]
    assert latency["expected_samples"] == plan.total_latency_samples
    assert latency["source"] == "compiled_plan"
    assert latency["pipeline_samples"] is None
    assert latency["sink_samples"] is None
    assert latency["physical"] == "not_measured"
    service.bypass_processing(transport=transport)
    assert service.processing_truth()["latency"]["expected_samples"] is None

    states = [event.state for event in recorder.processing_events]
    assert states == [
        ProcessingTruthState.REQUESTED,
        ProcessingTruthState.PREPARING,
        ProcessingTruthState.EFFECTIVE,
        ProcessingTruthState.BYPASSED,
    ]
    effective = recorder.processing_events[2]
    assert effective.plan_id == plan.plan_id
    assert effective.bit_perfect is False
    # Correlation with the execution that was actually proven.
    assert effective.host_generation == 1
    assert effective.pipeline_generation == candidate.pipeline_generation
    assert effective.runtime_identity == "fake:playbin3/audio-filter"
    assert effective.readback_proven is True
    preparing = recorder.processing_events[1]
    assert preparing.pipeline_generation == candidate.pipeline_generation
    assert all(
        event.bit_perfect is None
        for event in recorder.processing_events
        if event.state is not ProcessingTruthState.EFFECTIVE
    )
    # No DAC verdict was fabricated by DSP evidence.
    assert recorder.active_snapshot is None
    assert recorder.last_snapshot is None


def test_host_loss_records_unavailable_without_dac_truth() -> None:
    recorder = SignalTruthRecorder()
    service = AudioProcessingService(
        native_mapping=NativeProcessingMapping(), truth_recorder=recorder
    )
    service.note_requested()
    service.mark_host_lost("SIGKILL")
    last = recorder.processing_events[-1]
    assert last.state is ProcessingTruthState.UNAVAILABLE
    assert last.detail == "SIGKILL"
    assert last.bit_perfect is None
    assert recorder.active_snapshot is None


def test_processing_evidence_can_never_claim_bit_perfect() -> None:
    recorder = SignalTruthRecorder()
    with pytest.raises(ValueError):
        recorder.record_processing_event(
            ProcessingTruthEvent(
                state=ProcessingTruthState.EFFECTIVE,
                processing_generation=1,
                bit_perfect=True,
            )
        )
