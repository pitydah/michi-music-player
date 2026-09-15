"""DAC-V35-070 productive Signal Truth gates ST70-40..44."""

from pathlib import Path

import pytest

from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
from tests.dac.test_v35_productive_direct_composition import (
    _accept_current,
    _close_graph,
    _direct_graph,
)

_HW_PARAMS = """access: RW_INTERLEAVED
format: S32_LE
subformat: STD
channels: 2
rate: 96000 (96000/1)
period_size: 1024
buffer_size: 4096
msbits: 24
"""

_QT_APP = None


def _read_hw_params(path: str) -> str:
    return "DX5\n" if path.endswith("/id") else _HW_PARAMS


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def test_st70_40_production_graph_owns_one_signal_truth_recorder(
    tmp_path: Path,
) -> None:
    graph, _bindings = _direct_graph(tmp_path)
    try:
        assert graph.direct_output_executor._signal_truth is graph.signal_truth
    finally:
        _close_graph(graph)


def test_st70_41_productive_runtime_chain_can_classify_direct(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_read_hw_params)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        snapshot = graph.signal_truth.active_snapshot
        assert snapshot is not None
        assert snapshot.verdict is SignalTruthVerdict.DIRECT
        assert snapshot.source_file_facts is not None
        assert snapshot.decoded_runtime is not None
        assert snapshot.engine_effective is not None
        assert snapshot.device_negotiated is not None
    finally:
        _close_graph(graph)


def test_st70_42_missing_alsa_readback_stays_unknown(tmp_path: Path) -> None:
    graph, bindings = _direct_graph(
        tmp_path,
        alsa_hw_params_reader=lambda path: (
            "DX5\n"
            if path.endswith("/id")
            else (_ for _ in ()).throw(FileNotFoundError())
        ),
    )
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        snapshot = graph.signal_truth.active_snapshot
        assert snapshot is not None
        assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
        assert SignalTruthReason.ST_MISSING_ALSA in snapshot.reasons
    finally:
        _close_graph(graph)


def test_st70_43_productive_replacement_respects_destructive_boundary(
    tmp_path: Path,
) -> None:
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_read_hw_params)
    try:
        graph.playback.load_and_play(tmp_path / "a.flac")
        _accept_current(graph, bindings)
        old = graph.signal_truth.active_snapshot
        assert old is not None

        graph.playback.load_and_play(tmp_path / "b.flac")

        assert graph.signal_truth.active_snapshot is None
        assert graph.signal_truth.candidate_snapshot.identity != old.identity
        _accept_current(graph, bindings)
        assert graph.signal_truth.active_snapshot is not None
        assert graph.signal_truth.active_snapshot.identity != old.identity
    finally:
        _close_graph(graph)


def test_st70_44_current_runtime_error_is_captured_before_release(
    tmp_path: Path,
) -> None:
    from test_gstreamer_audio_port import _deliver, _FakeMsgType, _msg

    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_read_hw_params)
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        port = graph.gstreamer_engine_provider.current_port
        message, generation = _msg(
            port,
            _FakeMsgType.ERROR,
            bindings.pipelines[-1],
            error_text="ALSA XRUN",
        )
        _deliver(port, message, generation)

        assert graph.signal_truth.active_snapshot is None
        assert graph.signal_truth.last_snapshot is not None
        assert (
            graph.signal_truth.last_snapshot.verdict is SignalTruthVerdict.CONTRADICTED
        )
        assert SignalTruthReason.ST_XRUN in graph.signal_truth.last_snapshot.reasons
    finally:
        _close_graph(graph)
