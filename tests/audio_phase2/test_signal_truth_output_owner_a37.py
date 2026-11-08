"""A37 full-checkout output-owner integration contract.

Run under the real Michi checkout (not the isolated PR245 subset). These
fixtures invoke the real OutputSessionService methods without opening a DAC.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from michi.application.output_session_service import OutputSessionService
from michi.application.signal_truth_delivery import DisplayClaim, PublicationLedger
from michi.domain.audio_output import OutputSessionState
from michi.domain.signal_truth import (
    OutputFamilyState,
    SignalTruthRecorder,
)

FAMILIES = ("managed", "native_dsd", "dop", "dsd_pcm")


def _owner(family: str, recorder: SignalTruthRecorder | None = None):
    owner = OutputSessionService.__new__(OutputSessionService)
    owner._truth_recorder = recorder if recorder is not None else SignalTruthRecorder()
    owner._signal_truth_delivery = PublicationLedger()
    owner._mode = family
    owner._state = OutputSessionState.RUNNING
    owner._generation = 9
    owner._selected_device_id = "fixture:dac"
    owner._dsd_pcm_processing_effective = False
    plan = SimpleNamespace(
        plan_id="output-plan:X",
        stable_device_id="fixture:dac",
        processing_plan_id="processing-plan:DIFFERENT-NAMESPACE",
        transform_policy=("processing",),
        binding_generation=3,
        host_generation=7,
    )
    prepared = SimpleNamespace(
        plan=plan,
        execution_id="exec:9",
        stable_device_id="fixture:dac",
        runtime_identity={"host_generation": 7},
        host_generation=7,
    )
    for name in FAMILIES:
        setattr(owner, f"_{name}_prepared", prepared if name == family else None)
        setattr(owner, f"_{name}_plan", plan if name == family else None)
    return owner


def _record(owner, state):
    name = (
        "_record_output_family"
        if owner._mode == "managed"
        else f"_record_{owner._mode}_family"
    )
    getattr(owner, name)(state)


@pytest.mark.parametrize("family", FAMILIES)
def test_owner_real_recorder_running_receipt_is_current_scope_only(family):
    owner = _owner(family)
    _record(owner, OutputFamilyState.RUNNING)
    capture = owner._truth_recorder.read_capture_state()
    assert capture.output_family_events[-1].family == family
    assert capture.output_family_events[-1].execution_id == "exec:9"
    assert owner.read_current_family_delivery() == DisplayClaim.OBSERVED_RUNNING
    owner._generation += 1
    assert owner.read_current_family_delivery() == DisplayClaim.UNVERIFIED


@pytest.mark.parametrize("family", FAMILIES)
def test_owner_real_recorder_terminal_revokes_running_receipt(family):
    owner = _owner(family)
    _record(owner, OutputFamilyState.RUNNING)
    _record(owner, OutputFamilyState.UNAVAILABLE)
    assert owner.read_current_family_delivery() == DisplayClaim.OBSERVED_TERMINAL


def test_owner_real_recorder_failed_terminal_never_keeps_running_claim():
    class RejectTerminal(SignalTruthRecorder):
        def record_output_family_event(self, event):
            if event.state is OutputFamilyState.UNAVAILABLE:
                raise RuntimeError("simulated terminal loss")
            return super().record_output_family_event(event)

    owner = _owner("managed", RejectTerminal())
    _record(owner, OutputFamilyState.RUNNING)
    assert owner.read_current_family_delivery() == DisplayClaim.OBSERVED_RUNNING
    _record(owner, OutputFamilyState.UNAVAILABLE)
    assert owner.read_current_family_delivery() == DisplayClaim.UNVERIFIED


def test_owner_refuses_paused_as_current_playback():
    owner = _owner("managed")
    _record(owner, OutputFamilyState.RUNNING)
    owner._state = OutputSessionState.PAUSED
    assert owner.read_current_family_delivery() == DisplayClaim.UNVERIFIED


def test_owner_ledger_subscription_is_unsubscribable():
    owner = _owner("managed")
    calls: list[str] = []

    def callback():
        calls.append("updated")

    owner.subscribe_signal_truth_delivery(callback)
    _record(owner, OutputFamilyState.RUNNING)
    owner.unsubscribe_signal_truth_delivery(callback)
    count = len(calls)
    _record(owner, OutputFamilyState.UNAVAILABLE)
    assert count == 2
    assert len(calls) == count
