"""DAC-V35-050A — StrictSinkRecipe gates (S1..S9)."""

from __future__ import annotations

import dataclasses

import pytest

from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_output import (
    FallbackKind,
    GstSinkSpec,
    OutputPlan,
    PathSemantics,
    VolumePolicy,
)


def _plan(
    rate: int = 44100,
    fmt: str = "S16_LE",
    channels: int = 2,
    device: str = "hw:CARD=DX5,DEV=0",
    **overrides,
) -> OutputPlan:
    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator=device,
        generation=1,
        currently_available=True,
        card_index=1,
        pcm_device=0,
    )
    base: dict = dict(
        plan_id="plan:test",
        stable_device_id="usb:2622:0105:TEST",
        binding=binding,
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(rate, fmt, channels, 16),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec(factory="alsasink", device=device),
        resync_delay_ms=0,
        preconditions=("engine_gstreamer_direct",),
        evidence_refs=("probe:1",),
        decision_codes=("ENGINE_GSTREAMER_DIRECT",),
    )
    base.update(overrides)
    return OutputPlan(**base)


def test_s1_s16le_44100_stereo_recipe_exact() -> None:
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    recipe = recipe_from_plan(_plan())
    assert recipe.gst_format == "S16LE"
    assert recipe.rate_hz == 44100
    assert recipe.channels == 2
    assert recipe.media_type == "audio/x-raw"
    assert recipe.layout == "interleaved"
    assert recipe.sink_factory == "alsasink"
    assert recipe.plan_id == "plan:test"


def test_s2_s32le_96000_stereo_recipe_exact() -> None:
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    recipe = recipe_from_plan(_plan(rate=96000, fmt="S32_LE"))
    assert recipe.gst_format == "S32LE"
    assert recipe.rate_hz == 96000
    assert recipe.channels == 2


def test_s3_unsupported_format_fails_closed() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    with pytest.raises(StrictSinkError) as exc_info:
        recipe_from_plan(_plan(fmt="FLOAT_LE"))
    assert exc_info.value.code == "DIRECT_PLAN_INVALID"


def test_s4_recipe_device_equals_binding_locator() -> None:
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    recipe = recipe_from_plan(_plan(device="hw:CARD=DX5,DEV=1"))
    assert recipe.device == "hw:CARD=DX5,DEV=1"


def test_s5_sink_device_mismatch_fails_closed() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    plan = _plan(device="hw:CARD=DX5,DEV=0")
    inconsistent = dataclasses.replace(
        plan, sink=GstSinkSpec(factory="alsasink", device="hw:CARD=OTRO,DEV=0")
    )
    with pytest.raises(StrictSinkError) as exc_info:
        recipe_from_plan(inconsistent)
    assert exc_info.value.code == "DIRECT_PLAN_INVALID"


def test_s6_allow_resample_fails_closed() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    with pytest.raises(StrictSinkError):
        recipe_from_plan(_plan(allow_resample=True))


def test_s7_allow_remix_fails_closed() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    with pytest.raises(StrictSinkError):
        recipe_from_plan(_plan(allow_remix=True))


def test_s8_allow_processing_fails_closed() -> None:
    from michi.infrastructure.audio_output.strict_sink import (
        StrictSinkError,
        recipe_from_plan,
    )

    with pytest.raises(StrictSinkError):
        recipe_from_plan(_plan(allow_processing=True))


def test_s9_recipe_is_immutable() -> None:
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    recipe = recipe_from_plan(_plan())
    with pytest.raises(dataclasses.FrozenInstanceError):
        recipe.rate_hz = 48000  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        recipe.device = "hw:CARD=OTRO,DEV=0"  # type: ignore[misc]
