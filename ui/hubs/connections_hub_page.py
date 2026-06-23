"""ConnectionsHubPage — real servers, Home Audio, devices, diagnostics."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QProgressBar,
)

from ui.central.central_styles import glass_card_qss, glass_button_qss, glass_chip_qss


class ConnectionsHubPage(QWidget):
    def __init__(self, db=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("connectionsHubPage")
        self._db = db
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("connectionsHubScroll")

        content = QWidget()
        content.setObjectName("connectionsHubContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 32, 40, 32)
        content_layout.setSpacing(20)

        title = QLabel("Conexiones")
        title.setObjectName("connectionsHubTitle")
        content_layout.addWidget(title)

        servers = self._get_servers()
        subtitle = QLabel(
            f"Servidores musicales, Home Audio, dispositivos y diagnóstico de red. "
            f"{len(servers)} servidores configurados."
        )
        subtitle.setObjectName("connectionsHubSubtitle")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        if servers:
            server_card = QFrame()
            server_card.setObjectName("connectionsCard_servers")
            sc_layout = QVBoxLayout(server_card)
            sc_layout.setContentsMargins(20, 16, 20, 16)
            sc_layout.setSpacing(8)

            srv_title = QLabel(f"Servidores guardados ({len(servers)})")
            srv_title.setStyleSheet("QLabel { color: rgba(255,255,255,0.72); font-size: 13px; font-weight: 600; }")
            sc_layout.addWidget(srv_title)

            for srv in servers:
                srv_label = QLabel(f"  {srv.get('name', 'Servidor')} — {srv.get('stype', 'navidrome')} ({srv.get('url', '')})")
                srv_label.setStyleSheet(
                    "QLabel { color: rgba(143,183,255,0.62); font-size: 12px; }"
                )
                sc_layout.addWidget(srv_label)

            server_card.setStyleSheet(
                "QFrame { background: rgba(143,183,255,0.04); border: 1px solid rgba(143,183,255,0.08); "
                "border-radius: 12px; }"
            )
            content_layout.addWidget(server_card)

        devices = self._get_devices()
        if devices:
            dev_card = QFrame()
            dev_card.setObjectName("connectionsCard_devices")
            dc_layout = QVBoxLayout(dev_card)
            dc_layout.setContentsMargins(20, 16, 20, 16)
            dc_layout.setSpacing(8)

            dev_title = QLabel(f"Dispositivos ({len(devices)})")
            dev_title.setStyleSheet("QLabel { color: rgba(255,255,255,0.72); font-size: 13px; font-weight: 600; }")
            dc_layout.addWidget(dev_title)

            dev_row = QHBoxLayout()
            dev_row.setSpacing(8)
            for d in devices:
                dname = d.get("name", d.get("mount", "Dispositivo"))
                dmount = d.get("mount", "")
                chip = QPushButton(dname)
                chip.setToolTip(dmount)
                chip.setCursor(Qt.PointingHandCursor)
                chip.setStyleSheet(glass_chip_qss().replace("QLabel", "QPushButton") + "QPushButton:hover { background: rgba(143,183,255,0.08); }")
                chip.setFlat(True)
                chip.clicked.connect(lambda checked=None, m=dmount: self._navigate(f"dev:{m}"))
                dev_row.addWidget(chip)
            dev_row.addStretch()
            dc_layout.addLayout(dev_row)

            dev_card.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.020); border: 1px solid rgba(255,255,255,0.04); "
                "border-radius: 12px; }"
            )
            content_layout.addWidget(dev_card)

        discover_card = QFrame()
        discover_card.setObjectName("connectionsCard_discover")
        dc_layout = QVBoxLayout(discover_card)
        dc_layout.setContentsMargins(20, 16, 20, 16)
        dc_layout.setSpacing(8)

        dc_title = QLabel("Buscar servidores en la red")
        dc_title.setStyleSheet("QLabel { color: rgba(255,255,255,0.78); font-size: 13px; font-weight: 600; }")
        dc_layout.addWidget(dc_title)

        btn_row = QVBoxLayout()
        self._scan_btn = QPushButton("Escanear red local")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.clicked.connect(self._on_scan_network)
        btn_row.addWidget(self._scan_btn)

        self._scan_progress = QProgressBar()
        self._scan_progress.setRange(0, 0)
        self._scan_progress.setVisible(False)
        btn_row.addWidget(self._scan_progress)

        self._scan_results = QLabel("")
        self._scan_results.setWordWrap(True)
        self._scan_results.setStyleSheet("QLabel { color: rgba(143,183,255,0.52); font-size: 11px; }")
        self._scan_results.setVisible(False)
        btn_row.addWidget(self._scan_results)

        self._connect_btn = QPushButton("Conectar servidor detectado")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.setVisible(False)
        self._connect_btn.clicked.connect(self._on_connect_discovered)
        btn_row.addWidget(self._connect_btn)

        dc_layout.addLayout(btn_row)
        discover_card.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.020); border: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 12px; }"
        )
        content_layout.addWidget(discover_card)

        actions = [
            ("add_server", "Añadir servidor musical",
             "Conecta Navidrome, Jellyfin o Subsonic para acceder a tu música remota."),
            ("home_audio", "Home Audio",
             "Audio multiroom, parlantes Snapcast y Home Assistant."),
        ]

        for key, label, desc in actions:
            card = self._build_card(key, label, desc)
            content_layout.addWidget(card)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._apply_qss()

    def _on_scan_network(self):
        self._scan_btn.setEnabled(False)
        self._scan_progress.setVisible(True)
        self._scan_results.setVisible(True)
        self._scan_results.setText("Escaneando red local...")

        class ScanWorker(QThread):
            finished = Signal(list)
            def run(self):
                from integrations.connections.discovery_manager import DiscoveryManager
                mgr = DiscoveryManager(timeout=0.3)
                results = mgr.scan_known_ports()
                mdns = mgr.scan_mdns()
                all_results = results + mdns
                classified = [mgr.build_discovered_server(r) for r in all_results]
                self.finished.emit(classified)

        self._worker = ScanWorker(self)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.start()

    def _on_scan_done(self, results: list):
        self._scan_btn.setEnabled(True)
        self._scan_progress.setVisible(False)
        if not results:
            self._scan_results.setText("No se encontraron servidores en la red local.")
            self._connect_btn.setVisible(False)
        else:
            self._discovered = results
            lines = ["Servidores detectados:"]
            for i, s in enumerate(results[:5]):
                lines.append(f"  [{i+1}] {s.server_type}: {s.host}:{s.port}")
            self._scan_results.setText("\n".join(lines))
            self._connect_btn.setVisible(True)

    def _on_connect_discovered(self):
        if not hasattr(self, '_discovered') or not self._discovered:
            return
        w = self.window()
        if w and hasattr(w, '_add_server'):
            w._add_server()

    def _get_servers(self) -> list:
        try:
            import json
            import os
            path = os.path.expanduser("~/.local/share/michi-music-player/subsonic_servers.json")
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    @staticmethod
    def _get_devices() -> list:
        try:
            from library.library_db import get_mounted_devices
            return get_mounted_devices()
        except Exception:
            return []

    def _build_card(self, key: str, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"connectionsCard_{key}")

        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(8)

        c_title = QLabel(title)
        c_layout.addWidget(c_title)

        c_desc = QLabel(description)
        c_desc.setWordWrap(True)
        c_layout.addWidget(c_desc)

        btn = QPushButton(f"Abrir {title}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda checked=None, k=key: self._navigate(k))
        c_layout.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"connectionsCard_{key}"))
        return card

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#connectionsHubPage { background: #090B11; }
            QScrollArea#connectionsHubScroll { background: transparent; border: none; }
            QWidget#connectionsHubContent { background: transparent; }
            QLabel#connectionsHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#connectionsHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
        for key in ("add_server", "home_audio"):
            card = self.findChild(QFrame, f"connectionsCard_{key}")
            if card:
                for lbl in card.findChildren(QLabel):
                    if "font-size" not in (lbl.styleSheet() or ""):
                        lbl.setStyleSheet(
                            "QLabel { color: rgba(255,255,255,0.62); font-size: 12px; "
                            "background: transparent; border: none; }"
                        )
                for btn in card.findChildren(QPushButton):
                    btn.setStyleSheet(glass_button_qss("primary"))
