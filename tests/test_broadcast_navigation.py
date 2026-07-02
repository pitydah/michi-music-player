"""Tests: Broadcast hub navigation — routes, handlers, page instantiation."""

from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap


def _pix():
    pix = QPixmap(1, 1)
    pix.fill(Qt.transparent)
    return pix


class TestBroadcastNav:
    def test_broadcast_route_in_nav_routes(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        assert "broadcast_hub" in NAV_ROUTES

    def test_broadcast_route_has_handler(self):
        from ui.controllers.navigation_controller import NAV_ROUTES
        import ui.window
        method_name = NAV_ROUTES["broadcast_hub"]
        assert hasattr(ui.window.MainWindow, method_name), (
            f"broadcast_hub -> {method_name} missing"
        )

    def test_broadcast_sidebar_key(self):
        from ui.controllers.navigation_controller import resolve_sidebar_active_key
        assert resolve_sidebar_active_key("broadcast_hub") == "broadcast_hub"

    def test_broadcast_section_config(self):
        from ui.controllers.navigation_controller import SECTION_CONFIG
        assert "broadcast_hub" in SECTION_CONFIG
        assert SECTION_CONFIG["broadcast_hub"]["title"] == "Transmisiones"


def _fake_card(*a, **kw):
    from PySide6.QtWidgets import QFrame, QLabel
    card = QFrame()
    card._value_label = QLabel("0")
    return card

@patch("ui.broadcast.broadcast_hub_page.summary_card", side_effect=_fake_card)
def test_broadcast_page_renders(mock_card, qtbot):
    """Verify BroadcastHubPage instantiates and has all 5 tabs."""
    from streaming.radio_manager import RadioManager
    from ui.broadcast.broadcast_hub_page import BroadcastHubPage
    rm = RadioManager()
    page = BroadcastHubPage(radio_manager=rm)
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()
    assert page.navigate_requested is not None
    assert page._current_tab == "live"
    assert "live" in page._tab_widgets
    assert "podcasts" in page._tab_widgets
    assert "episodes" in page._tab_widgets
    assert "downloads" in page._tab_widgets
    assert "history" in page._tab_widgets


@patch("ui.broadcast.broadcast_hub_page.summary_card", side_effect=_fake_card)
def test_broadcast_tab_switching(mock_card, qtbot):
    """Verify tab switching works."""
    from streaming.radio_manager import RadioManager
    from ui.broadcast.broadcast_hub_page import BroadcastHubPage
    rm = RadioManager()
    page = BroadcastHubPage(radio_manager=rm)
    qtbot.addWidget(page)
    page._switch_tab("podcasts")
    assert page._current_tab == "podcasts"
    page._switch_tab("history")
    assert page._current_tab == "history"


@patch("ui.broadcast.broadcast_hub_page.summary_card", side_effect=_fake_card)
def test_broadcast_no_radio_manager_no_crash(mock_card, qtbot):
    """Verify page works without radio manager."""
    from ui.broadcast.broadcast_hub_page import BroadcastHubPage
    page = BroadcastHubPage(radio_manager=None)
    qtbot.addWidget(page)
    page.show()
    assert page.isVisible()
