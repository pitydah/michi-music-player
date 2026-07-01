"""Genre normalizer — clean, deduplicate, canonicalize, split, and detect issues.

This module provides both in-memory normalization and rules for persistent alias
management. All functions are pure (no side effects) for testability.
"""
from __future__ import annotations

import re
import unicodedata

# ── Delimiter patterns for multi-genre strings ──

_DELIM_RE = re.compile(r"\s*[,;/|&+]\s*")

# Known compound genres that should NOT be split on certain delimiters
_COMPOUND_GENRES = frozenset({
    "r&b", "drum & bass", "rock & roll", "hip-hop/rap",
    "singer/songwriter", "drum n bass", "drum and bass",
    "dnb", "d&b", "trip-hop", "post-punk", "post-rock",
    "post-hardcore", "post-metal", "post-black",
    "slow-core", "slowcore", "noise-rock", "noise rock",
    "math-rock", "math rock", "art-rock", "art rock",
    "garage-rock", "garage rock", "surf-rock", "surf rock",
    "psych-rock", "psychedelic rock", "stoner-rock", "stoner rock",
    "desert-rock", "desert rock", "krautrock",
    "emo-pop", "emo-pop punk", "pop-punk", "pop punk",
    "shoegaze", "dream-pop", "dream pop",
    "synth-pop", "synth pop", "synthpop",
    "electro-pop", "electro pop", "electropop",
    "indie-pop", "indie pop", "indie-rock", "indie rock",
    "alternative-rock", "alternative rock",
    "progressive-rock", "progressive rock",
    "new-wave", "new wave", "dark-wave", "darkwave",
    "cold-wave", "cold wave", "ethereal-wave", "ethereal wave",
    "chill-wave", "chillwave", "vaporwave",
    "lo-fi", "lofi", "hi-fi",
    "neo-soul", "neo soul", "neo-classical", "neoclassical",
    "neo-folk", "neofolk", "neo-psychedelia",
    "trip hop",
    "big-beat", "big beat", "break-beat", "breakbeat",
    "break-core", "breakcore",
    "speed-core", "speedcore", "hard-core", "hardcore",
    "industrial-metal", "industrial metal",
    "industrial-rock", "industrial rock",
    "gothic-rock", "gothic rock", "gothic-metal", "gothic metal",
    "symphonic-metal", "symphonic metal",
    "progressive-metal", "progressive metal",
    "power-metal", "power metal", "speed-metal", "speed metal",
    "thrash-metal", "thrash metal", "death-metal", "death metal",
    "black-metal", "black metal", "doom-metal", "doom metal",
    "sludge-metal", "sludge metal", "groove-metal", "groove metal",
    "nu-metal", "nu metal", "metal-core", "metalcore",
    "death-core", "deathcore", "math-core", "mathcore",
    "grind-core", "grindcore",
    "jazz-fusion", "jazz fusion", "acid-jazz", "acid jazz",
    "smooth-jazz", "smooth jazz",
    "bossa-nova", "bossa nova",
    "latin-jazz", "latin jazz",
    "blue-grass", "bluegrass",
    "roots-rock", "roots rock",
    "singer-songwriter",
    "spoken-word", "spoken word",
    "field-recording", "field recording",
    "musique-concrete", "musique concrete",
    "sound-art", "sound art",
    "video-game", "video game",
    "film-music", "film music",
})

# ── Junk genres — values that should be flagged ──

_JUNK_GENRES = frozenset({
    "unknown", "other", "misc", "none", "null", "various",
    "track", "unclassified", "uncategorized", "sin género",
    "sin genero", "no genre", "no genero", "genre", "genero",
    "untagged", "untitled", "not specified", "not available",
    "n/a", "na", "---", "--", "-", "", "0", "1",
})

# ── Common aliases mapped to canonical names (used by normalize_genre_name) ──

_ALIASES = {
    "synthpop": "Synth pop",
    "synth pop": "Synth pop",
    "synth-pop": "Synth pop",
    "electropop": "Electropop",
    "electro pop": "Electropop",
    "postpunk": "Post-punk",
    "post punk": "Post-punk",
    "punk rock": "Punk rock",
    "hiphop": "Hip-Hop",
    "hip hop": "Hip-Hop",
    "rnb": "R&B",
    "r&b": "R&B",
    "randb": "R&B",
    "rhythm and blues": "R&B",
    "alt rock": "Alternative rock",
    "alternative": "Alternative rock",
    "indie rock": "Indie rock",
    "indie pop": "Indie pop",
    "dream pop": "Dream pop",
    "shoegaze": "Shoegaze",
    "shoegazing": "Shoegaze",
    "prog rock": "Progressive rock",
    "progressive": "Progressive rock",
    "prog": "Progressive rock",
    "folk rock": "Folk rock",
    "hard rock": "Hard rock",
    "classic rock": "Classic rock",
    "blues rock": "Blues rock",
    "death metal": "Death metal",
    "black metal": "Black metal",
    "heavy metal": "Heavy metal",
    "thrash metal": "Thrash metal",
    "doom metal": "Doom metal",
    "speed metal": "Speed metal",
    "power metal": "Power metal",
    "dark wave": "Darkwave",
    "new wave": "New wave",
    "post rock": "Post-rock",
    "trip hop": "Trip-hop",
    "drum n bass": "Drum & Bass",
    "drum and bass": "Drum & Bass",
    "d&b": "Drum & Bass",
    "dnb": "Drum & Bass",
    "art rock": "Art rock",
    "noise": "Noise",
    "ambient": "Ambient",
    "industrial": "Industrial",
    "ebm": "EBM",
    "techno": "Techno",
    "house": "House",
    "deep house": "Deep house",
    "tech house": "Tech house",
    "minimal": "Minimal",
    "idm": "IDM",
    "breaks": "Breakbeat",
    "breakbeat": "Breakbeat",
    "jungle": "Jungle",
    "uk garage": "UK Garage",
    "garage": "UK Garage",
    "dubstep": "Dubstep",
    "grime": "Grime",
    "vaporwave": "Vaporwave",
    "chiptune": "Chiptune",
    "lo fi": "Lo-fi",
    "lofi": "Lo-fi",
    "neoclassical": "Neoclassical",
    "contemporary classical": "Contemporary classical",
    "baroque": "Baroque",
    "orchestral": "Orchestral",
    "chamber": "Chamber music",
    "opera": "Opera",
    "smooth jazz": "Smooth jazz",
    "fusion": "Jazz fusion",
    "acid jazz": "Acid jazz",
    "bossa nova": "Bossa nova",
    "mpb": "MPB",
    "samba": "Samba",
    "reggaeton": "Reggaeton",
    "salsa": "Salsa",
    "bachata": "Bachata",
    "cumbia": "Cumbia",
    "ranchera": "Ranchera",
    "norteño": "Norteño",
    "corrido": "Corrido",
    "flamenco": "Flamenco",
    "world": "World",
    "afrobeat": "Afrobeat",
    "funk": "Funk",
    "soul": "Soul",
    "gospel": "Gospel",
    "blues": "Blues",
    "disco": "Disco",
    "country": "Country",
    "bluegrass": "Bluegrass",
    "americana": "Americana",
    "soundtrack": "Soundtrack",
    "score": "Score",
    "experimental": "Experimental",
    "avant garde": "Avant-garde",
    "avant-garde": "Avant-garde",
    "new age": "New Age",
    "downtempo": "Downtempo",
    "chill": "Chillout",
    "chillout": "Chillout",
    "lounge": "Lounge",
    "easy listening": "Easy listening",
    "christmas": "Christmas",
    "xmas": "Christmas",
    "holiday": "Holiday",
    "spoken word": "Spoken word",
    "audiobook": "Audiobook",
    "podcast": "Podcast",
    "radio": "Radio",
    "live": "Live",
    "remix": "Remix",
    "instrumental": "Instrumental",
    "acoustic": "Acoustic",
    "electronic": "Electronic",
    "electronica": "Electronic",
    "clasica": "Música Clásica",
    "clásica": "Música Clásica",
    "classical": "Música Clásica",
    "musica clasica": "Música Clásica",
    "música clásica": "Música Clásica",
    "ost": "Banda Sonora",
    "original soundtrack": "Banda Sonora",
    "latin": "Música Latina",
    "latino": "Música Latina",
    "musica latina": "Música Latina",
    "música latina": "Música Latina",
    "hip-hop": "Hip-Hop",
    "rap/hip-hop": "Hip-Hop",
    "trap": "Trap",
    "drill": "Drill",
    "reggae": "Reggae",
    "dub": "Dub",
    "ska": "Ska",
    "punk": "Punk",
    "hardcore punk": "Hardcore punk",
    "pop": "Pop",
    "rock": "Rock",
    "jazz": "Jazz",
    "metal": "Metal",
    "folk": "Folk",
    "alternative rock": "Rock Alternativo",
    "alt-rock": "Rock Alternativo",
    "indie": "Indie",
}


def normalize_genre_name(raw: str) -> str:
    """Normalize a single genre name: strip, clean, canonicalize aliases."""
    name = raw.strip()
    if not name:
        return ""
    key = name.lower().strip()
    if key in _ALIASES:
        return _ALIASES[key]

    name = re.sub(r"\s+", " ", name)
    name = name.replace("_", " ")
    name = _normalize_unicode(name)
    parts = []
    for part in name.split("-"):
        parts.append(part.strip().title())
    name = "-".join(parts)
    name = name.replace("And", "and").replace("Of", "of").replace("In", "in")
    name = name.replace("Or", "or").replace("The", "the").replace("A ", "a ")
    if name.startswith("And "):
        name = "and" + name[3:]
    if name.startswith("Of "):
        name = "of" + name[2:]
    if name.startswith("A "):
        name = "a " + name[2:]
    name = name.strip()
    return name


def split_genres(raw: str) -> list[str]:
    """Split a multi-genre string into individual genre names.

    Preserves known compound genres (e.g. 'R&B', 'Drum & Bass', 'Rock & Roll').
    Uses _DELIM_RE (split on , ; / | & +) then recombines parts that form
    known compound genres. For '&' separated compounds, the first pass checks
    if the RAW value is already known as compound before splitting.
    """
    if not raw or not raw.strip():
        return []
    raw_lower = raw.lower().strip()
    if raw_lower in _COMPOUND_GENRES:
        return [normalize_genre_name(raw)]
    parts = _DELIM_RE.split(raw)
    result = []
    buffer = []
    for p in parts:
        stripped = p.strip()
        if not stripped:
            if buffer:
                result.append(normalize_genre_name(" ".join(buffer)))
                buffer = []
            continue
        candidate = " ".join(buffer + [stripped]).lower() if buffer else stripped.lower()
        if candidate in _COMPOUND_GENRES or (buffer and buffer[-1].lower() in ("and", "&", "n")):
            buffer.append(stripped)
        else:
            if buffer:
                result.append(normalize_genre_name(" ".join(buffer)))
            buffer = [stripped]
    if buffer:
        result.append(normalize_genre_name(" ".join(buffer)))
    if not result:
        result = [normalize_genre_name(p) for p in parts if p.strip()]
    return result


def canonicalize_genre(raw: str) -> str:
    """Return the canonical single genre name from a raw tag."""
    return normalize_genre_name(raw)


def genre_key(name: str) -> str:
    """Create a stable key from a genre name."""
    return name.lower().replace(" ", "_").replace("-", "_").replace("/", "_").replace("&", "and").replace("+", "_plus_")


def is_junk_genre(name: str) -> bool:
    """Return True if the genre name is a known junk/bad value."""
    key = name.lower().strip()
    if not key:
        return True
    return bool(key in _JUNK_GENRES)


def is_compound_genre(name: str) -> bool:
    """Return True if the genre name is a known compound genre."""
    return name.lower().strip() in _COMPOUND_GENRES


def get_alias_map() -> dict[str, str]:
    """Return a copy of the builtin alias map."""
    return dict(_ALIASES)


def get_junk_genres() -> frozenset:
    """Return the set of known junk genre values."""
    return _JUNK_GENRES


def get_compound_genres() -> frozenset:
    """Return the set of known compound genre values."""
    return _COMPOUND_GENRES


def genre_similarity(a: str, b: str) -> float:
    """Compute similarity between two genre names (0.0 to 1.0)."""
    ka = genre_key(a)
    kb = genre_key(b)
    if ka == kb:
        return 1.0
    from difflib import SequenceMatcher
    return SequenceMatcher(None, ka, kb).ratio()


def _normalize_unicode(text: str) -> str:
    """Normalize unicode characters (NFKC) and fix common diacritics."""
    text = unicodedata.normalize("NFKC", text)
    return text


def detect_dirty_genres(items) -> list[str]:
    """Find genre strings that have multiple values or non-standard formatting."""
    dirty = set()
    for item in items:
        genre = getattr(item, 'genre', '') or ''
        if not genre:
            continue
        if any(d in genre for d in (',', ';', '/', '|', '&')):
            dirty.add(genre)
        if genre != normalize_genre_name(genre):
            dirty.add(genre)
    return sorted(dirty)


def detect_duplicate_genres(items) -> list[dict]:
    """Detect probable duplicate genres (same normalised key, different raw values).

    Returns list of dicts: {canonical, raw_values, count, track_examples}
    """
    from collections import defaultdict
    groups: dict[str, dict] = defaultdict(lambda: {"raw_values": set(), "track_examples": [], "count": 0})
    for item in items:
        raw = (getattr(item, 'genre', '') or '').strip()
        if not raw:
            continue
        norm = normalize_genre_name(raw)
        key = genre_key(norm)
        if not key or is_junk_genre(norm):
            continue
        entry = groups[key]
        entry["raw_values"].add(raw)
        entry["count"] += 1
        if len(entry["track_examples"]) < 3:
            entry["track_examples"].append(getattr(item, 'filepath', '') or getattr(item, 'title', '') or '')
    results = []
    for _gkey, entry in groups.items():
        if len(entry["raw_values"]) > 1:
            results.append({
                "canonical": list(entry["raw_values"])[0],
                "raw_values": sorted(entry["raw_values"]),
                "count": entry["count"],
                "track_examples": entry["track_examples"],
            })
    return sorted(results, key=lambda r: -r["count"])
