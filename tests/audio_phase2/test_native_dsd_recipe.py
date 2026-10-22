"""AP2-F08 — strict Native DSD sink recipe tests (§84.1, §214)."""

from __future__ import annotations

import pytest

from michi.application.dsd_output_planner import (
    AlsaDsdTuple,
    NativeDsdPlanner,
    NativeDsdQualification,
)
from michi.domain.dsd_signal import (
    AlsaDsdGrouping,
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)
from michi.infrastructure.audio_output.strict_dsd_sink import (
    StrictDsdSinkError,
    StrictDsdSinkRecipe,
    recipe_from_native_plan,
)

DEVICE = "usb:152a:85dd"
LOCATOR = "hw:3,0"


def _source(
    *,
    packing: DsdPacking = DsdPacking.DSD_U8,
    bit_order: DsdBitOrder = DsdBitOrder.MSBF,
    organization: DsdOrganization = DsdOrganization.PLANAR,
) -> DsdSignalFormat:
    return DsdSignalFormat(
        bit_rate_hz=2_822_400,
        channels=2,
        packing=packing,
        bit_order=bit_order,
        organization=organization,
        layout=("FL", "FR"),
    )


def _plan(source: DsdSignalFormat | None = None):
    src = source or _source()
    requested = AlsaDsdTuple(
        format_name=AlsaDsdGrouping.DSD_U32_BE.alsa_format_name,
        frame_rate_hz=88_200,
        channels=2,
        sample_width_bits=32,
        source_bits_per_second_per_channel=2_822_400,
    )
    return NativeDsdPlanner().plan(
        stable_device_id=DEVICE,
        binding_locator=LOCATOR,
        binding_generation=7,
        source=src,
        qualifications=(
            NativeDsdQualification(
                stable_device_id=DEVICE,
                binding_generation=7,
                requested=requested,
                supported=True,
                evidence_ref="alsa-dsd:test",
            ),
        ),
        execution_id="exec:recipe",
        source_proven=True,
        active_engine_id="gstreamer",
    )


def test_recipe_caps_are_exact_and_never_pcm() -> None:
    recipe = recipe_from_native_plan(_plan())
    assert recipe.device == LOCATOR
    assert recipe.gst_dsd_format == "DSDU32BE"
    assert recipe.gst_rate_bytes_per_second_per_channel == 352_800
    assert recipe.channels == 2
    assert recipe.sink_factory == "alsasink"
    assert recipe.caps_string() == (
        "audio/x-dsd,format=DSDU32BE,rate=352800,channels=2,"
        "layout=interleaved,reversed-bytes=false"
    )


def test_planar_dsf_requires_explicit_dsdconvert() -> None:
    recipe = recipe_from_native_plan(_plan())
    assert recipe.requires_dsdconvert is True
    assert recipe.needs_dsdconvert is True
    assert recipe.normalize_reversed_bytes is False


def test_native_interleaved_u32be_needs_no_dsdconvert() -> None:
    source = _source(
        packing=DsdPacking.DSD_U32BE,
        organization=DsdOrganization.INTERLEAVED,
    )
    recipe = recipe_from_native_plan(_plan(source))
    assert recipe.requires_dsdconvert is False


def test_lsbf_source_normalizes_before_alsasink() -> None:
    recipe = recipe_from_native_plan(_plan(_source(bit_order=DsdBitOrder.LSBF)))
    assert recipe.normalize_reversed_bytes is True
    assert recipe.requires_dsdconvert is True


def test_target_reversed_bytes_is_refused() -> None:
    with pytest.raises(StrictDsdSinkError) as info:
        StrictDsdSinkRecipe(
            plan_id="native-dsd:test",
            device=LOCATOR,
            gst_dsd_format="DSDU32BE",
            gst_rate_bytes_per_second_per_channel=352_800,
            channels=2,
            normalize_reversed_bytes=False,
            requires_dsdconvert=False,
            target_reversed_bytes=True,
        )
    assert info.value.code == "DSD_RECIPE_REVERSED_TARGET"


def test_non_boolean_normalization_is_refused() -> None:
    with pytest.raises(StrictDsdSinkError) as info:
        StrictDsdSinkRecipe(
            plan_id="native-dsd:test",
            device=LOCATOR,
            gst_dsd_format="DSDU32BE",
            gst_rate_bytes_per_second_per_channel=352_800,
            channels=2,
            normalize_reversed_bytes="yes",  # type: ignore[arg-type]
            requires_dsdconvert=False,
        )
    assert info.value.code == "DSD_RECIPE_CONVERSION_INVALID"


def test_invalid_recipe_fields_are_refused() -> None:
    for kwargs, code in (
        ({"device": ""}, "DSD_RECIPE_DEVICE_MISSING"),
        ({"gst_dsd_format": "S32LE"}, "DSD_RECIPE_FORMAT_INVALID"),
        ({"gst_rate_bytes_per_second_per_channel": 0}, "DSD_RECIPE_RATE_INVALID"),
        ({"channels": 0}, "DSD_RECIPE_CHANNELS_INVALID"),
        ({"layout": "non-interleaved"}, "DSD_RECIPE_LAYOUT_INVALID"),
        (
            {
                "normalize_reversed_bytes": True,
                "requires_dsdconvert": False,
            },
            "DSD_RECIPE_CONVERSION_INVALID",
        ),
    ):
        base = {
            "plan_id": "native-dsd:test",
            "device": LOCATOR,
            "gst_dsd_format": "DSDU32BE",
            "gst_rate_bytes_per_second_per_channel": 352_800,
            "channels": 2,
            "normalize_reversed_bytes": False,
            "requires_dsdconvert": False,
        }
        base.update(kwargs)
        with pytest.raises(StrictDsdSinkError) as info:
            StrictDsdSinkRecipe(**base)
        assert info.value.code == code


def test_recipe_rejects_a_non_native_plan_object() -> None:
    with pytest.raises(StrictDsdSinkError) as info:
        recipe_from_native_plan(object())
    assert info.value.code == "DSD_RECIPE_PLAN_INVALID"
