"""Device knowledge service — provenance-resolved enrichment (AP2-F02).

Read-only projection over a versioned offline knowledge document. This service
never admits devices, never qualifies tuples, never writes USB/ALSA controls
and never talks to the network: ``AudioDeviceRegistry`` admission and
``DacQualificationService`` stay authoritative.

Failure is fail-soft by construction: a corrupt document, malformed entries or
missing provenance produce less knowledge, never an exception and never a
blocked playback path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from michi.domain.audio_device_knowledge import (
    DeviceKnowledge,
    EvidenceConfidence,
    EvidenceOrigin,
    EvidenceResolution,
    EvidenceSource,
)


@dataclass(frozen=True, slots=True)
class _KnowledgeEntry:
    """One parsed, provenance-complete knowledge row."""

    stable_device_id: str | None
    vendor_id: str | None
    product_id: str | None
    manufacturer_label: str | None
    product_label: str | None
    capability_hints: tuple[str, ...]
    sources: tuple[EvidenceSource, ...]

    def matches(
        self,
        stable_device_id: str,
        vendor_id: str | None,
        product_id: str | None,
    ) -> bool:
        if self.stable_device_id is not None:
            return self.stable_device_id == stable_device_id
        if self.vendor_id is not None and self.product_id is not None:
            return self.vendor_id == vendor_id and self.product_id == product_id
        return False


def _split_usb_ids(stable_device_id: str) -> tuple[str | None, str | None]:
    parts = stable_device_id.strip().split(":")
    if len(parts) >= 3 and parts[0] == "usb" and parts[1].strip() and parts[2].strip():
        return parts[1].strip().lower(), parts[2].strip().lower()
    return None, None


def _clean_text(raw: Any) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _enum_by_value_or_name(enum_type: type[Enum], raw: Any) -> Any:
    token = _clean_text(raw)
    if token is None:
        return None
    for member in enum_type:
        if member.value == token or member.name.lower() == token.lower():
            return member
    return None


def _parse_hints(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, dict):
        return tuple(str(key) for key, value in raw.items() if value)
    if isinstance(raw, (list, tuple)):
        return tuple(
            item.strip() for item in raw if isinstance(item, str) and item.strip()
        )
    return ()


def _parse_provenance(
    raw: Any, default_version: str | None
) -> tuple[EvidenceSource, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    sources: list[EvidenceSource] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        origin = _enum_by_value_or_name(EvidenceOrigin, item.get("origin"))
        if origin is None:
            continue
        ref = _clean_text(item.get("source_ref"))
        if ref is None:
            continue
        confidence = (
            _enum_by_value_or_name(EvidenceConfidence, item.get("confidence"))
            or EvidenceConfidence.UNKNOWN
        )
        version = _clean_text(item.get("source_version")) or default_version
        sources.append(
            EvidenceSource(
                origin=origin,
                confidence=confidence,
                source_ref=ref,
                source_version=version,
            )
        )
    return tuple(sources)


def _parse_entry(raw: Any, default_version: str | None) -> _KnowledgeEntry | None:
    if not isinstance(raw, dict):
        return None
    match = raw.get("match")
    if not isinstance(match, dict):
        return None
    stable_device_id = _clean_text(match.get("stable_device_id"))
    vendor_id = _clean_text(match.get("vid"))
    product_id = _clean_text(match.get("pid"))
    vendor_id = vendor_id.lower() if vendor_id is not None else None
    product_id = product_id.lower() if product_id is not None else None
    if stable_device_id is None and (vendor_id is None or product_id is None):
        # Partial match keys never invent a match: vid alone is ambiguous.
        return None
    identity = raw.get("identity")
    identity = identity if isinstance(identity, dict) else {}
    sources = _parse_provenance(raw.get("provenance"), default_version)
    if not sources:
        # Every displayed enrichment has provenance; unbacked rows are dropped.
        return None
    return _KnowledgeEntry(
        stable_device_id=stable_device_id,
        vendor_id=vendor_id,
        product_id=product_id,
        manufacturer_label=_clean_text(identity.get("commercial_manufacturer")),
        product_label=_clean_text(identity.get("commercial_model")),
        capability_hints=_parse_hints(raw.get("declared_capabilities")),
        sources=sources,
    )


def _load_entries(
    document: Any, source_version: str | None
) -> tuple[_KnowledgeEntry, ...]:
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except (TypeError, ValueError):
            return ()
    if isinstance(document, dict):
        version = _clean_text(document.get("version")) or source_version
        entries = document.get("entries")
    elif isinstance(document, (list, tuple)):
        version = source_version
        entries = document
    else:
        return ()
    if not isinstance(entries, (list, tuple)):
        return ()
    parsed: list[_KnowledgeEntry] = []
    for raw in entries:
        entry = _parse_entry(raw, version)
        if entry is not None:
            parsed.append(entry)
    return tuple(parsed)


class AudioDeviceKnowledgeService:
    """Resolve device knowledge with explicit, displayable provenance."""

    def __init__(
        self, document: Any = None, *, source_version: str | None = None
    ) -> None:
        self._entries = _load_entries(document, source_version)

    @classmethod
    def empty(cls) -> AudioDeviceKnowledgeService:
        return cls(None)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def knowledge_for(self, stable_device_id: str) -> DeviceKnowledge:
        """Descriptive enrichment only; never an admission or capability fact."""
        query = stable_device_id.strip() or stable_device_id
        vendor_id, product_id = _split_usb_ids(query)
        matches = [
            entry
            for entry in self._entries
            if entry.matches(query, vendor_id, product_id)
        ]
        if not matches:
            return DeviceKnowledge.unknown(query)
        sources: list[EvidenceSource] = []
        for entry in matches:
            for source in entry.sources:
                if source not in sources:
                    sources.append(source)
        labels = {(entry.manufacturer_label, entry.product_label) for entry in matches}
        if len(labels) != 1:
            # Contradictory rows stay conflicted: no label and no hint is
            # invented, only the provenance of the conflict is displayed.
            return DeviceKnowledge(
                stable_device_id=query,
                manufacturer_label=None,
                product_label=None,
                capability_hints=(),
                sources=tuple(sources),
                resolution=EvidenceResolution.CONFLICTED,
            )
        manufacturer, product = next(iter(labels))
        hints: list[str] = []
        for entry in matches:
            for hint in entry.capability_hints:
                if hint not in hints:
                    hints.append(hint)
        return DeviceKnowledge(
            stable_device_id=query,
            manufacturer_label=manufacturer,
            product_label=product,
            capability_hints=tuple(hints),
            sources=tuple(sources),
            resolution=EvidenceResolution.RESOLVED,
        )
