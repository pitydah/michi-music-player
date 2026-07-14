from __future__ import annotations

from typing import Callable

from core.lyrics.interfaces import SidecarProvider, EmbeddedLyricsWriter
from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsOperationResult,
    LyricsSource, LyricsErrorCode,
)


class LyricsStorageService:
    def __init__(
        self,
        sidecar_provider: SidecarProvider | None = None,
        embedded_writer: EmbeddedLyricsWriter | None = None,
        clock: Callable[[], str] | None = None,
    ):
        self._sidecar = sidecar_provider
        self._embedded = embedded_writer
        self._clock = clock or (lambda: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()))

    def save_sidecar(self, directory: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not self._sidecar:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="Sidecar provider not available",
            )
        doc.updated_at = self._clock()
        return self._sidecar.write(directory, doc)

    def delete_sidecar(self, directory: str, identity: TrackIdentity) -> bool:
        if not self._sidecar:
            return False
        return self._sidecar.delete(directory, identity)

    def save_embedded(self, filepath: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not self._embedded:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.WRITE_ERROR,
                message="Embedded writer not available",
            )
        doc.updated_at = self._clock()
        return self._embedded.write(filepath, doc)

    def save_manual(self, identity: TrackIdentity, plain_text: str,
                    synced_text: str = "") -> LyricsDocument:
        now = self._clock()
        doc = LyricsDocument(
            identity=identity,
            plain_text=plain_text,
            synced_text=synced_text,
            source=LyricsSource.MANUAL,
            fetched_at=now,
            updated_at=now,
        )
        if synced_text:
            from core.lyrics.parser import parse_lrc
            parsed = parse_lrc(synced_text)
            doc.lines = parsed.lines
            doc.metadata = parsed.metadata
            doc.offset_ms = parsed.offset_ms
        return doc

    def set_preferred_source(self, doc: LyricsDocument) -> LyricsDocument:
        if doc.has_synced:
            doc.source = LyricsSource.SIDECAR_LRC if doc.source in (LyricsSource.SIDECAR_LRC, LyricsSource.REMOTE_PROVIDER, LyricsSource.CACHE) else doc.source
        elif doc.has_plain:
            doc.source = LyricsSource.SIDECAR_TEXT
        return doc
