"""Sidebar Widget — premium glass dark navigation panel.
Public facade using modular sidebar components.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QScrollArea, QSizePolicy,
)

from ui.sidebar.sidebar_panel import SidebarPanel
from ui.sidebar.sidebar_brand import SidebarBrand
from ui.sidebar.sidebar_search import SidebarSearch
from ui.sidebar.sidebar_item import SidebarItem
from ui.sidebar.sidebar_section import SidebarSection
from ui.sidebar.sidebar_styles import sidebar_root_qss, scroll_area_qss


class SidebarWidget(QWidget):
    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sections: dict[str, SidebarSection] = {}
        self._items: dict[str, SidebarItem] = {}
        self._current_key = "library"
        from ui.theme import is_dark_mode
        self._dark = is_dark_mode()

        self.setObjectName("sidebarGlass")
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.setStyleSheet(sidebar_root_qss())

        # Main layout — SidebarPanel paints the glass background
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._panel = SidebarPanel(self)
        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(14, 14, 10, 12)
        panel_layout.setSpacing(8)
        main_layout.addWidget(self._panel)

        # ── Brand ──
        self._brand = SidebarBrand(self._panel)
        panel_layout.addWidget(self._brand)

        panel_layout.addSpacing(4)

        # ── Search ──
        self._search = SidebarSearch(self._panel)
        self._search.search_changed.connect(self._filter)
        panel_layout.addWidget(self._search)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(255,255,255,0.095);")
        panel_layout.addWidget(sep)

        # ── Scroll area ──
        self._scroll = QScrollArea(self._panel)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet(scroll_area_qss())

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        self._container_layout.addStretch()

        self._scroll.setWidget(self._container)
        panel_layout.addWidget(self._scroll)

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
        sec = SidebarSection(self._container, self._container_layout,
                             key, title, self._dark)
        self._container_layout.addStretch()
        self._sections[key] = sec
        return sec

    def add_item(self, section_key: str, key: str, text: str,
                 icon: str = "", badge: str = ""):
        sec = self._sections.get(section_key)
        if not sec:
            return None
        item = SidebarItem(text, key, icon, badge, self._dark)
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
            old.set_active(False)
        new = self._items.get(key)
        if new:
            new.set_active(True)
            self._current_key = key

    def _filter(self, text: str):
        text = text.lower()
        for item in self._items.values():
            matches = text == "" or text in item.text().lower()
            item.setVisible(matches)
        for sec in self._sections.values():
            has_vis = any(it.isVisible() for it in sec._items) if text != "" else True
            if text != "":
                sec.header.setVisible(has_vis)
                sec._container.setVisible(has_vis and not sec.header.collapsed)
            else:
                sec.header.setVisible(True)
                sec._container.setVisible(not sec.header.collapsed)
