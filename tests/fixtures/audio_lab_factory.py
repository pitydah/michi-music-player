"""Deterministic, legally generated audio fixtures for Audio Lab tests."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path


class AudioFixtureFactory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def wav(
        self,
        name: str = "tone.wav",
        *,
        duration: float = 0.25,
        sample_rate: int = 44_100,
        channels: int = 1,
        amplitude: float = 0.25,
        frequency: float = 440.0,
        silence: bool = False,
    ) -> Path:
        path = self.root / name
        frame_count = int(duration * sample_rate)
        with wave.open(str(path), "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            frames = bytearray()
            for index in range(frame_count):
                value = 0 if silence else int(
                    max(-1.0, min(1.0, amplitude * math.sin(2 * math.pi * frequency * index / sample_rate)))
                    * 32767
                )
                frame = struct.pack("<h", value)
                frames.extend(frame * channels)
            output.writeframes(bytes(frames))
        return path

    def empty(self, name: str = "empty.wav") -> Path:
        path = self.root / name
        path.write_bytes(b"")
        return path

    def truncated(self, source: Path, name: str = "truncated.wav") -> Path:
        path = self.root / name
        data = source.read_bytes()
        path.write_bytes(data[: max(1, len(data) // 3)])
        return path

    def compressed(self, source: Path, format_name: str, *, metadata: bool = False) -> Path:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg is required for compressed Audio Lab fixtures")
        format_name = format_name.lower()
        suffix = {"aac": "m4a", "opus": "opus"}.get(format_name, format_name)
        target = self.root / f"tone.{suffix}"
        codec_args = {
            "flac": ["-c:a", "flac"],
            "mp3": ["-c:a", "libmp3lame", "-b:a", "128k"],
            "opus": ["-c:a", "libopus", "-b:a", "96k"],
            "aac": ["-c:a", "aac", "-b:a", "128k"],
        }
        if format_name not in codec_args:
            raise ValueError(f"Unsupported synthetic fixture format: {format_name}")
        command = [ffmpeg, "-v", "error", "-y", "-i", str(source), *codec_args[format_name]]
        if metadata:
            command.extend(["-metadata", "title=Synthetic Tone", "-metadata", "artist=Michi Tests"])
        command.append(str(target))
        subprocess.run(command, check=True, capture_output=True)
        return target

    def corpus(self) -> dict[str, Path]:
        tone = self.wav()
        silence = self.wav("silence.wav", silence=True)
        clipping = self.wav("clipping.wav", amplitude=1.0)
        multichannel = self.wav("multichannel.wav", channels=2)
        hires = self.wav("hires.wav", sample_rate=96_000)
        fixtures = {
            "wav": tone,
            "silence": silence,
            "clipping": clipping,
            "multichannel": multichannel,
            "hires": hires,
            "empty": self.empty(),
            "truncated": self.truncated(tone),
        }
        if shutil.which("ffmpeg"):
            for format_name in ("flac", "mp3", "opus", "aac"):
                fixtures[format_name] = self.compressed(
                    tone, format_name, metadata=format_name == "flac"
                )
        return fixtures
