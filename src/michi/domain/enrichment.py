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


def dedupe_identity_ids(values: Sequence[str]) -> tuple[str, ...]:
    """R3.1/R3.2: normalize same-role identity hints — strip surrounding
    whitespace, drop empty-after-strip values, dedupe the stripped
    values preserving first-seen order. Repeated observations of the
    SAME id ("A", "A") are one identity; distinct ids are a conflict.
    NEVER called across roles (track artist != album artist) and NEVER
    case-normalized (external IDs are case-sensitive by provider
    contract)."""
    seen: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in seen:
            seen.append(stripped)
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
    musicbrainz_release_group_ids: tuple[str, ...] = ()
    musicbrainz_release_ids: tuple[str, ...] = ()
    musicbrainz_recording_ids: tuple[str, ...] = ()
    musicbrainz_release_track_ids: tuple[str, ...] = ()


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
        return cls(artist_ids=dedupe_identity_ids(raw.musicbrainz_artist_ids))


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
        """Project the album-role hints from raw file hints (R1: every
        distinct same-role observation is preserved — conflicts are the
        domain gates' job, never first-wins)."""
        return cls(
            release_group_ids=dedupe_identity_ids(raw.musicbrainz_release_group_ids),
            release_ids=dedupe_identity_ids(raw.musicbrainz_release_ids),
            album_artist_ids=dedupe_identity_ids(raw.musicbrainz_album_artist_ids),
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
    SUPERSEDED = auto()  # R1.2: a stale generation can never commit


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
    """One remote release-group candidate (R2).

    ``title`` is the required eligibility gate; artist identity lives in
    BOTH ``artist_credit_external_ids`` (verified external ids) and
    ``artist_credit_names`` (normalized-name fallback when the artist
    external identity is not yet resolved). ``first_release_year`` is
    corroborating only — YEAR NEVER identifies the artist (R2)."""

    release_group_id: str
    title: str = ""
    artist_credit_external_ids: tuple[str, ...] = ()
    artist_credit_names: tuple[str, ...] = ()
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
    hints = dedupe_identity_ids(evidence.identity_hints.artist_ids)
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


def resolve_release_hint_for_group(
    release_group_id: str,
    hint_release: str,
    edition_candidates: Sequence[ReleaseEditionCandidate],
) -> tuple[IdentityResolutionStatus, str]:
    """R3.2 RELEASE-EDITION CONTRADICTION DETECTION.

    A specific Release ID identifies ONE edition identity. Evaluate one
    deduplicated release hint against edition candidates for a resolved
    release group:

    - no matching candidate -> (RESOLVED, "") — not assigned;
    - matches in ONE group == resolved group -> (RESOLVED, hint);
    - matches in ONE group != resolved group -> IDENTITY_CONFLICT;
    - matches across MULTIPLE distinct groups -> IDENTITY_CONFLICT,
      even if one of them equals the resolved group (contradictory
      evidence is never accepted via ``any()``);
    - duplicate identical candidates (same release, same group) are
      duplicate observations, not a conflict.

    R3.2.1 DEFENSIVE INPUT: the resolved group and the hint are
    programmer/domain-contract arguments — invalid values raise
    ValueError (never reinterpreted as remote conflict). A MATCHING
    release candidate whose release_group_id is not a non-blank str is
    contradictory external evidence: IDENTITY_CONFLICT — never silently
    discarded, never an IndexError.
    """
    if not isinstance(release_group_id, str) or not release_group_id.strip():
        raise ValueError("release_group_id must be a non-blank str")
    if not isinstance(hint_release, str) or not hint_release.strip():
        raise ValueError("hint_release must be a non-blank str")
    resolved_group = release_group_id.strip()
    matches = [
        edition for edition in edition_candidates if edition.release_id == hint_release
    ]
    if not matches:
        return IdentityResolutionStatus.RESOLVED, ""
    normalized_groups: list[str] = []
    for edition in matches:
        group = edition.release_group_id
        if not isinstance(group, str) or not group.strip():
            return IdentityResolutionStatus.IDENTITY_CONFLICT, ""
        normalized_groups.append(group.strip())
    groups = dedupe_identity_ids(normalized_groups)
    if len(groups) > 1:
        return IdentityResolutionStatus.IDENTITY_CONFLICT, ""
    if groups[0] == resolved_group:
        return IdentityResolutionStatus.RESOLVED, hint_release
    return IdentityResolutionStatus.IDENTITY_CONFLICT, ""


def resolve_album_identity(
    group_candidates: Sequence[ReleaseGroupCandidate],
    edition_candidates: Sequence[ReleaseEditionCandidate],
    evidence: AlbumIdentityEvidence,
) -> AlbumIdentityResolution:
    """ALBUM IDENTITY GATE (R1 + R2, structural).

    - release-group hints: a single hint is authoritative when
      corroborated; multiple DISTINCT same-role hints -> IDENTITY_CONFLICT;
    - without hints, the candidate release-group TITLE must match the
      local album title under canonical normalization — a matching year
      alone is NEVER sufficient (title is a required gate);
    - R2/R3 ARTIST GATE: title + year never identifies the artist. When
      the artist external id is resolved, only candidates whose artist
      credits INCLUDE it survive; otherwise the local album-artist NAME
      must match a candidate credit name; candidates that cannot prove
      compatibility are excluded (fail-closed).
    - R3 NO-ARTIST GATE: WITHOUT any artist compatibility evidence,
      automatic resolution is FORBIDDEN — even a single unique title
      match stays AMBIGUOUS. Only an explicit release-group hint may
      bypass the artist gate;
    - ``first_release_year`` corroborates ONLY among candidates that
      already passed title + artist gates (documented same-artist
      duplicate case); it never creates a match;
    - the release EDITION (``release_id``) stays "" unless a release id
      hint is CORROBORATED by an edition candidate inside the resolved
      release group (R3); a hinted release provably belonging to another
      group is IDENTITY_CONFLICT; title/year can never infer an edition.
    """
    rg_hints = dedupe_identity_ids(evidence.identity_hints.release_group_ids)
    release_hints = dedupe_identity_ids(evidence.identity_hints.release_ids)
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
        # R2 ARTIST GATE: an album title (+ year) NEVER identifies the
        # artist. Candidates that cannot PROVE artist compatibility are
        # excluded (fail-closed, prefer false negative).
        resolved_artist = evidence.resolved_artist_external_id
        local_artist_name = _normalize_identity_text(evidence.local_album_artist_name)
        if resolved_artist:
            eligible = [
                c for c in eligible if resolved_artist in c.artist_credit_external_ids
            ]
            if not eligible:
                return AlbumIdentityResolution(status=IdentityResolutionStatus.NO_MATCH)
        elif local_artist_name:
            eligible = [
                c
                for c in eligible
                if any(
                    _normalize_identity_text(name) == local_artist_name
                    for name in c.artist_credit_names
                )
            ]
            if not eligible:
                return AlbumIdentityResolution(status=IdentityResolutionStatus.NO_MATCH)
        else:
            # R3 NO-ARTIST GATE: automatic album resolution REQUIRES artist
            # compatibility evidence (external id or credit name). A single
            # unique title match is not identity proof — even one candidate
            # stays AMBIGUOUS. Only an explicit release-group hint may
            # bypass this gate.
            return AlbumIdentityResolution(
                status=IdentityResolutionStatus.AMBIGUOUS,
                candidate_ids=tuple(sorted(c.release_group_id for c in eligible)),
            )
        if len(eligible) > 1:
            # Duplicates remain ONLY when the artist gate verified the
            # same artist. Year MAY corroborate (documented R2 semantics —
            # title + artist compatibility gates already established
            # identity); ties stay AMBIGUOUS.
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
        else:
            release_group_id = eligible[0].release_group_id

    release_id = ""
    if len(release_hints) == 1:
        hint_release = release_hints[0]
        # R3 RELEASE CORROBORATION: a Release id is edition-specific and
        # must be correlated to the resolved Release Group.
        if not edition_candidates:
            # CASE A: no edition evidence -> never assign (a lone hint is
            # not corroboration).
            release_id = ""
        else:
            status, release_id = resolve_release_hint_for_group(
                release_group_id, hint_release, edition_candidates
            )
            if status is IdentityResolutionStatus.IDENTITY_CONFLICT:
                return AlbumIdentityResolution(
                    status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                    candidate_ids=(hint_release,),
                )
    return AlbumIdentityResolution(
        status=IdentityResolutionStatus.RESOLVED,
        release_group_id=release_group_id,
        release_id=release_id,
    )


# ---------------------------------------------------------------------------
# 3b. PERSISTENT EXTERNAL IDENTITY AUTHORITY (R1)
# ---------------------------------------------------------------------------


class MatchMethod(Enum):
    """Provenance of a resolved external identity (R1).

    EMBEDDED_HINT — the file itself claimed the external id;
    AUTO — Michi resolved it from structural evidence;
    MANUAL — the user explicitly selected it. MANUAL is authoritative
    over automatic re-resolution and is NEVER represented by
    fabricating identity hints."""

    EMBEDDED_HINT = auto()
    AUTO = auto()
    MANUAL = auto()


class IdentityStatus(Enum):
    """Persistent identity state (R1). Only RESOLVED identities are
    persisted; the other states document why a mapping is absent when a
    future UI needs it. A candidate is NEVER persisted as resolved when
    the domain gate returned AMBIGUOUS."""

    RESOLVED = auto()
    AMBIGUOUS = auto()
    IDENTITY_CONFLICT = auto()
    NOT_FOUND = auto()


@dataclass(frozen=True)
class ArtistExternalIdentity:
    """Durable external identity authority for ONE local artist key.

    Separate from knowledge: the mapping survives knowledge deletion.
    Never added to ArtistRef.

    R2: the manual authority is expressed EXCLUSIVELY by
    ``match_method == MatchMethod.MANUAL`` — the redundant
    ``manually_confirmed`` boolean was removed (schema 3).

    R3.1 INVARIANTS: persistent identity rows represent RESOLVED
    mappings ONLY — AMBIGUOUS / IDENTITY_CONFLICT / NOT_FOUND are
    resolution OUTCOMES, never persistent records. Impossible
    constructions raise ValueError."""

    local_artist_key: str
    external_artist_id: str
    status: IdentityStatus = IdentityStatus.RESOLVED
    match_method: MatchMethod = MatchMethod.AUTO
    resolved_at: str = ""

    def __post_init__(self) -> None:
        # R3.2/R3.2.1: runtime TYPE validation BEFORE any attribute
        # access or string method — a wrong type must raise ValueError,
        # never AttributeError/TypeError.
        if not isinstance(self.status, IdentityStatus):
            raise ValueError(f"status must be an IdentityStatus, got {self.status!r}")
        for field_name in ("local_artist_key", "external_artist_id", "resolved_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise ValueError(
                    f"{field_name} must be str, got {type(value).__name__}"
                )
        if not self.local_artist_key.strip():
            raise ValueError("local_artist_key must not be empty")
        if not self.external_artist_id.strip():
            raise ValueError("external_artist_id must not be empty")
        # R3.2.1: durable external identity must ALREADY be canonical —
        # edge whitespace is rejected, never silently stripped/persisted.
        if self.external_artist_id != self.external_artist_id.strip():
            raise ValueError("external_artist_id must not have edge whitespace")
        if self.status is not IdentityStatus.RESOLVED:
            raise ValueError(
                "persistent identity rows are RESOLVED mappings only; "
                f"got {self.status.name}"
            )
        if not isinstance(self.match_method, MatchMethod):
            raise ValueError("match_method must be a valid MatchMethod")


@dataclass(frozen=True)
class AlbumExternalIdentity:
    """Durable external identity authority for ONE local album key.

    ``release_id`` stays "" unless edition-identifying evidence exists.
    Never added to AlbumRef.

    R3.1 INVARIANTS: RESOLVED mappings only; local key and release group
    non-empty; ``release_id`` MAY be empty (Release Group is the minimum
    external album identity)."""

    local_album_key: str
    release_group_id: str
    release_id: str = ""
    status: IdentityStatus = IdentityStatus.RESOLVED
    match_method: MatchMethod = MatchMethod.AUTO
    resolved_at: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, IdentityStatus):
            raise ValueError(f"status must be an IdentityStatus, got {self.status!r}")
        for field_name in (
            "local_album_key",
            "release_group_id",
            "release_id",
            "resolved_at",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str):
                raise ValueError(
                    f"{field_name} must be str, got {type(value).__name__}"
                )
        if not self.local_album_key.strip():
            raise ValueError("local_album_key must not be empty")
        if not self.release_group_id.strip():
            raise ValueError("release_group_id must not be empty")
        if self.release_group_id != self.release_group_id.strip():
            raise ValueError("release_group_id must not have edge whitespace")
        if self.release_id and not self.release_id.strip():
            raise ValueError("release_id must not be whitespace-only")
        if self.release_id != self.release_id.strip():
            raise ValueError("release_id must not have edge whitespace")
        if self.status is not IdentityStatus.RESOLVED:
            raise ValueError(
                "persistent identity rows are RESOLVED mappings only; "
                f"got {self.status.name}"
            )
        if not isinstance(self.match_method, MatchMethod):
            raise ValueError("match_method must be a valid MatchMethod")


# ---------------------------------------------------------------------------
# 4. EXTERNAL KNOWLEDGE / ENRICHMENT PROFILES
# ---------------------------------------------------------------------------


class EnrichmentEntityKind(Enum):
    """Entity kind of an asynchronous enrichment operation."""

    ARTIST = auto()
    ALBUM = auto()


@dataclass(frozen=True)
class KnowledgeProvenance:
    """Structured provenance of one externally acquired knowledge payload
    (R1). Empty fields mean UNKNOWN — never fabricate values. Individual
    payloads may come from different sources than the identity (identity:
    MusicBrainz, biography: Wikipedia, image: Wikimedia Commons), so
    profiles may carry per-field provenance where semantics differ."""

    provider: str = ""
    external_entity_id: str = ""
    source_url: str = ""
    retrieved_at: str = ""
    language: str = ""
    license: str = ""
    license_url: str = ""
    attribution: str = ""
    is_stale: bool = False  # R1: truthfully marks stale-cache knowledge


@dataclass(frozen=True)
class ArtistKnowledgeProfile:
    """Downloaded artist knowledge, joined by LOCAL artist key.

    Stored exclusively in enrichment.db. External fields (biography,
    external genres, external dates, artwork asset id) live ONLY here —
    never in TrackMetadata/ArtistRef, never written into audio files.
    R1: NO async lifecycle state (generation/request ids/pending state)
    may ever live here — this is data, not request state. Provenance is
    structured; the biography may carry its own provenance."""

    local_artist_key: str
    external_artist_id: str
    biography: str = ""
    external_genres: tuple[str, ...] = ()
    begin_year: int = 0
    end_year: int = 0
    artwork_asset_id: str = ""
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)
    biography_provenance: KnowledgeProvenance = field(
        default_factory=KnowledgeProvenance
    )
    # M6.9E typed external knowledge (all provider-attributable via
    # provenance; never canonical local metadata).
    sort_name: str = ""
    artist_type: str = ""
    area: str = ""
    official_website: str = ""
    wikipedia_page_title: str = ""
    wikipedia_language: str = ""
    commons_image_title: str = ""
    # R1 provenance-by-provider: Wikidata facts carry their OWN
    # provenance and never overwrite MusicBrainz facts (begin/end stay
    # MusicBrainz-owned).
    country_qid: str = ""
    country_label: str = ""
    wikidata_begin_year: int = 0
    wikidata_end_year: int = 0
    wikidata_provenance: KnowledgeProvenance = field(
        default_factory=KnowledgeProvenance
    )


@dataclass(frozen=True)
class AlbumKnowledgeProfile:
    """Downloaded album knowledge, joined by LOCAL album key.

    ``first_release_year`` / ``release_year`` are EXTERNAL dates — the
    local TrackMetadata.year and AlbumRef.year are never touched.
    ``external_genres`` never merge into local GenreRef values.
    ``release_id`` stays "" unless edition-identifying evidence exists.
    R1 release-level rule: ``release_year`` and ``label`` are
    RELEASE-level facts — they must stay "" unless ``release_id``
    identifies the specific edition (enforced invariant)."""

    local_album_key: str
    release_group_id: str
    release_id: str = ""
    external_genres: tuple[str, ...] = ()
    first_release_year: int = 0
    release_year: int = 0
    label: str = ""
    artwork_asset_id: str = ""
    provenance: KnowledgeProvenance = field(default_factory=KnowledgeProvenance)

    def __post_init__(self) -> None:
        if not self.release_id and (self.release_year or self.label):
            raise ValueError(
                "release-level facts (release_year/label) require a "
                "specific release identity (release_id)"
            )


# ---------------------------------------------------------------------------
# 4a. PROVIDER EXTERNAL-KNOWLEDGE DTOS (M6.9E — pure, typed, provenance-bound)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArtistExternalLinks:
    """Verified identity links discovered through MusicBrainz URL
    relationships — the ONLY lawful bridge to Wikidata/Wikipedia.
    R1.1: freshness rides along so stale links can never masquerade as
    fresh (the coordinator marks PARTIAL when they are stale)."""

    wikidata_qid: str = ""
    wikipedia_title: str = ""
    wikipedia_language: str = ""
    retrieved_at: str = ""
    is_stale: bool = False


@dataclass(frozen=True)
class WikidataArtistClaims:
    """Deterministic/fail-closed Wikidata facts for a VERIFIED QID.
    Ambiguous multi-claims stay unresolved (empty). R1: country is a
    QID (never disguised as a label); freshness rides along truthfully."""

    country_qid: str = ""
    country_label: str = ""
    official_website: str = ""
    commons_image_title: str = ""
    wikipedia_title: str = ""
    wikipedia_language: str = ""
    begin_year: int = 0
    end_year: int = 0
    retrieved_at: str = ""
    is_stale: bool = False


@dataclass(frozen=True)
class BiographyKnowledge:
    """Bounded Wikipedia biography extract (never raw HTML)."""

    text: str = ""
    page_title: str = ""
    source_url: str = ""
    language: str = ""
    license: str = ""
    attribution: str = ""
    retrieved_at: str = ""
    is_stale: bool = False


@dataclass(frozen=True)
class CommonsImageKnowledge:
    """Verified Wikimedia Commons image metadata (URL + license facts)."""

    source_url: str = ""
    license: str = ""
    license_url: str = ""
    artist: str = ""
    attribution: str = ""
    retrieved_at: str = ""
    is_stale: bool = False


@dataclass(frozen=True)
class CoverArtKnowledge:
    """Cover Art Archive external-cover metadata (fallback authority).
    R1.1: freshness rides along (is_stale/retrieved_at)."""

    image_url: str = ""
    entity_kind: str = ""  # "release" | "release-group"
    retrieved_at: str = ""
    is_stale: bool = False


# ---------------------------------------------------------------------------
# 4b. EXTERNAL ASSET RECORD (R1 — provenance + validation foundation)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichmentAssetRecord:
    """Provenance + metadata record for ONE downloaded external asset.

    The asset store fills ``checksum`` / ``width`` / ``height`` /
    ``managed_object`` during validation+storage; the caller supplies
    provenance fields. Never a path derived from remote titles: the
    caller-supplied ``asset_id`` is strictly validated (digest-safe).

    R2: ``managed_object`` is a RELATIVE, content-addressed storage key
    (e.g. "objects/<sha256>.png") — NEVER an absolute runtime path.
    Absolute paths would break backup/restore/data-root migration."""

    asset_id: str
    entity_kind: EnrichmentEntityKind
    external_entity_id: str
    mime_type: str
    checksum: str = ""
    provider: str = ""
    source_url: str = ""
    creator: str = ""
    license: str = ""
    license_url: str = ""
    attribution: str = ""
    width: int = 0
    height: int = 0
    managed_object: str = ""


# ---------------------------------------------------------------------------
# ASYNC ENTITY-CORRELATION FIREWALL
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichmentRequest:
    """Immutable correlation context for ONE async enrichment operation.

    Every operation carries exactly this context; a result may be committed
    ONLY if it still matches it (see ``EnrichmentRequestLedger``). Never
    correlate async results through mutable globals like ``_active_artist``.

    R2 RELEASE-EDITION CORRELATION: ``external_variant_id`` identifies the
    specific release edition when one exists:
    ARTIST: "" (external_entity_id is the artist MBID);
    ALBUM:   release MBID when the edition is known, else ""."""

    request_id: str
    entity_kind: EnrichmentEntityKind
    local_entity_key: str
    external_entity_id: str
    external_variant_id: str = ""
    generation: int = 0


class DeliveryVerdict(Enum):
    """Commit decision for a delivered async enrichment result.

    R3: COMMITTED means the profile was ACTUALLY persisted — a failed
    persistence write yields STORAGE_FAILED (terminal; the request is
    consumed and never resurrected automatically)."""

    COMMITTED = auto()
    STALE = auto()
    UNKNOWN = auto()
    MISMATCHED = auto()
    STORAGE_FAILED = auto()


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
        STALE — superseded by a newer request or explicitly invalidated
        (out-of-order / stale identity); UNKNOWN — never registered."""
        key = self._key(request)
        current = self._current.get(key)
        if current is not None and current.request_id == request.request_id:
            del self._current[key]
            return DeliveryVerdict.COMMITTED
        if request.request_id in self._superseded.get(key, ()):
            return DeliveryVerdict.STALE
        return DeliveryVerdict.UNKNOWN

    def invalidate(
        self, entity_kind: EnrichmentEntityKind, local_entity_key: str
    ) -> None:
        """R2: make the current pending request for an entity
        non-committable (identity reset / change / clear). The invalidated
        id is recorded as superseded so a late delivery yields STALE —
        never COMMITTED, never silently forgotten."""
        key = (entity_kind, local_entity_key)
        current = self._current.pop(key, None)
        if current is None:
            return
        superseded = self._superseded.setdefault(
            key, deque(maxlen=self._SUPERSEDED_CAP)
        )
        superseded.append(current.request_id)

    def invalidate_if_current(
        self,
        entity_kind: EnrichmentEntityKind,
        local_entity_key: str,
        expected_request_id: str,
        expected_generation: int,
    ) -> bool:
        """R1.2 EXACT REQUEST INVALIDATION: invalidate ONLY the request
        whose request_id AND generation match the current one. A stale
        worker (older generation or an already-replaced request) can
        NEVER invalidate a newer request — returns False in that case."""
        key = (entity_kind, local_entity_key)
        current = self._current.get(key)
        if current is None:
            return False
        if (
            current.request_id != expected_request_id
            or current.generation != expected_generation
        ):
            return False
        superseded = self._superseded.setdefault(
            key, deque(maxlen=self._SUPERSEDED_CAP)
        )
        superseded.append(current.request_id)
        del self._current[key]
        return True

    def invalidate_all(self) -> None:
        """R2: invalidate every pending request (clear-identities)."""
        for key, request in list(self._current.items()):
            superseded = self._superseded.setdefault(
                key, deque(maxlen=self._SUPERSEDED_CAP)
            )
            superseded.append(request.request_id)
        self._current.clear()

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
_NESTED_PROVENANCE_FIELDS = {
    name
    for name, f in (
        ArtistKnowledgeProfile.__dataclass_fields__
        | AlbumKnowledgeProfile.__dataclass_fields__
    ).items()
    if f.type is KnowledgeProvenance
}


def encode_artist_profile(profile: ArtistKnowledgeProfile) -> str:
    """Deterministic strict JSON of an artist knowledge profile."""
    return json.dumps(asdict(profile), sort_keys=True)


def encode_album_profile(profile: AlbumKnowledgeProfile) -> str:
    """Deterministic strict JSON of an album knowledge profile."""
    return json.dumps(asdict(profile), sort_keys=True)


def _decode_provenance(value) -> KnowledgeProvenance | None:
    """Strict nested provenance decode. R1: ``is_stale`` is OPTIONAL on
    decode (historical rows without it decode as False — backward
    compatible, no schema change)."""
    if not isinstance(value, dict):
        return None
    kwargs = {}
    for name, item in value.items():
        if name not in KnowledgeProvenance.__dataclass_fields__:
            continue  # future field — tolerated
        if name == "is_stale":
            if not isinstance(item, bool):
                return None
        elif not isinstance(item, str):
            return None
        kwargs[name] = item
    missing = set(KnowledgeProvenance.__dataclass_fields__) - set(kwargs)
    if missing and missing != {"is_stale"}:
        return None
    if "is_stale" not in kwargs:
        kwargs["is_stale"] = False
    return KnowledgeProvenance(**kwargs)


def _decode_profile(
    raw, model, str_fields, int_fields, tuple_fields, nested_fields, optional_fields=()
):
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
        elif name in nested_fields:
            nested = _decode_provenance(value)
            if nested is None:
                return None
            value = nested
        else:
            return None
        kwargs[name] = value
    missing = set(model.__dataclass_fields__) - set(kwargs)
    # M6.9E: profile-extension fields are OPTIONAL on decode so that
    # historical (R1/R2/R3-era) persisted profiles remain readable;
    # every pre-extension field stays strictly required.
    if not missing.issubset(set(optional_fields)):
        return None  # missing required field(s)
    return model(**kwargs)


_ARTIST_OPTIONAL_FIELDS = {
    "sort_name",
    "artist_type",
    "area",
    "official_website",
    "wikipedia_page_title",
    "wikipedia_language",
    "commons_image_title",
    "country_qid",
    "country_label",
    "wikidata_begin_year",
    "wikidata_end_year",
    "wikidata_provenance",
}


def decode_artist_profile(raw: str) -> ArtistKnowledgeProfile | None:
    """Strict decode; any violation returns None (skip, never fabricate).
    M6.9E extension fields are optional (historical rows stay valid)."""
    return _decode_profile(
        raw,
        ArtistKnowledgeProfile,
        _ARTIST_STR_FIELDS,
        _ARTIST_INT_FIELDS,
        _ARTIST_TUPLE_FIELDS,
        _NESTED_PROVENANCE_FIELDS,
        _ARTIST_OPTIONAL_FIELDS,
    )


def decode_album_profile(raw: str) -> AlbumKnowledgeProfile | None:
    """Strict decode; any violation returns None (skip, never fabricate)."""
    return _decode_profile(
        raw,
        AlbumKnowledgeProfile,
        _ALBUM_STR_FIELDS,
        _ALBUM_INT_FIELDS,
        _ALBUM_TUPLE_FIELDS,
        _NESTED_PROVENANCE_FIELDS,
    )
