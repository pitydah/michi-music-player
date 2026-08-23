"""Enrichment orchestration (M6.9F + BACKEND-R1 + R1.1).

The coordinator owns the provider WORKFLOW (evidence -> identity ->
knowledge -> assets -> delivery) while EnrichmentService remains the
identity/commit authority.

R1.1 additions:

- EXCEPTION BOUNDARY: the whole ``_run_artist`` / ``_run_album`` body
  (INCLUDING identity resolution) converges to a terminal state:
  transient failures -> OFFLINE; other provider/HTTP failures ->
  FAILED; unexpected programming errors are logged and FAILED — a
  worker Future can never die silently leaving the observer stuck.
- LINEARIZABLE DELIVERY: the final commit is serialized against
  cancel/supersede/shutdown under the coordinator lock (the network
  phases never hold it). If cancellation wins first the operation
  cannot deliver; if delivery wins first it completes exactly once.
- STALE TRUTH: stale knowledge from ANY provider (MB links, Commons,
  CAA, Wikipedia, Wikidata) marks the final state PARTIAL — never
  READY; stale identity resolution remains impossible.
- WIKIPEDIA FALLBACK: the biography fetch uses the FINAL projected
  page/language (MusicBrainz relation, else verified Wikidata
  sitelink) — never a name search.
- ASYNC SEARCH: submission is controlled (returns False after
  shutdown, never raises RuntimeError); provider failures surface via
  an error callback — never as an empty success.
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
    EnrichmentProviderError,
    ExternalIdentityResolverPort,
    HttpRequest,
    HttpTransportPort,
    MusicBrainzKnowledgeProviderPort,
    WikidataKnowledgeProviderPort,
    WikimediaCommonsProviderPort,
    WikipediaBiographyProviderPort,
    is_transient_provider_failure,
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


@dataclass(frozen=True)
class EnrichmentOperationEvent:
    """R1.2 typed, operation-correlated state event (application-only,
    never persisted, never identity). The future Presentation bridge
    filters by generation: any event belonging to an older generation is
    STALE by definition."""

    operation_id: str
    generation: int
    entity_kind: EnrichmentEntityKind
    local_entity_key: str
    state: EnrichmentOperationState


class EnrichmentOperationToken:
    """R1/R1.2 per-operation cancellation + generation state."""

    def __init__(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        generation: int,
    ) -> None:
        self.operation_id = uuid.uuid4().hex
        self.entity_kind = entity_kind
        self.local_entity_key = local_entity_key
        self.generation = generation
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()


StateCallback = Callable[[EnrichmentOperationEvent], None]
ResultCallback = Callable[[tuple], None]
ErrorCallback = Callable[[EnrichmentProviderError], None]


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
        # R1.2: reentrant — inline executors run work inside the
        # submission scope; service calls never take this lock.
        self._lock = threading.RLock()
        self._shutting_down = False

    # -- operation registry (R1.2: monotonic generations) ----------------------

    def _begin_operation(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> EnrichmentOperationToken | None:
        with self._lock:
            if self._shutting_down:
                return None
            key = (entity_kind, local_entity_key)
            previous = self._operations.get(key)
            if previous is not None:
                previous.cancel()
            self._operations[key] = None  # placeholder; replaced below
        # R1.3: THE SERVICE is the sole generation authority.
        generation = self._service.begin_operation(entity_kind, local_entity_key)
        token = EnrichmentOperationToken(entity_kind, local_entity_key, generation)
        with self._lock:
            self._operations[key] = token
        return token

    def _end_operation(self, token: EnrichmentOperationToken) -> None:
        with self._lock:
            key = (token.entity_kind, token.local_entity_key)
            current = self._operations.get(key)
            if current is token:
                del self._operations[key]

    def _current_token(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> EnrichmentOperationToken | None:
        with self._lock:
            return self._operations.get((entity_kind, local_entity_key))

    # -- public intents ---------------------------------------------------------

    def enrich_artist(
        self,
        artist: ArtistRef,
        albums: tuple[AlbumRef, ...],
        tracks: tuple[TrackRef, ...],
        on_state: StateCallback | None = None,
    ) -> None:
        if not self._enabled():
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ARTIST,
                artist.key,
                EnrichmentOperationState.DISABLED,
            )
            return
        token = self._begin_operation(EnrichmentEntityKind.ARTIST, artist.key)
        if token is None:
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ARTIST,
                artist.key,
                EnrichmentOperationState.CANCELLED,
            )
            return
        if not self._submit_if_running(
            lambda: self._run_artist(token, artist, albums, tracks, on_state)
        ):
            # R1.3: submission rejected (executor closed) — retire this
            # generation, remove the token, publish CANCELLED.
            self._retire_token(token)
            self._end_operation(token)
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ARTIST,
                artist.key,
                EnrichmentOperationState.CANCELLED,
            )

    def enrich_album(
        self,
        album: AlbumRef,
        resolved_artist_external_id: str = "",
        on_state: StateCallback | None = None,
    ) -> None:
        if not self._enabled():
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ALBUM,
                album.key,
                EnrichmentOperationState.DISABLED,
            )
            return
        token = self._begin_operation(EnrichmentEntityKind.ALBUM, album.key)
        if token is None:
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ALBUM,
                album.key,
                EnrichmentOperationState.CANCELLED,
            )
            return
        if not self._submit_if_running(
            lambda: self._run_album(token, album, resolved_artist_external_id, on_state)
        ):
            self._retire_token(token)
            self._end_operation(token)
            self._report_policy(
                on_state,
                EnrichmentEntityKind.ALBUM,
                album.key,
                EnrichmentOperationState.CANCELLED,
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
        with self._lock:
            token = self._operations.get(
                (EnrichmentEntityKind.ARTIST, local_artist_key)
            )
        if token is not None:
            self._retire_token(token)

    def cancel_album(self, local_album_key: str) -> None:
        with self._lock:
            token = self._operations.get((EnrichmentEntityKind.ALBUM, local_album_key))
        if token is not None:
            self._retire_token(token)

    def cancel_all(self) -> None:
        """R1.3: cancels the operations ACTIVE AT THE SNAPSHOT — each via
        its own generation retirement. A new operation started after the
        snapshot is never accidentally cancelled."""
        with self._lock:
            tokens = [
                token
                for token in self._operations.values()
                if token is not None
            ]
        for token in tokens:
            self._retire_token(token)

    def shutdown(self) -> None:
        """R1.3: admission closes FIRST, then every active generation is
        retired BEFORE the executor waits — a resolver returning during
        shutdown can never cross an authority gate."""
        with self._lock:
            self._shutting_down = True
            tokens = [
                token
                for token in self._operations.values()
                if token is not None
            ]
        for token in tokens:
            self._retire_token(token)
        self._executor.shutdown(wait=True)

    def clear_artist_knowledge(self, local_artist_key: str) -> None:
        self._service.clear_artist_knowledge(local_artist_key)

    def clear_album_knowledge(self, local_album_key: str) -> None:
        self._service.clear_album_knowledge(local_album_key)

    def reset_artist_identity(self, local_artist_key: str) -> None:
        self._service.reset_artist_identity(local_artist_key)

    def reset_album_identity(self, local_album_key: str) -> None:
        self._service.reset_album_identity(local_album_key)

    # -- manual async search (R1.1: controlled submission) -----------------------

    def _retire_token(
        self, token: EnrichmentOperationToken, request=None
    ) -> None:
        """R1.3 single retirement helper: token.cancel() + the Service
        generation barrier (retire_operation) which atomically retires
        the generation AND invalidates the same-generation request.
        Never key-scoped; never touches a newer generation."""
        token.cancel()
        self._service.retire_operation(
            token.entity_kind, token.local_entity_key, token.generation
        )

    def _submit_if_running(self, work) -> bool:
        """R1.1/R1.2: controlled submission boundary — after shutdown
        the method returns False instead of raising RuntimeError. The
        executor port itself also owns an admission contract (submit ->
        bool)."""
        with self._lock:
            if self._shutting_down:
                return False
            accepted = self._executor.submit(work)
            # Legacy ports return None; the R1.2 executor port returns
            # bool (False = closed). None counts as accepted.
            return accepted is not False

    def search_artist_candidates_async(
        self,
        artist_name: str,
        on_result: ResultCallback,
        on_error: ErrorCallback | None = None,
    ) -> bool:
        """Returns True when the job was accepted; False when the
        coordinator is shutting down. Provider failures reach
        ``on_error`` — never an empty success."""
        return self._submit_if_running(
            lambda: self._search_artist_worker(artist_name, on_result, on_error)
        )

    def search_album_candidates_async(
        self,
        album_title: str,
        artist_name: str,
        on_result: ResultCallback,
        on_error: ErrorCallback | None = None,
    ) -> bool:
        return self._submit_if_running(
            lambda: self._search_album_worker(
                album_title, artist_name, on_result, on_error
            )
        )

    def _search_artist_worker(
        self,
        artist_name: str,
        on_result: ResultCallback,
        on_error: ErrorCallback | None,
    ) -> None:
        try:
            on_result(self._search_artist_candidates_sync(artist_name))
        except EnrichmentProviderError as exc:
            if on_error is not None:
                on_error(exc)
            else:
                logger.warning("async artist search failed: %s", exc)

    def _search_album_worker(
        self,
        album_title: str,
        artist_name: str,
        on_result: ResultCallback,
        on_error: ErrorCallback | None,
    ) -> None:
        try:
            on_result(self._search_album_candidates_sync(album_title, artist_name))
        except EnrichmentProviderError as exc:
            if on_error is not None:
                on_error(exc)
            else:
                logger.warning("async album search failed: %s", exc)

    def _search_artist_candidates_sync(
        self, artist_name: str
    ) -> tuple[ArtistIdentityCandidateView, ...]:
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

    # -- artist workflow ----------------------------------------------------------

    def _run_artist(
        self,
        token: EnrichmentOperationToken,
        artist: ArtistRef,
        albums: tuple[AlbumRef, ...],
        tracks: tuple[TrackRef, ...],
        on_state: StateCallback | None,
    ) -> None:
        request = None
        try:
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            self._report(token, on_state, EnrichmentOperationState.RESOLVING_IDENTITY)
            evidence = self._evidence_builder.artist_evidence(artist, albums, tracks)
            outcome = self._service.request_artist_enrichment(
                evidence, generation=token.generation
            )
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
                if outcome.resolution.status is IdentityResolutionStatus.SUPERSEDED:
                    state = EnrichmentOperationState.CANCELLED
                self._report(token, on_state, state)
                return
            request = outcome.request
            external_id = request.external_entity_id
            local_key = request.local_entity_key
            self._report(token, on_state, EnrichmentOperationState.FETCHING_KNOWLEDGE)
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return

            partial = False
            profile = self._mb.fetch_artist(local_key, external_id)
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            try:
                links = self._mb.artist_links(external_id)
            except EnrichmentProviderError:
                links = ArtistExternalLinks()
                partial = True
            partial = partial or links.is_stale
            profile, partial = self._apply_artist_links(profile, links, partial)
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            profile, partial = self._apply_biography(profile, partial)
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            profile, partial = self._apply_artist_image(profile, external_id, partial)
            self._commit_artist(token, request, profile, partial, on_state)
        except EnrichmentProviderError as exc:
            self._terminal_failure(token, request, artist.key, exc, on_state)
        except Exception as exc:  # noqa: BLE001 — unexpected programming errors
            logger.exception("unexpected artist enrichment failure: %s", exc)
            self._terminal_unexpected(token, request, artist.key, on_state)
        finally:
            self._end_operation(token)

    def _commit_artist(
        self,
        token: EnrichmentOperationToken,
        request,
        profile: ArtistKnowledgeProfile,
        partial: bool,
        on_state: StateCallback | None,
    ) -> None:
        """R1.1 LINEARIZATION POINT: serialized against cancel /
        supersede / shutdown. If cancellation wins first, the operation
        can never deliver; if this gate wins first, the commit happens
        exactly once."""
        local_key = token.local_entity_key
        with self._lock:
            current = self._operations.get((EnrichmentEntityKind.ARTIST, local_key))
            if self._shutting_down or token.cancelled or current is not token:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            stale = profile.provenance.is_stale or profile.biography_provenance.is_stale
            verdict = self._service.deliver_artist_profile(request, profile)
        if verdict is DeliveryVerdict.COMMITTED:
            self._report(
                token,
                on_state,
                EnrichmentOperationState.PARTIAL
                if (partial or stale)
                else EnrichmentOperationState.READY,
            )
        else:
            self._report(token, on_state, EnrichmentOperationState.FAILED)

    def _apply_artist_links(
        self,
        profile: ArtistKnowledgeProfile,
        links: ArtistExternalLinks,
        partial: bool,
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
        self, profile: ArtistKnowledgeProfile, partial: bool
    ) -> tuple[ArtistKnowledgeProfile, bool]:
        """R1.1: biography uses the FINAL projected page/language
        (MusicBrainz relation, else verified Wikidata sitelink) already
        merged into the profile — never the original links object, never
        a name search."""
        title = profile.wikipedia_page_title
        language = profile.wikipedia_language
        if self._wikipedia is None or not title:
            return profile, partial
        try:
            bio = self._wikipedia.fetch_biography(title, language)
        except EnrichmentProviderError:
            return profile, True
        if not bio.text:
            return profile, True
        return (
            replace(
                profile,
                biography=bio.text,
                biography_provenance=KnowledgeProvenance(
                    provider="wikipedia",
                    external_entity_id=title,
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
                return profile, True
            partial = partial or image.is_stale
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

    # -- album workflow ------------------------------------------------------------

    def _run_album(
        self,
        token: EnrichmentOperationToken,
        album: AlbumRef,
        resolved_artist_external_id: str,
        on_state: StateCallback | None,
    ) -> None:
        request = None
        try:
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            self._report(token, on_state, EnrichmentOperationState.RESOLVING_IDENTITY)
            evidence = self._evidence_builder.album_evidence(
                album, resolved_artist_external_id
            )
            outcome = self._service.request_album_enrichment(
                evidence, generation=token.generation
            )
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
                if outcome.resolution.status is IdentityResolutionStatus.SUPERSEDED:
                    state = EnrichmentOperationState.CANCELLED
                self._report(token, on_state, state)
                return
            request = outcome.request
            self._report(token, on_state, EnrichmentOperationState.FETCHING_KNOWLEDGE)
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            partial = False
            profile = self._mb.fetch_release_group(
                request.local_entity_key,
                request.external_entity_id,
                request.external_variant_id,
            )
            if token.cancelled:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            profile, partial = self._apply_cover(profile, partial)
            self._commit_album(token, request, profile, partial, on_state)
        except EnrichmentProviderError as exc:
            self._terminal_failure(token, request, album.key, exc, on_state)
        except Exception as exc:  # noqa: BLE001 — unexpected programming errors
            logger.exception("unexpected album enrichment failure: %s", exc)
            self._terminal_unexpected(token, request, album.key, on_state)
        finally:
            self._end_operation(token)

    def _commit_album(
        self,
        token: EnrichmentOperationToken,
        request,
        profile: AlbumKnowledgeProfile,
        partial: bool,
        on_state: StateCallback | None,
    ) -> None:
        """R1.1 LINEARIZATION POINT (album)."""
        local_key = token.local_entity_key
        with self._lock:
            current = self._operations.get((EnrichmentEntityKind.ALBUM, local_key))
            if self._shutting_down or token.cancelled or current is not token:
                self._retire_token(token)
                self._report(token, on_state, EnrichmentOperationState.CANCELLED)
                return
            verdict = self._service.deliver_album_profile(request, profile)
        if verdict is DeliveryVerdict.COMMITTED:
            self._report(
                token,
                on_state,
                EnrichmentOperationState.PARTIAL
                if (partial or profile.provenance.is_stale)
                else EnrichmentOperationState.READY,
            )
        else:
            self._report(token, on_state, EnrichmentOperationState.FAILED)

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
                return profile, partial or cover.is_stale
            partial = partial or cover.is_stale
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

    # -- terminal convergence (R1.1) --------------------------------------------------

    def _terminal_failure(
        self,
        token: EnrichmentOperationToken,
        request,
        local_key: str,
        exc: EnrichmentProviderError,
        on_state: StateCallback | None,
    ) -> None:
        """R1.2: known provider/transport failures converge to a
        terminal state (transient -> OFFLINE; other -> FAILED). The
        worker invalidates EXACTLY its own request (if any) and its own
        generation — a stale worker can NEVER cancel a newer
        generation's request."""
        self._retire_token(token)
        if request is not None:
            self._service.cancel_request_exact(request)
        if is_transient_provider_failure(exc):
            self._report(token, on_state, EnrichmentOperationState.OFFLINE)
        else:
            self._report(token, on_state, EnrichmentOperationState.FAILED)

    def _terminal_unexpected(
        self,
        token: EnrichmentOperationToken,
        request,
        local_key: str,
        on_state: StateCallback | None,
    ) -> None:
        self._retire_token(token)
        if request is not None:
            self._service.cancel_request_exact(request)
        self._report(token, on_state, EnrichmentOperationState.FAILED)

    # -- helpers -----------------------------------------------------------------------

    @staticmethod
    def _declared_mime(response) -> str:
        raw = response.headers.get("content-type", "")
        mime = raw.split(";", 1)[0].strip().lower()
        if mime in {"image/jpeg", "image/png", "image/webp"}:
            return mime
        return ""

    @staticmethod
    def _report_policy(
        on_state: StateCallback | None,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        state: EnrichmentOperationState,
    ) -> None:
        """R1.2: NON-OPERATION policy notices (DISABLED / shutdown
        rejection). They carry operation_id "" and generation 0 — by
        definition never confused with a real correlated operation."""
        if on_state is not None:
            on_state(
                EnrichmentOperationEvent(
                    operation_id="",
                    generation=0,
                    entity_kind=entity_kind,
                    local_entity_key=local_entity_key,
                    state=state,
                )
            )

    @staticmethod
    def _report(
        token: EnrichmentOperationToken,
        on_state: StateCallback | None,
        state: EnrichmentOperationState,
    ) -> None:
        """R1.2: every callback carries the full operation correlation
        (operation_id + generation)."""
        if on_state is not None:
            on_state(
                EnrichmentOperationEvent(
                    operation_id=token.operation_id,
                    generation=token.generation,
                    entity_kind=token.entity_kind,
                    local_entity_key=token.local_entity_key,
                    state=state,
                )
            )
