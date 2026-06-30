"""DiagnosticsPage — analyse audio files and generate technical reports.

Reuses format_probe, quality_classifier and spectral_authenticator.
Includes experimental spectral coherence analysis for WAV PCM.
Results are probabilistic and not conclusive.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal, Slot, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QFileDialog, QScrollArea,
    QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QCheckBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_progress_qss,
)

logger = logging.getLogger("michi.diagnostics.ui")


class _FolderWorker(QObject):
    """Worker object for folder analysis. Emits results to main thread."""

    file_done = Signal(object)   # result dict
    folder_done = Signal()

    def __init__(self, file_list: list[str], include_spectral: bool):
        super().__init__()
        self._files = file_list
        self._include_spectral = include_spectral
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        from core.audio_lab.diagnostics_service import analyse_file
        for fp in self._files:
            if self._cancelled:
                break
            try:
                result = analyse_file(fp)
            except Exception as e:
                result = {
                    "filepath": fp, "filename": os.path.basename(fp),
                    "exists": True, "error": str(e),
                    "format_info": {}, "size_mb": 0.0, "duration_str": "",
                    "quality": {"category": "error", "label": "Error"},
                }
            if self._include_spectral and fp.lower().endswith(".wav") and not result.get("error"):
                try:
                    from core.audio_lab.diagnostics_service import analyse_spectral
                    spec = analyse_spectral(fp)
                    if spec:
                        result["spectral"] = spec
                except Exception:
                    pass
            self.file_done.emit(result)
        if not self._cancelled:
            self.folder_done.emit()


class DiagnosticsPage(QWidget):
    navigate_requested = Signal(str)

    diagnostics_updated = Signal(list)  # list of filepaths

    def __init__(self, worker_mgr=None, job_manager=None, db=None):
        super().__init__()
        self.setObjectName("diagnosticsPage")
        self._worker_mgr = worker_mgr
        self._job_manager = job_manager
        self._db = db
        self._results: list[dict] = []
        self._cancelled = False
        self._worker_thread: QThread | None = None
        self._worker_obj: _FolderWorker | None = None
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

        self._spectral_check = QCheckBox("Análisis espectral (WAV/FLAC experimental)")
        self._spectral_check.setStyleSheet(
            "color: rgba(255,255,255,0.70); font-size: 11px; "
            "background: transparent;"
        )
        self._spectral_check.setChecked(False)
        avl.addWidget(self._spectral_check)

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

        self._queue_btn = QPushButton("Cola persistente")
        self._queue_btn.setCursor(Qt.PointingHandCursor)
        self._queue_btn.setStyleSheet(glass_button_qss("ghost"))
        self._queue_btn.clicked.connect(self._analyse_with_job_manager)
        self._queue_btn.setVisible(self._job_manager is not None)
        btn_row.addWidget(self._queue_btn)

        self._library_btn = QPushButton("Analizar biblioteca completa")
        self._library_btn.setCursor(Qt.PointingHandCursor)
        self._library_btn.setStyleSheet(glass_button_qss("primary"))
        self._library_btn.clicked.connect(self._analyse_library)
        self._library_btn.setVisible(self._job_manager is not None and self._db is not None)
        btn_row.addWidget(self._library_btn)

        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(glass_button_qss("ghost"))
        self._clear_btn.clicked.connect(self._clear_results)
        btn_row.addWidget(self._clear_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet(glass_button_qss("danger"))
        self._cancel_btn.clicked.connect(self._cancel_analysis)
        self._cancel_btn.setVisible(False)
        btn_row.addWidget(self._cancel_btn)

        btn_row.addStretch()
        avl.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(glass_progress_qss())
        avl.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 11px; "
            "background: transparent;"
        )
        self._progress_label.setVisible(False)
        avl.addWidget(self._progress_label)

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

        export_row = QHBoxLayout()
        self._export_txt_btn = QPushButton("Exportar TXT")
        self._export_txt_btn.setCursor(Qt.PointingHandCursor)
        self._export_txt_btn.setStyleSheet(glass_button_qss("ghost"))
        self._export_txt_btn.clicked.connect(lambda: self._export_report("txt"))
        self._export_txt_btn.setEnabled(False)
        export_row.addWidget(self._export_txt_btn)

        self._export_csv_btn = QPushButton("Exportar CSV")
        self._export_csv_btn.setCursor(Qt.PointingHandCursor)
        self._export_csv_btn.setStyleSheet(glass_button_qss("ghost"))
        self._export_csv_btn.clicked.connect(lambda: self._export_report("csv"))
        self._export_csv_btn.setEnabled(False)
        export_row.addWidget(self._export_csv_btn)

        self._export_json_btn = QPushButton("Exportar JSON")
        self._export_json_btn.setCursor(Qt.PointingHandCursor)
        self._export_json_btn.setStyleSheet(glass_button_qss("ghost"))
        self._export_json_btn.clicked.connect(lambda: self._export_report("json"))
        self._export_json_btn.setEnabled(False)
        export_row.addWidget(self._export_json_btn)

        export_row.addStretch()
        report_vl.addLayout(export_row)

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

        from core.audio_lab.diagnostics_service import analyse_file
        result = analyse_file(fp)
        self._results = [result]
        self._sync_result(result)
        self.diagnostics_updated.emit([fp])

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

        from core.audio_lab.diagnostics_service import analyse_spectral
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

    def _analyse_with_job_manager(self):
        if not self._job_manager:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para análisis persistente"
        )
        if not folder:
            return
        self._start_job_analysis(folder)

    def _analyse_library(self):
        if not self._job_manager or not self._db:
            return
        from core.paths import database_path
        db_path = database_path()
        folder = os.path.dirname(db_path)
        roots = self._db._conn.execute(
            "SELECT path FROM library_roots WHERE enabled=1"
        ).fetchall()
        paths = [r[0] for r in roots if r[0]]
        if not paths:
            roots2 = self._db._conn.execute(
                "SELECT path FROM scan_roots WHERE enabled=1"
            ).fetchall()
            paths = [r[0] for r in roots2 if r[0]]
        if not paths:
            self._report_label.setText(
                "No hay raíces de biblioteca configuradas. "
                "Añade carpetas en Ajustes > Biblioteca."
            )
            return
        folder = paths[0]
        self._start_job_analysis(folder)

    def _start_job_analysis(self, folder: str):
        include_spectral = self._spectral_check.isChecked()
        from core.audio_lab.diagnostics_service import analyse_directory_job

        # Wire JobManager signals
        self._job_manager.job_progress.connect(self._on_job_progress)
        self._job_manager.job_completed.connect(self._on_job_completed)
        self._job_manager.job_failed.connect(self._on_job_failed)

        job_id = analyse_directory_job(
            folder, job_manager=self._job_manager,
            include_spectral=include_spectral,
        )
        if job_id:
            self._report_label.setText(
                f"Job creado: {job_id[:8]}... Analizando biblioteca."
            )
            self._library_btn.setEnabled(False)
        else:
            self._report_label.setText(
                "No se pudo crear el job de análisis."
            )

    def _on_job_progress(self, job_id: str, progress: float):
        pct = int(progress * 100)
        self._report_label.setText(
            f"Job {job_id[:8]}...: {pct}%"
        )

    def _on_job_completed(self, job_id: str, result: dict):
        self._library_btn.setEnabled(True)
        processed = result.get("processed", 0)
        errors = result.get("errors", [])
        synced = 0
        if self._db and hasattr(self._db, '_conn'):
            from core.audio_lab.audio_lab_sync import sync_audio_lab_cache_to_media_items
            import contextlib
            with contextlib.suppress(Exception):
                synced = sync_audio_lab_cache_to_media_items(self._db._conn)
        msg = f"Análisis completado: {processed} archivos procesados."
        if synced:
            msg += f" {synced} registros sincronizados."
        if errors:
            msg += f" {len(errors)} errores."
        self._report_label.setText(msg)

    def _on_job_failed(self, job_id: str, error: str):
        self._library_btn.setEnabled(True)
        self._report_label.setText(f"Job falló: {error}")

    def _analyse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con archivos de audio"
        )
        if not folder:
            return

        from core.audio_lab.diagnostics_service import AUDIO_EXTS

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

        self._cancelled = False
        self._results = []
        self._analyse_file_btn.setEnabled(False)
        self._analyse_folder_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, len(audio_files))
        self._progress.setValue(0)
        self._progress_label.setVisible(True)
        self._progress_label.setText(f"Analizando 0/{len(audio_files)}...")

        include_spectral = self._spectral_check.isChecked()
        self._total_files = len(audio_files)

        self._worker_obj = _FolderWorker(audio_files, include_spectral)
        self._worker_obj.file_done.connect(self._on_file_result)
        self._worker_obj.folder_done.connect(self._on_folder_analysis_done)

        self._worker_thread = QThread()
        self._worker_obj.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker_obj.run)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.start()

    def _sync_result(self, result: dict):
        if not self._db:
            return
        fp = result.get("filepath", "")
        if not fp:
            return
        try:
            from core.audio_lab.audio_lab_sync import sync_audio_lab_result_to_media_item
            sync_audio_lab_result_to_media_item(
                self._db._conn, fp, result,
            )
        except Exception:
            pass

    @Slot(object)
    def _on_file_result(self, result: dict):
        if self._cancelled:
            return
        self._results.append(result)
        self._sync_result(result)
        current = len(self._results)
        self._progress.setValue(min(current, self._total_files))
        self._progress_label.setText(
            f"Analizando {min(current, self._total_files)}/{self._total_files}..."
        )

    @Slot()
    def _on_folder_analysis_done(self):
        if self._cancelled:
            return
        self._analyse_finished()

    def _analyse_finished(self):
        self._analyse_file_btn.setEnabled(True)
        self._analyse_folder_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(500)
            self._worker_thread = None
        self._worker_obj = None
        if self._results:
            synced = [r.get("filepath", "") for r in self._results if r.get("filepath")]
            if synced:
                self.diagnostics_updated.emit(synced)
            self._populate_table()
            self._generate_report_btn.setEnabled(True)
            self._show_report()

    def _cancel_analysis(self):
        self._cancelled = True
        if self._worker_obj:
            self._worker_obj.cancel()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait(500)
            self._worker_thread = None
        self._worker_obj = None
        self._analyse_file_btn.setEnabled(True)
        self._analyse_folder_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(True)
        self._progress_label.setText("Análisis cancelado.")

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
            quality_text = q.get("label", q.get("category", "?"))
            spec = r.get("spectral", {})
            if spec and spec.get("label"):
                quality_text += f" | {spec['label']}"
            self._results_table.setItem(i, 5, QTableWidgetItem(quality_text))
            self._results_table.setItem(i, 6, QTableWidgetItem(
                f"{r.get('size_mb', 0)} MB" if r.get('size_mb') else "?"
            ))

        self._results_table.resizeColumnsToContents()
        self._results_table.setColumnWidth(0, 200)

    def _show_report(self):
        if not self._results:
            return

        from core.audio_lab.diagnostics_service import generate_report
        report = generate_report(self._results)

        lines = [
            "=== Resumen general ===",
            f"Total archivos: {report['total_files']}",
            f"Tamaño total: {report['total_size_mb']} MB",
            f"Duración total: {report['total_duration_str']}",
            "",
            "=== Formatos ===",
        ]
        for fmt, count in report["format_counts"].items():
            lines.append(f"  .{fmt}: {count} archivo(s)")
        lines.append("")
        lines.append("=== Resolución ===")
        if report["sample_rates"]:
            lines.append(
                f"  Frecuencias: {', '.join(str(s) for s in report['sample_rates'])} Hz"
            )
        if report["bit_depths"]:
            lines.append(
                f"  Profundidades: {', '.join(str(b) for b in report['bit_depths'])} bit"
            )
        if report["channels"]:
            lines.append(
                f"  Canales: {', '.join(str(c) for c in report['channels'])}"
            )
        lines.append("")
        lines.append("=== Calidad ===")
        for cat, count in report["quality_counts"].items():
            lines.append(f"  {cat}: {count}")
        if report["lossless_count"]:
            lines.append(f"  Lossless: {report['lossless_count']}")
        if report["lossy_count"]:
            lines.append(f"  Lossy: {report['lossy_count']}")
        if report["hires_count"]:
            lines.append(f"  Hi-Res: {report['hires_count']}")
        if report["dsd_count"]:
            lines.append(f"  DSD: {report['dsd_count']}")
        if report["missing_bit_depth"]:
            lines.append("")
            lines.append(f"=== Sin bit depth ({len(report['missing_bit_depth'])}) ===")
            for fp in report["missing_bit_depth"][:5]:
                lines.append(f"  ⚠ {os.path.basename(fp)}")
            if len(report["missing_bit_depth"]) > 5:
                lines.append(f"  ... y {len(report['missing_bit_depth']) - 5} más")
        if report["missing_duration"]:
            lines.append("")
            lines.append(f"=== Sin duración ({len(report['missing_duration'])}) ===")
            for fp in report["missing_duration"][:5]:
                lines.append(f"  ⚠ {os.path.basename(fp)}")
            if len(report["missing_duration"]) > 5:
                lines.append(f"  ... y {len(report['missing_duration']) - 5} más")
        if report["errors"]:
            lines.append("")
            lines.append(f"=== Problemas detectados ({len(report['errors'])}) ===")
            for e in report["errors"][:10]:
                lines.append(f"  ✗ {os.path.basename(e)}")
            if len(report["errors"]) > 10:
                lines.append(f"  ... y {len(report['errors']) - 10} más")
        if report["warnings"]:
            lines.append("")
            lines.append(f"=== Advertencias ({len(report['warnings'])}) ===")
            for fp, w in report["warnings"][:5]:
                lines.append(f"  ⚠ {os.path.basename(fp)}: {w}")
            if len(report["warnings"]) > 5:
                lines.append(f"  ... y {len(report['warnings']) - 5} más")

        self._report_label.setText("\n".join(lines))
