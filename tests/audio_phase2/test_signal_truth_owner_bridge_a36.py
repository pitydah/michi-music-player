"""A36 tests use the exact PR245 SignalTruthRecorder implementation.

OutputSession is a contract double implementing only the observed
transition_snapshot()/active_execution_id public interface. Full host/Qt
integration remains for OpenCode, not claimed here.
"""

import pytest

from michi.application.signal_truth_delivery import (
    PublicationKey,
    PublicationLedger,
    publish_family_fact,
)
from michi.application.signal_truth_owner_bridge import (
    overlay_from_output_session,
    read_output_owner_scope,
)
from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    OutputFamilyEvent,
    OutputFamilyState,
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthRecorder,
)


class OutputOwnerDouble:
    def __init__(
        self,
        family="pcm_managed",
        state="running",
        plan="output:real",
        eid="e:1",
        epoch=10,
    ):
        self.active_execution_id = eid
        self.snapshot = dict(
            family=family,
            state=state,
            plan_id=plan,
            execution_id=eid,
            generation=epoch,
            stable_device_id="test-dac",
            binding_generation=3,
            host_generation=20,
            processing_generation=0,
        )

    def transition_snapshot(self):
        return dict(self.snapshot)


def truth():
    return dict(
        effective_state="unknown", effective_plan_id=None, readback_proven=False
    )


def active_recorder(plan="output:real"):
    recorder = SignalTruthRecorder()
    ident = SignalTruthIdentity(
        plan_id=plan,
        execution_generation=7,
        port_generation=14,
        binding_generation=3,
        stable_device_id="test-dac",
        stable_endpoint_signature="hw:3,0",
    )
    pcm = PcmTuple(96000, "S24_3LE", 2, 24)
    recorder.begin_candidate(
        OutputPlanEvidence(
            identity=ident,
            requested_pcm=pcm,
            sink_factory="alsasink",
            sink_device="hw:3,0",
            fixed_gain_required=True,
        )
    )
    assert recorder.commit_candidate(ident)
    return recorder, ident


def frame(recorder):
    return dict(
        status="ACTIVE",
        captureRevision=recorder.read_capture_state().revision,
        pathVerdict="unknown",
        reasonCodes=["F03_REASON"],
        stages=[
            dict(id=name, summary=name)
            for name in ("source", "decode", "processing", "output", "device")
        ],
    )


def owner_overlay(recorder, owner, ledger=None):
    return overlay_from_output_session(
        frame_payload=frame(recorder),
        recorder=recorder,
        output_session=owner,
        f05_truth_reader=truth,
        ledger=ledger,
    )


def publish_running(recorder, owner, ledger):
    return publish_family_fact(
        ledger=ledger,
        key=PublicationKey(
            "managed", owner.active_execution_id, owner.snapshot["generation"]
        ),
        recorder=recorder,
        build_event=lambda: OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.RUNNING,
            execution_id=owner.active_execution_id,
            device_id="test-dac",
        ),
    )


def test_real_recorder_binding_issued_by_owner_and_retired():
    rec, _ = active_recorder()
    cap = rec.read_capture_state()
    assert (
        rec.resolve_active_execution_link(
            cap.active, execution_id="e:1", output_plan_id="output:real"
        )
        is None
    )
    rec.activate_execution("e:1", plan_id="output:real")
    assert rec.read_capture_state().revision > cap.revision
    current = rec.read_capture_state()
    assert (
        rec.resolve_active_execution_link(
            current.active, execution_id="e:1", output_plan_id="output:real"
        )
        == "e:1"
    )
    rec.retire_execution("e:1")
    assert rec.read_capture_state().revision > current.revision
    assert (
        rec.resolve_active_execution_link(
            rec.active_snapshot, execution_id="e:1", output_plan_id="output:real"
        )
        is None
    )


def test_duplicate_activation_idempotent_capture_revision():
    rec, _ = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    revision = rec.read_capture_state().revision
    rec.activate_execution("e:1", plan_id="output:real")
    assert rec.read_capture_state().revision == revision


def test_same_output_plan_multiple_live_executions_refuses_inheritance():
    rec, _ = active_recorder()
    rec.activate_execution("e:old", plan_id="output:real")
    rec.activate_execution("e:1", plan_id="output:real")
    assert (
        rec.resolve_active_execution_link(
            rec.active_snapshot, execution_id="e:1", output_plan_id="output:real"
        )
        is None
    )
    rec.retire_execution("e:old")
    assert (
        rec.resolve_active_execution_link(
            rec.active_snapshot, execution_id="e:1", output_plan_id="output:real"
        )
        == "e:1"
    )


def test_plan_from_other_owner_must_not_link():
    rec, _ = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    assert (
        rec.resolve_active_execution_link(
            rec.active_snapshot, execution_id="e:1", output_plan_id="processing:plan"
        )
        is None
    )
    assert (
        rec.resolve_active_execution_link(
            rec.active_snapshot, execution_id="e:wrong", output_plan_id="output:real"
        )
        is None
    )


def test_snapshot_identity_old_after_observe_or_retire_refused():
    rec, ident = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    old = rec.active_snapshot
    assert rec.retire_active(ident)
    assert (
        rec.resolve_active_execution_link(
            old, execution_id="e:1", output_plan_id="output:real"
        )
        is None
    )


def test_valid_output_owner_contract_maps_pcm_managed():
    scope = read_output_owner_scope(OutputOwnerDouble())
    assert scope["family"] == "managed"
    assert scope["generation"] == 10
    assert scope["execution_id"] == "e:1"
    assert scope["plan_id"] == "output:real"


@pytest.mark.parametrize(
    "field,value",
    [
        ("state", "stopped"),
        ("family", "shared"),
        ("generation", 0),
        ("generation", True),
        ("execution_id", "foreign"),
        ("plan_id", ""),
    ],
)
def test_invalid_output_owner_is_fail_closed(field, value):
    owner = OutputOwnerDouble()
    owner.snapshot[field] = value
    with pytest.raises(ValueError, match="ST_A36_OWNER_SCOPE_UNVERIFIED"):
        read_output_owner_scope(owner)


def test_owner_changes_between_reads_are_rejected():
    owner = OutputOwnerDouble()
    previous = owner.transition_snapshot
    reads = 0

    def changing():
        nonlocal reads
        reads += 1
        view = previous()
        if reads == 2:
            view["generation"] += 1
        return view

    owner.transition_snapshot = changing
    with pytest.raises(ValueError, match="ST_A36_OWNER_SCOPE_UNVERIFIED"):
        read_output_owner_scope(owner)


def test_missing_output_ledger_never_promotes_stale_running():
    rec, _ = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    owner = OutputOwnerDouble()
    rec.record_output_family_event(
        OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.RUNNING,
            execution_id="e:1",
            device_id="test-dac",
        )
    )
    result = owner_overlay(rec, owner)
    assert result["familyEvidenceState"] == "UNOBSERVED"
    assert "ST_C6_OUTPUT_DELIVERY_NOT_CERTIFIED" in result["familyEvidenceReasons"]
    assert result["reasonCodes"] == ["F03_REASON"]


def test_real_recorder_plus_owner_ledger_can_report_running_no_dsp_proof():
    rec, _ = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    owner = OutputOwnerDouble()
    ledger = PublicationLedger()
    publish_running(rec, owner, ledger)
    result = owner_overlay(rec, owner, ledger)
    assert result["familyEvidenceState"] == "RUNNING_REPORTED"
    assert result["dspExecutionState"] != "CURRENT_EXECUTION_CONFIRMED"
    assert result["stages"][0]["summary"] == "source"


def test_unissued_owner_binding_refuses_even_with_delivery():
    rec, _ = active_recorder()
    owner = OutputOwnerDouble()
    ledger = PublicationLedger()
    publish_running(rec, owner, ledger)
    result = owner_overlay(rec, owner, ledger)
    assert result["familyEvidenceState"] == "UNOBSERVED"
    assert "ST_C6_F03_OWNER_EXECUTION_LINK_MISSING" in result["familyEvidenceReasons"]


def test_terminal_publication_supersedes_accepted_running():
    rec, _ = active_recorder()
    rec.activate_execution("e:1", plan_id="output:real")
    owner = OutputOwnerDouble()
    ledger = PublicationLedger()
    publish_running(rec, owner, ledger)
    publish_family_fact(
        ledger=ledger,
        key=PublicationKey("managed", "e:1", 10),
        recorder=rec,
        build_event=lambda: OutputFamilyEvent(
            family="managed",
            state=OutputFamilyState.UNAVAILABLE,
            execution_id="e:1",
            device_id="test-dac",
        ),
    )
    result = owner_overlay(rec, owner, ledger)
    assert result["familyEvidenceState"] == "TERMINATED"
    assert result["dspExecutionState"] == "UNOBSERVED"


def test_direct_not_automatically_output_session_execution_linked():
    owner = OutputOwnerDouble(family="pcm_direct")
    with pytest.raises(ValueError):
        read_output_owner_scope(owner)
