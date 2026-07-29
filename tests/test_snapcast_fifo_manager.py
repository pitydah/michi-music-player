"""Metrics and writes for the Snapcast FIFO manager."""

from unittest.mock import patch

from integrations.snapcast import fifo_manager


def test_write_fifo_tracks_bytes_last_write_and_throughput() -> None:
    fifo_manager._reset_metrics()

    with (
        patch.object(fifo_manager, "get_snapfifo_fd", return_value=17),
        patch.object(fifo_manager.os, "write", return_value=4),
        patch.object(fifo_manager.time, "time", return_value=200.0),
        patch.object(fifo_manager.time, "monotonic", side_effect=[10.0, 12.0]),
    ):
        written = fifo_manager.write_fifo(b"tone")
        metrics = fifo_manager.fifo_metrics()

    assert written == 4
    assert metrics == {
        "bytes_written": 4,
        "last_write_time": 200.0,
        "throughput_bytes_per_second": 2.0,
    }


def test_write_fifo_without_reader_does_not_record_metrics() -> None:
    fifo_manager._reset_metrics()

    with patch.object(fifo_manager, "get_snapfifo_fd", return_value=None):
        written = fifo_manager.write_fifo(b"tone")

    assert written == 0
    assert fifo_manager.fifo_metrics()["bytes_written"] == 0
