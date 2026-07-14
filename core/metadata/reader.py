from __future__ import annotations

import hashlib
import os

from core.metadata.models import (
    MetadataDocument, TrackMetadata, TechnicalMetadata,
    ArtworkMetadata, MetadataOperationResult,
)
from core.metadata.enums import MetadataErrorCode
from core.metadata.registry import MetadataFormatRegistry
import contextlib


class MetadataReader:
    def __init__(self, format_registry: MetadataFormatRegistry,
                 adapters: dict[str, object] | None = None):
        self._registry = format_registry
        self._adapters = adapters or {}

    def probe(self, path: str) -> MetadataOperationResult:
        if not path:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.INVALID_PATH.value,
                message="No path provided",
            )
        if not os.path.exists(path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.FILE_NOT_FOUND.value,
                message=f"File not found: {path}",
            )
        if not os.path.isfile(path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NOT_A_FILE.value,
                message=f"Not a regular file: {path}",
            )
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        cap = self._registry.get_by_extension(ext)
        if cap is None or not cap.readable:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.UNSUPPORTED_FORMAT.value,
                message=f"Unsupported format: .{ext}",
            )
        return MetadataOperationResult(ok=True, data={"format": cap.format_id, "extension": ext})

    def read(self, path: str, include_artwork_metadata: bool = True,
             include_artwork_bytes: bool = False,
             include_raw_fields: bool = False,
             max_artwork_bytes: int = 10485760,
             strict: bool = False) -> MetadataOperationResult:
        probe = self.probe(path)
        if not probe.ok:
            return probe

        ext = os.path.splitext(path)[1].lower().lstrip(".")
        adapter = self._adapters.get(ext)
        if adapter is None:
            return self._read_mutagen(path, ext, probe.data.get("format", ""),
                                      include_artwork_metadata, include_artwork_bytes,
                                      include_raw_fields, max_artwork_bytes, strict)

        return adapter.read(path)

    def _read_mutagen(self, path: str, ext: str, fmt: str,
                      include_artwork: bool, include_artwork_bytes: bool,
                      include_raw: bool, max_artwork: int,
                      strict: bool) -> MetadataOperationResult:
        try:
            import mutagen
            import os
            st = os.stat(path)
            mf = mutagen.File(path)
            if mf is None:
                return MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.UNSUPPORTED_FORMAT.value,
                    message="Mutagen could not open file",
                )

            doc = MetadataDocument(
                source_path=path,
                format=fmt,
                technical=TechnicalMetadata(
                    container=fmt,
                    codec=self._detect_codec(mf),
                    duration_ms=int(getattr(mf.info, "length", 0) * 1000),
                    bitrate=int(getattr(mf.info, "bitrate", 0)),
                    sample_rate=int(getattr(mf.info, "sample_rate", 0)),
                    channels=getattr(mf.info, "channels", 0),
                    filesize=st.st_size,
                    mtime_ns=st.st_mtime_ns,
                    lossless=fmt in ("flac", "wav", "aiff", "dsf", "ape"),
                ),
            )

            if mf.tags is not None:
                doc.track = self._extract_tags(mf, ext)
                if include_artwork:
                    artworks = self._extract_artwork(mf, ext, include_artwork_bytes, max_artwork)
                    doc.artworks = artworks
                if include_raw:
                    doc.raw_fields = dict(mf.tags)

            return MetadataOperationResult(ok=True, data={"document": doc})

        except Exception as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.READ_FAILED.value,
                message=str(e),
            )

    def _extract_tags(self, mf, ext: str) -> TrackMetadata:
        meta = TrackMetadata()
        if not hasattr(mf, "tags") or mf.tags is None:
            return meta
        tags = mf.tags

        if ext == "mp3":
            return self._read_id3(tags)
        elif ext in ("m4a", "mp4", "m4b"):
            return self._read_mp4(tags)
        elif ext in ("flac", "ogg", "oga", "opus"):
            return self._read_vorbis(tags)

        return self._read_vorbis(tags)

    def _read_id3(self, tags) -> TrackMetadata:
        meta = TrackMetadata()
        frame_map = {
            "TIT2": ("title", str),
            "TPE1": ("artists", lambda v: [str(v)]),
            "TPE2": ("album_artist", str),
            "TALB": ("album", str),
            "TDRC": ("date", str),
            "TCON": ("genres", lambda v: [str(v)]),
            "TCOM": ("composer", str),
            "TEXT": ("lyricist", str),
            "TPUB": ("publisher", str),
            "COMM": ("comment", str),
            "USLT": ("lyrics", lambda v: str(v.text) if hasattr(v, "text") else ""),
        }
        for frame_id, (field, converter) in frame_map.items():
            if frame_id in tags:
                with contextlib.suppress(Exception):
                    setattr(meta, field, converter(tags[frame_id]))

        txxx_frames = tags.getall("TXXX")
        txxx_map = {
            "MusicBrainz Track Id": "musicbrainz_recording_id",
            "MusicBrainz Album Id": "musicbrainz_release_id",
            "MusicBrainz Album Artist Id": "musicbrainz_album_artist_ids",
            "MusicBrainz Artist Id": "musicbrainz_artist_ids",
            "MusicBrainz Release Group Id": "musicbrainz_release_group_id",
            "ISRC": "isrc",
            "BARCODE": "barcode",
            "CATALOGNUMBER": "catalog_number",
            "ACOUSTID_ID": "acoustid_id",
            "TRACKTOTAL": ("track_total", int),
            "DISCTOTAL": ("disc_total", int),
            "BPM": ("bpm", float),
        }
        for txxx in txxx_frames:
            desc = txxx.desc
            if desc in txxx_map:
                target = txxx_map[desc]
                if isinstance(target, tuple):
                    field_name, converter = target
                    with contextlib.suppress(Exception):
                        setattr(meta, field_name, converter(txxx.text[0]))
                elif isinstance(target, str):
                    if target in ("musicbrainz_artist_ids", "musicbrainz_album_artist_ids"):
                        val = txxx.text[0] if isinstance(txxx.text, list) else txxx.text
                        existing = getattr(meta, target, [])
                        if val not in existing:
                            existing.append(val)
                            setattr(meta, target, existing)
                    else:
                        setattr(meta, target, txxx.text[0] if isinstance(txxx.text, list) else txxx.text)

        trck = tags.get("TRCK")
        if trck:
            parts = str(trck).split("/")
            with contextlib.suppress(Exception):
                meta.track_number = int(parts[0])
            if len(parts) > 1:
                with contextlib.suppress(Exception):
                    meta.track_total = int(parts[1])

        return meta

    def _read_mp4(self, tags) -> TrackMetadata:
        meta = TrackMetadata()
        atom_map = {
            "\xa9nam": ("title", str),
            "\xa9ART": ("artists", lambda v: [str(v[0])] if isinstance(v, list) else [str(v)]),
            "aART": ("album_artist", lambda v: str(v[0]) if isinstance(v, list) else str(v)),
            "\xa9alb": ("album", str),
            "\xa9day": ("date", str),
            "\xa9gen": ("genres", lambda v: [str(v[0])] if isinstance(v, list) else [str(v)]),
            "\xa9wrt": ("composer", str),
            "\xa9lyr": ("lyrics", lambda v: str(v[0]) if isinstance(v, list) else str(v)),
            "cprt": ("copyright_", str),
            "soal": ("album", str),
        }
        for atom, (field, converter) in atom_map.items():
            if atom in tags:
                try:
                    val = tags[atom]
                    if isinstance(val, list):
                        val = val[0]
                    if isinstance(val, bytes):
                        val = val.decode("utf-8", errors="replace")
                    setattr(meta, field, converter(val))
                except Exception:
                    pass

        if "\xa9too" in tags:
            meta.comment = tags["\xa9too"][0] if isinstance(tags["\xa9too"], list) else str(tags["\xa9too"])

        trkn = tags.get("trkn")
        if trkn and isinstance(trkn, list) and len(trkn) > 0:
            parts = trkn[0]
            if isinstance(parts, bytes):
                parts = (int(parts[0]), int(parts[1]))
            if isinstance(parts, tuple) and len(parts) >= 1:
                meta.track_number = parts[0] if parts[0] else None
                if len(parts) >= 2:
                    meta.track_total = parts[1] if parts[1] else None

        disk = tags.get("disk")
        if disk and isinstance(disk, list) and len(disk) > 0:
            parts = disk[0]
            if isinstance(parts, tuple) and len(parts) >= 1:
                meta.disc_number = parts[0] if parts[0] else None
                if len(parts) >= 2:
                    meta.disc_total = parts[1] if parts[1] else None

        mb_map = {
            "----:com.apple.iTunes:MusicBrainz Track Id": "musicbrainz_recording_id",
            "----:com.apple.iTunes:MusicBrainz Album Id": "musicbrainz_release_id",
            "----:com.apple.iTunes:MusicBrainz Artist Id": "musicbrainz_artist_ids",
            "----:com.apple.iTunes:MusicBrainz Album Artist Id": "musicbrainz_album_artist_ids",
            "----:com.apple.iTunes:MusicBrainz Release Group Id": "musicbrainz_release_group_id",
            "----:com.apple.iTunes:ISRC": "isrc",
            "----:com.apple.iTunes:BARCODE": "barcode",
            "----:com.apple.iTunes:ACOUSTID_ID": "acoustid_id",
        }
        for atom, field in mb_map.items():
            if atom in tags:
                try:
                    val = tags[atom]
                    if isinstance(val, list) and len(val) > 0:
                        raw = val[0]
                        if isinstance(raw, bytes):
                            raw = raw.decode("utf-8", errors="replace").strip("\x00")
                        if field in ("musicbrainz_artist_ids", "musicbrainz_album_artist_ids"):
                            existing = getattr(meta, field, [])
                            if raw not in existing:
                                existing.append(raw)
                                setattr(meta, field, existing)
                        else:
                            setattr(meta, field, raw)
                except Exception:
                    pass

        return meta

    def _read_vorbis(self, tags) -> TrackMetadata:
        meta = TrackMetadata()
        vorbis_map = {
            "title": "title",
            "artist": ("artists", lambda v: v if isinstance(v, list) else [v]),
            "album": "album",
            "albumartist": "album_artist",
            "album artist": "album_artist",
            "tracknumber": ("track_number", lambda v: int(v.split("/")[0]) if "/" in v else int(v)),
            "tracktotal": ("track_total", int),
            "totaltracks": ("track_total", int),
            "discnumber": ("disc_number", lambda v: int(v.split("/")[0]) if "/" in v else int(v)),
            "disctotal": ("disc_total", int),
            "totaldiscs": ("disc_total", int),
            "date": "date",
            "originaldate": "original_date",
            "genre": ("genres", lambda v: v if isinstance(v, list) else [v]),
            "composer": "composer",
            "conductor": "conductor",
            "lyricist": "lyricist",
            "comment": "comment",
            "description": "comment",
            "copyright": "copyright_",
            "label": "label",
            "publisher": "publisher",
            "isrc": "isrc",
            "barcode": "barcode",
            "catalognumber": "catalog_number",
            "bpm": ("bpm", float),
            "language": "language",
            "compilation": ("compilation", lambda v: str(v).lower() in ("1", "true", "yes")),
            "lyrics": "lyrics",
            "unsyncedlyrics": "lyrics",
            "musicbrainz_trackid": "musicbrainz_recording_id",
            "musicbrainz_releasetrackid": "musicbrainz_recording_id",
            "musicbrainz_albumid": "musicbrainz_release_id",
            "musicbrainz_releasegroupid": "musicbrainz_release_group_id",
            "musicbrainz_artistid": ("musicbrainz_artist_ids", lambda v: [v] if isinstance(v, str) else v),
            "musicbrainz_albumartistid": ("musicbrainz_album_artist_ids", lambda v: [v] if isinstance(v, str) else v),
            "acoustid_id": "acoustid_id",
            "acoustid_fingerprint": "acoustid_id",
            "replaygain_track_gain": ("replaygain_track_gain", float),
            "replaygain_track_peak": ("replaygain_track_peak", float),
            "replaygain_album_gain": ("replaygain_album_gain", float),
            "replaygain_album_peak": ("replaygain_album_peak", float),
            "r128_track_gain": ("r128_track_gain", float),
            "r128_album_gain": ("r128_album_gain", float),
        }
        for tag_key, target in vorbis_map.items():
            if tag_key in tags:
                try:
                    val = tags[tag_key]
                    if isinstance(val, list):
                        val = val[0] if len(val) == 1 else val
                    if isinstance(target, tuple):
                        field_name, converter = target
                        setattr(meta, field_name, converter(val))
                    else:
                        setattr(meta, target, val)
                except Exception:
                    pass

        return meta

    def _extract_artwork(self, mf, ext: str, include_bytes: bool,
                         max_bytes: int) -> list[ArtworkMetadata]:
        artworks: list[ArtworkMetadata] = []
        try:
            if ext == "mp3":
                if hasattr(mf, "tags") and mf.tags is not None:
                    for apic in mf.tags.getall("APIC"):
                        aw = self._make_artwork(apic, include_bytes, max_bytes)
                        if aw:
                            artworks.append(aw)

            elif ext in ("flac", "ogg", "oga", "opus"):
                if hasattr(mf, "pictures"):
                    for pic in mf.pictures:
                        aw = self._make_artwork(pic, include_bytes, max_bytes)
                        if aw:
                            artworks.append(aw)

            elif ext in ("m4a", "mp4", "m4b") and "covr" in mf.tags:
                covr = mf.tags["covr"]
                for item in covr:
                    image_data = item if isinstance(item, bytes) else bytes(item)
                    if len(image_data) > max_bytes:
                        continue
                    aw = ArtworkMetadata(
                        artwork_id=f"covr_{len(artworks)}",
                        picture_type="front_cover",
                        mime_type=self._detect_image_type(image_data),
                        size_bytes=len(image_data),
                        content_hash=hashlib.sha256(image_data).hexdigest()[:16],
                        data_reference="embedded" if not include_bytes else "",
                    )
                    artworks.append(aw)
        except Exception:
            pass
        return artworks

    @staticmethod
    def _make_artwork(frame, include_bytes: bool,
                      max_bytes: int) -> ArtworkMetadata | None:
        data = getattr(frame, "data", None) or getattr(frame, "image_data", None)
        if data is None:
            return None
        if len(data) > max_bytes:
            return None
        import hashlib
        return ArtworkMetadata(
            artwork_id="",
            picture_type=str(getattr(frame, "type", "front_cover")),
            mime_type=getattr(frame, "mime", "image/jpeg"),
            width=getattr(frame, "width", 0),
            height=getattr(frame, "height", 0),
            depth=getattr(frame, "depth", 8),
            size_bytes=len(data),
            content_hash=hashlib.sha256(data).hexdigest()[:16],
            data_reference="embedded",
        )

    @staticmethod
    def _detect_codec(mf) -> str:
        import mutagen
        if isinstance(mf, mutagen.mp3.MP3):
            return "MP3"
        if isinstance(mf, mutagen.flac.FLAC):
            return "FLAC"
        if isinstance(mf, mutagen.oggvorbis.OggVorbis):
            return "Vorbis"
        if isinstance(mf, mutagen.oggopus.OggOpus):
            return "Opus"
        if isinstance(mf, mutagen.mp4.MP4):
            return "AAC"
        if isinstance(mf, mutagen.wave.WAVE):
            return "PCM"
        if isinstance(mf, mutagen.aiff.AIFF):
            return "PCM"
        if isinstance(mf, mutagen.apev2.APEv2):
            return "APE"
        if isinstance(mf, mutagen.asf.ASF):
            return "WMA"
        if isinstance(mf, mutagen.dsf.DSF):
            return "DSD"
        return ""

    @staticmethod
    def _detect_image_type(data: bytes) -> str:
        if len(data) < 4:
            return "application/octet-stream"
        if data[:4] == b"\x89PNG":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF":
            return "image/webp"
        return "application/octet-stream"
