"""ThemeService — canonical owner of theme state (mode, accent, artwork background).

Single authority per ADR-002: the theme mode, accent color, compact mode and
the artwork-derived background live HERE; QSettings persistence happens only
through this service (single write path); QML bridges are thin adapters that
re-expose the service state and re-emit its signals. The artwork color
extraction is delegated to ``BackgroundThemeService`` (a pure utility — it
keeps no parallel theme state).

``health()`` reports operational state plus the number of registered UI
consumers (bridges call ``register_consumer``), so health honestly reflects
whether the UI actually consumes the service.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.theme_service")

DEFAULT_THEME = "dark"
DEFAULT_ACCENT = "#8FB7FF"
DEFAULT_BG_PRIMARY = "#090B11"
DEFAULT_BG_DARKER = "#06080D"


class ThemeService(QObject):
    themeChanged = Signal(str)
    accentChanged = Signal(str)
    compactModeChanged = Signal(bool)
    backgroundChanged = Signal(str, str)  # primary_color, darker_color
    stateChanged = Signal()

    VALID_THEMES = ("dark", "light", "system", "high_contrast")

    def __init__(self, settings=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._consumers: dict[str, bool] = {}
        self._last_persisted_ok = True
        self._last_persist_error = ""
        from core.background_theme_service import BackgroundThemeService
        self._extractor = BackgroundThemeService()
        self._theme = DEFAULT_THEME
        self._accent_color = DEFAULT_ACCENT
        self._compact_mode = False
        self._bg_primary = DEFAULT_BG_PRIMARY
        self._bg_darker = DEFAULT_BG_DARKER
        self._load_persisted()

    # ── Persistence (single write path) ──

    def _read(self, key: str, default: Any) -> Any:
        settings = self._settings
        if settings is None:
            try:
                from core.settings_manager import get
                return get(key)
            except Exception:
                return default
        try:
            value = settings.value(key, default)
            return default if value is None else value
        except Exception:
            return default

    def _write(self, key: str, value: Any) -> None:
        try:
            settings = self._settings
            if settings is None:
                from core.settings_manager import set_
                set_(key, value)
            else:
                settings.setValue(key, value)
            self._last_persisted_ok = True
            self._last_persist_error = ""
        except Exception as exc:
            self._last_persisted_ok = False
            self._last_persist_error = str(exc)[:200]
            logger.error("ThemeService: failed to persist '%s': %s", key, exc)

    def _load_persisted(self) -> None:
        raw_theme = self._read("appearance/theme", DEFAULT_THEME)
        theme = str(raw_theme).lower()
        if theme not in self.VALID_THEMES:
            theme = DEFAULT_THEME
        self._theme = theme
        raw_accent = self._read("appearance/accent_color", DEFAULT_ACCENT)
        self._accent_color = str(raw_accent) if raw_accent else DEFAULT_ACCENT
        try:
            self._compact_mode = bool(self._read("appearance/compact_mode", False))
        except Exception:
            self._compact_mode = False

    # ── State ──

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def dark_mode(self) -> bool:
        return self._theme != "light"

    @property
    def accent_color(self) -> str:
        return self._accent_color

    @property
    def compact_mode(self) -> bool:
        return self._compact_mode

    @property
    def background_primary(self) -> str:
        return self._bg_primary

    @property
    def background_darker(self) -> str:
        return self._bg_darker

    # ── Setters (persist + emit; single write path) ──

    def set_theme(self, value: str) -> None:
        value = str(value or "").lower()
        if value not in self.VALID_THEMES:
            value = DEFAULT_THEME
        if value == self._theme:
            return
        self._theme = value
        self._write("appearance/theme", value)
        self.themeChanged.emit(value)
        self.stateChanged.emit()

    def set_accent_color(self, color: str) -> None:
        color = str(color or "")
        if not color.startswith("#"):
            color = f"#{color}"
        if color == self._accent_color:
            return
        self._accent_color = color
        self._write("appearance/accent_color", color)
        self.accentChanged.emit(color)
        self.stateChanged.emit()

    def set_compact_mode(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._compact_mode:
            return
        self._compact_mode = enabled
        self._write("appearance/compact_mode", enabled)
        self.compactModeChanged.emit(enabled)
        self.stateChanged.emit()

    # ── Artwork-derived background ──

    def extract_colors(self, pixmap) -> tuple[str, str]:
        """Extract primary/darker colors from artwork (no state mutation)."""
        return self._extractor.extract_colors(pixmap)

    def set_artwork_background(self, pixmap) -> None:
        """Apply artwork-derived background colors into theme state."""
        if pixmap is None or pixmap.isNull():
            self.reset_background()
            return
        primary, darker = self._extractor.extract_colors(pixmap)
        self._bg_primary = primary
        self._bg_darker = darker
        self.backgroundChanged.emit(primary, darker)
        self.stateChanged.emit()

    def apply_background(self, primary: str, darker: str) -> None:
        """Push explicit background colors into theme state."""
        primary = str(primary or DEFAULT_BG_PRIMARY)
        darker = str(darker or DEFAULT_BG_DARKER)
        self._bg_primary = primary
        self._bg_darker = darker
        self.backgroundChanged.emit(primary, darker)
        self.stateChanged.emit()

    def reset_background(self) -> None:
        self._bg_primary = DEFAULT_BG_PRIMARY
        self._bg_darker = DEFAULT_BG_DARKER
        self.backgroundChanged.emit(DEFAULT_BG_PRIMARY, DEFAULT_BG_DARKER)
        self.stateChanged.emit()

    # ── Consumers (health: does the UI actually consume this service?) ──

    def register_consumer(self, name: str) -> None:
        self._consumers[name] = True
        logger.debug("ThemeService: consumer '%s' registered", name)

    def unregister_consumer(self, name: str) -> None:
        self._consumers.pop(name, None)

    @property
    def consumer_count(self) -> int:
        return len(self._consumers)

    # ── Health ──

    def health(self) -> dict:
        """Honest health: operational + persistence ok + UI consumers."""
        settings_ok = True
        try:
            self._read("appearance/theme", DEFAULT_THEME)
        except Exception:
            settings_ok = False
        return {
            "available": True,
            "operational": True,
            "settings_ok": settings_ok,
            "last_persisted_ok": self._last_persisted_ok,
            "last_persist_error": self._last_persist_error,
            "consumers": self.consumer_count,
            "theme": self._theme,
            "accent_color": self._accent_color,
        }

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
