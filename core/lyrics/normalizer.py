from __future__ import annotations

import re
import unicodedata

from core.lyrics.models import TrackIdentity, NormalizedIdentity

_FEAT_PATTERN = re.compile(
    r"\b(?:feat\.?|ft\.?|featuring)\b",
    re.IGNORECASE,
)
_REMIX_PATTERN = re.compile(
    r"\b(?:remix|remaster(?:ed)?|live|edit|version|acoustic|instrumental)\b",
    re.IGNORECASE,
)
_PAREN_TAG = re.compile(r"\([^)]*\)")
_BRACKET_TAG = re.compile(r"\[[^\]]*\]")
_PUNCTUATION = re.compile(r"[^\w\s]")
_MULTI_SPACE = re.compile(r"\s+")


class TrackIdentityNormalizer:
    @staticmethod
    def normalize(identity: TrackIdentity) -> NormalizedIdentity:
        norm = NormalizedIdentity(original=identity)

        title = identity.title or ""
        artist = identity.artist or ""
        album = identity.album or ""

        norm.normalized_title = TrackIdentityNormalizer._normalize_field(title)
        norm.normalized_artist = TrackIdentityNormalizer._normalize_field(artist)
        norm.normalized_album = TrackIdentityNormalizer._normalize_field(album)

        tokens = set()
        for part in (norm.normalized_title, norm.normalized_artist):
            for word in part.split():
                if len(word) > 1:
                    tokens.add(word)
        norm.matching_tokens = sorted(tokens)

        return norm

    @staticmethod
    def _normalize_field(text: str) -> str:
        text = unicodedata.normalize("NFKC", text)
        text = text.lower().strip()
        text = _PAREN_TAG.sub("", text)
        text = _BRACKET_TAG.sub("", text)
        text = _FEAT_PATTERN.sub("", text)
        text = _PUNCTUATION.sub("", text)
        text = _MULTI_SPACE.sub(" ", text)
        return text.strip()

    @staticmethod
    def are_similar(a: str, b: str) -> bool:
        na = TrackIdentityNormalizer._normalize_field(a)
        nb = TrackIdentityNormalizer._normalize_field(b)
        if na == nb:
            return True
        return bool(len(na) > 2 and len(nb) > 2 and (na in nb or nb in na))

    @staticmethod
    def is_live_version(text: str) -> bool:
        lower = text.lower()
        return bool(re.search(r"\b(?:live|en vivo|concert)\b", lower))

    @staticmethod
    def is_remix(text: str) -> bool:
        lower = text.lower()
        return bool(re.search(r"\b(?:remix|remaster|reissue)\b", lower))
