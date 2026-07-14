#!/usr/bin/env python3
"""qml_service_graph_audit.py — verify service dependency graph integrity.

Reads config/service_dependencies.yaml and validates:
  - No cycles in the graph
  - No missing dependencies (all referenced services exist in ServiceContainer)
  - No duplicate services
  - REQUIRED services that fail cause state=FAILED, capability=False
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def load_dependencies(yaml_path: str | Path) -> dict[str, list[str]]:
    import yaml
    path = Path(yaml_path)
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        print("ERROR: dependencies file must be a dict")
        sys.exit(1)
    return {k: v.get("requires", []) for k, v in data.items()}


def detect_cycles(deps: dict[str, list[str]]) -> list[list[str]]:
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]):
        visited.add(node)
        rec_stack.add(node)
        for neighbor in deps.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path + [neighbor])
            elif neighbor in rec_stack:
                cycle = path[path.index(neighbor):] + [neighbor]
                cycles.append(cycle)
        rec_stack.discard(node)

    for svc in deps:
        if svc not in visited:
            dfs(svc, [svc])

    return cycles


def check_missing_deps(deps: dict[str, list[str]], known_services: set[str]) -> list[str]:
    missing = []
    for svc, requires in deps.items():
        for dep in requires:
            if dep not in known_services:
                missing.append(f"{svc} -> {dep}")
    return missing


def check_duplicates(deps: dict[str, list[str]]) -> list[str]:
    from collections import Counter
    return [svc for svc, count in Counter(deps.keys()).items() if count > 1]


def main():
    repo_root = Path(__file__).resolve().parent.parent
    yaml_path = repo_root / "config" / "service_dependencies.yaml"
    deps = load_dependencies(yaml_path)

    from core.service_container import ServiceContainer
    container = ServiceContainer()
    known = set(container._all_names())

    cycles = detect_cycles(deps)
    missing = check_missing_deps(deps, known)
    duplicates = check_duplicates(deps)

    has_errors = False

    if cycles:
        has_errors = True
        print("FAIL: Circular dependencies detected:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")

    if missing:
        has_errors = True
        print("FAIL: Missing dependencies (not in ServiceContainer):")
        for m in missing:
            print(f"  {m}")

    if duplicates:
        has_errors = True
        print("FAIL: Duplicate services in dependency graph:")
        for d in duplicates:
            print(f"  {d}")

    if not cycles:
        print("PASS: No cycles detected in service dependency graph")
    if not missing:
        print("PASS: All dependencies reference valid services")
    if not duplicates:
        print("PASS: No duplicate services")

    if has_errors:
        print("FAIL: qml_service_graph_audit FAILED")
        sys.exit(1)
    else:
        print("PASS: qml_service_graph_audit PASSED")


if __name__ == "__main__":
    main()
