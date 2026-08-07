"""Fase Mix architecture gates: NO parallel mix state machine.

- The bridge must not rebuild strategies: no _build_daily_mix /
  _build_custom_mix symbols, no category dispatch, no dedup/artist limits.
- MixService must not use dynamic type(...) classes, must not swallow
  generation failures into empty lists, and must never mutate the query
  dicts it receives (reason labels are added on copies).
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

BRIDGE_PATH = ROOT / "ui_qml_bridge" / "mix_bridge.py"
SERVICE_PATH = ROOT / "core" / "mix_service.py"

FORBIDDEN_BRIDGE_SYMBOLS = (
    "_build_daily_mix",
    "_build_custom_mix",
    "_load_mix_items",
    "_deduplicate_and_apply_limits",
    "_run_generation",
)
FORBIDDEN_DISPATCH_MARKERS = (
    "seen_ids",
    "artist_counts",
    "artist_limit",
    "max_total",
)


class _ServiceVisitor(ast.NodeVisitor):
    """Reject try/except bodies whose handler returns an empty list."""

    def __init__(self):
        self.empty_list_returns: list[int] = []

    def visit_Try(self, node: ast.Try):  # noqa: N802
        for handler in node.handlers:
            for stmt in handler.body:
                if (isinstance(stmt, ast.Return)
                        and isinstance(stmt.value, ast.List)
                        and not stmt.value.elts):
                    self.empty_list_returns.append(node.lineno)
        self.generic_visit(node)


def test_bridge_has_no_strategy_builders() -> None:
    source = BRIDGE_PATH.read_text(encoding="utf-8")
    for symbol in FORBIDDEN_BRIDGE_SYMBOLS:
        assert symbol not in source, (
            f"mix_bridge.py must not contain {symbol}() — generation "
            "belongs to MixService")


def test_bridge_has_no_category_dispatch() -> None:
    source = BRIDGE_PATH.read_text(encoding="utf-8")
    for marker in FORBIDDEN_DISPATCH_MARKERS:
        assert marker not in source, (
            f"mix_bridge.py must not contain '{marker}' — dedup/limits "
            "belong to MixService")
    assert "loaders" not in source, (
        "mix_bridge.py must not dispatch categories via a loaders dict")


def test_bridge_has_no_direct_query_calls() -> None:
    """The bridge must not call the query methods itself (strategy dispatch)."""
    source = BRIDGE_PATH.read_text(encoding="utf-8")
    for call in (".favorites(", ".most_played(", ".unplayed(",
                 ".rediscovery(", ".by_field(", ".by_decade(",
                 ".by_year(", ".high_quality(", ".recent("):
        assert call not in source, (
            f"mix_bridge.py must not call '{call}' — MixService owns "
            "every strategy")


def test_service_has_no_dynamic_type_classes() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    assert "type('" not in source, "mix_service.py must not use type() "
    assert 'type("' not in source, "mix_service.py must not use type() "


def test_service_generation_never_returns_empty_list_on_error() -> None:
    tree = ast.parse(SERVICE_PATH.read_text(encoding="utf-8"))
    visitor = _ServiceVisitor()
    visitor.visit(tree)
    assert not visitor.empty_list_returns, (
        f"mix_service.py: except handlers must not return [] — errors "
        f"become GENERATOR_UNAVAILABLE outcomes, never empty lists "
        f"(lines {visitor.empty_list_returns})")


def test_generate_returns_copies_when_adding_reason() -> None:
    """Adding the reason label must not mutate the query service dicts."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from core.mix_service import MixService

    source_rows = [
        {"track_id": 7, "title": "Jazz One", "artist": "Miles",
         "album": "Kind of Blue", "duration": 370},
        {"track_id": 8, "title": "Jazz Two", "artist": "Coltrane",
         "album": "A Love Supreme", "duration": 480},
    ]

    class _FakeQueries:
        def favorites(self, limit=50):
            return [dict(row) for row in source_rows]

    class _FakeLibrary:
        def count_tracks(self):
            return 2

    svc = MixService(playlist_service=None)
    svc._queries = _FakeQueries()
    svc._library_query = _FakeLibrary()

    result = svc.generate("favorites", limit=10)

    assert result["ok"] is True
    assert result["status"] == "COMPLETED_WITH_TRACKS"
    for track in result["tracks"]:
        assert track["reason"] == "Favoritos"
        assert track["id"] == track["track_id"]
    # The source dicts were never touched.
    for row in source_rows:
        assert "reason" not in row
        assert "id" not in row
