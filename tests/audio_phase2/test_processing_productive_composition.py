"""AP2-F05 Package A — production composition proof.

The REAL bootstrap graph must expose ONE AudioProcessingService wired over
the SAME hosted GStreamer port that plays audio; applying DSP through the
graph (not a private test service) must be possible, observable, and
reversible. Uses the lab sink so no DAC is required.
"""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

import pytest

_HAS_GI = importlib.util.find_spec("gi") is not None

pytestmark = pytest.mark.skipif(
    not _HAS_GI, reason="PyGObject/GStreamer not available on this host"
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run"
    / "fixtures/pcm16_44100.wav"
)


class _InlineExecutor:
    def submit(self, work, completed) -> None:
        try:
            value = work()
        except Exception as exc:  # noqa: BLE001 - typed completion boundary
            completed(None, exc)
        else:
            completed(value, None)


def _build_real_graph(tmp_path):
    from michi.bootstrap import _build_services
    from tests.conftest import FakeAudioPort

    graph = _build_services(
        tmp_path / "michi.db",
        backend=FakeAudioPort(),
        output_preparation_executor=_InlineExecutor(),
    )
    assert hasattr(graph, "audio_processing"), "production graph must own DSP"
    return graph


def test_production_graph_owns_one_processing_authority() -> None:
    import tempfile

    from michi.application.audio_processing_service import AudioProcessingService

    graph = _build_real_graph(Path(tempfile.mkdtemp()))
    assert isinstance(graph.audio_processing, AudioProcessingService)
    # ONE processing authority: the service is composed over the SAME
    # hosted provider port provider used by the Direct executor.
    provider = graph.gstreamer_engine_provider
    assert provider.current_port is None  # nothing opened yet
    truth = graph.audio_processing.processing_truth()
    assert truth["effective_state"] in {"bypassed", "unavailable", "preparing"}
    assert truth["bit_perfect"] is True  # nothing effective yet


def test_productive_dsp_through_the_real_graph(tmp_path, monkeypatch) -> None:
    """Apply DSP through the graph's service over REAL media + host."""
    if not FIXTURE.is_file():
        pytest.skip("PCM fixture unavailable")
    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")

    graph = _build_real_graph(tmp_path)
    port = graph.gstreamer_engine_provider.open()
    try:
        port.set_volume(0)
        port.load(FIXTURE)
        deadline = time.monotonic() + 30.0
        while not port.backend_state() and time.monotonic() < deadline:
            port.dispatch_pending()
            time.sleep(0.02)

        from michi.domain.audio_processing import PreampNode, ProcessingGraph
        from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

        signal = PcmSignalFormat(
            rate_hz=44100,
            transport_format="S16LE",
            significant_bits=16,
            layout=ChannelLayout(positions=("FL", "FR")),
        )
        graph_spec = ProcessingGraph(
            graph_id="graph:productive",
            revision=1,
            nodes=(PreampNode(node_id="pre", gain_db=-6.0),),
        )
        results: list[dict] = []
        failures: list[Exception] = []
        graph.audio_processing.apply_processing_async(
            graph_spec,
            signal,
            on_done=results.append,
            on_failed=failures.append,
            async_submit=_InlineExecutor().submit,
        )
        assert not failures, failures
        assert results and results[0]["plan_id"]
        assert graph.audio_processing.effective_state.value == "effective"
        truth = graph.audio_processing.processing_truth()
        assert truth["effective_state"] == "effective"
        assert truth["bit_perfect"] is False  # transforming path

        # The productive chain really processes (measured through the graph).
        metrics = port.capture_processing_output(0.7)
        assert metrics["frames"] > 0 and metrics["rms"] > 0.0

        # Disable through the same authority: proven bypass.
        disabled: list[bool] = []
        graph.audio_processing.disable_processing_async(
            on_done=disabled.append,
            on_failed=failures.append,
            async_submit=_InlineExecutor().submit,
        )
        assert not failures, failures
        assert disabled == [True]
        assert graph.audio_processing.effective_state.value == "bypassed"
        assert graph.audio_processing.processing_truth()["bit_perfect"] is True
    finally:
        port.close()


def test_dsp_request_before_gstreamer_open_fails_closed(tmp_path) -> None:
    """No hosted port -> typed transport refusal; requested intent survives."""
    import tempfile

    graph = _build_real_graph(Path(tempfile.mkdtemp()))
    from michi.domain.audio_processing import PreampNode, ProcessingGraph
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    signal = PcmSignalFormat(
        rate_hz=44100,
        transport_format="S16LE",
        significant_bits=16,
        layout=ChannelLayout(positions=("FL", "FR")),
    )
    graph_spec = ProcessingGraph(
        graph_id="graph:no-host",
        revision=1,
        nodes=(PreampNode(node_id="pre", gain_db=-3.0),),
    )
    failures: list[Exception] = []
    graph.audio_processing.apply_processing_async(
        graph_spec,
        signal,
        on_failed=failures.append,
        async_submit=_InlineExecutor().submit,
    )
    # Fail-closed chain: without a hosted port the capabilities are empty
    # and/or the transport is unavailable — never a false EFFECTIVE.
    assert failures and any(
        key in str(failures[0])
        for key in ("DSP_TRANSPORT_UNAVAILABLE", "DSP_STRATEGY_UNAVAILABLE")
    )
    assert graph.audio_processing.effective_state.value != "effective"
