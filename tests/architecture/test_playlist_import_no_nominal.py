"""Debt D1 (architecture): playlist import must not be nominal.

PlaylistService batch/import operations must be policy-aware and honest:
- ``begin()``/``commit()``/``rollback()`` never return success without a
  real transaction (PlaylistTransaction must issue BEGIN on ``db.conn``).
- ``cancel_import`` is never a nominal ``{"ok": True, "cancelled": True}``:
  it routes to ``job_service.cancel_job`` or answers NO_ACTIVE_IMPORT.
- ``add_tracks`` carries the policy in its result and can mark
  PARTIAL_SUCCESS / FAILED; ``import_playlist_file`` accepts a ctx.
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SERVICE_PATH = PROJECT_ROOT / "core" / "playlist_service.py"
PORTS_PATH = PROJECT_ROOT / "core" / "jobs" / "ports.py"
HANDLERS_PATH = PROJECT_ROOT / "core" / "jobs" / "handlers.py"
COMPOSITION_PATH = PROJECT_ROOT / "core" / "composition" / "jobs.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_method(tree: ast.Module, class_name: str,
                 method_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return item
    raise AssertionError(f"{class_name}.{method_name} not found")


def _source_of(node: ast.AST) -> str:
    return ast.unparse(node)


def test_transaction_begin_issues_real_begin() -> None:
    tree = _tree(SERVICE_PATH)
    method = _find_method(tree, "PlaylistTransaction", "begin")
    source = _source_of(method)
    assert "execute" in source and "BEGIN" in source, (
        "PlaylistTransaction.begin must issue BEGIN on db.conn — nominal "
        "transactions are prohibited (debt D1)")
    assert "self._db.conn" in source


def test_transaction_commit_rollback_are_real() -> None:
    tree = _tree(SERVICE_PATH)
    commit = _source_of(_find_method(tree, "PlaylistTransaction", "commit"))
    rollback = _source_of(_find_method(tree, "PlaylistTransaction", "rollback"))
    assert "conn.commit" in commit
    assert "conn.rollback" in rollback


def test_add_tracks_carries_policy_and_honest_status() -> None:
    tree = _tree(SERVICE_PATH)
    method = _find_method(tree, "PlaylistService", "add_tracks")
    source = _source_of(method)
    assert "policy" in source
    assert "ATOMIC_ROLLBACK" in source
    # The result must be able to express partial/failed batches.
    adders = [
        _source_of(_find_method(tree, "PlaylistService", name))
        for name in ("_add_tracks_atomic", "_add_tracks_loop")
    ]
    combined = " ".join(adders)
    assert "PARTIAL_SUCCESS" in combined
    assert "FAILED" in combined
    assert "rollback_performed" in combined


def test_import_playlist_file_is_policy_and_ctx_aware() -> None:
    tree = _tree(SERVICE_PATH)
    method = _find_method(tree, "PlaylistService", "import_playlist_file")
    source = _source_of(method)
    assert "policy" in source
    assert "ctx" in source
    assert "parse_playlist_entries" in source


def test_cancel_import_is_not_nominal() -> None:
    tree = _tree(SERVICE_PATH)
    method = _find_method(tree, "PlaylistService", "cancel_import")
    source = _source_of(method)
    assert "NO_ACTIVE_IMPORT" in source, (
        "cancel_import must answer NO_ACTIVE_IMPORT when there is no active "
        "job — nominal success is prohibited (debt D1)")
    assert "cancel_job" in source, (
        "cancel_import must route to job_service.cancel_job")


def test_no_nominal_cancelled_true_literal() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    assert '"cancelled": True' not in source, (
        "nominal cancelled=True literal must not appear in playlist_service")


def test_playlist_import_port_exists() -> None:
    tree = _tree(PORTS_PATH)
    assert any(isinstance(n, ast.ClassDef) and n.name == "PlaylistImportPort"
               for n in ast.walk(tree)), "PlaylistImportPort protocol missing"
    port = next(n for n in ast.walk(tree)
                if isinstance(n, ast.ClassDef) and n.name == "PlaylistImportPort")
    names = {n.name for n in ast.walk(port) if isinstance(n, ast.FunctionDef)}
    assert "import_playlist" in names


def test_playlist_import_handler_factory_exists() -> None:
    tree = _tree(HANDLERS_PATH)
    assert any(isinstance(n, ast.FunctionDef) and
               n.name == "make_playlist_import_handler"
               for n in ast.walk(tree)), (
        "make_playlist_import_handler factory missing")


def test_playlist_import_registered_in_composition() -> None:
    composition = COMPOSITION_PATH.read_text(encoding="utf-8")
    assert "register_handler(\"playlist_import\"" in composition, (
        "playlist_import handler must be registered in composition")
    assert "make_playlist_import_handler" in composition
