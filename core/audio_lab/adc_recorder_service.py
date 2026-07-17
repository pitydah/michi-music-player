"""Productive analog/ADC capture service for Michi Audio Lab.

The service owns exactly one recording process. Hardware discovery and capture
are capability-gated: unsupported platforms or missing tools return structured
errors instead of pretending that recording started.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioDevice:
    """Stable description of an input device and its FFmpeg capture target."""

    device_id: str
    name: str
    backend: str
    capture_spec: str
    is_usb: bool = False
    is_turntable: bool = False
    brand: str | None = None
    channels: int = 2
    sample_rate: int = 44100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecordingSession:
    session_id: str
    input_device: AudioDevice
    output_path: str
    format: str
    start_time: float
    end_time: float | None = None
    duration: float = 0.0
    file_size: int = 0
    markers: list[dict[str, Any]] = field(default_factory=list)
    status: str = "starting"
    error: str = ""
    pid: int | None = None


class USBTurntableDetector:
    """Discover audio capture devices without treating brand matching as proof."""

    TURNTABLE_BRANDS = (
        "audio-technica",
        "audiotechnica",
        "pro-ject",
        "project",
        "rega",
        "numark",
        "sony",
        "pioneer",
        "technics",
        "yamaha",
        "denon",
        "marantz",
        "cambridge audio",
        "behringer",
    )

    def __init__(self) -> None:
        self.detected_devices: list[AudioDevice] = []

    def scan_usb_devices(self) -> list[AudioDevice]:
        if sys.platform.startswith("linux"):
            devices = self._scan_linux()
        elif sys.platform == "win32":
            devices = self._scan_windows()
        elif sys.platform == "darwin":
            devices = self._scan_macos()
        else:
            devices = []
        self.detected_devices = devices
        return list(devices)

    def _classification(self, name: str) -> tuple[bool, str | None]:
        lowered = name.casefold()
        for brand in self.TURNTABLE_BRANDS:
            if brand in lowered:
                return True, brand.title()
        return False, None

    def _scan_linux(self) -> list[AudioDevice]:
        if not shutil.which("arecord"):
            return []
        try:
            result = subprocess.run(
                ["arecord", "-l"], capture_output=True, text=True, timeout=5, check=False
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Linux capture discovery failed: %s", exc)
            return []
        if result.returncode != 0:
            logger.warning("arecord -l failed: %s", result.stderr.strip())
            return []

        devices: list[AudioDevice] = []
        pattern = re.compile(
            r"card\s+(?P<card>\d+):\s*(?P<card_name>[^\[]+)?\[(?P<label>[^\]]+)\].*"
            r"device\s+(?P<device>\d+):\s*(?P<device_name>[^\[]+)?",
            re.IGNORECASE,
        )
        for line in result.stdout.splitlines():
            match = pattern.search(line)
            if not match:
                continue
            card = match.group("card")
            device = match.group("device")
            label = (match.group("label") or match.group("card_name") or "Audio input").strip()
            full_name = " ".join(part for part in (label, match.group("device_name")) if part).strip()
            is_turntable, brand = self._classification(full_name)
            lowered = line.casefold()
            devices.append(
                AudioDevice(
                    device_id=f"alsa:{card},{device}",
                    name=full_name,
                    backend="alsa",
                    capture_spec=f"hw:{card},{device}",
                    is_usb="usb" in lowered,
                    is_turntable=is_turntable,
                    brand=brand,
                )
            )
        return devices

    def _scan_windows(self) -> list[AudioDevice]:
        try:
            import pyaudio  # type: ignore
        except ImportError:
            logger.info("PyAudio is not installed; Windows capture discovery disabled")
            return []

        devices: list[AudioDevice] = []
        audio = pyaudio.PyAudio()
        try:
            for index in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(index)
                if int(info.get("maxInputChannels", 0)) <= 0:
                    continue
                name = str(info.get("name", f"Input {index}"))
                is_turntable, brand = self._classification(name)
                devices.append(
                    AudioDevice(
                        device_id=f"dshow:{index}",
                        name=name,
                        backend="dshow",
                        capture_spec=name,
                        is_usb="usb" in name.casefold(),
                        is_turntable=is_turntable,
                        brand=brand,
                        channels=min(int(info.get("maxInputChannels", 2)), 2),
                        sample_rate=int(info.get("defaultSampleRate", 44100)),
                    )
                )
        finally:
            audio.terminate()
        return devices

    def _scan_macos(self) -> list[AudioDevice]:
        """Parse FFmpeg's AVFoundation input list when available."""
        if not shutil.which("ffmpeg"):
            return []
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("macOS capture discovery failed: %s", exc)
            return []

        devices: list[AudioDevice] = []
        in_audio_section = False
        pattern = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+)$")
        for line in result.stderr.splitlines():
            lower = line.casefold()
            if "avfoundation audio devices" in lower:
                in_audio_section = True
                continue
            if in_audio_section and "avfoundation video devices" in lower:
                continue
            if not in_audio_section:
                continue
            match = pattern.search(line)
            if not match:
                continue
            index = match.group("index")
            name = match.group("name").strip()
            is_turntable, brand = self._classification(name)
            devices.append(
                AudioDevice(
                    device_id=f"avfoundation:{index}",
                    name=name,
                    backend="avfoundation",
                    capture_spec=f":{index}",
                    is_usb="usb" in name.casefold(),
                    is_turntable=is_turntable,
                    brand=brand,
                )
            )
        return devices

    def get_turntables(self) -> list[AudioDevice]:
        return [device for device in self.detected_devices if device.is_turntable]


class ADCRecorderService:
    """Own a single FFmpeg capture process and its recording session."""

    SUPPORTED_FORMATS = ("wav", "flac", "mp3", "opus")
    DSP_FILTERS = ("declicker", "dehisser", "riaa_eq", "noise_gate", "normalize")

    def __init__(self, detector: USBTurntableDetector | None = None) -> None:
        self.turntable_detector = detector or USBTurntableDetector()
        self.active_session: RecordingSession | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._monitor_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []
        self._lock = threading.RLock()
        self._paused_at: float | None = None
        self._paused_total = 0.0

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return bool(self._process and self._process.poll() is None and self.active_session)

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return bool(self.active_session and self.active_session.status == "paused")

    def available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def detect_devices(self) -> list[AudioDevice]:
        return self.turntable_detector.scan_usb_devices()

    def get_recommended_device(self) -> AudioDevice | None:
        devices = self.detect_devices()
        return next(
            (
                device
                for predicate in (
                    lambda item: item.is_turntable,
                    lambda item: item.is_usb,
                    lambda _item: True,
                )
                for device in devices
                if predicate(device)
            ),
            None,
        )

    def _input_args(self, device: AudioDevice) -> list[str]:
        if device.backend == "alsa":
            return ["-f", "alsa", "-i", device.capture_spec]
        if device.backend == "dshow":
            return ["-f", "dshow", "-i", f"audio={device.capture_spec}"]
        if device.backend == "avfoundation":
            return ["-f", "avfoundation", "-i", device.capture_spec]
        raise ValueError(f"Unsupported capture backend: {device.backend}")

    @staticmethod
    def _filter_chain(filters: list[str]) -> list[str]:
        chain: list[str] = []
        if "riaa_eq" in filters:
            # Approximate inverse RIAA curve. Kept opt-in because many USB
            # turntables already provide line-level, RIAA-equalized audio.
            chain.extend(
                (
                    "equalizer=f=50:t=q:w=0.7:g=-19",
                    "equalizer=f=500:t=q:w=0.7:g=0",
                    "equalizer=f=2122:t=q:w=0.7:g=19",
                )
            )
        if "declicker" in filters:
            chain.append("adeclick")
        if "dehisser" in filters:
            chain.append("afftdn=nf=-55")
        if "noise_gate" in filters:
            chain.append("agate=threshold=0.015:ratio=3:attack=10:release=250")
        if "normalize" in filters:
            chain.append("loudnorm=I=-18:TP=-1.0:LRA=11")
        return chain

    @staticmethod
    def _codec_args(fmt: str, bit_depth: int) -> list[str]:
        if fmt == "wav":
            codec = {16: "pcm_s16le", 24: "pcm_s24le", 32: "pcm_s32le"}.get(bit_depth)
            if not codec:
                raise ValueError("WAV bit depth must be 16, 24 or 32")
            return ["-c:a", codec]
        if fmt == "flac":
            return ["-c:a", "flac", "-compression_level", "8"]
        if fmt == "mp3":
            return ["-c:a", "libmp3lame", "-b:a", "320k"]
        if fmt == "opus":
            return ["-c:a", "libopus", "-b:a", "256k"]
        raise ValueError(f"Unsupported output format: {fmt}")

    def start_recording(
        self,
        device: AudioDevice,
        output_path: str,
        format: str = "wav",
        sample_rate: int = 44100,
        bit_depth: int = 16,
        channels: int = 2,
        apply_dsp: list[str] | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            if self.is_recording:
                return {"success": False, "error": "RECORDING_ALREADY_ACTIVE"}
            if not self.available():
                return {"success": False, "error": "FFMPEG_NOT_AVAILABLE"}

            fmt = format.casefold().strip()
            if fmt not in self.SUPPORTED_FORMATS:
                return {"success": False, "error": f"UNSUPPORTED_FORMAT:{fmt}"}
            if sample_rate < 8000 or sample_rate > 384000:
                return {"success": False, "error": "INVALID_SAMPLE_RATE"}
            if channels not in (1, 2):
                return {"success": False, "error": "INVALID_CHANNEL_COUNT"}

            filters = list(dict.fromkeys(apply_dsp or []))
            unknown_filters = sorted(set(filters) - set(self.DSP_FILTERS))
            if unknown_filters:
                return {
                    "success": False,
                    "error": "UNSUPPORTED_DSP_FILTER",
                    "filters": unknown_filters,
                }

            target = Path(output_path).expanduser()
            if target.suffix.casefold() != f".{fmt}":
                return {"success": False, "error": "OUTPUT_EXTENSION_MISMATCH"}
            if target.exists() and not overwrite:
                return {"success": False, "error": "OUTPUT_EXISTS"}
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                command = ["ffmpeg", "-hide_banner", "-nostdin" if False else "-loglevel", "warning"]
                command.extend(self._input_args(device))
                command.extend(["-ar", str(sample_rate), "-ac", str(channels)])
                filter_chain = self._filter_chain(filters)
                if filter_chain:
                    command.extend(["-af", ",".join(filter_chain)])
                command.extend(self._codec_args(fmt, bit_depth))
                command.extend(["-y" if overwrite else "-n", str(target)])
            except ValueError as exc:
                return {"success": False, "error": str(exc)}

            session = RecordingSession(
                session_id=f"rec_{uuid.uuid4().hex[:12]}",
                input_device=device,
                output_path=str(target),
                format=fmt,
                start_time=time.monotonic(),
            )
            self._stderr_lines.clear()
            self._paused_at = None
            self._paused_total = 0.0

            try:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                session.status = "error"
                session.error = str(exc)
                self.active_session = session
                return {"success": False, "error": str(exc)}

            session.pid = process.pid
            self.active_session = session
            self._process = process
            self._stderr_thread = threading.Thread(
                target=self._consume_stderr, args=(process,), daemon=True, name="michi-adc-stderr"
            )
            self._stderr_thread.start()

            # Detect invalid devices/codecs before reporting a successful start.
            time.sleep(0.15)
            if process.poll() is not None:
                session.status = "error"
                session.error = "\n".join(self._stderr_lines[-8:]) or f"ffmpeg exited {process.returncode}"
                self._process = None
                return {"success": False, "error": session.error}

            session.status = "recording"
            self._monitor_thread = threading.Thread(
                target=self._monitor_process, args=(process, session), daemon=True, name="michi-adc-monitor"
            )
            self._monitor_thread.start()
            return {
                "success": True,
                "session_id": session.session_id,
                "pid": process.pid,
                "output_path": str(target),
                "dsp_filters": filters,
            }

    def _consume_stderr(self, process: subprocess.Popen[bytes]) -> None:
        if not process.stderr:
            return
        for raw_line in iter(process.stderr.readline, b""):
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if line:
                with self._lock:
                    self._stderr_lines.append(line)
                    del self._stderr_lines[:-100]

    def _monitor_process(self, process: subprocess.Popen[bytes], session: RecordingSession) -> None:
        return_code = process.wait()
        with self._lock:
            now = time.monotonic()
            session.end_time = now
            session.duration = max(0.0, now - session.start_time - self._paused_total)
            target = Path(session.output_path)
            session.file_size = target.stat().st_size if target.exists() else 0
            if session.status not in ("stopping", "cancelled") and return_code != 0:
                session.status = "error"
                session.error = "\n".join(self._stderr_lines[-8:]) or f"ffmpeg exited {return_code}"
            elif session.status != "cancelled":
                session.status = "completed"
            if self._process is process:
                self._process = None

    def pause_recording(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            session = self.active_session
            if not process or process.poll() is not None or not session:
                return {"success": False, "error": "NO_ACTIVE_RECORDING"}
            if session.status == "paused":
                return {"success": True, "status": "paused"}
            if os.name != "posix":
                return {"success": False, "error": "PAUSE_UNSUPPORTED_ON_PLATFORM"}
            os.kill(process.pid, signal.SIGSTOP)
            self._paused_at = time.monotonic()
            session.status = "paused"
            return {"success": True, "status": "paused"}

    def resume_recording(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            session = self.active_session
            if not process or process.poll() is not None or not session:
                return {"success": False, "error": "NO_ACTIVE_RECORDING"}
            if session.status != "paused":
                return {"success": False, "error": "RECORDING_NOT_PAUSED"}
            if os.name != "posix":
                return {"success": False, "error": "RESUME_UNSUPPORTED_ON_PLATFORM"}
            os.kill(process.pid, signal.SIGCONT)
            if self._paused_at is not None:
                self._paused_total += time.monotonic() - self._paused_at
            self._paused_at = None
            session.status = "recording"
            return {"success": True, "status": "recording"}

    def stop_recording(self, timeout: float = 8.0) -> dict[str, Any]:
        with self._lock:
            process = self._process
            session = self.active_session
            if not process or process.poll() is not None or not session:
                return {"success": False, "error": "NO_ACTIVE_RECORDING"}
            if session.status == "paused" and os.name == "posix":
                os.kill(process.pid, signal.SIGCONT)
            session.status = "stopping"
            if process.stdin:
                try:
                    process.stdin.write(b"q\n")
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        return {"success": True, "status": self.active_session.status if self.active_session else "stopped"}

    def add_marker(self, timestamp: float | None = None, label: str = "") -> dict[str, Any]:
        with self._lock:
            session = self.active_session
            if not session or session.status not in ("recording", "paused"):
                return {"success": False, "error": "NO_ACTIVE_RECORDING"}
            elapsed = self._elapsed_locked()
            marker_time = elapsed if timestamp is None else float(timestamp)
            if marker_time < 0 or marker_time > elapsed + 0.5:
                return {"success": False, "error": "INVALID_MARKER_TIMESTAMP"}
            marker = {
                "timestamp": marker_time,
                "label": label.strip() or f"Pista {len(session.markers) + 1}",
                "created_at": time.time(),
            }
            session.markers.append(marker)
            session.markers.sort(key=lambda item: item["timestamp"])
            return {"success": True, "marker": dict(marker)}

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value).strip(" .")
        return cleaned[:120] or "Pista"

    def split_by_markers(self, input_file: str, output_dir: str) -> dict[str, Any]:
        with self._lock:
            session = self.active_session
            if not session or not session.markers:
                return {"success": False, "tracks": [], "errors": ["NO_MARKERS"]}
            markers = [dict(marker) for marker in session.markers]
            total_duration = session.duration or self._elapsed_locked()
            fmt = session.format

        source = Path(input_file)
        if not source.is_file():
            return {"success": False, "tracks": [], "errors": ["INPUT_NOT_FOUND"]}
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        if markers[0]["timestamp"] > 0.001:
            markers.insert(0, {"timestamp": 0.0, "label": "Pista 1"})

        tracks: list[dict[str, Any]] = []
        errors: list[str] = []
        for index, marker in enumerate(markers):
            start = float(marker["timestamp"])
            end = float(markers[index + 1]["timestamp"]) if index + 1 < len(markers) else total_duration
            duration = max(0.0, end - start)
            if duration <= 0:
                errors.append(f"INVALID_DURATION:{index + 1}")
                continue
            filename = f"{index + 1:02d}_{self._safe_name(str(marker['label']))}.{fmt}"
            output = target_dir / filename
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(start),
                "-i",
                str(source),
                "-t",
                str(duration),
                "-c:a",
                "copy",
                "-n",
                str(output),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=180, check=False)
            if completed.returncode == 0:
                tracks.append(
                    {
                        "index": index + 1,
                        "label": marker["label"],
                        "start": start,
                        "duration": duration,
                        "file": str(output),
                    }
                )
            else:
                errors.append(completed.stderr.strip() or f"TRACK_SPLIT_FAILED:{index + 1}")
        return {"success": not errors, "tracks": tracks, "errors": errors}

    def _elapsed_locked(self) -> float:
        session = self.active_session
        if not session:
            return 0.0
        if session.end_time is not None:
            return session.duration
        now = self._paused_at if session.status == "paused" and self._paused_at else time.monotonic()
        return max(0.0, now - session.start_time - self._paused_total)

    def get_recording_status(self) -> dict[str, Any]:
        with self._lock:
            session = self.active_session
            if not session:
                return {"active": False, "status": "idle"}
            target = Path(session.output_path)
            if target.exists():
                session.file_size = target.stat().st_size
            return {
                "active": self.is_recording,
                "paused": session.status == "paused",
                "session_id": session.session_id,
                "device": session.input_device.name,
                "duration": self._elapsed_locked(),
                "file_size": session.file_size,
                "markers_count": len(session.markers),
                "markers": [dict(marker) for marker in session.markers],
                "status": session.status,
                "output_path": session.output_path,
                "error": session.error,
                "pid": session.pid,
                "stderr_tail": list(self._stderr_lines[-8:]),
            }

    def shutdown(self) -> None:
        if self.is_recording:
            self.stop_recording(timeout=3.0)
