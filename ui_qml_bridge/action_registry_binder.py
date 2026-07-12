"""ActionRegistryBinder — injects real action handlers into ActionRegistry.

Registered in BridgeFactory after all bridges are created.
Every action with visible=True and enabled=True has a real handler.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from ui_qml_bridge.action_registry import ActionRegistry

logger = logging.getLogger("michi.action_binder")


class ActionRegistryBinder(QObject):
    dataChanged = Signal()
    def __init__(self, registry: ActionRegistry, bridges: dict[str, object], parent=None):
        super().__init__(parent)
        self._registry = registry
        self._bridges = bridges

    def bind_all(self):
        self._bind_navigation()
        self._bind_playback()
        self._bind_library()
        self._bind_playlist()
        self._bind_metadata()
        self._bind_system()

    def _nav(self):
        return self._bridges.get("navigation")

    def _playback(self):
        return self._bridges.get("playback")

    def _library(self):
        return self._bridges.get("library")

    def _playlists(self):
        return self._bridges.get("playlists")

    def _handler(self, bridge_method):
        def _call():
            try:
                return bridge_method() if callable(bridge_method) else {"ok": True}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return _call

    def _bind_navigation(self):
        nav = self._nav()
        if not nav or not hasattr(nav, 'navigate'):
            return
        routes = {
            "navigate_home": "home",
            "navigate_library": "library",
            "navigate_playlists": "playlists",
            "navigate_radio": "radio",
            "navigate_lyrics": "lyrics",
            "navigate_settings": "settings",
            "navigate_eq": "eq",
            "navigate_audio_lab": "audio_lab",
            "navigate_devices": "devices",
            "navigate_connections": "connections",
            "navigate_home_audio": "home_audio",
            "navigate_jobs": "jobs",
            "navigate_queue": "queue",
            "navigate_history": "history",
            "navigate_library_sources": "library_sources",
            "navigate_diagnostics": "diagnostics",
            "navigate_library_doctor": "library_doctor",
            "navigate_mix": "mix",
        }
        for action_id, route in routes.items():
            action = self._registry.get(action_id)
            if action:
                action.handler = lambda r=route: nav.navigate(r)

    def _bind_playback(self):
        pb = self._playback()
        if not pb:
            return
        actions_map = {
            "playback_playpause": ("togglePlayPause", False),
            "playback_next": ("nextTrack", False),
            "playback_prev": ("previousTrack", False),
            "playback_volume_up": ("volumeUp", False),
            "playback_volume_down": ("volumeDown", False),
            "playback_mute": ("toggleMute", False),
            "playback_seek_forward": ("seekForward", False),
            "playback_seek_back": ("seekBackward", False),
        }
        for action_id, (method, _destructive) in actions_map.items():
            action = self._registry.get(action_id)
            if action and hasattr(pb, method):
                fn = getattr(pb, method)
                action.handler = lambda f=fn: f() if callable(f) else {"ok": True}

    def _bind_library(self):
        lib = self._library()
        if not lib:
            return
        actions_map = {
            "library_refresh": ("refresh", False),
            "library_add_folder": ("scanMusicFolder", False),
        }
        for action_id, (method, _destructive) in actions_map.items():
            action = self._registry.get(action_id)
            if action and hasattr(lib, method):
                fn = getattr(lib, method)
                action.handler = lambda f=fn: f() if callable(f) else {"ok": True}

    def _bind_playlist(self):
        pl = self._playlists()
        if not pl:
            return
        action = self._registry.get("playlist_create")
        if action and hasattr(pl, 'createPlaylist'):
            action.handler = lambda: pl.createPlaylist("Nueva lista")

    def _bind_metadata(self):
        nav = self._nav()
        self._bridges.get("smart_tagging")
        if nav:
            action = self._registry.get("metadata_smart_tagging")
            if action:
                action.handler = lambda: nav.navigate("smart_tagging")
        action = self._registry.get("metadata_edit")
        if action and nav:
            action.handler = lambda: nav.navigate("metadata_inspector")

    def _bind_system(self):
        action = self._registry.get("app_quit")
        if action:
            import sys
            action.handler = lambda: sys.exit(0) or {"ok": True}

    def refresh(self):
        self.dataChanged.emit()
