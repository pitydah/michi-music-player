from __future__ import annotations

import os
import shutil

from core.metadata.models import (
    MetadataDocument, MetadataFieldChange,
    MetadataOperationResult, compute_file_signature,
)
from core.metadata.enums import (
    MetadataErrorCode, BackupPolicy, FieldOperation,
)
from core.metadata.registry import MetadataFormatRegistry
import contextlib


class MetadataWriter:
    def __init__(self, format_registry: MetadataFormatRegistry,
                 backup_policy: BackupPolicy = BackupPolicy.FULL_FILE_BACKUP):
        self._registry = format_registry
        self._policy = backup_policy

    def write(self, path: str, doc: MetadataDocument,
              changes: list[MetadataFieldChange] | None = None,
              backup_policy: BackupPolicy | None = None,
              verify_after_write: bool = True,
              preserve_mtime: bool = False) -> MetadataOperationResult:
        policy = backup_policy or self._policy
        if not os.path.exists(path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.FILE_NOT_FOUND.value,
            )
        if not os.path.isfile(path):
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.NOT_A_FILE.value,
            )

        ext = os.path.splitext(path)[1].lower().lstrip(".")
        cap = self._registry.get_by_extension(ext)
        if cap is None or not cap.writable:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.UNSUPPORTED_OPERATION.value,
                message=f"Format .{ext} is not writable",
            )

        before_sig = compute_file_signature(path)
        backup_path = ""
        if policy == BackupPolicy.FULL_FILE_BACKUP:
            backup_result = self._create_backup(path)
            if not backup_result.ok:
                return backup_result
            backup_path = backup_result.data.get("backup_path", "")

        self._apply_changes(doc, changes)

        try:
            mf = self._open_file(path)
            if mf is None:
                return MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.READ_FAILED.value,
                    message="Could not open file for writing",
                )
            self._apply_to_mutagen(mf, ext, doc, changes)
            mf.save()

            if verify_after_write:
                from core.metadata.reader import MetadataReader
                reader = MetadataReader(self._registry)
                verify = reader.read(path, include_artwork_metadata=True, include_artwork_bytes=False)
                if not verify.ok:
                    return MetadataOperationResult(
                        ok=False, code=MetadataErrorCode.VERIFY_FAILED.value,
                        message=f"Verify failed: {verify.message}",
                        retryable=True,
                    )

            after_sig = compute_file_signature(path)
            return MetadataOperationResult(
                ok=True,
                data={
                    "before_signature": before_sig,
                    "after_signature": after_sig,
                    "backup_path": backup_path,
                },
            )
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.WRITE_FAILED.value,
                message=str(e),
                retryable=True,
            )

    def _create_backup(self, path: str) -> MetadataOperationResult:
        try:
            backup_dir = os.path.join(os.path.dirname(path), ".michi_backups")
            os.makedirs(backup_dir, exist_ok=True)
            base = os.path.basename(path)
            backup_path = os.path.join(backup_dir, f"{base}.bak")
            shutil.copy2(path, backup_path)
            return MetadataOperationResult(
                ok=True, data={"backup_path": backup_path},
            )
        except (OSError, IOError) as e:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.BACKUP_FAILED.value,
                message=str(e),
            )

    def _open_file(self, path: str):
        try:
            import mutagen
            return mutagen.File(path)
        except Exception:
            return None

    def _apply_changes(self, doc: MetadataDocument,
                       changes: list[MetadataFieldChange] | None):
        if not changes:
            return
        for change in changes:
            if not change.selected:
                continue
            if change.operation == FieldOperation.SET:
                if hasattr(doc.track, change.field):
                    setattr(doc.track, change.field, change.new_value)
            elif change.operation == FieldOperation.CLEAR:
                if hasattr(doc.track, change.field):
                    if isinstance(getattr(doc.track, change.field), list):
                        setattr(doc.track, change.field, [])
                    else:
                        setattr(doc.track, change.field, "" if isinstance(getattr(doc.track, change.field), str) else None)
            elif change.operation == FieldOperation.APPEND:
                current = getattr(doc.track, change.field, [])
                if isinstance(current, list) and change.new_value not in current:
                    current.append(change.new_value)
            elif change.operation == FieldOperation.REMOVE:
                current = getattr(doc.track, change.field, [])
                if isinstance(current, list) and change.new_value in current:
                    current.remove(change.new_value)

    def _apply_to_mutagen(self, mf, ext: str, doc: MetadataDocument,
                          changes: list[MetadataFieldChange] | None):
        if changes:
            tracker = _ChangedTracker()
            for c in changes:
                if c.selected:
                    tracker.mark(c.field)
            self._write_fields(mf, ext, doc.track, tracker.marked_fields if tracker.marked_fields else None)
        else:
            self._write_fields(mf, ext, doc.track)

    def _write_fields(self, mf, ext: str, track, explicit_fields: set[str] | None = None):
        if not hasattr(mf, "tags") or mf.tags is None:
            try:
                mf.add_tags()
            except Exception:
                return
        tags = mf.tags

        if ext == "mp3":
            self._write_id3(tags, track, explicit_fields)
        elif ext in ("m4a", "mp4", "m4b"):
            self._write_mp4(tags, track, explicit_fields)
        elif ext in ("flac", "ogg", "oga", "opus"):
            self._write_vorbis(tags, track, explicit_fields)

    def _write_id3(self, tags, track, explicit_fields=None):
        from mutagen.id3 import TIT2, TPE1, TPE2, TALB, TDRC, TCOM, TXXX, USLT, TRCK, TPUB, TEXT
        _FRAME_MAP = {
            "title": ("TIT2", lambda v: TIT2(encoding=3, text=v)),
            "artists": ("TPE1", lambda v: TPE1(encoding=3, text=v[0] if v else "")),
            "album_artist": ("TPE2", lambda v: TPE2(encoding=3, text=v)),
            "album": ("TALB", lambda v: TALB(encoding=3, text=v)),
            "date": ("TDRC", lambda v: TDRC(encoding=3, text=v)),
            "composer": ("TCOM", lambda v: TCOM(encoding=3, text=v)),
            "publisher": ("TPUB", lambda v: TPUB(encoding=3, text=v)),
            "lyricist": ("TEXT", lambda v: TEXT(encoding=3, text=v)),
        }
        _TXXX_MAP = {
            "musicbrainz_recording_id": "MusicBrainz Track Id",
            "musicbrainz_release_id": "MusicBrainz Album Id",
            "musicbrainz_release_group_id": "MusicBrainz Release Group Id",
            "acoustid_id": "ACOUSTID_ID",
            "isrc": "ISRC",
            "barcode": "BARCODE",
            "catalog_number": "CATALOGNUMBER",
        }
        for field_name, (_frame_id, builder) in _FRAME_MAP.items():
            if explicit_fields and field_name not in explicit_fields:
                continue
            val = getattr(track, field_name, None)
            if val:
                with contextlib.suppress(Exception):
                    tags.add(builder(val))

        for field_name, txxx_desc in _TXXX_MAP.items():
            if explicit_fields and field_name not in explicit_fields:
                continue
            val = getattr(track, field_name, None)
            if val:
                if isinstance(val, list):
                    val = val[0] if val else ""
                with contextlib.suppress(Exception):
                    tags.add(TXXX(encoding=3, desc=txxx_desc, text=str(val)))

        if (not explicit_fields or "track_number" in explicit_fields or "track_total" in explicit_fields) and (track.track_number is not None or track.track_total is not None):
            tn = track.track_number or ""
            tt = track.track_total or ""
            trck_str = f"{tn}/{tt}" if tt else str(tn)
            tags.add(TRCK(encoding=3, text=trck_str))

        if (not explicit_fields or "lyrics" in explicit_fields) and track.lyrics:
            with contextlib.suppress(Exception):
                tags.add(USLT(encoding=3, text=track.lyrics))

    def _write_mp4(self, tags, track, explicit_fields=None):
        _ATOM_MAP = {
            "title": "\xa9nam",
            "album": "\xa9alb",
            "date": "\xa9day",
            "composer": "\xa9wrt",
            "copyright_": "cprt",
        }
        for field_name, atom in _ATOM_MAP.items():
            if explicit_fields and field_name not in explicit_fields:
                continue
            val = getattr(track, field_name, None)
            if val:
                tags[atom] = [str(val)]

        if (not explicit_fields or "artists" in explicit_fields) and track.artists:
            tags["\xa9ART"] = [str(track.artists[0])]
        if (not explicit_fields or "album_artist" in explicit_fields) and track.album_artist:
            tags["aART"] = [track.album_artist]

        if (not explicit_fields or "lyrics" in explicit_fields) and track.lyrics:
            tags["\xa9lyr"] = [track.lyrics]

        if (not explicit_fields or "track_number" in explicit_fields) and track.track_number is not None:
            tags["trkn"] = [(track.track_number, track.track_total or 0)]
        if (not explicit_fields or "disc_number" in explicit_fields) and track.disc_number is not None:
            tags["disk"] = [(track.disc_number, track.disc_total or 0)]

        _MB_ATOM_MAP = {
            "musicbrainz_recording_id": "----:com.apple.iTunes:MusicBrainz Track Id",
            "musicbrainz_release_id": "----:com.apple.iTunes:MusicBrainz Album Id",
            "acoustid_id": "----:com.apple.iTunes:ACOUSTID_ID",
            "isrc": "----:com.apple.iTunes:ISRC",
        }
        for field_name, atom in _MB_ATOM_MAP.items():
            if explicit_fields and field_name not in explicit_fields:
                continue
            val = getattr(track, field_name, None)
            if val:
                if isinstance(val, list):
                    val = val[0] if val else ""
                with contextlib.suppress(Exception):
                    tags[atom] = bytes(str(val).encode("utf-8"))

    def _write_vorbis(self, tags, track, explicit_fields=None):
        _VORBIS_MAP = {
            "title": "title",
            "album": "album",
            "album_artist": "albumartist",
            "date": "date",
            "original_date": "originaldate",
            "composer": "composer",
            "conductor": "conductor",
            "lyricist": "lyricist",
            "comment": "comment",
            "copyright_": "copyright",
            "publisher": "publisher",
            "label": "label",
            "language": "language",
            "isrc": "isrc",
            "barcode": "barcode",
            "catalog_number": "catalognumber",
            "lyrics": "lyrics",
            "musicbrainz_recording_id": "musicbrainz_trackid",
            "musicbrainz_release_id": "musicbrainz_albumid",
            "musicbrainz_release_group_id": "musicbrainz_releasegroupid",
            "acoustid_id": "acoustid_id",
        }
        for field_name, tag_key in _VORBIS_MAP.items():
            if explicit_fields and field_name not in explicit_fields:
                continue
            val = getattr(track, field_name, None)
            if val:
                if isinstance(val, list):
                    tags[tag_key] = [str(v) for v in val]
                else:
                    tags[tag_key] = [str(val)]

        if (not explicit_fields or "artists" in explicit_fields) and track.artists:
            tags["artist"] = [str(a) for a in track.artists]

        if not explicit_fields or "track_number" in explicit_fields or "track_total" in explicit_fields:
            if track.track_number is not None:
                tn = track.track_number
                if track.track_total is not None:
                    tags["tracknumber"] = [f"{tn}/{track.track_total}"]
                else:
                    tags["tracknumber"] = [str(tn)]
            if track.track_total is not None:
                tags["tracktotal"] = [str(track.track_total)]

        if not explicit_fields or "disc_number" in explicit_fields or "disc_total" in explicit_fields:
            if track.disc_number is not None:
                dn = track.disc_number
                if track.disc_total is not None:
                    tags["discnumber"] = [f"{dn}/{track.disc_total}"]
                else:
                    tags["discnumber"] = [str(dn)]
            if track.disc_total is not None:
                tags["disctotal"] = [str(track.disc_total)]

        if (not explicit_fields or "bpm" in explicit_fields) and track.bpm is not None:
            tags["bpm"] = [str(track.bpm)]
        if (not explicit_fields or "genres" in explicit_fields) and track.genres:
            tags["genre"] = track.genres


class _ChangedTracker:
    def __init__(self):
        self.marked_fields: set[str] = set()

    def mark(self, field: str):
        self.marked_fields.add(field)
