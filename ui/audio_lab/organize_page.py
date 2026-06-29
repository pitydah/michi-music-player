"""OrganizePage — batch file renaming and library organization.

Uses existing metadata/rename_engine.py for pattern-based renaming
and updates the library DB after file moves.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QFileDialog,
    QScrollArea,     QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressBar, QLineEdit,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_combo_qss,
    glass_progress_qss, glass_input_qss,
)
from metadata.tag_model import TrackTags

logger = logging.getLogger("michi.organize.ui")

_PATTERNS = {
    "Artista - Título": "%artist% - %title%",
    "Artista/Álbum/Nº - Título": "%artist%/%album%/%track% - %title%",
    "Nº - Título": "%track% - %title%",
    "Artista - Álbum - Nº - Título": "%artist% - %album% - %track% - %title%",
    "Álbum/Nº - Título": "%album%/%track% - %title%",
    "Personalizado...": "",
}

AUDIO_EXTS = frozenset({
    ".flac", ".wav", ".mp3", ".ogg", ".opus",
    ".m4a", ".aiff", ".wv", ".ape", ".dsf", ".dff",
})


class OrganizePage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("organizePage")
        self._files: list[str] = []
        self._preview: list[tuple[str, str]] = []
        self._db = None
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

        title = QLabel("Organizar Archivos")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Renombra y reorganiza tu biblioteca usando plantillas. "
            "Los cambios se aplican a los archivos y a la base de datos."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Source selection
        src_card = QFrame()
        src_card.setStyleSheet(glass_card_qss("orgSrcCard"))
        svl = QVBoxLayout(src_card)
        svl.setContentsMargins(20, 16, 20, 16)
        svl.setSpacing(10)

        sl = QLabel("Archivos a organizar")
        sl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        svl.addWidget(sl)

        btn_row = QHBoxLayout()
        self._folder_btn = QPushButton("Seleccionar carpeta...")
        self._folder_btn.setCursor(Qt.PointingHandCursor)
        self._folder_btn.setStyleSheet(glass_button_qss("secondary"))
        self._folder_btn.clicked.connect(self._select_folder)
        btn_row.addWidget(self._folder_btn)

        self._file_count = QLabel("0 archivos")
        self._file_count.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent;"
        )
        btn_row.addWidget(self._file_count)
        btn_row.addStretch()
        svl.addLayout(btn_row)

        cl.addWidget(src_card)

        # Pattern selection
        pat_card = QFrame()
        pat_card.setStyleSheet(glass_card_qss("orgPatCard"))
        pvl = QVBoxLayout(pat_card)
        pvl.setContentsMargins(20, 16, 20, 16)
        pvl.setSpacing(10)

        pl = QLabel("Plantilla de renombrado")
        pl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        pvl.addWidget(pl)

        p_row = QHBoxLayout()
        self._pattern_combo = QComboBox()
        self._pattern_combo.setStyleSheet(glass_combo_qss())
        self._pattern_combo.setMinimumWidth(300)
        for name in _PATTERNS:
            self._pattern_combo.addItem(name)
        self._pattern_combo.currentIndexChanged.connect(self._on_pattern_changed)
        p_row.addWidget(self._pattern_combo)

        self._pattern_edit = QLineEdit()
        self._pattern_edit.setStyleSheet(glass_input_qss())
        self._pattern_edit.setPlaceholderText("%artist%/%album%/%track% - %title%")
        self._pattern_edit.setText(_PATTERNS["Artista - Título"])
        p_row.addWidget(self._pattern_edit, 1)
        pvl.addLayout(p_row)

        hint = QLabel(
            "Variables disponibles: %artist%, %album%, %track%, %title%, "
            "%genre%, %year%, %albumartist%"
        )
        hint.setStyleSheet(
            "color: rgba(255,255,255,0.42); font-size: 11px; "
            "background: transparent;"
        )
        pvl.addWidget(hint)
        cl.addWidget(pat_card)

        # Preview
        prev_card = QFrame()
        prev_card.setStyleSheet(glass_card_qss("orgPrevCard"))
        prev_vl = QVBoxLayout(prev_card)
        prev_vl.setContentsMargins(20, 16, 20, 16)
        prev_vl.setSpacing(10)

        prev_header = QHBoxLayout()
        prevl = QLabel("Vista previa")
        prevl.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        prev_header.addWidget(prevl)

        self._preview_btn = QPushButton("Generar vista previa")
        self._preview_btn.setCursor(Qt.PointingHandCursor)
        self._preview_btn.setStyleSheet(glass_button_qss("primary"))
        self._preview_btn.clicked.connect(self._generate_preview)
        prev_header.addWidget(self._preview_btn)
        prev_header.addStretch()
        prev_vl.addLayout(prev_header)

        self._preview_table = QTableWidget()
        self._preview_table.setColumnCount(3)
        self._preview_table.setHorizontalHeaderLabels(
            ["Nº", "Ruta actual", "Nueva ruta"]
        )
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._preview_table.setStyleSheet(
            "QTableWidget { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.72); "
            "font-size: 11px; gridline-color: rgba(255,255,255,0.03); }"
            "QHeaderView::section { background: rgba(255,255,255,0.03); "
            "color: rgba(255,255,255,0.56); border: none; "
            "padding: 4px; font-size: 10px; }"
        )
        self._preview_table.setMinimumHeight(200)
        prev_vl.addWidget(self._preview_table)

        cl.addWidget(prev_card)

        # Apply
        apply_row = QHBoxLayout()
        self._apply_btn = QPushButton("Aplicar cambios")
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.setStyleSheet(glass_button_qss("primary"))
        self._apply_btn.clicked.connect(self._apply_changes)
        self._apply_btn.setEnabled(False)
        apply_row.addWidget(self._apply_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(glass_progress_qss())
        apply_row.addWidget(self._progress, 1)

        apply_row.addStretch()
        cl.addLayout(apply_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent;"
        )
        cl.addWidget(self._status_label)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta con archivos de audio"
        )
        if not folder:
            return

        self._files.clear()
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in AUDIO_EXTS:
                    self._files.append(os.path.join(root, f))

        self._files.sort()
        self._file_count.setText(f"{len(self._files)} archivos")
        self._status_label.setText(
            f"{len(self._files)} archivos encontrados en {folder}"
        )
        self._preview.clear()
        self._preview_table.setRowCount(0)
        self._apply_btn.setEnabled(False)

    def _on_pattern_changed(self, idx):
        name = self._pattern_combo.currentText()
        if name in _PATTERNS:
            self._pattern_edit.setText(_PATTERNS[name])

    def _get_pattern(self) -> str:
        return self._pattern_edit.text().strip()

    def _generate_preview(self):
        if not self._files:
            self._status_label.setText("Selecciona una carpeta primero.")
            return

        pattern = self._get_pattern()
        if not pattern:
            self._status_label.setText("Introduce una plantilla de renombrado.")
            return

        from metadata.rename_engine import preview_rename
        from metadata.tag_reader import read_tags

        tags_list = []
        errors = 0
        for fp in self._files:
            try:
                tags = read_tags(fp)
                tags_list.append(tags)
            except Exception:
                errors += 1
                dummy = TrackTags(filepath=fp)
                dummy.title = os.path.splitext(os.path.basename(fp))[0]
                tags_list.append(dummy)

        self._preview = preview_rename(tags_list, pattern)
        self._preview_table.setRowCount(len(self._preview))

        changed = 0
        for i, (old_p, new_p) in enumerate(self._preview):
            self._preview_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            short_old = old_p if len(old_p) < 80 else f"...{old_p[-77:]}"
            short_new = new_p if len(new_p) < 80 else f"...{new_p[-77:]}"
            self._preview_table.setItem(i, 1, QTableWidgetItem(short_old))
            self._preview_table.setItem(i, 2, QTableWidgetItem(short_new))
            if old_p != new_p:
                changed += 1

        self._preview_table.resizeColumnsToContents()
        self._preview_table.setColumnWidth(0, 40)
        self._apply_btn.setEnabled(changed > 0)

        status = f"Vista previa: {len(self._preview)} archivos"
        if changed:
            status += f", {changed} cambiarán"
        if errors:
            status += f", {errors} con errores de lectura"
        self._status_label.setText(status)

    def _apply_changes(self):
        if not self._preview:
            return

        from metadata.rename_engine import apply_rename

        changes = [(o, n) for o, n in self._preview if o != n]
        if not changes:
            return

        reply = QMessageBox.question(
            self, "Confirmar cambios",
            f"¿Renombrar y reorganizar {len(changes)} archivo(s)?\n\n"
            "Esta operación moverá archivos en tu disco y "
            "actualizará la base de datos.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._apply_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)

        ok_count, fail_count = apply_rename(changes)
        self._progress.setValue(50)

        # Update DB
        db_ok = 0
        db_fail = 0
        if self._db is None:
            try:
                from library.library_db import LibraryDB, DB_PATH
                self._db = LibraryDB(DB_PATH)
            except Exception:
                pass

        if self._db:
            for old_p, new_p in changes:
                if self._db.update_filepath(old_p, new_p):
                    db_ok += 1
                else:
                    db_fail += 1

        self._progress.setValue(100)

        msg = f"Renombrados: {ok_count} OK, {fail_count} errores"
        if db_ok:
            msg += f" | DB actualizada: {db_ok} registros"
        if db_fail:
            msg += f" | DB fallos: {db_fail}"
        self._status_label.setText(msg)

        logger.info("Organize completed: %s", msg)
        self._preview.clear()
        self._preview_table.setRowCount(0)
        self._apply_btn.setEnabled(False)
