from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentResult:
    intent_id: str
    confidence: float
    entities: dict[str, Any] = field(default_factory=dict)
    needs_llm: bool = False
    raw_text: str = ""


_INTENT_PATTERNS: list[tuple[str, str, bool]] = [
    ("greeting", r"(?i)\b(hola|buenas|hey|saludos|buen[ao]s)\b", False),
    ("help", r"(?i)\b(ayuda|qu[eé] puedes|funciones|capacidades|qu[eé] haces|como funciona)\b", False),
    ("search_library", r"(?i)\b(busca|encuentra|buscar|encuentrame|mu[eé]strame|listame|listar)\b", False),
    ("search_artist", r"(?i)\b(artista|artistas?)\b.*\b(música|canciones|albumes?|discos?)\b", False),
    ("search_album", r"(?i)\b(album|albumes?|disco)\b", False),
    ("search_genre", r"(?i)\b(genero|g[eé]nero|estilo|ritmo)\b", False),
    ("playback_play", r"(?i)\b(reproduce|pon|toca|suena|plays?|reproducci[oó]n)\b", False),
    ("playback_pause", r"(?i)\b(pausa|det[eé]n|para|stop|silencia)\b", False),
    ("playback_next", r"(?i)\b(siguiente|pr[oó]xima|cambia|adelante|next)\b", False),
    ("playback_prev", r"(?i)\b(anterior|atr[aá]s|prev|previo)\b", False),
    ("playback_volume", r"(?i)\b(volumen|vol|sube|baja|silencio|mute|m[uú]t)\b", False),
    ("playback_info", r"(?i)\b(que suena|que cancion|ahora|current|now playing|track actual)\b", False),
    ("playback_info", r"(?i)\b(info|informaci[oó]n|detalles?)\b.*\b(canci[oó]n|pista|track)\b", False),
    ("diagnosis", r"(?i)\b(diagn[oó]stico|diagnostica|revisa|verifica|chequea|health|estado del sistema)\b", False),
    ("diagnosis", r"(?i)\b(problema|error|fallo|issue|warn|warning)\b", False),
    ("suggestion", r"(?i)\b(sugiere|recomienda|qu[eé] me recomiendas|sugerencia|recomendaci[oó]n)\b", False),
    ("suggestion", r"(?i)\b(que escucho|que pongo|algo (bueno|nuevo|parecido|similar))\b", False),
    ("library_info", r"(?i)\b(cuantos?|cu[aá]ntos?|total|tamañ?o|estad[ií]sticas|stats)\b", False),
    ("library_info", r"(?i)\b(biblioteca|librer[ií]a|librar[yí]a|colecci[oó]n)\b.*\b(album|artista|cancion|pista)\b", False),
    ("navigate", r"(?i)\b(ve a|navega|abre|muestra|ir a|vamos a)\b", False),
    ("out_of_scope", r"(?i)\b(clima|tiempo|noticias|deportes|pol[ií]tica|econom[ií]a|receta|pel[ií]cula)\b", False),
]

_INTENT_ENTITY_EXTRACTORS: dict[str, list[tuple[str, re.Pattern]]] = {
    "search_library": [
        ("query", re.compile(r"(?i)(?:busca|encuentra|buscar|encuentrame|muestrame)\s+(.+)$")),
    ],
    "search_artist": [
        ("artist", re.compile(r"(?i)(?:de|del?)\s+(.+?)(?:\s+(?:en|que|\b)$|$)")),
    ],
    "search_album": [
        ("album", re.compile(r"(?i)(?:album|disco)\s+(.+?)(?:\s+(?:de|que|\b)$|$)")),
    ],
    "search_genre": [
        ("genre", re.compile(r"(?i)(?:genero|genero|estilo)\s+(.+?)$")),
    ],
    "navigate": [
        ("route", re.compile(r"(?i)(?:ve a|navega|abre|muestra|ir a|vamos a)\s+(.+)$")),
    ],
}


class IntentRouter:
    def __init__(self) -> None:
        self._patterns = _INTENT_PATTERNS
        self._extractors = _INTENT_ENTITY_EXTRACTORS

    def detect(self, text: str, context: dict[str, Any] | None = None) -> IntentResult:
        if not text:
            return IntentResult(intent_id="greeting", confidence=1.0, raw_text=text)

        best_intent = "unknown"
        best_confidence = 0.0
        best_entities: dict[str, Any] = {}

        for intent_id, pattern_str, _ in self._patterns:
            match = re.search(pattern_str, text)
            if match:
                confidence = self._calc_confidence(intent_id, match)
                if confidence > best_confidence:
                    best_intent = intent_id
                    best_confidence = confidence
                    entities = self._extract_entities(intent_id, text)
                    best_entities = entities

        needs_llm = best_confidence < 0.4 and best_intent != "greeting"

        return IntentResult(
            intent_id=best_intent,
            confidence=best_confidence,
            entities=best_entities,
            needs_llm=needs_llm,
            raw_text=text,
        )

    def _calc_confidence(self, intent_id: str, match: re.Match) -> float:
        base = 0.6
        if intent_id in ("search_library", "playback_info", "diagnosis"):
            base = 0.7
        if intent_id == "greeting":
            base = 0.9
        if intent_id == "out_of_scope":
            base = 0.5
        matched_len = len(match.group(0))
        total_len = len(match.string) if match.string else 1
        ratio = matched_len / max(total_len, 1)
        return min(base + ratio * 0.3, 1.0)

    def _extract_entities(self, intent_id: str, text: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        extractors = self._extractors.get(intent_id, [])
        for entity_name, pattern in extractors:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                if value:
                    entities[entity_name] = value
        return entities
