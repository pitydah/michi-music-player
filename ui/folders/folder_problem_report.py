"""Folder Problem Report — table of issues found in a folder with suggested actions."""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView,
)

from ui.central.central_styles import glass_button_qss

_SEVERITY_COLORS = {
    "critical": "#F44336",
    "warning": "#FF9800",
    "info": "#8FB7FF",
}

_ACTION_LABELS = {
    "scan_folder": "Escanear",
    "open_metadata_editor": "Editar metadata",
    "open_in_file_manager": "Abrir carpeta",
    "cleanup_missing": "Limpiar",
    "convert_or_ignore": "Convertir",
    "find_cover": "Buscar carátula",
    "review_formats": "Revisar",
    "add_library_root": "Agregar a biblioteca",
}


class FolderProblemReportDialog(QDialog):
    action_requested = Signal(str, object)  # action, FolderProblem

    def __init__(self, health, parent=None):
        super().__init__(parent)
        self._health = health
        self._problems = self._collect_problems(health)

        self.setWindowTitle(f"Problemas — {health and health.path or ''}")
        self.setMinimumSize(700, 400)
        self.setStyleSheet("""
            QDialog {
                background: #181C25;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"Problemas encontrados en {health and health.path or ''}" if health
                       else "Sin datos de salud")
        title.setStyleSheet("font-size:15px;font-weight:700;color:#fff;")
        layout.addWidget(title)

        if health:
            score_text = f"Salud: {health.score}/100 — {self._status_label(health.status)}"
            score_lbl = QLabel(score_text)
            score_lbl.setStyleSheet("font-size:12px;color:rgba(255,255,255,0.62);")
            layout.addWidget(score_lbl)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Archivo/Carpeta", "Problema", "Severidad", "Descripción", "Acción"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background: rgba(255,255,255,0.025);
                alternate-background-color: rgba(255,255,255,0.014);
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.065);
                border-radius: 12px;
                outline: none;
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.035);
                color: rgba(255,255,255,0.78);
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding: 8px 10px;
                font-size: 11.5px;
                font-weight: 700;
            }
            QTableWidget::item {
                padding: 6px 10px;
                color: rgba(255,255,255,0.82);
            }
        """)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        problems = self._collect_table_problems()
        table.setRowCount(len(problems))
        for row, (loc, ptype, sev, desc, action) in enumerate(problems):
            table.setItem(row, 0, QTableWidgetItem(loc))
            table.setItem(row, 1, QTableWidgetItem(ptype))
            sev_item = QTableWidgetItem(sev)
            sev_item.setForeground(Qt.GlobalColor.white)
            sev_item.setToolTip(f"Severidad: {sev}")
            table.setItem(row, 2, sev_item)
            table.setItem(row, 3, QTableWidgetItem(desc))
            table.setItem(row, 4, QTableWidgetItem(action))

        layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(glass_button_qss("secondary"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _collect_problems(self, health):
        """Build list of FolderProblem from health data."""
        from library.folder_models import FolderProblem
        problems = []
        if not health:
            return problems
        if not health.exists:
            problems.append(FolderProblem(
                path=health.path, problem_type="path_not_found",
                severity="critical", description="La carpeta no existe",
                suggested_action="open_in_file_manager"))
        if health.unindexed_audio_count:
            problems.append(FolderProblem(
                path=health.path, problem_type="not_indexed",
                severity="warning",
                description=f"{health.unindexed_audio_count} archivos sin indexar",
                suggested_action="scan_folder", file_count=health.unindexed_audio_count))
        if health.missing_metadata_count:
            problems.append(FolderProblem(
                path=health.path, problem_type="missing_metadata",
                severity="warning",
                description=f"{health.missing_metadata_count} archivos con metadata incompleta",
                suggested_action="open_metadata_editor", file_count=health.missing_metadata_count))
        if health.missing_cover and health.audio_count:
            problems.append(FolderProblem(
                path=health.path, problem_type="missing_cover",
                severity="info", description="No hay carátula local en esta carpeta",
                suggested_action="find_cover"))
        if health.unsupported_audio_count:
            problems.append(FolderProblem(
                path=health.path, problem_type="unsupported_audio",
                severity="warning",
                description=f"{health.unsupported_audio_count} archivos no soportados",
                suggested_action="convert_or_ignore", file_count=health.unsupported_audio_count))
        if health.missing_db_paths_count:
            problems.append(FolderProblem(
                path=health.path, problem_type="missing_from_db",
                severity="warning",
                description=f"{health.missing_db_paths_count} rutas en DB no existen en disco",
                suggested_action="cleanup_missing", file_count=health.missing_db_paths_count))
        if health.mixed_formats:
            problems.append(FolderProblem(
                path=health.path, problem_type="mixed_formats",
                severity="info",
                description=f"Formatos mezclados: {', '.join(health.formats)}",
                suggested_action="review_formats"))
        if not health.is_inside_library_root and not health.is_library_root and health.exists:
            problems.append(FolderProblem(
                path=health.path, problem_type="outside_library",
                severity="info", description="Fuera de la biblioteca",
                suggested_action="add_library_root"))
        return problems

    def _collect_table_problems(self):
        rows = []
        for p in self._problems:
            ptype = self._problem_label(p.problem_type)
            action = _ACTION_LABELS.get(p.suggested_action, p.suggested_action or "")
            rows.append((
                os.path.basename(p.path.rstrip("/")) or p.path,
                ptype,
                p.severity.capitalize(),
                p.description,
                action,
            ))
        return rows

    @staticmethod
    def _status_label(status: str) -> str:
        labels = {"excellent": "Excelente", "good": "Buena",
                  "attention": "Atención", "warning": "Advertencia",
                  "critical": "Crítica"}
        return labels.get(status, status)

    @staticmethod
    def _problem_label(ptype: str) -> str:
        labels = {
            "path_not_found": "No existe",
            "not_indexed": "No indexado",
            "missing_metadata": "Sin metadata",
            "missing_cover": "Sin carátula",
            "unsupported_audio": "No soportado",
            "missing_from_db": "Ruta faltante",
            "mixed_formats": "Formatos mixtos",
            "outside_library": "Fuera de biblioteca",
            "size_mismatch": "Tamaño cambiado",
            "mtime_mismatch": "Modificado",
            "permission": "Permiso denegado",
            "corrupted": "Posible corrupto",
        }
        return labels.get(ptype, ptype.replace("_", " ").capitalize())


def show_problem_report(health, parent=None):
    """Create and show a FolderProblemReportDialog."""
    dlg = FolderProblemReportDialog(health, parent)
    dlg.exec()
