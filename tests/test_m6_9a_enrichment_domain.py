"""M6.9A-R1 — pure enrichment domain gates (fail-closed identity semantics).

Coverage:
- ExternalIdentityHints is a SEPARATE raw carrier — never part of
  TrackMetadata; typed ROLE carriers (ArtistIdentityHints /
  AlbumIdentityHints) never merge track-artist and album-artist roles
- Artist homonym gate: name alone never resolves; year alone never
  resolves; name + associated album title resolves deterministically
- Album gate: title is a required gate; year alone never resolves;
  artist compatibility constrains candidates
- Identity conflict: same-role disagreeing hints conflict; different
  roles never auto-conflict
- Candidate-order determinism (permutations)
- Async correlation ledger: out-of-order/stale deliveries discarded
- Profile codecs round-trip deterministically (enrichment.db only)
"""

from itertools import permutations

from michi.domain.enrichment import (
    AlbumIdentityEvidence,
    AlbumIdentityHints,
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistIdentityEvidence,
    ArtistIdentityHints,
    ArtistKnowledgeProfile,
    DeliveryVerdict,
    EnrichmentEntityKind,
    EnrichmentRequest,
    EnrichmentRequestLedger,
    ExternalIdentityHints,
    IdentityResolutionStatus,
    KnowledgeProvenance,
    LocalAlbumEvidence,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
    decode_album_profile,
    decode_artist_profile,
    encode_album_profile,
    encode_artist_profile,
    resolve_album_identity,
    resolve_artist_identity,
)


def artist_candidate(external_id, name="", albums=(), disambiguation=""):
    return ArtistCandidate(
        external_artist_id=external_id,
        canonical_name=name,
        disambiguation=disambiguation,
        known_albums=tuple(
            LocalAlbumEvidence(a[0], a[1] if len(a) > 1 else 0) for a in albums
        ),
    )


def group_candidate(rg_id, title="", artist_credits=(), names=(), first_release_year=0):
    return ReleaseGroupCandidate(
        release_group_id=rg_id,
        title=title,
        artist_credit_external_ids=tuple(artist_credits),
        artist_credit_names=tuple(names),
        first_release_year=first_release_year,
    )


def artist_evidence(
    key="artist-a",
    name="",
    albums=(),
    hints: ArtistIdentityHints | None = None,
):
    return ArtistIdentityEvidence(
        local_artist_key=key,
        local_artist_name=name,
        known_albums=tuple(
            LocalAlbumEvidence(a[0], a[1] if len(a) > 1 else 0) for a in albums
        ),
        identity_hints=hints or ArtistIdentityHints(),
    )


def album_evidence(
    key="album-a",
    title="",
    artist_key="",
    artist_name="",
    resolved_artist_id="",
    year=0,
    hints: AlbumIdentityHints | None = None,
):
    return AlbumIdentityEvidence(  # type: ignore[call-arg]
        local_album_key=key,
        local_album_title=title,
        local_album_artist_key=artist_key,
        local_album_artist_name=artist_name,
        resolved_artist_external_id=resolved_artist_id,
        local_year=year,
        identity_hints=hints or AlbumIdentityHints(),
    )


class TestExternalIdentityHintsAreSeparate:
    def test_hints_are_not_track_metadata_fields(self):
        from michi.domain.library import TrackMetadata

        forbidden = {
            "musicbrainz_artist_id",
            "musicbrainz_album_id",
            "musicbrainz_release_group_id",
            "musicbrainz_recording_id",
            "wikidata_id",
            "biography",
            "artist_image",
            "external_cover",
            "external_genres",
        }
        assert not forbidden.intersection(TrackMetadata.__dataclass_fields__)

    def test_default_hints_are_empty(self):
        assert ExternalIdentityHints() == ExternalIdentityHints(
            musicbrainz_artist_ids=(),
            musicbrainz_album_artist_ids=(),
            musicbrainz_release_ids=(),
            musicbrainz_release_group_ids=(),
            musicbrainz_recording_ids=(),
            musicbrainz_release_track_ids=(),
        )


class TestRoleSeparation:
    """R1: track-artist ids NEVER automatically conflict with
    album-artist ids — they are different semantic roles."""

    def test_track_and_album_artist_hints_do_not_conflict(self):
        raw = ExternalIdentityHints(
            musicbrainz_artist_ids=("track-a",),
            musicbrainz_album_artist_ids=("album-b",),
        )
        artist_hints = ArtistIdentityHints.from_file_hints(raw)
        album_hints = AlbumIdentityHints.from_file_hints(raw)
        assert artist_hints.artist_ids == ("track-a",)
        assert album_hints.album_artist_ids == ("album-b",)
        # Artist resolution sees ONLY the track-artist role: a single id.
        resolution = resolve_artist_identity([], artist_evidence(hints=artist_hints))
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "track-a"

    def test_no_combined_artist_roles_helper_exists(self):
        from michi.domain.enrichment import (
            ArtistIdentityHints as Hints,
        )

        assert not hasattr(ExternalIdentityHints, "combined_artist_ids")
        assert set(Hints.__dataclass_fields__) == {"artist_ids"}
        assert set(AlbumIdentityHints.__dataclass_fields__) == {
            "release_group_ids",
            "release_ids",
            "album_artist_ids",
        }

    def test_two_track_artist_hints_same_role_conflict(self):
        resolution = resolve_artist_identity(
            [],
            artist_evidence(hints=ArtistIdentityHints(artist_ids=("mb-a", "mb-b"))),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_various_artists_album_role_never_conflicts_with_track_role(self):
        # Compilation: track artist Freddie, album artist Various Artists.
        raw = ExternalIdentityHints(
            musicbrainz_artist_ids=("freddie-id",),
            musicbrainz_album_artist_ids=("various-id",),
            musicbrainz_release_group_ids=("rg-x",),
        )
        artist_hints = ArtistIdentityHints.from_file_hints(raw)
        album_hints = AlbumIdentityHints.from_file_hints(raw)
        artist_resolution = resolve_artist_identity(
            [], artist_evidence(hints=artist_hints)
        )
        assert artist_resolution.status is IdentityResolutionStatus.RESOLVED
        assert artist_resolution.external_entity_id == "freddie-id"
        album_resolution = resolve_album_identity(
            [], [], album_evidence(hints=album_hints)
        )
        assert album_resolution.status is IdentityResolutionStatus.RESOLVED
        assert album_resolution.release_group_id == "rg-x"


class TestArtistHomonymGate:
    def test_name_alone_never_resolves(self):
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a", name="John Williams")],
            artist_evidence(name="John Williams"),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert resolution.external_entity_id == ""

    def test_year_alone_never_resolves(self):
        # Albums with empty titles: year-only evidence can never match.
        resolution = resolve_artist_identity(
            [
                artist_candidate("mb-a", name="John Williams", albums=(("", 1978),)),
            ],
            artist_evidence(name="John Williams", albums=(("", 1978),)),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_single_identity_hint_resolves(self):
        resolution = resolve_artist_identity(
            [],
            artist_evidence(
                name="John Williams",
                hints=ArtistIdentityHints(artist_ids=("mb-a",)),
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_hint_disagreeing_with_candidates_is_conflict(self):
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a"), artist_candidate("mb-b")],
            artist_evidence(hints=ArtistIdentityHints(artist_ids=("mb-x",))),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert resolution.external_entity_id == ""

    def test_name_mismatch_is_no_match(self):
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a", name="Someone Else", albums=(("The Planets",),))],
            artist_evidence(name="John Williams", albums=(("The Planets",),)),
        )
        assert resolution.status is IdentityResolutionStatus.NO_MATCH

    def test_name_plus_unique_album_title_resolves(self):
        resolution = resolve_artist_identity(
            [
                artist_candidate(
                    "mb-a",
                    name="John Williams",
                    albums=(("The Planets", 1978), ("Suite One", 1982)),
                ),
                artist_candidate(
                    "mb-b", name="John Williams", albums=(("Other Work", 2001),)
                ),
            ],
            artist_evidence(name="John Williams", albums=(("The Planets", 1978),)),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_john_williams_homonym_case(self):
        """Film composer vs guitarist: only associated album evidence
        distinguishes them; name alone is AMBIGUOUS."""
        composer = artist_candidate(
            "mb-composer",
            name="John Williams",
            disambiguation="film composer",
            albums=(("Star Wars", 1977), ("E.T.", 1982)),
        )
        guitarist = artist_candidate(
            "mb-guitarist",
            name="John Williams",
            disambiguation="guitarist",
            albums=(("The Height Below", 1969),),
        )
        assert (
            resolve_artist_identity(
                [composer, guitarist], artist_evidence(name="John Williams")
            ).status
            is IdentityResolutionStatus.AMBIGUOUS
        )
        resolution = resolve_artist_identity(
            [composer, guitarist],
            artist_evidence(name="John Williams", albums=(("Star Wars", 1977),)),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-composer"

    def test_tied_album_title_evidence_is_ambiguous(self):
        resolution = resolve_artist_identity(
            [
                artist_candidate(
                    "mb-a", name="John Williams", albums=(("Shared Title", 1978),)
                ),
                artist_candidate(
                    "mb-b", name="John Williams", albums=(("Shared Title", 1978),)
                ),
            ],
            artist_evidence(name="John Williams", albums=(("Shared Title", 1978),)),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_candidate_order_never_changes_verdict(self):
        candidates = [
            artist_candidate(
                "mb-a", name="John Williams", albums=(("The Planets", 1978),)
            ),
            artist_candidate(
                "mb-b", name="John Williams", albums=(("Other Work", 2001),)
            ),
        ]
        evidence = artist_evidence(
            name="John Williams", albums=(("The Planets", 1978),)
        )
        expected = resolve_artist_identity(candidates, evidence)
        for permutation in permutations(candidates):
            resolution = resolve_artist_identity(permutation, evidence)
            assert resolution == expected
        assert expected.status is IdentityResolutionStatus.RESOLVED
        assert expected.external_entity_id == "mb-a"


class TestPairedAlbumEvidence:
    """R1: title/year stay PAIRED — independent bags must not produce
    false cross-matches."""

    def test_year_corroboration_is_paired_not_bagged(self):
        # Local: Album A-1978, Album B-1990.
        # Candidate X: Album A-1990 (title matches, year differs).
        # Candidate Y: Album A-1978 (title+year match).
        resolution = resolve_artist_identity(
            [
                artist_candidate("mb-x", name="Artist", albums=(("Album A", 1990),)),
                artist_candidate("mb-y", name="Artist", albums=(("Album A", 1978),)),
            ],
            artist_evidence(
                name="Artist", albums=(("Album A", 1978), ("Album B", 1990))
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-y"

    def test_album_evidence_preserves_pairs(self):
        evidence = artist_evidence(
            name="Artist", albums=(("Album A", 1978), ("Album B", 1990))
        )
        assert evidence.known_albums == (
            LocalAlbumEvidence("Album A", 1978),
            LocalAlbumEvidence("Album B", 1990),
        )


class TestAlbumIdentityGate:
    def test_title_is_required_without_hint(self):
        resolution = resolve_album_identity(
            [group_candidate("rg-a", title="Kind of Blue", first_release_year=1959)],
            [],
            album_evidence(title="", year=1959),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_year_alone_never_resolves_group(self):
        # R3: even a unique title match resolves NOTHING without artist
        # compatibility evidence (year can never supply it).
        resolution = resolve_album_identity(
            [
                group_candidate("rg-a", title="Kind of Blue", first_release_year=1959),
                group_candidate("rg-b", title="Bitches Brew", first_release_year=1970),
            ],
            [],
            album_evidence(title="Kind of Blue", year=1970),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_release_group_hint_resolves_group_only(self):
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [],
            album_evidence(hints=AlbumIdentityHints(release_group_ids=("rg-a",))),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_conflicting_release_group_hints_conflict(self):
        resolution = resolve_album_identity(
            [],
            [],
            album_evidence(
                hints=AlbumIdentityHints(release_group_ids=("rg-a", "rg-b"))
            ),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_artist_compatibility_excludes_incompatible_groups(self):
        resolution = resolve_album_identity(
            [
                group_candidate(
                    "rg-a",
                    title="Greatest Hits",
                    artist_credits=("artist-a-id",),
                    first_release_year=1980,
                ),
                group_candidate(
                    "rg-b",
                    title="Greatest Hits",
                    artist_credits=("artist-b-id",),
                    first_release_year=1980,
                ),
            ],
            [],
            album_evidence(
                title="Greatest Hits", resolved_artist_id="artist-a-id", year=1980
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"

    def test_artist_compatibility_incompatible_is_no_match(self):
        resolution = resolve_album_identity(
            [
                group_candidate(
                    "rg-b",
                    title="Greatest Hits",
                    artist_credits=("artist-b-id",),
                ),
            ],
            [],
            album_evidence(title="Greatest Hits", resolved_artist_id="artist-a-id"),
        )
        assert resolution.status is IdentityResolutionStatus.NO_MATCH

    def test_tied_title_match_stays_ambiguous(self):
        resolution = resolve_album_identity(
            [
                group_candidate("rg-a", title="Greatest Hits"),
                group_candidate("rg-b", title="Greatest Hits"),
            ],
            [],
            album_evidence(title="Greatest Hits"),
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_edition_never_resolves_without_release_hint(self):
        resolution = resolve_album_identity(
            [group_candidate("rg-a", title="Kind of Blue", names=("Miles Davis",))],
            [ReleaseEditionCandidate(release_id="rel-1", release_group_id="rg-a")],
            album_evidence(title="Kind of Blue", artist_name="Miles Davis"),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_release_hint_with_corroboration_resolves_edition(self):
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [ReleaseEditionCandidate(release_id="rel-1", release_group_id="rg-a")],
            album_evidence(
                hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-1",)
                )
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == "rel-1"

    def test_release_hint_wrong_group_is_identity_conflict(self):
        # R3 CASE C: the hinted release provably belongs to a DIFFERENT
        # group — the contradiction is never silently dropped.
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [ReleaseEditionCandidate(release_id="rel-9", release_group_id="rg-other")],
            album_evidence(
                hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-9",)
                )
            ),
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert resolution.release_id == ""

    def test_release_hint_without_edition_evidence_not_assigned(self):
        # R3 CASE A: no edition candidates -> the release hint is NOT
        # corroborated; the group may resolve, the edition never does.
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [],
            album_evidence(
                hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-x",)
                )
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_release_hint_no_matching_candidate_not_assigned(self):
        # R3 CASE D: edition candidates exist but none matches the hint.
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [ReleaseEditionCandidate(release_id="rel-other", release_group_id="rg-a")],
            album_evidence(
                hints=AlbumIdentityHints(
                    release_group_ids=("rg-a",), release_ids=("rel-x",)
                )
            ),
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_album_candidate_order_never_changes_verdict(self):
        candidates = [
            group_candidate("rg-a", title="Greatest Hits"),
            group_candidate("rg-b", title="Greatest Hits"),
        ]
        evidence = album_evidence(title="Greatest Hits")
        expected = resolve_album_identity(candidates, [], evidence)
        assert expected.status is IdentityResolutionStatus.AMBIGUOUS
        for permutation in permutations(candidates):
            resolution = resolve_album_identity(permutation, [], evidence)
            assert resolution == expected


class TestEnrichmentRequestLedger:
    def _request(self, request_id, entity_kind, local_key, generation=0):
        return EnrichmentRequest(
            request_id=request_id,
            entity_kind=entity_kind,
            local_entity_key=local_key,
            external_entity_id=f"ext-{request_id}",
            generation=generation,
        )

    def test_out_of_order_artists_b_delivered_first(self):
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        b = self._request("b", EnrichmentEntityKind.ARTIST, "artist-b")
        ledger.register(a)
        ledger.register(b)
        assert ledger.deliver(b) is DeliveryVerdict.COMMITTED
        assert ledger.deliver(a) is DeliveryVerdict.COMMITTED
        assert ledger.pending_count() == 0

    def test_out_of_order_same_entity_stale_identity(self):
        ledger = EnrichmentRequestLedger()
        first = self._request(
            "a-1", EnrichmentEntityKind.ARTIST, "artist-a", generation=1
        )
        refreshed = self._request(
            "a-2", EnrichmentEntityKind.ARTIST, "artist-a", generation=2
        )
        ledger.register(first)
        ledger.register(refreshed)
        assert ledger.deliver(first) is DeliveryVerdict.STALE
        assert ledger.deliver(refreshed) is DeliveryVerdict.COMMITTED

    def test_double_delivery_rejected(self):
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        ledger.register(a)
        assert ledger.deliver(a) is DeliveryVerdict.COMMITTED
        assert ledger.deliver(a) is DeliveryVerdict.UNKNOWN

    def test_never_registered_is_unknown(self):
        ledger = EnrichmentRequestLedger()
        ghost = self._request("ghost", EnrichmentEntityKind.ARTIST, "artist-a")
        assert ledger.deliver(ghost) is DeliveryVerdict.UNKNOWN

    def test_entity_kinds_are_independent(self):
        ledger = EnrichmentRequestLedger()
        artist = self._request("a", EnrichmentEntityKind.ARTIST, "shared-key")
        album = self._request("al", EnrichmentEntityKind.ALBUM, "shared-key")
        ledger.register(artist)
        ledger.register(album)
        assert ledger.deliver(artist) is DeliveryVerdict.COMMITTED
        assert ledger.deliver(album) is DeliveryVerdict.COMMITTED

    def test_distinct_local_keys_never_cross(self):
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        b = self._request("b", EnrichmentEntityKind.ARTIST, "artist-b")
        ledger.register(a)
        ledger.register(b)
        assert ledger.deliver(a) is DeliveryVerdict.COMMITTED
        assert ledger.deliver(b) is DeliveryVerdict.COMMITTED

    def test_invalidate_makes_current_request_stale(self):
        """R2: invalidate(entity) -> the pending request is non-committable;
        a late delivery yields STALE, never COMMITTED."""
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        ledger.register(a)
        ledger.invalidate(EnrichmentEntityKind.ARTIST, "artist-a")
        assert ledger.deliver(a) is DeliveryVerdict.STALE
        assert ledger.pending_count() == 0

    def test_invalidate_is_scoped_to_one_entity(self):
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        b = self._request("b", EnrichmentEntityKind.ARTIST, "artist-b")
        ledger.register(a)
        ledger.register(b)
        ledger.invalidate(EnrichmentEntityKind.ARTIST, "artist-a")
        assert ledger.deliver(a) is DeliveryVerdict.STALE
        assert ledger.deliver(b) is DeliveryVerdict.COMMITTED

    def test_invalidate_scoped_by_entity_kind(self):
        ledger = EnrichmentRequestLedger()
        artist = self._request("a", EnrichmentEntityKind.ARTIST, "shared-key")
        album = self._request("al", EnrichmentEntityKind.ALBUM, "shared-key")
        ledger.register(artist)
        ledger.register(album)
        ledger.invalidate(EnrichmentEntityKind.ARTIST, "shared-key")
        assert ledger.deliver(artist) is DeliveryVerdict.STALE
        assert ledger.deliver(album) is DeliveryVerdict.COMMITTED

    def test_invalidate_all_stales_everything(self):
        ledger = EnrichmentRequestLedger()
        a = self._request("a", EnrichmentEntityKind.ARTIST, "artist-a")
        b = self._request("b", EnrichmentEntityKind.ALBUM, "album-b")
        ledger.register(a)
        ledger.register(b)
        ledger.invalidate_all()
        assert ledger.deliver(a) is DeliveryVerdict.STALE
        assert ledger.deliver(b) is DeliveryVerdict.STALE
        assert ledger.pending_count() == 0

    def test_invalidate_then_new_request_commits(self):
        ledger = EnrichmentRequestLedger()
        first = self._request("a-1", EnrichmentEntityKind.ARTIST, "artist-a")
        ledger.register(first)
        ledger.invalidate(EnrichmentEntityKind.ARTIST, "artist-a")
        second = self._request("a-2", EnrichmentEntityKind.ARTIST, "artist-a")
        ledger.register(second)
        assert ledger.deliver(first) is DeliveryVerdict.STALE
        assert ledger.deliver(second) is DeliveryVerdict.COMMITTED


class TestKnowledgeProfileCodecs:
    def test_artist_profile_round_trip(self):
        profile = ArtistKnowledgeProfile(
            local_artist_key="john williams",
            external_artist_id="mb-1234",
            biography="Composer.",
            external_genres=("Classical", "Film Score"),
            begin_year=1932,
            artwork_asset_id="asset-1",
            provenance=KnowledgeProvenance(
                provider="musicbrainz", source_url="https://example.org/a"
            ),
        )
        raw = encode_artist_profile(profile)
        assert isinstance(raw, str)
        assert decode_artist_profile(raw) == profile

    def test_album_profile_round_trip(self):
        profile = AlbumKnowledgeProfile(
            local_album_key="12::kind of blue::miles davis",
            release_group_id="rg-9",
            release_id="",
            external_genres=("Jazz",),
            first_release_year=1959,
            release_year=0,
            label="",
            artwork_asset_id="",
            provenance=KnowledgeProvenance(provider="musicbrainz"),
        )
        raw = encode_album_profile(profile)
        assert decode_album_profile(raw) == profile

    def test_malformed_payload_decodes_to_none(self):
        assert decode_artist_profile("{not json") is None
        assert decode_artist_profile('"just a string"') is None
        assert decode_album_profile("{}") is None

    def test_encoding_is_deterministic(self):
        profile = ArtistKnowledgeProfile(
            local_artist_key="k", external_artist_id="m", external_genres=("b", "a")
        )
        assert encode_artist_profile(profile) == encode_artist_profile(profile)
