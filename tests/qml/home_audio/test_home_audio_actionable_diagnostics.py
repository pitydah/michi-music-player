"""QML contract for actionable Home Audio diagnostics."""

from pathlib import Path


def test_diagnostics_page_exposes_actionable_signal_path() -> None:
    page = (
        Path(__file__).resolve().parents[3]
        / "ui_qml/pages/home_audio/DiagnosticsPage.qml"
    ).read_text(encoding="utf-8")

    for contract in (
        "measureLatency",
        "Michi → FIFO → Snapserver → Receptores",
        "Copiar diagnóstico",
        "Exportar informe",
        "bytes_written",
        "last_write_time",
        "throughput_bytes_per_second",
    ):
        assert contract in page
