from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _methods(path: str, class_name: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    target = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return {
        node.name
        for node in target.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def test_mix_query_service_implements_protocol():
    protocol = _methods(
        "core/protocols/mix_service_protocol.py",
        "MixServiceProtocol",
    )
    implementation = _methods(
        "core/mix_query_service.py",
        "MixQueryService",
    )
    assert protocol <= implementation


def test_mix_facade_exposes_bridge_category_contract():
    methods = _methods("core/mix_service.py", "MixService")
    expected = {
        "favorites",
        "recent",
        "most_played",
        "unplayed",
        "rediscovery",
        "genre",
        "by_field",
        "by_album",
        "by_decade",
        "by_year",
        "high_quality",
        "custom",
    }
    assert expected <= methods


def test_intelligence_composition_registers_distinct_services():
    source = (
        ROOT / "core/composition/intelligence.py"
    ).read_text(encoding="utf-8")
    assert (
        'container.register("mix_query_service", mix_query_service)'
        in source
    )
    assert (
        'container.register("recommendation_service", recommendation_service)'
        in source
    )
    assert 'container.register("mix_service", mix_service)' in source
