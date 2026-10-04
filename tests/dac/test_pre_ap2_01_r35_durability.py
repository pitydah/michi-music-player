"""R35 hardened durability — per-fixture sealing, crash survival, resume provenance."""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURES = (
    "nonzero_final_samples",
    "end_impulse",
    "same_tuple_two_track_boundary",
    "different_tuple_two_track_boundary",
)


@pytest.fixture(scope="module")
def lab():
    path = Path(__file__).parents[2] / "scripts" / "dac_m11_4_pcm_lab.py"
    spec = importlib.util.spec_from_file_location("dac_m11_4_pcm_lab", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tail_args(
    tmp_path: Path,
    wip_dir: Path,
    fixture: str,
    *,
    resume: bool = False,
    result: str = "PASS",
):
    media = tmp_path / f"{fixture}.wav"
    media.write_bytes(f"RIFF-{fixture}".encode())
    capture = tmp_path / f"{fixture}-capture.wav"
    capture.write_bytes(f"CAPTURE-{fixture}".encode())
    return Namespace(
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        mode="compatible",
        media=media,
        fixture=fixture,
        tail_result=result,
        evidence_kind="capture",
        evidence_reference=str(capture),
        method="operator-listening",
        falsifier_observed=False,
        timeout_seconds=5.0,
        wip_dir=wip_dir,
        resume=resume,
    )


def _wire(lab, monkeypatch, *, behavior, state=None):
    calls: list[str] = []
    recorded: list[dict] = []
    state = state if state is not None else {"facts": {}}

    def fake_play(_container, media, _mode):
        name = Path(media).stem
        calls.append(name)
        if behavior(name) == "crash":
            raise RuntimeError("simulated process death")
        return {"error_message": None}

    monkeypatch.setattr(
        lab,
        "_container",
        lambda *_args: SimpleNamespace(
            shutdown=lambda: None,
            _playback=SimpleNamespace(
                state=SimpleNamespace(status=lab.PlaybackStatus.STOPPED)
            ),
        ),
    )
    monkeypatch.setattr(lab, "_git_head", lambda: "head-abc")
    monkeypatch.setattr(lab, "_play", fake_play)
    monkeypatch.setattr(lab, "_pump", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        lab,
        "_manifest",
        lambda _path: {"experiments": {"R35": {"facts": dict(state["facts"])}}},
    )

    def fake_record(_path, **kwargs):
        recorded.append(kwargs)
        state["facts"] = kwargs.get("facts") or {}

    monkeypatch.setattr(lab, "_record", fake_record)
    return calls, recorded


def test_r35_durability_seals_each_fixture(lab, tmp_path, monkeypatch) -> None:
    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok")
    wip = tmp_path / "wip"

    for fixture in FIXTURES:
        assert lab.command_tail(_tail_args(tmp_path, wip, fixture)) == 0

    assert calls == list(FIXTURES)
    for fixture in FIXTURES:
        record = json.loads(
            (wip / f"fixture-{fixture}.json").read_text(encoding="utf-8")
        )
        assert record["fixture"] == fixture
        assert record["entry"]["result"] == "PASS"
        assert record["entry"]["fixture_sha256"]
        assert record["entry"]["sha256"]
    journal = (wip / "journal.jsonl").read_text(encoding="utf-8")
    assert journal.count("R35_FIXTURE_SEALED") == 4
    assert recorded[-1]["status"] == "PASS"
    assert set(recorded[-1]["facts"]["fixtures"]) == set(FIXTURES)


def test_r35_durability_crash_keeps_completed_fixtures(
    lab, tmp_path, monkeypatch
) -> None:
    calls, recorded = _wire(
        lab,
        monkeypatch,
        behavior=lambda name: (
            "crash" if name == "same_tuple_two_track_boundary" else "ok"
        ),
    )
    wip = tmp_path / "wip"

    for fixture in FIXTURES[:2]:
        assert lab.command_tail(_tail_args(tmp_path, wip, fixture)) == 0
    with pytest.raises(RuntimeError):
        lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[2]))

    for fixture in FIXTURES[:2]:
        assert (wip / f"fixture-{fixture}.json").is_file()
    assert not (wip / f"fixture-{FIXTURES[2]}.json").exists()
    assert len(recorded) == 2, "a crash must not import an unsealed fixture"


def test_r35_durability_resume_recovers_sealed_fixture(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    wip = tmp_path / "wip"
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0])) == 0

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0], resume=True)) == 0

    assert calls == [], "a sealed fixture must never be replayed on resume"
    journal = (wip / "journal.jsonl").read_text(encoding="utf-8")
    assert "R35_FIXTURE_RECOVERED" in journal
    assert recorded == [], "an unchanged canonical record must not be rewritten"


def test_r35_durability_resume_plays_unsealed_fixture(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    _wire(
        lab,
        monkeypatch,
        behavior=lambda name: "crash" if name == "end_impulse" else "ok",
        state=state,
    )
    wip = tmp_path / "wip"
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0])) == 0
    with pytest.raises(RuntimeError):
        lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[1]))

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[1], resume=True)) == 0

    assert calls == [FIXTURES[1]], "only the interrupted fixture may be replayed"
    assert (wip / f"fixture-{FIXTURES[1]}.json").is_file()
    assert set(recorded[-1]["facts"]["fixtures"]) == set(FIXTURES[:2])


def test_r35_durability_resume_provenance_mismatch_stops(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    wip = tmp_path / "wip"
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0])) == 0

    meta_path = wip / "wip-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["implementation_head"] = "different-head"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    with pytest.raises(SystemExit, match="STOP_R35_WIP_PROVENANCE_MISMATCH"):
        lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[1], resume=True))

    assert calls == [], "a changed environment must never resume sealed fixtures"
    assert recorded == []


def test_r35_durability_resume_with_changed_media_stops(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    wip = tmp_path / "wip"
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0])) == 0

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    resumed = _tail_args(tmp_path, wip, FIXTURES[0], resume=True)
    resumed.media.write_bytes(b"DIFFERENT-MEDIA-FOR-THE-SAME-FIXTURE")
    with pytest.raises(SystemExit, match="STOP_R35_WIP_PROVENANCE_MISMATCH"):
        lab.command_tail(resumed)

    assert calls == [], "changed media bytes must never reuse a sealed fixture"
    assert recorded == []


def test_r35_durability_sealed_fail_is_sticky(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    wip = tmp_path / "wip"
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0], result="FAIL")) == 0

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    with pytest.raises(SystemExit, match="STOP_R35_FIXTURE_SEALED_FAIL"):
        lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0]))

    assert calls == [], "a sealed FAIL must be retested in a fresh WIP directory"
    assert recorded == []


def test_r35_durability_not_observed_can_be_retried(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    wip = tmp_path / "wip"
    assert (
        lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0], result="NOT_OBSERVED"))
        == 0
    )

    calls, recorded = _wire(lab, monkeypatch, behavior=lambda _name: "ok", state=state)
    assert lab.command_tail(_tail_args(tmp_path, wip, FIXTURES[0])) == 0

    assert calls == [FIXTURES[0]], "an unobserved fixture must be replayed"
    journal = (wip / "journal.jsonl").read_text(encoding="utf-8")
    assert "R35_FIXTURE_RETRY" in journal
    record = json.loads(
        (wip / f"fixture-{FIXTURES[0]}.json").read_text(encoding="utf-8")
    )
    assert record["entry"]["result"] == "PASS"
    assert recorded[-1]["status"] == "REQUIRES_OPERATOR_CONFIRMATION"
