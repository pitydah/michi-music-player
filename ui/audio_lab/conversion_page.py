"""ConversionPage — batch audio format converter using EncoderService."""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QFileDialog,
    QScrollArea,     QListWidget,
    QProgressBar, QCheckBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_combo_qss,
    glass_progress_qss,
)

logger = logging.getLogger("michi.conversion.ui")

AUDIO_EXTS = (".flac", ".wav", ".mp3", ".ogg", ".opus", ".m4a", ".aiff", ".wv")


class ConversionPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("conversionPage")
        self._files: list[str] = []
        self._encoder = None
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

        title = QLabel("Convertir Formatos")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Convierte archivos de audio entre formatos preservando "
            "metadatos. Los originales no se modifican."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        # Source selection
        src_card = QFrame()
        src_card.setStyleSheet(glass_card_qss("convSrcCard"))
        src_layout = QVBoxLayout(src_card)
        src_layout.setContentsMargins(20, 16, 20, 16)
        src_layout.setSpacing(10)

        src_label = QLabel("Archivos fuente")
        src_label.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent;"
        )
        src_layout.addWidget(src_label)

        btn_row = QHBoxLayout()
        self._add_files_btn = QPushButton("Agregar archivos...")
        self._add_files_btn.setCursor(Qt.PointingHandCursor)
        self._add_files_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_files_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self._add_files_btn)

        self._add_folder_btn = QPushButton("Agregar carpeta...")
        self._add_folder_btn.setCursor(Qt.PointingHandCursor)
        self._add_folder_btn.setStyleSheet(glass_button_qss("secondary"))
        self._add_folder_btn.clicked.connect(self._add_folder)
        btn_row.addWidget(self._add_folder_btn)

        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(glass_button_qss("ghost"))
        self._clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        src_layout.addLayout(btn_row)

        self._file_list = QListWidget()
        self._file_list.setStyleSheet(
            "QListWidget { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 8px; color: rgba(255,255,255,0.72); "
            "font-size: 11px; min-height: 120px; }"
        )
        src_layout.addWidget(self._file_list)
        cl.addWidget(src_card)

        # Format selection
        fmt_card = QFrame()
        fmt_card.setStyleSheet(glass_card_qss("convFmtCard"))
        fmt_layout = QHBoxLayout(fmt_card)
        fmt_layout.setContentsMargins(20, 16, 20, 16)
        fmt_layout.setSpacing(12)

        fmt_layout.addWidget(QLabel("Convertir a:"))
        self._target_combo = QComboBox()
        self._target_combo.setStyleSheet(glass_combo_qss())
        self._target_combo.addItem("FLAC (lossless)", "flac")
        self._target_combo.addItem("MP3 320 kbps", "mp3")
        self._target_combo.addItem("Opus 192 kbps", "opus")
        self._target_combo.addItem("ALAC (Apple Lossless)", "alac")
        self._target_combo.addItem("WAV (sin compresión)", "wav")
        fmt_layout.addWidget(self._target_combo)

        fmt_layout.addWidget(QLabel("Destino:"))
        self._dest_btn = QPushButton("Seleccionar carpeta...")
        self._dest_btn.setCursor(Qt.PointingHandCursor)
        self._dest_btn.setStyleSheet(glass_button_qss("secondary"))
        self._dest_btn.clicked.connect(self._select_dest)
        fmt_layout.addWidget(self._dest_btn)

        self._keep_org = QCheckBox("Conservar originales")
        self._keep_org.setChecked(True)
        self._keep_org.setStyleSheet(
            "color: rgba(255,255,255,0.72); font-size: 12px; "
            "background: transparent;"
        )
        fmt_layout.addWidget(self._keep_org)
        fmt_layout.addStretch()
        cl.addWidget(fmt_card)

        # Convert button + progress
        self._convert_btn = QPushButton("Iniciar conversión")
        self._convert_btn.setCursor(Qt.PointingHandCursor)
        self._convert_btn.setStyleSheet(glass_button_qss("primary"))
        self._convert_btn.clicked.connect(self._start_conversion)
        cl.addWidget(self._convert_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setStyleSheet(glass_progress_qss())
        cl.addWidget(self._progress)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 12px; "
            "background: transparent;"
        )
        cl.addWidget(self._status_label)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivos de audio", "",
            "Audio (*.flac *.wav *.mp3 *.ogg *.opus *.m4a *.aiff *.wv)"
        )
        for f in files:
            if f not in self._files:
                self._files.append(f)
                self._file_list.addItem(os.path.basename(f))
        self._update_status()

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if not folder:
            return
        added = 0
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(AUDIO_EXTS):
                    fp = os.path.join(root, f)
                    if fp not in self._files:
                        self._files.append(fp)
                        self._file_list.addItem(os.path.relpath(fp, folder))
                        added += 1
        if added == 0:
            self._status_label.setText("No se encontraron archivos de audio.")
        else:
            self._update_status()

    def _clear_files(self):
        self._files.clear()
        self._file_list.clear()
        self._update_status()

    def _select_dest(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar destino")
        if d:
            self._dest = d
            self._dest_btn.setText(f"Destino: {os.path.basename(d)}")

    def _update_status(self):
        self._status_label.setText(
            f"{len(self._files)} archivo(s) seleccionado(s)"
        )

    def _start_conversion(self):
        if not self._files:
            self._status_label.setText("Selecciona archivos primero.")
            return

        target = self._target_combo.currentData()
        dest = getattr(self, '_dest', None)
        if not dest:
            dest = os.path.dirname(self._files[0])
            self._dest = dest

        if not self._encoder:
            from ui.audio_lab.services.encoder_service import EncoderService
            self._encoder = EncoderService()
            self._encoder.encode_finished.connect(self._on_encode_finished)
            self._encoder.encode_error.connect(self._on_encode_error)

        self._convert_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._total = len(self._files)
        self._done = 0
        self._status_label.setText(f"Convirtiendo 0/{self._total}...")

        for fp in self._files:
            base = os.path.splitext(os.path.basename(fp))[0]
            out = os.path.join(dest, f"{base}.{target}")
            if target == "flac":
                self._encoder.encode_to_flac(fp, out)
            elif target == "mp3":
                self._encoder.encode_to_mp3(fp, out, 320)
            elif target == "opus":
                self._encoder.encode_to_opus(fp, out, 192)
            elif target == "alac":
                self._encoder.encode_to_alac(fp, out)
            elif target == "wav":
                import shutil
                shutil.copy2(fp, out)
                self._on_encode_finished(fp, out)

    def _on_encode_finished(self, input_path: str, output_path: str):
        self._done += 1
        pct = int(self._done / self._total * 100)
        self._progress.setValue(pct)
        self._status_label.setText(
            f"Convertidos {self._done}/{self._total}: "
            f"{os.path.basename(output_path)}"
        )
        if self._done >= self._total:
            self._convert_btn.setEnabled(True)
            self._status_label.setText(
                f"Conversión completada: {self._done} archivos."
            )

    def _on_encode_error(self, input_path: str, error: str):
        self._done += 1
        logger.warning("Conversion error for %s: %s", input_path, error)
        self._status_label.setText(
            f"Error en {os.path.basename(input_path)}: {error}"
        )
        if self._done >= self._total:
            self._convert_btn.setEnabled(True)
