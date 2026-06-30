"""Query parser — parse field-based search queries like artist:Genesis year:>2000."""
import re
from dataclasses import dataclass, field
from enum import Enum


class FieldOp(Enum):
    EQ = "="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="


@dataclass
class FieldTerm:
    field: str
    op: FieldOp
    value: str


@dataclass
class ParsedQuery:
    """Result of parsing a search query string."""
    freetext: str = ""                     # remaining free-text portion
    terms: list[FieldTerm] = field(default_factory=list)
    sort_field: str = ""
    sort_asc: bool = True

    @property
    def has_field_terms(self) -> bool:
        return len(self.terms) > 0

    @property
    def is_empty(self) -> bool:
        return not self.freetext and not self.terms


# Field names understood by the parser → column or filter
FIELD_MAP: dict[str, str] = {
    "artist": "artist",
    "album": "album",
    "albumartist": "albumartist",
    "title": "title",
    "genre": "genre",
    "composer": "composer",
    "year": "year",
    "format": "ext",
    "ext": "ext",
    "kind": "kind",
    "bitrate": "bitrate",
    "rating": "rating",
    "play_count": "play_count",
    "path": "filepath",
    "directory": "directory",
    "filename": "filename",
    "source": "source_type",
    "bpm": "bpm",
    "sample_rate": "sample_rate",
    "channels": "channels",
    "bit_depth": "bit_depth",
    "key": "key",
    "quality": "quality",
}

OPERATOR_PATTERN = re.compile(r'(>=|<=|!=|>|<|=)')


def parse_query(text: str) -> ParsedQuery:
    """Parse a field-based query string into a ParsedQuery.

    Examples:
        artist:Genesis album:"The Lamb Lies Down" year:1974
        format:flac bitrate:>900 rating:>=4
        path:/Music/Jazz some free text
    """
    if not text:
        return ParsedQuery()

    result = ParsedQuery()
    remaining = text.strip()
    freetext_parts: list[str] = []

    while remaining:
        # Match field:value or field:"quoted value"
        m = re.match(r'([a-z_]+)\s*:\s*', remaining, re.IGNORECASE)
        if not m:
            # No field prefix — consume next token as freetext
            next_space = remaining.find(" ")
            if next_space == -1:
                freetext_parts.append(remaining)
                remaining = ""
            else:
                freetext_parts.append(remaining[:next_space])
                remaining = remaining[next_space + 1:].lstrip()
            continue

        field_label = m.group(1).lower()
        column = FIELD_MAP.get(field_label)
        after_colon = remaining[m.end():]

        # Extract value (quoted or unquoted)
        value, consumed = _extract_value(after_colon)
        remaining = after_colon[consumed:].lstrip()

        if column is None:
            # Unknown field → treat as freetext
            freetext_parts.append(f"{field_label}:{value}")
            continue

        # Parse operator from value
        op, clean_value = _parse_operator(value)

        if field_label in ("sort", "order"):
            result.sort_field = clean_value
            result.sort_asc = not clean_value.lower().startswith("desc")
            continue

        result.terms.append(FieldTerm(field=column, op=op, value=clean_value))

    result.freetext = " ".join(freetext_parts).strip()
    return result


def _extract_value(text: str) -> tuple[str, int]:
    """Extract a value from text, handling quoted strings.

    Returns (value, chars_consumed).
    """
    text = text.lstrip()
    if not text:
        return "", 0

    if text[0] == '"':
        end = text.find('"', 1)
        if end != -1:
            return text[1:end], end + 1
        return text[1:], len(text)

    # Unquoted — consume until space or end
    space = text.find(" ")
    if space == -1:
        return text, len(text)
    return text[:space], space


def _parse_operator(value: str) -> tuple[FieldOp, str]:
    """Extract comparison operator from value.

    '>=4'  → (FieldOp.GTE, '4')
    '>900'  → (FieldOp.GT, '900')
    '<100'  → (FieldOp.LT, '100')
    '<=5'   → (FieldOp.LTE, '5')
    '1974'  → (FieldOp.EQ, '1974')
    """
    m = OPERATOR_PATTERN.match(value)
    if not m:
        return FieldOp.EQ, value

    op_str = m.group(1)
    op_map = {
        ">=": FieldOp.GTE,
        "<=": FieldOp.LTE,
        "!=": FieldOp.EQ,  # mapped to NOT EQ in SQL
        ">": FieldOp.GT,
        "<": FieldOp.LT,
        "=": FieldOp.EQ,
    }
    clean_value = value[m.end():].strip()
    return op_map.get(op_str, FieldOp.EQ), clean_value
