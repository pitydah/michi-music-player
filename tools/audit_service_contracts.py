#!/usr/bin/env python3
"""Audit service declarations, composition registration and protocols.

This script is intentionally AST-only: it does not import PySide6, initialize
GStreamer or open the library database. It can therefore run in CI and on a
minimal development machine.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ContractSpec:
    protocol_path: str
    protocol_class: str
    implementation_path: str
    implementation_class: str


DEFAULT_CONTRACTS = {
    "mix_query_service": ContractSpec(
        protocol_path="core/protocols/mix_service_protocol.py",
        protocol_class="MixServiceProtocol",
        implementation_path="core/mix_query_service.py",
        implementation_class="MixQueryService",
    ),
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def _literal_strings(node: ast.AST) -> set[str]:
    values: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.add(child.value)
    return values


def declared_services(container_path: Path) -> set[str]:
    tree = _parse(container_path)
    declared: set[str] = set()
    target_methods = {
        "_required_names",
        "_optional_names",
        "_capability_gated_names",
        "_deferred_physical_names",
        "_deferred_names",
    }
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in target_methods
        ):
            declared.update(_literal_strings(node))
    return declared


def registered_services(composition_dir: Path) -> set[str]:
    registered: set[str] = set()
    for path in sorted(composition_dir.glob("*.py")):
        tree = _parse(path)
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr != "register"
                or not node.args
            ):
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                registered.add(first.value)
    return registered


def bridge_dependencies(factory_path: Path) -> set[str]:
    tree = _parse(factory_path)
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if (
            not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Attribute)
            or node.func.attr not in {"_get", "get", "require"}
            or not node.args
        ):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            dependencies.add(first.value)
    return dependencies


def class_methods(path: Path, class_name: str) -> set[str]:
    tree = _parse(path)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not child.name.startswith("_")
            }
    raise ValueError(f"Class {class_name!r} not found in {path}")


def contract_report(
    root: Path,
    specs: dict[str, ContractSpec],
) -> dict[str, dict]:
    report: dict[str, dict] = {}
    for service, spec in specs.items():
        protocol_methods = class_methods(
            root / spec.protocol_path,
            spec.protocol_class,
        )
        implementation_methods = class_methods(
            root / spec.implementation_path,
            spec.implementation_class,
        )
        missing = sorted(protocol_methods - implementation_methods)
        report[service] = {
            **asdict(spec),
            "protocol_methods": sorted(protocol_methods),
            "implementation_methods": sorted(implementation_methods),
            "missing_methods": missing,
            "ok": not missing,
        }
    return report


def build_report(root: Path = ROOT) -> dict:
    declared = declared_services(root / "core/service_container.py")
    registered = registered_services(root / "core/composition")
    bridge_used = bridge_dependencies(
        root / "ui_qml_bridge/bridge_factory.py"
    )
    contracts = contract_report(root, DEFAULT_CONTRACTS)
    fatal_contracts = [
        name for name, item in contracts.items() if not item["ok"]
    ]
    return {
        "declared_services": sorted(declared),
        "registered_services": sorted(registered),
        "bridge_dependencies": sorted(bridge_used),
        "declared_not_registered": sorted(declared - registered),
        "registered_not_declared": sorted(registered - declared),
        "bridge_dependencies_not_declared": sorted(bridge_used - declared),
        "contracts": contracts,
        "fatal_contracts": fatal_contracts,
        "ok": not fatal_contracts,
    }


def _print_human(report: dict) -> None:
    print("Michi service-contract audit")
    print(f"  declared:    {len(report['declared_services'])}")
    print(f"  registered:  {len(report['registered_services'])}")
    print(f"  bridge deps: {len(report['bridge_dependencies'])}")
    print()
    for key in (
        "declared_not_registered",
        "registered_not_declared",
        "bridge_dependencies_not_declared",
    ):
        values = report[key]
        print(f"{key}: {len(values)}")
        for value in values:
            print(f"  - {value}")
    print("contracts:")
    for service, item in report["contracts"].items():
        status = "OK" if item["ok"] else "FAIL"
        print(f"  - {service}: {status}")
        for method in item["missing_methods"]:
            print(f"      missing: {method}")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report()
    if args.json:
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _print_human(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
