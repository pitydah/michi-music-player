"""Library Doctor panel — diagnostic UI with category cards and repair suggestions."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QProgressBar,
)

from ui.central.central_styles import glass_button_qss


class LibraryDoctorPanel(QWidget):
    scan_requested = Signal()
    open_category = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("libraryDoctorPanel")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("doctorHeader")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 12, 20, 12)

        title = QLabel("Library Doctor")
        title.setObjectName("doctorTitle")
        h_layout.addWidget(title)

        self._status = QLabel(
            "Analiza tu biblioteca en busca de metadata faltante, artistas duplicados, "
            "álbumes partidos y mas."
        )
        self._status.setObjectName("doctorStatus")
        self._status.setWordWrap(True)
        h_layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._scan_btn = QPushButton("Escanear biblioteca")
        self._scan_btn.setObjectName("doctorScanBtn")
        self._scan_btn.setCursor(Qt.PointingHandCursor)
        self._scan_btn.clicked.connect(self.scan_requested.emit)
        btn_row.addWidget(self._scan_btn)

        self._progress = QProgressBar()
        self._progress.setObjectName("doctorProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        btn_row.addWidget(self._progress)

        btn_row.addStretch()
        h_layout.addLayout(btn_row)

        layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("doctorScroll")

        self._content = QWidget()
        self._content.setObjectName("doctorContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 12, 20, 16)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        self._apply_qss()

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#libraryDoctorPanel { background: transparent; }
            QFrame#doctorHeader { background: transparent; border-bottom: 1px solid rgba(255,255,255,0.03); }
            QLabel#doctorTitle { color: rgba(255,255,255,0.88); font-size: 16px; font-weight: 600; }
            QLabel#doctorStatus { color: rgba(255,255,255,0.52); font-size: 12px; margin-top: 2px; }
            QScrollArea#doctorScroll { background: transparent; border: none; }
            QWidget#doctorContent { background: transparent; }
        """)
        self._scan_btn.setStyleSheet(glass_button_qss("primary"))

    def set_loading(self, loading: bool):
        self._progress.setVisible(loading)
        self._scan_btn.setEnabled(not loading)
        if loading:
            self._status.setText("Escaneando biblioteca...")

    def show_results(self, scan: dict, repair_plan: dict):
        self._status.setText(
            f"{repair_plan.get('total_issues', 0)} problemas detectados. "
            f"{repair_plan.get('fixable', 0)} se pueden corregir automaticamente."
        )

        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        categories = [
            ("missing_metadata", "Metadata faltante", scan.get("missing_metadata", 0), "medium"),
            ("duplicate_artists", "Artistas duplicados", scan.get("duplicate_artists", 0), "medium"),
            ("split_albums", "Albumes partidos", scan.get("split_albums", 0), "low"),
            ("missing_artwork", "Carátulas faltantes", scan.get("missing_artwork", 0), "low"),
            ("possible_duplicates", "Posibles duplicados", scan.get("possible_duplicates", 0), "info"),
        ]

        for cat_key, cat_label, count, severity in categories:
            if count == 0:
                continue
            card = self._build_category_card(cat_key, cat_label, count, severity)
            idx = self._content_layout.count() - 1
            self._content_layout.insertWidget(max(0, idx), card)

        if repair_plan.get("suggestions"):
            sep = QLabel("Sugerencias de reparacion")
            sep.setStyleSheet("color: rgba(255,255,255,0.42); font-size: 11px; font-weight: 600; padding-top: 8px;")
            idx = self._content_layout.count() - 1
            self._content_layout.insertWidget(max(0, idx), sep)

            for sug in repair_plan["suggestions"]:
                sug_card = self._build_suggestion_card(sug)
                idx = self._content_layout.count() - 1
                self._content_layout.insertWidget(max(0, idx), sug_card)

    def _build_category_card(self, cat_key: str, label: str, count: int,
                             severity: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"doctorCard_{cat_key}")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(12)

        sev_colors = {
            "medium": "rgba(200,180,100,0.60)",
            "low": "rgba(143,183,255,0.50)",
            "info": "rgba(255,255,255,0.35)",
        }
        sev_color = sev_colors.get(severity, "rgba(255,255,255,0.35)")

        sev_dot = QLabel("●")
        sev_dot.setStyleSheet(f"QLabel {{ color: {sev_color}; font-size: 18px; }}")
        sev_dot.setFixedWidth(20)
        card_layout.addWidget(sev_dot)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(label)
        name.setStyleSheet("QLabel { color: rgba(255,255,255,0.78); font-size: 13px; font-weight: 500; }")
        info.addWidget(name)

        count_label = QLabel(f"{count} elementos")
        count_label.setStyleSheet(f"QLabel {{ color: {sev_color}; font-size: 11px; }}")
        info.addWidget(count_label)
        card_layout.addLayout(info, 1)

        card.setStyleSheet(
            "QFrame { border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; "
            "background: rgba(255,255,255,0.015); }"
        )
        return card

    def _build_suggestion_card(self, sug: dict) -> QFrame:
        card = QFrame()
        card.setObjectName("doctorSuggestion")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(4)

        action = QLabel(sug.get("action", ""))
        action.setWordWrap(True)
        action.setStyleSheet("QLabel { color: rgba(255,255,255,0.62); font-size: 12px; }")
        layout.addWidget(action)

        meta = QLabel(f"{sug.get('count', 0)} items · {sug.get('category', '')}")
        meta.setStyleSheet("QLabel { color: rgba(255,255,255,0.30); font-size: 10px; }")
        layout.addWidget(meta)

        card.setStyleSheet(
            "QFrame { border: 1px solid rgba(143,183,255,0.06); border-radius: 8px; "
            "background: rgba(143,183,255,0.02); }"
        )
        return card
