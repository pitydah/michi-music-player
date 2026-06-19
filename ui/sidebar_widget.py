"""Sidebar Widget — premium scrollable sections with collapsible headers."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QScrollArea, QGraphicsOpacityEffect, QSizePolicy,
)

from ui.icons import get_icon
from ui.icon_renderer import render_svg_icon
from ui.design_tokens import (
    SIDEBAR_ITEM_H, SIDEBAR_ICON,
    SIDEBAR_ACTIVE_GRADIENT,
)


# ── Section Header ──

class _SectionHeader(QWidget):
    clicked = Signal()

    def __init__(self, text: str, dark: bool):
        super().__init__()
        self._collapsed = False
        self._text = text
        self._dark = dark
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 6)
        layout.setSpacing(0)

        txt_c = "rgba(245,245,247,0.82)" if dark else "rgba(28,28,30,0.82)"
        self._title = QLabel(text)
        self._title.setStyleSheet(
            f"font-size:12px;font-weight:680;color:{txt_c};"
            "background:transparent;border:none;")
        layout.addWidget(self._title)
        layout.addStretch()

        chev_c = "rgba(245,245,247,0.76)" if dark else "rgba(28,28,30,0.76)"
        self._chevron = QLabel("˅")
        self._chevron.setStyleSheet(
            f"font-size:11px;color:{chev_c};background:transparent;border:none;")
        self._chevron.setFixedWidth(16)
        self._chevron.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._chevron)

    def toggle(self) -> bool:
        self._collapsed = not self._collapsed
        self._chevron.setText("˄" if self._collapsed else "˅")
        return self._collapsed

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        c = "rgba(255,255,255,0.96)" if self._dark else "rgba(28,28,30,0.96)"
        self._title.setStyleSheet(
            f"font-size:12px;font-weight:680;color:{c};"
            "background:transparent;border:none;")
        cc = "rgba(255,255,255,0.90)" if self._dark else "rgba(28,28,30,0.90)"
        self._chevron.setStyleSheet(
            f"font-size:11px;color:{cc};background:transparent;border:none;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        c = "rgba(245,245,247,0.82)" if self._dark else "rgba(28,28,30,0.82)"
        self._title.setStyleSheet(
            f"font-size:12px;font-weight:680;color:{c};"
            "background:transparent;border:none;")
        cc = "rgba(245,245,247,0.76)" if self._dark else "rgba(28,28,30,0.76)"
        self._chevron.setStyleSheet(
            f"font-size:11px;color:{cc};background:transparent;border:none;")
        super().leaveEvent(event)


# ── Item ──

class _Item(QFrame):
    clicked = Signal(str)

    def __init__(self, text: str, key: str, icon: str = "",
                 badge: str = "", dark: bool = False):
        super().__init__()
        self._key = key
        self._dark = dark
        self._active = False
        self._icon_name = icon
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(SIDEBAR_ITEM_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        # Icon — fixed size, left side
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(SIDEBAR_ICON, SIDEBAR_ICON)
        self._icon_label.setScaledContents(False)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setStyleSheet("background:transparent;border:none;")
        self._icon_effect = QGraphicsOpacityEffect()
        self._icon_effect.setOpacity(1.0)
        self._icon_label.setGraphicsEffect(self._icon_effect)

        self._load_icon(icon)
        layout.addWidget(self._icon_label)

        # Text — left-aligned, expands with sidebar
        self._label = QLabel(text)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._label.setStyleSheet(
            "font-size:13px;font-weight:520;color:rgba(255,255,255,0.92);"
            "background:transparent;border:none;")
        layout.addWidget(self._label)
        layout.addStretch()

        # Badge — right side, fixed
        self._badge_label = None
        if badge:
            self._badge_label = QLabel(badge)
            self._badge_label.setStyleSheet(
                "font-size:10px;color:rgba(245,245,247,0.45);"
                "background:rgba(255,255,255,0.06);"
                "border-radius:4px;padding:1px 6px;border:none;")
            layout.addWidget(self._badge_label)

        self._refresh_styles()

    def _load_icon(self, name: str):
        path = get_icon(name) if name else ""
        pix = render_svg_icon(path, SIDEBAR_ICON) if path else QPixmap()
        self._icon_label.setPixmap(pix)

    def _refresh_styles(self):
        if self._active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: {SIDEBAR_ACTIVE_GRADIENT};
                    border: 1px solid rgba(255,255,255,0.18);
                    border-radius: 11px;
                    margin: 1px 8px;
                }}
            """)
            self._label.setStyleSheet(
                "font-size:13px;font-weight:650;color:#ffffff;"
                "background:transparent;border:none;")
            if self._icon_effect:
                self._icon_effect.setOpacity(0.90)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: transparent;
                    border: none;
                    border-radius: 10px;
                    margin: 1px 8px;
                }
            """)
            self._label.setStyleSheet(
                "font-size:13px;font-weight:520;color:rgba(255,255,255,0.92);"
                "background:transparent;border:none;")
            if self._icon_effect:
                self._icon_effect.setOpacity(1.0)

    def enterEvent(self, event):
        if not self._active:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(255,255,255,0.085);
                    border: none;
                    border-radius: 10px;
                    margin: 1px 8px;
                }
            """)
            self._label.setStyleSheet(
                "font-size:13px;font-weight:520;"
                "color:rgba(255,255,255,0.98);"
                "background:transparent;border:none;")
            if self._icon_effect:
                self._icon_effect.setOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self._active:
            self._refresh_styles()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._key)
        super().mousePressEvent(event)

    def set_style_active(self, active: bool):
        self._active = active
        self._refresh_styles()

    @property
    def key(self) -> str:
        return self._key

    def text(self) -> str:
        return self._label.text()


# ── Section Container ──

class _Section:
    def __init__(self, parent: QWidget, layout: QVBoxLayout,
                 key: str, title: str, dark: bool):
        self.key = key
        self._items: list[_Item] = []
        self.header = _SectionHeader(title, dark)
        self.header.clicked.connect(self._on_header_click)
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._inner = QVBoxLayout(self._container)
        self._inner.setContentsMargins(0, 0, 0, 0)
        self._inner.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self._container)

    def _on_header_click(self):
        self.header.toggle()
        self._container.setVisible(not self.header.collapsed)

    def add_item(self, item: _Item):
        self._inner.addWidget(item)
        self._items.append(item)

    def destroy(self):
        self.header.setParent(None)
        self.header.deleteLater()
        self._container.setParent(None)
        self._container.deleteLater()
        self._items.clear()


# ── Sidebar Widget ──

class SidebarWidget(QWidget):
    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections: dict[str, _Section] = {}
        self._items: dict[str, _Item] = {}
        self._current_key = "library"
        from ui.theme import is_dark_mode
        self._dark = is_dark_mode()

        self.setObjectName("sidebarGlass")
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.setStyleSheet("""
            QWidget#sidebarGlass {
                background: transparent;
                border: none;
            }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 10, 12)
        outer.setSpacing(8)

        # ── Branding ──
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(4, 4, 4, 4)
        brand_row.setSpacing(10)

        app_icon_label = QLabel()
        app_icon_path = str(Path(__file__).parent.parent / "icons" / "app_icon.png")
        app_pix = QPixmap(app_icon_path)
        if not app_pix.isNull():
            app_icon_label.setPixmap(
                app_pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            app_icon_label.setFixedSize(32, 32)
        app_icon_label.setStyleSheet("background:transparent;border:none;")
        brand_row.addWidget(app_icon_label)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title_lbl = QLabel("ASTRA")
        title_lbl.setStyleSheet(
            "font-size:16px;font-weight:760;color:rgba(255,255,255,0.96);"
            "background:transparent;border:none;")
        sub_lbl = QLabel("Music Player")
        sub_lbl.setStyleSheet(
            "font-size:11px;color:rgba(245,245,247,0.66);"
            "background:transparent;border:none;")
        brand_text.addWidget(title_lbl)
        brand_text.addWidget(sub_lbl)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        outer.addLayout(brand_row)

        outer.addSpacing(4)

        # ── Search ──
        self._search = QLineEdit()
        self._search.setObjectName("sidebarSearch")
        self._search.setPlaceholderText("Buscar")
        self._search.setClearButtonEnabled(True)
        self._search.setStyleSheet("""
            QLineEdit#sidebarSearch {
                background: rgba(255,255,255,0.14);
                border: 1px solid rgba(255,255,255,0.13);
                border-radius: 15px;
                padding: 7px 32px 7px 12px;
                color: rgba(255,255,255,0.94);
                font-size: 13px;
                selection-background-color: rgba(221,0,122,0.45);
            }
            QLineEdit#sidebarSearch:focus {
                background: rgba(255,255,255,0.18);
                border: 1px solid rgba(255,255,255,0.20);
            }
        """)
        self._search.setAttribute(Qt.WA_MacShowFocusRect, False)
        self._search.textChanged.connect(self._filter)
        outer.addWidget(self._search)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.095);")
        outer.addWidget(sep)

        # ── Scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:4px;background:transparent;}"
            "QScrollBar::handle:vertical{"
            "background:rgba(128,128,128,0.30);border-radius:2px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical"
            "{height:0;}")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    def _clear(self):
        for sec in list(self._sections.values()):
            sec.destroy()
        self._sections.clear()
        self._items.clear()

    def add_section(self, key: str, title: str, icon: str = ""):
        n = self._container_layout.count()
        if n > 0:
            stretch_item = self._container_layout.takeAt(n - 1)
            del stretch_item
        sec = _Section(self._container, self._container_layout,
                       key, title, self._dark)
        self._container_layout.addStretch()
        self._sections[key] = sec
        return sec

    def add_item(self, section_key: str, key: str, text: str,
                 icon: str = "", badge: str = ""):
        sec = self._sections.get(section_key)
        if not sec:
            return None
        item = _Item(text, key, icon, badge, self._dark)
        item.clicked.connect(lambda checked=None, k=key: self._on_item_click(k))
        sec.add_item(item)
        self._items[key] = item
        return item

    def _on_item_click(self, key: str):
        self.set_active(key)
        self.item_clicked.emit(key)

    def set_active(self, key: str):
        old = self._items.get(self._current_key)
        if old:
            old.set_style_active(False)
        new = self._items.get(key)
        if new:
            new.set_style_active(True)
            self._current_key = key

    def _filter(self, text: str):
        text = text.lower()
        for item in self._items.values():
            item.setVisible(text == "" or text in item.text().lower())
        for sec in self._sections.values():
            has_vis = any(it.isVisible() for it in sec._items)
            if text != "":
                sec.header.setVisible(has_vis)
                sec._container.setVisible(has_vis and not sec.header.collapsed)
            else:
                sec.header.setVisible(True)
                sec._container.setVisible(not sec.header.collapsed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(70, 74, 88, 250))
        grad.setColorAt(1.0, QColor(48, 52, 64, 250))

        painter.setBrush(grad)
        painter.setPen(QPen(QColor(255, 255, 255, 36), 1))
        painter.drawRoundedRect(rect, 16, 16)

        painter.end()
