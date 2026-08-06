"""Bridges must not execute SQL directly (ADR-003).

Only the capability_bridge FTS probe is whitelisted. library_bridge must be
free of mutation SQL (INSERT/DELETE/UPDATE); read-only SELECTs are tolerated
until the query service exposes the same data.
"""
from __future__ import annotations

import re
from pathlib import Path

BRIDGES_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge"

# capability_bridge probes FTS5 availability with a SELECT on the real
# connection — the only sanctioned database touch in the bridge layer.
WHITELISTED_FILES = {"capability_bridge.py"}

FORBIDDEN_PATTERNS = [
    (r"sqlite3\.(connect|Connection)", "sqlite3 connection"),
    (r"\bINSERT\s+INTO\b", "INSERT INTO"),
    (r"\bDELETE\s+FROM\b", "DELETE FROM"),
    (r"\bUPDATE\s+[\w]+\s+SET\b", "UPDATE ... SET"),
]


def _bridge_files():
    return sorted(
        path for path in BRIDGES_DIR.glob("*.py")
        if path.name not in WHITELISTED_FILES
    )


def test_no_bridge_opens_sqlite_connections() -> None:
    offenders = []
    for path in _bridge_files():
        source = path.read_text(encoding="utf-8")
        if re.search(r"sqlite3\.(connect|Connection)", source):
            offenders.append(path.name)
    assert offenders == [], (
        f"Bridges opening sqlite connections: {offenders}"
    )


def test_no_bridge_runs_mutation_sql() -> None:
    offenders = []
    for path in _bridge_files():
        source = path.read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_PATTERNS:
            if re.search(pattern, source, re.IGNORECASE):
                offenders.append(f"{path.name}:{label}")
    assert offenders == [], (
        f"Bridges with direct SQL: {offenders}"
    )


def test_library_bridge_has_no_mutation_sql() -> None:
    """library_bridge must not contain INSERT/DELETE/UPDATE (Slice 3)."""
    source = (BRIDGES_DIR / "library_bridge.py").read_text(encoding="utf-8")
    for pattern, label in [
        (r"\bINSERT\s+INTO\b", "INSERT INTO"),
        (r"\bDELETE\s+FROM\b", "DELETE FROM"),
        (r"\bUPDATE\s+[\w]+\s+SET\b", "UPDATE ... SET"),
    ]:
        assert not re.search(pattern, source, re.IGNORECASE), (
            f"library_bridge contains forbidden mutation SQL: {label}"
        )
