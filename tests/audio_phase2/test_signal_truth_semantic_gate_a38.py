"""A38 F03 compatibility/negative gate, PR245 domain with synthetic F03 doubles.

The full F03 service remains in the product checkout; tests against the real
service need OpenCode and MUST NOT be counted by this isolated suite.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from michi.application.signal_truth_semantic_gate import reconcile_f03_semantics
from michi.domain.audio_evidence import PcmTuple
from michi.domain.signal_truth import (
    OutputPlanEvidence,
    SignalTruthIdentity,
    SignalTruthRecorder,
)


def _snapshot():
    identity = SignalTruthIdentity(
        plan_id="output:A",
        execution_generation=2,
        port_generation=5,
        binding_generation=3,
        stable_device_id="fixture:device",
        stable_endpoint_signature="fixture:endpoint",
    )
    recorder = SignalTruthRecorder()
    recorder.begin_candidate(
        OutputPlanEvidence(
            identity=identity,
            requested_pcm=PcmTuple(96000, "S24_3LE", 2, 24),
            sink_factory="alsasink",
            sink_device="hw:1,0",
            fixed_gain_required=True,
        )
    )
    assert recorder.commit_candidate(identity)
    return recorder.read_capture_state()


def _semantic(snapshot, *, change=None):
    reasons = tuple(reason.value for reason in snapshot.reasons)
    nodes = [
        SimpleNamespace(
            kind=SimpleNamespace(value=kind),
            node_id=kind,
            state=SimpleNamespace(value="not_observed"),
            reason_codes=(),
        )
        for kind in ("source", "decode", "engine", "device")
    ]
    # Synthetic reason partition only. The REAL mapping is owned by F03.
    nodes[2].reason_codes = reasons
    model = SimpleNamespace(
        identity=snapshot.identity,
        verdict=snapshot.verdict.value,
        reasons=reasons,
        nodes=tuple(nodes),
    )
    if change:
        change(model)
    return model


def _frame():
    return {
        "status": "ACTIVE",
        "pathVerdict": "direct",
        "reasonCodes": ["OLD_UNTRUSTED_LABEL"],
        "headline": "Direct path",
        "headlineTone": "success",
        "indicatorState": "observed",
        "pathProofState": "verified",
        "pathProofLabel": "Verified path",
        "stages": [
            {"id": kind, "state": "observed", "summary": "legacy"}
            for kind in ("source", "decode", "processing", "output", "device")
        ],
    }


def _run(*, change=None, revision_change=False, frame=None):
    capture = _snapshot()
    return reconcile_f03_semantics(
        _frame() if frame is None else frame,
        capture.active,
        capture_revision=capture.revision,
        observed_revision=capture.revision + int(revision_change),
        projector=lambda snapshot: _semantic(snapshot, change=change),
    )


def test_exact_verdict_and_reason_codes_reconciled_from_f03_not_qml():
    capture = _snapshot()
    result = reconcile_f03_semantics(
        _frame(),
        capture.active,
        capture_revision=capture.revision,
        observed_revision=capture.revision,
        projector=lambda snap: _semantic(snap),
    )
    assert result["canonicalF03State"] == "RECONCILED"
    assert result["pathVerdict"] == capture.active.verdict.value
    assert result["reasonCodes"] == [r.value for r in capture.active.reasons]
    assert result["pathProofState"] == "partially_verified"
    assert result["stages"][0]["state"] == "unknown"
    assert result["stages"][2]["state"] == "observed"  # F03 isn't F05


def test_refuses_temporal_revision_change_before_invoking_projector():
    called = []
    capture = _snapshot()
    result = reconcile_f03_semantics(
        _frame(),
        capture.active,
        capture_revision=capture.revision,
        observed_revision=capture.revision + 1,
        projector=lambda x: called.append(x),
    )
    assert called == []
    assert result["canonicalF03Reason"] == "ST_A38_CAPTURE_REVISION_CHANGED"
    assert result["pathVerdict"] == "unknown"
    assert all(s["state"] == "unknown" for s in result["stages"])


def test_foreign_identity_refused():
    result = _run(
        change=lambda p: setattr(
            p,
            "identity",
            replace(
                p.identity,
                execution_generation=p.identity.execution_generation + 1,
            ),
        )
    )
    assert result["canonicalF03State"] == "REFUSED"
    assert result["reasonCodes"] == []


def test_changed_verdict_refused():
    result = _run(change=lambda p: setattr(p, "verdict", "direct"))
    assert result["canonicalF03State"] == "REFUSED"


def test_missing_canonical_reason_refused():
    capture = _snapshot()
    if not capture.active.reasons:
        pytest.skip("real recorder fixture has no reasons")
    result = _run(change=lambda p: setattr(p, "reasons", p.reasons[1:]))
    assert result["canonicalF03State"] == "REFUSED"


def test_duplicate_node_reason_refused():
    def mutate(p):
        p.nodes[0].reason_codes = p.nodes[2].reason_codes

    result = _run(change=mutate)
    assert result["canonicalF03State"] == "REFUSED"


def test_wrong_semantic_node_order_refused():
    result = _run(change=lambda p: setattr(p, "nodes", tuple(reversed(p.nodes))))
    assert result["canonicalF03State"] == "REFUSED"


def test_illegal_semantic_node_state_refused():
    def mutate(p):
        p.nodes[2].state = SimpleNamespace(value="certified_bitperfect")

    assert _run(change=mutate)["canonicalF03State"] == "REFUSED"


def test_semantic_device_observation_limits_claim_to_alsa_boundary():
    def mutate(p):
        p.nodes[3].state = SimpleNamespace(value="observed")

    result = _run(change=mutate)
    assert result["pathProofLabel"] == "Ruta observada hasta ALSA"
    assert result["pathProofState"] != "verified"


def test_semantic_transport_raw_facts_not_exposed():
    def mutate(p):
        p.nodes[3].requested = (("locator", "secret:/home/user/private"),)

    result = _run(change=mutate)
    assert "secret:" not in str(result)
    assert result["canonicalF03Nodes"] == [
        {"kind": kind, "state": "not_observed"}
        for kind in ("source", "decode", "engine", "device")
    ]


def test_refusal_avoids_leaking_exception_text():
    def raise_sensitive(_snapshot):
        raise ValueError("private file /home/someone/music/file.flac")

    capture = _snapshot()
    result = reconcile_f03_semantics(
        _frame(),
        capture.active,
        capture_revision=capture.revision,
        observed_revision=capture.revision,
        projector=raise_sensitive,
    )
    assert result["canonicalF03State"] == "REFUSED"
    assert "/home/" not in str(result)


def test_no_capture_returns_no_positive_claim():
    result = reconcile_f03_semantics(
        _frame(),
        None,
        capture_revision=0,
        observed_revision=0,
        projector=lambda _: pytest.fail("must not project missing snapshot"),
    )
    assert result["canonicalF03State"] == "REFUSED"


def test_idle_without_capture_keeps_idle_status():
    frame = {**_frame(), "status": "NOT_ACTIVE", "pathProofState": "no_path"}
    result = reconcile_f03_semantics(
        frame,
        None,
        capture_revision=0,
        observed_revision=0,
        projector=lambda _: pytest.fail("must not project missing snapshot"),
    )
    assert result["canonicalF03State"] == "NO_CAPTURE"
    assert result["status"] == "NOT_ACTIVE"


def test_f03_contradiction_cannot_be_masked_by_legacy_positive_indicator():
    capture = _snapshot()
    # Deliberately modify both canonical and recorder verdict to contradicted
    # using a frozen snapshot copy, to test the presentation refusal boundary.
    snapshot = replace(capture.active, verdict=SimpleNamespace(value="contradicted"))
    result = reconcile_f03_semantics(
        _frame(),
        snapshot,
        capture_revision=capture.revision,
        observed_revision=capture.revision,
        projector=lambda snap: _semantic(snap),
    )
    assert result["pathVerdict"] == "contradicted"
    assert result["headlineTone"] == "error"
    assert result["indicatorState"] == "error"


def test_pending_cannot_be_promoted_to_active_by_f03():
    pending = {**_frame(), "status": "PENDING", "pathProofState": "pending"}
    result = _run(frame=pending)
    assert result["status"] == "PENDING"
    assert result["pathProofState"] == "pending"


def test_null_reason_values_are_refused_not_invented():
    result = _run(change=lambda p: setattr(p.nodes[1], "reason_codes", ("fake",)))
    assert result["canonicalF03State"] == "REFUSED"


def test_unlinked_family_clears_legacy_pcm_and_alsa_rows():
    from michi.application.signal_truth_semantic_gate import mask_unlinked_output_family

    before = _frame()
    before["stages"][3]["detailRows"] = [["ALSA", "hw:secret"]]
    actual = mask_unlinked_output_family(before)
    assert actual["canonicalF03State"] == "OWNER_LINK_REQUIRED"
    assert actual["pathVerdict"] == "unknown"
    assert actual["reasonCodes"] == []
    assert actual["stages"][3]["detailRows"] == []
    assert "hw:secret" not in str(actual)
    assert before["stages"][3]["detailRows"] == [["ALSA", "hw:secret"]]


def test_unlinked_family_never_promotes_effective_dsp():
    from michi.application.signal_truth_semantic_gate import mask_unlinked_output_family

    before = _frame()
    before["stages"][2]["state"] = "transformed"
    actual = mask_unlinked_output_family(before)
    assert actual["stages"][2]["state"] == "unknown"
    assert actual["indicatorState"] == "unknown"


def test_refusal_redacts_stale_runtime_identity_and_source_path():
    before = _frame()
    before["sourceIdentity"] = "/home/user/private-library/secret.flac"
    before["identity"] = {"stable_device_id": "secret-id"}
    actual = _run(revision_change=True, frame=before)
    assert actual["sourceIdentity"] == ""
    assert actual["identity"] == {}
    assert "secret.flac" not in str(actual)
    assert "secret-id" not in str(actual)


def test_real_f03_service_contract_when_full_checkout_is_available():
    """Cross-phase F03 gate. The isolated source subset skips this explicitly."""
    try:
        from michi.application.signal_path_service import SignalPathService
    except ModuleNotFoundError:
        pytest.skip("Real F03 service needs the complete Michi checkout")
    capture = _snapshot()
    actual = reconcile_f03_semantics(
        _frame(),
        capture.active,
        capture_revision=capture.revision,
        observed_revision=capture.revision,
        projector=SignalPathService().project,
    )
    assert actual["canonicalF03State"] == "RECONCILED"
    assert actual["reasonCodes"] == [r.value for r in capture.active.reasons]
    assert len(actual["canonicalF03Nodes"]) == 4
