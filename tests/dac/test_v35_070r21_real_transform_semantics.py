"""DAC-V35-070R2.1 mandatory real GI transform/pass-through gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
from michi.infrastructure.audio_output.runtime_inspector import (
    DIRECT_CONVERTER_ACTIVE,
    DIRECT_RESAMPLER_ACTIVE,
    DirectRuntimeValidationError,
    validate_runtime_semantics,
)
from michi.infrastructure.audio_output.strict_sink import StrictSinkRecipe
from tests.dac.test_v35_070_signal_truth import (
    _alsa,
    _complete,
    _engine,
    _identity,
    _pcm,
)
from tests.dac.test_v35_070r2_real_gstreamer_provenance import (
    _build_runtime_test_sink,
    _gst_runtime,
    _prerolled_playbin,
    _RealGraphView,
)


@dataclass(frozen=True)
class _RuntimeRecipe:
    plan_id: str
    sink_factory: str = "fakesink"
    device: str = ""
    format: str = "S16LE"
    rate: int = 48_000
    channels: int = 2

    def caps_string(self) -> str:
        return (
            f"audio/x-raw,format={self.format},rate={self.rate},"
            f"channels={self.channels},layout=interleaved"
        )


def _real_snapshot(
    tmp_path: Path,
    *,
    source_format: str = "S16LE",
    source_rate: int = 48_000,
    source_channels: int = 2,
    sink_format: str = "S16LE",
    sink_rate: int = 48_000,
    sink_channels: int = 2,
):
    recipe = _RuntimeRecipe(
        plan_id=(
            f"r21:{source_format}:{source_rate}:{source_channels}:"
            f"{sink_format}:{sink_rate}:{sink_channels}"
        ),
        format=sink_format,
        rate=sink_rate,
        channels=sink_channels,
    )
    gst, bindings, recipe, pipeline, sink = _prerolled_playbin(
        tmp_path,
        recipe,
        source_format,
        source_rate,
        source_channels,
    )
    snapshot = bindings.snapshot_direct_runtime(
        pipeline,
        recipe,
        execution_generation=1,
        port_generation=1,
    )
    return gst, pipeline, sink, recipe, snapshot


def _validation_recipe(recipe: _RuntimeRecipe) -> StrictSinkRecipe:
    return StrictSinkRecipe(
        plan_id=recipe.plan_id,
        sink_factory="alsasink",
        device="hw:CARD=TEST,DEV=0",
        media_type="audio/x-raw",
        gst_format=recipe.format,
        rate_hz=recipe.rate,
        channels=recipe.channels,
        layout="interleaved",
    )


def _truth_from_real(snapshot, *, source_rate=48_000, source_channels=2):
    identity = _identity()
    decoded = _pcm(
        rate=source_rate,
        fmt=snapshot.decoded_format.replace("LE", "_LE"),
        channels=source_channels,
        significant_bits=snapshot.decoded_significant_bits,
    )
    effective = _pcm(
        rate=snapshot.negotiated_rate_hz,
        fmt=snapshot.negotiated_format.replace("LE", "_LE"),
        channels=snapshot.negotiated_channels,
        significant_bits=snapshot.effective_significant_bits,
    )
    engine = replace(
        _engine(identity, pcm=effective),
        transform_evidence=snapshot.transform_evidence,
    )
    return _complete(
        decoded=decoded,
        engine=engine,
        alsa=_alsa(identity, pcm=effective),
    ).candidate_snapshot


@pytest.mark.gstreamer_runtime
def test_r21_04_real_audioconvert_passthrough_is_observed(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(tmp_path)
    try:
        assert snapshot.transform_evidence.converter_present is True
        assert snapshot.transform_evidence.converter_transforming is False
        assert snapshot.transform_evidence.remix_transforming is False
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_05_real_audioconvert_active_conversion_is_observed(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(
        tmp_path,
        source_format="S16LE",
        sink_format="S32LE",
    )
    try:
        assert snapshot.transform_evidence.converter_present is True
        assert snapshot.transform_evidence.converter_transforming is True
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_06_real_audioresample_passthrough_is_observed(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(tmp_path)
    try:
        assert snapshot.transform_evidence.resampler_present is True
        assert snapshot.transform_evidence.resampler_transforming is False
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_07_real_audioresample_active_change_is_observed(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(
        tmp_path,
        source_rate=96_000,
        sink_rate=48_000,
    )
    try:
        assert snapshot.transform_evidence.resampler_present is True
        assert snapshot.transform_evidence.resampler_transforming is True
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_10_real_passthrough_snapshot_reaches_production_validator(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, recipe, snapshot = _real_snapshot(tmp_path)
    try:
        evidence = validate_runtime_semantics(
            _validation_recipe(recipe),
            snapshot,
            require_sink_identity=False,
        )
        assert evidence.negotiated_format == "S16LE"
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_11_real_active_resample_fails_production_validator(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, recipe, snapshot = _real_snapshot(
        tmp_path,
        source_rate=96_000,
        sink_rate=48_000,
    )
    try:
        with pytest.raises(DirectRuntimeValidationError) as exc_info:
            validate_runtime_semantics(
                _validation_recipe(recipe),
                snapshot,
                require_sink_identity=False,
            )
        assert exc_info.value.code == DIRECT_RESAMPLER_ACTIVE
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_12_real_active_conversion_is_bounded_by_production_validator(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, recipe, snapshot = _real_snapshot(
        tmp_path,
        source_format="S16LE",
        sink_format="S32LE",
    )
    try:
        with pytest.raises(DirectRuntimeValidationError) as exc_info:
            validate_runtime_semantics(
                _validation_recipe(recipe),
                snapshot,
                require_sink_identity=False,
            )
        assert exc_info.value.code == DIRECT_CONVERTER_ACTIVE
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
@pytest.mark.parametrize(
    ("unrelated_factory", "field"),
    [
        ("audioconvert", "converter_present"),
        ("audioresample", "resampler_present"),
    ],
)
def test_r21_13_14_unrelated_transform_branch_is_ignored(
    unrelated_factory: str,
    field: str,
) -> None:
    gst = _gst_runtime()
    from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings

    bindings = GStreamerBindings()
    bindings.ensure_loaded()
    recipe = _RuntimeRecipe("r21-unrelated")
    pipeline = gst.Pipeline.new(None)
    source = gst.ElementFactory.make("audiotestsrc", "selected_source")
    capsfilter = gst.ElementFactory.make("capsfilter", "selected_caps")
    sink = _build_runtime_test_sink(gst, recipe)
    unrelated = gst.ElementFactory.make(unrelated_factory, "unrelated_transform")
    elements = (pipeline, source, capsfilter, sink, unrelated)
    assert all(item is not None for item in elements)
    capsfilter.set_property("caps", gst.Caps.from_string(recipe.caps_string()))
    for element in (source, capsfilter, sink, unrelated):
        assert pipeline.add(element)
    assert source.link(capsfilter)
    assert capsfilter.link(sink)
    graph = _RealGraphView(sink, pipeline)
    try:
        assert pipeline.set_state(gst.State.PAUSED) != gst.StateChangeReturn.FAILURE
        result, state, _pending = pipeline.get_state(5 * gst.SECOND)
        assert result != gst.StateChangeReturn.FAILURE
        assert state == gst.State.PAUSED
        snapshot = bindings.snapshot_direct_runtime(
            graph,
            recipe,
            execution_generation=1,
            port_generation=1,
        )
        assert getattr(snapshot.transform_evidence, field) is False
        assert unrelated_factory not in snapshot.graph_factories
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_17_18_real_selected_decoder_and_proxy_path_remain_valid(
    tmp_path: Path,
) -> None:
    gst, pipeline, sink, _recipe, snapshot = _real_snapshot(tmp_path)
    try:
        assert snapshot.decoded_format == "S16LE"
        assert snapshot.graph_inspection_complete is True
        assert isinstance(sink.get_static_pad("sink"), gst.GhostPad)
        assert isinstance(sink.get_static_pad("sink").get_peer(), gst.GhostPad)
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_21_real_passthrough_converter_does_not_become_dsp(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(tmp_path)
    try:
        assert _truth_from_real(snapshot).verdict is SignalTruthVerdict.DIRECT
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_22_real_passthrough_resampler_does_not_become_resampled(
    tmp_path: Path,
) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(tmp_path)
    try:
        assert _truth_from_real(snapshot).verdict is SignalTruthVerdict.DIRECT
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_23_real_active_resample_becomes_resampled(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(
        tmp_path,
        source_rate=96_000,
        sink_rate=48_000,
    )
    try:
        truth = _truth_from_real(snapshot, source_rate=96_000)
        assert truth.verdict is SignalTruthVerdict.RESAMPLED
        assert SignalTruthReason.ST_RATE_MISMATCH in truth.reasons
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_24_real_channel_change_becomes_remixed(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, snapshot = _real_snapshot(
        tmp_path,
        source_channels=2,
        sink_channels=1,
    )
    try:
        truth = _truth_from_real(snapshot, source_channels=2)
        assert truth.verdict is SignalTruthVerdict.REMIXED
        assert SignalTruthReason.ST_CHANNEL_MISMATCH in truth.reasons
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r21_30_real_gstreamer_teardown_reaches_null(tmp_path: Path) -> None:
    gst, pipeline, _sink, _recipe, _snapshot = _real_snapshot(tmp_path)

    assert pipeline.set_state(gst.State.NULL) != gst.StateChangeReturn.FAILURE
    result, state, _pending = pipeline.get_state(5 * gst.SECOND)
    assert result != gst.StateChangeReturn.FAILURE
    assert state == gst.State.NULL
