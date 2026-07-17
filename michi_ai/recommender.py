from __future__ import annotations

import random
from typing import Any, Callable

_LIBRARY_PROVIDER: Callable[[], list[dict[str, str]]] | None = None


def set_library_provider(provider: Callable[[], list[dict[str, str]]]):
    global _LIBRARY_PROVIDER
    _LIBRARY_PROVIDER = provider


def _get_library() -> list[dict[str, str]]:
    if _LIBRARY_PROVIDER:
        try:
            return _LIBRARY_PROVIDER()
        except Exception:
            pass
    return _MOCK_LIBRARY


_MOCK_LIBRARY: list[dict[str, str]] = [
    {"artist": "Pink Floyd", "album": "The Dark Side of the Moon", "title": "Money", "genre": "rock"},
    {"artist": "Pink Floyd", "album": "The Dark Side of the Moon", "title": "Time", "genre": "rock"},
    {"artist": "Pink Floyd", "album": "Wish You Were Here", "title": "Shine On You Crazy Diamond", "genre": "rock"},
    {"artist": "Miles Davis", "album": "Kind of Blue", "title": "So What", "genre": "jazz"},
    {"artist": "Miles Davis", "album": "Kind of Blue", "title": "Freddie Freeloader", "genre": "jazz"},
    {"artist": "John Coltrane", "album": "A Love Supreme", "title": "Part I: Acknowledgement", "genre": "jazz"},
    {"artist": "Daft Punk", "album": "Random Access Memories", "title": "Get Lucky", "genre": "electronic"},
    {"artist": "Daft Punk", "album": "Discovery", "title": "One More Time", "genre": "electronic"},
    {"artist": "Beethoven", "album": "Symphony No. 9", "title": "Ode to Joy", "genre": "classical"},
    {"artist": "Beethoven", "album": "Symphony No. 5", "title": "Allegro con brio", "genre": "classical"},
    {"artist": "Nina Simone", "album": "I Put a Spell on You", "title": "Feeling Good", "genre": "soul"},
    {"artist": "Aretha Franklin", "album": "I Never Loved a Man", "title": "Respect", "genre": "soul"},
    {"artist": "Led Zeppelin", "album": "IV", "title": "Stairway to Heaven", "genre": "rock"},
    {"artist": "Queen", "album": "A Night at the Opera", "title": "Bohemian Rhapsody", "genre": "rock"},
    {"artist": "Bob Marley", "album": "Legend", "title": "No Woman No Cry", "genre": "reggae"},
    {"artist": "Bob Marley", "album": "Legend", "title": "Buffalo Soldier", "genre": "reggae"},
    {"artist": "Talking Heads", "album": "Remain in Light", "title": "Once in a Lifetime", "genre": "rock"},
    {"artist": "Radiohead", "album": "OK Computer", "title": "Paranoid Android", "genre": "rock"},
    {"artist": "Kendrick Lamar", "album": "To Pimp a Butterfly", "title": "Alright", "genre": "hip-hop"},
    {"artist": "Buena Vista Social Club", "album": "Buena Vista Social Club", "title": "Chan Chan", "genre": "latin"},
]


def recommend(
    genre: str | None = None,
    artist: str | None = None,
    mood: str | None = None,
    count: int = 5,
) -> list[dict[str, Any]]:
    pool = list(_get_library())

    if genre:
        genre_lower = genre.lower()
        pool = [t for t in pool if t["genre"].lower() == genre_lower]
    if artist:
        artist_lower = artist.lower()
        pool = [t for t in pool if artist_lower in t["artist"].lower()]

    if mood:
        mood = mood.lower()
        mood_map: dict[str, list[str]] = {
            "feliz": ["get lucky", "one more time", "feeling good"],
            "triste": ["time", "no woman no cry", "ode to joy"],
            "energico": ["respect", "bohemian rhapsody", "money", "alright"],
            "relajado": ["so what", "once in a lifetime", "chan chan"],
        }
        keywords = mood_map.get(mood, [])
        if keywords:
            pool = [t for t in pool if any(kw in t["title"].lower() for kw in keywords)]

    random.shuffle(pool)
    return pool[:count]
