"""Michi Link single-domain authority (Slice 7, ADR-002).

- Exactly ONE productive ``MicroServerService`` and ONE productive
  ``ContinueOnServerService`` exist in the tree. A class is productive when
  its module is NOT marked ``# LEGACY``.
- The composition registers the advanced ``integrations/michi_link/services/``
  stack under ``michi_link_*`` keys; the legacy variants are never imported
  by composition builders or QML bridges.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests.architecture._helpers import composition_source

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

LEGACY_MARKER = "# LEGACY"

# Module → class names it must NOT define as productive.
DESIGNATED_LEGACY_MODULES = {
    "core/micro_server_service.py": "MicroServerService",
    "integrations/micro_server_service.py": "MicroServerService",
    "integrations/michi_link/micro_server_client.py": "MicroServerClient",
    "integrations/michi_link/import_client.py": "ImportClient",
    "integrations/michi_link/continue_on_server_service.py": "ContinueOnServerService",
}

PRODUCTIVE_MODULES = {
    "integrations/michi_link/services/micro_server_service.py": "MicroServerService",
    "integrations/michi_link/services/continue_on_server_service.py": "ContinueOnServerService",
    "integrations/michi_link/services/import_to_server_service.py": "ImportToServerService",
    "integrations/michi_link/services/remote_library_service.py": "RemoteLibraryService",
    "integrations/michi_link/services/track_identity_service.py": "TrackIdentityService",
    "integrations/michi_link/services/diagnostics_service.py": "LinkDiagnosticsService",
}

COMPOSITION_KEYS = (
    "michi_link_client",
    "michi_link_server_service",
    "michi_link_import_service",
    "michi_link_continue_service",
    "michi_link_remote_library_service",
    "michi_link_track_identity_service",
    "michi_link_diagnostics_service",
)

SCAN_DIRS = ("core", "integrations", "sync", "ui_qml_bridge")
_CLASS_RE = re.compile(r"^class\s+(\w+)\b", re.M)


def _class_definitions(class_name: str) -> list[str]:
    """All modules defining ``class class_name`` (relative paths)."""
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


def _is_legacy(module_path: str) -> bool:
    source = (PROJECT_ROOT / module_path).read_text(
        encoding="utf-8", errors="ignore")
    return LEGACY_MARKER in source


def test_exactly_one_productive_micro_server_service() -> None:
    defining = _class_definitions("MicroServerService")
    productive = [m for m in defining if not _is_legacy(m)]
    assert productive == [
        "integrations/michi_link/services/micro_server_service.py"
    ], (
        f"Expected exactly one productive MicroServerService, got {productive}"
    )


def test_exactly_one_productive_continue_on_server_service() -> None:
    defining = _class_definitions("ContinueOnServerService")
    productive = [m for m in defining if not _is_legacy(m)]
    assert productive == [
        "integrations/michi_link/services/continue_on_server_service.py"
    ], (
        f"Expected exactly one productive ContinueOnServerService, "
        f"got {productive}"
    )


def test_legacy_modules_are_marked() -> None:
    for module_path, class_name in DESIGNATED_LEGACY_MODULES.items():
        source = (PROJECT_ROOT / module_path).read_text(
            encoding="utf-8", errors="ignore")
        assert LEGACY_MARKER in source, (
            f"{module_path} defines {class_name} without a LEGACY marker"
        )


def test_productive_modules_not_marked_legacy() -> None:
    for module_path, class_name in PRODUCTIVE_MODULES.items():
        assert not _is_legacy(module_path), (
            f"Productive {class_name} module must not be LEGACY-marked: "
            f"{module_path}"
        )
        source = (PROJECT_ROOT / module_path).read_text(
            encoding="utf-8", errors="ignore")
        assert re.search(rf"^class\s+{class_name}\b", source, re.M), (
            f"{module_path} does not define {class_name}"
        )


def test_composition_registers_advanced_services() -> None:
    from tests.architecture._helpers import registered_keys

    keys = registered_keys()
    for key in COMPOSITION_KEYS:
        assert key in keys, (
            f"Composition must register '{key}'"
        )
    source = composition_source()
    assert "integrations.michi_link.services" in source, (
        "Composition must import the advanced services package"
    )


def test_composition_never_imports_legacy_variants() -> None:
    source = composition_source()
    for legacy_import in (
        "from core.micro_server_service import",
        "import core.micro_server_service",
        "from integrations.micro_server_service import",
        "import integrations.micro_server_service",
        "from integrations.michi_link.micro_server_client import",
        "from integrations.michi_link.import_client import",
        "from integrations.michi_link.continue_on_server_service import",
    ):
        assert legacy_import not in source, (
            f"Composition must not import legacy variant: {legacy_import}"
        )


def test_bridges_never_import_legacy_variants() -> None:
    bridge_dir = PROJECT_ROOT / "ui_qml_bridge"
    for path in bridge_dir.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        for forbidden in (
            "core.micro_server_service",
            "integrations.micro_server_service",
            "michi_link.micro_server_client",
            "michi_link.import_client",
            "michi_link.continue_on_server_service",
        ):
            assert forbidden not in source, (
                f"{path.relative_to(PROJECT_ROOT)} imports legacy "
                f"'{forbidden}'"
            )
