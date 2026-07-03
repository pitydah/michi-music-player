"""MPRIS DBus adapter for KDE Plasma integration.

Implements org.mpris.MediaPlayer2 and Player interfaces using dbus-python.
"""

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from PySide6.QtCore import QObject
from audio.player import PlaybackState, PlayerEngine

SERVICE_NAME = "org.mpris.MediaPlayer2.michi"
OBJECT_PATH = "/org/mpris/MediaPlayer2"


class MPRISObject(dbus.service.Object):
    """Single object implementing both MPRIS interfaces."""

    def __init__(self, bus_name, obj_path):
        super().__init__(bus_name, obj_path)
        self._engine: PlayerEngine | None = None
        self._metadata = {}
        self._volume = 0.7

    # ── org.mpris.MediaPlayer2 interface ──

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2")
    def Raise(self):
        pass

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2")
    def Quit(self):
        pass

    # ── org.mpris.MediaPlayer2.Player interface ──

    def set_engine(self, engine):
        self._engine = engine
        engine.position_changed.connect(self._on_position)
        engine.state_changed.connect(self._on_state)
        engine.duration_changed.connect(self._on_duration)

    def set_player_service(self, player_service):
        """Listen to PlayerService signals for MPD backend support."""
        self._player_service = player_service

    @property
    def _playback_state(self):
        if not self._engine:
            return "Stopped"
        s = self._engine.state
        if s == PlaybackState.PLAYING:
            return "Playing"
        elif s == PlaybackState.PAUSED:
            return "Paused"
        return "Stopped"

    def set_metadata(self, title="", artist="", album="", duration=0):
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

    def set_volume(self, vol: float):
        self._volume = vol
        self.PropertiesChanged(
            "org.mpris.MediaPlayer2.Player",
            {"Volume": dbus.Double(vol)}, [])

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Next(self):
        api = self._player_api()
        api and api.play_next()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Previous(self):
        api = self._player_api()
        api and api.play_prev()

    def _player_api(self):
        ps = getattr(self, '_player_service', None)
        return ps or self._engine

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Pause(self):
        api = self._player_api()
        api and api.pause()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def PlayPause(self):
        api = self._player_api()
        api and api.toggle()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Stop(self):
        api = self._player_api()
        api and api.stop()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player")
    def Play(self):
        ps = getattr(self, '_player_service', None)
        if ps:
            ps.play_or_resume()
        elif self._engine:
            self._engine.resume()

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="x")
    def Seek(self, offset):
        ps = getattr(self, '_player_service', None)
        if ps:
            snap = ps.get_playback_snapshot() if hasattr(ps, 'get_playback_snapshot') else None
            pos = snap.position_seconds if snap else 0
            ps.seek(max(0, pos + offset / 1e6))
            return
        if self._engine:
            pos_ns = self._engine.get_position_ns() if hasattr(self._engine, 'get_position_ns') else 0
            if pos_ns:
                secs = pos_ns / 1e9 + offset / 1e6
                self._engine.seek(max(0, secs))

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="ox")
    def SetPosition(self, track_id, position):
        ps = getattr(self, '_player_service', None)
        if ps:
            ps.seek(position / 1e6)
            return
        if self._engine:
            current_us = (self._engine.get_position_ns() // 1000) if hasattr(self._engine, 'get_position_ns') else 0
            offset = position - current_us
            self.Seek(offset)

    @dbus.service.method(dbus_interface="org.mpris.MediaPlayer2.Player",
                         in_signature="s")
    def OpenUri(self, uri):
        api = self._player_api()
        if api:
            if uri.startswith(("http://", "https://", "icy://")):
                api.play_url(uri)
            else:
                api.play(uri)

    @dbus.service.signal(dbus_interface="org.mpris.MediaPlayer2.Player",
                         signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.signal(dbus_interface="org.freedesktop.DBus.Properties",
                         signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    # ── org.freedesktop.DBus.Properties ──

    @dbus.service.method(dbus_interface="org.freedesktop.DBus.Properties",
                         in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.GetAll(interface)[prop]

    @dbus.service.method(dbus_interface="org.freedesktop.DBus.Properties",
                         in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
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
            status = "Stopped"
            if self._engine:
                s = self._engine.state
                if s == PlaybackState.PLAYING:
                    status = "Playing"
                elif s == PlaybackState.PAUSED:
                    status = "Paused"
            pos_us = (self._engine.get_position_ns() // 1000) if (self._engine and hasattr(self._engine, 'get_position_ns')) else 0
            loop_map = {"none": "None", "one": "Track", "all": "Playlist"}
            repeat = getattr(self._engine, '_repeat', 'none') or 'none'
            shuffle = getattr(self._engine, '_shuffle', False)
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

    def _on_position(self, seconds):
        self.Seeked(int(seconds * 1e6))

    def _on_state(self, state):
        self.PropertiesChanged(
            "org.mpris.MediaPlayer2.Player",
            {"PlaybackStatus": self._get_status()}, [])

    def _on_duration(self, seconds):
        if seconds > 0 and "mpris:length" in self._metadata:
            self._metadata["mpris:length"] = dbus.Int64(int(seconds * 1e6))
            self.PropertiesChanged(
                "org.mpris.MediaPlayer2.Player",
                {"Metadata": dbus.Dictionary(self._metadata, signature="sv")}, [])

    def _get_status(self):
        ps = getattr(self, '_player_service', None)
        if ps:
            state = getattr(ps, 'state', None)
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

    def __init__(self, parent=None):
        super().__init__(parent)
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(SERVICE_NAME, bus)
        self._object = MPRISObject(bus_name, OBJECT_PATH)

    @property
    def player(self) -> MPRISObject:
        return self._object
