"""MPRIS controller — manages D-Bus MPRIS integration with graceful fallback."""
import contextlib
import logging


class MPRISController:
    def __init__(self, window):
        self._win = window
        self._adapter = None

    def init(self):
        """Initialize MPRIS if DBus is available. Never raises."""
        try:
            from adapters.mpris import MPRISAdapter
            self._adapter = MPRISAdapter(self._win)
            self._adapter.player.set_engine(self._win._ctx.player)
        except Exception:
            logging.getLogger("astra").debug("MPRIS integration not available (no dbus)")

    @property
    def adapter(self):
        return self._adapter

    @property
    def is_active(self) -> bool:
        return self._adapter is not None

    def update_metadata(self, title: str, artist: str = "",
                        album: str = "", duration: int = 0):
        """Update MPRIS metadata if the adapter is active."""
        if self._adapter:
            with contextlib.suppress(Exception):
                self._adapter.player.set_metadata(
                    title=title, artist=artist,
                    album=album, duration=duration)
