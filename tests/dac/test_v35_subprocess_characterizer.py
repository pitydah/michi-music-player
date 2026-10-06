"""Subprocess-isolated source characterization — protocol and isolation gates."""

from __future__ import annotations

import importlib.util
import json
import struct
import sys
import time
import wave
from pathlib import Path

import pytest

from michi.application.audio_output_ports import SourceCharacterizationError
from michi.infrastructure.audio_engines.subprocess_characterizer import (
    SCHEMA_VERSION,
    SubprocessSourceCharacterizer,
)


def _ok_payload(rate: int = 44100, channels: int = 2, bits: int | None = 16) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "result": {
            "encoding": "PCM",
            "rate_hz": rate,
            "significant_bits": bits,
            "channels": channels,
            "channel_positions": None,
        },
    }


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "tone.wav"
    path.write_bytes(b"RIFF")
    return path


def test_sc_01_worker_success_yields_the_decoded_signal(tmp_path, monkeypatch) -> None:
    characterizer = SubprocessSourceCharacterizer()
    monkeypatch.setattr(
        characterizer,
        "_run",
        lambda argv, generation: (json.dumps(_ok_payload()).encode(), b"", 0, False),
    )

    signal = characterizer.characterize(_source(tmp_path))

    assert signal.encoding == "PCM"
    assert signal.rate_hz == 44100
    assert signal.channels == 2
    assert signal.significant_bits == 16
    assert signal.channel_positions is None


def test_sc_02_wedged_worker_is_terminated_and_typed(tmp_path, monkeypatch) -> None:
    characterizer = SubprocessSourceCharacterizer(timeout_ms=250)
    monkeypatch.setattr(
        characterizer,
        "_argv",
        lambda source: [sys.executable, "-c", "import time; time.sleep(30)"],
    )

    started = time.monotonic()
    with pytest.raises(SourceCharacterizationError) as exc:
        characterizer.characterize(_source(tmp_path))

    assert exc.value.code == "SOURCE_CHARACTERIZATION_TIMEOUT"
    assert time.monotonic() - started < 5.0, "a wedged worker must be killed fast"


def test_sc_03_worker_error_json_wins_over_exit_code(tmp_path, monkeypatch) -> None:
    characterizer = SubprocessSourceCharacterizer()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "error": {"code": "SOURCE_ENCODING_UNSUPPORTED", "detail": "not PCM"},
    }
    monkeypatch.setattr(
        characterizer,
        "_run",
        lambda argv, generation: (json.dumps(payload).encode(), b"", 1, False),
    )

    with pytest.raises(SourceCharacterizationError) as exc:
        characterizer.characterize(_source(tmp_path))

    assert exc.value.code == "SOURCE_ENCODING_UNSUPPORTED"


def test_sc_04_garbage_stdout_is_a_protocol_failure(tmp_path, monkeypatch) -> None:
    characterizer = SubprocessSourceCharacterizer()
    monkeypatch.setattr(
        characterizer,
        "_run",
        lambda argv, generation: (b"not-json", b"boom", 1, False),
    )

    with pytest.raises(SourceCharacterizationError) as exc:
        characterizer.characterize(_source(tmp_path))

    assert exc.value.code == "SOURCE_CHARACTERIZATION_FAILED"


def test_sc_05_missing_source_never_spawns_a_worker(tmp_path) -> None:
    characterizer = SubprocessSourceCharacterizer()

    with pytest.raises(SourceCharacterizationError) as exc:
        characterizer.characterize(tmp_path / "missing.flac")

    assert exc.value.code == "SOURCE_FILE_UNAVAILABLE"


def test_sc_06_superseded_generation_is_stale(tmp_path, monkeypatch) -> None:
    characterizer = SubprocessSourceCharacterizer()

    def run(argv, generation):
        characterizer.cancel()  # supersede while the worker "runs"
        return (json.dumps(_ok_payload()).encode(), b"", 0, False)

    monkeypatch.setattr(characterizer, "_run", run)

    with pytest.raises(SourceCharacterizationError) as exc:
        characterizer.characterize(_source(tmp_path))

    assert exc.value.code == "SOURCE_CHARACTERIZATION_STALE"


def test_sc_07_real_worker_characterizes_a_wav(tmp_path) -> None:
    if importlib.util.find_spec("gi") is None:
        pytest.skip("PyGObject/GStreamer unavailable in this environment")
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(44100)
        handle.writeframes(b"".join(struct.pack("<hh", 0, 0) for _ in range(2205)))

    signal = SubprocessSourceCharacterizer(timeout_ms=10000).characterize(path)

    assert signal.encoding == "PCM"
    assert signal.rate_hz == 44100
    assert signal.channels == 2
