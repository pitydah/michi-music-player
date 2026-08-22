"""M6.9A-R2 — common-title album identity safety (§12-18, §81, §99).

Behavioral gates proving that album TITLE + YEAR never identifies the
artist:
- common title, different artists, local artist name -> resolved by the
  ARTIST gate (year only corroborates)
- unknown artist common title -> AMBIGUOUS (year must never choose)
- same-artist same-title duplicates: year MAY corroborate (documented),
  ties stay AMBIGUOUS
- resolved external artist id gate
- candidates that cannot prove artist compatibility are excluded
  (fail-closed)
- candidate order never changes verdicts
"""

from itertools import permutations

from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    IdentityResolutionStatus,
    ReleaseGroupCandidate,
    resolve_album_identity,
)


def rg(rid, title, artists=(), names=(), year=0):
    return ReleaseGroupCandidate(
        release_group_id=rid,
        title=title,
        artist_credit_external_ids=tuple(artists),
        artist_credit_names=tuple(names),
        first_release_year=year,
    )


def evidence(
    title,
    artist_name="",
    resolved_artist_id="",
    year=0,
):
    return AlbumIdentityEvidence(
        local_album_key="album-key",
        local_album_title=title,
        local_album_artist_key=artist_name.casefold() if artist_name else "",
        local_album_artist_name=artist_name,
        resolved_artist_external_id=resolved_artist_id,
        local_year=year,
    )


class TestCommonTitleDifferentArtists:
    def test_artist_gate_resolves_not_year(self):
        """§16: Greatest Hits / Artist A / 1980 vs Artist B / 1990.
        Local artist = Artist A -> RG-A wins by ARTIST + TITLE, not year."""
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
                rg("rg-b", "Greatest Hits", names=("Artist B",), year=1990),
            ],
            [],
            evidence("Greatest Hits", artist_name="Artist A", year=1980),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"

    def test_year_cannot_flip_artist_gate(self):
        """Even if the local year matches the WRONG artist's year, the
        artist gate decides first."""
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
                rg("rg-b", "Greatest Hits", names=("Artist B",), year=1990),
            ],
            [],
            evidence("Greatest Hits", artist_name="Artist A", year=1990),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"

    def test_unknown_artist_common_title_is_ambiguous(self):
        """§17: no artist id, no artist name -> year MUST NOT choose."""
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
                rg("rg-b", "Greatest Hits", names=("Artist B",), year=1990),
            ],
            [],
            evidence("Greatest Hits", year=1980),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_resolved_artist_id_gate(self):
        resolution = resolve_album_identity(
            [
                rg(
                    "rg-a",
                    "Greatest Hits",
                    artists=("artist-a-id",),
                    names=("Artist A",),
                ),
                rg(
                    "rg-b",
                    "Greatest Hits",
                    artists=("artist-b-id",),
                    names=("Artist B",),
                ),
            ],
            [],
            evidence("Greatest Hits", resolved_artist_id="artist-a-id"),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"

    def test_unknown_credits_fail_closed_with_name_gate(self):
        """A candidate that cannot prove artist compatibility is excluded
        even when it is the only title match."""
        resolution = resolve_album_identity(
            [rg("rg-a", "Greatest Hits")],  # no credits at all
            [],
            evidence("Greatest Hits", artist_name="Artist A"),
        )
        assert resolution.status is IdentityResolutionStatus.NO_MATCH

    def test_permutations_never_change_verdict(self):
        candidates = [
            rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
            rg("rg-b", "Greatest Hits", names=("Artist B",), year=1990),
        ]
        local = evidence("Greatest Hits", artist_name="Artist A", year=1980)
        expected = resolve_album_identity(candidates, [], local)
        assert expected.release_group_id == "rg-a"
        for permuted in permutations(candidates):
            assert resolve_album_identity(permuted, [], local) == expected


class TestSameArtistCommonTitle:
    def test_same_artist_year_may_corroborate(self):
        """§18: title + artist gates passed; year corroborates the
        duplicate case (documented R2 semantics)."""
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
                rg("rg-b", "Greatest Hits", names=("Artist A",), year=1990),
            ],
            [],
            evidence("Greatest Hits", artist_name="Artist A", year=1990),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-b"

    def test_same_artist_tied_year_is_ambiguous(self):
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",), year=1980),
                rg("rg-b", "Greatest Hits", names=("Artist A",), year=1980),
            ],
            [],
            evidence("Greatest Hits", artist_name="Artist A", year=1980),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_same_artist_unknown_year_is_ambiguous(self):
        resolution = resolve_album_identity(
            [
                rg("rg-a", "Greatest Hits", names=("Artist A",)),
                rg("rg-b", "Greatest Hits", names=("Artist A",)),
            ],
            [],
            evidence("Greatest Hits", artist_name="Artist A"),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS
