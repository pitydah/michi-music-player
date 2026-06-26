"""Radio Manager — manages the list of radio stations."""
import contextlib
import os
import json
import time
from dataclasses import dataclass, asdict, field

try:
    from gi.repository import Gst
except ImportError:
    Gst = None

CONFIG_DIR = os.path.expanduser("~/.local/share/michi-music-player")
RADIO_FILE = os.path.join(CONFIG_DIR, "radio_stations.json")


@dataclass
class RadioStation:
    name: str
    url: str
    id: int = 0
    image_path: str = ""
    tags: list[str] = field(default_factory=list)
    homepage: str = ""
    country: str = ""
    codec: str = ""
    favorite: bool = False
    last_played: str = ""
    play_count: int = 0


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
            if not isinstance(data, list):
                raise ValueError("Expected JSON array")
            self._stations = []
            for s in data:
                normalized = {
                    "name": s.get("name", ""),
                    "url": s.get("url", ""),
                    "id": s.get("id", 0),
                    "image_path": s.get("image_path", ""),
                    "tags": s.get("tags", []),
                    "homepage": s.get("homepage", ""),
                    "country": s.get("country", ""),
                    "codec": s.get("codec", ""),
                    "favorite": s.get("favorite", False),
                    "last_played": s.get("last_played", ""),
                    "play_count": s.get("play_count", 0),
                }
                self._stations.append(RadioStation(**normalized))
            self._next_id = max([s.id for s in self._stations] + [0]) + 1
        except Exception:
            import logging
            log = logging.getLogger("michi")
            log.warning("Radio stations JSON corrupt — backing up as .broken")
            corrupted = RADIO_FILE + ".broken"
            with contextlib.suppress(OSError):
                os.replace(RADIO_FILE, corrupted)
            self._stations = []
            self._next_id = 1

    def _save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = RADIO_FILE + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump([asdict(s) for s in self._stations], f, indent=2)
            os.replace(tmp, RADIO_FILE)
        except OSError as e:
            import logging
            logging.getLogger("michi").warning("Failed to save radio stations: %s", e)

    def get_all(self) -> list[RadioStation]:
        return self._stations.copy()

    def count(self) -> int:
        return len(self._stations)

    def add(self, name: str, url: str, image_path: str = "",
            tags: list[str] | None = None, homepage: str = "",
            country: str = "", codec: str = "") -> RadioStation:
        station = RadioStation(
            name=name, url=url, id=self._next_id, image_path=image_path,
            tags=tags or [], homepage=homepage, country=country, codec=codec)
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

    def update(self, station_id: int, name: str, url: str, image_path: str = "",
               tags: list[str] | None = None, homepage: str = "",
               country: str = "", codec: str = "") -> bool:
        for s in self._stations:
            if s.id == station_id:
                s.name = name
                s.url = url
                s.image_path = image_path
                s.tags = tags if tags is not None else s.tags
                s.homepage = homepage
                s.country = country
                s.codec = codec
                self._save()
                return True
        return False

    def duplicate(self, station_id: int) -> RadioStation | None:
        for s in self._stations:
            if s.id == station_id:
                new_s = RadioStation(
                    name=f"{s.name} (copia)", url=s.url,
                    id=self._next_id, image_path=s.image_path,
                    tags=list(s.tags), homepage=s.homepage,
                    country=s.country, codec=s.codec)
                self._stations.append(new_s)
                self._next_id += 1
                self._save()
                return new_s
        return None

    def mark_played(self, station_id: int):
        for s in self._stations:
            if s.id == station_id:
                s.last_played = time.strftime("%Y-%m-%d %H:%M")
                s.play_count += 1
                self._save()
                return

    def toggle_favorite(self, station_id: int) -> bool:
        for s in self._stations:
            if s.id == station_id:
                s.favorite = not s.favorite
                self._save()
                return s.favorite
        return False

    def find_by_url(self, url: str) -> RadioStation | None:
        normalized = url.strip().lower()
        for s in self._stations:
            if s.url.strip().lower() == normalized:
                return s
        return None

    def start_recording(self, url: str, output_path: str) -> bool:
        """Record a radio stream to file using GStreamer."""
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)

        safe_url = url.replace("'", "\\'")

        pipeline = Gst.Pipeline.new("radio-record")
        src = Gst.ElementFactory.make("uridecodebin", None)
        conv = Gst.ElementFactory.make("audioconvert", None)

        enc_name = "lamemp3enc"
        enc = Gst.ElementFactory.make(enc_name, None)
        if not enc:
            enc_name = "opusenc"
            enc = Gst.ElementFactory.make(enc_name, None)
        if enc and enc_name == "lamemp3enc":
            enc.set_property("target", "bitrate")
            enc.set_property("bitrate", 192)

        sink = Gst.ElementFactory.make("filesink", None)
        if not all([src, conv, enc, sink]):
            import logging
            logging.getLogger("michi.radio").warning(
                "Missing GStreamer elements for recording: uridecodebin=%s, audioconvert=%s, enc=%s/opusenc=%s, filesink=%s",
                src is not None, conv is not None, enc is not None, enc_name, sink is not None)
            return False

        src.set_property("uri", safe_url)
        sink.set_property("location", output_path)

        for e in [src, conv, enc, sink]:
            pipeline.add(e)
        src.link(conv)
        conv.link(enc)
        enc.link(sink)

        self._record_pipeline = pipeline
        ret = pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            import logging
            logging.getLogger("michi.radio").warning("Failed to start recording pipeline")
            self._record_pipeline = None
            return False
        return True

    def stop_recording(self):
        if hasattr(self, '_record_pipeline') and self._record_pipeline:
            self._record_pipeline.set_state(Gst.State.NULL)
            self._record_pipeline.get_state(Gst.CLOCK_TIME_NONE)
            self._record_pipeline = None
