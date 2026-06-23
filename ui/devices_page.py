"""Michi Sync Suite — professional device sync hub."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, card_title_qss, card_desc_qss, section_label_qss,
)
from ui.services.device_registry import PairedDevice
from ui.services.device_sync_controller import DeviceSyncController
from ui.services.transcode_service import TRANSCODE_PROFILES


class DevicesPage(QWidget):
    def __init__(self, db=None, window=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("devicesPage")
        self._db = db
        self._win = window
        self._controller = DeviceSyncController(db) if db else None
        self._build_ui()
        QTimer.singleShot(500, self._refresh_devices)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("devicesScroll")

        content = QWidget()
        content.setObjectName("devicesContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Michi Sync Suite")
        title.setObjectName("devicesTitle")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "Sincroniza tu música con teléfonos, tablets, reproductores y "
            "dispositivos USB. Transferencia local tipo LocalSend."
        )
        subtitle.setObjectName("devicesSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        sec_label = QLabel("DISPOSITIVOS EMPAREJADOS")
        sec_label.setStyleSheet(section_label_qss())
        content_layout.addWidget(sec_label)

        self._paired_container = QVBoxLayout()
        self._paired_container.setSpacing(10)
        content_layout.addLayout(self._paired_container)

        sec_label2 = QLabel("RED LOCAL")
        sec_label2.setStyleSheet(section_label_qss())
        content_layout.addWidget(sec_label2)

        scan_row = QHBoxLayout()
        self._scan_btn = QPushButton("Buscar dispositivos")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.clicked.connect(self._on_scan)
        scan_row.addWidget(self._scan_btn)
        scan_row.addStretch()
        content_layout.addLayout(scan_row)

        self._scan_results = QLabel("")
        self._scan_results.setWordWrap(True)
        self._scan_results.setStyleSheet("QLabel { color: rgba(255,255,255,0.52); font-size: 12px; }")
        content_layout.addWidget(self._scan_results)

        sec_label3 = QLabel("PERFILES DE SINCRONIZACIÓN")
        sec_label3.setStyleSheet(section_label_qss())
        content_layout.addWidget(sec_label3)

        profiles_row = QHBoxLayout()
        profiles_row.setSpacing(12)
        for pid, pinfo in TRANSCODE_PROFILES.items():
            card = QFrame()
            card.setObjectName(f"profileCard_{pid}")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(16, 12, 16, 12)
            c_layout.setSpacing(4)
            pname = QLabel(pinfo["name"])
            pname.setStyleSheet(card_title_qss().replace("16px", "13px"))
            c_layout.addWidget(pname)
            pdesc = QLabel(pinfo["description"])
            pdesc.setWordWrap(True)
            pdesc.setStyleSheet(card_desc_qss())
            c_layout.addWidget(pdesc)
            card.setStyleSheet(glass_card_qss(f"profileCard_{pid}"))
            profiles_row.addWidget(card)
        content_layout.addLayout(profiles_row)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _refresh_devices(self):
        self._show_paired_devices()

    def _show_paired_devices(self):
        while self._paired_container.count():
            item = self._paired_container.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not self._controller:
            return

        devices = self._controller.paired_devices
        if not devices:
            empty = QLabel("No hay dispositivos emparejados. Busca dispositivos en la red local.")
            empty.setStyleSheet("QLabel { color: rgba(255,255,255,0.42); font-size: 12px; padding: 16px; }")
            self._paired_container.addWidget(empty)
            return

        for d in devices:
            card = self._build_device_card(d)
            self._paired_container.addWidget(card)

    def _build_device_card(self, device: PairedDevice) -> QFrame:
        card = QFrame()
        card.setObjectName(f"pairedCard_{device.device_id}")

        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(16, 14, 16, 14)
        c_layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(4)
        name = QLabel(device.name)
        name.setStyleSheet("QLabel { color: rgba(255,255,255,0.88); font-size: 14px; font-weight: 600; }")
        info.addWidget(name)
        meta = QLabel(f"{device.device_type} · {device.host}:{device.port} · {device.last_seen or 'nunca'}")
        meta.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; }")
        info.addWidget(meta)
        c_layout.addLayout(info, 1)

        sync_btn = QPushButton("Sincronizar")
        sync_btn.setCursor(Qt.PointingHandCursor)
        sync_btn.setStyleSheet(glass_button_qss("primary"))
        c_layout.addWidget(sync_btn)

        forget_btn = QPushButton("Olvidar")
        forget_btn.setCursor(Qt.PointingHandCursor)
        forget_btn.clicked.connect(lambda: self._on_unpair(device.device_id))
        c_layout.addWidget(forget_btn)

        card.setStyleSheet(glass_card_qss(f"pairedCard_{device.device_id}", "elevated"))
        return card

    def _on_scan(self):
        self._scan_btn.setEnabled(False)
        self._scan_results.setText("Escaneando red local...")

        from integrations.connections.discovery_manager import DiscoveryManager
        mgr = DiscoveryManager(timeout=0.3)
        hosts = mgr.scan_known_ports()
        mdns = mgr.scan_mdns()
        all_found = hosts + mdns

        found_devices = []
        for s in all_found:
            if hasattr(self._controller, 'check_device_available'):
                available = self._controller.check_device_available(s.host, s.port)
                if available:
                    found_devices.append(s)

        self._scan_btn.setEnabled(True)
        if found_devices:
            lines = ["Dispositivos detectados:"]
            for s in found_devices[:5]:
                lines.append(
                    f"  {s.host}:{s.port} ({s.server_type}) — "
                    f"Click para emparejar"
                )
            self._scan_results.setText("\n".join(lines))
        else:
            self._scan_results.setText(
                "No se detectaron dispositivos. Asegúrate de que la app "
                "Michi Sync esté abierta en tu Android."
            )

    def _on_unpair(self, device_id: str):
        if self._controller:
            self._controller.unpair_device(device_id)
            self._show_paired_devices()

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#devicesPage { background: #090B11; }
            QScrollArea#devicesScroll { background: transparent; border: none; }
            QWidget#devicesContent { background: transparent; }
            QLabel#devicesTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#devicesSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
        self._scan_btn.setStyleSheet(glass_button_qss("primary"))
