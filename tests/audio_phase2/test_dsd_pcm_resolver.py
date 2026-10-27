from __future__ import annotations

from pathlib import Path

from michi.application.dsd_policy_service import (
    DsdPolicyDecision,
    OutputFamily,
)
from michi.application.dsd_to_pcm_plan import DsdToPcmPlanner
from tests.audio_phase2.test_dop_resolver import _resolver


def test_productive_resolver_selects_explicit_dsd_to_pcm():
    decision = DsdPolicyDecision(
        decision=OutputFamily.DSD_TO_PCM,
        reason="DSD_TO_PCM",
        reasons=("DSD_TO_PCM",),
        conversion_consent_required=False,
        quality_profile="FAST",
    )
    resolver = _resolver(
        None,
        dsd_pcm_policy_provider=lambda _source: decision,
        dsd_pcm_planner=DsdToPcmPlanner(),
        dsd_pcm_target_rates=lambda _device, _binding: (88_200,),
        dsd_pcm_host_generation=lambda: 1,
        dsd_pcm_decoder_available=True,
    )
    request = resolver(Path("/media/track.dsf"))
    assert request.dsd_pcm_plan is not None
    plan = request.dsd_pcm_plan
    assert plan.stable_device_id == "dev:dac"
    assert plan.binding_locator == "hw:2,0"
    assert plan.binding_generation == 7
    assert plan.target_rate_hz == 88_200
    assert plan.host_generation == 1
    assert request.selected_device_id == "dev:dac"
