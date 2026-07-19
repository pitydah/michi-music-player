"""Canonical vinyl/ADC recording service.

This module owns capture state and device discovery. Legacy Audio Lab and the
Qt ``VinylCaptureService`` delegate here so there is only one recording engine.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from .vinyl_types import (
    CaptureDevice,
    CaptureRequest,
    RecordingSession,
    RecordingStatus,
    StereoLevels,
)

logger = logging.getLogger("michi.vinyl.recorder")


class USBTurntableDetector:
    """Enumerate input devices and flag likely USB turntables."""

    TURNTABLE_BRANDS = [
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
        "art",
        "behringer",
        "ion",
        "teac",
        "akai",
    ]

    _ALSA_RE = re.compile(
        r"card\s+(?P<card>\d+):\s*(?P<card_id>[^\[]+)\[(?P<card_name>[^\]]+)\],"
        r"\s*device\s+(?P<device>\d+):\s*(?P<device_name>[^\[]+)",
        re.IGNORECASE,
    )
    _AVFOUNDATION_RE = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+)$")

    def __init__(self) -> None:
        self.detected_devices: list[CaptureDevice] = []

    @staticmethod
    def _brand_info(name: str) -> tuple[bool, str | None]:
        lowered = name.lower()
        for brand in USBTurntableDetector.TURNTABLE_BRANDS:
            if brand in lowered:
                return True, brand.title()
        turntable_words = ("turntable", "phono", "vinyl", "usb audio codec")
        return any(word in lowered for word in turntable_words), None

    def scan_usb_devices(self) -> list[CaptureDevice]:
        try:
            if os.name == "nt":
                devices = self._scan_windows()
            elif sys_platform() == "darwin":
                devices = self._scan_macos()
            else:
                devices = self._scan_linux()
        except Exception:
            logger.exception("Audio input discovery failed")
            devices = []
        self.detected_devices = devices
        return devices

    def _scan_linux(self) -> list[CaptureDevice]:
        if not shutil.which("arecord"):
            return []
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("arecord device scan failed: %s", result.stderr.strip())
            return []

        devices: list[CaptureDevice] = []
        for line in result.stdout.splitlines():
            match = self._ALSA_RE.search(line)
            if not match:
                continue
            card = int(match.group("card"))
            dev = int(match.group("device"))
            name = match.group("card_name").strip()
            detail = match.group("device_name").strip()
            full_name = f"{name} — {detail}" if detail and detail not in name else name
            is_turntable, brand = self._brand_info(full_name)
            is_usb = "usb" in line.lower()
            devices.append(
                CaptureDevice(
                    device_id=card * 100 + dev,
                    name=full_name,
                    description=line.strip(),
                    backend="ffmpeg-alsa",
                    source=f"hw:{card},{dev}",
                    is_usb=is_usb,
                    is_turntable=is_turntable,
                    brand=brand,
                    sample_rate=44100,
                    channels=2,
                    is_default=not devices,
                )
            )
        return devices

    def _scan_windows(self) -> list[CaptureDevice]:
        try:
            import pyaudio
        except ImportError:
            logger.info("PyAudio is not installed; Windows input discovery disabled")
            return []

        p = pyaudio.PyAudio()
        devices: list[CaptureDevice] = []
        try:
            for index in range(p.get_device_count()):
                info = p.get_device_info_by_index(index)
                max_inputs = int(info.get("maxInputChannels", 0))
                if max_inputs <= 0:
                    continue
                name = str(info.get("name", f"Input {index}"))
                is_turntable, brand = self._brand_info(name)
                devices.append(
                    CaptureDevice(
                        device_id=index,
                        name=name,
                        description=name,
                        backend="ffmpeg-dshow",
                        source=name,
                        is_usb="usb" in name.lower(),
                        is_turntable=is_turntable,
                        brand=brand,
                        sample_rate=int(info.get("defaultSampleRate", 44100)),
                        channels=min(max_inputs, 2),
                        channel_counts=list(range(1, min(max_inputs, 2) + 1)),
                        is_default=bool(info.get("isDefaultInput", False)),
                    )
                )
        finally:
            p.terminate()
        return devices

    def _scan_macos(self) -> list[CaptureDevice]:
        if not shutil.which("ffmpeg"):
            return []
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-f",
                "avfoundation",
                "-list_devices",
                "true",
                "-i",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        devices: list[CaptureDevice] = []
        in_audio_section = False
        for line in result.stderr.splitlines():
            lowered = line.lower()
            if "avfoundation audio devices" in lowered:
                in_audio_section = True
                continue
            if "avfoundation video devices" in lowered:
                in_audio_section = False
                continue
            if not in_audio_section:
                continue
            match = self._AVFOUNDATION_RE.search(line.strip())
            if not match:
                continue
            index = int(match.group("index"))
            name = match.group("name").strip()
            is_turntable, brand = self._brand_info(name)
            devices.append(
                CaptureDevice(
                    device_id=index,
                    name=name,
                    description=name,
                    backend="ffmpeg-avfoundation",
                    source=str(index),
                    is_usb="usb" in name.lower(),
                    is_turntable=is_turntable,
                    brand=brand,
                    sample_rate=44100,
                    channels=2,
                    is_default=not devices,
                )
            )
        return devices

    def get_turntables(self) -> list[CaptureDevice]:
        return [device for device in self.detected_devices if device.is_turntable]

    def apply_riaa_eq(self, device: CaptureDevice) -> bool:
        """Compatibility helper; RIAA is applied only when explicitly requested."""
        return bool(device.is_turntable)


def sys_platform() -> str:
    import sys

    return sys.platform


class VinylRecorderService:
    """Single source of truth for ADC/vinyl recording state."""

    SUPPORTED_FORMATS = ("wav", "flac", "mp3", "opus")
    DSP_FILTER_ALIASES = {
        "riaa": "riaa_eq",
        "declick": "declicker",
        "dehiss": "dehisser",
    }
    DSP_FILTERS = {
        "riaa_eq",
        "declicker",
        "dehisser",
        "noise_gate",
        "highpass",
        "normalize",
    }
    PCM_CODEC_BY_DEPTH = {
        16: "pcm_s16le",
        24: "pcm_s24le",
        32: "pcm_s32le",
    }

    def __init__(self, detector: USBTurntableDetector | None = None) -> None:
        self.turntable_detector = detector or USBTurntableDetector()
        self.active_session: RecordingSession | None = None
        self.recording_thread: threading.Thread | None = None
        self.is_recording = False
        self.is_paused = False

        self._process: subprocess.Popen | None = None
        self._stderr_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._state_lock = threading.RLock()
        self._stderr_tail: list[str] = []
        self._manual_stop = False

    def __del__(self) -> None:
        try:
            self.stop_recording()
        except Exception:
            pass

    def available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def detect_devices(self) -> list[CaptureDevice]:
        return self.turntable_detector.scan_usb_devices()

    def get_recommended_device(self) -> CaptureDevice | None:
        devices = self.detect_devices()
        for predicate in (
            lambda d: d.is_turntable,
            lambda d: d.is_usb,
            lambda d: d.is_default,
            lambda _d: True,
        ):
            match = next((device for device in devices if predicate(device)), None)
            if match is not None:
                return match
        return None

    @classmethod
    def _normalise_filters(cls, filters: list[str] | None) -> list[str]:
        result: list[str] = []
        for item in filters or []:
            normalised = cls.DSP_FILTER_ALIASES.get(item, item)
            if normalised in cls.DSP_FILTERS and normalised not in result:
                result.append(normalised)
        return result

    @classmethod
    def _build_filter_chain(cls, filters: list[str] | None) -> list[str]:
        chain: list[str] = []
        for item in cls._normalise_filters(filters):
            if item == "riaa_eq":
                chain.extend(
                    [
                        "equalizer=f=50:t=q:w=0.7:g=-19.0",
                        "equalizer=f=500:t=q:w=0.7:g=0",
                        "equalizer=f=2122:t=q:w=0.7:g=19.0",
                    ]
                )
            elif item == "declicker":
                chain.append("adeclick")
            elif item == "dehisser":
                chain.append("afftdn=nf=-70")
            elif item == "noise_gate":
                chain.append("agate=threshold=0.015:ratio=10:attack=5:release=250")
            elif item == "highpass":
                chain.append("highpass=f=20")
            elif item == "normalize":
                chain.append("loudnorm=I=-18:TP=-1.5:LRA=11")
        chain.append("astats=metadata=1:reset=1")
        return chain

    @classmethod
    def _input_args(cls, device: CaptureDevice) -> list[str]:
        if os.name == "nt":
            return ["-f", "dshow", "-i", f"audio={device.source or device.name}"]
        if sys_platform() == "darwin":
            return ["-f", "avfoundation", "-i", f":{device.source}"]
        return ["-f", "alsa", "-i", device.source or f"hw:{device.device_id}"]

    @classmethod
    def _output_args(cls, request: CaptureRequest) -> list[str]:
        fmt = request.format.lower()
        if fmt == "wav":
            codec = cls.PCM_CODEC_BY_DEPTH.get(request.bit_depth)
            if codec is None:
                raise ValueError(f"Unsupported PCM bit depth: {request.bit_depth}")
            return ["-c:a", codec, request.output_path]
        if fmt == "flac":
            sample_fmt = "s16" if request.bit_depth <= 16 else "s32"
            return [
                "-c:a",
                "flac",
                "-sample_fmt",
                sample_fmt,
                "-compression_level",
                "8",
                request.output_path,
            ]
        if fmt == "mp3":
            return ["-c:a", "libmp3lame", "-b:a", "320k", request.output_path]
        if fmt == "opus":
            return ["-c:a", "libopus", "-b:a", "256k", request.output_path]
        raise ValueError(f"Unsupported output format: {request.format}")

    @classmethod
    def build_command(cls, request: CaptureRequest) -> list[str]:
        chain = cls._build_filter_chain(request.dsp_filters)
        return [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-loglevel",
            "info",
            "-thread_queue_size",
            "1024",
            *cls._input_args(request.device),
            "-ar",
            str(request.sample_rate),
            "-ac",
            str(request.channels),
            "-af",
            ",".join(chain),
            "-y",
            *cls._output_args(request),
        ]

    def start_recording(
        self,
        device: CaptureDevice,
        output_path: str | None = None,
        format: str = "wav",
        sample_rate: int = 44100,
        bit_depth: int = 24,
        channels: int = 2,
        apply_dsp: list[str] | None = None,
        output_file: str | None = None,
    ) -> dict[str, Any]:
        """Start capture. ``output_file`` remains a legacy alias."""

        target = output_path or output_file
        result: dict[str, Any] = {
            "success": False,
            "error": None,
            "session_id": None,
        }
        with self._state_lock:
            if self.is_recording:
                result["error"] = "Ya hay una grabación en curso"
                return result
            if not self.available():
                result["error"] = "FFmpeg no está disponible"
                return result
            if not target:
                result["error"] = "Falta la ruta de salida"
                return result
            fmt = format.lower()
            if fmt not in self.SUPPORTED_FORMATS:
                result["error"] = f"Formato {fmt} no soportado"
                return result
            if sample_rate <= 0 or channels not in (1, 2):
                result["error"] = "Configuración de captura inválida"
                return result
            if fmt in ("wav", "flac") and bit_depth not in self.PCM_CODEC_BY_DEPTH:
                result["error"] = f"Profundidad {bit_depth}-bit no soportada"
                return result

            path = Path(target).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            request = CaptureRequest(
                device=device,
                output_path=str(path),
                format=fmt,
                sample_rate=int(sample_rate),
                bit_depth=int(bit_depth),
                channels=int(channels),
                dsp_filters=self._normalise_filters(apply_dsp),
            )
            try:
                command = self.build_command(request)
            except Exception as exc:
                result["error"] = str(exc)
                return result

            session = RecordingSession(
                session_id=f"rec_{uuid.uuid4().hex[:12]}",
                input_device=device,
                output_path=str(path),
                format=fmt,
                sample_rate=request.sample_rate,
                bit_depth=request.bit_depth,
                channels=request.channels,
                start_time=time.monotonic(),
                status=RecordingStatus.RECORDING.value,
            )
            self.active_session = session
            self._stderr_tail.clear()
            self._stop_event.clear()
            self._manual_stop = False

            logger.info("Starting vinyl capture: %s", " ".join(command))
            try:
                self._process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            except Exception as exc:
                session.status = RecordingStatus.FAILED.value
                session.error = str(exc)
                result["error"] = str(exc)
                return result

            self.is_recording = True
            self.is_paused = False
            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                name="vinyl-ffmpeg-stderr",
                daemon=True,
            )
            self._stderr_thread.start()
            self.recording_thread = threading.Thread(
                target=self._monitor_process,
                name="vinyl-ffmpeg-monitor",
                daemon=True,
            )
            self.recording_thread.start()

            time.sleep(0.08)
            if self._process.poll() is not None:
                self._finalize_process()
                result["error"] = session.error or self._last_error()
                return result

            result["success"] = True
            result["session_id"] = session.session_id
            result["output_path"] = session.output_path
            return result

    def _drain_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        channel = 0
        try:
            for raw_line in process.stderr:
                line = raw_line.strip()
                if not line:
                    continue
                self._stderr_tail.append(line)
                if len(self._stderr_tail) > 80:
                    del self._stderr_tail[:-80]
                channel_match = re.search(r"Channel:\s*(\d+)", line)
                if channel_match:
                    channel = int(channel_match.group(1))
                    continue
                self._parse_level_line(line, channel)
        except Exception:
            logger.debug("FFmpeg stderr reader stopped", exc_info=True)

    def _parse_level_line(self, line: str, channel: int) -> None:
        session = self.active_session
        if session is None:
            return
        peak_match = re.search(r"Peak level dB:\s*(-?inf|[-+]?\d+(?:\.\d+)?)", line)
        rms_match = re.search(r"RMS level dB:\s*(-?inf|[-+]?\d+(?:\.\d+)?)", line)
        if not peak_match and not rms_match:
            return

        def parse(value: str) -> float:
            return -60.0 if "inf" in value.lower() else max(-120.0, float(value))

        levels = session.levels
        if peak_match:
            value = parse(peak_match.group(1))
            if channel == 2:
                levels.right_peak_dbfs = value
                levels.clipping_right = value >= -0.1
            else:
                levels.left_peak_dbfs = value
                levels.clipping_left = value >= -0.1
                if session.channels == 1:
                    levels.right_peak_dbfs = value
                    levels.clipping_right = levels.clipping_left
        if rms_match:
            value = parse(rms_match.group(1))
            if channel == 2:
                levels.right_rms_dbfs = value
            else:
                levels.left_rms_dbfs = value
                if session.channels == 1:
                    levels.right_rms_dbfs = value

    def _monitor_process(self) -> None:
        process = self._process
        if process is None:
            return
        while process.poll() is None and not self._stop_event.wait(0.25):
            self._update_session_metrics()
        self._update_session_metrics()
        self._finalize_process()

    def _elapsed(self) -> float:
        session = self.active_session
        if session is None or session.start_time <= 0:
            return 0.0
        now = session.paused_at if session.paused_at is not None else time.monotonic()
        return max(0.0, now - session.start_time - session.total_paused)

    def _update_session_metrics(self) -> None:
        session = self.active_session
        if session is None:
            return
        session.duration = self._elapsed()
        try:
            session.file_size = Path(session.output_path).stat().st_size
        except OSError:
            session.file_size = 0

    def _finalize_process(self) -> None:
        with self._state_lock:
            session = self.active_session
            process = self._process
            if session is None:
                self.is_recording = False
                self.is_paused = False
                return
            self._update_session_metrics()
            session.end_time = time.time()
            return_code = process.poll() if process is not None else 0
            if self._manual_stop or return_code == 0:
                session.status = RecordingStatus.COMPLETED.value
            else:
                session.status = RecordingStatus.FAILED.value
                session.error = self._last_error()
            self.is_recording = False
            self.is_paused = False
            session.paused_at = None

    def _last_error(self) -> str:
        meaningful = [
            line
            for line in self._stderr_tail
            if "error" in line.lower()
            or "invalid" in line.lower()
            or "cannot" in line.lower()
            or "failed" in line.lower()
        ]
        if meaningful:
            return meaningful[-1][-500:]
        if self._stderr_tail:
            return self._stderr_tail[-1][-500:]
        return "El proceso de captura finalizó inesperadamente"

    def pause_recording(self) -> bool:
        with self._state_lock:
            if not self.is_recording or self.is_paused or self._process is None:
                return False
            if os.name == "nt":
                logger.warning("Pause is not supported by the FFmpeg backend on Windows")
                return False
            try:
                os.kill(self._process.pid, signal.SIGSTOP)
            except OSError:
                logger.exception("Unable to pause FFmpeg capture")
                return False
            self.is_paused = True
            if self.active_session is not None:
                self.active_session.status = RecordingStatus.PAUSED.value
                self.active_session.paused_at = time.monotonic()
            return True

    def resume_recording(self) -> bool:
        with self._state_lock:
            if not self.is_recording or not self.is_paused or self._process is None:
                return False
            if os.name == "nt":
                return False
            try:
                os.kill(self._process.pid, signal.SIGCONT)
            except OSError:
                logger.exception("Unable to resume FFmpeg capture")
                return False
            if self.active_session is not None:
                if self.active_session.paused_at is not None:
                    self.active_session.total_paused += (
                        time.monotonic() - self.active_session.paused_at
                    )
                self.active_session.paused_at = None
                self.active_session.status = RecordingStatus.RECORDING.value
            self.is_paused = False
            return True

    def stop_recording(self) -> dict[str, Any]:
        with self._state_lock:
            process = self._process
            if not self.is_recording:
                return {
                    "success": False,
                    "error": "No hay grabación activa",
                    "output_path": (
                        self.active_session.output_path if self.active_session else ""
                    ),
                }
            if process is None:
                self.is_recording = False
                self.is_paused = False
                if self.recording_thread is not None:
                    try:
                        self.recording_thread.join(timeout=1)
                    except Exception:
                        pass
                return {
                    "success": True,
                    "output_path": (
                        self.active_session.output_path if self.active_session else ""
                    ),
                    "duration": (
                        self.active_session.duration if self.active_session else 0.0
                    ),
                    "file_size": (
                        self.active_session.file_size if self.active_session else 0
                    ),
                }
            if self.is_paused and os.name != "nt":
                try:
                    os.kill(process.pid, signal.SIGCONT)
                except OSError:
                    pass
            self._manual_stop = True
            self._stop_event.set()
            try:
                if process.stdin is not None:
                    process.stdin.write("q\n")
                    process.stdin.flush()
                process.wait(timeout=8)
            except Exception:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

        thread = self.recording_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)
        self._finalize_process()
        session = self.active_session
        return {
            "success": True,
            "output_path": session.output_path if session else "",
            "duration": session.duration if session else 0.0,
            "file_size": session.file_size if session else 0,
        }

    def add_marker(
        self, timestamp: Optional[float] = None, label: str = ""
    ) -> dict[str, Any]:
        session = self.active_session
        if session is None or not self.is_recording:
            return {"success": False, "error": "No hay grabación activa"}
        ts = self._elapsed() if timestamp is None else max(0.0, float(timestamp))
        marker = {
            "timestamp": ts,
            "label": label or f"Pista {len(session.markers) + 1}",
            "created_at": time.time(),
        }
        session.markers.append(marker)
        session.markers.sort(key=lambda item: float(item["timestamp"]))
        return {"success": True, "marker": marker}

    def split_by_markers(self, input_file: str, output_dir: str) -> dict[str, Any]:
        session = self.active_session
        if session is None or not session.markers:
            return {
                "success": False,
                "tracks": [],
                "errors": ["No hay marcadores para dividir"],
            }
        from .exporter import split_by_markers

        return split_by_markers(
            input_path=input_file,
            output_dir=output_dir,
            markers=session.markers,
            total_duration=session.duration,
        )

    def get_recording_status(self) -> dict[str, Any]:
        session = self.active_session
        if session is None:
            empty_levels = StereoLevels().to_dict()
            return {
                "active": False,
                "paused": False,
                "status": RecordingStatus.IDLE.value,
                "duration": 0.0,
                "file_size": 0,
                "markers_count": 0,
                "markers": [],
                "levels": empty_levels,
                "level": -60.0,
            }
        self._update_session_metrics()
        levels = session.levels.to_dict()
        return {
            "active": self.is_recording,
            "paused": self.is_paused,
            "session_id": session.session_id,
            "device": session.input_device.name,
            "device_id": session.input_device.device_id,
            "duration": session.duration,
            "file_size": session.file_size,
            "markers_count": len(session.markers),
            "markers": list(session.markers),
            "status": session.status,
            "output_path": session.output_path,
            "format": session.format,
            "sample_rate": session.sample_rate,
            "bit_depth": session.bit_depth,
            "channels": session.channels,
            "levels": levels,
            "level": max(levels["left_peak_dbfs"], levels["right_peak_dbfs"]),
            "error": session.error,
        }

    def cleanup(self) -> None:
        if self.is_recording:
            self.stop_recording()
        self._process = None
        self.recording_thread = None
        self._stderr_thread = None


AudioDevice = CaptureDevice
ADCRecorderService = VinylRecorderService
