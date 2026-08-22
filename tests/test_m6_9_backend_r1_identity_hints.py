"""M6.9-BACKEND-R1 — identity hints evidence preservation.

Mandatory matrix:
A. same RG repeated across tracks → single RG
B. RG-A + RG-B → both preserved → IDENTITY_CONFLICT downstream
C. release-A + release-B → both preserved → IDENTITY_CONFLICT
D. track artist + album artist roles never conflict
E. whitespace/blank/duplicate normalization
F. track-order permutations → same identity verdict
Plus: extractor raw normalization and role projections.
"""

from itertools import permutations
from pathlib import Path

from michi.application.enrichment_evidence import (
    LibraryEnrichmentEvidenceBuilder,
    _aggregate_hints,
)
from michi.domain.enrichment import (
    AlbumIdentityHints,
    ArtistIdentityHints,
    ExternalIdentityHints,
    IdentityResolutionStatus,
    resolve_album_identity,
    resolve_artist_identity,
)
from michi.domain.library import TrackRef, build_music_model


class FakeExtractor:
    def __init__(self, hints_by_path):
        self._hints = hints_by_path

    def extract_hints(self, file_path):
        return self._hints.get(str(file_path), ExternalIdentityHints())


def hint(**kwargs):
    return ExternalIdentityHints(**kwargs)


class TestRawCarrierTupleRoles:
    def test_roles_are_tuples(self):
        fields = ExternalIdentityHints.__dataclass_fields__
        for name in (
            "musicbrainz_artist_ids",
            "musicbrainz_album_artist_ids",
            "musicbrainz_release_group_ids",
            "musicbrainz_release_ids",
            "musicbrainz_recording_ids",
            "musicbrainz_release_track_ids",
        ):
            assert fields[name].type == tuple[str, ...], name

    def test_no_scalar_parallel_authority(self):
        fields = set(ExternalIdentityHints.__dataclass_fields__)
        assert "musicbrainz_release_id" not in fields
        assert "musicbrainz_release_group_id" not in fields
        assert "musicbrainz_recording_id" not in fields
        assert "musicbrainz_release_track_id" not in fields


class TestAggregationPreservesConflicts:
    def test_same_rg_repeated_single(self):
        merged = _aggregate_hints(
            FakeExtractor(
                {
                    "/a": hint(musicbrainz_release_group_ids=("rg-a",)),
                    "/b": hint(musicbrainz_release_group_ids=("rg-a",)),
                    "/c": hint(musicbrainz_release_group_ids=("rg-a",)),
                }
            ),
            ["/a", "/b", "/c"],
        )
        album = AlbumIdentityHints.from_file_hints(merged)
        assert album.release_group_ids == ("rg-a",)

    def test_rg_conflict_preserved(self):
        merged = _aggregate_hints(
            FakeExtractor(
                {
                    "/a": hint(musicbrainz_release_group_ids=("rg-a",)),
                    "/b": hint(musicbrainz_release_group_ids=("rg-b",)),
                }
            ),
            ["/a", "/b"],
        )
        album = AlbumIdentityHints.from_file_hints(merged)
        assert album.release_group_ids == ("rg-a", "rg-b")
        # Downstream: conflict, never first-wins.
        resolution = resolve_album_identity(
            [],
            [],
            __import__(
                "michi.domain.enrichment", fromlist=["AlbumIdentityEvidence"]
            ).AlbumIdentityEvidence(
                local_album_key="k",
                local_album_title="X",
                identity_hints=album,
            ),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_release_conflict_preserved(self):
        merged = _aggregate_hints(
            FakeExtractor(
                {
                    "/a": hint(
                        musicbrainz_release_group_ids=("rg-a",),
                        musicbrainz_release_ids=("rel-a",),
                    ),
                    "/b": hint(
                        musicbrainz_release_group_ids=("rg-a",),
                        musicbrainz_release_ids=("rel-b",),
                    ),
                }
            ),
            ["/a", "/b"],
        )
        album = AlbumIdentityHints.from_file_hints(merged)
        assert album.release_ids == ("rel-a", "rel-b")
        from michi.domain.enrichment import AlbumIdentityEvidence

        resolution = resolve_album_identity(
            [],
            [],
            AlbumIdentityEvidence(
                local_album_key="k",
                local_album_title="X",
                identity_hints=album,
            ),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_track_artist_album_artist_roles_never_conflict(self):
        merged = _aggregate_hints(
            FakeExtractor(
                {
                    "/a": hint(
                        musicbrainz_artist_ids=("track-a",),
                        musicbrainz_album_artist_ids=("album-b",),
                    )
                }
            ),
            ["/a"],
        )
        artist = ArtistIdentityHints.from_file_hints(merged)
        album = AlbumIdentityHints.from_file_hints(merged)
        assert artist.artist_ids == ("track-a",)
        assert album.album_artist_ids == ("album-b",)
        # Artist resolution with a single track-role hint resolves...
        resolution = resolve_artist_identity(
            [],
            __import__(
                "michi.domain.enrichment", fromlist=["ArtistIdentityEvidence"]
            ).ArtistIdentityEvidence(
                local_artist_key="k", local_artist_name="n", identity_hints=artist
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        # ...and never sees the album-artist role.
        assert resolution.external_entity_id == "track-a"

    def test_whitespace_blank_duplicates_normalized(self):
        merged = _aggregate_hints(
            FakeExtractor(
                {"/a": hint(musicbrainz_artist_ids=(" A ", "A", "", "  ", "B"))}
            ),
            ["/a"],
        )
        artist = ArtistIdentityHints.from_file_hints(merged)
        assert artist.artist_ids == ("A", "B")

    def test_track_order_permutations_same_verdict(self):
        extractor = FakeExtractor(
            {
                "/a": hint(musicbrainz_release_group_ids=("rg-a",)),
                "/b": hint(musicbrainz_release_group_ids=("rg-b",)),
                "/c": hint(musicbrainz_release_group_ids=("rg-a",)),
            }
        )
        paths = ["/a", "/b", "/c"]
        for permuted in permutations(paths):
            merged = _aggregate_hints(extractor, list(permuted))
            album = AlbumIdentityHints.from_file_hints(merged)
            # Tuple ORDER may follow first-observation order (data only,
            # never authority) — the distinct SET and the VERDICT must be
            # identical for every permutation.
            assert set(album.release_group_ids) == {"rg-a", "rg-b"}
            assert len(album.release_group_ids) == 2
            from michi.domain.enrichment import AlbumIdentityEvidence

            resolution = resolve_album_identity(
                [],
                [],
                AlbumIdentityEvidence(
                    local_album_key="k",
                    local_album_title="X",
                    identity_hints=album,
                ),
            )
            assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT


class TestEvidenceBuilderUnion:
    def test_builder_album_evidence_union(self):
        tracks = (
            TrackRef(
                file_path=Path("/a.flac"),
                title="T1",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
            TrackRef(
                file_path=Path("/b.flac"),
                title="T2",
                artist="Artist A",
                album="Album X",
                year=1980,
                album_artist="Artist A",
            ),
        )
        model = build_music_model(tracks)
        builder = LibraryEnrichmentEvidenceBuilder(
            FakeExtractor(
                {
                    "/a.flac": hint(musicbrainz_release_group_ids=("rg-a",)),
                    "/b.flac": hint(musicbrainz_release_group_ids=("rg-b",)),
                }
            )
        )
        evidence = builder.album_evidence(model.albums[0])
        assert evidence.identity_hints.release_group_ids == ("rg-a", "rg-b")
