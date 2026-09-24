"""DAC-V35-070R1 productive graph gates ST70R1-P01..P08."""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.domain.audio_device import BindingKind
from michi.domain.audio_evidence import PcmTuple
from michi.domain.audio_output import AudioOutputSelection
from michi.domain.signal_truth import (
    AlsaRuntimeEvidence,
    DecodedRuntimeEvidence,
    SignalTruthReason,
    SignalTruthVerdict,
)
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


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def _runtime_reader(text: str = _HW_PARAMS):
    return lambda path: "DX5\n" if path.endswith("/id") else text


def _load_and_accept(graph, bindings, path: Path):
    graph.playback.load_and_play(path)
    _accept_current(graph, bindings)
    snapshot = graph.signal_truth.active_snapshot
    assert snapshot is not None
    return snapshot


def _proven_chain():
    """R110R1 §12: the OBSERVED transforming converter with the proven policy."""
    from michi.domain.audio_evidence import RuntimeTransformEvidence

    return RuntimeTransformEvidence(
        converter_present=True,
        converter_transforming=True,
        resampler_present=False,
        resampler_transforming=False,
        remix_transforming=False,
        converter_dithering_disabled=True,
        converter_noise_shaping_disabled=True,
    )


def test_st70r1_p01_real_discovery_registry_and_runtime_observer(tmp_path: Path):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    try:
        device_id = "usb:2622:0105:DX5ABC123"
        binding = graph.audio_device_registry.binding_for(
            device_id, BindingKind.ALSA_PCM
        )
        assert binding is not None
        assert binding.pcm_subdevice == 0
        graph.playback.load_and_play(tmp_path / "direct.flac")
        identity = graph.signal_truth.candidate_snapshot.identity
        event = graph.direct_output_executor._alsa_runtime_observer.observe(
            identity, binding
        )
        assert isinstance(event, AlsaRuntimeEvidence)
        assert event.pcm_subdevice == binding.pcm_subdevice == 0
    finally:
        _close_graph(graph)


def test_st70r1_p02_synthetic_s32_composition_does_not_claim_direct(
    tmp_path: Path,
):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "direct.flac")
        assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
        assert SignalTruthReason.ST_SIGNIFICANT_BITS_UNKNOWN in snapshot.reasons
    finally:
        _close_graph(graph)


def test_st70r1_p03_authorized_route_does_not_require_alsa_container_bits(
    tmp_path: Path,
):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    bindings.direct_snapshot_overrides = {
        "decoded_format": "S24_3LE",
        "decoded_sbits": 24,
        "effective_sbits": 24,
        "graph": ("wavparse", "audioconvert", "capsfilter", "alsasink"),
        "transform_evidence": _proven_chain(),
    }
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "adapted.flac")
        # R110R1 PRESERVATION SEMANTIC UPDATE
        # Old invariant: without ALSA runtime container bits the authorized
        #   route stays UNKNOWN.
        # Why superseded: the ALSA stage negotiates the CARRIER container; the
        #   productive decoded width plus the authorized pair and the declared
        #   policy prove preservation (§17). The protected invariant (no
        #   synthetic evidence ever REPLACES runtime truth) is preserved: the
        #   plan never fabricates the container width.
        # Canonical authority: §297 + §292.
        # New invariant: the productive authorized route converges to
        #   DIRECT_CONTAINER_ADAPTED.
        assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
        assert SignalTruthReason.ST_CONTAINER_ADAPTED in snapshot.reasons
    finally:
        _close_graph(graph)


def test_st70r1_p04_missing_engine_container_bits_do_not_block_authorized_route(
    tmp_path: Path,
):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    bindings.direct_snapshot_overrides = {
        "decoded_format": "S24_3LE",
        "decoded_sbits": 24,
        "effective_sbits": None,
        "graph": ("wavparse", "audioconvert", "capsfilter", "alsasink"),
        "transform_evidence": _proven_chain(),
    }
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "unknown.flac")
        # R110R1 PRESERVATION SEMANTIC UPDATE (same family as p03): the missing
        # engine CONTAINER width does not block the proven authorized route.
        # Canonical authority: §297 + §292.
        assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
        assert SignalTruthReason.ST_CONTAINER_ADAPTED in snapshot.reasons
    finally:
        _close_graph(graph)


def test_st70r1_p05_a_b_c_late_b_evidence_is_ignored(tmp_path: Path):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    try:
        _load_and_accept(graph, bindings, tmp_path / "a.flac")
        graph.playback.load_and_play(tmp_path / "b.flac")
        identity_b = graph.signal_truth.candidate_snapshot.identity
        graph.playback.load_and_play(tmp_path / "c.flac")
        identity_c = graph.signal_truth.candidate_snapshot.identity
        _accept_current(graph, bindings)

        active_before = graph.signal_truth.active_snapshot
        assert active_before is not None and active_before.identity == identity_c
        assert (
            graph.signal_truth.observe(
                DecodedRuntimeEvidence(identity_b, PcmTuple(44_100, "S16_LE", 2, 16))
            )
            is False
        )
        assert graph.signal_truth.active_snapshot is active_before
    finally:
        _close_graph(graph)


def test_st70r1_p06_shared_supersession_preserves_recorder_authority(
    tmp_path: Path,
):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    try:
        _load_and_accept(graph, bindings, tmp_path / "direct.flac")
        recorder = graph.signal_truth
        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.load_and_play(tmp_path / "shared.flac")
        _accept_current(graph, bindings)
        assert graph.signal_truth is recorder
        assert recorder.active_snapshot is None
    finally:
        _close_graph(graph)


def test_st70r1_p07_wrong_alsa_hardware_tuple_is_contradicted(tmp_path: Path):
    wrong_rate = _HW_PARAMS.replace("rate: 96000 (96000/1)", "rate: 48000 (48000/1)")
    graph, bindings = _direct_graph(
        tmp_path, alsa_hw_params_reader=_runtime_reader(wrong_rate)
    )
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "wrong.flac")
        assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
        assert SignalTruthReason.ST_ALSA_NEGOTIATION_CONTRADICTION in snapshot.reasons
    finally:
        _close_graph(graph)


def test_st70r1_p08_direct_fixed_non_unity_can_never_be_direct(tmp_path: Path):
    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    bindings.direct_snapshot_overrides = {"gain": 0.5}
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "attenuated.flac")
        assert snapshot.verdict is SignalTruthVerdict.CONTRADICTED
        assert SignalTruthReason.ST_GAIN_NOT_UNITY in snapshot.reasons
    finally:
        _close_graph(graph)


def test_pev110r1_02_productive_authorized_route_converges(tmp_path: Path):
    """R110R1 §55: the PRODUCTIVE composition reaches an adapted Direct verdict.

    No manual snapshot population: the real graph plans the canonical 24-bit
    carrier, loads, accepts and records the decoded runtime facts, and the
    classifier converges through the productive Signal Truth surface.
    """
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict

    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    bindings.direct_snapshot_overrides = {
        "decoded_format": "S24_3LE",
        "decoded_sbits": 24,
        "effective_sbits": 24,
        "graph": ("wavparse", "audioconvert", "capsfilter", "alsasink"),
        "transform_evidence": _proven_chain(),
    }
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "productive.flac")

        assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED, (
            snapshot.reasons
        )
        assert snapshot.reasons == (SignalTruthReason.ST_CONTAINER_ADAPTED,)
    finally:
        _close_graph(graph)


def test_pev110r1_02_productive_representation_change_without_mechanism_is_not_direct(
    tmp_path: Path,
):
    """§34: through the PRODUCTIVE composition, a representation change with no
    observed mechanism must never become adapted Direct."""
    from michi.domain.audio_evidence import RuntimeTransformEvidence
    from michi.domain.signal_truth import SignalTruthVerdict

    graph, bindings = _direct_graph(tmp_path, alsa_hw_params_reader=_runtime_reader())
    bindings.direct_snapshot_overrides = {
        "decoded_format": "S24_3LE",
        "decoded_sbits": 24,
        "effective_sbits": 24,
        "graph": ("wavparse", "capsfilter", "alsasink"),
        "transform_evidence": RuntimeTransformEvidence(converter_present=False),
    }
    try:
        snapshot = _load_and_accept(graph, bindings, tmp_path / "no-mechanism.flac")

        assert snapshot.verdict is not SignalTruthVerdict.DIRECT
        assert snapshot.verdict is not SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED
        assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    finally:
        _close_graph(graph)
