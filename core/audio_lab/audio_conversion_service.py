"""AudioConversionService — convert audio files between formats.

Flow: selection → profile → format → codec → quality → sample rate →
bit depth → channel policy → metadata → artwork → ReplayGain →
output folder → naming → collisions → space → preview → confirm →
job → progress → cancel → results → library integration.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from core.worker_manager import WorkerManager

logger = logging.getLogger("michi.audio_lab.conversion")

AUDIO_ONLY_FORMATS = {"FLAC", "WAV", "AIFF", "MP3", "AAC", "Opus", "Vorbis", "ALAC"}


@dataclass
class ConversionJob:
    id: str = ""
    status: str = "pending"
    progress: float = 0.0
    source: str = ""
    target: str = ""
    format: str = ""
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0


@dataclass
class ConversionProfile:
    name: str = "Custom"
    format: str = "FLAC"
    codec: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    copy_metadata: bool = True
    copy_artwork: bool = True
    apply_replaygain: bool = False
    filename_template: str = "{artist} - {title}"
    output_dir: str = ""


class AudioConversionService(QObject):
    conversionStarted = Signal(str)
    conversionProgress = Signal(str, float)
    conversionCompleted = Signal(str, str)
    conversionFailed = Signal(str, str)

    def __init__(self, db=None, wm: WorkerManager | None = None,
                 profile_service=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._wm = wm
        self._profile_service = profile_service
        self._active_jobs: dict[str, ConversionJob] = {}

    def preview(self, source: str, profile: ConversionProfile) -> dict[str, Any]:
        if not source or not os.path.isfile(source):
            return {"ok": False, "error": "SOURCE_NOT_FOUND"}
        if profile.format not in AUDIO_ONLY_FORMATS:
            return {"ok": False, "error": f"UNSUPPORTED_FORMAT:{profile.format}"}
        src_path = Path(source)
        estimated_size = src_path.stat().st_size * self._size_ratio(profile.format)
        target_name = profile.filename_template.format(
            artist="{artist}", title=src_path.stem, album="{album}"
        )
        target_name = target_name.replace("{artist}", "Unknown").replace("{album}", "Unknown")
        target_path = Path(profile.output_dir) / f"{target_name}.{profile.format.lower()}"
        space_ok = True
        if profile.output_dir:
            try:
                free = shutil.disk_usage(profile.output_dir).free
                space_ok = free > estimated_size * 2
            except Exception:
                space_ok = True
        return {
            "ok": True,
            "source": source,
            "target": str(target_path),
            "estimated_size": estimated_size,
            "space_ok": space_ok,
            "format": profile.format,
            "collision": target_path.exists(),
        }

    def convert(self, source: str, profile: ConversionProfile,
                on_progress: Callable | None = None,
                on_done: Callable | None = None) -> str:
        job_id = f"conv_{int(time.time())}_{id(source)}"
        job = ConversionJob(id=job_id, source=source, format=profile.format)
        self._active_jobs[job_id] = job
        self.conversionStarted.emit(job_id)

        if self._wm:
            task_id = f"audio_conv_{job_id}"

            def _run():
                result = self._do_convert(source, profile, job)
                return result

            def _completed(result):
                job.status = "completed" if result.get("ok") else "failed"
                job.finished_at = time.time()
                if result.get("ok"):
                    job.target = result.get("target", "")
                    self.conversionCompleted.emit(job_id, job.target)
                else:
                    job.error = result.get("error", "")
                    self.conversionFailed.emit(job_id, job.error)
                if on_done:
                    on_done(result)

            self._wm.run_task(task_id, _run, on_done=_completed,
                              cancellable=True, owner="audio_lab_conv")
        else:
            result = self._do_convert(source, profile, job)
            job.finished_at = time.time()
            if result.get("ok"):
                job.status = "completed"
                job.target = result.get("target", "")
                self.conversionCompleted.emit(job_id, job.target)
            else:
                job.status = "failed"
                job.error = result.get("error", "")
                self.conversionFailed.emit(job_id, job.error)
            if on_done:
                on_done(result)

        return job_id

    def _do_convert(self, source: str, profile: ConversionProfile,
                    job: ConversionJob) -> dict[str, Any]:
        try:
            fmt = profile.format.lower()
            target_dir = profile.output_dir or str(Path(source).parent)
            target_name = f"{Path(source).stem}.{fmt}"
            target_path = str(Path(target_dir) / target_name)
            job.target = target_path

            import subprocess
            cmd = self._build_command(source, target_path, profile)
            if not cmd:
                job.status = "failed"
                job.error = "NO_COMMAND_AVAILABLE"
                return {"ok": False, "error": "NO_COMMAND_AVAILABLE"}

            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if proc.returncode != 0:
                return {"ok": False, "error": proc.stderr[:500] or "Conversion failed"}

            if not os.path.isfile(target_path):
                return {"ok": False, "error": "Output file not created", "error_code": "FILE_NOT_CREATED"}
            return {"ok": True, "target": target_path, "format": profile.format}
        except Exception as e:
            logger.exception("Conversion failed for %s", source)
            return {"ok": False, "error": str(e)}

    def _build_command(self, source: str, target: str, profile: ConversionProfile) -> list[str] | None:
        fmt = profile.format.lower()
        if fmt == "flac":
            cmd = ["ffmpeg", "-i", source, "-c:a", "flac"]
            if profile.bit_depth > 0:
                cmd += ["-sample_fmt", f"s{profile.bit_depth}"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd += ["-compression_level", "8", target]
            return cmd
        if fmt == "wav":
            cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s16le"]
            if profile.bit_depth == 24:
                cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s24le"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd.append(target)
            return cmd
        if fmt == "aiff":
            cmd = ["ffmpeg", "-i", source, "-c:a", "pcm_s16be"]
            if profile.sample_rate > 0:
                cmd += ["-ar", str(profile.sample_rate)]
            cmd.append(target)
            return cmd
        if fmt == "mp3":
            cmd = ["ffmpeg", "-i", source, "-c:a", "libmp3lame"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd += ["-q:a", "2", target]
            return cmd
        if fmt in ("aac", "m4a"):
            cmd = ["ffmpeg", "-i", source, "-c:a", "aac"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd.append(target)
            return cmd
        if fmt == "opus":
            cmd = ["ffmpeg", "-i", source, "-c:a", "libopus"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd.append(target)
            return cmd
        if fmt in ("ogg", "vorbis"):
            cmd = ["ffmpeg", "-i", source, "-c:a", "libvorbis"]
            if profile.bitrate > 0:
                cmd += ["-b:a", f"{profile.bitrate}k"]
            cmd += ["-q:a", "3", target]
            return cmd
        if fmt == "alac":
            cmd = ["ffmpeg", "-i", source, "-c:a", "alac", target]
            return cmd
        return None

    def cancel(self, job_id: str) -> bool:
        if job_id in self._active_jobs:
            self._active_jobs[job_id].status = "cancelled"
            return True
        return False

    def _size_ratio(self, fmt: str) -> float:
        return {"MP3": 0.1, "AAC": 0.1, "Opus": 0.08, "Vorbis": 0.12,
                "FLAC": 0.5, "ALAC": 0.5, "WAV": 1.0, "AIFF": 1.0}.get(fmt, 0.5)
