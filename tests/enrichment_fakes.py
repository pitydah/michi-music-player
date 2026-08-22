"""M6.9A test fakes — enrichment bounded contexts only.

Never touches the canonical library ports (MetadataExtractorPort,
LibraryIndexRepository, ArtworkCachePort stay untouched by these fakes).
"""

from pathlib import Path

from michi.application.enrichment_ports import (
    AlbumKnowledgeProviderPort,
    ArtistKnowledgeProviderPort,
    EnrichmentAssetStorePort,
    EnrichmentProviderError,
    ExternalIdentityResolverPort,
    KnowledgeRepositoryPort,
)
from michi.application.ports import LibraryIndexRepository
from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
)


class FakeIdentityResolver(ExternalIdentityResolverPort):
    """Returns preconfigured candidates; records evidence for assertions."""

    def __init__(self, artists=(), groups=(), editions=()):
        self._artists = tuple(artists)
        self._groups = tuple(groups)
        self._editions = tuple(editions)
        self.artist_evidence: list[ArtistIdentityEvidence] = []
        self.group_evidence: list[AlbumIdentityEvidence] = []
        self.edition_evidence: list[AlbumIdentityEvidence] = []

    def find_artist_candidates(
        self, evidence: ArtistIdentityEvidence
    ) -> tuple[ArtistCandidate, ...]:
        self.artist_evidence.append(evidence)
        return self._artists

    def find_release_group_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseGroupCandidate, ...]:
        self.group_evidence.append(evidence)
        return self._groups

    def find_release_edition_candidates(
        self, evidence: AlbumIdentityEvidence
    ) -> tuple[ReleaseEditionCandidate, ...]:
        self.edition_evidence.append(evidence)
        return self._editions


class FakeArtistProvider(ArtistKnowledgeProviderPort):
    """Builds deterministic profiles; ``offline`` simulates provider failure."""

    def __init__(self, offline: bool = False):
        self._offline = offline
        self.fetch_calls: list[tuple[str, str]] = []

    def fetch_profile(
        self, local_artist_key: str, external_artist_id: str
    ) -> ArtistKnowledgeProfile:
        self.fetch_calls.append((local_artist_key, external_artist_id))
        if self._offline:
            raise EnrichmentProviderError(f"offline: {external_artist_id}")
        return ArtistKnowledgeProfile(
            local_artist_key=local_artist_key,
            external_artist_id=external_artist_id,
            biography=f"Biography of {external_artist_id}",
            external_genres=(f"genre-{external_artist_id}",),
            artwork_asset_id=f"asset-{external_artist_id}",
            source="fake",
        )


class FakeAlbumProvider(AlbumKnowledgeProviderPort):
    """Builds deterministic album profiles; ``offline`` simulates failure."""

    def __init__(self, offline: bool = False):
        self._offline = offline
        self.fetch_calls: list[tuple[str, str, str]] = []

    def fetch_profile(
        self, local_album_key: str, release_group_id: str, release_id: str = ""
    ) -> AlbumKnowledgeProfile:
        self.fetch_calls.append((local_album_key, release_group_id, release_id))
        if self._offline:
            raise EnrichmentProviderError(f"offline: {release_group_id}")
        return AlbumKnowledgeProfile(
            local_album_key=local_album_key,
            release_group_id=release_group_id,
            release_id=release_id,
            external_genres=(f"genre-{release_group_id}",),
            first_release_year=1959,
            source="fake",
        )


class RecordingKnowledgeRepository(KnowledgeRepositoryPort):
    """In-memory repository with a full call log for contamination gates."""

    def __init__(self):
        self.artists: dict[str, ArtistKnowledgeProfile] = {}
        self.albums: dict[str, AlbumKnowledgeProfile] = {}
        self.artist_saves: list[ArtistKnowledgeProfile] = []
        self.album_saves: list[AlbumKnowledgeProfile] = []

    def save_artist_profile(self, profile: ArtistKnowledgeProfile) -> None:
        self.artists[profile.local_artist_key] = profile
        self.artist_saves.append(profile)

    def save_album_profile(self, profile: AlbumKnowledgeProfile) -> None:
        self.albums[profile.local_album_key] = profile
        self.album_saves.append(profile)

    def load_artist_profile(
        self, local_artist_key: str
    ) -> ArtistKnowledgeProfile | None:
        return self.artists.get(local_artist_key)

    def load_album_profile(self, local_album_key: str) -> AlbumKnowledgeProfile | None:
        return self.albums.get(local_album_key)

    def load_artist_profiles(self) -> tuple[ArtistKnowledgeProfile, ...]:
        return tuple(sorted(self.artists.values(), key=lambda p: p.local_artist_key))

    def load_album_profiles(self) -> tuple[AlbumKnowledgeProfile, ...]:
        return tuple(sorted(self.albums.values(), key=lambda p: p.local_album_key))

    def clear(self) -> None:
        self.artists.clear()
        self.albums.clear()

    def version(self) -> int:
        return 1

    @property
    def write_count(self) -> int:
        return len(self.artist_saves) + len(self.album_saves)


class RecordingAssetStore(EnrichmentAssetStorePort):
    """In-memory external artwork store; call log for authority gates."""

    def __init__(self):
        self.assets: dict[str, bytes] = {}
        self.stored_ids: list[str] = []

    def store(self, asset_id: str, data: bytes, mime_type: str) -> str | None:
        del mime_type  # unused in the fake
        self.assets[asset_id] = data
        self.stored_ids.append(asset_id)
        return f"/enrichment/assets/{asset_id}"

    def path_for(self, asset_id: str) -> Path | None:
        if asset_id not in self.assets:
            return None
        return Path(f"/enrichment/assets/{asset_id}")

    def clear(self) -> None:
        self.assets.clear()


class RecordingLibraryIndexRepository(LibraryIndexRepository):
    """SPY on the canonical library index — enrichment must never write."""

    def __init__(self):
        self.writes: list[str] = []

    def load_all(self):
        self.writes.append("load_all")
        return ()

    def upsert_many(self, entries):
        self.writes.append("upsert_many")

    def remove(self, track_id: str):
        self.writes.append("remove")

    def apply_delta(self, upserts, removed):
        self.writes.append("apply_delta")

    def clear(self):
        self.writes.append("clear")

    def version(self) -> int:
        return 1
