"""Player bar controller — wraps NowPlayingBar interactions for external controllers."""
import os


class PlayerBarController:
    def __init__(self, player_bar):
        self._bar = player_bar

    def set_track(self, name: str, artist: str = "", cover: str = ""):
        self._bar.set_track(name, artist, cover)

    def set_track_from_ref(self, track):
        """Resolve cover art from TrackRef and update NowPlayingBar."""
        from library.cover_art_service import CoverArtService
        name = track.title or os.path.basename(track.uri)
        cover_path = track.cover_path or CoverArtService.find_cover(track.uri)
        self.set_track(name, track.artist or "", cover_path or "")

    def set_quality(self, text: str):
        self._bar.set_quality(text)

    def set_state(self, state: str):
        self._bar.set_state(state)

    def set_position(self, pos: int):
        self._bar.set_position(pos)

    def set_duration(self, dur: int):
        self._bar.set_duration(dur)

    def reset(self):
        """Full stop — reset all player bar state."""
        self._bar.set_state("stopped")
        self._bar.set_position(0)
        self._bar.set_duration(0)
        self._bar.set_track("Sin reproducción", "Añade música a la biblioteca")

    def set_transmit_active(self, active: bool, device_name: str = ""):
        self._bar.set_transmit_active(active, device_name)

    def transmit_button_position(self):
        """Returns global position under the transmit button for menu placement."""
        return self._bar.transmit_button_position()

    def transmit_button(self):
        """DEPRECATED: use transmit_button_position() instead.
        Returns the transmit QPushButton for menu positioning."""
        return self._bar._transmit_btn

    def volume_value(self) -> int:
        return self._bar.get_volume()

    def change_volume(self, delta: int):
        v = min(100, max(0, self.volume_value() + delta))
        self._bar.volume_changed.emit(v)

    def mute(self):
        self._bar.volume_changed.emit(0)
