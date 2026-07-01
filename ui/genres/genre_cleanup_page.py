"""GenreCleanupPage — panel for detecting and resolving genre issues."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QPushButton, QFrame, QDialog,
)

from ui.central.central_styles import glass_button_qss
from ui.genres.genre_empty_states import GenreEmptyState
from ui.genres.genre_operation_dialog import GenreOperationPreviewDialog

_BG = "#090B11"
_TEXT = "#FFFFFF"
_TEXT2 = "rgba(255,255,255,0.78)"
_TEXT3 = "rgba(255,255,255,0.62)"
_ACCENT = "#8FB7FF"
_WARN = "#FFB347"
_ERROR = "#FF6B6B"


class GenreCleanupPage(QWidget):
    back_requested = Signal()
    merge_requested = Signal(list, str)
    apply_genre_requested = Signal(list, str)
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG};")
        self._sections = {}

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {_BG}; border: none; }}"
            "QScrollBar:vertical { background: transparent; width: 4px; margin: 4px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.10); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(28, 16, 28, 36)
        self._layout.setSpacing(16)

        self._build_header()
        self._build_scan_button()

        self._untagged_section = self._make_section("Canciones sin género", "untagged")
        self._duplicates_section = self._make_section("Duplicados probables", "duplicate")
        self._junk_section = self._make_section("Géneros basura", "junk")
        self._rare_section = self._make_section("Géneros raros", "rare")
        self._multi_section = self._make_section("Separadores múltiples", "multi")

        self._empty_state = GenreEmptyState()
        self._empty_state.setVisible(False)
        self._layout.addWidget(self._empty_state)

        self._scroll.setWidget(self._container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

    def _build_header(self):
        card = QFrame()
        card.setObjectName("cleanupHeader")
        card.setStyleSheet(
            "QFrame#cleanupHeader { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(255,255,255,0.04),stop:1 rgba(143,183,255,0.06));"
            "border: 1px solid rgba(143,183,255,0.08); border-radius: 18px; }"
            "QLabel { background: transparent; border: none; }")
        hl = QVBoxLayout(card)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(4)
        title = QLabel("Limpieza de géneros")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {_TEXT};")
        hl.addWidget(title)
        sub = QLabel("Normaliza estilos, detecta duplicados y corrige canciones sin género.")
        sub.setStyleSheet(f"font-size: 12px; color: {_TEXT3};")
        hl.addWidget(sub)
        self._layout.addWidget(card)

    def _build_scan_button(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        scan_btn = QPushButton("Escanear problemas")
        scan_btn.setCursor(Qt.PointingHandCursor)
        scan_btn.setStyleSheet(glass_button_qss("primary"))
        scan_btn.setFixedHeight(30)
        scan_btn.clicked.connect(self.refresh_requested.emit)
        row.addWidget(scan_btn)
        row.addStretch()
        self._layout.addLayout(row)

    def _make_section(self, title: str, key: str) -> dict:
        card = QFrame()
        card.setObjectName(f"section_{key}")
        card.setStyleSheet(
            f"QFrame#section_{key} {{ background: rgba(255,255,255,0.03);"
            "border: 1px solid rgba(255,255,255,0.045); border-radius: 14px; }}"
            "QLabel { background: transparent; border: none; }")
        card.setVisible(False)
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(8)
        hdr = QLabel(title)
        hdr.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {_TEXT};")
        cv.addWidget(hdr)
        self._layout.addWidget(card)
        return {"card": card, "layout": cv, "key": key}

    def _clear_layout(self, layout):
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def set_untagged(self, data: dict):
        self._clear_layout(self._untagged_section["layout"])
        if not data or not data.get("count"):
            self._untagged_section["card"].setVisible(False)
            return
        self._untagged_section["card"].setVisible(True)
        label = QLabel(f"{data['count']} canciones sin género")
        label.setStyleSheet(f"color: {_WARN}; font-size: 12px;")
        self._untagged_section["layout"].addWidget(label)
        for item in data.get("tracks", [])[:10]:
            title = getattr(item, 'title', '') or getattr(item, 'filename', '') or ''
            artist = getattr(item, 'artist', '') or ''
            row_lbl = QLabel(f"{title} — {artist}")
            row_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px;")
            self._untagged_section["layout"].addWidget(row_lbl)

    def set_duplicates(self, duplicates: list[dict]):
        self._clear_layout(self._duplicates_section["layout"])
        if not duplicates:
            self._duplicates_section["card"].setVisible(False)
            return
        self._duplicates_section["card"].setVisible(True)
        label = QLabel(f"{len(duplicates)} grupos de géneros duplicados")
        label.setStyleSheet(f"color: {_WARN}; font-size: 12px;")
        self._duplicates_section["layout"].addWidget(label)

        for dup in duplicates[:10]:
            row_lbl = QLabel(
                f"Fusionar en: {dup.get('canonical', '?')} "
                f"({dup.get('count', 0)} canciones)")
            row_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px;")
            self._duplicates_section["layout"].addWidget(row_lbl)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            apply_btn = QPushButton("Fusionar")
            apply_btn.setCursor(Qt.PointingHandCursor)
            apply_btn.setStyleSheet(glass_button_qss("accent"))
            apply_btn.setFixedHeight(24)
            sources = list(dup.get("raw_values", []))
            target = dup.get("canonical", "")
            apply_btn.clicked.connect(
                lambda checked=False, s=sources, t=target, c=dup.get('count', 0):
                self._show_merge_dialog(s, t, c))
            btn_row.addWidget(apply_btn)
            btn_row.addStretch()
            self._duplicates_section["layout"].addLayout(btn_row)

    def set_junk(self, junk: list[dict]):
        self._clear_layout(self._junk_section["layout"])
        if not junk:
            self._junk_section["card"].setVisible(False)
            return
        self._junk_section["card"].setVisible(True)
        label = QLabel(f"{len(junk)} valores no reconocidos como género")
        label.setStyleSheet(f"color: {_ERROR}; font-size: 12px;")
        self._junk_section["layout"].addWidget(label)
        for j in junk[:8]:
            row_lbl = QLabel(f"'{j.get('value', '?')}' — {j.get('count', 0)} canciones")
            row_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px;")
            self._junk_section["layout"].addWidget(row_lbl)

    def set_rare(self, rare: list[dict]):
        self._clear_layout(self._rare_section["layout"])
        if not rare:
            self._rare_section["card"].setVisible(False)
            return
        self._rare_section["card"].setVisible(True)
        label = QLabel(f"{len(rare)} géneros con menos de 3 canciones")
        label.setStyleSheet(f"color: {_WARN}; font-size: 12px;")
        self._rare_section["layout"].addWidget(label)
        for r_item in rare[:10]:
            row_lbl = QLabel(
                f"{r_item.get('genre', '?')} — {r_item.get('track_count', 0)} canciones")
            row_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px;")
            self._rare_section["layout"].addWidget(row_lbl)

    def set_multi_genre(self, issues: list[dict]):
        self._clear_layout(self._multi_section["layout"])
        if not issues:
            self._multi_section["card"].setVisible(False)
            return
        self._multi_section["card"].setVisible(True)
        label = QLabel(f"{len(issues)} canciones con géneros múltiples")
        label.setStyleSheet(f"color: {_ACCENT}; font-size: 12px;")
        self._multi_section["layout"].addWidget(label)
        for issue in issues[:8]:
            title = issue.get("title", "")
            raw = issue.get("raw_genre", "")
            suggested = ", ".join(issue.get("suggested_genres", []))
            row_lbl = QLabel(f"{title}: '{raw}' → {suggested}")
            row_lbl.setStyleSheet(f"color: {_TEXT2}; font-size: 11px;")
            self._multi_section["layout"].addWidget(row_lbl)

    def _show_merge_dialog(self, sources: list, target: str, count: int):
        dialog = GenreOperationPreviewDialog(
            "Fusionar géneros", sources, target, track_count=count, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.merge_requested.emit(sources, target)

    def show_empty(self, message: str = "No se detectaron problemas de géneros"):
        self._untagged_section["card"].setVisible(False)
        self._duplicates_section["card"].setVisible(False)
        self._junk_section["card"].setVisible(False)
        self._rare_section["card"].setVisible(False)
        self._multi_section["card"].setVisible(False)
        self._empty_state.setVisible(True)
        self._empty_state._title.setText(message)
        self._empty_state._subtitle.setText("Tu biblioteca de géneros está en buen estado.")
