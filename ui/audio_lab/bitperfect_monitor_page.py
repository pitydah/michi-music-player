"""BitPerfectMonitorPage — displays real-time bit-perfect verification status."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QFrame, QScrollArea,
)

from ui.central.central_styles import glass_card_qss

_STATUS_COLORS = {
    "off": "#666666",
    "requested": "#ffd54f",
    "not_verified": "#ff9800",
    "verified": "#4caf50",
    "broken": "#f44336",
    "not_connected": "#ff9800",
}


class BitperfectMonitorPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("bitperfectMonitorPage")
        self.setStyleSheet("#bitperfectMonitorPage { background: #090B11; }")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        title = QLabel("Monitor Bit-Perfect")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; background: transparent;")
        cl.addWidget(title)

        sub = QLabel(
            "Verificación en tiempo real de la ruta de audio bit-perfect.\n"
            "Compara el archivo original con la salida real del DAC.")
        sub.setStyleSheet("color: rgba(255,255,255,0.56); font-size: 13px; background: transparent;")
        sub.setWordWrap(True)
        cl.addWidget(sub)

        self._status_card = self._build_card("Estado Bit-Perfect", self._build_status_section())
        cl.addWidget(self._status_card)

        self._input_card = self._build_card("Archivo", self._build_info_section())
        cl.addWidget(self._input_card)

        self._output_card = self._build_card("Salida", self._build_output_section())
        cl.addWidget(self._output_card)

        self._dsp_card = self._build_card("Procesamiento", self._build_dsp_section())
        cl.addWidget(self._dsp_card)

        self._warnings_card = self._build_card("Advertencias", self._build_warnings_section())
        cl.addWidget(self._warnings_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_card(self, card_title: str, panel: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName(f"bpCard_{card_title[:20]}")
        card.setStyleSheet(glass_card_qss(card.objectName(), "base"))
        vl = QVBoxLayout(card)
        vl.setContentsMargins(20, 16, 20, 16)
        vl.setSpacing(10)

        t = QLabel(card_title)
        t.setStyleSheet("color: rgba(255,255,255,0.88); font-size: 15px; font-weight: 600; background: transparent; border: none;")
        vl.addWidget(t)

        vl.addWidget(panel)
        return card

    def _build_status_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self._status_label = QLabel("—")
        self._status_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #666;")
        layout.addWidget(self._status_label)

        self._status_reason = QLabel("")
        self._status_reason.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.62);")
        self._status_reason.setWordWrap(True)
        layout.addWidget(self._status_reason)

        return w

    def _build_info_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._input_codec = QLabel("Codec: —")
        self._input_rate = QLabel("Sample Rate: —")
        self._input_depth = QLabel("Bit Depth: —")
        self._input_channels = QLabel("Canales: —")
        for lbl in (self._input_codec, self._input_rate, self._input_depth, self._input_channels):
            lbl.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.72);")
            layout.addWidget(lbl)
        return w

    def _build_output_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._output_backend = QLabel("Backend: —")
        self._output_device = QLabel("Dispositivo: —")
        self._output_rate = QLabel("Sample Rate real: —")
        self._output_format = QLabel("Formato real: —")
        self._output_channels = QLabel("Canales reales: —")
        for lbl in (self._output_backend, self._output_device, self._output_rate,
                    self._output_format, self._output_channels):
            lbl.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.72);")
            layout.addWidget(lbl)
        return w

    def _build_dsp_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._dsp_eq = QLabel("EQ: —")
        self._dsp_rg = QLabel("ReplayGain: —")
        self._dsp_spectrum = QLabel("Spectrum: —")
        self._dsp_volume = QLabel("Volumen digital: —")
        self._dsp_resample = QLabel("Resampling: —")
        for lbl in (self._dsp_eq, self._dsp_rg, self._dsp_spectrum,
                    self._dsp_volume, self._dsp_resample):
            lbl.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.72);")
            layout.addWidget(lbl)
        return w

    def _build_warnings_section(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self._warnings_list = QLabel("Sin advertencias")
        self._warnings_list.setStyleSheet("font-size: 13px; color: #ff9800;")
        self._warnings_list.setWordWrap(True)
        layout.addWidget(self._warnings_list)
        return w

    def update_from_report(self, report, diagnostics=None):
        """Update UI from a BitperfectReport and optional AudioDiagnostics."""
        color = _STATUS_COLORS.get(report.status, "#666")
        labels = {
            "off": "Apagado — El perfil actual no es bit-perfect",
            "requested": "Solicitado — Esperando reproducción activa",
            "not_verified": "No verificado — No se puede confirmar la ruta",
            "verified": "Verificado — La ruta es bit-perfect",
            "broken": "Roto — La ruta no es bit-perfect",
        }
        self._status_label.setText(labels.get(report.status, report.status))
        self._status_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {color};")
        self._status_reason.setText("\n".join(report.reasons) if report.reasons else "")

        self._input_codec.setText("Codec: —")
        self._input_rate.setText("Sample Rate: {report.input_sample_rate} Hz" if report.input_sample_rate else "Sample Rate: —")
        self._input_depth.setText("Bit Depth: {report.input_bit_depth}-bit" if report.input_bit_depth else "Bit Depth: —")
        self._input_channels.setText(f"Canales: {report.input_channels}" if report.input_channels else "Canales: —")

        backend = getattr(diagnostics, 'backend_id', '') or getattr(diagnostics, 'backend', '')
        self._output_backend.setText(f"Backend: {backend}" if backend else "Backend: —")
        self._output_device.setText(f"Dispositivo: {report.device}" if report.device else "Dispositivo: —")
        self._output_rate.setText(f"Sample Rate real: {report.output_sample_rate} Hz" if report.output_sample_rate else "Sample Rate real: —")
        self._output_format.setText(f"Formato real: {report.output_format}" if report.output_format else "Formato real: —")
        self._output_channels.setText(f"Canales reales: {report.output_channels}" if report.output_channels else "Canales reales: —")

        eq_active = getattr(diagnostics, 'eq_active', False)
        rg_active = getattr(diagnostics, 'replaygain_active', False)
        spec_active = getattr(diagnostics, 'spectrum_active', False)
        vol_active = getattr(diagnostics, 'digital_volume_active', False)
        resample_active = getattr(diagnostics, 'resampling_active', False)
        self._dsp_eq.setText(f"EQ: {'ACTIVO' if eq_active else 'Inactivo'}")
        self._dsp_rg.setText(f"ReplayGain: {'ACTIVO' if rg_active else 'Inactivo'}")
        self._dsp_spectrum.setText(f"Spectrum: {'ACTIVO' if spec_active else 'Inactivo'}")
        self._dsp_volume.setText(f"Volumen digital: {'ACTIVO' if vol_active else 'Bloqueado'}")
        self._dsp_resample.setText(f"Resampling: {'ACTIVO' if resample_active else 'Inactivo'}")

        if report.reasons:
            self._warnings_list.setText("\n".join(f"⚠ {r}" for r in report.reasons))
        else:
            self._warnings_list.setText("Sin advertencias")
