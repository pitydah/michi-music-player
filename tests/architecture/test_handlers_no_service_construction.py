"""Fase Jobs (architecture): core/jobs/handlers.py must be a PURE factory
over injected ports.

Handlers are prohibited from resolving services: no ``ServiceClass(...)``
constructor calls, no ``container.get(...)``, no ``fallback_service =
ServiceClass(...)``. Every factory closes over the port instances passed by
composition (core/composition/jobs.py).
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

HANDLERS_PATH = PROJECT_ROOT / "core" / "jobs" / "handlers.py"
COMPOSITION_JOBS_PATH = PROJECT_ROOT / "core" / "composition" / "jobs.py"


def _module(path: Path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_stdlib_names(tree: ast.Module) -> set[str]:
    allowed_prefixes = ("__future__", "logging", "typing", "collections")
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(allowed_prefixes):
                    names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").startswith(allowed_prefixes):
                names.add(node.module)
    return names


def test_handlers_import_only_stdlib() -> None:
    tree = _module(HANDLERS_PATH)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    assert imports, "handlers.py must import something"
    allowed = _imported_stdlib_names(tree)
    for node in imports:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in allowed, (
                    f"handlers.py must not import {alias.name}"
                )
        else:
            assert node.module in allowed, (
                f"handlers.py must not import {node.module}"
            )


def _names(tree: ast.Module) -> set[str]:
    """Every identifier referenced in code (docstrings excluded)."""
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def test_no_container_access_in_handlers() -> None:
    tree = _module(HANDLERS_PATH)
    assert "container" not in _names(tree), (
        "handlers.py must never reference a service container"
    )


def test_no_service_instantiation_in_handlers() -> None:
    """No CamelCase constructor call anywhere in handlers.py.

    Factories (make_*) are lowercase calls; any ``Name(...)`` starting with
    an uppercase letter is a service/adapter instantiation — prohibited.
    ``RuntimeError`` is the only allowed uppercase builtin (error signalling).
    """
    allowed_builtins = {"RuntimeError"}
    tree = _module(HANDLERS_PATH)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id[:1].isupper():
            if node.func.id not in allowed_builtins:
                offenders.append(node.func.id)
    assert offenders == [], (
        f"handlers.py must not instantiate services/adapters: {offenders}"
    )


def test_no_fallback_instantiation_in_handlers() -> None:
    tree = _module(HANDLERS_PATH)
    assert "fallback" not in _names(tree), (
        "handlers.py must never build fallback services"
    )
    assert "container" not in _names(tree)


def test_composition_registers_handlers_with_pure_factories() -> None:
    """The composition closes over ports: register_handler(...) receives a
    make_* factory call, never a service resolved at execution time."""
    tree = _module(COMPOSITION_JOBS_PATH)
    registered = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "register_handler":
            registered.append(ast.unparse(node))
    assert registered, "composition must register production handlers"
    for call in registered:
        assert "make_" in call, (
            f"register_handler must receive a pure factory: {call}"
        )
        assert "container.get" not in call
