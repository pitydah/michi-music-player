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

    def begin_operation(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        generation: int,
    ) -> None:
        """Record ``generation`` as the current productive authority for
        the entity (monotonic: a higher generation always wins)."""
        with self._authority_lock:
            key = (entity_kind, local_entity_key)
            current = self._operation_generations.get(key, 0)
            self._operation_generations[key] = max(current, generation)

    def cancel_operation(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        generation: int,
    ) -> None:
        """Make ``generation`` non-current. Only affects the generation
        that IS currently authorized — never a newer one (no-op for a
        superseded generation)."""
        with self._authority_lock:
            key = (entity_kind, local_entity_key)
            if self._operation_generations.get(key) == generation:
                self._operation_generations[key] = generation + 1

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
        identity = ArtistExternalIdentity(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        with self._authority_lock:
            self._persist_artist_identity_transition(identity)
        return identity

    def reset_artist_identity(self, local_artist_key: str) -> None:
        with self._authority_lock:
            self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)
            self._identity_repository.delete_artist_identity(local_artist_key)
            self._repository.delete_artist_profile(local_artist_key)

    def confirm_album_identity(
        self,
        local_album_key: str,
        release_group_id: str,
        release_id: str = "",
    ) -> AlbumExternalIdentity:
        identity = AlbumExternalIdentity(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            status=IdentityStatus.RESOLVED,
            match_method=MatchMethod.MANUAL,
            resolved_at=_utc_now_iso(),
        )
        with self._authority_lock:
            self._persist_album_identity_transition(identity)
        return identity

    def reset_album_identity(self, local_album_key: str) -> None:
        with self._authority_lock:
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)
            self._identity_repository.delete_album_identity(local_album_key)
            self._repository.delete_album_profile(local_album_key)

    def clear_identities(self) -> None:
        with self._authority_lock:
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

    def cancel_artist_request(self, local_artist_key: str) -> None:
        """Legacy key-scoped intent (kept for compatibility): invalidates
        the CURRENT request of the entity. Exact per-request invalidation
        is ``cancel_request_exact`` — stale workers must use that."""
        with self._authority_lock:
            self._ledger.invalidate(EnrichmentEntityKind.ARTIST, local_artist_key)

    def cancel_album_request(self, local_album_key: str) -> None:
        with self._authority_lock:
            self._ledger.invalidate(EnrichmentEntityKind.ALBUM, local_album_key)

    def cancel_all_requests(self) -> None:
        with self._authority_lock:
            self._ledger.invalidate_all()

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
