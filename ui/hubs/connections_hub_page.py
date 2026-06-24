"""ConnectionsHubPage — premium service hub for music servers, devices and network."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QProgressBar,
)

from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_chip_button_qss, glass_progress_qss,
    card_title_qss, card_desc_qss, card_meta_qss,
    page_title_qss, page_subtitle_qss,
)

_SERVICE_DEFS = [
    ("navidrome", "Navidrome", "Servidor de música Subsonic moderno.", "add_server"),
    ("jellyfin", "Jellyfin", "Centro multimedia completo.", "add_server"),
    ("subsonic", "Subsonic", "Servidor de música compatible Subsonic.", "add_server"),
    ("home_assistant", "Home Assistant", "Domótica y multiroom.", "home_audio"),
    ("snapcast", "Snapcast", "Audio sincronizado multiroom.", "home_audio"),
    ("michi_local", "Michi Local", "Servidor propio en esta máquina.", "add_server"),
    ("custom", "Servidor manual", "Conecta cualquier servidor Subsonic.", "add_server"),
]


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
        cl = QVBoxLayout(content)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(24)

        title = QLabel("Conexiones")
        title.setObjectName("connectionsHubTitle")
        cl.addWidget(title)

        servers = self._get_servers()
        subtitle = QLabel(
            "Conecta servidores musicales, servicios de red "
            "y dispositivos locales sin salir de Michi."
        )
        subtitle.setObjectName("connectionsHubSubtitle")
        subtitle.setWordWrap(True)
        cl.addWidget(subtitle)

        # ── Saved servers ──
        if servers:
            sec = QLabel("SERVIDORES CONFIGURADOS")
            sec.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
            cl.addWidget(sec)
            grid = QGridLayout()
            grid.setSpacing(12)
            cols = max(1, (self.width() or 800) // 320)
            for i, srv in enumerate(servers):
                grid.addWidget(self._build_server_card(srv), i // cols, i % cols, Qt.AlignTop)
            cl.addLayout(grid)

        # ── Service grid ──
        sec2 = QLabel("SERVICIOS DISPONIBLES")
        sec2.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec2)
        svc_grid = QGridLayout()
        svc_grid.setSpacing(14)
        cols2 = max(1, (self.width() or 800) // 200)
        for i, (key, name, desc, nav) in enumerate(_SERVICE_DEFS):
            svc_grid.addWidget(
                self._build_service_card(key, name, desc, nav), i // cols2, i % cols2, Qt.AlignTop)
        cl.addLayout(svc_grid)

        # ── Mounted devices ──
        devices = self._get_devices()
        if devices:
            sec3 = QLabel("DISPOSITIVOS MONTADOS")
            sec3.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
            cl.addWidget(sec3)
            dev_row = QHBoxLayout()
            dev_row.setSpacing(8)
            for d in devices:
                dname = d.get("name", d.get("mount", "Dispositivo"))
                dmount = d.get("mount", "")
                chip = QPushButton(dname)
                chip.setToolTip(dmount)
                chip.setCursor(Qt.PointingHandCursor)
                chip.setStyleSheet(glass_chip_button_qss())
                chip.clicked.connect(lambda c=None, m=dmount: self._navigate(f"dev:{m}"))
                dev_row.addWidget(chip)
            dev_row.addStretch()
            cl.addLayout(dev_row)

        # ── Network scan ──
        sec4 = QLabel("RED LOCAL")
        sec4.setStyleSheet("QLabel { color: rgba(255,255,255,0.48); font-size: 11px; font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec4)
        scan_card = QFrame()
        scan_card.setObjectName("connectionsScanCard")
        sc = QVBoxLayout(scan_card)
        sc.setContentsMargins(20, 16, 20, 16)
        sc.setSpacing(10)

        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Escanear red local")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.setStyleSheet(glass_button_qss("secondary"))
        self._scan_btn.clicked.connect(self._on_scan_network)
        btn_row.addWidget(self._scan_btn)
        btn_row.addStretch()
        sc.addLayout(btn_row)

        self._scan_progress = QProgressBar()
        self._scan_progress.setRange(0, 0)
        self._scan_progress.setVisible(False)
        self._scan_progress.setStyleSheet(glass_progress_qss())
        sc.addWidget(self._scan_progress)

        self._scan_results = QLabel("")
        self._scan_results.setWordWrap(True)
        self._scan_results.setStyleSheet("QLabel { color: rgba(143,183,255,0.60); font-size: 12px; }")
        self._scan_results.setVisible(False)
        sc.addWidget(self._scan_results)

        self._connect_btn = QPushButton("Conectar servidor detectado")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.setStyleSheet(glass_button_qss("primary"))
        self._connect_btn.setVisible(False)
        self._connect_btn.clicked.connect(self._on_connect_discovered)
        sc.addWidget(self._connect_btn)

        scan_card.setStyleSheet(glass_card_qss("connectionsScanCard", "elevated"))
        cl.addWidget(scan_card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

    def _build_service_card(self, key: str, name: str, desc: str, nav: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"svcCard_{key}")
        card.setMinimumHeight(170)
        card.setCursor(Qt.PointingHandCursor)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(6)

        name_lbl = QLabel(name)
        name_lbl.setObjectName(f"svcTitle_{key}")
        name_lbl.setStyleSheet(card_title_qss())
        vl.addWidget(name_lbl)

        icon_area = QLabel(name[0] if name else "?")
        icon_area.setAlignment(Qt.AlignCenter)
        icon_area.setStyleSheet(
            "QLabel { font-size: 28px; font-weight: 700; color: rgba(255,255,255,0.22); "
            "background: transparent; border: none; }")
        vl.addWidget(icon_area, 1)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(card_desc_qss())
        vl.addWidget(desc_lbl)

        btn = QPushButton(f"Abrir {name}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("secondary"))
        btn.clicked.connect(lambda c=None, n=nav: self._navigate(n))
        vl.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"svcCard_{key}", "base"))
        return card

    def _build_server_card(self, srv: dict) -> QFrame:
        card = QFrame()
        name = srv.get("name", "Servidor")
        stype = srv.get("stype", "navidrome")
        url = srv.get("url", "")
        key = f"srv_{name.replace(' ','_')}"
        card.setObjectName(key)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(6)

        title = QLabel(name)
        title.setStyleSheet(card_title_qss())
        vl.addWidget(title)

        t = QLabel(f"{stype.title()} · {url}")
        t.setStyleSheet(card_meta_qss())
        vl.addWidget(t)

        btn = QPushButton("Abrir servidor")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("secondary"))
        btn.clicked.connect(lambda c=None, u=url: self._navigate(f"srv:{name}"))
        vl.addWidget(btn)

        card.setStyleSheet(glass_card_qss(key, "elevated"))
        return card

    def _on_scan_network(self):
        self._scan_btn.setEnabled(False)
        self._scan_progress.setVisible(True)
        self._scan_results.setVisible(True)
        self._scan_results.setText("Buscando servicios locales...")

        class ScanWorker(QThread):
            finished = Signal(list)
            def run(self):
                from integrations.connections.discovery_manager import DiscoveryManager
                mgr = DiscoveryManager(timeout=0.3)
                results = mgr.scan_known_ports()
                mdns = mgr.scan_mdns()
                classified = [mgr.build_discovered_server(r) for r in results + mdns]
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

    def _navigate(self, target: str):
        w = self.window()
        if w and hasattr(w, '_on_sidebar_navigate'):
            w._on_sidebar_navigate(target)

    def _apply_qss(self):
        self.setStyleSheet(
            page_title_qss() + page_subtitle_qss() + """
            QWidget#connectionsHubPage { background: #090B11; }
            QScrollArea#connectionsHubScroll { background: transparent; border: none; }
            QWidget#connectionsHubContent { background: transparent; }
            QLabel#connectionsHubTitle { color: rgba(255,255,255,0.92); font-size: 22px; font-weight: 700; }
            QLabel#connectionsHubSubtitle { color: rgba(255,255,255,0.56); font-size: 13px; }
        """)
