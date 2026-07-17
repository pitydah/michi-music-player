from __future__ import annotations

import re
from typing import Final

_INTENT_PATTERNS: Final[list[tuple[str, str]]] = [
    ("greeting", r"\b(hola|buenas|buen(os|as) (d[ií]as|tardes|noches)|hey|saludos|qu[eé] tal|hello|hi|good morning|good evening|hey there)\b"),
    ("play_music", r"\b(p(o|ó)n|reproduce|toca|ponte|poner|inicia|suena|play|start playing|put on)\b.*\b(m[uú]sica|cancion(es)?|rock|pop|jazz|cl[aá]sica|electr(o|ó)nica|reggae|blues|metal|hip.?hop|rap|indie|folk|soul|r.?n.?b|country|latina|salsa|bachata|reguet[oó]n|cumbia|punk|grunge|alternativa|instrumental)\b"),
    ("play_music", r"\b(reproduce|toca|pon|play|start)\s+.+"),
    ("recommend", r"\b(recomienda|sugiere|qu[eé] me recomiendas|qu[eé] me pongo|qu[eé] sugieres|what do you recommend|suggest|recommend)\b"),
    ("recommend", r"\b(dame|quiero|busco|necesito)\b.*\b(recomendacion(es)?|sugerencia(s)?|m[uú]sica nueva|algo nuevo|inspiraci[oó]n)\b"),
    ("artist_info", r"\b(qui[eé]n es|cu[eé]ntame sobre|dime de|informaci[oó]n de|biograf[íi]a de|about|tell me about|who is)\b.*\b(artist(a)?)\b"),
    ("artist_info", r"\b(qui[eé]n es|cu[eé]ntame sobre|dime de|informaci[oó]n de|biograf[íi]a de|about|tell me about|who is)\s+(.+)"),
    ("album_info", r"\b(dime\s+del|informaci[oó]n\s+del|about album|album info|tell me about)\b.*\b([aAáÁ]lbum|[dD]isco)\b"),
    ("album_info", r"\b([aA]lbum|[dD]isco)\b.*\b(de|del|llamado|titulado)\s+(.+)"),
    ("genre_info", r"\b(qu[eé] es|explica|caracter[ií]sticas de|informaci[oó]n de|dime sobre)\b.*\b(g[eé]nero|estilo)\b"),
    ("genre_info", r"\b(dime|cu[eé]ntame|habla)\b.*\b(de(l)?)\s+(rock|pop|jazz|cl[aá]sica|electr(o|ó)nica|reggae|blues|metal|hip.?hop|rap|indie|folk|soul|punk|grunge)\b"),
    ("library_status", r"\b(cu[aá]ntas|cua[aá]ntos|qu[eé] (hay|tengo)|estado de (la )?biblioteca|resumen|status|library|estad[ií]sticas|totales)\b.*\b(canciones?|temas?|[aá]lbumes?|artistas?|g[eé]neros?)\b"),
    ("library_status", r"\b(cu[aá]nta|qu[eé] (m[uú]sica|contenido)|estado)\b.*\b(m[uú]sica|biblioteca|librer[ií]a|library)\b"),
    ("library_status", r"\b(library|biblioteca|m[uú]sica)\b.*\b(status|estado|resumen|totales|health)\b"),
]


def classify(query: str) -> str:
    query_lower = query.strip().lower()
    if not query_lower:
        return "unknown"

    for intent, pattern in _INTENT_PATTERNS:
        if re.search(pattern, query_lower):
            return intent

    greeting_words = {"hola", "hello", "hi", "hey", "saludos", "buenas"}
    if query_lower in greeting_words or query_lower.split()[0] in greeting_words:
        return "greeting"

    play_triggers = {"play", "pon", "reproduce", "toca", "ponte", "inicia", "suena", "poner", "reproducir", "start"}
    if query_lower.split()[0] in play_triggers and len(query_lower.split()) > 1:
        return "play_music"

    return "unknown"
