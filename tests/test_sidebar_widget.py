"""Tests for SidebarWidget — modular glass dark sidebar."""
from PySide6.QtWidgets import QApplication
import sys

_app = QApplication.instance() or QApplication(sys.argv)


def test_sidebar_instantiate():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    assert w is not None


def test_add_section():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    sec = w.add_section("library", "Biblioteca")
    assert sec is not None
    assert "library" in w._sections


def test_add_item():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    w.add_section("library", "Biblioteca")
    item = w.add_item("library", "albums", "Álbumes", "album")
    assert item is not None
    assert "albums" in w._items
    assert item.text() == "Álbumes"


def test_set_active():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    w.add_section("library", "Biblioteca")
    w.add_item("library", "albums", "Álbumes", "album")
    w.add_item("library", "songs", "Canciones", "music_note")
    w.set_active("albums")
    assert w._current_key == "albums"
    assert w._items["albums"]._active is True
    assert w._items["songs"]._active is False


def test_filter_shows_matching():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    w.show()
    w.add_section("library", "Biblioteca")
    w.add_item("library", "albums", "Álbumes", "album")
    w.add_item("library", "songs", "Canciones", "music_note")
    w._filter("álb")
    assert not w._items["albums"].isHidden()
    assert w._items["songs"].isHidden()


def test_filter_empty_restores():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    w.show()
    w.add_section("library", "Biblioteca")
    w.add_item("library", "albums", "Álbumes", "album")
    w._filter("álb")
    w._filter("")
    assert not w._items["albums"].isHidden()


def test_item_click_emits():
    from ui.sidebar_widget import SidebarWidget
    w = SidebarWidget()
    w.add_section("library", "Biblioteca")
    w.add_item("library", "albums", "Álbumes", "album")
    emitted = []

    def _on_click(k):
        emitted.append(k)

    w.item_clicked.connect(_on_click)
    w._on_item_click("albums")
    assert "albums" in emitted


def test_sidebar_item_badge():
    from ui.sidebar.sidebar_item import SidebarItem
    item = SidebarItem("Home Audio", "home_audio", "speaker", "NEW", dark=True)
    assert item.key == "home_audio"
    assert item.text() == "Home Audio"
    assert item._badge_label is not None
    item.set_active(True)
    assert item._active is True
