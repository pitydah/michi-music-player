from __future__ import annotations

import random
from typing import Any

_GREETING_RESPONSES = [
    "¡Hola! Soy Michi AI. ¿En qué puedo ayudarte? Puedo reproducir música, recomendarte canciones o darte información sobre artistas y álbumes.",
    "¡Buenas! Michi AI al servicio. Dime qué necesitas: reproducir, recomendar o consultar tu biblioteca.",
    "Hey, soy Michi AI. ¿Qué tal? Estoy aquí para ayudarte con tu música.",
]

_PLAY_TEMPLATES = [
    "Reproduciendo {title} de {artist}.",
    "Ahora suena {title} — {artist}.",
    "Poniendo {title} de {artist}.",
]

_RECOMMEND_TEMPLATES = [
    "Te recomiendo escuchar {title} de {artist} — es {genre}.",
    "¿Qué tal {title} de {artist}? Un gran tema de {genre}.",
    "No te pierdas {title} de {artist}. {genre} en su máxima expresión.",
]

_ARTIST_TEMPLATES = [
    "{artist} es un{article} artist{a} reconocido{a} en el mundo de la música. "
    "Tiene canciones en tu biblioteca como {examples}.",
    "¡{artist}! Un{article} gran artist{a} con temas increíbles en tu colección: {examples}.",
]

_ALBUM_TEMPLATES = [
    'El álbum "{album}" de {artist} está en tu biblioteca. Incluye canciones como {examples}.',
    '"{album}" de {artist} — un gran disco. En tu colección tienes: {examples}.',
]

_GENRE_TEMPLATES = [
    "El género {genre} está presente en tu biblioteca con {count} canciones.",
    "Tienes {count} temas de {genre} en tu colección.",
]

_LIBRARY_TEMPLATES = [
    "Tu biblioteca tiene {tracks} canciones, {albums} álbumes y {artists} artistas.",
    "Resumen: {tracks} temas, {albums} discos, {artists} intérpretes.",
]

_UNKNOWN_RESPONSE = (
    "No entendí tu consulta. Puedo ayudarte a reproducir música, "
    "recomendar canciones o darte información sobre artistas y álbumes."
)


def compose(intent: str, results: dict[str, Any] | None = None) -> str:
    results = results or {}

    if intent == "greeting":
        return random.choice(_GREETING_RESPONSES)

    if intent == "play_music":
        items = results.get("items", [])
        if not items:
            return "No encontré canciones para reproducir con esos criterios."
        chosen = random.choice(items)
        template = random.choice(_PLAY_TEMPLATES)
        return template.format(**chosen)

    if intent == "recommend":
        items = results.get("items", [])
        if not items:
            return "No tengo recomendaciones disponibles en este momento."
        parts = []
        for item in items[:3]:
            template = random.choice(_RECOMMEND_TEMPLATES)
            parts.append(template.format(**item))
        return "\n".join(parts)

    if intent == "artist_info":
        artist = results.get("artist", "")
        examples = results.get("examples", "")
        if not artist:
            return "¿Sobre qué artista quieres información?"
        gender = results.get("gender", "o")
        article = "a" if gender == "a" else ""
        if article:
            return random.choice(_ARTIST_TEMPLATES).format(
                artist=artist, article=article, a="a", examples=examples
            ).replace("un a", "una").replace("una gran", "una gran")
        return random.choice(_ARTIST_TEMPLATES).format(
            artist=artist, article="", a=gender, examples=examples
        )

    if intent == "album_info":
        album = results.get("album", "")
        artist = results.get("artist", "")
        examples = results.get("examples", "")
        if not album:
            return "¿De qué álbum quieres saber más?"
        template = random.choice(_ALBUM_TEMPLATES)
        return template.format(album=album, artist=artist, examples=examples)

    if intent == "genre_info":
        genre = results.get("genre", "")
        count = results.get("count", 0)
        if not genre:
            return "¿De qué género quieres información?"
        template = random.choice(_GENRE_TEMPLATES)
        return template.format(genre=genre, count=count)

    if intent == "library_status":
        tracks = results.get("tracks", 0)
        albums = results.get("albums", 0)
        artists = results.get("artists", 0)
        template = random.choice(_LIBRARY_TEMPLATES)
        return template.format(tracks=tracks, albums=albums, artists=artists)

    return _UNKNOWN_RESPONSE
