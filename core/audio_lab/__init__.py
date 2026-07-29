"""Audio Lab — consolidated audio analysis, conversion, normalization tools."""
from __future__ import annotations

import importlib

_LAZY_MODULES: set[str] = {
    "adc_recorder_service",
    "audio_analysis_service",
    "audio_batch_service",
    "audio_comparison_service",
    "audio_conversion_service",
    "audio_integrity_service",
    "audio_lab_contracts",
    "audio_lab_job_adapter",
    "audio_lab_profile_service",
    "audio_lab_service",
    "audio_lab_state",
    "audio_lab_sync",
    "audio_normalization_service",
    "audio_probe_service",
    "backup_manifest",
    "cd_ripper_service",
    "dependencies",
    "diagnostics_helpers",
    "diagnostics_service",
    "job_controller",
    "library_health",
    "metadata_doctor",
    "periodic_analyzer",
    "replaygain_service",
    "reporting",
}


def __getattr__(name: str):
    if name in _LAZY_MODULES:
        return importlib.import_module(f"core.audio_lab.{name}")
    raise AttributeError(f"module 'core.audio_lab' has no attribute '{name}'")
