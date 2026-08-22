"""M6.9A — pure enrichment domain gates (fail-closed identity resolution).

RED phase: the module imports fail at collection until
``michi/domain/enrichment.py`` exposes the M6.9A contract.

Coverage:
- ExternalIdentityHints is a SEPARATE carrier — never part of TrackMetadata
- Artist homonym gate: name alone never resolves; evidence-based matching
  is fail-closed (AMBIGUOUS on ties, IDENTITY_CONFLICT on disagreeing hints)
- Album identity gate: release GROUP may auto-resolve with strong evidence;
  the specific release edition remains "" unless edition-identifying hints
- Async correlation ledger: out-of-order and stale deliveries are discarded
- Profile codecs round-trip deterministically (enrichment.db only)
"""

from michi.domain.enrichment import (
    AlbumKnowledgeProfile,
    ArtistCandidate,
    ArtistKnowledgeProfile,
    DeliveryVerdict,
    EnrichmentEntityKind,
    EnrichmentRequest,
    EnrichmentRequestLedger,
    ExternalIdentityHints,
    IdentityEvidence,
    IdentityResolutionStatus,
    ReleaseEditionCandidate,
    ReleaseGroupCandidate,
    decode_album_profile,
    decode_artist_profile,
    encode_album_profile,
    encode_artist_profile,
    resolve_album_identity,
    resolve_artist_identity,
)


def artist_candidate(external_id, albums=(), years=()):
    return ArtistCandidate(
        external_artist_id=external_id, album_titles=tuple(albums), years=tuple(years)
    )


def group_candidate(rg_id, title="", release_titles=(), first_release_year=0):
    return ReleaseGroupCandidate(
        release_group_id=rg_id,
        title=title,
        release_titles=tuple(release_titles),
        first_release_year=first_release_year,
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

    def test_combined_artist_ids_deduplicates(self):
        hints = ExternalIdentityHints(
            musicbrainz_artist_ids=("a1", "a2"),
            musicbrainz_album_artist_ids=("a2", "a3"),
        )
        assert hints.combined_artist_ids() == ("a1", "a2", "a3")

    def test_default_hints_are_empty(self):
        assert ExternalIdentityHints() == ExternalIdentityHints(
            musicbrainz_artist_ids=(),
            musicbrainz_album_artist_ids=(),
            musicbrainz_release_id="",
            musicbrainz_release_group_id="",
            musicbrainz_recording_id="",
            musicbrainz_release_track_id="",
        )


class TestArtistHomonymGate:
    def test_name_alone_never_resolves(self):
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a")], IdentityEvidence()
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert resolution.external_entity_id == ""

    def test_single_identity_hint_resolves(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        resolution = resolve_artist_identity([], evidence)
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_hint_resolves_against_candidates(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-a",))
        )
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a"), artist_candidate("mb-b")], evidence
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_hint_disagreeing_with_candidates_is_conflict(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_artist_ids=("mb-x",))
        )
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a"), artist_candidate("mb-b")], evidence
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert resolution.external_entity_id == ""

    def test_conflicting_hints_never_pick_first(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(
                musicbrainz_artist_ids=("mb-a", "mb-b")
            )
        )
        resolution = resolve_artist_identity([], evidence)
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT
        assert resolution.external_entity_id == ""

    def test_unique_album_title_evidence_resolves(self):
        evidence = IdentityEvidence(local_album_titles=("The Planets",))
        resolution = resolve_artist_identity(
            [
                artist_candidate("mb-a", albums=("The Planets", "Suite One")),
                artist_candidate("mb-b", albums=("Other Work",)),
            ],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_tied_evidence_is_ambiguous(self):
        evidence = IdentityEvidence(local_album_titles=("Shared Title",))
        resolution = resolve_artist_identity(
            [
                artist_candidate("mb-a", albums=("Shared Title",)),
                artist_candidate("mb-b", albums=("Shared Title",)),
            ],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS
        assert resolution.external_entity_id == ""

    def test_year_evidence_resolves(self):
        evidence = IdentityEvidence(local_years=(1978,))
        resolution = resolve_artist_identity(
            [
                artist_candidate("mb-a", years=(1978, 1982)),
                artist_candidate("mb-b", years=(2001,)),
            ],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.external_entity_id == "mb-a"

    def test_unmatched_evidence_is_no_match(self):
        evidence = IdentityEvidence(local_album_titles=("Nothing Like This",))
        resolution = resolve_artist_identity(
            [artist_candidate("mb-a", albums=("Other",))], evidence
        )
        assert resolution.status is IdentityResolutionStatus.NO_MATCH

    def test_empty_candidates_with_evidence_is_no_match(self):
        evidence = IdentityEvidence(local_album_titles=("Anything",))
        resolution = resolve_artist_identity([], evidence)
        assert resolution.status is IdentityResolutionStatus.NO_MATCH


class TestAlbumIdentityGate:
    def test_release_group_hint_resolves_group_only(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-a")
        )
        resolution = resolve_album_identity([group_candidate("rg-a")], [], evidence)
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_release_group_hint_not_in_candidates_is_conflict(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(musicbrainz_release_group_id="rg-x")
        )
        resolution = resolve_album_identity(
            [group_candidate("rg-a"), group_candidate("rg-b")], [], evidence
        )
        assert resolution.status is IdentityResolutionStatus.IDENTITY_CONFLICT

    def test_unique_title_year_match_resolves_group(self):
        evidence = IdentityEvidence(
            local_album_titles=("Kind of Blue",), local_years=(1959,)
        )
        resolution = resolve_album_identity(
            [
                group_candidate("rg-a", title="Kind of Blue", first_release_year=1959),
                group_candidate("rg-b", title="Bitches Brew", first_release_year=1970),
            ],
            [],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_name_alone_never_resolves_group(self):
        resolution = resolve_album_identity(
            [group_candidate("rg-a")], [], IdentityEvidence()
        )
        assert resolution.status is IdentityResolutionStatus.AMBIGUOUS

    def test_edition_never_resolves_without_release_hint(self):
        evidence = IdentityEvidence(
            local_album_titles=("Kind of Blue",), local_years=(1959,)
        )
        resolution = resolve_album_identity(
            [group_candidate("rg-a", title="Kind of Blue", first_release_year=1959)],
            [ReleaseEditionCandidate(release_id="rel-1", release_group_id="rg-a")],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""

    def test_release_hint_with_corroboration_resolves_edition(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(
                musicbrainz_release_group_id="rg-a",
                musicbrainz_release_id="rel-1",
            )
        )
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [ReleaseEditionCandidate(release_id="rel-1", release_group_id="rg-a")],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == "rel-1"

    def test_release_hint_from_wrong_group_does_not_set_edition(self):
        evidence = IdentityEvidence(
            identity_hints=ExternalIdentityHints(
                musicbrainz_release_group_id="rg-a",
                musicbrainz_release_id="rel-9",
            )
        )
        resolution = resolve_album_identity(
            [group_candidate("rg-a")],
            [ReleaseEditionCandidate(release_id="rel-9", release_group_id="rg-other")],
            evidence,
        )
        assert resolution.status is IdentityResolutionStatus.RESOLVED
        assert resolution.release_group_id == "rg-a"
        assert resolution.release_id == ""


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
        # Neither delivery consumes the other entity's pending context.
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


class TestKnowledgeProfileCodecs:
    def test_artist_profile_round_trip(self):
        profile = ArtistKnowledgeProfile(
            local_artist_key="john williams",
            external_artist_id="mb-1234",
            biography="Composer.",
            external_genres=("Classical", "Film Score"),
            begin_year=1932,
            artwork_asset_id="asset-1",
            source="test",
            generation=2,
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
            source="test",
            generation=1,
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
