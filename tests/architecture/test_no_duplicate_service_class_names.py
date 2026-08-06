"""No undocumented duplicate class names across runtime modules.

A duplicate class name is only acceptable when it is declared in this test's
designation table (exact file sets are enforced): service-level duplicates
must have exactly one productive implementation, and parallel-layer names
(DTOs, interfaces, per-layer providers) are documented as coexisting.
Any NEW duplicate name fails this test.
"""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SCAN_DIRS = ("core", "library", "streaming", "recognition", "integrations",
             "ui_qml_bridge", "sync")
_CLASS_RE = re.compile(r"^class\s+(\w+)\b", re.M)

# Service-level duplicates: exactly one productive file per class name.
SERVICE_DUPLICATES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # (productive files, legacy files)
    "MicroServerService": (
        ("integrations/michi_link/services/micro_server_service.py",),
        ("core/micro_server_service.py", "integrations/micro_server_service.py"),
    ),
    "ContinueOnServerService": (
        ("integrations/michi_link/services/continue_on_server_service.py",),
        ("integrations/michi_link/continue_on_server_service.py",),
    ),
    "RadioService": (
        ("core/radio/service.py",),
        ("core/radio/radio_service.py",),
    ),
    "LyricsService": (
        ("core/lyrics/service.py",),
        ("core/lyrics_service.py",),
    ),
    "CoverArtService": (
        ("core/library/artwork_resolver.py",),
        ("core/cover_art_service.py", "library/cover_art_service.py"),
    ),
}

# Parallel-layer names that legitimately coexist (repositories, DTOs,
# interfaces, per-layer providers). Exact file sets are enforced.
COEXISTING_DUPLICATES: dict[str, tuple[str, ...]] = {
    "AlbumEnrichmentService": (
        "core/album_enrichment_service.py",
        "integrations/artist_metadata/album_enrichment_service.py",
    ),
    "ArtistEnrichmentService": (
        "core/artist_enrichment_service.py",
        "integrations/artist_metadata/artist_enrichment_service.py",
    ),
    "AlbumIdentity": (
        "core/library/identity.py",
        "library/album_identity.py",
    ),
    "AlbumRepository": (
        "core/library/repositories/album_repository.py",
        "library/album_repository.py",
    ),
    "GenreRepository": (
        "core/library/repositories/genre_repository.py",
        "library/genre_repository.py",
    ),
    "TrackIdentity": (
        "core/library/identity.py",
        "core/lyrics/models.py",
        "integrations/michi_link/services/track_identity_service.py",
    ),
    "Clock": (
        "core/radio/interfaces.py",
        "core/lyrics/interfaces.py",
    ),
    "NetworkStatus": (
        "core/radio/interfaces.py",
        "core/lyrics/interfaces.py",
    ),
    "EventBus": (
        "core/event_bus.py",
        "core/radio/events.py",
    ),
    "IntentResult": (
        "core/ai/intent_router.py",
        "integrations/ai_assistant/intent_router.py",
    ),
    "IntentRouter": (
        "core/ai/intent_router.py",
        "integrations/ai_assistant/intent_router.py",
    ),
    "LibraryContextProvider": (
        "core/assistant_context_providers.py",
        "core/context/providers/library_context_provider.py",
    ),
    "PlaybackContextProvider": (
        "core/assistant_context_providers.py",
        "core/context/providers/playback_context_provider.py",
    ),
    "SettingsContextProvider": (
        "core/assistant_context_providers.py",
        "core/context/providers/settings_context_provider.py",
    ),
    "SnapcastAdapter": (
        "integrations/connections/adapters/snapcast_adapter.py",
        "ui_qml_bridge/adapters/snapcast_adapter.py",
    ),
    "OperationResult": (
        "core/results.py",
        "core/result.py",
        "core/models/operation_result.py",
    ),
    "PairedDevice": (
        "core/device_sync_service.py",
        "core/mobile_sync_service.py",
        "core/sync/device_registry.py",
    ),
    "TrackDto": (
        "integrations/michi_link/models.py",
        "sync/sync_protocol.py",
    ),
    "DeviceInfo": (
        "sync/sync_protocol.py",
        "sync/transport.py",
    ),
    "ConfigChange": (
        "integrations/michi_ecosystem/ecosystem_models.py",
        "integrations/michi_ecosystem/config_planner.py",
    ),
    "ConversionJob": (
        "core/audio_lab/audio_conversion_service.py",
        "ui_qml_bridge/conversion_bridge.py",
    ),
    "ConversionProfile": (
        "core/audio_lab/audio_conversion_service.py",
        "core/audio_lab/audio_lab_contracts.py",
    ),
    "HomeAudioError": (
        "integrations/home_audio_service.py",
        "integrations/home_audio_errors.py",
    ),
    "MixDefinition": (
        "core/mix_rules.py",
        "core/mix/repository.py",
    ),
    "RadioStation": (
        "core/radio/repository.py",
        "streaming/radio_manager.py",
    ),
    "SettingsApplyResult": (
        "core/settings_adapters.py",
        "core/settings_runtime_coordinator.py",
    ),
    "EcosystemConfigPlanner": (
        "integrations/michi_ecosystem/ecosystem_config_planner.py",
        "integrations/michi_ecosystem/config_planner.py",
    ),
    "EcosystemHealthGraph": (
        "integrations/michi_ecosystem/ecosystem_models.py",
        "integrations/michi_ecosystem/health_graph.py",
    ),
}

ALL_DESIGNATIONS = {
    name: (prod + legacy)
    for name, (prod, legacy) in SERVICE_DUPLICATES.items()
}
ALL_DESIGNATIONS.update(COEXISTING_DUPLICATES)


def _all_class_names() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for directory in SCAN_DIRS:
        base = PROJECT_ROOT / directory
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            for match in _CLASS_RE.finditer(source):
                found.setdefault(match.group(1), []).append(
                    path.relative_to(PROJECT_ROOT).as_posix()
                )
    return {name: sorted(files) for name, files in found.items()}


def test_no_undocumented_duplicate_class_names() -> None:
    duplicates = {
        name: files for name, files in _all_class_names().items()
        if len(set(files)) > 1
    }
    undocumented = {
        name: files for name, files in duplicates.items()
        if name not in ALL_DESIGNATIONS
    }
    assert undocumented == {}, (
        f"Undocumented duplicate class names: {undocumented}"
    )


def test_documented_duplicates_match_exact_file_sets() -> None:
    actual = _all_class_names()
    for name, expected_files in ALL_DESIGNATIONS.items():
        defining = actual.get(name, [])
        assert sorted(expected_files) == defining, (
            f"Duplicate '{name}' file set drifted: "
            f"expected {sorted(expected_files)}, found {defining}"
        )


def test_service_duplicates_have_single_productive_file() -> None:
    for name, (productive, legacy) in SERVICE_DUPLICATES.items():
        assert len(productive) == 1, (
            f"'{name}' must have exactly one productive file, got {productive}"
        )
        assert not set(productive) & set(legacy), (
            f"'{name}' productive/legacy sets overlap"
        )
