"""Enrichment coordination service — M6.9A async-correlation firewall.

The service is the ONLY application-side entry point for enrichment. It
depends EXCLUSIVELY on the enrichment bounded contexts (identity resolver,
knowledge providers, knowledge repository, asset store) and the pure
domain gates. It has NO access to the canonical library ports
(LibraryIndexRepository, MetadataExtractorPort, ArtworkCachePort, any tag
writer) — reverse propagation from external knowledge into local metadata
is structurally impossible.

Correlation contract: ``request_*`` resolves identity (fail-closed) and
registers an immutable ``EnrichmentRequest``; ``deliver_*`` commits a
result ONLY while it still matches that original request context.
Stale / out-of-order / unknown / mismatched deliveries are discarded —
never applied.
"""

import logging
from dataclasses import dataclass
from uuid import uuid4

from michi.application.enrichment_ports import (
    AlbumKnowledgeProviderPort,
    ArtistKnowledgeProviderPort,
    EnrichmentAssetStorePort,
    ExternalIdentityResolverPort,
    KnowledgeRepositoryPort,
)
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityResolution,
    AlbumKnowledgeProfile,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    DeliveryVerdict,
    EnrichmentEntityKind,
    EnrichmentRequest,
    EnrichmentRequestLedger,
    IdentityResolution,
    IdentityResolutionStatus,
    resolve_album_identity,
    resolve_artist_identity,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichmentRequestOutcome:
    """Result of a ``request_*`` call: the fail-closed identity verdict
    plus the registered pending request (None unless RESOLVED)."""

    resolution: IdentityResolution | AlbumIdentityResolution
    request: EnrichmentRequest | None


class EnrichmentService:
    """Fail-closed enrichment coordinator (M6.9A).

    Never uses mutable global/current entity fields: every pending
    operation is correlated through the immutable ``EnrichmentRequest``
    registered in the ledger. A result for Artist A can never mutate
    Artist B — neither via routing nor via shared state.
    """

    def __init__(
        self,
        resolver: ExternalIdentityResolverPort,
        artist_provider: ArtistKnowledgeProviderPort,
        album_provider: AlbumKnowledgeProviderPort,
        repository: KnowledgeRepositoryPort,
        asset_store: EnrichmentAssetStorePort | None = None,
    ) -> None:
        self._resolver = resolver
        self._artist_provider = artist_provider
        self._album_provider = album_provider
        self._repository = repository
        self._asset_store = asset_store
        self._ledger = EnrichmentRequestLedger()

    # ------------------------------------------------------------------
    # ARTIST ENRICHMENT
    # ------------------------------------------------------------------

    def request_artist_enrichment(
        self,
        evidence: ArtistIdentityEvidence,
        generation: int = 0,
    ) -> EnrichmentRequestOutcome:
        """Resolve the artist identity (homonym + conflict gates) and
        register the pending async request. AMBIGUOUS / IDENTITY_CONFLICT /
        NO_MATCH produce NO request — no profile is ever attached.

        R1: the local entity key rides inside the entity-specific
        evidence (never a shared/generic evidence bag)."""
        candidates = self._resolver.find_artist_candidates(evidence)
        resolution = resolve_artist_identity(candidates, evidence)
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        request = self._register(
            EnrichmentEntityKind.ARTIST,
            evidence.local_artist_key,
            resolution.external_entity_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_artist_profile(
        self, request: EnrichmentRequest, profile: ArtistKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an artist result ONLY if it matches its immutable request
        context (kind, local key, external id). Out-of-order/stale/unknown
        deliveries are discarded."""
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        if profile.external_artist_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_artist_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        self._repository.save_artist_profile(profile)
        return verdict

    def deliver_artist_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending artist request after provider failure — with
        ZERO repository writes. The canonical library is never touched by
        enrichment failure."""
        return self._ledger.deliver(request)

    # ------------------------------------------------------------------
    # ALBUM ENRICHMENT
    # ------------------------------------------------------------------

    def request_album_enrichment(
        self,
        evidence: AlbumIdentityEvidence,
        generation: int = 0,
    ) -> EnrichmentRequestOutcome:
        """Resolve the album identity (release GROUP gate) and register the
        pending request. The specific release edition id stays "" unless
        edition-identifying evidence exists.

        R1: album resolution uses the entity-specific
        ``AlbumIdentityEvidence`` — title is a required gate, year never
        resolves alone, and the resolved artist identity (when available)
        constrains artist-credit compatibility."""
        group_candidates = self._resolver.find_release_group_candidates(evidence)
        edition_candidates = self._resolver.find_release_edition_candidates(evidence)
        resolution = resolve_album_identity(
            group_candidates, edition_candidates, evidence
        )
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        if not resolution.release_group_id:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        request = self._register(
            EnrichmentEntityKind.ALBUM,
            evidence.local_album_key,
            resolution.release_group_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_album_profile(
        self, request: EnrichmentRequest, profile: AlbumKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an album result ONLY if it matches its immutable request
        context. Reverse-order deliveries never cross entity ownership."""
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        if profile.release_group_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_album_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        self._repository.save_album_profile(profile)
        return verdict

    def deliver_album_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending album request after provider failure — ZERO
        repository writes."""
        return self._ledger.deliver(request)

    # ------------------------------------------------------------------

    def pending_count(self) -> int:
        """Pending correlated requests (diagnostics/tests)."""
        return self._ledger.pending_count()

    def _register(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        external_entity_id: str,
        generation: int,
    ) -> EnrichmentRequest:
        request = EnrichmentRequest(
            request_id=uuid4().hex,
            entity_kind=entity_kind,
            local_entity_key=local_entity_key,
            external_entity_id=external_entity_id,
            generation=generation,
        )
        self._ledger.register(request)
        return request
