from __future__ import annotations

import re
from typing import Callable

from core.radio.models import StreamMetadata

_MAX_FIELD_LENGTH = 1024
_MAX_TITLE_LENGTH = 4096

_HEADER_PATTERN = re.compile(
    rb"^([\w-]+):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
)


def parse_icy_headers(raw: bytes) -> StreamMetadata:
    meta = StreamMetadata()

    for match in _HEADER_PATTERN.finditer(raw):
        key = match.group(1).lower().decode("ascii", errors="replace")
        value = _sanitize_string(match.group(2))

        if key == "icy-name":
            meta.icy_name = value[:_MAX_FIELD_LENGTH]
        elif key == "icy-genre":
            meta.icy_genre = value[:_MAX_FIELD_LENGTH]
        elif key == "icy-br":
            meta.icy_br = value[:_MAX_FIELD_LENGTH]
        elif key == "icy-url":
            meta.icy_url = value[:_MAX_FIELD_LENGTH]
        elif key == "icy-description":
            meta.icy_description = value[:_MAX_FIELD_LENGTH]
        elif key == "icy-metaint":
            pass

    return meta


def parse_icy_metaint(raw_headers: bytes) -> int:
    for match in _HEADER_PATTERN.finditer(raw_headers):
        key = match.group(1).lower().decode("ascii", errors="replace")
        if key == "icy-metaint":
            try:
                return int(match.group(2).strip())
            except (ValueError, TypeError):
                return 0
    return 0


def parse_stream_title(data: bytes, encoding: str = "utf-8") -> str | None:
    if not data:
        return None

    try:
        text = data.decode(encoding, errors="replace")
    except (LookupError, ValueError):
        text = data.decode("utf-8", errors="replace")

    text = text.strip("\x00\r\n\t ")

    if not text:
        return None

    text = _strip_non_printable(text)

    if len(text) > _MAX_TITLE_LENGTH:
        text = text[:_MAX_TITLE_LENGTH]

    text = _strip_null(text)

    if not text.strip():
        return None

    if text.startswith("StreamTitle='") or text.startswith('StreamTitle="'):
        end = text.find("';") if text.startswith("StreamTitle='") else text.find('";')
        if end == -1:
            end = text.rfind("'") if text.startswith("StreamTitle='") else text.rfind('"')
            if end <= len("StreamTitle='"):
                return None
        else:
            end = end + 1
        title = text[len("StreamTitle='"):end] if text.startswith("StreamTitle='") else text[len('StreamTitle="'):end]
        title = title.rstrip("';\"")
        return title.strip()

    return text


def _sanitize_string(raw: bytes) -> str:
    try:
        s = raw.decode("utf-8", errors="replace")
    except (LookupError, ValueError):
        s = raw.decode("latin-1", errors="replace")
    s = _strip_non_printable(s)
    s = _strip_null(s)
    return s.strip()


def _strip_non_printable(s: str) -> str:
    return "".join(c if c.isprintable() or c in "\n\r\t" else " " for c in s)


def _strip_null(s: str) -> str:
    return s.replace("\x00", "")


class IcyMetadataTracker:
    def __init__(self, on_metadata: Callable[[StreamMetadata], None] | None = None):
        self._last_metadata: StreamMetadata = StreamMetadata()
        self._on_metadata = on_metadata

    def update_headers(self, raw: bytes) -> StreamMetadata:
        meta = parse_icy_headers(raw)
        if self._has_changed(meta):
            self._last_metadata = meta
            if self._on_metadata:
                self._on_metadata(meta)
        return meta

    def update_stream_title(self, raw: bytes, encoding: str = "utf-8") -> str | None:
        title = parse_stream_title(raw, encoding)
        if title is None:
            return None
        if title != self._last_metadata.stream_title:
            self._last_metadata.stream_title = title
            if self._on_metadata:
                self._on_metadata(self._last_metadata)
        return title

    @property
    def current(self) -> StreamMetadata:
        return self._last_metadata

    def _has_changed(self, meta: StreamMetadata) -> bool:
        return (
            meta.icy_name != self._last_metadata.icy_name
            or meta.icy_genre != self._last_metadata.icy_genre
            or meta.icy_url != self._last_metadata.icy_url
            or meta.icy_br != self._last_metadata.icy_br
        )

    def reset(self):
        self._last_metadata = StreamMetadata()
