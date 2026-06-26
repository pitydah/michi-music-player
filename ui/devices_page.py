"""Michi Sync Suite — professional device sync hub with content selector + manifest viewer."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QComboBox,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss,
    card_title_qss, card_desc_qss, section_label_qss,
)
from ui.services.device_registry import PairedDevice
from ui.services.device_sync_controller import DeviceSyncController
from ui.services.transcode_service import TRANSCODE_PROFILES


class DevicesPage(QWidget):
    def __init__(self, db=None, sync_manager=None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("devicesPage")
        self._db = db
        self._sync_mgr = sync_manager
        self._controller = DeviceSyncController(db) if db else None
        if self._controller and self._sync_mgr:
            self._sync_mgr.set_manifest_provider(
                self._controller.get_manifest_public)
            self._sync_mgr.set_delta_provider(
                self._controller.build_delta_manifest)
        self._discovered: list[dict] = []
        self._content_mode = "favorites"
        self._build_ui()
        self._wire_sync_manager()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        sbar = scroll.verticalScrollBar()
        sbar.setSingleStep(20)
        scroll.setObjectName("devicesScroll")

        content = QWidget()
        content.setObjectName("devicesContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(20)

        # Icon + title row
        from ui.icons import get_pixmap
        icon_row = QHBoxLayout()
        icon_row.setSpacing(12)
        icon_lbl = QLabel()
        pix = get_pixmap("michi_sync", size=40)
        if pix and not pix.isNull():
            icon_lbl.setPixmap(pix)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        icon_row.addWidget(icon_lbl)

        title = QLabel("Michi Sync Suite")
        title.setObjectName("devicesTitle")
        icon_row.addWidget(title)
        icon_row.addStretch()
        cl.addLayout(icon_row)

        self._subtitle = QLabel("Sincroniza tu música con tus dispositivos.")
        self._subtitle.setObjectName("devicesSubtitle")
        self._subtitle.setWordWrap(True)
        cl.addWidget(self._subtitle)

        # ── Server summary ──
        self._build_server_card(cl)

        # ── Content selector ──
        self._build_content_selector(cl)

        # ── Paired devices ──
        sec1 = QLabel("EMPAREJADOS")
        sec1.setStyleSheet(section_label_qss())
        cl.addWidget(sec1)
        self._paired_layout = QVBoxLayout()
        self._paired_layout.setSpacing(10)
        cl.addLayout(self._paired_layout)

        # ── Discovered ──
        sec2 = QLabel("RED LOCAL")
        sec2.setStyleSheet(section_label_qss())
        cl.addWidget(sec2)
        self._discovered_layout = QVBoxLayout()
        self._discovered_layout.setSpacing(10)
        cl.addLayout(self._discovered_layout)

        # ── Manifest viewer ──
        sec3 = QLabel("ÚLTIMO MANIFIESTO")
        sec3.setStyleSheet(section_label_qss())
        cl.addWidget(sec3)
        self._manifest_viewer = QLabel("Sin manifiesto generado.")
        self._manifest_viewer.setWordWrap(True)
        self._manifest_viewer.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.64); font-size: 11px; "
            "font-family: monospace; }")
        cl.addWidget(self._manifest_viewer)

        # ── Test buttons ──
        test_row = QHBoxLayout()
        test_row.setSpacing(8)
        for label, slot in [
            ("Probar /api/ping", self._on_test_ping),
            ("Probar manifiesto", self._on_test_manifest),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(glass_button_qss("ghost"))
            btn.clicked.connect(slot)
            test_row.addWidget(btn)
        test_row.addStretch()
        cl.addLayout(test_row)

        # ── Profiles ──
        profiles_row = QHBoxLayout()
        profiles_row.setSpacing(12)
        for pid, pinfo in TRANSCODE_PROFILES.items():
            card = QFrame()
            card.setObjectName(f"profile_{pid}")
            cl2 = QVBoxLayout(card)
            cl2.setContentsMargins(16, 12, 16, 12)
            cl2.setSpacing(4)
            pn = QLabel(pinfo["name"])
            pn.setStyleSheet(card_title_qss().replace("16px", "13px"))
            cl2.addWidget(pn)
            pd = QLabel(pinfo["description"])
            pd.setWordWrap(True)
            pd.setStyleSheet(card_desc_qss())
            cl2.addWidget(pd)
            card.setStyleSheet(glass_card_qss(f"profile_{pid}"))
            profiles_row.addWidget(card)
        cl.addLayout(profiles_row)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

    def _build_server_card(self, cl):
        card = QFrame()
        card.setObjectName("syncServerCard")
        c2 = QVBoxLayout(card)
        c2.setContentsMargins(20, 16, 20, 16)
        c2.setSpacing(8)

        row1 = QHBoxLayout()
        self._status_label = QLabel("Sync: inactivo")
        self._status_label.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.56); font-size: 12px; }")
        row1.addWidget(self._status_label)
        row1.addStretch()

        self._toggle_btn = QPushButton("Activar Michi Sync")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._on_toggle_sync)
        row1.addWidget(self._toggle_btn)
        c2.addLayout(row1)

        self._server_info = QLabel("Puerto 53318 · 0 dispositivos emparejados")
        self._server_info.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.38); font-size: 11px; }")
        c2.addWidget(self._server_info)

        card.setStyleSheet(glass_card_qss("syncServerCard", "elevated"))
        cl.addWidget(card)

    def _build_content_selector(self, cl):
        row = QHBoxLayout()
        row.setSpacing(8)
        sel_label = QLabel("Sincronizar:")
        sel_label.setStyleSheet("QLabel { color: rgba(255,255,255,0.52); font-size: 12px; }")
        row.addWidget(sel_label)

        self._content_combo = QComboBox()
        self._content_combo.addItem("Favoritos", "favorites")
        self._content_combo.addItem("Primeras 30 canciones", "sample")
        self._content_combo.addItem("Toda la biblioteca", "all")
        self._content_combo.currentIndexChanged.connect(
            lambda: setattr(self, '_content_mode',
                            self._content_combo.currentData()))
        row.addWidget(self._content_combo)
        row.addStretch()
        cl.addLayout(row)

    def _wire_sync_manager(self):
        if not self._sync_mgr:
            return
        self._sync_mgr.peer_found.connect(self._on_peer_found)
        self._sync_mgr.peer_lost.connect(self._on_peer_lost)
        self._sync_mgr.client_connected.connect(self._on_client_connected)

    def _refresh(self):
        self._update_server_card()
        self._show_paired()
        self._show_discovered()
        self._update_manifest_viewer()

    def _update_server_card(self):
        active = self._sync_mgr and self._sync_mgr.is_active
        paired = len(self._controller.paired_devices) if self._controller else 0
        url = f"http://<ip>:{53318 if active else 0}"

        if active:
            self._status_label.setText("Sync: ACTIVO")
            self._toggle_btn.setText("Desactivar")
            self._toggle_btn.setStyleSheet(glass_button_qss("secondary"))
        else:
            self._status_label.setText("Sync: inactivo")
            self._toggle_btn.setText("Activar Michi Sync")
            self._toggle_btn.setStyleSheet(glass_button_qss("primary"))

        self._server_info.setText(
            f"Puerto 53318 · URL: {url} · {paired} dispositivos emparejados"
        )

    def _show_paired(self):
        while self._paired_layout.count():
            w = self._paired_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not self._controller:
            return
        devices = self._controller.paired_devices
        if not devices:
            empty = QLabel("Sin dispositivos emparejados.")
            empty.setStyleSheet("QLabel { color: rgba(255,255,255,0.54); font-size: 12px; padding: 8px; }")
            self._paired_layout.addWidget(empty)
            return
        for d in devices:
            self._paired_layout.addWidget(
                self._build_device_card(d, paired=True))

    def _show_discovered(self):
        while self._discovered_layout.count():
            w = self._discovered_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not self._discovered:
            empty = QLabel("No hay dispositivos en la red local.")
            empty.setStyleSheet("QLabel { color: rgba(255,255,255,0.54); font-size: 12px; padding: 8px; }")
            self._discovered_layout.addWidget(empty)
            return
        for d in self._discovered:
            self._discovered_layout.addWidget(
                self._build_device_card(d, paired=False))

    def _update_manifest_viewer(self):
        if not self._controller:
            return
        text = "Sin manifiesto generado."
        for d in self._controller.paired_devices:
            public = self._controller.get_manifest_public(d.device_id)
            if public:
                tracks = public.get("tracks", [])
                preview = []
                for t in tracks[:10]:
                    chk = t.get("checksum", "")[:8]
                    preview.append(
                        f"  {t['title'][:40]} · {t['artist'][:30]}\n"
                        f"    {t['download_path']}  SHA256:{chk}"
                    )
                text = (
                    f"Manifest: {public.get('manifest_id')}\n"
                    f"Dispositivo: {d.device_id}\n"
                    f"Tracks: {public.get('total_tracks')} · "
                    f"Tamaño: {public.get('total_size',0)/1048576:.1f} MB\n"
                    f"Creado: {public.get('created_at')}\n\n"
                    + "\n".join(preview)
                )
                break
        self._manifest_viewer.setText(text)

    def _build_device_card(self, device, paired: bool = False) -> QFrame:
        card = QFrame()
        card_id = device.get("device_id", device.get("alias", "unknown"))
        card.setObjectName(f"devCard_{card_id}")
        c2 = QHBoxLayout(card)
        c2.setContentsMargins(16, 14, 16, 14)
        c2.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(4)
        name = device.get("name", device.get("alias", "Dispositivo"))
        nl = QLabel(str(name))
        nl.setStyleSheet("QLabel { color: rgba(255,255,255,0.88); font-size: 14px; font-weight: 600; }")
        info.addWidget(nl)

        if paired and isinstance(device, PairedDevice):
            meta = f"{device.device_type} · {device.host}:{device.port}"
        else:
            meta = f"Red local · {device.get('host', device.get('ip', ''))}"
        ml = QLabel(meta)
        ml.setStyleSheet("QLabel { color: rgba(255,255,255,0.44); font-size: 11px; }")
        info.addWidget(ml)
        c2.addLayout(info, 1)

        if paired:
            sid = QPushButton("Sincronizar ahora")
            sid.setCursor(Qt.PointingHandCursor)
            sid.setStyleSheet(glass_button_qss("primary"))
            if isinstance(device, PairedDevice):
                did = device.device_id
                sid.clicked.connect(lambda c=None, d=did: self._on_sync_device(d))
            c2.addWidget(sid)

            forget = QPushButton("Olvidar")
            forget.setCursor(Qt.PointingHandCursor)
            forget.setStyleSheet(glass_button_qss("danger"))
            if hasattr(device, "device_id"):
                did = device.device_id
                forget.clicked.connect(lambda c=None, d=did: self._on_unpair(d))
            c2.addWidget(forget)

            view = QPushButton("Manifiesto")
            view.setCursor(Qt.PointingHandCursor)
            view.setStyleSheet(glass_button_qss("secondary"))
            if isinstance(device, PairedDevice):
                did = device.device_id
                view.clicked.connect(
                    lambda c=None, d=did: (
                        self._show_manifest_for(d), self._update_manifest_viewer()
                    ))
            c2.addWidget(view)
        else:
            pair = QPushButton("Emparejar")
            pair.setCursor(Qt.PointingHandCursor)
            pair.setStyleSheet(glass_button_qss("accent"))
            alias = device.get("alias", "")
            ip_val = device.get("ip", device.get("host", ""))
            pair.clicked.connect(lambda c=None, a=alias, h=ip_val: self._on_pair(a, h))
            c2.addWidget(pair)

        card.setStyleSheet(glass_card_qss(f"devCard_{card_id}",
                            "elevated" if paired else "base"))
        return card

    def _on_toggle_sync(self):
        if self._sync_mgr:
            self._sync_mgr.toggle()
        self._update_server_card()

    def _on_peer_found(self, alias: str, ip: str):
        for d in self._discovered:
            if d.get("alias") == alias:
                d["ip"] = ip
                self._show_discovered()
                return
        device_id = f"sync_{alias}"
        if self._sync_mgr:
            info = self._sync_mgr.get_peer_info(alias)
            if info:
                device_id = info["device_id"]
        self._discovered.append({
            "alias": alias, "ip": ip, "device_id": device_id,
        })
        self._show_discovered()

    def _on_peer_lost(self, alias: str):
        self._discovered = [d for d in self._discovered
                           if d.get("alias") != alias]
        self._show_discovered()

    def _on_client_connected(self, alias: str):
        for d in self._discovered:
            if d.get("alias") == alias:
                d["connected"] = True
                self._show_discovered()
                return

    def _on_pair(self, alias: str, ip: str):
        if not self._controller:
            return
        device_id = f"sync_{alias}"
        device_model = ""
        device_type = "android"
        if self._sync_mgr:
            info = self._sync_mgr.get_peer_info(alias)
            if info:
                device_id = info.get("device_id", device_id)
                device_model = info.get("device_model", "")
                device_type = info.get("device_type", "android")
        if device_id == f"sync_{alias}":
            self._subtitle.setText(
                "Dispositivo sin ID persistente.")
        self._controller.pair_device(
            device_id, alias, host=ip,
            device_type=device_type, device_model=device_model,
        )
        self._discovered = [d for d in self._discovered
                           if d.get("alias") != alias]
        self._show_discovered()
        self._show_paired()
        self._update_server_card()

    def _on_unpair(self, device_id: str):
        if self._controller:
            self._controller.unpair_device(device_id)
            self._show_paired()
            self._update_server_card()

    def _on_sync_device(self, device_id: str):
        if not self._controller:
            return
        mode = self._content_mode
        manifest = None
        if mode == "favorites":
            manifest = self._controller.build_manifest_from_favorites(device_id)
        elif mode == "all":
            manifest = self._controller.build_manifest_from_all(device_id)
        else:
            items = self._db.get_all()[:30] if hasattr(self._db, "get_all") else []
            tids = [getattr(i, "id", 0) for i in items if getattr(i, "id", 0)]
            manifest = self._controller.build_manifest(tids, device_id)

        if manifest and manifest.total_tracks > 0:
            size_mb = manifest.total_size / (1024 * 1024)
            self._subtitle.setText(
                f"Manifiesto listo: {manifest.total_tracks} canciones, "
                f"{size_mb:.1f} MB. Abre Michi Sync en tu Android.")
        else:
            self._subtitle.setText("No se pudo generar el manifiesto.")
        self._update_manifest_viewer()

    def _show_manifest_for(self, device_id: str):
        if not self._controller:
            return
        public = self._controller.get_manifest_public(device_id)
        if public:
            self._manifest_viewer.setText(
                f"Mostrando manifiesto para {device_id}\n"
                f"Tracks: {public.get('total_tracks')} · "
                f"Tamaño: {public.get('total_size',0)/1048576:.1f} MB"
            )
        else:
            self._manifest_viewer.setText("Sin manifiesto para este dispositivo.")

    def _on_test_ping(self):
        if not self._sync_mgr:
            self._subtitle.setText("Servidor no iniciado.")
            return
        import urllib.request
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:53318/api/ping", method="GET")
            with urllib.request.urlopen(req, timeout=3) as r:
                import json
                data = json.loads(r.read().decode())
                self._subtitle.setText(
                    f"/api/ping OK — version {data.get('version','?')}")
        except Exception as e:
            self._subtitle.setText(f"Error: {e}")

    def _on_test_manifest(self):
        if not self._controller:
            return
        devices = self._controller.paired_devices
        if not devices:
            self._subtitle.setText("Sin dispositivos emparejados.")
            return
        public = self._controller.get_manifest_public(devices[0].device_id)
        if public:
            self._subtitle.setText(
                f"Manifiesto OK: {public.get('total_tracks')} tracks, "
                f"{public.get('total_size',0)/1048576:.1f} MB")
        else:
            self._subtitle.setText("Sin manifiesto. Genera uno primero.")

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#devicesPage { background: #090B11; }
            QScrollArea#devicesScroll { background: transparent; border: none; }
            QWidget#devicesContent { background: transparent; }
            QLabel#devicesTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#devicesSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
            QComboBox {
                background: rgba(255,255,255,0.045);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px;
                padding: 6px 10px;
                color: rgba(255,255,255,0.82);
                font-size: 12px;
            }
        """)
