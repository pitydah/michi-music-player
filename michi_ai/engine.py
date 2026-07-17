from __future__ import annotations

from typing import Any

from michi_ai.intent_classifier import classify
from michi_ai.recommender import recommend
from michi_ai.response_composer import compose


def process(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        return {
            "intent": "unknown",
            "response": "Por favor escribe algo para que pueda ayudarte.",
            "actions": [],
        }

    intent = classify(query)
    results: dict[str, Any] = {}

    if intent == "play_music":
        items = recommend(count=5)
        filtered = _filter_by_keywords(query, items)
        results["items"] = filtered or items

    elif intent == "recommend":
        genre = _extract_genre(query)
        mood = _extract_mood(query)
        items = recommend(genre=genre, mood=mood, count=5)
        results["items"] = items

    elif intent == "artist_info":
        artist = _extract_artist_name(query)
        if artist:
            items = recommend(artist=artist)
            examples = ", ".join(t["title"] for t in items[:3]) if items else ""
            results["artist"] = artist
            results["examples"] = examples
            results["gender"] = "o"

    elif intent == "album_info":
        album = _extract_album_name(query)
        if album:
            items = [t for t in recommend(count=50) if album.lower() in t["album"].lower()]
            examples = ", ".join(t["title"] for t in items[:3]) if items else ""
            artist = items[0]["artist"] if items else ""
            results["album"] = album
            results["artist"] = artist
            results["examples"] = examples

    elif intent == "genre_info":
        genre = _extract_genre(query)
        if genre:
            items = recommend(genre=genre, count=50)
            results["genre"] = genre
            results["count"] = len(items)

    elif intent == "library_status":
        all_items = recommend(count=50)
        tracks = len(all_items)
        albums = len({t["album"] for t in all_items})
        artists = len({t["artist"] for t in all_items})
        results["tracks"] = tracks
        results["albums"] = albums
        results["artists"] = artists

    response = compose(intent, results)

    actions: list[dict[str, Any]] = []
    if intent == "play_music" and results.get("items"):
        actions.append({"type": "play", "items": results["items"][:1]})
    elif intent == "recommend" and results.get("items"):
        actions.append({"type": "show_recommendations", "items": results["items"]})

    return {
        "intent": intent,
        "response": response,
        "actions": actions,
    }


def _filter_by_keywords(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = query.lower()
    genre_keywords = {"rock", "pop", "jazz", "clásica", "clasica", "electrónica",
                      "electronica", "reggae", "blues", "metal", "soul", "latin"}
    for word in q.split():
        if word in genre_keywords:
            genre = "classical" if word in ("clásica", "clasica") else word
            genre = "electronic" if word in ("electrónica", "electronica") else genre
            return [t for t in items if t["genre"] == genre]
    return []


_GENRE_MAP = {
    "rock": "rock", "pop": "pop", "jazz": "jazz", "clasica": "classical",
    "clásica": "classical", "electronica": "electronic", "electrónica": "electronic",
    "reggae": "reggae", "blues": "blues", "metal": "metal", "soul": "soul",
    "hip hop": "hip-hop", "hip-hop": "hip-hop", "rap": "hip-hop",
    "indie": "rock", "folk": "folk", "punk": "rock", "latina": "latin",
    "latin": "latin", "salsa": "latin", "cumbia": "latin",
}


def _extract_genre(query: str) -> str | None:
    q = query.lower()
    for keyword, genre in _GENRE_MAP.items():
        if keyword in q:
            return genre
    return None


_MOOD_MAP = {
    "feliz": "feliz", "alegre": "feliz", "happy": "feliz",
    "triste": "triste", "melancolico": "triste", "melancólico": "triste", "sad": "triste",
    "energia": "energico", "energía": "energico", "energico": "energico",
    "enérgico": "energico", "energetic": "energico",
    "relajado": "relajado", "relax": "relajado", "calm": "relajado", "tranquilo": "relajado",
    "nostalgia": "nostalgico", "nostálgico": "nostalgico", "nostalgic": "nostalgico",
}


def _extract_mood(query: str) -> str | None:
    q = query.lower()
    for keyword, mood in _MOOD_MAP.items():
        if keyword in q:
            return mood
    return None


_AFTER_PATTERNS = {
    "quién es ": "", "quien es ": "", "cuéntame sobre ": "", "cuentame sobre ": "",
    "dime de ": "", "información de ": "", "informacion de ": "",
    "biografía de ": "", "biografia de ": "", "tell me about ": "", "who is ": "",
}


def _extract_artist_name(query: str) -> str | None:
    q = query.lower()
    for prefix, _ in _AFTER_PATTERNS.items():
        if prefix in q:
            idx = q.index(prefix) + len(prefix)
            rest = q[idx:].strip().rstrip(".")
            if rest:
                return rest.title()
    words = q.split()
    if len(words) >= 3 and words[0] in ("quién", "quien", "who"):
        return " ".join(words[2:]).title() if len(words) > 2 else None
    return None


def _extract_album_name(query: str) -> str | None:
    q = query.lower()
    for marker in ("del álbum ", "del album ", "del disco ", "el album ", "el álbum ",
                   "el disco ", "titulado ", "llamado "):
        if marker in q:
            idx = q.index(marker) + len(marker)
            rest = q[idx:].strip().rstrip(".")
            if rest:
                return rest.title()
    return None
