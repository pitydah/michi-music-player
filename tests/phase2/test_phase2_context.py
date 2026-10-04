"""phase2_context (R11-G12-CONTEXT-TOOL) — extractor gates CTX-01..CTX-09."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "phase2_context", ROOT / "scripts/phase2_context.py"
)
context = importlib.util.module_from_spec(SPEC)
sys.modules["phase2_context"] = context
SPEC.loader.exec_module(context)

BOOTSTRAP = (
    "<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->\n"
    "bootstrap body\n"
    "<!-- MICHI_PHASE2:BOOTSTRAP:END -->\n"
)
INDEX_BLOCK = (
    "<!-- MICHI_PHASE2:PHASE_INDEX:BEGIN -->\n"
    "phases\n"
    "<!-- MICHI_PHASE2:PHASE_INDEX:END -->\n"
)
CONTRACT = (
    "<!-- MICHI_PHASE2:CONTRACT:R11-F00:BEGIN -->\n"
    "f00 contract body\n"
    "<!-- MICHI_PHASE2:CONTRACT:R11-F00:END -->\n"
)
PHASE = (
    "<!-- MICHI_PHASE2:PHASE:AP2-F00:BEGIN -->\n"
    "PHASE_ID: AP2-F00\n"
    "DEPENDENCIES: NONE\n"
    "MUST_READ_ANCHORS: R11-F00\n"
    "<!-- MICHI_PHASE2:PHASE:AP2-F00:END -->\n"
)
# the canonical spec reproduces its own anchor literals inside code examples
SELF_REFERENCE = '```python\n    "<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->",\n```\n'


def _repo(tmp_path: Path, *, contract: str = CONTRACT, extra: str = "") -> Path:
    repo = tmp_path / "repo"
    spec = repo / context.CANONICAL_PATH
    spec.parent.mkdir(parents=True)
    spec.write_text(
        "# 0. Intro\n"
        + BOOTSTRAP
        + INDEX_BLOCK
        + contract
        + PHASE
        + SELF_REFERENCE
        + extra,
        encoding="utf-8",
    )
    return repo


def test_cts_orientation_blocks_productive_mutation(tmp_path: Path) -> None:
    index = context.build_index(_repo(tmp_path))
    text = context.emit_context(index, "AP2-F00", "orientation")
    assert "PRODUCTIVE_MUTATION_ALLOWED: FALSE" in text


def test_cts_implementation_contains_every_anchor_once(tmp_path: Path) -> None:
    index = context.build_index(_repo(tmp_path))
    text = context.emit_context(index, "AP2-F00", "implementation")
    assert text.count("## CONTRACT R11-F00") == 1
    assert "PRODUCTIVE_MUTATION_ALLOWED: TRUE" in text


def test_cts_output_is_deterministic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    first = context.emit_context(context.build_index(repo), "AP2-F00", "implementation")
    second = context.emit_context(
        context.build_index(repo), "AP2-F00", "implementation"
    )
    assert first == second


def test_cts_duplicate_contract_anchor_stops(tmp_path: Path) -> None:
    repo = _repo(tmp_path, contract=CONTRACT + CONTRACT)
    with pytest.raises(SystemExit, match="STOP_CONTRACT_DUPLICATE"):
        context.build_index(repo)


def test_cts_duplicate_top_level_section_stops(tmp_path: Path) -> None:
    repo = _repo(tmp_path, extra="# 0. Duplicated\n")
    with pytest.raises(SystemExit, match="STOP_SPEC_DUPLICATE_SECTION"):
        context.build_index(repo)


def test_cts_missing_must_read_anchor_stops(tmp_path: Path) -> None:
    phase = PHASE.replace("R11-F00", "R11-MISSING")
    repo = _repo(tmp_path)
    spec = repo / context.CANONICAL_PATH
    spec.write_text(spec.read_text(encoding="utf-8").replace(PHASE, phase), "utf-8")
    with pytest.raises(SystemExit, match="STOP_CONTRACT_MISSING"):
        context.receipt(context.build_index(repo), "AP2-F00")


def test_cts_receipt_hash_changes_with_contract_material(tmp_path: Path) -> None:
    first = context.receipt(context.build_index(_repo(tmp_path / "a")), "AP2-F00")[
        "contract_set_sha256"
    ]
    changed = CONTRACT.replace("f00 contract body", "f00 contract body v2")
    second = context.receipt(
        context.build_index(_repo(tmp_path / "b", contract=changed)), "AP2-F00"
    )["contract_set_sha256"]
    assert first != second


def test_cts_unknown_phase_stops(tmp_path: Path) -> None:
    index = context.build_index(_repo(tmp_path))
    with pytest.raises(SystemExit, match="STOP_PHASE_UNKNOWN"):
        context.emit_context(index, "AP2-F99", "implementation")
