from __future__ import annotations

import re

from core.lyrics.models import LyricsLine, LyricsMetadata, LyricsDocument, LyricsWord
import contextlib

_LINE_PATTERN = re.compile(
    r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]",
)
_ENHANCED_WORD_PATTERN = re.compile(
    r"<(\d{1,3}):(\d{2})\.(\d{2,3})>",
)
_TAG_PATTERN = re.compile(
    r"^\[([a-zA-Z]+):(.+)\]$"
)
_KNOWN_TAGS = frozenset({
    "ar", "al", "ti", "by", "re", "ve", "la", "offset",
})


def parse_lrc(text: str) -> LyricsDocument:
    doc = LyricsDocument()
    lines: list[LyricsLine] = []
    plain_lines: list[str] = []
    offset_ms = 0
    current_line_id = 0

    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            continue

        tag_match = _TAG_PATTERN.match(stripped)
        if tag_match:
            tag_key = tag_match.group(1).lower()
            tag_value = tag_match.group(2).strip()
            if tag_key in _KNOWN_TAGS:
                _apply_tag(doc.metadata, tag_key, tag_value)
                if tag_key == "offset":
                    with contextlib.suppress(ValueError, TypeError):
                        offset_ms = int(tag_value)
            continue

        timestamps = list(_LINE_PATTERN.finditer(stripped))
        if not timestamps:
            plain_lines.append(stripped)
            continue

        text_part = stripped[timestamps[-1].end():].strip()
        if not text_part:
            continue

        for m in timestamps:
            ts_ms = _to_ms(m)
            adjusted_ts = max(0, ts_ms + offset_ms)
            line = LyricsLine(
                line_id=str(current_line_id),
                start_ms=float(adjusted_ts),
                text=text_part,
            )
            _try_extract_words(stripped, line)
            lines.append(line)
            current_line_id += 1

    lines.sort(key=lambda ln: ln.start_ms)
    _assign_end_times(lines)

    doc.lines = lines
    doc.plain_text = "\n".join(plain_lines)
    doc.synced_text = text
    doc.offset_ms = offset_ms

    for ln in lines:
        if ln.text:
            doc.plain_text = doc.plain_text + ("\n" + ln.text if doc.plain_text else ln.text)

    return doc


def serialize_lrc(doc: LyricsDocument) -> str:
    parts: list[str] = []

    meta = doc.metadata
    if meta.artist:
        parts.append(f"[ar:{meta.artist}]")
    if meta.album:
        parts.append(f"[al:{meta.album}]")
    if meta.title:
        parts.append(f"[ti:{meta.title}]")
    if meta.author:
        parts.append(f"[by:{meta.author}]")
    if meta.editor:
        parts.append(f"[re:{meta.editor}]")
    if meta.version:
        parts.append(f"[ve:{meta.version}]")
    if meta.language:
        parts.append(f"[la:{meta.language}]")
    if doc.offset_ms:
        parts.append(f"[offset:{doc.offset_ms}]")

    for line in doc.lines:
        if line.words and all(w.start_ms >= 0 for w in line.words):
            word_str = "".join(
                f"<{int(w.start_ms // 60000):d}:{int((w.start_ms % 60000) / 1000):02d}.{int(w.start_ms % 1000):03d}>{w.text}"
                for w in line.words
            )
            parts.append(word_str)
        elif line.start_ms >= 0:
            ts = _format_ts(line.start_ms)
            parts.append(f"[{ts}]{line.text}")
        else:
            parts.append(line.text)

    return "\n".join(parts)


def parse_plain(text: str) -> LyricsDocument:
    doc = LyricsDocument()
    lines: list[LyricsLine] = []
    for i, raw in enumerate(text.strip().split("\n")):
        s = raw.strip()
        if s:
            lines.append(LyricsLine(line_id=str(i), text=s))
    doc.lines = lines
    doc.plain_text = text
    return doc


def normalize_document(doc: LyricsDocument) -> LyricsDocument:
    doc.lines.sort(key=lambda ln: ln.start_ms)
    _assign_end_times(doc.lines)
    if doc.offset_ms != 0:
        for line in doc.lines:
            line.start_ms = max(0, line.start_ms + doc.offset_ms)
            line.end_ms = max(0, line.end_ms + doc.offset_ms)
            for w in line.words:
                w.start_ms = max(0, w.start_ms + doc.offset_ms)
                w.end_ms = max(0, w.end_ms + doc.offset_ms)
        doc.offset_ms = 0
    return doc


def _apply_tag(meta: LyricsMetadata, key: str, value: str):
    mapping = {
        "ar": "artist", "al": "album", "ti": "title",
        "by": "author", "re": "editor", "ve": "version", "la": "language",
    }
    field = mapping.get(key)
    if field:
        setattr(meta, field, value)


def _to_ms(match: re.Match) -> int:
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    millis_str = match.group(3)
    if millis_str is None:
        return (minutes * 60 + seconds) * 1000
    millis = int(millis_str.ljust(3, "0")[:3])
    return (minutes * 60 + seconds) * 1000 + millis


def _format_ts(ms: float) -> str:
    total_sec = int(ms / 1000)
    minutes = total_sec // 60
    seconds = total_sec % 60
    millis = int(ms % 1000)
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"


def _try_extract_words(raw_line: str, line: LyricsLine):
    words = []
    pos = 0
    for m in _ENHANCED_WORD_PATTERN.finditer(raw_line):
        if m.start() < pos:
            continue
        word_start = _enhanced_to_ms(m)
        word_text_end = raw_line.find(" ", m.end())
        if word_text_end == -1:
            word_text = raw_line[m.end():].strip()
        else:
            word_text = raw_line[m.end():word_text_end].strip()
        if word_text and word_start >= 0:
            words.append(LyricsWord(
                start_ms=float(word_start),
                text=word_text,
            ))
        pos = m.end()
    if words:
        for i in range(len(words) - 1):
            words[i].end_ms = words[i + 1].start_ms
        line.words = words
        if words and line.start_ms == 0:
            line.start_ms = words[0].start_ms


def _enhanced_to_ms(match: re.Match) -> int:
    minutes = int(match.group(1))
    seconds = int(match.group(2))
    millis_str = match.group(3)
    millis = int(millis_str.ljust(3, "0")[:3])
    return (minutes * 60 + seconds) * 1000 + millis


def _assign_end_times(lines: list[LyricsLine]):
    for i in range(len(lines) - 1):
        if lines[i].end_ms <= 0 and lines[i + 1].start_ms > lines[i].start_ms:
            lines[i].end_ms = lines[i + 1].start_ms
    if lines and lines[-1].end_ms <= 0:
        lines[-1].end_ms = lines[-1].start_ms + 5000
