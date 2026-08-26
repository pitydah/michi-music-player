"""Layer import-boundary regression guard (LOCAL-STABILIZATION-01.6.3).

Uses a lightweight AST walk of the src tree: no heavyweight architecture
tooling, deterministic, fast. Enforces the canonical dependency direction:

    presentation → application → domain
    infrastructure → application ports

    domain      must not import application/infrastructure/presentation/PySide6
    application must not import infrastructure/presentation/PySide6
    presentation must not import infrastructure
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "michi"

FORBIDDEN = {
    "application": {"michi.infrastructure", "michi.presentation", "PySide6"},
    "domain": {
        "michi.application",
        "michi.infrastructure",
        "michi.presentation",
        "PySide6",
    },
    "presentation": {"michi.infrastructure"},
}


def _module_prefixes(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    prefixes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                prefixes.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefixes.add(node.module)
    return prefixes


def _violates(prefixes, forbidden):
    return sorted(
        p for p in prefixes for f in forbidden if p == f or p.startswith(f + ".")
    )


def _modules(layer: str):
    return sorted((SRC / layer).glob("*.py"))


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_import_boundaries(layer):
    for module in _modules(layer):
        violations = _violates(_module_prefixes(module), FORBIDDEN[layer])
        assert not violations, (
            f"{module.name} imports forbidden layer roots: {violations}"
        )


def test_application_has_no_infrastructure_import():
    for module in _modules("application"):
        violations = _violates(_module_prefixes(module), {"michi.infrastructure"})
        assert not violations, module.name


def test_m4r1_queue_service_constructor_seal():
    """AR02/AR03: QueueService has NO legacy positional compatibility seam.

    QueueService(playback) MUST fail at the Python signature level."""
    import inspect

    from michi.application.queue_service import QueueService

    sig = inspect.signature(QueueService.__init__)
    params = list(sig.parameters)
    assert "legacy_playback_args" not in params
    assert "*" in str(sig)  # keyword-only max_tracks
    assert "playback" not in "".join(params).lower()
    # positional call must fail
    import pytest

    with pytest.raises(TypeError):
        QueueService(object())  # type: ignore[arg-type]


def test_m4r1_queue_service_source_has_no_playback():
    """AR01: QueueService source has no PlaybackService / playback commands."""
    import inspect

    from michi.application import queue_service as qs

    src = inspect.getsource(qs)
    for forbidden in (
        "import PlaybackService",
        "from michi.application.playback_service",
        "load_and_play",
        "subscribe_end_of_media",
        "play_index",
        "set_repeat_mode",
        "set_shuffle_enabled",
    ):
        assert forbidden not in src, f"forbidden in QueueService: {forbidden}"


def test_m4r1_queue_state_no_playback_fields():
    """AR06: QueueState has no current_index/repeat/shuffle."""
    from michi.domain.queue import QueueState

    assert not hasattr(QueueState(), "current_index")
    assert not hasattr(QueueState(), "repeat_mode")
    assert not hasattr(QueueState(), "shuffle_enabled")


def test_m4r1_library_bridge_activate_no_service_fallback():
    """AR05: LibraryBridge.activate does not invoke LibraryService.activate."""
    import inspect

    from michi.presentation.library_bridge import LibraryBridge

    src = inspect.getsource(LibraryBridge.activate)
    assert "play_visible_track" in src
    assert "self._service.activate" not in src


class TestKCRGates:
    """KCR-015: architecture invariants sealed by AST/source gates."""

    def test_no_queue_playback_fossils(self):
        import ast

        tree = ast.parse(Path("src/michi/application/queue_service.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                assert node.attr != "_navigator", (
                    "queue_service must not own _navigator"
                )
                if node.attr == "shuffle_enabled":
                    assert "state" not in ast.unparse(node).replace(" ", "").split(".")[
                        0
                    ] or "self._state.shuffle_enabled" not in ast.unparse(node)

    def test_no_legacy_constructor_seams(self):
        import inspect

        import pytest  # noqa: F401

        from michi.application.library_service import LibraryService
        from michi.application.playlist_service import PlaylistService
        from michi.application.queue_service import QueueService

        for cls in (QueueService, PlaylistService, LibraryService):
            sig = inspect.signature(cls.__init__)
            params = list(sig.parameters.values())[1:]  # drop self
            assert not any(p.kind == p.VAR_POSITIONAL for p in params), (
                f"{cls.__name__} still has a var-positional legacy seam"
            )
        # concrete TypeError proofs
        with pytest.raises(TypeError):
            PlaylistService(object())
        with pytest.raises(TypeError):
            LibraryService(object(), object())  # legacy positional queue
        with pytest.raises(TypeError):
            QueueService(object())  # keyword-only too

    def test_no_bootstrap_private_integration(self):
        src = Path("src/michi/bootstrap/__init__.py").read_text()
        assert "router._bound" not in src
        assert "_scan_runner._relay" not in src

    def test_no_obsolete_playback_switch_path(self):
        import michi.application.playback_service as mod

        assert not hasattr(mod.PlaybackService, "switch_track")

    def test_bootstrap_no_qt_reexport(self):
        import michi.bootstrap as mod

        assert not hasattr(mod, "QtMultimediaBackend")

    def test_queue_no_repeat_reexport(self):
        import michi.domain.queue as mod

        assert not hasattr(mod, "RepeatMode")
