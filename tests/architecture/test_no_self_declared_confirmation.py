"""P0 Fase Metadata — no self-declared confirmation in the metadata domain.

The metadata editing domain must NEVER authorize an operation with a
self-declared ``confirmed=True`` + ``source="ui"/"doctor"/"durable_job"/
"ai_plan"`` intent. Authorization exists only as a ConfirmationToken issued
by ConfirmationService. This test scans the four domain files:

- ``core/metadata_editor_service.py``
- ``core/library_doctor_service.py``
- ``ui_qml_bridge/metadata_bridge.py``
- ``core/assistant_metadata_gateway.py``

Rules:
1. No ``ast.Dict`` literal combines keys ``confirmed`` and ``source``.
2. No ``source="ui"/"doctor"/"durable_job"/"ai_plan"`` kwargs remain in the
   editor, bridge or gateway (the doctor keeps exactly one audit tag on the
   mutation-service call — an event tag, NOT an authorization claim; the
   authorization gate lives in ``repair()`` with a token).
3. Every canonical apply path requires a token: ``apply_batch``,
   ``apply_single``, ``repair`` and ``apply_review`` accept/reference
   ``confirmation_token``.
"""
from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

SCANNED_FILES = (
    "core/metadata_editor_service.py",
    "core/library_doctor_service.py",
    "ui_qml_bridge/metadata_bridge.py",
    "core/assistant_metadata_gateway.py",
)

AUTHORIZATION_SOURCES = ("ui", "doctor", "durable_job", "ai_plan")

# Apply paths that MUST be token-gated (method name -> file -> token exposure).
TOKEN_GATED_METHODS = {
    "apply_batch": ("core/metadata_editor_service.py", "confirmation_token"),
    "apply_single": ("core/metadata_editor_service.py", "confirmation_token"),
    "repair": ("core/library_doctor_service.py", "confirmation_token"),
    "apply_review": ("core/assistant_metadata_gateway.py", "confirmation_token"),
}


def _parse(path: str) -> ast.Module:
    source = (PROJECT_ROOT / path).read_text(encoding="utf-8")
    return ast.parse(source)


def _self_declared_dicts(tree: ast.Module) -> list[ast.Dict]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = {
            key.value
            for key in (node.keys or [])
            if isinstance(key, ast.Constant)
        }
        if "confirmed" in keys and "source" in keys:
            found.append(node)
    return found


def _source_kwargs(tree: ast.Module) -> list[ast.Call]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords or []:
            if kw.arg != "source":
                continue
            if (isinstance(kw.value, ast.Constant)
                    and kw.value.value in AUTHORIZATION_SOURCES):
                found.append(node)
    return found


def _function_body(path: str, name: str) -> ast.FunctionDef | None:
    tree = _parse(path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_no_confirmed_source_self_declaration_in_domain() -> None:
    for path in SCANNED_FILES:
        tree = _parse(path)
        dicts = _self_declared_dicts(tree)
        assert not dicts, (
            f"{path} still self-declares confirmation via "
            f"confirmed=True + source= at line "
            f"{dicts[0].lineno}"
        )


def test_no_authorization_source_kwargs_in_editor_bridge_gateway() -> None:
    for path in ("core/metadata_editor_service.py",
                 "ui_qml_bridge/metadata_bridge.py",
                 "core/assistant_metadata_gateway.py"):
        tree = _parse(path)
        calls = _source_kwargs(tree)
        assert not calls, (
            f"{path} still uses source="
            f"{AUTHORIZATION_SOURCES} as authorization at line "
            f"{calls[0].lineno}"
        )


def test_doctor_source_audit_tag_is_not_authorization() -> None:
    """The only remaining source="doctor" in the doctor service is the
    mutation-service event tag (audit), not a confirmation claim; the repair
    authorization gate requires a token."""
    source = (PROJECT_ROOT / "core" / "library_doctor_service.py").read_text(
        encoding="utf-8")
    assert source.count('source="doctor"') == 1
    assert "remove_tracks_from_library" in source.split('source="doctor"')[0][-200:]


def test_apply_paths_require_token() -> None:
    for method, (path, token_ref) in TOKEN_GATED_METHODS.items():
        fn = _function_body(path, method)
        assert fn is not None, f"{path} must define {method}"
        fn_source = ast.unparse(fn)
        assert token_ref in fn_source, (
            f"{method} in {path} must be token-gated "
            f"(references {token_ref})"
        )


def test_apply_batch_tracks_per_track_token_reasons() -> None:
    """apply_batch must surface token rejection codes per track."""
    fn = _function_body("core/metadata_editor_service.py", "apply_batch")
    assert fn is not None
    source = ast.unparse(fn)
    assert "missing_confirmation" in source
    assert "reason" in source
