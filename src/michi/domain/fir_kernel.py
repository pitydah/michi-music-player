"""AP2-F06 — stateless, hash-verified FIR kernel authority.

This module is NOT the durable IR store (R11-F13 owns that). F06 consumes an
injected ``ImpulseResponseStorePort`` and verifies the complete bytes here
before any native installation:

* complete SHA-256 over the float32-LE mono IR bytes,
* bounded taps, finite coefficients, non-empty kernel,
* mono IR contract (per-channel mapping is a later, explicit slice),
* deterministic fingerprint for the native readback.

Failing closed is mandatory: no FIR may reach GStreamer without this proof.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass

MAX_FIR_TAPS = 65536
_IR_HASH_LEN = 64


class FirKernelError(ValueError):
    """Typed FIR kernel rejection (never a silent fallback)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FirKernel:
    coefficients: tuple[float, ...]
    sha256: str
    rate_hz: int
    channels: int

    @property
    def taps(self) -> int:
        return len(self.coefficients)

    @property
    def fingerprint(self) -> str:
        """Canonical hash of the exact float32-LE coefficients."""
        return fir_kernel_fingerprint(self.coefficients)


def fir_kernel_fingerprint(coefficients: tuple[float, ...]) -> str:
    payload = struct.pack(f"<{len(coefficients)}f", *coefficients)
    return hashlib.sha256(payload).hexdigest()


def verify_fir_kernel(
    raw: bytes,
    *,
    expected_sha256: str,
    rate_hz: int,
    channels: int,
    max_taps: int = MAX_FIR_TAPS,
) -> FirKernel:
    """Verify IR bytes and return the immutable kernel or raise typedly."""
    sha = str(expected_sha256 or "").strip().lower()
    if len(sha) != _IR_HASH_LEN or any(ch not in "0123456789abcdef" for ch in sha):
        raise FirKernelError(
            "FIR_KERNEL_HASH_INVALID", "expected_sha256 must be 64 hex chars"
        )
    if not isinstance(raw, (bytes, bytearray, memoryview)) or not raw:
        raise FirKernelError("FIR_KERNEL_EMPTY", "IR bytes are empty")
    payload = bytes(raw)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != sha:
        raise FirKernelError(
            "FIR_KERNEL_HASH_MISMATCH",
            f"IR bytes hash {actual} != expected {sha}",
        )
    if len(payload) % 4 != 0:
        raise FirKernelError(
            "FIR_KERNEL_MALFORMED", "float32 IR length is not sample-aligned"
        )
    taps = len(payload) // 4
    if taps <= 0:
        raise FirKernelError("FIR_KERNEL_EMPTY", "IR has no taps")
    if taps > int(max_taps):
        raise FirKernelError("FIR_KERNEL_TOO_LARGE", f"{taps} taps exceeds {max_taps}")
    if not isinstance(rate_hz, int) or isinstance(rate_hz, bool) or rate_hz <= 0:
        raise FirKernelError("FIR_KERNEL_RATE_INVALID", "IR rate must be > 0")
    if not isinstance(channels, int) or isinstance(channels, bool) or channels <= 0:
        raise FirKernelError("FIR_KERNEL_CHANNELS_INVALID", "IR channels must be > 0")
    if channels != 1:
        raise FirKernelError(
            "FIR_KERNEL_CHANNELS_UNSUPPORTED",
            "only a mono IR is authorized in this slice",
        )
    coefficients = struct.unpack(f"<{taps}f", payload)
    for index, value in enumerate(coefficients):
        if not math.isfinite(value):
            raise FirKernelError(
                "FIR_KERNEL_NON_FINITE", f"coefficient {index} is not finite"
            )
    return FirKernel(
        coefficients=tuple(float(value) for value in coefficients),
        sha256=sha,
        rate_hz=int(rate_hz),
        channels=int(channels),
    )
