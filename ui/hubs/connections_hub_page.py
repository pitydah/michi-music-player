"""ConnectionsHubPage — Servidores y conexiones del ecosistema Michi."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QProgressBar,
)

from ui.effects.michi_glass import apply_card_shadow
from ui.central.central_styles import (
    glass_card_qss, glass_button_qss, glass_chip_button_qss, glass_progress_qss,
    glass_hero_qss, badge_qss,
    card_title_qss, card_desc_qss, card_meta_qss, section_label_qss,
)

_SERVICE_DEFS = [
    ("navidrome", "Navidrome", "Servidor de música Subsonic moderno.", "add_server"),
    ("jellyfin", "Jellyfin", "Centro multimedia completo.", "add_server"),
    ("subsonic", "Subsonic", "Servidor de música compatible Subsonic.", "add_server"),
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
        cl.setContentsMargins(40, 16, 40, 32)
        cl.setSpacing(20)

        # ── 1. Michi Micro Server — hero ──
        ms_card = QFrame()
        ms_card.setObjectName("mmsHero")
        ms_card.setStyleSheet(glass_hero_qss("mmsHero"))
        ms_card.setMinimumHeight(200)
        ms_vl = QVBoxLayout(ms_card)
        ms_vl.setContentsMargins(24, 18, 24, 18)
        ms_vl.setSpacing(8)

        ms_header = QHBoxLayout()
        ms_title = QLabel("Michi Micro Server")
        ms_title.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: rgba(255,255,255,0.94);")
        ms_header.addWidget(ms_title)
        ms_badge = QLabel("Ecosistema Michi")
        ms_badge.setStyleSheet(badge_qss("active"))
        ms_header.addWidget(ms_badge)
        ms_badge2 = QLabel("Rust")
        ms_badge2.setStyleSheet(badge_qss("info"))
        ms_header.addWidget(ms_badge2)
        ms_badge3 = QLabel("Streaming")
        ms_badge3.setStyleSheet(badge_qss("info"))
        ms_header.addWidget(ms_badge3)
        ms_header.addStretch()
        ms_vl.addLayout(ms_header)

        ms_desc = QLabel(
            "Servidor musical doméstico del ecosistema Michi para centralizar "
            "biblioteca, metadatos, playlists y streaming local o remoto.")
        ms_desc.setWordWrap(True)
        ms_desc.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.56);")
        ms_vl.addWidget(ms_desc)

        ms_status = QLabel("● No configurado")
        ms_status.setStyleSheet(
            "font-size: 12px; color: rgba(255,255,255,0.46);")
        ms_vl.addWidget(ms_status)

        ms_btns = QHBoxLayout()
        ms_btns.setSpacing(10)
        btn_search = QPushButton("Buscar Michi Micro Server")
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.setStyleSheet(glass_button_qss("primary"))
        btn_search.clicked.connect(self._on_scan_network)
        ms_btns.addWidget(btn_search)
        btn_manual = QPushButton("Agregar manualmente")
        btn_manual.setCursor(Qt.PointingHandCursor)
        btn_manual.setStyleSheet(glass_button_qss("secondary"))
        btn_manual.clicked.connect(lambda: self._navigate("add_server"))
        ms_btns.addWidget(btn_manual)
        btn_concept = QPushButton("Ver concepto")
        btn_concept.setCursor(Qt.PointingHandCursor)
        btn_concept.setStyleSheet(glass_button_qss("ghost"))
        ms_btns.addWidget(btn_concept)
        ms_btns.addStretch()
        ms_vl.addLayout(ms_btns)

        apply_card_shadow(ms_card)
        cl.addWidget(ms_card)

        # ── 2. Saved servers ──
        servers = self._get_servers()
        if servers:
            sec = QLabel("SERVIDORES CONFIGURADOS")
            sec.setStyleSheet(section_label_qss())
            cl.addWidget(sec)
            grid = QGridLayout()
            grid.setSpacing(12)
            cols = max(1, (self.width() or 800) // 320)
            for i, srv in enumerate(servers):
                grid.addWidget(self._build_server_card(srv), i // cols, i % cols, Qt.AlignTop)
            cl.addLayout(grid)

        # ── 3. External services ──
        sec2 = QLabel("SERVIDORES EXTERNOS")
        sec2.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.48); font-size: 11px;"
            " font-weight: 600; letter-spacing: 1px; }")
        cl.addWidget(sec2)
        svc_grid = QGridLayout()
        svc_grid.setSpacing(14)
        cols2 = max(1, (self.width() or 800) // 200)
        for i, (key, name, desc, nav) in enumerate(_SERVICE_DEFS):
            svc_grid.addWidget(
                self._build_service_card(key, name, desc, nav),
                i // cols2, i % cols2, Qt.AlignTop)
        cl.addLayout(svc_grid)

        # ── 4. Michi Local ──
        local_row = QHBoxLayout()
        local_row.setSpacing(10)
        local_chip = QPushButton("Michi Local — servidor en esta máquina")
        local_chip.setCursor(Qt.PointingHandCursor)
        local_chip.setStyleSheet(glass_chip_button_qss())
        local_chip.clicked.connect(lambda: self._navigate("home_audio"))
        local_row.addWidget(local_chip)
        local_row.addStretch()
        cl.addLayout(local_row)

        # ── 5. Home Audio access ──
        other_row = QHBoxLayout()
        other_row.setSpacing(10)
        other_label = QLabel("Audio doméstico")
        other_label.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.42);")
        other_row.addWidget(other_label)
        for _key, name in (("home_assistant", "Home Assistant"), ("snapcast", "Snapcast")):
            chip = QPushButton(name)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(glass_chip_button_qss())
            chip.clicked.connect(lambda c=None: self._navigate("home_audio"))
            other_row.addWidget(chip)
        other_row.addStretch()
        cl.addLayout(other_row)
        cl.addSpacing(8)

        # ── 6. Network scan ──
        sec4 = QLabel("RED LOCAL")
        sec4.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.48); font-size: 11px;"
            " font-weight: 600; letter-spacing: 1px; }")
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
        self._scan_results.setStyleSheet(
            "QLabel { color: rgba(143,183,255,0.60); font-size: 12px; }")
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

        # ── 7. Mounted devices ──
        devices = self._get_devices()
        if devices:
            sec3 = QLabel("DISPOSITIVOS MONTADOS")
            sec3.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.48); font-size: 11px;"
                " font-weight: 600; letter-spacing: 1px; }")
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

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self._apply_qss()

    def _build_micro_server_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("mmsHero")
        card.setStyleSheet(glass_hero_qss("mmsHero"))
        card.setMinimumHeight(200)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(24, 18, 24, 18)
        vl.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Michi Micro Server")
        title.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: rgba(255,255,255,0.94);")
        header.addWidget(title)
        b1 = QLabel("Ecosistema Michi")
        b1.setStyleSheet(badge_qss("active"))
        header.addWidget(b1)
        b2 = QLabel("Rust")
        b2.setStyleSheet(badge_qss("info"))
        header.addWidget(b2)
        b3 = QLabel("Streaming")
        b3.setStyleSheet(badge_qss("info"))
        header.addWidget(b3)
        header.addStretch()
        vl.addLayout(header)

        desc = QLabel(
            "Servidor musical doméstico del ecosistema Michi para centralizar "
            "biblioteca, metadatos, playlists y streaming local o remoto.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.56);")
        vl.addWidget(desc)

        status = QLabel("● No configurado")
        status.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.46);")
        vl.addWidget(status)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        btn1 = QPushButton("Buscar Michi Micro Server")
        btn1.setCursor(Qt.PointingHandCursor)
        btn1.setStyleSheet(glass_button_qss("primary"))
        btn1.clicked.connect(self._on_scan_network)
        btns.addWidget(btn1)
        btn2 = QPushButton("Agregar manualmente")
        btn2.setCursor(Qt.PointingHandCursor)
        btn2.setStyleSheet(glass_button_qss("secondary"))
        btn2.clicked.connect(lambda: self._navigate("add_server"))
        btns.addWidget(btn2)
        btn3 = QPushButton("Ver concepto")
        btn3.setCursor(Qt.PointingHandCursor)
        btn3.setStyleSheet(glass_button_qss("ghost"))
        btns.addWidget(btn3)
        btns.addStretch()
        vl.addLayout(btns)
        return card

    def _build_service_card(self, key: str, name: str, desc: str, nav: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"svcCard_{key}")
        card.setMinimumHeight(150)
        card.setCursor(Qt.PointingHandCursor)
        vl = QVBoxLayout(card)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(6)

        name_lbl = QLabel(name)
        name_lbl.setObjectName(f"svcTitle_{key}")
        name_lbl.setStyleSheet(card_title_qss())
        vl.addWidget(name_lbl)

        ext_badge = QLabel("Externo")
        ext_badge.setStyleSheet(badge_qss("remote"))
        vl.addWidget(ext_badge)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(card_desc_qss())
        vl.addWidget(desc_lbl)

        btn = QPushButton(f"Abrir {name}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(glass_button_qss("secondary"))
        btn.clicked.connect(lambda c=None, n=nav: self._navigate(n))
        vl.addWidget(btn)

        card.setStyleSheet(glass_card_qss(f"svcCard_{key}", "compact"))
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
            self._scan_results.setText(
                "No se encontraron servidores en la red local.\n"
                "Verifica que Michi Micro Server o tus servidores "
                "compatibles estén encendidos y en la misma red.")
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
            from core.paths import subsonic_servers_path
            path = subsonic_servers_path()
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
        self.setStyleSheet("""
            QWidget#connectionsHubPage { background: #090B11; }
            QScrollArea#connectionsHubScroll { background: transparent; border: none; }
            QWidget#connectionsHubContent { background: transparent; }
        """)
        apply_card_shadow(self.findChild(QFrame, "mmsHero"))
        for key, _name, _desc, _nav in _SERVICE_DEFS:
            card = self.findChild(QFrame, f"svcCard_{key}")
            if card:
                apply_card_shadow(card)
        scan_card = self.findChild(QFrame, "connectionsScanCard")
        if scan_card:
            apply_card_shadow(scan_card)
        for srv in self._get_servers():
            name = srv.get("name", "Servidor")
            key = f"srv_{name.replace(' ','_')}"
            card = self.findChild(QFrame, key)
            if card:
                apply_card_shadow(card)
