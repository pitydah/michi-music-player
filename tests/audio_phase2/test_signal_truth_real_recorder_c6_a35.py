"""AP2-F11 A35: C6 against PR245 recorder + A26 owner-delivery implementation.

Upstream source is an exact-blob-sha mirror, not a full checkout. Qt, OutputSession
wiring, physical hardware and F03 semantic projection are intentionally NOT_RUN.
"""

from __future__ import annotations

from michi.application.signal_truth_causal_view import build_c6_qml_overlay
from michi.application.signal_truth_delivery import (
    PublicationKey,
    PublicationLedger,
    project_family_delivery,
    publish_family_fact,
)
from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    OutputFamilyEvent,
    OutputFamilyState,
    OutputPlanEvidence,
    ProcessingTruthEvent,
    ProcessingTruthState,
    SignalTruthIdentity,
    SignalTruthRecorder,
)


def _recorder(cls=SignalTruthRecorder) -> SignalTruthRecorder:
    recorder = cls()
    identity = SignalTruthIdentity(
        plan_id="output:plan-A",
        execution_generation=4,
        port_generation=13,
        binding_generation=2,
        stable_device_id="test-dac",
        stable_endpoint_signature="test-port",
    )
    pcm = PcmTuple(96000, "S24_3LE", 2, 24)
    recorder.begin_candidate(
        OutputPlanEvidence(
            identity=identity,
            requested_pcm=pcm,
            sink_factory="alsasink",
            sink_device="hw:2,0",
            fixed_gain_required=True,
        )
    )
    assert recorder.commit_candidate(identity)
    return recorder


def _family(state=OutputFamilyState.RUNNING):
    return OutputFamilyEvent(
        family="managed",
        state=state,
        execution_id="output-exec:alpha",
        device_id="test-dac",
        bit_perfect=None,
    )


def _owner():
    return {
        "family": "managed",
        "state": "running",
        "execution_id": "output-exec:alpha",
        "stable_device_id": "test-dac",
        "generation": 4,
        "binding_generation": 2,
        "host_generation": 9,
    }


def _f05():
    return {
        "effective_state": "effective",
        "effective_plan_id": "dsp:plan-X",
        "effective_revision": 3,
        "runtime_identity": "host:dsp-real",
        "readback_proven": True,
    }


def _dsp(state=ProcessingTruthState.EFFECTIVE):
    return ProcessingTruthEvent(
        state=state,
        processing_generation=3,
        plan_id="dsp:plan-X",
        host_generation=9,
        pipeline_generation=13,
        runtime_identity="host:dsp-real",
        readback_proven=True,
    )


def _frame(recorder):
    return {
        "status": "ACTIVE",
        "captureRevision": recorder.read_capture_state().revision,
        "pathVerdict": "unknown",
        "reasonCodes": ["CANONICAL_F03_UNCHANGED"],
        "stages": [
            {"id": x, "summary": f"original-{x}"}
            for x in ("source", "decode", "processing", "output", "device")
        ],
    }


def _project(recorder, ledger, frame, *, owner_reader=_owner, dsp_reader=_f05):
    return build_c6_qml_overlay(
        frame_payload=frame,
        recorder=recorder,
        owner_scope_reader=owner_reader,
        f05_truth_reader=dsp_reader,
        linked_execution_reader=lambda snapshot: (
            "output-exec:alpha" if snapshot is recorder.active_snapshot else None
        ),
        family_delivery_reader=lambda owner: project_family_delivery(
            ledger,
            recorder=recorder,
            family="managed",
            execution_id=owner.get("execution_id"),
            owner_epoch=4,
        ),
    )


def test_real_recorder_delivery_joins_family_but_not_dsp_without_adoption():
    recorder = _recorder()
    ledger = PublicationLedger()
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "output-exec:alpha", 4),
        recorder=recorder,
        build_event=_family,
    )
    recorder.record_processing_event(_dsp())
    frame = _frame(recorder)
    view = _project(recorder, ledger, frame)
    assert view["audioFamily"] == "managed"
    assert view["familyEvidenceState"] == "RUNNING_REPORTED"
    assert view["dspExecutionState"] == "MOTOR_EFFECTIVE"
    assert view["stages"][2]["state"] == "unknown"
    assert view["pathVerdict"] == "unknown"
    assert view["reasonCodes"] == ["CANONICAL_F03_UNCHANGED"]
    assert all(
        stage["id"] == expected
        for stage, expected in zip(
            view["stages"],
            ["source", "decode", "processing", "output", "device"],
            strict=False,
        )
    )


def test_real_recorder_terminal_invalidates_running_and_current_dsp():
    recorder = _recorder()
    ledger = PublicationLedger()
    for state in (OutputFamilyState.RUNNING, OutputFamilyState.UNAVAILABLE):
        publish_family_fact(
            ledger=ledger,
            key=PublicationKey("managed", "output-exec:alpha", 4),
            recorder=recorder,
            build_event=lambda state=state: _family(state),
        )
    recorder.record_processing_event(_dsp())
    view = _project(recorder, ledger, _frame(recorder))
    assert view["familyEvidenceState"] == "TERMINATED"
    assert view["dspExecutionState"] == "UNOBSERVED"


def test_real_recorder_processing_bypass_later_revokes_motor_evidence():
    recorder = _recorder()
    ledger = PublicationLedger()
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "output-exec:alpha", 4),
        recorder=recorder,
        build_event=_family,
    )
    recorder.record_processing_event(_dsp())
    recorder.record_processing_event(
        ProcessingTruthEvent(
            state=ProcessingTruthState.BYPASSED,
            processing_generation=4,
            plan_id=None,
            pipeline_generation=None,
        )
    )
    view = _project(recorder, ledger, _frame(recorder))
    assert view["familyEvidenceState"] == "RUNNING_REPORTED"
    assert view["dspExecutionState"] == "UNOBSERVED"


def test_real_recorder_owner_f05_changes_during_read_discards_overlay():
    recorder = _recorder()
    ledger = PublicationLedger()
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "output-exec:alpha", 4),
        recorder=recorder,
        build_event=_family,
    )
    recorder.record_processing_event(_dsp())
    reads = 0

    def changing_f05():
        nonlocal reads
        reads += 1
        truth = _f05()
        if reads == 2:
            truth["effective_state"] = "bypassed"
        return truth

    frame = _frame(recorder)
    view = _project(recorder, ledger, frame, dsp_reader=changing_f05)
    assert reads == 2
    assert view["presentationWarning"] == "ST_C6_CROSS_OWNER_READ_UNSTABLE"
    assert view["stages"] == frame["stages"]
    assert view["dspExecutionState"] == "UNOBSERVED"


def test_real_recorder_stream_counters_include_evictions_but_do_not_certify_producer():
    recorder = SignalTruthRecorder()
    for i in range(70):
        recorder.record_output_family_event(
            OutputFamilyEvent(
                family="managed",
                state=OutputFamilyState.RUNNING,
                execution_id=f"e{i}",
            )
        )
        recorder.record_processing_event(
            ProcessingTruthEvent(
                state=ProcessingTruthState.REQUESTED,
                processing_generation=i,
            )
        )
    capture = recorder.read_capture_state()
    assert capture.output_event_sequence == 70
    assert capture.processing_event_sequence == 70
    assert capture.output_evicted_count == 6
    assert capture.processing_evicted_count == 6
    assert len(capture.output_family_events) == len(capture.processing_events) == 64
    assert capture.output_event_sequence - capture.output_evicted_count == 64
    assert not hasattr(capture, "producer_continuity_certified")


def test_unvalidated_output_receipt_cannot_confirm_dsp():
    recorder = _recorder()
    ledger = PublicationLedger()  # Nothing acknowledged.
    recorder.record_output_family_event(_family())
    recorder.record_processing_event(_dsp())
    view = _project(recorder, ledger, _frame(recorder))
    assert view["dspExecutionState"] != "CURRENT_EXECUTION_CONFIRMED"
    assert view["familyEvidenceState"] == "UNOBSERVED"
    assert "ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED" in view["familyEvidenceReasons"]


def test_lost_terminal_delivery_revokes_last_running_even_if_owner_is_stale():
    class TerminalLossRecorder(SignalTruthRecorder):
        def record_output_family_event(self, event):
            if event.state is OutputFamilyState.UNAVAILABLE:
                return None  # swallowed delivery, source remains outdated
            return super().record_output_family_event(event)

    recorder = _recorder(TerminalLossRecorder)
    ledger = PublicationLedger()
    key = PublicationKey("managed", "output-exec:alpha", 4)
    accepted = publish_family_fact(
        ledger=ledger, key=key, recorder=recorder, build_event=_family
    )
    assert accepted.status.value == "ACCEPTED_IN_RECORDER"
    dropped = publish_family_fact(
        ledger=ledger,
        key=key,
        recorder=recorder,
        build_event=lambda: _family(OutputFamilyState.UNAVAILABLE),
    )
    assert dropped.status.value == "FAILED"
    frame = _frame(recorder)
    frame["captureRevision"] = recorder.read_capture_state().revision
    view = _project(recorder, ledger, frame)
    assert view["familyEvidenceState"] == "UNOBSERVED"
    assert view["dspExecutionState"] == "UNOBSERVED"
    assert "ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED" in view["familyEvidenceReasons"]


def test_native_dsd_real_recorder_never_inherits_pcm_decode_rows():
    recorder = _recorder()
    ledger = PublicationLedger()
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("native_dsd", "output-exec:alpha", 4),
        recorder=recorder,
        build_event=lambda: OutputFamilyEvent(
            family="native_dsd",
            state=OutputFamilyState.RUNNING,
            execution_id="output-exec:alpha",
            device_id="test-dac",
        ),
    )
    frame = _frame(recorder)
    frame["stages"][1]["detailRows"] = [["Decoded PCM", "24/96"]]
    frame["stages"][3]["detailRows"] = [["Negotiated PCM", "S24_3LE"]]
    view = build_c6_qml_overlay(
        frame_payload=frame,
        recorder=recorder,
        owner_scope_reader=lambda: dict(_owner(), family="native_dsd"),
        f05_truth_reader=_f05,
        linked_execution_reader=lambda snapshot: (
            "output-exec:alpha" if snapshot is recorder.active_snapshot else None
        ),
        family_delivery_reader=lambda owner: project_family_delivery(
            ledger,
            recorder=recorder,
            family="native_dsd",
            execution_id="output-exec:alpha",
            owner_epoch=4,
        ),
    )
    assert view["audioFamily"] == "native_dsd"
    assert "no hay decodificación PCM" in view["stages"][1]["summary"]
    assert view["stages"][1]["detailRows"] == []
    assert view["stages"][3]["detailRows"] == []
    assert view["reasonCodes"] == ["CANONICAL_F03_UNCHANGED"]
    assert view["dspExecutionState"] != "CURRENT_EXECUTION_CONFIRMED"


def test_dop_real_recorder_never_confirms_dac_reception_from_carrier():
    recorder = _recorder()
    ledger = PublicationLedger()
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("dop", "output-exec:alpha", 4),
        recorder=recorder,
        build_event=lambda: OutputFamilyEvent(
            family="dop",
            state=OutputFamilyState.RUNNING,
            execution_id="output-exec:alpha",
            device_id="test-dac",
        ),
    )
    frame = _frame(recorder)
    frame["stages"][1]["detailRows"] = [["PCM 176.4 kHz", "Carrier"]]
    view = build_c6_qml_overlay(
        frame_payload=frame,
        recorder=recorder,
        owner_scope_reader=lambda: dict(_owner(), family="dop"),
        f05_truth_reader=_f05,
        linked_execution_reader=lambda snapshot: (
            "output-exec:alpha" if snapshot is recorder.active_snapshot else None
        ),
        family_delivery_reader=lambda owner: project_family_delivery(
            ledger,
            recorder=recorder,
            family="dop",
            execution_id="output-exec:alpha",
            owner_epoch=4,
        ),
    )
    assert view["audioFamily"] == "dop"
    assert view["stages"][1]["detailRows"] == []
    assert "receptor no ha sido verificado" in view["stages"][3]["detail"]
    assert view["dspExecutionState"] != "CURRENT_EXECUTION_CONFIRMED"
