"""Michi Sync Suite — professional device sync hub using existing SyncManager."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
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
        self._discovered: list[dict] = []
        self._build_ui()
        self._wire_sync_manager()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        sbar = scroll.verticalScrollBar()
        sbar.setSingleStep(20)
        scroll.setObjectName("devicesScroll")

        content = QWidget()
        content.setObjectName("devicesContent")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(20)

        title = QLabel("Michi Sync Suite")
        title.setObjectName("devicesTitle")
        cl.addWidget(title)

        self._subtitle = QLabel(
            "Sincroniza tu musica con telefonos, tablets y dispositivos."
        )
        self._subtitle.setObjectName("devicesSubtitle")
        self._subtitle.setWordWrap(True)
        cl.addWidget(self._subtitle)

        # ── Sync status ──
        status_row = QHBoxLayout()
        self._status_label = QLabel("Sync: inactivo")
        self._status_label.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 12px; }")
        status_row.addWidget(self._status_label)
        status_row.addStretch()

        self._toggle_sync_btn = QPushButton("Activar Michi Sync")
        self._toggle_sync_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_sync_btn.clicked.connect(self._on_toggle_sync)
        status_row.addWidget(self._toggle_sync_btn)
        cl.addLayout(status_row)

        cl.addSpacing(4)

        # ── Paired devices ──
        sec1 = QLabel("EMPAREJADOS")
        sec1.setStyleSheet(section_label_qss())
        cl.addWidget(sec1)
        self._paired_layout = QVBoxLayout()
        self._paired_layout.setSpacing(10)
        cl.addLayout(self._paired_layout)

        # ── Discovered on network ──
        sec2 = QLabel("RED LOCAL")
        sec2.setStyleSheet(section_label_qss())
        cl.addWidget(sec2)
        self._discovered_layout = QVBoxLayout()
        self._discovered_layout.setSpacing(10)
        cl.addLayout(self._discovered_layout)

        # ── Profiles ──
        sec3 = QLabel("PERFILES")
        sec3.setStyleSheet(section_label_qss())
        cl.addWidget(sec3)

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

    def _wire_sync_manager(self):
        if not self._sync_mgr:
            return
        self._sync_mgr.peer_found.connect(self._on_peer_found)
        self._sync_mgr.peer_lost.connect(self._on_peer_lost)
        self._sync_mgr.client_connected.connect(self._on_client_connected)

    def _refresh(self):
        self._update_sync_status()
        self._show_paired()
        self._show_discovered()

    def _update_sync_status(self):
        active = self._sync_mgr and self._sync_mgr.is_active
        if active:
            self._status_label.setText("Sync: activo — puerto 53318")
            self._toggle_sync_btn.setText("Desactivar")
            self._toggle_sync_btn.setStyleSheet(glass_button_qss("secondary"))
            self._subtitle.setText(
                "Servidor activo. Tu biblioteca esta disponible para "
                "dispositivos en la red local."
            )
        else:
            self._status_label.setText("Sync: inactivo")
            self._toggle_sync_btn.setText("Activar Michi Sync")
            self._toggle_sync_btn.setStyleSheet(glass_button_qss("primary"))
            self._subtitle.setText(
                "Activa el servidor para sincronizar musica con tus "
                "dispositivos en la red local."
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
            empty.setStyleSheet("QLabel { color: rgba(255,255,255,0.38); font-size: 12px; padding: 8px; }")
            self._paired_layout.addWidget(empty)
            return

        for d in devices:
            card = self._build_device_card(d, paired=True)
            self._paired_layout.addWidget(card)

    def _show_discovered(self):
        while self._discovered_layout.count():
            w = self._discovered_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        if not self._discovered:
            empty = QLabel("No hay dispositivos en la red local.")
            empty.setStyleSheet("QLabel { color: rgba(255,255,255,0.38); font-size: 12px; padding: 8px; }")
            self._discovered_layout.addWidget(empty)
            return

        for d in self._discovered:
            card = self._build_device_card(d, paired=False)
            self._discovered_layout.addWidget(card)

    def _build_device_card(self, device, paired: bool = False) -> QFrame:
        card = QFrame()
        card_id = device.get("device_id", device.get("alias", "unknown"))
        card.setObjectName(f"devCard_{card_id}")

        cl2 = QHBoxLayout(card)
        cl2.setContentsMargins(16, 14, 16, 14)
        cl2.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(4)

        name = device.get("name", device.get("alias", "Dispositivo"))
        nl = QLabel(str(name))
        nl.setStyleSheet("QLabel { color: rgba(255,255,255,0.88); font-size: 14px; font-weight: 600; }")
        info.addWidget(nl)

        if paired and isinstance(device, PairedDevice):
            meta = f"{device.device_type} · {device.host}:{device.port}"
        else:
            host = device.get("host", device.get("ip", ""))
            meta = f"Red local · {host}"
        ml = QLabel(meta)
        ml.setStyleSheet("QLabel { color: rgba(255,255,255,0.44); font-size: 11px; }")
        info.addWidget(ml)
        cl2.addLayout(info, 1)

        if paired:
            sync_btn = QPushButton("Sincronizar ahora")
            sync_btn.setCursor(Qt.PointingHandCursor)
            sync_btn.setStyleSheet(glass_button_qss("primary"))
            cl2.addWidget(sync_btn)

            forget_btn = QPushButton("Olvidar")
            forget_btn.setCursor(Qt.PointingHandCursor)
            if hasattr(device, "device_id"):
                did = device.device_id
                forget_btn.clicked.connect(lambda c=None, d=did: self._on_unpair(d))
            cl2.addWidget(forget_btn)
        else:
            pair_btn = QPushButton("Emparejar")
            pair_btn.setCursor(Qt.PointingHandCursor)
            alias = device.get("alias", "")
            ip_val = device.get("ip", device.get("host", ""))
            pair_btn.clicked.connect(
                lambda c=None, a=alias, h=ip_val: self._on_pair(a, h))
            cl2.addWidget(pair_btn)

        card.setStyleSheet(glass_card_qss(f"devCard_{card_id}",
                            "elevated" if paired else "base"))
        return card

    def _on_toggle_sync(self):
        if self._sync_mgr:
            self._sync_mgr.toggle()
        self._update_sync_status()

    def _on_peer_found(self, alias: str, ip: str):
        for d in self._discovered:
            if d.get("alias") == alias:
                d["ip"] = ip
                self._show_discovered()
                return
        self._discovered.append({"alias": alias, "ip": ip})
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
        if self._controller:
            did = f"sync_{alias}"
            self._controller.pair_device(did, alias, host=ip)
            self._discovered = [d for d in self._discovered
                               if d.get("alias") != alias]
            self._show_discovered()
            self._show_paired()

    def _on_unpair(self, device_id: str):
        if self._controller:
            self._controller.unpair_device(device_id)
            self._show_paired()

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#devicesPage { background: #090B11; }
            QScrollArea#devicesScroll { background: transparent; border: none; }
            QWidget#devicesContent { background: transparent; }
            QLabel#devicesTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#devicesSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
