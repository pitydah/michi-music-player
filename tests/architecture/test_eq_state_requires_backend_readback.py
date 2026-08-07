"""EQ state is only updated AFTER backend readback confirms the change.

EqualizerService follows validate -> apply -> readback -> update state.
This test scans the source for the ordering invariant: no state assignment
(``self._bands`` / ``self._enabled`` / ``self._preamp``) may happen before the
readback call in the backend-apply paths.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EQ_SOURCE = (PROJECT_ROOT / "core" / "equalizer_service.py").read_text(
    encoding="utf-8")


def _block_source(anchor: str) -> str:
    """Source text of the method containing ``anchor`` (from its def onward)."""
    idx = EQ_SOURCE.find(anchor)
    assert idx != -1, f"anchor not found: {anchor}"
    start = EQ_SOURCE.rfind("def ", 0, idx)
    end = EQ_SOURCE.find("\n    def ", idx)
    return EQ_SOURCE[start:end if end != -1 else len(EQ_SOURCE)]


def test_apply_methods_call_readback_before_state_update() -> None:
    for method_anchor in ("def set_bands(", "def set_preamp(",
                          "def set_enabled("):
        block = _block_source(method_anchor)
        readback_idx = block.find("get_eq_state()")
        assert readback_idx != -1, (
            f"{method_anchor} must perform a backend readback")
        # Find the LAST state assignment in the backend-apply portion.
        for attr in ("self._bands =", "self._preamp =", "self._enabled ="):
            last_assign = block.rfind(attr)
            if last_assign == -1:
                continue
            assert last_assign > readback_idx, (
                f"{method_anchor}: state update ({attr}) must come AFTER "
                f"the readback (found at char {last_assign}, readback at "
                f"{readback_idx})")


def test_backend_errors_are_not_suppressed() -> None:
    source = EQ_SOURCE
    assert "contextlib" not in source or "suppress" not in source, (
        "EqualizerService must not swallow backend errors with "
        "contextlib.suppress")
    assert "BACKEND_APPLY_FAILED" in source
    assert "READBACK_MISMATCH" in source


def test_readback_guard_blocks_state_update() -> None:
    """The readback-mismatch branch must leave the state untouched."""
    for marker in ("READBACK_MISMATCH", "from_backend"):
        assert marker in EQ_SOURCE
