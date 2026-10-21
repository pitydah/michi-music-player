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


def test_infinite_generator_is_rejected_without_materializing() -> None:
    import itertools

    class _Asset:
        asset_id = "ir:sha256:" + "c" * 64

    class _Provider:
        def load_float32_mono(self, asset_id: str):
            return itertools.count(1.0)  # open-ended; must hit the tap budget

    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels((_Asset(),), _Provider(), timeout_s=1.0)
    assert info.value.code == "FIR_KERNEL_TOO_LARGE"
    assert time.monotonic() - started < 0.5


def test_slow_iterator_is_released_at_the_deadline() -> None:
    class _Asset:
        asset_id = "ir:sha256:" + "d" * 64

    class _Provider:
        def load_float32_mono(self, asset_id: str):
            def _slow():
                yield 0.5
                time.sleep(1.0)  # iteration blocks AFTER the provider returned
                yield 0.5

            return _slow()

    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels((_Asset(),), _Provider(), timeout_s=0.05)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    assert time.monotonic() - started < 0.5


def test_lying_length_does_not_bypass_the_tap_budget() -> None:
    class _Asset:
        asset_id = "ir:sha256:" + "e" * 64

    class _DeclaredSmall:
        def __len__(self) -> int:
            return 1

        def __iter__(self):
            return iter(range(9000))

    class _Provider:
        def load_float32_mono(self, asset_id: str):
            return _DeclaredSmall()

    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels((_Asset(),), _Provider(), timeout_s=1.0)
    assert info.value.code == "FIR_KERNEL_TOO_LARGE"


def test_invalid_provider_results_are_typed() -> None:
    class _Asset:
        asset_id = "ir:sha256:" + "f" * 64

    class _Provider:
        def __init__(self, value) -> None:
            self.value = value

        def load_float32_mono(self, asset_id: str):
            return self.value

    for value in (None, 42, "kernel", {"a": 1}, object()):
        with pytest.raises(ProcessingCompilationError) as info:
            acquire_kernels((_Asset(),), _Provider(value), timeout_s=1.0)
        assert info.value.code == "DSP_FIR_STORE_INVALID", value


def test_iteration_errors_are_typed() -> None:
    class _Asset:
        asset_id = "ir:sha256:" + "1" * 64

    class _Provider:
        def load_float32_mono(self, asset_id: str):
            def _failing():
                yield 0.5
                raise ValueError("stream corrupted")

            return _failing()

    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels((_Asset(),), _Provider(), timeout_s=1.0)
    assert info.value.code == "DSP_FIR_STORE_INVALID"


def test_in_flight_budget_refuses_when_the_provider_stays_hung(monkeypatch) -> None:
    import threading

    from michi.application import ir_acquisition

    # Previous deadline tests may leave a daemon thread finishing; drain first
    # so this test asserts the cap, not their leftovers.
    for _ in range(200):
        if ir_acquisition.in_flight_calls() == 0:
            break
        time.sleep(0.02)
    monkeypatch.setattr(ir_acquisition, "MAX_IN_FLIGHT", 1)
    release = threading.Event()

    def _hung():
        release.wait(2.0)
        return (0.5,)

    try:
        with pytest.raises(ProcessingCompilationError) as info:
            ir_acquisition.bounded_ir_call(_hung, timeout_s=0.05)
        assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
        assert ir_acquisition.in_flight_calls() == 1

        with pytest.raises(ProcessingCompilationError) as info:
            ir_acquisition.bounded_ir_call(lambda: (0.5,), timeout_s=1.0)
        assert info.value.code == "DSP_FIR_STORE_BUSY"
    finally:
        release.set()

    for _ in range(100):
        if ir_acquisition.in_flight_calls() == 0:
            break
        time.sleep(0.02)
    assert ir_acquisition.in_flight_calls() == 0


def test_total_budget_covers_all_assets() -> None:
    class _Asset:
        def __init__(self, asset_id: str) -> None:
            self.asset_id = asset_id

    class _Provider:
        def load_float32_mono(self, asset_id: str):
            time.sleep(0.1)
            return (0.5,)

    assets = (
        _Asset("ir:sha256:" + "2" * 64),
        _Asset("ir:sha256:" + "3" * 64),
    )
    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_kernels(assets, _Provider(), timeout_s=1.0, total_timeout_s=0.15)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    assert time.monotonic() - started < 0.5


class _Node:
    def __init__(self, asset_id: str) -> None:
        self.asset_id = asset_id


def _valid_metadata(asset_id: str, **overrides):
    sha = asset_id.rsplit(":", 1)[-1]
    data = {"sha256": sha, "rate_hz": 48000, "channels": 1}
    data.update(overrides)
    return data


def test_acquire_ir_assets_returns_metadata_and_kernels() -> None:
    from michi.application.ir_acquisition import acquire_ir_assets

    node = _Node("ir:sha256:" + "a" * 64)

    class _Provider:
        def metadata(self, asset_id: str):
            return _valid_metadata(asset_id)

        def load_float32_mono(self, asset_id: str):
            return (0.5, 0.5)

    assets, kernels = acquire_ir_assets((node,), _Provider(), total_timeout_s=1.0)
    assert len(assets) == 1
    assert assets[0].asset_id == node.asset_id
    assert assets[0].sha256 == "a" * 64
    assert assets[0].rate_hz == 48000
    assert kernels[node.asset_id] == (0.5, 0.5)


def test_malformed_metadata_is_typed() -> None:
    from michi.application.ir_acquisition import acquire_ir_assets

    node = _Node("ir:sha256:" + "b" * 64)

    class _Provider:
        def __init__(self, metadata) -> None:
            self._metadata = metadata

        def metadata(self, asset_id: str):
            return self._metadata

        def load_float32_mono(self, asset_id: str):
            return (0.5,)

    sha = "b" * 64
    cases = [
        (None, "DSP_FIR_STORE_INVALID"),
        ({}, "DSP_FIR_ASSET_HASH_UNAVAILABLE"),
        ({"sha256": "x" * 64}, "DSP_FIR_ASSET_HASH_UNAVAILABLE"),
        ({"sha256": sha}, "DSP_FIR_STORE_INVALID"),
        ({"sha256": sha, "rate_hz": "96000", "channels": 1}, "DSP_FIR_STORE_INVALID"),
        ({"sha256": sha, "rate_hz": 0, "channels": 1}, "DSP_FIR_STORE_INVALID"),
        ({"sha256": sha, "rate_hz": 48000, "channels": True}, "DSP_FIR_STORE_INVALID"),
        ({"sha256": sha, "rate_hz": 48000, "channels": 0}, "DSP_FIR_STORE_INVALID"),
    ]
    for metadata, code in cases:
        with pytest.raises(ProcessingCompilationError) as info:
            acquire_ir_assets((node,), _Provider(metadata), total_timeout_s=1.0)
        assert info.value.code == code, metadata


def test_metadata_and_coefficients_share_the_total_budget() -> None:
    from michi.application.ir_acquisition import acquire_ir_assets

    node = _Node("ir:sha256:" + "c" * 64)

    class _Provider:
        def metadata(self, asset_id: str):
            time.sleep(0.04)
            return _valid_metadata(asset_id)

        def load_float32_mono(self, asset_id: str):
            time.sleep(0.04)
            return (0.5,)

    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_ir_assets((node,), _Provider(), timeout_s=1.0, total_timeout_s=0.06)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    assert time.monotonic() - started < 0.5


def test_metadata_queries_share_the_total_budget_across_nodes() -> None:
    from michi.application.ir_acquisition import acquire_ir_assets

    nodes = (
        _Node("ir:sha256:" + "d" * 64),
        _Node("ir:sha256:" + "e" * 64),
    )

    class _Provider:
        def metadata(self, asset_id: str):
            time.sleep(0.05)
            return _valid_metadata(asset_id)

        def load_float32_mono(self, asset_id: str):
            return (0.5,)

    started = time.monotonic()
    with pytest.raises(ProcessingCompilationError) as info:
        acquire_ir_assets(nodes, _Provider(), timeout_s=1.0, total_timeout_s=0.08)
    assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
    assert time.monotonic() - started < 0.5


def test_real_in_flight_cap_refuses_a_fifth_parallel_acquisition() -> None:
    import threading

    from michi.application import ir_acquisition

    for _ in range(200):
        if ir_acquisition.in_flight_calls() == 0:
            break
        time.sleep(0.02)
    release = threading.Event()

    def _hung():
        release.wait(2.0)
        return (0.5,)

    try:
        for _ in range(ir_acquisition.MAX_IN_FLIGHT):
            with pytest.raises(ProcessingCompilationError) as info:
                ir_acquisition.bounded_ir_call(_hung, timeout_s=0.05)
            assert info.value.code == "DSP_FIR_STORE_TIMEOUT"
        assert ir_acquisition.in_flight_calls() == ir_acquisition.MAX_IN_FLIGHT

        with pytest.raises(ProcessingCompilationError) as info:
            ir_acquisition.bounded_ir_call(lambda: (0.5,), timeout_s=1.0)
        assert info.value.code == "DSP_FIR_STORE_BUSY"
    finally:
        release.set()

    for _ in range(200):
        if ir_acquisition.in_flight_calls() == 0:
            break
        time.sleep(0.02)
    assert ir_acquisition.in_flight_calls() == 0
