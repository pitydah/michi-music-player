"""QML bridge for settings — read-only persisted preference exposure.

Depends on SettingsService. No SQLite, Playback, Library, or Navigation.

M10.3 exposes persisted preferences read-only.
Future Settings UI mutations must preserve capability ownership:
runtime playback changes go through PlaybackService,
library changes go through LibraryService,
and SettingsService remains the persisted preference owner.
"""

from PySide6.QtCore import Property, QObject

from michi.application.settings_service import SettingsService


class SettingsBridge(QObject):
    """Thin adapter: SettingsService persisted state → QML read-only properties."""

    def __init__(self, service: SettingsService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service

    def _get_last_directory(self) -> str:
        return self._service.state.last_directory

    def _get_volume(self) -> int:
        return self._service.state.volume

    def _get_muted(self) -> bool:
        return self._service.state.muted

    lastDirectory = Property(str, _get_last_directory)
    volume = Property(int, _get_volume)
    muted = Property(bool, _get_muted)
