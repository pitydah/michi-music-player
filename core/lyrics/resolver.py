from __future__ import annotations

import logging

from core.lyrics.interfaces import (
    LyricsCacheRepository, EmbeddedLyricsReader,
    SidecarProvider, NetworkStatus,
)
from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsOperationResult,
    LyricsSource, LyricsErrorCode, MatchConfidence,
    LyricsSettings,
)
from core.lyrics.registry import LyricsProviderRegistry
from core.lyrics.matcher import compute_match_score, rank_candidates
from core.lyrics.cancellation import LyricsCancellationToken, LyricsRequestTracker
from core.lyrics.events import LyricEventBus
from core.lyrics.trace import LyricsTraceRecorder

logger = logging.getLogger("michi.lyrics.resolver")

_DEFAULT_ORDER = [
    LyricsSource.MANUAL,
    LyricsSource.EMBEDDED,
    LyricsSource.SIDECAR_LRC,
    LyricsSource.SIDECAR_TEXT,
    LyricsSource.CACHE,
    LyricsSource.REMOTE_PROVIDER,
]


class LyricsResolver:
    def __init__(
        self,
        provider_registry: LyricsProviderRegistry,
        cache_repo: LyricsCacheRepository | None = None,
        embedded_reader: EmbeddedLyricsReader | None = None,
        sidecar_provider: SidecarProvider | None = None,
        event_bus: LyricEventBus | None = None,
        trace: LyricsTraceRecorder | None = None,
        network_status: NetworkStatus | None = None,
        settings: LyricsSettings | None = None,
    ):
        self._registry = provider_registry
        self._cache = cache_repo
        self._embedded = embedded_reader
        self._sidecar = sidecar_provider
        self._bus = event_bus or LyricEventBus()
        self._trace = trace
        self._network = network_status
        self._settings = settings or LyricsSettings()
        self._tracker = LyricsRequestTracker()

    def resolve(
        self,
        identity: TrackIdentity,
        settings_override: LyricsSettings | None = None,
        cancellation_token: LyricsCancellationToken | None = None,
    ) -> LyricsOperationResult:
        settings = settings_override or self._settings
        request_id = self._next_request_id(identity)
        track_hash = _hash_identity(identity)

        self._bus.emit("lyrics_resolution_started", request_id=request_id, track_hash=track_hash)
        if self._trace:
            self._trace.begin(request_id, identity)

        if cancellation_token and cancellation_token.cancelled:
            return self._cancelled(request_id, track_hash)

        source_order = self._resolve_order(settings)

        for source in source_order:
            if cancellation_token and cancellation_token.cancelled:
                return self._cancelled(request_id, track_hash)

            if source == LyricsSource.MANUAL:
                result = self._check_manual(identity)
            elif source == LyricsSource.EMBEDDED:
                result = self._check_embedded(identity)
            elif source == LyricsSource.SIDECAR_LRC:
                result = self._check_sidecar(identity, ".lrc")
            elif source == LyricsSource.SIDECAR_TEXT:
                result = self._check_sidecar(identity, ".txt")
            elif source == LyricsSource.CACHE:
                result = self._check_cache(identity)
            elif source == LyricsSource.REMOTE_PROVIDER:
                result = self._check_remote(identity, settings, cancellation_token)
            else:
                continue

            self._bus.emit("lyrics_source_checked", request_id=request_id,
                           track_hash=track_hash, source=source.value,
                           status=result.code.value if result else "error")
            if self._trace and result:
                self._trace.record_source(source.value, result.code.value)

            if result and result.ok and result.document:
                result.document.match_confidence = compute_match_score(identity, result.document)
                self._bus.emit("lyrics_resolved", request_id=request_id,
                               track_hash=track_hash, source=source.value,
                               status="found")
                if self._trace:
                    self._trace.end("found")
                return result

            if result and result.code == LyricsErrorCode.CANCELLED:
                return result

        self._bus.emit("lyrics_not_found", request_id=request_id, track_hash=track_hash)
        if self._trace:
            self._trace.end("not_found")
        return LyricsOperationResult(
            ok=False, code=LyricsErrorCode.NOT_FOUND,
            message="No lyrics found from any source",
        )

    def resolve_offline(self, identity: TrackIdentity) -> LyricsOperationResult:
        return self.resolve(
            identity,
            settings_override=LyricsSettings(
                remote_enabled=False, offline_mode=True,
            ),
        )

    def search_candidates(
        self,
        identity: TrackIdentity,
        cancellation_token: LyricsCancellationToken | None = None,
    ) -> LyricsOperationResult:
        if self._network and not self._network.is_online:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.OFFLINE,
                message="No network available",
            )
        all_candidates: list[LyricsDocument] = []
        for provider in self._registry.list_enabled():
            if cancellation_token and cancellation_token.cancelled:
                return self._cancelled("", _hash_identity(identity))
            result = provider.search(identity)
            if result.ok and result.candidates:
                all_candidates.extend(result.candidates)

        if not all_candidates:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.NOT_FOUND,
                message="No candidates found",
            )

        ranked = rank_candidates(identity, all_candidates)
        docs = [doc for doc, _ in ranked]
        best_conf = ranked[0][1] if ranked else MatchConfidence.REJECTED

        if best_conf == MatchConfidence.REJECTED:
            return LyricsOperationResult(
                ok=False, code=LyricsErrorCode.AMBIGUOUS_MATCH,
                message="No candidate with sufficient confidence",
                candidates=docs,
            )

        return LyricsOperationResult(
            ok=True, candidates=docs, source=LyricsSource.REMOTE_PROVIDER,
        )

    def select_candidate(self, identity: TrackIdentity,
                         candidate: LyricsDocument) -> LyricsOperationResult:
        cache_key = self._make_cache_key(candidate.provider_id, identity)
        if self._cache:
            self._cache.put(cache_key, candidate)
        return LyricsOperationResult(
            ok=True, document=candidate,
            source=candidate.source,
        )

    def cancel(self):
        self._tracker.cancel_current()
        self._bus.emit("lyrics_resolution_cancelled")

    def _check_manual(self, identity: TrackIdentity) -> LyricsOperationResult | None:
        return None

    def _check_embedded(self, identity: TrackIdentity) -> LyricsOperationResult | None:
        if not self._embedded:
            return None
        if not identity.filepath:
            return None
        return self._embedded.read(identity.filepath)

    def _check_sidecar(self, identity: TrackIdentity, ext: str) -> LyricsOperationResult | None:
        if not self._sidecar:
            return None
        directory = identity.filepath
        if directory:
            directory = __import__("os").path.dirname(directory)
        if not directory:
            return None
        return self._sidecar.read(directory, identity)

    def _check_cache(self, identity: TrackIdentity) -> LyricsOperationResult | None:
        if not self._cache:
            return None
        for provider in self._registry.list_enabled():
            cache_key = self._make_cache_key(provider.contract.provider_id, identity)
            doc = self._cache.get(cache_key)
            if doc is not None:
                return LyricsOperationResult(
                    ok=True, document=doc, source=LyricsSource.CACHE,
                )
            if self._cache.get_negative(cache_key):
                return None
        return None

    def _check_remote(
        self, identity: TrackIdentity,
        settings: LyricsSettings, cancellation_token: LyricsCancellationToken | None,
    ) -> LyricsOperationResult | None:
        if not settings.remote_enabled:
            return None
        if self._network and not self._network.is_online:
            return None

        for provider in self._registry.resolve_order(settings.provider_order):
            if cancellation_token and cancellation_token.cancelled:
                return LyricsOperationResult(
                    ok=False, code=LyricsErrorCode.CANCELLED,
                    cancelled=True,
                )
            result = provider.resolve(identity)
            if result.ok and result.document:
                return result

        return None

    def _resolve_order(self, settings: LyricsSettings) -> list[LyricsSource]:
        if settings.offline_mode:
            return [s for s in _DEFAULT_ORDER if s != LyricsSource.REMOTE_PROVIDER]
        return list(_DEFAULT_ORDER)

    def _cancelled(self, request_id: str, track_hash: str) -> LyricsOperationResult:
        self._bus.emit("lyrics_resolution_cancelled", request_id=request_id, track_hash=track_hash)
        return LyricsOperationResult(
            ok=False, code=LyricsErrorCode.CANCELLED,
            cancelled=True, message="Cancelled",
        )

    @staticmethod
    def _next_request_id(identity: TrackIdentity) -> str:
        import time
        return f"req_{int(time.time() * 1000)}_{hash(identity.title)}"

    @staticmethod
    def _make_cache_key(provider_id: str, identity: TrackIdentity) -> str:
        return f"{provider_id}:{identity.title.lower().strip()}|{identity.artist.lower().strip()}"


def _hash_identity(identity: TrackIdentity) -> str:
    import hashlib
    raw = f"{identity.title}|{identity.artist}|{identity.album}|{identity.duration_ms}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
