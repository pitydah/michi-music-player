"""Enrichment coordination service — M6.9A/R1/R1.1/R1.2 authority.

The service is the ONLY application-side authority for identity
persistence, async request registration and knowledge delivery. It has
NO access to canonical library ports, tag writers or providers over the
network.

R1.2 OPERATION GENERATION AUTHORITY:

- per (entity_kind, local_entity_key) a MONOTONIC generation exists in
  the service (runtime/application state, never persisted);
- every async operation carries its generation inside its
  ``EnrichmentRequest``;
- identity transitions, request registration, request invalidation and
  final deliveries re-validate the generation INSIDE the authority lock
  (``threading.RLock``) — a stale worker can physically finish its
  computation but can NEVER cross an authority commit gate again;
- request invalidation is EXACT (``invalidate_if_current``): a stale
  worker can never cancel a newer generation's request;
- manual identity operations (confirm/reset/clear) and deliveries are
  serialized by the SAME lock: no logical window exists where an old
  request stays valid after a newer identity transition.

NO provider/network work happens under the authority lock.
"""

import logging
import threading
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
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichmentRequestOutcome:
    """Result of a ``request_*`` call: the fail-closed identity verdict
    plus the registered pending request (None unless RESOLVED)."""

    resolution: IdentityResolution | AlbumIdentityResolution
    request: EnrichmentRequest | None


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class EnrichmentService:
    """Fail-closed enrichment authority (M6.9A + R1 + R1.1 + R1.2)."""

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
        # R1.2: application-side operation generation authority.
        self._operation_generations: dict[tuple[EnrichmentEntityKind, str], int] = {}
        self._authority_lock = threading.RLock()

    # ------------------------------------------------------------------
    # R1.2 OPERATION GENERATION AUTHORITY
    # ------------------------------------------------------------------

    def _bump_generation_locked(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> int:
        """THE single generation allocator (R1.3). Generations are
        strictly monotonic per entity for the Service lifetime — never
        reused, never cleared."""
        key = (entity_kind, local_entity_key)
        current = self._operation_generations.get(key, 0)
        next_generation = current + 1
        self._operation_generations[key] = next_generation
        return next_generation

    def begin_operation(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> int:
        """R1.3: THE Service is the SOLE generation authority. Allocates
        the next monotonic generation and registers it as CURRENT."""
        with self._authority_lock:
            return self._bump_generation_locked(entity_kind, local_entity_key)

    def retire_operation(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        generation: int,
    ) -> bool:
        """R1.3 canonical retirement barrier.

        Under the authority lock: if ``generation`` is NOT the current
        authority it returns False (a stale worker can never retire a
        newer generation). If it IS current: the authority epoch is
        advanced (the generation can never cross a commit gate again)
        and the pending request of THAT generation (if any) is
        invalidated — atomically."""
        with self._authority_lock:
            key = (entity_kind, local_entity_key)
            if self._operation_generations.get(key) != generation:
                return False
            self._bump_generation_locked(entity_kind, local_entity_key)
            self._ledger.invalidate_if_generation_current(
                entity_kind, local_entity_key, generation
            )
            return True

    def is_current_operation(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        generation: int,
    ) -> bool:
        with self._authority_lock:
            return (
                self._operation_generations.get((entity_kind, local_entity_key))
                == generation
            )

    # ------------------------------------------------------------------
    # IDENTITY AUTHORITY POLICY (MANUAL > EMBEDDED_HINT > AUTO)
    # ------------------------------------------------------------------

    def _revoke_artist_identity(self, local_artist_key: str) -> None:
        """R3.1: evidence-dependent non-manual identity revocation.
        CALLED UNDER THE AUTHORITY LOCK."""
        self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
        existing = self._identity_repository.load_artist_identity(local_artist_key)
        if existing is None or existing.match_method is MatchMethod.MANUAL:
            return
        self._identity_repository.delete_artist_identity(local_artist_key)
        self._repository.delete_artist_profile(local_artist_key)

    def _revoke_album_identity(self, local_album_key: str) -> None:
        self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
        existing = self._identity_repository.load_album_identity(local_album_key)
        if existing is None or existing.match_method is MatchMethod.MANUAL:
            return
        self._identity_repository.delete_album_identity(local_album_key)
        self._repository.delete_album_profile(local_album_key)

    def _persist_artist_identity_transition(self, new: ArtistExternalIdentity) -> None:
        """R2/R1.2: centralized artist identity transition (stale
        knowledge + pending request invalidated on identity CHANGE).
        CALLED UNDER THE AUTHORITY LOCK."""
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
        key = new.local_album_key
        existing = self._identity_repository.load_album_identity(key)
        if existing is not None and (
            existing.release_group_id != new.release_group_id
            or existing.release_id != new.release_id
        ):
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, key)
            self._repository.delete_album_profile(key)
        self._identity_repository.save_album_identity(new)

    def _short_circuit_artist(
        self, existing: ArtistExternalIdentity, generation: int
    ) -> EnrichmentRequestOutcome:
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ARTIST, existing.local_artist_key, generation
            ):
                return EnrichmentRequestOutcome(
                    resolution=IdentityResolution(
                        status=IdentityResolutionStatus.SUPERSEDED
                    ),
                    request=None,
                )
            resolution = IdentityResolution(
                status=IdentityResolutionStatus.RESOLVED,
                external_entity_id=existing.external_artist_id,
            )
            request = self._register_locked(
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
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ALBUM, existing.local_album_key, generation
            ):
                return EnrichmentRequestOutcome(
                    resolution=AlbumIdentityResolution(
                        status=IdentityResolutionStatus.SUPERSEDED
                    ),
                    request=None,
                )
            resolution = AlbumIdentityResolution(
                status=IdentityResolutionStatus.RESOLVED,
                release_group_id=existing.release_group_id,
                release_id=existing.release_id,
            )
            request = self._register_locked(
                EnrichmentEntityKind.ALBUM,
                existing.local_album_key,
                existing.release_group_id,
                existing.release_id,
                generation,
            )
            return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def _is_current_locked(
        self, entity_kind: EnrichmentEntityKind, local_key: str, generation: int
    ) -> bool:
        recorded = self._operation_generations.get((entity_kind, local_key))
        if recorded is None and generation == 0:
            # R1.2: generation 0 with no recorded authority = LEGACY
            # standalone call (direct service use). The production
            # coordinator ALWAYS begins operations with generation >= 1,
            # which makes the authority real and stale workers unable to
            # commit. Documented contract.
            return True
        return recorded == generation

    def _register_locked(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        external_entity_id: str,
        external_variant_id: str,
        generation: int,
        artist_dependency_local_key: str = "",
        artist_dependency_id: str = "",
    ) -> EnrichmentRequest:
        request = EnrichmentRequest(
            request_id=uuid4().hex,
            entity_kind=entity_kind,
            local_entity_key=local_entity_key,
            external_entity_id=external_entity_id,
            external_variant_id=external_variant_id,
            generation=generation,
            artist_dependency_local_key=artist_dependency_local_key,
            artist_dependency_id=artist_dependency_id,
        )
        self._ledger.register(request)
        return request

    # ------------------------------------------------------------------
    # ARTIST ENRICHMENT
    # ------------------------------------------------------------------

    def request_artist_enrichment(
        self,
        evidence: ArtistIdentityEvidence,
        generation: int = 0,
    ) -> EnrichmentRequestOutcome:
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
            return self._short_circuit_artist(existing, generation)

        # RESOLUTION (no authority lock, no authority mutation).
        if current_hints:
            resolution = resolve_artist_identity((), evidence)
        else:
            candidates = self._resolver.find_artist_candidates(evidence)
            resolution = resolve_artist_identity(candidates, evidence)

        # AUTHORITY COMMIT GATE (R1.2): short locked section — generation
        # gate, identity transition, exact request registration.
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ARTIST, local_key, generation
            ):
                # R1.2: a stale worker can never mutate authority here.
                return EnrichmentRequestOutcome(
                    resolution=IdentityResolution(
                        status=IdentityResolutionStatus.SUPERSEDED
                    ),
                    request=None,
                )
            if resolution.status is not IdentityResolutionStatus.RESOLVED:
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
            request = self._register_locked(
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
        """R1.2: the WHOLE validation+commit is one authority transaction
        (generation gate, exact-request check, identity check, ledger
        consumption, knowledge persistence) — serialized against manual
        identity changes and reset."""
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        if profile.external_artist_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_artist_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ARTIST,
                request.local_entity_key,
                request.generation,
            ):
                return DeliveryVerdict.STALE
            current = self._identity_repository.load_artist_identity(
                request.local_entity_key
            )
            if (
                current is None
                or current.external_artist_id != request.external_entity_id
            ):
                return DeliveryVerdict.STALE
            verdict = self._ledger.deliver(request)
            if verdict is not DeliveryVerdict.COMMITTED:
                return verdict
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
        if request.entity_kind is not EnrichmentEntityKind.ARTIST:
            return DeliveryVerdict.MISMATCHED
        with self._authority_lock:
            return self._ledger.deliver(request)

    def cancel_request_exact(self, request: EnrichmentRequest) -> bool:
        """R1.2: invalidate EXACTLY this request (request_id +
        generation) — a stale worker can never cancel a newer one."""
        with self._authority_lock:
            return self._ledger.invalidate_if_current(
                request.entity_kind,
                request.local_entity_key,
                request.request_id,
                request.generation,
            )

    # ------------------------------------------------------------------
    # ALBUM ENRICHMENT
    # ------------------------------------------------------------------

    def request_album_enrichment(
        self,
        evidence: AlbumIdentityEvidence,
        generation: int = 0,
    ) -> EnrichmentRequestOutcome:
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
            return self._short_circuit_album(existing, generation)
        if (
            existing is not None
            and existing.match_method is MatchMethod.EMBEDDED_HINT
            and not current_rg_hints
            and current_release_hints
        ):
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

        # RESOLUTION (no authority lock).
        if current_rg_hints:
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

        # AUTHORITY COMMIT GATE.
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ALBUM, local_key, generation
            ):
                return EnrichmentRequestOutcome(
                    resolution=AlbumIdentityResolution(
                        status=IdentityResolutionStatus.SUPERSEDED
                    ),
                    request=None,
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
            request = self._register_locked(
                EnrichmentEntityKind.ALBUM,
                local_key,
                resolution.release_group_id,
                resolution.release_id,
                generation,
                evidence.local_album_artist_key,
                evidence.resolved_artist_external_id,
            )
            return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def _refine_embedded_album_release(
        self,
        existing: AlbumExternalIdentity,
        evidence: AlbumIdentityEvidence,
        generation: int,
    ) -> EnrichmentRequestOutcome:
        from michi.domain.enrichment import resolve_release_hint_for_group

        hints = dedupe_identity_ids(evidence.identity_hints.release_ids)
        if len(hints) > 1:
            with self._authority_lock:
                if self._is_current_locked(
                    EnrichmentEntityKind.ALBUM,
                    existing.local_album_key,
                    generation,
                ):
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
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ALBUM, existing.local_album_key, generation
            ):
                return EnrichmentRequestOutcome(
                    resolution=AlbumIdentityResolution(
                        status=IdentityResolutionStatus.SUPERSEDED
                    ),
                    request=None,
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
            request = self._register_locked(
                EnrichmentEntityKind.ALBUM,
                existing.local_album_key,
                existing.release_group_id,
                release_id,
                generation,
                evidence.local_album_artist_key,
                evidence.resolved_artist_external_id,
            )
            return EnrichmentRequestOutcome(resolution=resolution, request=request)

    def deliver_album_profile(
        self, request: EnrichmentRequest, profile: AlbumKnowledgeProfile
    ) -> DeliveryVerdict:
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        if profile.release_group_id != request.external_entity_id:
            return DeliveryVerdict.MISMATCHED
        if profile.release_id != request.external_variant_id:
            return DeliveryVerdict.MISMATCHED
        if profile.local_album_key != request.local_entity_key:
            return DeliveryVerdict.MISMATCHED
        with self._authority_lock:
            if not self._is_current_locked(
                EnrichmentEntityKind.ALBUM,
                request.local_entity_key,
                request.generation,
            ):
                return DeliveryVerdict.STALE
            current = self._identity_repository.load_album_identity(
                request.local_entity_key
            )
            if (
                current is None
                or current.release_group_id != request.external_entity_id
                or current.release_id != request.external_variant_id
            ):
                return DeliveryVerdict.STALE
            if request.artist_dependency_id:
                # R1.3 FIX-07: the album actually resolved through its
                # artist identity at request time (a non-empty dependency
                # id) — revalidate under the authority lock. If the
                # artist identity was reset or re-confirmed since, this
                # result is stale (zero writes). A dependency key without
                # a captured id played no part in resolution and is not
                # enforced.
                artist_identity = self._identity_repository.load_artist_identity(
                    request.artist_dependency_local_key
                )
                if (
                    artist_identity is None
                    or artist_identity.external_artist_id
                    != request.artist_dependency_id
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
        if request.entity_kind is not EnrichmentEntityKind.ALBUM:
            return DeliveryVerdict.MISMATCHED
        with self._authority_lock:
            return self._ledger.deliver(request)

    # ------------------------------------------------------------------
    # MANUAL IDENTITY AUTHORITY (serialized against delivery)
    # ------------------------------------------------------------------

    def confirm_artist_identity(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistExternalIdentity:
        """R1.3 MANUAL AUTHORITY BARRIER: under the same authority lock,
        the current generation epoch is advanced (every in-flight
        automatic operation becomes SUPERSEDED), the same-generation
        pending request is invalidated, and the MANUAL identity is
        persisted. MANUAL can never be downgraded by a late AUTO/
        EMBEDDED operation."""
        identity = ArtistExternalIdentity(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        with self._authority_lock:
            self._bump_generation_locked(
                EnrichmentEntityKind.ARTIST, local_artist_key
            )
            self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
            self._persist_artist_identity_transition(identity)
        return identity

    def reset_artist_identity(self, local_artist_key: str) -> None:
        """R1.3 RESET BARRIER: advance the epoch and invalidate the
        same-generation request under the lock — an old worker can never
        resurrect identity/request/knowledge after a reset."""
        with self._authority_lock:
            self._bump_generation_locked(
                EnrichmentEntityKind.ARTIST, local_artist_key
            )
            self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
            self._identity_repository.delete_artist_identity(local_artist_key)
            self._repository.delete_artist_profile(local_artist_key)

    def confirm_album_identity(
        self,
        local_album_key: str,
        release_group_id: str,
        release_id: str = "",
    ) -> AlbumExternalIdentity:
        """R1.3 MANUAL ALBUM BARRIER (same semantics as the artist one —
        the exact manual release tuple can never be replaced by a late
        automatic operation)."""
        identity = AlbumExternalIdentity(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        with self._authority_lock:
            self._bump_generation_locked(
                EnrichmentEntityKind.ALBUM, local_album_key
            )
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
            self._persist_album_identity_transition(identity)
        return identity

    def reset_album_identity(self, local_album_key: str) -> None:
        with self._authority_lock:
            self._bump_generation_locked(
                EnrichmentEntityKind.ALBUM, local_album_key
            )
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
            self._identity_repository.delete_album_identity(local_album_key)
            self._repository.delete_album_profile(local_album_key)

    def clear_identities(self) -> None:
        """R1.3 GLOBAL AUTHORITY BARRIER: every known entity's epoch is
        advanced (no generation can ever commit again), all pending
        requests are invalidated, then identity + knowledge are cleared.
        The generation dict is NEVER cleared — monotonicity is kept for
        the Service lifetime."""
        with self._authority_lock:
            for key in list(self._operation_generations):
                entity_kind, local_entity_key = key
                self._bump_generation_locked(entity_kind, local_entity_key)
            self._ledger.invalidate_all()
            self._identity_repository.clear_identities()
            self._repository.clear_knowledge()

    # ------------------------------------------------------------------
    # CLEAR / READ / INTENT SURFACE
    # ------------------------------------------------------------------

    def clear_knowledge(self) -> None:
        with self._authority_lock:
            self._repository.clear_knowledge()

    def clear_artist_knowledge(self, local_artist_key: str) -> None:
        with self._authority_lock:
            self._repository.delete_artist_profile(local_artist_key)

    def clear_album_knowledge(self, local_album_key: str) -> None:
        with self._authority_lock:
            self._repository.delete_album_profile(local_album_key)

    def get_artist_knowledge(
        self, local_artist_key: str
    ) -> ArtistKnowledgeProfile | None:
        try:
            identity = self._identity_repository.load_artist_identity(local_artist_key)
            if identity is None:
                return None
            profile = self._repository.load_artist_profile(local_artist_key)
        except EnrichmentStorageError:
            return None
        if profile is None or profile.external_artist_id != identity.external_artist_id:
            return None
        return profile

    def get_album_knowledge(self, local_album_key: str) -> AlbumKnowledgeProfile | None:
        try:
            identity = self._identity_repository.load_album_identity(local_album_key)
            if identity is None:
                return None
            profile = self._repository.load_album_profile(local_album_key)
        except EnrichmentStorageError:
            return None
        if profile is None:
            return None
        if profile.release_group_id != identity.release_group_id:
            return None
        if profile.release_id != identity.release_id:
            return None
        return profile

    def pending_count(self) -> int:
        return self._ledger.pending_count()
