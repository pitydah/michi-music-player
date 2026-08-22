"""Enrichment bounded contexts — pure domain, no Qt/infra dependencies.

M6.9A METADATA/ENRICHMENT FIREWALL. Five distinct bounded contexts:

1. LOCAL FILE METADATA ......... ``michi.domain.library`` (TrackMetadata,
   TrackRef, AlbumRef, ArtistRef, MusicModel) — the ONLY canonical carrier
   of media-file tags and local technical stream facts.
2. LOCAL EXTERNAL IDENTITY HINTS ``ExternalIdentityHints`` — MusicBrainz
   ids that may already exist inside local tags. Local identity EVIDENCE,
   never canonical musical metadata.
3. RESOLVED EXTERNAL IDENTITY .. ``IdentityResolution`` /
   ``AlbumIdentityResolution`` — the fail-closed mapping from local
   evidence to an external entity id.
4. EXTERNAL KNOWLEDGE .......... ``ArtistKnowledgeProfile`` /
   ``AlbumKnowledgeProfile`` — downloaded enrichment stored exclusively in
   enrichment.db. Never merged into context 1/2 models.
5. METADATA EDITING ............ FUTURE — never implemented here.

ONE-WAY DATA FLOW: canonical local library -> local evidence -> identity
resolver -> external knowledge. NO reverse propagation: external knowledge
can never mutate TrackMetadata, AlbumRef/ArtistRef, library_index, or
audio file tags.

Every asynchronous enrichment operation carries immutable correlation
(``EnrichmentRequest``): a result may be committed ONLY while it still
matches its original request context (``EnrichmentRequestLedger``).
Stale/out-of-order responses are discarded — no mutable
_active_artist/_current_album-style globals may ever be used.
"""

import json
from collections import deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum, auto

# ---------------------------------------------------------------------------
# 2. LOCAL EXTERNAL IDENTITY HINTS
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalIdentityHints:
    """Identity hints that may exist inside FLAC/MP3/M4A tags.

    PURE LOCAL EVIDENCE about which external entity a file claims to be.
    NOT canonical musical metadata: these fields must NEVER be added to
    TrackMetadata. Actual tag extraction belongs to a later explicitly
    authorized WP — M6.9A only defines the carrier and the gates.
    """

    musicbrainz_artist_ids: tuple[str, ...] = ()
    musicbrainz_album_artist_ids: tuple[str, ...] = ()
    musicbrainz_release_id: str = ""
    musicbrainz_release_group_id: str = ""
    musicbrainz_recording_id: str = ""
    musicbrainz_release_track_id: str = ""

    def combined_artist_ids(self) -> tuple[str, ...]:
        """Distinct artist-level hint ids (track artist + album artist),
        preserving first-seen order."""
        seen: list[str] = []
        for hint_id in (
            *self.musicbrainz_artist_ids,
            *self.musicbrainz_album_artist_ids,
        ):
            if hint_id and hint_id not in seen:
                seen.append(hint_id)
        return tuple(seen)


@dataclass(frozen=True)
class IdentityEvidence:
    """Local corroborating evidence for identity resolution.

    Album titles and years come from the canonical local library ONLY.
    ``identity_hints`` are the optional tag-embedded ids (context 2)."""

    local_album_titles: tuple[str, ...] = ()
    local_years: tuple[int, ...] = ()
    identity_hints: ExternalIdentityHints = field(default_factory=ExternalIdentityHints)


# ---------------------------------------------------------------------------
# 3. RESOLVED EXTERNAL IDENTITY — fail-closed gates
# ---------------------------------------------------------------------------


class IdentityResolutionStatus(Enum):
    """Fail-closed resolution taxonomy (M6.9A).

    AMBIGUOUS and IDENTITY_CONFLICT are terminal non-resolutions: no
    enrichment profile may ever be attached on either."""

    RESOLVED = auto()
    AMBIGUOUS = auto()
    IDENTITY_CONFLICT = auto()
    NO_MATCH = auto()


@dataclass(frozen=True)
class ArtistCandidate:
    """One remote artist candidate returned by the resolver, with the
    evidence that could corroborate a match against local data."""

    external_artist_id: str
    album_titles: tuple[str, ...] = ()
    years: tuple[int, ...] = ()


@dataclass(frozen=True)
class ReleaseGroupCandidate:
    """One remote release-group candidate (album identity context)."""

    release_group_id: str
    title: str = ""
    release_titles: tuple[str, ...] = ()
    first_release_year: int = 0


@dataclass(frozen=True)
class ReleaseEditionCandidate:
    """One specific release edition inside a release group.

    Edition evidence is ONLY ever an explicit embedded release id — album
    title + artist can never identify one specific edition (M6.9A)."""

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
    (an embedded release id hint) specifically identifies the edition."""

    status: IdentityResolutionStatus
    release_group_id: str = ""
    release_id: str = ""
    candidate_ids: tuple[str, ...] = ()


def _normalize_identity_text(raw: str) -> str:
    """Casefold + whitespace collapse — same semantics as the local keys."""
    return " ".join(raw.casefold().split())


def _match_score(
    candidate_titles: Sequence[str],
    candidate_years: Sequence[int],
    evidence: IdentityEvidence,
) -> int:
    """Count of corroborating local facts (titles and years)."""
    local_titles = {_normalize_identity_text(t) for t in evidence.local_album_titles}
    local_years = set(evidence.local_years)
    score = 0
    for title in candidate_titles:
        if _normalize_identity_text(title) in local_titles:
            score += 1
    for year in candidate_years:
        if year in local_years:
            score += 1
    return score


def _resolve_by_evidence(
    candidates: Sequence[tuple[int, str]],
    status_type: type,
) -> "IdentityResolution":
    """Shared evidence-matching core: unique best match wins; ties stay
    AMBIGUOUS; a single non-matching candidate is NO_MATCH; MULTIPLE
    non-matching candidates remain plausible -> AMBIGUOUS (fail-closed:
    several candidates may still be the right one)."""
    if not candidates:
        return status_type(status=IdentityResolutionStatus.NO_MATCH)
    best = max(score for score, _ in candidates)
    if best == 0:
        if len(candidates) == 1:
            return status_type(status=IdentityResolutionStatus.NO_MATCH)
        return status_type(
            status=IdentityResolutionStatus.AMBIGUOUS,
            candidate_ids=tuple(sorted(eid for _, eid in candidates)),
        )
    top = [external_id for score, external_id in candidates if score == best]
    if len(top) > 1:
        return status_type(
            status=IdentityResolutionStatus.AMBIGUOUS,
            candidate_ids=tuple(sorted(top)),
        )
    return status_type(
        status=IdentityResolutionStatus.RESOLVED, external_entity_id=top[0]
    )


def resolve_artist_identity(
    candidates: Sequence[ArtistCandidate],
    evidence: IdentityEvidence,
) -> IdentityResolution:
    """ARTIST HOMONYM GATE + IDENTITY CONFLICT GATE (fail-closed).

    Canonical ArtistRef identity is the normalized local name, so identical
    names can be different real-world artists. Auto-match by name alone is
    FORBIDDEN:

    - conflicting embedded hints -> IDENTITY_CONFLICT (never pick first /
      majority / most popular);
    - a single hint is authoritative when corroborated, else CONFLICT;
    - without hints, only strong corroborating evidence (album titles,
      years) may resolve — and only when exactly one candidate wins;
    - anything else -> AMBIGUOUS / NO_MATCH: no profile is attached.
    """
    hint_ids = evidence.identity_hints.combined_artist_ids()
    if len(hint_ids) > 1:
        return IdentityResolution(
            status=IdentityResolutionStatus.IDENTITY_CONFLICT,
            candidate_ids=tuple(hint_ids),
        )
    if len(hint_ids) == 1:
        hint_id = hint_ids[0]
        candidate_ids = {c.external_artist_id for c in candidates}
        if candidate_ids and hint_id not in candidate_ids:
            return IdentityResolution(
                status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                candidate_ids=tuple(sorted(candidate_ids | {hint_id})),
            )
        return IdentityResolution(
            status=IdentityResolutionStatus.RESOLVED, external_entity_id=hint_id
        )
    if not evidence.local_album_titles and not evidence.local_years:
        # Name alone can never identify a real-world artist.
        return IdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)
    scored = [
        (_match_score(c.album_titles, c.years, evidence), c.external_artist_id)
        for c in candidates
    ]
    return _resolve_by_evidence(scored, IdentityResolution)


def resolve_album_identity(
    group_candidates: Sequence[ReleaseGroupCandidate],
    edition_candidates: Sequence[ReleaseEditionCandidate],
    evidence: IdentityEvidence,
) -> AlbumIdentityResolution:
    """ALBUM IDENTITY GATE (M6.9A).

    The local AlbumRef key (title + resolved album artist) maps naturally
    to a MusicBrainz RELEASE GROUP — never to one specific Release edition.

    - release group: strong evidence (hint, or unique title/year match)
      may resolve; ties stay AMBIGUOUS; disagreeing hints CONFLICT;
    - release edition: ``release_id`` stays "" unless an embedded
      ``musicbrainz_release_id`` hint specifically identifies the edition
      and corroborates the resolved group. Downloaded release date/label
      info must never overwrite local album year (never even offered).
    """
    hint_rg = evidence.identity_hints.musicbrainz_release_group_id
    hint_release = evidence.identity_hints.musicbrainz_release_id
    release_group_id = ""
    if hint_rg:
        candidate_ids = {c.release_group_id for c in group_candidates}
        if candidate_ids and hint_rg not in candidate_ids:
            return AlbumIdentityResolution(
                status=IdentityResolutionStatus.IDENTITY_CONFLICT,
                candidate_ids=tuple(sorted(candidate_ids | {hint_rg})),
            )
        release_group_id = hint_rg
    elif not evidence.local_album_titles and not evidence.local_years:
        # Title+artist alone is not sufficient identity evidence.
        return AlbumIdentityResolution(status=IdentityResolutionStatus.AMBIGUOUS)
    else:
        scored = [
            (
                _match_score(
                    (c.title, *c.release_titles),
                    (c.first_release_year,) if c.first_release_year > 0 else (),
                    evidence,
                ),
                c.release_group_id,
            )
            for c in group_candidates
        ]
        resolution = _resolve_by_evidence(scored, IdentityResolution)
        if resolution.status is not IdentityResolutionStatus.RESOLVED:
            return AlbumIdentityResolution(
                status=resolution.status, candidate_ids=resolution.candidate_ids
            )
        release_group_id = resolution.external_entity_id

    release_id = ""
    if hint_release:
        if not edition_candidates:
            release_id = hint_release
        else:
            corroborated = [
                e
                for e in edition_candidates
                if e.release_id == hint_release
                and (not release_group_id or e.release_group_id == release_group_id)
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
    never in TrackMetadata/ArtistRef, never written into audio files."""

    local_artist_key: str
    external_artist_id: str
    biography: str = ""
    external_genres: tuple[str, ...] = ()
    begin_year: int = 0
    end_year: int = 0
    artwork_asset_id: str = ""
    source: str = ""
    generation: int = 0


@dataclass(frozen=True)
class AlbumKnowledgeProfile:
    """Downloaded album knowledge, joined by LOCAL album key.

    ``first_release_year`` / ``release_year`` are EXTERNAL dates — the
    local TrackMetadata.year and AlbumRef.year are never touched.
    ``external_genres`` never merge into local GenreRef values.
    ``release_id`` stays "" unless edition-identifying evidence exists."""

    local_album_key: str
    release_group_id: str
    release_id: str = ""
    external_genres: tuple[str, ...] = ()
    first_release_year: int = 0
    release_year: int = 0
    label: str = ""
    artwork_asset_id: str = ""
    source: str = ""
    generation: int = 0


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
    """Pending-request correlation registry (M6.9A).

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
