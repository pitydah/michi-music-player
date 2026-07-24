from __future__ import annotations

import pytest

from core.audio_lab.audio_lab_contracts import (
    AudioLabCapability,
    AudioLabCapabilityStatus,
    AudioLabErrorCode,
    AudioLabJobSnapshot,
    AudioLabJobStatus,
    AudioLabOperation,
    AudioLabOperationResult,
    ConversionProfile,
)
from core.audio_lab.audio_conversion_service import ConversionProfile as ServiceProfile
from tests.fixtures.audio_lab_factory import AudioFixtureFactory


def test_operation_result_envelopes_are_qml_serializable() -> None:
    assert AudioLabOperationResult.immediate({"format": "FLAC"}).to_qml() == {
        "ok": True,
        "result": {"format": "FLAC"},
        "job_id": "",
        "status": "",
        "error_code": "",
        "message": "",
        "detail": "",
        "recoverable": False,
        "requires_confirmation": False,
        "confirmation_token": "",
        "warning": "",
        "operation": "",
    }
    queued = AudioLabOperationResult.queued("alab_analysis_1").to_qml()
    assert queued["ok"] is True
    assert queued["status"] == "queued"
    failed = AudioLabOperationResult.failure(
        AudioLabErrorCode.INVALID_PROFILE, "Perfil inválido", recoverable=True
    ).to_qml()
    assert failed["ok"] is False
    assert failed["error_code"] == "INVALID_PROFILE"


def test_job_progress_is_monotonic_and_bounded() -> None:
    job = AudioLabJobSnapshot("job-1", AudioLabOperation.ANALYSIS)
    job.set_progress(0.25, "Probe")
    job.set_progress(1.0, "Done")
    assert job.to_qml()["status"] == AudioLabJobStatus.QUEUED.value
    with pytest.raises(ValueError):
        job.set_progress(0.5)
    with pytest.raises(ValueError):
        job.set_progress(1.1)


def test_conversion_profile_is_shared_and_accepts_qml_legacy_keys() -> None:
    assert ServiceProfile is ConversionProfile
    profile = ConversionProfile.from_mapping(
        {
            "format": "OPUS",
            "vbr_quality": 5.0,
            "preserve_metadata": False,
            "preserve_artwork": False,
            "collision_policy": "skip",
        }
    )
    assert profile.format == "OPUS"
    assert profile.vbr_quality == 5.0
    assert profile.copy_metadata is False
    assert profile.copy_artwork is False
    assert profile.collision_policy == "skip"


def test_capability_contract_is_structured() -> None:
    capability = AudioLabCapability(
        id="conversion",
        available=False,
        status=AudioLabCapabilityStatus.DEPENDENCY_MISSING,
        reason="FFmpeg no disponible",
        dependencies=("ffmpeg",),
        platform="linux",
    ).to_qml()
    assert capability["status"] == "dependency_missing"
    assert capability["dependencies"] == ["ffmpeg"]


def test_synthetic_audio_corpus_is_reproducible(tmp_path) -> None:
    corpus = AudioFixtureFactory(tmp_path).corpus()
    required = {"wav", "silence", "clipping", "multichannel", "hires", "empty", "truncated"}
    assert required <= corpus.keys()
    assert corpus["wav"].read_bytes().startswith(b"RIFF")
    assert corpus["empty"].stat().st_size == 0
    assert corpus["truncated"].stat().st_size < corpus["wav"].stat().st_size
