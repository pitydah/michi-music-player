"""Device knowledge as descriptive enrichment (AP2-F02, R11-F02).

Pure domain module: stdlib only, no sysfs/USB/ALSA access, no persistence, no
network and no admission logic. Knowledge describes what is *documented* about
a device; it never admits, hides or qualifies anything. ``AudioDeviceRegistry``
admission and ``DacQualificationService`` stay authoritative.

The evidence vocabulary is the F02-local subset of the closed multisource
model (spec 126): a later phase owns the full ``domain/evidence.py`` model and
may re-export or adapt these primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceOrigin(Enum):
    """Where a knowledge claim came from (spec 126 vocabulary)."""

    SYSFS = "sysfs"
    USB_DESCRIPTOR = "usb_descriptor"
    ALSA = "alsa"
    UDEV_HWDB = "udev_hwdb"
    USB_IDS = "usb_ids"
    KERNEL_KNOWLEDGE = "kernel_knowledge"
    MICHI_KB = "michi_kb"
    PHYSICAL_QUALIFICATION = "physical_qualification"
    RUNTIME = "runtime"
    MANUFACTURER_DECLARED = "manufacturer_declared"


class EvidenceConfidence(Enum):
    """Strength of one provenance record (spec 126 vocabulary)."""

    AUTHORITATIVE = "authoritative"
    STRONG = "strong"
    CORROBORATED = "corroborated"
    WEAK = "weak"
    UNKNOWN = "unknown"


class EvidenceResolution(Enum):
    """Aggregate state of a resolved knowledge claim (spec 126 vocabulary)."""

    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    CONFLICTED = "conflicted"
    STALE = "stale"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """One provenance record behind a knowledge claim."""

    origin: EvidenceOrigin
    confidence: EvidenceConfidence
    source_ref: str
    source_version: str | None = None

    def __post_init__(self) -> None:
        if not self.source_ref.strip():
            raise ValueError("evidence source requires a concrete source_ref")

    @property
    def label(self) -> str:
        """Deterministic display label: ``origin:ref`` plus ``@version``."""
        base = f"{self.origin.value}:{self.source_ref}"
        return f"{base}@{self.source_version}" if self.source_version else base


@dataclass(frozen=True, slots=True)
class DeviceKnowledge:
    """Resolved descriptive enrichment for one retained stable identity.

    ``resolution`` never promotes knowledge into runtime truth: a documented
    capability hint does not change the planner's ``UNKNOWN`` runtime
    capability, and a missing or conflicted row stays explicitly unknown.
    """

    stable_device_id: str
    manufacturer_label: str | None
    product_label: str | None
    capability_hints: tuple[str, ...]
    sources: tuple[EvidenceSource, ...]
    resolution: EvidenceResolution

    def __post_init__(self) -> None:
        if not self.stable_device_id.strip():
            raise ValueError("device knowledge requires a stable_device_id")
        if self.resolution is EvidenceResolution.RESOLVED and not self.sources:
            raise ValueError("resolved knowledge requires at least one source")

    @classmethod
    def unknown(cls, stable_device_id: str) -> DeviceKnowledge:
        """Fail-closed enrichment used when nothing is known or resolvable."""
        return cls(
            stable_device_id=stable_device_id,
            manufacturer_label=None,
            product_label=None,
            capability_hints=(),
            sources=(),
            resolution=EvidenceResolution.UNKNOWN,
        )

    @property
    def provenance_labels(self) -> tuple[str, ...]:
        return tuple(source.label for source in self.sources)
