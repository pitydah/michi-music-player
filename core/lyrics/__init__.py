from core.lyrics.models import (
    TrackIdentity, LyricsDocument, LyricsLine, LyricsWord,
    LyricsOperationResult, LyricsMetadata, LyricsAttribution,
    LyricsSettings, ProviderContract, NormalizedIdentity,
    LyricsSource, LyricsStatus, MatchConfidence, LyricsErrorCode,
    compute_track_hash, compute_content_hash,
)
from core.lyrics.service import LyricsService
from core.lyrics.resolver import LyricsResolver
from core.lyrics.registry import LyricsProviderRegistry
from core.lyrics.parser import parse_lrc, serialize_lrc, parse_plain, normalize_document
from core.lyrics.timeline import LyricsTimeline
from core.lyrics.normalizer import TrackIdentityNormalizer
from core.lyrics.matcher import compute_match_score, rank_candidates
from core.lyrics.editor import LyricsEditorService
from core.lyrics.storage import LyricsStorageService
from core.lyrics.trace import LyricsTraceRecorder
from core.lyrics.attribution import LyricsAttributionPolicy
from core.lyrics.events import LyricEventBus, LyricDomainEvent
from core.lyrics.cancellation import LyricsCancellationToken, LyricsCancellationSource, LyricsRequestTracker

__all__ = [
    "TrackIdentity", "LyricsDocument", "LyricsLine", "LyricsWord",
    "LyricsOperationResult", "LyricsMetadata", "LyricsAttribution",
    "LyricsSettings", "ProviderContract", "NormalizedIdentity",
    "LyricsSource", "LyricsStatus", "MatchConfidence", "LyricsErrorCode",
    "compute_track_hash", "compute_content_hash",
    "LyricsService", "LyricsResolver", "LyricsProviderRegistry",
    "parse_lrc", "serialize_lrc", "parse_plain", "normalize_document",
    "LyricsTimeline", "TrackIdentityNormalizer",
    "compute_match_score", "rank_candidates",
    "LyricsEditorService", "LyricsStorageService",
    "LyricsTraceRecorder", "LyricsAttributionPolicy",
    "LyricEventBus", "LyricDomainEvent",
    "LyricsCancellationToken", "LyricsCancellationSource", "LyricsRequestTracker",
]
