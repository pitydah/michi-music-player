"""AP2-F01 — execution-family vocabulary: canonical, orthogonal to engines.

Contract anchors: R11-F01 (create-only slice), R11-G03 (output families),
R11-G02 (authority map: execution family is orthogonal to engine selection).
These tests are the RED contract for ``michi.domain.audio_execution``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_execution import AudioExecutionFamily

MODULE_PATH = Path(sys.modules["michi.domain.audio_execution"].__file__)

EXPECTED_MEMBERS: tuple[tuple[str, str], ...] = (
    ("SHARED_PCM", "shared_pcm"),
    ("DIRECT_PCM", "direct_pcm"),
    ("MANAGED_PCM", "managed_pcm"),
    ("NATIVE_DSD", "native_dsd"),
    ("DOP", "dop"),
)


def _imported_modules(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append("." * node.level + (node.module or ""))
    return modules


def test_execution_family_contains_exactly_the_canonical_five() -> None:
    assert [(member.name, member.value) for member in AudioExecutionFamily] == list(
        EXPECTED_MEMBERS
    )


@pytest.mark.parametrize("name,value", EXPECTED_MEMBERS)
def test_execution_family_member_values(name: str, value: str) -> None:
    assert getattr(AudioExecutionFamily, name).value == value


def test_direct_pcm_is_distinct_from_managed_pcm() -> None:
    assert AudioExecutionFamily.DIRECT_PCM is not AudioExecutionFamily.MANAGED_PCM
    assert (
        AudioExecutionFamily.DIRECT_PCM.value != AudioExecutionFamily.MANAGED_PCM.value
    )


def test_native_dsd_is_distinct_from_dop() -> None:
    assert AudioExecutionFamily.NATIVE_DSD is not AudioExecutionFamily.DOP
    assert AudioExecutionFamily.NATIVE_DSD.value != AudioExecutionFamily.DOP.value


def test_no_accidental_alias_values() -> None:
    values = [member.value for member in AudioExecutionFamily]
    assert len(values) == len(set(values)) == 5


def test_execution_family_is_string_interoperable() -> None:
    assert AudioExecutionFamily.DIRECT_PCM == "direct_pcm"
    assert str(AudioExecutionFamily.DOP) == "dop"


def test_execution_family_vocabulary_does_not_collide_with_engine_identity() -> None:
    engine_values = {member.value for member in AudioEngineId}
    family_values = {member.value for member in AudioExecutionFamily}
    assert engine_values & family_values == set()
    # Audio Processing must never become a fourth AudioEngine id.
    assert "processing" not in engine_values


def test_execution_module_imports_stay_pure_domain() -> None:
    imports = _imported_modules(MODULE_PATH)
    assert imports, "audio_execution must declare its imports"
    forbidden_prefixes = (
        "PySide6",
        "gi",
        "Gst",
        "sqlite3",
        "ctypes",
        "michi.presentation",
        "michi.infrastructure",
        "michi.bootstrap",
        "michi.application",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in forbidden_prefixes
        ), f"forbidden import: {name}"
        top = name.split(".")[0]
        assert top in sys.stdlib_module_names or top == "michi", f"non-stdlib: {name}"
        if top == "michi":
            assert name == "michi.domain" or name.startswith("michi.domain."), name
