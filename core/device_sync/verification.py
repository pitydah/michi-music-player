"""VerificationService — checksum/readback verification after transfer.

Every successful transfer is verified by comparing size + SHA-256 of the
destination against the source (real readback, chunked — no fabricated
success). Devices that support physical readback can extend this via the
adapter, but the checksum path is always real.
"""
from __future__ import annotations

import hashlib
import logging

from core.device_sync.models import VerificationResult

logger = logging.getLogger("michi.device_sync.verification")


def sha256_file(path: str, chunk_size: int = 65536) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class VerificationService:
    def verify(self, source: str, dest: str) -> VerificationResult:
        try:
            import os

            src_size = os.path.getsize(source)
            dst_size = os.path.getsize(dest)
            size_match = src_size == dst_size
            if not size_match:
                return VerificationResult(ok=False, size_match=False)
            src_checksum = sha256_file(source)
            dst_checksum = sha256_file(dest)
            checksum_match = src_checksum == dst_checksum
            return VerificationResult(
                ok=checksum_match,
                size_match=True,
                checksum_match=checksum_match,
                source_checksum=src_checksum,
                dest_checksum=dst_checksum,
            )
        except OSError:
            return VerificationResult(ok=False)
