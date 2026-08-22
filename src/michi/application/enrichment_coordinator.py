"""Enrichment orchestration (M6.9F + M6.9-BACKEND-R1).

The coordinator owns the provider WORKFLOW (evidence -> identity ->
knowledge -> assets -> delivery) while EnrichmentService remains the
identity/commit authority. It never owns canonical library metadata,
never runs network on the caller's thread (all work is submitted to the
executor), and reports EPHEMERAL operation states that are never
persisted as identity and never stored inside knowledge profiles.

R1 CANCELLATION MODEL (per-operation, race-safe):
- every operation carries an immutable ``EnrichmentOperationToken``
  (operation_id / entity_kind / local_entity_key / cancelled state);
- a new operation on the same entity SUPERSEDES the previous one;
- ``cancel_all()`` cancels ACTIVE operations only — the coordinator
  stays fully reusable afterwards;
- ``shutdown()`` is TERMINAL: freeze new work, cancel active
  operations, invalidate pending requests and join the executor;
- cancellation is checked before resolution, after resolution, before
  every remote phase, after expensive provider calls, before asset
  store and IMMEDIATELY before delivery — a cancelled operation never
  commits knowledge.
"""

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum, auto

from michi.application.enrichment_evidence import LibraryEnrichmentEvidenceBuilder
from michi.application.enrichment_ports import (
    ArtistExternalLinks,
    CoverArtArchiveProviderPort,
    EnrichmentAssetStorePort,
    EnrichmentExecutorPort,
    EnrichmentHttpStatusError,
    EnrichmentProviderError,
    ExternalIdentityResolverPort,
    HttpRequest,
    HttpTransportPort,
    MusicBrainzKnowledgeProviderPort,
    WikidataKnowledgeProviderPort,
    WikimediaCommonsProviderPort,
    WikipediaBiographyProviderPort,
)
from michi.application.enrichment_service import EnrichmentService
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    DeliveryVerdict,
    EnrichmentAssetRecord,
    EnrichmentEntityKind,
    IdentityResolutionStatus,
    KnowledgeProvenance,
)
from michi.domain.library import AlbumRef, ArtistRef, TrackRef

logger = logging.getLogger(__name__)


class EnrichmentOperationState(Enum):
    """Ephemeral operation states (never persisted as identity)."""

    IDLE = auto()
    DISABLED = auto()
    RESOLVING_IDENTITY = auto()
    AMBIGUOUS = auto()
    NOT_FOUND = auto()
    FETCHING_KNOWLEDGE = auto()
    READY = auto()
    PARTIAL = auto()
    OFFLINE = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass(frozen=True)
class ArtistIdentityCandidateView:
    """User-decision projection (never raw provider JSON)."""

    external_artist_id: str
    display_name: str
    disambiguation: str
    provider: str = "musicbrainz"


@dataclass(frozen=True)
class AlbumIdentityCandidateView:
    external_release_group_id: str
    display_title: str
    artist_credit: str
    year: int
    provider: str = "musicbrainz"


class EnrichmentOperationToken:
    """R1 per-operation cancellation state (application-only, never
    persisted, never identity)."""

    def __init__(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> None:
        self.operation_id = uuid.uuid4().hex
        self.entity_kind = entity_kind
        self.local_entity_key = local_entity_key
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()


StateCallback = Callable[[str, EnrichmentOperationState], None]
CandidateCallback = Callable[
    [tuple[ArtistIdentityCandidateView | AlbumIdentityCandidateView, ...]], None
]


class EnrichmentCoordinator:
    """Provider workflow orchestration with offline-safe partials."""

    def __init__(
        self,
        service: EnrichmentService,
        resolver: ExternalIdentityResolverPort,
        evidence_builder: LibraryEnrichmentEvidenceBuilder,
        mb_knowledge: MusicBrainzKnowledgeProviderPort,
        wikidata: WikidataKnowledgeProviderPort | None,
        wikipedia: WikipediaBiographyProviderPort | None,
        commons: WikimediaCommonsProviderPort | None,
        coverart: CoverArtArchiveProviderPort | None,
        asset_store: EnrichmentAssetStorePort | None,
        executor: EnrichmentExecutorPort,
        transport: HttpTransportPort | None,
        enabled: Callable[[], bool],
    ) -> None:
        self._service = service
        self._resolver = resolver
        self._evidence_builder = evidence_builder
        self._mb = mb_knowledge
        self._wikidata = wikidata
        self._wikipedia = wikipedia
        self._commons = commons
        self._coverart = coverart
        self._assets = asset_store
        self._executor = executor
        self._transport = transport
        self._enabled = enabled
        self._operations: dict[
            tuple[EnrichmentEntityKind, str], EnrichmentOperationToken
        ] = {}
        self._lock = threading.Lock()
        self._shutting_down = False

    # -- operation registry (R1) ---------------------------------------------

    def _begin_operation(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> EnrichmentOperationToken | None:
        """Register the current operation for an entity; a NEW operation
        supersedes (cancels) the previous one. Returns None when the
        coordinator is shutting down."""
        token = EnrichmentOperationToken(entity_kind, local_entity_key)
        with self._lock:
            if self._shutting_down:
                return None
            key = (entity_kind, local_entity_key)
            previous = self._operations.get(key)
            if previous is not None:
                previous.cancel()  # supersession
            self._operations[key] = token
        return token

    def _end_operation(self, token: EnrichmentOperationToken) -> None:
        with self._lock:
            key = (token.entity_kind, token.local_entity_key)
            current = self._operations.get(key)
            if current is token:
                del self._operations[key]

    # -- public intents ------------------------------------------------------

    def enrich_artist(
        self,
        artist: ArtistRef,
        albums: tuple[AlbumRef, ...],
        tracks: tuple[TrackRef, ...],
        on_state: StateCallback | None = None,
    ) -> None:
        if not self._enabled():
            self._report(on_state, artist.key, EnrichmentOperationState.DISABLED)
            return
        token = self._begin_operation(EnrichmentEntityKind.ARTIST, artist.key)
        if token is None:
            self._report(on_state, artist.key, EnrichmentOperationState.CANCELLED)
            return
        self._executor.submit(
            lambda: self._run_artist(token, artist, albums, tracks, on_state)
        )

    def enrich_album(
        self,
        album: AlbumRef,
        resolved_artist_external_id: str = "",
        on_state: StateCallback | None = None,
    ) -> None:
        if not self._enabled():
            self._report(on_state, album.key, EnrichmentOperationState.DISABLED)
            return
        token = self._begin_operation(EnrichmentEntityKind.ALBUM, album.key)
        if token is None:
            self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
            return
        self._executor.submit(
            lambda: self._run_album(token, album, resolved_artist_external_id, on_state)
        )

    def refresh_artist_enrichment(
        self,
        artist: ArtistRef,
        albums: tuple[AlbumRef, ...],
        tracks: tuple[TrackRef, ...],
        on_state: StateCallback | None = None,
    ) -> None:
        self.enrich_artist(artist, albums, tracks, on_state)

    def refresh_album_enrichment(
        self,
        album: AlbumRef,
        resolved_artist_external_id: str = "",
        on_state: StateCallback | None = None,
    ) -> None:
        self.enrich_album(album, resolved_artist_external_id, on_state)

    def cancel_artist(self, local_artist_key: str) -> None:
        """Cancel the ACTIVE artist operation (superseded by design)."""
        with self._lock:
            token = self._operations.get(
                (EnrichmentEntityKind.ARTIST, local_artist_key)
            )
        if token is not None:
            token.cancel()
        self._service.cancel_artist_request(local_artist_key)

    def cancel_album(self, local_album_key: str) -> None:
        with self._lock:
            token = self._operations.get((EnrichmentEntityKind.ALBUM, local_album_key))
        if token is not None:
            token.cancel()
        self._service.cancel_album_request(local_album_key)

    def cancel_all(self) -> None:
        """Cancel ACTIVE operations only — the coordinator remains fully
        reusable afterwards."""
        with self._lock:
            tokens = list(self._operations.values())
        for token in tokens:
            token.cancel()
        self._service.cancel_all_requests()

    def shutdown(self) -> None:
        """TERMINAL: freeze new work, cancel active operations,
        invalidate pending requests and join the executor."""
        with self._lock:
            self._shutting_down = True
            tokens = list(self._operations.values())
        for token in tokens:
            token.cancel()
        self._service.cancel_all_requests()
        self._executor.shutdown(wait=True)

    def clear_artist_knowledge(self, local_artist_key: str) -> None:
        self._service.clear_artist_knowledge(local_artist_key)

    def clear_album_knowledge(self, local_album_key: str) -> None:
        self._service.clear_album_knowledge(local_album_key)

    def reset_artist_identity(self, local_artist_key: str) -> None:
        self._service.reset_artist_identity(local_artist_key)

    def reset_album_identity(self, local_album_key: str) -> None:
        self._service.reset_album_identity(local_album_key)

    # -- manual search (R1: ALWAYS off the caller's thread) -------------------

    def search_artist_candidates_async(
        self,
        artist_name: str,
        on_result: CandidateCallback,
    ) -> None:
        """R1: manual candidate search runs on the enrichment executor —
        the caller is never blocked by network work."""
        self._executor.submit(
            lambda: on_result(self._search_artist_candidates_sync(artist_name))
        )

    def search_album_candidates_async(
        self,
        album_title: str,
        artist_name: str,
        on_result: CandidateCallback,
    ) -> None:
        self._executor.submit(
            lambda: on_result(
                self._search_album_candidates_sync(album_title, artist_name)
            )
        )

    def _search_artist_candidates_sync(
        self, artist_name: str
    ) -> tuple[ArtistIdentityCandidateView, ...]:
        """INTERNAL (executor thread): results NEVER become identity."""
        if not self._enabled():
            return ()
        evidence = ArtistIdentityEvidence(
            local_artist_key="", local_artist_name=artist_name
        )
        candidates = self._resolver.find_artist_candidates(evidence)
        return tuple(
            ArtistIdentityCandidateView(
                external_artist_id=c.external_artist_id,
                display_name=c.canonical_name,
                disambiguation=c.disambiguation,
            )
            for c in candidates
        )

    def _search_album_candidates_sync(
        self, album_title: str, artist_name: str
    ) -> tuple[AlbumIdentityCandidateView, ...]:
        if not self._enabled():
            return ()
        evidence = AlbumIdentityEvidence(
            local_album_key="",
            local_album_title=album_title,
            local_album_artist_name=artist_name,
        )
        candidates = self._resolver.find_release_group_candidates(evidence)
        return tuple(
            AlbumIdentityCandidateView(
                external_release_group_id=c.release_group_id,
                display_title=c.title,
                artist_credit=", ".join(c.artist_credit_names),
                year=c.first_release_year,
            )
            for c in candidates
        )

    def confirm_artist_identity(
        self, local_artist_key: str, external_artist_id: str
    ) -> None:
        self._service.confirm_artist_identity(local_artist_key, external_artist_id)

    def confirm_album_identity(
        self, local_album_key: str, release_group_id: str, release_id: str = ""
    ) -> None:
        self._service.confirm_album_identity(
            local_album_key, release_group_id, release_id
        )

    # -- artist workflow -------------------------------------------------------

    def _run_artist(
        self,
        token: EnrichmentOperationToken,
        artist: ArtistRef,
        albums: tuple[AlbumRef, ...],
        tracks: tuple[TrackRef, ...],
        on_state: StateCallback | None,
    ) -> None:
        try:
            if self._gate_cancelled(
                token, artist.key, None, on_state, cancel_artist=True
            ):
                return
            self._report(
                on_state, artist.key, EnrichmentOperationState.RESOLVING_IDENTITY
            )
            evidence = self._evidence_builder.artist_evidence(artist, albums, tracks)
            outcome = self._service.request_artist_enrichment(evidence)
            if self._gate_cancelled(
                token, artist.key, outcome.request, on_state, cancel_artist=True
            ):
                return
            if outcome.request is None:
                state = {
                    IdentityResolutionStatus.AMBIGUOUS: (
                        EnrichmentOperationState.AMBIGUOUS
                    ),
                    IdentityResolutionStatus.IDENTITY_CONFLICT: (
                        EnrichmentOperationState.AMBIGUOUS
                    ),
                    IdentityResolutionStatus.NO_MATCH: (
                        EnrichmentOperationState.NOT_FOUND
                    ),
                }.get(outcome.resolution.status, EnrichmentOperationState.FAILED)
                self._report(on_state, artist.key, state)
                return
            request = outcome.request
            external_id = request.external_entity_id
            local_key = request.local_entity_key
            self._report(
                on_state, artist.key, EnrichmentOperationState.FETCHING_KNOWLEDGE
            )
            if self._gate_cancelled(token, artist.key, request, on_state):
                return

            partial = False
            try:
                profile = self._mb.fetch_artist(local_key, external_id)
            except EnrichmentProviderError as exc:
                self._service.deliver_artist_failure(request)
                self._report_failure(on_state, artist.key, exc)
                return
            if self._gate_cancelled(token, artist.key, request, on_state):
                return
            try:
                links = self._mb.artist_links(external_id)
            except EnrichmentProviderError:
                links = ArtistExternalLinks()
                partial = True
            profile, partial = self._apply_artist_links(profile, links, partial)
            if self._gate_cancelled(token, artist.key, request, on_state):
                return
            profile, partial = self._apply_biography(profile, links, partial)
            if self._gate_cancelled(token, artist.key, request, on_state):
                return
            profile, partial = self._apply_artist_image(profile, external_id, partial)
            if self._gate_cancelled(token, artist.key, request, on_state):
                return
            # R1: IMMEDIATELY before delivery — a cancelled operation
            # never commits knowledge.
            verdict = self._service.deliver_artist_profile(request, profile)
            if verdict is DeliveryVerdict.COMMITTED:
                stale = (
                    profile.provenance.is_stale or profile.biography_provenance.is_stale
                )
                self._report(
                    on_state,
                    artist.key,
                    EnrichmentOperationState.PARTIAL
                    if (partial or stale)
                    else EnrichmentOperationState.READY,
                )
            else:
                self._report(on_state, artist.key, EnrichmentOperationState.FAILED)
        finally:
            self._end_operation(token)

    def _gate_cancelled(
        self,
        token: EnrichmentOperationToken,
        local_key: str,
        request,
        on_state: StateCallback | None,
        cancel_artist: bool = False,
    ) -> bool:
        """R1 gate: True when the operation was cancelled. Invalidates the
        pending request and reports CANCELLED — ZERO knowledge commit."""
        if not token.cancelled:
            return False
        self._service.cancel_artist_request(local_key)
        self._report(on_state, local_key, EnrichmentOperationState.CANCELLED)
        return True

    def _apply_artist_links(
        self, profile: ArtistKnowledgeProfile, links: ArtistExternalLinks, partial: bool
    ) -> tuple[ArtistKnowledgeProfile, bool]:
        merged = replace(
            profile,
            wikipedia_page_title=links.wikipedia_title,
            wikipedia_language=links.wikipedia_language,
        )
        if self._wikidata is None or not links.wikidata_qid:
            return merged, partial
        try:
            claims = self._wikidata.fetch_artist_claims(links.wikidata_qid)
        except EnrichmentProviderError:
            return merged, True
        sitelink_title = links.wikipedia_title or claims.wikipedia_title
        sitelink_lang = links.wikipedia_language or claims.wikipedia_language
        return (
            replace(
                merged,
                wikipedia_page_title=sitelink_title or merged.wikipedia_page_title,
                wikipedia_language=sitelink_lang or merged.wikipedia_language,
                country_qid=claims.country_qid,
                country_label=claims.country_label,
                official_website=claims.official_website or merged.official_website,
                commons_image_title=(
                    claims.commons_image_title or merged.commons_image_title
                ),
                wikidata_begin_year=claims.begin_year,
                wikidata_end_year=claims.end_year,
                wikidata_provenance=KnowledgeProvenance(
                    provider="wikidata",
                    external_entity_id=links.wikidata_qid,
                    retrieved_at=claims.retrieved_at,
                    is_stale=claims.is_stale,
                ),
            ),
            partial or claims.is_stale,
        )

    def _apply_biography(
        self, profile: ArtistKnowledgeProfile, links: ArtistExternalLinks, partial: bool
    ) -> tuple[ArtistKnowledgeProfile, bool]:
        if self._wikipedia is None or not links.wikipedia_title:
            return profile, partial
        try:
            bio = self._wikipedia.fetch_biography(
                links.wikipedia_title, links.wikipedia_language
            )
        except EnrichmentProviderError:
            return profile, True
        if not bio.text:
            # R1 (P2-02): a verified page without biography is an empty
            # OPTIONAL result — PARTIAL, never FAILED.
            return profile, True
        return (
            replace(
                profile,
                biography=bio.text,
                biography_provenance=KnowledgeProvenance(
                    provider="wikipedia",
                    external_entity_id=links.wikipedia_title,
                    source_url=bio.source_url,
                    language=bio.language,
                    license=bio.license,
                    attribution=bio.attribution,
                    retrieved_at=bio.retrieved_at,
                    is_stale=bio.is_stale,
                ),
            ),
            partial or bio.is_stale,
        )

    def _apply_artist_image(
        self, profile: ArtistKnowledgeProfile, external_id: str, partial: bool
    ) -> tuple[ArtistKnowledgeProfile, bool]:
        if self._commons is None or not profile.commons_image_title:
            return profile, partial
        if self._assets is None or self._transport is None:
            return profile, partial
        try:
            image = self._commons.fetch_image(profile.commons_image_title)
            if not image.source_url:
                return profile, True  # optional image missing
            response = self._transport.get(HttpRequest(url=image.source_url))
        except (EnrichmentProviderError, ValueError):
            return profile, True
        record = EnrichmentAssetRecord(
            asset_id=f"artist-{external_id}",
            entity_kind=EnrichmentEntityKind.ARTIST,
            external_entity_id=external_id,
            mime_type=self._declared_mime(response),
            provider="wikimedia-commons",
            source_url=image.source_url,
            creator=image.artist,
            license=image.license,
            license_url=image.license_url,
            attribution=image.attribution,
        )
        stored = self._assets.store(record, response.body)
        if stored is None:
            return profile, True
        return replace(profile, artwork_asset_id=stored.asset_id), partial

    # -- album workflow -------------------------------------------------------

    def _run_album(
        self,
        token: EnrichmentOperationToken,
        album: AlbumRef,
        resolved_artist_external_id: str,
        on_state: StateCallback | None,
    ) -> None:
        try:
            if token.cancelled:
                self._service.cancel_album_request(album.key)
                self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
                return
            self._report(
                on_state, album.key, EnrichmentOperationState.RESOLVING_IDENTITY
            )
            evidence = self._evidence_builder.album_evidence(
                album, resolved_artist_external_id
            )
            outcome = self._service.request_album_enrichment(evidence)
            if token.cancelled:
                self._service.cancel_album_request(album.key)
                self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
                return
            if outcome.request is None:
                state = {
                    IdentityResolutionStatus.AMBIGUOUS: (
                        EnrichmentOperationState.AMBIGUOUS
                    ),
                    IdentityResolutionStatus.IDENTITY_CONFLICT: (
                        EnrichmentOperationState.AMBIGUOUS
                    ),
                    IdentityResolutionStatus.NO_MATCH: (
                        EnrichmentOperationState.NOT_FOUND
                    ),
                }.get(outcome.resolution.status, EnrichmentOperationState.FAILED)
                self._report(on_state, album.key, state)
                return
            request = outcome.request
            self._report(
                on_state, album.key, EnrichmentOperationState.FETCHING_KNOWLEDGE
            )
            if token.cancelled:
                self._service.cancel_album_request(album.key)
                self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
                return
            partial = False
            try:
                profile = self._mb.fetch_release_group(
                    request.local_entity_key,
                    request.external_entity_id,
                    request.external_variant_id,
                )
            except EnrichmentProviderError as exc:
                self._service.deliver_album_failure(request)
                self._report_failure(on_state, album.key, exc)
                return
            if token.cancelled:
                self._service.cancel_album_request(album.key)
                self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
                return
            profile, partial = self._apply_cover(profile, partial)
            if token.cancelled:
                self._service.cancel_album_request(album.key)
                self._report(on_state, album.key, EnrichmentOperationState.CANCELLED)
                return
            verdict = self._service.deliver_album_profile(request, profile)
            if verdict is DeliveryVerdict.COMMITTED:
                self._report(
                    on_state,
                    album.key,
                    EnrichmentOperationState.PARTIAL
                    if (partial or profile.provenance.is_stale)
                    else EnrichmentOperationState.READY,
                )
            else:
                self._report(on_state, album.key, EnrichmentOperationState.FAILED)
        finally:
            self._end_operation(token)

    def _apply_cover(
        self, profile: AlbumKnowledgeProfile, partial: bool
    ) -> tuple[AlbumKnowledgeProfile, bool]:
        if self._coverart is None or self._assets is None or self._transport is None:
            return profile, partial
        try:
            cover = self._coverart.fetch_cover(
                release_id=profile.release_id,
                release_group_id=profile.release_group_id,
            )
            if not cover.image_url:
                return profile, True  # optional cover missing
            response = self._transport.get(HttpRequest(url=cover.image_url))
        except (EnrichmentProviderError, ValueError):
            return profile, True
        entity_id = profile.release_id or profile.release_group_id
        record = EnrichmentAssetRecord(
            asset_id=f"album-{entity_id}",
            entity_kind=EnrichmentEntityKind.ALBUM,
            external_entity_id=entity_id,
            mime_type=self._declared_mime(response),
            provider="coverartarchive",
            source_url=cover.image_url,
        )
        stored = self._assets.store(record, response.body)
        if stored is None:
            return profile, True
        return replace(profile, artwork_asset_id=stored.asset_id), partial

    # -- helpers ----------------------------------------------------------------

    @staticmethod
    def _declared_mime(response) -> str:
        """R1 (P1-11): normalize Content-Type; pass ONLY a supported
        image MIME as the declared hint, else "" (sniff decides)."""
        raw = response.headers.get("content-type", "")
        mime = raw.split(";", 1)[0].strip().lower()
        if mime in {"image/jpeg", "image/png", "image/webp"}:
            return mime
        return ""

    @staticmethod
    def _report(
        on_state: StateCallback | None, key: str, state: EnrichmentOperationState
    ) -> None:
        if on_state is not None:
            on_state(key, state)

    @staticmethod
    def _report_failure(
        on_state: StateCallback | None, key: str, exc: EnrichmentProviderError
    ) -> None:
        if isinstance(exc, EnrichmentHttpStatusError):
            EnrichmentCoordinator._report(
                on_state, key, EnrichmentOperationState.FAILED
            )
        else:
            EnrichmentCoordinator._report(
                on_state, key, EnrichmentOperationState.OFFLINE
            )
