"""DAC-V35-070R2.1 typed transform and pass-through semantics gates."""

from __future__ import annotations

from dataclasses import replace

import pytest

from michi.domain.audio_evidence import (
    RuntimeTransformEvidence,
    intrinsic_pcm_significant_bits,
)
from michi.infrastructure.audio_output.runtime_inspector import (
    DIRECT_CONVERTER_ACTIVE,
    DIRECT_CONVERTER_STATE_UNKNOWN,
    DIRECT_REMIX_ACTIVE,
    DIRECT_RESAMPLER_ACTIVE,
    DIRECT_RESAMPLER_STATE_UNKNOWN,
    DirectRuntimeValidationError,
    validate_runtime,
)
from tests.dac.test_v35_runtime_inspector import _recipe, _snapshot

_QT_APP = None


@pytest.fixture(autouse=True)
def _qt_runtime():
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    _QT_APP = QApplication.instance() or QApplication([])
    yield _QT_APP


def test_r21_01_intrinsic_r2_semantics_remain_frozen() -> None:
    assert intrinsic_pcm_significant_bits("S16LE") == 16
    assert intrinsic_pcm_significant_bits("S24LE") == 24
    assert intrinsic_pcm_significant_bits("S24_32LE") is None
    assert intrinsic_pcm_significant_bits("S32LE") is None
    assert intrinsic_pcm_significant_bits("F32LE") is None


def test_r21_02_converter_presence_is_not_transformation() -> None:
    snapshot = _snapshot(
        graph_factories=("audioconvert", "capsfilter", "alsasink"),
        transform_evidence=RuntimeTransformEvidence(
            converter_present=True,
            converter_transforming=False,
            remix_transforming=False,
        ),
    )

    validate_runtime(_recipe(), snapshot)


def test_r21_03_resampler_presence_is_not_transformation() -> None:
    snapshot = _snapshot(
        graph_factories=("audioresample", "capsfilter", "alsasink"),
        transform_evidence=RuntimeTransformEvidence(
            resampler_present=True,
            resampler_transforming=False,
        ),
    )

    validate_runtime(_recipe(), snapshot)


@pytest.mark.parametrize(
    ("evidence", "expected_code"),
    [
        (
            RuntimeTransformEvidence(
                converter_present=True,
                converter_transforming=None,
            ),
            DIRECT_CONVERTER_STATE_UNKNOWN,
        ),
        (
            RuntimeTransformEvidence(
                resampler_present=True,
                resampler_transforming=None,
            ),
            DIRECT_RESAMPLER_STATE_UNKNOWN,
        ),
    ],
)
def test_r21_08_09_unknown_transform_state_fails_closed(
    evidence: RuntimeTransformEvidence,
    expected_code: str,
) -> None:
    # The recipe declares the container preservation policy for the canonical
    # 24-bit -> S32 carrier target (§1822 step 6 / §292). An active transform is
    # refused when that policy is NOT declared, which is the invariant here.
    undeclared = replace(_recipe(), container_conversion=False)
    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(undeclared, _snapshot(transform_evidence=evidence))

    assert exc_info.value.code == expected_code


@pytest.mark.parametrize(
    ("evidence", "expected_code"),
    [
        (
            RuntimeTransformEvidence(
                converter_present=True,
                converter_transforming=True,
            ),
            DIRECT_CONVERTER_ACTIVE,
        ),
        (
            RuntimeTransformEvidence(
                resampler_present=True,
                resampler_transforming=True,
            ),
            DIRECT_RESAMPLER_ACTIVE,
        ),
    ],
)
def test_r21_active_transform_fails_direct_validation(
    evidence: RuntimeTransformEvidence,
    expected_code: str,
) -> None:
    # An UNDECLARED active transform is refused. The recipe declares the
    # container preservation policy for the canonical 24-bit -> S32 carrier
    # target (§1822 step 6 / §292), so the invariant is exercised without it.
    undeclared = replace(_recipe(), container_conversion=False)
    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(undeclared, _snapshot(transform_evidence=evidence))

    assert exc_info.value.code == expected_code


def test_r21_independent_active_remix_fails_direct_validation() -> None:
    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(
            _recipe(),
            _snapshot(
                transform_evidence=RuntimeTransformEvidence(
                    remix_transforming=True,
                )
            ),
        )

    assert exc_info.value.code == DIRECT_REMIX_ACTIVE


def test_r21_incomplete_graph_flag_fails_direct_validation() -> None:
    with pytest.raises(DirectRuntimeValidationError) as exc_info:
        validate_runtime(_recipe(), _snapshot(graph_inspection_complete=False))

    assert exc_info.value.code == "DIRECT_GRAPH_INSPECTION_FAILED"


def _signal_truth_with_transforms(
    evidence: RuntimeTransformEvidence,
    *,
    decoded=None,
    engine_pcm=None,
    alsa_pcm=None,
):
    from tests.dac.test_v35_070_signal_truth import (
        _alsa,
        _complete,
        _engine,
        _identity,
    )

    identity = _identity()
    engine = replace(
        _engine(identity, pcm=engine_pcm),
        transform_evidence=evidence,
    )
    return _complete(
        decoded=decoded,
        engine=engine,
        alsa=_alsa(identity, pcm=alsa_pcm),
    ).candidate_snapshot


def test_r21_21_passthrough_converter_does_not_become_dsp() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, False, False, None, False)
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT


def test_r21_22_passthrough_resampler_does_not_become_resampled() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(False, None, True, False, None)
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT


def test_r21_23_active_rate_change_becomes_resampled() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _pcm

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(False, None, True, True, None),
        decoded=_pcm(rate=96_000),
        engine_pcm=_pcm(rate=48_000),
        alsa_pcm=_pcm(rate=48_000),
    )

    assert snapshot.verdict is SignalTruthVerdict.RESAMPLED
    assert SignalTruthReason.ST_RATE_MISMATCH in snapshot.reasons


def test_r21_24_active_channel_change_becomes_remixed() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _pcm

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, True, False, None, True),
        decoded=_pcm(channels=2),
        engine_pcm=_pcm(channels=1),
        alsa_pcm=_pcm(channels=1),
    )

    assert snapshot.verdict is SignalTruthVerdict.REMIXED
    assert SignalTruthReason.ST_CHANNEL_MISMATCH in snapshot.reasons


@pytest.mark.parametrize(
    ("evidence", "expected_reason"),
    [
        (
            RuntimeTransformEvidence(True, None, False, None, None),
            "ST_CONVERTER_STATE_UNKNOWN",
        ),
        (
            RuntimeTransformEvidence(False, None, True, None, None),
            "ST_RESAMPLER_STATE_UNKNOWN",
        ),
    ],
)
def test_r21_25_26_unknown_transform_state_makes_signal_truth_unknown(
    evidence: RuntimeTransformEvidence,
    expected_reason: str,
) -> None:
    from michi.domain.signal_truth import SignalTruthVerdict

    snapshot = _signal_truth_with_transforms(evidence)

    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert expected_reason in {reason.value for reason in snapshot.reasons}


def test_r21_positive_resample_precedes_unrelated_unknown_converter() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _pcm

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, None, True, True, None),
        decoded=_pcm(rate=96_000),
        engine_pcm=_pcm(rate=48_000),
        alsa_pcm=_pcm(rate=48_000),
    )

    assert snapshot.verdict is SignalTruthVerdict.RESAMPLED


def test_r21_active_format_conversion_with_unknown_sbits_stays_unknown() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _pcm

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, True, False, None, False),
        decoded=_pcm(fmt="S24_3LE", significant_bits=24),
        engine_pcm=_pcm(fmt="S32_LE", significant_bits=None),
        alsa_pcm=_pcm(fmt="S32_LE", significant_bits=None),
    )

    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: a transforming converter with unknown sbits stays UNKNOWN
    #   because the container width is unknown.
    # Why superseded: the verdict is still UNKNOWN, but the blocking fact is now
    #   the UNPROVEN preservation policy of the active converter (§44), not the
    #   container width. The protected invariant (never Direct) is preserved.
    # Canonical authority: §292 (explicit preservation policy) + §297.
    # New invariant: UNKNOWN, blocked by the unproven converter policy.
    assert snapshot.verdict is SignalTruthVerdict.UNKNOWN
    assert SignalTruthReason.ST_CONVERTER_STATE_UNKNOWN in snapshot.reasons


def test_r21_proven_container_adaptation_remains_bounded() -> None:
    from michi.domain.signal_truth import SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _pcm

    # R110R1 PRESERVATION SEMANTIC UPDATE
    # Old invariant: a transforming converter alone certifies an adapted Direct
    #   route.
    # Why superseded: §44 requires the OBSERVED converter to PROVE its
    #   preservation policy (dithering and noise shaping disabled).
    # Canonical authority: §292 (explicit preservation policy) + §297.
    # New invariant: the proven authorized adaptation stays
    #   DIRECT_CONTAINER_ADAPTED, now with the policy proven.
    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(
            True,
            True,
            False,
            None,
            False,
            converter_dithering_disabled=True,
            converter_noise_shaping_disabled=True,
        ),
        decoded=_pcm(fmt="S24_3LE", significant_bits=24),
        engine_pcm=_pcm(fmt="S32_LE", significant_bits=24),
        alsa_pcm=_pcm(fmt="S32_LE", significant_bits=24),
    )

    assert snapshot.verdict is SignalTruthVerdict.DIRECT_CONTAINER_ADAPTED


def test_r21_15_multiple_converter_states_aggregate_fail_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        _aggregate_transform_states,
    )

    assert _aggregate_transform_states([False, False]) is False
    assert _aggregate_transform_states([False, True]) is True
    assert _aggregate_transform_states([False, None]) is None


def test_r21_16_multiple_resampler_states_aggregate_fail_closed() -> None:
    from michi.infrastructure.audio_engines.gstreamer import (
        _aggregate_transform_states,
    )

    assert _aggregate_transform_states([False, False, False]) is False
    assert _aggregate_transform_states([None, True, False]) is True
    assert _aggregate_transform_states([None, False, False]) is None


def test_r21_19_s32_still_has_unknown_significant_bits() -> None:
    assert intrinsic_pcm_significant_bits("S32_LE") is None


def test_r21_20_twenty_four_in_thirty_two_still_requires_proof() -> None:
    assert intrinsic_pcm_significant_bits("S24_32LE") is None


def test_r21_27_non_unity_gain_still_cannot_be_direct() -> None:
    from michi.domain.signal_truth import SignalTruthReason, SignalTruthVerdict
    from tests.dac.test_v35_070_signal_truth import _engine

    snapshot = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, False, True, False, False)
    )
    assert snapshot.verdict is SignalTruthVerdict.DIRECT

    non_unity = _signal_truth_with_transforms(
        RuntimeTransformEvidence(True, False, True, False, False)
    )
    identity = non_unity.identity
    from tests.dac.test_v35_070_signal_truth import _alsa, _complete

    contradicted = _complete(
        engine=replace(
            _engine(identity, gain=0.5),
            transform_evidence=RuntimeTransformEvidence(
                True, False, True, False, False
            ),
        ),
        alsa=_alsa(identity),
    ).candidate_snapshot
    assert contradicted.verdict is SignalTruthVerdict.CONTRADICTED
    assert SignalTruthReason.ST_GAIN_NOT_UNITY in contradicted.reasons


def test_r21_28_stale_transform_evidence_cannot_mutate_new_candidate() -> None:
    from michi.domain.signal_truth import (
        EngineRuntimeEvidence,
        SignalTruthRecorder,
    )
    from tests.dac.test_v35_070_signal_truth import _engine, _identity, _plan

    recorder = SignalTruthRecorder()
    identity_b = _identity(execution=2, port=8)
    identity_c = _identity(execution=3, port=9)
    recorder.begin_candidate(_plan(identity_b))
    recorder.begin_candidate(_plan(identity_c))
    before = recorder.candidate_snapshot
    stale: EngineRuntimeEvidence = replace(
        _engine(identity_b),
        transform_evidence=RuntimeTransformEvidence(False, None, True, True, None),
    )

    assert recorder.observe(stale) is False
    assert recorder.candidate_snapshot is before


def test_r21_29_direct_to_shared_clears_active_transform_truth(tmp_path) -> None:
    from michi.domain.audio_output import AudioOutputSelection
    from tests.dac.test_v35_productive_direct_composition import (
        _accept_current,
        _close_graph,
        _direct_graph,
    )

    graph, bindings = _direct_graph(tmp_path)
    bindings.direct_snapshot_overrides = {
        "graph": ("audioconvert", "audioresample", "capsfilter", "alsasink"),
        "transform_evidence": RuntimeTransformEvidence(True, False, True, False, False),
    }
    try:
        graph.playback.load_and_play(tmp_path / "direct.flac")
        _accept_current(graph, bindings)
        assert graph.signal_truth.active_snapshot is not None
        assert (
            graph.signal_truth.active_snapshot.engine_effective.transform_evidence
            == bindings.direct_snapshot_overrides["transform_evidence"]
        )

        graph.audio_output_profiles.save_selection(AudioOutputSelection(None, None, 2))
        graph.playback.load_and_play(tmp_path / "shared.flac")
        _accept_current(graph, bindings)

        assert graph.signal_truth.active_snapshot is None
    finally:
        _close_graph(graph)
