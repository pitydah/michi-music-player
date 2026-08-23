"""Enrichment ports — external-knowledge bounded contexts (M6.9A).

M6.9A naming firewall: external-data APIs must NEVER use generic
"metadata" naming (ArtistMetadataProvider / RemoteMetadata /
OnlineMetadataService / MetadataBroker are FORBIDDEN). The word Metadata
is reserved for LOCAL FILE METADATA (``MetadataExtractorPort`` in
``michi.application.ports``). Everything here speaks KNOWLEDGE /
IDENTITY / ENRICHMENT and depends on the pure domain in
``michi.domain.enrichment`` only.

These ports live in their own module so ``ports.py`` (and with it
MetadataExtractorPort) stays byte-for-byte unchanged — M6.9A MUST NOT
modify the metadata extraction boundary.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistExternalIdentity,
    ArtistExternalLinks,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    BiographyKnowledge,
    CommonsImageKnowledge,
    CoverArtKnowledge,
    EnrichmentAssetRecord,
    ExternalIdentityHints,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
    WikidataArtistClaims,
)


class EnrichmentProviderError(RuntimeError):
    """An external enrichment source failed or is unreachable (offline).

    Enrichment failure is NEVER an error for the canonical library: the
    caller discards the request and the local library stays untouched."""


class EnrichmentTransportError(EnrichmentProviderError):
    """R1: operational transport failure (URLError/TimeoutError/OSError/
    body-read failure) — retryable category, never an HTTP status."""


_TRANSIENT_HTTP_STATUS = frozenset({429, 502, 503, 504})


def is_transient_provider_failure(exc: BaseException) -> bool:
    """R1.1: THE single canonical transient-failure rule used by the
    retry policy, the stale-cache fallback eligibility and the
    OFFLINE/FAILED operation classification:

    - EnrichmentTransportError: transient;
    - EnrichmentHttpStatusError with 429/502/503/504: transient;
    - EVERYTHING else (400/401/403/404/418/500/501/505, invalid JSON,
      validation failures, unsafe URLs, provider contract violations):
      NOT transient.
    """
    if isinstance(exc, EnrichmentTransportError):
        return True
    if isinstance(exc, EnrichmentHttpStatusError):
        return exc.status_code in _TRANSIENT_HTTP_STATUS
    return False  # includes EnrichmentResponseLimitError


class EnrichmentResponseLimitError(EnrichmentProviderError):
    """R1.2: a provider response exceeded the configured size bound.

    NOT a transport failure: never transient, never retried, never
    eligible for stale fallback, never OFFLINE — a content/limit failure
    (FAILED)."""


class EnrichmentHttpStatusError(EnrichmentProviderError):
    """Narrow transport error carrying the provider HTTP status (M6.9):
    enables the bounded retry policy (429/502/503/504) without leaking
    urllib exceptions."""

    def __init__(self, status_code: int, headers: dict[str, str], message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers


class EnrichmentStorageError(RuntimeError):
    """Normalized enrichment persistence/storage access failure (R2/R3).

    Raised for OPERATIONAL storage failures across the enrichment
    boundary: identity reads, identity writes, knowledge reads,
    knowledge writes, deletes, clears and version reads. Also raised
    for corrupt/malformed persistent IDENTITY rows (corruption must
    never look like "no identity exists"). sqlite3.Error never crosses
    the infrastructure/application boundary. The canonical library is
    never affected."""


class ExternalIdentityResolverPort(ABC):
    """Resolves local identity evidence into external identity candidates.

    The resolver only FINDS candidates; the fail-closed gates
    (``resolve_artist_identity`` / ``resolve_album_identity``) live in the
    pure domain and decide AMBIGUOUS / IDENTITY_CONFLICT / NO_MATCH.

    R1: entity-specific evidence — artists receive
    ``ArtistIdentityEvidence``, albums receive ``AlbumIdentityEvidence``.
    The two are never interchangeable."""

    @abstractmethod
    def find_artist_candidates(
        self, evidence: ArtistIdentityEvidence
    ) -> tuple[ArtistCandidate, ...]: ...

    @abstractmethod
    def find_release_group_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseGroupCandidate, ...]: ...

    @abstractmethod
    def find_release_edition_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseEditionCandidate, ...]: ...


class ArtistKnowledgeProviderPort(ABC):
    """Fetches external knowledge for a RESOLVED artist identity.

    May raise ``EnrichmentProviderError`` (offline / failure) — never
    returns fabricated profiles. The returned profile is keyed by the
    LOCAL artist key (the presentation-join key) and carries the external
    id for correlation."""

    @abstractmethod
    def fetch_profile(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistKnowledgeProfile: ...


class AlbumKnowledgeProviderPort(ABC):
    """Fetches external knowledge for a RESOLVED release group.

    May raise ``EnrichmentProviderError`` (offline / failure). External
    dates/genres/labels ride ONLY in the knowledge profile — never into
    TrackMetadata/AlbumRef."""

    @abstractmethod
    def fetch_profile(
        self, local_album_key: str, release_group_id: str, release_id: str = ""
    ) -> AlbumKnowledgeProfile: ...


class KnowledgeRepositoryPort(ABC):
    """Persistence of knowledge profiles — enrichment.db EXCLUSIVELY.

    The repository owns its own storage (enrichment.db). It MUST NEVER
    touch library_index / library_meta tables and never share the
    canonical library index database semantics.

    R1: knowledge != identity. This port owns ONLY downloaded knowledge.
    Identity authority lives in ``IdentityRepositoryPort``.

    R3 TRUTHFUL STORAGE: knowledge is cache-like, but storage truth is
    still observable — WRITES (save/delete/clear_knowledge) raise
    ``EnrichmentStorageError`` on failure (never a fake success). READS
    also raise ``EnrichmentStorageError`` on storage failure; a
    malformed cache row degrades to None (logged, never a crash)."""

    @abstractmethod
    def save_artist_profile(self, profile: ArtistKnowledgeProfile) -> None: ...

    @abstractmethod
    def save_album_profile(self, profile: AlbumKnowledgeProfile) -> None: ...

    @abstractmethod
    def delete_artist_profile(self, local_artist_key: str) -> None: ...

    @abstractmethod
    def delete_album_profile(self, local_album_key: str) -> None: ...

    @abstractmethod
    def load_artist_profile(
        self, local_artist_key: str
    ) -> ArtistKnowledgeProfile | None: ...

    @abstractmethod
    def load_album_profile(
        self, local_album_key: str
    ) -> AlbumKnowledgeProfile | None: ...

    @abstractmethod
    def load_artist_profiles(self) -> tuple[ArtistKnowledgeProfile, ...]: ...

    @abstractmethod
    def load_album_profiles(self) -> tuple[AlbumKnowledgeProfile, ...]: ...

    @abstractmethod
    def clear_knowledge(self) -> None: ...

    @abstractmethod
    def version(self) -> int: ...


class IdentityRepositoryPort(ABC):
    """Persistence of the external identity authority (R1/R2) —
    enrichment.db.

    IDENTITY != KNOWLEDGE: resolved/manual mappings live here and survive
    knowledge deletion. Only ``reset_*_identity`` (or
    ``clear_identities``) removes them.

    R2 TRUTHFUL PERSISTENCE: identity WRITES (save/delete/clear) raise
    ``EnrichmentStorageError`` on failure — never silent.

    R3 TRUTHFUL READS: load failures RAISE ``EnrichmentStorageError``
    too — None means "no identity exists", NEVER "storage is broken".
    A read failure must not be mistaken for absence (and never trigger
    automatic re-resolution)."""

    @abstractmethod
    def save_artist_identity(self, identity: ArtistExternalIdentity) -> None: ...

    @abstractmethod
    def save_album_identity(self, identity: AlbumExternalIdentity) -> None: ...

    @abstractmethod
    def delete_artist_identity(self, local_artist_key: str) -> None: ...

    @abstractmethod
    def delete_album_identity(self, local_album_key: str) -> None: ...

    @abstractmethod
    def load_artist_identity(
        self, local_artist_key: str
    ) -> ArtistExternalIdentity | None: ...

    @abstractmethod
    def load_album_identity(
        self, local_album_key: str
    ) -> AlbumExternalIdentity | None: ...

    @abstractmethod
    def load_artist_identities(self) -> tuple[ArtistExternalIdentity, ...]: ...

    @abstractmethod
    def load_album_identities(self) -> tuple[AlbumExternalIdentity, ...]: ...

    @abstractmethod
    def clear_identities(self) -> None: ...


class EnrichmentAssetStorePort(ABC):
    """Storage for downloaded enrichment assets (e.g. external artwork).

    A THIRD artwork authority (M6.9A): LOCAL (embedded/folder) artwork and
    USER artwork keep their own stores; external downloads go HERE only.
    Must never reuse or mutate the canonical local artwork cache and never
    write downloaded bytes into audio files.

    R1 hardening contract (before any network provider exists):
    - size bound (one constant), image MIME allowlist, decode validation
    - strict asset-id validation (never remote titles as paths)
    - atomic writes (no partial visible assets), sha256 checksum
    - provenance rides in the ``EnrichmentAssetRecord``
    """

    @abstractmethod
    def store(
        self, record: EnrichmentAssetRecord, data: bytes
    ) -> EnrichmentAssetRecord | None:
        """Validate + persist asset bytes; returns the COMPLETED record
        (checksum / dimensions / managed_object filled) or None when any
        validation step fails — a failure never leaves a partial asset
        and never destroys the previous valid asset."""

    @abstractmethod
    def path_for(self, asset_id: str) -> Path | None: ...

    @abstractmethod
    def record_for(self, asset_id: str) -> EnrichmentAssetRecord | None: ...

    @abstractmethod
    def clear(self) -> None: ...


@dataclass(frozen=True)
class HttpRequest:
    """Immutable enrichment HTTP request (M6.9B). GET only for M6.9."""

    url: str
    method: str = "GET"
    headers: tuple[tuple[str, str], ...] = ()
    timeout_seconds: float = 10.0


@dataclass(frozen=True)
class HttpResponse:
    """Immutable enrichment HTTP response (M6.9B)."""

    status_code: int
    headers: dict[str, str]
    body: bytes
    final_url: str


class HttpTransportPort(ABC):
    """Provider HTTP boundary (M6.9B) — enrichment-specific, never the
    generic application ports. HTTPS only, host-allowlisted, bounded."""

    @abstractmethod
    def get(self, request: HttpRequest) -> HttpResponse: ...


class IdentityHintExtractorPort(ABC):
    """READ-ONLY extraction of external identity hints embedded in local
    audio tags (M6.9D). NEVER writes tags; NEVER part of the canonical
    MetadataExtractor."""

    @abstractmethod
    def extract_hints(self, file_path: Path) -> ExternalIdentityHints: ...


class EnrichmentExecutorPort(ABC):
    """Off-UI-thread execution boundary (M6.9F + R1.2). All provider
    work runs here — never on the Qt UI thread.

    R1.2 ADMISSION CONTRACT: ``submit`` returns True when the job was
    accepted, False when the executor is closed — it NEVER raises
    RuntimeError after shutdown. ``shutdown`` marks the executor closed
    under its own lifecycle lock."""

    @abstractmethod
    def submit(self, work: Callable[[], None]) -> bool: ...

    @abstractmethod
    def shutdown(self, wait: bool = True) -> None: ...


class ProviderCacheEntry:
    """Decoded provider-cache payload (M6.9B)."""

    def __init__(
        self,
        provider: str,
        url: str,
        status_code: int,
        body: bytes,
        retrieved_at: float,
        expires_at: float,
        etag: str = "",
        last_modified: str = "",
    ) -> None:
        self.provider = provider
        self.url = url
        self.status_code = status_code
        self.body = body
        self.retrieved_at = retrieved_at
        self.expires_at = expires_at
        self.etag = etag
        self.last_modified = last_modified


class ProviderCachePort(ABC):
    """Provider-response cache (M6.9B) — SEPARATE storage authority,
    never enrichment.db (schema 3 stays frozen)."""

    @abstractmethod
    def get(self, provider: str, url: str) -> ProviderCacheEntry | None: ...

    @abstractmethod
    def get_stale(self, provider: str, url: str) -> ProviderCacheEntry | None: ...

    @abstractmethod
    def put(
        self,
        provider: str,
        url: str,
        response: HttpResponse,
        ttl_seconds: float,
        etag: str = "",
        last_modified: str = "",
    ) -> None: ...

    @abstractmethod
    def remove_expired(self, older_than_days: int = 90) -> int: ...


# ---------------------------------------------------------------------------
# M6.9E — KNOWLEDGE PROVIDER PORTS (identity stays the resolver's authority)
# ---------------------------------------------------------------------------


class MusicBrainzKnowledgeProviderPort(ABC):
    """MusicBrainz structured knowledge for a RESOLVED identity, plus
    the verified URL relations that bridge to Wikidata/Wikipedia."""

    @abstractmethod
    def fetch_artist(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistKnowledgeProfile: ...

    @abstractmethod
    def artist_links(self, external_artist_id: str) -> ArtistExternalLinks: ...

    @abstractmethod
    def fetch_release_group(
        self, local_album_key: str, release_group_id: str, release_id: str = ""
    ) -> AlbumKnowledgeProfile: ...


class WikidataKnowledgeProviderPort(ABC):
    """Wikidata structured facts ONLY for a verified QID (never name
    search — Wikidata is not an identity resolver)."""

    @abstractmethod
    def fetch_artist_claims(self, qid: str) -> WikidataArtistClaims: ...


class WikipediaBiographyProviderPort(ABC):
    """Bounded Wikipedia biography for a VERIFIED page title."""

    @abstractmethod
    def fetch_biography(self, title: str, language: str = "") -> BiographyKnowledge: ...


class WikimediaCommonsProviderPort(ABC):
    """Verified Commons image metadata (license/attribution)."""

    @abstractmethod
    def fetch_image(self, file_title: str) -> CommonsImageKnowledge: ...


class CoverArtArchiveProviderPort(ABC):
    """CAA external album-cover fallback for a resolved Release or
    Release Group."""

    @abstractmethod
    def fetch_cover(
        self, release_id: str = "", release_group_id: str = ""
    ) -> CoverArtKnowledge: ...
