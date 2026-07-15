"""VinylLabPage — digitalise vinyl records via ADC/line-in capture.

Flows through: source selection → calibration → record side A/B →
waveform review → track splitting → cleanup → export → import.
"""

from __future__ import annotations

import logging
import os
import tempfile

import numpy as np

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QScrollArea, QFileDialog, QMessageBox, QProgressBar,
    QListWidget, QListWidgetItem,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_combo_qss,
    glass_progress_qss,
)

logger = logging.getLogger("michi.vinyl.ui")


class VinylLabPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, worker_mgr=None):
        super().__init__()
        self.setObjectName("vinylLabPage")
        self.setStyleSheet("#vinylLabPage { background: #090B11; }")
        self._worker_mgr = worker_mgr
        self._capture = None
        self._project_id = ""
        self._side_a_path = ""
        self._side_b_path = ""
        self._current_side = "A"
        self._is_recording = False
        self._waveform_data: list[float] = []
        self._split_points: list[float] = []
        self._monitor_active = False
        self._monitor_timer = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("vinylLabContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(16)

        # ── Header ──
        title = QLabel("Digitalizar Vinilo")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)
        sub = QLabel(
            "EXPERIMENTAL — Captura desde tu ADC/platina, separa pistas "
            "y exporta a FLAC.\n"
            "Las resoluciones 24/96 y 24/192 dependen de las capacidades "
            "reales de tu dispositivo."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # ── Step 1: Source selection ──
        step1 = self._build_step_box(
            "Paso 1: Seleccionar fuente de audio",
            self._build_source_panel(),
        )
        cl.addWidget(step1)

        # ── Step 2: Calibration ──
        step2 = self._build_step_box(
            "Paso 2: Calibrar nivel",
            self._build_calibration_panel(),
        )
        cl.addWidget(step2)

        # ── Step 3: Recording ──
        step3 = self._build_step_box(
            "Paso 3: Grabar",
            self._build_recording_panel(),
        )
        cl.addWidget(step3)

        # ── Step 4: Waveform & split ──
        step4 = self._build_step_box(
            "Paso 4: Revisar y separar pistas",
            self._build_split_panel(),
        )
        cl.addWidget(step4)

        # ── Step 5: Export ──
        step5 = self._build_step_box(
            "Paso 5: Exportar",
            self._build_export_panel(),
        )
        cl.addWidget(step5)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_step_box(self, title: str, panel: QWidget) -> QFrame:
        box = QFrame()
        box.setObjectName(f"vinylStep_{title[:20]}")
        box.setStyleSheet(glass_card_qss(box.objectName(), "base"))

        bl = QVBoxLayout(box)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.setSpacing(10)

        t = QLabel(title)
        t.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 15px; "
            "font-weight: 600; background: transparent; border: none;"
        )
        bl.addWidget(t)
        bl.addWidget(panel)
        return box

    def _build_source_panel(self) -> QWidget:
        w = QWidget()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(10)

        self._source_combo = QComboBox()
        self._source_combo.setStyleSheet(glass_combo_qss())
        self._source_combo.setMinimumWidth(300)
        self._source_combo.addItem("Por defecto (autoaudiosrc)")
        wl.addWidget(QLabel("Fuente:"))
        wl.addWidget(self._source_combo)

        self._sr_combo = QComboBox()
        self._sr_combo.setStyleSheet(glass_combo_qss())
        for sr in [44100, 48000, 96000]:
            label = f"{sr // 1000}.{sr % 1000 // 100} kHz"
            self._sr_combo.addItem(label, sr)
        self._sr_combo.addItem("192 kHz (experimental)", 192000)
        self._sr_combo.setCurrentIndex(2)  # 96 kHz default
        # Nota: las resoluciones dependen de las capacidades reales del ADC
        wl.addWidget(QLabel("Frecuencia:"))
        wl.addWidget(self._sr_combo)

        self._bd_combo = QComboBox()
        self._bd_combo.setStyleSheet(glass_combo_qss())
        self._bd_combo.addItem("16 bit", 16)
        self._bd_combo.addItem("24 bit", 24)
        self._bd_combo.setCurrentIndex(1)  # 24-bit default
        wl.addWidget(QLabel("Profundidad:"))
        wl.addWidget(self._bd_combo)

        wl.addStretch()
        return w

    def _build_calibration_panel(self) -> QWidget:
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(8)

        row = QHBoxLayout()
        self._cal_level = QProgressBar()
        self._cal_level.setRange(0, 100)
        self._cal_level.setValue(0)
        self._cal_level.setStyleSheet(glass_progress_qss() + """
            QProgressBar { height: 20px; border-radius: 6px; }
        """)
        row.addWidget(QLabel("Nivel L/R:"))
        row.addWidget(self._cal_level, 1)

        self._peak_label = QLabel("Peak: -- dB")
        self._peak_label.setStyleSheet(
            "color: rgba(255,255,255,0.62); font-size: 11px; "
            "background: transparent;"
        )
        row.addWidget(self._peak_label)

        self._cal_btn = QPushButton("Iniciar monitoreo")
        self._cal_btn.setCursor(Qt.PointingHandCursor)
        self._cal_btn.setStyleSheet(glass_button_qss("secondary"))
        self._cal_btn.clicked.connect(self._toggle_monitor)
        row.addWidget(self._cal_btn)
        wl.addLayout(row)

        hint = QLabel(
            "Ajusta el volumen de tu platina/ADC hasta que el nivel "
            "alcance el verde sin llegar a rojo. "
            "El pico ideal está entre -6 dB y -1 dB."
        )
        hint.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 11px; "
            "background: transparent;"
        )
        hint.setWordWrap(True)
        wl.addWidget(hint)
        return w

    def _build_recording_panel(self) -> QWidget:
        w = QWidget()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(12)

        self._project_name = QLabel("Proyecto: Nuevo")
        self._project_name.setStyleSheet(
            "color: rgba(255,255,255,0.72); font-size: 12px; "
            "background: transparent;"
        )
        wl.addWidget(self._project_name)

        self._side_label = QLabel("Cara A")
        self._side_label.setStyleSheet(
            "color: rgba(143,183,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        wl.addWidget(self._side_label)

        self._record_btn = QPushButton("Grabar Cara A")
        self._record_btn.setCursor(Qt.PointingHandCursor)
        self._record_btn.setStyleSheet(glass_button_qss("primary"))
        self._record_btn.clicked.connect(self._toggle_recording)
        wl.addWidget(self._record_btn)

        self._pause_btn = QPushButton("Pausa")
        self._pause_btn.setCursor(Qt.PointingHandCursor)
        self._pause_btn.setStyleSheet(glass_button_qss("ghost"))
        self._pause_btn.clicked.connect(self._toggle_pause)
        self._pause_btn.setVisible(False)
        wl.addWidget(self._pause_btn)

        self._rec_time = QLabel("00:00")
        self._rec_time.setStyleSheet(
            "color: rgba(255,255,255,0.82); font-size: 18px; "
            "font-weight: 700; background: transparent;"
        )
        wl.addWidget(self._rec_time)

        self._rec_progress = QProgressBar()
        self._rec_progress.setRange(0, 0)
        self._rec_progress.setVisible(False)
        self._rec_progress.setStyleSheet(glass_progress_qss())
        self._rec_progress.setFixedWidth(120)
        wl.addWidget(self._rec_progress)

        wl.addStretch()
        return w

    def _build_split_panel(self) -> QWidget:
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(8)

        # Waveform placeholder
        self._waveform_widget = QLabel("(Graba una cara para ver la waveform)")
        self._waveform_widget.setFixedHeight(80)
        self._waveform_widget.setStyleSheet(
            "background: rgba(255,255,255,0.02); border: 1px solid "
            "rgba(255,255,255,0.04); border-radius: 8px; "
            "color: rgba(255,255,255,0.42); font-size: 11px;"
        )
        self._waveform_widget.setAlignment(Qt.AlignCenter)
        wl.addWidget(self._waveform_widget)

        row = QHBoxLayout()
        self._detect_btn = QPushButton("Detectar silencios")
        self._detect_btn.setCursor(Qt.PointingHandCursor)
        self._detect_btn.setStyleSheet(glass_button_qss("secondary"))
        self._detect_btn.clicked.connect(self._detect_silences)
        row.addWidget(self._detect_btn)

        self._split_list = QListWidget()
        self._split_list.setStyleSheet(
            "QListWidget { background: transparent; border: 1px solid "
            "rgba(255,255,255,0.04); border-radius: 8px; "
            "color: rgba(255,255,255,0.72); font-size: 11px; }"
        )
        self._split_list.setMaximumHeight(100)
        row.addWidget(self._split_list, 1)
        wl.addLayout(row)
        return w

    def _build_export_panel(self) -> QWidget:
        w = QWidget()
        wl = QHBoxLayout(w)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(12)

        self._export_format = QComboBox()
        self._export_format.setStyleSheet(glass_combo_qss())
        self._export_format.addItem("FLAC (recomendado)", "flac")
        self._export_format.addItem("WAV sin comprimir", "wav")
        wl.addWidget(QLabel("Formato:"))
        wl.addWidget(self._export_format)

        self._export_dir_btn = QPushButton("Seleccionar destino...")
        self._export_dir_btn.setCursor(Qt.PointingHandCursor)
        self._export_dir_btn.setStyleSheet(glass_button_qss("secondary"))
        self._export_dir_btn.clicked.connect(self._select_export_dir)
        wl.addWidget(self._export_dir_btn)

        self._export_btn = QPushButton("Exportar")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setStyleSheet(glass_button_qss("primary"))
        self._export_btn.clicked.connect(self._export_and_import)
        wl.addWidget(self._export_btn)

        self._export_progress = QProgressBar()
        self._export_progress.setRange(0, 100)
        self._export_progress.setValue(0)
        self._export_progress.setVisible(False)
        self._export_progress.setStyleSheet(glass_progress_qss())
        wl.addWidget(self._export_progress, 1)

        wl.addStretch()
        return w

    # ── Actions ──

    def _toggle_pause(self):
        if not self._capture:
            return
        if self._capture.is_paused:
            self._capture.resume_recording()
            self._pause_btn.setText("Pausa")
            self._record_btn.setText(f"Detener Cara {self._current_side}")
        else:
            self._capture.pause_recording()
            self._pause_btn.setText("Reanudar")
            self._record_btn.setText(f"En pausa — Cara {self._current_side}")

    def _toggle_monitor(self):
        if not self._capture:
            from vinyl.capture_service import VinylCaptureService
            try:
                self._capture = VinylCaptureService()
            except Exception as e:
                QMessageBox.warning(
                    self, "Vinyl Lab",
                    f"No se pudo inicializar la captura: {e}"
                )
                return

        if hasattr(self, '_monitor_timer') and self._monitor_timer.isActive():
            self._monitor_timer.stop()
            self._monitor_active = False
            self._cal_btn.setText("Iniciar monitoreo")
            self._cal_level.setValue(0)
            self._peak_label.setText("Peak: -- dB")
        else:
            self._monitor_timer = QTimer()
            self._monitor_timer.timeout.connect(self._update_monitor)
            self._monitor_timer.start(200)
            self._monitor_active = True
            self._cal_btn.setText("Detener monitoreo")

    def _update_monitor(self):
        if not self._capture:
            return
        level = self._capture.get_level()
        self._cal_level.setValue(int(level * 100))
        if level > 0:
            db = 20 * np.log10(max(level, 0.001))
            self._peak_label.setText(f"Peak: {db:.1f} dB")
        else:
            self._peak_label.setText("Peak: -- dB")

    def _toggle_recording(self):
        if not self._capture:
            from vinyl.capture_service import VinylCaptureService
            try:
                self._capture = VinylCaptureService()
                self._capture.recording_started.connect(self._on_recording_started)
                self._capture.recording_finished.connect(self._on_recording_finished)
                self._capture.recording_error.connect(self._on_recording_error)
            except Exception as e:
                QMessageBox.warning(
                    self, "Vinyl Lab",
                    f"No se pudo inicializar la captura de audio: {e}\n\n"
                    "Asegúrate de tener GStreamer y los plugins de captura instalados."
                )
                return

        sr = self._sr_combo.currentData() or 96000
        bd = self._bd_combo.currentData() or 24
        self._capture.set_format(sr, bd, 2)

        if not self._is_recording:
            fd, filepath = tempfile.mkstemp(
                suffix=".wav", prefix=f"vinyl_{self._current_side}_"
            )
            os.close(fd)
            if self._current_side == "A":
                self._side_a_path = filepath
            else:
                self._side_b_path = filepath

            if self._capture.start_recording(filepath):
                self._is_recording = True
                self._record_btn.setText(
                    f"Detener Cara {self._current_side}"
                )
                self._record_btn.setStyleSheet(glass_button_qss("danger"))
                self._pause_btn.setVisible(True)
                self._pause_btn.setText("Pausa")
                self._pause_btn.setStyleSheet(glass_button_qss("ghost"))
                self._rec_progress.setVisible(True)
                self._rec_timer = QTimer()
                self._rec_timer.timeout.connect(self._update_rec_time)
                self._rec_timer.start(200)
                if not self._monitor_active:
                    self._monitor_timer = QTimer()
                    self._monitor_timer.timeout.connect(self._update_monitor)
                    self._monitor_timer.start(200)
                    self._monitor_active = True
        elif self._capture.is_paused:
            self._capture.resume_recording()
            self._record_btn.setText(
                f"Detener Cara {self._current_side}"
            )
            self._pause_btn.setText("Pausa")
        else:
            self._capture.stop_recording()
            self._is_recording = False
            self._pause_btn.setVisible(False)
            self._record_btn.setText(
                f"Grabar Cara {'B' if self._current_side == 'A' else 'A'}"
            )
            self._record_btn.setStyleSheet(glass_button_qss("primary"))
            self._rec_progress.setVisible(False)
            if hasattr(self, '_rec_timer'):
                self._rec_timer.stop()

            if self._current_side == "A":
                self._current_side = "B"
                self._side_label.setText("Cara B")
                self._record_btn.setText("Grabar Cara B")

    def _on_recording_started(self, filepath: str):
        logger.info("Recording started: %s", filepath)

    def _on_recording_finished(self, filepath: str):
        logger.info("Recording finished: %s", filepath)
        self._build_waveform(filepath)

    def _on_recording_error(self, error: str):
        self._is_recording = False
        self._record_btn.setText("Grabar")
        self._record_btn.setStyleSheet(glass_button_qss("primary"))
        self._rec_progress.setVisible(False)
        QMessageBox.warning(self, "Error", f"Error de captura: {error}")

    def _update_rec_time(self):
        if self._capture and self._capture.is_recording:
            try:
                secs = self._capture.get_recording_seconds()
                m, s = divmod(int(secs), 60)
                self._rec_time.setText(f"{m:02d}:{s:02d}")
            except Exception:
                pass

    def _build_waveform(self, filepath: str):
        from vinyl.waveform_builder import build_waveform
        result = build_waveform(filepath)
        if result.get("error"):
            self._waveform_widget.setText(f"Error: {result['error']}")
            return

        peaks = result.get("peaks", [])
        if peaks:
            self._waveform_data = peaks
            self._render_waveform(peaks, result.get("duration_sec", 0))
            self._waveform_widget.setText(
                f"Waveform: {result.get('duration_sec', 0):.1f}s "
                f"· {result.get('sample_rate', 0) // 1000} kHz "
                f"· Pico: {result.get('max_peak', 0)*100:.0f}%"
            )

    def _render_waveform(self, peaks: list[float], duration_sec: float):
        from PySide6.QtGui import QPainter, QPixmap, QColor, QLinearGradient
        w = max(self._waveform_widget.width(), 200)
        h = 80
        pix = QPixmap(w, h)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(143, 183, 255, 100))
        grad.setColorAt(0.5, QColor(143, 183, 255, 180))
        grad.setColorAt(1.0, QColor(143, 183, 255, 100))

        pen = painter.pen()
        pen.setBrush(grad)
        pen.setWidth(2)
        painter.setPen(pen)

        if len(peaks) > 1:
            step = max(1, len(peaks) // w)
            narrowed = peaks[::step][:w]
            cx = w / max(len(narrowed), 1)
            for i, p in enumerate(narrowed):
                x = int(i * cx)
                bar_h = max(1, int(p * h * 0.9))
                y = (h - bar_h) // 2
                painter.drawLine(x, y, x, y + bar_h)

        painter.end()
        self._waveform_widget.setPixmap(pix)

    def _detect_silences(self):
        fp = self._side_a_path or self._side_b_path
        if not fp or not os.path.exists(fp):
            QMessageBox.information(
                self, "Vinyl Lab",
                "Graba una cara primero antes de detectar silencios."
            )
            return

        from vinyl.waveform_builder import detect_silences, silence_to_split_points
        from vinyl.waveform_builder import build_waveform

        silences = detect_silences(fp)
        wf = build_waveform(fp)
        duration = wf.get("duration_sec", 0)
        self._split_points = silence_to_split_points(silences, duration)

        self._split_list.clear()
        for i, pt in enumerate(self._split_points):
            if i < len(self._split_points) - 1:
                dur = self._split_points[i + 1] - pt
                item = QListWidgetItem(
                    f"Pista {i + 1}: {pt:.1f}s - "
                    f"{self._split_points[i + 1]:.1f}s "
                    f"({dur:.0f}s)"
                )
                self._split_list.addItem(item)

    def _select_export_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar destino")
        if d:
            self._export_dir = d
            self._export_dir_btn.setText(f"Destino: {os.path.basename(d)}")

    def _export_and_import(self):
        fp = self._side_a_path or self._side_b_path
        if not fp or not os.path.exists(fp):
            QMessageBox.information(
                self, "Vinyl Lab",
                "No hay grabación para exportar."
            )
            return

        if not self._split_points:
            QMessageBox.information(
                self, "Vinyl Lab",
                "Detecta los silencios primero para separar las pistas."
            )
            return

        export_dir = getattr(self, '_export_dir', "")
        if not export_dir:
            export_dir = os.path.dirname(fp)
            self._export_dir = export_dir

        fmt = self._export_format.currentData() or "flac"
        self._export_progress.setVisible(True)
        self._export_progress.setValue(5)

        tracks = [
            {"track_number": i + 1, "title": f"Track {i + 1}"}
            for i in range(len(self._split_points) - 1)
        ]

        if self._worker_mgr:
            from vinyl.exporter import export_side
            self._export_btn.setEnabled(False)
            self._export_progress.setRange(0, 0)
            self._export_progress.setValue(0)
            self._worker_mgr.run_task(
                "vinyl_export",
                export_side, fp, export_dir, self._split_points, tracks, fmt,
                on_done=lambda r: self._on_export_done(r, export_dir, fmt),
                on_error=lambda e: self._on_export_error(e),
            )
        else:
            self._export_sync(fp, export_dir, fmt, tracks)

    def _export_sync(self, fp, export_dir, fmt, tracks):
        from vinyl.exporter import export_side
        result = export_side(fp, export_dir, self._split_points, tracks, fmt)
        self._on_export_done(result, export_dir, fmt)

    def _on_export_done(self, result, export_dir, fmt):
        self._export_progress.setRange(0, 100)
        self._export_progress.setValue(80)
        self._export_btn.setEnabled(True)
        exported = result.get("exported", [])
        errors = result.get("errors", [])
        imported = 0
        if exported:
            try:
                from ui.audio_lab.services.library_importer import LibraryImporter
                importer = LibraryImporter()
                r = importer.import_tracks(exported, {}, destination=export_dir)
                imported = len(r.get("ok", []))
                if imported:
                    importer.add_to_library(r["ok"])
            except Exception as e:
                logger.warning("Library import failed: %s", e)
        self._export_progress.setValue(100)
        msg = (
            f"Exportación completada.\n"
            f"{len(exported)} pistas exportadas a {fmt.upper()} en:\n"
            f"{export_dir}"
        )
        if errors:
            msg += f"\n\n{len(errors)} error(es):\n" + "\n".join(errors[:3])
        if imported:
            msg += f"\n\n{imported} pista(s) importada(s) a la biblioteca."
        else:
            msg += "\n\n(Importación a biblioteca no disponible)"
        QMessageBox.information(self, "Vinyl Lab", msg)

    def _on_export_error(self, error):
        self._export_btn.setEnabled(True)
        self._export_progress.setVisible(False)
        QMessageBox.warning(self, "Vinyl Lab", f"Error de exportación:\n{error}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._waveform_data:
            duration = 0.0
            fp = self._side_a_path or self._side_b_path
            if fp:
                from vinyl.waveform_builder import build_waveform
                wf = build_waveform(fp)
                duration = wf.get("duration_sec", 0)
            self._render_waveform(self._waveform_data, duration)
