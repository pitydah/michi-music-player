"""MPRIS DBus adapter for KDE Plasma integration.

Implements org.mpris.MediaPlayer2 and Player interfaces using dbus-python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from PySide6.QtCore import QObject
from audio.player import PlaybackState, PlayerEngine

if TYPE_CHECKING:
    from audio.player_service import PlayerService
    from core.protocols.queue_service_protocol import QueueServiceProtocol

SERVICE_NAME = "org.mpris.MediaPlayer2.michi"
OBJECT_PATH = "/org/mpris/MediaPlayer2"


class MPRISObject(dbus.service.Object):
    """Single object implementing both MPRIS interfaces."""

    def __init__(self, bus_name: Any, obj_path: str) -> None:
        super().__init__(bus_name, obj_path)
        self._engine: PlayerEngine | None = None
        self._player_service: PlayerService | None = None
        self._queue_service: QueueServiceProtocol | None = None
        self._metadata: dict[str, Any] = {}
        self._volume = 0.7

    # ── org.mpris.MediaPlayer2 interface ──

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2")
    def Raise(self) -> None:
        return None

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2")
    def Quit(self) -> None:
        return None

    # ── org.mpris.MediaPlayer2.Player interface ──

    def set_engine(self, engine: PlayerEngine) -> None:
        self._engine = engine
        engine.position_changed.connect(self._on_position)
        engine.state_changed.connect(self._on_state)
        engine.duration_changed.connect(self._on_duration)

    def set_player_service(self, player_service: PlayerService) -> None:
        """Listen to PlayerService signals for MPD backend support."""
        self._player_service = player_service

    def set_queue_service(self, queue_service: QueueServiceProtocol) -> None:
        """Use QueueService as the authority for queue navigation."""
        self._queue_service = queue_service

    def set_metadata(
        self,
        title: str = "",
        artist: str = "",
        album: str = "",
        duration: float = 0,
    ) -> None:
        self._metadata = {
            "mpris:trackid": dbus.ObjectPath(f"/michi/{title or 'unknown'}"),
            "xesam:title": title or "Unknown",
            "xesam:artist": dbus.Array([artist or "Unknown"], signature="s"),
            "xesam:album": album or "",
            "mpris:length": dbus.Int64(duration * 1000000),
            "mpris:artUrl": "",
        }
        self.PropertiesChanged(
            "org.mpris.MediaPlayer2.Player",
            {"Metadata": dbus.Dictionary(self._metadata, signature="sv")}, [])

    def set_volume(self, vol: float) -> None:
        self._volume = vol
        self.PropertiesChanged(
            "org.mpris.MediaPlayer2.Player",
            {"Volume": dbus.Double(vol)}, [])

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Next(self) -> None:
        queue = getattr(self, "_queue_service", None)
        if queue:
            queue.next()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Previous(self) -> None:
        queue = getattr(self, "_queue_service", None)
        if queue:
            queue.previous()

    def _player_api(self) -> Any:
        ps = getattr(self, "_player_service", None)
        return ps or self._engine

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Pause(self) -> None:
        api = self._player_api()
        api and api.pause()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def PlayPause(self) -> None:
        api = self._player_api()
        api and api.toggle()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Stop(self) -> None:
        api = self._player_api()
        api and api.stop()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Play(self) -> None:
        ps = getattr(self, "_player_service", None)
        if ps:
            ps.play_or_resume()
        elif self._engine:
            self._engine.resume()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="x")
    def Seek(self, offset: Any) -> None:
        ps = getattr(self, "_player_service", None)
        if ps:
            snap = ps.get_playback_snapshot() if hasattr(ps, "get_playback_snapshot") else None
            pos = snap.position_seconds if snap else 0
            ps.seek(max(0, pos + offset / 1e6))
            return
        if self._engine:
            pos_ns = self._engine.get_position_ns() if hasattr(self._engine, "get_position_ns") else 0
            if pos_ns:
                secs = pos_ns / 1e9 + offset / 1e6
                self._engine.seek(max(0, secs))

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="ox")
    def SetPosition(self, track_id: Any, position: Any) -> None:
        ps = getattr(self, "_player_service", None)
        if ps:
            ps.seek(position / 1e6)
            return
        if self._engine:
            current_us = (self._engine.get_position_ns() // 1000) if hasattr(self._engine, "get_position_ns") else 0
            offset = position - current_us
            self.Seek(offset)

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="s")
    def OpenUri(self, uri: Any) -> None:
        api = self._player_api()
        if api:
            if uri.startswith(("http://", "https://", "icy://")):
                api.play_url(uri)
            else:
                api.play(uri)

    @dbus.service.signal(dbus_interface="org.mpris.MediaPlayer2.Player",
                         signature="x")
    def Seeked(self, position: Any) -> None:
        return None

    @dbus.service.signal(dbus_interface="org.freedesktop.DBus.Properties",
                         signature="sa{sv}as")
    def PropertiesChanged(
        self, interface: Any, changed: Any, invalidated: Any
    ) -> None:
        return None

    # ── org.freedesktop.DBus.Properties ──

    @dbus.service.method(dbus_interface="org.freedesktop.DBus.Properties",
                         in_signature="ss", out_signature="v")
    def Get(self, interface: Any, prop: Any) -> Any:
        return self.GetAll(interface)[prop]

    @dbus.service.method(dbus_interface="org.freedesktop.DBus.Properties",
                         in_signature="ssv")
    def Set(self, interface: Any, prop: Any, value: Any) -> None:
        if interface != "org.mpris.MediaPlayer2.Player":
            return
        queue = self._queue_service
        if prop == "LoopStatus" and queue:
            mode = {"None": "none", "Track": "one", "Playlist": "all"}.get(
                str(value)
            )
            if mode:
                queue.set_repeat(mode)
        elif prop == "Shuffle" and queue:
            queue.set_shuffle(bool(value))
        elif prop == "Volume":
            self.set_volume(float(value))
            api = self._player_api()
            if api and hasattr(api, "set_volume"):
                api.set_volume(int(float(value) * 100))

    @dbus.service.method(dbus_interface="org.freedesktop.DBus.Properties",
                         in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface: Any) -> dict[str, Any]:
        if interface == "org.mpris.MediaPlayer2":
            return {
                "CanQuit": True,
                "CanRaise": True,
                "HasTrackList": False,
                "Identity": "Michi Music Player",
                "DesktopEntry": "michi-music-player",
                "SupportedUriSchemes": ["file", "http", "https"],
                "SupportedMimeTypes": ["audio/mpeg", "audio/flac",
                                      "audio/ogg", "audio/wav",
                                      "audio/x-dsd", "audio/aac"],
            }
        if interface == "org.mpris.MediaPlayer2.Player":
            status = self._get_status()
            player_service = getattr(self, "_player_service", None)
            snapshot = (
                player_service.get_playback_snapshot()
                if player_service and hasattr(player_service, "get_playback_snapshot")
                else None
            )
            if snapshot is not None:
                pos_us = int(snapshot.position_seconds * 1_000_000)
            elif self._engine and hasattr(self._engine, "get_position_ns"):
                pos_us = self._engine.get_position_ns() // 1_000
            else:
                pos_us = 0
            loop_map = {"none": "None", "one": "Track", "all": "Playlist"}
            repeat = self._queue_service.repeat if self._queue_service else "none"
            shuffle = self._queue_service.shuffle if self._queue_service else False
            return {
                "PlaybackStatus": status,
                "LoopStatus": loop_map.get(repeat, "None"),
                "Rate": dbus.Double(1.0),
                "Shuffle": bool(shuffle),
                "Metadata": dbus.Dictionary(self._metadata, signature="sv"),
                "Volume": dbus.Double(self._volume),
                "Position": dbus.Int64(pos_us),
                "MinimumRate": dbus.Double(1.0),
                "MaximumRate": dbus.Double(1.0),
                "CanGoNext": True,
                "CanGoPrevious": True,
                "CanPlay": True,
                "CanPause": True,
                "CanSeek": True,
                "CanControl": True,
            }
        return {}

    # ── Internal slots ──

    def _on_position(self, seconds: float) -> None:
        self.Seeked(int(seconds * 1e6))

    def _on_state(self, state: Any) -> None:
        self.PropertiesChanged(
            "org.mpris.MediaPlayer2.Player",
            {"PlaybackStatus": self._get_status()}, [])

    def _on_duration(self, seconds: float) -> None:
        if seconds > 0 and "mpris:length" in self._metadata:
            self._metadata["mpris:length"] = dbus.Int64(int(seconds * 1e6))
            self.PropertiesChanged(
                "org.mpris.MediaPlayer2.Player",
                {"Metadata": dbus.Dictionary(self._metadata, signature="sv")}, [])

    def _get_status(self) -> str:
        ps = getattr(self, "_player_service", None)
        if ps:
            state = getattr(ps, "state", None)
            if callable(state):
                state = state()
            mapped = {
                "playing": "Playing",
                "paused": "Paused",
                "stopped": "Stopped",
            }.get(state)
            if mapped:
                return mapped
        if not self._engine:
            return "Stopped"
        s = self._engine.state
        if s == PlaybackState.PLAYING:
            return "Playing"
        elif s == PlaybackState.PAUSED:
            return "Paused"
        return "Stopped"


class MPRISAdapter(QObject):
    """Registers MPRIS on the session bus."""

    def __init__(
        self,
        player_service: PlayerService | None = None,
        queue_service: QueueServiceProtocol | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(SERVICE_NAME, bus)
        self._object = MPRISObject(bus_name, OBJECT_PATH)
        if player_service is not None:
            self._object.set_player_service(player_service)
        if queue_service is not None:
            self._object.set_queue_service(queue_service)

    @property
    def player(self) -> MPRISObject:
        return self._object

    def shutdown(self) -> None:
        self._object.remove_from_connection()
