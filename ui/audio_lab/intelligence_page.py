"""IntelligencePage — local music intelligence: BPM, key, energy, similarity, local radio.

Connects to existing audio_analysis (FeatureRepository, AnalysisService).
Gracefully degrades if analysis backend is unavailable.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QProgressBar,
)

from ui.icons import get_pixmap
from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_progress_qss,
)

logger = logging.getLogger("michi.intelligence.ui")


class IntelligencePage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, db=None, worker_mgr=None):
        super().__init__()
        self.setObjectName("intelligencePage")
        self._db = db
        self._worker_mgr = worker_mgr
        self._analysis = None
        self._repo = None
        self._backend_available = False
        self._build_ui()
        self._check_backend()

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

        title = QLabel("Inteligencia Local")
        title.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 22px; "
            "font-weight: 700; background: transparent;"
        )
        cl.addWidget(title)

        sub = QLabel(
            "Extrae características musicales de tu biblioteca: "
            "BPM, tonalidad, energía y similitud."
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.56); font-size: 13px; "
            "background: transparent;"
        )
        sub.setWordWrap(True)
        cl.addWidget(sub)

        status_card = QFrame()
        status_card.setStyleSheet(glass_card_qss("intelStatusCard", "base"))
        svl = QVBoxLayout(status_card)
        svl.setContentsMargins(20, 16, 20, 16)
        svl.setSpacing(8)

        st = QLabel("Estado del análisis")
        st.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 15px; "
            "font-weight: 600; background: transparent;"
        )
        svl.addWidget(st)

        self._status_lines = {}
        for label in ("Backend:", "Archivos analizados:", "Jobs pendientes:"):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "color: rgba(255,255,255,0.56); font-size: 11px; "
                "background: transparent;"
            )
            val = QLabel("--")
            val.setStyleSheet(
                "color: rgba(255,255,255,0.78); font-size: 11px; "
                "font-weight: 600; background: transparent;"
            )
            row.addWidget(lbl)
            row.addWidget(val, 1)
            svl.addLayout(row)
            self._status_lines[label] = val

        self._notice_label = QLabel("")
        self._notice_label.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 11px; background: transparent;"
        )
        self._notice_label.setWordWrap(True)
        svl.addWidget(self._notice_label)

        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Analizar biblioteca")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.setStyleSheet(glass_button_qss("primary"))
        self._scan_btn.clicked.connect(self._analyze_all)
        btn_row.addWidget(self._scan_btn)

        self._rebuild_btn = QPushButton("Reconstruir índice")
        self._rebuild_btn.setCursor(Qt.PointingHandCursor)
        self._rebuild_btn.setStyleSheet(glass_button_qss("secondary"))
        self._rebuild_btn.clicked.connect(self._rebuild_index)
        btn_row.addWidget(self._rebuild_btn)

        btn_row.addStretch()
        svl.addLayout(btn_row)

        self._analysis_progress = QProgressBar()
        self._analysis_progress.setRange(0, 100)
        self._analysis_progress.setValue(0)
        self._analysis_progress.setVisible(False)
        self._analysis_progress.setStyleSheet(glass_progress_qss())
        svl.addWidget(self._analysis_progress)

        cl.addWidget(status_card)

        grid = QGridLayout()
        grid.setSpacing(14)

        feature_cards = [
            ("sidebar_identifier", "BPM",
             "Tempo en pulsaciones por minuto.",
             self._show_bpm),
            ("sidebar_mix", "Tonalidad (Key)",
             "Key musical aproximada.",
             self._show_key),
            ("sidebar_popular", "Energía",
             "Nivel de energía RMS.",
             self._show_energy),
            ("sidebar_albums", "Similitud",
             "Distancia coseno entre vectores de\n"
             "features acústicas.",
             self._show_similarity),
            ("sidebar_radio", "Radio Local",
             "Genera lista de reproducción\n"
             "infinita desde una canción.",
             self._play_local_radio),
            ("sidebar_library", "Mix Inteligente",
             "Mix basado en reglas:\n"
             "BPM, key, energía, calidad.",
             self._create_smart_mix),
        ]

        for idx, (icon, title_t, desc, callback) in enumerate(feature_cards):
            card = self._build_feature_card(icon, title_t, desc, callback)
            grid.addWidget(card, idx // 3, idx % 3)

        for col in range(3):
            grid.setColumnStretch(col, 1)
        cl.addLayout(grid)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _build_feature_card(self, icon_key: str, title_t: str, desc: str,
                            callback) -> QFrame:
        card = QFrame()
        card.setObjectName(f"intelFeatureCard_{title_t}")
        card.setStyleSheet(glass_card_qss(card.objectName(), "elevated"))
        card.setMinimumHeight(140)

        cv = QVBoxLayout(card)
        cv.setContentsMargins(20, 16, 20, 16)
        cv.setSpacing(8)

        pix = get_pixmap(icon_key, size=36)
        icon_lbl = QLabel()
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "background: rgba(143,183,255,0.06);"
            "border: 1px solid rgba(143,183,255,0.06);"
            "border-radius: 8px;"
        )
        cv.addWidget(icon_lbl)

        t = QLabel(title_t)
        t.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; "
            "font-weight: 600; background: transparent; border: none;"
        )
        cv.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet(
            "color: rgba(255,255,255,0.50); font-size: 11px; "
            "background: transparent; border: none;"
        )
        d.setWordWrap(True)
        cv.addWidget(d)

        cv.addStretch()

        btn = QPushButton("Abrir")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("primary"))
        btn.setFixedWidth(80)
        btn.clicked.connect(callback)
        cv.addWidget(btn)

        return card

    def _set_notice(self, text: str):
        if hasattr(self, "_notice_label"):
            self._notice_label.setText(text)

    def _check_backend(self):
        try:
            from audio_analysis.dependency_check import check_dependencies
            deps = check_dependencies()
            self._backend_available = deps.get("available", False)
            self._status_lines["Backend:"].setText(
                deps.get("backend", "disabled").capitalize()
                if self._backend_available else "No disponible"
            )
            if not self._backend_available:
                missing = ", ".join(deps.get("missing", [])) or "dependencias"
                self._set_notice(
                    f"Análisis acústico no disponible. Falta: {missing}."
                )
        except Exception as e:
            logger.warning("Backend check failed: %s", e)
            self._backend_available = False
            self._status_lines["Backend:"].setText("Error")
            self._set_notice(f"No se pudo comprobar el backend: {e}")

        if not self._backend_available:
            self._scan_btn.setEnabled(False)
            self._rebuild_btn.setEnabled(False)
            self._status_lines["Archivos analizados:"].setText("—")
            self._status_lines["Jobs pendientes:"].setText("—")
        else:
            self._refresh_status()

    def _get_service(self):
        if self._analysis is None and self._backend_available:
            try:
                from audio_analysis.analysis_service import AnalysisService
                self._analysis = AnalysisService(
                    db=self._db, worker_mgr=self._worker_mgr
                )
                self._analysis.analysis_batch_finished.connect(
                    self._on_analysis_batch_finished
                )
            except Exception as e:
                logger.warning("AnalysisService init failed: %s", e)
                self._set_notice(f"No se pudo iniciar AnalysisService: {e}")
        return self._analysis

    def _refresh_status(self):
        if not self._backend_available:
            return
        try:
            from audio_analysis.feature_repository import FeatureRepository
            repo = FeatureRepository()
            count = repo._conn.execute(
                "SELECT COUNT(*) FROM audio_feature WHERE status='completed'"
            ).fetchone()[0]
            pending = repo._conn.execute(
                "SELECT COUNT(*) FROM audio_analysis_job "
                "WHERE status IN ('pending','running')"
            ).fetchone()[0]
            self._status_lines["Archivos analizados:"].setText(str(count))
            self._status_lines["Jobs pendientes:"].setText(str(pending))
        except Exception as e:
            logger.warning("Status refresh error: %s", e)
            self._set_notice(f"No se pudo leer el estado del análisis: {e}")

    def _collect_track_ids(self) -> list[int]:
        if not self._db or not hasattr(self._db, "get_all"):
            return []
        ids: list[int] = []
        try:
            for item in self._db.get_all():
                tid = getattr(item, "id", None)
                filepath = getattr(item, "filepath", "")
                if isinstance(tid, int) and tid > 0 and filepath:
                    ids.append(tid)
        except Exception as e:
            logger.warning("Could not collect track ids: %s", e)
        return ids

    def _analyze_all(self):
        if not self._backend_available:
            self._status_lines["Backend:"].setText("No disponible")
            return

        analysis = self._get_service()
        if not analysis:
            self._set_notice("AnalysisService no está disponible.")
            return
        if not analysis.enabled:
            self._set_notice(
                "Análisis acústico desactivado en configuración. "
                "Actívalo antes de analizar la biblioteca."
            )
            return
        if not self._worker_mgr:
            self._set_notice(
                "WorkerManager no disponible: no se pueden ejecutar jobs en segundo plano."
            )
            return

        track_ids = self._collect_track_ids()
        if not track_ids:
            self._set_notice("No hay pistas locales válidas para analizar.")
            return

        self._scan_btn.setEnabled(False)
        self._analysis_progress.setVisible(True)
        self._analysis_progress.setRange(0, 0)
        self._set_notice(f"Encolando análisis para {len(track_ids)} pistas...")
        batch_id = analysis.analyze_tracks_async(track_ids)
        self._set_notice(f"Análisis encolado: {batch_id}")
        self._refresh_status()

    def _on_analysis_batch_finished(self, _batch_id: str, summary: object):
        self._analysis_progress.setVisible(False)
        self._analysis_progress.setRange(0, 100)
        self._analysis_progress.setValue(100)
        self._scan_btn.setEnabled(True)
        status = "completado"
        if isinstance(summary, dict):
            status = summary.get("status", status)
        self._set_notice(f"Análisis {status}.")
        self._refresh_status()

    def _rebuild_index(self):
        if not self._backend_available:
            return
        try:
            from audio_analysis.feature_repository import FeatureRepository
            repo = FeatureRepository()
            repo._conn.execute("DELETE FROM audio_similarity_cache")
            repo._conn.commit()
            logger.info("Similarity index rebuilt")
            self._set_notice("Índice de similitud reconstruido.")
        except Exception as e:
            logger.warning("Rebuild failed: %s", e)
            self._set_notice(f"No se pudo reconstruir el índice: {e}")
        self._refresh_status()

    def _show_bpm(self):
        self.navigate_requested.emit("library_hub")

    def _show_key(self):
        self.navigate_requested.emit("library_hub")

    def _show_energy(self):
        self.navigate_requested.emit("library_hub")

    def _show_similarity(self):
        self._set_notice("Vista de similitud pendiente de conectar a Mix/Playlists.")
        logger.info("Similarity view — pending implementation")

    def _play_local_radio(self):
        self._set_notice("Radio local pendiente de conectar al generador de cola.")
        logger.info("Local radio — pending implementation")

    def _create_smart_mix(self):
        self._set_notice("Mix inteligente pendiente de conectar al motor de playlists.")
        logger.info("Smart mix — pending implementation")
