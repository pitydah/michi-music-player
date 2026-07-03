"""MPD protocol parser — parses MPD text responses into Python objects.

Handles OK, ACK, key: value pairs, multiline responses, and list responses.
Follows the MPD protocol specification: https://mpd.readthedocs.io/en/latest/protocol.html
"""

from audio.mpd.mpd_errors import MpdProtocolError, MpdAckError


class MpdResponse:
    """Parsed MPD response."""

    def __init__(self, lines: list[str], raw: str = ""):
        self.lines = lines
        self.raw = raw
        self.is_ok = False
        self.is_ack = False
        self.ack_code = 0
        self.ack_message = ""
        self.pairs: dict[str, str] = {}
        self.lists: dict[str, list[dict[str, str]]] = {}
        self._parse()

    LIST_HEADER_KEYS = {"file", "directory", "playlist", "outputid"}

    def _parse(self):
        if not self.lines:
            raise MpdProtocolError("Empty response")

        last = self.lines[-1].strip()

        if last == "OK" or last.startswith("OK MPD "):
            self.is_ok = True
            body = self.lines[:-1]
        elif last.startswith("ACK"):
            self.is_ack = True
            self._parse_ack(last)
            body = self.lines[:-1]
        else:
            body = self.lines

        if body:
            self._parse_body(body)

    def _parse_ack(self, line: str):
        """Parse ACK [code@tag] {message}"""
        rest = line[3:].strip()
        if rest.startswith("[") and "]" in rest:
            bracket_end = rest.index("]")
            code_tag = rest[1:bracket_end]
            rest = rest[bracket_end + 1:].strip()
            if "@" in code_tag:
                parts = code_tag.split("@")
                try:
                    self.ack_code = int(parts[0])
                except ValueError:
                    self.ack_code = -1
        self.ack_message = rest.strip("{} ")

    def _parse_body(self, body: list[str]):
        entries: list[dict[str, str]] = []
        current: dict[str, str] = {}
        first_key: str | None = None

        for line in body:
            stripped = line.strip()
            if not stripped:
                if current:
                    entries.append(current)
                    current = {}
                continue

            if ": " not in stripped:
                continue

            key, value = stripped.split(": ", 1)
            key = key.strip()
            value = value.strip()

            if not first_key:
                first_key = key

            if first_key and key in self.LIST_HEADER_KEYS and current and key in current:
                entries.append(current)
                current = {}

            current[key] = value

        if current:
            entries.append(current)

        self.pairs = {}

        if len(entries) == 1:
            entry = entries[0]
            list_candidate = first_key
            has_header = list_candidate in self.LIST_HEADER_KEYS
            if has_header:
                self.lists[list_candidate] = entries
                for k, v in entry.items():
                    if k not in self.LIST_HEADER_KEYS:
                        self.pairs[k] = v
            else:
                for k, v in entry.items():
                    self.pairs[k] = v
                if first_key:
                    self.lists[first_key] = entries
        elif len(entries) > 1:
            list_key = first_key or "entry"
            for entry in entries:
                for k, v in entry.items():
                    if k not in self.LIST_HEADER_KEYS:
                        self.pairs[k] = v
            self.lists[list_key] = entries

    def require_ok(self):
        if self.is_ack:
            raise MpdAckError(
                f"MPD ACK [{self.ack_code}]: {self.ack_message}")
        if not self.is_ok:
            raise MpdProtocolError(f"Unexpected response: {self.raw[:200]}")

    def first_list(self) -> list[dict[str, str]]:
        for lst in self.lists.values():
            return lst
        return []


def parse_response(raw: str) -> MpdResponse:
    """Parse a raw MPD response string into an MpdResponse.

    Empty lines in the body are entry separators in MPD's list format.
    We keep them by replacing empty lines with a sentinel before filtering
    trailing-only empties.
    """
    all_lines = raw.split("\n")
    non_empty = []
    for i, line in enumerate(all_lines):
        stripped = line.strip()
        if not stripped:
            if i < len(all_lines) - 1 and any(all_lines[j].strip() for j in range(i + 1, len(all_lines))):
                non_empty.append("")
            continue
        non_empty.append(stripped)
    return MpdResponse(non_empty, raw)
