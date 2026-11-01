"""AP2-F10 S17 — DSP reconfiguration must preserve PAUSED and converge at EOS."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests.audio_phase2.test_dsd_pcm_product_dsp_e2e import _profile
from tests.audio_phase2.test_dsd_source_truth import build_dsf
from tests.audio_phase2.test_managed_productive_flow import (
    DEVICE_ID,
    _build_graph,
    _close,
)

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("gi") is None
    or shutil.which("gst-inspect-1.0") is None
    or subprocess.run(
        ["gst-inspect-1.0", "avdec_dsd_msbf"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode
    != 0,
    reason="gst-libav DSD decoder unavailable on this host",
)


def _pump_until(graph, predicate, *, timeout: float = 20.0) -> bool:
    port = graph.gstreamer_engine_provider.current_port
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        port.dispatch_pending()
        if predicate():
            return True
        time.sleep(0.02)
    port.dispatch_pending()
    return bool(predicate())


def _build_live_graph(tmp_path, monkeypatch, *, sample_count: int):
    from michi.application.settings_service import SettingsService
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from michi.domain.library import TrackMetadata
    from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
    from tests.audio_phase2.test_managed_productive_flow import _Metadata

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("MICHI_GST_LAB_SYNC", "1")
    monkeypatch.setenv("MICHI_DSD_PCM_CAPTURE", "400000")
    monkeypatch.setattr(
        _Metadata,
        "extract",
        lambda _self, _path: TrackMetadata(
            title="dsd", sample_rate_hz=2_822_400, bit_depth=1, channels=2
        ),
    )
    settings = SettingsService(
        SQLiteSettingsRepository.open_for_startup(tmp_path / "michi.db")
    )
    settings.set_dsd_pcm_conversion_consent(True)
    settings.set_dsd_pcm_dsp_consent(True)
    graph, coordinator = _build_graph(tmp_path, settings_service=settings)
    source = tmp_path / "paused-eos.dsf"
    source.write_bytes(build_dsf(sample_count=sample_count))
    graph.dac_qualification.cache_evidence(
        DEVICE_ID,
        (
            CapabilityEvidence(
                stable_device_id=DEVICE_ID,
                tuple=PcmTuple(88_200, "F32LE", 2, 32),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="michi-alsa-probe",
                observed_at_ns=1,
                environment_fingerprint=(
                    graph.dac_qualification.current_environment_fingerprint(DEVICE_ID)
                ),
                evidence_refs=("probe:dsd-pcm-f32",),
            ),
        ),
    )
    graph.set_processing_profile(_profile())
    coordinator.select_device(DEVICE_ID)
    coordinator.select_path_mode("strict")
    return graph, source


def _signal():
    from michi.domain.audio_signal import ChannelLayout, PcmSignalFormat

    return PcmSignalFormat(
        rate_hz=88_200,
        transport_format="F32LE",
        significant_bits=32,
        layout=ChannelLayout(positions=("FL", "FR")),
    )


def test_dsp_reconfiguration_while_paused_never_autoplays(
    tmp_path, monkeypatch
) -> None:
    from michi.domain.audio_processing import ProcessingGraph
    from michi.domain.playback import PlaybackStatus
    from tests.audio_phase2.test_processing_productive_composition import (
        _InlineExecutor,
    )

    graph, source = _build_live_graph(tmp_path, monkeypatch, sample_count=28_224_000)
    try:
        accepted: list[Path] = []
        graph.playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert _pump_until(
            graph,
            lambda: (
                graph.output_session.state.value == "running"
                and graph.audio_processing.effective_state.value == "effective"
            ),
        )

        graph.playback.pause()
        assert _pump_until(
            graph, lambda: graph.playback.state.status is PlaybackStatus.PAUSED
        )

        executor = _InlineExecutor()
        disabled: list[bool] = []
        failures: list[Exception] = []
        graph.audio_processing.disable_processing_async(
            on_done=disabled.append,
            on_failed=failures.append,
            async_submit=executor.submit,
        )
        assert _pump_until(graph, lambda: bool(disabled or failures))
        assert disabled == []
        assert len(failures) == 1
        assert "DSP_PAUSED_REQUIRES_RESUME" in str(failures[0])
        identity = graph.gstreamer_engine_provider.current_port.query_dsd_pcm_identity()
        assert identity["processing"]["graph_revision"] == 1
        time.sleep(0.3)
        assert graph.playback.state.status is PlaybackStatus.PAUSED

        graph.playback.resume()
        assert _pump_until(
            graph, lambda: graph.playback.state.status is PlaybackStatus.PLAYING
        )

        disabled.clear()
        failures.clear()
        graph.audio_processing.disable_processing_async(
            on_done=disabled.append,
            on_failed=failures.append,
            async_submit=executor.submit,
        )
        assert _pump_until(graph, lambda: bool(disabled or failures)), failures
        assert failures == []
        assert disabled == [True]
        assert graph.audio_processing.effective_state.value == "bypassed"

        applied: list[dict] = []
        graph.audio_processing.apply_processing_async(
            ProcessingGraph(
                graph_id="graph:dsd-resumed",
                revision=3,
                nodes=_profile().graph.nodes,
            ),
            _signal(),
            on_done=applied.append,
            on_failed=failures.append,
            async_submit=executor.submit,
        )
        assert _pump_until(graph, lambda: bool(applied or failures)), failures
        assert failures == []
        assert applied and applied[0]["plan_id"]
        assert graph.audio_processing.effective_state.value == "effective"
        identity = graph.gstreamer_engine_provider.current_port.query_dsd_pcm_identity()
        assert identity["processing"]["caps_source"] == "negotiated"
        assert identity["processing"]["graph_revision"] == 3

        graph.playback.stop()
        assert graph.output_session.state.value == "idle"
    finally:
        _close(graph)


def test_eos_invalidates_dsp_and_never_autoplays(tmp_path, monkeypatch) -> None:
    from michi.domain.signal_truth import OutputFamilyState

    graph, source = _build_live_graph(tmp_path, monkeypatch, sample_count=2_822_400)
    try:
        accepted: list[Path] = []
        graph.playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        assert _pump_until(
            graph,
            lambda: (
                graph.output_session.state.value == "running"
                and graph.audio_processing.effective_state.value == "effective"
            ),
        )

        def eos_observed() -> bool:
            return any(
                event.family == "dsd_pcm"
                and event.state is OutputFamilyState.UNAVAILABLE
                and event.detail == "eos"
                for event in graph.signal_truth.output_family_events
            )

        assert _pump_until(graph, eos_observed, timeout=20.0)
        assert graph.audio_processing.effective_state.value == "unavailable"
        assert accepted == [source]
        graph.playback.stop()
        assert graph.output_session.state.value == "idle"
        assert accepted == [source]
    finally:
        _close(graph)
