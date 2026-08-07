"""Mix generation must never present an empty result as a generated mix
(ADR-005).  ``MixService.generate`` returns an explicit MixGenerationStatus;
no fallback mix with title/description is constructed when the outcome is
empty.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _source(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8")


def _function_source(text: str, name: str) -> ast.FunctionDef | None:
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_generate_returns_explicit_status_values() -> None:
    from core.mix.models import MixGenerationStatus

    source = _source("core/mix_service.py")
    fn = _function_source(source, "generate")
    assert fn is not None, "MixService.generate() must exist"
    text = ast.get_source_segment(source, fn) or ""

    for status in MixGenerationStatus:
        assert status.value in text or status.name in text, (
            f"generate() does not reference {status.value}"
        )
    assert "INVALID_STRATEGY" in text, "unknown strategies must be explicit"
    assert "GENERATOR_UNAVAILABLE" in text, "missing generator must be explicit"


def test_no_fallback_mix_constructed_on_empty_result() -> None:
    """No fake mix (title/description with zero tracks) may be built."""
    mix_source = _source("core/mix_service.py")
    smart_source = _source("recommendation/smart_mix_service.py")

    assert "fallback_" not in mix_source, "fallback mix factory removed"
    assert "Sin resultados" not in smart_source, (
        "fake 'Sin resultados' mix removed from SmartMixService"
    )
    for source in (mix_source, smart_source):
        assert not re.search(r'title="Mix \w+".*count', source), (
            "fake titled mix with empty count found"
        )


def test_no_type_dynamic_classes_in_smart_mix_service() -> None:
    """Strategy dispatch must use real classes, never type(...) construction."""
    tree = ast.parse(_source("recommendation/smart_mix_service.py"))
    offenders = [
        ast.get_source_segment(_source("recommendation/smart_mix_service.py"), node) or "<call>"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "type"
    ]
    assert offenders == [], f"dynamic type() classes found: {offenders}"
    assert "_strategies" in _source("recommendation/smart_mix_service.py"), (
        "static strategy registry missing"
    )
