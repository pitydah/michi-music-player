"""Library preferences coordination — syncs runtime directory with Settings."""

from michi.application.library_service import LibraryService
from michi.application.settings_service import SettingsService


class LibraryPreferencesCoordinator:
    """Restore persisted last_directory on start, update on successful scan.

    Never calls scanner, never auto-scans, never touches recent_files.
    """

    def __init__(self, library: LibraryService, settings: SettingsService) -> None:
        self._library = library
        self._settings = settings
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        # Restore persisted directory as hint (no scan)
        last = self._settings.state.last_directory
        self._library.restore_directory_hint(last)
        # Subscribe to scan-driven changes
        self._library.subscribe_changed(self._on_library_changed)

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        self._library.unsubscribe_changed(self._on_library_changed)

    def _on_library_changed(self) -> None:
        directory = self._library.state.current_directory
        if not directory:
            return
        if directory == self._settings.state.last_directory:
            return
        self._settings.set_last_directory(directory)
