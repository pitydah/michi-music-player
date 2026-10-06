"""Phase-2 contract isolation gates.

Prevents a repeat of the F05 rebase contamination: processing-runtime
failure semantics belong ONLY to the phases that own the runtime, and the
closed phase contracts must stay byte-meaningful for their own scope.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md"

#: Terms that only the processing runtime (F05) may own. "readback
#: mismatch" is intentionally absent: it has legitimate pre-existing
#: occurrences in other phases (verified against 51aedb2, the pre-rebase
#: canonical plan).
F05_ONLY_TERMS = (
    "host loss during active processing",
    "child graph build failure",
    "unsupported native strategy",
    "PREPARE_PROCESSING_CANDIDATE",
    "PRODUCTIVE PARENT Gst OBJECT COUNT = 0",
    "gstreamer_host_protocol.py",
)

#: Phases that do NOT own the processing runtime.
NON_OWNER_PHASES = tuple(f"R11-F{index:02d}" for index in (*range(0, 5), *range(7, 16)))


def _block(text: str, name: str) -> str:
    begin = f"<!-- MICHI_PHASE2:CONTRACT:{name}:BEGIN -->"
    end = f"<!-- MICHI_PHASE2:CONTRACT:{name}:END -->"
    assert text.count(begin) == 1, f"{name}: BEGIN anchor"
    assert text.count(end) == 1, f"{name}: END anchor"
    return text.split(begin, 1)[1].split(end, 1)[0]


def _spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_closed_phase_contracts_carry_no_f05_processing_semantics() -> None:
    text = _spec_text()
    for phase in NON_OWNER_PHASES:
        block = _block(text, phase)
        for term in F05_ONLY_TERMS:
            assert term not in block, f"{phase} must not own {term!r}"


def test_f05_contract_owns_the_host_aware_processing_runtime() -> None:
    block = _block(_spec_text(), "R11-F05")
    for term in (
        "host loss during active processing",
        "child graph build failure",
        "readback mismatch",
        "unsupported native strategy",
        "PREPARE_PROCESSING_CANDIDATE",
        "PRODUCTIVE PARENT Gst OBJECT COUNT = 0",
        "gstreamer_host_protocol.py",
        "F05-WU0 PRE-RUNTIME ENABLER",
        "output_session_service.py",
        "playback_service.py",
        "second AudioPort / second GStreamer host / second SignalTruthRecorder",
    ):
        assert term in block, f"R11-F05 must own {term!r}"


def test_f06_references_the_processing_runtime_owner() -> None:
    block = _block(_spec_text(), "R11-F06")
    assert "see the R11-F05 Universal failure semantics extension" in block


def test_f05_phase_card_is_host_aware() -> None:
    text = _spec_text()
    begin = "<!-- MICHI_PHASE2:PHASE:AP2-F05:BEGIN -->"
    end = "<!-- MICHI_PHASE2:PHASE:AP2-F05:END -->"
    card = text.split(begin, 1)[1].split(end, 1)[0]
    for term in (
        "191.10",
        "GStreamer Output Host",
        "PRODUCTIVE PARENT Gst OBJECT COUNT = 0",
        "single-flight",
    ):
        assert term in card, f"AP2-F05 card must mention {term!r}"


def test_guniversal_failure_blocks_stay_restored_for_closed_phases() -> None:
    """The pre-existing cross-phase rules remain where they were canonical."""
    text = _spec_text()
    for phase in NON_OWNER_PHASES:
        block = _block(text, phase)
        assert "no false success" in block, phase
        assert "newer user intent wins" in block, phase
