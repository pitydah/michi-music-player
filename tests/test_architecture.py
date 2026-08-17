"""Layer import-boundary regression guard (LOCAL-STABILIZATION-01.6.3).

Uses a lightweight AST walk of the src tree: no heavyweight architecture
tooling, deterministic, fast. Enforces the canonical dependency direction:

    presentation → application → domain
    infrastructure → application ports

    domain      must not import application/infrastructure/presentation/PySide6
    application must not import infrastructure/presentation/PySide6
    presentation must not import infrastructure
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "michi"

FORBIDDEN = {
    "application": {"michi.infrastructure", "michi.presentation", "PySide6"},
    "domain": {
        "michi.application",
        "michi.infrastructure",
        "michi.presentation",
        "PySide6",
    },
    "presentation": {"michi.infrastructure"},
}


def _module_prefixes(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefixes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                prefixes.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefixes.add(node.module)
    return prefixes


def _violates(prefixes, forbidden):
    return sorted(
        p for p in prefixes for f in forbidden if p == f or p.startswith(f + ".")
    )


def _modules(layer: str):
    return sorted((SRC / layer).glob("*.py"))


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_import_boundaries(layer):
    for module in _modules(layer):
        violations = _violates(_module_prefixes(module), FORBIDDEN[layer])
        assert not violations, (
            f"{module.name} imports forbidden layer roots: {violations}"
        )


def test_application_has_no_infrastructure_import():
    for module in _modules("application"):
        violations = _violates(_module_prefixes(module), {"michi.infrastructure"})
        assert not violations, module.name
