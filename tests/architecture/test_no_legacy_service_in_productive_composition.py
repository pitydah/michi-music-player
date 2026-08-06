"""LEGACY_COMPONENT classes must never enter productive composition."""
from __future__ import annotations

from tests.architecture._helpers import composition_source

# Classes designated LEGACY_COMPONENT in the manifest — composition must not
# import, instantiate, or register them under any productive key.
# LibraryMutationService is NOT legacy anymore: Slice 3 bound the
# library_mutation_service key to the real class (it was an orphan only
# because the key pointed at MetadataEditorService).
LEGACY_CLASS_NAMES = (
    "JobManager",
    "AudioLabJobAdapter",
)


def test_legacy_classes_absent_from_composition() -> None:
    source = composition_source()
    for class_name in LEGACY_CLASS_NAMES:
        assert class_name not in source, (
            f"LEGACY_COMPONENT class '{class_name}' appears in composition builders"
        )


def test_manifest_legacy_markers_aligned() -> None:
    from core.service_manifest import SERVICE_MANIFEST, ServiceClass

    legacy_entries = {
        name for name, desc in SERVICE_MANIFEST.items()
        if desc.service_class == ServiceClass.LEGACY_COMPONENT
    }
    assert legacy_entries == {"job_manager", "audio_lab_job_adapter"}, (
        f"Unexpected LEGACY_COMPONENT manifest entries: {legacy_entries}"
    )
