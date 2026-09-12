"""DAC-V35-050A — runtime validator gates (R1..R9)."""

from __future__ import annotations

import pytest

from michi.infrastructure.audio_output.runtime_inspector import (
    DirectRuntimeSnapshot,
    validate_runtime,
)


def _plan(rate: int = 96000, fmt: str = "S32_LE", channels: int = 2):
    from michi.domain.audio_device import AudioDeviceBinding, BindingKind
    from michi.domain.audio_evidence import PcmTuple
    from michi.domain.audio_output import (
        FallbackKind,
        GstSinkSpec,
        OutputPlan,
        PathSemantics,
        VolumePolicy,
    )

    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=DX5,DEV=0",
        generation=1,
        currently_available=True,
        card_index=1,
        pcm_device=0,
    )
    return OutputPlan(
        plan_id="plan:test",
        stable_device_id="usb:test",
        binding=binding,
        path_semantics=PathSemantics.HARDWARE_RAW,
        requested_pcm=PcmTuple(rate, fmt, channels, 24),
        engine_id="gstreamer",
        volume_policy=VolumePolicy.FIXED,
        allow_resample=False,
        allow_remix=False,
        allow_processing=False,
        fallback=FallbackKind.STOP,
        sink=GstSinkSpec(factory="alsasink", device="hw:CARD=DX5,DEV=0"),
        resync_delay_ms=0,
        preconditions=("engine_gstreamer_direct",),
        evidence_refs=("probe:1",),
        decision_codes=("ENGINE_GSTREAMER_DIRECT",),
    )


def _recipe():
    from michi.infrastructure.audio_output.strict_sink import recipe_from_plan

    return recipe_from_plan(_plan())


def _snapshot(**overrides) -> DirectRuntimeSnapshot:
    base: dict = dict(
        execution_generation=1,
        port_generation=1,
        plan_id="plan:test",
        sink_factory="alsasink",
        sink_device="hw:CARD=DX5,DEV=0",
        negotiated_format="S32LE",
        negotiated_rate_hz=96000,
        negotiated_channels=2,
        graph_factories=("capsfilter", "alsasink"),
    )
    base.update(overrides)
    return DirectRuntimeSnapshot(**base)


def test_r1_exact_snapshot_yields_evidence() -> None:
    evidence = validate_runtime(_recipe(), _snapshot())
    assert evidence.plan_id == "plan:test"
    assert evidence.sink_factory == "alsasink"
    assert evidence.sink_device == "hw:CARD=DX5,DEV=0"
    assert evidence.negotiated_format == "S32LE"
    assert evidence.negotiated_rate_hz == 96000
    assert evidence.negotiated_channels == 2
    assert evidence.graph_factories == ("capsfilter", "alsasink")


def test_r2_wrong_plan_id_is_stale() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(plan_id="plan:otro"))
    assert exc_info.value.code == "DIRECT_STALE_EXECUTION"


def test_r3_wrong_sink_factory() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(sink_factory="autoaudiosink"))
    assert exc_info.value.code == "DIRECT_SINK_MISMATCH"


def test_r4_wrong_device() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(sink_device="hw:CARD=OTRO,DEV=0"))
    assert exc_info.value.code == "DIRECT_DEVICE_MISMATCH"


def test_r5_missing_caps_unavailable() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(negotiated_format=None))
    assert exc_info.value.code == "DIRECT_CAPS_UNAVAILABLE"


def test_r6_wrong_format() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(negotiated_format="S16LE"))
    assert exc_info.value.code == "DIRECT_FORMAT_MISMATCH"


def test_r7_wrong_rate() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(negotiated_rate_hz=48000))
    assert exc_info.value.code == "DIRECT_RATE_MISMATCH"


def test_r8_wrong_channels() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(negotiated_channels=1))
    assert exc_info.value.code == "DIRECT_CHANNEL_MISMATCH"


def test_r9_audioresample_present() -> None:
    from michi.infrastructure.audio_output.runtime_inspector import (
        DirectRuntimeValidationError,
    )

    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(
            _recipe(),
            _snapshot(graph_factories=("capsfilter", "audioresample", "alsasink")),
        )
    assert exc_info.value.code == "DIRECT_RESAMPLER_PRESENT"
