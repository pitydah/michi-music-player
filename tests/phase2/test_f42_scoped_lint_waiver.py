"""M11.3F/F42: scoped lint exception, never a frozen audio-source edit.

A single existing style diagnostic is grandfathered only while the original
adapter bytes remain sealed and Ruff still reports precisely that diagnostic.
This test does not authorize any changes to the adapter or its seal.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = "src/michi/infrastructure/audio_engines/gstreamer.py"
F42_TEST = ROOT / "tests/test_m11_3f_engine_selection.py"


def _canonical_seal() -> str:
    tree = ast.parse(F42_TEST.read_text(encoding="utf-8"))
    for item in tree.body:
        if isinstance(item, ast.ClassDef) and item.name == "TestF42AdapterContract":
            for member in item.body:
                if not isinstance(member, ast.Assign):
                    continue
                if not any(
                    isinstance(target, ast.Name) and target.id == "_BASELINE_HASHES"
                    for target in member.targets
                ):
                    continue
                declared = ast.literal_eval(member.value)
                return declared[FROZEN]
    raise AssertionError("F42 canonical checksum is missing")


def _sealed(payload: bytes, expected: str) -> bool:
    return hashlib.sha256(payload).hexdigest()[:16] == expected


def test_f42_adapter_remains_byte_identical_to_canonical_seal() -> None:
    expected = _canonical_seal()
    baseline = (ROOT / FROZEN).read_bytes()
    assert expected == "7ec89e800b4ad975"
    assert _sealed(baseline, expected)
    assert not _sealed(baseline + b"# changed", expected)


def test_f42_ruff_exception_is_specific_to_one_sealed_source_and_rule() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ignores = config["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert ignores.get(FROZEN) == ["SIM102"]
    assert "SIM102" not in config["tool"]["ruff"]["lint"].get("ignore", [])


def test_f42_legacy_diagnostic_is_exactly_one_sim102_at_frozen_site() -> None:
    process = subprocess.run(
        [
            "ruff",
            "check",
            "--isolated",
            "--select",
            "SIM102",
            "--output-format",
            "json",
            FROZEN,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert process.returncode == 1, process.stderr
    payload = json.loads(process.stdout)
    actual = [(item["code"], item["location"]["row"]) for item in payload]
    assert actual == [("SIM102", 4149)], actual
