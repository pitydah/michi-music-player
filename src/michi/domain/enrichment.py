"""Enrichment bounded contexts — pure domain, no Qt/infra dependencies.

M6.9A METADATA/ENRICHMENT FIREWALL + M6.9A-R1 IDENTITY SEMANTICS.

Five distinct bounded contexts:

1. LOCAL FILE METADATA ......... ``michi.domain.library`` (TrackMetadata,
   TrackRef, AlbumRef, ArtistRef, MusicModel) — the ONLY canonical carrier
   of media-file tags and local technical stream facts.
2. LOCAL EXTERNAL IDENTITY HINTS ``ExternalIdentityHints`` (raw file-level
   carrier) with TYPED ROLE carriers: ``ArtistIdentityHints`` (track-artist
   role) and ``AlbumIdentityHints`` (release group / release / album-artist
   roles). Track-artist ids and album-artist ids are DIFFERENT semantic
   roles and are NEVER merged into one conflict set (R1).
3. RESOLVED EXTERNAL IDENTITY .. ``IdentityResolution`` /
   ``AlbumIdentityResolution`` — fail-closed mapping from entity-specific
   evidence (``ArtistIdentityEvidence`` / ``AlbumIdentityEvidence``).
4. EXTERNAL KNOWLEDGE .......... ``ArtistKnowledgeProfile`` /
   ``AlbumKnowledgeProfile`` — downloaded enrichment stored exclusively in
   enrichment.db. Never merged into context 1/2 models.
5. METADATA EDITING ............ FUTURE — never implemented here.

ONE-WAY DATA FLOW: canonical local library -> local evidence -> identity
resolver -> external knowledge. NO reverse propagation.

R1 matching is STRUCTURAL, not additive point soup: eligibility gates
(name/title) -> required structural evidence (associated album titles) ->
corroborating evidence (years) -> deterministic uniqueness. Year evidence
alone can NEVER resolve an artist or an album/release group.

Every asynchronous enrichment operation carries immutable correlation
(``EnrichmentRequest``): a result may be committed ONLY while it still
matches its original request context (``EnrichmentRequestLedger``).
"""

import json
from collections import deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum, auto


def _normalize_identity_text(raw: str) -> str:
    """Casefold + whitespace collapse — same semantics as the local keys."""
    return " ".join(raw.casefold().split())


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    """Distinct non-empty values preserving first-seen order."""
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return tuple(seen)


# ---------------------------------------------------------------------------
# 2. LOCAL EXTERNAL IDENTITY HINTS — typed ROLE carriers (R1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalIdentityHints:
    """RAW identity hints that may exist inside FLAC/MP3/M4A tags.

    PURE LOCAL EVIDENCE about which external entities a file claims to
    be. NOT canonical musical metadata: these fields must NEVER be added
    to TrackMetadata. Actual tag extraction belongs to a later explicitly
    authorized WP — this is only the carrier.

    R1: this raw carrier is NEVER used directly for matching. Matching
    uses the typed role carriers ``ArtistIdentityHints`` (track-artist
    role) and ``AlbumIdentityHints`` (release group / release /
    album-artist roles). Track-artist ids and album-artist ids are
    different semantic roles — they never merge into one conflict set.
    """

    musicbrainz_artist_ids: tuple[str, ...] = ()
    musicbrainz_album_artist_ids: tuple[str, ...] = ()
    musicbrainz_release_id: str = ""
    musicbrainz_release_group_id: str = ""
    musicbrainz_recording_id: str = ""
    musicbrainz_release_track_id: str = ""


@dataclass(frozen=True)
class ArtistIdentityHints:
    """Track-artist-role identity hints (R1).

    Contains ONLY the track-artist semantic role. Album-artist ids belong
    to ``AlbumIdentityHints`` — the two roles NEVER automatically
    conflict with each other."""

    artist_ids: tuple[str, ...] = ()

    @classmethod
    def from_file_hints(cls, raw: ExternalIdentityHints) -> "ArtistIdentityHints":
        """Project ONLY the track-artist role from raw file hints."""
        return cls(artist_ids=_dedupe(raw.musicbrainz_artist_ids))


@dataclass(frozen=True)
class AlbumIdentityHints:
    """Album-role identity hints (R1).

    Release-group ids and release ids are DISTINCT semantic levels (R1
    preserves the M6.9A release-group != release rule). Album-artist ids
    are a separate role from track-artist ids."""

    release_group_ids: tuple[str, ...] = ()
    release_ids: tuple[str, ...] = ()
    album_artist_ids: tuple[str, ...] = ()

    @classmethod
    def from_file_hints(cls, raw: ExternalIdentityHints) -> "AlbumIdentityHints":
        """Project the album-role hints from raw file hints."""
        return cls(
            release_group_ids=(
                (raw.musicbrainz_release_group_id,)
                if raw.musicbrainz_release_group_id
                else ()
            ),
            release_ids=(
                (raw.musicbrainz_release_id,) if raw.musicbrainz_release_id else ()
            ),
            album_artist_ids=_dedupe(raw.musicbrainz_album_artist_ids),
        )


# ---------------------------------------------------------------------------
# ENTITY-SPECIFIC IDENTITY EVIDENCE (R1 — never shared bags)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LocalAlbumEvidence:
    """One locally known album fact with its PAIRED association (R1).

    Title and year stay paired: independent title/year bags can create
    false cross-matches (Album A-1978 / Album B-1990 must never degrade
    into titles=(A, B), years=(1978, 1990))."""

    title: str
    year: int = 0


@dataclass(frozen=True)
class ArtistIdentityEvidence:
    """Local evidence for ARTIST identity resolution (R1).

    ``known_albums`` preserves title/year association per album."""

    local_artist_key: str
    local_artist_name: str
    known_albums: tuple[LocalAlbumEvidence, ...] = ()
    identity_hints: ArtistIdentityHints = field(default_factory=ArtistIdentityHints)


@dataclass(frozen=True)
class AlbumIdentityEvidence:
    """Local evidence for ALBUM / release-group identity resolution (R1).

    Separate from ``ArtistIdentityEvidence``: release-group/release
    matching uses the local album facts, optionally the already-resolved
    artist identity for artist-credit compatibility, and album-role
    hints."""

    local_album_key: str
    local_album_title: str
    local_album_artist_key: str = ""
    local_album_artist_name: str = ""
    resolved_artist_external_id: str = ""
    local_year: int = 0
    identity_hints: AlbumIdentityHints = field(default_factory=AlbumIdentityHints)


# ---------------------------------------------------------------------------
# 3. RESOLVED EXTERNAL IDENTITY — fail-closed gates
# ---------------------------------------------------------------------------


class IdentityResolutionStatus(Enum):
    """Fail-closed resolution taxonomy (M6.9A + R1).

    AMBIGUOUS and IDENTITY_CONFLICT are terminal non-resolutions: no
    enrichment profile may ever be attached on either."""

    RESOLVED = auto()
    AMBIGUOUS = auto()
    IDENTITY_CONFLICT = auto()
    NO_MATCH = auto()


@dataclass(frozen=True)
class ArtistCandidate:
    """One remote artist candidate with first-class identity facts (R1).

    ``canonical_name`` is the eligibility-gate name; ``disambiguation``
    documents the provider's comment (never identity truth);
    ``known_albums`` carries paired title/year facts. Popularity/ranking
    are NOT identity evidence and are never persisted here."""

    external_artist_id: str
    canonical_name: str = ""
    disambiguation: str = ""
    known_albums: tuple[LocalAlbumEvidence, ...] = ()


@dataclass(frozen=True)
class ReleaseGroupCandidate:
    """One remote release-group candidate (R1).

    ``title`` is the required eligibility gate; ``artist_credit_external_ids``
    allows artist-credit compatibility when the artist identity is already
    resolved; ``first_release_year`` is corroborating only (never
    sufficient alone)."""

    release_group_id: str
    title: str = ""
    artist_credit_external_ids: tuple[str, ...] = ()
    first_release_year: int = 0


@dataclass(frozen=True)
class ReleaseEditionCandidate:
    """One specific release edition inside a release group.

    Edition evidence is ONLY ever an explicit embedded/manual release id —
    album title + artist can never identify one specific edition
    (M6.9A rule, preserved by R1)."""

    release_id: str
    release_group_id: str


@dataclass(frozen=True)
class IdentityResolution:
    """Artist-level resolution verdict. ``external_entity_id`` is set ONLY
    when status is RESOLVED; ``candidate_ids`` carries diagnostics."""

    status: IdentityResolutionStatus
    external_entity_id: str = ""
    candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlbumIdentityResolution:
    """Album-level resolution verdict (M6.9A album identity gate).

    ``release_group_id`` may auto-resolve with strong evidence;
    ``release_id`` remains "" unless edition-identifying evidence
    (an embedded/manual release id) specifically identifies the edition."""

    status: IdentityResolutionStatus
    release_group_id: str = ""
    release_id: str = ""
    candidate_ids: tuple[str, ...] = ()


def resolve_artist_identity(
    candidates: Sequence[ArtistCandidate],
    evidence: ArtistIdentityEvidence,
) -> IdentityResolution:
    """ARTIST HOMONYM + IDENTITY CONFLICT GATES (R1, structural).

    Match hierarchy (strongest first):

    - explicit identity hint (embedded/manual role id) is authoritative;
      multiple DISTINCT track-artist hints -> IDENTITY_CONFLICT (never
      first/majority/most-popular);
    - eligibility: candidate canonical name MUST match the local artist
      name under canonical normalization — name match alone NEVER
      resolves (AMBIGUOUS when no other evidence exists);
    - resolution: at least one strong associated music fact (known local
      album title matching a candidate album title) is REQUIRED; a
      compatible year strengthens a title match; YEAR ALONE can never
      create a match;
    - uniqueness: the candidate with the most title matches wins; ties on
      title matches break by year corroboration; remaining ties stay
      AMBIGUOUS. Candidate order never influences the verdict.
    """
    hints = evidence.identity_hints.artist_ids
    if len(hints) > 1:
        return IdentityResolution(
            status=IdentityResolutionStatus.IDENTITY_CONFLICT,
            candidate_ids=hints,
        )
    if len(hints) == 1:
        hint_id = hints[0]
        candidate_ids = {c.external_artist_id for c in candidates}
        if candidate_ids and hint_id not in candidate_ids:
            return IdentityResolution(
                status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                candidate_ids=tuple(sorted(candidate_ids | {hint_id})),
            )
        return IdentityResolution(
            status=IdentityResolutionStatus.RESOLVED, external_entity_id=hint_id
        )

    local_name = _normalize_identity_text(evidence.local_artist_name)
    if not local_name:
        return IdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)
    eligible = [
        c
        for c in candidates
        if _normalize_identity_text(c.canonical_name) == local_name
    ]
    if not eligible:
        return IdentityResolution(status=IdentityResolutionStatus.NO_MATCH)
    if not evidence.known_albums:
        # NAME ALONE NEVER RESOLVES.
        return IdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)

    local_titles = [
        _normalize_identity_text(album.title)
        for album in evidence.known_albums
        if album.title
    ]
    if not local_titles:
        # Year-only evidence is not representable as a match (R1).
        return IdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)

    scored: list[tuple[int, int, str]] = []
    for candidate in eligible:
        candidate_years = {
            _normalize_identity_text(album.title): album.year
            for album in candidate.known_albums
            if album.title
        }
        title_matches = 0
        year_corroborations = 0
        for album in evidence.known_albums:
            title = _normalize_identity_text(album.title)
            if not title:
                continue
            if title not in candidate_years:
                continue
            title_matches += 1
            if album.year > 0 and candidate_years[title] == album.year:
                year_corroborations += 1
        scored.append(
            (title_matches, year_corroborations, candidate.external_artist_id)
        )

    best_titles = max(title_matches for title_matches, _, _ in scored)
    if best_titles == 0:
        # Name matched but no associated album fact: never resolve.
        return IdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)
    top = [row for row in scored if row[0] == best_titles]
    best_years = max(year_corroborations for _, year_corroborations, _ in top)
    winners = [row for row in top if row[1] == best_years]
    if len(winners) > 1:
        return IdentityResolution(
            status=IdentityResolutionStatus.AMBIGUOUS,
            candidate_ids=tuple(sorted(row[2] for row in winners)),
        )
    return IdentityResolution(
        status=IdentityResolutionStatus.RESOLVED, external_entity_id=winners[0][2]
    )


def resolve_album_identity(
    group_candidates: Sequence[ReleaseGroupCandidate],
    edition_candidates: Sequence[ReleaseEditionCandidate],
    evidence: AlbumIdentityEvidence,
) -> AlbumIdentityResolution:
    """ALBUM IDENTITY GATE (R1, structural).

    - release-group hints: a single hint is authoritative when
      corroborated; multiple DISTINCT same-role hints -> IDENTITY_CONFLICT;
    - without hints, the candidate release-group TITLE must match the
      local album title under canonical normalization — a matching year
      alone is NEVER sufficient (title is a required gate);
    - artist compatibility: when the artist identity is already resolved,
      candidates whose artist credits are known but exclude that external
      id are ineligible;
    - ``first_release_year`` corroborates a title match, never creates it;
    - the release EDITION (``release_id``) stays "" unless a release id
      hint corroborated against the resolved release group exists.
      Title/year can never infer an edition.
    """
    rg_hints = evidence.identity_hints.release_group_ids
    release_hints = evidence.identity_hints.release_ids
    if len(rg_hints) > 1:
        return AlbumIdentityResolution(
            status=IdentityResolutionStatus.IDENTITY_CONFLICT,
            candidate_ids=rg_hints,
        )
    if len(release_hints) > 1:
        return AlbumIdentityResolution(
            status=IdentityResolutionStatus.IDENTITY_CONFLICT,
            candidate_ids=release_hints,
        )

    release_group_id = ""
    if len(rg_hints) == 1:
        hint_rg = rg_hints[0]
        candidate_ids = {c.release_group_id for c in group_candidates}
        if candidate_ids and hint_rg not in candidate_ids:
            return AlbumIdentityResolution(
                status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                candidate_ids=tuple(sorted(candidate_ids | {hint_rg})),
            )
        release_group_id = hint_rg
    else:
        local_title = _normalize_identity_text(evidence.local_album_title)
        if not local_title:
            # Title is a REQUIRED gate: no title means no auto match.
            return AlbumIdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)
        eligible = [
            c
            for c in group_candidates
            if _normalize_identity_text(c.title) == local_title
        ]
        if not eligible:
            return AlbumIdentityResolution(status=IdentityResolutionStatus.NO_MATCH)
        resolved_artist = evidence.resolved_artist_external_id
        if resolved_artist:
            compatible = [
                c
                for c in eligible
                if not c.artist_credit_external_ids
                or resolved_artist in c.artist_credit_external_ids
            ]
            if not compatible:
                return AlbumIdentityResolution(status=IdentityResolutionStatus.NO_MATCH)
            eligible = compatible
        scored: list[tuple[int, str]] = []
        for candidate in eligible:
            year_corroboration = (
                1
                if candidate.first_release_year > 0
                and candidate.first_release_year == evidence.local_year
                else 0
            )
            scored.append((year_corroboration, candidate.release_group_id))
        best = max(year_corroboration for year_corroboration, _ in scored)
        winners = [
            rg for year_corroboration, rg in scored if year_corroboration == best
        ]
        if len(winners) > 1:
            return AlbumIdentityResolution(
                status=IdentityResolutionStatus.AMBIGUOUS,
                candidate_ids=tuple(sorted(winners)),
            )
        release_group_id = winners[0]

    release_id = ""
    if len(release_hints) == 1:
        hint_release = release_hints[0]
        if not edition_candidates:
            release_id = hint_release
        else:
            corroborated = [
                edition
                for edition in edition_candidates
                if edition.release_id == hint_release
                and (
                    not release_group_id or edition.release_group_id == release_group_id
                )
            ]
            if corroborated:
                release_id = hint_release
    return AlbumIdentityResolution(
        status=IdentityResolutionStatus.RESOLVED,
        release_group_id=release_group_id,
        release_id=release_id,
    )


# ---------------------------------------------------------------------------
# 4. EXTERNAL KNOWLEDGE / ENRICHMENT PROFILES
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtistKnowledgeProfile:
    """Downloaded artist knowledge, joined by LOCAL artist key.

    Stored exclusively in enrichment.db. External fields (biography,
    external genres, external dates, artwork asset id) live ONLY here —
    never in TrackMetadata/ArtistRef, never written into audio files.
    R1: NO async lifecycle state (generation/request ids/pending state)
    may ever live here — this is data, not request state."""

    local_artist_key: str
    external_artist_id: str
    biography: str = ""
    external_genres: tuple[str, ...] = ()
    begin_year: int = 0
    end_year: int = 0
    artwork_asset_id: str = ""
    source: str = ""


@dataclass(frozen=True)
class AlbumKnowledgeProfile:
    """Downloaded album knowledge, joined by LOCAL album key.

    ``first_release_year`` / ``release_year`` are EXTERNAL dates — the
    local TrackMetadata.year and AlbumRef.year are never touched.
    ``external_genres`` never merge into local GenreRef values.
    ``release_id`` stays "" unless edition-identifying evidence exists.
    R1: release-level facts (``release_year``, ``label``) must stay ""
    unless ``release_id`` identifies the specific edition."""

    local_album_key: str
    release_group_id: str
    release_id: str = ""
    external_genres: tuple[str, ...] = ()
    first_release_year: int = 0
    release_year: int = 0
    label: str = ""
    artwork_asset_id: str = ""
    source: str = ""


# ---------------------------------------------------------------------------
# ASYNC ENTITY-CORRELATION FIREWALL
# ---------------------------------------------------------------------------


class EnrichmentEntityKind(Enum):
    """Entity kind of an asynchronous enrichment operation."""

    ARTIST = auto()
    ALBUM = auto()


@dataclass(frozen=True)
class EnrichmentRequest:
    """Immutable correlation context for ONE async enrichment operation.

    Every operation carries exactly this context; a result may be committed
    ONLY if it still matches it (see ``EnrichmentRequestLedger``). Never
    correlate async results through mutable globals like ``_active_artist``.
    """

    request_id: str
    entity_kind: EnrichmentEntityKind
    local_entity_key: str
    external_entity_id: str
    generation: int = 0


class DeliveryVerdict(Enum):
    """Commit decision for a delivered async enrichment result."""

    COMMITTED = auto()
    STALE = auto()
    UNKNOWN = auto()
    MISMATCHED = auto()


class EnrichmentRequestLedger:
    """Pending-request correlation registry (M6.9A + R1).

    Tracks the CURRENT request per (entity_kind, local_entity_key). A new
    registration supersedes the previous one; a delivery commits ONLY when
    the request is still current. Out-of-order, double and unknown
    deliveries are discarded — Artist A results can never commit under
    Artist B's context."""

    _SUPERSEDED_CAP = 64

    def __init__(self) -> None:
        self._current: dict[tuple[EnrichmentEntityKind, str], EnrichmentRequest] = {}
        self._superseded: dict[tuple[EnrichmentEntityKind, str], deque[str]] = {}

    @staticmethod
    def _key(request: EnrichmentRequest) -> tuple[EnrichmentEntityKind, str]:
        return (request.entity_kind, request.local_entity_key)

    def register(self, request: EnrichmentRequest) -> None:
        """Make ``request`` the current pending operation for its entity."""
        key = self._key(request)
        previous = self._current.get(key)
        if previous is None:
            self._current[key] = request
            return
        if previous.request_id == request.request_id:
            return
        superseded = self._superseded.setdefault(
            key, deque(maxlen=self._SUPERSEDED_CAP)
        )
        superseded.append(previous.request_id)
        self._current[key] = request

    def deliver(self, request: EnrichmentRequest) -> DeliveryVerdict:
        """Decide whether a delivered result may commit.

        COMMITTED — the request is still current (it is consumed: a second
        delivery of the same request becomes UNKNOWN);
        STALE — superseded by a newer request (out-of-order / stale
        identity); UNKNOWN — never registered."""
        key = self._key(request)
        current = self._current.get(key)
        if current is not None and current.request_id == request.request_id:
            del self._current[key]
            return DeliveryVerdict.COMMITTED
        if request.request_id in self._superseded.get(key, ()):
            return DeliveryVerdict.STALE
        return DeliveryVerdict.UNKNOWN

    def pending_count(self) -> int:
        return len(self._current)


# ---------------------------------------------------------------------------
# ENRICHMENT PROFILE CODEC — enrichment.db ONLY (never library_index)
# ---------------------------------------------------------------------------

_ARTIST_STR_FIELDS = {
    name
    for name, f in ArtistKnowledgeProfile.__dataclass_fields__.items()
    if f.type is str
}
_ARTIST_INT_FIELDS = {
    name
    for name, f in ArtistKnowledgeProfile.__dataclass_fields__.items()
    if f.type is int
}
_ARTIST_TUPLE_FIELDS = {
    name
    for name, f in ArtistKnowledgeProfile.__dataclass_fields__.items()
    if f.type == tuple[str, ...]
}

_ALBUM_STR_FIELDS = {
    name
    for name, f in AlbumKnowledgeProfile.__dataclass_fields__.items()
    if f.type is str
}
_ALBUM_INT_FIELDS = {
    name
    for name, f in AlbumKnowledgeProfile.__dataclass_fields__.items()
    if f.type is int
}
_ALBUM_TUPLE_FIELDS = {
    name
    for name, f in AlbumKnowledgeProfile.__dataclass_fields__.items()
    if f.type == tuple[str, ...]
}


def encode_artist_profile(profile: ArtistKnowledgeProfile) -> str:
    """Deterministic strict JSON of an artist knowledge profile."""
    return json.dumps(asdict(profile), sort_keys=True)


def encode_album_profile(profile: AlbumKnowledgeProfile) -> str:
    """Deterministic strict JSON of an album knowledge profile."""
    return json.dumps(asdict(profile), sort_keys=True)


def _decode_profile(raw, model, str_fields, int_fields, tuple_fields):
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    kwargs = {}
    for name, value in payload.items():
        if name not in model.__dataclass_fields__:
            continue  # future field — tolerated
        if name in str_fields:
            if not isinstance(value, str):
                return None
        elif name in int_fields:
            if isinstance(value, bool) or not isinstance(value, int):
                return None
        elif name in tuple_fields:
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                return None
            value = tuple(value)
        else:
            return None
        kwargs[name] = value
    if set(kwargs) != set(model.__dataclass_fields__):
        return None  # missing field(s)
    return model(**kwargs)


def decode_artist_profile(raw: str) -> ArtistKnowledgeProfile | None:
    """Strict decode; any violation returns None (skip, never fabricate)."""
    return _decode_profile(
        raw,
        ArtistKnowledgeProfile,
        _ARTIST_STR_FIELDS,
        _ARTIST_INT_FIELDS,
        _ARTIST_TUPLE_FIELDS,
    )


def decode_album_profile(raw: str) -> AlbumKnowledgeProfile | None:
    """Strict decode; any violation returns None (skip, never fabricate)."""
    return _decode_profile(
        raw,
        AlbumKnowledgeProfile,
        _ALBUM_STR_FIELDS,
        _ALBUM_INT_FIELDS,
        _ALBUM_TUPLE_FIELDS,
    )
