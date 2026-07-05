"""MetadataBridge — metadata inspector and editor for QML.

Supports read, write, artwork, and batch operations.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from pathlib import Path
import contextlib

logger = logging.getLogger("michi.metadata")

_NA = "No disponible"


def _read_full_metadata(filepath: str) -> dict:
    p = Path(filepath)
    if not p.is_file():
        return {"error": "FILE_NOT_FOUND"}
    result = {
        "title": p.stem, "artist": "", "album": "", "album_artist": "",
        "genre": "", "year": 0, "track_number": 0, "track_total": 0,
        "disc_number": 0, "disc_total": 0, "composer": "", "comment": "",
        "bpm": 0, "format": p.suffix.lower().lstrip(".").upper(),
        "size": p.stat().st_size if p.exists() else 0,
        "bitrate": 0, "sample_rate": 0, "bit_depth": 0, "channels": 0, "duration": 0.0,
        "has_artwork": False,
    }
    try:
        from mutagen import File as MFile
        audio = MFile(filepath)
        if audio is None:
            return result
        if hasattr(audio, 'tags') and audio.tags:
            tags = audio.tags
            result["title"] = str(tags.get("title", [result["title"]])[0]) if "title" in tags else result["title"]
            result["artist"] = str(tags.get("artist", [""])[0]) if "artist" in tags else ""
            result["album"] = str(tags.get("album", [""])[0]) if "album" in tags else ""
            result["album_artist"] = str(tags.get("albumartist", [""])[0]) if "albumartist" in tags else ""
            result["genre"] = str(tags.get("genre", [""])[0]) if "genre" in tags else ""
            result["composer"] = str(tags.get("composer", [""])[0]) if "composer" in tags else ""
            result["comment"] = str(tags.get("comment", [""])[0]) if "comment" in tags else ""
            with contextlib.suppress(ValueError, TypeError):
                result["year"] = int(str(tags.get("year", [0])[0])) if "year" in tags else 0
            with contextlib.suppress(ValueError, TypeError):
                result["track_number"] = int(str(tags.get("tracknumber", [0])[0]).split("/")[0]) if "tracknumber" in tags else 0
            with contextlib.suppress(ValueError, IndexError, TypeError):
                result["track_total"] = int(str(tags.get("tracknumber", [""])[0]).split("/")[1]) if "tracknumber" in tags and "/" in str(tags["tracknumber"][0]) else 0
            result["has_artwork"] = "APIC:" in str(type(audio)) or hasattr(audio, 'pictures') and len(audio.pictures) > 0
        if hasattr(audio, 'info') and audio.info:
            info = audio.info
            if hasattr(info, 'bitrate') and info.bitrate:
                result["bitrate"] = info.bitrate
            if hasattr(info, 'sample_rate') and info.sample_rate:
                result["sample_rate"] = info.sample_rate
            if hasattr(info, 'channels') and info.channels:
                result["channels"] = info.channels
            if hasattr(info, 'bits_per_sample') and info.bits_per_sample:
                result["bit_depth"] = info.bits_per_sample
            if hasattr(info, 'length') and info.length:
                result["duration"] = info.length
    except Exception:
        logger.debug("Metadata read failed for %s", filepath, exc_info=True)
    return result


class MetadataBridge(QObject):
    dataChanged = Signal()
    selectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_filepath = ""
        self._has_selection = False
        self._is_loading = False
        self._error_message = ""
        self._track_title = ""
        self._track_artist = ""
        self._track_album = ""
        self._fields = []
        self._quality_summary = ""
        self._artwork_status = ""
        self._all_fields: dict = {}

    @Property(bool, notify=selectionChanged)
    def hasSelection(self): return self._has_selection

    @Property(bool, notify=dataChanged)
    def isLoading(self): return self._is_loading

    @Property(str, notify=dataChanged)
    def errorMessage(self): return self._error_message

    @Property(str, notify=dataChanged)
    def trackTitle(self): return self._track_title

    @Property(str, notify=dataChanged)
    def trackArtist(self): return self._track_artist

    @Property(str, notify=dataChanged)
    def trackAlbum(self): return self._track_album

    @Property("QVariantList", notify=dataChanged)
    def fields(self): return self._fields

    @Property(str, notify=dataChanged)
    def qualitySummary(self): return self._quality_summary

    @Property(str, notify=dataChanged)
    def artworkStatus(self): return self._artwork_status

    @Property(bool, notify=selectionChanged)
    def canApply(self): return self._has_selection and bool(self._current_filepath)

    @Slot(str, result=dict)
    def loadMetadata(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        p = Path(filepath)
        if not p.is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        self._current_filepath = filepath
        self._has_selection = True
        self._is_loading = True
        self._error_message = ""
        meta = _read_full_metadata(filepath)
        if "error" in meta:
            self._error_message = meta["error"]
            self._is_loading = False
            self.dataChanged.emit()
            return {"ok": False, "error": meta["error"]}
        self._all_fields = meta
        self._track_title = meta.get("title", _NA)
        self._track_artist = meta.get("artist", _NA)
        self._track_album = meta.get("album", _NA)
        self._fields = [
            {"key": "title", "label": "Título", "value": meta.get("title", ""), "type": "text"},
            {"key": "artist", "label": "Artista", "value": meta.get("artist", ""), "type": "text"},
            {"key": "album", "label": "Álbum", "value": meta.get("album", ""), "type": "text"},
            {"key": "album_artist", "label": "Artista del álbum", "value": meta.get("album_artist", ""), "type": "text"},
            {"key": "genre", "label": "Género", "value": meta.get("genre", ""), "type": "text"},
            {"key": "year", "label": "Año", "value": meta.get("year", 0), "type": "int"},
            {"key": "track_number", "label": "# Pista", "value": meta.get("track_number", 0), "type": "int"},
            {"key": "track_total", "label": "Total pistas", "value": meta.get("track_total", 0), "type": "int"},
            {"key": "disc_number", "label": "# Disco", "value": meta.get("disc_number", 0), "type": "int"},
            {"key": "disc_total", "label": "Total discos", "value": meta.get("disc_total", 0), "type": "int"},
            {"key": "composer", "label": "Compositor", "value": meta.get("composer", ""), "type": "text"},
            {"key": "comment", "label": "Comentario", "value": meta.get("comment", ""), "type": "text"},
            {"key": "bpm", "label": "BPM", "value": meta.get("bpm", 0), "type": "int"},
            {"key": "format", "label": "Formato", "value": meta.get("format", ""), "type": "info"},
            {"key": "bitrate", "label": "Bitrate", "value": meta.get("bitrate", 0), "type": "info"},
            {"key": "sample_rate", "label": "Frecuencia", "value": meta.get("sample_rate", 0), "type": "info"},
            {"key": "bit_depth", "label": "Profundidad", "value": meta.get("bit_depth", 0), "type": "info"},
            {"key": "channels", "label": "Canales", "value": meta.get("channels", 0), "type": "info"},
            {"key": "duration", "label": "Duración", "value": meta.get("duration", 0.0), "type": "info"},
        ]
        self._quality_summary = f"{meta.get('format', '?')} · {meta.get('bitrate', 0) // 1000}kbps · {meta.get('sample_rate', 0)}Hz"
        self._artwork_status = "Con carátula" if meta.get("has_artwork") else "Sin carátula"
        self._is_loading = False
        self.dataChanged.emit()
        return {"ok": True, "title": meta.get("title", "")}

    @Slot(str, str, result=dict)
    def setField(self, key: str, value: str):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE_SELECTED"}
        self._all_fields[key] = value
        self._fields = [{"key": f.get("key"), "label": f.get("label"), "value": self._all_fields.get(f.get("key"), f.get("value")), "type": f.get("type")} for f in self._fields]
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def saveChanges(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE_SELECTED"}
        try:
            from metadata.tag_writer import write_tags
            from metadata.tag_model import TrackTags
            tags = TrackTags(filepath=self._current_filepath)
            for k, v in self._all_fields.items():
                if hasattr(tags, k):
                    setattr(tags, k, v)
            tags.dirty = True
            ok = write_tags(tags)
            if ok:
                self._error_message = ""
                self._quality_summary = "Metadatos guardados"
                self.dataChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "WRITE_FAILED"}
        except Exception as e:
            logger.debug("saveChanges failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def hasArtwork(self):
        return {"ok": True, "has_artwork": self._all_fields.get("has_artwork", False)}

    @Slot(str, result=dict)
    def replaceArtwork(self, image_path: str):
        if not image_path or not Path(image_path).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE_SELECTED"}
        try:
            from metadata.tag_writer import write_tags
            from metadata.tag_model import TrackTags
            tags = TrackTags(filepath=self._current_filepath)
            tags.artwork_dirty = True
            with open(image_path, "rb") as f:
                tags.artwork_data = f.read()
            ok = write_tags(tags)
            if ok:
                self._artwork_status = "Carátula actualizada"
                self.dataChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "WRITE_FAILED"}
        except Exception as e:
            logger.debug("replaceArtwork failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def removeArtwork(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE_SELECTED"}
        try:
            from metadata.tag_writer import write_tags
            from metadata.tag_model import TrackTags
            tags = TrackTags(filepath=self._current_filepath)
            tags.artwork_dirty = True
            tags.artwork_data = b""
            ok = write_tags(tags)
            if ok:
                self._artwork_status = "Carátula eliminada"
                self.dataChanged.emit()
                return {"ok": True}
            return {"ok": False, "error": "WRITE_FAILED"}
        except Exception as e:
            logger.debug("removeArtwork failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot()
    def clear(self):
        self._current_filepath = ""
        self._has_selection = False
        self._is_loading = False
        self._error_message = ""
        self._track_title = ""
        self._track_artist = ""
        self._track_album = ""
        self._fields = []
        self._quality_summary = ""
        self._artwork_status = ""
        self._all_fields = {}
        self.dataChanged.emit()

    @Slot()
    def refresh(self):
        if self._current_filepath:
            self.loadMetadata(self._current_filepath)
        elif self._has_selection:
            self.dataChanged.emit()
