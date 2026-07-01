"""GenreOperationPreviewDialog — preview and confirmation for genre operations.

Shows affected tracks count, source/target info, and write_tags checkbox.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCheckBox, QFrame, QDialogButtonBox,
)

_BG = "#090B11"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"
_WARN = "#FFB347"


class GenreOperationPreviewDialog(QDialog):
    def __init__(self, op_type: str, sources: list[str], target: str,
                 track_count: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirmar operación")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background: {_BG}; border-radius: 14px; }}
        """)

        self._write_tags = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Confirmar operación")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {_TEXT}; background: transparent;")
        layout.addWidget(title)

        op_frame = QFrame()
        op_frame.setStyleSheet(
            "background: rgba(255,255,255,0.03); border-radius: 10px;"
            "border: 1px solid rgba(255,255,255,0.06);")
        op_layout = QVBoxLayout(op_frame)
        op_layout.setContentsMargins(16, 12, 16, 12)
        op_layout.setSpacing(6)

        op_name = QLabel(f"Operación: {op_type}")
        op_name.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {_ACCENT};")
        op_layout.addWidget(op_name)

        if sources:
            src_str = ", ".join(sources[:5])
            if len(sources) > 5:
                src_str += f" y {len(sources) - 5} más"
            src_lbl = QLabel(f"Origen: {src_str}")
            src_lbl.setStyleSheet(f"font-size: 12px; color: {_TEXT2};")
            src_lbl.setWordWrap(True)
            op_layout.addWidget(src_lbl)

        tgt_lbl = QLabel(f"Destino: {target}")
        tgt_lbl.setStyleSheet(f"font-size: 12px; color: {_TEXT2};")
        op_layout.addWidget(tgt_lbl)

        if track_count:
            cnt_lbl = QLabel(f"Afectará: {track_count} canciones")
            cnt_lbl.setStyleSheet(f"font-size: 12px; color: {_WARN}; font-weight: 600;")
            op_layout.addWidget(cnt_lbl)

        layout.addWidget(op_frame)

        mode_frame = QFrame()
        mode_frame.setStyleSheet(
            "background: rgba(255,255,255,0.03); border-radius: 10px;"
            "border: 1px solid rgba(255,255,255,0.06);")
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(16, 12, 16, 12)
        mode_layout.setSpacing(6)

        db_lbl = QLabel("Solo base de datos Michi")
        db_lbl.setStyleSheet(f"font-size: 12px; color: {_TEXT3};")
        mode_layout.addWidget(db_lbl)

        self._write_cb = QCheckBox("Escribir también en archivos físicos")
        self._write_cb.setStyleSheet(f"""
            QCheckBox {{ color: {_TEXT2}; font-size: 11px; spacing: 8px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;
              border: 1px solid rgba(255,255,255,0.2); background: transparent; }}
            QCheckBox::indicator:checked {{ background: {_ACCENT}; border: 1px solid {_ACCENT}; }}
        """)
        self._write_cb.stateChanged.connect(
            lambda s: setattr(self, '_write_tags', bool(s)))
        mode_layout.addWidget(self._write_cb)

        warn_lbl = QLabel(
            "Esta operación modificará etiquetas de archivos de audio. "
            "Se recomienda respaldo.")
        warn_lbl.setStyleSheet(f"font-size: 10px; color: {_WARN};")
        warn_lbl.setWordWrap(True)
        mode_layout.addWidget(warn_lbl)

        layout.addWidget(mode_frame)

        buttons = QDialogButtonBox()
        buttons.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,255,255,0.05); color: {_TEXT2};
              border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
              padding: 8px 20px; font-size: 12px; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.08); }}
        """)
        cancel_btn = buttons.addButton("Cancelar", QDialogButtonBox.RejectRole)
        apply_btn = buttons.addButton("Aplicar", QDialogButtonBox.AcceptRole)
        apply_btn.setStyleSheet(f"""
            QPushButton {{ background: {_ACCENT}; color: #090B11;
              border: none; border-radius: 8px;
              padding: 8px 20px; font-size: 12px; font-weight: 700; }}
            QPushButton:hover {{ background: rgba(143,183,255,0.80); }}
        """)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    @property
    def write_tags(self) -> bool:
        return self._write_tags
