"""AP2-F06 — bounded IR acquisition outside the pure compiler.

A slow or hung injected provider must fail typed at the deadline and must not
block the preparation worker or supersession/cancellation.
"""

from __future__ import annotations

import time

import pytest

from michi.application.ir_acquisition import (
    acquire_kernels,
    bounded_ir_call,
)
from michi.application.processing_graph_compiler import ProcessingCompilationError


def test_bounded_call_returns_a_fast_result() -> None:
    assert bounded_ir_call(lambda: (0.5, 0.5), timeout_s=1.0) == (0.5, 0.5)


def test_slow_provider_fails_typed_within_the_deadline() -> None:
    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        bounded_ir_call(lambda: time.sleep(1.0), timeout_s=0.05)
    elapsed = time.monotonic() - started
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    # The caller is released at the deadline, NOT when the provider returns.
    assert elapsed < 0.5, elapsed


def test_provider_errors_are_relayed_typed() -> None:
    class _StoreError(RuntimeError):
        code = "IR_STORE_IO"

    def _fail() -> None:
        raise _StoreError("disk failed")

    with pytest.raises(ProcessingCompilationError) as info:
        bounded_ir_call(_fail, timeout_s=1.0)
    assert info.value.code == "IR_STORE_IO"

    def _invalid() -> None:
        raise ValueError("bad")

    with pytest.raises(ProcessingCompilationError) as info:
        bounded_ir_call(_invalid, timeout_s=1.0)
    assert info.value.code == "DSP_FIR_STORE_FAILED"


def test_acquire_kernels_bounds_every_asset() -> None:
    class _Asset:
        def __init__(self, asset_id: str, coefficients):
            self.asset_id = asset_id
            self.coefficients = coefficients
            self.delay = 0.0

    class _Provider:
        def __init__(self, assets) -> None:
            self.assets = {asset.asset_id: asset for asset in assets}

        def load_float32_mono(self, asset_id: str):
            asset = self.assets[asset_id]
            if asset.delay:
                time.sleep(asset.delay)
            return asset.coefficients

    first = _Asset("ir:sha256:" + "a" * 64, (0.5, 0.5))
    second = _Asset("ir:sha256:" + "b" * 64, (1.0,))
    provider = _Provider((first, second))
    assert acquire_kernels((first, second), provider) == {
        first.asset_id: (0.5, 0.5),
        second.asset_id: (1.0,),
    }

    second.delay = 1.0
    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels((first, second), provider, timeout_s=0.05)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    assert time.monotonic() - started < 0.5


def test_non_positive_timeout_is_a_typed_refusal() -> None:
    with pytest.raises(ProcessingCompilationError) as info:
        bounded_ir_call(lambda: 1, timeout_s=0)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
