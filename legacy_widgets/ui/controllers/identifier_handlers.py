"""LEGACY - reemplazado por ui_qml_bridge correspondiente."""

"""Identifier handlers — music recognition toggle, track detection, and signal wiring."""
import os


class IdentifierHandlers:
    def __init__(self, window):
        self._win = window

    def toggle(self, enabled: bool):
        self._win._identifier_ctrl.enabled = enabled
        self._win._identifier_view.set_identifier_enabled(enabled)
        if not enabled:
            self._win._identifier_ctrl.stop()

    def clear_detected(self):
        self._win._db.clear_detected_tracks()
        self._win._identifier_view.set_detected_tracks([])

    def on_track_detected(self, track):
        self._win._identifier_view.set_detected_tracks(
            self._win._db.get_detected_tracks(100))

    def on_detection_failed(self, error: str):
        self._win._identifier_view.set_status_message(error)

    def on_track_selected(self, track: dict):
        filepath = track.get("filepath")
        if filepath and os.path.exists(filepath):
            self._win._play_file(filepath)
        else:
            title = track.get("title", "")
            artist = track.get("artist", "")
            if title or artist:
                self._win._search.setText(f"{title} {artist}")
                self._win._search_ctrl.set_active("local")
                self._win._search_ctrl.search(f"{title} {artist}")

    def on_settings(self):
        self._win._show_preferences("identifier")

    def on_play(self, track: dict):
        fp = track.get("matched_filepath") or track.get("filepath", "")
        if fp and os.path.isfile(fp):
            self._win._play_file(fp)
        else:
            self._win._toast_svc.show("Archivo no encontrado en biblioteca", "info")

    def on_search(self, track: dict):
        title = track.get("title", "")
        artist = track.get("artist", "")
        if title or artist:
            self._win._search.setText(f"{title} {artist}")
            self._win._search_ctrl.set_active("local")
            self._win._search_ctrl.search(f"{title} {artist}")

    def on_delete(self, track: dict):
        idx = track.get("id", 0)
        if hasattr(self._win._db, 'delete_detected_track'):
            self._win._db.delete_detected_track(idx)
            self._win._identifier_view.set_detected_tracks(
                self._win._db.get_detected_tracks(100))

    def wire_signals(self):
        v = self._win._identifier_view
        v.toggle_requested.connect(self.toggle)
        v.clear_requested.connect(self.clear_detected)
        v.track_selected.connect(self.on_track_selected)
        v.identify_once_requested.connect(
            lambda: self._win._identifier_ctrl.identify_once()
            if self._win._identifier_ctrl else None)
        v.settings_requested.connect(self.on_settings)
        v.play_track_requested.connect(self.on_play)
        v.search_track_requested.connect(self.on_search)
        v.delete_track_requested.connect(self.on_delete)
        if self._win._detection:
            self._win._detection.track_detected.connect(self.on_track_detected)
            self._win._detection.detection_failed.connect(self.on_detection_failed)
        if self._win._identifier_ctrl:
            self._win._identifier_ctrl.state_changed.connect(
                self._win._identifier_view.set_identifier_state)
            self._win._identifier_ctrl.source_changed.connect(
                self._win._identifier_view.set_source_status)
            self._win._identifier_ctrl.provider_changed.connect(
                self._win._identifier_view.set_provider_status)

    def show(self, key):
        self._win._identifier_view.set_detected_tracks(
            self._win._db.get_detected_tracks(100))
        self._win._fade_content("identifier")
