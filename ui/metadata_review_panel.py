"""Metadata review panel — field-by-field comparison and approval for AI-assisted review."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QLabel, QFrame, QCheckBox,
)

from ui.central.central_styles import glass_button_qss


class MetadataReviewPanel(QWidget):
    review_apply_requested = Signal(str, dict)
    review_reject_requested = Signal(str)
    review_undo_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("metadataReviewPanel")
        self._review_id: str = ""
        self._checkboxes: dict[str, QCheckBox] = {}
        self._field_rows: dict[str, dict] = {}
        self._build_ui()
        self._apply_qss()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("reviewHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 12)

        self._title_label = QLabel("Revisión de metadata")
        self._title_label.setObjectName("reviewTitle")
        header_layout.addWidget(self._title_label)

        self._subtitle_label = QLabel("Compara los datos actuales con las sugerencias antes de aplicar cambios.")
        self._subtitle_label.setObjectName("reviewSubtitle")
        self._subtitle_label.setWordWrap(True)
        header_layout.addWidget(self._subtitle_label)

        self._warning_label = QLabel("Las sugerencias externas pueden contener errores. Revisa cada campo antes de aplicar.")
        self._warning_label.setObjectName("reviewWarning")
        self._warning_label.setWordWrap(True)
        header_layout.addWidget(self._warning_label)

        layout.addWidget(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setObjectName("reviewScroll")

        self._content = QWidget()
        self._content.setObjectName("reviewContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 8, 16, 16)
        self._content_layout.setSpacing(12)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(16, 8, 16, 16)
        actions.setSpacing(8)

        self._accept_all_btn = QPushButton("Aceptar todos")
        self._accept_all_btn.setObjectName("reviewAcceptAll")
        self._accept_all_btn.setCursor(Qt.PointingHandCursor)
        self._accept_all_btn.clicked.connect(self._on_accept_all)
        actions.addWidget(self._accept_all_btn)

        self._reject_all_btn = QPushButton("Rechazar todos")
        self._reject_all_btn.setObjectName("reviewRejectAll")
        self._reject_all_btn.setCursor(Qt.PointingHandCursor)
        self._reject_all_btn.clicked.connect(self._on_reject_all)
        actions.addWidget(self._reject_all_btn)

        self._apply_btn = QPushButton("Aplicar cambios")
        self._apply_btn.setObjectName("reviewApplyBtn")
        self._apply_btn.setCursor(Qt.PointingHandCursor)
        self._apply_btn.clicked.connect(self._on_apply)
        actions.addWidget(self._apply_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setObjectName("reviewCancelBtn")
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.clicked.connect(lambda: self.review_reject_requested.emit(self._review_id))
        actions.addWidget(self._cancel_btn)

        layout.addLayout(actions)

    def _apply_qss(self):
        self.setStyleSheet("""
            QWidget#metadataReviewPanel {
                background: #090B11;
            }
            QFrame#reviewHeader {
                background: transparent;
                border-bottom: 1px solid rgba(255,255,255,0.03);
            }
            QLabel#reviewTitle {
                color: rgba(255,255,255,0.92);
                font-size: 15px;
                font-weight: 600;
            }
            QLabel#reviewSubtitle {
                color: rgba(255,255,255,0.58);
                font-size: 12px;
                margin-top: 4px;
            }
            QLabel#reviewWarning {
                color: rgba(143,183,255,0.52);
                font-size: 11px;
                margin-top: 6px;
            }
            QScrollArea#reviewScroll {
                background: transparent;
                border: none;
            }
            QWidget#reviewContent {
                background: transparent;
            }
        """)
        self._accept_all_btn.setStyleSheet(glass_button_qss("ghost"))
        self._reject_all_btn.setStyleSheet(glass_button_qss("ghost"))
        self._apply_btn.setStyleSheet(glass_button_qss("primary"))
        self._cancel_btn.setStyleSheet(glass_button_qss("ghost"))

    def load_review(self, review_data: dict):
        self._review_id = review_data.get("review_id", "")
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._checkboxes.clear()
        self._field_rows.clear()

        self._title_label.setText(f"Revisión de metadata — {review_data.get('status', '')}")
        proposals = review_data.get("proposals", [])
        total = sum(len(p.get("changes", [])) for p in proposals)
        self._subtitle_label.setText(
            f"Compara los datos actuales con las sugerencias ({total} cambios propuestos) "
            f"antes de aplicar cambios."
        )

        for proposal in proposals:
            track_label = QLabel(
                f"{proposal.get('title', '')} — {proposal.get('artist_name', '')}"
            )
            track_label.setStyleSheet(
                "QLabel { color: rgba(255,255,255,0.78); font-size: 13px; "
                "font-weight: 600; padding: 4px 0; }"
            )
            idx = self._content_layout.count() - 1
            self._content_layout.insertWidget(max(0, idx), track_label)

            for change in proposal.get("changes", []):
                card = self._build_change_card(change, proposal.get("proposal_id", ""))
                idx = self._content_layout.count() - 1
                self._content_layout.insertWidget(max(0, idx), card)

    def _build_change_card(self, change: dict, proposal_id: str) -> QFrame:
        card = QFrame()
        card.setObjectName(f"changeCard_{change.get('field','')}")
        card.setStyleSheet(
            "QFrame { border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; "
            "background: rgba(255,255,255,0.015); padding: 10px; }"
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        field_name = QLabel(change.get("field", ""))
        field_name.setStyleSheet(
            "QLabel { color: rgba(143,183,255,0.78); font-size: 12px; font-weight: 600; }"
        )
        top_row.addWidget(field_name)

        conf = change.get("confidence", 0)
        conf_color = "rgba(255,255,255,0.42)"
        if conf >= 0.90:
            conf_color = "rgba(100,220,140,0.60)"
        elif conf >= 0.75:
            conf_color = "rgba(200,180,100,0.60)"
        elif conf > 0:
            conf_color = "rgba(220,140,100,0.50)"
        conf_label = QLabel(f"{conf:.0%} — {change.get('source','')}")
        conf_label.setStyleSheet(f"QLabel {{ color: {conf_color}; font-size: 10px; }}")
        top_row.addWidget(conf_label)
        top_row.addStretch()

        chk = QCheckBox()
        chk.setCursor(Qt.PointingHandCursor)
        chk.setChecked(conf >= 0.85)
        key = f"{proposal_id}:{change.get('field','')}"
        self._checkboxes[key] = chk
        self._field_rows[key] = {"proposal_id": proposal_id, "field": change.get("field", "")}
        chk.setStyleSheet(
            "QCheckBox::indicator { width: 16px; height: 16px; }"
        )
        top_row.addWidget(chk)
        layout.addLayout(top_row)

        vals = QLabel(
            f"Actual: {change.get('current_value','(vacio)')}  →  "
            f"Sugerido: {change.get('suggested_value','(sin sugerencia)')}"
        )
        vals.setWordWrap(True)
        vals.setStyleSheet("QLabel { color: rgba(255,255,255,0.62); font-size: 12px; }")
        layout.addWidget(vals)

        reason = change.get("reason", "")
        if reason:
            rl = QLabel(reason)
            rl.setStyleSheet("QLabel { color: rgba(255,255,255,0.35); font-size: 10px; }")
            layout.addWidget(rl)

        return card

    def _on_accept_all(self):
        for chk in self._checkboxes.values():
            chk.setChecked(True)

    def _on_reject_all(self):
        for chk in self._checkboxes.values():
            chk.setChecked(False)

    def _on_apply(self):
        if not self._review_id:
            return
        accepted: dict[int, list[str]] = {}
        for key, chk in self._checkboxes.items():
            if chk.isChecked():
                info = self._field_rows.get(key, {})
                proposal_id = info.get("proposal_id", "")
                field = info.get("field", "")
                track_id = 0
                if proposal_id:
                    track_id = int(proposal_id.split("_", 1)[0]) if proposal_id.split("_")[0].isdigit() else 0
                if track_id:
                    if track_id not in accepted:
                        accepted[track_id] = []
                    if field not in accepted[track_id]:
                        accepted[track_id].append(field)

        self.review_apply_requested.emit(self._review_id, accepted)

    def show_undo_button(self, show: bool):
        pass  # undo handled by reconsidering
