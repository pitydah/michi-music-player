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
from pathlib import Path

from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistExternalIdentity,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
)


class EnrichmentProviderError(RuntimeError):
    """An external enrichment source failed or is unreachable (offline).

    Enrichment failure is NEVER an error for the canonical library: the
    caller discards the request and the local library stays untouched."""


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
    canonical library index database semantics. Best effort: sqlite
    errors are logged, never raised.

    R1: knowledge != identity. This port owns ONLY downloaded knowledge.
    Identity authority lives in ``IdentityRepositoryPort``."""

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
    """Persistence of the external identity authority (R1) — enrichment.db.

    IDENTITY != KNOWLEDGE: resolved/manual mappings live here and survive
    knowledge deletion. Only ``reset_*_identity`` (or
    ``clear_identities``) removes them. Never raises on sqlite errors."""

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
    write downloaded bytes into audio files."""

    @abstractmethod
    def store(self, asset_id: str, data: bytes, mime_type: str) -> str | None:
        """Persist asset bytes; returns the stored path (None on failure)."""

    @abstractmethod
    def path_for(self, asset_id: str) -> Path | None: ...

    @abstractmethod
    def clear(self) -> None: ...
