"""R25 hardened durability — per-delay sealing, crash survival, resume provenance."""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def lab():
    path = Path(__file__).parents[2] / "scripts" / "dac_m11_4_pcm_lab.py"
    spec = importlib.util.spec_from_file_location("dac_m11_4_pcm_lab", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _observations_file(tmp_path: Path) -> Path:
    path = tmp_path / "observations.json"
    path.write_text(
        json.dumps(
            {
                str(delay): {
                    "evidence_reference": f"operator:test:{delay}",
                    "observed_result": "PASS: intact",
                }
                for delay in (0, 100, 250, 500, 1000)
            }
        ),
        encoding="utf-8",
    )
    return path


def _transition_args(tmp_path: Path, wip_dir: Path, *, resume: bool = False):
    marker = tmp_path / "marker.wav"
    marker.write_bytes(b"RIFF-marker")
    media = []
    for index in range(7):
        item = tmp_path / f"fixture-{index}.wav"
        item.write_bytes(f"RIFF-{index}".encode())
        media.append(item)
    return Namespace(
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        mode="compatible",
        media=media,
        first_sample_method="operator-listening",
        first_sample_fixture=marker,
        first_sample_expected_marker="tick",
        first_sample_observations=_observations_file(tmp_path),
        wip_dir=wip_dir,
        resume=resume,
    )


def _fake_run(delay: int) -> dict:
    return {
        "configured_delay_ms": delay,
        "actual_hold_ms": delay,
        "edges": ["44100->44100"],
        "stale_generation_observed": False,
        "hidden_conversion_observed": False,
        "xrun_count": 0,
        "receipts": [
            {"error": None, "xrun_count": 0, "actual_hold_ms": delay} for _ in range(7)
        ],
    }


def _wire(lab, monkeypatch, *, behavior):
    calls: list[int] = []

    def fake_run(_container, _args, delay, _evidence):
        calls.append(delay)
        return behavior(delay)

    monkeypatch.setattr(
        lab, "_container", lambda *_args: SimpleNamespace(shutdown=lambda: None)
    )
    monkeypatch.setattr(lab, "_git_head", lambda: "head-abc")
    monkeypatch.setattr(lab, "_run_r25_delay", fake_run)
    monkeypatch.setattr(
        lab, "_r25_result", lambda _runs: ("REQUIRES_OPERATOR_CONFIRMATION", None)
    )
    recorded: dict = {}
    monkeypatch.setattr(lab, "_record", lambda _path, **kwargs: recorded.update(kwargs))
    return calls, recorded


def test_r25_durability_seals_each_delay(lab, tmp_path, monkeypatch) -> None:
    calls, recorded = _wire(lab, monkeypatch, behavior=_fake_run)
    args = _transition_args(tmp_path, tmp_path / "wip")

    assert lab.command_transition(args) == 0

    assert calls == [0, 100, 250, 500, 1000]
    for delay in (0, 100, 250, 500, 1000):
        record = json.loads(
            (tmp_path / "wip" / f"delay-{delay:04d}.json").read_text(encoding="utf-8")
        )
        assert record["delay_ms"] == delay
        assert len(record["run"]["receipts"]) == 7
        assert record["first_sample_evidence"]
    journal = (tmp_path / "wip" / "journal.jsonl").read_text(encoding="utf-8")
    assert journal.count("R25_DELAY_SEALED") == 5
    assert recorded["status"] == "REQUIRES_OPERATOR_CONFIRMATION"


def test_r25_durability_crash_keeps_completed_delays(
    lab, tmp_path, monkeypatch
) -> None:
    def behavior(delay: int) -> dict:
        if delay == 500:
            raise RuntimeError("simulated process death")
        return _fake_run(delay)

    _calls, recorded = _wire(lab, monkeypatch, behavior=behavior)
    args = _transition_args(tmp_path, tmp_path / "wip")

    with pytest.raises(RuntimeError):
        lab.command_transition(args)

    for delay in (0, 100, 250):
        assert (tmp_path / "wip" / f"delay-{delay:04d}.json").is_file()
    for delay in (500, 1000):
        assert not (tmp_path / "wip" / f"delay-{delay:04d}.json").exists()
    assert recorded == {}, "no canonical R25 record may be built after a crash"


def test_r25_durability_resume_continues_only_missing(
    lab, tmp_path, monkeypatch
) -> None:
    def crash(delay: int) -> dict:
        if delay == 500:
            raise RuntimeError("simulated process death")
        return _fake_run(delay)

    _wire(lab, monkeypatch, behavior=crash)
    wip = tmp_path / "wip"
    with pytest.raises(RuntimeError):
        lab.command_transition(_transition_args(tmp_path, wip))

    calls, recorded = _wire(lab, monkeypatch, behavior=_fake_run)
    resumed = _transition_args(tmp_path, wip, resume=True)

    assert lab.command_transition(resumed) == 0

    assert calls == [500, 1000], "sealed delays must be recovered, not re-executed"
    journal = (wip / "journal.jsonl").read_text(encoding="utf-8")
    assert journal.count("R25_DELAY_RECOVERED") == 3
    assert recorded["status"] == "REQUIRES_OPERATOR_CONFIRMATION"


def test_r25_durability_resume_provenance_mismatch_stops(
    lab, tmp_path, monkeypatch
) -> None:
    _wire(lab, monkeypatch, behavior=_fake_run)
    wip = tmp_path / "wip"
    lab.command_transition(_transition_args(tmp_path, wip))

    meta_path = wip / "wip-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["implementation_head"] = "different-head"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    calls, recorded = _wire(lab, monkeypatch, behavior=_fake_run)
    resumed = _transition_args(tmp_path, wip, resume=True)

    with pytest.raises(SystemExit, match="STOP_R25_WIP_PROVENANCE_MISMATCH"):
        lab.command_transition(resumed)

    assert calls == [], "a changed environment must never resume sealed delays"
    assert recorded == {}


def test_r25_durability_resume_with_changed_observations_stops(
    lab, tmp_path, monkeypatch
) -> None:
    _wire(lab, monkeypatch, behavior=_fake_run)
    wip = tmp_path / "wip"
    args = _transition_args(tmp_path, wip)
    lab.command_transition(args)

    calls, recorded = _wire(lab, monkeypatch, behavior=_fake_run)
    resumed = _transition_args(tmp_path, wip, resume=True)
    observations = resumed.first_sample_observations
    payload = json.loads(observations.read_text(encoding="utf-8"))
    payload["100"]["observed_result"] = "FAIL: changed after the fact"
    observations.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit, match="STOP_R25_WIP_PROVENANCE_MISMATCH"):
        lab.command_transition(resumed)

    assert calls == [], "changed operator inputs must never reuse sealed delays"
    assert recorded == {}
