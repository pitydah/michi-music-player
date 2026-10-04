"""R36 hardened durability — per-case prepare/action/complete checkpoints.

Covers MICHI_M11_4_HARDENED_PHYSICAL_CAMPAIGN_R11_1 section 15 (R36): each case
is independently durable, the checkpoints survive a crash, provenance is
verified before reuse and XRUN injection unavailability is recorded honestly as
DEFERRED_ENVIRONMENT — never fabricating ``fault_injected=true``.
"""

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


def _identity(execution: int = 2, port: int = 3) -> dict:
    return {"execution_generation": execution, "port_generation": port}


def _play_result(
    lab, *, execution: int = 2, port: int = 3, state: str = "direct_container_adapted"
) -> dict:
    return {
        "status": lab.PlaybackStatus.PLAYING.value,
        "error_message": None,
        "signal_truth": {
            "identity": _identity(execution, port),
            "verdict": {"state": state},
        },
    }


def _row() -> dict:
    return {
        "stableDeviceId": "usb:1111:2222:1-2",
        "alsaLocator": "hw:CARD=DAC,DEV=0",
        "available": True,
        "generation": 4,
    }


def _usb() -> dict:
    return {"sysfs_path": "/sys/1-2", "busnum": 1, "devnum": 5}


def _media(tmp_path: Path) -> Path:
    path = tmp_path / "track.wav"
    path.write_bytes(b"track")
    return path


def _wire(lab, monkeypatch, *, state=None):
    state = state if state is not None else {"facts": {}}
    recorded: list[dict] = []
    monkeypatch.setattr(lab, "_git_head", lambda: "head-abc")
    monkeypatch.setattr(
        lab,
        "_manifest",
        lambda _path: {"experiments": {"R36": {"facts": dict(state["facts"])}}},
    )

    def fake_record(_path, **kwargs):
        recorded.append(kwargs)
        state["facts"] = kwargs.get("facts") or {}

    monkeypatch.setattr(lab, "_record", fake_record)
    return recorded


def _fake_container(lab, monkeypatch, *, proc_path: Path | None = None):
    container = SimpleNamespace(shutdown=lambda: None)
    if proc_path is not None:
        snapshot = SimpleNamespace(
            device_negotiated=SimpleNamespace(proc_path=str(proc_path))
        )
        container._signal_truth = SimpleNamespace(active_snapshot=snapshot)
    monkeypatch.setattr(lab, "_container", lambda *_args: container)
    return container


def _play_spy(lab, monkeypatch, results):
    calls: list[str] = []
    queue = list(results)

    def fake(_container, media, _mode):
        calls.append(str(media))
        return queue.pop(0) if queue else _play_result(lab)

    monkeypatch.setattr(lab, "_play", fake)
    return calls


def _prepare_args(tmp_path: Path, media: Path) -> Namespace:
    return Namespace(
        case="suspend_resume",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=media,
        mode="compatible",
        operator_reference="operator:session-1",
        wip_dir=tmp_path / "wip",
    )


def _complete_args(tmp_path: Path, media: Path, *, resume: bool = False) -> Namespace:
    return Namespace(
        case="suspend_resume",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=media,
        mode="compatible",
        wip_dir=tmp_path / "wip",
        resume=resume,
    )


def _xrun_args(tmp_path: Path, media: Path, *, resume: bool = False) -> Namespace:
    return Namespace(
        case="induced_underrun",
        device_id="usb:1111:2222:1-2",
        locator="hw:CARD=DAC,DEV=0",
        manifest=tmp_path / "manifest.json",
        media=media,
        mode="compatible",
        wip_dir=tmp_path / "wip",
        resume=resume,
        inject=True,
    )


def _prepare(lab, monkeypatch, tmp_path: Path, media: Path, *, suspend_before=10):
    _fake_container(lab, monkeypatch)
    _play_spy(lab, monkeypatch, [_play_result(lab)])
    monkeypatch.setattr(lab, "_row", lambda *_args: _row())
    monkeypatch.setattr(lab, "_usb_instance_witness", lambda _device_id: _usb())
    monkeypatch.setattr(lab, "_suspend_success_count", lambda: suspend_before)
    return lab.command_fault_prepare(_prepare_args(tmp_path, media))


def test_r36_durability_prepare_seals_pending_baseline(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    recorded = _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)

    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    wip = tmp_path / "wip"
    record = json.loads(
        (wip / "case-suspend_resume-prepare.json").read_text(encoding="utf-8")
    )
    assert record["phase"] == "prepare"
    assert record["payload"]["operator_reference"] == "operator:session-1"
    journal = (wip / "journal.jsonl").read_text(encoding="utf-8")
    assert "R36_CASE_PREPARE" in journal
    assert recorded[-1]["status"] == "REQUIRES_OPERATOR_CONFIRMATION"
    pending = recorded[-1]["facts"]["pending_cases"]
    assert pending["suspend_resume"]["case"] == "suspend_resume"


def test_r36_durability_complete_seals_action_and_complete(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)
    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])
    monkeypatch.setattr(lab, "_row", lambda *_args: _row())
    monkeypatch.setattr(lab, "_usb_instance_witness", lambda _device_id: _usb())
    monkeypatch.setattr(lab, "_suspend_success_count", lambda: 11)

    assert lab.command_fault_complete(_complete_args(tmp_path, media)) == 0

    wip = tmp_path / "wip"
    action = json.loads(
        (wip / "case-suspend_resume-action.json").read_text(encoding="utf-8")
    )
    assert action["payload"]["suspend_success_after"] == 11
    complete = json.loads(
        (wip / "case-suspend_resume-complete.json").read_text(encoding="utf-8")
    )
    assert complete["result"] == "PASS"
    assert complete["payload"]["continuity_proof"] is True
    facts = recorded[-1]["facts"]
    assert facts["cases"]["suspend_resume"]["continuity_proof"] is True
    assert "suspend_resume" not in facts["pending_cases"]
    assert recorded[-1]["status"] == "REQUIRES_OPERATOR_CONFIRMATION"


def test_r36_durability_resume_recovers_sealed_case(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)
    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])
    monkeypatch.setattr(lab, "_row", lambda *_args: _row())
    monkeypatch.setattr(lab, "_usb_instance_witness", lambda _device_id: _usb())
    monkeypatch.setattr(lab, "_suspend_success_count", lambda: 11)
    assert lab.command_fault_complete(_complete_args(tmp_path, media)) == 0

    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    calls = _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])
    with pytest.raises(SystemExit, match="STOP_R36_CASE_ALREADY_SEALED"):
        lab.command_fault_complete(_complete_args(tmp_path, media))
    assert calls == [], "a sealed PASS case must not be replayed"
    assert recorded == []

    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    calls = _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])
    assert lab.command_fault_complete(_complete_args(tmp_path, media, resume=True)) == 0
    assert calls == [], "a resumed case must never be replayed"
    journal = (tmp_path / "wip" / "journal.jsonl").read_text(encoding="utf-8")
    assert "R36_CASE_RECOVERED" in journal
    assert recorded == [], "an unchanged canonical record must not be rewritten"


def test_r36_durability_baseline_mismatch_stops(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)
    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    state["facts"]["pending_cases"]["suspend_resume"]["operator_reference"] = "tampered"
    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    calls = _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])

    with pytest.raises(SystemExit, match="STOP_R36_WIP_PROVENANCE_MISMATCH"):
        lab.command_fault_complete(_complete_args(tmp_path, media))

    assert calls == [], "a drifted baseline must never be completed"
    assert recorded == []


def test_r36_durability_provenance_mismatch_stops(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)
    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    meta_path = tmp_path / "wip" / "wip-meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["implementation_head"] = "different-head"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    calls = _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])

    with pytest.raises(SystemExit, match="STOP_R36_WIP_PROVENANCE_MISMATCH"):
        lab.command_fault_complete(_complete_args(tmp_path, media))

    assert calls == [], "a changed environment must never resume sealed cases"
    assert recorded == []


def test_r36_durability_changed_media_stops(lab, tmp_path, monkeypatch) -> None:
    state = {"facts": {}}
    _wire(lab, monkeypatch, state=state)
    media = _media(tmp_path)
    assert _prepare(lab, monkeypatch, tmp_path, media) == 0

    media.write_bytes(b"DIFFERENT-MEDIA-FOR-THE-SAME-CASE")
    recorded = _wire(lab, monkeypatch, state=state)
    _fake_container(lab, monkeypatch)
    calls = _play_spy(lab, monkeypatch, [_play_result(lab, execution=3, port=4)])

    with pytest.raises(SystemExit, match="STOP_R36_WIP_PROVENANCE_MISMATCH"):
        lab.command_fault_complete(_complete_args(tmp_path, media))

    assert calls == [], "changed media bytes must never reuse a sealed baseline"
    assert recorded == []


def test_r36_durability_xrun_deferred_without_kernel_injection(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    recorded = _wire(lab, monkeypatch, state=state)
    substream = tmp_path / "sub0"
    substream.mkdir()
    (substream / "hw_params").write_bytes(b"")
    _fake_container(lab, monkeypatch, proc_path=substream / "hw_params")
    media = _media(tmp_path)
    _play_spy(lab, monkeypatch, [_play_result(lab)])

    assert lab.command_xrun(_xrun_args(tmp_path, media)) == 0

    wip = tmp_path / "wip"
    deferred = json.loads(
        (wip / "case-induced_underrun-deferred.json").read_text(encoding="utf-8")
    )
    assert deferred["payload"]["environment_deferred"] is True
    assert deferred["payload"]["mechanism_available"] is False
    assert "fault_injected" not in deferred["payload"]
    facts = recorded[-1]["facts"]["cases"]["induced_underrun"]
    assert facts["environment_deferred"] is True
    assert "fault_injected" not in facts
    assert recorded[-1]["status"] == "REQUIRES_OPERATOR_CONFIRMATION"


def test_r36_durability_xrun_complete_when_injection_available(
    lab, tmp_path, monkeypatch
) -> None:
    state = {"facts": {}}
    recorded = _wire(lab, monkeypatch, state=state)
    substream = tmp_path / "sub1"
    substream.mkdir()
    (substream / "hw_params").write_bytes(b"")
    (substream / "xrun_injection").write_text("0\n", encoding="utf-8")
    (substream / "status").write_text("XRUN\n", encoding="utf-8")
    _fake_container(lab, monkeypatch, proc_path=substream / "hw_params")
    media = _media(tmp_path)
    _play_spy(lab, monkeypatch, [_play_result(lab)])
    monkeypatch.setattr(lab, "_pump", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        lab,
        "_truth",
        lambda _container: {
            "identity": _identity(3, 4),
            "verdict": {"state": "direct_container_adapted", "reason_codes": []},
        },
    )
    monkeypatch.setattr(
        lab,
        "_runtime_resource_snapshot",
        lambda _container: {"pump_alive": True, "port_generation": 4},
    )

    assert lab.command_xrun(_xrun_args(tmp_path, media)) == 0

    wip = tmp_path / "wip"
    complete = json.loads(
        (wip / "case-induced_underrun-complete.json").read_text(encoding="utf-8")
    )
    assert complete["result"] == "PASS"
    assert complete["payload"]["fault_injected"] is True
    assert complete["payload"]["xrun_observed"] is True
    assert (substream / "xrun_injection").read_text(encoding="utf-8").strip() == "1"
    assert recorded[-1]["status"] == "REQUIRES_OPERATOR_CONFIRMATION"
    assert recorded[-1]["facts"]["cases"]["induced_underrun"]["fault_injected"] is True
