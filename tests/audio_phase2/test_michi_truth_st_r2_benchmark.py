"""ST-R2 benchmark must measure canonical frames and synthetic QML separately."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/benchmark_michi_truth_st_r2.py"


def _module():
    spec = importlib.util.spec_from_file_location("st_r2_benchmark", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_stage_sequence_accepts_only_five_to_eight():
    module = _module()
    assert module.canonical_stage_ids(5) == (
        "source",
        "decode",
        "processing",
        "output",
        "device",
    )
    eight = module.canonical_stage_ids(8)
    assert eight == (
        "source",
        "decode",
        "processing",
        "resample",
        "channel-remap",
        "fir",
        "output",
        "device",
    )
    for invalid in (0, 4, 9, 20):
        with pytest.raises(ValueError):
            module.canonical_stage_ids(invalid)


def test_canonical_projection_keeps_eight_valid_stages():
    module = _module()
    frame = module._base()
    frame["stages"] = module._stage_payload(8)
    projected = module.TruthFrame.from_reconciled(frame).to_qml()
    assert [stage["id"] for stage in projected["stages"]] == list(
        module.canonical_stage_ids(8)
    )


def test_twenty_stages_are_synthetic_presentation_only():
    module = _module()
    assert module.CANONICAL_COUNTS == (5, 8)
    assert 20 not in module.CANONICAL_COUNTS
    assert 20 in module.QML_STRESS_COUNTS


def test_destruction_measurement_delivers_deferred_deletes():
    module = _module()
    source = inspect.getsource(module._measure_qml)
    assert "QEvent.Type.DeferredDelete" in source
    assert "sendPostedEvents" in source
    assert "destruction_verified" in source
