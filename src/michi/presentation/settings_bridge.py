"""QML bridge for settings — persisted preference exposure + thin mutations.

Depends on SettingsService. No SQLite, Playback, Library, or Navigation.

M10.3 exposes persisted preferences read-only; M5.C6 adds theme and window
geometry mutation slots. Mutation slots stay thin: they decode/forward to
SettingsService and never touch persistence directly.
"""

import logging

from PySide6.QtCore import Property, QObject, Slot

from michi.application.settings_service import SettingsService
from michi.domain.settings import (
    window_geometry_from_json,
    window_geometry_to_json,
)

logger = logging.getLogger(__name__)


class SettingsBridge(QObject):
    """Thin adapter: SettingsService persisted state → QML properties/slots."""

    def __init__(self, service: SettingsService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service

    def _get_last_directory(self) -> str:
        return self._service.state.last_directory

    def _get_volume(self) -> int:
        return self._service.state.volume

    def _get_muted(self) -> bool:
        return self._service.state.muted

    def _get_theme(self) -> str:
        return self._service.state.theme

    def _get_window_geometry(self) -> str:
        return window_geometry_to_json(self._service.state.window_geometry)

    lastDirectory = Property(str, _get_last_directory)
    volume = Property(int, _get_volume)
    muted = Property(bool, _get_muted)
    theme = Property(str, _get_theme)
    windowGeometry = Property(str, _get_window_geometry)

    @Slot(str)
    def set_theme(self, theme: str) -> None:
        self._service.set_theme(theme)

    @Slot(str)
    def set_window_geometry(self, json_str: str) -> None:
        geometry, malformed = window_geometry_from_json(json_str)
        if malformed:
            logger.warning("ignoring malformed window geometry from QML: %r", json_str)
            return
        self._service.set_window_geometry(geometry)
