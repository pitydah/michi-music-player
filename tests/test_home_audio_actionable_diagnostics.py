"""Actionable Home Audio diagnostics service and bridge contracts."""

from typing import Any
from unittest.mock import MagicMock, patch

from core.home_audio_service import HomeAudioService
from ui_qml_bridge.home_audio_bridge import HomeAudioBridge


class MemorySettings:
    """Minimal settings store for HomeAudioService tests."""

    def value(self, key: str, default: Any = None) -> Any:
        return default

    def setValue(self, key: str, value: Any) -> None:
        return None


def test_generate_test_tone_writes_pcm_to_snapcast_fifo() -> None:
    service = HomeAudioService(settings=MemorySettings())
    with patch(
        "integrations.snapcast.fifo_manager.write_fifo", return_value=17640
    ) as write_fifo:
        result = service.generateTestTone(durationMs=100, frequencyHz=440)

    payload = write_fifo.call_args.args[0]
    assert result == {"ok": True, "bytes_written": 17640, "duration_ms": 100}
    assert len(payload) == 17640
    assert payload != bytes(len(payload))


def test_generate_test_tone_reports_fifo_without_reader() -> None:
    service = HomeAudioService(settings=MemorySettings())
    with patch("integrations.snapcast.fifo_manager.write_fifo", return_value=0):
        result = service.generateTestTone(durationMs=50, frequencyHz=880)

    assert result == {"ok": False, "error": "FIFO_WRITE_FAILED", "bytes_written": 0}


def test_measure_latency_returns_receiver_report_and_control_rtt() -> None:
    service = HomeAudioService(settings=MemorySettings())
    service.get_receivers = MagicMock(
        return_value=[
            {"id": "receiver-1", "name": "Studio", "connected": True, "latency_ms": 32}
        ]
    )
    with patch("core.home_audio_service.time.perf_counter", side_effect=[10.0, 10.012]):
        result = service.measureLatency("receiver-1")

    assert result == {
        "ok": True,
        "receiver_id": "receiver-1",
        "receiver_name": "Studio",
        "latency_ms": 32,
        "control_rtt_ms": 12,
    }


def test_measure_latency_rejects_offline_receiver() -> None:
    service = HomeAudioService(settings=MemorySettings())
    service.get_receivers = MagicMock(
        return_value=[{"id": "receiver-1", "connected": False, "latency_ms": 32}]
    )

    assert service.measureLatency("receiver-1") == {
        "ok": False,
        "error": "RECEIVER_OFFLINE",
    }


def test_bridge_uses_test_tone_and_latency_service_contracts() -> None:
    service = MagicMock()
    service.generate_test_tone.return_value = {"ok": True, "bytes_written": 4096}
    service.measure_latency.return_value = {"ok": True, "latency_ms": 24}
    bridge = HomeAudioBridge(home_audio_service=service)

    assert bridge.testTone()["bytes_written"] == 4096
    assert bridge.measureLatency("receiver-1")["latency_ms"] == 24
    service.generate_test_tone.assert_called_once_with()
    service.measure_latency.assert_called_once_with("receiver-1")


def test_diagnostics_report_can_be_copied_and_exported(tmp_path) -> None:
    bridge = HomeAudioBridge(home_audio_service=MagicMock())
    report_path = tmp_path / "home-audio.txt"
    clipboard = MagicMock()
    with patch(
        "ui_qml_bridge.home_audio_bridge.QGuiApplication.clipboard",
        return_value=clipboard,
    ):
        copied = bridge.copyDiagnostics("Signal path OK")
    exported = bridge.exportDiagnostics(str(report_path), "Signal path OK")

    clipboard.setText.assert_called_once_with("Signal path OK")
    assert copied == {"ok": True}
    assert exported == {"ok": True, "path": str(report_path)}
    assert report_path.read_text(encoding="utf-8") == "Signal path OK"
