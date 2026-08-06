"""Shared helpers for architecture tests: static registration extraction."""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

COMPOSITION_FILES = (
    PROJECT_ROOT / "core" / "composition" / "infrastructure.py",
    PROJECT_ROOT / "core" / "composition" / "playback.py",
    PROJECT_ROOT / "core" / "composition" / "library.py",
    PROJECT_ROOT / "core" / "composition" / "audio_lab.py",
    PROJECT_ROOT / "core" / "composition" / "ecosystem.py",
    PROJECT_ROOT / "core" / "composition" / "settings.py",
    PROJECT_ROOT / "core" / "composition" / "intelligence.py",
    PROJECT_ROOT / "core" / "application_bootstrap.py",
)

_REGISTER_RE = re.compile(
    r"register\(\s*(?P<quote>['\"])(?P<key>[a-z_0-9]+)(?P=quote)\s*,"
)

# Standalone runtime components declared in the manifest that are NOT
# registered in the container (they live in bridges/engines/backends).
STANDALONE_MANIFEST_KEYS = frozenset({
    "job_bridge", "job_manager", "audio_lab_job_adapter",
    "action_registry_binder", "selection_context_bridge", "bridge_factory",
    "page_state_store", "hybrid_audio_manager", "provider_manager",
    "knowledge_broker", "mpd_service_manager",
    "route_registry_bridge", "command_palette_bridge",
})


def registered_keys() -> set[str]:
    """Collect every container key registered by the composition builders.

    Static analysis of register("key", ...) calls — deterministic and
    headless-safe; the composition modules themselves do not expose a key list.
    """
    keys: set[str] = set()
    for path in COMPOSITION_FILES:
        source = path.read_text(encoding="utf-8")
        for match in _REGISTER_RE.finditer(source):
            keys.add(match.group("key"))
    return keys


def composition_source() -> str:
    """Concatenated source of every composition builder for regex scans."""
    chunks = []
    for path in COMPOSITION_FILES:
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)
