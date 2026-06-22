"""Music Identifier View — premium dashboard for music recognition."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QComboBox, QPushButton,
)
from ui.identifier_widgets import (
    _GlassCard, _GlassButton, _PrimaryButton, StatusPill,
    DetectionResultCard, EmptyState,
)


class MusicIdentifierView(QWidget):
    toggle_requested = Signal(bool)
    clear_requested = Signal()
    track_selected = Signal(dict)
    identify_once_requested = Signal()
    settings_requested = Signal()
    play_track_requested = Signal(dict)
    search_track_requested = Signal(dict)
    delete_track_requested = Signal(dict)
    detection_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            " stop:0 rgba(20,22,28,0.94), stop:1 rgba(8,10,16,0.94));")
        self._enabled = False
        self._status = "idle"
        self._source_type = ""
        self._source_label = ""
        self._paused_reason = ""
        self._provider = "none"
        self._provider_ok = False
        self._filter_source = "todas"
        self._filter_match = "todas"
        self._tracks = []

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12);"
            "  border-radius: 3px; min-height: 30px; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(24, 20, 24, 40)
        self._layout.setSpacing(14)

        self._build_hero()
        self._build_status_cards()
        self._build_history()
        self._build_diag()
        self._layout.addStretch()

        self._scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    # ── Hero ──

    def _build_hero(self):
        hero = QWidget()
        hero.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "  stop:0 rgba(255,255,255,0.06),"
            "  stop:0.6 rgba(255,255,255,0.025),"
            "  stop:1 rgba(70,145,255,0.06));"
            "border: 1px solid rgba(255,255,255,0.09);"
            "border-radius: 22px;")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(24, 22, 24, 22)
        hl.setSpacing(20)

        left = QVBoxLayout()
        left.setSpacing(4)
        t = QLabel("Identificador musical")
        t.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: rgba(255,255,255,0.94);")
        left.addWidget(t)
        s = QLabel("Reconoce musica desde radio y streams, guarda el historial y cruza resultados con tu biblioteca.")
        s.setWordWrap(True)
        s.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.45);")
        left.addWidget(s)
        left.addSpacing(6)

        # Badge row
        badges = QHBoxLayout()
        badges.setSpacing(8)
        self._pill_status = StatusPill("", "idle")
        badges.addWidget(self._pill_status)

        self._lbl_source = QLabel("Sin reproduccion")
        self._lbl_source.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.42);"
            "background: rgba(255,255,255,0.035); border-radius: 8px; padding: 4px 10px;")
        badges.addWidget(self._lbl_source)

        self._lbl_provider = QLabel("Ningun proveedor")
        self._lbl_provider.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.42);"
            "background: rgba(255,255,255,0.035); border-radius: 8px; padding: 4px 10px;")
        badges.addWidget(self._lbl_provider)
        badges.addStretch()
        left.addLayout(badges)
        left.addSpacing(4)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        self._toggle_btn = _PrimaryButton("Activar")
        self._toggle_btn.clicked.connect(self._on_toggle)
        btn_id = _GlassButton("Identificar ahora")
        btn_id.clicked.connect(self.identify_once_requested.emit)
        btn_pref = _GlassButton("Preferencias")
        btn_pref.clicked.connect(self.settings_requested.emit)
        btns.addWidget(self._toggle_btn)
        btns.addWidget(btn_id)
        btns.addWidget(btn_pref)
        btns.addStretch()
        left.addLayout(btns)
        hl.addLayout(left, 1)
        self._layout.addWidget(hero)

    def _on_toggle(self):
        self._enabled = not self._enabled
        self.toggle_requested.emit(self._enabled)

    # ── Status cards ──

    def _build_status_cards(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        # Source card
        self._source_card = _GlassCard()
        sc = QVBoxLayout(self._source_card)
        sc.setContentsMargins(18, 14, 18, 14)
        sc.setSpacing(6)
        st = QLabel("Estado de escucha")
        st.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        sc.addWidget(st)
        self._lbl_source_detail = QLabel("")
        self._lbl_source_detail.setWordWrap(True)
        self._lbl_source_detail.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.48);")
        sc.addWidget(self._lbl_source_detail)
        self._lbl_pause = QLabel("")
        self._lbl_pause.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.72); font-weight: 600;")
        sc.addWidget(self._lbl_pause)
        sc.addStretch()
        row.addWidget(self._source_card)

        # Provider card
        self._prov_card = _GlassCard()
        pc = QVBoxLayout(self._prov_card)
        pc.setContentsMargins(18, 14, 18, 14)
        pc.setSpacing(6)
        pt = QLabel("Proveedor")
        pt.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        pc.addWidget(pt)
        self._lbl_prov_status = QLabel("Ninguno")
        self._lbl_prov_status.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.62);")
        pc.addWidget(self._lbl_prov_status)
        self._lbl_prov_config = QLabel("")
        self._lbl_prov_config.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.38);")
        pc.addWidget(self._lbl_prov_config)
        pc.addStretch()
        row.addWidget(self._prov_card)

        self._layout.addLayout(row)

    # ── History ──

    def _build_history(self):
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(8)

        hdr = QHBoxLayout()
        ht = QLabel("Historial de detecciones")
        ht.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: rgba(255,255,255,0.88);")
        hdr.addWidget(ht)
        hdr.addStretch()

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(
            ["Todas", "Radio", "Navidrome", "Jellyfin", "Stream", "Manual"])
        self._filter_combo.currentTextChanged.connect(self._apply_filter)
        self._filter_combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.62);"
            "  border: 1px solid rgba(255,255,255,0.07); border-radius: 8px;"
            "  padding: 4px 8px; font-size: 11px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background: #1a1d24;"
            "  color: rgba(255,255,255,0.78); border: 1px solid rgba(255,255,255,0.08); }")
        hdr.addWidget(self._filter_combo)

        cl.addLayout(hdr)

        self._hist_layout = QVBoxLayout()
        self._hist_layout.setSpacing(6)
        cl.addLayout(self._hist_layout)

        self._empty_state = EmptyState(
            "Aun no hay canciones detectadas",
            "Activa el identificador mientras escuchas radio o streams.")
        self._empty_state.hide()
        cl.addWidget(self._empty_state)

        clear_btn = QPushButton("Limpiar historial")
        clear_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.32); font-size: 11px;"
            "  background: transparent; border: none; }"
            "QPushButton:hover { color: #FF453A; }")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_requested.emit)
        cl.addWidget(clear_btn, alignment=Qt.AlignRight)

        self._layout.addWidget(card)

    def _apply_filter(self, text: str):
        fmap = {"Todas": "todas", "Radio": "radio", "Navidrome": "navidrome",
                "Jellyfin": "jellyfin", "Stream": "remote_stream", "Manual": "manual"}
        self._filter_source = fmap.get(text, "todas")
        self._refresh_history()

    # ── Diagnostics ──

    def _build_diag(self):
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)
        t = QLabel("Diagnostico")
        t.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(t)
        self._lbl_diag = QLabel("")
        self._lbl_diag.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.42);")
        self._lbl_diag.setWordWrap(True)
        cl.addWidget(self._lbl_diag)
        self._layout.addWidget(card)

    # ── Public API ──

    def set_identifier_state(self, state: str):
        self._status = state
        self._pill_status.set_state(state)
        self._toggle_btn.setText("Desactivar" if self._enabled else "Activar")

    def set_identifier_enabled(self, enabled: bool):
        self._enabled = enabled
        self._toggle_btn.setText("Desactivar" if enabled else "Activar")

    def set_status_message(self, text: str):
        self._lbl_diag.setText(text)

    def set_source_status(self, source_type: str, source_label: str = "",
                          paused_reason: str = ""):
        self._source_type = source_type
        self._source_label = source_label
        self._paused_reason = paused_reason

        disp = source_label or {
            "radio": "Radio", "navidrome": "Navidrome", "jellyfin": "Jellyfin",
            "remote_stream": "Stream", "local_file": "Archivo local",
        }.get(source_type, source_type or "Sin reproduccion")
        self._lbl_source.setText(f"Fuente: {disp}")

        if paused_reason:
            self._lbl_pause.setText(paused_reason)
            self._lbl_source_detail.setText("Identificador pausado")
        elif source_type in ("radio", "navidrome", "jellyfin", "remote_stream"):
            self._lbl_pause.setText("")
            self._lbl_source_detail.setText(
                "Escuchando automaticamente — Astra reconocera nuevas canciones.")
        elif source_type in ("local_file", "device_file"):
            self._lbl_pause.setText(
                "Pausado: archivo local con metadatos conocidos")
            self._lbl_source_detail.setText("")
        else:
            self._lbl_pause.setText("")
            self._lbl_source_detail.setText("")

    def set_provider_status(self, name: str, configured: bool):
        self._provider = name
        self._provider_ok = configured
        self._lbl_provider.setText(
            name.capitalize() if name != "none" else "Ninguno")
        self._lbl_prov_status.setText(
            "Configurado" if configured else "No configurado")
        self._lbl_prov_config.setText(
            f"Proveedor: {name}" if name != "none" else "Selecciona un proveedor")

    def set_detected_tracks(self, tracks: list[dict]):
        self._tracks = tracks
        self._refresh_history()

    def _refresh_history(self):
        while self._hist_layout.count():
            w = self._hist_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        filtered = self._tracks
        if self._filter_source != "todas":
            filtered = [t for t in filtered
                        if (t.get("source_type", "") == self._filter_source
                            or t.get("source", "") == self._filter_source)]

        if not filtered:
            self._empty_state.show()
            return
        self._empty_state.hide()

        for track in filtered:
            card = DetectionResultCard(track)
            card.play_requested.connect(self.play_track_requested.emit)
            card.search_requested.connect(self.search_track_requested.emit)
            card.delete_requested.connect(self.delete_track_requested.emit)
            self._hist_layout.addWidget(card)
