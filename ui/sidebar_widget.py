"""Sidebar Widget — premium scrollable sections with collapsible headers."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QPixmap, QPainter, QColor, QLinearGradient, QRadialGradient, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QFrame, QScrollArea, QSizePolicy,
)

from ui.icon_loader import get_sidebar_icon
from ui.design_tokens import (
    SIDEBAR_ITEM_H, SIDEBAR_ICON,
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
        layout.setContentsMargins(12, 14, 12, 4)
        layout.setSpacing(0)

        txt_c = "rgba(255,255,255,0.42)" if dark else "rgba(28,28,30,0.42)"
        self._title = QLabel(text.upper())
        self._title.setStyleSheet(
            f"font-size:11px;font-weight:720;color:{txt_c};"
            "background:transparent;border:none;")
        layout.addWidget(self._title)
        layout.addStretch()

        chev_c = "rgba(255,255,255,0.38)" if dark else "rgba(28,28,30,0.38)"
        self._chevron = QLabel("\u25be")  # ▾ expanded
        self._chevron.setStyleSheet(
            f"font-size:10px;color:{chev_c};background:transparent;border:none;")
        self._chevron.setFixedWidth(14)
        self._chevron.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._chevron)

    def toggle(self) -> bool:
        self._collapsed = not self._collapsed
        self._chevron.setText("\u25b8" if self._collapsed else "\u25be")  # ▸ / ▾
        return self._collapsed

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        c = "rgba(255,255,255,0.70)" if self._dark else "rgba(28,28,30,0.70)"
        self._title.setStyleSheet(
            f"font-size:11px;font-weight:720;color:{c};"
            "background:transparent;border:none;")
        cc = "rgba(255,255,255,0.62)" if self._dark else "rgba(28,28,30,0.62)"
        self._chevron.setStyleSheet(
            f"font-size:10px;color:{cc};background:transparent;border:none;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        c = "rgba(255,255,255,0.42)" if self._dark else "rgba(28,28,30,0.42)"
        self._title.setStyleSheet(
            f"font-size:11px;font-weight:720;color:{c};"
            "background:transparent;border:none;")
        cc = "rgba(255,255,255,0.38)" if self._dark else "rgba(28,28,30,0.38)"
        self._chevron.setStyleSheet(
            f"font-size:10px;color:{cc};background:transparent;border:none;")
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
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        # Accent bar — visible only when active
        self._accent = QFrame()
        self._accent.setFixedWidth(3)
        self._accent.setStyleSheet(
            "background: transparent; border-radius: 2px; border: none;")
        layout.addWidget(self._accent)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(SIDEBAR_ICON, SIDEBAR_ICON)
        self._icon_label.setScaledContents(False)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._icon_label.setStyleSheet(
            "background: transparent; border: none; padding: 0px; margin: 0px;")

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
        if name:
            pix = get_sidebar_icon(name, active=self._active, size=SIDEBAR_ICON)
        else:
            pix = QPixmap(SIDEBAR_ICON, SIDEBAR_ICON)
            pix.fill(Qt.transparent)
        self._icon_label.setPixmap(pix)

    def _refresh_styles(self):
        if self._active:
            self.setStyleSheet(
                "background: qlineargradient("
                "  x1:0, y1:0, x2:1, y2:0,"
                "  stop:0 rgba(110,150,255,0.16),"
                "  stop:1 rgba(255,255,255,0.07));"
                "border: 1px solid rgba(255,255,255,0.12);"
                "border-radius: 12px; margin: 1px 6px;")
            self._label.setStyleSheet(
                "font-size:13px;font-weight:680;color:#FFFFFF;"
                "background:transparent;border:none;")
            self._accent.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                " stop:0 #7AA7FF, stop:1 #D85CFF);"
                " border-radius: 2px; border: none;")
            if self._badge_label:
                self._badge_label.setStyleSheet(
                    "font-size:10px;color:rgba(245,245,247,0.72);"
                    "background:rgba(255,255,255,0.10);"
                    "border-radius:5px;padding:1px 7px;border:none;")
            self._load_icon(self._icon_name)
        else:
            self.setStyleSheet(
                "background: transparent; border: none;"
                "border-radius: 12px; margin: 1px 6px;")
            self._label.setStyleSheet(
                "font-size:13px;font-weight:540;color:rgba(255,255,255,0.74);"
                "background:transparent;border:none;")
            self._accent.setStyleSheet(
                "background: transparent; border-radius: 2px; border: none;")
            if self._badge_label:
                self._badge_label.setStyleSheet(
                    "font-size:10px;color:rgba(245,245,247,0.45);"
                    "background:rgba(255,255,255,0.06);"
                    "border-radius:5px;padding:1px 7px;border:none;")

    def enterEvent(self, event):
        if not self._active:
            self.setStyleSheet(
                "background: rgba(255,255,255,0.06);"
                "border: 1px solid rgba(255,255,255,0.075);"
                "border-radius: 12px; margin: 1px 6px;")
            self._label.setStyleSheet(
                "font-size:13px;font-weight:600;"
                "color:rgba(255,255,255,0.94);"
                "background:transparent;border:none;")
            self._accent.setStyleSheet(
                "background: transparent; border-radius: 2px; border: none;")
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
        brand_card = QFrame()
        brand_card.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04);"
            "  border: 1px solid rgba(255,255,255,0.07);"
            "  border-radius: 14px; }")
        brand_inner = QHBoxLayout(brand_card)
        brand_inner.setContentsMargins(10, 8, 10, 8)
        brand_inner.setSpacing(10)

        app_icon_label = QLabel()
        app_icon_path = str(Path(__file__).parent.parent / "icons" / "app_icon.png")
        app_pix = QPixmap(app_icon_path)
        if not app_pix.isNull():
            app_icon_label.setPixmap(
                app_pix.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            app_icon_label.setFixedSize(34, 34)
        app_icon_label.setStyleSheet("background:transparent;border:none;")
        brand_inner.addWidget(app_icon_label)

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
        brand_inner.addLayout(brand_text)
        brand_inner.addStretch()
        outer.addWidget(brand_card)

        outer.addSpacing(4)

        # ── Search ──
        self._search = QLineEdit()
        self._search.setObjectName("sidebarSearch")
        self._search.setPlaceholderText("Buscar en Astra")
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
            "QScrollBar:vertical{width:3px;background:transparent;}"
            "QScrollBar::handle:vertical{"
            "background:rgba(255,255,255,0.18);min-height:36px;border-radius:2px;}"
            "QScrollBar::handle:vertical:hover{background:rgba(255,255,255,0.32);}"
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

        # Base dark gradient
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(31, 35, 48, 248))
        grad.setColorAt(0.4, QColor(24, 27, 38, 248))
        grad.setColorAt(1.0, QColor(14, 17, 26, 248))

        painter.setBrush(grad)
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1))
        painter.drawRoundedRect(rect, 16, 16)

        # Subtle blue glow from top-left
        glow = QRadialGradient(rect.topLeft(), rect.width())
        glow.setColorAt(0.0, QColor(80, 120, 255, 22))
        glow.setColorAt(0.6, QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 16, 16)

        painter.end()
