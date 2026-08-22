"""Enrichment coordination service — M6.9A/R1/R2 async-correlation firewall.

The service is the ONLY application-side entry point for enrichment. It
depends EXCLUSIVELY on the enrichment bounded contexts (identity resolver,
knowledge providers, knowledge repository, identity repository, asset
store) and the pure domain gates. It has NO access to the canonical
library ports (LibraryIndexRepository, MetadataExtractorPort,
ArtworkCachePort, any tag writer) — reverse propagation from external
knowledge into local metadata is structurally impossible.

R1: identity authority persisted separately from knowledge; MANUAL
mappings override automatic re-resolution and survive clear_knowledge().

R2:
- Identity transitions are CENTRALIZED (_persist_*_identity_transition):
  ANY identity change (AUTO / EMBEDDED_HINT / MANUAL) invalidates the
  pending request and deletes the stale knowledge profile BEFORE the new
  identity becomes durable. Same-external-id MatchMethod changes preserve
  knowledge. Album identity compares the (release_group_id, release_id)
  tuple.
- reset_*_identity / clear_identities INVALIDATE pending requests first;
  a late result can never repopulate knowledge after reset/clear.
- Delivery requires the CURRENT persisted identity to EXIST and match —
  a result without a current identity is STALE (defense-in-depth).
- Album requests correlate the release EDITION (external_variant_id);
  release-level knowledge can never commit against the wrong edition.
"""

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from michi.application.enrichment_ports import (
    AlbumKnowledgeProviderPort,
    ArtistKnowledgeProviderPort,
    EnrichmentAssetStorePort,
    EnrichmentProviderError,
    EnrichmentStorageError,
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
    dedupe_identity_ids,
    resolve_album_identity,
    resolve_artist_identity,
    resolve_release_hint_for_group,
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
    """Fail-closed enrichment coordinator (M6.9A + R1 + R2).

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
    # IDENTITY AUTHORITY POLICY (R3.1 — MANUAL > EMBEDDED_HINT > AUTO)
    # ------------------------------------------------------------------

    def _revoke_artist_identity(self, local_artist_key: str) -> None:
        """R3.1: a non-MANUAL identity is evidence-dependent. When the
        fresh resolution no longer supports it, invalidate the pending
        request and remove the durable identity + knowledge. MANUAL
        authority is NEVER revoked here."""
        self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
        existing = self._identity_repository.load_artist_identity(local_artist_key)
        if existing is None or existing.match_method is MatchMethod.MANUAL:
            return
        self._identity_repository.delete_artist_identity(local_artist_key)
        self._repository.delete_artist_profile(local_artist_key)

    def _revoke_album_identity(self, local_album_key: str) -> None:
        """R3.1 album equivalent of the AUTO/EMBEDDED revocation policy."""
        self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
        existing = self._identity_repository.load_album_identity(local_album_key)
        if existing is None or existing.match_method is MatchMethod.MANUAL:
            return
        self._identity_repository.delete_album_identity(local_album_key)
        self._repository.delete_album_profile(local_album_key)

    def _short_circuit_artist(
        self, existing: ArtistExternalIdentity, generation: int
    ) -> EnrichmentRequestOutcome:
        """Reuse a persisted identity as the request authority without
        touching the resolver (MANUAL and hint-less EMBEDDED_HINT)."""
        resolution = IdentityResolution(
            status=IdentityResolutionStatus.RESOLVED,
            external_entity_id=existing.external_artist_id,
        )
        request = self._register(
            EnrichmentEntityKind.ARTIST,
            existing.local_artist_key,
            existing.external_artist_id,
            "",
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def _short_circuit_album(
        self, existing: AlbumExternalIdentity, generation: int
    ) -> EnrichmentRequestOutcome:
        resolution = AlbumIdentityResolution(
            status=IdentityResolutionStatus.RESOLVED,
            release_group_id=existing.release_group_id,
            release_id=existing.release_id,
        )
        request = self._register(
            EnrichmentEntityKind.ALBUM,
            existing.local_album_key,
            existing.release_group_id,
            existing.release_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def _refine_embedded_album_release(
        self,
        existing: AlbumExternalIdentity,
        evidence: AlbumIdentityEvidence,
        generation: int,
    ) -> EnrichmentRequestOutcome:
        """R3.2: persisted EMBEDDED RG + NEW explicit release hint(s).

        The persisted group stays authoritative (never downgraded to
        AUTO); the current release evidence is evaluated via the pure
        contradiction-aware helper:
        - corroborated in the persisted group -> refine the edition
          (MatchMethod remains EMBEDDED_HINT; old release-level
          knowledge invalidated if the tuple changed);
        - uncorroborated -> group preserved, release not trusted;
        - proven in another group / multiple groups -> IDENTITY_CONFLICT
          and revocation of the non-manual mapping.
        """
        hints = dedupe_identity_ids(evidence.identity_hints.release_ids)
        if len(hints) > 1:
            self._revoke_album_identity(existing.local_album_key)
            return EnrichmentRequestOutcome(
                resolution=AlbumIdentityResolution(
                    status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                    candidate_ids=hints,
                ),
                request=None,
            )
        edition_candidates = self._resolver.find_release_edition_candidates(evidence)
        status, release_id = resolve_release_hint_for_group(
            existing.release_group_id, hints[0], edition_candidates
        )
        if status is IdentityResolutionStatus.IDENTITY_CONFLICT:
            self._revoke_album_identity(existing.local_album_key)
            return EnrichmentRequestOutcome(
                resolution=AlbumIdentityResolution(
                    status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                    candidate_ids=(hints[0],),
                ),
                request=None,
            )
        self._persist_album_identity_transition(
            AlbumExternalIdentity(
                local_album_key=existing.local_album_key,
                release_group_id=existing.release_group_id,
                release_id=release_id,
                status=IdentityStatus.RESOLVED,
                match_method=MatchMethod.EMBEDDED_HINT,
                resolved_at=_utc_now_iso(),
            )
        )
        resolution = AlbumIdentityResolution(
            status=IdentityResolutionStatus.RESOLVED,
            release_group_id=existing.release_group_id,
            release_id=release_id,
        )
        request = self._register(
            EnrichmentEntityKind.ALBUM,
            existing.local_album_key,
            existing.release_group_id,
            release_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    # ------------------------------------------------------------------
    # IDENTITY TRANSITIONS (R2 — centralized, atomic semantics)
    # ------------------------------------------------------------------

    def _persist_artist_identity_transition(self, new: ArtistExternalIdentity) -> None:
        """R2: persist an artist identity with stale-knowledge semantics.

        If the external id CHANGED: invalidate the pending request and
        delete the stale knowledge profile BEFORE persisting. Same id with
        a different MatchMethod (e.g. AUTO -> MANUAL) preserves knowledge.
        """
        key = new.local_artist_key
        existing = self._identity_repository.load_artist_identity(key)
        if (
            existing is not None
            and existing.external_artist_id != new.external_artist_id
        ):
            self._ledger.invalidate(EnrichmentEntityKind.ARTIST, key)
            self._repository.delete_artist_profile(key)
        self._identity_repository.save_artist_identity(new)

    def _persist_album_identity_transition(self, new: AlbumExternalIdentity) -> None:
        """R2: persist an album identity with stale-knowledge semantics.

        The album identity is the TUPLE (release_group_id, release_id):
        if EITHER changes, the pending request is invalidated and the
        stale knowledge profile deleted BEFORE persisting."""
        key = new.local_album_key
        existing = self._identity_repository.load_album_identity(key)
        if existing is not None and (
            existing.release_group_id != new.release_group_id
            or existing.release_id != new.release_id
        ):
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, key)
            self._repository.delete_album_profile(key)
        self._identity_repository.save_album_identity(new)

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

        R3.1 MATCH AUTHORITY (MANUAL > EMBEDDED_HINT > AUTO):
        - MANUAL: sticky — short-circuits resolution entirely;
        - EMBEDDED_HINT: a persisted embedded mapping is stronger than
          inferred AUTO evidence — without NEW explicit same-role hints
          it is reused directly; new explicit hints decide via the
          normal gates (same -> retained, different -> transition,
          multiple distinct -> IDENTITY_CONFLICT + revocation);
        - AUTO: evidence-dependent — a fresh non-RESOLVED outcome
          (AMBIGUOUS / IDENTITY_CONFLICT / NO_MATCH) REVOKES the old
          AUTO identity and hides its knowledge."""
        local_key = evidence.local_artist_key
        existing = self._identity_repository.load_artist_identity(local_key)
        if existing is not None and existing.match_method is MatchMethod.MANUAL:
            return self._short_circuit_artist(existing, generation)
        current_hints = dedupe_identity_ids(evidence.identity_hints.artist_ids)
        if (
            existing is not None
            and existing.match_method is MatchMethod.EMBEDDED_HINT
            and not current_hints
        ):
            # Weaker AUTO evidence must never replace a persisted
            # embedded identity: reuse it without resolving.
            return self._short_circuit_artist(existing, generation)

        if current_hints:
            # R1 OFFLINE EMBEDDED AUTHORITY: explicit identity hints are
            # LOCAL evidence — they resolve WITHOUT any network search
            # (a single distinct hint resolves directly; multiple
            # distinct hints conflict with ZERO network calls).
            resolution = resolve_artist_identity((), evidence)
        else:
            candidates = self._resolver.find_artist_candidates(evidence)
            resolution = resolve_artist_identity(candidates, evidence)
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            # R3.1: evidence no longer supports the old automatic
            # mapping — revoke it (ledger first, then durable deletion).
            self._revoke_artist_identity(local_key)
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        method = MatchMethod.EMBEDDED_HINT if current_hints else MatchMethod.AUTO
        self._persist_artist_identity_transition(
            ArtistExternalIdentity(
                local_artist_key=local_key,
                external_artist_id=resolution.external_entity_id,
                status=IdentityStatus.RESOLVED,
                match_method=method,
                resolved_at=_utc_now_iso(),
            )
        )
        request = self._register(
            EnrichmentEntityKind.ARTIST,
            local_key,
            resolution.external_entity_id,
            "",
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_artist_profile(
        self, request: EnrichmentRequest, profile: ArtistKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an artist result ONLY if it matches its immutable request
        context AND the current identity authority. R2: a MISSING current
        identity is STALE too (defense-in-depth on top of invalidation)."""
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        if profile.external_artist_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_artist_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        current = self._identity_repository.load_artist_identity(
            request.local_entity_key
        )
        if current is None or current.external_artist_id != request.external_entity_id:
            # Identity missing (reset/clear) or changed: discard.
            return DeliveryVerdict.STALE
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        # R3: COMMITTED means ACTUALLY persisted. A failed knowledge
        # write is STORAGE_FAILED — terminal, never a fake success.
        try:
            self._repository.save_artist_profile(profile)
        except EnrichmentStorageError:
            logger.warning(
                "enrichment artist profile persistence failed for %r",
                request.local_entity_key,
            )
            return DeliveryVerdict.STORAGE_FAILED
        return verdict

    def deliver_artist_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending ARTIST request after provider failure — with
        ZERO repository writes. Kind-checked: an album request is NEVER
        consumed here."""
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

        R3.1: the same authority precedence applies — MANUAL sticky;
        a persisted EMBEDDED_HINT release-group mapping is reused when
        the current request carries no new explicit release-group hint;
        AUTO mappings are revoked when fresh evidence becomes
        AMBIGUOUS / IDENTITY_CONFLICT / NO_MATCH."""
        local_key = evidence.local_album_key
        existing = self._identity_repository.load_album_identity(local_key)
        if existing is not None and existing.match_method is MatchMethod.MANUAL:
            return self._short_circuit_album(existing, generation)
        current_rg_hints = dedupe_identity_ids(
            evidence.identity_hints.release_group_ids
        )
        current_release_hints = dedupe_identity_ids(evidence.identity_hints.release_ids)
        if (
            existing is not None
            and existing.match_method is MatchMethod.EMBEDDED_HINT
            and not current_rg_hints
            and not current_release_hints
        ):
            # R3.2: short-circuit ONLY without ANY current direct album
            # hint — a NEW explicit release_id is direct edition evidence
            # and must be processed, never ignored.
            return self._short_circuit_album(existing, generation)
        if (
            existing is not None
            and existing.match_method is MatchMethod.EMBEDDED_HINT
            and not current_rg_hints
            and current_release_hints
        ):
            # R3.2 RELEASE-ONLY REFINEMENT: the persisted RG remains the
            # stronger direct identity authority; the current explicit
            # release hint is evaluated against it.
            return self._refine_embedded_album_release(existing, evidence, generation)

        if not evidence.resolved_artist_external_id and evidence.local_album_artist_key:
            artist_identity = self._identity_repository.load_artist_identity(
                evidence.local_album_artist_key
            )
            if artist_identity is not None:
                evidence = replace(
                    evidence,
                    resolved_artist_external_id=artist_identity.external_artist_id,
                )
        if current_rg_hints:
            # R1 OFFLINE EMBEDDED RG AUTHORITY: an explicit release-group
            # hint resolves WITHOUT a group search. A release-edition
            # hint still requires corroboration — if the edition lookup
            # fails (offline), the RG persists and the release stays ""
            # (never trusted without corroboration).
            if current_release_hints:
                try:
                    edition_candidates = self._resolver.find_release_edition_candidates(
                        evidence
                    )
                except EnrichmentProviderError:
                    edition_candidates = ()
            else:
                edition_candidates = ()
            resolution = resolve_album_identity((), edition_candidates, evidence)
        else:
            group_candidates = self._resolver.find_release_group_candidates(evidence)
            edition_candidates = self._resolver.find_release_edition_candidates(
                evidence
            )
            resolution = resolve_album_identity(
                group_candidates, edition_candidates, evidence
            )
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            self._revoke_album_identity(local_key)
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        if not resolution.release_group_id:
            self._revoke_album_identity(local_key)
            return EnrichmentRequestOutcome(resolution=resolution, request=None)
        method = MatchMethod.EMBEDDED_HINT if current_rg_hints else MatchMethod.AUTO
        self._persist_album_identity_transition(
            AlbumExternalIdentity(
                local_album_key=local_key,
                release_group_id=resolution.release_group_id,
                release_id=resolution.release_id,
                status=IdentityStatus.RESOLVED,
                match_method=method,
                resolved_at=_utc_now_iso(),
            )
        )
        request = self._register(
            EnrichmentEntityKind.ALBUM,
            local_key,
            resolution.release_group_id,
            resolution.release_id,
            generation,
        )
        return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_album_profile(
        self, request: EnrichmentRequest, profile: AlbumKnowledgeProfile
    ) -> DeliveryVerdict:
        """Commit an album result ONLY if it matches its immutable request
        context AND the current identity authority.

        R2 RELEASE-EDITION CORRELATION: the profile's release_id must
        equal the request's release variant exactly — release-level
        knowledge can never commit against the wrong edition."""
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        if profile.release_group_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.release_id != request.external_variant_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_album_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        current = self._identity_repository.load_album_identity(
            request.local_entity_key
        )
        if (
            current is None
            or current.release_group_id != request.external_entity_id
            or current.release_id != request.external_variant_id
        ):
            return DeliveryVerdict.STALE
        verdict = self._ledger.deliver(request)
        if verdict is not DeliveryVerdict.COMMITTED:
            return verdict
        try:
            self._repository.save_album_profile(profile)
        except EnrichmentStorageError:
            logger.warning(
                "enrichment album profile persistence failed for %r",
                request.local_entity_key,
            )
            return DeliveryVerdict.STORAGE_FAILED
        return verdict

    def deliver_album_failure(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Close a pending ALBUM request after provider failure — ZERO
        repository writes. Kind-checked (never consumes an artist
        request)."""
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        return self._ledger.deliver(request)

    # ------------------------------------------------------------------
    # MANUAL IDENTITY AUTHORITY (R1 + R2 transitions)
    # ------------------------------------------------------------------

    def confirm_artist_identity(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistExternalIdentity:
        """Explicit user confirmation: persist a MANUAL mapping through the
        centralized transition (an identity CHANGE invalidates pending
        requests and deletes stale knowledge; a same-id method change does
        not). Local file tags are NEVER touched."""
        identity = ArtistExternalIdentity(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        self._persist_artist_identity_transition(identity)
        return identity

    def reset_artist_identity(self, local_artist_key: str) -> None:
        """R2 order: invalidate the pending request FIRST (runtime
        safety), then delete the durable identity, then the associated
        knowledge. A late result can never commit after reset."""
        self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
        self._identity_repository.delete_artist_identity(local_artist_key)
        self._repository.delete_artist_profile(local_artist_key)

    def confirm_album_identity(
        self,
        local_album_key: str,
        release_group_id: str,
        release_id: str = "",
    ) -> AlbumExternalIdentity:
        """Explicit user confirmation for an album (release group and
        optionally one specific release edition), via the centralized
        (release_group_id, release_id) tuple transition."""
        identity = AlbumExternalIdentity(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        self._persist_album_identity_transition(identity)
        return identity

    def reset_album_identity(self, local_album_key: str) -> None:
        """R2: invalidate the pending request FIRST, then delete identity
        and knowledge."""
        self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
        self._identity_repository.delete_album_identity(local_album_key)
        self._repository.delete_album_profile(local_album_key)

    # ------------------------------------------------------------------
    # CLEAR SEMANTICS (R1 + R2)
    # ------------------------------------------------------------------

    def clear_knowledge(self) -> None:
        """Delete downloaded knowledge; MANUAL/AUTO/EMBEDDED_HINT identity
        mappings are PRESERVED."""
        self._repository.clear_knowledge()

    def cancel_artist_request(self, local_artist_key: str) -> None:
        """M6.9-BACKEND-R1: invalidate ONLY the async correlation for an
        artist — never deletes identity, knowledge or local data."""
        self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)

    def cancel_album_request(self, local_album_key: str) -> None:
        """R1: invalidate ONLY the async correlation for an album."""
        self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)

    def cancel_all_requests(self) -> None:
        """R1: invalidate every pending async enrichment request."""
        self._ledger.invalidate_all()

    def clear_artist_knowledge(self, local_artist_key: str) -> None:
        """M6.9F: per-entity intent — knowledge only, identity preserved."""
        self._repository.delete_artist_profile(local_artist_key)

    def clear_album_knowledge(self, local_album_key: str) -> None:
        """M6.9F: per-entity intent — knowledge only, identity preserved."""
        self._repository.delete_album_profile(local_album_key)

    def clear_identities(self) -> None:
        """R2 safest public contract: invalidate ALL pending requests,
        clear the identity authority, clear active knowledge. No old
        request can repopulate anything after this call."""
        self._ledger.invalidate_all()
        self._identity_repository.clear_identities()
        self._repository.clear_knowledge()

    # ------------------------------------------------------------------
    # KNOWLEDGE READ AUTHORITY (R2 — no orphan knowledge presentation)
    # ------------------------------------------------------------------

    def get_artist_knowledge(
        self, local_artist_key: str
    ) -> ArtistKnowledgeProfile | None:
        """Knowledge is valid ONLY under the CURRENT resolved identity:
        a profile whose external id differs (or whose identity is missing)
        is never returned — stale rows are invisible to presentation."""
        # R3 presentation-safe degradation: storage failures on READS
        # become None for the presentation caller (authority workflows
        # keep the truthful raise).
        try:
            identity = self._identity_repository.load_artist_identity(local_artist_key)
            if identity is None:
                return None
            profile = self._repository.load_artist_profile(local_artist_key)
        except EnrichmentStorageError:
            logger.warning(
                "enrichment artist knowledge read degraded for %r",
                local_artist_key,
            )
            return None
        if profile is None or profile.external_artist_id != identity.external_artist_id:
            return None
        return profile

    def get_album_knowledge(self, local_album_key: str) -> AlbumKnowledgeProfile | None:
        """Album knowledge is valid ONLY when both the release GROUP and
        the release EDITION match the current identity."""
        try:
            identity = self._identity_repository.load_album_identity(local_album_key)
            if identity is None:
                return None
            profile = self._repository.load_album_profile(local_album_key)
        except EnrichmentStorageError:
            logger.warning(
                "enrichment album knowledge read degraded for %r",
                local_album_key,
            )
            return None
        if profile is None:
            return None
        if profile.release_group_id != identity.release_group_id:
            return None
        if profile.release_id != identity.release_id:
            return None
        return profile

    # ------------------------------------------------------------------

    def pending_count(self) -> int:
        """Pending correlated requests (diagnostics/tests)."""
        return self._ledger.pending_count()

    def _register(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        external_entity_id: str,
        external_variant_id: str,
        generation: int,
    ) -> EnrichmentRequest:
        request = EnrichmentRequest(
            request_id=uuid4().hex,
            entity_kind=entity_kind,
            local_entity_key=local_entity_key,
            external_entity_id=external_entity_id,
            external_variant_id=external_variant_id,
            generation=generation,
        )
        self._ledger.register(request)
        return request
