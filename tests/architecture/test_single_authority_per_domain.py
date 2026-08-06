"""Single authority per domain: exactly one productive implementation each.

Every known duplicate *Service class must have exactly one productive
implementation file; the rest are explicitly designated legacy. Mirrors the
duplicity table of RUNTIME_SERVICE_AUDIT_CURRENT §8.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# class name -> (productive file, legacy files). Legacy entries that no longer
# exist on disk are tolerated so retirement can proceed file by file.
DOMAIN_AUTHORITY: dict[str, tuple[str, tuple[str, ...]]] = {
    "MicroServerService": (
        "integrations/michi_link/services/micro_server_service.py",
        ("core/micro_server_service.py", "integrations/micro_server_service.py"),
    ),
    "ContinueOnServerService": (
        "integrations/michi_link/services/continue_on_server_service.py",
        ("integrations/michi_link/continue_on_server_service.py",),
    ),
    "RadioService": (
        "core/radio/service.py",
        ("core/radio/radio_service.py",),
    ),
    "LyricsService": (
        "core/lyrics/service.py",
        ("core/lyrics_service.py",),
    ),
    "CoverArtService": (
        "core/library/artwork_resolver.py",
        ("core/cover_art_service.py", "library/cover_art_service.py"),
    ),
}

SCAN_DIRS = ("core", "library", "streaming", "recognition", "integrations",
             "ui_qml_bridge", "sync")
_CLASS_RE = re.compile(r"^class\s+(\w+)\b", re.M)


def _find_defining_files(class_name: str) -> list[str]:
    found = []
    for directory in SCAN_DIRS:
        base = PROJECT_ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(rf"^class\s+{class_name}\b", source, re.M):
                found.append(path.relative_to(PROJECT_ROOT).as_posix())
    return sorted(found)


def test_known_duplicates_have_single_productive_implementation() -> None:
    for class_name, (productive, legacy) in DOMAIN_AUTHORITY.items():
        defining = _find_defining_files(class_name)
        assert productive in defining, (
            f"{class_name}: productive file '{productive}' no longer defines it "
            f"(defining files: {defining})"
        )
        extra = [f for f in defining if f != productive and f not in legacy]
        assert extra == [], (
            f"{class_name}: unexpected defining files not designated legacy: {extra}"
        )
        assert len(defining) >= 2, (
            f"{class_name}: expected at least 2 defining files, found {defining}"
        )


def test_legacy_files_are_designated_in_manifest() -> None:
    """Legacy implementations must not be bound to productive manifest keys."""
    from core.service_manifest import SERVICE_MANIFEST, ServiceClass

    legacy_classes = {
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.service_class == ServiceClass.LEGACY_COMPONENT
    }
    assert "job_manager" in legacy_classes
    assert "audio_lab_job_adapter" in legacy_classes


def test_radio_and_lyrics_authority_match_manifest() -> None:
    from core.service_manifest import SERVICE_MANIFEST, ServiceClass, ServicePriority

    radio = SERVICE_MANIFEST["radio_service"]
    lyrics = SERVICE_MANIFEST["lyrics_service"]
    assert radio.priority == ServicePriority.OPTIONAL
    assert lyrics.priority == ServicePriority.OPTIONAL
    assert radio.service_class != ServiceClass.LEGACY_COMPONENT
    assert lyrics.service_class != ServiceClass.LEGACY_COMPONENT
