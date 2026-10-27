from __future__ import annotations

import json
from pathlib import Path

import pytest

from michi.application.dsd_to_pcm_plan import (
    DEFAULT_QUALITY_PROFILE,
    QUALITY_RATE_LADDERS,
    DsdToPcmPlanError,
    DsdToPcmPlanner,
    decoder_factory_for,
    dsd_decoder_native_rate_hz,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)


def _format(
    *,
    bits=2_822_400,
    order=DsdBitOrder.LSBF,
    organization=DsdOrganization.PLANAR,
    channels=2,
):
    layouts = {1: ("FC",), 2: ("FL", "FR")}
    return DsdSignalFormat(
        bit_rate_hz=bits,
        channels=channels,
        packing=DsdPacking.DSD_U8,
        bit_order=order,
        organization=organization,
        layout=layouts[channels],
    )


@pytest.mark.parametrize(
    ("bits", "native"),
    [
        (2_822_400, 352_800),
        (5_644_800, 705_600),
        (11_289_600, 1_411_200),
        (22_579_200, 2_822_400),
    ],
)
def test_native_rate(bits, native):
    assert dsd_decoder_native_rate_hz(bits) == native


def test_native_rate_rejects_invalid():
    with pytest.raises(ValueError):
        dsd_decoder_native_rate_hz(0)
    with pytest.raises(ValueError):
        dsd_decoder_native_rate_hz(2_822_401)


def test_decoder_factory_mapping():
    assert decoder_factory_for(_format()) == "avdec_dsd_lsbf"
    assert decoder_factory_for(_format(order=DsdBitOrder.MSBF)) == "avdec_dsd_msbf"
    assert (
        decoder_factory_for(_format(organization=DsdOrganization.INTERLEAVED))
        == "avdec_dsd_lsbf"
    )


def test_manifest_matches_code_ladders():
    manifest = json.loads(
        Path("docs/audio/phase2/dsd2pcm_profiles_v1.json").read_text()
    )
    for name, ladder in QUALITY_RATE_LADDERS.items():
        assert tuple(manifest["profiles"][name]["ladder_hz"]) == ladder
    assert manifest["resampler"]["quality"] == 10
    assert manifest["resampler"]["resample_method"] == "kaiser"


@pytest.mark.parametrize(
    ("profile", "target"),
    [
        ("FAST", 88_200),
        ("BALANCED", 176_400),
        ("HIGH", 352_800),
        ("REFERENCE", 705_600),
    ],
)
def test_plan_selects_first_qualified_ladder_rate(profile, target):
    plan = DsdToPcmPlanner().plan(
        source_identity="track:1",
        source_format=_format(),
        quality_profile=profile,
        binding_generation=7,
        available_output_rates=(88_200, 176_400, 352_800, 705_600),
        decoder_available=True,
        target_qualified=True,
        backend_version="1.28.8",
    )
    if target > 352_800:
        assert plan.target_rate_hz == 352_800
    else:
        assert plan.target_rate_hz == target
    assert plan.output_format == "F32LE"
    assert plan.decoder_factory == "avdec_dsd_lsbf"


def test_plan_uses_resampler_only_when_needed():
    plan = DsdToPcmPlanner().plan(
        source_identity="track:1",
        source_format=_format(),
        quality_profile="HIGH",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
    )
    assert plan.target_rate_hz == 88_200
    assert plan.resampler_policy
    native = DsdToPcmPlanner().plan(
        source_identity="track:1",
        source_format=_format(),
        quality_profile="HIGH",
        binding_generation=1,
        available_output_rates=(352_800,),
        decoder_available=True,
        target_qualified=True,
    )
    assert native.resampler_policy == ()


def test_no_qualified_target():
    with pytest.raises(DsdToPcmPlanError) as exc:
        DsdToPcmPlanner().plan(
            source_identity="track:1",
            source_format=_format(),
            quality_profile="HIGH",
            binding_generation=1,
            available_output_rates=(48_000,),
            decoder_available=True,
            target_qualified=True,
        )
    assert exc.value.code == "DSD_PCM_NO_QUALIFIED_TARGET_RATE"


def test_decoder_missing_and_unqualified():
    planner = DsdToPcmPlanner()
    with pytest.raises(DsdToPcmPlanError, match="DSD_PCM_DECODER_UNAVAILABLE"):
        planner.plan(
            source_identity="t",
            source_format=_format(),
            quality_profile="HIGH",
            binding_generation=1,
            available_output_rates=(88_200,),
            decoder_available=False,
            target_qualified=True,
        )
    with pytest.raises(DsdToPcmPlanError, match="DSD_PCM_TARGET_UNQUALIFIED"):
        planner.plan(
            source_identity="t",
            source_format=_format(),
            quality_profile="HIGH",
            binding_generation=1,
            available_output_rates=(88_200,),
            decoder_available=True,
            target_qualified=False,
        )


def test_default_profile_is_high():
    assert DEFAULT_QUALITY_PROFILE == "HIGH"


def _plan(**kw):
    base = dict(
        source_identity="track:1",
        source_format=_format(),
        quality_profile="HIGH",
        binding_generation=1,
        available_output_rates=(88_200,),
        decoder_available=True,
        target_qualified=True,
        backend_version="1.28.8",
    )
    base.update(kw)
    return DsdToPcmPlanner().plan(**base)


def test_plan_id_changes_with_semantic_inputs():
    base = _plan()
    assert _plan(source_format=_format(channels=1)).plan_id != base.plan_id
    assert _plan(backend_version="1.29.0").plan_id != base.plan_id
    assert _plan(processing_graph_revision=1).plan_id != base.plan_id
    assert _plan(evidence_refs=("ev:1",)).plan_id != base.plan_id
    assert _plan(binding_generation=2).plan_id != base.plan_id


def test_plan_id_is_deterministic_for_equal_semantics():
    assert _plan().plan_id == _plan().plan_id
