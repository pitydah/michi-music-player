"""A46 coverage manifest validation; not product test execution evidence."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/audio/phase2/F11_SIGNAL_TRUTH_A46_R15C_COVERAGE.json"


def test_fifty_research_oracles_registered_without_false_executions():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["schema"] == "michi.ap2.f11.r15c.coverage.v1"
    assert m["research_status"] == "50_DESIGNED_ZERO_EXECUTED_AT_SOURCE_CUT"
    assert m["external_test_certification"] is False
    assert m["hardware_qualification"] is False
    rows = m["cases"]
    assert len(rows) == 50
    assert [r["id"] for r in rows] == [f"R15C-{i:02d}" for i in range(1, 51)]
    assert all(
        r["integration_status"] == "NOT_RUN" and r["evidence"] is None for r in rows
    )
    assert all(r["stimulus"] and r["oracle"] and r["source_pattern"] for r in rows)


def test_candidate_links_do_not_assert_pass_or_hardware_boundary():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    links = [r for r in m["cases"] if r["candidate_tests"]]
    assert {r["id"] for r in links} == {"R15C-13", "R15C-42", "R15C-43", "R15C-44"}
    assert all(r["integration_status"] == "NOT_RUN" for r in links)
    assert not any(
        "PASS" in r["scope"] or "DAC_VERIFIED" in r["scope"] for r in m["cases"]
    )
