"""Enrichment coordination service — M6.9A/R1 async-correlation firewall.

The service is the ONLY application-side entry point for enrichment. It
depends EXCLUSIVELY on the enrichment bounded contexts (identity resolver,
knowledge providers, knowledge repository, identity repository, asset
store) and the pure domain gates. It has NO access to the canonical
library ports (LibraryIndexRepository, MetadataExtractorPort,
ArtworkCachePort, any tag writer) — reverse propagation from external
knowledge into local metadata is structurally impossible.

R1 additions:

- Identity authority: resolved identities persist SEPARATELY from
  downloaded knowledge; MANUAL mappings are authoritative over automatic
  re-resolution and survive ``clear_knowledge()``.
- ``confirm_*_identity`` / ``reset_*_identity`` touch ONLY the external
  identity authority (never local file tags).
- Identity changes invalidate the associated knowledge profile (a stale
  biography can never be shown under a new identity).
- Delivery is additionally guarded by the CURRENT persisted identity:
  a result whose external id no longer matches the authority is STALE.
"""

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from michi.application.enrichment_ports import (
    AlbumKnowledgeProviderPort,
    ArtistKnowledgeProviderPort,
    EnrichmentAssetStorePort,
    ExternalIdentityResolverPort,
    IdentityRepositoryPort,
    KnowledgeRepositoryPort,
)
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumIdentityResolution,
    AlbumKnowledgeProfile,
    ArtistExternalIdentity,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    DeliveryVerdict,
    EnrichmentEntityKind,
    EnrichmentRequest,
    EnrichmentRequestLedger,
    IdentityResolution,
    IdentityResolutionStatus,
    IdentityStatus,
    MatchMethod,
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


def _utc_now_iso() -> str:
    """UTC timestamp for identity resolution records (deterministic
    format, honest wall-clock value)."""
    return datetime.now(UTC).isoformat(timespec="seconds")


class EnrichmentService:
    """Fail-closed enrichment coordinator (M6.9A + R1).

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
        identity_repository: IdentityRepositoryPort,
        asset_store: EnrichmentAssetStorePort | None = None,
    ) -> None:
        self._resolver = resolver
        self._artist_provider = artist_provider
        self._album_provider = album_provider
        self._repository = repository
        self._identity_repository = identity_repository
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
        register the pending async request.

        R1: a persisted MANUAL mapping is authoritative — it short-circuits
        automatic re-resolution. AUTO/EMBEDDED_HINT resolutions are
        persisted into the identity authority (identity != knowledge)."""
        local_key = evidence.local_artist_key
        existing = self._identity_repository.load_artist_identity(local_key)
        if existing is not None and existing.match_method is MatchMethod.MANUAL:
            resolution = IdentityResolution(
                status=IdentityResolutionStatus.RESOLVED,
                external_entity_id=existing.external_artist_id,
            )
            request = self._register(
                EnrichmentEntityKind.ARTIST,
                local_key,
                existing.external_artist_id,
                generation,
            )
            return EnrichmentRequestOutcome(resolution=resolution, request=request)

        candidates = self._resolver.find_artist_candidates(evidence)
        resolution = resolve_artist_identity(candidates, evidence)
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        method = (
            MatchMethod.EMBEDDED_HINT
            if evidence.identity_hints.artist_ids
            else MatchMethod.AUTO
        )
        self._identity_repository.save_artist_identity(
            ArtistExternalIdentity(
                local_artist_key=local_key,
                external_artist_id=resolution.external_entity_id,
                status=IdentityStatus.RESOLVED,
                match_method=method,
                manually_confirmed=False,
                resolved_at=_utc_now_iso(),
            )
        )
        request = self._register(
            EnrichmentEntityKind.ARTIST,
            local_key,
            resolution.external_entity_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_artist_profile(
        self, request: EnrichmentRequest, profile: ArtistKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an artist result ONLY if it matches its immutable request
        context AND the current identity authority. Out-of-order/stale/
        unknown/mismatched deliveries are discarded."""
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        if profile.external_artist_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_artist_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        current = self._identity_repository.load_artist_identity(
            request.local_entity_key
        )
        if (
            current is not None
            and current.external_artist_id != request.external_entity_id
        ):
            # Identity changed while the request was in flight: discard.
            return DeliveryVerdict.STALE
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        self._repository.save_artist_profile(profile)
        return verdict

    def deliver_artist_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending ARTIST request after provider failure — with
        ZERO repository writes. R1: the request kind is checked — an
        album request is NEVER consumed here."""
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        return self._ledger.deliver(request)

    # ------------------------------------------------------------------
    # ALBUM ENRICHMENT
    # ------------------------------------------------------------------

    def request_album_enrichment(
        self,
        evidence: AlbumIdentityEvidence,
        generation: int = 0,
    ) -> EnrichmentRequestOutcome:
        """Resolve the album identity (release GROUP gate) and register
        the pending request.

        R1: a persisted MANUAL album mapping is authoritative; the
        already-resolved artist identity (when present) is injected into
        the evidence so artist-credit compatibility constrains matching."""
        local_key = evidence.local_album_key
        existing = self._identity_repository.load_album_identity(local_key)
        if existing is not None and existing.match_method is MatchMethod.MANUAL:
            resolution = AlbumIdentityResolution(
                status=IdentityResolutionStatus.RESOLVED,
                release_group_id=existing.release_group_id,
                release_id=existing.release_id,
            )
            request = self._register(
                EnrichmentEntityKind.ALBUM,
                local_key,
                existing.release_group_id,
                generation,
            )
            return EnrichmentRequestOutcome(resolution=resolution, request=request)

        if not evidence.resolved_artist_external_id and evidence.local_album_artist_key:
            artist_identity = self._identity_repository.load_artist_identity(
                evidence.local_album_artist_key
            )
            if artist_identity is not None:
                evidence = replace(
                    evidence,
                    resolved_artist_external_id=artist_identity.external_artist_id,
                )
        group_candidates = self._resolver.find_release_group_candidates(evidence)
        edition_candidates = self._resolver.find_release_edition_candidates(evidence)
        resolution = resolve_album_identity(
            group_candidates, edition_candidates, evidence
        )
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        if not resolution.release_group_id:
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        method = (
            MatchMethod.EMBEDDED_HINT
            if evidence.identity_hints.release_group_ids
            else MatchMethod.AUTO
        )
        self._identity_repository.save_album_identity(
            AlbumExternalIdentity(
                local_album_key=local_key,
                release_group_id=resolution.release_group_id,
                release_id=resolution.release_id,
                status=IdentityStatus.RESOLVED,
                match_method=method,
                manually_confirmed=False,
                resolved_at=_utc_now_iso(),
            )
        )
        request = self._register(
            EnrichmentEntityKind.ALBUM,
            local_key,
            resolution.release_group_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_album_profile(
        self, request: EnrichmentRequest, profile: AlbumKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an album result ONLY if it matches its immutable request
        context AND the current identity authority."""
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        if profile.release_group_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_album_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        current = self._identity_repository.load_album_identity(
            request.local_entity_key
        )
        if (
            current is not None
            and current.release_group_id != request.external_entity_id
        ):
            return DeliveryVerdict.STALE
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        self._repository.save_album_profile(profile)
        return verdict

    def deliver_album_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending ALBUM request after provider failure — ZERO
        repository writes. R1: kind-checked (never consumes an artist
        request)."""
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        return self._ledger.deliver(request)

    # ------------------------------------------------------------------
    # MANUAL IDENTITY AUTHORITY (R1)
    # ------------------------------------------------------------------

    def confirm_artist_identity(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistExternalIdentity:
        """Explicit user confirmation: persist a MANUAL mapping.

        If the mapping CHANGES the external id, the associated knowledge
        profile is deleted — a stale biography/photo can never be shown
        under the new identity. Local file tags are NEVER touched."""
        previous = self._identity_repository.load_artist_identity(local_artist_key)
        if previous is not None and previous.external_artist_id != external_artist_id:
            self._repository.delete_artist_profile(local_artist_key)
        identity = ArtistExternalIdentity(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            manually_confirmed=True,
            resolved_at=_utc_now_iso(),
        )
        self._identity_repository.save_artist_identity(identity)
        return identity

    def reset_artist_identity(self, local_artist_key: str) -> None:
        """Remove the artist identity mapping AND its associated knowledge
        (R1 contract: resetting identity clears knowledge for that entity
        so nothing displays under an unresolved identity)."""
        self._identity_repository.delete_artist_identity(local_artist_key)
        self._repository.delete_artist_profile(local_artist_key)

    def confirm_album_identity(
        self,
        local_album_key: str,
        release_group_id: str,
        release_id: str = "",
    ) -> AlbumExternalIdentity:
        """Explicit user confirmation for an album (release group, and
        optionally one specific release edition)."""
        previous = self._identity_repository.load_album_identity(local_album_key)
        if previous is not None and previous.release_group_id != release_group_id:
            self._repository.delete_album_profile(local_album_key)
        identity = AlbumExternalIdentity(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            manually_confirmed=True,
            resolved_at=_utc_now_iso(),
        )
        self._identity_repository.save_album_identity(identity)
        return identity

    def reset_album_identity(self, local_album_key: str) -> None:
        """Remove the album identity mapping AND its associated knowledge."""
        self._identity_repository.delete_album_identity(local_album_key)
        self._repository.delete_album_profile(local_album_key)

    # ------------------------------------------------------------------
    # CLEAR SEMANTICS (R1)
    # ------------------------------------------------------------------

    def clear_knowledge(self) -> None:
        """Delete downloaded knowledge; MANUAL/AUTO/EMBEDDED_HINT identity
        mappings are PRESERVED."""
        self._repository.clear_knowledge()

    def clear_identities(self) -> None:
        """Delete the whole identity authority (explicit; never called by
        knowledge clearing)."""
        self._identity_repository.clear_identities()

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
