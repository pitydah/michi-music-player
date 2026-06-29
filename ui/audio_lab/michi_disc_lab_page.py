"""MichiDiscLabPage — CD ripping, encoding, and import interface with real cdparanoia."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar,
    QScrollArea, QFileDialog,
)

from ui.audio_lab.models import RIP_PROFILES, EXTRACTION_MODES
from ui.audio_lab.services.external_tools import check_all_tools
from ui.audio_lab.services.disc_detection_service import DiscDetectionService
from ui.audio_lab.services.rip_job_manager import RipJobManager
from ui.audio_lab.services.encoder_service import EncoderService
from ui.central.central_styles import (
    glass_button_qss, glass_progress_qss, glass_card_qss,
    clean_table_qss, clean_table_header_qss, combo_dropdown_qss,
)


class MichiDiscLabPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("michiDiscLabPage")
        self._tools = check_all_tools()
        self._detection = DiscDetectionService()
        self._rip_manager = RipJobManager(self)
        self._encoder = EncoderService(self)
        self._current_job_id: str = ""
        self._destination: str = ""
        self._iso_mode: bool = False
        self._build_ui()
        self._wire_signals()
        self._update_diagnostics()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("discLabScroll")

        content = QWidget()
        content.setObjectName("discLabContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        title = QLabel("Michi Disc Lab")
        title.setObjectName("discLabTitle")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "Importación Hi-Fi, ripeo seguro y conversión inteligente "
            "de discos de música."
        )
        subtitle.setObjectName("discLabSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        content_layout.addWidget(self._build_drive_panel())
        content_layout.addWidget(self._build_track_table())
        content_layout.addWidget(self._build_settings_panel())
        content_layout.addWidget(self._build_progress_panel())
        content_layout.addWidget(self._build_diagnostics_panel())
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

    def _wire_signals(self):
        self._rip_manager.track_started.connect(self._on_track_started)
        self._rip_manager.track_finished.connect(self._on_track_finished)
        self._rip_manager.progress_changed.connect(self._on_progress)
        self._rip_manager.job_finished.connect(self._on_job_finished)
        self._rip_manager.error_occurred.connect(self._on_rip_error)

    def _build_drive_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("discLabDrivePanel")
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(16, 12, 16, 12)
        p_layout.setSpacing(8)

        self._drive_status = QLabel("Esperando disco de música...")
        self._drive_status.setObjectName("driveStatus")
        p_layout.addWidget(self._drive_status)

        btn_row = QHBoxLayout()
        self._scan_drive_btn = QPushButton("Buscar unidad óptica")
        self._scan_drive_btn.setObjectName("scanDriveBtn")
        self._scan_drive_btn.setCursor(Qt.PointingHandCursor)
        self._scan_drive_btn.clicked.connect(self._on_scan_drive)
        btn_row.addWidget(self._scan_drive_btn)

        self._analyze_disc_btn = QPushButton("Analizar disco")
        self._analyze_disc_btn.setObjectName("analyzeDiscBtn")
        self._analyze_disc_btn.setCursor(Qt.PointingHandCursor)
        self._analyze_disc_btn.setEnabled(False)
        self._analyze_disc_btn.clicked.connect(self._on_analyze_disc)
        btn_row.addWidget(self._analyze_disc_btn)

        self._iso_toggle_btn = QPushButton("Usar ISO")
        self._iso_toggle_btn.setObjectName("isoToggleBtn")
        self._iso_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._iso_toggle_btn.clicked.connect(self._on_toggle_iso)
        btn_row.addWidget(self._iso_toggle_btn)

        self._iso_select_btn = QPushButton("Seleccionar ISO")
        self._iso_select_btn.setObjectName("isoSelectBtn")
        self._iso_select_btn.setCursor(Qt.PointingHandCursor)
        self._iso_select_btn.setVisible(False)
        self._iso_select_btn.clicked.connect(self._on_select_iso)
        btn_row.addWidget(self._iso_select_btn)

        btn_row.addStretch()
        p_layout.addLayout(btn_row)

        return panel

    def _build_track_table(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("discLabTrackPanel")
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(16, 12, 16, 12)

        self._track_table = QTableWidget()
        self._track_table.setObjectName("discLabTable")
        self._track_table.horizontalHeader().setObjectName("discLabTableHeader")
        self._track_table.setColumnCount(5)
        self._track_table.setHorizontalHeaderLabels(
            ["#", "Título", "Artista", "Duración", "Estado"]
        )
        self._track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._track_table.setSelectionBehavior(QTableWidget.SelectRows)
        p_layout.addWidget(self._track_table)

        return panel

    def _build_settings_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("discLabSettingsPanel")
        p_layout = QHBoxLayout(panel)
        p_layout.setContentsMargins(16, 12, 16, 12)
        p_layout.setSpacing(12)

        profile_label = QLabel("Perfil:")
        profile_label.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 12px;")
        p_layout.addWidget(profile_label)

        self._profile_combo = QComboBox()
        self._profile_data: list[str] = []
        for p in RIP_PROFILES:
            if p.available:
                idx = self._profile_combo.addItem(p.name)
                self._profile_data.append(p.format)
            else:
                self._profile_combo.addItem(f"{p.name} (próximamente)")
        self._profile_combo.setCurrentIndex(0)

        mode_label = QLabel("Modo:")
        mode_label.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 12px;")
        p_layout.addWidget(mode_label)

        self._mode_combo = QComboBox()
        for value, text, _desc in EXTRACTION_MODES:
            self._mode_combo.addItem(text, value)
        p_layout.addWidget(self._mode_combo)

        dest_label = QLabel("Destino:")
        dest_label.setStyleSheet("color: rgba(255,255,255,0.62); font-size: 12px;")
        p_layout.addWidget(dest_label)

        self._dest_btn = QPushButton("Seleccionar carpeta...")
        self._dest_btn.setObjectName("destBtn")
        self._dest_btn.setCursor(Qt.PointingHandCursor)
        self._dest_btn.clicked.connect(self._on_select_destination)
        p_layout.addWidget(self._dest_btn)

        p_layout.addStretch()

        self._import_btn = QPushButton("Importar disco")
        self._import_btn.setObjectName("importBtn")
        self._import_btn.setCursor(Qt.PointingHandCursor)
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._on_import_disc)
        p_layout.addWidget(self._import_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setObjectName("cancelRipBtn")
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel_rip)
        p_layout.addWidget(self._cancel_btn)

        return panel

    def _build_progress_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("discLabProgressPanel")
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(16, 8, 16, 12)

        self._progress = QProgressBar()
        self._progress.setObjectName("discLabProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        p_layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("discLabProgressLabel")
        self._progress_label.setVisible(False)
        p_layout.addWidget(self._progress_label)

        return panel

    def _build_diagnostics_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("discLabDiagPanel")
        p_layout = QVBoxLayout(panel)
        p_layout.setContentsMargins(16, 8, 16, 12)

        diag_title = QLabel("Diagnóstico de herramientas externas")
        diag_title.setObjectName("diagTitle")
        p_layout.addWidget(diag_title)

        self._diag_text = QLabel("")
        self._diag_text.setObjectName("diagText")
        self._diag_text.setWordWrap(True)
        p_layout.addWidget(self._diag_text)

        return panel

    def _update_diagnostics(self):
        lines = []
        for name, tool in self._tools.items():
            icon = "+" if tool.available else "-"
            note = ""
            if not tool.available and tool.recommended_for:
                note = f" ({tool.recommended_for} no disponible)"
            lines.append(f"{icon} {name}: {'Disponible' if tool.available else 'No instalado'}{note}")
        self._diag_text.setText("\n".join(lines))

    def _on_scan_drive(self):
        if self._iso_mode:
            self._on_select_iso()
            return
        drives = self._detection.detect_drives()
        if drives:
            self._current_drive = drives[0]
            self._drive_status.setText(f"Unidad detectada: {self._current_drive}")
            self._analyze_disc_btn.setEnabled(True)
        else:
            self._drive_status.setText(
                "No se detectaron unidades ópticas. "
                "Conecta una unidad de CD/DVD/Blu-ray."
            )
            self._scan_drive_btn.setText("Reintentar")
            self._analyze_disc_btn.setEnabled(False)

    def _on_toggle_iso(self):
        self._iso_mode = not self._iso_mode
        if self._iso_mode:
            self._detection.unmount_iso()
            self._iso_toggle_btn.setText("Usar unidad")
            self._scan_drive_btn.setVisible(False)
            self._iso_select_btn.setVisible(True)
            self._drive_status.setText("Selecciona un archivo ISO de CD de audio.")
            self._analyze_disc_btn.setEnabled(False)
        else:
            self._iso_mode = False
            self._iso_toggle_btn.setText("Usar ISO")
            self._scan_drive_btn.setVisible(True)
            self._iso_select_btn.setVisible(False)
            self._drive_status.setText("Esperando disco de música...")
            self._analyze_disc_btn.setEnabled(False)

    def _on_select_iso(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar imagen ISO", "",
            "Imágenes ISO (*.iso);;Imágenes de disco (*.iso *.bin *.cue);;Todos los archivos (*)",
        )
        if not path:
            return
        loop = self._detection.mount_iso(path)
        if loop:
            self._current_drive = loop
            self._iso_select_btn.setText(os.path.basename(path))
            self._drive_status.setText(f"ISO montado: {os.path.basename(path)} → {loop}")
            self._analyze_disc_btn.setEnabled(True)
        else:
            self._drive_status.setText(
                "No se pudo montar el ISO. Verifica que udisksctl esté instalado."
            )

    def _on_analyze_disc(self):
        drive = getattr(self, '_current_drive', '') or self._detection.get_default_drive()
        if not drive:
            self._drive_status.setText("No hay unidad o ISO seleccionado.")
            return

        has_cd = self._detection.detect_audio_cd(drive)
        if not has_cd:
            if self._iso_mode:
                self._drive_status.setText("No se pudo leer la tabla de contenido del ISO.")
            else:
                self._drive_status.setText(
                    f"No se detectó un CD de audio en {drive}. "
                    "Inserta un disco de música y reintenta."
                )
            self._import_btn.setEnabled(False)
            self._populate_tracks([])
            return

        toc = self._detection.get_disc_toc(drive)
        src = self._detection.current_source_name
        self._drive_status.setText(
            f"Disco detectado: {toc.get('tracks', 0)} pistas, "
            f"{self._fmt_duration(toc.get('duration_seconds', 0))}"
            + (f" ({src})" if src else "")
        )
        self._import_btn.setEnabled(True)
        self._populate_tracks(toc.get("track_list", []))

    def _populate_tracks(self, track_list: list[dict]):
        self._track_table.setRowCount(len(track_list))
        for i, track in enumerate(track_list):
            self._track_table.setItem(i, 0, QTableWidgetItem(str(track.get("number", i + 1))))
            self._track_table.setItem(i, 1, QTableWidgetItem(f"Pista {track.get('number', i + 1)}"))
            self._track_table.setItem(i, 2, QTableWidgetItem("Desconocido"))
            dur = track.get("duration") or 0
            m = int(dur // 60)
            s = int(dur % 60)
            self._track_table.setItem(i, 3, QTableWidgetItem(f"{m}:{s:02d}"))
            self._track_table.setItem(i, 4, QTableWidgetItem("Pendiente"))

    def _on_import_disc(self):
        drive = getattr(self, '_current_drive', '') or self._detection.get_default_drive()
        if not self._destination:
            self._drive_status.setText("Selecciona una carpeta de destino primero.")
            return

        profile_idx = self._profile_combo.currentIndex()
        profile_name = (self._profile_data[profile_idx]
                        if 0 <= profile_idx < len(self._profile_data)
                        else "wav")
        mode_value = self._mode_combo.currentData() or "fast"

        job = self._rip_manager.create_job(
            drive=drive, profile=profile_name,
            destination=self._destination,
            extraction_mode=mode_value,
        )
        self._current_job_id = job.id

        self._import_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress.setValue(0)
        self._progress_label.setText("Iniciando ripeo...")

        self._rip_manager.start_job(job.id)

    def _on_cancel_rip(self):
        if self._current_job_id:
            self._rip_manager.cancel_job(self._current_job_id)
        self._progress_label.setText("Cancelado")
        self._import_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._current_job_id = ""

    def _on_select_destination(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de destino",
        )
        if folder:
            self._destination = folder
            self._dest_btn.setText(folder)

    def _on_track_started(self, job_id: str, track_num: int, total: int):
        self._progress_label.setText(f"Ripeando pista {track_num} de {total}...")
        if 0 < track_num <= self._track_table.rowCount():
            self._track_table.setItem(track_num - 1, 4, QTableWidgetItem("Ripeando..."))

    def _on_track_finished(self, job_id: str, track_num: int, output_path: str):
        if 0 < track_num <= self._track_table.rowCount():
            self._track_table.setItem(track_num - 1, 4, QTableWidgetItem("Completado"))
        self._progress_label.setText(f"Pista {track_num} completada.")

    def _on_progress(self, job_id: str, track_num: int, progress: float, status: str):
        self._progress.setValue(int(progress * 100))
        if status == "error":
            self._progress_label.setText(f"Error en pista {track_num}")
        elif status == "completed":
            pass

    def _on_job_finished(self, job_id: str, result: dict):
        self._progress.setValue(100)
        status = result.get("status", "completed")
        self._progress_label.setText(
            f"Ripeo {status}: {result.get('tracks_ripped', 0)} pistas"
        )
        self._import_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        self._current_job_id = ""

    def _on_rip_error(self, job_id: str, error: str):
        self._progress_label.setText(f"Error: {error}")
        self._import_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02d}"

    def _apply_qss(self):
        # Page background
        self.setStyleSheet("QWidget#michiDiscLabPage { background: #090B11; }")

        # Scroll area
        scr = self.findChild(QScrollArea, "discLabScroll")
        if scr:
            scr.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # Content
        cnt = self.findChild(QWidget, "discLabContent")
        if cnt:
            cnt.setStyleSheet("background: transparent;")

        # Title / subtitle
        t = self.findChild(QLabel, "discLabTitle")
        if t:
            t.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.92); font-size: 18px;"
                "  font-weight: 700; background: transparent; border: none; }")
        s = self.findChild(QLabel, "discLabSubtitle")
        if s:
            s.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.56); font-size: 13px;"
                "  background: transparent; border: none; margin-bottom: 4px; }")

        # Glass panels
        for pn in ("discLabDrivePanel", "discLabSettingsPanel", "discLabProgressPanel",
                   "discLabDiagPanel", "discLabTrackPanel"):
            p = self.findChild(QFrame, pn)
            if p:
                p.setStyleSheet(glass_card_qss(pn, "elevated"))

        # Drive status
        ds = self.findChild(QLabel, "driveStatus")
        if ds:
            ds.setStyleSheet(
                "QLabel { color: rgba(143,183,255,0.72); font-size: 14px;"
                "  background: transparent; border: none; }")

        # Table
        table = self.findChild(QTableWidget, "discLabTable")
        if table:
            table.setStyleSheet(clean_table_qss())
            hh = table.horizontalHeader()
            if hh:
                hh.setStyleSheet(clean_table_header_qss())

        # Diagnostic labels
        for oname in ("diagTitle", "diagText", "discLabProgressLabel"):
            lbl = self.findChild(QLabel, oname)
            if lbl:
                lbl.setStyleSheet(
                    "QLabel { color: rgba(255,255,255,0.60); font-size: 11px;"
                    "  background: transparent; border: none; }"
                    if oname != "discLabProgressLabel" else
                    "QLabel { color: rgba(255,255,255,0.54); font-size: 11px;"
                    "  background: transparent; border: none; }")

        # ComboBoxes
        _COMBO_STYLE = f"""
            QComboBox {{
                background: rgba(255,255,255,0.045);
                border: 1px solid rgba(255,255,255,0.055);
                border-radius: 8px;
                padding: 6px 10px;
                color: rgba(255,255,255,0.82);
                font-size: 12px;
            }}
            QComboBox:hover {{
                border: 1px solid rgba(255,255,255,0.08);
            }}
            {combo_dropdown_qss()}
        """
        for cb in self.findChildren(QComboBox):
            cb.setStyleSheet(_COMBO_STYLE)

        # Progress bar
        prog = self.findChild(QProgressBar, "discLabProgress")
        if prog:
            prog.setStyleSheet(glass_progress_qss())

        # Buttons
        for btn_name in ("scanDriveBtn", "analyzeDiscBtn", "destBtn",
                         "isoToggleBtn", "isoSelectBtn", "cancelRipBtn"):
            btn = self.findChild(QPushButton, btn_name)
            if btn:
                btn.setStyleSheet(glass_button_qss("ghost"))
        import_btn = self.findChild(QPushButton, "importBtn")
        if import_btn:
            import_btn.setStyleSheet(glass_button_qss("primary"))
