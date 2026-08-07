"""Architecture (debt D3b): LinkDiagnosticsService never constructs services
at runtime.

- No ``ServiceClass(...)`` constructor call inside any method.
- The constructor receives its dependencies (client, track identity service,
  import service); missing dependencies degrade to explicit ``skipped``
  statuses instead of ad-hoc construction.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_PATH = (
    PROJECT_ROOT / "integrations" / "michi_link" / "services" / "diagnostics_service.py"
)

# Classes the service used to construct inside methods (F11 finding).
FORBIDDEN_RUNTIME_CONSTRUCTIONS = {
    "TrackIdentityService",
    "ImportToServerService",
    "MichiLinkClient",
}


def _module() -> ast.Module:
    return ast.parse(SERVICE_PATH.read_text(encoding="utf-8"), filename=str(SERVICE_PATH))


def _methods(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def test_no_service_construction_inside_methods() -> None:
    tree = _module()
    offenders = []
    for fn in _methods(tree):
        if fn.name == "__init__":
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_RUNTIME_CONSTRUCTIONS:
                    offenders.append(f"{fn.name}: {func.id}(")
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if func.value.id in FORBIDDEN_RUNTIME_CONSTRUCTIONS:
                        offenders.append(f"{fn.name}: {func.value.id}.{func.attr}(")
    assert offenders == [], f"Runtime construction in methods: {offenders}"


def test_constructor_receives_dependencies() -> None:
    tree = _module()
    init = next(
        (fn for fn in _methods(tree) if fn.name == "__init__"), None
    )
    assert init is not None, "LinkDiagnosticsService must define __init__"
    arg_names = {a.arg for a in init.args.args}
    for required in ("client", "track_identity_service", "import_service"):
        assert required in arg_names, (
            f"__init__ must accept {required}= (debt D3b)"
        )


def test_uninjected_services_degrade_to_skipped() -> None:
    from integrations.michi_link.services.diagnostics_service import (
        LinkDiagnosticsService,
    )

    svc = LinkDiagnosticsService(
        client=MagicMock(), track_identity_service=None, import_service=None,
    )
    identity = svc.check_track_identity("/tmp/song.flac")
    assert identity["status"] == "skipped"
    assert "not injected" in identity.get("reason", "")

    preflight = svc.check_import_preflight("127.0.0.1", 53318)
    assert preflight["status"] in ("skipped", "ok")
    assert "not injected" in preflight.get("note", "")

    mapping = svc.check_import_mapping("127.0.0.1", 53318)
    assert mapping["status"] == "skipped"
    assert "not injected" in mapping.get("reason", "")


def test_injected_services_are_used_not_rebuilt() -> None:
    from integrations.michi_link.services.diagnostics_service import (
        LinkDiagnosticsService,
    )

    client = MagicMock()
    identity_svc = MagicMock()
    identity_svc.compute.return_value = MagicMock(
        ok=True,
        data=MagicMock(quick_hash="aabbccdd", content_hash="xx", file_size=10),
        message="",
    )
    svc = LinkDiagnosticsService(
        client=client, track_identity_service=identity_svc, import_service=None,
    )
    result = svc.check_track_identity("/tmp/song.flac")
    assert result["status"] == "ok"
    identity_svc.compute.assert_called_once_with("/tmp/song.flac")
