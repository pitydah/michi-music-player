"""Synthetic contract falsifiers only; NOT tests against Michi repository/Qt."""

from __future__ import annotations

from dataclasses import replace

import pytest

from michi.application.signal_truth_causal import (
    ContinuityCertificate,
    Correlation,
    DspEvent,
    DspOwner,
    InputStability,
    OutputScope,
    RouteBindingProof,
    correlate,
)


def factory():
    o = OutputScope("managed", "exec:A", 11, "RUNNING", 7, 31, 4, 108)
    p = DspOwner("effective", "dsp:PEQ", 19, "runtime:7.31", True, 7, 31, 55, 12, 306)
    e = (DspEvent("EFFECTIVE", "dsp:PEQ", 19, "runtime:7.31", True, 7, 31, 12, 306),)
    l = RouteBindingProof(  # noqa: E741
        "OUTPUT_SESSION",
        "ADOPTED",
        "managed",
        "exec:A",
        11,
        108,
        55,
        7,
        31,
        4,
        "dsp:PEQ",
        19,
        "runtime:7.31",
    )
    c = ContinuityCertificate(12, 306, True, 55)
    s = InputStability(8, 8, 108, 108, 55, 55)
    return o, p, e, l, c, s


def decide(*, o=None, p=None, e=None, l="default", c="default", s="default"):  # noqa: E741
    base = factory()
    return correlate(
        o or base[0],
        p or base[1],
        e if e is not None else base[2],
        link=base[3] if l == "default" else l,
        continuity=base[4] if c == "default" else c,
        stable=base[5] if s == "default" else s,
    )


def test_strong_positive_requires_all_owners():
    r = decide()
    assert r.correlation is Correlation.CONFIRMED
    assert r.motor_readback_observed and r.confirmed_for_current_execution


def test_plan_namespaces_can_be_different():
    assert factory()[0].execution_id != factory()[1].plan_id
    assert decide().correlation is Correlation.CONFIRMED


@pytest.mark.parametrize(
    "part,change,expected",
    [
        ("o", {"state": "READY"}, Correlation.UNCORRELATED),
        ("o", {"state": "PAUSED"}, Correlation.UNCORRELATED),
        ("o", {"execution_id": None}, Correlation.UNCORRELATED),
        ("o", {"family": "direct"}, Correlation.UNCORRELATED),
        ("o", {"host_generation": None}, Correlation.UNCORRELATED),
        ("o", {"session_generation": 0}, Correlation.UNCORRELATED),
        ("p", {"state": "bypassed"}, Correlation.REVOKED),
        ("p", {"state": "unavailable"}, Correlation.REVOKED),
        ("p", {"state": "preparing"}, Correlation.UNCORRELATED),
        ("p", {"readback_proven": False}, Correlation.UNCORRELATED),
        ("p", {"runtime_identity": None}, Correlation.UNCORRELATED),
        ("p", {"host_generation": 8}, Correlation.CONFLICTED),
        ("p", {"pipeline_generation": 32}, Correlation.CONFLICTED),
        ("p", {"latest_event_sequence": None}, Correlation.UNCORRELATED),
        ("l", {"execution_id": "exec:previous"}, Correlation.CONFLICTED),
        ("l", {"session_generation": 12}, Correlation.CONFLICTED),
        ("l", {"binding_generation": 5}, Correlation.CONFLICTED),
        ("l", {"dsp_runtime_identity": "runtime:other"}, Correlation.CONFLICTED),
        ("l", {"issuing_owner": "UI"}, Correlation.UNCORRELATED),
        ("l", {"adoption_state": "PREPARED"}, Correlation.UNCORRELATED),
        ("c", {"ordered_tail_complete": False}, Correlation.UNCORRELATED),
        ("c", {"event_epoch": 13}, Correlation.UNCORRELATED),
        ("s", {"output_revision_end": 109}, Correlation.UNCORRELATED),
        ("s", {"recorder_revision_end": 9}, Correlation.UNCORRELATED),
        ("s", {"dsp_revision_end": 56}, Correlation.UNCORRELATED),
    ],
)
def test_single_mutation_falsifiers(part, change, expected):
    o, p, e, l, c, s = factory()  # noqa: E741
    obj = {"o": o, "p": p, "l": l, "c": c, "s": s}
    altered = replace(obj[part], **change)
    kwargs = {part: altered}
    r = decide(**kwargs)
    assert r.correlation is expected
    assert not r.confirmed_for_current_execution


def test_no_link_is_not_enough_even_if_all_gen_equal():
    assert decide(l=None).correlation is Correlation.UNCORRELATED


def test_no_continuity_is_not_enough():
    assert decide(c=None).correlation is Correlation.UNCORRELATED


def test_absent_event_is_not_effective():
    assert decide(e=()).correlation is Correlation.UNCORRELATED


def test_terminal_revokes_earlier_effective():
    o, p, e, l, c, s = factory()  # noqa: E741
    past = replace(e[0], sequence=305)
    terminal = replace(
        e[0],
        sequence=306,
        state="BYPASSED",
        readback_proven=False,
        plan_id=None,
        runtime_identity=None,
    )
    r = decide(e=(past, terminal))
    assert r.correlation is Correlation.REVOKED


def test_stale_latest_runtime_id_is_not_confirmed():
    e = replace(factory()[2][0], runtime_identity="old")
    assert decide(e=(e,)).correlation is Correlation.STALE


def test_stale_latest_dsp_revision_is_not_confirmed():
    e = replace(factory()[2][0], processing_generation=18)
    assert decide(e=(e,)).correlation is Correlation.STALE


def test_unproven_event_readback_is_not_confirmed():
    e = replace(factory()[2][0], readback_proven=False)
    assert decide(e=(e,)).correlation is Correlation.UNCORRELATED


def test_sequence_gap_rejects_positive():
    one = replace(factory()[2][0], sequence=303)
    two = replace(factory()[2][0], sequence=306)
    assert decide(e=(one, two)).correlation is Correlation.UNCORRELATED


def test_latest_event_missing_rejects_positive():
    event = replace(factory()[2][0], sequence=305)
    assert decide(e=(event,)).correlation is Correlation.UNCORRELATED


def test_wrong_event_epoch_rejects_positive():
    event = replace(factory()[2][0], event_epoch=11)
    assert decide(e=(event,)).correlation is Correlation.UNCORRELATED


def test_duplicate_event_sequence_rejects_positive():
    event = factory()[2][0]
    assert decide(e=(event, event)).correlation is Correlation.CONFLICTED


def test_event_order_reversed_rejects_positive():
    event = factory()[2][0]
    assert (
        decide(e=(event, replace(event, sequence=305))).correlation
        is Correlation.CONFLICTED
    )


def test_same_textual_plan_with_new_execution_not_enough():
    o = replace(factory()[0], execution_id="exec:B")
    assert decide(o=o).correlation is Correlation.CONFLICTED


def test_host_restart_with_reused_pipeline_rejected():
    o = replace(factory()[0], host_generation=8)
    assert decide(o=o).correlation is Correlation.CONFLICTED


def test_execution_equals_dsp_plan_accidentally_still_requires_link():
    o = replace(factory()[0], execution_id="dsp:PEQ")
    assert decide(o=o, l=None).correlation is Correlation.UNCORRELATED


def test_service_effective_without_route_link_is_not_current_playback():
    r = decide(l=None)
    assert r.motor_readback_observed and not r.confirmed_for_current_execution


def test_same_positive_with_dsd_pcm_when_proof_scoped():
    o, p, e, l, c, s = factory()  # noqa: E741
    assert (
        decide(
            o=replace(o, family="dsd_pcm"), l=replace(l, family="dsd_pcm")
        ).correlation
        is Correlation.CONFIRMED
    )


def test_no_dsp_positive_for_dop_even_with_matching_proof():
    o, p, e, l, c, s = factory()  # noqa: E741
    assert (
        decide(o=replace(o, family="dop"), l=replace(l, family="dop")).correlation
        is Correlation.UNCORRELATED
    )


def test_old_readback_positive_does_not_overrule_host_loss():
    p = replace(factory()[1], state="unavailable", readback_proven=False)
    assert decide(p=p).correlation is Correlation.REVOKED


def test_independent_owner_rev_changes_fail_even_with_same_identity():
    p = replace(factory()[1], owner_revision=56)
    assert decide(p=p).correlation is Correlation.UNCORRELATED


def test_repeated_fresh_effective_is_valid_only_with_new_sequence_and_certificate():
    o, p, e, l, c, s = factory()  # noqa: E741
    recent = replace(e[0], sequence=307)
    p = replace(p, latest_event_sequence=307)
    c = replace(c, latest_sequence=307)
    assert (
        decide(p=p, e=(replace(e[0], sequence=306), recent), c=c).correlation
        is Correlation.CONFIRMED
    )
