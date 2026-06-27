"""HomeController — manages the Home dashboard page refresh lifecycle."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject

from ui.hubs.home_page import HomePage

if TYPE_CHECKING:
    from ui.window import MainWindow

logger = logging.getLogger("michi.home_controller")


class HomeController(QObject):
    """Owns HomePage lifecycle — refreshes stats, servers, devices, current track."""

    def __init__(self, window: MainWindow):
        super().__init__(window)
        self._win = window
        self._page: HomePage | None = None

    @property
    def page(self) -> HomePage | None:
        return self._page

    def _ensure_page(self) -> HomePage:
        if self._page is None:
            self._page = HomePage(
                db=self._win._db,
                playback=self._win._playback,
                window=self._win,
            )
            self._page.navigation_requested.connect(
                self._win._on_sidebar_navigate)
        return self._page

    def show(self):
        """Show the Home page in the content stack."""
        page = self._ensure_page()
        w = self._win
        if not w._views.widget("home"):
            w._views.register("home", page)
        self.refresh()
        w._fade_content("home")

    def refresh(self):
        """Gather fresh data and push to the HomePage."""
        page = self._page
        if page is None:
            return
        try:
            servers = self._get_servers()
            devices = self._get_devices()
            page.refresh(
                items=self._win._all_items,
                servers=servers,
                devices=devices,
            )
        except Exception:
            logger.exception("HomeController refresh failed")

    def _get_servers(self):
        try:
            from streaming.subsonic_client import load_servers
            return load_servers()
        except Exception:
            return []

    def _get_devices(self):
        mgr = getattr(self._win, '_sync_mgr', None)
        if mgr and getattr(mgr, 'is_active', False):
            try:
                return mgr.get_all_peers()
            except Exception:
                return []
        return []
