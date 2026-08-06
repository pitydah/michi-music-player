"""Context capabilities must derive from runtime — never a static all-True dict.

Source scan: snapshot/capability builders in ``ContextService`` and
``MichiAISnapshotService`` must not contain a hardcoded True capability
dictionary; capability evidence must reference container health or the
capability resolver (S4 truthfulness, ADR-005).
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CONTEXT_SERVICE = PROJECT_ROOT / "core" / "context" / "context_service.py"
AI_SNAPSHOT = PROJECT_ROOT / "michi_ai" / "context" / "ai_snapshot_service.py"
CAPABILITIES_PROVIDER = (
    PROJECT_ROOT / "core" / "context" / "providers" / "snapshot" / "capabilities.py"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _literal_true_dicts(path: Path) -> list[tuple[int, str]]:
    """Return (line, key) for dict literals assigning `True` to a capability key."""
    tree = ast.parse(_source(path))
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=False):
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if not key.value.startswith("can_") and not key.value.startswith(
                        "can_"):
                    continue
                if isinstance(value, ast.Constant) and value.value is True:
                    hits.append((node.lineno, key.value))
    return hits


def test_context_service_has_no_hardcoded_true_capability() -> None:
    hits = _literal_true_dicts(CONTEXT_SERVICE)
    assert hits == [], f"Hardcoded True capabilities in ContextService: {hits}"


def test_michi_ai_snapshot_has_no_hardcoded_true_capability() -> None:
    hits = _literal_true_dicts(AI_SNAPSHOT)
    assert hits == [], f"Hardcoded True capabilities in MichiAISnapshotService: {hits}"


def test_context_service_capabilities_consult_runtime() -> None:
    src = _source(CONTEXT_SERVICE)
    assert "is_capable" in src or "contains" in src, (
        "ContextService capability builder must consult container health"
    )
    assert "_runtime_capability" in src


def test_michi_ai_snapshot_capabilities_consult_runtime() -> None:
    src = _source(AI_SNAPSHOT)
    assert "resolve" in src and "capability_resolver" in src, (
        "MichiAISnapshotService capabilities must consult the capability resolver"
    )
    assert "container" in src


def test_capabilities_provider_has_no_static_true_dict() -> None:
    hits = _literal_true_dicts(CAPABILITIES_PROVIDER)
    assert hits == [], f"Hardcoded True capabilities in provider: {hits}"


def test_capabilities_provider_uses_container_and_resolver() -> None:
    src = _source(CAPABILITIES_PROVIDER)
    assert "container" in src and "capability_resolver" in src
    assert "service_missing" in src, (
        "Capabilities must report a reason when the backing service is missing"
    )
