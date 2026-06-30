"""DiagnosticsPage — analyse audio files and generate technical reports.

Reuses format_probe and quality_classifier from existing modules.
Marked as Experimental — Fake Hi-Res detection is not included yet.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QScrollArea,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_progress_qss,
)

logger = logging.getLogger("michi.diagnostics.ui")


class DiagnosticsPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("diagnosticsPage")
        self._results: list[dict] = []
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

        title = QLabel("Diagnóstico")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "EXPERIMENTAL — Analiza archivos de audio individuales o "
            "carpetas completas usando format_probe y quality_classifier.\n"
            "Genera un reporte técnico con formato, calidad, duración "
            "y estadísticas de colección."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Action buttons
        action_card = QFrame()
        action_card.setStyleSheet(glass_card_qss("diagActionsCard"))
        avl = QVBoxLayout(action_card)
        avl.setContentsMargins(20, 16, 20, 16)
        avl.setSpacing(10)

        al = QLabel("Acciones")
        al.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        avl.addWidget(al)

        btn_row = QHBoxLayout()
        self._analyse_file_btn = QPushButton("Analizar archivo...")
        self._analyse_file_btn.setCursor(Qt.PointingHandCursor)
        self._analyse_file_btn.setStyleSheet(glass_button_qss("secondary"))
        self._analyse_file_btn.clicked.connect(self._analyse_file)
        btn_row.addWidget(self._analyse_file_btn)

        self._analyse_folder_btn = QPushButton("Analizar carpeta...")
        self._analyse_folder_btn.setCursor(Qt.PointingHandCursor)
        self._analyse_folder_btn.setStyleSheet(glass_button_qss("secondary"))
        self._analyse_folder_btn.clicked.connect(self._analyse_folder)
        btn_row.addWidget(self._analyse_folder_btn)

        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(glass_button_qss("ghost"))
        self._clear_btn.clicked.connect(self._clear_results)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        avl.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(glass_progress_qss())
        avl.addWidget(self._progress)

        cl.addWidget(action_card)

        # Results table
        results_card = QFrame()
        results_card.setStyleSheet(glass_card_qss("diagResultsCard"))
        rvl = QVBoxLayout(results_card)
        rvl.setContentsMargins(20, 16, 20, 16)
        rvl.setSpacing(10)

        rl = QLabel("Resultados")
        rl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        rvl.addWidget(rl)

        self._results_table = QTableWidget()
        self._results_table.setColumnCount(7)
        self._results_table.setHorizontalHeaderLabels(
            ["Archivo", "Formato", "SR", "BD", "Duración", "Calidad", "Tamaño"]
        )
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._results_table.setStyleSheet(
            "QTableWidget { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.72); "
            "font-size: 11px; gridline-color: rgba(255,255,255,0.03); }"
            "QHeaderView::section { background: rgba(255,255,255,0.03); "
            "color: rgba(255,255,255,0.56); border: none; "
            "padding: 4px; font-size: 10px; }"
        )
        self._results_table.setMinimumHeight(150)
        rvl.addWidget(self._results_table)

        cl.addWidget(results_card)

        # Spectral analysis
        spec_card = QFrame()
        spec_card.setStyleSheet(glass_card_qss("diagSpecCard"))
        svl = QVBoxLayout(spec_card)
        svl.setContentsMargins(20, 16, 20, 16)
        svl.setSpacing(10)

        spec_title = QLabel("Coherencia espectral Hi-Res")
        spec_title.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        svl.addWidget(spec_title)

        spec_sub = QLabel(
            "EXPERIMENTAL — Evalúa si el contenido espectral es coherente "
            "con la resolución declarada.\n"
            "El resultado es probabilístico y no debe interpretarse "
            "como prueba definitiva."
        )
        spec_sub.setStyleSheet(
            "color: rgba(255,255,255,0.48); font-size: 11px; "
            "background: transparent;"
        )
        spec_sub.setWordWrap(True)
        svl.addWidget(spec_sub)

        spec_btn_row = QHBoxLayout()
        self._spectral_btn = QPushButton("Analizar archivo WAV...")
        self._spectral_btn.setCursor(Qt.PointingHandCursor)
        self._spectral_btn.setStyleSheet(glass_button_qss("secondary"))
        self._spectral_btn.clicked.connect(self._analyse_spectral)
        spec_btn_row.addWidget(self._spectral_btn)
        spec_btn_row.addStretch()
        svl.addLayout(spec_btn_row)

        self._spectral_result = QLabel("")
        self._spectral_result.setStyleSheet(
            "color: rgba(255,255,255,0.72); font-size: 12px; "
            "background: transparent;"
        )
        self._spectral_result.setWordWrap(True)
        svl.addWidget(self._spectral_result)

        cl.addWidget(spec_card)

        # Report
        report_card = QFrame()
        report_card.setStyleSheet(glass_card_qss("diagReportCard"))
        report_vl = QVBoxLayout(report_card)
        report_vl.setContentsMargins(20, 16, 20, 16)
        report_vl.setSpacing(8)

        report_title = QLabel("Reporte técnico")
        report_title.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        report_vl.addWidget(report_title)

        self._report_label = QLabel(
            "Analiza archivos o carpetas para ver el reporte."
        )
        self._report_label.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent;"
        )
        self._report_label.setWordWrap(True)
        report_vl.addWidget(self._report_label)

        self._generate_report_btn = QPushButton("Generar reporte")
        self._generate_report_btn.setCursor(Qt.PointingHandCursor)
        self._generate_report_btn.setStyleSheet(glass_button_qss("primary"))
        self._generate_report_btn.clicked.connect(self._show_report)
        self._generate_report_btn.setEnabled(False)
        report_vl.addWidget(self._generate_report_btn)

        cl.addWidget(report_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _analyse_file(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de audio", "",
            "Audio (*.flac *.wav *.mp3 *.ogg *.opus *.m4a *.aiff *.wv *.dsf *.dff)"
        )
        if not fp:
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        from ui.audio_lab.diagnostics_service import analyse_file
        result = analyse_file(fp)
        self._results = [result]

        self._populate_table()
        self._generate_report_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._show_report()

    def _analyse_spectral(self):
        fp, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo WAV para análisis espectral", "",
            "WAV (*.wav)"
        )
        if not fp:
            return

        self._spectral_result.setText("Analizando contenido espectral...")
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()

        from ui.audio_lab.diagnostics_service import analyse_spectral
        result = analyse_spectral(fp)

        lines = [
            f"Archivo: {fp.split('/')[-1]}",
            f"Veredicto: {result.get('label', '?')}",
            f"Confianza: {result.get('confidence', 'N/A')}",
            f"Explicación: {result.get('explanation', '?')}",
        ]
        metrics = result.get("metrics", {})
        if metrics:
            lines.append("")
            lines.append("Métricas espectrales:")
            for k, v in metrics.items():
                if isinstance(v, float):
                    lines.append(f"  {k}: {v:.2f}")
                elif isinstance(v, bool):
                    lines.append(f"  {k}: {'Sí' if v else 'No'}")
                else:
                    lines.append(f"  {k}: {v}")

        error = result.get("error", "")
        if error:
            lines.append("")
            lines.append(f"Error: {error}")

        self._spectral_result.setText("\n".join(lines))

    def _analyse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con archivos de audio"
        )
        if not folder:
            return

        from ui.audio_lab.diagnostics_service import analyse_file, AUDIO_EXTS

        audio_files = []
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    audio_files.append(os.path.join(root, f))

        if not audio_files:
            QMessageBox.information(
                self, "Diagnóstico",
                "No se encontraron archivos de audio en la carpeta seleccionada."
            )
            return

        self._progress.setVisible(True)
        self._progress.setRange(0, len(audio_files))
        self._progress.setValue(0)

        self._results = []
        for i, fp in enumerate(audio_files):
            self._results.append(analyse_file(fp))
            self._progress.setValue(i + 1)
            from PySide6.QtCore import QCoreApplication
            QCoreApplication.processEvents()

        self._populate_table()
        self._generate_report_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._show_report()

    def _clear_results(self):
        self._results.clear()
        self._results_table.setRowCount(0)
        self._report_label.setText("Resultados limpiados.")
        self._generate_report_btn.setEnabled(False)

    def _populate_table(self):
        self._results_table.setRowCount(len(self._results))
        for i, r in enumerate(self._results):
            fi = r.get("format_info", {})
            q = r.get("quality", {})
            self._results_table.setItem(i, 0, QTableWidgetItem(r.get("filename", "")))
            self._results_table.setItem(i, 1, QTableWidgetItem(
                fi.get("container", "").upper() or fi.get("codec", "") or "?"
            ))
            sr = fi.get("sample_rate", 0)
            self._results_table.setItem(i, 2, QTableWidgetItem(
                f"{sr // 1000}.{sr % 1000 // 100} kHz" if sr else "?"
            ))
            bd = fi.get("bit_depth", 0)
            self._results_table.setItem(i, 3, QTableWidgetItem(
                f"{bd} bit" if bd else "?"
            ))
            self._results_table.setItem(i, 4, QTableWidgetItem(
                r.get("duration_str", "?")
            ))
            self._results_table.setItem(i, 5, QTableWidgetItem(
                q.get("label", q.get("category", "?"))
            ))
            self._results_table.setItem(i, 6, QTableWidgetItem(
                f"{r.get('size_mb', 0)} MB" if r.get('size_mb') else "?"
            ))

        self._results_table.resizeColumnsToContents()
        self._results_table.setColumnWidth(0, 200)

    def _show_report(self):
        if not self._results:
            return

        from ui.audio_lab.diagnostics_service import generate_report
        report = generate_report(self._results)

        lines = [
            f"Total archivos: {report['total_files']}",
            f"Tamaño total: {report['total_size_mb']} MB",
            f"Duración total: {report['total_duration_str']}",
            "",
            "Formatos:",
        ]
        for fmt, count in report["format_counts"].items():
            lines.append(f"  .{fmt}: {count} archivo(s)")
        lines.append("")
        lines.append("Calidad:")
        for cat, count in report["quality_counts"].items():
            lines.append(f"  {cat}: {count}")
        if report["sample_rates"]:
            lines.append("")
            lines.append(
                f"Frecuencias: {', '.join(str(s) for s in report['sample_rates'])} Hz"
            )
        if report["bit_depths"]:
            lines.append(
                f"Profundidades: {', '.join(str(b) for b in report['bit_depths'])} bit"
            )
        if report["errors"]:
            lines.append("")
            lines.append(f"Errores: {len(report['errors'])} archivo(s)")
            for e in report["errors"][:5]:
                lines.append(f"  ✗ {os.path.basename(e)}")
        if report["warnings"]:
            lines.append("")
            lines.append(f"Advertencias: {len(report['warnings'])}")
            for fp, w in report["warnings"][:5]:
                lines.append(f"  ⚠ {os.path.basename(fp)}: {w}")

        self._report_label.setText("\n".join(lines))
