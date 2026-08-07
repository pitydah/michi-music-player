"""Embedded lyrics writer backed by mutagen.

Writes lyrics into audio file tags (USLT for MP3, LYRICS for Vorbis,
\"\\xa9lyr\" for MP4). Ported from the legacy ``core/lyrics/lyrics_storage_service``
so the canonical storage service can offer the same behaviour through the
``EmbeddedLyricsWriter`` protocol (ADR-002 single domain authority).
"""
from __future__ import annotations

import os

from core.lyrics.interfaces import EmbeddedLyricsWriter
from core.lyrics.models import (
    LyricsDocument, LyricsOperationResult, LyricsErrorCode,
)


class MutagenEmbeddedLyricsWriter(EmbeddedLyricsWriter):
    def write(self, filepath: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not filepath or not os.path.isfile(filepath):
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="Audio file not found",
            )
        text = doc.synced_text if doc.synced_text else doc.plain_text
        if not text:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="No lyrics text to embed",
            )
        try:
            import mutagen
        except ImportError:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="mutagen not available",
            )
        try:
            audio = mutagen.File(filepath)
            if audio is None:
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.WRITE_ERROR,
                    message="Unsupported audio container",
                )
        except Exception as exc:  # pragma: no cover - container parsing errors
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message=str(exc),
            )

        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == ".mp3":
                self._write_mp3(audio, text)
            elif ext in (".flac", ".ogg", ".opus"):
                self._write_vorbis(audio, text)
            elif ext in (".mp4", ".m4a", ".m4b"):
                self._write_mp4(audio, text)
            else:
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.WRITE_ERROR,
                    message=f"Unsupported container: {ext}",
                )
            audio.save()
        except Exception as exc:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message=str(exc),
            )
        return LyricsOperationResult(ok=True, document=doc)

    @staticmethod
    def _write_mp3(audio, text: str):
        from mutagen.id3 import USLT
        if audio.tags is None:
            audio.add_tags()
        audio.tags.delall("USLT")
        audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=text))

    @staticmethod
    def _write_vorbis(audio, text: str):
        if not hasattr(audio, "tags") or audio.tags is None:
            return
        audio.tags["LYRICS"] = text

    @staticmethod
    def _write_mp4(audio, text: str):
        if not hasattr(audio, "tags") or audio.tags is None:
            return
        audio.tags["\xa9lyr"] = [text]
