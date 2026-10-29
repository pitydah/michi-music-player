"""AP2-F10 — selected F06 profile drives real DSD→PCM product playback."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from tests.audio_phase2.test_dsd_source_truth import build_dsf
from tests.audio_phase2.test_managed_productive_flow import (
    DEVICE_ID,
    _build_graph,
    _close,
)

_HAS_GI = importlib.util.find_spec("gi") is not None


def _has_dsd_decoder() -> bool:
    inspector = shutil.which("gst-inspect-1.0")
    if inspector is None:
        return False
    return (
        subprocess.run(
            [inspector, "avdec_dsd_msbf"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


pytestmark = pytest.mark.skipif(
    not _HAS_GI or not _has_dsd_decoder(),
    reason="gst-libav DSD decoder unavailable on this host",
)


def _profile():
    from michi.domain.audio_processing import (
        BiquadType,
        ParametricEqNode,
        PeqBand,
        ProcessingGraph,
        ProcessingProfile,
    )

    return ProcessingProfile(
        profile_id="profile:dsd-peq",
        display_name="DSD PEQ",
        graph=ProcessingGraph(
            graph_id="graph:dsd-product-peq",
            revision=1,
            nodes=(
                ParametricEqNode(
                    node_id="peq",
                    bands=(PeqBand("b1", BiquadType.PEAK, 1000.0, 1.4, 12.0, True),),
                ),
            ),
        ),
    )


def test_selected_profile_is_effective_on_product_dsd_playback(tmp_path, monkeypatch):
    from michi.application.settings_service import SettingsService
    from michi.domain.audio_evidence import (
        CapabilityEvidence,
        EvidenceStrength,
        PcmTuple,
    )
    from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

    monkeypatch.setenv("MICHI_GST_LAB_SINK", "fakesink")
    monkeypatch.setenv("MICHI_DSD_PCM_CAPTURE", "400000")
    from michi.domain.library import TrackMetadata
    from tests.audio_phase2.test_managed_productive_flow import _Metadata

    monkeypatch.setattr(
        _Metadata,
        "extract",
        lambda _self, _path: TrackMetadata(
            title="dsd", sample_rate_hz=2_822_400, bit_depth=1, channels=2
        ),
    )
    db = tmp_path / "michi.db"
    settings = SettingsService(SQLiteSettingsRepository.open_for_startup(db))
    settings.set_dsd_pcm_conversion_consent(True)
    settings.set_dsd_pcm_dsp_consent(True)
    graph, coordinator = _build_graph(tmp_path, settings_service=settings)
    source = tmp_path / "product-dsp.dsf"
    source.write_bytes(build_dsf(sample_count=8_192))
    try:
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
                        graph.dac_qualification.current_environment_fingerprint(
                            DEVICE_ID
                        )
                    ),
                    evidence_refs=("probe:dsd-pcm-f32",),
                ),
            ),
        )
        graph.set_processing_profile(_profile())
        coordinator.select_device(DEVICE_ID)
        coordinator.select_path_mode("strict")
        accepted: list[Path] = []
        graph.playback.load_and_play(source, on_accepted=accepted.append)
        assert accepted == [source]
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if graph.output_session.state.value == "running":
                break
            graph.gstreamer_engine_provider.current_port.dispatch_pending()
            time.sleep(0.02)
        assert graph.output_session.state.value == "running"
        assert graph.audio_processing.effective_state.value == "effective"
        assert (
            graph.output_session._dsd_pcm_prepared.runtime_identity[
                "processing_effective"
            ]
            is True
        )
        port = graph.gstreamer_engine_provider.current_port
        identity = port.query_dsd_pcm_identity()
        assert identity["processing"]["graph_revision"] == 1
        assert identity["processing"]["caps_source"] == "negotiated"
        execution = graph.output_session.active_execution_id
        eos_deadline = time.monotonic() + 8.0
        while time.monotonic() < eos_deadline:
            port.dispatch_pending()
            if graph.output_session._dsd_pcm_terminal_execution == execution:
                break
            time.sleep(0.02)
        assert graph.output_session._dsd_pcm_terminal_execution == execution
        evidence = port.query_dsd_pcm_evidence()
        assert evidence["capture"]["byte_count"] > 0
        assert evidence["capture"]["sha256"]
        assert graph.audio_processing.effective_state.value != "effective"
        graph.playback.stop()
        assert graph.output_session.state.value == "idle"
    finally:
        _close(graph)
