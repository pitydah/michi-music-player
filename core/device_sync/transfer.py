"""TransferAdapter — controlled copy/transcode execution.

Copies are chunked with cooperative cancellation checks. Transcodes run
EXTERNAL tools (ffmpeg) ONLY through the injected ProcessController —
never ``subprocess`` directly. Partial files are cleaned up on cancel
and on failure.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from core.device_sync.models import (
    SyncErrorCode,
    SyncPlanItem,
    TransferOutcome,
    TransferStatus,
)
from core.device_sync.transcode_planning import build_ffmpeg_command

logger = logging.getLogger("michi.device_sync.transfer")

TRANSFER_CHUNK_SIZE = 65536


class TransferAdapter:
    def __init__(self, process_controller=None, chunk_size: int = TRANSFER_CHUNK_SIZE):
        self._pc = process_controller
        self._chunk_size = chunk_size

    def transfer(
        self,
        item: SyncPlanItem,
        ctx=None,
        progress_cb=None,
        device_mount: str = "",
    ) -> TransferOutcome:
        if device_mount and not Path(device_mount).is_dir():
            return TransferOutcome(
                ok=False, status=TransferStatus.FAILED.value,
                error_code=SyncErrorCode.DEVICE_DISCONNECTED.value,
                error="Device mount disappeared before transfer",
            )

        if item.action == "transcode":
            return self._transcode(item, ctx, progress_cb)
        return self._copy(item, ctx, progress_cb)

    # ── Copy ──

    def _copy(self, item: SyncPlanItem, ctx, progress_cb) -> TransferOutcome:
        src = Path(item.source)
        dst = Path(item.dest)
        total = item.size_bytes or (src.stat().st_size if src.exists() else 0)
        done = 0
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(src, "rb") as fin, open(dst, "wb") as fout:
                while True:
                    if ctx is not None:
                        ctx.token.raise_if_cancelled()
                    chunk = fin.read(self._chunk_size)
                    if not chunk:
                        break
                    fout.write(chunk)
                    done += len(chunk)
                    if progress_cb:
                        progress_cb(done, total)
            return TransferOutcome(
                ok=True, status=TransferStatus.COMPLETED.value,
                bytes_transferred=done,
            )
        except Exception as exc:  # noqa: BLE001
            dst.unlink(missing_ok=True)
            if _is_cancelled(ctx):
                return TransferOutcome(
                    ok=False, status=TransferStatus.CANCELLED.value,
                    error_code=SyncErrorCode.CANCELLED.value,
                    error="Transfer cancelled",
                )
            return TransferOutcome(
                ok=False, status=TransferStatus.FAILED.value,
                error_code=SyncErrorCode.TRANSFER_FAILED.value,
                error=str(exc),
            )

    # ── Transcode (controlled subprocess) ──

    def _transcode(self, item: SyncPlanItem, ctx, progress_cb) -> TransferOutcome:
        if self._pc is None:
            return TransferOutcome(
                ok=False, status=TransferStatus.FAILED.value,
                error_code=SyncErrorCode.TRANSFER_FAILED.value,
                error="ProcessController unavailable for transcode",
            )
        cmd = build_ffmpeg_command(item.source, item.transcode_profile, "")
        if not cmd:
            return TransferOutcome(
                ok=False, status=TransferStatus.FAILED.value,
                error_code=SyncErrorCode.FORMAT_UNSUPPORTED.value,
                error=f"No transcode command for {item.transcode_profile}",
            )
        dst = Path(item.dest)
        tmp = str(dst) + ".part"
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = self._pc.spawn_sync("ffmpeg", cmd + [tmp],
                                       stdout=os.devnull, stderr=os.devnull)
            if proc is None:
                return TransferOutcome(
                    ok=False, status=TransferStatus.FAILED.value,
                    error_code=SyncErrorCode.TRANSFER_FAILED.value,
                    error="ffmpeg spawn failed",
                )
            while proc.poll() is None:
                if ctx is not None:
                    ctx.token.raise_if_cancelled()
                time.sleep(0.05)
            if proc.poll() != 0:
                self._pc.cleanup_sync(proc.pid)
                _cleanup(tmp)
                return TransferOutcome(
                    ok=False, status=TransferStatus.FAILED.value,
                    error_code=SyncErrorCode.TRANSFER_FAILED.value,
                    error=f"ffmpeg exit {proc.poll()}",
                )
            self._pc.cleanup_sync(proc.pid)
            if not Path(tmp).exists():
                _cleanup(tmp)
                return TransferOutcome(
                    ok=False, status=TransferStatus.FAILED.value,
                    error_code=SyncErrorCode.TRANSFER_FAILED.value,
                    error="Transcode produced no output",
                )
            os.replace(tmp, str(dst))
            size = dst.stat().st_size if dst.exists() else 0
            if progress_cb:
                progress_cb(size, size)
            return TransferOutcome(
                ok=True, status=TransferStatus.COMPLETED.value,
                bytes_transferred=size,
            )
        except Exception as exc:  # noqa: BLE001
            _cleanup(tmp)
            if _is_cancelled(ctx):
                return TransferOutcome(
                    ok=False, status=TransferStatus.CANCELLED.value,
                    error_code=SyncErrorCode.CANCELLED.value,
                    error="Transcode cancelled",
                )
            return TransferOutcome(
                ok=False, status=TransferStatus.FAILED.value,
                error_code=SyncErrorCode.TRANSFER_FAILED.value,
                error=str(exc),
            )


def _is_cancelled(ctx) -> bool:
    if ctx is None or not hasattr(ctx, "token"):
        return False
    try:
        return bool(ctx.token.is_cancelled())
    except Exception:  # noqa: BLE001
        return False


def _cleanup(path: str):
    import contextlib

    with contextlib.suppress(OSError):
        os.unlink(path)
