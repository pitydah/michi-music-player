"""Player bar controller — wraps NowPlayingBar interactions for external controllers."""
import os


class PlayerBarController:
    def __init__(self, player_bar, context_service=None):
        self._player_bar = player_bar
        self._context_svc = context_service

    def set_track(self, name: str, artist: str = "", cover: str = ""):
        self._player_bar.set_track(name, artist, cover)

    def set_track_from_ref(self, track):
        """Resolve cover art from TrackRef and update NowPlayingBar."""
        from library.cover_art_service import CoverArtService
        name = track.title or os.path.basename(track.uri)
        cover_path = track.cover_path or CoverArtService.find_cover(track.uri)
        self.set_track(name, track.artist or "", cover_path or "")

    def set_quality(self, text: str):
        self._player_bar.set_quality(text)

    def set_quality_info(self, label: str, category: str = "unknown",
                         tooltip: str = ""):
        """Set quality badge with category-colored styling."""
        self._player_bar.set_quality_info(label, category, tooltip)
        if self._context_svc and label:
            self._context_svc.record_quality_updated(quality=label, category=category)

    def set_state(self, state: str):
        self._player_bar.set_state(state)

    def set_position(self, pos: int):
        self._player_bar.set_position(pos)

    def set_duration(self, dur: int):
        self._player_bar.set_duration(dur)

    def reset(self):
        """Full stop — complete visual reset."""
        if hasattr(self._player_bar, 'reset_visual_state'):
            self._player_bar.reset_visual_state()
        else:
            self._player_bar.set_state("stopped")
            self._player_bar.set_position(0)
            self._player_bar.set_duration(0)
        if self._context_svc:
            self._context_svc.record_playback_stopped(reason="player_bar_reset")

    def set_transmit_active(self, active: bool, device_name: str = ""):
        self._player_bar.set_transmit_active(active, device_name)

    def transmit_button_position(self):
        """Returns global position under the transmit button for menu placement."""
        return self._player_bar.transmit_button_position()

    def transmit_button(self):
        """Returns the transmit QPushButton for menu positioning."""
        return self._player_bar._transmit_btn

    def audio_output_button(self):
        """Returns the audio output QPushButton for menu positioning."""
        return self._player_bar.audio_output_button()

    def volume_value(self) -> int:
        return self._player_bar.get_volume()

    def change_volume(self, delta: int):
        v = min(100, max(0, self.volume_value() + delta))
        self._player_bar.volume_changed.emit(v)

    def mute(self):
        self._player_bar.volume_changed.emit(0)

    def set_route_tooltip(self, diagnostics):
        """Set audio route diagnostic info via the player bar facade."""
        self._player_bar.set_route_tooltip(diagnostics)
