"""DAC-V35-070R2 mandatory real GI/GStreamer/playbin3 provenance gates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from michi.infrastructure.audio_engines.gstreamer import GStreamerBindings


@dataclass(frozen=True)
class _Recipe:
    plan_id: str = "r2-real"
    sink_factory: str = "fakesink"
    device: str = ""

    @staticmethod
    def caps_string() -> str:
        return "audio/x-raw,format=S16LE,rate=48000,channels=2"


@dataclass(frozen=True)
class _S32Recipe(_Recipe):
    plan_id: str = "r2-real-s32"

    @staticmethod
    def caps_string() -> str:
        return (
            "audio/x-raw,format=S32LE,rate=48000,channels=2,"
            "significant-bits=24,depth=24"
        )


@dataclass(frozen=True)
class _S24Recipe(_Recipe):
    plan_id: str = "r2-real-s24"

    @staticmethod
    def caps_string() -> str:
        return "audio/x-raw,format=S24LE,rate=48000,channels=2"


def _gst_runtime():
    try:
        import gi

        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ImportError, ValueError) as exc:  # pragma: no cover - CI config failure
        pytest.fail(f"R2 mandatory GI/GStreamer runtime unavailable: {exc}")
    Gst.init(None)
    return Gst


def _require_factory(gst, name: str) -> None:
    assert gst.ElementFactory.find(name) is not None, (
        f"R2 mandatory GStreamer factory unavailable: {name}"
    )


def _write_flac(gst, path: Path, source_format: str = "S16LE") -> None:
    pipeline = gst.parse_launch(
        "audiotestsrc num-buffers=20 wave=silence ! "
        f"audio/x-raw,format={source_format},rate=48000,channels=2 ! "
        f"flacenc ! filesink location={path}"
    )
    try:
        assert pipeline.set_state(gst.State.PLAYING) != gst.StateChangeReturn.FAILURE
        message = pipeline.get_bus().timed_pop_filtered(
            5 * gst.SECOND, gst.MessageType.EOS | gst.MessageType.ERROR
        )
        assert message is not None and message.type == gst.MessageType.EOS
    finally:
        pipeline.set_state(gst.State.NULL)


def _build_runtime_test_sink(gst, recipe):
    sink_bin = gst.Bin.new("michi_direct_sink")
    capsfilter = gst.ElementFactory.make("capsfilter", "michi_direct_caps")
    sink = gst.ElementFactory.make("fakesink", "michi_direct_alsa")
    assert sink_bin is not None and capsfilter is not None and sink is not None
    capsfilter.set_property("caps", gst.Caps.from_string(recipe.caps_string()))
    sink.set_property("sync", False)
    assert sink_bin.add(capsfilter)
    assert sink_bin.add(sink)
    assert capsfilter.link(sink)
    ghost = gst.GhostPad.new("sink", capsfilter.get_static_pad("sink"))
    assert ghost is not None and sink_bin.add_pad(ghost)
    return sink_bin


def _prerolled_playbin(tmp_path: Path, recipe=None, source_format: str = "S16LE"):
    gst = _gst_runtime()
    for name in ("playbin3", "alsasink", "flacenc", "flacdec"):
        _require_factory(gst, name)
    media = tmp_path / "r2-real.flac"
    _write_flac(gst, media, source_format)
    bindings = GStreamerBindings()
    bindings.ensure_loaded()
    recipe = recipe or _Recipe()
    pipeline = bindings.make_playbin3()
    assert pipeline is not None
    sink = _build_runtime_test_sink(gst, recipe)
    bindings.set_audio_sink(pipeline, sink)
    pipeline.set_property("uri", media.as_uri())
    assert pipeline.set_state(gst.State.PAUSED) != gst.StateChangeReturn.FAILURE
    state_result, state, _pending = pipeline.get_state(5 * gst.SECOND)
    assert state_result != gst.StateChangeReturn.FAILURE
    assert state == gst.State.PAUSED
    return gst, bindings, recipe, pipeline, sink


@pytest.mark.gstreamer_runtime
def test_r2_21_required_real_gstreamer_factories_are_installed() -> None:
    gst = _gst_runtime()

    for name in ("playbin3", "alsasink", "capsfilter", "flacenc", "flacdec"):
        _require_factory(gst, name)


@pytest.mark.gstreamer_runtime
def test_r2_22_real_playbin_selected_decoder_caps_are_observed(tmp_path: Path) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(tmp_path)
    try:
        snapshot = bindings.snapshot_direct_runtime(
            pipeline, recipe, execution_generation=7, port_generation=11
        )

        assert snapshot.graph_inspection_complete is True
        assert snapshot.decoded_format == "S16LE"
        assert snapshot.decoded_rate_hz == 48000
        assert snapshot.decoded_channels == 2
        assert snapshot.decoded_significant_bits == 16
    finally:
        assert pipeline.set_state(gst.State.NULL) != gst.StateChangeReturn.FAILURE


@pytest.mark.gstreamer_runtime
@pytest.mark.parametrize(
    (
        "recipe",
        "source_format",
        "expected_bits",
        "decoded_format",
        "decoded_bits",
    ),
    [
        (_Recipe(), "S16LE", 16, "S16LE", 16),
        (_S24Recipe(), "S24LE", 24, "S24_32LE", None),
    ],
)
def test_r2_23_real_effective_caps_use_intrinsic_format_precision(
    tmp_path: Path,
    recipe,
    source_format: str,
    expected_bits: int,
    decoded_format: str,
    decoded_bits: int | None,
) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(
        tmp_path, recipe, source_format
    )
    try:
        snapshot = bindings.snapshot_direct_runtime(
            pipeline, recipe, execution_generation=1, port_generation=1
        )

        assert snapshot.negotiated_format == source_format
        assert snapshot.effective_significant_bits == expected_bits
        assert snapshot.decoded_format == decoded_format
        assert snapshot.decoded_significant_bits == decoded_bits
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r2_24_real_selected_branch_reports_reachable_factories(
    tmp_path: Path,
) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(tmp_path)
    try:
        snapshot = bindings.snapshot_direct_runtime(
            pipeline, recipe, execution_generation=1, port_generation=1
        )

        assert "flacdec" in snapshot.graph_factories
        assert "capsfilter" in snapshot.graph_factories
        assert "fakesink" in snapshot.graph_factories
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r2_25_real_path_crosses_ghost_proxy_and_factoryless_bin(
    tmp_path: Path,
) -> None:
    gst, _bindings, _recipe, pipeline, sink = _prerolled_playbin(tmp_path)
    try:
        external_sink_pad = sink.get_static_pad("sink")
        upstream = external_sink_pad.get_peer()

        assert isinstance(external_sink_pad, gst.GhostPad)
        assert isinstance(upstream, gst.GhostPad)
        assert upstream.get_parent_element() is not None
        assert upstream.get_parent_element().get_factory() is None
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r2_26_real_unrelated_decoder_cannot_create_ambiguity(
    tmp_path: Path,
) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(tmp_path)
    unrelated = gst.ElementFactory.make("flacdec", "r2_unrelated_decoder")
    assert unrelated is not None and pipeline.add(unrelated)
    try:
        snapshot = bindings.snapshot_direct_runtime(
            pipeline, recipe, execution_generation=1, port_generation=1
        )

        assert snapshot.decoded_format == "S16LE"
        assert snapshot.decoded_significant_bits == 16
    finally:
        pipeline.set_state(gst.State.NULL)


class _RealGraphView:
    def __init__(self, sink, pipeline) -> None:
        self._sink = sink
        self._pipeline = pipeline

    def get_property(self, name):
        if name == "audio-sink":
            return self._sink
        if name == "volume":
            return 1.0
        if name == "mute":
            return False
        return None

    def get_clock(self):
        return self._pipeline.get_clock()


def _real_static_graph(gst, bindings, upstream_elements):
    recipe = _Recipe()
    pipeline = gst.Pipeline.new(None)
    sink = _build_runtime_test_sink(gst, recipe)
    mixer = gst.ElementFactory.make("audiomixer", "r2_mixer")
    assert pipeline is not None and mixer is not None
    assert pipeline.add(mixer)
    assert pipeline.add(sink)
    assert mixer.link(sink)
    for element in upstream_elements:
        assert pipeline.add(element)
        assert element.link(mixer)
    return recipe, pipeline, sink, _RealGraphView(sink, pipeline)


@pytest.mark.gstreamer_runtime
def test_r2_27_real_multiple_reachable_decoders_are_ambiguous() -> None:
    gst = _gst_runtime()
    bindings = GStreamerBindings()
    bindings.ensure_loaded()
    decoders = tuple(
        gst.ElementFactory.make("flacdec", f"r2_decoder_{index}") for index in range(2)
    )
    assert all(decoder is not None for decoder in decoders)
    recipe, pipeline, _sink, graph = _real_static_graph(gst, bindings, decoders)
    try:
        snapshot = bindings.snapshot_direct_runtime(
            graph, recipe, execution_generation=1, port_generation=1
        )

        assert snapshot.graph_inspection_complete is True
        assert snapshot.decoded_format is None
        assert snapshot.decoded_significant_bits is None
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r2_28_real_zero_reachable_decoders_stays_unknown() -> None:
    gst = _gst_runtime()
    bindings = GStreamerBindings()
    bindings.ensure_loaded()
    identity = gst.ElementFactory.make("identity", "r2_not_a_decoder")
    assert identity is not None
    recipe, pipeline, _sink, graph = _real_static_graph(gst, bindings, (identity,))
    try:
        snapshot = bindings.snapshot_direct_runtime(
            graph, recipe, execution_generation=1, port_generation=1
        )

        assert snapshot.graph_inspection_complete is True
        assert snapshot.decoded_format is None
    finally:
        pipeline.set_state(gst.State.NULL)


@pytest.mark.gstreamer_runtime
def test_r2_29_real_playbin_teardown_reaches_null_bounded(tmp_path: Path) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(tmp_path)
    bindings.snapshot_direct_runtime(
        pipeline, recipe, execution_generation=1, port_generation=1
    )

    assert pipeline.set_state(gst.State.NULL) != gst.StateChangeReturn.FAILURE
    result, state, _pending = pipeline.get_state(5 * gst.SECOND)
    assert result != gst.StateChangeReturn.FAILURE
    assert state == gst.State.NULL


@pytest.mark.gstreamer_runtime
def test_r2_30_real_custom_caps_fields_cannot_fill_s32_precision(
    tmp_path: Path,
) -> None:
    gst, bindings, recipe, pipeline, _sink = _prerolled_playbin(tmp_path, _S32Recipe())
    try:
        snapshot = bindings.snapshot_direct_runtime(
            pipeline, recipe, execution_generation=1, port_generation=1
        )

        assert snapshot.negotiated_format == "S32LE"
        assert snapshot.effective_significant_bits is None
    finally:
        pipeline.set_state(gst.State.NULL)
