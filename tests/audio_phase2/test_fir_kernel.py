"""AP2-F06 — stateless FIR kernel verification (hash, bounds, finiteness).

The durable IR store is F13; this module verifies bytes only.
"""

from __future__ import annotations

import hashlib
import math
import struct

import pytest

from michi.domain.fir_kernel import (
    FirKernelError,
    fir_kernel_fingerprint,
    verify_fir_kernel,
)


def _raw(coefficients) -> bytes:
    return struct.pack(f"<{len(coefficients)}f", *coefficients)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def test_identity_gain_and_lowpass_kernels_are_accepted() -> None:
    identity_raw = _raw((1.0,))
    identity = verify_fir_kernel(
        identity_raw, expected_sha256=_sha(identity_raw), rate_hz=48000, channels=1
    )
    assert identity.coefficients == (1.0,)
    assert identity.taps == 1
    assert identity.fingerprint == _sha(identity_raw)

    gain_raw = _raw((0.5, 0.5))
    gain = verify_fir_kernel(
        gain_raw, expected_sha256=_sha(gain_raw), rate_hz=44100, channels=1
    )
    assert gain.coefficients == (0.5, 0.5)

    lowpass = (0.25, 0.5, 0.25)
    lp_raw = _raw(lowpass)
    kernel = verify_fir_kernel(
        lp_raw, expected_sha256=_sha(lp_raw), rate_hz=96000, channels=1
    )
    assert kernel.coefficients == lowpass
    assert kernel.rate_hz == 96000


def test_hash_mismatch_rejects_before_any_execution() -> None:
    raw = _raw((0.5, 0.5))
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(
            raw, expected_sha256=_sha(_raw((1.0, 0.0))), rate_hz=44100, channels=1
        )
    assert info.value.code == "FIR_KERNEL_HASH_MISMATCH"


@pytest.mark.parametrize(
    ("raw", "code", "kwargs"),
    [
        (b"", "FIR_KERNEL_EMPTY", {}),
        (b"abc", "FIR_KERNEL_MALFORMED", {}),
        (_raw((1.0,)) + b"\x00", "FIR_KERNEL_MALFORMED", {}),
        (_raw((math.nan,)), "FIR_KERNEL_NON_FINITE", {}),
        (_raw((math.inf,)), "FIR_KERNEL_NON_FINITE", {}),
    ],
)
def test_malformed_kernels_fail_closed(raw, code, kwargs) -> None:
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(
            raw, expected_sha256=_sha(raw), rate_hz=44100, channels=1, **kwargs
        )
    assert info.value.code == code


def test_bounds_rate_and_channels_are_enforced() -> None:
    raw = _raw((1.0, 0.0))
    sha = _sha(raw)
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(raw, expected_sha256=sha, rate_hz=0, channels=1)
    assert info.value.code == "FIR_KERNEL_RATE_INVALID"
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(raw, expected_sha256=sha, rate_hz=44100, channels=0)
    assert info.value.code == "FIR_KERNEL_CHANNELS_INVALID"
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(raw, expected_sha256=sha, rate_hz=44100, channels=2)
    assert info.value.code == "FIR_KERNEL_CHANNELS_UNSUPPORTED"
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(
            _raw((1.0, 2.0, 3.0)),
            expected_sha256=_sha(_raw((1.0, 2.0, 3.0))),
            rate_hz=44100,
            channels=1,
            max_taps=2,
        )
    assert info.value.code == "FIR_KERNEL_TOO_LARGE"
    with pytest.raises(FirKernelError) as info:
        verify_fir_kernel(raw, expected_sha256="not-a-sha", rate_hz=44100, channels=1)
    assert info.value.code == "FIR_KERNEL_HASH_INVALID"


def test_fingerprint_is_deterministic_and_value_sensitive() -> None:
    first = fir_kernel_fingerprint((0.1, 0.2, 0.3))
    second = fir_kernel_fingerprint((0.1, 0.2, 0.3))
    other = fir_kernel_fingerprint((0.1, 0.2, 0.3000001))
    assert first == second
    assert first != other
    assert len(first) == 64
