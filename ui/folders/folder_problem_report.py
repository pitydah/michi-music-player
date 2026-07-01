"""Folder Problem Report — visual table of issues with suggested actions."""

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView,
)

from ui.central.central_styles import glass_button_qss
from library.folder_models import FolderHealth

_SEVERITY_LABELS = {"critical": "Cr\u00edtica", "warning": "Advertencia", "info": "Informativo"}
_ACTION_LABELS = {
    "scan_folder": "Escanear", "open_metadata_editor": "Editar metadata",
    "open_in_file_manager": "Abrir carpeta", "cleanup_missing": "Limpiar",
    "convert_or_ignore": "Convertir", "find_cover": "Buscar car\u00e1tula",
    "review_formats": "Revisar", "add_library_root": "Agregar a biblioteca",
}
_PROBLEM_LABELS = {
    "path_not_found": "No existe", "not_indexed": "No indexado",
    "missing_metadata": "Sin metadata", "missing_cover": "Sin car\u00e1tula",
    "unsupported_audio": "No soportado", "missing_from_db": "Ruta faltante",
    "mixed_formats": "Formatos mixtos", "outside_library": "Fuera de biblioteca",
    "size_mismatch": "Tama\u00f1o cambiado", "mtime_mismatch": "Modificado",
    "permission": "Permiso denegado", "corrupted": "Posible corrupto",
    "unknown": "Desconocido",
}
_SEVERITY_COLORS = {
    "critical": "#F44336", "warning": "#FF9800", "info": "#8FB7FF",
}


def _collect_problems(health: FolderHealth) -> list[dict]:
    """Build a list of problem dicts from FolderHealth."""
    problems = []
    if not health:
        return problems
    if not health.exists:
        problems.append({"loc": os.path.basename(health.path.rstrip("/")) or health.path,
                         "type": "path_not_found", "severity": "critical",
                         "desc": "La carpeta no existe en disco"})
    if health.unindexed_audio_count:
        problems.append({"loc": health.path, "type": "not_indexed", "severity": "warning",
                         "desc": f"{health.unindexed_audio_count} archivos no indexados",
                         "action": "scan_folder"})
    if health.missing_metadata_count:
        problems.append({"loc": health.path, "type": "missing_metadata", "severity": "warning",
                         "desc": f"{health.missing_metadata_count} archivos con metadata incompleta",
                         "action": "open_metadata_editor"})
    if health.missing_cover and health.audio_count:
        problems.append({"loc": health.path, "type": "missing_cover", "severity": "info",
                         "desc": "No se encontr\u00f3 car\u00e1tula local", "action": "find_cover"})
    if health.unsupported_audio_count:
        problems.append({"loc": health.path, "type": "unsupported_audio", "severity": "warning",
                         "desc": f"{health.unsupported_audio_count} archivos no soportados",
                         "action": "convert_or_ignore"})
    if health.missing_db_paths_count:
        problems.append({"loc": health.path, "type": "missing_from_db", "severity": "warning",
                         "desc": f"{health.missing_db_paths_count} rutas en DB no existen en disco",
                         "action": "cleanup_missing"})
    if health.mixed_formats:
        problems.append({"loc": health.path, "type": "mixed_formats", "severity": "info",
                         "desc": f"Formatos: {', '.join(health.formats)}",
                         "action": "review_formats"})
    if not health.is_inside_library_root and not health.is_library_root and health.exists:
        problems.append({"loc": health.path, "type": "outside_library", "severity": "info",
                         "desc": "Esta carpeta no pertenece a la biblioteca",
                         "action": "add_library_root"})
    return problems


def show_problem_report(health: FolderHealth, parent=None):
    """Show a folder problem report dialog. Returns None."""
    dlg = FolderProblemReportDialog(health, parent)
    dlg.exec()


class FolderProblemReportDialog(QDialog):
    def __init__(self, health: FolderHealth, parent=None):
        super().__init__(parent)
        self._health = health
        self._problems = _collect_problems(health)

        self.setWindowTitle(
            f"Problemas \u2014 {os.path.basename(health.path.rstrip('/')) if health else ''}")
        self.setMinimumSize(700, 400)
        self.setStyleSheet("""
            QDialog { background: #181C25; border-radius: 16px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        if health:
            title = QLabel(
                f"Problemas en {os.path.basename(health.path.rstrip('/')) or health.path}")
            title.setStyleSheet("font-size:15px;font-weight:700;color:#fff;")
            layout.addWidget(title)

            score_text = (
                f"Salud: {health.score}/100 \u2014 "
                f"{self._status_label(health.status)}")
            score_lbl = QLabel(score_text)
            score_lbl.setStyleSheet("font-size:12px;color:rgba(255,255,255,0.62);")
            layout.addWidget(score_lbl)
        else:
            title = QLabel("Sin datos de salud")
            title.setStyleSheet("font-size:15px;font-weight:700;color:#fff;")
            layout.addWidget(title)

        if not self._problems:
            empty = QLabel("No se detectaron problemas en esta carpeta.")
            empty.setStyleSheet("font-size:13px;color:rgba(255,255,255,0.68);padding:20px 0;")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
        else:
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(
                ["Severidad", "Tipo", "Archivo/Carpeta", "Descripci\u00f3n", "Acci\u00f3n"])
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
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            header.setSectionResizeMode(3, QHeaderView.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

            table.setRowCount(len(self._problems))
            for row, p in enumerate(self._problems):
                sev = p.get("severity", "info")
                sev_item = QTableWidgetItem(
                    _SEVERITY_LABELS.get(sev, sev.capitalize()))
                sev_item.setForeground(Qt.GlobalColor.white)
                sev_item.setToolTip(f"Severidad: {sev}")
                table.setItem(row, 0, sev_item)

                ptype = _PROBLEM_LABELS.get(p.get("type", ""), p.get("type", ""))
                table.setItem(row, 1, QTableWidgetItem(ptype))

                loc = (os.path.basename(p.get("loc", "").rstrip("/"))
                       or p.get("loc", ""))
                table.setItem(row, 2, QTableWidgetItem(loc))

                table.setItem(row, 3, QTableWidgetItem(p.get("desc", "")))
                action = _ACTION_LABELS.get(p.get("action", ""), "")
                table.setItem(row, 4, QTableWidgetItem(action))

            layout.addWidget(table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(glass_button_qss("secondary"))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _status_label(status: str) -> str:
        labels = {"excellent": "Excelente", "good": "Buena",
                  "attention": "Atenci\u00f3n", "warning": "Advertencia",
                  "critical": "Cr\u00edtica"}
        return labels.get(status, status)
