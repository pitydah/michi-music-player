from __future__ import annotations

import logging
from typing import Callable

from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsOperationResult,
    LyricsSettings, LyricsErrorCode,
)
from core.lyrics.resolver import LyricsResolver
from core.lyrics.registry import LyricsProviderRegistry
from core.lyrics.interfaces import LyricsCacheRepository
from core.lyrics.storage import LyricsStorageService
from core.lyrics.editor import LyricsEditorService
from core.lyrics.timeline import LyricsTimeline
from core.lyrics.trace import LyricsTraceRecorder
from core.lyrics.attribution import LyricsAttributionPolicy
from core.lyrics.events import LyricEventBus
from core.lyrics.cancellation import LyricsCancellationToken

logger = logging.getLogger("michi.lyrics.service")


class LyricsService:
    def __init__(
        self,
        resolver: LyricsResolver,
        provider_registry: LyricsProviderRegistry,
        cache_repo: LyricsCacheRepository | None = None,
        storage_service: LyricsStorageService | None = None,
        editor_service: LyricsEditorService | None = None,
        timeline: LyricsTimeline | None = None,
        event_bus: LyricEventBus | None = None,
        trace: LyricsTraceRecorder | None = None,
        attribution: LyricsAttributionPolicy | None = None,
        clock: Callable[[], str] | None = None,
        network_status=None,
        settings: LyricsSettings | None = None,
    ):
        self._resolver = resolver
        self._registry = provider_registry
        self._cache = cache_repo
        self._storage = storage_service
        self._editor = editor_service
        self._timeline = timeline or LyricsTimeline()
        self._bus = event_bus or LyricEventBus()
        self._trace = trace or LyricsTraceRecorder()
        self._attribution = attribution or LyricsAttributionPolicy()
        self._clock = clock or (lambda: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()))
        self._network = network_status
        self._settings = settings or LyricsSettings()
        self._current_document: LyricsDocument | None = None

    def resolve(self, identity: TrackIdentity,
                token: LyricsCancellationToken | None = None) -> LyricsOperationResult:
        result = self._resolver.resolve(identity, cancellation_token=token)
        if result.ok and result.document:
            self._current_document = result.document
            self._timeline.load(result.document)
        return result

    def resolve_offline(self, identity: TrackIdentity) -> LyricsOperationResult:
        return self._resolver.resolve_offline(identity)

    def search_candidates(self, identity: TrackIdentity,
                          token: LyricsCancellationToken | None = None) -> LyricsOperationResult:
        return self._resolver.search_candidates(identity, token)

    def select_candidate(self, identity: TrackIdentity,
                         candidate: LyricsDocument) -> LyricsOperationResult:
        result = self._resolver.select_candidate(identity, candidate)
        if result.ok and result.document:
            self._current_document = result.document
            self._timeline.load(result.document)
        return result

    def refresh(self, identity: TrackIdentity,
                token: LyricsCancellationToken | None = None) -> LyricsOperationResult:
        cache_key = self._make_cache_key("", identity)
        if self._cache:
            self._cache.invalidate(cache_key)
        return self.resolve(identity, token)

    def cancel(self):
        self._resolver.cancel()

    def get_cached(self, cache_key: str) -> LyricsDocument | None:
        if self._cache:
            return self._cache.get(cache_key)
        return None

    def invalidate(self, cache_key: str):
        if self._cache:
            self._cache.invalidate(cache_key)

    def load_sidecar(self, directory: str, identity: TrackIdentity) -> LyricsOperationResult:
        if not self._storage:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.WRITE_ERROR)
        return self._storage.save_sidecar(directory, LyricsDocument(identity=identity))

    def save_sidecar(self, directory: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not self._storage:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.WRITE_ERROR)
        return self._storage.save_sidecar(directory, doc)

    def save_embedded(self, filepath: str, doc: LyricsDocument) -> LyricsOperationResult:
        if not self._storage:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.WRITE_ERROR)
        return self._storage.save_embedded(filepath, doc)

    def begin_edit(self, doc: LyricsDocument | None = None):
        self._editor.load(doc or self._current_document or LyricsDocument())

    def apply_edit(self) -> LyricsOperationResult:
        if self._editor.current:
            self._current_document = self._editor.current
            self._timeline.load(self._editor.current)
        return LyricsOperationResult(ok=True, document=self._editor.current)

    def undo(self) -> LyricsOperationResult:
        result = self._editor.undo()
        if result.ok and result.document:
            self._current_document = result.document
            self._timeline.load(result.document)
        return result

    def redo(self) -> LyricsOperationResult:
        result = self._editor.redo()
        if result.ok and result.document:
            self._current_document = result.document
            self._timeline.load(result.document)
        return result

    def commit_edit(self) -> LyricsOperationResult:
        if self._editor.current:
            self._current_document = self._editor.current
            self._timeline.load(self._editor.current)
        return LyricsOperationResult(ok=True, document=self._editor.current)

    def discard_edit(self):
        self._editor.load(self._current_document or LyricsDocument())

    def get_active_line(self, position_ms: float):
        return self._timeline.active_line(position_ms)

    def health(self) -> dict:
        return {
            "providers": len(self._registry._providers) if hasattr(self._registry, "_providers") else 0,
            "has_cache": self._cache is not None,
            "has_storage": self._storage is not None,
            "current_document": self._current_document is not None,
            "settings": {
                "remote_enabled": self._settings.remote_enabled,
                "offline_mode": self._settings.offline_mode,
            },
        }

    def shutdown(self):
        self._registry.close_all()
        if self._cache:
            self._cache.close()

    @property
    def event_bus(self) -> LyricEventBus:
        return self._bus

    @property
    def editor(self) -> LyricsEditorService:
        return self._editor

    @property
    def timeline(self) -> LyricsTimeline:
        return self._timeline

    @property
    def attribution(self) -> LyricsAttributionPolicy:
        return self._attribution

    @staticmethod
    def _make_cache_key(provider_id: str, identity: TrackIdentity) -> str:
        return f"{provider_id}:{identity.title.lower().strip()}|{identity.artist.lower().strip()}"
