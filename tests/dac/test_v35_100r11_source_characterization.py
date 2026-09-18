"""DAC-V35-100R1.1 decoded-source and explicit-Stop corrective gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.audio_output_planner import (
    SOURCE_RATE_UNKNOWN,
    OutputPlanner,
    PlannerRefusal,
)
from michi.application.audio_output_ports import SourceCharacterizationError
from michi.application.output_session_service import OutputSessionError
from michi.domain.audio_evidence import DecodedSourceSignal, PcmTuple, SourceFileFacts
from michi.domain.audio_output import OutputPlan
from michi.infrastructure.audio_engines.gstreamer import (
    GStreamerBindings,
    GStreamerSourceCharacterizer,
)
from tests.dac.test_v34_output_planner import _evidence, _facts


def test_sc100r11_01_planner_uses_decoded_signal_not_file_metadata() -> None:
    """Decoded PCM is planning truth; file facts remain provenance only."""
    decoded = DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    contradictory_file_facts = SourceFileFacts(
        container="mp3",
        codec="MP3",
        nominal_pcm=PcmTuple(96_000, "", 2, 24),
    )

    plan = OutputPlanner().plan(
        _facts(
            decoded_source=decoded,
            source_file_facts=contradictory_file_facts,
            evidence=(_evidence(44_100, "S16_LE", 2, 16),),
        )
    )

    assert isinstance(plan, OutputPlan)
    assert plan.requested_pcm == PcmTuple(44_100, "S16_LE", 2, 16)
    assert plan.source_file_facts == contradictory_file_facts


class _CharacterizationBindings:
    def __init__(self, signal: DecodedSourceSignal) -> None:
        self.signal = signal
        self.calls: list[tuple[Path, int]] = []
        self.cancel_calls = 0
        self.on_characterize = None

    def characterize_local_file(self, path: Path, timeout_ns: int):
        self.calls.append((path, timeout_ns))
        if self.on_characterize is not None:
            self.on_characterize()
        return self.signal

    def cancel_source_characterization(self):
        self.cancel_calls += 1


def test_sc100r11_02_mp3_characterization_returns_decoded_pcm() -> None:
    decoded = DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    bindings = _CharacterizationBindings(decoded)
    characterizer = GStreamerSourceCharacterizer(bindings, timeout_ms=750)

    assert characterizer.characterize(Path("song.mp3")) == decoded
    assert bindings.calls == [(Path("song.mp3"), 750_000_000)]


def test_sc100r11_03_second_codec_characterization_is_not_hardcoded() -> None:
    decoded = DecodedSourceSignal("PCM", 96_000, 24, 2, None)
    bindings = _CharacterizationBindings(decoded)

    assert (
        GStreamerSourceCharacterizer(bindings).characterize(Path("song.flac"))
        == decoded
    )


def test_sc100r11_04_superseded_characterization_result_is_rejected() -> None:
    bindings = _CharacterizationBindings(
        DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    )
    characterizer = GStreamerSourceCharacterizer(bindings)
    bindings.on_characterize = characterizer.cancel

    with pytest.raises(SourceCharacterizationError) as caught:
        characterizer.characterize(Path("stale.mp3"))

    assert caught.value.code == "SOURCE_CHARACTERIZATION_STALE"
    assert bindings.cancel_calls == 1


def test_cancelled_generic_binding_error_is_reported_as_stale() -> None:
    bindings = _CharacterizationBindings(
        DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    )
    characterizer = GStreamerSourceCharacterizer(bindings)

    def cancel_then_fail():
        characterizer.cancel()
        raise RuntimeError("teardown raced with decode")

    bindings.on_characterize = cancel_then_fail

    with pytest.raises(SourceCharacterizationError) as caught:
        characterizer.characterize(Path("stale.mp3"))

    assert caught.value.code == "SOURCE_CHARACTERIZATION_STALE"


def test_cancel_is_nonthrowing_when_runtime_cancel_is_unavailable() -> None:
    bindings = _CharacterizationBindings(
        DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    )

    def unavailable_cancel():
        raise ImportError("GStreamer unavailable")

    bindings.cancel_source_characterization = unavailable_cancel

    GStreamerSourceCharacterizer(bindings).cancel()


class _FakeCapsStructure:
    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def get_name(self):
        return "audio/x-raw"

    def get_value(self, name):
        return self._values.get(name)


class _FakeCaps:
    def __init__(self, values: dict[str, object]) -> None:
        self._structure = _FakeCapsStructure(values)

    def get_size(self):
        return 1

    def get_structure(self, _index):
        return self._structure


class _FakePad:
    def __init__(self, caps: _FakeCaps) -> None:
        self._caps = caps

    def get_current_caps(self):
        return self._caps


class _FakeSink:
    def __init__(self, caps: _FakeCaps) -> None:
        self._pad = _FakePad(caps)
        self.properties: dict[str, object] = {}

    def set_property(self, name, value):
        self.properties[name] = value

    def get_static_pad(self, name):
        assert name == "sink"
        return self._pad


class _FakeCharacterizationPipeline:
    def __init__(self, gst) -> None:
        self._gst = gst
        self.properties: dict[str, object] = {}
        self.states: list[object] = []

    def set_property(self, name, value):
        self.properties[name] = value

    def set_state(self, state):
        self.states.append(state)
        if state is self._gst.State.NULL and self._gst.fail_null:
            return self._gst.StateChangeReturn.FAILURE
        return self._gst.StateChangeReturn.SUCCESS

    def get_state(self, _timeout_ns):
        if self._gst.timeout:
            return (
                self._gst.StateChangeReturn.ASYNC,
                self._gst.State.READY,
                self._gst.State.PAUSED,
            )
        return (
            self._gst.StateChangeReturn.SUCCESS,
            self._gst.State.PAUSED,
            self._gst.State.VOID_PENDING,
        )


class _FakeCharacterizationGst:
    class State:
        NULL = object()
        READY = object()
        PAUSED = object()
        VOID_PENDING = object()

    class StateChangeReturn:
        FAILURE = object()
        SUCCESS = object()
        ASYNC = object()

    def __init__(self, *, timeout: bool = False, fail_null: bool = False) -> None:
        self.timeout = timeout
        self.fail_null = fail_null
        self.factories: list[str] = []
        self.pipeline = _FakeCharacterizationPipeline(self)
        self.caps = _FakeCaps({"format": "S16LE", "rate": 44_100, "channels": 2})
        owner = self

        class _Factory:
            @staticmethod
            def make(name, _instance_name):
                owner.factories.append(name)
                if name == "playbin3":
                    return owner.pipeline
                if name == "fakesink":
                    return _FakeSink(owner.caps)
                return None

        self.ElementFactory = _Factory


def _bindings_with_fake_gst(gst: _FakeCharacterizationGst) -> GStreamerBindings:
    bindings = GStreamerBindings()
    bindings._gst = gst
    return bindings


def test_sc100r11_05_characterization_uses_only_fake_sinks_and_cleans_up(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.mp3"
    source.write_bytes(b"not decoded by the deterministic fake")
    gst = _FakeCharacterizationGst()

    decoded = _bindings_with_fake_gst(gst).characterize_local_file(source, 500_000_000)

    assert decoded == DecodedSourceSignal("PCM", 44_100, 16, 2, None)
    assert gst.factories == ["playbin3", "fakesink", "fakesink", "fakesink"]
    assert "alsasink" not in gst.factories
    assert gst.pipeline.states == [gst.State.PAUSED, gst.State.NULL]


def test_sc100r11_06_timeout_is_typed_and_still_cleans_up(tmp_path: Path) -> None:
    source = tmp_path / "source.flac"
    source.write_bytes(b"fake")
    gst = _FakeCharacterizationGst(timeout=True)

    with pytest.raises(SourceCharacterizationError) as caught:
        _bindings_with_fake_gst(gst).characterize_local_file(source, 1)

    assert caught.value.code == "SOURCE_CHARACTERIZATION_TIMEOUT"
    assert gst.pipeline.states[-1] is gst.State.NULL


def test_characterization_cleanup_failure_is_typed(tmp_path: Path) -> None:
    source = tmp_path / "source.flac"
    source.write_bytes(b"fake")
    gst = _FakeCharacterizationGst(fail_null=True)

    with pytest.raises(SourceCharacterizationError) as caught:
        _bindings_with_fake_gst(gst).characterize_local_file(source, 1)

    assert caught.value.code == "SOURCE_CHARACTERIZATION_CLEANUP_FAILED"


def test_sc100r11_07_productive_resolver_characterizes_before_planning(
    tmp_path: Path,
) -> None:
    from michi.domain.library import TrackMetadata
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    metadata = TrackMetadata(
        title="MP3",
        container="mp3",
        codec="MP3",
        sample_rate_hz=44_100,
        bit_depth=0,
        channels=2,
    )
    graph, bindings = _direct_graph(tmp_path, source_metadata=metadata)
    bindings.source_characterization_overrides = {
        "format": "S16LE",
        "rate": 44_100,
        "channels": 2,
    }
    source = tmp_path / "song.mp3"
    try:
        request = graph.output_session._request_for(source)

        assert request.facts is not None
        assert request.facts.decoded_source == DecodedSourceSignal(
            "PCM", 44_100, 16, 2, None
        )
        assert request.facts.source_file_facts.codec == "MP3"
        assert bindings.source_characterization_calls == [source]
        assert bindings.pipelines == []
        assert graph.direct_output_executor.handle is None
    finally:
        _close_graph(graph)


def test_sc100r11_08_characterization_failure_is_typed_before_output(
    tmp_path: Path,
) -> None:
    from tests.dac.test_v35_productive_direct_composition import (
        _close_graph,
        _direct_graph,
    )

    graph, bindings = _direct_graph(tmp_path)
    bindings.source_characterization_error = SourceCharacterizationError(
        "SOURCE_CHARACTERIZATION_TIMEOUT", "synthetic timeout"
    )
    try:
        with pytest.raises(OutputSessionError) as caught:
            graph.output_session.prepare_for_media(tmp_path / "slow.flac")

        assert caught.value.code == "SOURCE_CHARACTERIZATION_TIMEOUT"
        assert bindings.pipelines == []
        assert graph.direct_output_executor.handle is None
        assert graph.signal_truth.active_snapshot is None
    finally:
        _close_graph(graph)


def test_sc100r11_09_nonexistent_local_source_fails_before_pipeline(
    tmp_path: Path,
) -> None:
    gst = _FakeCharacterizationGst()

    with pytest.raises(SourceCharacterizationError) as caught:
        _bindings_with_fake_gst(gst).characterize_local_file(
            tmp_path / "missing.mp3", 1
        )

    assert caught.value.code == "SOURCE_FILE_UNAVAILABLE"
    assert gst.factories == []


def test_sc100r11_10_unknown_decoded_precision_never_uses_nominal_bits() -> None:
    result = OutputPlanner().plan(
        _facts(
            decoded_source=DecodedSourceSignal("PCM", 96_000, None, 2, None),
            source_file_facts=SourceFileFacts(
                "flac", "FLAC", PcmTuple(96_000, "", 2, 24)
            ),
        )
    )

    assert isinstance(result, PlannerRefusal)
    assert result.code == SOURCE_RATE_UNKNOWN
