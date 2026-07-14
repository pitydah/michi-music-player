from __future__ import annotations

import re
from typing import Any

from michi_ai.v2.core.models import Ambiguity, EntityType, ExtractedEntity

_ARTIST_SKIP_PREFIXES: frozenset[str] = frozenset({"algo", "nada", "todo", "alguno", "un", "una", "el", "la", "los", "las", "que", "cual"})
_NUMERAL_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?)")
_ORDINAL_PATTERN = re.compile(
    r"\b(primer[oa]?|segund[oa]?|tercer[oa]?|cuart[oa]?|quint[oa]?|"
    r"sext[oa]?|séptim[oa]?|octav[oa]?|noven[oa]?|décim[oa]?|"
    r"últim[oa]?|pendltimo|antependltimo)\b",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")
_DECADE_PATTERN = re.compile(r"\b(años?\s+)?(19\d0|20\d0)s?\b", re.IGNORECASE)
_QUANTITY_PATTERN = re.compile(r"\b(los\s+)?(últimos?\s+)?(\d+)\s+(canciones?|temas?|pistas?|álbumes?|discos?|playlists?)\b", re.IGNORECASE)
_DEVICE_PATTERN = re.compile(r"\b(dispositivo|teléfono|tablet|raspberry|pc|server|servidor|chromecast|snapcast)\b", re.IGNORECASE)
_FORMAT_PATTERN = re.compile(r"\b(flac|wav|aiff|alac|ogg|opus|mp3|aac|wma|dsd|dff|dsf|ape|wv)\b", re.IGNORECASE)
_BITRATE_PATTERN = re.compile(r"\b(\d+)\s*(kbps|k|K)\b")
_SAMPLE_RATE_PATTERN = re.compile(r"\b(\d+)\s*(khz|kHz|hz|Hz)\b")
_BIT_DEPTH_PATTERN = re.compile(r"\b(\d+)\s*(bit|bits|bpc)\b")
_REFERENCE_PATTERN = re.compile(r"\b(este|esta|estos|estas|ese|esa|esos|esas|esto|eso|aquello|aquel|aquella|actual|seleccionad[oa]|mismo|misma)\b", re.IGNORECASE)
_SCOPE_PATTERN = re.compile(r"\b(selección|cola|biblioteca|disco|álbum|artista|género|playlist|favoritos|lista)\b", re.IGNORECASE)
_SORT_PATTERN = re.compile(r"\b(más\s+(nuev[oa]s?|reciente|viejo|antiguo|escuchado|popular)|por\s+(nombre|año|género|artista|álbum|fecha|rating|duración))\b", re.IGNORECASE)
_FILTER_PATTERN = re.compile(r"\b(que\s+(no\s+)?haya?|con\s+|\bsin\s+|\bmenos\s+de\b|\bmás\s+de\b|\bentre\b)", re.IGNORECASE)
_POSITION_PATTERN = re.compile(r"\b(segund[oa]?|tercer[oa]?|siguiente|anterior|primero|último)\s+(canción|tema|pista|track|elemento)\b", re.IGNORECASE)


class EntityExtractor:
    def extract(self, text: str, context: dict[str, Any] | None = None) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        context = context or {}

        artist = self._extract_artist(text)
        if artist:
            entities.append(artist)

        album = self._extract_album(text)
        if album:
            entities.append(album)

        track = self._extract_track(text)
        if track:
            entities.append(track)

        playlist = self._extract_playlist(text)
        if playlist:
            entities.append(playlist)

        genre = self._extract_genre(text)
        if genre:
            entities.append(genre)

        year = self._extract_year(text)
        if year:
            entities.append(year)

        decade = self._extract_decade(text)
        if decade:
            entities.append(decade)

        device = self._extract_device(text)
        if device:
            entities.append(device)

        fmt = self._extract_format(text)
        if fmt:
            entities.append(fmt)

        bitrate = self._extract_bitrate(text)
        if bitrate:
            entities.append(bitrate)

        sample_rate = self._extract_sample_rate(text)
        if sample_rate:
            entities.append(sample_rate)

        bit_depth = self._extract_bit_depth(text)
        if bit_depth:
            entities.append(bit_depth)

        quantity = self._extract_quantity(text)
        if quantity:
            entities.append(quantity)

        position = self._extract_position(text)
        if position:
            entities.append(position)

        scope = self._extract_scope(text)
        if scope:
            entities.append(scope)

        ref = self._extract_reference(text, context)
        if ref:
            entities.append(ref)

        sort = self._extract_sort(text)
        if sort:
            entities.append(sort)

        filtr = self._extract_filter(text)
        if filtr:
            entities.append(filtr)

        return entities

    def extract_ambiguation(self, text: str, entities: list[ExtractedEntity]) -> list[Ambiguity]:
        ambiguities: list[Ambiguity] = []
        pronouns = _REFERENCE_PATTERN.findall(text.lower())
        has_reference = any(e.name == EntityType.PATH_REFERENCE for e in entities)
        has_scope = any(e.name == EntityType.SCOPE for e in entities)
        if (pronouns or has_reference) and not has_scope:
            ambiguities.append(Ambiguity(
                    field="scope",
                    clarification_question="¿A qué te refieres? ¿La selección actual, la cola, o algo más?",
                ))
        return ambiguities

    def _extract_artist(self, text: str) -> ExtractedEntity | None:
        lowered = text.lower()
        patterns = [
            r"\b(?:de|del|para)\s+([a-záéíóúñ]{3,}(?:\s+[a-záéíóúñ]+){0,3})(?:\s+(?:en|,|\sy\s+)|$)",
            r"\b(?:algo\s+de)\s+([a-záéíóúñ]{3,}(?:\s+[a-záéíóúñ]+){0,3})",
            r"^(?:pon|reproduce|busca|encuentra)\s+(?:a\s+)?([a-záéíóúñ]{3,}(?:\s+[a-záéíóúñ]+){0,3})",
        ]
        for p in patterns:
            m = re.search(p, lowered)
            if m:
                name = m.group(1).strip()
                first_word = name.split()[0] if name else ""
                if first_word in _ARTIST_SKIP_PREFIXES:
                    continue
                if name and len(name) > 2:
                    return ExtractedEntity(
                        name=EntityType.ARTIST, value=name.title(),
                        confidence=0.85, source_text=m.group(0),
                    )
        return None

    def _extract_album(self, text: str) -> ExtractedEntity | None:
        patterns = [
            r"(?:el\s+)?(?:disco|álbum|album|placa|lp)\s+(?:de\s+)?(?:llamado|titulado|llamad[oa]?)?\s*[`'\"¡¿]?([A-ZÁÉÍÓÚÑa-záéíóúñ0-9][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{2,40})[`'\"]?",
            r"reproduce\s+(?:el\s+)?(?:disco|álbum|album)\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{2,40})",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                name = m.group(1).strip().strip("'\"").strip("¿¡")
                if len(name) > 2:
                    return ExtractedEntity(
                        name=EntityType.ALBUM, value=name,
                        confidence=0.80, source_text=m.group(0),
                    )
        return None

    def _extract_track(self, text: str) -> ExtractedEntity | None:
        patterns = [
            r"(?:la\s+)?(?:canción|canción|cancion|tema|pista|track|rola|song)\s+(?:de\s+)?(?:llamada|titulada|llamad[oa]?)?\s*[`'\"¡¿]?([A-ZÁÉÍÓÚÑa-záéíóúñ0-9][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{2,60})[`'\"]?",
            r"reproduce\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{2,60})\s+(?:de|del)\s+",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                name = m.group(1).strip().strip("'\"").strip("¿¡")
                if len(name) > 2:
                    return ExtractedEntity(
                        name=EntityType.TRACK, value=name,
                        confidence=0.75, source_text=m.group(0),
                    )
        return None

    def _extract_playlist(self, text: str) -> ExtractedEntity | None:
        m = re.search(r"(?:la\s+)?playlist\s+(?:de\s+)?(?:llamada|titulada)?\s*[`'\"¡¿]?([A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{2,60})[`'\"]?", text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().strip("'\"").strip("¿¡")
            if len(name) > 1:
                return ExtractedEntity(
                    name=EntityType.PLAYLIST, value=name,
                    confidence=0.80, source_text=m.group(0),
                )
        return None

    def _extract_genre(self, text: str) -> ExtractedEntity | None:
        genres = [
            "rock", "pop", "jazz", "blues", "clásica", "clasica", "electrónica", "electronica",
            "hip hop", "rap", "reggaeton", "reggae", "salsa", "bachata", "merengue",
            "cumbia", "folklore", "tango", "milonga", "bossanova", "bossa nova",
            "metal", "punk", "hardcore", "indie", "alternativa", "alternativo",
            "r&b", "soul", "funk", "disco", "house", "techno", "trance", "dubstep",
            "country", "folk", "latina", "latino", "brasil", "samba", "forro",
            "kpop", "k-pop", "jpop", "j-pop", "anime", "banda sonora", "soundtrack",
        ]
        for g in genres:
            m = re.search(r"\b" + re.escape(g) + r"\b", text, re.IGNORECASE)
            if m:
                return ExtractedEntity(
                    name=EntityType.GENRE, value=g.title(),
                    confidence=0.90, source_text=m.group(0),
                )
        return None

    def _extract_year(self, text: str) -> ExtractedEntity | None:
        m = _YEAR_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.YEAR, value=int(m.group(1)),
                confidence=0.95, source_text=m.group(0),
            )
        return None

    def _extract_decade(self, text: str) -> ExtractedEntity | None:
        m = _DECADE_PATTERN.search(text)
        if m:
            decade_str = m.group(2) if m.group(2) else m.group(0)
            return ExtractedEntity(
                name=EntityType.DECADE, value=decade_str,
                confidence=0.90, source_text=m.group(0),
            )
        return None

    def _extract_device(self, text: str) -> ExtractedEntity | None:
        m = _DEVICE_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.DEVICE, value=m.group(1).lower(),
                confidence=0.85, source_text=m.group(0),
            )
        return None

    def _extract_format(self, text: str) -> ExtractedEntity | None:
        m = _FORMAT_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.FORMAT, value=m.group(1).upper(),
                confidence=0.95, source_text=m.group(0),
            )
        return None

    def _extract_bitrate(self, text: str) -> ExtractedEntity | None:
        m = _BITRATE_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.BITRATE, value=int(m.group(1)),
                confidence=0.90, source_text=m.group(0),
            )
        return None

    def _extract_sample_rate(self, text: str) -> ExtractedEntity | None:
        m = _SAMPLE_RATE_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.SAMPLE_RATE, value=int(m.group(1)),
                confidence=0.90, source_text=m.group(0),
            )
        return None

    def _extract_bit_depth(self, text: str) -> ExtractedEntity | None:
        m = _BIT_DEPTH_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.BIT_DEPTH, value=int(m.group(1)),
                confidence=0.90, source_text=m.group(0),
            )
        return None

    def _extract_quantity(self, text: str) -> ExtractedEntity | None:
        m = _QUANTITY_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.QUANTITY, value=int(m.group(3)),
                confidence=0.90, source_text=m.group(0),
            )
        return None

    def _extract_position(self, text: str) -> ExtractedEntity | None:
        m = _POSITION_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.POSITION, value=m.group(0),
                confidence=0.80, source_text=m.group(0),
            )
        m = re.search(r"\b(primer[oa]?|segund[oa]?|tercer[oa]?|cuart[oa]?|quint[oa]?)\s+(canción|tema|track|pista|elemento)\b", text, re.IGNORECASE)
        if m:
            return ExtractedEntity(
                name=EntityType.POSITION, value=m.group(0),
                confidence=0.85, source_text=m.group(0),
            )
        return None

    def _extract_scope(self, text: str) -> ExtractedEntity | None:
        m = _SCOPE_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.SCOPE, value=m.group(1).lower(),
                confidence=0.85, source_text=m.group(0),
            )
        return None

    def _extract_reference(self, text: str, context: dict[str, Any] | None) -> ExtractedEntity | None:
        m = _REFERENCE_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.PATH_REFERENCE, value=m.group(1).lower(),
                confidence=0.70, source_text=m.group(0),
                resolved=False,
            )
        return None

    def _extract_sort(self, text: str) -> ExtractedEntity | None:
        m = _SORT_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.SORT, value=m.group(0).lower(),
                confidence=0.80, source_text=m.group(0),
            )
        return None

    def _extract_filter(self, text: str) -> ExtractedEntity | None:
        m = _FILTER_PATTERN.search(text)
        if m:
            return ExtractedEntity(
                name=EntityType.FILTER, value=m.group(0).lower(),
                confidence=0.75, source_text=m.group(0),
            )
        return None
