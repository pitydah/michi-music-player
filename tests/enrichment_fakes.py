"""M6.9A test fakes — enrichment bounded contexts only.

Never touches the canonical library ports (MetadataExtractorPort,
LibraryIndexRepository, ArtworkCachePort stay untouched by these fakes).
"""

import hashlib
from dataclasses import asdict
from pathlib import Path

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
from michi.application.ports import LibraryIndexRepository
from michi.domain.enrichment import (
    AlbumExternalIdentity,
    AlbumIdentityEvidence,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistExternalIdentity,
    ArtistIdentityEvidence,
    ArtistKnowledgeProfile,
    EnrichmentAssetRecord,
    KnowledgeProvenance,
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
            provenance=KnowledgeProvenance(provider="fake"),
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
            provenance=KnowledgeProvenance(provider="fake"),
        )


class RecordingKnowledgeRepository(KnowledgeRepositoryPort):
    """In-memory repository with a full call log for contamination gates."""

    def __init__(self):
        self.artists: dict[str, ArtistKnowledgeProfile] = {}
        self.albums: dict[str, AlbumKnowledgeProfile] = {}
        self.artist_saves: list[ArtistKnowledgeProfile] = []
        self.album_saves: list[AlbumKnowledgeProfile] = []
        self.artist_deletes: list[str] = []
        self.album_deletes: list[str] = []
        self.clear_knowledge_calls = 0

    def save_artist_profile(self, profile: ArtistKnowledgeProfile) -> None:
        self.artists[profile.local_artist_key] = profile
        self.artist_saves.append(profile)

    def save_album_profile(self, profile: AlbumKnowledgeProfile) -> None:
        self.albums[profile.local_album_key] = profile
        self.album_saves.append(profile)

    def delete_artist_profile(self, local_artist_key: str) -> None:
        self.artist_deletes.append(local_artist_key)
        self.artists.pop(local_artist_key, None)

    def delete_album_profile(self, local_album_key: str) -> None:
        self.album_deletes.append(local_album_key)
        self.albums.pop(local_album_key, None)

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

    def clear_knowledge(self) -> None:
        self.clear_knowledge_calls += 1
        self.artists.clear()
        self.albums.clear()

    def version(self) -> int:
        return 1

    @property
    def write_count(self) -> int:
        return len(self.artist_saves) + len(self.album_saves)


class InMemoryIdentityRepository(IdentityRepositoryPort):
    """In-memory identity authority with a call log."""

    def __init__(self):
        self.artists: dict[str, ArtistExternalIdentity] = {}
        self.albums: dict[str, AlbumExternalIdentity] = {}
        self.artist_saves: list[ArtistExternalIdentity] = []
        self.album_saves: list[AlbumExternalIdentity] = []
        self.clear_calls = 0

    def save_artist_identity(self, identity: ArtistExternalIdentity) -> None:
        self.artists[identity.local_artist_key] = identity
        self.artist_saves.append(identity)

    def save_album_identity(self, identity: AlbumExternalIdentity) -> None:
        self.albums[identity.local_album_key] = identity
        self.album_saves.append(identity)

    def delete_artist_identity(self, local_artist_key: str) -> None:
        self.artists.pop(local_artist_key, None)

    def delete_album_identity(self, local_album_key: str) -> None:
        self.albums.pop(local_album_key, None)

    def load_artist_identity(
        self, local_artist_key: str
    ) -> ArtistExternalIdentity | None:
        return self.artists.get(local_artist_key)

    def load_album_identity(self, local_album_key: str) -> AlbumExternalIdentity | None:
        return self.albums.get(local_album_key)

    def load_artist_identities(self) -> tuple[ArtistExternalIdentity, ...]:
        return tuple(sorted(self.artists.values(), key=lambda i: i.local_artist_key))

    def load_album_identities(self) -> tuple[AlbumExternalIdentity, ...]:
        return tuple(sorted(self.albums.values(), key=lambda i: i.local_album_key))

    def clear_identities(self) -> None:
        self.clear_calls += 1
        self.artists.clear()
        self.albums.clear()


class FailingIdentityRepository(InMemoryIdentityRepository):
    """R2 storage-failure fake: writes raise the normalized storage
    error (configurable per operation). Reads behave normally."""

    def __init__(self):
        super().__init__()
        self.fail_save = True
        self.fail_delete = True
        self.fail_clear = True

    def _maybe_fail(self, flag: bool) -> None:
        if flag:
            raise EnrichmentStorageError("injected storage failure")

    def save_artist_identity(self, identity: ArtistExternalIdentity) -> None:
        self._maybe_fail(self.fail_save)
        super().save_artist_identity(identity)

    def save_album_identity(self, identity: AlbumExternalIdentity) -> None:
        self._maybe_fail(self.fail_save)
        super().save_album_identity(identity)

    def delete_artist_identity(self, local_artist_key: str) -> None:
        self._maybe_fail(self.fail_delete)
        super().delete_artist_identity(local_artist_key)

    def delete_album_identity(self, local_album_key: str) -> None:
        self._maybe_fail(self.fail_delete)
        super().delete_album_identity(local_album_key)

    def clear_identities(self) -> None:
        self._maybe_fail(self.fail_clear)
        super().clear_identities()


class RecordingAssetStore(EnrichmentAssetStorePort):
    """In-memory external artwork store; call log for authority gates."""

    def __init__(self):
        self.assets: dict[str, bytes] = {}
        self.records: dict[str, EnrichmentAssetRecord] = {}
        self.stored_ids: list[str] = []

    def store(
        self, record: EnrichmentAssetRecord, data: bytes
    ) -> EnrichmentAssetRecord | None:
        self.assets[record.asset_id] = data
        self.stored_ids.append(record.asset_id)
        completed = EnrichmentAssetRecord(
            **{
                **asdict(record),
                "checksum": hashlib.sha256(data).hexdigest(),
                "local_path": f"/enrichment/assets/{record.asset_id}",
            }
        )
        self.records[record.asset_id] = completed
        return completed

    def path_for(self, asset_id: str) -> Path | None:
        if asset_id not in self.assets:
            return None
        return Path(f"/enrichment/assets/{asset_id}")

    def record_for(self, asset_id: str) -> EnrichmentAssetRecord | None:
        return self.records.get(asset_id)

    def clear(self) -> None:
        self.assets.clear()
        self.records.clear()


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
