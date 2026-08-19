"""M7 — Rich Canonical Local Search — pure domain module.

Search is a DETERMINISTIC DERIVED PROJECTION of the canonical M6 model.
It never redefines album/artist/compilation identity, never touches the
filesystem, never reads metadata, and never persists anything.

CANONICAL LIBRARY = SOURCE OF TRUTH
SEARCH = DETERMINISTIC DERIVED PROJECTION
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum, auto

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_search_text(text: str) -> str:
    """Normalize text for MATCHING (search representation — never writeback).

    Pipeline: Unicode NFKD -> strip combining marks (accent-insensitive:
    "Beyoncé" == "beyonce") -> casefold ("MILES" == "miles", "ß" == "ss")
    -> collapse whitespace -> strip. Deterministic and pure.
    """
    decomposed = unicodedata.normalize("NFKD", text or "")
    no_diacritics = "".join(
        ch for ch in decomposed if not unicodedata.combining(ch)
    )
    return _WHITESPACE_RE.sub(" ", no_diacritics.casefold()).strip()


def tokenize_search_text(text: str) -> tuple[str, ...]:
    """Whitespace tokens of the normalized text; never empty tokens."""
    normalized = normalize_search_text(text)
    if not normalized:
        return ()
    return tuple(normalized.split(" "))


@dataclass(frozen=True)
class SearchQuery:
    """Pure immutable query: raw (presentation) + normalized (matching).

    ``active`` is False when there are no tokens (empty/whitespace query):
    search is then inactive and the canonical collections pass through.
    """

    raw: str
    normalized: str
    tokens: tuple[str, ...]

    @classmethod
    def from_raw(cls, raw: str) -> "SearchQuery":
        text = raw or ""
        return cls(
            raw=text,
            normalized=normalize_search_text(text),
            tokens=tokenize_search_text(text),
        )

    @property
    def active(self) -> bool:
        return bool(self.tokens)


class SearchMatchType(Enum):
    """Deterministic match categories (no fuzzy/typo-correction in M7 1.0)."""

    EXACT = auto()
    PREFIX = auto()
    TOKEN_PREFIX = auto()
    SUBSTRING = auto()
    NONE = auto()


def match_token_to_field(token: str, field: str) -> SearchMatchType:
    """Match one normalized token against one normalized field.

    EXACT: token == field; PREFIX: field starts with token; TOKEN_PREFIX:
    some whitespace-delimited word of the field starts with token; else
    SUBSTRING when the token appears anywhere in the field; NONE."""
    if not token or not field:
        return SearchMatchType.NONE
    if token == field:
        return SearchMatchType.EXACT
    if field.startswith(token):
        return SearchMatchType.PREFIX
    if any(word.startswith(token) for word in field.split(" ")):
        return SearchMatchType.TOKEN_PREFIX
    if token in field:
        return SearchMatchType.SUBSTRING
    return SearchMatchType.NONE


# Deterministic relevance weights (documented in M7_SEARCH_MASTER_PLAN.md).
# Field priority: title > artist ≈ album_artist > album > composer > genre
# > display_name. A garbage multi-field substring can never outrank an
# exact title (2 tokens of substring ≈ 2×700 < exact title 1600).
_FIELD_PRIORITY = {
    "title": 600,
    "artist": 500,
    "album_artist": 500,
    "album": 400,
    "composer": 300,
    "genre": 250,
    "display_name": 100,
}
_TYPE_BONUS = {
    SearchMatchType.EXACT: 1000,
    SearchMatchType.PREFIX: 700,
    SearchMatchType.TOKEN_PREFIX: 500,
    SearchMatchType.SUBSTRING: 300,
}


@dataclass(frozen=True)
class TrackSearchDocument:
    """Search representation of a canonical TrackRef — NOT a new entity.
    Holds the canonical reference (identity only, no copy) plus the
    pre-normalized searchable fields."""

    track: object  # canonical TrackRef
    norm_title: str = ""
    norm_artist: str = ""
    norm_album: str = ""
    norm_album_artist: str = ""
    norm_genre: str = ""
    norm_composer: str = ""
    norm_display_name: str = ""

    @property
    def track_id(self) -> str:
        return str(self.track.file_path)

    @classmethod
    def from_track(cls, track) -> "TrackSearchDocument":
        return cls(
            track=track,
            norm_title=normalize_search_text(track.title),
            norm_artist=normalize_search_text(track.artist),
            norm_album=normalize_search_text(track.album),
            norm_album_artist=normalize_search_text(track.album_artist),
            norm_genre=normalize_search_text(track.genre),
            norm_composer=normalize_search_text(track.composer),
            norm_display_name=normalize_search_text(track.display_name),
        )

    def _fields(self):
        # FIXED iteration order: deterministic first-wins on score ties.
        return (
            ("title", self.norm_title),
            ("artist", self.norm_artist),
            ("album_artist", self.norm_album_artist),
            ("album", self.norm_album),
            ("composer", self.norm_composer),
            ("genre", self.norm_genre),
            ("display_name", self.norm_display_name),
        )

    def match_token(self, token: str) -> tuple[SearchMatchType, str, int]:
        """Best (match_type, field, score) for the token across ALL fields."""
        best_type = SearchMatchType.NONE
        best_field = ""
        best_score = 0
        for field, value in self._fields():
            match_type = match_token_to_field(token, value)
            if match_type is SearchMatchType.NONE:
                continue
            score = _FIELD_PRIORITY[field] + _TYPE_BONUS[match_type]
            if score > best_score:  # strictly greater: fixed order breaks ties
                best_type = match_type
                best_field = field
                best_score = score
        return best_type, best_field, best_score

    def total_score(self, tokens: tuple[str, ...]) -> int:
        total = 0
        for token in tokens:
            _, _, score = self.match_token(token)
            if score == 0:
                return 0  # AND semantics: every token must match somewhere
            total += score
        return total


@dataclass(frozen=True)
class EntitySearchDocument:
    """Search representation of a canonical entity (AlbumRef/ArtistRef/
    GenreRef/ComposerRef) — reference + pre-normalized searchable fields.

    Albums: name=title plus artist (album artist), composers and genres as
    extra fields. Artists/Genres/Composers: name only (no relation
    expansion — tracks appear as track results, not entity results)."""

    entity: object  # canonical AlbumRef/ArtistRef/GenreRef/ComposerRef
    key: str
    name: str
    norm_name: str = ""
    extra: tuple[tuple[str, str], ...] = ()  # (field, NORMALIZED value)

    def match_token(self, token: str) -> tuple[SearchMatchType, str, int]:
        best_type = SearchMatchType.NONE
        best_field = ""
        best_score = 0
        for field, value in (("name", self.norm_name), *self.extra):
            match_type = match_token_to_field(token, value)
            if match_type is SearchMatchType.NONE:
                continue
            score = _FIELD_PRIORITY.get(field, 100) + _TYPE_BONUS[match_type]
            if score > best_score:
                best_type = match_type
                best_field = field
                best_score = score
        return best_type, best_field, best_score

    def total_score(self, tokens: tuple[str, ...]) -> int:
        total = 0
        for token in tokens:
            _, _, score = self.match_token(token)
            if score == 0:
                return 0  # AND semantics
            total += score
        return total


def _album_document(album) -> EntitySearchDocument:
    return EntitySearchDocument(
        entity=album,
        key=album.key,
        name=album.title,
        norm_name=normalize_search_text(album.title),
        extra=(
            ("artist", normalize_search_text(album.artist)),
            ("composer", normalize_search_text(" ".join(album.composers))),
            ("genre", normalize_search_text(" ".join(album.genres))),
        ),
    )


def _named_document(entity) -> EntitySearchDocument:
    return EntitySearchDocument(
        entity=entity, key=entity.key, name=entity.name,
        norm_name=normalize_search_text(entity.name),
    )


@dataclass(frozen=True)
class SearchCorpus:
    """Derived pre-normalized search documents.

    Built ONLY when the canonical library changes; a query change just
    matches against the corpus. Never persisted — rebuildable from the M6
    canonical model at any time."""

    tracks: tuple[TrackSearchDocument, ...] = ()
    albums: tuple[EntitySearchDocument, ...] = ()
    artists: tuple[EntitySearchDocument, ...] = ()
    genres: tuple[EntitySearchDocument, ...] = ()
    composers: tuple[EntitySearchDocument, ...] = ()

    @classmethod
    def from_tracks(cls, tracks) -> "SearchCorpus":
        return cls(tracks=tuple(TrackSearchDocument.from_track(t) for t in tracks))


def build_search_corpus(
    tracks,
    albums=(),
    artists=(),
    genres=(),
    composers=(),
) -> SearchCorpus:
    """Build the derived corpus from the canonical M6 collections."""
    return SearchCorpus(
        tracks=tuple(TrackSearchDocument.from_track(t) for t in tracks),
        albums=tuple(_album_document(a) for a in albums),
        artists=tuple(_named_document(a) for a in artists),
        genres=tuple(_named_document(g) for g in genres),
        composers=tuple(_named_document(c) for c in composers),
    )


@dataclass(frozen=True)
class SearchProjection:
    """Deterministic derived search results over the canonical model."""

    query: SearchQuery
    tracks: tuple = ()
    albums: tuple = ()
    artists: tuple = ()
    genres: tuple = ()
    composers: tuple = ()

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    @property
    def album_count(self) -> int:
        return len(self.albums)

    @property
    def artist_count(self) -> int:
        return len(self.artists)

    @property
    def genre_count(self) -> int:
        return len(self.genres)

    @property
    def composer_count(self) -> int:
        return len(self.composers)

    @property
    def total_count(self) -> int:
        return (
            self.track_count
            + self.album_count
            + self.artist_count
            + self.genre_count
            + self.composer_count
        )

    @property
    def matched_track_ids(self) -> frozenset[str]:
        return frozenset(str(t.file_path) for t in self.tracks)


def _ranked_entities(query: SearchQuery, docs) -> tuple:
    """Deterministic entity ordering: score desc -> canonical name -> key."""
    scored = []
    for doc in docs:
        score = doc.total_score(query.tokens)
        if score == 0:
            continue
        scored.append((score, doc))
    scored.sort(key=lambda pair: (-pair[0], pair[1].norm_name, pair[1].key))
    return tuple(doc.entity for _, doc in scored)


def build_search_projection(query: SearchQuery, corpus: SearchCorpus) -> SearchProjection:
    """Pure projector: score the corpus against the query.

    Track ordering: score desc -> canonical display sort (title/sort_title
    casefold, then path) -> canonical ID. NEVER input order."""
    if not query.active:
        return SearchProjection(query=query)
    scored = []
    for doc in corpus.tracks:
        score = doc.total_score(query.tokens)
        if score == 0:
            continue
        scored.append((score, doc))
    scored.sort(key=lambda pair: (-pair[0], pair[1].norm_title, pair[1].track_id))
    return SearchProjection(
        query=query,
        tracks=tuple(doc.track for _, doc in scored),
        albums=_ranked_entities(query, corpus.albums),
        artists=_ranked_entities(query, corpus.artists),
        genres=_ranked_entities(query, corpus.genres),
        composers=_ranked_entities(query, corpus.composers),
    )
