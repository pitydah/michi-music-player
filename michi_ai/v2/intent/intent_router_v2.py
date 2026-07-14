from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from michi_ai.v2.core.models import (
    ExtractedEntity, IntentCandidate, IntentId, ParsedIntent,
)
from michi_ai.v2.intent.entity_extractor import EntityExtractor

logger = logging.getLogger(__name__)


@dataclass
class NormalizedText:
    original: str
    cleaned: str
    transformations: list[str] = field(default_factory=list)


class TextNormalizer:
    def normalize(self, text: str) -> NormalizedText:
        original = text
        transformations: list[str] = []
        cleaned = text.strip()

        cleaned = cleaned.lower()
        transformations.append("lowercase")

        replacements = {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "ü": "u", "ñ": "n",
        }
        for accented, plain in replacements.items():
            if accented in cleaned:
                cleaned = cleaned.replace(accented, plain)
                transformations.append(f"accent:{accented}->{plain}")

        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return NormalizedText(original=original, cleaned=cleaned, transformations=transformations)


class RuleIntentDetector:
    _RULES: dict[IntentId, list[tuple[str, float]]] = {
        IntentId.PLAY_TRACK: [
            (r"\b(pon|reproduce|toca|suena|ponme|reproducime|tocame)\s+(la\s+)?(canción|canción|tema|track|pista|rola)", 0.90),
            (r"\breproduce(?:\s|$)", 0.70),
            (r"\bpon(?:\s|$)", 0.65),
        ],
        IntentId.PLAY_ALBUM: [
            (r"\b(pon|reproduce|toca)\s+(el\s+)?(disco|álbum|album|placa|lp)\s+", 0.90),
            (r"\b(reproduce|toca|pon)\s+(el\s+)?(últim[oa]|ultim[oa])\s+(disco|álbum|album)\s+", 0.92),
        ],
        IntentId.PLAY_ARTIST: [
            (r"\b(pon|reproduce|toca|escucha)\s+(a\s+)?(?:el\s+)?artista\s+", 0.90),
            (r"\b(pon|reproduce|toca)\s+(?:a\s+)?el\s+(?:últim[oa]|ultim[oa])\s+(disco|álbum|album)\s+", 0.85),
        ],
        IntentId.PLAY_PLAYLIST: [
            (r"\b(pon|reproduce|toca)\s+(la\s+)?playlist\s+", 0.90),
        ],
        IntentId.PLAY_MIX: [
            (r"\b(pon|reproduce|toca|haz(me)?|crea)\s+(un\s+)?mix\s+", 0.85),
            (r"\b(arm[ae]|haz[me]?|crea)\s+(un\s+)?(mix|mezcla|combo)\s+", 0.85),
        ],
        IntentId.PAUSE: [
            (r"\bpaus[ae](?:\s|$)", 0.95),
            (r"\bdet[eé]n[ae](?:\s|$)", 0.85),
            (r"\bpara\s+(la\s+)?(música|reproducción|playback|musica)", 0.90),
        ],
        IntentId.RESUME: [
            (r"\b(reanuda|contin[aú]a|sigue|resume|continuar)(?:\s|$)", 0.95),
        ],
        IntentId.STOP: [
            (r"\bdet[eé]n(?:\s|$)", 0.80),
            (r"\bpara(?:\s|$)", 0.70),
            (r"\bdeja\s+de\s+reproducir", 0.90),
        ],
        IntentId.NEXT: [
            (r"\bsiguiente(?:\s|$)", 0.90),
            (r"\bpasa\s+(a\s+)?la\s+siguiente", 0.90),
            (r"\bsalta\s+(a\s+)?(la\s+)?siguiente", 0.85),
            (r"\bnext(?:\s|$)", 0.85),
        ],
        IntentId.PREVIOUS: [
            (r"\banterior(?:\s|$)", 0.90),
            (r"\b(regresa|vuelve|retrocede)\s+(a\s+)?(la\s+)?anterior", 0.90),
            (r"\bprev(ious)?(?:\s|$)", 0.85),
        ],
        IntentId.SEEK: [
            (r"\badelanta\s+(\d+)\s*(segundos?|minutos?|s|m)\s*", 0.90),
            (r"\bretrocede\s+(\d+)\s*(segundos?|minutos?|s|m)\s*", 0.90),
            (r"\b(salta|ve|anda)\s+(a\s+)?(los?\s+)?(\d+):(\d+)\s*", 0.85),
        ],
        IntentId.SET_VOLUME: [
            (r"\bsube\s+(el\s+)?volumen\s*", 0.85),
            (r"\bbaja\s+(el\s+)?volumen\s*", 0.85),
            (r"\bvolumen\s+(a\s+)?(\d+)\s*", 0.90),
            (r"\bvolume?\s*(?:a\s+)?(\d+)\s*", 0.85),
        ],
        IntentId.SET_REPEAT: [
            (r"\brepite\s+(la\s+)?(canción|playlist|cola|current|todo)", 0.90),
            (r"\b(repeat|repetir|modo\s+repetir)", 0.85),
        ],
        IntentId.SET_SHUFFLE: [
            (r"\b(aleatorio|shuffle|azar|barajar|mezclar|desordenar)", 0.90),
            (r"\bmodo\s+(aleatorio|shuffle|azar)", 0.92),
        ],
        IntentId.ADD_TO_QUEUE: [
            (r"\bagrega\s+(est[ao]s?|estas|lo)\s+(a\s+)?(la\s+)?(cola|fila|lista|queue)\s*", 0.90),
            (r"\b(añade|agrega|pon|mete)\s+(a\s+)?(la\s+)?cola\s*", 0.85),
            (r"\bencolar\s*", 0.85),
        ],
        IntentId.PLAY_NEXT: [
            (r"\b(reproduce|toca|pon)\s+(después|al\s+siguiente|luego|enseguida)\s*", 0.85),
            (r"\bplay\s+next\s*", 0.85),
        ],
        IntentId.CLEAR_QUEUE: [
            (r"\blimpia\s+(la\s+)?cola\s*", 0.90),
            (r"\bborra\s+la\s+cola\s*", 0.85),
            (r"\bvacía\s+(la\s+)?cola\s*", 0.85),
            (r"\bclear\s+queue\s*", 0.85),
        ],
        IntentId.GET_QUEUE: [
            (r"\b(qu[eé]|muestra|lista|enseña|como\s+viene)\s+(hay\s+en\s+)?(la\s+)?cola", 0.85),
            (r"\bqueue(?:\s|$)", 0.70),
        ],
        IntentId.SEARCH_LIBRARY: [
            (r"\bbusca\s+", 0.85),
            (r"\bencuentra\s+", 0.80),
            (r"\bsearch\s+", 0.80),
            (r"\b(qu[eé]|cuales?)\s+(hay|tienes?|existe)\s+(de\s+)?", 0.70),
        ],
        IntentId.CREATE_PLAYLIST: [
            (r"\bcrea\s+(una\s+)?playlist\s+", 0.90),
            (r"\bhaz(me)?\s+(una\s+)?(playlist|lista)\s+", 0.85),
        ],
        IntentId.CREATE_MIX: [
            (r"\bhaz(me)?\s+(un\s+)?mix\s+", 0.90),
            (r"\bcrea\s+(un\s+)?mix\s+", 0.90),
            (r"\barm[ae]\s+(un\s+)?mix\s+", 0.85),
        ],
        IntentId.SCAN_HEALTH: [
            (r"\b(revisa|escanea|analiza|diagnostica|examina)\s+(la\s+)?(biblioteca|librería|salud|health)\b", 0.85),
            (r"\blibrary\s+doctor\b", 0.90),
            (r"\b(revisa|analiza)\s+la\s+salud\s+", 0.80),
        ],
        IntentId.INSPECT_METADATA: [
            (r"\b(inspecciona|revisa|examina|checkea?|chequea?)\s+(metadata|metadatos|tags?|etiquetas)\b", 0.85),
        ],
        IntentId.DIAGNOSE_ECOSYSTEM: [
            (r"\b(diagnostica|revisa|analiza)\s+(el\s+)?(ecosistema|conexiones|sync|sincro)\b", 0.85),
            (r"\bpor\s+qu[eé]\s+(el\s+)?(servidor|server|dispositivo|dev)\s+(no\s+)?(aparece|funciona|conecta|anda)\b", 0.80),
        ],
        IntentId.START_CONVERSION: [
            (r"\b(convertir|convierte|cambia|transforma)\s+(a|en|para)\s+", 0.85),
            (r"\bconversi[oó]n\s+", 0.80),
        ],
        IntentId.PLAN_SYNC: [
            (r"\bsincroniza\s+(esta\s+)?(playlist|lista|selección)\s+(con|para|al)\s+(el\s+)?(dispositivo|reproductor|device)\b", 0.85),
            (r"\bsync\s+(playlist|lista)\s+", 0.80),
        ],
        IntentId.SUGGEST_SETTING: [
            (r"\bsugi[eé]re\s+(un\s+)?(cambio|cambiar|ajuste|configuración)\s+", 0.80),
            (r"\bcambia\s+(la\s+)?configuración\s+", 0.75),
        ],
        IntentId.NAVIGATE: [
            (r"\b(abre|muestra|ve\s+a|navega\s+a|anda\s+a|dirígete\s+a)\s+", 0.80),
            (r"\b(open|show|go\s+to|navigate)\s+", 0.75),
        ],
        IntentId.GENERAL_QUERY: [
            (r"\b(qu[eé]\s+(es|son|significa|hace|puedes))\b", 0.60),
            (r"\b(explícame|cuéntame|dime|inform[ae])\s+(sobre|acerca|de)\b", 0.60),
            (r"\bc[óo]mo\s+funciona\b", 0.60),
        ],
    }

    def detect(self, text: str, entities: list[ExtractedEntity]) -> list[IntentCandidate]:
        candidates: list[IntentCandidate] = []
        for intent_id, patterns in self._RULES.items():
            best_confidence = 0.0
            best_rule = ""
            for pattern_str, base_confidence in patterns:
                m = re.search(pattern_str, text, re.IGNORECASE)
                if m:
                    confidence = self._adjust_confidence(base_confidence, intent_id, text, entities)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_rule = pattern_str

            if best_confidence > 0.0:
                candidates.append(IntentCandidate(
                    intent=ParsedIntent(
                        intent_id=intent_id.value,
                        confidence=best_confidence,
                        source="rules",
                        matched_rule=best_rule,
                    ),
                    rank=0,
                ))

        candidates.sort(key=lambda c: c.intent.confidence, reverse=True)
        ranked: list[IntentCandidate] = []
        for i, c in enumerate(candidates):
            ranked.append(IntentCandidate(intent=c.intent, rank=i + 1))
        return ranked

        return candidates

    def _adjust_confidence(self, base: float, intent: IntentId, text: str, entities: list[ExtractedEntity]) -> float:
        confidence = base
        entity_types = {e.name for e in entities}

        if intent == IntentId.PLAY_ARTIST and "artist" in entity_types:
            confidence = min(confidence + 0.10, 0.98)
        if intent == IntentId.PLAY_ALBUM and "album" in entity_types:
            confidence = min(confidence + 0.10, 0.98)
        if intent == IntentId.CREATE_MIX and "genre" in entity_types:
            confidence = min(confidence + 0.10, 0.98)
        if intent == IntentId.START_CONVERSION and "format" in entity_types:
            confidence = min(confidence + 0.08, 0.98)
        if intent == IntentId.PLAY_TRACK and "track" not in entity_types:
            confidence = max(confidence - 0.10, 0.0)
        if intent == IntentId.PLAY_ARTIST and "album" in entity_types:
            confidence = max(confidence - 0.20, 0.0)
        if intent == IntentId.PLAY_ALBUM and "album" in entity_types:
            confidence = min(confidence + 0.10, 0.98)

        negation = re.search(r"\b(no\s+|sin\s+|excepto|menos|evita|quit[ae])\b", text, re.IGNORECASE)
        if negation and intent in (IntentId.PAUSE, IntentId.STOP, IntentId.CLEAR_QUEUE):
            confidence = max(confidence - 0.20, 0.0)

        return confidence


class SectionIntentDetector:
    def detect(self, text: str, section: str) -> str:
        section_map: dict[str, list[tuple[str, str]]] = {
            "library_hub": [
                (r"\b(biblioteca|librería|library|car[pb]eta|archivo)\b", "search_library"),
            ],
            "playback_hub": [
                (r"\b(reproducción|playback|player|reproductor|now\s*playing)\b", "playback_control"),
            ],
            "playlists": [
                (r"\b(playlists?|lista|listas)\b", "playlist_management"),
            ],
            "mix_hub": [
                (r"\b(mix|mezcla|combo|recomendación|smart)\b", "mix_generation"),
            ],
            "audio_lab": [
                (r"\b(audio.?lab|analiz[ae]|convert|conversi[oó]n|ecualiz|formato)\b", "audio_lab"),
            ],
            "connections_hub": [
                (r"\b(conexión|conexiones|sync|sincro|ecosistema|pair|emparejar)\b", "connections"),
            ],
            "devices": [
                (r"\b(dispositivo|device|tel[eé]fono|tablet|raspberry|chromecast)\b", "devices"),
            ],
            "home_audio": [
                (r"\b(home.?audio|snapcast|multiroom|zonas?|altavoz|speaker)\b", "home_audio"),
            ],
            "settings": [
                (r"\b(configuración|setting|preferencias|preferences|ajuste)\b", "settings"),
            ],
            "metadata_editor": [
                (r"\b(metadata|metadatos|tag|etiqueta|musicbrainz|cover|carátula)\b", "metadata"),
            ],
        }

        for section_key, patterns in section_map.items():
            if text in (section_key, section.replace("_", " ")):
                for p, action in patterns:
                    if re.search(p, text, re.IGNORECASE):
                        return action
        return ""


class CandidateRanker:
    CONFIDENCE_THRESHOLD = 0.50
    AMBIGUITY_THRESHOLD = 0.15

    def rank(self, candidates: list[IntentCandidate]) -> list[IntentCandidate]:
        if not candidates:
            return []
        candidates.sort(key=lambda c: c.intent.confidence, reverse=True)
        ranked: list[IntentCandidate] = []
        for i, c in enumerate(candidates):
            ranked.append(IntentCandidate(intent=c.intent, rank=i + 1))
        return ranked

    def best(self, candidates: list[IntentCandidate]) -> ParsedIntent | None:
        if not candidates:
            return None
        if len(candidates) == 1 and candidates[0].intent.confidence >= self.CONFIDENCE_THRESHOLD:
            return candidates[0].intent
        if len(candidates) >= 2:
            first = candidates[0].intent
            second = candidates[1].intent
            diff = first.confidence - second.confidence
            if first.confidence >= self.CONFIDENCE_THRESHOLD and diff > self.AMBIGUITY_THRESHOLD:
                return first
        return None

    def ambiguous(self, candidates: list[IntentCandidate]) -> list[IntentCandidate]:
        if len(candidates) < 2:
            return []
        first = candidates[0].intent
        second = candidates[1].intent
        diff = first.confidence - second.confidence
        if first.confidence >= self.CONFIDENCE_THRESHOLD and diff <= self.AMBIGUITY_THRESHOLD:
            return candidates[:2]
        return []


class AmbiguityResolver:
    def build_clarification(self, candidates: list[IntentCandidate]) -> str:
        if not candidates:
            return "No entendí tu solicitud. ¿Podrías reformularla?"
        options = []
        seen: set[str] = set()
        for c in candidates:
            label = c.intent.intent_id.replace("_", " ").title()
            if label not in seen:
                seen.add(label)
                options.append(f"  {len(options) + 1}. {label}")

        if options:
            return "¿Cuál de estas opciones quisiste decir?\n" + "\n".join(options)
        return "No entendí tu solicitud. ¿Podrías reformularla?"


class IntentRouterV2:
    def __init__(self) -> None:
        self.normalizer = TextNormalizer()
        self.rule_detector = RuleIntentDetector()
        self.section_detector = SectionIntentDetector()
        self.entity_extractor = EntityExtractor()
        self.ranker = CandidateRanker()
        self.ambiguity_resolver = AmbiguityResolver()

    def detect(self, text: str, context: dict[str, Any] | None = None) -> ParsedIntent:
        ctx = context or {}
        normalized = self.normalizer.normalize(text)
        entities = self.entity_extractor.extract(normalized.cleaned, ctx)
        candidates = self.rule_detector.detect(normalized.cleaned, entities)

        self.section_detector.detect(normalized.cleaned, ctx.get("active_section", ""))
        ranked = self.ranker.rank(candidates)

        best = self.ranker.best(ranked)
        ambiguous = self.ranker.ambiguous(ranked)

        if best is not None:
            return ParsedIntent(
                intent_id=best.intent_id,
                confidence=best.confidence,
                source=best.source,
                entities={e.name: e.value for e in entities if e.confidence >= 0.7},
                constraints=self._build_constraints(entities),
                requested_actions=(best.intent_id,),
                negated_actions=self._detect_negations(normalized.cleaned, best.intent_id),
                requires_clarification=False,
                reasoning_summary=f"Coincidió patrón de regla '{best.matched_rule}' con confianza {best.confidence:.2f}",
            )

        if ambiguous:
            return ParsedIntent(
                intent_id=ambiguous[0].intent.intent_id,
                confidence=ambiguous[0].intent.confidence,
                source=ambiguous[0].intent.source,
                entities={e.name: e.value for e in entities if e.confidence >= 0.7},
                requires_clarification=True,
                clarification_question=self.ambiguity_resolver.build_clarification(ambiguous),
                reasoning_summary="Múltiples intenciones posibles con confianza similar",
            )

        if entities:
            return ParsedIntent(
                intent_id="general_query",
                confidence=0.40,
                source="fallback",
                entities={e.name: e.value for e in entities if e.confidence >= 0.7},
                requires_clarification=False,
                reasoning_summary="No se detectó una intención clara, pero se encontraron entidades",
            )

        return ParsedIntent(
            intent_id="unknown",
            confidence=0.0,
            source="fallback",
            reasoning_summary="No se pudo reconocer la intención",
        )

    def _build_constraints(self, entities: list[ExtractedEntity]) -> dict[str, Any]:
        constraints: dict[str, Any] = {}
        for e in entities:
            if e.name in ("quantity", "year", "decade", "bitrate", "sample_rate", "bit_depth"):
                constraints[e.name] = e.value
            if e.name == "sort":
                constraints["sort"] = e.value
            if e.name == "filter":
                constraints["filter"] = e.value
        return constraints

    def _detect_negations(self, text: str, intent: str) -> tuple[str, ...]:
        negated: list[str] = []
        m = re.search(r"\b(no\s+)(borres?|elimines?|quites?|remuevas?|cambies?|modifiques?|destruyas?)\b", text, re.IGNORECASE)
        if m:
            negated.append("modify")
        m = re.search(r"\b(sin\s+confirmar|preguntar)\b", text, re.IGNORECASE)
        if m:
            negated.append("confirmation")
        return tuple(negated)
