"""FIFO manager for Snapcast audio distribution.

Manages the lifecycle of the named pipe (FIFO) that connects
the GStreamer playback pipeline to Snapserver.

Architecture:
    GStreamer tee → queue → audioconvert → audioresample →
    capsfilter(44100:16:2) → fdsink → FIFO → Snapserver → Snapclients

The FIFO is created once at app startup and reused across tracks.
A single file descriptor is shared by all GStreamer pipelines
(only one plays at a time).
"""
from __future__ import annotations

import contextlib
import logging
import os
import stat
import threading
import time

logger = logging.getLogger("michi.snapfifo")

_FIFO_PATH = "/tmp/michi-snapfifo"
_fifo_fd: int | None = None
_metrics_lock = threading.Lock()
_bytes_written = 0
_last_write_time = 0.0
_measurement_started_at = 0.0


def ensure_fifo(path: str = _FIFO_PATH) -> bool:
    """Create the FIFO if it doesn't exist. Returns True if ready."""
    if os.path.exists(path):
        if stat.S_ISFIFO(os.stat(path).st_mode):
            return True
        logger.warning("Removing non-FIFO file at %s", path)
        os.unlink(path)
    try:
        os.mkfifo(path, 0o644)
        logger.info("Created FIFO at %s", path)
        return True
    except OSError as exc:
        logger.error("Failed to create FIFO %s: %s", path, exc)
        return False


def open_fifo(path: str = _FIFO_PATH) -> int | None:
    """Open the FIFO for writing (non-blocking). Returns fd or None."""
    global _fifo_fd
    try:
        fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        _fifo_fd = fd
        logger.info("Opened snapfifo (fd=%d)", fd)
        return fd
    except OSError as exc:
        logger.warning("Failed to open snapfifo: %s", exc)
        return None


def get_snapfifo_fd() -> int | None:
    """Get the current FIFO file descriptor, opening if needed."""
    global _fifo_fd
    if _fifo_fd is not None:
        return _fifo_fd
    if ensure_fifo():
        return open_fifo()
    return None


def write_fifo(data: bytes) -> int:
    """Write as much audio data as possible and update FIFO metrics."""
    global _bytes_written, _last_write_time, _measurement_started_at
    fd = get_snapfifo_fd()
    if fd is None or not data:
        return 0
    try:
        written = os.write(fd, data)
    except (BlockingIOError, BrokenPipeError, OSError):
        logger.debug("Snapfifo write unavailable", exc_info=True)
        return 0
    if written <= 0:
        return 0
    now_monotonic = time.monotonic()
    with _metrics_lock:
        if _measurement_started_at == 0.0:
            _measurement_started_at = now_monotonic
        _bytes_written += written
        _last_write_time = time.time()
    return written


def fifo_metrics() -> dict[str, int | float]:
    """Return cumulative bytes, last write time, and average throughput."""
    now = time.monotonic()
    with _metrics_lock:
        elapsed = now - _measurement_started_at if _measurement_started_at else 0.0
        throughput = _bytes_written / elapsed if elapsed > 0 else 0.0
        return {
            "bytes_written": _bytes_written,
            "last_write_time": _last_write_time,
            "throughput_bytes_per_second": throughput,
        }


def _reset_metrics() -> None:
    """Reset process-local FIFO counters for isolated tests."""
    global _bytes_written, _last_write_time, _measurement_started_at
    with _metrics_lock:
        _bytes_written = 0
        _last_write_time = 0.0
        _measurement_started_at = 0.0


def close_fifo() -> None:
    """Close the FIFO file descriptor."""
    global _fifo_fd
    if _fifo_fd is not None:
        with contextlib.suppress(OSError):
            os.close(_fifo_fd)
        _fifo_fd = None
        logger.info("Closed snapfifo")


def fifo_path() -> str:
    """Return the FIFO path (for Snapserver config)."""
    return _FIFO_PATH
