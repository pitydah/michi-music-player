"""Radio Manager — manages the list of radio stations."""

import os
import json
from dataclasses import dataclass, asdict

CONFIG_DIR = os.path.expanduser("~/.local/share/astra-music-player")
RADIO_FILE = os.path.join(CONFIG_DIR, "radio_stations.json")


@dataclass
class RadioStation:
    name: str
    url: str
    id: int = 0


class RadioManager:
    def __init__(self):
        self._stations: list[RadioStation] = []
        self._next_id = 1
        self._load()

    def _load(self):
        if not os.path.exists(RADIO_FILE):
            return
        try:
            with open(RADIO_FILE, "r") as f:
                data = json.load(f)
                self._stations = [RadioStation(**s) for s in data]
                self._next_id = max([s.id for s in self._stations] + [0]) + 1
        except Exception:
            self._stations = []
            self._next_id = 1

    def _save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(RADIO_FILE, "w") as f:
            json.dump([asdict(s) for s in self._stations], f, indent=2)

    def get_all(self) -> list[RadioStation]:
        return self._stations.copy()

    def add(self, name: str, url: str) -> RadioStation:
        station = RadioStation(name=name, url=url, id=self._next_id)
        self._stations.append(station)
        self._next_id += 1
        self._save()
        return station

    def remove(self, station_id: int) -> bool:
        for i, s in enumerate(self._stations):
            if s.id == station_id:
                del self._stations[i]
                self._save()
                return True
        return False

    def update(self, station_id: int, name: str, url: str) -> bool:
        for s in self._stations:
            if s.id == station_id:
                s.name = name
                s.url = url
                self._save()
                return True
        return False

    def start_recording(self, url: str, output_path: str) -> bool:
        """Record a radio stream to file using GStreamer."""
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        pipeline_str = (
            f"uridecodebin uri={url} ! audioconvert ! "
            f"lamemp3enc target=bitrate bitrate=192 ! "
            f"filesink location={output_path}"
        )
        self._record_pipeline = Gst.parse_launch(pipeline_str)
        if self._record_pipeline:
            self._record_pipeline.set_state(Gst.State.PLAYING)
            return True
        return False

    def stop_recording(self):
        if hasattr(self, '_record_pipeline') and self._record_pipeline:
            self._record_pipeline.set_state(Gst.State.NULL)
            self._record_pipeline = None
