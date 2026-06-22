"""Home Audio View — premium dark/glass multiroom dashboard."""
import time
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QSlider,
)

class HomeAudioView(QWidget):
    connect_requested = Signal()
    refresh_requested = Signal()
    enable_multiroom_requested = Signal(bool)
    device_cast_current_requested = Signal(dict)
    device_play_requested = Signal(dict)
    device_pause_requested = Signal(dict)
    device_stop_requested = Signal(dict)
    device_volume_changed = Signal(dict, int)
    group_selected_requested = Signal(dict)
    open_settings_requested = Signal()
    open_receiver_wizard_requested = Signal()
    create_group_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._needs_refresh = True
        self._ha_connected = False
        self._multiroom_active = False
        self._snapserver_running = False
        self._transmit_active = False
        self._transmit_device_name = ""
        self._snap_ctrl_port = 1705
        self._api_running = False
        self._mdns_running = False
        self._local_media_running = False
        self._devices = []
        self._groups = []
        self._activity_log = []
        self._current_tab = "resumen"

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 6px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12);"
            "  border-radius: 3px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(24, 20, 24, 40)
        self._layout.setSpacing(14)

        self._build_tabs()
        self._build_hero()
        self._build_grid()

        self._layout.addStretch()
        self._scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        self._add_activity("Sistema listo")

    def set_data(self, ha_connected, multiroom_active, snapserver_running,
                 devices, groups, transmit_active=False, transmit_device_name="",
                 snap_ctrl_port=1705, api_running=False, mdns_running=False,
                 local_media_running=False):
        prev_devices = len(self._devices)
        self._ha_connected = ha_connected
        self._multiroom_active = multiroom_active
        self._snapserver_running = snapserver_running
        self._transmit_active = transmit_active
        self._transmit_device_name = transmit_device_name
        self._snap_ctrl_port = snap_ctrl_port
        self._api_running = api_running
        self._mdns_running = mdns_running
        self._local_media_running = local_media_running
        self._devices = devices or []
        self._groups = groups or []
        self._needs_refresh = False

        if ha_connected and not getattr(self, '_prev_ha', True):
            self._add_activity("Home Assistant conectado")
        elif not ha_connected and getattr(self, '_prev_ha', False):
            self._add_activity("Home Assistant desconectado")
        self._prev_ha = ha_connected

        if snapserver_running and not getattr(self, '_prev_snap', True):
            self._add_activity("Snapserver iniciado")
        elif not snapserver_running and getattr(self, '_prev_snap', False):
            self._add_activity("Snapserver detenido")
        self._prev_snap = snapserver_running

        if len(self._devices) > prev_devices:
            self._add_activity(f"{len(self._devices) - prev_devices} receptor(es) nuevo(s)")

        self._refresh_ui()

    def refresh_if_needed(self):
        if self._needs_refresh:
            self._refresh_ui()

    def _add_activity(self, msg: str):
        self._activity_log.insert(0, {"msg": msg, "time": time.time()})
        if len(self._activity_log) > 20:
            self._activity_log = self._activity_log[:20]

    def set_diagnostics(self, updates: dict):
        for label, text in updates.items():
            if label in self._diag_labels:
                self._diag_labels[label].setText(text)

    def _refresh_ui(self):
        self._refresh_badges()
        self._refresh_content_area()

    # ── Tabs ──

    def _build_tabs(self):
        tabs_row = QHBoxLayout()
        tabs_row.setSpacing(4)
        self._tab_btns = {}
        self._tab_keys = [
            ("resumen", "Resumen"),
            ("dispositivos", "Dispositivos"),
            ("grupos", "Grupos"),
            ("diagnostico", "Diagnostico"),
            ("receptores", "Receptores"),
        ]
        for key, label in self._tab_keys:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(_TAB_QSS)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._on_tab(k))
            btn.setChecked(key == "resumen")
            tabs_row.addWidget(btn)
            self._tab_btns[key] = btn
        tabs_row.addStretch()
        self._layout.addLayout(tabs_row)

    def _on_tab(self, key: str):
        self._current_tab = key
        for k, btn in self._tab_btns.items():
            btn.setChecked(k == key)
        self._refresh_content_area()

    def _refresh_content_area(self):
        _clear_layout(self._grid_wrapper)
        tab = self._current_tab

        if tab == "resumen":
            self._build_resumen_in_grid()
        elif tab == "dispositivos":
            self._build_devices_full()
        elif tab == "grupos":
            self._build_groups_full()
        elif tab == "diagnostico":
            self._build_diag_full()
        elif tab == "receptores":
            self._build_receivers_full()

    # ── Hero ──

    def _build_hero(self):
        hero = QFrame()
        hero.setStyleSheet(
            "QFrame#hero {"
            "  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "    stop:0 rgba(255,255,255,0.065),"
            "    stop:0.55 rgba(255,255,255,0.035),"
            "    stop:1 rgba(143,183,255,0.065));"
            "  border: 1px solid rgba(143,183,255,0.12);"
            "  border-radius: 22px; }"
            "QLabel { background: transparent; }")
        hero.setObjectName("hero")
        hero.setMinimumHeight(150)
        hero.setMaximumHeight(180)

        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(24, 22, 24, 22)
        h_layout.setSpacing(20)

        # Left: text + badges + buttons
        left = QVBoxLayout()
        left.setSpacing(6)

        hero_title = QLabel("Centro de audio doméstico")
        hero_title.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: rgba(255,255,255,0.94);")
        left.addWidget(hero_title)

        hero_sub = QLabel(
            "Conecta Home Assistant, Snapcast y tus parlantes para enviar música")
        hero_sub.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.48);")
        left.addWidget(hero_sub)

        left.addSpacing(6)

        # Badges
        badges = QHBoxLayout()
        badges.setSpacing(8)
        self._hero_badge_ha = StatusPill("Home Assistant", "Desconectado", "error")
        self._hero_badge_mr = StatusPill("Multiroom", "Inactivo", "warning")
        self._hero_badge_snap = StatusPill("Snapserver", "Detenido", "error")
        self._hero_badge_dev = StatusPill("Receptores", "0", "neutral")
        self._hero_badge_tx = StatusPill("Transmitiendo", "Local", "neutral")
        badges.addWidget(self._hero_badge_ha)
        badges.addWidget(self._hero_badge_mr)
        badges.addWidget(self._hero_badge_snap)
        badges.addWidget(self._hero_badge_dev)
        badges.addWidget(self._hero_badge_tx)
        badges.addStretch()
        left.addLayout(badges)

        left.addSpacing(4)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(8)
        btn_ha = _PrimaryButton("Conectar Home Assistant")
        btn_ha.clicked.connect(self.connect_requested.emit)
        btn_mr = _SecondaryButton("Activar Multiroom")
        btn_mr.clicked.connect(
            lambda: self.enable_multiroom_requested.emit(not self._multiroom_active))
        btn_rf = _GhostButton("Actualizar")
        btn_rf.clicked.connect(self.refresh_requested.emit)
        btn_pref = _GhostButton("Preferencias")
        btn_pref.clicked.connect(self.open_settings_requested.emit)

        btns.addWidget(btn_ha)
        btns.addWidget(btn_mr)
        btns.addWidget(btn_rf)
        btns.addWidget(btn_pref)
        btns.addStretch()
        left.addLayout(btns)

        h_layout.addLayout(left)

        # Right: abstract visual
        visual = _HeroVisual()
        h_layout.addWidget(visual)

        self._layout.addWidget(hero)
        self._layout.addSpacing(4)

    def _refresh_badges(self):
        ha_state = "Conectado" if self._ha_connected else "Desconectado"
        ha_level = "success" if self._ha_connected else "error"
        mr_state = "Activo" if self._multiroom_active else "Inactivo"
        mr_level = "success" if self._multiroom_active else "warning"
        snap_state = "En ejecucion" if self._snapserver_running else "Detenido"
        snap_level = "success" if self._snapserver_running else "error"
        dev_count = str(len(self._devices))
        dev_level = "success" if self._devices else "neutral"

        self._hero_badge_ha.set_state(ha_state, ha_level)
        self._hero_badge_mr.set_state(mr_state, mr_level)
        self._hero_badge_snap.set_state(snap_state, snap_level)
        self._hero_badge_dev.set_state(dev_count, dev_level)
        tx_state = self._transmit_device_name if self._transmit_active and self._transmit_device_name else "Local"
        tx_level = "success" if self._transmit_active else "neutral"
        self._hero_badge_tx.set_state(tx_state, tx_level)

        # Update multiroom button text
        if hasattr(self, '_hero_btn_mr'):
            self._hero_btn_mr.setText(
                "Detener" if self._multiroom_active else "Activar Multiroom")

    # ── Grid layout ──

    def _build_grid(self):
        self._grid_wrapper = QHBoxLayout()
        self._grid_wrapper.setSpacing(0)
        self._layout.addLayout(self._grid_wrapper)

    def _build_resumen_in_grid(self):
        grid = QGridLayout()
        grid.setSpacing(14)

        # Row 1 — System Status + Multiroom
        sys_card = self._build_system_card()
        mr_card = self._build_multiroom_card()
        grid.addWidget(sys_card, 0, 0)
        grid.addWidget(mr_card, 0, 1)

        # Row 2 — Devices (full width)
        dev_card = self._build_devices_card()
        grid.addWidget(dev_card, 1, 0, 1, 2)

        # Row 3 — Groups + Diagnostics + Activity
        groups_card = self._build_groups_card()
        diag_card = self._build_diagnostics_card()
        act_card = self._build_activity_card()
        grid.addWidget(groups_card, 2, 0)
        grid.addWidget(diag_card, 2, 1)
        grid.addWidget(act_card, 2, 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        self._grid_wrapper.addLayout(grid)

    # ── System Status card ──

    def _build_system_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(0)

        title = QLabel("Estado del sistema")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(title)
        cl.addSpacing(10)

        rows_data = [
            "Home Assistant", "API Astra", "mDNS", "Servidor local", "Ultima sinc",
        ]
        self._sys_labels = {}
        for label in rows_data:
            r = QHBoxLayout()
            r.setSpacing(8)
            r.setContentsMargins(0, 4, 0, 4)
            dot = QLabel("")
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                "border-radius: 4px; background: rgba(255,255,255,0.20);")
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.52);")
            val = QLabel("—")
            val.setStyleSheet(
                "font-size: 11px; color: rgba(255,255,255,0.72); font-weight: 600;")
            r.addWidget(dot)
            r.addWidget(lbl)
            r.addStretch()
            r.addWidget(val)
            cl.addLayout(r)
            self._sys_labels[label] = (dot, val)

            if label != rows_data[-1]:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(
                    "border: none; border-top: 1px solid rgba(255,255,255,0.06);")
                cl.addWidget(sep)

        self._refresh_system_rows()
        return card

    def _refresh_system_rows(self):
        if not hasattr(self, '_sys_labels'):
            return
        updates = {
            "Home Assistant": ("Conectado" if self._ha_connected else "No conectado",
                               "#8FB7FF" if self._ha_connected else "rgba(255,255,255,0.20)"),
            "API Astra": ("Activa" if self._api_running else "No activa",
                          "#8FB7FF" if self._api_running else "rgba(255,255,255,0.20)"),
            "mDNS": ("Activo" if self._mdns_running else "Inactivo",
                     "#8FB7FF" if self._mdns_running else "rgba(255,255,255,0.20)"),
            "Servidor local": ("Activo" if self._local_media_running else "No activo",
                               "#8FB7FF" if self._local_media_running else "rgba(255,255,255,0.20)"),
            "Ultima sinc": ("—", "rgba(255,255,255,0.20)"),
        }
        for label, (dot, val) in self._sys_labels.items():
            text, color = updates.get(label, ("—", "rgba(255,255,255,0.20)"))
            dot.setStyleSheet(f"border-radius: 4px; background: {color};")
            val.setText(text)

    # ── Multiroom card ──

    def _build_multiroom_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(8)

        title = QLabel("Modo Multiroom")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(title)

        if self._snapserver_running:
            cl.addWidget(StatusPill("Activo", "En ejecucion", "success"))
            info = QHBoxLayout()
            info.setSpacing(12)
            for kv in [("Stream", "FLAC 44.1kHz"), ("Puerto", str(self._snap_ctrl_port or 1705)),
                        ("Receptores", str(len(self._devices)))]:
                k = QLabel(kv[0])
                k.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.42);")
                v = QLabel(kv[1])
                v.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.72); font-weight: 600;")
                info.addWidget(k)
                info.addWidget(v)
            info.addStretch()
            cl.addLayout(info)
            btn_stop = _SecondaryButton("Detener Multiroom")
            btn_stop.clicked.connect(
                lambda: self.enable_multiroom_requested.emit(False))
            cl.addWidget(btn_stop)
        else:
            cl.addWidget(StatusPill("Inactivo", "Sin servicio", "error"))
            desc = QLabel(
                "Activa Snapserver para enviar audio sincronizado\na toda la casa.")
            desc.setStyleSheet(
                "font-size: 11px; color: rgba(255,255,255,0.42);")
            desc.setWordWrap(True)
            cl.addWidget(desc)
            cl.addSpacing(4)
            btn_start = _SecondaryButton("Activar Multiroom")
            btn_start.clicked.connect(
                lambda: self.enable_multiroom_requested.emit(True))
            cl.addWidget(btn_start)

        cl.addStretch()
        return card

    # ── Devices card ──

    def _build_devices_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("Dispositivos")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        hdr.addWidget(title)
        hdr.addStretch()
        add_btn = _GhostButton("+ Crear receptor")
        add_btn.clicked.connect(self.open_receiver_wizard_requested.emit)
        hdr.addWidget(add_btn)
        cl.addLayout(hdr)

        if not self._devices:
            empty = self._empty_state(
                "No hay parlantes detectados",
                "Conecta Home Assistant o activa Snapcast\npara descubrir receptores en tu red.",
                [("Conectar Home Assistant", self.connect_requested.emit),
                 ("Activar Multiroom",
                  lambda: self.enable_multiroom_requested.emit(True))])
            cl.addWidget(empty)
            return card

        grid = QGridLayout()
        grid.setSpacing(10)
        for i, dev in enumerate(self._devices[:6]):
            tile = _DeviceTile(dev)
            tile.cast_requested.connect(
                lambda d=dev: self.device_cast_current_requested.emit(d))
            tile.play_requested.connect(
                lambda d=dev: self.device_play_requested.emit(d))
            tile.pause_requested.connect(
                lambda d=dev: self.device_pause_requested.emit(d))
            tile.stop_requested.connect(
                lambda d=dev: self.device_stop_requested.emit(d))
            tile.volume_changed.connect(
                lambda v, d=dev: self.device_volume_changed.emit(d, v))
            row, col = divmod(i, 3)
            grid.addWidget(tile, row, col)
        cl.addLayout(grid)
        return card

    def _build_devices_full(self):
        cl = self._grid_wrapper
        card = _GlassCard()
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("Dispositivos")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        hdr.addWidget(title)
        hdr.addStretch()
        add_btn = _GhostButton("+ Crear receptor")
        add_btn.clicked.connect(self.open_receiver_wizard_requested.emit)
        hdr.addWidget(add_btn)
        cv.addLayout(hdr)

        if not self._devices:
            cv.addWidget(self._empty_state(
                "No hay parlantes detectados",
                "Conecta Home Assistant o activa Snapcast para descubrir receptores.",
                [("Conectar Home Assistant", self.connect_requested.emit),
                 ("Activar Multiroom",
                  lambda: self.enable_multiroom_requested.emit(True))]))
        else:
            grid = QGridLayout()
            grid.setSpacing(10)
            for i, dev in enumerate(self._devices):
                tile = _DeviceTile(dev)
                tile.cast_requested.connect(
                    lambda d=dev: self.device_cast_current_requested.emit(d))
                tile.play_requested.connect(
                    lambda d=dev: self.device_play_requested.emit(d))
                tile.pause_requested.connect(
                    lambda d=dev: self.device_pause_requested.emit(d))
                tile.stop_requested.connect(
                    lambda d=dev: self.device_stop_requested.emit(d))
                tile.volume_changed.connect(
                    lambda v, d=dev: self.device_volume_changed.emit(d, v))
                row, col = divmod(i, 3)
                grid.addWidget(tile, row, col)
            cv.addLayout(grid)

        cl.addWidget(card)

    # ── Groups card ──

    def _build_groups_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(10)

        title = QLabel("Grupos / Zonas")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(title)

        zones = self._groups or [
            {"id": "living", "name": "Sala de estar", "members": 0, "active": False},
            {"id": "bedroom", "name": "Dormitorio", "members": 0, "active": False},
            {"id": "kitchen", "name": "Cocina", "members": 0, "active": False},
            {"id": "all", "name": "Toda la casa", "members": 0, "active": False},
        ]

        for z in zones[:4]:
            row = QHBoxLayout()
            row.setSpacing(8)
            zone_icon = QLabel("")
            zone_icon.setFixedSize(32, 32)
            zone_icon.setStyleSheet(
                "background: rgba(143,183,255,0.08); border-radius: 10px;"
                "border: 1px solid rgba(143,183,255,0.14);")
            from ui.icons import get_pixmap
            zpx = get_pixmap("sidebar_devices", size=18)
            if not zpx.isNull():
                zone_icon.setPixmap(zpx)
                zone_icon.setAlignment(Qt.AlignCenter)
            zname = QLabel(z.get("name", ""))
            zname.setStyleSheet(
                "font-size: 12px; color: rgba(255,255,255,0.78); font-weight: 600;")
            count = QLabel(f"{z.get('members', 0)} parlantes")
            count.setStyleSheet(
                "font-size: 10px; color: rgba(255,255,255,0.38);")
            row.addWidget(zone_icon)
            row.addWidget(zname)
            row.addStretch()
            row.addWidget(count)

            send_btn = _GhostButton("Enviar")
            send_btn.clicked.connect(
                lambda checked, zz=z: self.group_selected_requested.emit(zz))
            row.addWidget(send_btn)
            cl.addLayout(row)

        create_btn = _GhostButton("+ Crear grupo")
        create_btn.clicked.connect(self.create_group_requested.emit)
        cl.addWidget(create_btn)
        cl.addStretch()
        return card

    def _build_groups_full(self):
        cl = self._grid_wrapper
        cl.addWidget(self._build_groups_card())

    # ── Diagnostics card ──

    def _build_diagnostics_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(0)

        title = QLabel("Diagnostico")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(title)
        cl.addSpacing(10)

        rows = [
            "Home Assistant", "Snapserver", "mDNS",
            "API Astra", "Servidor local", "Ultimo error",
            "IP local", "Firewall",
        ]
        self._diag_labels = {}
        for label in rows:
            r = QHBoxLayout()
            r.setSpacing(6)
            r.setContentsMargins(0, 3, 0, 3)
            icon = QLabel("")
            icon.setFixedSize(6, 6)
            icon.setStyleSheet(
                "border-radius: 3px; background: rgba(255,255,255,0.18);")
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.48);")
            val = QLabel("—")
            val.setStyleSheet(
                "font-size: 11px; color: rgba(255,255,255,0.66); font-weight: 600;")
            r.addWidget(icon)
            r.addWidget(lbl)
            r.addStretch()
            r.addWidget(val)
            cl.addLayout(r)
            self._diag_labels[label] = val

        self._refresh_diagnostics_data()
        return card

    def _build_diag_full(self):
        cl = self._grid_wrapper
        cl.addWidget(self._build_diagnostics_card())

    def _build_receivers_full(self):
        cl = self._grid_wrapper
        from integrations.snapcast.receivers import ReceiverWizard
        wizard = ReceiverWizard()
        cl.addWidget(wizard)

    def _refresh_diagnostics_data(self):
        if not hasattr(self, '_diag_labels'):
            return
        updates = {
            "Home Assistant": "Conectado" if self._ha_connected else "No conectado",
            "Snapserver": "Activo" if self._snapserver_running else "Detenido",
            "mDNS": "No verificado",
            "API Astra": "No activa",
            "Servidor local": "No activo",
            "Ultimo error": "—",
            "IP local": "—",
            "Firewall": "—",
        }
        for label, val in self._diag_labels.items():
            val.setText(updates.get(label, "—"))

    # ── Activity card ──

    def _build_activity_card(self) -> QFrame:
        card = _GlassCard()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)

        title = QLabel("Actividad reciente")
        title.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: rgba(255,255,255,0.88);")
        cl.addWidget(title)
        cl.addSpacing(4)

        if not self._activity_log:
            cl.addWidget(self._empty_state_no_btns(
                "Sin actividad reciente",
                "Los eventos de conexion y transmision\napareceran aqui."))
        else:
            now = time.time()
            for entry in self._activity_log[:5]:
                row = QHBoxLayout()
                row.setSpacing(8)
                dot = QLabel("")
                dot.setFixedSize(5, 5)
                dot.setStyleSheet(
                    "border-radius: 2px; background: rgba(255,255,255,0.22);")
                msg = QLabel(entry["msg"])
                msg.setStyleSheet(
                    "font-size: 11px; color: rgba(255,255,255,0.56);")
                delta = max(0, int(now - entry["time"]))
                if delta < 60:
                    time_str = f"{delta}s"
                elif delta < 3600:
                    time_str = f"{delta // 60} min"
                else:
                    time_str = f"{delta // 3600}h"
                ts = QLabel(time_str)
                ts.setStyleSheet(
                    "font-size: 10px; color: rgba(255,255,255,0.28);")
                row.addWidget(dot)
                row.addWidget(msg, 1)
                row.addWidget(ts)
                cl.addLayout(row)
        cl.addStretch()
        return card

    # ── Empty state helper ──

    def _empty_state(self, title: str, subtitle: str,
                     actions: list) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)
        lay.setContentsMargins(16, 24, 16, 24)
        lay.setSpacing(8)

        icon = QLabel("")
        icon.setFixedSize(48, 48)
        icon.setStyleSheet(
            "background: rgba(143,183,255,0.08); border-radius: 16px;"
            "border: 1px solid rgba(143,183,255,0.14);")
        icon.setAlignment(Qt.AlignCenter)
        from ui.icons import get_pixmap
        epix = get_pixmap("sidebar_devices", size=24)
        if not epix.isNull():
            icon.setPixmap(epix)
        lay.addWidget(icon, alignment=Qt.AlignCenter)

        t = QLabel(title)
        t.setAlignment(Qt.AlignCenter)
        t.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.72);")
        lay.addWidget(t)

        s = QLabel(subtitle)
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        s.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.38);")
        lay.addWidget(s)

        if actions:
            ab = QHBoxLayout()
            ab.setAlignment(Qt.AlignCenter)
            ab.setSpacing(8)
            for label, cb in actions:
                btn = _SecondaryButton(label)
                btn.clicked.connect(cb)
                ab.addWidget(btn)
            lay.addLayout(ab)

        return w

    def _empty_state_no_btns(self, title: str, subtitle: str) -> QWidget:
        return self._empty_state(title, subtitle, [])


# ── Widget primitives ──

_STATUS_COLORS = {
    "success": "#8FB7FF", "warning": "rgba(143,183,255,0.72)",
    "error": "rgba(143,183,255,0.48)", "neutral": "rgba(255,255,255,0.52)",
}


class StatusPill(QFrame):
    def __init__(self, label: str, value: str, level: str = "neutral"):
        super().__init__()
        color = _STATUS_COLORS.get(level, _STATUS_COLORS["neutral"])
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.03);"
            "  border: 1px solid rgba(255,255,255,0.02);"
            "  border-radius: 10px; padding: 5px 10px; }"
            "QLabel { background: transparent; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        dot = QLabel("")
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"border-radius: 3px; background: {color};")
        text = QLabel(f"{label} · {value}")
        text.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {color};")
        lay.addWidget(dot)
        lay.addWidget(text)
        self._dot = dot
        self._text = text
        self._label = label

    def set_state(self, value: str, level: str):
        color = _STATUS_COLORS.get(level, _STATUS_COLORS["neutral"])
        self._dot.setStyleSheet(f"border-radius: 3px; background: {color};")
        self._text.setText(f"{self._label} · {value}")
        self._text.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {color};")


_TAB_QSS = (
    "QPushButton { font-size: 11px; font-weight: 600;"
    "  color: rgba(255,255,255,0.56);"
    "  background: rgba(255,255,255,0.03);"
    "  border: 1px solid rgba(255,255,255,0.05);"
    "  border-radius: 9px; padding: 6px 14px; }"
    "QPushButton:checked { color: rgba(255,255,255,0.92);"
    "  background: rgba(143,183,255,0.14);"
    "  border: 1px solid rgba(143,183,255,0.28); }"
    "QPushButton:hover { background: rgba(255,255,255,0.06);"
    "  border: 1px solid rgba(255,255,255,0.10); }")


class _PrimaryButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(
            "QPushButton { color: #FFFFFF; font-size: 12px; font-weight: 700;"
            "  background: rgba(143,183,255,0.18);"
            "  border: 1px solid rgba(143,183,255,0.32);"
            "  border-radius: 13px; padding: 10px 18px; }"
            "QPushButton:hover { background: rgba(143,183,255,0.28);"
            "  border: 1px solid rgba(143,183,255,0.48); }"
            "QPushButton:pressed { background: rgba(143,183,255,0.12); }")
        self.setCursor(Qt.PointingHandCursor)


class _SecondaryButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.78); font-size: 12px;"
            "  font-weight: 600; background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.105);"
            "  border-radius: 13px; padding: 8px 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.10);"
            "  border: 1px solid rgba(255,255,255,0.16); }"
            "QPushButton:pressed { background: rgba(255,255,255,0.04); }")
        self.setCursor(Qt.PointingHandCursor)


class _GhostButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.52); font-size: 11px;"
            "  font-weight: 500; background: transparent;"
            "  border: 1px solid rgba(255,255,255,0.07);"
            "  border-radius: 10px; padding: 6px 12px; }"
            "QPushButton:hover { color: rgba(255,255,255,0.78);"
            "  background: rgba(255,255,255,0.06);"
            "  border: 1px solid rgba(255,255,255,0.12); }")
        self.setCursor(Qt.PointingHandCursor)


class _HeroVisual(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(180)
        self.setStyleSheet("background: transparent;")
        vlay = QVBoxLayout(self)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Abstract circles
        circles = QWidget()
        circles.setStyleSheet("background: transparent;")
        circles.setMinimumHeight(90)
        cl = QVBoxLayout(circles)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setAlignment(Qt.AlignCenter)
        cl.setSpacing(0)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        row.setSpacing(12)
        for size, alpha in [(36, 0.12), (24, 0.08), (16, 0.06)]:
            dot = QLabel("")
            dot.setFixedSize(size, size)
            dot.setStyleSheet(
                f"background: rgba(143,183,255,{alpha});"
                f"border: 1px solid rgba(143,183,255,{alpha + 0.05});"
                f"border-radius: {size // 2}px;")
            row.addWidget(dot)
        cl.addLayout(row)
        vlay.addWidget(circles)
        vlay.addStretch()


class _GlassCard(QFrame):
    def __init__(self, name: str = ""):
        super().__init__()
        if name:
            self.setObjectName(name)
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.025);"
            "  border-radius: 14px;"
            "  border: 1px solid rgba(255,255,255,0.020); }"
            "QLabel { background: transparent; }")


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


class _DeviceTile(QFrame):
    cast_requested = Signal()
    play_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    volume_changed = Signal(int)

    def __init__(self, device: dict):
        super().__init__()
        self._device = device
        self.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.035);"
            "  border-radius: 14px; border: 1px solid rgba(255,255,255,0.06); }"
            "QFrame:hover { background: rgba(255,255,255,0.055);"
            "  border: 1px solid rgba(255,255,255,0.10); }"
            "QLabel { background: transparent; }")
        self.setCursor(Qt.ArrowCursor)
        self.setMinimumHeight(150)
        self.setMaximumHeight(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 8)
        layout.setSpacing(4)

        name = QLabel(device.get("name", "Dispositivo"))
        name.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: rgba(255,255,255,0.88);")
        layout.addWidget(name)

        state_text = device.get("state", "unavailable")
        if device.get("media_title"):
            state_text = device["media_title"]
            if device.get("media_artist"):
                state_text += f" — {device['media_artist']}"
        sub = QLabel(state_text)
        sub.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.42);")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        d_type = device.get("device_type") or device.get("backend") or ""
        room = device.get("room") or device.get("area") or ""
        type_label = f"{d_type}{' · ' + room if room else ''}"
        t = QLabel(type_label)
        t.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.35);")
        layout.addWidget(t)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(4)

        for icon_name, signal_name in [
            ("warm_play", "play_requested"),
            ("warm_pause", "pause_requested"),
            ("warm_next", "stop_requested"),
        ]:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.06);"
                "  border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; }"
                "QPushButton:hover { background: rgba(255,255,255,0.14);"
                "  border: 1px solid rgba(255,255,255,0.16); }")
            btn.setCursor(Qt.PointingHandCursor)
            from ui.icons import get_qicon
            qicon = get_qicon(icon_name, size=18)
            if not qicon.isNull():
                btn.setIcon(qicon)
            sig = getattr(self, signal_name)
            btn.clicked.connect(sig.emit)
            btn.setToolTip({"warm_play": "Play", "warm_pause": "Pause",
                            "warm_next": "Stop"}[icon_name])
            ctrl.addWidget(btn)

        cast_btn = QPushButton("Enviar aqui")
        cast_btn.setStyleSheet(
            "QPushButton { font-size: 10px; color: rgba(255,255,255,0.78);"
            "  font-weight: 600; background: rgba(255,255,255,0.10);"
            "  border: 1px solid rgba(255,255,255,0.14); border-radius: 6px;"
            "  padding: 3px 8px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.18);"
            "  border: 1px solid rgba(255,255,255,0.22); }")
        cast_btn.setCursor(Qt.PointingHandCursor)
        cast_btn.clicked.connect(self.cast_requested.emit)
        ctrl.addWidget(cast_btn)
        ctrl.addStretch()

        vol = device.get("volume_level")
        v = int(vol * 100) if isinstance(vol, float) else 50
        vol_slider = QSlider(Qt.Horizontal)
        vol_slider.setRange(0, 100)
        vol_slider.setValue(v)
        vol_slider.setFixedWidth(70)
        vol_slider.setStyleSheet(
            "QSlider::groove:horizontal {"
            "  background: rgba(255,255,255,0.08); height: 4px;"
            "  border-radius: 2px; }"
            "QSlider::handle:horizontal {"
            "  background: rgba(255,255,255,0.70); width: 10px;"
            "  height: 10px; margin: -3px 0; border-radius: 5px; }"
            "QSlider::sub-page:horizontal {"
            "  background: rgba(255,255,255,0.35); border-radius: 2px; }")
        vol_slider.setCursor(Qt.PointingHandCursor)
        vol_slider.valueChanged.connect(self.volume_changed.emit)
        ctrl.addWidget(vol_slider)

        layout.addLayout(ctrl)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.cast_requested.emit()
